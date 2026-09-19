from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from ..database import get_db
from .. import models, schemas, auth

router = APIRouter(prefix="/musicians", tags=["musicians"])

@router.get("/", response_model=List[schemas.MusicianResponse])
def read_musicians(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    musicians = db.query(models.Musician).all()
    return musicians

@router.post("/", response_model=schemas.MusicianResponse, status_code=status.HTTP_201_CREATED)
def create_musician(
    musician: schemas.MusicianCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_admin)
):
    db_musician = models.Musician(
        **musician.dict(),
        created_by=current_user.id
    )
    db.add(db_musician)
    db.commit()
    db.refresh(db_musician)
    return db_musician

@router.delete("/{musician_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_musician(
    musician_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_admin)
):
    musician = db.query(models.Musician).filter(models.Musician.id == musician_id).first()
    if not musician:
        raise HTTPException(status_code=404, detail="Musician not found")
    
    db.delete(musician)
    db.commit()
    return None