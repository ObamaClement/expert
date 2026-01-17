from .symptom import SymptomCreate,SymptomBase,SymptomUpdate, Symptom
from .disease import DiseaseCreate,DiseaseBase,DiseaseUpdate, Disease
from . import relations
from .medication import MedicationCreate,MedicationBase,MedicationUpdate, Medication
from .media import ImageMedicaleBase,ImageMedicaleUpdate, ImageMedicale
from .clinical_case import ClinicalCaseCreate,ClinicalCaseBase,ClinicalCaseUpdate, ClinicalCase
from .expert_strategy import ExpertStrategyCreate,ExpertStrategyBase,ExpertStrategyUpdate, ExpertStrategy

# === LIGNE À AJOUTER À LA FIN DU FICHIER ===
from .chat_message import ChatMessage, ChatMessageCreate, ChatMessageBase