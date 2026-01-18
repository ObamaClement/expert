# ==============================================================================
# FICHIER D'INITIALISATION DU PACKAGE 'schemas'
# ------------------------------------------------------------------------------
# Ce fichier a deux rôles principaux :
# 1. Il signale à Python que le dossier 'schemas' est un "package", c'est-à-dire
#    un ensemble de modules qui peuvent être importés.
# 2. Il définit ce qui est accessible publiquement lorsque l'on importe 'schemas'.
#    C'est le "hall d'entrée" du package.
# ==============================================================================

# --- IMPORTS EXISTANTS (validés) ---
# Chaque ligne rend des classes spécifiques directement accessibles
# depuis le package 'schemas'.
# Exemple : `from app import schemas` puis `schemas.Symptom`

from .symptom import SymptomCreate, SymptomBase, SymptomUpdate, Symptom
from .disease import DiseaseCreate, DiseaseBase, DiseaseUpdate, Disease
from .medication import MedicationCreate, MedicationBase, MedicationUpdate, Medication
from .media import ImageMedicaleBase, ImageMedicaleUpdate, ImageMedicale
from .clinical_case import ClinicalCaseCreate, ClinicalCaseBase, ClinicalCaseUpdate, ClinicalCase
from .expert_strategy import ExpertStrategyCreate, ExpertStrategyBase, ExpertStrategyUpdate, ExpertStrategy

# --- NOUVEAUX IMPORTS (pour corriger les erreurs) ---

# 1. CORRECTION POUR 'chat_message'
# Cette ligne importe les classes `ChatMessage` et `ChatMessageCreate` depuis le
# fichier `chat_message.py`. Sans cela, l'erreur `AttributeError: module 'app.schemas'
# has no attribute 'ChatMessageCreate'` se produit.
from .chat_message import ChatMessage, ChatMessageCreate

# 2. IMPORTATION DES MODULES COMPLETS
# Pour les schémas complexes comme 'relations' et 'simulation', il est souvent
# plus propre d'importer le module entier.
# Cela signifie qu'on y accédera avec une syntaxe comme `schemas.simulation.SessionStartRequest`.
# C'est ce que nous avons déjà fait dans le code des services.

# Rend le module 'relations.py' accessible via `schemas.relations`
from . import relations

# Rend le module 'simulation.py' accessible via `schemas.simulation`.
# C'est cette ligne qui a corrigé la première erreur `AttributeError` que vous aviez.
from . import simulation

# ==============================================================================
# FIN DU FICHIER
# ------------------------------------------------------------------------------
# Avec ce fichier, l'application sait maintenant où trouver TOUS les schémas
# Pydantic dont elle a besoin, que ce soit par import direct de classe
# (ex: schemas.Symptom) ou par import de module (ex: schemas.simulation.HintResponse).
# ==============================================================================