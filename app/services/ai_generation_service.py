import logging
import requests
import json
from typing import Dict, Any, List, Tuple
from sqlalchemy.orm import Session, joinedload

from .. import models, schemas
from ..config import settings

logger = logging.getLogger(__name__)

# Constantes pour l'API OpenRouter
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
# MISE A JOUR: Utilisation d'un modèle plus performant et toujours gratuit si disponible
MODEL_NAME = "mistralai/mistral-7b-instruct:free"

def _call_openrouter_api(prompt: str) -> Dict[str, Any]:
    """Fonction de base pour appeler l'API OpenRouter et parser la réponse JSON."""
    logger.info("Début de l'appel à l'API OpenRouter...")
    headers = {
        "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }
    data = {
        "model": MODEL_NAME,
        "messages": [{"role": "user", "content": prompt}],
        "response_format": {"type": "json_object"},
    }

    try:
        response = requests.post(OPENROUTER_API_URL, headers=headers, data=json.dumps(data), timeout=90)
        response.raise_for_status()
        response_json = response.json()
        content_str = response_json['choices'][0]['message']['content']
        logger.info("Réponse de l'IA reçue et parsée avec succès.")
        return json.loads(content_str)
    except requests.exceptions.RequestException as e:
        logger.error(f"Erreur lors de l'appel à l'API OpenRouter: {e}")
        # Retourner une structure d'erreur valide pour que le code appelant ne plante pas
        return {"error": "API call failed", "details": str(e), "score_diagnostic": 0, "score_therapeutique": 0, "score_demarche": 0, "feedback_global": "Erreur de connexion au service d'IA.", "recommendation_next_step": "Veuillez réessayer plus tard."}
    except (json.JSONDecodeError, KeyError, IndexError) as e:
        logger.error(f"Erreur lors du parsing de la réponse JSON de l'IA: {e}")
        return {"error": "Failed to parse AI response", "details": str(e), "score_diagnostic": 0, "score_therapeutique": 0, "score_demarche": 0, "feedback_global": "Erreur lors de l'interprétation de la réponse de l'IA.", "recommendation_next_step": "Veuillez réessayer plus tard."}

def generate_exam_result(case: models.ClinicalCase, session_history: List[str], exam_name: str) -> Dict[str, Any]:
    """Génère un résultat d'examen plausible en utilisant l'IA."""
    prompt = f"""
    ROLE: Tu es un simulateur de laboratoire médical ultra-réaliste.
    CONTEXTE: Un étudiant en médecine interagit avec un cas clinique simulé. La pathologie réelle du patient est "{case.pathologie_principale.nom_fr}". L'histoire de la maladie est: "{case.presentation_clinique.get('histoire_maladie', 'Non spécifiée')}".
    HISTORIQUE DES ACTIONS DE L'ÉTUDIANT: {json.dumps(session_history, indent=2)}
    TACHE: L'étudiant vient de demander l'examen suivant: "{exam_name}".
    INSTRUCTIONS:
    1. Génère un résultat réaliste pour cet examen.
    2. Le résultat doit être COHÉRENT avec la pathologie sous-jacente et l'historique.
    3. Ne révèle JAMAIS le diagnostic directement. Sois subtil. Si l'examen n'est pas pertinent, le résultat doit être normal.
    4. Réponds UNIQUEMENT avec un objet JSON. Ne fournis aucun texte avant ou après le JSON.
    5. Le JSON doit avoir deux clés: "rapport" (une chaîne décrivant les observations brutes) et "conclusion" (une chaîne avec l'interprétation médicale concise).
    EXEMPLE DE SORTIE: {{"rapport": "Créatinine: 150 µmol/L (Norme: 60-110). Urée: 10 mmol/L (Norme: 2.5-7.5).", "conclusion": "Insuffisance rénale modérée."}}
    """
    ai_response = _call_openrouter_api(prompt)
    return {"rapport": ai_response.get("rapport", "Erreur de génération du rapport."), "conclusion": ai_response.get("conclusion", "Aucune conclusion générée.")}

def generate_hint(case: models.ClinicalCase, session_history: List[str], hint_level: int) -> Tuple[str, str]:
    """Génère un indice contextuel en utilisant l'IA."""
    if hint_level == 0: hint_type_instruction = "une question socratique ouverte pour orienter sa réflexion initiale sur l'anamnèse."
    elif hint_level == 1: hint_type_instruction = "un rappel de cours ou de méthode clinique pertinent par rapport aux informations déjà collectées."
    elif hint_level == 2: hint_type_instruction = "un indice direct sur une action clé à entreprendre (examen physique ou paraclinique) qu'il n'a pas encore faite."
    else: hint_type_instruction = "un indice spécifique pointant vers un groupe de diagnostics possibles ou une anomalie clé à ne pas manquer."

    prompt = f"""
    ROLE: Tu es un tuteur médical pédagogue et bienveillant.
    CONTEXTE: Un étudiant gère un cas de "{case.pathologie_principale.nom_fr}".
    HISTORIQUE DES ACTIONS DE L'ÉTUDIANT: {json.dumps(session_history, indent=2)}
    TACHE: L'étudiant demande de l'aide. Il en est à sa {hint_level + 1}ème demande. Fournis {hint_type_instruction}
    INSTRUCTIONS:
    1. L'indice doit être court, utile et ne jamais donner la solution.
    2. Adapte l'indice à ce que l'étudiant a déjà fait ou n'a pas fait.
    3. Réponds UNIQUEMENT avec un objet JSON contenant les clés "hint_type" (choisis parmi: "question_socratique", "rappel_de_cours", "indice_direct", "indice_specifique") et "content".
    """
    ai_response = _call_openrouter_api(prompt)
    return ai_response.get("hint_type", "info"), ai_response.get("content", "Erreur lors de la génération de l'indice.")

def evaluate_final_submission(db: Session, case: models.ClinicalCase, submission: schemas.simulation.SubmissionRequest, session_history: list) -> Tuple[schemas.simulation.EvaluationResult, str, str]:
    """Évalue la soumission finale de l'apprenant en utilisant l'IA et retourne un objet Pydantic."""
    correct_pathology_name = case.pathologie_principale.nom_fr
    db_pathology_submitted = db.query(models.Disease).filter(models.Disease.id == submission.diagnosed_pathology_id).first()
    submitted_pathology_name = db_pathology_submitted.nom_fr if db_pathology_submitted else f"ID Inconnu ({submission.diagnosed_pathology_id})"
    
    correct_treatments_raw = db.query(models.TraitementPathologie).options(joinedload(models.TraitementPathologie.medicament)).filter(
        models.TraitementPathologie.pathologie_id == case.pathologie_principale_id
    ).all()
    correct_treatment_names = [t.medicament.nom_commercial or t.medicament.dci for t in correct_treatments_raw] if correct_treatments_raw else ["Aucun traitement spécifique défini"]

    submitted_meds_raw = db.query(models.Medication).filter(models.Medication.id.in_(submission.prescribed_medication_ids)).all()
    submitted_med_names = [m.nom_commercial or m.dci for m in submitted_meds_raw]

    ### MODIFICATION CLÉ : MISE À JOUR DU PROMPT POUR L'ÉCHELLE DE NOTATION /20 ###
    prompt = f"""
    ROLE: Tu es un professeur de médecine expert et juste, chargé d'évaluer la performance d'un étudiant sur une simulation de cas clinique.
    
    CONTEXTE DU CAS:
    - Diagnostic Correct: "{correct_pathology_name}"
    - Traitements Recommandés (liste informative): {json.dumps(correct_treatment_names)}
    
    SOUMISSION DE L'ÉTUDIANT:
    - Diagnostic Proposé: "{submitted_pathology_name}"
    - Traitements Prescrits: {json.dumps(submitted_med_names)}
    - Historique de sa démarche (actions effectuées): {json.dumps(session_history, indent=2)}

    TA MISSION:
    Évalue la performance et réponds UNIQUEMENT avec un objet JSON.
    Le JSON doit contenir EXACTEMENT les clés suivantes avec des notes flottantes:
    1. "score_diagnostic": note sur 10. (10 si exact, 5-7 si proche, 0 sinon).
    2. "score_therapeutique": note sur 5. (Évalue la pertinence du traitement prescrit PAR RAPPORT AU DIAGNOSTIC CORRECT).
    3. "score_demarche": note sur 5. (Évalue la logique et la pertinence des examens demandés. Une démarche logique peut avoir des points même si le diagnostic final est faux).
    4. "feedback_global": Un paragraphe concis de 3-4 phrases (point positif, axe d'amélioration, encouragement).
    5. "recommendation_next_step": Une phrase courte (choisis parmi: 'reprendre un cas de difficulté similaire', 'passer à un cas de difficulté supérieure', 'revoir les bases de cette catégorie').
    """
    
    ai_response = _call_openrouter_api(prompt)
    
    ### MODIFICATION CLÉ : LOGIQUE DE PARSING ROBUSTE ET CRÉATION DE L'OBJET PYDANTIC ###
    try:
        score_diag = float(ai_response.get("score_diagnostic", 0.0))
        score_ther = float(ai_response.get("score_therapeutique", 0.0))
        score_dem = float(ai_response.get("score_demarche", 0.0))
        
        # Calcul du score total sur 20
        score_total = round(score_diag + score_ther + score_dem, 2)
        
    except (ValueError, TypeError) as e:
        logger.error(f"Erreur de type dans les scores retournés par l'IA: {e}. Scores mis à 0.")
        score_diag, score_ther, score_dem, score_total = 0.0, 0.0, 0.0, 0.0

    # Création de l'objet Pydantic `EvaluationResult`
    eval_result = schemas.simulation.EvaluationResult(
        score_diagnostic=score_diag,
        score_therapeutique=score_ther,
        score_demarche=score_dem,
        score_total=score_total
    )
    
    feedback = ai_response.get("feedback_global", "Erreur lors de la génération du feedback.")
    recommendation = ai_response.get("recommendation_next_step", "Veuillez réessayer.")

    return eval_result, feedback, recommendation