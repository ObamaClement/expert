from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from ... import schemas
from ...services import chat_service
from ...dependencies import get_db

router = APIRouter(
    prefix="/chat",
    tags=["Chat"]
)


@router.post("/sessions/{session_id}/messages", response_model=schemas.chat_message.ChatMessage, status_code=status.HTTP_201_CREATED)
def post_chat_message(
    session_id: UUID,
    message_data: schemas.chat_message.ChatMessageCreate,
    db: Session = Depends(get_db)
):
    """
    Poste un nouveau message dans le chat d'une session de simulation.
    
    C'est l'endpoint principal utilisé par le frontend pour envoyer les messages
    de l'étudiant, et par l'orchestrateur pour sauvegarder les réponses du
    patient virtuel ou du tuteur.
    """
    try:
        return chat_service.create_chat_message(db=db, session_id=session_id, message=message_data)
    except ValueError as e:
        # Le service lève une ValueError si la session n'existe pas.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/sessions/{session_id}/messages", response_model=List[schemas.chat_message.ChatMessage])
def get_chat_history(session_id: UUID, db: Session = Depends(get_db)):
    """
    Récupère l'historique complet des messages pour une session de simulation.
    
    Permet au frontend de reconstruire la conversation lors du chargement ou
    d'une reprise de session.
    """
    # Vérifier que la session existe pour donner une erreur 404 claire
    session = db.query(schemas.models.SimulationSession).filter(schemas.models.SimulationSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"La session avec l'ID {session_id} n'a pas été trouvée.")
        
    messages = chat_service.get_messages_by_session(db=db, session_id=session_id)
    return messages