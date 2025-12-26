from pydantic import BaseModel, Field
from typing import Any, Dict, Optional
from decimal import Decimal

# Importer les schémas de base pour l'affichage
from .symptom import Symptom
from .disease import Disease
from .medication import Medication


# ==============================================================================
# Schéma de Base et de Création pour l'Association
# ==============================================================================
class PathologieSymptomeBase(BaseModel):
    """
    Schéma de base pour l'association Pathologie-Symptôme.
    Contient les champs nécessaires pour créer ou mettre à jour le lien.
    """
    pathologie_id: int
    symptome_id: int
    probabilite: Optional[Decimal] = Field(None, ge=0, le=1)
    sensibilite: Optional[Decimal] = Field(None, ge=0, le=1)
    specificite: Optional[Decimal] = Field(None, ge=0, le=1)
    phase_maladie: Optional[str] = None
    frequence: Optional[str] = None
    est_pathognomonique: bool = False
    importance_diagnostique: Optional[int] = Field(None, ge=1, le=5)

class PathologieSymptomeCreate(PathologieSymptomeBase):
    """
    Schéma utilisé spécifiquement pour créer une nouvelle association.
    """
    pass


# ==============================================================================
# Schémas pour la Lecture (Réponse de l'API)
# ==============================================================================
class PathologieSymptome(PathologieSymptomeBase):
    """
    Schéma complet pour la réponse de l'API, incluant l'ID de l'association.
    """
    id: int

    class Config:
        from_attributes = True


class SymptomForDiseaseDetail(BaseModel):
    """
    Schéma pour afficher les détails d'un symptôme DANS le contexte d'une pathologie.
    """
    symptome: Symptom
    probabilite: Optional[Decimal]
    importance_diagnostique: Optional[int]
    est_pathognomonique: bool

    class Config:
        from_attributes = True


class DiseaseForSymptomDetail(BaseModel):
    """
    Schéma pour afficher les détails d'une pathologie DANS le contexte d'un symptôme
    (utile pour le diagnostic différentiel).
    """
    pathologie: Disease
    probabilite: Optional[Decimal]
    importance_diagnostique: Optional[int]

    class Config:
        from_attributes = True



# Contenu à AJOUTER à la fin de app/schemas/relations.py

# Importer le schéma de base pour l'affichage


# ==============================================================================
# Schémas pour l'Association Traitement-Pathologie
# ==============================================================================
class TraitementPathologieBase(BaseModel):
    pathologie_id: int
    medicament_id: int
    type_traitement: Optional[str] = None
    ligne_traitement: Optional[int] = None
    indication_precise: Optional[str] = None
    efficacite_taux: Optional[Decimal] = Field(None, ge=0, le=100)
    duree_traitement_jours: Optional[int] = None
    posologie_detaillee: Optional[Dict[str, Any]] = None
    niveau_preuve: Optional[str] = None
    guidelines_source: Optional[str] = None
    rang_preference: Optional[int] = 99

class TraitementPathologieCreate(TraitementPathologieBase):
    pass

class TraitementPathologie(TraitementPathologieBase):
    id: int
    class Config:
        from_attributes = True

class MedicationForDiseaseDetail(BaseModel):
    """
    Schéma pour afficher les détails d'un médicament DANS le contexte d'une pathologie.
    """
    medicament: Medication
    type_traitement: Optional[str]
    ligne_traitement: Optional[int]
    rang_preference: Optional[int]
    
    class Config:
        from_attributes = True

# ==============================================================================
# Schémas pour l'Association Traitement-Symptôme
# ==============================================================================
class TraitementSymptomeBase(BaseModel):
    symptome_id: int
    medicament_id: int
    efficacite: Optional[str] = None
    rapidite_action: Optional[str] = None
    posologie_recommandee: Optional[str] = None
    rang_preference: Optional[int] = 99

class TraitementSymptomeCreate(TraitementSymptomeBase):
    pass

class TraitementSymptome(TraitementSymptomeBase):
    id: int
    class Config:
        from_attributes = True

class MedicationForSymptomDetail(BaseModel):
    """
    Schéma pour afficher les détails d'un médicament DANS le contexte d'un symptôme.
    """
    medicament: Medication
    efficacite: Optional[str]
    rang_preference: Optional[int]

    class Config:
        from_attributes = True