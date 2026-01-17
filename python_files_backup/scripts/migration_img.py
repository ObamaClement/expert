import sys
import os
import cloudinary
import cloudinary.uploader
from sqlalchemy.orm import Session
from datetime import datetime

# Configuration du chemin pour les imports de l'application
# Permet au script de "voir" le dossier app/ même s'il est dans scripts/
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.database import SessionLocal
from app.models.media import ImageMedicale
from app.config import settings

# 1. Configuration Cloudinary
# Les clés sont chargées depuis votre fichier .env via settings
cloudinary.config( 
    cloud_name = settings.CLOUDINARY_CLOUD_NAME, 
    api_key = settings.CLOUDINARY_API_KEY, 
    api_secret = settings.CLOUDINARY_API_SECRET,
    secure = True
)

OUTPUT_LOG_FILE = "migration_mapping_log.txt"

def migrate_images():
    print("🚀 Démarrage de la migration des images vers Cloudinary...")
    print(f"📄 Un rapport sera généré dans : {OUTPUT_LOG_FILE}")
    
    db = SessionLocal()
    mapping_log = [] # Liste pour stocker les correspondances
    
    try:
        # 2. Récupérer les images locales
        # On filtre celles qui ne commencent PAS par 'http'
        images_to_migrate = db.query(ImageMedicale).filter(
            ~ImageMedicale.fichier_url.like('http%')
        ).all()
        
        total_images = len(images_to_migrate)
        print(f"📊 {total_images} images trouvées à migrer.")
        
        # En-tête du fichier de log
        mapping_log.append(f"--- RAPPORT DE MIGRATION DU {datetime.now()} ---")
        mapping_log.append(f"Total à traiter : {total_images}\n")
        mapping_log.append(f"{'ID':<5} | {'ANCIEN CHEMIN LOCAL':<60} | {'NOUVELLE URL CLOUDINARY'}")
        mapping_log.append("-" * 150)
        
        success_count = 0
        error_count = 0
        
        for img in images_to_migrate:
            # Reconstruire le chemin absolu du fichier sur votre machine
            # On suppose que le chemin en BDD est relatif à la racine du projet
            # ex: "storage/media/images/radio.jpg"
            local_rel_path = img.fichier_url
            local_abs_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', local_rel_path))
            
            print(f"  -> Traitement ID {img.id}...")
            
            if os.path.exists(local_abs_path):
                try:
                    # 3. Upload vers Cloudinary
                    # folder="sti_medical/radiology" permet de ranger les fichiers dans le cloud
                    upload_result = cloudinary.uploader.upload(
                        local_abs_path, 
                        folder="sti_medical_expert/radiology",
                        public_id=f"img_{img.id}_{os.path.basename(local_abs_path).split('.')[0]}" 
                    )
                    
                    new_url = upload_result.get("secure_url")
                    
                    # 4. Mise à jour de la Base de Données
                    img.fichier_url = new_url
                    
                    # Ajout au rapport
                    log_line = f"{img.id:<5} | {local_rel_path:<60} | {new_url}"
                    mapping_log.append(log_line)
                    
                    success_count += 1
                    print(f"     ✅ Succès.")
                    
                except Exception as e:
                    error_msg = f"ERREUR UPLOAD: {str(e)}"
                    print(f"     ❌ {error_msg}")
                    mapping_log.append(f"{img.id:<5} | {local_rel_path:<60} | {error_msg}")
                    error_count += 1
            else:
                error_msg = "FICHIER LOCAL INTROUVABLE"
                print(f"     ⚠️ {error_msg} : {local_abs_path}")
                mapping_log.append(f"{img.id:<5} | {local_rel_path:<60} | {error_msg}")
                error_count += 1
        
        # Validation finale des changements en BDD
        db.commit()
        
        # Écriture du fichier de log
        mapping_log.append("\n" + "-" * 150)
        mapping_log.append(f"RÉSUMÉ : Succès {success_count} / Erreurs {error_count}")
        
        with open(OUTPUT_LOG_FILE, "w", encoding="utf-8") as f:
            f.write("\n".join(mapping_log))
            
        print(f"\n✨ Migration terminée.")
        print(f"✅ Succès : {success_count}")
        print(f"❌ Erreurs : {error_count}")
        print(f"📄 Rapport sauvegardé : {os.path.abspath(OUTPUT_LOG_FILE)}")
        
    except Exception as e:
        print(f"❌ Erreur critique du script : {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    migrate_images()