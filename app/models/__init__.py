from .base import Base
from .symptom import Symptom
from .disease import Disease
from .medication import Medication
from .media import ImageMedicale
from .clinical_case import ClinicalCase
from .expert_strategy import ExpertStrategy
from .relations import PathologieSymptome, TraitementPathologie, TraitementSymptome
from .prerequisite import Competence, PrerequisCompetence

# --- AJOUTER CES LIGNES SI ELLES MANQUENT ---
from .learner_models import (
    Learner, LearnerCompetencyMastery, LearnerCognitiveProfile, 
    LearnerMisconception, LearnerGoal, LearnerPreference, 
    LearnerAchievement, LearnerStrategy
)
from .tracking_models import (
    SimulationSession, InteractionLog, ChatMessage, LearnerAffectiveState
)
from .tutor_models import (
    LearningPath, TutorDecision, TutorStrategiesHistory, 
    TutorScaffoldingState, TutorSocraticState, TutorMotivationalState, 
    TutorFeedbackLog
)
from .expert_user import ExpertUser