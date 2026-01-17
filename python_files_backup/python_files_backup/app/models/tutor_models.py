from sqlalchemy import Column, Integer, String, Text, Float, ForeignKey, JSON, TIMESTAMP, text, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from .base import Base

class LearningPath(Base):
    __tablename__ = "learning_paths"

    id = Column(Integer, primary_key=True, index=True)
    learner_id = Column(Integer, ForeignKey("learners.id"), nullable=False)
    
    algorithme_recommandation = Column(String(100))
    ordered_case_ids = Column(JSON, comment="Liste ordonnée des IDs des cas") 
    progression = Column(Float, default=0.0)
    status = Column(String(50), default="in_progress")
    created_at = Column(TIMESTAMP, server_default=text("now()"))

    learner = relationship("Learner")


class TutorDecision(Base):
    __tablename__ = "tutor_decisions"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(UUID(as_uuid=True), ForeignKey("simulation_sessions.id"))
    trigger_event_id = Column(Integer, ForeignKey("interaction_logs.id"), nullable=True)
    
    timestamp = Column(TIMESTAMP, server_default=text("now()"))
    strategy_used = Column(String(100)) # Socratique, Scaffolding...
    action_choisie = Column(String(100)) # Hint, Encouragement
    intervention_content = Column(Text)
    rationale = Column(JSON) # Pourquoi j'ai fait ça ?
    succes_intervention = Column(Boolean, nullable=True)

    session = relationship("SimulationSession", back_populates="tutor_decisions")


class TutorStrategiesHistory(Base):
    __tablename__ = "tutor_strategies_history"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(UUID(as_uuid=True), ForeignKey("simulation_sessions.id"))
    timestamp = Column(TIMESTAMP, server_default=text("now()"))
    strategy_name = Column(String(100))
    relevance_score = Column(Float)


class TutorScaffoldingState(Base):
    __tablename__ = "tutor_scaffolding_state"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(UUID(as_uuid=True), ForeignKey("simulation_sessions.id"))
    competence_cible_id = Column(Integer, ForeignKey("competences_cliniques.id"))
    current_level = Column(Integer, default=0)
    indices_deja_donnes = Column(JSON)


class TutorSocraticState(Base):
    __tablename__ = "tutor_socratic_state"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(UUID(as_uuid=True), ForeignKey("simulation_sessions.id"))
    tactic_used = Column(String(100))
    target_concept = Column(String(255))
    step_in_dialogue = Column(Integer)


class TutorMotivationalState(Base):
    __tablename__ = "tutor_motivational_state"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(UUID(as_uuid=True), ForeignKey("simulation_sessions.id"))
    intervention_type = Column(String(100))
    emotional_state_before = Column(JSON)


class TutorFeedbackLog(Base):
    __tablename__ = "tutor_feedback_logs"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(UUID(as_uuid=True), ForeignKey("simulation_sessions.id"))
    feedback_type = Column(String(50))
    content = Column(Text)