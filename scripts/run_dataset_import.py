import sys
import os

# Le sys.path.insert n'est plus nécessaire si on lance avec 'python -m'
# Mais on le garde au cas où, en le sécurisant
if __name__ == "__main__" and __package__ is None:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.database import SessionLocal
from datasets.integrators.mimic3_dics_integrator import MIMIC3DictionariesIntegrator
from datasets.integrators.mimic3_integrator import MIMIC3RelationsIntegrator
from datasets.assembler.case_assembler import CaseAssembler
from datasets.integrators.manual_images_integrator import ManualImagesIntegrator

# --- CONFIGURATION DES CHEMINS D'ACCÈS ---
MIMIC_BASE_PATH = "/home/clement/Téléchargements/archive (1)/mimic-iii-clinical-database-demo-1.4"
SOURCE_IMAGES_DIR = "/home/clement/Téléchargements/imgradio" 
MAPPING_CSV_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'datasets/mapping/images_mapping.csv'))

MIMIC_FILES_PATHS = {
    "d_icd_diagnoses": os.path.join(MIMIC_BASE_PATH, "D_ICD_DIAGNOSES.csv"),
    "d_labitems": os.path.join(MIMIC_BASE_PATH, "D_LABITEMS.csv"),
    "d_items": os.path.join(MIMIC_BASE_PATH, "D_ITEMS.csv"),
    "prescriptions": os.path.join(MIMIC_BASE_PATH, "PRESCRIPTIONS.csv"),
    "diagnoses_icd": os.path.join(MIMIC_BASE_PATH, "DIAGNOSES_ICD.csv"),
    "labevents": os.path.join(MIMIC_BASE_PATH, "LABEVENTS.csv"),
    "admissions": os.path.join(MIMIC_BASE_PATH, "ADMISSIONS.csv"),
}

def check_paths(paths: dict):
    all_found = True
    for key, path in paths.items():
        if not os.path.exists(path):
            print(f"❌ ERREUR: Fichier non trouvé pour '{key}': {path}")
            all_found = False
    return all_found

def main():
    print("--- Démarrage du script d'importation complet ---")
    
    if not check_paths(MIMIC_FILES_PATHS):
        print("\nAttention: Fichiers MIMIC manquants.")
        # On continue quand même pour tester les autres intégrateurs si besoin
    
    db_session = SessionLocal()
    
    try:
        print("\n" + "="*50)
        print("ÉTAPE 1: PEUPLEMENT DES DICTIONNAIRES")
        dics_integrator = MIMIC3DictionariesIntegrator(db_session=db_session, paths=MIMIC_FILES_PATHS)
        dics_integrator.run_all()

        print("\n" + "="*50)
        print("ÉTAPE 2: CRÉATION DES RELATIONS")
        relations_integrator = MIMIC3RelationsIntegrator(db_session=db_session, paths=MIMIC_FILES_PATHS)
        relations_integrator.run()

        print("\n" + "="*50)
        print("ÉTAPE 3: ASSEMBLAGE DES CAS CLINIQUES")
        case_assembler = CaseAssembler(db_session=db_session, paths=MIMIC_FILES_PATHS)
        case_assembler.run()

        print("\n" + "="*50)
        print("ÉTAPE 4: IMPORTATION DES IMAGES MANUELLES")
        if not os.path.exists(MAPPING_CSV_PATH):
            print(f"❌ ERREUR: Fichier de mapping non trouvé : {MAPPING_CSV_PATH}")
        else:
            images_integrator = ManualImagesIntegrator(
                db_session=db_session,
                mapping_csv_path=MAPPING_CSV_PATH,
                source_images_dir="" 
            )
            images_integrator.run()

    except Exception as e:
        print(f"\n❌ UNE ERREUR CRITIQUE EST SURVENUE : {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        print("\nFermeture de la session de base de données.")
        db_session.close()

if __name__ == "__main__":
    main()