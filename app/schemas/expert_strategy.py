from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from decimal import Decimal

# ==============================================================================
# Schéma de Base
# ==============================================================================
class ExpertStrategyBase(BaseModel):
    """
    Schéma de base pour une règle/stratégie experte.
    """
    code_regle: str = Field(..., max_length=50)
    categorie: str
    priorite: int = Field(default=5, ge=1, le=10)
    conditions: Dict[str, Any]
    actions: List[Dict[str, Any]]
    description_naturelle: Optional[str] = None
    justification_medicale: Optional[str] = None
    expert_auteur: Optional[str] = None
    date_validation: Optional[date] = None
    est_active: bool = True


# ==============================================================================
# Schéma pour la Création
# ==============================================================================
class ExpertStrategyCreate(ExpertStrategyBase):
    """
    Schéma utilisé pour créer une nouvelle règle.
    """
    pass


# ==============================================================================
# Schéma pour la Mise à Jour
# ==============================================================================
class ExpertStrategyUpdate(BaseModel):
    """
    Schéma pour la mise à jour partielle d'une règle.
    """
    code_regle: Optional[str] = Field(None, max_length=50)
    categorie: Optional[str] = None
    priorite: Optional[int] = Field(None, ge=1, le=10)
    conditions: Optional[Dict[str, Any]] = None
    actions: Optional[List[Dict[str, Any]]] = None
    description_naturelle: Optional[str] = None
    justification_medicale: Optional[str] = None
    expert_auteur: Optional[str] = None
    date_validation: Optional[date] = None
    est_active: Optional[bool] = None


# ==============================================================================
# Schéma pour la Lecture (Réponse API)
# ==============================================================================
class ExpertStrategy(ExpertStrategyBase):
    """
    Schéma complet pour représenter une règle en réponse d'API.
    """
    id: int
    nb_activations: int
    taux_succes: Optional[Decimal] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True