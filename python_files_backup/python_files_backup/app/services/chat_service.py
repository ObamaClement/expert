from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID

from .. import models, schemas


def create_chat_message(db: Session, session_id: UUID, message: schemas.ChatMessageCreate) -> models.ChatMessage:
    """
    Crée un nouveau message de chat et l'associe à une session.
    
    :param db: Session de base de données.
    :param session_id: L'ID de la session de simulation à laquelle le message appartient.
    :param message: Le schéma Pydantic contenant les données du message.
    :return: L'objet ChatMessage créé.
    """
    # Vérifier que la session parente existe pour garantir l'intégrité
    session = db.query(models.SimulationSession).filter(models.SimulationSession.id == session_id).first()
    if not session:
        raise ValueError(f"La session avec l'ID {session_id} n'a pas été trouvée.")

    # Créer l'instance du modèle SQLAlchemy
    db_message = models.ChatMessage(
        **message.model_dump(),
        session_id=session_id
    )
    
    db.add(db_message)
    db.commit()
    db.refresh(db_message)
    
    return db_message


def get_messages_by_session(db: Session, session_id: UUID) -> List[models.ChatMessage]:
    """
    Récupère tous les messages d'une session de simulation, triés par ordre chronologique.
    
    :param db: Session de base de données.
    :param session_id: L'ID de la session à interroger.
    :return: Une liste d'objets ChatMessage.
    """
    return db.query(models.ChatMessage).filter(
        models.ChatMessage.session_id == session_id
    ).order_by(models.ChatMessage.timestamp.asc()).all()