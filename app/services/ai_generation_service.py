#=== Fichier: ./app/services/ai_generation_service.py ===

import logging
import requests
import json
import time
import uuid
import re
from typing import Dict, Any, List, Tuple, Optional, Union

from sqlalchemy.orm import Session, joinedload
from .. import models, schemas
from ..config import settings

# ==============================================================================
# CONFIGURATION DU LOGGER "AI-KERNEL" (Niveau Expert)
# ==============================================================================
# Ce logger est configuré pour capturer absolument tout ce qui entre et sort.
logger = logging.getLogger("ai_kernel")
logger.setLevel(logging.DEBUG)

if not logger.handlers:
    handler = logging.StreamHandler()
    # Format riche avec fichier et ligne pour retrouver l'origine du log
    formatter = logging.Formatter(
        '%(asctime)s - [AI-KERNEL] - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

# Constantes API
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
# Modèle choisi : Mistral 7B Instruct (Bon rapport qualité/prix/performance pour le roleplay)
# Alternatives : 'openai/gpt-4o-mini', 'anthropic/claude-3-haiku'
MODEL_NAME = "mistralai/devstral-2512:free" 

# Configuration de résilience
MAX_RETRIES = 3
TIMEOUT_SECONDS = 60  # On laisse du temps à l'IA pour réfléchir

def _clean_json_string(json_str: str) -> str:
    """
    Nettoie une chaîne JSON brute renvoyée par un LLM.
    Les LLM aiment bien entourer le JSON de balises Markdown ```json ... ``` 
    ou ajouter du texte avant/après.
    """
    # 1. Supprimer les balises Markdown
    if "```" in json_str:
        # Regex pour capturer le contenu entre ```json et ``` ou juste ``` et ```
        pattern = r"```(?:json)?\s*(.*?)\s*```"
        match = re.search(pattern, json_str, re.DOTALL)
        if match:
            json_str = match.group(1)
    
    # 2. Trouver la première accolade ouvrante et la dernière fermante
    start = json_str.find("{")
    end = json_str.rfind("}")
    
    if start != -1 and end != -1:
        json_str = json_str[start : end + 1]
    
    return json_str.strip()

def _call_openrouter_api(
    input_data: Union[str, List[Dict[str, str]]], 
    json_mode: bool = False,
    temperature: float = 0.7,
    request_tag: str = "GENERIC"
) -> Any:
    """
    Fonction noyau (Core) pour appeler l'API LLM.
    Elle est conçue pour être une boîte noire totalement transparente via les logs.
    
    :param input_data: Le prompt (str) ou la liste de messages (list).
    :param json_mode: Force le modèle à produire du JSON et active le validateur.
    :param temperature: Créativité (0.0 = Rigide, 1.0 = Folie).
    :param request_tag: Étiquette pour suivre les logs (ex: PATIENT, EXAM, EVAL).
    """
    call_id = str(uuid.uuid4())[:8] # ID unique pour tracer CET appel dans les logs
    
    logger.info(f"⚡ [AI-{call_id}] DÉBUT TRANSACTION | Tag: {request_tag} | Mode JSON: {json_mode}")

    # 1. Normalisation du Payload
    messages = []
    if isinstance(input_data, str):
        messages = [{"role": "user", "content": input_data}]
    else:
        messages = input_data

    # ==========================================================================
    # 🔍 PROMPT DUMP - C'est ici qu'on voit ce que l'IA voit
    # ==========================================================================
    logger.debug(f"\n{'='*40} [AI-{call_id}] PROMPT ENVOYÉ {'='*40}")
    for i, msg in enumerate(messages):
        role = msg.get('role', 'unknown').upper()
        content = msg.get('content', '')
        # On logue tout, même si c'est long. C'est le but du debug expert.
        logger.debug(f"[{i}] {role}:\n{content}\n{'-'*20}")
    logger.debug(f"{'='*100}\n")
    # ==========================================================================

    headers = {
        "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://expert-cmck.onrender.com",
        "X-Title": "STI Medical Expert System"
    }
    
    payload = {
        "model": MODEL_NAME,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": 1500, # Assez large pour des réponses détaillées
    }

    if json_mode:
        # Certains modèles supportent 'json_object', d'autres non.
        # Mistral 7B Instruct Free le gère parfois mal via API, on compte sur le prompt.
        # On ajoute quand même le hint si l'API le supporte.
        payload["response_format"] = {"type": "json_object"}

    # 2. Boucle de Tentatives (Retry Pattern)
    attempt = 0
    
    while attempt < MAX_RETRIES:
        attempt += 1
        start_time = time.time()
        
        try:
            if attempt > 1:
                logger.warning(f"   🔄 [AI-{call_id}] Tentative de connexion {attempt}/{MAX_RETRIES}...")
                time.sleep(2 * attempt) # Backoff exponentiel (2s, 4s, 6s)

            logger.debug(f"   🚀 [AI-{call_id}] Envoi requête POST vers {OPENROUTER_API_URL}...")
            
            response = requests.post(
                OPENROUTER_API_URL, 
                headers=headers, 
                data=json.dumps(payload), 
                timeout=TIMEOUT_SECONDS
            )
            
            latency = time.time() - start_time
            
            # --- Analyse de la Réponse HTTP ---
            if response.status_code == 200:
                response_data = response.json()
                
                # Metrics
                usage = response_data.get('usage', {})
                prompt_tok = usage.get('prompt_tokens', 0)
                comp_tok = usage.get('completion_tokens', 0)
                logger.info(f"   ✅ [AI-{call_id}] HTTP 200 OK | {latency:.2f}s | Tokens: {prompt_tok}in/{comp_tok}out")

                # Extraction du contenu
                try:
                    choice = response_data['choices'][0]
                    raw_content = choice['message']['content']
                    finish_reason = choice.get('finish_reason', 'unknown')
                    
                    if finish_reason == 'length':
                        logger.warning(f"   ⚠️ [AI-{call_id}] Attention: La réponse a été tronquée (max_tokens atteint).")

                    # ==========================================================
                    # 🔍 RESPONSE DUMP - Ce que l'IA a réellement répondu
                    # ==========================================================
                    logger.debug(f"\n{'='*40} [AI-{call_id}] RÉPONSE BRUTE {'='*40}")
                    logger.debug(f"{raw_content}")
                    logger.debug(f"{'='*100}\n")
                    # ==========================================================

                    # Traitement JSON si requis
                    if json_mode:
                        cleaned_content = _clean_json_string(raw_content)
                        try:
                            parsed_json = json.loads(cleaned_content)
                            logger.info(f"   ✅ [AI-{call_id}] JSON parsé avec succès.")
                            return parsed_json
                        except json.JSONDecodeError as je:
                            logger.error(f"   ❌ [AI-{call_id}] Échec du parsing JSON.")
                            logger.error(f"      Brut nettoyé : {cleaned_content}")
                            logger.error(f"      Erreur : {str(je)}")
                            # En debug expert, on veut savoir si c'est l'IA qui déraille
                            # On ne retry pas un échec de logique (parsing), on lève l'exception
                            raise ValueError(f"L'IA n'a pas produit un JSON valide : {str(je)}")
                    
                    # Mode texte simple
                    return raw_content

                except (KeyError, IndexError) as e:
                    logger.error(f"   ❌ [AI-{call_id}] Structure de réponse API inattendue: {response_data}")
                    raise ValueError("Erreur de format API OpenRouter")

            elif response.status_code == 429:
                logger.warning(f"   ⚠️ [AI-{call_id}] Rate Limit atteint (429). Pause forcée.")
                time.sleep(5) # Pause fixe en cas de surcharge
                continue 
            
            elif response.status_code >= 500:
                logger.error(f"   🔥 [AI-{call_id}] Erreur Serveur IA ({response.status_code}).")
                logger.debug(f"      Body: {response.text}")
                continue
            
            else:
                # Erreur client (400, 401, 403) -> Pas de retry, c'est de notre faute (clé API, format)
                logger.critical(f"   ⛔ [AI-{call_id}] Erreur Client {response.status_code}.")
                logger.critical(f"      Réponse: {response.text}")
                response.raise_for_status()

        except requests.exceptions.RequestException as e:
            logger.error(f"   🌐 [AI-{call_id}] Exception Réseau : {str(e)}")
            continue

    # Si on sort de la boucle, c'est l'échec total
    logger.critical(f"   💀 [AI-{call_id}] ÉCHEC TOTAL après {MAX_RETRIES} tentatives.")
    
    if json_mode:
        return {} # Retour vide safe
    return "(Erreur technique : Le service d'IA est injoignable pour le moment.)"


# ==============================================================================
# SERVICES MÉTIERS (Business Logic)
# ==============================================================================

def generate_patient_reply_chat(messages: List[Dict[str, str]]) -> str:
    """
    Génère la réplique du patient. C'est ici qu'on ajuste la 'température'
    pour avoir un patient plus ou moins vivant.
    """
    logger.info(f"🎭 [AI-ACTOR] Demande de réplique patient ({len(messages)} messages dans l'historique)")
    
    # Température 0.85 : Assez créatif pour varier les formules de politesse et la douleur,
    # mais pas trop pour ne pas inventer des symptômes délirants.
    response = _call_openrouter_api(
        input_data=messages,
        json_mode=False,
        temperature=0.85,
        request_tag="PATIENT_ACTOR"
    )
    
    if isinstance(response, str):
        return response
    return "..."


def generate_exam_result(
    case: models.ClinicalCase, 
    session_history: List[str], 
    exam_name: str
) -> Dict[str, Any]:
    """
    Génère un résultat d'examen médical réaliste basé sur le cas.
    """
    logger.info(f"🔬 [AI-LAB] Demande examen : {exam_name}")
    
    # On fournit un contexte riche pour que l'IA puisse inventer des chiffres cohérents
    # ex: Si le cas est une anémie, l'IA doit mettre une hémoglobine basse.
    
    lab_data_context = json.dumps(case.donnees_paracliniques, ensure_ascii=False) if case.donnees_paracliniques else "Non spécifié"
    
    prompt = f"""
ROLE: Tu es un automate de laboratoire d'hôpital de haute précision.
TA MISSION: Générer le rapport technique d'un examen médical.

CONTEXTE CLINIQUE DU PATIENT:
- Pathologie (Connue du système, inconnue de l'étudiant) : {case.pathologie_principale.nom_fr}
- Histoire : {case.presentation_clinique.get('histoire_maladie', '')}
- Données biologiques réelles du cas : {lab_data_context}

DEMANDE DE L'ÉTUDIANT :
"Je souhaite prescrire : {exam_name}"

CONSIGNES DE GÉNÉRATION :
1. Si l'examen est pertinent pour la pathologie, génère des valeurs anormales COHÉRENTES avec la maladie.
2. Si l'examen n'a rien à voir, génère des résultats NORMAUX.
3. Le format de sortie doit être un JSON strict.
4. "rapport": Une description technique détaillée (chiffres, unités, aspect).
5. "conclusion": Une phrase de synthèse clinique (ex: "Syndrome inflammatoire modéré").

FORMAT JSON ATTENDU :
{{
  "rapport": "...",
  "conclusion": "..."
}}
"""
    result = _call_openrouter_api(
        input_data=prompt,
        json_mode=True,
        temperature=0.3, # Faible température pour rester factuel et précis
        request_tag="EXAM_GENERATION"
    )
    
    # Fallback structurel
    if not result or not isinstance(result, dict):
        logger.error("   ❌ [AI-LAB] L'IA n'a pas renvoyé de dict pour l'examen.")
        return {
            "rapport": "Erreur technique lors de l'analyse de l'échantillon.",
            "conclusion": "Résultat non disponible."
        }
    
    return {
        "rapport": result.get("rapport", "Données techniques manquantes."),
        "conclusion": result.get("conclusion", "R.A.S.")
    }


def evaluate_final_submission(
    db: Session,
    case: models.ClinicalCase,
    submission: schemas.simulation.SubmissionRequest,
    session_history: list
) -> Tuple[schemas.simulation.EvaluationResult, str, str]:
    """
    Le Juge Suprême. Évalue la performance de l'étudiant.
    """
    logger.info("⚖️ [AI-JUDGE] Début du processus d'évaluation finale")

    # 1. Récupération de la Vérité (Correct)
    correct_pathology = case.pathologie_principale.nom_fr
    
    # Récupération des traitements attendus (Jointure)
    correct_treatments_objs = db.query(models.TraitementPathologie).options(
        joinedload(models.TraitementPathologie.medicament)
    ).filter(
        models.TraitementPathologie.pathologie_id == case.pathologie_principale_id
    ).all()
    
    correct_treatments_list = []
    for t in correct_treatments_objs:
        med_name = t.medicament.nom_commercial or t.medicament.dci
        correct_treatments_list.append(f"- {med_name} ({t.type_traitement})")
    
    correct_treatments_str = "\n".join(correct_treatments_list) if correct_treatments_list else "Aucun traitement spécifique défini en base."

    # 2. Récupération de la Soumission (Student)
    student_pathology_obj = db.query(models.Disease).filter(
        models.Disease.id == submission.diagnosed_pathology_id
    ).first()
    student_pathology = student_pathology_obj.nom_fr if student_pathology_obj else f"ID Inconnu ({submission.diagnosed_pathology_id})"

    student_meds_objs = db.query(models.Medication).filter(
        models.Medication.id.in_(submission.prescribed_medication_ids)
    ).all()
    student_meds_str = ", ".join([m.nom_commercial for m in student_meds_objs]) if student_meds_objs else "Aucun médicament prescrit."

    # 3. Formatage de l'historique pour le Juge
    # On limite la taille pour ne pas exploser le contexte, mais on garde l'essentiel
    history_summary = json.dumps(session_history, indent=2, ensure_ascii=False)
    if len(history_summary) > 4000:
        history_summary = history_summary[:4000] + "... (tronqué)"

    # 4. Prompt d'Évaluation (Critique)
    prompt = f"""
TU ES UN PROFESSEUR DE MÉDECINE EXPERT (JURY D'EXAMEN).
Tu dois noter un étudiant sur la résolution d'un cas clinique. Sois juste mais rigoureux.

--- LE CAS CLINIQUE (CORRIGÉ) ---
DIAGNOSTIC CORRECT : {correct_pathology}
TRAITEMENTS ATTENDUS :
{correct_treatments_str}

--- LA SOUMISSION DE L'ÉTUDIANT ---
DIAGNOSTIC PROPOSÉ : {student_pathology}
TRAITEMENTS PRESCRITS : {student_meds_str}

--- DÉROULEMENT DE LA CONSULTATION ---
{history_summary}

--- TA MISSION ---
Attribue 3 notes et rédige un feedback.
1. score_diagnostic (sur 10) : 10 si exact, 5 si famille proche, 0 si faux.
2. score_therapeutique (sur 5) : 5 si traitements clés présents, pénalité si médicaments dangereux ou inutiles.
3. score_demarche (sur 5) : Basé sur l'historique. A-t-il posé les bonnes questions ? Fait les bons examens ?

FORMAT JSON ATTENDU :
{{
  "score_diagnostic": float,
  "score_therapeutique": float,
  "score_demarche": float,
  "feedback_global": "Texte pédagogique expliquant les erreurs et les réussites. Sois direct.",
  "recommendation_next_step": "Conseil pour la prochaine fois (ex: Réviser la cardio...)"
}}
"""

    # 5. Appel IA
    logger.info("   🚀 [AI-JUDGE] Envoi du dossier au jury (LLM)...")
    eval_json = _call_openrouter_api(
        input_data=prompt,
        json_mode=True,
        temperature=0.2, # Très faible température pour une notation stable
        request_tag="EVALUATION_JURY"
    )

    # 6. Parsing Résultat
    try:
        s_diag = float(eval_json.get("score_diagnostic", 0))
        s_ther = float(eval_json.get("score_therapeutique", 0))
        s_dem = float(eval_json.get("score_demarche", 0))
        
        # Calcul total
        total = s_diag + s_ther + s_dem
        
        # Clamp (au cas où l'IA hallucine une note de 12/10)
        s_diag = min(10, max(0, s_diag))
        s_ther = min(5, max(0, s_ther))
        s_dem = min(5, max(0, s_dem))
        total = min(20, max(0, total))

        logger.info(f"   🏆 [AI-JUDGE] Verdict rendu : {total}/20")
        logger.debug(f"      Détails : Diag={s_diag}, Ther={s_ther}, Dem={s_dem}")

        result_obj = schemas.simulation.EvaluationResult(
            score_diagnostic=s_diag,
            score_therapeutique=s_ther,
            score_demarche=s_dem,
            score_total=total
        )
        
        return result_obj, eval_json.get("feedback_global", ""), eval_json.get("recommendation_next_step", "")

    except Exception as e:
        logger.error(f"   ❌ [AI-JUDGE] Erreur lecture verdict : {e}")
        # En cas de crash du juge, on met 0 pour forcer une révision manuelle (ou éviter de valider à tort)
        return schemas.simulation.EvaluationResult(
            score_diagnostic=0, score_therapeutique=0, score_demarche=0, score_total=0
        ), "Erreur technique lors de l'évaluation. Veuillez contacter l'administration.", "Réessayer."

def generate_hint(case: models.ClinicalCase, session_history: List[str], hint_level: int) -> Tuple[str, str]:
    """
    Génère un indice contextuel pour débloquer l'étudiant.
    """
    logger.info(f"💡 [AI-TUTOR] Demande d'indice niveau {hint_level}")
    
    level_desc = "Indice vague, une simple question pour orienter."
    if hint_level == 1: level_desc = "Indice modéré, pointer vers une zone anatomique ou un type d'examen."
    if hint_level >= 2: level_desc = "Indice fort, suggérer une piste diagnostique précise sans donner la réponse."

    prompt = f"""
ROLE: Tuteur pédagogique en médecine.
CONTEXTE: L'étudiant est bloqué sur un cas de {case.pathologie_principale.nom_fr}.
HISTORIQUE: {str(session_history)[-800:]}

TACHE: Fournir un indice de niveau : {hint_level}/3.
DESCRIPTION DU NIVEAU: {level_desc}

JSON ATTENDU:
{{
  "hint_type": "question_socratique" OU "rappel_theorique" OU "piste_clinique",
  "content": "Le texte de l'indice..."
}}
"""
    result = _call_openrouter_api(prompt, json_mode=True, request_tag="HINT_GEN")
    
    if isinstance(result, dict):
        return result.get("hint_type", "info"), result.get("content", "Relisez bien l'anamnèse.")
    return "info", "Concentrez-vous sur les symptômes principaux."