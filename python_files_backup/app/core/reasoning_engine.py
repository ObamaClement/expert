from typing import List, Dict, Any

def evaluate_condition(condition: Dict[str, Any], facts: Dict[str, Any]) -> bool:
    """
    Évalue une seule condition par rapport à un ensemble de faits.
    Version très simple pour commencer.
    """
    fact_type = condition.get("fact")
    fact_value = condition.get("value")
    operator = condition.get("operator")

    if fact_type == "symptom" and operator == "present":
        return fact_value in facts.get("symptoms", [])
    
    if fact_type == "context" and operator == "is":
        return fact_value in facts.get("context", [])
    
    # Ajouter d'autres logiques d'évaluation ici plus tard (ex: age > 65)
    
    return False


def forward_chaining_engine(rules: List[Dict[str, Any]], facts: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Moteur de raisonnement simple en chaînage avant.

    :param rules: Une liste de règles, où chaque règle est un dictionnaire
                  avec les clés 'conditions' et 'actions'.
    :param facts: Un dictionnaire représentant les faits connus sur le patient
                  (ex: {"symptoms": ["Fièvre", "Toux"], "context": ["zone_endemique"]}).
    :return: Une liste de toutes les actions des règles qui ont été déclenchées.
    """
    triggered_actions = []

    for rule in rules:
        conditions = rule.get("conditions", {})
        
        # Pour l'instant, nous ne gérons que l'opérateur "AND"
        if conditions.get("operator") == "AND":
            all_conditions_met = True
            for condition in conditions.get("rules", []):
                if not evaluate_condition(condition, facts):
                    all_conditions_met = False
                    break  # Inutile de vérifier les autres conditions de cette règle
            
            if all_conditions_met:
                # Toutes les conditions sont remplies, on ajoute les actions
                triggered_actions.extend(rule.get("actions", []))

    return triggered_actions

"""""
# Ajoutez ce bloc à la fin du fichier pour tester
if __name__ == "__main__":
    # Définir une règle de test (copiée de notre exemple précédent)
    test_rule = {
        "code_regle": "DIAG_PALU_SIMPLE_01",
        "conditions": {
            "operator": "AND",
            "rules": [
                {"fact": "symptom", "value": "Fièvre", "operator": "present"},
                {"fact": "context", "value": "zone_endemique", "operator": "is"}
            ]
        },
        "actions": [
            {"action": "add_hypothesis", "pathology": "Paludisme simple", "confidence": 0.7}
        ]
    }
    
    # Définir des faits qui devraient déclencher la règle
    patient_facts = {
        "symptoms": ["Fièvre", "Toux"],
        "context": ["zone_endemique"]
    }
    
    print("Test du moteur de raisonnement...")
    conclusions = forward_chaining_engine(rules=[test_rule], facts=patient_facts)
    
    print(f"Faits: {patient_facts}")
    print(f"Règles: {[test_rule['code_regle']]}")
    print(f"Conclusions: {conclusions}")
    
    # Vérification du test
    assert len(conclusions) == 1
    assert conclusions[0]['pathology'] == 'Paludisme simple'
    print("\n✅ Test réussi !")
    
    """