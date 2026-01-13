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
    ARRAY,
    DECIMAL,
    text
)
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector

from .base import Base


class ClinicalCase(Base):
    """
    Modèle SQLAlchemy pour la table des cas cliniques enrichis.
    C'est l'objet central utilisé pour les scénarios d'apprentissage.
    """
    __tablename__ = "cas_cliniques_enrichis"

    id = Column(Integer, primary_key=True, index=True)

    # --- Identification et Intégrité ---
    code_fultang = Column(String(100), unique=True, index=True, comment="Identifiant unique provenant de Fultang (ou synthétique)")
    hash_integrite = Column(String(64), nullable=True, comment="SHA-256 pour la preuve d'intégrité des données brutes")

    # --- Liaisons aux Connaissances de Base ---
    pathologie_principale_id = Column(Integer, ForeignKey("pathologies.id"), nullable=True, index=True)
    # pathologie_secondaires_ids = Column(ARRAY(Integer), comment="Liste d'IDs de pathologies comorbides")


    pathologies_secondaires_ids = Column(ARRAY(Integer), comment="Liste d'IDs de pathologies comorbides ou secondaires")

    # --- Données du Scénario ---
    donnees_brutes = Column(JSON, nullable=True, comment="Données originales (ex: de Fultang) avant traitement")
    presentation_clinique = Column(JSON, nullable=False, comment="Histoire du patient, symptômes présentés, etc.")
    donnees_paracliniques = Column(JSON, comment="Résultats des examens pour ce cas spécifique")
    evolution_patient = Column(Text, comment="Description de l'évolution du patient pendant le cas")
    
    # --- Liaisons Multimédia ---
    images_associees_ids = Column(ARRAY(Integer), comment="Liste des IDs des images de la table 'images_medicales'")
    sons_associes_ids = Column(ARRAY(Integer), comment="Liste des IDs des sons de la table 'sons_medicaux'")

    # --- Liaisons Thérapeutiques ---
    # ordonnance_utilisee_id = Column(Integer, ForeignKey("ordonnances_types.id"), nullable=True)
    medicaments_prescrits = Column(JSON, comment="Liste des médicaments prescrits dans ce cas")

    # --- Métadonnées Pédagogiques ---
    niveau_difficulte = Column(Integer, default=3, comment="Difficulté du cas (1-5)")
    duree_estimee_resolution_min = Column(Integer, comment="Temps estimé pour résoudre le cas")
    objectifs_apprentissage = Column(JSON, comment="Liste des compétences à acquérir")
    competences_requises = Column(JSON, comment="Mapping Q-Matrix pour ce cas")

    valide_expert = Column(Boolean, default=False)
    

    statut_publication = Column(
        String(50), 
        default="brouillon", 
        nullable=False,
        index=True,
        comment="Statut du cas: brouillon, en_revision, valide, archive"
    )
    
    # --- MISE À JOUR DU CHAMP EXISTANT ---
    # On garde le lien vers l'expert qui valide
    

    # Clé étrangère vers la table experts
    expert_validateur_id = Column(Integer, ForeignKey("experts.id"), nullable=True)
    

    


    # Relation avec ExpertUser
    expert_validateur = relationship("ExpertUser", back_populates="cas_valides")
    date_validation = Column(Date)

    qualite_donnees = Column(Integer, comment="Qualité des données sources (1-5)")

    # --- Métriques d'Utilisation ---
    nb_utilisations = Column(Integer, default=0)
    note_moyenne_apprenants = Column(DECIMAL(3, 2))
    taux_succes_diagnostic = Column(DECIMAL(5, 2))
    
    # --- Intelligence Artificielle ---
    embedding_texte = Column(Vector(384), nullable=True, comment="Embedding de la description textuelle du cas")
    embedding_global = Column(Vector(1536), nullable=True, comment="Embedding multimodal fusionné (texte+image+son)")
    
    # --- Horodatage ---
    created_at = Column(TIMESTAMP, nullable=False, server_default=text("now()"))
    updated_at = Column(TIMESTAMP, nullable=False, server_default=text("now()"), onupdate=text("now()"))

    # --- Relations ---
    pathologie_principale = relationship("Disease")

    

    def __repr__(self) -> str:
        return f"<ClinicalCase(id={self.id}, code='{self.code_fultang}')>"