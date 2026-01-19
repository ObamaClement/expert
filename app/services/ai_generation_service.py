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
# Utilisation d'un modèle performant et gratuit si disponible, sinon fallback
MODEL_NAME = "mistralai/mistral-7b-instruct:free"

def _call_openrouter_api(prompt: str) -> Dict[str, Any]:
    """Fonction de base pour appeler l'API OpenRouter et parser la réponse JSON."""
    logger.info("[_call_openrouter_api] Envoi du prompt à l'IA...")
    
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
        response = requests.post(
            OPENROUTER_API_URL, 
            headers=headers, 
            data=json.dumps(data), 
            timeout=90
        )
        response.raise_for_status()
        response_json = response.json()
        content_str = response_json['choices'][0]['message']['content']
        
        logger.info("  -> ✅ Réponse IA reçue et parsée.")
        return json.loads(content_str)
    
    except requests.exceptions.RequestException as e:
        logger.error(f"  -> ❌ Erreur API OpenRouter: {e}")
        return {
            "error": "API call failed",
            "details": str(e),
            "score_diagnostic": 0,
            "score_therapeutique": 0,
            "score_demarche": 0,
            "feedback_global": "Erreur de connexion au service d'IA. Veuillez réessayer.",
            "recommendation_next_step": "Veuillez réessayer plus tard."
        }
    
    except (json.JSONDecodeError, KeyError, IndexError) as e:
        logger.error(f"  -> ❌ Erreur parsing JSON: {e}")
        return {
            "error": "Failed to parse AI response",
            "details": str(e),
            "score_diagnostic": 0,
            "score_therapeutique": 0,
            "score_demarche": 0,
            "feedback_global": "Erreur technique lors de l'interprétation de la réponse de l'IA.",
            "recommendation_next_step": "Veuillez réessayer plus tard."
        }


def generate_exam_result(
    case: models.ClinicalCase, 
    session_history: List[str], 
    exam_name: str
) -> Dict[str, Any]:
    """Génère un résultat d'examen plausible en utilisant l'IA."""
    logger.info(f"[generate_exam_result] Examen: '{exam_name}'")
    
    prompt = f"""
ROLE: Tu es un simulateur de laboratoire médical ultra-réaliste.

CONTEXTE:
- Pathologie réelle du patient: "{case.pathologie_principale.nom_fr}"
- Histoire de la maladie: "{case.presentation_clinique.get('histoire_maladie', 'Non spécifiée')}"
- Historique des actions de l'étudiant: {json.dumps(session_history, indent=2)}

TÂCHE:
L'étudiant demande l'examen: "{exam_name}"

INSTRUCTIONS:
1. Génère un résultat RÉALISTE et COHÉRENT avec la pathologie.
2. Ne révèle JAMAIS le diagnostic directement. Sois subtil.
3. Si l'examen n'est pas pertinent, le résultat doit être normal.
4. Réponds UNIQUEMENT avec un objet JSON (pas de texte avant/après).
5. Clés obligatoires: "rapport" (observations brutes) et "conclusion" (interprétation concise).

EXEMPLE:
{{"rapport": "Créatinine: 150 µmol/L (Norme: 60-110). Urée: 10 mmol/L (Norme: 2.5-7.5).", "conclusion": "Insuffisance rénale modérée."}}
"""
    
    ai_response = _call_openrouter_api(prompt)
    
    return {
        "rapport": ai_response.get("rapport", "Erreur de génération du rapport."),
        "conclusion": ai_response.get("conclusion", "Aucune conclusion générée.")
    }


def generate_hint(
    case: models.ClinicalCase, 
    session_history: List[str], 
    hint_level: int
) -> Tuple[str, str]:
    """Génère un indice contextuel en utilisant l'IA."""
    logger.info(f"[generate_hint] Niveau: {hint_level}")
    
    # Déterminer le type d'indice selon le niveau
    if hint_level == 0:
        hint_type_instruction = "une question socratique ouverte pour orienter la réflexion initiale."
    elif hint_level == 1:
        hint_type_instruction = "un rappel de cours ou de méthode clinique pertinent."
    elif hint_level == 2:
        hint_type_instruction = "un indice direct sur une action clé à entreprendre."
    else:
        hint_type_instruction = "un indice spécifique pointant vers un diagnostic possible."

    prompt = f"""
ROLE: Tu es un tuteur médical pédagogue et bienveillant.

CONTEXTE:
- Pathologie du cas: "{case.pathologie_principale.nom_fr}"
- Historique des actions de l'étudiant: {json.dumps(session_history, indent=2)}
- Demande d'aide n°{hint_level + 1}

TÂCHE:
Fournis {hint_type_instruction}

INSTRUCTIONS:
1. L'indice doit être court, utile et JAMAIS donner la solution.
2. Adapte l'indice à ce que l'étudiant a déjà fait.
3. Réponds UNIQUEMENT avec un objet JSON.
4. Clés: "hint_type" (parmi: "question_socratique", "rappel_de_cours", "indice_direct", "indice_specifique") et "content".
"""
    
    ai_response = _call_openrouter_api(prompt)
    
    return (
        ai_response.get("hint_type", "info"),
        ai_response.get("content", "Erreur lors de la génération de l'indice.")
    )


