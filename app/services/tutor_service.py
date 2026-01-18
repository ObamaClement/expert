from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc
from typing import List, Tuple, Dict, Any, Optional
from uuid import UUID
from datetime import datetime
import random

from .. import models, schemas
from . import simulation_service, disease_service, interaction_log_service, ai_generation_service

def _get_learner_history(db: Session, learner_id: int, category: str) -> List[models.SimulationSession]:
    """Récupère l'historique des sessions d'un apprenant pour une catégorie, les plus récentes d'abord."""
    return db.query(models.SimulationSession).join(
        models.ClinicalCase, models.SimulationSession.cas_clinique_id == models.ClinicalCase.id
    ).join(
        models.Disease, models.ClinicalCase.pathologie_principale_id == models.Disease.id
    ).filter(
        models.SimulationSession.learner_id == learner_id,
        models.Disease.categorie == category
    ).order_by(desc(models.SimulationSession.start_time)).all()

def _select_case_for_activity(db: Session, category: str, session_type: str, last_score: Optional[float], completed_ids: List[int], formative_cases_ids: List[int] = []) -> models.ClinicalCase:
    """Sélectionne le cas clinique approprié en fonction de la logique pédagogique."""
    
    # Pour une évaluation sommative, on choisit au hasard parmi les 3 derniers cas formatifs
    if session_type == "sommative":
        if not formative_cases_ids:
            raise ValueError("Erreur logique: demande d'évaluation sommative sans cas formatifs préalables.")
        
        case_to_evaluate_id = random.choice(formative_cases_ids)
        next_case = db.query(models.ClinicalCase).filter(models.ClinicalCase.id == case_to_evaluate_id).first()
        if not next_case:
             raise ValueError(f"Le cas clinique avec l'ID {case_to_evaluate_id} pour l'évaluation sommative est introuvable.")
        return next_case

    # Pour les sessions de test ou formatives
    query = db.query(models.ClinicalCase).join(
        models.Disease, models.ClinicalCase.pathologie_principale_id == models.Disease.id
    ).filter(
        models.Disease.categorie == category,
        models.ClinicalCase.id.notin_(completed_ids)
    )

    if session_type == "test":
        # Difficulté intermédiaire pour la première évaluation
        query = query.filter(models.ClinicalCase.niveau_difficulte.between(10, 20))
    else: # Formative
        if last_score is not None:
            if last_score < 12: # Mauvaise note, on reste au même niveau ou plus facile
                current_level_case = db.query(models.ClinicalCase).filter(models.ClinicalCase.id == completed_ids[0]).first() if completed_ids else None
                difficulty_target = current_level_case.niveau_difficulte if current_level_case else 10
                query = query.filter(models.ClinicalCase.niveau_difficulte <= difficulty_target)
            else: # Bonne note, on progresse de n+3
                current_level_case = db.query(models.ClinicalCase).filter(models.ClinicalCase.id == completed_ids[0]).first() if completed_ids else None
                difficulty_target = (current_level_case.niveau_difficulte if current_level_case else 0) + 3
                query = query.filter(models.ClinicalCase.niveau_difficulte >= difficulty_target)

    # Toujours prendre le cas le plus facile correspondant aux critères
    next_case = query.order_by(models.ClinicalCase.niveau_difficulte.asc()).first()
    
    # Fallback si aucun cas n'est trouvé dans la tranche de difficulté exacte
    if not next_case:
        fallback_query = db.query(models.ClinicalCase).join(
            models.Disease, models.ClinicalCase.pathologie_principale_id == models.Disease.id
        ).filter(
            models.Disease.categorie == category,
            models.ClinicalCase.id.notin_(completed_ids)
        )
        if last_score is not None and last_score >= 12: # Si on progressait, on cherche plus haut
            next_case = fallback_query.order_by(models.ClinicalCase.niveau_difficulte.asc()).first()
        else: # Sinon on cherche plus bas
            next_case = fallback_query.order_by(models.ClinicalCase.niveau_difficulte.desc()).first()

    if not next_case:
        raise ValueError(f"Plus aucun cas clinique non résolu disponible dans la catégorie '{category}'.")
        
    return next_case

