from sqlalchemy import Column, Integer, String, Text, Boolean, TIMESTAMP, text
from sqlalchemy.orm import relationship
from .base import Base

class ExpertUser(Base):
    __tablename__ = "experts"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    nom_complet = Column(String(255))
    specialite = Column(String(100))
    hopital_affiliation = Column(String(255))
    role = Column(String(50), default="validateur") # superadmin, validateur, contributeur
    
    last_login = Column(TIMESTAMP)
    created_at = Column(TIMESTAMP, nullable=False, server_default=text("now()"))

    # Relation avec les cas cliniques validés
    cas_valides = relationship("ClinicalCase", back_populates="expert_validateur")