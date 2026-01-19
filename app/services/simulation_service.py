import logging
from sqlalchemy.orm import Session
from uuid import UUID
from typing import Optional, List, Dict, Any
import json

from .. import models

logger = logging.getLogger(__name__)

def create_session(
    db: Session, 
    learner_id: int, 
    case_id: int, 
    session_type: str,
    formative_count: int = 0,
    formative_cases_pool: List[int] = None
) -> models.SimulationSession:
    """
    Crée un nouvel enregistrement de session de simulation dans la base de données.
    """
    logger.info(f"🔨 [SESSION-FACTORY] Création session...")
    logger.info(f"   - Learner: {learner_id}")
    logger.info(f"   - Case: {case_id}")
    logger.info(f"   - Type: {session_type}")
    logger.info(f"   - Count: {formative_count}")
    
    # Sécurisation de la liste pour le JSON
    # On s'assure que c'est une liste d'entiers valide, même vide
    pool = formative_cases_pool if formative_cases_pool is not None else []
    logger.info(f"   - Pool (raw): {pool}")
    
    # Construction du contexte de session
    # On force la sérialisation JSON explicite pour éviter les ambiguïtés SQLAlchemy
    context = {
        "session_type": session_type,
        "formative_count_since_eval": int(formative_count), # Force int
        "dialogue": [],
        "formative_cases_pool": pool
    }
    
    try:
        # Création de l'instance du modèle SQLAlchemy
        db_session = models.SimulationSession(
            learner_id=learner_id,
            cas_clinique_id=case_id,
            statut="in_progress",
            # SQLAlchemy gère normalement la conversion dict -> JSONB/JSON
            # Mais si ça plante, c'est souvent ici.
            context_state=context 
        )

        db.add(db_session)
        db.commit()
        db.refresh(db_session)

        logger.info(f"   ✅ [CREATED] Session ID: {db_session.id}")
        return db_session
        
    except Exception as e:
        logger.error(f"   ❌ [ERROR] Erreur lors de la création en BDD: {str(e)}")
        import traceback
        logger.error(traceback.format_exc()) # Traceback complet pour le debug
        db.rollback()
        raise e


def get_session_by_id(db: Session, session_id: UUID) -> Optional[models.SimulationSession]:
    """
    Récupère une session de simulation par son ID.
    """
    return db.query(models.SimulationSession).filter(
        models.SimulationSession.id == session_id
    ).first()


def update_session_status(
    db: Session, 
    session_id: UUID, 
    new_status: str, 
    score: float = None
) -> models.SimulationSession:
    """
    Met à jour le statut d'une session et optionnellement son score.
    """
    session = get_session_by_id(db, session_id)
    if not session:
        raise ValueError(f"Session {session_id} introuvable.")
    
    session.statut = new_status
    if score is not None:
        session.score_final = score
    
    db.commit()
    db.refresh(session)
    
    return session