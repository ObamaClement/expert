from sqlalchemy.orm import Session
from typing import List, Optional

from .. import models, schemas

def get_disease_by_id(db: Session, disease_id: int) -> Optional[models.Disease]:
    """
    Récupère une pathologie par son ID.
    """
    return db.query(models.Disease).filter(models.Disease.id == disease_id).first()

def get_disease_by_icd10(db: Session, icd10_code: str) -> Optional[models.Disease]:
    """
    Récupère une pathologie par son code CIM-10.
    """
    return db.query(models.Disease).filter(models.Disease.code_icd10 == icd10_code).first()

def get_all_diseases(db: Session, skip: int = 0, limit: int = 100) -> List[models.Disease]:
    """
    Récupère une liste de toutes les pathologies avec pagination.
    """
    return db.query(models.Disease).offset(skip).limit(limit).all()

def create_disease(db: Session, disease: schemas.DiseaseCreate) -> models.Disease:
    """
    Crée une nouvelle pathologie dans la base de données.
    """
    disease_data = disease.model_dump()
    db_disease = models.Disease(**disease_data)
    
    db.add(db_disease)
    db.commit()
    db.refresh(db_disease)
    
    return db_disease

def update_disease(db: Session, disease_id: int, disease_update: schemas.DiseaseUpdate) -> Optional[models.Disease]:
    """
    Met à jour une pathologie existante.
    """
    db_disease = get_disease_by_id(db, disease_id)
    if not db_disease:
        return None

    update_data = disease_update.model_dump(exclude_unset=True)
    
    for key, value in update_data.items():
        setattr(db_disease, key, value)
        
    db.commit()
    db.refresh(db_disease)
    
    return db_disease

def delete_disease(db: Session, disease_id: int) -> Optional[models.Disease]:
    """
    Supprime une pathologie de la base de données.
    """
    db_disease = get_disease_by_id(db, disease_id)
    if not db_disease:
        return None

    db.delete(db_disease)
    db.commit()
    
    return db_disease

def add_symptom_to_disease(db: Session, association_data: schemas.relations.PathologieSymptomeCreate) -> models.PathologieSymptome:
    """
    Associe un symptôme à une pathologie avec des attributs de relation.
    """
    # Vérifier que la pathologie et le symptôme existent
    db_disease = get_disease_by_id(db, disease_id=association_data.pathologie_id)
    # Nous aurons besoin d'importer le symptom_service pour cette vérification
    from . import symptom_service
    db_symptom = symptom_service.get_symptom_by_id(db, symptom_id=association_data.symptome_id)

    if not db_disease or not db_symptom:
        # Idéalement, lever une exception plus spécifique
        raise ValueError("Pathologie ou Symptôme non trouvé.")

    # Créer l'objet d'association
    association = models.PathologieSymptome(**association_data.model_dump())
    
    db.add(association)
    db.commit()
    db.refresh(association)
    
    return association


def get_symptoms_for_disease(db: Session, disease_id: int) -> List[models.PathologieSymptome]:
    """
    Récupère tous les symptômes associés à une pathologie, avec les détails de la relation.
    """
    return db.query(models.PathologieSymptome).filter(models.PathologieSymptome.pathologie_id == disease_id).all()


def add_treatment_to_disease(db: Session, association_data: schemas.relations.TraitementPathologieCreate) -> models.TraitementPathologie:
    """
    Associe un médicament à une pathologie en tant que traitement.
    """
    db_disease = get_disease_by_id(db, disease_id=association_data.pathologie_id)
    from . import medication_service
    db_medication = medication_service.get_medication_by_id(db, medication_id=association_data.medicament_id)

    if not db_disease or not db_medication:
        raise ValueError("Pathologie ou Médicament non trouvé.")

    association = models.TraitementPathologie(**association_data.model_dump())
    
    db.add(association)
    db.commit()
    db.refresh(association)
    
    return association


def get_treatments_for_disease(db: Session, disease_id: int) -> List[models.TraitementPathologie]:
    """
    Récupère tous les traitements associés à une pathologie.
    """
    return db.query(models.TraitementPathologie).filter(models.TraitementPathologie.pathologie_id == disease_id).all()