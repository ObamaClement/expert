import sys
import os

# Ajoute la racine du projet au path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.database import SessionLocal
from app import models

def generate_matrix():
    db = SessionLocal()
    print("--- Génération de la Q-Matrix (Lien Cas <-> Compétences) ---")

    # 1. Charger toutes les compétences pour avoir leurs IDs et codes
    competencies = db.query(models.Competence).all()
    comp_map = {c.code_competence: c.id for c in competencies}
    
    if not comp_map:
        print("❌ Aucune compétence trouvée. Veuillez lancer populate_competencies.py d'abord.")
        return

    # 2. Récupérer tous les cas cliniques
    cases = db.query(models.ClinicalCase).all()
    print(f"Traitement de {len(cases)} cas cliniques...")

    count_updated = 0
    for case in cases:
        required_skills = {} # Dictionnaire pour stocker les compétences requises {code: id}

        # --- RÈGLES D'ATTRIBUTION DES COMPÉTENCES ---

        # Règle 1 : Socle commun (Tout cas nécessite ces bases)
        # Bloom 1-2
        common_skills = ["IDENTIFIER_MOTIF", "EMPATHIE", "ANAMNESE_HISTOIRE"]
        for code in common_skills:
            if code in comp_map:
                required_skills[code] = comp_map[code]

        # Règle 2 : Si le cas a des symptômes biologiques (Labo)
        # Bloom 4
        if case.donnees_paracliniques and "lab_results" in case.donnees_paracliniques:
            if len(case.donnees_paracliniques["lab_results"]) > 0:
                if "INTERPRETATION_BIOLOGIE" in comp_map:
                    required_skills["INTERPRETATION_BIOLOGIE"] = comp_map["INTERPRETATION_BIOLOGIE"]

        # Règle 3 : Si le cas a des images
        # Bloom 4
        if case.images_associees_ids and len(case.images_associees_ids) > 0:
            if "INTERPRETATION_IMAGERIE" in comp_map:
                required_skills["INTERPRETATION_IMAGERIE"] = comp_map["INTERPRETATION_IMAGERIE"]

        # Règle 4 : Si le cas a des médicaments prescrits
        # Bloom 6
        if case.medicaments_prescrits and len(case.medicaments_prescrits) > 0:
            if "PRESCRIPTION_THERAPEUTIQUE" in comp_map:
                required_skills["PRESCRIPTION_THERAPEUTIQUE"] = comp_map["PRESCRIPTION_THERAPEUTIQUE"]
        
        # Règle 5 : Compétences de Raisonnement (Toujours nécessaires pour un cas complet)
        # Bloom 4-5
        reasoning_skills = ["GENERATION_HYPOTHESES", "DIAGNOSTIC_DIFFERENTIEL", "SYNTHESE_CLINIQUE"]
        for code in reasoning_skills:
            if code in comp_map:
                required_skills[code] = comp_map[code]

        # --- MISE À JOUR DU CAS ---
        
        # On sauvegarde le résultat sous forme de JSON { "CODE_COMPETENCE": ID_COMPETENCE }
        case.competences_requises = required_skills
        
        # On calcule un niveau de difficulté suggéré basé sur la richesse du cas
        # Base: 1. +1 si labo, +1 si images, +1 si médicaments, +1 si comorbidités
        difficulty = 1
        if "INTERPRETATION_BIOLOGIE" in required_skills: difficulty += 1
        if "INTERPRETATION_IMAGERIE" in required_skills: difficulty += 1
        if "PRESCRIPTION_THERAPEUTIQUE" in required_skills: difficulty += 1
        if case.pathologies_secondaires_ids: difficulty += 1
        
        case.niveau_difficulte = min(difficulty, 5) # Max 5

        count_updated += 1

    db.commit()
    db.close()
    print(f"✨ Terminé. {count_updated} cas cliniques mis à jour avec leur Q-Matrix.")

if __name__ == "__main__":
    generate_matrix()