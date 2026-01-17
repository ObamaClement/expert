from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    JSON,
    TIMESTAMP,
    DECIMAL,
    text
)
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector

from .base import Base


class Disease(Base):
    """
    Modèle SQLAlchemy pour la table des pathologies (maladies).

    Cette table contient toutes les informations détaillées sur chaque maladie
    connue par le système, y compris le contexte local, les caractéristiques
    cliniques et les vecteurs pour l'IA.
    """
    __tablename__ = "pathologies"

    id = Column(Integer, primary_key=True, index=True)

    # --- Identification et Classification ---
    code_icd10 = Column(String(20), unique=True, index=True, comment="Code international de la maladie (CIM-10)")
    nom_fr = Column(String(255), nullable=False, index=True)
    nom_en = Column(String(255))
    nom_local = Column(String(255), comment="Noms locaux ou courants au Cameroun")
    categorie = Column(String(100), index=True, comment="Ex: Infectieuse, Chronique, Parasitaire")

    # --- Données Cliniques et Épidémiologiques ---
    prevalence_cameroun = Column(DECIMAL(5, 2), comment="Prévalence en % dans le contexte camerounais")
    niveau_gravite = Column(Integer, comment="Échelle de 1 (bénin) à 5 (critique)")
    description = Column(Text)
    physiopathologie = Column(Text, comment="Mécanisme de la maladie")
    evolution_naturelle = Column(Text, comment="Comment la maladie évolue sans traitement")
    complications = Column(JSON, comment="Complications possibles")
    facteurs_risque = Column(JSON, comment="Facteurs de risque associés")
    prevention = Column(Text, comment="Mesures de prévention")

    # --- Intelligence Artificielle ---
    embedding_vector = Column(Vector(384), nullable=True, comment="Vecteur d'embedding pour la recherche sémantique")

    # --- Horodatage ---
    created_at = Column(TIMESTAMP, nullable=False, server_default=text("now()"))
    updated_at = Column(TIMESTAMP, nullable=False, server_default=text("now()"), onupdate=text("now()"))

    # --- Relations ---
    # Nous préparons le terrain pour la future relation avec les symptômes.
    # Pour l'instant, elle reste en commentaire pour éviter les erreurs d'import circulaire.
    symptomes = relationship(
         "PathologieSymptome",
         back_populates="pathologie",
         cascade="all, delete-orphan"
    
     )
    
    traitements = relationship(
        "TraitementPathologie",
        back_populates="pathologie",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Disease(id={self.id}, nom_fr='{self.nom_fr}')>"