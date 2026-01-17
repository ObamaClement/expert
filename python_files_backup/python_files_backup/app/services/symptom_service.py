from sqlalchemy.orm import Session
from typing import List, Optional

from .. import models, schemas
from ..utils.exceptions import NotFoundException # Nous créerons ce fichier plus tard


def get_symptom_by_id(db: Session, symptom_id: int) -> Optional[models.Symptom]:
    """
    Récupère un symptôme par son ID.
    """
    return db.query(models.Symptom).filter(models.Symptom.id == symptom_id).first()


def get_symptom_by_name(db: Session, name: str) -> Optional[models.Symptom]:
    """
    Récupère un symptôme par son nom.
    """
    return db.query(models.Symptom).filter(models.Symptom.nom == name).first()


def get_all_symptoms(db: Session, skip: int = 0, limit: int = 100) -> List[models.Symptom]:
    """
    Récupère une liste de tous les symptômes avec pagination.
    """
    return db.query(models.Symptom).offset(skip).limit(limit).all()


def create_symptom(db: Session, symptom: schemas.SymptomCreate) -> models.Symptom:
    """
    Crée un nouveau symptôme dans la base de données.
    
    Prend un schéma Pydantic 'SymptomCreate' en entrée, le convertit en
    modèle SQLAlchemy 'Symptom' et l'ajoute à la base de données.
    """
    # Convertit le schéma Pydantic en dictionnaire
    symptom_data = symptom.model_dump()
    
    # Crée une instance du modèle SQLAlchemy
    db_symptom = models.Symptom(**symptom_data)
    
    # Ajoute l'instance à la session de la base de données
    db.add(db_symptom)
    # Valide la transaction pour l'écrire en base
    db.commit()
    # Rafraîchit l'instance pour obtenir les valeurs générées par la BDD (comme l'ID)
    db.refresh(db_symptom)
    
    return db_symptom


def update_symptom(db: Session, symptom_id: int, symptom_update: schemas.SymptomUpdate) -> Optional[models.Symptom]:
    """
    Met à jour un symptôme existant.
    """
    db_symptom = get_symptom_by_id(db, symptom_id)
    if not db_symptom:
        # Plus tard, nous lèverons une exception personnalisée
        # raise NotFoundException(detail=f"Symptom with id {symptom_id} not found")
        return None

    # Convertit le schéma Pydantic en dictionnaire, en excluant les valeurs non définies
    update_data = symptom_update.model_dump(exclude_unset=True)
    
    for key, value in update_data.items():
        setattr(db_symptom, key, value)
        
    db.commit()
    db.refresh(db_symptom)
    
    return db_symptom


def delete_symptom(db: Session, symptom_id: int) -> Optional[models.Symptom]:
    """
    Supprime un symptôme de la base de données.
    """
    db_symptom = get_symptom_by_id(db, symptom_id)
    if not db_symptom:
        # raise NotFoundException(detail=f"Symptom with id {symptom_id} not found")
        return None

    db.delete(db_symptom)
    db.commit()
    
    return db_symptom

def get_diseases_for_symptom(db: Session, symptom_id: int) -> List[models.PathologieSymptome]:
    """
    Récupère toutes les pathologies associées à un symptôme (diagnostic différentiel).
    """
    return db.query(models.PathologieSymptome).filter(models.PathologieSymptome.symptome_id == symptom_id).all()





def add_treatment_to_symptom(db: Session, association_data: schemas.relations.TraitementSymptomeCreate) -> models.TraitementSymptome:
    """
    Associe un médicament à un symptôme en tant que traitement symptomatique.
    """
    db_symptom = get_symptom_by_id(db, symptom_id=association_data.symptome_id)
    from . import medication_service
    db_medication = medication_service.get_medication_by_id(db, medication_id=association_data.medicament_id)

    if not db_symptom or not db_medication:
        raise ValueError("Symptôme ou Médicament non trouvé.")

    association = models.TraitementSymptome(**association_data.model_dump())
    
    db.add(association)
    db.commit()
    db.refresh(association)
    
    return association


def get_treatments_for_symptom(db: Session, symptom_id: int) -> List[models.TraitementSymptome]:
    """
    Récupère tous les traitements associés à un symptôme.
    """
    return db.query(models.TraitementSymptome).filter(models.TraitementSymptome.symptome_id == symptom_id).all()