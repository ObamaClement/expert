from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from uuid import UUID

from .clinical_case import ClinicalCase

# ==============================================================================
# SCHÉMAS POUR LE DÉMARRAGE D'UNE SESSION
# ==============================================================================

class SessionStartRequest(BaseModel):
    learner_id: int = Field(..., description="L'ID de l'apprenant qui commence la session.")
    category: str = Field(..., description="La catégorie de pathologie choisie (ex: 'Cardiologie').")

class SessionStartResponse(BaseModel):
    session_id: UUID = Field(..., description="L'ID unique de la session créée.")
    session_type: str = Field(..., description="Le type de session (test, formative, sommative).")
    clinical_case: ClinicalCase = Field(..., description="Les détails complets du cas clinique sélectionné.")

    class Config:
        from_attributes = True

# ==============================================================================
# SCHÉMAS POUR LES ACTIONS DE L'APPRENANT
# ==============================================================================

class LearnerActionRequest(BaseModel):
    action_type: str = Field(..., description="Le type d'action (ex: 'parametres_vitaux', 'examen_complementaire').")
    action_name: str = Field(..., description="Le nom spécifique de l'action (ex: 'Prise des constantes', 'NFS').")
    justification: Optional[str] = Field(None, description="La justification de l'apprenant pour cette action.")

class LearnerActionResponse(BaseModel):
    action_type: str
    action_name: str
    result: Dict[str, Any] = Field(..., description="Le résultat de l'action (ex: rapport et conclusion d'un examen).")
    feedback: Optional[str] = Field(None, description="Un feedback immédiat du tuteur sur la pertinence de l'action.")

# ==============================================================================
# SCHÉMA POUR LA RÉPONSE D'INDICE
# ==============================================================================

class HintResponse(BaseModel):
    hint_type: str = Field(..., description="Le type d'indice (ex: 'question_socratique', 'indice_direct').")
    content: str = Field(..., description="Le contenu textuel de l'indice.")

# ==============================================================================
# SCHÉMAS POUR LA SOUMISSION ET L'ÉVALUATION FINALE
# ==============================================================================

class SubmissionRequest(BaseModel):
    diagnosed_pathology_id: int = Field(..., description="L'ID de la pathologie principale diagnostiquée.")
    prescribed_medication_ids: List[int] = Field(default_factory=list, description="Liste des IDs des médicaments prescrits.")

class EvaluationResult(BaseModel):
    """
    Détaille les différentes composantes du score final, sur un total de 20 points.
    """
    score_diagnostic: float = Field(..., description="Score pour la justesse du diagnostic (sur 10).")
    score_therapeutique: float = Field(..., description="Score pour la pertinence du traitement (sur 5).")
    score_demarche: float = Field(..., description="Score pour la démarche clinique (sur 5).")
    score_total: float = Field(..., description="Score total sur 20.")

class SubmissionResponse(BaseModel):
    """
    Réponse de l'API après l'évaluation de la soumission de l'apprenant.
    """
    evaluation: EvaluationResult = Field(..., description="Le détail du score obtenu.")
    feedback_global: str = Field(..., description="Un commentaire global sur la performance.")
    recommendation_next_step: str = Field(..., description="Recommandation pour la suite du parcours.")