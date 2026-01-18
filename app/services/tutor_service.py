import logging
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc
from typing import List, Tuple, Dict, Any, Optional
from uuid import UUID
from datetime import datetime
import random

from .. import models, schemas
from . import simulation_service, disease_service, interaction_log_service, ai_generation_service

logger = logging.getLogger(__name__)

def _get_learner_history(db: Session, learner_id: int, category: str) -> List[models.SimulationSession]:
    """Récupère l'historique de l'apprenant pour une catégorie donnée, du plus récent au plus ancien."""
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
    return history

def _select_case_for_activity(db: Session, category: str, session_type: str, last_score: Optional[float], seen_case_ids: List[int], learner_id: int, last_difficulty: int, formative_cases_ids: List[int] = []) -> models.ClinicalCase:
    """Sélectionne un cas clinique en fonction de la logique pédagogique."""
    logger.info(f"[_select_case_for_activity] Début de la sélection. Type: '{session_type}', dernier score: {last_score}, dernière difficulté: {last_difficulty}")
    logger.info(f"  -> IDs des cas déjà vus à exclure: {seen_case_ids}")

    # --- Logique pour Session Sommative ---
    if session_type == "sommative":
        if not formative_cases_ids:
            logger.error("Tentative de session sommative sans cas formatifs préalables !")
            raise ValueError("Erreur logique: session sommative demandée sans cas formatifs.")
        case_to_evaluate_id = random.choice(formative_cases_ids)
        logger.info(f"  -> Mode SOMMATIF: Sélection aléatoire du cas #{case_to_evaluate_id} parmi les cas formatifs {formative_cases_ids}")
        next_case = db.query(models.ClinicalCase).filter(models.ClinicalCase.id == case_to_evaluate_id).first()
        if not next_case: raise ValueError(f"Cas {case_to_evaluate_id} pour l'évaluation sommative introuvable.")
        logger.info(f"    -> ✅ Cas sommatif trouvé: #{next_case.id} (Niveau {next_case.niveau_difficulte})")
        return next_case

    # --- Logique pour Sessions 'test' ou 'formative' ---
    query = db.query(models.ClinicalCase).join(
        models.Disease, models.ClinicalCase.pathologie_principale_id == models.Disease.id
    ).filter(
        models.Disease.categorie == category,
        models.ClinicalCase.id.notin_(seen_case_ids)
    )
    
    difficulty_target = last_difficulty
    if session_type == "test":
        logger.info("  -> Mode TEST: Vise une difficulté de départ autour de 10.")
        difficulty_target = 10
    elif session_type == "formative":
        if last_score is not None:
            if last_score >= 12: # Seuil de réussite sur 20
                difficulty_target = last_difficulty + 3
                logger.info(f"  -> Mode FORMATIF (SUCCÈS): Progression -> vise niveau ~{difficulty_target}.")
            else:
                difficulty_target = last_difficulty
                logger.info(f"  -> Mode FORMATIF (ÉCHEC): Stagnation -> vise niveau ~{difficulty_target}.")
    
    # Filtrer par difficulté cible
    query = query.filter(models.ClinicalCase.niveau_difficulte.between(difficulty_target - 2, difficulty_target + 2))

    next_case = query.order_by(models.ClinicalCase.niveau_difficulte.asc()).first()
    
    # --- Logique de Fallback si aucun cas n'est trouvé à la difficulté cible ---
    if not next_case:
        logger.warning("  -> Aucun cas trouvé avec les filtres stricts. Passage au mode Fallback.")
        fallback_query = db.query(models.ClinicalCase).join(models.Disease, models.ClinicalCase.pathologie_principale_id == models.Disease.id).filter(
            models.Disease.categorie == category, models.ClinicalCase.id.notin_(seen_case_ids)
        )
        all_available_cases = fallback_query.all()
        if not all_available_cases:
            logger.error(f"  -> FALLBACK ÉCHOUÉ: Plus aucun cas non vu dans la catégorie '{category}'.")
            raise ValueError(f"Plus aucun cas clinique non résolu disponible dans la catégorie '{category}'.")

        # Trouver le cas le plus proche de la difficulté cible
        next_case = min(all_available_cases, key=lambda x: abs(x.niveau_difficulte - difficulty_target))
        logger.info(f"    -> Fallback: Cas le plus proche du niveau {difficulty_target} trouvé: #{next_case.id} (Niveau {next_case.niveau_difficulte})")

    logger.info(f"    -> ✅ Cas final sélectionné: #{next_case.id} (Niveau {next_case.niveau_difficulte})")
    return next_case

