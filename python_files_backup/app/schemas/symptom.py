from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

# ==============================================================================
# Schéma de Base
# ==============================================================================
class SymptomBase(BaseModel):
    """
    Schéma de base pour un symptôme.
    Contient les champs communs à la création et à la lecture.
    """
    nom: str
    nom_local: Optional[str] = None
    categorie: Optional[str] = None
    type_symptome: Optional[str] = None
    description: Optional[str] = None
    questions_anamnese: Optional[Dict[str, Any]] = None
    signes_alarme: bool = False


# ==============================================================================
# Schéma pour la Création (ce que l'API attend dans un POST)
# ==============================================================================
class SymptomCreate(SymptomBase):
    """
    Schéma utilisé pour créer un nouveau symptôme via l'API.
    Hérite de SymptomBase et n'ajoute aucun champ supplémentaire pour l'instant.
    """
    pass


# ==============================================================================
# Schéma pour la Mise à Jour (ce que l'API attend dans un PATCH)
# ==============================================================================
class SymptomUpdate(BaseModel):
    """
    Schéma utilisé pour mettre à jour un symptôme existant.
    Tous les champs sont optionnels pour permettre des mises à jour partielles.
    """
    nom: Optional[str] = None
    nom_local: Optional[str] = None
    categorie: Optional[str] = None
    type_symptome: Optional[str] = None
    description: Optional[str] = None
    questions_anamnese: Optional[Dict[str, Any]] = None
    signes_alarme: Optional[bool] = None


# ==============================================================================
# Schéma pour la Lecture (ce que l'API renvoie)
# ==============================================================================
class Symptom(SymptomBase):
    """
    Schéma complet pour représenter un symptôme, y compris les champs
    générés par la base de données comme 'id' et 'created_at'.
    Ce sera le modèle de réponse de l'API.
    """
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        """
        Configuration pour Pydantic.
        'from_attributes = True' (anciennement 'orm_mode') permet au modèle Pydantic
        de lire les données directement depuis un objet SQLAlchemy.
        C'est le lien magique entre notre modèle de BDD et notre schéma d'API.
        """
        from_attributes = True