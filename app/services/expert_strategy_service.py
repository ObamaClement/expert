from sqlalchemy.orm import Session
from typing import List, Optional

from .. import models, schemas

def get_strategy_by_id(db: Session, strategy_id: int) -> Optional[models.ExpertStrategy]:
    """
    Récupère une règle par son ID.
    """
    return db.query(models.ExpertStrategy).filter(models.ExpertStrategy.id == strategy_id).first()

def get_strategy_by_code(db: Session, code: str) -> Optional[models.ExpertStrategy]:
    """
    Récupère une règle par son code unique.
    """
    return db.query(models.ExpertStrategy).filter(models.ExpertStrategy.code_regle == code).first()

def get_all_strategies(db: Session, skip: int = 0, limit: int = 100) -> List[models.ExpertStrategy]:
    """
    Récupère une liste de toutes les règles avec pagination.
    """
    return db.query(models.ExpertStrategy).offset(skip).limit(limit).all()

def get_active_strategies_by_category(db: Session, category: str) -> List[models.ExpertStrategy]:
    """
    Récupère toutes les règles actives pour une catégorie donnée, triées par priorité.
    Cette fonction sera très utile pour le moteur de raisonnement.
    """
    return db.query(models.ExpertStrategy).filter(
        models.ExpertStrategy.categorie == category,
        models.ExpertStrategy.est_active == True
    ).order_by(models.ExpertStrategy.priorite.desc()).all()


def create_strategy(db: Session, strategy: schemas.ExpertStrategyCreate) -> models.ExpertStrategy:
    """
    Crée une nouvelle règle dans la base de données.
    """
    strategy_data = strategy.model_dump()
    db_strategy = models.ExpertStrategy(**strategy_data)
    
    db.add(db_strategy)
    db.commit()
    db.refresh(db_strategy)
    
    return db_strategy

def update_strategy(db: Session, strategy_id: int, strategy_update: schemas.ExpertStrategyUpdate) -> Optional[models.ExpertStrategy]:
    """
    Met à jour une règle existante.
    """
    db_strategy = get_strategy_by_id(db, strategy_id)
    if not db_strategy:
        return None

    update_data = strategy_update.model_dump(exclude_unset=True)
    
    for key, value in update_data.items():
        setattr(db_strategy, key, value)
        
    db.commit()
    db.refresh(db_strategy)
    
    return db_strategy

def delete_strategy(db: Session, strategy_id: int) -> Optional[models.ExpertStrategy]:
    """
    Supprime une règle de la base de données.
    """
    db_strategy = get_strategy_by_id(db, strategy_id)
    if not db_strategy:
        return None

    db.delete(db_strategy)
    db.commit()
    
    return db_strategy