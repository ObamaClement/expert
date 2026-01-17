import os
from sqlalchemy.orm import Session
from typing import List, Optional
from fastapi import UploadFile
import cloudinary
import cloudinary.uploader

from .. import models, schemas
from ..config import settings

# --- CONFIGURATION CLOUDINARY ---
# Cette configuration est faite une seule fois au chargement du module.
# Elle utilise les variables chargées depuis votre fichier .env.
cloudinary.config(
    cloud_name = settings.CLOUDINARY_CLOUD_NAME,
    api_key = settings.CLOUDINARY_API_KEY,
    api_secret = settings.CLOUDINARY_API_SECRET,
    secure = True
)


async def save_upload_file_to_cloud(upload_file: UploadFile) -> str:
    """
    Fonction utilitaire pour uploader un fichier directement vers Cloudinary
    et retourner son URL sécurisée.
    """
    try:
        # Lire le contenu du fichier en mémoire
        content = await upload_file.read()
        
        # Envoyer le contenu à Cloudinary
        upload_result = cloudinary.uploader.upload(
            content,
            folder="sti_medical_expert/uploads"  # Dossier de destination sur Cloudinary
        )
        
        # Récupérer l'URL sécurisée (https://...)
        secure_url = upload_result.get("secure_url")
        if not secure_url:
            raise Exception("Échec de l'upload vers Cloudinary, URL non retournée.")
            
        return secure_url
    finally:
        # Toujours fermer le fichier après lecture
        await upload_file.close()


async def create_image_medicale(
    db: Session,
    file: UploadFile,
    type_examen: str,
    sous_type: Optional[str] = None,
    pathologie_id: Optional[int] = None,
    description: Optional[str] = None
) -> models.ImageMedicale:
    """
    Crée une nouvelle entrée pour une image médicale.
    1. Sauvegarde le fichier sur Cloudinary.
    2. Crée l'enregistrement correspondant en base de données avec l'URL cloud.
    """
    # 1. Sauvegarder le fichier physique sur le cloud
    cloud_url = await save_upload_file_to_cloud(file)

    # 2. Créer l'objet SQLAlchemy avec les métadonnées et l'URL cloud
    db_image = models.ImageMedicale(
        type_examen=type_examen,
        sous_type=sous_type,
        pathologie_id=pathologie_id,
        description=description,
        fichier_url=cloud_url, # <-- C'est maintenant l'URL Cloudinary !
        format_image=file.content_type.split('/')[-1] if file.content_type else None,
        taille_ko=file.size // 1024 if file.size else None,
    )
    
    db.add(db_image)
    db.commit()
    db.refresh(db_image)
    
    return db_image


def get_image_medicale_by_id(db: Session, image_id: int) -> Optional[models.ImageMedicale]:
    """
    Récupère une image médicale par son ID.
    """
    return db.query(models.ImageMedicale).filter(models.ImageMedicale.id == image_id).first()


def get_all_images_medicales(db: Session, skip: int = 0, limit: int = 100) -> List[models.ImageMedicale]:
    """
    Récupère une liste de toutes les images médicales avec pagination.
    """
    return db.query(models.ImageMedicale).offset(skip).limit(limit).all()


def update_image_medicale_metadata(
    db: Session,
    image_id: int,
    image_update: schemas.ImageMedicaleUpdate
) -> Optional[models.ImageMedicale]:
    """
    Met à jour les métadonnées d'une image médicale existante.
    """
    db_image = get_image_medicale_by_id(db, image_id)
    if not db_image:
        return None

    update_data = image_update.model_dump(exclude_unset=True)
    
    for key, value in update_data.items():
        setattr(db_image, key, value)
        
    db.commit()
    db.refresh(db_image)
    
    return db_image


def delete_image_medicale(db: Session, image_id: int) -> Optional[models.ImageMedicale]:
    """
    Supprime une image médicale.
    1. Supprime l'enregistrement de la base de données.
    2. (Optionnel) Supprime le fichier sur Cloudinary.
    """
    db_image = get_image_medicale_by_id(db, image_id)
    if not db_image:
        return None

    # Optionnel : Ajouter ici la logique pour supprimer l'image de Cloudinary
    # via cloudinary.uploader.destroy(...) si vous voulez un nettoyage complet.
    # Pour l'instant, nous nous contentons de supprimer la référence.

    db.delete(db_image)
    db.commit()
    
    return db_image