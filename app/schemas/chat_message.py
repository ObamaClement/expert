import logging
from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, Any
from datetime import datetime
from uuid import UUID

# ==============================================================================
# CONFIGURATION DU LOGGER SCHEMAS
# ==============================================================================
logger = logging.getLogger("schemas.chat")
logger.setLevel(logging.DEBUG)

if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - [SCHEMA-CHAT] - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

logger.info("🔧 Chargement des définitions de schémas ChatMessage...")

# ==============================================================================
# SOUS-SCHÉMA : FEEDBACK TUTEUR (NOUVEAU)
# ==============================================================================
class TutorFeedback(BaseModel):
    """
    Structure stricte du feedback pédagogique généré par l'IA Tuteur.
    Ce modèle sert à valider le JSON brut reçu du LLM avant stockage.
    """
    chronology_check: str = Field(
        ..., 
        description="Analyse critique de la chronologie (ex: 'Prématuré', 'Pertinent')."
    )
    interpretation_guide: str = Field(
        ..., 
        description="Clés d'interprétation de la réponse du patient (Sémiologie)."
    )
    better_question: str = Field(
        ..., 
        description="Suggestion de reformulation ou de meilleure question."
    )

    @field_validator('chronology_check')
    @classmethod
    def validate_chronology(cls, v):
        # On logue pour le debug si l'IA génère quelque chose d'étrange
        if len(v) < 3:
            logger.warning(f"⚠️ Chronology check très court détecté : '{v}'")
        return v

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
    message_metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict, 
        description="Métadonnées optionnelles (ex: intention détectée)"
    )


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
    
    # Le dictionnaire peut contenir la clé 'tutor_feedback' qui suivra 
    # la structure TutorFeedback définie plus haut.
    message_metadata: Optional[Dict[str, Any]] = None

    class Config:
        """
        Permet la conversion automatique depuis un objet SQLAlchemy.
        """
        from_attributes = True

logger.info("✅ Schémas ChatMessage (et TutorFeedback) chargés avec succès.")