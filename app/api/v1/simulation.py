#=== Fichier: ./app/api/v1/simulation.py ===

import logging
import time
import uuid
from typing import Any, Dict
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.orm import Session

from ... import schemas, models
from ...services import tutor_service
from ...dependencies import get_db

# ==============================================================================
# CONFIGURATION DU LOGGER API SIMULATION
# ==============================================================================
logger = logging.getLogger("api_simulation")
logger.setLevel(logging.DEBUG)

if not logger.handlers:
    handler = logging.StreamHandler()
    # Format enrichi pour le debug API
    formatter = logging.Formatter('%(asctime)s - [API-SIM] - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

router = APIRouter(
    prefix="/simulation",
    tags=["Simulation"]
)

# ==============================================================================
# 1. DÉMARRAGE DE SESSION
# ==============================================================================

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
    Initialise le contexte, choisit un cas clinique et prépare le patient virtuel.
    """
    req_id = str(uuid.uuid4())[:8]
    start_time = time.time()
    
    logger.info(f"📥 [REQ-{req_id}] POST /sessions/start | Learner: {request_data.learner_id} | Cat: {request_data.category}")

    try:
        # Appel au service orchestrateur
        session, clinical_case, session_type = tutor_service.start_new_session(
            db=db,
            learner_id=request_data.learner_id,
            category=request_data.category
        )
        
        # --- SÉRIALISATION MANUELLE (Protection Pydantic) ---
        # On convertit l'objet SQLAlchemy Pathologie en dictionnaire simple
        # pour éviter l'erreur "Unable to serialize unknown type"
        patho_dict = None
        if clinical_case.pathologie_principale:
            p = clinical_case.pathologie_principale
            patho_dict = {
                "id": p.id,
                "nom_fr": p.nom_fr,
                "code_icd10": p.code_icd10,
                "categorie": p.categorie,
                "description": p.description
            }

        # Construction du dictionnaire pour le schéma de réponse
        case_dict = {
            "id": clinical_case.id,
            "code_fultang": clinical_case.code_fultang,
            "niveau_difficulte": clinical_case.niveau_difficulte,
            "pathologie_principale": patho_dict, # Dict pur, pas d'objet ORM
            "presentation_clinique": clinical_case.presentation_clinique,
            "donnees_paracliniques": clinical_case.donnees_paracliniques
        }

        response = schemas.simulation.SessionStartResponse(
            session_id=session.id,
            session_type=session_type,
            clinical_case=case_dict,
            start_time=session.start_time
        )
        
        duration = time.time() - start_time
        logger.info(f"   ✅ [REQ-{req_id}] Session démarrée : {session.id} ({duration:.2f}s)")
        
        return response

    except ValueError as e:
        logger.warning(f"   ⚠️ [REQ-{req_id}] Erreur validation (400/404): {str(e)}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        
    except Exception as e:
        logger.critical(f"   ❌ [REQ-{req_id}] Erreur serveur (500): {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur interne lors du démarrage de la session: {str(e)}"
        )

# ==============================================================================
# 2. ACTIONS (Examens, Traitements, Gestes)
# ==============================================================================

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
    Traite une action effectuée par l'apprenant (Examen, Prescription).
    Déclenche l'IA génératrice pour les résultats d'examens.
    """
    req_id = str(uuid.uuid4())[:8]
    start_time = time.time()
    
    logger.info(f"📥 [REQ-{req_id}] POST /actions | Session: {session_id}")
    logger.debug(f"   [REQ-{req_id}] Action: {action_data.action_type} -> {action_data.action_name}")

    try:
        # Appel au service Tutor
        result_data, feedback = tutor_service.process_learner_action(
            db=db,
            session_id=session_id,
            action_data=action_data
        )
        
        # Reconstruction des métadonnées pour l'affichage frontend
        from ...services.tutor_service import VirtualTimeManager, VirtualBudgetManager
        cost = VirtualBudgetManager.estimate_cost(action_data.action_name)
        duration_min = VirtualTimeManager.calculate_duration(action_data.action_type, action_data.action_name)
        
        meta = schemas.simulation.ActionMetadata(
            virtual_cost=cost,
            virtual_duration=duration_min
        )

        response = schemas.simulation.LearnerActionResponse(
            action_type=action_data.action_type,
            action_name=action_data.action_name,
            result=result_data,
            feedback=feedback,
            meta=meta
        )
        
        duration = time.time() - start_time
        logger.info(f"   ✅ [REQ-{req_id}] Action traitée avec succès ({duration:.2f}s)")
        
        return response

    except ValueError as e:
        logger.warning(f"   ⚠️ [REQ-{req_id}] Erreur fonctionnelle: {str(e)}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        
    except Exception as e:
        logger.error(f"   ❌ [REQ-{req_id}] Erreur technique action: {str(e)}")
        import traceback
        logger.debug(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors du traitement de l'action: {str(e)}"
        )

# ==============================================================================
# 3. INDICES (Hints)
# ==============================================================================

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
    req_id = str(uuid.uuid4())[:8]
    logger.info(f"📥 [REQ-{req_id}] POST /request-hint | Session: {session_id}")

    try:
        hint_type, hint_content = tutor_service.provide_hint(
            db=db,
            session_id=session_id
        )
        
        response = schemas.simulation.HintResponse(
            hint_type=hint_type,
            content=hint_content,
            cost_penalty=5 
        )
        
        logger.info(f"   ✅ [REQ-{req_id}] Indice fourni ({hint_type})")
        return response

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"   ❌ [REQ-{req_id}] Erreur indice: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Impossible de générer un indice."
        )

# ==============================================================================
# 4. SOUMISSION FINALE (Mode Sémantique)
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
    Accepte maintenant du texte libre qui sera analysé sémantiquement par l'IA.
    """
    req_id = str(uuid.uuid4())[:8]
    start_time = time.time()
    
    logger.info(f"📥 [REQ-{req_id}] POST /submit | Session: {session_id}")
    
    # LOGS SÉMANTIQUES : On affiche ce que l'étudiant a écrit
    diag_text = submission_data.diagnosed_pathology_text
    treat_text = submission_data.prescribed_treatment_text
    # Tronquage pour l'affichage propre
    treat_preview = treat_text[:50] + "..." if len(treat_text) > 50 else treat_text
    
    logger.info(f"   📝 Diagnostic soumis : '{diag_text}'")
    logger.info(f"   💊 Traitement soumis : '{treat_preview}'")

    try:
        # Appel au service d'évaluation (IA Juge)
        eval_result, feedback, recommendation = tutor_service.evaluate_submission(
            db=db,
            session_id=session_id,
            submission_data=submission_data
        )

        response = schemas.simulation.SubmissionResponse(
            evaluation=eval_result,
            feedback_global=feedback,
            recommendation_next_step=recommendation,
            # On pourrait ajouter ici les métriques finales calculées
            session_duration_seconds=int(time.time() - start_time) 
        )
        
        duration = time.time() - start_time
        logger.info(f"   🏆 [REQ-{req_id}] Évaluation terminée. Note: {eval_result.score_total}/20 ({duration:.2f}s)")
        
        return response

    except ValueError as e:
        logger.warning(f"   ⚠️ [REQ-{req_id}] Données invalides (404): {str(e)}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.critical(f"   ❌ [REQ-{req_id}] Erreur critique évaluation (500): {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de l'évaluation: {str(e)}"
        )
    

@router.get(
    "/learners/{learner_id}/history",
    response_model=schemas.simulation.LearnerDetailedHistoryResponse,
    summary="Obtenir l'historique détaillé par catégorie"
)
def get_learner_detailed_history(
    learner_id: int,
    db: Session = Depends(get_db)
):
    """
    Renvoie l'historique complet des sessions de l'apprenant, regroupé par spécialité médicale (catégorie).
    
    Structure de retour :
    - learner_id
    - historique_par_categorie: [
        {
            "categorie": "Cardiologie",
            "moyenne_categorie": 14.5,
            "sessions": [ ...liste des sessions... ]
        },
        ...
    ]
    """
    try:
        return tutor_service.get_learner_history_by_category(db=db, learner_id=learner_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Erreur historique apprenant: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Erreur lors de la génération de l'historique."
        )