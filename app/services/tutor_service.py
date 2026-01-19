import logging
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc
from typing import List, Tuple, Dict, Any, Optional
from uuid import UUID
from datetime import datetime
import random

from .. import models, schemas
from . import simulation_service, interaction_log_service, ai_generation_service, clinical_case_service

logger = logging.getLogger(__name__)

def _get_learner_history(db: Session, learner_id: int, category: str) -> List[models.SimulationSession]:
    """
    Récupère l'historique complet des sessions de l'apprenant pour une catégorie,
    trié du plus ancien au plus récent (pour rejouer le film de la progression).
    """
    return db.query(models.SimulationSession).join(
        models.ClinicalCase, models.SimulationSession.cas_clinique_id == models.ClinicalCase.id
    ).join(
        models.Disease, models.ClinicalCase.pathologie_principale_id == models.Disease.id
    ).filter(
        models.SimulationSession.learner_id == learner_id,
        models.Disease.categorie == category
    ).order_by(models.SimulationSession.start_time.asc()).all()


def _calculate_current_state(history: List[models.SimulationSession]) -> Tuple[int, str, List[int]]:
    """
    Analyse l'historique pour déterminer l'état actuel de l'apprenant.
    
    Retourne:
    - current_level (int): Niveau de difficulté calculé (0-30)
    - next_session_type (str): 'formative' ou 'sommative'
    - formative_buffer (List[int]): Liste des IDs des cas formatifs du cycle en cours
    """
    current_level = 1 # Niveau de départ
    formative_buffer = [] # Stocke les cas formatifs du cycle actuel

    # On ne regarde que les sessions terminées pour calculer la progression
    completed_sessions = [s for s in history if s.statut == "completed"]

    for session in completed_sessions:
        # Récupérer le type depuis le contexte (par défaut 'formative' si ancien format)
        s_type = session.context_state.get("session_type", "formative")
        
        if s_type == "sommative":
            # C'est un examen -> On évalue la progression
            score = session.score_final if session.score_final is not None else 0
            
            if score >= 12.0:
                # Réussite : On monte de niveau
                current_level += 3
            else:
                # Échec : On stagne (ou on baisse légèrement pour renforcer)
                current_level = max(1, current_level - 1)
            
            # Fin du cycle, on vide le buffer
            formative_buffer = []
            
        else:
            # C'est une session formative -> On l'ajoute au buffer du cycle
            formative_buffer.append(session.cas_clinique_id)
            
            # Si on a accumulé 3 sessions formatives ou plus dans ce cycle, 
            # on vide le buffer virtuellement pour le calcul suivant, 
            # car la prochaine DEVRAIT être sommative.
            if len(formative_buffer) > 3:
                # Cas rare où l'utilisateur a fait trop de formatives sans sommative
                # On garde les 3 dernières pour le pool
                formative_buffer = formative_buffer[-3:]

    # Détermination de la prochaine étape
    if len(formative_buffer) >= 3:
        next_session_type = "sommative"
    else:
        next_session_type = "formative"
        
    # Plafond niveau max
    current_level = min(30, current_level)

    return current_level, next_session_type, formative_buffer


def start_new_session(db: Session, learner_id: int, category: str) -> Tuple[models.SimulationSession, models.ClinicalCase, str]:
    """
    Orchestre le démarrage d'une session.
    Gère la reprise de session et la logique de cycle pédagogique.
    """
    logger.info(f"--- Démarrage session (Learner: {learner_id}, Cat: {category}) ---")

    # 1. Récupérer l'historique
    history = _get_learner_history(db, learner_id, category)

    # 2. Vérifier s'il y a une session en cours (non terminée)
    # On regarde la dernière session de l'historique (qui est trié par date asc, donc la dernière est à la fin)
    if history:
        last_session = history[-1]
        if last_session.statut == "in_progress":
            logger.info(f"  -> 🔄 Reprise de la session {last_session.id}")
            db.refresh(last_session, ["cas_clinique"])
            if last_session.cas_clinique:
                db.refresh(last_session.cas_clinique, ["pathologie_principale"])
            
            s_type = last_session.context_state.get("session_type", "formative")
            return last_session, last_session.cas_clinique, s_type

    # 3. Calculer l'état pédagogique actuel
    current_level, next_type, formative_buffer = _calculate_current_state(history)
    
    logger.info(f"  -> État calculé : Niveau {current_level}, Prochain type: {next_type}")
    logger.info(f"  -> Buffer formatif : {formative_buffer}")

    # 4. Sélectionner le cas clinique
    selected_case = None
    
    # Liste de tous les cas déjà faits pour éviter les répétitions en formatif
    all_seen_ids = [s.cas_clinique_id for s in history]

    if next_type == "sommative":
        # En sommatif, on reprend un cas du buffer (déjà vu)
        if not formative_buffer:
            # Fallback de sécurité : si pas de buffer, on cherche un cas niveau actuel
            logger.warning("  ⚠️ Pas de cas dans le buffer pour sommative. Fallback sur recherche standard.")
            selected_case = clinical_case_service.get_case_for_progression(
                db, category, current_level, [] # On autorise les doublons ici exceptionnellement
            )
        else:
            # Choix aléatoire parmi les 3 cas formatifs précédents
            case_id = random.choice(formative_buffer)
            selected_case = clinical_case_service.get_case_by_id(db, case_id)
            logger.info(f"  -> 🎲 Cas sommatif sélectionné dans le buffer : {case_id}")

    else:
        # En formatif, on veut un NOUVEAU cas proche du niveau actuel
        selected_case = clinical_case_service.get_case_for_progression(
            db, category, current_level, all_seen_ids
        )

    if not selected_case:
        raise ValueError(f"Aucun cas clinique disponible pour la catégorie '{category}' au niveau {current_level}.")

    # 5. Créer la session
    new_session = simulation_service.create_session(
        db=db,
        learner_id=learner_id,
        case_id=selected_case.id,
        session_type=next_type,
        formative_count=len(formative_buffer), # Pour info dans le contexte
        formative_cases_pool=formative_buffer
    )
    
    # Rafraîchir pour avoir les relations
    db.refresh(new_session, ["cas_clinique"])
    if new_session.cas_clinique:
        db.refresh(new_session.cas_clinique, ["pathologie_principale"])

    return new_session, new_session.cas_clinique, next_type


