#=== Fichier: ./app/services/chat_service.py ===

import logging
import time
import uuid
import json
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from .. import models, schemas
# Services dépendants
from .patient_actor_service import patient_actor_service
from . import ai_generation_service  # <-- Le service Intelligence qu'on vient de modifier

# ==============================================================================
# CONFIGURATION DU LOGGER "CHAT-ORCHESTRATOR"
# ==============================================================================
logger = logging.getLogger("chat_orchestrator")
logger.setLevel(logging.DEBUG)

if not logger.handlers:
    handler = logging.StreamHandler()
    # Format ultra-détaillé pour le debugging de production
    formatter = logging.Formatter(
        '%(asctime)s - [CHAT-CORE] - %(levelname)s - [Trace: %(trace_id)s] - %(message)s'
    )
    
    # Filtre pour injecter trace_id par défaut si absent (évite les crashs de log)
    class ContextFilter(logging.Filter):
        def filter(self, record):
            if not hasattr(record, 'trace_id'):
                record.trace_id = 'SYSTEM'
            return True
    
    handler.addFilter(ContextFilter())
    handler.setFormatter(formatter)
    logger.addHandler(handler)

# ==============================================================================
# CONSTANTES
# ==============================================================================
AUTHORIZED_SENDERS_TRIGGER = ["student", "apprenant", "learner", "user"]

