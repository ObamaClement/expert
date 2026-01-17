from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any

from ...services import diagnostic_engine
from ...dependencies import get_db

router = APIRouter(
    prefix="/diagnostic-engine",
    tags=["Diagnostic Engine"]
)


@router.post("/run", response_model=List[Dict[str, Any]])
def run_diagnostic_engine(
    patient_facts: diagnostic_engine.DiagnosticInput,
    db: Session = Depends(get_db)
):
    """
    Exécute le moteur de raisonnement sur un ensemble de faits patient.

    Prend en entrée une liste de symptômes et de contextes, et retourne
    une liste d'actions/conclusions basées sur les règles expertes actives
    dans le système.
    """
    if not patient_facts.symptoms:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La liste des symptômes ne peut pas être vide."
        )

    conclusions = diagnostic_engine.run_diagnostic(db=db, patient_facts=patient_facts)
    
    return conclusions