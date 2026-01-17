from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    JSON,
    TIMESTAMP,
    ForeignKey,
    DECIMAL,
    text
)
from sqlalchemy.orm import relationship

from .base import Base


class Competence(Base):
    """
    Modèle SQLAlchemy pour les compétences cliniques (Knowledge Components).
    """
    __tablename__ = "competences_cliniques"

    id = Column(Integer, primary_key=True, index=True)

    # --- Identification ---
    code_competence = Column(String(50), unique=True, nullable=False, index=True, comment="Code unique (ex: 'ANAMNESE_DOULEUR')")
    nom = Column(String(255), nullable=False)
    categorie = Column(String(100), index=True, comment="Ex: Anamnese, Examen_physique, Raisonnement, Technique")
    
    # --- Pédagogie ---
    niveau_bloom = Column(Integer, comment="Niveau dans la taxonomie de Bloom (1-6)")
    description = Column(Text)
    objectifs_apprentissage = Column(JSON, comment="Liste détaillée des objectifs")
    criteres_maitrise = Column(JSON, comment="Critères pour valider la compétence")
    
    # --- Hiérarchie (Parent/Enfant) ---
    parent_competence_id = Column(Integer, ForeignKey("competences_cliniques.id"), nullable=True)
    ordre_apprentissage = Column(Integer, default=0)

    # --- Horodatage ---
    created_at = Column(TIMESTAMP, nullable=False, server_default=text("now()"))

    # --- Relations ---
    children = relationship("Competence", 
                          back_populates="parent",
                          cascade="all, delete-orphan")
    
    parent = relationship("Competence", 
                        back_populates="children",
                        remote_side=[id])

    # Relation vers les prérequis
    prerequis = relationship(
        "Competence",
        secondary="prerequis_competences",
        primaryjoin="Competence.id==prerequis_competences.c.competence_id",
        secondaryjoin="Competence.id==prerequis_competences.c.prerequis_id",
        backref="est_prerequis_pour"
    )

    def __repr__(self) -> str:
        return f"<Competence(code='{self.code_competence}', nom='{self.nom}')>"


class PrerequisCompetence(Base):
    """
    Table d'association pour le graphe de prérequis entre compétences.
    Permet de dire : "Pour apprendre A, il faut d'abord maîtriser B".
    """
    __tablename__ = "prerequis_competences"

    id = Column(Integer, primary_key=True)
    
    # La compétence cible (Celle qu'on veut apprendre)
    competence_id = Column(Integer, ForeignKey("competences_cliniques.id"), nullable=False)
    
    # La compétence prérequise (Celle qu'on doit déjà avoir)
    prerequis_id = Column(Integer, ForeignKey("competences_cliniques.id"), nullable=False)
    
    # --- Métadonnées de la relation ---
    type_relation = Column(String(50), default="STRICT", comment="STRICT, RECOMMANDE, SUPPORTIF")
    force_relation = Column(DECIMAL(3, 2), default=1.0, comment="Force du lien (0-1)")

    def __repr__(self) -> str:
        return f"<Prerequis(target={self.competence_id}, needed={self.prerequis_id})>"