from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
from uuid import UUID

# ==============================================================================
# Schéma de Base
# ==============================================================================
class ChatMessageBase(BaseModel):
    """
    Schéma de base pour un message de chat.
    Contient les champs communs.
    """
    sender: str = Field(..., description="Qui envoie le message (ex: 'student', 'patient_llm', 'tutor_system')")
    content: str = Field(..., description="Le contenu textuel du message.")


# ==============================================================================
# Schéma pour la Création (ce que le Frontend envoie)
# ==============================================================================
class ChatMessageCreate(ChatMessageBase):
    """
    Schéma utilisé pour créer un nouveau message de chat via l'API.
    La session_id sera fournie dans l'URL, pas dans le corps.
    """
    message_metadata: Optional[Dict[str, Any]] = Field(None, description="Métadonnées optionnelles (ex: intention détectée)")


# ==============================================================================
# Schéma pour la Lecture (ce que l'API renvoie)
# ==============================================================================
class ChatMessage(ChatMessageBase):
    """
    Schéma complet pour représenter un message de chat en réponse d'API.
    """
    id: int
    session_id: UUID
    timestamp: datetime
    message_metadata: Optional[Dict[str, Any]] = None

    class Config:
        """
        Permet la conversion automatique depuis un objet SQLAlchemy.
        """
        from_attributes = True