import sys
import os
from sqlalchemy.orm import Session
from collections import defaultdict
import random

# Ajoute la racine du projet au path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.database import SessionLocal
from app import models

def link_images_to_cases():
    """
    Script pour lier les images existantes aux cas cliniques basés sur la pathologie.
    """
    print("🚀 Démarrage du script de liaison Images ↔ Cas Cliniques...")
    
    db = SessionLocal()
    
    try:
        # --- Étape 1: Pré-charger toutes les images par pathologie ---
        print("  -> Pré-chargement de la bibliothèque d'images...")
        
        images_by_pathology = defaultdict(list)
        all_images = db.query(models.ImageMedicale).filter(
            models.ImageMedicale.pathologie_id.isnot(None)
        ).all()
        
        for img in all_images:
            images_by_pathology[img.pathologie_id].append(img.id)
            
        print(f"     -> {len(all_images)} images trouvées et groupées par {len(images_by_pathology)} pathologies.")

        # --- Étape 2: Parcourir tous les cas cliniques ---
        print("\n  -> Analyse des cas cliniques à enrichir...")
        
        # On ne prend que les cas qui n'ont pas encore d'images
        cases_to_update = db.query(models.ClinicalCase).filter(
            (models.ClinicalCase.images_associees_ids == None) |
            (models.ClinicalCase.images_associees_ids == [])
        ).all()
        
        print(f"     -> {len(cases_to_update)} cas cliniques sans images trouvés.")
        
        update_count = 0
        
        for case in cases_to_update:
            pathologie_id = case.pathologie_principale_id
            
            # --- Étape 3: Trouver des images compatibles ---
            if pathologie_id in images_by_pathology:
                
                # Récupérer la liste des images disponibles pour cette pathologie
                available_image_ids = images_by_pathology[pathologie_id]
                
                # --- Étape 4: Créer le lien ---
                # On associe une image aléatoire parmi celles disponibles
                selected_image_id = random.choice(available_image_ids)
                
                case.images_associees_ids = [selected_image_id]
                
                print(f"     -> ✅ Cas {case.id} (Pathologie {pathologie_id}) lié à l'Image {selected_image_id}.")
                update_count += 1
        
        if update_count > 0:
            print(f"\n  -> Validation de {update_count} mises à jour dans la base de données...")
            db.commit()
            print("     -> ✅ Terminé.")
        else:
            print("\n  -> Aucun nouveau lien à créer.")

        print(f"\n✨ Script de liaison terminé. {update_count} cas cliniques ont été enrichis avec une image.")
        
    except Exception as e:
        print(f"❌ Erreur critique : {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    link_images_to_cases()