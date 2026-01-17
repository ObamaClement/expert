from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional

from .. import models
from ..core import reasoning_engine
from . import expert_strategy_service

# Pour le typage, nous pouvons définir un schéma simple ici
from pydantic import BaseModel

class DiagnosticInput(BaseModel):
    """
    Schéma simple pour les données d'entrée du moteur de diagnostic.
    """
    symptoms: List[str]
    context: List[str] = []
    age: Optional[int] = None
    # ... d'autres faits pertinents pourraient être ajoutés ici


def run_diagnostic(db: Session, patient_facts: DiagnosticInput) -> List[Dict[str, Any]]:
    """
    Orchestre le processus de diagnostic.

    1. Récupère les règles de diagnostic actives depuis la base de données.
    2. Formate les faits du patient.
    3. Appelle le moteur de raisonnement.
    4. Retourne les actions/conclusions.
    """
    # 1. Récupérer les règles
    # On utilise la fonction 'intelligente' que nous avions créée dans le service des stratégies
    diagnostic_rules_db = expert_strategy_service.get_active_strategies_by_category(
        db, category="DIAGNOSTIC"
    )

    if not diagnostic_rules_db:
        return []

    # Convertir les objets SQLAlchemy en dictionnaires simples pour le moteur de logique pure
    rules_list = [
        {
            "code_regle": rule.code_regle,
            "conditions": rule.conditions,
            "actions": rule.actions,
        }
        for rule in diagnostic_rules_db
    ]

    # 2. Formater les faits (déjà au bon format grâce à Pydantic)
    facts_dict = patient_facts.model_dump()

    # 3. Appeler le moteur de raisonnement
    conclusions = reasoning_engine.forward_chaining_engine(
        rules=rules_list,
        facts=facts_dict
    )

    # 4. Retourner les conclusions
    return conclusions