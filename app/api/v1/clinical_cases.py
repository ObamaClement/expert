from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from ... import schemas, models
from ...services import clinical_case_service, media_service, symptom_service, disease_service
from ...dependencies import get_db

router = APIRouter(
    prefix="/clinical-cases",
    tags=["Clinical Cases"]
)


@router.post("/", response_model=schemas.clinical_case.ClinicalCase, status_code=status.HTTP_201_CREATED)
def create_clinical_case(case_data: schemas.clinical_case.ClinicalCaseCreate, db: Session = Depends(get_db)):
    """
    Crée un nouveau cas clinique.
    """
    db_case_by_code = clinical_case_service.get_case_by_code(db, code=case_data.code_fultang)
    if db_case_by_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Un cas avec le code '{case_data.code_fultang}' existe déjà."
        )
    try:
        # Le service create_case retournera un objet SQLAlchemy
        db_case = clinical_case_service.create_case(db=db, case=case_data)
        # La conversion vers le schéma Pydantic se fait automatiquement par FastAPI
        return db_case
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/", response_model=List[schemas.clinical_case.ClinicalCaseSimple])
def read_all_clinical_cases(skip: int = 0, limit: int = 25, db: Session = Depends(get_db)):
    """
    Récupère une liste simplifiée de cas cliniques.
    """
    cases = clinical_case_service.get_all_cases(db, skip=skip, limit=limit)
    
    # La conversion vers le schéma Pydantic gère automatiquement la construction de la réponse
    # en utilisant les relations SQLAlchemy et les configurations 'from_attributes'.
    # Cependant, pour des champs calculés comme 'nb_images', nous devons construire la réponse manuellement.
    response = []
    for case in cases:
        case_simple = schemas.clinical_case.ClinicalCaseSimple(
            id=case.id,
            code_fultang=case.code_fultang,
            niveau_difficulte=case.niveau_difficulte,
            pathologie_principale=case.pathologie_principale,
            nb_images=len(case.images_associees_ids) if case.images_associees_ids else 0,
            nb_sons=len(case.sons_associes_ids) if case.sons_associes_ids else 0,
        )
        response.append(case_simple)
    return response


@router.get("/{case_id}", response_model=schemas.clinical_case.ClinicalCase)
def read_clinical_case(case_id: int, db: Session = Depends(get_db)):
    """
    Récupère un cas clinique complet par son ID, avec tous les objets liés.
    """
    # 1. Récupérer le cas brut
    db_case = clinical_case_service.get_case_by_id(db, case_id=case_id)
    if db_case is None:
        raise HTTPException(status_code=404, detail="Cas clinique non trouvé.")
    
    # 2. Convertir en dictionnaire pour pouvoir injecter les champs enrichis
    case_dict = db_case.__dict__

    # 3. Enrichir : Pathologies Secondaires
    pathologies_secondaires = []
    if db_case.pathologies_secondaires_ids:
        for p_id in db_case.pathologies_secondaires_ids:
            p_obj = disease_service.get_disease_by_id(db, disease_id=p_id)
            if p_obj:
                pathologies_secondaires.append(p_obj)
    case_dict['pathologies_secondaires'] = pathologies_secondaires

    # 4. Enrichir : Images
    images = []
    if db_case.images_associees_ids:
        for img_id in db_case.images_associees_ids:
            img = media_service.get_image_medicale_by_id(db, image_id=img_id)
            if img:
                images.append(img)
    case_dict['images_associees'] = images

    # 5. Enrichir : Présentation Clinique Détaillée
    # Le champ 'presentation_clinique' en base contient juste des IDs.
    # Nous devons aller chercher les objets Symptômes complets.
    symptomes_details_in_case = []
    presentation_dict = db_case.presentation_clinique or {}
    
    if 'symptomes_patient' in presentation_dict:
        for item in presentation_dict['symptomes_patient']:
            # item ressemble à {'symptome_id': 1, 'details': 'Fièvre forte'}
            sympt_id = item.get('symptome_id')
            sympt_obj = symptom_service.get_symptom_by_id(db, symptom_id=sympt_id)
            
            if sympt_obj:
                symptomes_details_in_case.append({
                    "symptome": sympt_obj, # L'objet complet
                    "details": item.get('details', '')
                })
    
    case_dict['presentation_clinique_detail'] = {
        "histoire_maladie": presentation_dict.get('histoire_maladie', ''),
        "symptomes_patient": symptomes_details_in_case,
        "antecedents": presentation_dict.get('antecedents')
    }

    # 6. Validation et Retour
    # On passe le dictionnaire enrichi à Pydantic pour qu'il le valide et le formate
    return schemas.clinical_case.ClinicalCase.model_validate(case_dict)

@router.patch("/{case_id}", response_model=schemas.clinical_case.ClinicalCase)
def update_clinical_case(case_id: int, case_data: schemas.clinical_case.ClinicalCaseUpdate, db: Session = Depends(get_db)):
    """
    Met à jour un cas clinique.
    """
    db_case = clinical_case_service.update_case(db, case_id=case_id, case_update=case_data)
    if db_case is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cas clinique non trouvé.")
    # La conversion vers le schéma de réponse se fait automatiquement
    return db_case


@router.delete("/{case_id}", response_model=schemas.clinical_case.ClinicalCase)
def delete_clinical_case(case_id: int, db: Session = Depends(get_db)):
    """
    Supprime un cas clinique.
    """
    db_case = clinical_case_service.delete_case(db, case_id=case_id)
    if db_case is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cas clinique non trouvé.")
    # La conversion vers le schéma de réponse se fait automatiquement
    return db_case