def start_new_session(db: Session, learner_id: int, category: str) -> Tuple[models.SimulationSession, models.ClinicalCase, str]:
    learner = db.query(models.Learner).filter(models.Learner.id == learner_id).first()
    if not learner: raise ValueError(f"L'apprenant avec l'ID {learner_id} n'a pas été trouvé.")

    history = _get_learner_history(db, learner_id, category)
    
    # Vérifier s'il y a une session en cours
    last_session = history[0] if history else None
    if last_session and last_session.statut == "in_progress":
        db.refresh(last_session, attribute_names=["cas_clinique"])
        if last_session.cas_clinique: db.refresh(last_session.cas_clinique, attribute_names=["pathologie_principale"])
        session_type = last_session.context_state.get("session_type", "formative")
        return last_session, last_session.cas_clinique, session_type

    # Déterminer la logique de la nouvelle session
    completed_history = [s for s in history if s.statut == "completed"]
    completed_ids = [s.cas_clinique_id for s in completed_history]
    
    if not completed_history:
        session_type = "test"
        last_score = None
        formative_cases_ids = []
    else:
        last_eval = next((s for s in completed_history if s.context_state.get("session_type") in ["test", "sommative"]), None)
        formative_since_last_eval = [s for s in completed_history if s.end_time > (last_eval.end_time if last_eval else datetime.min)]
        
        if len(formative_since_last_eval) >= 3:
            session_type = "sommative"
            last_score = last_eval.score_final if last_eval else None
            formative_cases_ids = [s.cas_clinique_id for s in formative_since_last_eval[:3]]
        else:
            session_type = "formative"
            last_score = last_eval.score_final if last_eval else None
            if last_score is not None and last_score < 12: # Si on a échoué la dernière sommative, on reset le compteur
                formative_since_last_eval = []
            formative_cases_ids = []
            
    next_clinical_case = _select_case_for_activity(db, category, session_type, last_score, completed_ids, formative_cases_ids)
    
    # Stocker le compteur formatif dans le contexte
    formative_count = len(formative_since_last_eval) + 1 if session_type == 'formative' else 0
    
    new_session = simulation_service.create_session(
        db=db, learner_id=learner_id, case_id=next_clinical_case.id, session_type=session_type, formative_count=formative_count
    )
    
    db.refresh(new_session, attribute_names=["cas_clinique"])
    if new_session.cas_clinique: db.refresh(new_session.cas_clinique, attribute_names=["pathologie_principale"])

    return new_session, new_session.cas_clinique, session_type


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
            
            # Mise à jour BKT (Bayesian Knowledge Tracing) simplifiée
            is_success = eval_result.score_total >= 12
            mastery.mastery_level = (mastery.mastery_level or 0.5) * (eval_result.score_total / 20)
            mastery.nb_success = (mastery.nb_success or 0) + (1 if is_success else 0)
            mastery.nb_failures = (mastery.nb_failures or 0) + (0 if is_success else 1)

    db.commit()
    return eval_result, feedback, recommendation

# Les autres fonctions (process_learner_action, provide_hint, etc.) restent les mêmes qu'avant.
# ... (coller ici le reste des fonctions: process_learner_action, _get_or_create_scaffolding_state, provide_hint)

def process_learner_action(db: Session, session_id: UUID, action_data: schemas.simulation.LearnerActionRequest) -> Tuple[Dict[str, Any], str]:
    interaction_log_service.create_interaction_log(db=db, session_id=session_id, action_data=action_data)
    
    session = db.query(models.SimulationSession).options(joinedload(models.SimulationSession.cas_clinique).joinedload(models.ClinicalCase.pathologie_principale)).filter(models.SimulationSession.id == session_id).first()
    if not session: raise ValueError(f"Session {session_id} non trouvée.")

    history_logs = db.query(models.InteractionLog).filter(models.InteractionLog.session_id == session_id).order_by(models.InteractionLog.timestamp.asc()).all()
    session_history = [f"Action: {l.action_content.get('name')}, Justification: {l.action_content.get('justification')}" for l in history_logs]

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