def start_new_session(db: Session, learner_id: int, category: str) -> Tuple[models.SimulationSession, models.ClinicalCase, str]:
    logger.info(f"\n\n================ [START] start_new_session pour learner #{learner_id}, category '{category}' ================")
    
    history = _get_learner_history(db, learner_id, category)
    
    # --- 1. REPRISE DE SESSION NON TERMINÉE ---
    last_session = history[0] if history else None
    if last_session and last_session.statut == "in_progress":
        logger.info(f"  -> Reprise de la session 'in_progress' existante: {last_session.id}")
        db.refresh(last_session, ["cas_clinique"])
        if last_session.cas_clinique: db.refresh(last_session.cas_clinique, ["pathologie_principale"])
        return last_session, last_session.cas_clinique, last_session.context_state.get("session_type", "formative")

    # --- 2. DÉTERMINATION DU TYPE DE LA NOUVELLE SESSION ---
    completed_history = [s for s in history if s.statut == "completed"]
    seen_case_ids = {s.cas_clinique_id for s in history} # Utiliser un set pour performance
    
    session_type = "test"
    last_score = None
    last_difficulty = 10 # Difficulté de base
    formative_cases_ids = []

    if not completed_history:
        logger.info("  -> Logique: Aucun historique complété. Démarrage session 'test'.")
    else:
        # Trouver la dernière évaluation (sommative ou test initial)
        last_eval = next((s for s in completed_history if s.context_state.get("session_type") in ["sommative", "test"]), None)
        
        if not last_eval:
             logger.info("  -> Logique: Sessions complétées mais aucune évaluation. On continue en 'formative'.")
             session_type = "formative"
        else:
            logger.info(f"  -> Logique: Dernière évaluation trouvée: Session ID {last_eval.id}, Score: {last_eval.score_final}, Fin: {last_eval.end_time}")
            last_eval_case = db.query(models.ClinicalCase).filter_by(id=last_eval.cas_clinique_id).first()
            last_difficulty = last_eval_case.niveau_difficulte if last_eval_case else 10
            
            # Compter les sessions formatives complétées *après* cette dernière évaluation
            formative_since_last_eval = [s for s in completed_history if s.end_time and s.end_time > last_eval.end_time and s.context_state.get("session_type") == "formative"]
            logger.info(f"  -> Logique: {len(formative_since_last_eval)} session(s) formative(s) complétée(s) depuis.")

            if len(formative_since_last_eval) >= 3:
                logger.info("  -> Logique: Cycle de 3 formatives terminé. Passage en 'sommative'.")
                session_type = "sommative"
                formative_cases_ids = [s.cas_clinique_id for s in formative_since_last_eval[:3]]
            else:
                logger.info("  -> Logique: Cycle formatif en cours. Nouvelle session 'formative'.")
                session_type = "formative"
                last_score = last_eval.score_final # Le score de la dernière éval guide la difficulté de la formative
                
    # --- 3. SÉLECTION DU CAS CLINIQUE ---
    next_clinical_case = _select_case_for_activity(db, category, session_type, last_score, list(seen_case_ids), learner_id, last_difficulty, formative_cases_ids)
    
    # --- 4. CRÉATION DE LA NOUVELLE SESSION ---
    new_session = simulation_service.create_session(
        db=db, learner_id=learner_id, case_id=next_clinical_case.id, session_type=session_type
    )
    
    db.refresh(new_session, ["cas_clinique"])
    if new_session.cas_clinique: db.refresh(new_session.cas_clinique, ["pathologie_principale"])

    logger.info(f"================ [END] start_new_session, nouvelle session: {new_session.id} (type: {session_type}) ================\n")
    return new_session, new_session.cas_clinique, session_type

def process_learner_action(db: Session, session_id: UUID, action_data: schemas.simulation.LearnerActionRequest) -> Tuple[Dict[str, Any], str]:
    """Traite une action de l'apprenant et génère un résultat via l'IA."""
    interaction_log_service.create_interaction_log(db=db, session_id=session_id, action_data=action_data)
    session = db.query(models.SimulationSession).options(joinedload(models.SimulationSession.cas_clinique).joinedload(models.ClinicalCase.pathologie_principale)).filter(models.SimulationSession.id == session_id).first()
    if not session: raise ValueError(f"Session {session_id} non trouvée.")
    history_logs = db.query(models.InteractionLog).filter(models.InteractionLog.session_id == session_id).order_by(models.InteractionLog.timestamp.asc()).all()
    session_history = [f"Action: {l.action_content.get('name')}, Justification: {l.action_content.get('justification') or 'N/A'}" for l in history_logs]
    action_result = ai_generation_service.generate_exam_result(case=session.cas_clinique, session_history=session_history, exam_name=action_data.action_name)
    return action_result, None # Feedback immédiat non implémenté pour l'instant

