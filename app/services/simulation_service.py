import logging
from sqlalchemy.orm import Session
from uuid import UUID
from typing import Optional

from .. import models

# Obtenir une instance du logger configuré
logger = logging.getLogger(__name__)

def create_session(
    db: Session, 
    learner_id: int, 
    case_id: int, 
    session_type: str,
    formative_count: int = 0
) -> models.SimulationSession:
    """
    Crée un nouvel enregistrement de session de simulation dans la base de données.
    """
    logger.info(f"Début de create_session pour learner_id={learner_id}, case_id={case_id}")
    
    context = {
        "session_type": session_type, 
        "formative_count_since_eval": formative_count,
        "dialogue": []
    }
    logger.info(f"  -> Contexte de session à enregistrer: {context}")
    
    db_session = models.SimulationSession(
        learner_id=learner_id,
        cas_clinique_id=case_id,
        statut="in_progress",
        context_state=context
    )

    db.add(db_session)
    db.commit()
    db.refresh(db_session)

    logger.info(f"  -> Session créée avec succès. ID: {db_session.id}")
    return db_session

def get_session_by_id(db: Session, session_id: UUID) -> Optional[models.SimulationSession]:
    """Récupère une session de simulation par son ID."""
    return db.query(models.SimulationSession).filter(models.SimulationSession.id == session_id).first()