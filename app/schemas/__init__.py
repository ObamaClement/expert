# Importe les schémas existants pour qu'ils restent accessibles
from .symptom import SymptomCreate, SymptomBase, SymptomUpdate, Symptom
from .disease import DiseaseCreate, DiseaseBase, DiseaseUpdate, Disease
from .medication import MedicationCreate, MedicationBase, MedicationUpdate, Medication
from .media import ImageMedicaleBase, ImageMedicaleUpdate, ImageMedicale
from .clinical_case import ClinicalCaseCreate, ClinicalCaseBase, ClinicalCaseUpdate, ClinicalCase
from .expert_strategy import ExpertStrategyCreate, ExpertStrategyBase, ExpertStrategyUpdate, ExpertStrategy

# Importe les modules de schémas pour les relations et la simulation
from . import relations

# --- LIGNE AJOUTÉE ---
# En important le module 'simulation' ici, on le rend accessible via 'schemas.simulation'
from . import simulation

# --- AJOUT POUR LE CHAT (BONNE PRATIQUE) ---
# Il est probable que ce module soit aussi nécessaire ailleurs
from . import chat_message