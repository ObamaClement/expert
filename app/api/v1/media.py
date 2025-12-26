from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
    UploadFile,
    File,
    Form
)
from sqlalchemy.orm import Session
from typing import List, Optional

from ... import schemas, models
from ...services import media_service
from ...dependencies import get_db

router = APIRouter(
    prefix="/media",
    tags=["Media"]
)


@router.post("/images/upload", response_model=schemas.media.ImageMedicale, status_code=status.HTTP_201_CREATED)
async def upload_image_medicale(
    file: UploadFile = File(..., description="Le fichier image à uploader"),
    type_examen: str = Form(..., description="Type d'examen (ex: Radiographie)"),
    sous_type: Optional[str] = Form(None, description="Sous-type (ex: Thorax)"),
    pathologie_id: Optional[int] = Form(None, description="ID de la pathologie associée"),
    description: Optional[str] = Form(None, description="Description de l'image"),
    db: Session = Depends(get_db)
):
    """
    Uploade une image médicale et crée l'enregistrement de ses métadonnées.
    """
    # Vérifier le type de fichier si nécessaire
    if not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Le fichier uploadé n'est pas une image."
        )

    db_image = await media_service.create_image_medicale(
        db=db,
        file=file,
        type_examen=type_examen,
        sous_type=sous_type,
        pathologie_id=pathologie_id,
        description=description
    )
    return db_image


@router.get("/images", response_model=List[schemas.media.ImageMedicale])
def read_all_images_metadata(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    Récupère une liste des métadonnées de toutes les images médicales.
    """
    images = media_service.get_all_images_medicales(db, skip=skip, limit=limit)
    return images


@router.get("/images/{image_id}", response_model=schemas.media.ImageMedicale)
def read_image_metadata(image_id: int, db: Session = Depends(get_db)):
    """
    Récupère les métadonnées d'une image médicale spécifique par son ID.
    """
    db_image = media_service.get_image_medicale_by_id(db, image_id=image_id)
    if db_image is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image non trouvée.")
    return db_image


@router.patch("/images/{image_id}", response_model=schemas.media.ImageMedicale)
def update_image_metadata(
    image_id: int,
    metadata_update: schemas.media.ImageMedicaleUpdate,
    db: Session = Depends(get_db)
):
    """
    Met à jour les métadonnées d'une image médicale existante.
    """
    db_image = media_service.update_image_medicale_metadata(db, image_id=image_id, image_update=metadata_update)
    if db_image is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image non trouvée.")
    return db_image


@router.delete("/images/{image_id}", response_model=schemas.media.ImageMedicale)
def delete_image(image_id: int, db: Session = Depends(get_db)):
    """
    Supprime une image médicale (métadonnées et fichier physique).
    """
    db_image = media_service.delete_image_medicale(db, image_id=image_id)
    if db_image is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image non trouvée.")
    return db_image