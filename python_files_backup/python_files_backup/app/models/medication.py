from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    JSON,
    TIMESTAMP,
    text
)
from pgvector.sqlalchemy import Vector
from sqlalchemy.orm import relationship
from .base import Base


class Medication(Base):
    """
    Modèle SQLAlchemy pour la table des médicaments.

    Cette table est le catalogue central de tous les médicaments connus par le système,
    incluant des informations pharmacologiques et contextuelles (disponibilité, coût).
    """
    __tablename__ = "medicaments"

    id = Column(Integer, primary_key=True, index=True)

    # --- Identification ---
    nom_commercial = Column(String(255), index=True)
    dci = Column(String(255), nullable=False, index=True, comment="Dénomination Commune Internationale")
    
    # --- Classification et Formulation ---
    classe_therapeutique = Column(String(255), index=True)
    forme_galenique = Column(String(100), comment="Ex: Comprimé, Sirop, Injectable")
    dosage = Column(String(100))
    voie_administration = Column(String(100), comment="Ex: Orale, IV, IM, Cutanée")

    # --- Informations Pharmacologiques ---
    mecanisme_action = Column(Text)
    indications = Column(JSON)
    contre_indications = Column(JSON)
    effets_secondaires = Column(JSON)
    interactions_medicamenteuses = Column(JSON)
    precautions_emploi = Column(Text)
    posologie_standard = Column(JSON, comment="Posologie standard par âge, poids, indication")

    # --- Contexte Local (Cameroun) ---
    disponibilite_cameroun = Column(String(50), comment="Ex: Urbain, Rural, CHU_uniquement")
    cout_moyen_fcfa = Column(Integer)
    statut_prescription = Column(String(50), comment="Ex: Prescription_obligatoire, OTC")

    # --- Intelligence Artificielle ---
    embedding_vector = Column(Vector(384), nullable=True, comment="Vecteur d'embedding pour la recherche de médicaments similaires")

    # --- Horodatage ---
    created_at = Column(TIMESTAMP, nullable=False, server_default=text("now()"))
    updated_at = Column(TIMESTAMP, nullable=False, server_default=text("now()"), onupdate=text("now()"))

    traitements_pathologies = relationship("TraitementPathologie", back_populates="medicament")
    traitements_symptomes = relationship("TraitementSymptome", back_populates="medicament")

    def __repr__(self) -> str:
        return f"<Medication(id={self.id}, dci='{self.dci}')>"