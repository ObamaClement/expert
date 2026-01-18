from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID

# Importe les schémas que nous avons définis
from ... import schemas
from ...dependencies import get_db
# Importe les services
from ...services import tutor_service, simulation_service

router = APIRouter(
    prefix="/simulation",
    tags=["Simulation"]
)

@router.post(
    "/sessions/start",
    response_model=schemas.simulation.SessionStartResponse,
    status_code=status.HTTP_201_CREATED
)
def start_simulation_session(
    request_data: schemas.simulation.SessionStartRequest,
    db: Session = Depends(get_db)
):
    """
    Démarre une nouvelle session de simulation pour un apprenant.
    """
    try:
        session, clinical_case, session_type = tutor_service.start_new_session(
            db=db,
            learner_id=request_data.learner_id,
            category=request_data.category
        )
        return schemas.simulation.SessionStartResponse(
            session_id=session.id,
            session_type=session_type,
            clinical_case=clinical_case
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Une erreur inattendue est survenue: {str(e)}"
        )

@router.post(
    "/sessions/{session_id}/actions",
    response_model=schemas.simulation.LearnerActionResponse
)
def perform_learner_action(
    session_id: UUID,
    action_data: schemas.simulation.LearnerActionRequest,
    db: Session = Depends(get_db)
):
    """
    Traite une action effectuée par l'apprenant pendant une session.
    """
    try:
        action_result, feedback = tutor_service.process_learner_action(
            db=db,
            session_id=session_id,
            action_data=action_data
        )
        return schemas.simulation.LearnerActionResponse(
            action_type=action_data.action_type,
            action_name=action_data.action_name,
            result=action_result,
            feedback=feedback
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors du traitement de l'action: {str(e)}"
        )

@router.post(
    "/sessions/{session_id}/request-hint",
    response_model=schemas.simulation.HintResponse
)
def request_hint(
    session_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Permet à un apprenant de demander un indice pour la session en cours.
    """
    try:
        hint_type, hint_content = tutor_service.provide_hint(
            db=db,
            session_id=session_id
        )
        
        return schemas.simulation.HintResponse(
            hint_type=hint_type,
            content=hint_content
        )

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la génération de l'indice: {str(e)}"
        )

# ==============================================================================
# NOUVEL ENDPOINT POUR LA SOUMISSION FINALE
# ==============================================================================

@router.post(
    "/sessions/{session_id}/submit",
    response_model=schemas.simulation.SubmissionResponse
)
def submit_final_diagnosis(
    session_id: UUID,
    submission_data: schemas.simulation.SubmissionRequest,
    db: Session = Depends(get_db)
):
    """
    Soumet le diagnostic et le traitement final de l'apprenant pour évaluation.
    """
    try:
        # La logique complexe d'évaluation est déléguée au service tuteur
        eval_result, feedback, recommendation = tutor_service.evaluate_submission(
            db=db,
            session_id=session_id,
            submission_data=submission_data
        )

        return schemas.simulation.SubmissionResponse(
            evaluation=eval_result,
            feedback_global=feedback,
            recommendation_next_step=recommendation
        )

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de l'évaluation de la soumission: {str(e)}"
        )