def evaluate_final_submission(
    db: Session,
    case: models.ClinicalCase,
    submission: schemas.simulation.SubmissionRequest,
    session_history: list
) -> Tuple[schemas.simulation.EvaluationResult, str, str]:
    """
    Évalue la soumission finale de l'apprenant en utilisant l'IA.
    Notation stricte sur 20 points.
    """
    logger.info("[evaluate_final_submission] Début de l'évaluation...")
    
    # Récupérer les informations sur le diagnostic correct
    correct_pathology_name = case.pathologie_principale.nom_fr
    
    # Récupérer le diagnostic soumis par l'apprenant
    db_pathology_submitted = db.query(models.Disease).filter(
        models.Disease.id == submission.diagnosed_pathology_id
    ).first()
    
    submitted_pathology_name = (
        db_pathology_submitted.nom_fr 
        if db_pathology_submitted 
        else f"ID Inconnu ({submission.diagnosed_pathology_id})"
    )
    
    # Récupérer les traitements recommandés pour la pathologie
    correct_treatments_raw = db.query(models.TraitementPathologie).options(
        joinedload(models.TraitementPathologie.medicament)
    ).filter(
        models.TraitementPathologie.pathologie_id == case.pathologie_principale_id
    ).all()
    
    correct_treatment_names = [
        t.medicament.nom_commercial or t.medicament.dci 
        for t in correct_treatments_raw
    ] if correct_treatments_raw else ["Aucun traitement spécifique défini"]

    # Récupérer les médicaments prescrits par l'apprenant
    submitted_meds_raw = db.query(models.Medication).filter(
        models.Medication.id.in_(submission.prescribed_medication_ids)
    ).all()
    
    submitted_med_names = [
        m.nom_commercial or m.dci 
        for m in submitted_meds_raw
    ]

    # ===================================================================
    # PROMPT CORRIGÉ POUR NOTATION SUR /20
    # ===================================================================
    prompt = f"""
ROLE: Tu es un professeur de médecine expert et juste, chargé d'évaluer la performance d'un étudiant sur une simulation de cas clinique.

CONTEXTE DU CAS:
- Diagnostic Correct: "{correct_pathology_name}"
- Traitements Recommandés: {json.dumps(correct_treatment_names, ensure_ascii=False)}

SOUMISSION DE L'ÉTUDIANT:
- Diagnostic Proposé: "{submitted_pathology_name}"
- Traitements Prescrits: {json.dumps(submitted_med_names, ensure_ascii=False)}
- Historique de sa démarche: {json.dumps(session_history, indent=2, ensure_ascii=False)}

TA MISSION:
Évalue la performance et réponds UNIQUEMENT avec un objet JSON.

BARÈME DE NOTATION (TOTAL /20):
1. "score_diagnostic": Note sur 10 points
   - 10 si diagnostic exact
   - 7-8 si diagnostic proche (même famille pathologique)
   - 3-5 si diagnostic partiellement pertinent
   - 0 si totalement erroné

2. "score_therapeutique": Note sur 5 points
   - Évalue la pertinence du traitement prescrit par rapport au DIAGNOSTIC CORRECT
   - 5 si traitement optimal
   - 3-4 si traitement acceptable
   - 1-2 si traitement sous-optimal
   - 0 si totalement inadapté ou dangereux

3. "score_demarche": Note sur 5 points
   - Évalue la logique et la pertinence des examens demandés
   - Une démarche rigoureuse peut avoir des points même si le diagnostic final est faux
   - 5 si démarche exemplaire (anamnèse + examens pertinents + logique)
   - 3-4 si démarche correcte
   - 1-2 si démarche lacunaire
   - 0 si démarche chaotique

4. "feedback_global": Paragraphe de 3-4 phrases (point positif + axe d'amélioration + encouragement)

5. "recommendation_next_step": Une phrase courte parmi:
   - "Passer à un cas de difficulté supérieure" (si score >= 12/20)
   - "Reprendre un cas de difficulté similaire" (si score < 12/20)
   - "Revoir les bases de cette catégorie" (si score < 8/20)

EXEMPLE DE RÉPONSE ATTENDUE:
{{
  "score_diagnostic": 8.0,
  "score_therapeutique": 4.0,
  "score_demarche": 3.5,
  "feedback_global": "Bon travail sur l'anamnèse. Le diagnostic est proche mais manque de précision. Les examens demandés étaient pertinents. Continue à affiner ta démarche diagnostique.",
  "recommendation_next_step": "Reprendre un cas de difficulté similaire"
}}
"""
    
    # Appel à l'IA
    ai_response = _call_openrouter_api(prompt)
    
    # ===================================================================
    # PARSING ROBUSTE ET CRÉATION DE L'OBJET PYDANTIC
    # ===================================================================
    try:
        score_diag = float(ai_response.get("score_diagnostic", 0.0))
        score_ther = float(ai_response.get("score_therapeutique", 0.0))
        score_dem = float(ai_response.get("score_demarche", 0.0))
        
        # Calcul du score total sur 20 par Python (plus fiable que l'IA)
        score_total = round(score_diag + score_ther + score_dem, 2)
        
        # Vérification de cohérence (bornage)
        if score_total > 20:
            logger.warning(f"⚠️  Score total > 20 détecté ({score_total}). Normalisation à 20.")
            score_total = 20.0
        
    except (ValueError, TypeError) as e:
        logger.error(f"❌ Erreur de type dans les scores: {e}. Scores mis à 0.")
        score_diag, score_ther, score_dem, score_total = 0.0, 0.0, 0.0, 0.0

    # Création de l'objet Pydantic `EvaluationResult`
    eval_result = schemas.simulation.EvaluationResult(
        score_diagnostic=score_diag,
        score_therapeutique=score_ther,
        score_demarche=score_dem,
        score_total=score_total
    )
    
    feedback = ai_response.get(
        "feedback_global", 
        "Erreur lors de la génération du feedback."
    )
    
    recommendation = ai_response.get(
        "recommendation_next_step", 
        "Veuillez réessayer."
    )

    logger.info(f"  -> ✅ Évaluation terminée: {score_total}/20 (Diag: {score_diag}, Théra: {score_ther}, Démarche: {score_dem})")
    
    return eval_result, feedback, recommendation