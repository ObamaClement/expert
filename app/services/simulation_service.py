from sqlalchemy.orm import Session
from uuid import UUID
from typing import Optional

from .. import models, schemas

def create_session(
    db: Session, 
    learner_id: int, 
    case_id: int, 
    session_type: str,
    formative_count: int = 0  # <--- PARAMÈTRE AJOUTÉ
) -> models.SimulationSession:
    """
    Crée un nouvel enregistrement de session de simulation dans la base de données.
    """
    db_session = models.SimulationSession(
        learner_id=learner_id,
        cas_clinique_id=case_id,
        statut="in_progress",
        # --- MODIFICATION ICI ---
        # Le contexte stocke maintenant le type ET le compteur de sessions formatives.
        context_state={
            "session_type": session_type, 
            "formative_count_since_eval": formative_count,
            "dialogue": []
        }
    )

    db.add(db_session)
    db.commit()
    db.refresh(db_session)

    return db_session


def get_session_by_id(db: Session, session_id: UUID) -> Optional[models.SimulationSession]:
    """
    Récupère une session de simulation par son ID.
    """
    return db.query(models.SimulationSession).filter(models.SimulationSession.id == session_id).first()