def create_chat_message(
    db: Session, 
    session_id: UUID, 
    message: schemas.ChatMessageCreate
) -> models.ChatMessage:
    """
    Orchestre le flux de conversation complet :
    1. Sauvegarde du message de l'Étudiant.
    2. Génération de la réponse du Patient (Patient Actor).
    3. Génération du feedback pédagogique (Tuteur AI).
    4. Sauvegarde de la réponse enrichie.
    
    Cette fonction est transactionnelle et résiliente : un échec du Tuteur
    ne doit pas empêcher la réponse du Patient.
    """
    # ID de traçabilité unique pour toute cette transaction
    trace_id = f"MSG-{str(uuid.uuid4())[:8].upper()}"
    start_total = time.time()
    
    # Injection du trace_id pour les logs
    log_extra = {'trace_id': trace_id}

    logger.info(f"📨 Nouvelle requête de message pour Session {session_id}", extra=log_extra)
    logger.debug(f"   Payload reçu : {json.dumps(message.model_dump(), ensure_ascii=False)}", extra=log_extra)

    # ==========================================================================
    # ÉTAPE 1 : VALIDATION ET CHARGEMENT DU CONTEXTE
    # ==========================================================================
    try:
        logger.debug("   🔍 Étape 1: Vérification session & chargement cas clinique...", extra=log_extra)
        
        # On charge la session ET le cas clinique en une fois (optimisation)
        db_session = db.query(models.SimulationSession).filter(
            models.SimulationSession.id == session_id
        ).first()

        if not db_session:
            logger.error(f"   ❌ Session introuvable UUID={session_id}", extra=log_extra)
            raise ValueError(f"La session avec l'ID {session_id} n'a pas été trouvée.")
        
        # On récupère le cas clinique car le Tuteur en aura besoin pour comparer à la "Vérité Terrain"
        clinical_case = db_session.cas_clinique
        if not clinical_case:
            logger.critical("   ⛔ Session trouvée mais aucun cas clinique associé ! Corruption de données.", extra=log_extra)
            raise ValueError("Erreur critique : Session sans cas clinique.")

        # Vérification statut session
        if db_session.statut in ["completed", "abandoned"]:
            logger.warning(f"   ⚠️ Écriture dans une session terminée ({db_session.statut})", extra=log_extra)

    except SQLAlchemyError as e:
        logger.critical(f"   🔥 Erreur DB critique lors de l'init : {str(e)}", extra=log_extra)
        raise e

    # ==========================================================================
    # ÉTAPE 2 : PERSISTANCE DU MESSAGE APPRENANT
    # ==========================================================================
    learner_msg_obj = None
    try:
        logger.info("   💾 Étape 2: Sauvegarde message APPRENANT...", extra=log_extra)
        
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
        
        logger.info(f"   ✅ Message Apprenant sauvegardé (ID: {learner_msg_obj.id})", extra=log_extra)

    except Exception as e:
        db.rollback()
        logger.error(f"   ❌ Échec sauvegarde message apprenant : {str(e)}", extra=log_extra)
        raise e

    # ==========================================================================
    # ÉTAPE 3 : DÉCLENCHEMENT DE L'INTELLIGENCE ARTIFICIELLE
    # ==========================================================================
    sender_normalized = message.sender.lower().strip()
    
    # On ne répond que si c'est un humain qui parle
    if sender_normalized in AUTHORIZED_SENDERS_TRIGGER:
        logger.info(f"   🤖 Déclenchement Pipeline IA (Sender='{message.sender}')...", extra=log_extra)
        
        # --- 3.A : GÉNÉRATION RÉPONSE PATIENT (ACTOR) ---
        patient_response_text = "..."
        actor_duration = 0.0
        
        try:
            actor_start = time.time()
            logger.debug("   [IA-1] Appel au PatientActorService...", extra=log_extra)
            
            patient_response_text = patient_actor_service.generate_response(
                db=db,
                session_id=session_id,
                student_message=message.content
            )
            
            actor_duration = time.time() - actor_start
            logger.info(f"   ✅ [IA-1] Patient a répondu en {actor_duration:.2f}s", extra=log_extra)
            logger.debug(f"      Contenu : '{patient_response_text[:50]}...'", extra=log_extra)

        except Exception as e:
            logger.critical(f"   🔥 [IA-1] CRASH PATIENT ACTOR : {str(e)}", extra=log_extra)
            import traceback
            logger.error(traceback.format_exc())
            patient_response_text = "(Le patient semble confus et ne répond pas...)"

        # --- 3.B : ANALYSE PÉDAGOGIQUE (TUTEUR) ---
        # C'est ici que la magie opère. On analyse la paire (Question Étudiant / Réponse Patient)
        tutor_feedback_data = {}
        tutor_duration = 0.0
        
        try:
            tutor_start = time.time()
            logger.debug("   [IA-2] Appel au AiGenerationService (Module Tuteur)...", extra=log_extra)
            
            # On a besoin de l'historique pour savoir à quelle étape on est (Début ? Fin ?)
            # Optimisation : On compte juste, pas besoin de charger tout le texte
            history_count = db.query(models.ChatMessage).filter(
                models.ChatMessage.session_id == session_id
            ).count()
            
            # Appel à la fonction qu'on a créée en Phase 3
            tutor_feedback_data = ai_generation_service.generate_pedagogical_feedback(
                case=clinical_case,
                student_msg=message.content,
                patient_msg=patient_response_text,
                chat_history_count=history_count
            )
            
            tutor_duration = time.time() - tutor_start
            
            if tutor_feedback_data:
                logger.info(f"   ✅ [IA-2] Tuteur a analysé en {tutor_duration:.2f}s", extra=log_extra)
            else:
                logger.warning(f"   ⚠️ [IA-2] Tuteur silencieux (pas de feedback généré)", extra=log_extra)

        except Exception as e:
            # IMPORTANT : Le crash du tuteur ne doit PAS bloquer la réponse du patient
            logger.error(f"   ❌ [IA-2] Erreur Tuteur (Non-bloquant) : {str(e)}", extra=log_extra)
            tutor_feedback_data = {}

        # ======================================================================
        # ÉTAPE 4 : ASSEMBLAGE ET PERSISTANCE FINALE
        # ======================================================================
        try:
            logger.info("   💾 Étape 4: Sauvegarde réponse PATIENT enrichie...", extra=log_extra)
            
            # Construction des métadonnées enrichies
            final_metadata = {
                "generated_by": "PatientActorService",
                "reply_to": learner_msg_obj.id,
                "latencies": {
                    "patient_actor": f"{actor_duration:.2f}s",
                    "tutor_analysis": f"{tutor_duration:.2f}s"
                },
                # C'est ici qu'on injecte le résultat du Tuteur !
                # Le frontend cherchera cette clé pour afficher la bulle.
                "tutor_feedback": tutor_feedback_data 
            }
            
            patient_msg_obj = models.ChatMessage(
                session_id=session_id,
                sender="Patient",
                content=patient_response_text,
                message_metadata=final_metadata,
                timestamp=datetime.now()
            )
            
            db.add(patient_msg_obj)
            db.commit()
            db.refresh(patient_msg_obj)
            
            logger.info(f"   ✅ Réponse Patient sauvegardée (ID: {patient_msg_obj.id})", extra=log_extra)
            
            # Log final de performance
            total_duration = time.time() - start_total
            logger.info(f"🏁 [REQ-FIN] Transaction terminée en {total_duration:.2f}s", extra=log_extra)
            logger.info(f"   (Patient: {actor_duration:.2f}s + Tuteur: {tutor_duration:.2f}s + Overhead: {total_duration - actor_duration - tutor_duration:.2f}s)", extra=log_extra)

        except Exception as e:
            db.rollback()
            logger.critical(f"   🔥 Erreur sauvegarde finale : {str(e)}", extra=log_extra)
            # Ici on ne relève pas l'erreur si le message étudiant est passé, 
            # mais idéalement il faudrait gérer une file de retry.
    
    else:
        logger.info(f"   zzz Pas de réponse IA requise (Sender '{message.sender}' ignoré)", extra=log_extra)

    # On retourne le message initial (REST standard), le client fera un GET pour voir la réponse
    return learner_msg_obj


def get_messages_by_session(db: Session, session_id: UUID) -> List[models.ChatMessage]:
    """
    Récupère l'historique complet des messages pour une session.
    """
    start = time.time()
    trace_id = f"HIST-{str(uuid.uuid4())[:4]}"
    log_extra = {'trace_id': trace_id}
    
    logger.debug(f"📜 Récupération historique Session {session_id}", extra=log_extra)
    
    try:
        messages = db.query(models.ChatMessage).filter(
            models.ChatMessage.session_id == session_id
        ).order_by(models.ChatMessage.timestamp.asc()).all()
        
        duration = time.time() - start
        
        # Stats rapides pour le log
        count_tutor_feedback = sum(1 for m in messages if m.message_metadata and "tutor_feedback" in m.message_metadata and m.message_metadata["tutor_feedback"])
        
        logger.info(f"   ✅ {len(messages)} messages trouvés ({duration:.3f}s)", extra=log_extra)
        logger.debug(f"      Dont {count_tutor_feedback} avec feedback tuteur actif.", extra=log_extra)
        
        return messages
        
    except SQLAlchemyError as e:
        logger.error(f"   ❌ Erreur DB lecture historique : {str(e)}", extra=log_extra)
        raise e