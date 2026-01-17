from sqlalchemy import Column, Integer, String, Float, ForeignKey, JSON, TIMESTAMP, text, Boolean, Text
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
from .base import Base

class SimulationSession(Base):
    __tablename__ = "simulation_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    learner_id = Column(Integer, ForeignKey("learners.id"), nullable=False)
    cas_clinique_id = Column(Integer, ForeignKey("cas_cliniques_enrichis.id"), nullable=False)
    
    start_time = Column(TIMESTAMP, server_default=text("now()"))
    end_time = Column(TIMESTAMP)
    score_final = Column(Float)
    temps_total = Column(Integer)
    cout_virtuel_genere = Column(Integer)
    statut = Column(String(50), default="en_cours")
    raison_fin = Column(String(100))
    current_stage = Column(String(50))
    context_state = Column(JSON)

    learner = relationship("Learner", back_populates="sessions")
    cas_clinique = relationship("ClinicalCase")
    
    # --- Relations ---
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")
    tutor_decisions = relationship("TutorDecision", back_populates="session")
    
    # --- RELATION VERS INTERACTION LOG CORRIGÉE ET ACTIVÉE ---
    logs = relationship("InteractionLog", back_populates="session", cascade="all, delete-orphan")
    # ----------------------------------------------------

class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(UUID(as_uuid=True), ForeignKey("simulation_sessions.id"), nullable=False)
    
    timestamp = Column(TIMESTAMP, server_default=text("now()"))
    sender = Column(String(50), nullable=False) # student, patient, tutor
    content = Column(Text, nullable=False)
    
    # Suppression des champs qui n'existent plus dans la migration la plus récente
    # intention_detectee = Column(String(100))
    # sentiment_analyse = Column(String(50))
    message_metadata = Column(JSON)

    session = relationship("SimulationSession", back_populates="messages")


# === CLASSE 'InteractionLog' AJOUTÉE ===
# Ce modèle manquait, ce qui causait l'ImportError.
class InteractionLog(Base):
    __tablename__ = "interaction_logs"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(UUID(as_uuid=True), ForeignKey("simulation_sessions.id"))
    
    timestamp = Column(TIMESTAMP, server_default=text("now()"))
    action_category = Column(String(50))
    action_type = Column(String(100))
    action_content = Column(JSON)
    response_latency = Column(Integer)
    charge_cognitive_estimee = Column(Float)
    est_pertinent = Column(Boolean)

    session = relationship("SimulationSession", back_populates="logs")


# === CLASSE 'LearnerAffectiveState' AJOUTÉE ===
# Ce modèle était également importé dans __init__.py mais manquant dans ce fichier.
class LearnerAffectiveState(Base):
    __tablename__ = "learner_affective_states"

    id = Column(Integer, primary_key=True)
    session_id = Column(UUID(as_uuid=True), ForeignKey("simulation_sessions.id"))
    timestamp = Column(TIMESTAMP, server_default=text("now()"))
    stress_level = Column(Float)
    confidence_level = Column(Float)
    motivation_level = Column(Float)
    frustration_level = Column(Float)

    session = relationship("SimulationSession")