from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from ... import schemas, models
from ...services import medication_service
from ...dependencies import get_db

router = APIRouter(
    prefix="/medications",
    tags=["Medications"]
)


@router.post("/", response_model=schemas.medication.Medication, status_code=status.HTTP_201_CREATED)
def create_medication(medication_data: schemas.medication.MedicationCreate, db: Session = Depends(get_db)):
    """
    Crée un nouveau médicament.
    Vérifie l'unicité du DCI (Dénomination Commune Internationale).
    """
    db_medication = medication_service.get_medication_by_dci(db, dci=medication_data.dci)
    if db_medication:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Un médicament avec le DCI '{medication_data.dci}' existe déjà."
        )
    return medication_service.create_medication(db=db, medication=medication_data)


@router.get("/", response_model=List[schemas.medication.Medication])
def read_medications(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    Récupère une liste de médicaments.
    """
    medications = medication_service.get_all_medications(db, skip=skip, limit=limit)
    return medications


@router.get("/{medication_id}", response_model=schemas.medication.Medication)
def read_medication(medication_id: int, db: Session = Depends(get_db)):
    """
    Récupère un médicament par son ID.
    """
    db_medication = medication_service.get_medication_by_id(db, medication_id=medication_id)
    if db_medication is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Médicament non trouvé.")
    return db_medication


@router.patch("/{medication_id}", response_model=schemas.medication.Medication)
def update_medication(medication_id: int, medication_data: schemas.medication.MedicationUpdate, db: Session = Depends(get_db)):
    """
    Met à jour un médicament.
    """
    db_medication = medication_service.update_medication(db, medication_id=medication_id, medication_update=medication_data)
    if db_medication is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Médicament non trouvé.")
    return db_medication


@router.delete("/{medication_id}", response_model=schemas.medication.Medication)
def delete_medication(medication_id: int, db: Session = Depends(get_db)):
    """
    Supprime un médicament.
    """
    db_medication = medication_service.delete_medication(db, medication_id=medication_id)
    if db_medication is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Médicament non trouvé.")
    return db_medication