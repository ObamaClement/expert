#=== Fichier: ./app/api/v1/chat.py ===

import logging
import time
import uuid
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from ... import schemas, models
from ...services import chat_service
from ...dependencies import get_db

# ==============================================================================
# CONFIGURATION DU LOGGER API
# ==============================================================================
logger = logging.getLogger("api_chat")
logger.setLevel(logging.DEBUG)

if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - [API-CHAT] - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

router = APIRouter(
    prefix="/chat",
    tags=["Chat"]
)

@router.post(
    "/sessions/{session_id}/messages", 
    response_model=schemas.chat_message.ChatMessage, 
    status_code=status.HTTP_201_CREATED
)
def post_chat_message(
    session_id: UUID,
    message_data: schemas.chat_message.ChatMessageCreate,
    db: Session = Depends(get_db)
):
    """
    Poste un nouveau message dans le chat d'une session de simulation.
    
    ATTENTION : Cet endpoint est synchrone et bloquant. 
    Si c'est un message de l'étudiant, il va déclencher le Patient Actor (IA).
    La réponse peut prendre quelques secondes.
    """
    # ID de requête pour corréler avec les logs des services
    req_id = str(uuid.uuid4())[:8]
    start_time = time.time()
    
    logger.info(f"📥 [REQ-{req_id}] POST /messages | Session: {session_id}")
    logger.debug(f"   [REQ-{req_id}] Payload: Sender='{message_data.sender}' | Content='{message_data.content[:50]}...'")

    try:
        # Appel au service (qui va orchestrer l'IA si nécessaire)
        new_message = chat_service.create_chat_message(
            db=db, 
            session_id=session_id, 
            message=message_data
        )
        
        duration = time.time() - start_time
        logger.info(f"   ✅ [REQ-{req_id}] Succès HTTP 201 | Durée totale: {duration:.2f}s | Msg ID: {new_message.id}")
        
        return new_message

    except ValueError as e:
        # Erreur fonctionnelle (ex: Session introuvable)
        logger.warning(f"   ⚠️ [REQ-{req_id}] Erreur 404 (Resource Not Found): {str(e)}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    
    except Exception as e:
        # Erreur technique (Bug code, Crash DB, Crash IA critique)
        logger.error(f"   ❌ [REQ-{req_id}] Erreur 500 (Internal Server Error): {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Erreur interne lors du traitement du message: {str(e)}"
        )

@router.get(
    "/sessions/{session_id}/messages", 
    response_model=List[schemas.chat_message.ChatMessage]
)
def get_chat_history(
    session_id: UUID, 
    db: Session = Depends(get_db)
):
    """
    Récupère l'historique complet des messages pour une session.
    Utilisé par le frontend pour rafraîchir la vue (polling) et voir si le patient a répondu.
    """
    req_id = str(uuid.uuid4())[:8]
    start_time = time.time()
    
    logger.debug(f"🔍 [REQ-{req_id}] GET /messages | Session: {session_id}")

    try:
        # Vérification pré-service pour un log API plus propre
        # (Bien que le service le fasse aussi, le faire ici permet de logger l'erreur HTTP correspondante)
        session = db.query(models.SimulationSession).filter(models.SimulationSession.id == session_id).first()
        if not session:
            logger.warning(f"   ⚠️ [REQ-{req_id}] Session introuvable.")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"La session {session_id} n'existe pas.")
        
        messages = chat_service.get_messages_by_session(db=db, session_id=session_id)
        
        duration = time.time() - start_time
        logger.info(f"   ✅ [REQ-{req_id}] Succès HTTP 200 | {len(messages)} messages récupérés | {duration:.3f}s")
        
        return messages

    except HTTPException:
        raise # On relance les exceptions HTTP créées au-dessus
    
    except Exception as e:
        logger.error(f"   ❌ [REQ-{req_id}] Erreur 500 récupération historique: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Impossible de récupérer l'historique."
        )