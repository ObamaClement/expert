import logging
from sqlalchemy.orm import Session
from uuid import UUID
from .. import models, schemas

logger = logging.getLogger(__name__)

def create_interaction_log(db: Session, session_id: UUID, action_data: schemas.simulation.LearnerActionRequest) -> models.InteractionLog:
    session = db.query(models.SimulationSession).filter(models.SimulationSession.id == session_id).first()
    if not session:
        logger.error(f"[create_interaction_log] Tentative de log pour une session inexistante: {session_id}")
        raise ValueError(f"Session {session_id} non trouvée.")

    db_log = models.InteractionLog(
        session_id=session_id,
        action_category="EXAMINATION",
        action_type=action_data.action_type,
        action_content={
            "name": action_data.action_name,
            "justification": action_data.justification or None # Correction pour accepter None
        }
    )

    db.add(db_log)
    db.commit()
    db.refresh(db_log)
    return db_log