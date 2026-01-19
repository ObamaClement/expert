#=== Fichier: ./app/services/ai_generation_service.py ===

import logging
import requests
import json
import time
import uuid
import re
import traceback
from typing import Dict, Any, List, Tuple, Optional, Union
from enum import Enum

from sqlalchemy.orm import Session, joinedload
from .. import models, schemas
from ..config import settings
from ..core.prompts.exam_prompts import exam_prompt_builder

# ==============================================================================
# CONFIGURATION DU LOGGER "AI-KERNEL" (Niveau Expert / Debugging)
# ==============================================================================
# Ce logger est configuré pour capturer absolument tout ce qui entre et sort.
# Il est distinct du logger principal pour permettre un filtrage fin.
logger = logging.getLogger("ai_kernel")
logger.setLevel(logging.DEBUG)

if not logger.handlers:
    handler = logging.StreamHandler()
    # Format enrichi : Date - Logger - Niveau - Fichier:Ligne - Message
    formatter = logging.Formatter(
        '%(asctime)s - [AI-KERNEL] - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

# ==============================================================================
# CONSTANTES ET CONFIGURATION
# ==============================================================================

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

# Modèle choisi : Mistral 7B Instruct (Bon rapport qualité/prix/performance pour le roleplay)
# Alternatives testées : 'openai/gpt-4o-mini', 'anthropic/claude-3-haiku'
MODEL_NAME = "mistralai/devstral-2512:free" 

# Configuration de résilience
MAX_RETRIES_NETWORK = 3    # Tentatives en cas d'échec de connexion
MAX_RETRIES_LOGIC = 2      # Tentatives en cas de JSON malformé
TIMEOUT_SECONDS = 60       # Timeout strict pour ne pas bloquer le worker

class AiTaskType(Enum):
    """Énumération des types de tâches pour le tagging des logs."""
    CHAT_PATIENT = "CHAT_PATIENT"
    EXAM_GENERATION = "EXAM_GENERATION"
    EVALUATION = "EVALUATION"
    HINT_GENERATION = "HINT_GENERATION"

# ==============================================================================
# UTILITAIRES DE NETTOYAGE ET VALIDATION
# ==============================================================================

def _clean_json_string(json_str: str, trace_id: str = "N/A") -> str:
    """
    Nettoie une chaîne JSON brute renvoyée par un LLM.
    Les LLM aiment bien entourer le JSON de balises Markdown ```json ... ``` 
    ou ajouter du texte avant/après ("Voici le rapport : ...").
    
    :param json_str: La chaîne brute reçue de l'API.
    :param trace_id: ID de traçabilité pour les logs.
    :return: Une chaîne contenant uniquement le JSON potentiel.
    """
    original_len = len(json_str)
    
    # 1. Supprimer les balises Markdown (classique)
    if "```" in json_str:
        logger.debug(f"   🧹 [{trace_id}] Détection de blocs Markdown, nettoyage en cours...")
        # Regex pour capturer le contenu entre ```json et ``` ou juste ``` et ```
        pattern = r"```(?:json)?\s*(.*?)\s*```"
        match = re.search(pattern, json_str, re.DOTALL)
        if match:
            json_str = match.group(1)
            logger.debug(f"   🧹 [{trace_id}] Bloc Markdown extrait.")
    
    # 2. Trouver la première accolade ouvrante et la dernière fermante
    # Cela élimine tout le texte introductif ("Sure, here is the JSON:")
    start = json_str.find("{")
    end = json_str.rfind("}")
    
    if start != -1 and end != -1:
        if start > 0 or end < len(json_str) - 1:
            logger.debug(f"   🧹 [{trace_id}] Rognage du texte autour du JSON (Indices: {start} à {end})")
            json_str = json_str[start : end + 1]
    
    final_len = len(json_str)
    if final_len != original_len:
        logger.debug(f"   ✨ [{trace_id}] Nettoyage terminé : {original_len} -> {final_len} chars")
        
    return json_str.strip()

def _validate_exam_json_structure(data: Dict[str, Any], trace_id: str) -> bool:
    """
    Vérifie que le JSON d'un examen contient les clés minimales requises.
    
    :param data: Le dictionnaire parsé.
    :return: True si valide, False sinon.
    """
    required_keys = ["rapport_complet", "conclusion"]
    missing = [k for k in required_keys if k not in data]
    
    if missing:
        logger.error(f"   ❌ [{trace_id}] Validation JSON échouée. Clés manquantes : {missing}")
        return False
    
    # Vérification du contenu non vide
    if not data.get("rapport_complet") or len(str(data["rapport_complet"])) < 10:
        logger.warning(f"   ⚠️ [{trace_id}] Validation suspecte : 'rapport_complet' semble trop court.")
        # On laisse passer mais on logue le warning
        
    return True

# ==============================================================================
# NOYAU D'APPEL API (CORE)
# ==============================================================================

def _call_openrouter_api(
    input_data: Union[str, List[Dict[str, str]]], 
    json_mode: bool = False,
    temperature: float = 0.7,
    task_type: AiTaskType = AiTaskType.CHAT_PATIENT,
    max_tokens: int = 1500
) -> Any:
    """
    Fonction noyau (Core) pour appeler l'API LLM.
    Elle est conçue pour être une boîte noire totalement transparente via les logs.
    
    :param input_data: Le prompt (str) ou la liste de messages (list).
    :param json_mode: Force le modèle à produire du JSON et active le validateur.
    :param temperature: Créativité (0.0 = Rigide, 1.0 = Folie).
    :param task_type: Type de tâche pour le logging.
    """
    trace_id = f"AI-{str(uuid.uuid4())[:6].upper()}"
    
    logger.info(f"⚡ [{trace_id}] DÉBUT TRANSACTION API | Tâche: {task_type.value} | Mode JSON: {json_mode}")
    logger.debug(f"   [{trace_id}] Config: Temp={temperature}, MaxTokens={max_tokens}, Model={MODEL_NAME}")

    # 1. Normalisation du Payload
    messages = []
    if isinstance(input_data, str):
        messages = [{"role": "user", "content": input_data}]
    else:
        messages = input_data

    # ==========================================================================
    # 🔍 PROMPT DUMP - LOGGING EXTENSIF
    # ==========================================================================
    logger.debug(f"\n{'='*40} [{trace_id}] PROMPT ENVOYÉ {'='*40}")
    for i, msg in enumerate(messages):
        role = msg.get('role', 'unknown').upper()
        content = msg.get('content', '')
        # Affichage sécurisé (tronqué si trop long pour la console, mais on garde assez pour debug)
        display_content = content if len(content) < 2000 else f"{content[:2000]}... [TRONQUÉ {len(content)-2000} chars]"
        logger.debug(f"[{i}] {role}:\n{display_content}\n{'-'*20}")
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
        "max_tokens": max_tokens,
    }

    if json_mode:
        # Hint pour les modèles compatibles OpenAI
        payload["response_format"] = {"type": "json_object"}

    # 2. Boucle de Tentatives (Retry Loop)
    attempt = 0
    
    while attempt < MAX_RETRIES_NETWORK:
        attempt += 1
        start_time = time.time()
        
        try:
            if attempt > 1:
                logger.warning(f"   🔄 [{trace_id}] Tentative réseau {attempt}/{MAX_RETRIES_NETWORK}...")
                # Backoff exponentiel (2s, 4s, 8s...)
                sleep_time = 2 ** attempt
                time.sleep(sleep_time)

            logger.debug(f"   🚀 [{trace_id}] Envoi requête POST vers {OPENROUTER_API_URL}...")
            
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
                
                # Metrics d'utilisation
                usage = response_data.get('usage', {})
                p_tok = usage.get('prompt_tokens', 0)
                c_tok = usage.get('completion_tokens', 0)
                logger.info(f"   ✅ [{trace_id}] Succès HTTP 200 | Latence: {latency:.2f}s | Tokens: {p_tok} in / {c_tok} out")

                # Extraction du contenu
                try:
                    if not response_data.get('choices'):
                        raise ValueError("Liste 'choices' vide dans la réponse API")

                    choice = response_data['choices'][0]
                    raw_content = choice['message']['content']
                    finish_reason = choice.get('finish_reason', 'unknown')
                    
                    if finish_reason == 'length':
                        logger.warning(f"   ⚠️ [{trace_id}] Attention: La réponse a été tronquée (max_tokens atteint). Le JSON risque d'être cassé.")

                    # ==========================================================
                    # 🔍 RESPONSE DUMP
                    # ==========================================================
                    logger.debug(f"\n{'='*40} [{trace_id}] RÉPONSE BRUTE IA {'='*40}")
                    logger.debug(f"{raw_content}")
                    logger.debug(f"{'='*100}\n")
                    # ==========================================================

                    # Traitement JSON si requis
                    if json_mode:
                        cleaned_content = _clean_json_string(raw_content, trace_id)
                        try:
                            parsed_json = json.loads(cleaned_content)
                            logger.info(f"   ✅ [{trace_id}] JSON parsé et validé techniquement.")
                            return parsed_json
                        except json.JSONDecodeError as je:
                            logger.error(f"   ❌ [{trace_id}] Échec du parsing JSON.")
                            logger.error(f"      Source nettoyée : {cleaned_content}")
                            logger.error(f"      Erreur Python : {str(je)}")
                            
                            # Logique de Retry "Logique" (si on n'a pas épuisé les essais)
                            # On pourrait relancer l'appel en disant à l'IA qu'elle s'est trompée,
                            # mais pour ce prototype, on lève l'erreur pour le catch global.
                            raise ValueError(f"L'IA n'a pas produit un JSON valide : {str(je)}")
                    
                    # Mode texte simple
                    return raw_content

                except (KeyError, IndexError, ValueError) as e:
                    logger.error(f"   ❌ [{trace_id}] Erreur structurelle réponse API : {str(e)}")
                    # On ne retry pas une erreur de structure interne, c'est probablement fatal
                    raise e

            elif response.status_code == 429:
                logger.warning(f"   ⚠️ [{trace_id}] Rate Limit atteint (429). Pause forcée.")
                time.sleep(5) # Pause fixe
                continue 
            
            elif response.status_code >= 500:
                logger.error(f"   🔥 [{trace_id}] Erreur Serveur IA ({response.status_code}).")
                logger.debug(f"      Body: {response.text}")
                continue
            
            else:
                # Erreur client (400, 401, 403) -> Pas de retry
                logger.critical(f"   ⛔ [{trace_id}] Erreur Client {response.status_code}.")
                logger.critical(f"      Réponse: {response.text}")
                response.raise_for_status()

        except requests.exceptions.RequestException as e:
            logger.error(f"   🌐 [{trace_id}] Exception Réseau : {str(e)}")
            continue

    # Si on sort de la boucle, c'est l'échec total
    logger.critical(f"   💀 [{trace_id}] ÉCHEC TOTAL après {MAX_RETRIES_NETWORK} tentatives réseaux.")
    
    if json_mode:
        return {} 
    return "(Erreur technique : Le service d'IA est injoignable pour le moment.)"


