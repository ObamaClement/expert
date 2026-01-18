from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc
from typing import List, Tuple, Dict, Any, Optional
from uuid import UUID
from datetime import datetime
import random

from .. import models, schemas
from . import simulation_service, disease_service, interaction_log_service, ai_generation_service

def _get_learner_history(db: Session, learner_id: int, category: str) -> List[models.SimulationSession]:
    """Récupère TOUT l'historique (en cours et terminé) pour une catégorie, le plus récent en premier."""
    print("\n--- [LOG _get_learner_history] ---")
    history = db.query(models.SimulationSession).join(
        models.ClinicalCase, models.SimulationSession.cas_clinique_id == models.ClinicalCase.id
    ).join(
        models.Disease, models.ClinicalCase.pathologie_principale_id == models.Disease.id
    ).filter(
        models.SimulationSession.learner_id == learner_id,
        models.Disease.categorie == category
    ).order_by(desc(models.SimulationSession.start_time)).all()
    print(f"  -> {len(history)} session(s) trouvée(s) pour l'apprenant #{learner_id} dans la catégorie '{category}'.")
    for i, s in enumerate(history):
        print(f"    - Session {i+1}: ID={s.id}, Statut='{s.statut}', Type='{s.context_state.get('session_type')}', Score={s.score_final}")
    print("------------------------------------")
    return history

def _select_case_for_activity(db: Session, category: str, session_type: str, last_score: Optional[float], seen_case_ids: List[int], learner_id: int, formative_cases_ids: List[int] = []) -> models.ClinicalCase:
    """Sélectionne le cas clinique approprié."""
    print("\n--- [LOG _select_case_for_activity] ---")
    print(f"  -> Recherche d'un cas de type: '{session_type}'")
    print(f"  -> Score de la dernière évaluation: {last_score}")
    print(f"  -> IDs des cas déjà vus à exclure: {seen_case_ids}")

    if session_type == "sommative":
        if not formative_cases_ids:
            raise ValueError("Erreur logique: demande d'évaluation sommative sans cas formatifs préalables.")
        case_to_evaluate_id = random.choice(formative_cases_ids)
        print(f"  -> Mode SOMMATIF: Sélection aléatoire du cas #{case_to_evaluate_id} parmi {formative_cases_ids}")
        next_case = db.query(models.ClinicalCase).filter(models.ClinicalCase.id == case_to_evaluate_id).first()
        if not next_case:
             raise ValueError(f"Cas {case_to_evaluate_id} pour l'évaluation sommative introuvable.")
        print(f"    -> ✅ Cas trouvé: #{next_case.id} ({next_case.code_fultang})")
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
        print("  -> Mode TEST: recherche d'un cas de difficulté [10, 20].")
    elif last_score is not None:
        last_completed_session = db.query(models.SimulationSession).filter(models.SimulationSession.learner_id==learner_id, models.SimulationSession.statut=='completed').order_by(desc(models.SimulationSession.end_time)).first()
        current_difficulty = 10
        if last_completed_session:
             case = db.query(models.ClinicalCase).filter_by(id=last_completed_session.cas_clinique_id).first()
             if case: current_difficulty = case.niveau_difficulte
        
        if last_score < 12:
            difficulty_target = current_difficulty
            print(f"  -> Mode FORMATIF (ÉCHEC): recherche d'un cas autour du niveau {difficulty_target}.")
            query = query.filter(models.ClinicalCase.niveau_difficulte.between(difficulty_target - 2, difficulty_target + 2))
        else:
            difficulty_target = current_difficulty + 3
            print(f"  -> Mode FORMATIF (SUCCÈS): recherche d'un cas de niveau >= {difficulty_target}.")
            query = query.filter(models.ClinicalCase.niveau_difficulte >= difficulty_target)

    next_case = query.order_by(models.ClinicalCase.niveau_difficulte.asc()).first()
    
    if not next_case:
        print("  -> ⚠️ Aucun cas trouvé avec les filtres stricts. Passage au mode Fallback.")
        fallback_query = db.query(models.ClinicalCase).join(
            models.Disease, models.ClinicalCase.pathologie_principale_id == models.Disease.id
        ).filter(
            models.Disease.categorie == category,
            models.ClinicalCase.id.notin_(seen_case_ids)
        )
        if difficulty_target > 0:
            all_available_cases = fallback_query.all()
            if all_available_cases:
                next_case = min(all_available_cases, key=lambda x: abs(x.niveau_difficulte - difficulty_target))
                print(f"    -> Fallback: Cas le plus proche du niveau cible {difficulty_target} trouvé: #{next_case.id} (Niveau {next_case.niveau_difficulte})")
        if not next_case:
            next_case = fallback_query.order_by(models.ClinicalCase.niveau_difficulte.asc()).first()
            if next_case: print(f"    -> Fallback: Cas le plus facile disponible trouvé: #{next_case.id} (Niveau {next_case.niveau_difficulte})")

    if not next_case:
        raise ValueError(f"Plus aucun cas clinique non résolu disponible dans la catégorie '{category}'.")
        
    print(f"    -> ✅ Cas final sélectionné: #{next_case.id} ({next_case.code_fultang}, Niveau {next_case.niveau_difficulte})")
    print("------------------------------------")
    return next_case

