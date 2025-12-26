from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from ... import schemas, models
from ...services import expert_strategy_service
from ...dependencies import get_db

router = APIRouter(
    prefix="/expert-strategies",
    tags=["Expert Strategies"]
)


@router.post("/", response_model=schemas.expert_strategy.ExpertStrategy, status_code=status.HTTP_201_CREATED)
def create_expert_strategy(strategy_data: schemas.expert_strategy.ExpertStrategyCreate, db: Session = Depends(get_db)):
    """
    Crée une nouvelle règle/stratégie experte.
    """
    db_strategy = expert_strategy_service.get_strategy_by_code(db, code=strategy_data.code_regle)
    if db_strategy:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Une règle avec le code '{strategy_data.code_regle}' existe déjà."
        )
    return expert_strategy_service.create_strategy(db=db, strategy=strategy_data)


@router.get("/", response_model=List[schemas.expert_strategy.ExpertStrategy])
def read_all_expert_strategies(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    Récupère une liste de toutes les règles expertes.
    """
    strategies = expert_strategy_service.get_all_strategies(db, skip=skip, limit=limit)
    return strategies


@router.get("/{strategy_id}", response_model=schemas.expert_strategy.ExpertStrategy)
def read_expert_strategy(strategy_id: int, db: Session = Depends(get_db)):
    """
    Récupère une règle experte par son ID.
    """
    db_strategy = expert_strategy_service.get_strategy_by_id(db, strategy_id=strategy_id)
    if db_strategy is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Règle non trouvée.")
    return db_strategy


@router.patch("/{strategy_id}", response_model=schemas.expert_strategy.ExpertStrategy)
def update_expert_strategy(strategy_id: int, strategy_data: schemas.expert_strategy.ExpertStrategyUpdate, db: Session = Depends(get_db)):
    """
    Met à jour une règle experte.
    """
    db_strategy = expert_strategy_service.update_strategy(db, strategy_id=strategy_id, strategy_update=strategy_data)
    if db_strategy is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Règle non trouvée.")
    return db_strategy


@router.delete("/{strategy_id}", response_model=schemas.expert_strategy.ExpertStrategy)
def delete_expert_strategy(strategy_id: int, db: Session = Depends(get_db)):
    """
    Supprime une règle experte.
    """
    db_strategy = expert_strategy_service.delete_strategy(db, strategy_id=strategy_id)
    if db_strategy is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Règle non trouvée.")
    return db_strategy