from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from uuid import UUID

# Nous importons le schéma existant pour un cas clinique complet
# car nous devrons le renvoyer lorsque la session commence.
from .clinical_case import ClinicalCase

# ==============================================================================
# SCHÉMAS POUR LE DÉMARRAGE D'UNE SESSION
# ==============================================================================

class SessionStartRequest(BaseModel):
    """
    Schéma pour la requête de démarrage d'une nouvelle session de simulation.
    """
    learner_id: int = Field(..., description="L'ID de l'apprenant qui commence la session.")
    category: str = Field(..., description="La catégorie de pathologie choisie par l'apprenant (ex: 'Cardiologie').")


class SessionStartResponse(BaseModel):
    """
    Schéma pour la réponse envoyée après la création réussie d'une session.
    """
    session_id: UUID = Field(..., description="L'ID unique de la session qui vient d'être créée.")
    session_type: str = Field(..., description="Le type de session déterminé par le tuteur (test, formative, sommative).")
    clinical_case: ClinicalCase = Field(..., description="Les détails complets du cas clinique sélectionné.")

    class Config:
        from_attributes = True

# ==============================================================================
# SCHÉMAS POUR LES ACTIONS DE L'APPRENANT
# ==============================================================================

class LearnerActionRequest(BaseModel):
    """
    Schéma pour une action effectuée par l'apprenant pendant la simulation.
    """
    action_type: str = Field(..., description="Le type d'action (ex: 'request_vitals', 'request_exam').")
    action_name: str = Field(..., description="Le nom spécifique de l'action (ex: 'Tension Artérielle', 'Radiographie Thoracique').")
    justification: Optional[str] = Field(None, description="La justification de l'apprenant pour demander cet examen.")


class LearnerActionResponse(BaseModel):
    """
    Schéma pour la réponse à une action de l'apprenant.
    """
    action_type: str = Field(..., description="Le type d'action qui a été traitée.")
    action_name: str = Field(..., description="Le nom de l'action traitée.")
    result: Dict[str, Any] = Field(..., description="Le résultat de l'action, généré par l'IA (ex: {'valeur': '120/80 mmHg'}).")
    feedback: Optional[str] = Field(None, description="Un feedback immédiat du tuteur sur la pertinence de l'action.")

# ==============================================================================
# SCHÉMA POUR LA RÉPONSE D'INDICE
# ==============================================================================

class HintResponse(BaseModel):
    """
    Schéma pour la réponse contenant un indice fourni par le tuteur.
    """
    hint_type: str = Field(..., description="Le type d'indice (ex: 'simple_rappel', 'question_socratique').")
    content: str = Field(..., description="Le contenu textuel de l'indice.")

# ==============================================================================
# SCHÉMAS POUR LA SOUMISSION ET L'ÉVALUATION FINALE
# ==============================================================================

class SubmissionRequest(BaseModel):
    """
    Schéma pour la soumission finale de l'apprenant (diagnostic et traitement).
    """
    diagnosed_pathology_id: int = Field(..., description="L'ID de la pathologie principale diagnostiquée par l'apprenant.")
    prescribed_medication_ids: List[int] = Field(default_factory=list, description="Liste des IDs des médicaments prescrits.")


class EvaluationResult(BaseModel):
    """
    Détaille les différentes composantes du score final.
    """
    score_diagnostic: float = Field(..., description="Score pour la justesse du diagnostic (0 à 10).")
    score_therapeutique: float = Field(..., description="Score pour la pertinence du traitement (0 à 5).")
    score_demarche: float = Field(..., description="Score pour la démarche (examens pertinents, consultation des images) (0 à 5).")
    score_total: float = Field(..., description="Score total sur 20.")


class SubmissionResponse(BaseModel):
    """
    Réponse de l'API après l'évaluation de la soumission de l'apprenant.
    """
    evaluation: EvaluationResult = Field(..., description="Le détail du score obtenu.")
    feedback_global: str = Field(..., description="Un commentaire global sur la performance.")
    recommendation_next_step: str = Field(..., description="Recommandation pour la suite (ex: refaire un cas similaire, passer au niveau supérieur).")