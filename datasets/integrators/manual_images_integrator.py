import pandas as pd
import os
import shutil
from sqlalchemy.orm import Session
from typing import List

from app import models
from ..base_integrator import BaseIntegrator

# Chemin relatif où vous avez mis vos images
STORAGE_REL_PATH = "storage/media/images" 

class ManualImagesIntegrator(BaseIntegrator):
    """
    Intégrateur pour cataloguer les images manuelles déjà présentes dans le dossier storage.
    """

    def __init__(self, db_session: Session, mapping_csv_path: str, source_images_dir: str = None):
        super().__init__(db_session, mapping_csv_path)
        self.storage_dir = os.path.abspath(STORAGE_REL_PATH)
        print(f"--- Initialisation de l'intégrateur d'images ---")
        print(f"Dossier des images : {self.storage_dir}")

    def extract(self):
        """Lit le fichier de mapping."""
        return pd.read_csv(self.path, chunksize=1000)

    def transform(self, data_chunk: pd.DataFrame) -> List[dict]:
        """Prépare les données."""
        actions = []
        for _, row in data_chunk.iterrows():
            filename = str(row['filename']).strip()
            file_path = os.path.join(self.storage_dir, filename)
            
            if not os.path.exists(file_path):
                print(f"⚠️ Fichier manquant dans storage : {filename}")
                continue

            # Nettoyage et parsing des IDs
            raw_ids = str(row['cas_ids'])
            cas_ids_str = raw_ids.replace('"', '').replace("'", "")
            cas_ids = []
            for x in cas_ids_str.split(','):
                x = x.strip()
                if x.isdigit():
                    cas_ids.append(int(x))
            
            # Log de débogage
            # print(f"[DEBUG] Image {filename} -> IDs cibles : {cas_ids}")

            actions.append({
                "filename": filename,
                "file_path": file_path,
                "cas_ids": cas_ids,
                "type_examen": row['type_examen'],
                "description": row['description']
            })
        return actions

    def load(self, actions: List[dict]):
        """Crée les entrées en base."""
        for action in actions:
            filename = action['filename']
            file_url = os.path.join(STORAGE_REL_PATH, filename)
            
            existing_img = self.db.query(models.ImageMedicale).filter(
                models.ImageMedicale.fichier_url == file_url
            ).first()

            if not existing_img:
                new_image = models.ImageMedicale(
                    type_examen=action['type_examen'],
                    description=action['description'],
                    fichier_url=file_url,
                    format_image=filename.split('.')[-1].lower()
                )
                self.db.add(new_image)
                self.db.flush()
                image_id = new_image.id
                print(f"    -> Image cataloguée : {filename} (ID: {image_id})")
            else:
                image_id = existing_img.id

            # Lier aux Cas Cliniques
            for case_id_csv in action['cas_ids']: 
                
                # Pour chaque ID de la liste, on applique le décalage
                case_id_db = case_id_csv + 908  
                
                # On cherche le cas correspondant en base
                case = self.db.query(models.ClinicalCase).filter(models.ClinicalCase.id == case_id_db).first()
                if case:
                    # ... (le reste du code utilise 'case', donc c'est bon)
                    if case.images_associees_ids is None:
                        case.images_associees_ids = []
                    
                    current_ids = list(case.images_associees_ids)
                    if image_id not in current_ids:
                        current_ids.append(image_id)
                        case.images_associees_ids = current_ids
                        print(f"       -> ✅ Liée au cas {case_id_db} ({case.code_fultang})")

        try:
            self.db.commit()
        except Exception as e:
            print(f"❌ Erreur commit : {e}")
            self.db.rollback()