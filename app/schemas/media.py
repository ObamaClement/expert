from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, date

# ==============================================================================
# Schéma de Base pour les Métadonnées d'une Image
# ==============================================================================
class ImageMedicaleBase(BaseModel):
    """
    Schéma de base contenant les métadonnées modifiables d'une image médicale.
    """
    type_examen: str
    sous_type: Optional[str] = None
    pathologie_id: Optional[int] = None
    description: Optional[str] = None
    signes_radiologiques: Optional[Dict[str, Any]] = None
    annotations: Optional[List[Dict[str, Any]]] = None
    interpretation_experte: Optional[str] = None
    diagnostic_differentiel: Optional[List[str]] = None
    niveau_difficulte: Optional[int] = Field(None, ge=1, le=5)
    qualite_image: Optional[int] = Field(None, ge=1, le=5)
    valide_expert: Optional[bool] = False
    expert_validateur: Optional[str] = None
    date_validation: Optional[date] = None


# ==============================================================================
# Schéma pour la Mise à Jour des Métadonnées
# ==============================================================================
class ImageMedicaleUpdate(BaseModel):
    """
    Schéma pour la mise à jour partielle des métadonnées d'une image.
    Tous les champs sont optionnels.
    """
    type_examen: Optional[str] = None
    sous_type: Optional[str] = None
    pathologie_id: Optional[int] = None
    description: Optional[str] = None
    signes_radiologiques: Optional[Dict[str, Any]] = None
    annotations: Optional[List[Dict[str, Any]]] = None
    interpretation_experte: Optional[str] = None
    diagnostic_differentiel: Optional[List[str]] = None
    niveau_difficulte: Optional[int] = Field(None, ge=1, le=5)
    qualite_image: Optional[int] = Field(None, ge=1, le=5)
    valide_expert: Optional[bool] = None
    expert_validateur: Optional[str] = None
    date_validation: Optional[date] = None


# ==============================================================================
# Schéma pour la Lecture (Réponse API)
# ==============================================================================
class ImageMedicale(ImageMedicaleBase):
    """
    Schéma complet pour représenter les métadonnées d'une image en réponse d'API.
    """
    id: int
    fichier_url: str
    fichier_miniature_url: Optional[str] = None
    format_image: Optional[str] = None
    taille_ko: Optional[int] = None
    resolution: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

# Nous ajouterons les schémas pour SonMedical ici plus tard.