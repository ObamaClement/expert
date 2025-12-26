import sys
import os

# Ajoute la racine du projet au path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.database import SessionLocal
from app import models

def populate():
    db = SessionLocal()
    print("--- Peuplement des Compétences Cliniques (Structure Consultation & Bloom) ---")

    # ---------------------------------------------------------
    # 1. Compétences Racines (Les Grandes Étapes de la Consultation)
    # ---------------------------------------------------------
    root_skills = [
        {"code": "RELATION", "nom": "1. Accueil et Relation Patient", "cat": "Communication", "bloom": 2},
        {"code": "ANAMNESE", "nom": "2. Anamnèse (Interrogatoire)", "cat": "Enquête", "bloom": 3},
        {"code": "EXAMEN_PHYSIQUE", "nom": "3. Examen Clinique", "cat": "Observation", "bloom": 3},
        {"code": "RAISONNEMENT", "nom": "4. Raisonnement Diagnostique", "cat": "Raisonnement", "bloom": 4},
        {"code": "PARACLINIQUE", "nom": "5. Examens Complémentaires", "cat": "Investigation", "bloom": 4},
        {"code": "SYNTHESE", "nom": "6. Diagnostic et Explication", "cat": "Synthèse", "bloom": 5},
        {"code": "PRISE_EN_CHARGE", "nom": "7. Traitement et Suivi", "cat": "Action", "bloom": 6},
    ]

    roots = {}
    for skill in root_skills:
        existing = db.query(models.Competence).filter(models.Competence.code_competence == skill["code"]).first()
        if not existing:
            new_skill = models.Competence(
                code_competence=skill["code"],
                nom=skill["nom"],
                categorie=skill["cat"],
                niveau_bloom=skill["bloom"],
                description=f"Compétence racine pour l'étape : {skill['nom']}"
            )
            db.add(new_skill)
            db.commit()
            db.refresh(new_skill)
            roots[skill["code"]] = new_skill
            print(f"✅ Racine créée : {skill['nom']} (Bloom {skill['bloom']})")
        else:
            roots[skill["code"]] = existing
            print(f"ℹ️ Racine existante : {skill['nom']}")

    # ---------------------------------------------------------
    # 2. Sous-Compétences Spécifiques (Détails opératoires)
    # ---------------------------------------------------------
    specific_skills = [
        # 1. Accueil
        {"code": "IDENTIFIER_MOTIF", "nom": "Identifier le motif de consultation", "parent": "RELATION", "bloom": 1},
        {"code": "EMPATHIE", "nom": "Communication empathique", "parent": "RELATION", "bloom": 2},

        # 2. Anamnèse
        {"code": "ANAMNESE_HISTOIRE", "nom": "Caractériser l'histoire de la maladie (PQRST)", "parent": "ANAMNESE", "bloom": 3},
        {"code": "ANAMNESE_ANTECEDENTS", "nom": "Recueillir les antécédents (perso/famille)", "parent": "ANAMNESE", "bloom": 2},
        {"code": "ANAMNESE_TRAITEMENTS", "nom": "Recenser traitements et allergies", "parent": "ANAMNESE", "bloom": 2},
        {"code": "ANAMNESE_MODE_VIE", "nom": "Identifier les facteurs de mode de vie", "parent": "ANAMNESE", "bloom": 2},

        # 3. Examen Physique
        {"code": "SIGNES_VITAUX", "nom": "Mesurer et interpréter les constantes", "parent": "EXAMEN_PHYSIQUE", "bloom": 3},
        {"code": "EXAMEN_CIBLE", "nom": "Réaliser l'examen physique ciblé", "parent": "EXAMEN_PHYSIQUE", "bloom": 3},
        {"code": "RECONNAISSANCE_SIGNES", "nom": "Reconnaître les signes physiques d'alerte", "parent": "EXAMEN_PHYSIQUE", "bloom": 3},

        # 4. Raisonnement
        {"code": "GENERATION_HYPOTHESES", "nom": "Formuler des hypothèses diagnostiques", "parent": "RAISONNEMENT", "bloom": 4},
        {"code": "DIAGNOSTIC_DIFFERENTIEL", "nom": "Mener un diagnostic différentiel", "parent": "RAISONNEMENT", "bloom": 5},

        # 5. Paraclinique
        {"code": "PRESCRIPTION_PERTINENTE", "nom": "Prescrire les examens pertinents", "parent": "PARACLINIQUE", "bloom": 5},
        {"code": "INTERPRETATION_BIOLOGIE", "nom": "Interpréter les résultats biologiques", "parent": "PARACLINIQUE", "bloom": 4},
        {"code": "INTERPRETATION_IMAGERIE", "nom": "Interpréter l'imagerie médicale", "parent": "PARACLINIQUE", "bloom": 4},

        # 6. Synthèse
        {"code": "SYNTHESE_CLINIQUE", "nom": "Intégrer les données pour conclure", "parent": "SYNTHESE", "bloom": 5},
        {"code": "ANNONCE_DIAGNOSTIC", "nom": "Expliquer le diagnostic au patient", "parent": "SYNTHESE", "bloom": 3},

        # 7. Prise en charge
        {"code": "PRESCRIPTION_THERAPEUTIQUE", "nom": "Établir le plan thérapeutique", "parent": "PRISE_EN_CHARGE", "bloom": 6},
        {"code": "EDUCATION_PATIENT", "nom": "Éduquer le patient sur sa maladie", "parent": "PRISE_EN_CHARGE", "bloom": 3},
        {"code": "SUIVI_EVOLUTION", "nom": "Planifier le suivi et la surveillance", "parent": "PRISE_EN_CHARGE", "bloom": 5},
    ]

    created_skills = {}
    for skill in specific_skills:
        existing = db.query(models.Competence).filter(models.Competence.code_competence == skill["code"]).first()
        if not existing:
            parent = roots.get(skill["parent"])
            new_skill = models.Competence(
                code_competence=skill["code"],
                nom=skill["nom"],
                categorie=parent.categorie if parent else "Autre",
                parent_competence_id=parent.id if parent else None,
                niveau_bloom=skill["bloom"],
                description=f"Sous-compétence de : {parent.nom if parent else 'Racine'}"
            )
            db.add(new_skill)
            db.commit()
            db.refresh(new_skill)
            created_skills[skill["code"]] = new_skill
            print(f"  -> Sous-compétence créée : {skill['nom']} (Bloom {skill['bloom']})")
        else:
            created_skills[skill["code"]] = existing

    # ---------------------------------------------------------
    # 3. Création des Prérequis (Le Graphe de Dépendance)
    # ---------------------------------------------------------
    # Logique : "Pour faire B, il faut savoir faire A"
    prerequisites = [
        # Logique interne à l'Anamnèse
        ("ANAMNESE_HISTOIRE", "IDENTIFIER_MOTIF"), # On ne peut pas creuser l'histoire si on n'a pas le motif
        
        # Logique Anamnèse -> Examen
        ("EXAMEN_CIBLE", "ANAMNESE_HISTOIRE"), # L'examen est guidé par l'histoire
        
        # Logique vers Raisonnement
        ("GENERATION_HYPOTHESES", "ANAMNESE_HISTOIRE"),
        ("GENERATION_HYPOTHESES", "SIGNES_VITAUX"),
        
        # Logique vers Paraclinique
        ("PRESCRIPTION_PERTINENTE", "GENERATION_HYPOTHESES"), # On prescrit pour tester une hypothèse
        
        # Logique vers Synthèse
        ("SYNTHESE_CLINIQUE", "INTERPRETATION_BIOLOGIE"),
        ("SYNTHESE_CLINIQUE", "DIAGNOSTIC_DIFFERENTIEL"),
        
        # Logique vers Traitement (Le sommet)
        ("PRESCRIPTION_THERAPEUTIQUE", "SYNTHESE_CLINIQUE"), # Pas de traitement sans diagnostic
        ("EDUCATION_PATIENT", "SYNTHESE_CLINIQUE"),
    ]

    for target_code, req_code in prerequisites:
        target = created_skills.get(target_code)
        req = created_skills.get(req_code)

        if target and req:
            # Vérifier si le lien existe déjà
            link_exists = db.query(models.PrerequisCompetence).filter(
                models.PrerequisCompetence.competence_id == target.id,
                models.PrerequisCompetence.prerequis_id == req.id
            ).first()

            if not link_exists:
                new_link = models.PrerequisCompetence(
                    competence_id=target.id,
                    prerequis_id=req.id,
                    type_relation="STRICT"
                )
                db.add(new_link)
                print(f"    🔗 Prérequis créé : {req.nom} -> {target.nom}")

    db.commit()
    db.close()
    print("✨ Peuplement des compétences pédagogiques terminé.")

if __name__ == "__main__":
    populate()