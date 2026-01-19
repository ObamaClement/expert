import logging
from sqlalchemy.orm import Session
from uuid import UUID
from typing import Optional, List

from .. import models

logger = logging.getLogger(__name__)

def create_session(
    db: Session, 
    learner_id: int, 
    case_id: int, 
    session_type: str,
    formative_count: int = 0,
    formative_cases_pool: List[int] = None
) -> models.SimulationSession:
    """
    Crée un nouvel enregistrement de session de simulation dans la base de données.
    
    Args:
        db: La session de base de données.
        learner_id: L'ID de l'apprenant.
        case_id: L'ID du cas clinique sélectionné pour cette session.
        session_type: Le type de session ('test', 'formative', 'sommative').
        formative_count: Compteur de sessions formatives depuis la dernière évaluation.
        formative_cases_pool: Liste des IDs des cas formatifs pour l'évaluation sommative.
    
    Returns:
        L'objet SimulationSession qui vient d'être créé.
    """
    logger.info(f"[create_session] Création pour learner_id={learner_id}, case_id={case_id}")
    logger.info(f"  -> Type: {session_type}, Compteur formatif: {formative_count}")
    
    # Construction du contexte de session
    context = {
        "session_type": session_type,
        "formative_count_since_eval": formative_count,
        "dialogue": [],
        "formative_cases_pool": formative_cases_pool or []
    }
    
    logger.info(f"  -> Contexte de session: {context}")
    
    # Création de l'instance du modèle SQLAlchemy
    db_session = models.SimulationSession(
        learner_id=learner_id,
        cas_clinique_id=case_id,
        statut="in_progress",
        context_state=context
    )

    db.add(db_session)
    db.commit()
    db.refresh(db_session)

    logger.info(f"  -> ✅ Session créée avec succès. ID: {db_session.id}")
    return db_session


def get_session_by_id(db: Session, session_id: UUID) -> Optional[models.SimulationSession]:
    """
    Récupère une session de simulation par son ID.
    
    Args:
        db: La session de base de données.
        session_id: L'UUID de la session à récupérer.
    
    Returns:
        L'objet SimulationSession ou None si non trouvé.
    """
    return db.query(models.SimulationSession).filter(
        models.SimulationSession.id == session_id
    ).first()


def update_session_status(
    db: Session, 
    session_id: UUID, 
    new_status: str,
    score: float = None
) -> models.SimulationSession:
    """
    Met à jour le statut d'une session et optionnellement son score.
    
    Args:
        db: La session de base de données.
        session_id: L'UUID de la session à mettre à jour.
        new_status: Le nouveau statut ('in_progress', 'completed', 'abandoned').
        score: Le score final (optionnel).
    
    Returns:
        La session mise à jour.
    """
    session = get_session_by_id(db, session_id)
    if not session:
        raise ValueError(f"Session {session_id} introuvable.")
    
    session.statut = new_status
    if score is not None:
        session.score_final = score
    
    db.commit()
    db.refresh(session)
    
    logger.info(f"[update_session_status] Session {session_id} -> statut: {new_status}, score: {score}")
    return session