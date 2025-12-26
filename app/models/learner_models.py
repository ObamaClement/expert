from sqlalchemy import Column, Integer, String, Float, ForeignKey, JSON, TIMESTAMP, text, Boolean
from sqlalchemy.orm import relationship
from .base import Base

class Learner(Base):
    __tablename__ = "learners"

    id = Column(Integer, primary_key=True, index=True)
    matricule = Column(String(50), unique=True, index=True)
    nom = Column(String(255))
    email = Column(String(255), unique=True, index=True)
    niveau_etudes = Column(String(50)) # Med 3, Interne...
    specialite_visee = Column(String(100))
    langue_preferee = Column(String(10), default="fr")
    date_inscription = Column(TIMESTAMP, server_default=text("now()"))

    # Relations
    competency_mastery = relationship("LearnerCompetencyMastery", back_populates="learner")
    misconceptions = relationship("LearnerMisconception", back_populates="learner")
    sessions = relationship("SimulationSession", back_populates="learner")


class LearnerCompetencyMastery(Base):
    __tablename__ = "learner_competency_mastery"

    id = Column(Integer, primary_key=True, index=True)
    learner_id = Column(Integer, ForeignKey("learners.id"), nullable=False)
    competence_id = Column(Integer, ForeignKey("competences_cliniques.id"), nullable=False)
    
    mastery_level = Column(Float, default=0.0) # Probabilité BKT (0-1)
    confidence = Column(Float, default=0.0) # Certitude du système
    last_practice_date = Column(TIMESTAMP)
    nb_success = Column(Integer, default=0)
    nb_failures = Column(Integer, default=0)
    streak_correct = Column(Integer, default=0)

    learner = relationship("Learner", back_populates="competency_mastery")
    competence = relationship("Competence") # Lien vers Module Expert


class LearnerCognitiveProfile(Base):
    __tablename__ = "learner_cognitive_profiles"

    id = Column(Integer, primary_key=True)
    learner_id = Column(Integer, ForeignKey("learners.id"), unique=True)
    
    vitesse_assimilation = Column(Float)
    capacite_memoire_travail = Column(Float)
    tendance_impulsivite = Column(Float) # 0 (Réfléchi) - 1 (Impulsif)
    prefer_visual = Column(Boolean, default=False)
    
    learner = relationship("Learner")


class LearnerMisconception(Base):
    __tablename__ = "learner_misconceptions"

    id = Column(Integer, primary_key=True)
    learner_id = Column(Integer, ForeignKey("learners.id"))
    
    type_erreur = Column(String(255)) # ex: "Confond Virus/Bactérie"
    frequence_apparition = Column(Integer, default=1)
    resistance_correction = Column(Float, default=0.0) # 0-1
    detected_at = Column(TIMESTAMP, server_default=text("now()"))
    
    learner = relationship("Learner", back_populates="misconceptions")


class LearnerGoal(Base):
    __tablename__ = "learner_goals"
    id = Column(Integer, primary_key=True)
    learner_id = Column(Integer, ForeignKey("learners.id"))
    type_objectif = Column(String(100))
    domaine_cible = Column(String(100))
    date_limite = Column(TIMESTAMP)
    statut = Column(String(50)) # en_cours, atteint, abandonne


class LearnerPreference(Base):
    __tablename__ = "learner_preferences"
    id = Column(Integer, primary_key=True)
    learner_id = Column(Integer, ForeignKey("learners.id"))
    cle = Column(String(100))
    valeur = Column(String(255))


class LearnerAchievement(Base):
    __tablename__ = "learner_achievements"
    id = Column(Integer, primary_key=True)
    learner_id = Column(Integer, ForeignKey("learners.id"))
    badge_id = Column(String(100))
    date_obtention = Column(TIMESTAMP, server_default=text("now()"))


class LearnerStrategy(Base):
    __tablename__ = "learner_strategies"
    id = Column(Integer, primary_key=True)
    learner_id = Column(Integer, ForeignKey("learners.id"))
    strategy_name = Column(String(100)) # ex: "Gaming", "Help Seeking"
    frequency = Column(Integer)
    effectiveness = Column(Float)