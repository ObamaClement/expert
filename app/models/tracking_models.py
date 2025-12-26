from sqlalchemy import Column, Integer, String, Float, ForeignKey, JSON, TIMESTAMP, Text, text, Boolean, BigInteger
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
    temps_total = Column(Integer) # secondes
    cout_virtuel_genere = Column(Integer)
    statut = Column(String(50), default="en_cours") # en_cours, termine, abandonne
    raison_fin = Column(String(100))

    # État courant du jeu (pour reprise)
    current_stage = Column(String(50)) # anamnèse, examen...
    context_state = Column(JSON) # État interne du patient virtuel

    learner = relationship("Learner", back_populates="sessions")
    cas_clinique = relationship("ClinicalCase")
    
    # Relations
    logs = relationship("InteractionLog", back_populates="session")
    messages = relationship("ChatMessage", back_populates="session")
    tutor_decisions = relationship("TutorDecision", back_populates="session")


class InteractionLog(Base):
    __tablename__ = "interaction_logs"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(UUID(as_uuid=True), ForeignKey("simulation_sessions.id"))
    
    timestamp = Column(TIMESTAMP, server_default=text("now()"))
    action_category = Column(String(50)) # Anamnèse, Examen...
    action_type = Column(String(100)) # PoseQuestion, ClicImage
    action_content = Column(JSON)
    response_latency = Column(Integer) # ms
    charge_cognitive_estimee = Column(Float)
    est_pertinent = Column(Boolean)
    
    session = relationship("SimulationSession", back_populates="logs")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(UUID(as_uuid=True), ForeignKey("simulation_sessions.id"))
    
    timestamp = Column(TIMESTAMP, server_default=text("now()"))
    sender = Column(String(50)) # student, patient, tutor
    content = Column(Text)
    intention_detectee = Column(String(100))
    sentiment_analyse = Column(String(50))
    message_metadata = Column(JSON) # tokens, model used...

    session = relationship("SimulationSession", back_populates="messages")


class LearnerAffectiveState(Base):
    __tablename__ = "learner_affective_states"

    id = Column(Integer, primary_key=True)
    session_id = Column(UUID(as_uuid=True), ForeignKey("simulation_sessions.id"))
    timestamp = Column(TIMESTAMP, server_default=text("now()"))
    
    stress_level = Column(Float) # 0-100
    confidence_level = Column(Float)
    motivation_level = Column(Float)
    frustration_level = Column(Float)