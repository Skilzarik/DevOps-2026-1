from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel
from ..database import get_db
from .. import models, schemas, auth

router = APIRouter(prefix="/discs", tags=["discs"])

class RestockRequest(BaseModel):
    quantity: int

@router.get("/", response_model=List[schemas.DiscResponse])
def read_discs(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    discs = db.query(models.Disc).all()
    return discs

@router.post("/", response_model=schemas.DiscResponse, status_code=status.HTTP_201_CREATED)
def create_disc(
    disc: schemas.DiscCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_admin)
):
    musician = db.query(models.Musician).filter(models.Musician.id == disc.musician_id).first()
    if not musician:
        raise HTTPException(status_code=400, detail="Musician not found")
    db_disc = models.Disc(
        **disc.dict(),
        created_by=current_user.id
    )
    db.add(db_disc)
    db.commit()
    db.refresh(db_disc)
    return db_disc

@router.post("/{disc_id}/restock", response_model=schemas.DiscResponse)
def restock_disc(
    disc_id: int,
    restock_data: RestockRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_admin)
):
    disc = db.query(models.Disc).filter(models.Disc.id == disc_id).first()
    if not disc:
        raise HTTPException(status_code=404, detail="Диск не найден")
    
    if restock_data.quantity <= 0:
        raise HTTPException(status_code=400, detail="Количество должно быть больше нуля")

    disc.stock += restock_data.quantity
    db.commit()
    db.refresh(disc)
    return disc

@router.delete("/{disc_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_disc(
    disc_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_admin)
):
    disc = db.query(models.Disc).filter(models.Disc.id == disc_id).first()
    if not disc:
        raise HTTPException(status_code=404, detail="Disc not found")
    
    if disc.sales:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete disc with existing sales"
        )
    
    db.delete(disc)
    db.commit()
    return None