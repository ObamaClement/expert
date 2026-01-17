import pandas as pd
from sqlalchemy.orm import Session
from typing import Dict, List, Any
import math
import random

from app import models
from app.services.embedding_service import embedding_service # <-- IMPORT

def clean_nan(value: Any) -> Any:
    """Remplace les valeurs NaN par None."""
    if value is None: return None
    if isinstance(value, float) and math.isnan(value): return None
    if isinstance(value, str) and value.lower() == 'nan': return None
    return value


class CaseAssembler:
    """
    Assemble des cas cliniques enrichis à partir de MIMIC-III.
    """
    def __init__(self, db_session: Session, paths: Dict[str, str]):
        self.db = db_session
        self.paths = paths
        self.disease_map: Dict[str, int] = {}
        self.symptom_map: Dict[str, int] = {}
        self.medication_map: Dict[str, int] = {}
        self.images_by_disease: Dict[int, List[int]] = {} 
        print("--- Initialisation de l'assembleur de cas cliniques ---")

    def _preload_data(self):
        print("  -> Pré-chargement des dictionnaires...")
        
        diseases = self.db.query(models.Disease.id, models.Disease.code_icd10).all()
        self.disease_map = {str(code).strip(): id for id, code in diseases}
        
        symptoms = self.db.query(models.Symptom.id, models.Symptom.nom).all()
        self.symptom_map = {nom: id for id, nom in symptoms}

        meds = self.db.query(models.Medication.id, models.Medication.nom_commercial).all()
        self.medication_map = {nom: id for id, nom in meds}

        # Images
        images = self.db.query(models.ImageMedicale.id, models.ImageMedicale.pathologie_id).filter(models.ImageMedicale.pathologie_id != None).all()
        for img_id, path_id in images:
            if path_id not in self.images_by_disease:
                self.images_by_disease[path_id] = []
            self.images_by_disease[path_id].append(img_id)

        # CSVs
        self.df_diagnoses = pd.read_csv(
            self.paths['diagnoses_icd'],
            usecols=['hadm_id', 'icd9_code', 'seq_num'],
            dtype={'icd9_code': str}
        )
        
        self.df_labitems = pd.read_csv(self.paths['d_labitems'], usecols=['itemid', 'label'])
        self.itemid_to_label = pd.Series(self.df_labitems.label.values, index=self.df_labitems.itemid).to_dict()

    def run(self):
        self._preload_data()

        admissions_path = self.paths.get('admissions')
        if not admissions_path: return

        print("\n🚀 Démarrage de l'assemblage des cas cliniques...")
        df_admissions = pd.read_csv(admissions_path)
        
        # --- Agrégation Labos ---
        print("  -> Agrégation des résultats de laboratoire...")
        labevents_chunk_iterator = pd.read_csv(self.paths['labevents'], chunksize=100000, usecols=['hadm_id', 'itemid', 'valuenum', 'valueuom', 'flag'])
        admission_labs: Dict[int, Dict[str, Any]] = {}
        for chunk in labevents_chunk_iterator:
            chunk['valuenum'].fillna(0, inplace=True)
            chunk['valueuom'].fillna('', inplace=True)
            chunk['flag'].fillna('', inplace=True)
            abnormal_events = chunk[chunk['flag'] == 'abnormal'].dropna(subset=['hadm_id'])
            for _, event in abnormal_events.iterrows():
                hadm_id = int(event['hadm_id'])
                if hadm_id not in admission_labs: admission_labs[hadm_id] = {}
                symptom_name = self.itemid_to_label.get(event['itemid'])
                if symptom_name and symptom_name not in admission_labs[hadm_id]:
                    admission_labs[hadm_id][symptom_name] = {
                        "nom": symptom_name, "valeur": event['valuenum'], "unite": event['valueuom']
                    }
        
        # --- Agrégation Médicaments ---
        print("  -> Agrégation des prescriptions médicamenteuses...")
        prescriptions_path = self.paths.get('prescriptions')
        admission_meds: Dict[int, List[Dict[str, Any]]] = {}
        if prescriptions_path:
            presc_chunk_iterator = pd.read_csv(prescriptions_path, chunksize=50000, usecols=['hadm_id', 'drug', 'dose_val_rx', 'dose_unit_rx'], dtype=str)
            for chunk in presc_chunk_iterator:
                chunk = chunk.dropna(subset=['hadm_id', 'drug'])
                for _, row in chunk.iterrows():
                    hadm_id = int(float(row['hadm_id']))
                    if hadm_id not in admission_meds: admission_meds[hadm_id] = []
                    drug_name = str(row['drug']).strip()
                    med_id = self.medication_map.get(drug_name)
                    if med_id:
                        admission_meds[hadm_id].append({
                            "medicament_id": med_id, "nom": drug_name, "dose": f"{row['dose_val_rx']} {row['dose_unit_rx']}"
                        })

        # --- Assemblage ---
        new_cases = []
        existing_case_codes = {c[0] for c in self.db.query(models.ClinicalCase.code_fultang).all()}

        for _, admission in df_admissions.iterrows():
            hadm_id = admission['hadm_id']
            case_code = f"MIMIC_{hadm_id}"

            if case_code in existing_case_codes: continue

            diagnoses_for_admission = self.df_diagnoses[self.df_diagnoses['hadm_id'] == hadm_id].sort_values('seq_num')
            if diagnoses_for_admission.empty: continue

            main_diag_id = None
            secondary_diag_ids = []
            for _, diag_row in diagnoses_for_admission.iterrows():
                raw_diag_code = str(diag_row['icd9_code']).strip()
                normalized_diag_code = raw_diag_code.lstrip('0')
                if not normalized_diag_code and raw_diag_code.isnumeric(): normalized_diag_code = '0'
                elif not normalized_diag_code: normalized_diag_code = raw_diag_code
                diag_id = self.disease_map.get(normalized_diag_code) or self.disease_map.get(raw_diag_code)

                if diag_id:
                    if diag_row['seq_num'] == 1:
                        main_diag_id = diag_id
                    else:
                        secondary_diag_ids.append(diag_id)
            
            if not main_diag_id: continue

            # Symptômes
            lab_results_dict = admission_labs.get(hadm_id, {})
            lab_results_list = list(lab_results_dict.values())
            symptomes_patient = []
            symptoms_text_list = [] # Pour le vecteur
            
            for lab_res in lab_results_list:
                symptom_id = self.symptom_map.get(lab_res['nom'])
                if symptom_id:
                    symptomes_patient.append({
                        "symptome_id": symptom_id, "details": f"Valeur: {lab_res.get('valeur')} {lab_res.get('unite') or ''}".strip()
                    })
                    symptoms_text_list.append(f"{lab_res['nom']} {lab_res.get('valeur')}")

            history_text = f"Admission pour : {admission['diagnosis']}"
            presentation = {
                "histoire_maladie": history_text,
                "symptomes_patient": symptomes_patient
            }
            
            meds_list = admission_meds.get(hadm_id, [])

            # Images
            images_ids = []
            if main_diag_id in self.images_by_disease:
                available_images = self.images_by_disease[main_diag_id]
                if available_images:
                    images_ids.append(random.choice(available_images))

            # --- VECTORISATION ---
            # On vectorise l'histoire clinique combinée aux symptômes principaux
            # C'est ce texte que le RAG utilisera pour trouver des cas similaires
            full_case_text = f"{history_text}. Symptômes biologiques notables : {', '.join(symptoms_text_list[:10])}"
            vector = embedding_service.get_text_embedding(full_case_text)

            new_case = models.ClinicalCase(
                code_fultang=case_code,
                pathologie_principale_id=main_diag_id,
                pathologies_secondaires_ids=secondary_diag_ids,
                presentation_clinique=presentation,
                donnees_paracliniques={"lab_results": lab_results_list},
                medicaments_prescrits=meds_list,
                images_associees_ids=images_ids,
                niveau_difficulte=2 + len(secondary_diag_ids),
                embedding_texte=vector # <-- AJOUT
            )
            new_cases.append(new_case)

        print(f"  -> {len(new_cases)} cas cliniques assemblés.")

        if new_cases:
            try:
                self.db.bulk_save_objects(new_cases)
                self.db.commit()
                print(f"✨ Chargement de {len(new_cases)} nouveaux cas cliniques réussi.")

                print("\n--- Aperçu des 10 premiers cas cliniques chargés ---")
                first_10_cases = self.db.query(models.ClinicalCase).order_by(models.ClinicalCase.id.desc()).limit(10).all()
                for i, case_from_db in enumerate(reversed(first_10_cases)):
                    disease_name = case_from_db.pathologie_principale.nom_fr if case_from_db.pathologie_principale else "Inconnue"
                    # Vérifier si le vecteur est présent (pour le log)
                    has_vector = "OUI" if case_from_db.embedding_texte is not None else "NON"
                    
                    print(f"\n[{i+1}] Cas: {case_from_db.code_fultang}")
                    print(f"    Pathologie: {disease_name}")
                    print(f"    Vecteur IA généré: {has_vector}") # <-- Affichage validation

            except Exception as e:
                print(f"❌ Erreur lors du chargement des cas : {e}")
                self.db.rollback()
        else:
            print("✨ Aucun nouveau cas clinique à ajouter.")