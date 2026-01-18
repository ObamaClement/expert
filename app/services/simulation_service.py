from sqlalchemy.orm import Session
from uuid import UUID
from typing import Optional

from .. import models, schemas

def create_session(
    db: Session, 
    learner_id: int, 
    case_id: int, 
    session_type: str
) -> models.SimulationSession:
    """
    Crée un nouvel enregistrement de session de simulation dans la base de données.

    Args:
        db: La session de base de données.
        learner_id: L'ID de l'apprenant.
        case_id: L'ID du cas clinique sélectionné pour cette session.
        session_type: Le type de session (ex: 'test', 'formative', 'sommative').

    Returns:
        L'objet SimulationSession qui vient d'être créé.
    """
    # On crée une instance du modèle SQLAlchemy
    # L'ID UUID sera généré automatiquement par la base de données grâce au 'default'
    db_session = models.SimulationSession(
        learner_id=learner_id,
        cas_clinique_id=case_id,
        statut="in_progress",  # Le statut initial est toujours "en cours"
        # Nous stockons des informations contextuelles importantes dans le JSON
        # pour un usage futur par le tuteur.
        context_state={"session_type": session_type, "dialogue": []}
    )

    db.add(db_session)
    db.commit()
    db.refresh(db_session) # Pour récupérer l'ID et autres valeurs par défaut de la BDD

    return db_session


def get_session_by_id(db: Session, session_id: UUID) -> Optional[models.SimulationSession]:
    """
    Récupère une session de simulation par son ID.
    (Nous en aurons besoin pour les prochaines étapes).
    """
    return db.query(models.SimulationSession).filter(models.SimulationSession.id == session_id).first()

# D'autres fonctions (update_session, add_log_to_session, etc.) seront ajoutées ici plus tard.