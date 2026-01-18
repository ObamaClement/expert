import logging
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc
from typing import List, Tuple, Dict, Any, Optional
from uuid import UUID
from datetime import datetime
import random

from .. import models, schemas
from . import simulation_service, disease_service, interaction_log_service, ai_generation_service

# Obtenir une instance du logger
logger = logging.getLogger(__name__)

def _get_learner_history(db: Session, learner_id: int, category: str) -> List[models.SimulationSession]:
    logger.info(f"[_get_learner_history] Recherche de l'historique pour learner_id={learner_id}, category='{category}'")
    history = db.query(models.SimulationSession).join(
        models.ClinicalCase, models.SimulationSession.cas_clinique_id == models.ClinicalCase.id
    ).join(
        models.Disease, models.ClinicalCase.pathologie_principale_id == models.Disease.id
    ).filter(
        models.SimulationSession.learner_id == learner_id,
        models.Disease.categorie == category
    ).order_by(desc(models.SimulationSession.start_time)).all()
    logger.info(f"  -> {len(history)} session(s) trouvée(s) au total.")
    for i, s in enumerate(history):
        logger.debug(f"    - Historique {i+1}: ID={s.id}, Statut='{s.statut}', Type='{s.context_state.get('session_type')}', Score={s.score_final}")
    return history

def _select_case_for_activity(db: Session, category: str, session_type: str, last_score: Optional[float], seen_case_ids: List[int], learner_id: int, formative_cases_ids: List[int] = []) -> models.ClinicalCase:
    logger.info(f"[_select_case_for_activity] Début de la sélection de cas.")
    logger.info(f"  -> Critères: type='{session_type}', last_score={last_score}, catégorie='{category}'")
    logger.info(f"  -> IDs des cas déjà vus à exclure: {seen_case_ids}")

    if session_type == "sommative":
        if not formative_cases_ids:
            logger.error("Tentative de session sommative sans cas formatifs !")
            raise ValueError("Erreur logique: demande d'évaluation sommative sans cas formatifs préalables.")
        case_to_evaluate_id = random.choice(formative_cases_ids)
        logger.info(f"  -> Mode SOMMATIF: Sélection aléatoire du cas #{case_to_evaluate_id} parmi {formative_cases_ids}")
        next_case = db.query(models.ClinicalCase).filter(models.ClinicalCase.id == case_to_evaluate_id).first()
        if not next_case:
             raise ValueError(f"Cas {case_to_evaluate_id} pour l'évaluation sommative introuvable.")
        logger.info(f"    -> ✅ Cas sommatif trouvé: #{next_case.id} ({next_case.code_fultang})")
        return next_case

    query = db.query(models.ClinicalCase).join(
        models.Disease, models.ClinicalCase.pathologie_principale_id == models.Disease.id
    ).filter(
        models.Disease.categorie == category,
        models.ClinicalCase.id.notin_(seen_case_ids)
    )
    
    difficulty_target = 0
    if session_type == "test":
        query = query.filter(models.ClinicalCase.niveau_difficulte.between(10, 20))
        logger.info("  -> Mode TEST: Filtrage sur difficulté [10, 20].")
    elif last_score is not None:
        last_completed_session = db.query(models.SimulationSession).filter(
            models.SimulationSession.learner_id == learner_id, models.SimulationSession.statut == 'completed'
        ).order_by(desc(models.SimulationSession.end_time)).first()
        
        current_difficulty = 10
        if last_completed_session:
             case = db.query(models.ClinicalCase).filter_by(id=last_completed_session.cas_clinique_id).first()
             if case: current_difficulty = case.niveau_difficulte
        logger.info(f"  -> Niveau de difficulté actuel basé sur le dernier cas réussi: {current_difficulty}")

        if last_score < 12:
            difficulty_target = current_difficulty
            logger.info(f"  -> Mode FORMATIF (ÉCHEC): recherche autour du niveau {difficulty_target}.")
            query = query.filter(models.ClinicalCase.niveau_difficulte.between(difficulty_target - 2, difficulty_target + 2))
        else:
            difficulty_target = current_difficulty + 3
            logger.info(f"  -> Mode FORMATIF (SUCCÈS): recherche d'un niveau >= {difficulty_target}.")
            query = query.filter(models.ClinicalCase.niveau_difficulte >= difficulty_target)

    next_case = query.order_by(models.ClinicalCase.niveau_difficulte.asc()).first()
    
    if not next_case:
        logger.warning("  -> Aucun cas trouvé avec les filtres stricts. Passage au mode Fallback.")
        fallback_query = db.query(models.ClinicalCase).join(
            models.Disease, models.ClinicalCase.pathologie_principale_id == models.Disease.id
        ).filter(models.Disease.categorie == category, models.ClinicalCase.id.notin_(seen_case_ids))
        
        all_available_cases = fallback_query.all()
        if not all_available_cases:
            logger.error(f"  -> FALLBACK ÉCHOUÉ: Plus aucun cas non vu dans la catégorie '{category}'.")
            raise ValueError(f"Plus aucun cas clinique non résolu disponible dans la catégorie '{category}'.")

        if difficulty_target > 0:
            next_case = min(all_available_cases, key=lambda x: abs(x.niveau_difficulte - difficulty_target))
            logger.info(f"    -> Fallback: Cas le plus proche du niveau cible {difficulty_target} trouvé: #{next_case.id} (Niveau {next_case.niveau_difficulte})")
        else:
            next_case = fallback_query.order_by(models.ClinicalCase.niveau_difficulte.asc()).first()
            logger.info(f"    -> Fallback: Cas le plus facile disponible trouvé: #{next_case.id} (Niveau {next_case.niveau_difficulte})")

    logger.info(f"    -> ✅ Cas final sélectionné: #{next_case.id} ({next_case.code_fultang}, Niveau {next_case.niveau_difficulte})")
    return next_case

