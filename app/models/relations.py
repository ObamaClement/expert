from sqlalchemy import (
    JSON,
    Column,
    Integer,
    ForeignKey,
    DECIMAL,
    String,
    Boolean,
    Text
)
from sqlalchemy.orm import relationship

from .base import Base


class PathologieSymptome(Base):
    """
    Modèle de la table d'association entre Pathologies et Symptômes.

    Cette table matérialise la relation "plusieurs-à-plusieurs" et permet de stocker
    des informations contextuelles sur le lien, telles que la probabilité
    d'apparition, la spécificité, etc.
    """
    __tablename__ = "pathologie_symptomes"

    id = Column(Integer, primary_key=True)

    # --- Clés Étrangères ---
    pathologie_id = Column(Integer, ForeignKey("pathologies.id"), nullable=False)
    symptome_id = Column(Integer, ForeignKey("symptomes.id"), nullable=False)

    # --- Attributs de la Relation ---
    probabilite = Column(DECIMAL(5, 4), comment="Probabilité d'apparition du symptôme pour cette pathologie P(symptôme|pathologie)")
    sensibilite = Column(DECIMAL(5, 4))
    specificite = Column(DECIMAL(5, 4))
    phase_maladie = Column(String(50), comment="Phase de la maladie où le symptôme apparaît (ex: Précoce, Tardive)")
    frequence = Column(String(50), comment="Fréquence d'apparition (ex: Constant, Fréquent, Occasionnel)")
    est_pathognomonique = Column(Boolean, default=False, comment="Si True, ce symptôme seul suffit presque à poser le diagnostic")
    importance_diagnostique = Column(Integer, comment="Échelle de 1 à 5 sur l'importance de ce symptôme pour le diagnostic")

    # --- Relations Inverses (Back-population) ---
    # Permet d'accéder à l'objet parent directement depuis une instance de cette classe.
    # ex: mon_association.pathologie -> renvoie l'objet Disease
    pathologie = relationship("Disease", back_populates="symptomes")
    symptome = relationship("Symptom", back_populates="pathologies")

    def __repr__(self) -> str:
        return f"<PathologieSymptome(pathologie_id={self.pathologie_id}, symptome_id={self.symptome_id})>"
    

# Contenu à AJOUTER à la fin de app/models/relations.py

class TraitementPathologie(Base):
    """
    Table d'association pour les traitements spécifiques aux pathologies.
    """
    __tablename__ = "traitements_pathologies"

    id = Column(Integer, primary_key=True)
    pathologie_id = Column(Integer, ForeignKey("pathologies.id"), nullable=False)
    medicament_id = Column(Integer, ForeignKey("medicaments.id"), nullable=False)

    type_traitement = Column(String(50), comment="Ex: Premiere_intention, Alternative, Adjuvant")
    ligne_traitement = Column(Integer, comment="Ex: 1ère ligne, 2e ligne")
    indication_precise = Column(Text)
    efficacite_taux = Column(DECIMAL(5, 2), comment="Taux de succès en %")
    duree_traitement_jours = Column(Integer)
    posologie_detaillee = Column(JSON)
    niveau_preuve = Column(String(50), comment="Grade de recommandation (A, B, C)")
    guidelines_source = Column(String(255), comment="Source (OMS, MINSANTE Cameroun, etc.)")
    rang_preference = Column(Integer, default=99)

    pathologie = relationship("Disease", back_populates="traitements")
    medicament = relationship("Medication", back_populates="traitements_pathologies")


class TraitementSymptome(Base):
    """
    Table d'association pour les traitements symptomatiques.
    """
    __tablename__ = "traitements_symptomes"

    id = Column(Integer, primary_key=True)
    symptome_id = Column(Integer, ForeignKey("symptomes.id"), nullable=False)
    medicament_id = Column(Integer, ForeignKey("medicaments.id"), nullable=False)

    efficacite = Column(String(50), comment="Ex: Tres_efficace, Efficace, Modere")
    rapidite_action = Column(String(100), comment="Ex: Immediate, <30min")
    posologie_recommandee = Column(Text)
    rang_preference = Column(Integer, default=99)
    
    symptome = relationship("Symptom", back_populates="traitements")
    medicament = relationship("Medication", back_populates="traitements_symptomes")


