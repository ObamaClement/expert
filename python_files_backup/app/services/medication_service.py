from sqlalchemy.orm import Session
from typing import List, Optional

from .. import models, schemas

def get_medication_by_id(db: Session, medication_id: int) -> Optional[models.Medication]:
    """
    Récupère un médicament par son ID.
    """
    return db.query(models.Medication).filter(models.Medication.id == medication_id).first()

def get_medication_by_dci(db: Session, dci: str) -> Optional[models.Medication]:
    """
    Récupère un médicament par son DCI (Dénomination Commune Internationale).
    """
    return db.query(models.Medication).filter(models.Medication.dci == dci).first()

def get_all_medications(db: Session, skip: int = 0, limit: int = 100) -> List[models.Medication]:
    """
    Récupère une liste de tous les médicaments avec pagination.
    """
    return db.query(models.Medication).offset(skip).limit(limit).all()

def create_medication(db: Session, medication: schemas.MedicationCreate) -> models.Medication:
    """
    Crée un nouveau médicament dans la base de données.
    """
    medication_data = medication.model_dump()
    db_medication = models.Medication(**medication_data)
    
    db.add(db_medication)
    db.commit()
    db.refresh(db_medication)
    
    return db_medication

def update_medication(db: Session, medication_id: int, medication_update: schemas.MedicationUpdate) -> Optional[models.Medication]:
    """
    Met à jour un médicament existant.
    """
    db_medication = get_medication_by_id(db, medication_id)
    if not db_medication:
        return None

    update_data = medication_update.model_dump(exclude_unset=True)
    
    for key, value in update_data.items():
        setattr(db_medication, key, value)
        
    db.commit()
    db.refresh(db_medication)
    
    return db_medication

def delete_medication(db: Session, medication_id: int) -> Optional[models.Medication]:
    """
    Supprime un médicament de la base de données.
    """
    db_medication = get_medication_by_id(db, medication_id)
    if not db_medication:
        return None

    db.delete(db_medication)
    db.commit()
    
    return db_medication




# Contenu à AJOUTER à la fin de app/services/medication_service.py

def get_diseases_treated_by_medication(db: Session, medication_id: int) -> List[models.TraitementPathologie]:
    """
    Récupère toutes les pathologies traitées par un médicament.
    """
    return db.query(models.TraitementPathologie).filter(models.TraitementPathologie.medicament_id == medication_id).all()


def get_symptoms_treated_by_medication(db: Session, medication_id: int) -> List[models.TraitementSymptome]:
    """
    Récupère tous les symptômes traités par un médicament.
    """
    return db.query(models.TraitementSymptome).filter(models.TraitementSymptome.medicament_id == medication_id).all()