def start_new_session(db: Session, learner_id: int, category: str) -> Tuple[models.SimulationSession, models.ClinicalCase, str]:
    logger.info(f"\n\n================ [START] start_new_session pour learner #{learner_id}, category '{category}' ================")
    
    history = _get_learner_history(db, learner_id, category)
    
    last_session = history[0] if history else None
    if last_session and last_session.statut == "in_progress":
        logger.info("  -> Une session est déjà 'in_progress'. Reprise de cette session.")
        db.refresh(last_session, attribute_names=["cas_clinique"])
        if last_session.cas_clinique: db.refresh(last_session.cas_clinique, attribute_names=["pathologie_principale"])
        session_type = last_session.context_state.get("session_type", "formative")
        logger.info(f"    -> ✅ Reprise de la session #{last_session.id} (Type: {session_type})")
        return last_session, last_session.cas_clinique, session_type

    completed_history = [s for s in history if s.statut == "completed"]
    seen_case_ids = [s.cas_clinique_id for s in history]
    
    session_type, last_score, formative_cases_ids = "test", None, []

    if not completed_history:
        logger.info("  -> Logique: Aucun historique complété. Démarrage d'une session de 'test'.")
    else:
        last_eval = next((s for s in completed_history if s.context_state.get("session_type") in ["test", "sommative"]), None)
        if not last_eval:
            logger.info("  -> Logique: Historique trouvé mais sans évaluation (test/sommative). Démarrage d'une session 'formative'.")
            session_type = "formative"
            last_score = None # Pas de score de référence
        else:
            logger.info(f"  -> Logique: Dernière évaluation trouvée: Session #{last_eval.id}, Score: {last_eval.score_final}")
            formative_since_last_eval = [s for s in completed_history if s.end_time > last_eval.end_time and s.context_state.get("session_type") == "formative"]
            logger.info(f"  -> Logique: {len(formative_since_last_eval)} session(s) formative(s) trouvée(s) depuis cette évaluation.")

            if last_eval.score_final < 12:
                 logger.info("  -> Logique: Le score de la dernière éval était < 12. On recommence un cycle formatif.")
                 session_type = "formative"
                 last_score = last_eval.score_final
            elif len(formative_since_last_eval) >= 3:
                logger.info("  -> Logique: 3 sessions formatives ou plus complétées. Démarrage d'une session 'sommative'.")
                session_type = "sommative"
                last_score = last_eval.score_final
                formative_cases_ids = [s.cas_clinique_id for s in formative_since_last_eval[:3]]
            else:
                logger.info("  -> Logique: Moins de 3 sessions formatives. Démarrage d'une nouvelle session 'formative'.")
                session_type = "formative"
                last_score = last_eval.score_final
                
    next_clinical_case = _select_case_for_activity(db, category, session_type, last_score, seen_case_ids, learner_id, formative_cases_ids)
    
    formative_count = 0
    if session_type == 'formative':
        if 'last_eval' in locals() and last_eval and last_eval.score_final >= 12:
            formative_count = len(formative_since_last_eval) + 1
        else:
            formative_count = 1 # On commence ou recommence le cycle
    
    new_session = simulation_service.create_session(
        db=db, learner_id=learner_id, case_id=next_clinical_case.id, session_type=session_type, formative_count=formative_count
    )
    
    db.refresh(new_session, attribute_names=["cas_clinique"])
    if new_session.cas_clinique: db.refresh(new_session.cas_clinique, attribute_names=["pathologie_principale"])

    logger.info(f"================ [END] start_new_session ================\n")
    return new_session, new_session.cas_clinique, session_type

