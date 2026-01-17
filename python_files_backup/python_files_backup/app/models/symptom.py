from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Boolean,
    JSON,
    TIMESTAMP,
    text
)
from pgvector.sqlalchemy import Vector
from sqlalchemy.orm import relationship

from .base import Base


class Symptom(Base):
    """
    Modèle SQLAlchemy pour la table des symptômes.

    Cette table est le catalogue central de tous les symptômes connus par le système expert.
    Elle inclut des informations détaillées pour permettre un raisonnement clinique fin
    et des recherches sémantiques.
    """
    __tablename__ = "symptomes"

    id = Column(Integer, primary_key=True, index=True)

    # --- Identification et Catégorisation ---
    nom = Column(String(255), nullable=False, unique=True, index=True)
    nom_local = Column(String(255), comment="Nom vernaculaire ou local, ex: 'Ntou-tou' pour la toux")
    categorie = Column(String(100), index=True, comment="Catégorie fonctionnelle (ex: Respiratoire, Neurologique, Digestif)")
    type_symptome = Column(String(50), comment="Type de symptôme (ex: Subjectif, Objectif, Signe clinique)")

    # --- Description et Contexte Clinique ---
    description = Column(Text, comment="Description détaillée du symptôme et de sa signification clinique.")
    questions_anamnese = Column(JSON, comment="Liste structurée de questions pour explorer ce symptôme (ex: PQRST)")
    signes_alarme = Column(Boolean, default=False, nullable=False, comment="Indique si ce symptôme est un signe de gravité ('red flag')")

    # --- Intelligence Artificielle ---
    embedding_vector = Column(Vector(384), nullable=True, comment="Vecteur d'embedding pour la recherche sémantique (ex: BioBERT)")

    # --- Horodatage ---
    created_at = Column(TIMESTAMP, nullable=False, server_default=text("now()"))
    updated_at = Column(TIMESTAMP, nullable=False, server_default=text("now()"), onupdate=text("now()"))

    # --- Relations ---
    # Relation vers la table d'association 'pathologie_symptomes'
    # 'back_populates' assure la synchronisation de la relation des deux côtés.
    # 'cascade' signifie que si un symptôme est supprimé, ses associations le seront aussi.
    pathologies = relationship(
        "PathologieSymptome",
        back_populates="symptome",
        cascade="all, delete-orphan"
    )
    traitements = relationship(
        "TraitementSymptome",
        back_populates="symptome",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Symptom(id={self.id}, nom='{self.nom}')>"