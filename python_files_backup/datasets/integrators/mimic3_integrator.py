import pandas as pd
from sqlalchemy.orm import Session
from typing import Dict, Set

from app import models

class MIMIC3RelationsIntegrator:
    """
    Intégrateur pour déduire et créer les relations entre pathologies,
    symptômes et médicaments avec des probabilités réelles (basées sur les patients uniques).
    """

    def __init__(self, db_session: Session, paths: Dict[str, str]):
        self.db = db_session
        self.paths = paths
        self.disease_map: Dict[str, int] = {}
        self.symptom_map: Dict[str, int] = {}
        self.medication_map: Dict[str, int] = {}
        print("--- Initialisation de l'intégrateur de relations MIMIC-III ---")

    def _preload_dictionaries(self):
        print("  -> Pré-chargement des dictionnaires...")
        diseases = self.db.query(models.Disease.id, models.Disease.code_icd10).all()
        self.disease_map = {str(code).strip(): id for id, code in diseases}
        
        symptoms = self.db.query(models.Symptom.id, models.Symptom.nom).all()
        self.symptom_map = {nom: id for id, nom in symptoms}

        meds = self.db.query(models.Medication.id, models.Medication.nom_commercial).all()
        self.medication_map = {nom: id for id, nom in meds}

    def run(self):
        self._preload_dictionaries()

        # --- Étape 1: Carte des diagnostics et COMPTAGE ---
        print("\n🚀 Étape 1: Carte des diagnostics et calcul des totaux...")
        diagnoses_path = self.paths.get('diagnoses_icd')
        if not diagnoses_path: return
            
        admissions_diagnoses = {}
        disease_counts: Dict[str, int] = {} 

        df_diag = pd.read_csv(diagnoses_path, usecols=['hadm_id', 'icd9_code'], dtype={'icd9_code': str})
        for _, row in df_diag.iterrows():
            hadm_id = row['hadm_id']
            icd9_code = str(row['icd9_code']).strip()
            
            normalized_code = icd9_code.lstrip('0')
            if not normalized_code and icd9_code.isnumeric(): normalized_code = '0'
            elif not normalized_code: normalized_code = icd9_code

            if normalized_code in self.disease_map:
                code_to_use = normalized_code
            elif icd9_code in self.disease_map:
                code_to_use = icd9_code
            else:
                continue

            if hadm_id not in admissions_diagnoses:
                admissions_diagnoses[hadm_id] = set()
            
            if code_to_use not in admissions_diagnoses[hadm_id]:
                admissions_diagnoses[hadm_id].add(code_to_use)
                disease_counts[code_to_use] = disease_counts.get(code_to_use, 0) + 1
        
        print(f"  -> Carte construite. {len(disease_counts)} maladies différentes trouvées.")

        # --- Étape 2: Analyse des résultats (CORRECTION LOGIQUE) ---
        print("\n🚀 Étape 2: Analyse des résultats de laboratoire anormaux...")
        labevents_path = self.paths.get('labevents')
        d_labitems_path = self.paths.get('d_labitems')
        if not labevents_path or not d_labitems_path: return

        df_labitems = pd.read_csv(d_labitems_path, usecols=['itemid', 'label'])
        itemid_to_label = pd.Series(df_labitems.label.values, index=df_labitems.itemid).to_dict()

        # CORRECTION : Utiliser un Set pour stocker les hadm_id uniques
        co_occurrences: Dict[str, Dict[str, Set[int]]] = {} 

        chunk_iterator = pd.read_csv(labevents_path, chunksize=100000, usecols=['hadm_id', 'itemid', 'flag'])
        
        for chunk in chunk_iterator:
            abnormal_events = chunk[chunk['flag'] == 'abnormal'].dropna()
            for _, event in abnormal_events.iterrows():
                hadm_id = event['hadm_id']
                itemid = event['itemid']
                diagnoses = admissions_diagnoses.get(hadm_id)
                symptom_name = itemid_to_label.get(itemid)

                if diagnoses and symptom_name and symptom_name in self.symptom_map:
                    for icd9_code in diagnoses:
                        if icd9_code not in co_occurrences:
                            co_occurrences[icd9_code] = {}
                        
                        if symptom_name not in co_occurrences[icd9_code]:
                            co_occurrences[icd9_code][symptom_name] = set() # Initialiser un Set
                        
                        # Ajouter l'ID de l'admission (les doublons sont ignorés par le Set)
                        co_occurrences[icd9_code][symptom_name].add(hadm_id)
        
        # --- Étape 3: Chargement des relations ---
        print("\n🚀 Étape 3: Chargement des relations (Probabilités réelles)...")
        new_relations = []
        
        log_limit = 10 
        current_log = 0

        for icd9_code, symptom_sets in co_occurrences.items():
            disease_id = self.disease_map.get(icd9_code)
            total_cases = disease_counts.get(icd9_code, 1)

            if not disease_id: continue

            for symptom_name, unique_patients_set in symptom_sets.items():
                symptom_id = self.symptom_map.get(symptom_name)
                if not symptom_id: continue
                
                # CORRECTION : Compter la taille du Set (nombre de patients uniques)
                unique_count = len(unique_patients_set)
                
                # Calcul correct : (Nb patients uniques avec symptôme) / (Nb total patients avec maladie)
                prob = unique_count / total_cases 
            
            # Logs de vérification
                if current_log < 120: # Augmentons la limite à 20 pour voir plus de cas
                    print(f"  [LOG] Maladie {icd9_code} (ID BDD: {disease_id})")
                    print(f"        Symptôme: {symptom_name}")
                    # Afficher clairement si c'est un cas unique ou non
                    if total_cases == 1:
                        print(f"        -> ⚠️ UN SEUL PATIENT connu pour cette maladie dans le dataset.")
                    else:
                        print(f"        -> ✅ PLUSIEURS PATIENTS ({total_cases}).")
                    
                    print(f"        -> Calcul: {unique_count}/{total_cases} = {prob:.4f}")
                    print("        --------------------------------------------------")
                    current_log += 1

                if prob > 0.05:
                    new_relations.append(models.PathologieSymptome(
                        pathologie_id=disease_id,
                        symptome_id=symptom_id,
                        probabilite=prob,
                        frequence=f"{prob*100:.1f}%",
                        importance_diagnostique=3
                    ))

        if new_relations:
            try:
                self.db.bulk_save_objects(new_relations)
                self.db.commit()
                print(f"✨ Chargement de {len(new_relations)} relations pathologie-symptôme.")
            except Exception:
                self.db.rollback()

        # --- Étape 4 & 5: Relations Thérapeutiques (Même logique de correction) ---
        print("\n🚀 Étape 4: Analyse des prescriptions...")
        prescriptions_path = self.paths.get('prescriptions')
        if not prescriptions_path: return

        # CORRECTION : Utiliser un Set pour les médicaments aussi
        med_co_occurrences: Dict[str, Dict[str, Set[int]]] = {}

        chunk_iterator = pd.read_csv(prescriptions_path, chunksize=10000, usecols=['hadm_id', 'drug'], dtype=str)
        for chunk in chunk_iterator:
            for _, row in chunk.iterrows():
                hadm_id = int(row['hadm_id']) if pd.notna(row['hadm_id']) else None
                drug_name = str(row['drug']).strip()
                diagnoses = admissions_diagnoses.get(hadm_id)
                
                if diagnoses and drug_name in self.medication_map:
                    for icd9_code in diagnoses:
                        if icd9_code not in med_co_occurrences:
                            med_co_occurrences[icd9_code] = {}
                        
                        if drug_name not in med_co_occurrences[icd9_code]:
                            med_co_occurrences[icd9_code][drug_name] = set()
                        
                        med_co_occurrences[icd9_code][drug_name].add(hadm_id)

        print("\n🚀 Étape 5: Chargement des relations thérapeutiques...")
        new_treatments = []
        for icd9_code, drug_sets in med_co_occurrences.items():
            disease_id = self.disease_map.get(icd9_code)
            total_cases = disease_counts.get(icd9_code, 1)

            if not disease_id: continue

            # Trier par nombre de patients uniques
            top_drugs = sorted(drug_sets.items(), key=lambda x: len(x[1]), reverse=True)[:10]

            for drug_name, unique_patients_set in top_drugs:
                med_id = self.medication_map.get(drug_name)
                if not med_id: continue
                
                unique_count = len(unique_patients_set)
                frequence = (unique_count / total_cases) * 100
                
                new_treatments.append(models.TraitementPathologie(
                    pathologie_id=disease_id,
                    medicament_id=med_id,
                    efficacite_taux=frequence,
                    type_traitement=f"Prescrit dans {frequence:.1f}% des cas"
                ))

        if new_treatments:
            try:
                self.db.bulk_save_objects(new_treatments)
                self.db.commit()
                print(f"✨ Chargement de {len(new_treatments)} relations thérapeutiques.")
            except Exception:
                self.db.rollback()