def _get_or_create_scaffolding_state(db: Session, session_id: UUID) -> models.TutorScaffoldingState:
    state = db.query(models.TutorScaffoldingState).filter(models.TutorScaffoldingState.session_id == session_id).first()
    if not state:
        state = models.TutorScaffoldingState(session_id=session_id, current_level=0, indices_deja_donnes=[])
        db.add(state); db.commit(); db.refresh(state)
    return state

def provide_hint(db: Session, session_id: UUID) -> Tuple[str, str]:
    """Fournit un indice à l'apprenant en suivant une logique de scaffolding."""
    state = _get_or_create_scaffolding_state(db, session_id)
    session = db.query(models.SimulationSession).options(joinedload(models.SimulationSession.cas_clinique).joinedload(models.ClinicalCase.pathologie_principale)).filter(models.SimulationSession.id == session_id).first()
    if not session: raise ValueError(f"Session {session_id} non trouvée.")
    history_logs = db.query(models.InteractionLog).filter(models.InteractionLog.session_id == session_id).all()
    session_history = [f"Action: {l.action_content.get('name')}" for l in history_logs]
    hint_type, hint_content = ai_generation_service.generate_hint(case=session.cas_clinique, session_history=session_history, hint_level=state.current_level)
    decision = models.TutorDecision(session_id=session_id, strategy_used="Scaffolding", action_choisie="Fournir un Indice", intervention_content=hint_content, rationale={"reason": "Demande de l'apprenant", "level": state.current_level})
    db.add(decision)
    state.current_level += 1
    db.commit()
    return hint_type, hint_content

def evaluate_submission(db: Session, session_id: UUID, submission_data: schemas.simulation.SubmissionRequest) -> Tuple[schemas.simulation.EvaluationResult, str, str]:
    """Évalue la soumission finale de l'apprenant."""
    logger.info(f"[evaluate_submission] Début de l'évaluation pour la session {session_id}")
    session = db.query(models.SimulationSession).options(joinedload(models.SimulationSession.cas_clinique).joinedload(models.ClinicalCase.pathologie_principale)).filter(models.SimulationSession.id == session_id).first()
    if not session: raise ValueError(f"Session {session_id} non trouvée.")
    if session.statut == "completed": raise ValueError("Cette session a déjà été évaluée.")

    case = session.cas_clinique
    logs = db.query(models.InteractionLog).filter(models.InteractionLog.session_id == session_id).all()
    history_for_eval = [{"type": log.action_type, "name": log.action_content.get('name'), "justification": log.action_content.get('justification')} for log in logs]
    
    # --- CORRECTION DU BUG ET DE LA LOGIQUE DE NOTATION ---
    # 1. L'IA retourne un objet Pydantic, pas un dictionnaire.
    # 2. Le score total de l'IA est sur 20 (10+5+5).
    # 3. Nous devons enregistrer ce score sur 20 en BDD.
    
    eval_result_from_ai, feedback, recommendation = ai_generation_service.evaluate_final_submission(db=db, case=case, submission=submission_data, session_history=history_for_eval)
    
    # Accès direct aux attributs de l'objet Pydantic (Correction du bug .get())
    score_diag = eval_result_from_ai.score_diagnostic
    score_ther = eval_result_from_ai.score_therapeutique
    score_dem = eval_result_from_ai.score_demarche
    
    # Le score total est déjà sur 20, pas besoin de conversion.
    score_total_sur_20 = eval_result_from_ai.score_total

    logger.info(f"  -> Scores bruts de l'IA: Diag={score_diag}/10, Thera={score_ther}/5, Demarche={score_dem}/5. Total={score_total_sur_20}/20.")

    # Mettre à jour la session avec le statut et le score correct
    session.statut = "completed"
    session.score_final = score_total_sur_20  # On stocke le score sur 20
    session.end_time = datetime.now()
    
    db.commit()
    logger.info(f"  -> Session {session_id} marquée comme 'completed' avec un score final de {session.score_final}/20.")
    
    # Retourner l'objet d'évaluation final
    return eval_result_from_ai, feedback, recommendation