# ... (Le reste du code reste identique, vous pouvez le copier depuis votre version existante)
def process_learner_action(db: Session, session_id: UUID, action_data: schemas.simulation.LearnerActionRequest) -> Tuple[Dict[str, Any], str]:
    interaction_log_service.create_interaction_log(db=db, session_id=session_id, action_data=action_data)
    
    session = db.query(models.SimulationSession).options(joinedload(models.SimulationSession.cas_clinique).joinedload(models.ClinicalCase.pathologie_principale)).filter(models.SimulationSession.id == session_id).first()
    if not session: raise ValueError(f"Session {session_id} non trouvée.")

    history_logs = db.query(models.InteractionLog).filter(models.InteractionLog.session_id == session_id).order_by(models.InteractionLog.timestamp.asc()).all()
    session_history = [f"Action: {l.action_content.get('name')}, Justification: {l.action_content.get('justification') or 'N/A'}" for l in history_logs]

    action_result = ai_generation_service.generate_exam_result(
        case=session.cas_clinique, session_history=session_history, exam_name=action_data.action_name
    )

    return action_result, None

def _get_or_create_scaffolding_state(db: Session, session_id: UUID) -> models.TutorScaffoldingState:
    state = db.query(models.TutorScaffoldingState).filter(models.TutorScaffoldingState.session_id == session_id).first()
    if not state:
        state = models.TutorScaffoldingState(session_id=session_id, current_level=0, indices_deja_donnes=[])
        db.add(state); db.commit(); db.refresh(state)
    return state

def provide_hint(db: Session, session_id: UUID) -> Tuple[str, str]:
    state = _get_or_create_scaffolding_state(db, session_id)
    session = db.query(models.SimulationSession).options(joinedload(models.SimulationSession.cas_clinique).joinedload(models.ClinicalCase.pathologie_principale)).filter(models.SimulationSession.id == session_id).first()
    if not session: raise ValueError(f"Session {session_id} non trouvée.")

    history_logs = db.query(models.InteractionLog).filter(models.InteractionLog.session_id == session_id).all()
    session_history = [f"Action: {l.action_content.get('name')}" for l in history_logs]

    hint_type, hint_content = ai_generation_service.generate_hint(
        case=session.cas_clinique, session_history=session_history, hint_level=state.current_level
    )

    decision = models.TutorDecision(session_id=session_id, strategy_used="Scaffolding", action_choisie="Fournir un Indice", intervention_content=hint_content, rationale={"reason": "Demande de l'apprenant", "level": state.current_level})
    db.add(decision)
    state.current_level += 1
    db.commit()

    return hint_type, hint_content

def evaluate_submission(db: Session, session_id: UUID, submission_data: schemas.simulation.SubmissionRequest) -> Tuple[schemas.simulation.EvaluationResult, str, str]:
    session = db.query(models.SimulationSession).options(
        joinedload(models.SimulationSession.cas_clinique).joinedload(models.ClinicalCase.pathologie_principale)
    ).filter(models.SimulationSession.id == session_id).first()
    if not session: raise ValueError(f"Session {session_id} non trouvée.")
    if session.statut == "completed": raise ValueError("Cette session a déjà été évaluée.")

    case = session.cas_clinique
    
    logs = db.query(models.InteractionLog).filter(models.InteractionLog.session_id == session_id).all()
    history_for_eval = [{"type": log.action_type, "name": log.action_content.get('name'), "justification": log.action_content.get('justification')} for log in logs]
    
    eval_result, feedback, recommendation = ai_generation_service.evaluate_final_submission(
        db=db, case=case, submission=submission_data, session_history=history_for_eval
    )
    
    session.statut = "completed"
    session.score_final = eval_result.score_total
    session.end_time = datetime.now()
    
    session_type = session.context_state.get("session_type")
    if session_type in ["sommative", "test"] and case.competences_requises:
        competency_id_to_update = case.competences_requises.get("SYNTHESE_CLINIQUE")
        if competency_id_to_update:
            mastery = db.query(models.LearnerCompetencyMastery).filter(
                models.LearnerCompetencyMastery.learner_id == session.learner_id,
                models.LearnerCompetencyMastery.competence_id == competency_id_to_update
            ).first()
            if not mastery:
                mastery = models.LearnerCompetencyMastery(learner_id=session.learner_id, competence_id=competency_id_to_update)
                db.add(mastery)
            
            is_success = eval_result.score_total >= 12
            mastery.mastery_level = (mastery.mastery_level or 0.5) * (eval_result.score_total / 20)
            mastery.nb_success = (mastery.nb_success or 0) + (1 if is_success else 0)
            mastery.nb_failures = (mastery.nb_failures or 0) + (0 if is_success else 1)

    db.commit()
    return eval_result, feedback, recommendation