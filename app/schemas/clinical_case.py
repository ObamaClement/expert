from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from decimal import Decimal

# Importer les autres schémas pour les réponses imbriquées
from .disease import Disease
from .media import ImageMedicale
from .symptom import Symptom






# --- NOUVEAUX SOUS-SCHÉMAS ---
class SymptomInCase(BaseModel):
    symptome_id: int
    details: str # Ex: "Fièvre élevée (40°C) apparue brutalement il y a 48h"

class PresentationClinique(BaseModel):
    histoire_maladie: str
    symptomes_patient: List[SymptomInCase]
    antecedents: Optional[Dict[str, Any]] = None
# ==============================================================================
# Schéma de Base et de Création
# ==============================================================================
class ClinicalCaseBase(BaseModel):
    """
    Schéma de base pour un cas clinique, contenant les champs éditables.
    """
    code_fultang: str = Field(..., description="Identifiant unique (Fultang ou synthétique)")
    pathologie_principale_id: Optional[int] = None
    pathologies_secondaires_ids: Optional[List[int]] = []
    presentation_clinique: PresentationClinique
    donnees_paracliniques: Optional[Dict[str, Any]] = None
    evolution_patient: Optional[str] = None
    images_associees_ids: Optional[List[int]] = []
    sons_associes_ids: Optional[List[int]] = []
    medicaments_prescrits: Optional[List[Dict[str, Any]]] = []
    niveau_difficulte: int = Field(default=3, ge=1, le=5)
    duree_estimee_resolution_min: Optional[int] = None
    objectifs_apprentissage: Optional[List[str]] = []
    competences_requises: Optional[Dict[str, Any]] = {}


class ClinicalCaseCreate(ClinicalCaseBase):
    """
    Schéma utilisé pour créer un nouveau cas clinique via l'API.
    """
    pass


# ==============================================================================
# Schéma pour la Mise à Jour
# ==============================================================================
class ClinicalCaseUpdate(BaseModel):
    """
    Schéma pour la mise à jour partielle d'un cas clinique.
    """
    code_fultang: Optional[str] = None
    pathologie_principale_id: Optional[int] = None
    presentation_clinique: Optional[Dict[str, Any]] = None
    donnees_paracliniques: Optional[Dict[str, Any]] = None
    evolution_patient: Optional[str] = None
    images_associees_ids: Optional[List[int]] = None
    sons_associes_ids: Optional[List[int]] = None
    medicaments_prescrits: Optional[List[Dict[str, Any]]] = None
    niveau_difficulte: Optional[int] = Field(None, ge=1, le=5)
    duree_estimee_resolution_min: Optional[int] = None
    objectifs_apprentissage: Optional[List[str]] = None
    competences_requises: Optional[Dict[str, Any]] = None
    valide_expert: Optional[bool] = None
    expert_validateur: Optional[str] = None
    date_validation: Optional[date] = None


# ==============================================================================
# Schémas pour la Lecture (Réponse API)
# ==============================================================================
class ClinicalCaseSimple(BaseModel):
    """
    Schéma simplifié pour les listes de cas cliniques.
    """
    id: int
    code_fultang: str
    niveau_difficulte: int
    pathologie_principale: Optional[Disease] = None # Affiche l'objet maladie complet
    nb_images: int
    nb_sons: int

    class Config:
        from_attributes = True


# --- NOUVEAU SCHÉMA DE LECTURE ENRICHI ---
class SymptomDetailInCase(BaseModel):
    symptome: Symptom # L'objet symptôme complet
    details: str # Les détails spécifiques au cas

class PresentationCliniqueDetail(BaseModel):
    histoire_maladie: str
    symptomes_patient: List[SymptomDetailInCase]
    antecedents: Optional[Dict[str, Any]] = None


class ClinicalCase(ClinicalCaseBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    pathologie_principale: Optional[Disease] = None
    pathologies_secondaires: List[Disease] = [] # <- AJOUTER
    images_associees: List[ImageMedicale] = []
    
    # --- ENRICHISSEMENT DE LA PRÉSENTATION CLINIQUE ---
    presentation_clinique_detail: Optional[PresentationCliniqueDetail] = None

    class Config:
        from_attributes = True

