from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    JSON,
    TIMESTAMP,
    Boolean,
    Date,
    ForeignKey,
    text
)
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector

from .base import Base


class ImageMedicale(Base):
    """
    Modèle SQLAlchemy pour la table des images médicales.
    Catalogue toutes les images (radios, scanners, etc.) avec leurs métadonnées.
    """
    __tablename__ = "images_medicales"

    id = Column(Integer, primary_key=True, index=True)

    # --- Classification et Liaison ---
    type_examen = Column(String(100), nullable=False, index=True, comment="Ex: Radiographie, Échographie, Scanner")
    sous_type = Column(String(100), comment="Ex: Thorax, Abdomen, Crâne")
    pathologie_id = Column(Integer, ForeignKey("pathologies.id"), nullable=True, index=True)

    # --- Gestion du Fichier ---
    fichier_url = Column(String(500), nullable=False, comment="URL vers le fichier (S3, stockage local, etc.)")
    fichier_miniature_url = Column(String(500), comment="URL vers une version miniature de l'image")
    format_image = Column(String(20), comment="Ex: DICOM, PNG, JPEG")
    taille_ko = Column(Integer)
    resolution = Column(String(50))

    # --- Métadonnées Cliniques ---
    description = Column(Text, comment="Description générale de l'image ou du cas")
    signes_radiologiques = Column(JSON, comment="Signes spécifiques visibles (ex: opacité, épanchement)")
    annotations = Column(JSON, comment="Coordonnées et descriptions de zones d'intérêt")
    interpretation_experte = Column(Text, comment="Compte-rendu d'un radiologue expert")
    diagnostic_differentiel = Column(JSON, comment="Autres diagnostics possibles basés sur l'image")

    # --- Métadonnées Pédagogiques ---
    niveau_difficulte = Column(Integer, comment="Difficulté d'interprétation de l'image (1-5)")
    qualite_image = Column(Integer, comment="Qualité technique de l'image (1-5)")

    # --- Intelligence Artificielle ---
    embedding_vision = Column(Vector(384), nullable=True, comment="Vecteur d'embedding pour la recherche par similarité visuelle")

    # --- Validation et Horodatage ---
    valide_expert = Column(Boolean, default=False)
    expert_validateur = Column(String(255))
    date_validation = Column(Date)
    created_at = Column(TIMESTAMP, nullable=False, server_default=text("now()"))

    # --- Relations ---
    # Permet d'accéder à l'objet Pathologie depuis une ImageMedicale
    pathologie = relationship("Disease") # Nous n'avons pas besoin de back_populates ici pour l'instant

    def __repr__(self) -> str:
        return f"<ImageMedicale(id={self.id}, type='{self.type_examen}')>"