# ==============================================================================
# SERVICES MÉTIERS (Business Logic)
# ==============================================================================

def generate_patient_reply_chat(messages: List[Dict[str, str]]) -> str:
    """
    Génère la réplique du patient (Mode Chat).
    
    Cette fonction est appelée par le PatientActorService.
    Elle privilégie une température élevée pour la variété et le naturel.
    """
    try:
        response = _call_openrouter_api(
            input_data=messages,
            json_mode=False,
            temperature=0.85, # Créatif
            task_type=AiTaskType.CHAT_PATIENT,
            max_tokens=300 # Réponses courtes (patient)
        )
        
        if isinstance(response, str):
            return response
        return "..."
    except Exception as e:
        logger.error(f"Erreur dans generate_patient_reply_chat: {e}")
        return "(Silence...)"


def generate_exam_result(
    case: models.ClinicalCase, 
    session_history: List[str], 
    exam_name: str,
    exam_justification: str = "Non spécifiée"
) -> Dict[str, Any]:
    """
    Génère un résultat d'examen médical structuré.
    
    C'est le CŒUR de la fonctionnalité d'examen.
    Elle utilise le `ExamPromptBuilder` pour créer un prompt contextuel hyper-précis.
    """
    logger.info(f"🔬 [AI-LAB] Demande génération examen : '{exam_name}'")
    
    # 1. Préparation des données pour le Builder
    # Conversion du modèle SQLAlchemy en dict simpliste pour le builder
    case_data = {
        "pathologie_principale": {
            "nom_fr": case.pathologie_principale.nom_fr if case.pathologie_principale else "Inconnue"
        },
        "niveau_gravite": case.niveau_difficulte,
        "donnees_paracliniques": case.donnees_paracliniques,
        "description": case.pathologie_principale.description if case.pathologie_principale else "",
        "physiopathologie": case.pathologie_principale.physiopathologie if case.pathologie_principale else ""
    }
    
    # Extraction sommaire du persona depuis l'historique ou données par défaut
    # (Idéalement, on devrait passer le persona complet, mais ici on fait simple pour l'âge/sexe)
    patient_persona = {
        "age": "Adulte (selon dossier)", # Sera affiné si le texte du cas contient l'âge
        "genre": "Non spécifié"
    }
    
    exam_req = {
        "name": exam_name,
        "type": "tous", # Le builder déduira le type (bio/imag)
        "justification": exam_justification
    }

    # 2. Construction du Prompt via le Builder dédié
    prompt = exam_prompt_builder.build_prompt(
        case_data=case_data,
        exam_request=exam_req,
        patient_persona=patient_persona
    )

    # 3. Appel IA avec logique de retry sur le format JSON
    logic_attempts = 0
    final_result = None
    
    while logic_attempts < MAX_RETRIES_LOGIC:
        logic_attempts += 1
        
        try:
            result = _call_openrouter_api(
                input_data=prompt,
                json_mode=True,
                temperature=0.2, # Très strict pour des données médicales
                task_type=AiTaskType.EXAM_GENERATION,
                max_tokens=1000
            )
            
            # 4. Validation Métier
            if isinstance(result, dict) and _validate_exam_json_structure(result, f"EXAM-{logic_attempts}"):
                final_result = result
                break # Succès !
            else:
                logger.warning(f"   ⚠️ [AI-LAB] Tentative {logic_attempts}: JSON reçu mais invalide structurellement.")
                # On retente (l'aléatoire de la température peut aider à corriger)
        
        except Exception as e:
            logger.error(f"   ❌ [AI-LAB] Tentative {logic_attempts} échouée : {str(e)}")
            # On retente
            
    # 5. Gestion du Fallback (Si échec après retries)
    if not final_result:
        logger.critical(f"   💀 [AI-LAB] Échec définitif de génération de l'examen '{exam_name}'. Utilisation du fallback.")
        return {
            "type_resultat": "erreur",
            "rapport_complet": f"Erreur technique : Impossible de générer le rapport pour {exam_name}. Veuillez contacter le support.",
            "conclusion": "Examen non réalisé."
        }
    
    # 6. Post-traitement (optionnel)
    # On pourrait ajouter ici des vérifications de sécurité (mots interdits, etc.)
    
    logger.info(f"   🎉 [AI-LAB] Résultat généré avec succès. Conclusion : {final_result.get('conclusion', '')[:50]}...")
    return final_result


