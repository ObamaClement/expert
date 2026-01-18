from datetime import datetime
from sqlalchemy.orm import Session, joinedload
from typing import List, Tuple, Dict, Any, Optional
from uuid import UUID
import time

from .. import models, schemas
from . import simulation_service, disease_service, interaction_log_service, ai_generation_service

def _get_learner_history(db: Session, learner_id: int, category: str) -> List[models.SimulationSession]:
    """Récupère l'historique des sessions complétées par l'apprenant pour une catégorie donnée."""
    return db.query(models.SimulationSession).join(
        models.ClinicalCase, models.SimulationSession.cas_clinique_id == models.ClinicalCase.id
    ).join(
        models.Disease, models.ClinicalCase.pathologie_principale_id == models.Disease.id
    ).filter(
        models.SimulationSession.learner_id == learner_id,
        models.SimulationSession.statut == "completed",
        models.Disease.categorie == category
    ).order_by(models.SimulationSession.end_time.desc()).all()

def _determine_session_type_and_difficulty(history: List[models.SimulationSession]) -> Tuple[str, Optional[float], List[int]]:
    """Détermine le type de la prochaine session et le niveau de difficulté initial."""
    if not history:
        # Première fois dans cette catégorie -> Évaluation de test
        return "test", None, []

    last_test_or_sommative = next((s for s in history if s.context_state.get("session_type") in ["test", "sommative"]), None)
    
    if not last_test_or_sommative:
        # Devrait être rare, mais si seulement des formatives existent, on continue
        formative_sessions = [s for s in history if s.context_state.get("session_type") == "formative"]
        if len(formative_sessions) >= 3:
            return "sommative", None, []
        return "formative", None, []

    formative_since_last_eval = [s for s in history if s.end_time > last_test_or_sommative.end_time]
    
    if len(formative_since_last_eval) >= 3:
        return "sommative", last_test_or_sommative.score_final, []
    else:
        return "formative", last_test_or_sommative.score_final, [s.cas_clinique_id for s in history]

def _select_next_case(db: Session, category: str, session_type: str, last_score: Optional[float], completed_ids: List[int]) -> models.ClinicalCase:
    """Sélectionne le cas clinique approprié."""
    query = db.query(models.ClinicalCase).join(
        models.Disease, models.ClinicalCase.pathologie_principale_id == models.Disease.id
    ).filter(
        models.Disease.categorie == category,
        models.ClinicalCase.id.notin_(completed_ids)
    )

    if session_type == "test":
        query = query.filter(models.ClinicalCase.niveau_difficulte.between(10, 20))
    else: # formative or sommative
        if last_score is not None:
            if last_score <= 10: # Mauvaise note
                query = query.filter(models.ClinicalCase.niveau_difficulte < 10)
            elif last_score <= 15: # Note moyenne
                query = query.filter(models.ClinicalCase.niveau_difficulte.between(10, 20))
            else: # Bonne note
                query = query.filter(models.ClinicalCase.niveau_difficulte > 20)
    
    # Toujours prendre le plus facile des cas disponibles dans la tranche de difficulté
    next_case = query.order_by(models.ClinicalCase.niveau_difficulte.asc()).first()
    
    if not next_case:
        # Fallback: si aucun cas n'est trouvé dans la tranche, on prend le plus facile disponible
        next_case = db.query(models.ClinicalCase).join(
            models.Disease, models.ClinicalCase.pathologie_principale_id == models.Disease.id
        ).filter(
            models.Disease.categorie == category,
            models.ClinicalCase.id.notin_(completed_ids)
        ).order_by(models.ClinicalCase.niveau_difficulte.asc()).first()

    if not next_case:
        raise ValueError(f"Plus aucun cas disponible dans la catégorie '{category}'.")
        
    return next_case

def start_new_session(db: Session, learner_id: int, category: str) -> Tuple[models.SimulationSession, models.ClinicalCase, str]:
    learner = db.query(models.Learner).filter(models.Learner.id == learner_id).first()
    if not learner:
        raise ValueError(f"L'apprenant avec l'ID {learner_id} n'a pas été trouvé.")

    history = _get_learner_history(db, learner_id, category)
    session_type, last_score, completed_ids = _determine_session_type_and_difficulty(history)
    
    next_clinical_case = _select_next_case(db, category, session_type, last_score, completed_ids)
    
    new_session = simulation_service.create_session(
        db=db, learner_id=learner_id, case_id=next_clinical_case.id, session_type=session_type
    )
    
    # Charger la pathologie principale pour qu'elle soit disponible dans la réponse
    db.refresh(new_session, attribute_names=["cas_clinique"])
    db.refresh(new_session.cas_clinique, attribute_names=["pathologie_principale"])

    return new_session, new_session.cas_clinique, session_type

def process_learner_action(db: Session, session_id: UUID, action_data: schemas.simulation.LearnerActionRequest) -> Tuple[Dict[str, Any], str]:
    log = interaction_log_service.create_interaction_log(db=db, session_id=session_id, action_data=action_data)
    
    session = db.query(models.SimulationSession).options(joinedload(models.SimulationSession.cas_clinique)).filter(models.SimulationSession.id == session_id).first()
    if not session: raise ValueError(f"Session {session_id} non trouvée.")

    # Récupérer l'historique des actions et du chat pour le contexte
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
    session = db.query(models.SimulationSession).options(joinedload(models.SimulationSession.cas_clinique)).filter(models.SimulationSession.id == session_id).first()
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
    
    # Récupérer l'historique complet pour l'évaluation
    logs = db.query(models.InteractionLog).filter(models.InteractionLog.session_id == session_id).all()
    history_for_eval = [{"type": log.action_type, "name": log.action_content.get('name'), "justification": log.action_content.get('justification')} for log in logs]
    
    eval_result, feedback, recommendation = ai_generation_service.evaluate_final_submission(
        db=db, # Le service IA aura besoin de la DB pour fetch les noms
        case=case,
        submission=submission_data,
        session_history=history_for_eval
    )
    
    session.statut = "completed"
    session.score_final = eval_result.score_total
    session.end_time = datetime.time()
    
    # Mettre à jour les compétences de l'apprenant si c'est une évaluation sommative ou de test
    session_type = session.context_state.get("session_type")
    if session_type in ["sommative", "test"]:
        # Logique simplifiée : on met à jour la compétence principale du cas
        # Une logique plus fine mapperait les actions aux compétences requises
        competency_id = case.competences_requises.get("SYNTHESE_CLINIQUE") if case.competences_requises else None
        if competency_id:
            mastery = db.query(models.LearnerCompetencyMastery).filter(
                models.LearnerCompetencyMastery.learner_id == session.learner_id,
                models.LearnerCompetencyMastery.competence_id == competency_id
            ).first()
            if not mastery:
                mastery = models.LearnerCompetencyMastery(learner_id=session.learner_id, competence_id=competency_id)
                db.add(mastery)
            
            # Mise à jour BKT (Bayesian Knowledge Tracing) simplifiée
            mastery.mastery_level = (mastery.mastery_level or 0.5) * (eval_result.score_total / 20)
            mastery.nb_success = (mastery.nb_success or 0) + (1 if eval_result.score_total >= 10 else 0)
            mastery.nb_failures = (mastery.nb_failures or 0) + (1 if eval_result.score_total < 10 else 0)

    db.commit()
    return eval_result, feedback, recommendation