def process_learner_action(
    db: Session, 
    session_id: UUID, 
    action_data: schemas.simulation.LearnerActionRequest
) -> Tuple[Dict[str, Any], str]:
    """Traite une action de l'apprenant."""
    
    # 1. Logger l'action
    interaction_log_service.create_interaction_log(db, session_id, action_data)
    
    # 2. Récupérer le contexte
    session = db.query(models.SimulationSession).options(
        joinedload(models.SimulationSession.cas_clinique).joinedload(models.ClinicalCase.pathologie_principale)
    ).filter(models.SimulationSession.id == session_id).first()
    
    if not session:
        raise ValueError("Session introuvable")

    # 3. Construire l'historique pour l'IA
    logs = db.query(models.InteractionLog).filter(
        models.InteractionLog.session_id == session_id
    ).order_by(models.InteractionLog.timestamp.asc()).all()
    
    history_text = [
        f"Action: {l.action_content.get('name')} (Justif: {l.action_content.get('justification')})" 
        for l in logs
    ]

    # 4. Générer le résultat
    result = ai_generation_service.generate_exam_result(
        session.cas_clinique, 
        history_text, 
        action_data.action_name
    )
    
    return result, None


def provide_hint(db: Session, session_id: UUID) -> Tuple[str, str]:
    """Fournit un indice."""
    # Récupérer ou créer l'état de scaffolding (table existante)
    state = db.query(models.TutorScaffoldingState).filter_by(session_id=session_id).first()
    if not state:
        state = models.TutorScaffoldingState(session_id=session_id, current_level=0)
        db.add(state)
        db.commit()

    session = db.query(models.SimulationSession).options(
        joinedload(models.SimulationSession.cas_clinique).joinedload(models.ClinicalCase.pathologie_principale)
    ).filter_by(id=session_id).first()

    # Historique pour l'IA
    logs = db.query(models.InteractionLog).filter_by(session_id=session_id).all()
    history_text = [f"Action: {l.action_content.get('name')}" for l in logs]

    # Génération
    h_type, h_content = ai_generation_service.generate_hint(
        session.cas_clinique, 
        history_text, 
        state.current_level
    )

    # Mise à jour niveau d'aide
    state.current_level += 1
    db.commit()

    return h_type, h_content


def evaluate_submission(
    db: Session, 
    session_id: UUID, 
    submission_data: schemas.simulation.SubmissionRequest
) -> Tuple[schemas.simulation.EvaluationResult, str, str]:
    """
    Évalue la session et la clôture.
    """
    session = db.query(models.SimulationSession).options(
        joinedload(models.SimulationSession.cas_clinique).joinedload(models.ClinicalCase.pathologie_principale)
    ).filter_by(id=session_id).first()
    
    if not session:
        raise ValueError("Session introuvable")
    
    if session.statut == "completed":
        raise ValueError("Session déjà évaluée")

    # 1. Préparer l'historique pour l'IA
    logs = db.query(models.InteractionLog).filter_by(session_id=session_id).all()
    history_json = [
        {"type": l.action_type, "name": l.action_content.get('name'), "justif": l.action_content.get('justification')}
        for l in logs
    ]

    # 2. Appel IA (Note sur 20)
    eval_result, feedback, recommendation = ai_generation_service.evaluate_final_submission(
        db, session.cas_clinique, submission_data, history_json
    )

    # 3. Mise à jour Session
    session.score_final = eval_result.score_total
    session.statut = "completed"
    session.end_time = datetime.now()
    
    db.commit()
    
    logger.info(f"✅ Session {session_id} terminée. Score: {session.score_final}/20")

    return eval_result, feedback, recommendation