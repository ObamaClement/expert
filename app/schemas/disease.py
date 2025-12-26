from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal

# ==============================================================================
# Schéma de Base
# ==============================================================================
class DiseaseBase(BaseModel):
    """
    Schéma de base pour une pathologie, contenant les champs modifiables.
    """
    nom_fr: str
    code_icd10: str
    nom_en: Optional[str] = None
    nom_local: Optional[str] = None
    categorie: Optional[str] = None
    prevalence_cameroun: Optional[Decimal] = Field(None, ge=0, le=100)
    niveau_gravite: Optional[int] = Field(None, ge=1, le=5)
    description: Optional[str] = None
    physiopathologie: Optional[str] = None
    evolution_naturelle: Optional[str] = None
    complications: Optional[Dict[str, Any]] = None
    facteurs_risque: Optional[Dict[str, Any]] = None
    prevention: Optional[str] = None


# ==============================================================================
# Schéma pour la Création (ce que l'API attend dans un POST)
# ==============================================================================
class DiseaseCreate(DiseaseBase):
    """
    Schéma utilisé pour créer une nouvelle pathologie.
    """
    pass


# ==============================================================================
# Schéma pour la Mise à Jour (ce que l'API attend dans un PATCH)
# ==============================================================================
class DiseaseUpdate(BaseModel):
    """
    Schéma pour la mise à jour partielle d'une pathologie.
    Tous les champs sont optionnels.
    """
    nom_fr: Optional[str] = None
    code_icd10: Optional[str] = None
    nom_en: Optional[str] = None
    nom_local: Optional[str] = None
    categorie: Optional[str] = None
    prevalence_cameroun: Optional[Decimal] = Field(None, ge=0, le=100)
    niveau_gravite: Optional[int] = Field(None, ge=1, le=5)
    description: Optional[str] = None
    physiopathologie: Optional[str] = None
    evolution_naturelle: Optional[str] = None
    complications: Optional[Dict[str, Any]] = None
    facteurs_risque: Optional[Dict[str, Any]] = None
    prevention: Optional[str] = None


# ==============================================================================
# Schéma pour la Lecture (ce que l'API renvoie)
# ==============================================================================
class Disease(DiseaseBase):
    """
    Schéma complet pour représenter une pathologie en réponse d'API.
    Inclut les champs non modifiables comme 'id' et les horodatages.
    """
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        """
        Permet la conversion automatique depuis un objet SQLAlchemy.
        """
        from_attributes = True