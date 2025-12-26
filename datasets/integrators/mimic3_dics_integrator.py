import pandas as pd
from sqlalchemy.orm import Session
from typing import Dict, Set

from app import models

class MIMIC3DictionariesIntegrator:
    """
    Intégrateur spécialisé pour peupler les tables de référence (dictionnaires)
    de notre base de données à partir des fichiers correspondants de MIMIC-III.
    """

    def __init__(self, db_session: Session, paths: Dict[str, str]):
        """
        Initialise l'intégrateur avec une session de base de données et un
        dictionnaire des chemins vers les fichiers CSV nécessaires.
        """
        self.db = db_session
        self.paths = paths
        print("--- Initialisation de l'intégrateur de dictionnaires MIMIC-III ---")

    def populate_pathologies(self):
        """
        Peuple la table 'pathologies' depuis D_ICD_DIAGNOSES.csv.
        """
        print("\n🚀 Démarrage du peuplement de la table 'pathologies'...")
        path = self.paths.get('d_icd_diagnoses')
        if not path:
            print("❌ Chemin pour D_ICD_DIAGNOSES.csv non fourni. Étape ignorée.")
            return

        existing_codes = {c[0] for c in self.db.query(models.Disease.code_icd10).all()}
        print(f"  -> {len(existing_codes)} pathologies déjà en base.")
        
        chunk_iterator = pd.read_csv(
            path, 
            chunksize=5000, 
            usecols=['icd9_code', 'long_title'], 
            encoding='latin1',
            dtype={'icd9_code': str}
        )
        
        total_added = 0
        for chunk in chunk_iterator:
            new_diseases = []
            for _, row in chunk.iterrows():
                code = str(row['icd9_code']).strip()
                if code and code not in existing_codes:
                    existing_codes.add(code)
                    new_diseases.append(models.Disease(
                        code_icd10=code,
                        nom_fr=str(row['long_title']).strip()[:255],
                        categorie="Importé de MIMIC-III"
                    ))
            
            if new_diseases:
                self.db.bulk_save_objects(new_diseases)
                total_added += len(new_diseases)

        self.db.commit()
        print(f"✨ Peuplement terminé. {total_added} nouvelles pathologies ajoutées.")

    def populate_symptoms_from_items(self):
        """
        Peuple la table 'symptomes' depuis D_LABITEMS.csv et D_ITEMS.csv.
        """
        print("\n🚀 Démarrage du peuplement de la table 'symptomes'...")
        files_to_process = {
            'd_labitems': {'categorie': 'Biologique'},
            'd_items': {'categorie': 'Signe Vital/Clinique'}
        }
        
        existing_symptoms = {s[0] for s in self.db.query(models.Symptom.nom).all()}
        print(f"  -> {len(existing_symptoms)} symptômes déjà en base.")

        total_added = 0
        for key, info in files_to_process.items():
            path = self.paths.get(key)
            if not path:
                print(f"⚠️ Chemin pour {key}.csv non fourni. Étape ignorée.")
                continue
            
            print(f"  -> Traitement de {path}...")
            # Utiliser un chunksize pour éviter de charger tout le fichier en mémoire
            chunk_iterator = pd.read_csv(path, usecols=['label'], encoding='latin1', chunksize=10000)
            
            for chunk in chunk_iterator:
                new_symptoms = []
                unique_labels = chunk['label'].dropna().unique()

                for label in unique_labels:
                    clean_label = str(label).strip()
                    if clean_label and clean_label not in existing_symptoms:
                        existing_symptoms.add(clean_label)
                        new_symptoms.append(models.Symptom(
                            nom=clean_label[:255],
                            categorie=info['categorie']
                        ))
                
                if new_symptoms:
                    self.db.bulk_save_objects(new_symptoms)
                    total_added += len(new_symptoms)
        
        self.db.commit()
        print(f"✨ Peuplement terminé. {total_added} nouveaux symptômes ajoutés.")

    def populate_medications(self):
        """
        Peuple la table 'medicaments' depuis PRESCRIPTIONS.csv.
        Utilise la colonne 'drug' (nom commercial) et 'formulary_drug_cd' (comme proxy DCI pour l'instant).
        """
        print("\n🚀 Démarrage du peuplement de la table 'medicaments'...")
        path = self.paths.get('prescriptions')
        if not path:
            print("❌ Chemin pour PRESCRIPTIONS.csv non fourni. Étape ignorée.")
            return

        existing_meds = {m[0] for m in self.db.query(models.Medication.nom_commercial).all()}
        print(f"  -> {len(existing_meds)} médicaments déjà en base.")
        
        # Lecture par lots car PRESCRIPTIONS.csv peut être très gros
        chunk_iterator = pd.read_csv(
            path, 
            chunksize=10000, 
            usecols=['drug', 'drug_type', 'formulary_drug_cd', 'prod_strength', 'dose_val_rx', 'dose_unit_rx', 'route'],
            dtype=str # Tout lire en string pour éviter les erreurs de type
        )
        
        total_added = 0
        for chunk in chunk_iterator:
            new_meds = []
            # On ne garde que les noms de médicaments uniques dans ce lot
            unique_drugs = chunk.drop_duplicates(subset=['drug'])
            
            for _, row in unique_drugs.iterrows():
                drug_name = str(row['drug']).strip()
                
                if drug_name and drug_name not in existing_meds:
                    existing_meds.add(drug_name)
                    
                    # Construction de l'objet Médicament
                    # Note: Dans MIMIC, 'drug' est souvent le nom commercial.
                    # 'formulary_drug_cd' est un code interne, on l'utilise comme DCI temporaire
                    # si 'drug_name_generic' n'est pas dispo (ce qui est le cas dans la démo parfois).
                    new_meds.append(models.Medication(
                        nom_commercial=drug_name,
                        dci=str(row['formulary_drug_cd']).strip()[:255], 
                        classe_therapeutique="Importé de MIMIC-III",
                        dosage=str(row['prod_strength']).strip()[:100] if pd.notna(row['prod_strength']) else None,
                        voie_administration=str(row['route']).strip()[:100] if pd.notna(row['route']) else None,
                        disponibilite_cameroun="Inconnue"
                    ))
            
            if new_meds:
                self.db.bulk_save_objects(new_meds)
                total_added += len(new_meds)

        self.db.commit()
        print(f"✨ Peuplement terminé. {total_added} nouveaux médicaments ajoutés.")

    def run_all(self):
        """
        Exécute toutes les étapes de peuplement des dictionnaires.
        """
        self.populate_pathologies()
        self.populate_symptoms_from_items()
        self.populate_medications() # <- NOUVELLE ÉTAPE