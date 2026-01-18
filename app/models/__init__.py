# ==============================================================================
# FICHIER D'INITIALISATION DU PACKAGE 'models'
# ------------------------------------------------------------------------------
# Ce fichier centralise l'importation de toutes les classes de modèles SQLAlchemy,
# les rendant facilement accessibles depuis le reste de l'application via
# l'import `from app import models`.
# ==============================================================================

# --- Modèle de Base ---
from .base import Base

# --- Modèles du Domaine Expert ---
from .symptom import Symptom
from .disease import Disease
from .medication import Medication
from .media import ImageMedicale
from .clinical_case import ClinicalCase
from .expert_strategy import ExpertStrategy
from .relations import PathologieSymptome, TraitementPathologie, TraitementSymptome
from .prerequisite import Competence, PrerequisCompetence
from .expert_user import ExpertUser

# --- Modèles de l'Apprenant ---
from .learner_models import (
    Learner,
    LearnerCompetencyMastery,
    LearnerCognitiveProfile,
    LearnerMisconception,
    LearnerGoal,
    LearnerPreference,
    LearnerAchievement,
    LearnerStrategy
)

# --- Modèles de Suivi (Tracking) ---
from .tracking_models import (
    SimulationSession,
    ChatMessage,
    # La ligne ci-dessous est la correction clé pour l'erreur actuelle
    InteractionLog,
    LearnerAffectiveState
)

# --- Modèles du Tuteur ---
from .tutor_models import (
    LearningPath,
    TutorDecision,
    TutorStrategiesHistory,
    TutorScaffoldingState,
    TutorSocraticState,
    TutorMotivationalState,
    TutorFeedbackLog
)

# ==============================================================================
# FIN DU FICHIER
# ==============================================================================