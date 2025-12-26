import os
import shutil
from sqlalchemy.orm import Session
from typing import List, Optional
from fastapi import UploadFile

from .. import models, schemas

# Définir le chemin de base pour le stockage.
# Plus tard, cela pourrait pointer vers un service cloud comme S3.
STORAGE_PATH = "storage/media/images"


async def save_upload_file(upload_file: UploadFile, destination: str) -> None:
    """
    Fonction utilitaire pour sauvegarder un fichier uploadé sur le disque.
    """
    try:
        # Assurer que le dossier de destination existe
        os.makedirs(os.path.dirname(destination), exist_ok=True)
        with open(destination, "wb") as buffer:
            # Lire le contenu du fichier par morceaux pour ne pas surcharger la mémoire
            shutil.copyfileobj(upload_file.file, buffer)
    finally:
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
    1. Sauvegarde le fichier sur le disque.
    2. Crée l'enregistrement correspondant en base de données.
    """
    # Définir le chemin de sauvegarde du fichier
    file_path = os.path.join(STORAGE_PATH, file.filename)
    
    # Sauvegarder le fichier physique
    await save_upload_file(file, file_path)

    # Créer l'objet SQLAlchemy avec les métadonnées
    db_image = models.ImageMedicale(
        type_examen=type_examen,
        sous_type=sous_type,
        pathologie_id=pathologie_id,
        description=description,
        fichier_url=file_path, # Stocke le chemin d'accès
        format_image=file.content_type,
        taille_ko=file.size // 1024 if file.size else None,
        # Les autres champs (embedding, etc.) seront remplis plus tard
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
    2. Supprime le fichier physique du disque.
    """
    db_image = get_image_medicale_by_id(db, image_id)
    if not db_image:
        return None

    # Supprimer le fichier physique s'il existe
    if db_image.fichier_url and os.path.exists(db_image.fichier_url):
        os.remove(db_image.fichier_url)

    db.delete(db_image)
    db.commit()
    
    return db_image