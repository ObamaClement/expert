from sqlalchemy.orm import Session
from uuid import UUID
from typing import Dict, Any

from .. import models, schemas

def create_interaction_log(
    db: Session,
    session_id: UUID,
    action_data: schemas.simulation.LearnerActionRequest
) -> models.InteractionLog:
    """
    Crée un enregistrement dans la table interaction_logs pour tracer
    une action effectuée par l'apprenant.

    Args:
        db: La session de base de données.
        session_id: L'ID de la session de simulation en cours.
        action_data: Le schéma Pydantic contenant les détails de l'action.

    Returns:
        L'objet InteractionLog qui vient d'être créé.
    """
    # Vérifie que la session parente existe
    session = db.query(models.SimulationSession).filter(models.SimulationSession.id == session_id).first()
    if not session:
        # Cette erreur ne devrait normalement pas se produire si la route est bien protégée
        raise ValueError(f"Session {session_id} non trouvée.")

    # Création de l'objet de log SQLAlchemy
    db_log = models.InteractionLog(
        session_id=session_id,
        action_category="EXAMINATION",  # Catégorie générale pour ce type d'action
        action_type=action_data.action_type,
        # Stocke les détails complets de l'action au format JSON
        action_content={
            "name": action_data.action_name,
            "justification": action_data.justification
        }
    )

    db.add(db_log)
    db.commit()
    db.refresh(db_log)

    return db_log