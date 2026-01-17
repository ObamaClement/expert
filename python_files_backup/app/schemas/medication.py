from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime

# ==============================================================================
# Schéma de Base
# ==============================================================================
class MedicationBase(BaseModel):
    """
    Schéma de base pour un médicament, contenant les champs modifiables.
    """
    dci: str
    nom_commercial: Optional[str] = None
    classe_therapeutique: Optional[str] = None
    forme_galenique: Optional[str] = None
    dosage: Optional[str] = None
    voie_administration: Optional[str] = None
    mecanisme_action: Optional[str] = None
    indications: Optional[Dict[str, Any]] = None
    contre_indications: Optional[Dict[str, Any]] = None
    effets_secondaires: Optional[Dict[str, Any]] = None
    interactions_medicamenteuses: Optional[Dict[str, Any]] = None
    precautions_emploi: Optional[str] = None
    posologie_standard: Optional[Dict[str, Any]] = None
    disponibilite_cameroun: Optional[str] = None
    cout_moyen_fcfa: Optional[int] = None
    statut_prescription: Optional[str] = None


# ==============================================================================
# Schéma pour la Création
# ==============================================================================
class MedicationCreate(MedicationBase):
    """
    Schéma utilisé pour créer un nouveau médicament.
    'dci' est le seul champ strictement requis.
    """
    pass


# ==============================================================================
# Schéma pour la Mise à Jour
# ==============================================================================
class MedicationUpdate(BaseModel):
    """
    Schéma pour la mise à jour partielle d'un médicament.
    """
    dci: Optional[str] = None
    nom_commercial: Optional[str] = None
    classe_therapeutique: Optional[str] = None
    # ... (tous les autres champs de MedicationBase en optionnel)
    forme_galenique: Optional[str] = None
    dosage: Optional[str] = None
    voie_administration: Optional[str] = None
    mecanisme_action: Optional[str] = None
    indications: Optional[Dict[str, Any]] = None
    contre_indications: Optional[Dict[str, Any]] = None
    effets_secondaires: Optional[Dict[str, Any]] = None
    interactions_medicamenteuses: Optional[Dict[str, Any]] = None
    precautions_emploi: Optional[str] = None
    posologie_standard: Optional[Dict[str, Any]] = None
    disponibilite_cameroun: Optional[str] = None
    cout_moyen_fcfa: Optional[int] = None
    statut_prescription: Optional[str] = None


# ==============================================================================
# Schéma pour la Lecture (Réponse API)
# ==============================================================================
class Medication(MedicationBase):
    """
    Schéma complet pour représenter un médicament en réponse d'API.
    """
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True