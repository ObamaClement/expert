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
    
    # --- RELATION VERS INTERACTION LOG MISE EN COMMENTAIRE ---
    # Nous la réactiverons quand la table 'interaction_logs' sera créée.
    # logs = relationship("InteractionLog", back_populates="session")
    # ----------------------------------------------------

class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(UUID(as_uuid=True), ForeignKey("simulation_sessions.id"), nullable=False)
    
    timestamp = Column(TIMESTAMP, server_default=text("now()"))
    sender = Column(String(50), nullable=False) # student, patient, tutor
    content = Column(Text, nullable=False)
    message_metadata = Column(JSON)

    session = relationship("SimulationSession", back_populates="messages")