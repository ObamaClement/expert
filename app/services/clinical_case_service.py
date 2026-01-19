import logging
from sqlalchemy.orm import Session
from typing import List, Optional
import random

from .. import models, schemas
from . import disease_service, media_service

# Logger spécifique
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

def get_case_by_id(db: Session, case_id: int) -> Optional[models.ClinicalCase]:
    return db.query(models.ClinicalCase).filter(models.ClinicalCase.id == case_id).first()

def get_case_by_code(db: Session, code: str) -> Optional[models.ClinicalCase]:
    return db.query(models.ClinicalCase).filter(models.ClinicalCase.code_fultang == code).first()

def get_all_cases(db: Session, skip: int = 0, limit: int = 100) -> List[models.ClinicalCase]:
    return db.query(models.ClinicalCase).offset(skip).limit(limit).all()

def get_case_for_progression(
    db: Session, 
    category: str, 
    target_difficulty: int, 
    exclude_case_ids: List[int]
) -> Optional[models.ClinicalCase]:
    """
    Recherche intelligente de cas.
    """
    logger.info(f"📚 [CASE-SEARCH] Recherche: Cat='{category}', Cible={target_difficulty}")
    logger.debug(f"   -> Exclusions ({len(exclude_case_ids)}): {exclude_case_ids}")

    base_query = db.query(models.ClinicalCase).join(
        models.Disease, models.ClinicalCase.pathologie_principale_id == models.Disease.id
    ).filter(
        models.Disease.categorie == category,
        models.ClinicalCase.id.notin_(exclude_case_ids)
    )

    # Fonction helper pour sécuriser le niveau
    def get_difficulty(c):
        return c.niveau_difficulte if c.niveau_difficulte is not None else 1

    # 1. Recherche stricte (Cible +/- 2)
    strict_candidates = base_query.filter(
        models.ClinicalCase.niveau_difficulte.between(target_difficulty - 2, target_difficulty + 2)
    ).all()
    
    logger.debug(f"   -> Candidats stricts (+/-2): {len(strict_candidates)}")

    if strict_candidates:
        chosen = random.choice(strict_candidates)
        logger.info(f"   ✅ [FOUND] Cas strict trouvé: {chosen.id} (Niveau {get_difficulty(chosen)})")
        return chosen

    # 2. Recherche élargie (Cible +/- 5)
    wide_candidates = base_query.filter(
        models.ClinicalCase.niveau_difficulte.between(target_difficulty - 5, target_difficulty + 5)
    ).all()

    logger.debug(f"   -> Candidats larges (+/-5): {len(wide_candidates)}")

    if wide_candidates:
        chosen = min(wide_candidates, key=lambda c: abs(get_difficulty(c) - target_difficulty))
        logger.info(f"   ✅ [FOUND] Cas large trouvé: {chosen.id} (Niveau {get_difficulty(chosen)})")
        return chosen

    # 3. Fallback
    fallback_candidates = base_query.all()
    logger.debug(f"   -> Candidats fallback (tout reste): {len(fallback_candidates)}")
    
    if fallback_candidates:
        # On filtre ceux qui n'ont pas de niveau pour éviter les erreurs, ou on leur donne une valeur par défaut
        valid_candidates = [c for c in fallback_candidates]
        
        if not valid_candidates:
             logger.error("   ❌ [ERROR] Cas trouvés mais aucun valide (problème de données ?)")
             return None

        chosen = min(valid_candidates, key=lambda c: abs(get_difficulty(c) - target_difficulty))
        logger.info(f"   ⚠️ [FOUND] Cas fallback trouvé: {chosen.id} (Niveau {get_difficulty(chosen)})")
        return chosen

    logger.error("   ❌ [NOT-FOUND] Aucun cas disponible.")
    return None



# --- NOUVELLE FONCTION ---
def get_cases_by_category(db: Session, category: str) -> List[models.ClinicalCase]:
    """Récupère tous les cas d'une catégorie spécifique."""
    return db.query(models.ClinicalCase).join(
        models.Disease, models.ClinicalCase.pathologie_principale_id == models.Disease.id
    ).filter(
        models.Disease.categorie == category
    ).all()



# Fonctions CRUD standard
def create_case(db: Session, case: schemas.ClinicalCaseCreate) -> models.ClinicalCase:
    if case.pathologie_principale_id:
        if not disease_service.get_disease_by_id(db, case.pathologie_principale_id):
            raise ValueError(f"Pathologie {case.pathologie_principale_id} introuvable")
    
    case_data = case.model_dump()
    db_case = models.ClinicalCase(**case_data)
    db.add(db_case)
    db.commit()
    db.refresh(db_case)
    return db_case

def update_case(db: Session, case_id: int, case_update: schemas.ClinicalCaseUpdate) -> Optional[models.ClinicalCase]:
    db_case = get_case_by_id(db, case_id)
    if not db_case: return None
    for key, value in case_update.model_dump(exclude_unset=True).items():
        setattr(db_case, key, value)
    db.commit()
    db.refresh(db_case)
    return db_case

def delete_case(db: Session, case_id: int) -> Optional[models.ClinicalCase]:
    db_case = get_case_by_id(db, case_id)
    if not db_case: return None
    db.delete(db_case)
    db.commit()
    return db_case