from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
import random

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


def get_case_for_progression(
    db: Session, 
    category: str, 
    target_difficulty: int, 
    exclude_case_ids: List[int]
) -> Optional[models.ClinicalCase]:
    """
    Trouve un cas clinique adapté à la progression de l'apprenant.
    Cherche un cas dans la catégorie donnée, proche du niveau de difficulté cible,
    en excluant ceux déjà réalisés.
    
    Logique de recherche :
    1. Cherche exact ou +/- 1 niveau.
    2. Si rien, élargit à +/- 3 niveaux.
    3. Si rien, prend n'importe quel cas de la catégorie non fait.
    """
    base_query = db.query(models.ClinicalCase).join(
        models.Disease, models.ClinicalCase.pathologie_principale_id == models.Disease.id
    ).filter(
        models.Disease.categorie == category,
        models.ClinicalCase.id.notin_(exclude_case_ids)
    )

    # 1. Recherche stricte (Cible +/- 1)
    strict_candidates = base_query.filter(
        models.ClinicalCase.niveau_difficulte.between(target_difficulty - 1, target_difficulty + 1)
    ).all()

    if strict_candidates:
        return random.choice(strict_candidates)

    # 2. Recherche élargie (Cible +/- 3)
    wide_candidates = base_query.filter(
        models.ClinicalCase.niveau_difficulte.between(target_difficulty - 3, target_difficulty + 3)
    ).all()

    if wide_candidates:
        # On prend celui qui est le plus proche du niveau cible
        return min(wide_candidates, key=lambda c: abs(c.niveau_difficulte - target_difficulty))

    # 3. Fallback (N'importe quel cas de la catégorie non fait)
    fallback_candidates = base_query.all()
    
    if fallback_candidates:
        # On prend le plus proche disponible, même s'il est loin
        return min(fallback_candidates, key=lambda c: abs(c.niveau_difficulte - target_difficulty))

    return None


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