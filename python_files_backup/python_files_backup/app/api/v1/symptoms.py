from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from ... import schemas, models
from ...services import symptom_service
from ...dependencies import get_db

# Création d'un nouveau routeur.
# C'est comme une mini-application FastAPI que l'on pourra inclure dans notre app principale.
router = APIRouter(
    prefix="/symptoms",  # Toutes les routes de ce fichier commenceront par /symptoms
    tags=["Symptoms"]      # Groupe les routes dans la documentation interactive
)


@router.post("/", response_model=schemas.Symptom, status_code=status.HTTP_201_CREATED)
def create_symptom(symptom: schemas.SymptomCreate, db: Session = Depends(get_db)):
    """
    Crée un nouveau symptôme.
    """
    # Vérifie si un symptôme avec le même nom existe déjà
    db_symptom = symptom_service.get_symptom_by_name(db, name=symptom.nom)
    if db_symptom:
        raise HTTPException(status_code=400, detail="Un symptôme avec ce nom existe déjà.")
    
    return symptom_service.create_symptom(db=db, symptom=symptom)


@router.get("/", response_model=List[schemas.Symptom])
def read_symptoms(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    Récupère une liste de symptômes.
    """
    symptoms = symptom_service.get_all_symptoms(db, skip=skip, limit=limit)
    return symptoms


@router.get("/{symptom_id}", response_model=schemas.Symptom)
def read_symptom(symptom_id: int, db: Session = Depends(get_db)):
    """
    Récupère un symptôme par son ID.
    """
    db_symptom = symptom_service.get_symptom_by_id(db, symptom_id=symptom_id)
    if db_symptom is None:
        raise HTTPException(status_code=404, detail="Symptôme non trouvé.")
    return db_symptom


@router.patch("/{symptom_id}", response_model=schemas.Symptom)
def update_symptom(symptom_id: int, symptom: schemas.SymptomUpdate, db: Session = Depends(get_db)):
    """
    Met à jour un symptôme.
    """
    db_symptom = symptom_service.update_symptom(db, symptom_id=symptom_id, symptom_update=symptom)
    if db_symptom is None:
        raise HTTPException(status_code=404, detail="Symptôme non trouvé.")
    return db_symptom


@router.delete("/{symptom_id}", response_model=schemas.Symptom)
def delete_symptom(symptom_id: int, db: Session = Depends(get_db)):
    """
    Supprime un symptôme.
    """
    db_symptom = symptom_service.delete_symptom(db, symptom_id=symptom_id)
    if db_symptom is None:
        raise HTTPException(status_code=404, detail="Symptôme non trouvé.")
    return db_symptom

# Contenu à AJOUTER à la fin de app/api/v1/symptoms.py

@router.get(
    "/{symptom_id}/diseases",
    response_model=List[schemas.relations.DiseaseForSymptomDetail],
    tags=["Disease-Symptom Relations"]
)
def get_diseases_for_symptom(symptom_id: int, db: Session = Depends(get_db)):
    """
    Récupère la liste de toutes les pathologies pouvant présenter ce symptôme
    (utile pour le diagnostic différentiel).
    """
    associations = symptom_service.get_diseases_for_symptom(db, symptom_id=symptom_id)
    if not associations:
        return []
        
    response = []
    for assoc in associations:
        response.append({
            "pathologie": assoc.pathologie,
            "probabilite": assoc.probabilite,
            "importance_diagnostique": assoc.importance_diagnostique
        })
    return response



# Contenu à AJOUTER à la fin de app/api/v1/symptoms.py

@router.post(
    "/{symptom_id}/treatments",
    response_model=schemas.relations.TraitementSymptome,
    status_code=status.HTTP_201_CREATED,
    tags=["Therapeutic Relations"]
)
def add_treatment_to_symptom(
    symptom_id: int,
    association_data: schemas.relations.TraitementSymptomeCreate,
    db: Session = Depends(get_db)
):
    """
    Associe un médicament à un symptôme pour un traitement symptomatique.
    """
    if symptom_id != association_data.symptome_id:
        raise HTTPException(status_code=400, detail="Incohérence des IDs de symptôme.")
    
    try:
        return symptom_service.add_treatment_to_symptom(db=db, association_data=association_data)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get(
    "/{symptom_id}/treatments",
    response_model=List[schemas.relations.MedicationForSymptomDetail],
    tags=["Therapeutic Relations"]
)
def get_treatments_for_symptom(symptom_id: int, db: Session = Depends(get_db)):
    """
    Récupère la liste des traitements pour un symptôme spécifique.
    """
    associations = symptom_service.get_treatments_for_symptom(db, symptom_id=symptom_id)
    return [
        {
            "medicament": assoc.medicament,
            "efficacite": assoc.efficacite,
            "rang_preference": assoc.rang_preference,
        }
        for assoc in associations
    ]