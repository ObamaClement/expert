from sqlalchemy import (
    DECIMAL,
    Column,
    Integer,
    String,
    Text,
    JSON,
    TIMESTAMP,
    Boolean,
    Date,
    text
)
from sqlalchemy.orm import relationship

from .base import Base


class ExpertStrategy(Base):
    """
    Modèle SQLAlchemy pour la table des règles de production (stratégies expertes).
    
    Cette table stocke la logique IF-THEN du système expert.
    """
    __tablename__ = "regles_production"

    id = Column(Integer, primary_key=True, index=True)

    # --- Identification et Métadonnées ---
    code_regle = Column(String(50), unique=True, nullable=False, index=True)
    categorie = Column(String(100), index=True, comment="Ex: DIAGNOSTIC, THERAPEUTIQUE, PEDAGOGIQUE, ALERTE")
    priorite = Column(Integer, default=5, comment="Priorité d'exécution (1-10), 10 étant le plus prioritaire")
    
    # --- Structure de la Règle (IF-THEN) ---
    conditions = Column(JSON, nullable=False, comment="Partie 'IF' de la règle, structurée en JSON")
    # Exemple de 'conditions':
    # {
    #   "operator": "AND",
    #   "rules": [
    #     {"fact": "symptom", "value": "Fièvre", "operator": "present"},
    #     {"fact": "symptom", "value": "Toux", "operator": "present"},
    #     {"fact": "age", "value": 65, "operator": "greater_than"}
    #   ]
    # }

    actions = Column(JSON, nullable=False, comment="Partie 'THEN' de la règle, structurée en JSON")
    # Exemple d' 'actions':
    # [
    #   {"action": "add_hypothesis", "pathology": "Pneumonie", "confidence": 0.8},
    #   {"action": "recommend_exam", "exam": "Radio Thorax", "urgency": "high"}
    # ]

    # --- Documentation et Validation ---
    description_naturelle = Column(Text, comment="Description de la règle en langage naturel")
    justification_medicale = Column(Text, comment="Source ou justification clinique de la règle")
    expert_auteur = Column(String(255))
    date_validation = Column(Date)
    est_active = Column(Boolean, default=True, nullable=False)

    # --- Métriques ---
    nb_activations = Column(Integer, default=0)
    taux_succes = Column(DECIMAL(5, 4))

    # --- Horodatage ---
    created_at = Column(TIMESTAMP, nullable=False, server_default=text("now()"))
    updated_at = Column(TIMESTAMP, nullable=False, server_default=text("now()"), onupdate=text("now()"))

    def __repr__(self) -> str:
        return f"<ExpertStrategy(id={self.id}, code='{self.code_regle}')>"