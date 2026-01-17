import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# --- MODIFICATION 1: Chargement de l'environnement ---
from dotenv import load_dotenv

# Ajoute la racine du projet au chemin de recherche de Python
sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), '..')))
# Charge le fichier .env qui se trouve à la racine du projet
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))
# -----------------------------------------------------


# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)


# --- MODIFICATION 2: Importation des Modèles ---
# Importer la 'Base' depuis notre application
from app.models.base import Base

# --- IMPORT DE TOUS LES MODÈLES POUR ALEMBIC ---
# Module Expert
from app.models.symptom import Symptom
from app.models.disease import Disease
from app.models.medication import Medication
from app.models.media import ImageMedicale
from app.models.relations import PathologieSymptome, TraitementPathologie, TraitementSymptome
from app.models.clinical_case import ClinicalCase
from app.models.expert_strategy import ExpertStrategy
from app.models.expert_user import ExpertUser
from app.models.prerequisite import Competence, PrerequisCompetence

# Module Apprenant
from app.models.learner_models import (
    Learner, LearnerCompetencyMastery, LearnerCognitiveProfile, 
    LearnerMisconception, LearnerGoal, LearnerPreference, 
    LearnerAchievement, LearnerStrategy
)

# Module Suivi (Tracking)
from app.models.tracking_models import (
    SimulationSession, InteractionLog, ChatMessage, LearnerAffectiveState
)

# Module Tuteur
from app.models.tutor_models import (
    LearningPath, TutorDecision, TutorStrategiesHistory, 
    TutorScaffoldingState, TutorSocraticState, TutorMotivationalState, 
    TutorFeedbackLog
)
# --------------------------------------------------

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = os.environ.get('DATABASE_URL')
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    # --- MODIFICATION 3: Configuration de l'Engine ---
    configuration = config.get_section(config.config_ini_section)
    configuration['sqlalchemy.url'] = os.environ.get('DATABASE_URL')
    
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    # -------------------------------------------------

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()