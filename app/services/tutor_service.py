import logging
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc
from typing import List, Tuple, Dict, Any, Optional
from uuid import UUID
from datetime import datetime
import random
import traceback

from .. import models, schemas
from . import simulation_service, interaction_log_service, ai_generation_service, clinical_case_service

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

def _get_learner_history(db: Session, learner_id: int, category: str) -> List[models.SimulationSession]:
    return db.query(models.SimulationSession).join(
        models.ClinicalCase, models.SimulationSession.cas_clinique_id == models.ClinicalCase.id
    ).join(
        models.Disease, models.ClinicalCase.pathologie_principale_id == models.Disease.id
    ).filter(
        models.SimulationSession.learner_id == learner_id,
        models.Disease.categorie == category
    ).order_by(models.SimulationSession.start_time.asc()).all()


def _calculate_current_state(history: List[models.SimulationSession]) -> Tuple[int, str, List[int]]:
    current_level = 1
    formative_buffer = [] 
    
    # On prend completed ET abandoned (modifié pour le test si besoin, mais restons sur completed)
    completed_sessions = [s for s in history if s.statut == "completed"]

    for session in completed_sessions:
        s_type = session.context_state.get("session_type", "formative")
        score = session.score_final if session.score_final is not None else 0
        
        case_id = session.cas_clinique_id
        if case_id is None: continue 

        if s_type == "test":
            current_level = max(1, int(score))
            formative_buffer = []

        elif s_type == "sommative" or s_type == "summative":
            if score >= 12.0:
                current_level += 3
            else:
                current_level = max(1, current_level - 1)
            formative_buffer = []

        else:
            formative_buffer.append(case_id)
            if len(formative_buffer) > 3:
                formative_buffer = formative_buffer[-3:]

    current_level = min(30, current_level)
    
    if len(formative_buffer) >= 3:
        next_session_type = "sommative"
    else:
        next_session_type = "formative"

    return current_level, next_session_type, formative_buffer


def start_new_session(db: Session, learner_id: int, category: str) -> Tuple[models.SimulationSession, models.ClinicalCase, str]:
    logger.info(f"🚀 [START] Demande session - Learner: {learner_id}, Cat: {category}")

    history = _get_learner_history(db, learner_id, category)

    # --- NETTOYAGE DES SESSIONS EN COURS (MODE TEST) ---
    if history:
        last_session = history[-1]
        if last_session.statut == "in_progress":
            logger.warning(f"⚠️ [CLEANUP-TEST] Session {last_session.id} non terminée.")
            logger.warning("   -> Forçage 'completed' avec score 15/20 pour simuler une progression.")
            
            last_session.statut = "completed"
            last_session.score_final = 15.0 # Simule une réussite
            last_session.end_time = datetime.now()
            db.commit()
            
            # On recharge l'historique pour prendre en compte ce changement
            history = _get_learner_history(db, learner_id, category)

    # Calcul de l'état
    has_completed = any(s.statut == "completed" for s in history)
    if not has_completed and not history:
        logger.info("🆕 [NEW-USER] Aucun historique. Force TYPE = TEST.")
        next_type = "test"
        current_level = 10
        formative_buffer = []
    else:
        current_level, next_type, formative_buffer = _calculate_current_state(history)

    logger.info(f"📊 État calculé : Niveau {current_level} | Prochain type : {next_type}")

    # Sélection Cas
    selected_case = None
    all_seen_ids = [s.cas_clinique_id for s in history if s.cas_clinique_id is not None]

    if next_type == "sommative":
        if not formative_buffer:
            logger.warning("⚠️ [LOGIC] Sommative demandée mais buffer vide. Fallback Formative.")
            next_type = "formative"
        else:
            case_id = random.choice(formative_buffer)
            selected_case = clinical_case_service.get_case_by_id(db, case_id)
            logger.info(f"🎲 [PICK] Cas sommatif sélectionné : {case_id}")

    if next_type in ["formative", "test"]:
        selected_case = clinical_case_service.get_case_for_progression(
            db, category, current_level, all_seen_ids
        )

    if not selected_case:
        logger.warning("⚠️ [FALLBACK] Aucun cas neuf trouvé. Recyclage.")
        # Utilisation de la nouvelle fonction optimisée (get_cases_by_category)
        cat_cases = clinical_case_service.get_cases_by_category(db, category)
        
        if cat_cases:
            selected_case = random.choice(cat_cases)
            logger.info(f"♻️ [RECYCLE] Cas recyclé : {selected_case.id}")
        else:
             logger.error(f"❌ [CRITICAL] Aucun cas trouvé pour {category}")
             raise ValueError(f"Aucun cas clinique disponible pour la catégorie '{category}'.")

    # Création session
    logger.info(f"💾 [PRE-CREATE] Tentative création session avec Cas {selected_case.id}")
    
    try:
        new_session = simulation_service.create_session(
            db=db,
            learner_id=learner_id,
            case_id=selected_case.id,
            session_type=next_type,
            formative_count=len(formative_buffer),
            formative_cases_pool=formative_buffer
        )
        
        db.refresh(new_session, ["cas_clinique"])
        if new_session.cas_clinique:
            db.refresh(new_session.cas_clinique, ["pathologie_principale"])

        return new_session, new_session.cas_clinique, next_type
        
    except Exception as e:
        logger.error(f"❌ [CRITICAL] Erreur lors de la création : {str(e)}")
        logger.error(traceback.format_exc())
        raise e


# (Autres fonctions inchangées...)
def process_learner_action(db, session_id, action_data):
    interaction_log_service.create_interaction_log(db, session_id, action_data)
    session = db.query(models.SimulationSession).filter_by(id=session_id).first()
    if not session: raise ValueError("Session introuvable")
    return ai_generation_service.generate_exam_result(session.cas_clinique, [], action_data.action_name), None

def provide_hint(db, session_id):
    return "hint", "Ceci est un indice mocké."

def evaluate_submission(db, session_id, submission_data):
    session = db.query(models.SimulationSession).filter_by(id=session_id).first()
    if not session: raise ValueError("Session introuvable")
    
    # Simulation pour éviter les appels IA qui coûtent cher/prennent du temps pendant le debug
    # (Remettez le vrai appel IA une fois le cycle validé)
    
    logs = db.query(models.InteractionLog).filter_by(session_id=session_id).all()
    history_json = [{"type": "action", "name": "test"}]
    
    eval_result, feedback, recommendation = ai_generation_service.evaluate_final_submission(
        db, session.cas_clinique, submission_data, history_json
    )

    session.score_final = eval_result.score_total
    session.statut = "completed"
    session.end_time = datetime.now()
    db.commit()
    
    return eval_result, feedback, recommendation