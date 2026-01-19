#=== Fichier: ./app/services/chat_service.py ===

import logging
import time
import uuid
import json
from typing import List, Optional
from uuid import UUID
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from .. import models, schemas
from .patient_actor_service import patient_actor_service

# ==============================================================================
# CONFIGURATION DU LOGGER "CHAT"
# ==============================================================================
logger = logging.getLogger("chat_service")
logger.setLevel(logging.DEBUG)

if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - [CHAT-SVC] - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

def create_chat_message(db: Session, session_id: UUID, message: schemas.ChatMessageCreate) -> models.ChatMessage:
    """
    Crée un message dans le chat et, si l'expéditeur est l'étudiant, 
    déclenche la réponse automatique du Patient Actor.
    
    Cette fonction est le "Chef d'Orchestre" du dialogue.
    """
    request_id = str(uuid.uuid4())[:8]
    start_total = time.time()
    
    logger.info(f"📨 [REQ-{request_id}] Nouvelle demande de message pour Session {session_id}")
    logger.debug(f"   [REQ-{request_id}] Données brutes reçues : {message.model_dump()}")

    # 1. Validation Préalable de la Session
    # -------------------------------------------------------------------------
    try:
        logger.debug(f"   [REQ-{request_id}] Vérification existence session...")
        db_session = db.query(models.SimulationSession).filter(
            models.SimulationSession.id == session_id
        ).first()

        if not db_session:
            logger.error(f"   ❌ [REQ-{request_id}] Session introuvable UUID={session_id}")
            raise ValueError(f"La session avec l'ID {session_id} n'a pas été trouvée.")
        
        # Vérification si la session est terminée (optionnel, selon règles métier)
        if db_session.statut in ["completed", "abandoned"]:
            logger.warning(f"   ⚠️ [REQ-{request_id}] Tentative d'écriture dans une session terminée ({db_session.statut})")
            # On laisse passer pour l'instant, mais on logue le warning.

    except SQLAlchemyError as e:
        logger.critical(f"   ❌ [REQ-{request_id}] Erreur DB lors de la vérification session : {str(e)}")
        raise e

    # 2. Persistance du Message de l'Apprenant (USER)
    # -------------------------------------------------------------------------
    learner_msg_obj = None
    try:
        logger.info(f"   💾 [REQ-{request_id}] Enregistrement message APPRENANT...")
        
        learner_msg_obj = models.ChatMessage(
            session_id=session_id,
            sender=message.sender,
            content=message.content,
            message_metadata=message.message_metadata or {},
            timestamp=datetime.now()
        )
        
        db.add(learner_msg_obj)
        db.commit()
        db.refresh(learner_msg_obj)
        
        logger.info(f"   ✅ [REQ-{request_id}] Message Apprenant sauvegardé (ID: {learner_msg_obj.id})")

    except Exception as e:
        db.rollback()
        logger.error(f"   ❌ [REQ-{request_id}] Échec sauvegarde message apprenant : {str(e)}")
        raise e

    # 3. Déclenchement du Patient Actor (IA)
    # -------------------------------------------------------------------------
    # On ne déclenche que si c'est un étudiant/apprenant qui parle.
    # Si c'est "System" ou "Tutor" ou déjà "Patient", on ne répond pas.
    
    AUTHORIZED_SENDERS_TRIGGER = ["student", "apprenant", "learner", "user"]
    sender_normalized = message.sender.lower().strip()
    
    if sender_normalized in AUTHORIZED_SENDERS_TRIGGER:
        logger.info(f"   🎭 [REQ-{request_id}] Déclenchement du PATIENT ACTOR requis (Sender='{message.sender}')")
        
        try:
            # Appel synchrone au service Patient Actor
            # Note : Cela peut prendre 2 à 10 secondes selon le LLM.
            actor_start = time.time()
            
            logger.debug(f"   [REQ-{request_id}] >> Passage de relais au PatientActorService...")
            
            patient_response_text = patient_actor_service.generate_response(
                db=db,
                session_id=session_id,
                student_message=message.content
            )
            
            actor_duration = time.time() - actor_start
            logger.debug(f"   [REQ-{request_id}] << Retour du PatientActorService ({actor_duration:.2f}s)")
            
            if not patient_response_text:
                logger.warning(f"   ⚠️ [REQ-{request_id}] Le Patient Actor a renvoyé une réponse vide.")
                patient_response_text = "..."

            # 4. Persistance de la Réponse du Patient (AI)
            # ---------------------------------------------------------------------
            logger.info(f"   💾 [REQ-{request_id}] Enregistrement réponse PATIENT...")
            
            patient_msg_obj = models.ChatMessage(
                session_id=session_id,
                sender="Patient", # Expéditeur normalisé
                content=patient_response_text,
                message_metadata={
                    "generated_by": "PatientActorService",
                    "model": "LLM", 
                    "reply_to": learner_msg_obj.id,
                    "processing_time": f"{actor_duration:.2f}s"
                },
                timestamp=datetime.now()
            )
            
            db.add(patient_msg_obj)
            db.commit()
            db.refresh(patient_msg_obj)
            
            logger.info(f"   ✅ [REQ-{request_id}] Réponse Patient sauvegardée (ID: {patient_msg_obj.id})")

        except Exception as e:
            # Si l'IA plante, on ne veut pas faire échouer la requête HTTP de l'étudiant.
            # Son message a déjà été enregistré à l'étape 2.
            # On logue l'erreur critique mais on continue.
            logger.critical(f"   ❌ [REQ-{request_id}] CRASH PATIENT ACTOR : {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            
            # Optionnel : Insérer un message système d'erreur dans le chat ?
            # Pour l'instant, on laisse silencieux pour ne pas briser l'immersion,
            # ou on pourrait mettre un message "Le patient ne semble pas vous entendre..."
    else:
        logger.info(f"   zzz [REQ-{request_id}] Pas de déclenchement IA (Sender '{message.sender}' ignoré)")

    total_duration = time.time() - start_total
    logger.info(f"🏁 [REQ-{request_id}] Traitement message terminé en {total_duration:.2f}s")
    
    # On retourne l'objet message INITIAL (celui de l'utilisateur), 
    # car c'est la réponse REST standard à un POST.
    # Le frontend devra rafraîchir (GET) pour voir la réponse du patient.
    return learner_msg_obj


def get_messages_by_session(db: Session, session_id: UUID) -> List[models.ChatMessage]:
    """
    Récupère l'historique complet des messages pour une session.
    Trié par ordre chronologique croissant (du plus vieux au plus récent).
    """
    start = time.time()
    request_id = str(uuid.uuid4())[:4]
    
    logger.debug(f"📜 [HIST-{request_id}] Récupération historique Session {session_id}")
    
    try:
        messages = db.query(models.ChatMessage).filter(
            models.ChatMessage.session_id == session_id
        ).order_by(models.ChatMessage.timestamp.asc()).all()
        
        duration = time.time() - start
        
        # Logs statistiques
        count_student = sum(1 for m in messages if m.sender in ["Apprenant", "Student", "student"])
        count_patient = sum(1 for m in messages if m.sender == "Patient")
        count_system = len(messages) - count_student - count_patient
        
        logger.info(f"   ✅ [HIST-{request_id}] {len(messages)} messages trouvés ({duration:.3f}s)")
        logger.debug(f"      - Apprenant : {count_student}")
        logger.debug(f"      - Patient   : {count_patient}")
        logger.debug(f"      - Système   : {count_system}")
        
        return messages
        
    except SQLAlchemyError as e:
        logger.error(f"   ❌ [HIST-{request_id}] Erreur DB lecture historique : {str(e)}")
        raise e