def evaluate_final_submission(
    db: Session,
    case: models.ClinicalCase,
    submission: schemas.simulation.SubmissionRequest,
    session_history: list
) -> Tuple[schemas.simulation.EvaluationResult, str, str]:
    """
    Le Juge Sémantique. Évalue la performance de l'étudiant en comparant
    ses réponses textuelles avec la vérité structurée de la base de données.
    """
    eval_id = f"JUDGE-{str(uuid.uuid4())[:6]}"
    logger.info(f"⚖️ [{eval_id}] Démarrage évaluation SÉMANTIQUE")

    # 1. Récupération de la VÉRITÉ TERRAIN (Ce qu'il fallait trouver)
    # -------------------------------------------------------------------------
    logger.debug(f"   [{eval_id}] Chargement de la vérité terrain depuis la BDD...")
    
    # Pathologie correcte
    correct_pathology_name = case.pathologie_principale.nom_fr
    
    # Traitements corrects (liste des médicaments liés à la pathologie)
    correct_treatments_objs = db.query(models.TraitementPathologie).options(
        joinedload(models.TraitementPathologie.medicament)
    ).filter(
        models.TraitementPathologie.pathologie_id == case.pathologie_principale_id
    ).all()
    
    # On construit une liste lisible pour l'IA : "Nom (Type - Ligne)"
    correct_treatments_list = []
    for t in correct_treatments_objs:
        med_name = t.medicament.nom_commercial or t.medicament.dci
        details = []
        if t.type_traitement: details.append(t.type_traitement)
        if t.ligne_traitement: details.append(f"{t.ligne_traitement}ère ligne")
        
        info_str = f"- {med_name}"
        if details:
            info_str += f" ({', '.join(details)})"
        correct_treatments_list.append(info_str)
    
    correct_treatments_str = "\n".join(correct_treatments_list) if correct_treatments_list else "Pas de traitement spécifique défini en base (se référer aux guidelines)."

    logger.debug(f"   [{eval_id}] Vérité Patho: {correct_pathology_name}")
    logger.debug(f"   [{eval_id}] Vérité Traitements: {len(correct_treatments_list)} items")

    # 2. Récupération de la SOUMISSION ÉTUDIANT (Texte libre)
    # -------------------------------------------------------------------------
    student_diagnosis_text = submission.diagnosed_pathology_text
    student_treatment_text = submission.prescribed_treatment_text
    
    logger.debug(f"   [{eval_id}] Input Étudiant Patho: '{student_diagnosis_text}'")
    logger.debug(f"   [{eval_id}] Input Étudiant Traitement: '{student_treatment_text[:50]}...'")

    # 3. Formatage de l'historique (Preuves de la démarche)
    # -------------------------------------------------------------------------
    # On tronque pour ne pas dépasser la fenêtre de contexte du LLM
    history_str = json.dumps(session_history, indent=2, ensure_ascii=False)
    if len(history_str) > 5000:
        history_str = history_str[:5000] + "\n... [HISTORIQUE TRONQUÉ] ..."

    # 4. Construction du PROMPT DU JURY (Comparaison Sémantique)
    # -------------------------------------------------------------------------
    prompt = f"""
TU ES UN PROFESSEUR DE MÉDECINE EXPERT (JURY D'EXAMEN).
Ta mission est d'évaluer la pertinence clinique de la réponse d'un étudiant.
Tu dois faire une COMPARAISON SÉMANTIQUE entre la vérité terrain et la réponse de l'étudiant.

--- 1. LE DIAGNOSTIC ---
VÉRITÉ (Attendu) : "{correct_pathology_name}"
RÉPONSE ÉTUDIANT : "{student_diagnosis_text}"

Instruction de notation Diagnostic :
- 10/10 : Diagnostic exact ou synonyme médical parfait (ex: "Infarctus" = "IDM").
- 7-9/10 : Diagnostic très proche ou incomplet (ex: "Paludisme" au lieu de "Paludisme grave").
- 4-6/10 : Bonne famille de maladie mais imprécis (ex: "Infection virale" pour "Grippe").
- 0-3/10 : Diagnostic faux ou dangereux.

--- 2. LE TRAITEMENT ---
VÉRITÉ (Recommandé) :
{correct_treatments_str}

RÉPONSE ÉTUDIANT :
"{student_treatment_text}"

Instruction de notation Thérapeutique :
- Analyse si l'étudiant a cité les molécules clés (DCI ou nom commercial).
- 5/5 : Traitement complet et adapté.
- 3-4/5 : Molécule principale présente mais incomplet.
- 0-2/5 : Traitement inefficace ou dangereux.

--- 3. LA DÉMARCHE CLINIQUE (HISTORIQUE) ---
Parcours de l'étudiant :
{history_str}

Instruction de notation Démarche :
- 5/5 : Questions pertinentes, examens justifiés, logique claire.
- 0-2/5 : Questions au hasard, examens inutiles ("pêche aux infos").

--- FORMAT DE SORTIE ATTENDU (JSON) ---
{{
  "score_diagnostic": float,  // Note sur 10
  "score_therapeutique": float, // Note sur 5
  "score_demarche": float,      // Note sur 5
  "feedback_global": "Analyse pédagogique détaillée. Explique pourquoi le diagnostic est bon/mauvais par rapport à la vérité. Commente le choix des médicaments.",
  "recommendation_next_step": "Conseil court (ex: 'Revoir la pharmacologie des antipaludéens')."
}}
"""

    # 5. Appel IA
    # -------------------------------------------------------------------------
    logger.info(f"   🚀 [{eval_id}] Envoi du dossier au jury (LLM)...")
    
    # On utilise _call_openrouter_api (assurez-vous qu'elle est bien définie dans le fichier complet)
    eval_json = _call_openrouter_api(
        input_data=prompt,
        json_mode=True,
        temperature=0.2, # Faible température pour une notation objective
        task_type=AiTaskType.EVALUATION
    )

    # 6. Parsing et Validation du Résultat
    # -------------------------------------------------------------------------
    try:
        # Sécurisation des types
        s_diag = float(eval_json.get("score_diagnostic", 0))
        s_ther = float(eval_json.get("score_therapeutique", 0))
        s_dem = float(eval_json.get("score_demarche", 0))
        
        # Clamp des notes (au cas où l'IA note sur 20 au lieu de 10)
        s_diag = min(10, max(0, s_diag))
        s_ther = min(5, max(0, s_ther))
        s_dem = min(5, max(0, s_dem))
        
        total = s_diag + s_ther + s_dem
        
        logger.info(f"   🏆 [{eval_id}] Verdict rendu : {total}/20")
        logger.debug(f"      Détails : Diag={s_diag}/10, Ther={s_ther}/5, Dem={s_dem}/5")
        logger.debug(f"      Feedback : {eval_json.get('feedback_global', '')[:100]}...")

        result_obj = schemas.simulation.EvaluationResult(
            score_diagnostic=s_diag,
            score_therapeutique=s_ther,
            score_demarche=s_dem,
            score_total=total
        )
        
        return result_obj, eval_json.get("feedback_global", "Évaluation complétée."), eval_json.get("recommendation_next_step", "Continuer.")

    except Exception as e:
        logger.error(f"   ❌ [{eval_id}] Erreur lecture verdict : {e}")
        logger.debug(f"      JSON reçu : {eval_json}")
        
        # Fallback pour ne pas bloquer l'UI
        return schemas.simulation.EvaluationResult(
            score_diagnostic=0, score_therapeutique=0, score_demarche=0, score_total=0
        ), "Erreur technique lors de l'évaluation automatique. Vos réponses ont été enregistrées.", "Veuillez contacter l'administrateur."

def generate_hint(case: models.ClinicalCase, session_history: List[str], hint_level: int) -> Tuple[str, str]:
    """
    Génère un indice.
    """
    logger.info(f"💡 [AI-TUTOR] Indice niveau {hint_level}")
    
    prompt = f"""
ROLE: Tuteur médical.
CONTEXTE: Cas de {case.pathologie_principale.nom_fr}.
NIVEAU AIDE: {hint_level}/3.
HISTORIQUE: {str(session_history)[-1000:]}

Donne un indice pédagogique JSON : {{ "hint_type": "...", "content": "..." }}
"""
    res = _call_openrouter_api(prompt, json_mode=True, task_type=AiTaskType.HINT_GENERATION)
    if isinstance(res, dict):
        return res.get("hint_type", "info"), res.get("content", "Analysez les symptômes.")
    return "info", "Continuez."