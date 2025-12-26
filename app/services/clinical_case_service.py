from sqlalchemy.orm import Session
from typing import List, Optional

from .. import models, schemas

# Importer les autres services dont nous aurons besoin
from . import disease_service
from . import media_service


def get_case_by_id(db: Session, case_id: int) -> Optional[models.ClinicalCase]:
    """
    Récupère un cas clinique par son ID.
    """
    return db.query(models.ClinicalCase).filter(models.ClinicalCase.id == case_id).first()


def get_case_by_code(db: Session, code: str) -> Optional[models.ClinicalCase]:
    """
    Récupère un cas clinique par son code Fultang ou synthétique.
    """
    return db.query(models.ClinicalCase).filter(models.ClinicalCase.code_fultang == code).first()


def get_all_cases(db: Session, skip: int = 0, limit: int = 100) -> List[models.ClinicalCase]:
    """
    Récupère une liste de tous les cas cliniques avec pagination.
    """
    return db.query(models.ClinicalCase).offset(skip).limit(limit).all()


def create_case(db: Session, case: schemas.ClinicalCaseCreate) -> models.ClinicalCase:
    """
    Crée un nouveau cas clinique dans la base de données.
    """
    # Vérifier que la pathologie principale existe, si elle est fournie
    if case.pathologie_principale_id:
        db_disease = disease_service.get_disease_by_id(db, disease_id=case.pathologie_principale_id)
        if not db_disease:
            raise ValueError(f"La pathologie avec l'ID {case.pathologie_principale_id} n'existe pas.")

    # Vérifier que les images associées existent, si elles sont fournies
    if case.images_associees_ids:
        for img_id in case.images_associees_ids:
            db_image = media_service.get_image_medicale_by_id(db, image_id=img_id)
            if not db_image:
                raise ValueError(f"L'image avec l'ID {img_id} n'existe pas.")

    case_data = case.model_dump()
    db_case = models.ClinicalCase(**case_data)
    
    db.add(db_case)
    db.commit()
    db.refresh(db_case)
    
    return db_case


def update_case(db: Session, case_id: int, case_update: schemas.ClinicalCaseUpdate) -> Optional[models.ClinicalCase]:
    """
    Met à jour un cas clinique existant.
    """
    db_case = get_case_by_id(db, case_id)
    if not db_case:
        return None

    update_data = case_update.model_dump(exclude_unset=True)
    
    for key, value in update_data.items():
        setattr(db_case, key, value)
        
    db.commit()
    db.refresh(db_case)
    
    return db_case


def delete_case(db: Session, case_id: int) -> Optional[models.ClinicalCase]:
    """
    Supprime un cas clinique de la base de données.
    Note : Ne supprime pas les entités associées (maladies, images...).
    """
    db_case = get_case_by_id(db, case_id)
    if not db_case:
        return None

    db.delete(db_case)
    db.commit()
    
    return db_case