def start_new_session(db: Session, learner_id: int, category: str) -> Tuple[models.SimulationSession, models.ClinicalCase, str]:
    print("\n\n================ [LOG start_new_session] ================")
    learner = db.query(models.Learner).filter(models.Learner.id == learner_id).first()
    if not learner: raise ValueError(f"L'apprenant avec l'ID {learner_id} n'a pas été trouvé.")

    history = _get_learner_history(db, learner_id, category)
    
    last_session = history[0] if history else None
    if last_session and last_session.statut == "in_progress":
        print("  -> Une session est déjà 'in_progress'. Reprise de la session.")
        db.refresh(last_session, attribute_names=["cas_clinique"])
        if last_session.cas_clinique: db.refresh(last_session.cas_clinique, attribute_names=["pathologie_principale"])
        session_type = last_session.context_state.get("session_type", "formative")
        print(f"    -> ✅ Reprise de la session #{last_session.id} (Type: {session_type})")
        return last_session, last_session.cas_clinique, session_type

    completed_history = [s for s in history if s.statut == "completed"]
    seen_case_ids = [s.cas_clinique_id for s in history]
    
    session_type, last_score, formative_cases_ids = "test", None, []

    if not completed_history:
        print("  -> Aucun historique complété. Démarrage d'une session de 'test'.")
    else:
        last_eval = next((s for s in completed_history if s.context_state.get("session_type") in ["test", "sommative"]), None)
        if not last_eval:
            print("  -> Historique trouvé mais sans évaluation (test/sommative). Démarrage d'une session 'formative'.")
            session_type = "formative"
        else:
            print(f"  -> Dernière évaluation trouvée: Session #{last_eval.id}, Score: {last_eval.score_final}")
            formative_since_last_eval = [s for s in completed_history if s.end_time > last_eval.end_time and s.context_state.get("session_type") == "formative"]
            print(f"  -> {len(formative_since_last_eval)} session(s) formative(s) depuis cette évaluation.")

            if last_eval.score_final < 12:
                 print("  -> Le score de la dernière éval était < 12. On recommence un cycle formatif.")
                 session_type = "formative"
                 last_score = last_eval.score_final
            elif len(formative_since_last_eval) >= 3:
                print("  -> 3 sessions formatives complétées. Démarrage d'une session 'sommative'.")
                session_type = "sommative"
                last_score = last_eval.score_final
                formative_cases_ids = [s.cas_clinique_id for s in formative_since_last_eval[:3]]
            else:
                print("  -> Moins de 3 sessions formatives. Démarrage d'une nouvelle session 'formative'.")
                session_type = "formative"
                last_score = last_eval.score_final
                
    next_clinical_case = _select_case_for_activity(db, category, session_type, last_score, seen_case_ids, learner_id, formative_cases_ids)
    
    formative_count = (len(formative_since_last_eval) + 1) if 'formative_since_last_eval' in locals() and session_type == 'formative' and last_eval and last_eval.score_final >= 12 else 1
    
    new_session = simulation_service.create_session(
        db=db, learner_id=learner_id, case_id=next_clinical_case.id, session_type=session_type, formative_count=formative_count
    )
    
    db.refresh(new_session, attribute_names=["cas_clinique"])
    if new_session.cas_clinique: db.refresh(new_session.cas_clinique, attribute_names=["pathologie_principale"])

    return new_session, new_session.cas_clinique, session_type

# ... (Le reste du fichier, `process_learner_action`, `provide_hint`, `evaluate_submission`, etc. reste identique)
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