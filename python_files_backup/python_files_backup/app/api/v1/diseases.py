from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from ... import schemas, models
from ...services import disease_service
from ...dependencies import get_db

router = APIRouter(
    prefix="/diseases",
    tags=["Diseases"]
)


@router.post("/", response_model=schemas.disease.Disease, status_code=status.HTTP_201_CREATED)
def create_disease(disease_data: schemas.disease.DiseaseCreate, db: Session = Depends(get_db)):
    """
    Crée une nouvelle pathologie.
    Vérifie l'unicité du code CIM-10.
    """
    db_disease = disease_service.get_disease_by_icd10(db, icd10_code=disease_data.code_icd10)
    if db_disease:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Une pathologie avec le code CIM-10 '{disease_data.code_icd10}' existe déjà."
        )
    return disease_service.create_disease(db=db, disease=disease_data)


@router.get("/", response_model=List[schemas.disease.Disease])
def read_diseases(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    Récupère une liste de pathologies.
    """
    diseases = disease_service.get_all_diseases(db, skip=skip, limit=limit)
    return diseases


@router.get("/{disease_id}", response_model=schemas.disease.Disease)
def read_disease(disease_id: int, db: Session = Depends(get_db)):
    """
    Récupère une pathologie par son ID.
    """
    db_disease = disease_service.get_disease_by_id(db, disease_id=disease_id)
    if db_disease is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pathologie non trouvée.")
    return db_disease


@router.patch("/{disease_id}", response_model=schemas.disease.Disease)
def update_disease(disease_id: int, disease_data: schemas.disease.DiseaseUpdate, db: Session = Depends(get_db)):
    """
    Met à jour une pathologie.
    """
    db_disease = disease_service.update_disease(db, disease_id=disease_id, disease_update=disease_data)
    if db_disease is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pathologie non trouvée.")
    return db_disease


@router.delete("/{disease_id}", response_model=schemas.disease.Disease)
def delete_disease(disease_id: int, db: Session = Depends(get_db)):
    """
    Supprime une pathologie.
    """
    db_disease = disease_service.delete_disease(db, disease_id=disease_id)
    if db_disease is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pathologie non trouvée.")
    return db_disease

# Contenu à AJOUTER à la fin de app/api/v1/diseases.py

@router.post(
    "/{disease_id}/symptoms",
    response_model=schemas.relations.PathologieSymptome,
    status_code=status.HTTP_201_CREATED,
    tags=["Disease-Symptom Relations"] # Un nouveau tag pour l'organisation
)
def add_symptom_to_disease(
    disease_id: int, 
    association_data: schemas.relations.PathologieSymptomeCreate, 
    db: Session = Depends(get_db)
):
    """
    Associe un symptôme à une pathologie avec des attributs de relation
    (probabilité, importance, etc.).
    """
    # Assurer la cohérence des IDs
    if disease_id != association_data.pathologie_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="L'ID de la pathologie dans l'URL ne correspond pas à celui dans le corps de la requête."
        )
    
    try:
        return disease_service.add_symptom_to_disease(db=db, association_data=association_data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get(
    "/{disease_id}/symptoms",
    response_model=List[schemas.relations.SymptomForDiseaseDetail],
    tags=["Disease-Symptom Relations"]
)
def get_symptoms_for_disease(disease_id: int, db: Session = Depends(get_db)):
    """
    Récupère la liste de tous les symptômes associés à une pathologie,
    avec les détails de la relation et les détails du symptôme lui-même.
    """
    associations = disease_service.get_symptoms_for_disease(db, disease_id=disease_id)
    if not associations:
        # Ce n'est pas une erreur, la maladie peut simplement n'avoir aucun symptôme associé pour l'instant
        return []
    
    # Transformer les données pour correspondre au schéma de réponse attendu
    response = []
    for assoc in associations:
        response.append({
            "symptome": assoc.symptome, # L'objet Symptom complet
            "probabilite": assoc.probabilite,
            "importance_diagnostique": assoc.importance_diagnostique,
            "est_pathognomonique": assoc.est_pathognomonique
        })
    return response


# Contenu à AJOUTER à la fin de app/api/v1/diseases.py

@router.post(
    "/{disease_id}/treatments",
    response_model=schemas.relations.TraitementPathologie,
    status_code=status.HTTP_201_CREATED,
    tags=["Therapeutic Relations"]
)
def add_treatment_to_disease(
    disease_id: int, 
    association_data: schemas.relations.TraitementPathologieCreate, 
    db: Session = Depends(get_db)
):
    """
    Associe un médicament à une pathologie en tant que traitement.
    """
    if disease_id != association_data.pathologie_id:
        raise HTTPException(status_code=400, detail="Incohérence des IDs de pathologie.")
    
    try:
        return disease_service.add_treatment_to_disease(db=db, association_data=association_data)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get(
    "/{disease_id}/treatments",
    response_model=List[schemas.relations.MedicationForDiseaseDetail],
    tags=["Therapeutic Relations"]
)
def get_treatments_for_disease(disease_id: int, db: Session = Depends(get_db)):
    """
    Récupère la liste des traitements recommandés pour une pathologie.
    """
    associations = disease_service.get_treatments_for_disease(db, disease_id=disease_id)
    return [
        {
            "medicament": assoc.medicament,
            "type_traitement": assoc.type_traitement,
            "ligne_traitement": assoc.ligne_traitement,
            "rang_preference": assoc.rang_preference,
        }
        for assoc in associations
    ]