<<<<<<< HEAD
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from ..database import get_db
from .. import models, schemas, auth

router = APIRouter(prefix="/sales", tags=["sales"])

@router.get("/", response_model=List[schemas.SaleResponse])
def read_sales(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    sales = db.query(models.Sale).order_by(models.Sale.sold_at.desc()).all()
    return sales

@router.post("/", response_model=schemas.SaleResponse, status_code=status.HTTP_201_CREATED)
def create_sale(
    sale: schemas.SaleCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    disc = db.query(models.Disc).filter(models.Disc.id == sale.disc_id).first()
    if not disc:
        raise HTTPException(status_code=404, detail="Disc not found")

    if disc.stock < sale.quantity:
        raise HTTPException(
            status_code=400,
            detail=f"Not enough stock. Available: {disc.stock}"
        )

    total_price = disc.price * sale.quantity
    db_sale = models.Sale(
        disc_id=sale.disc_id,
        quantity=sale.quantity,
        total_price=total_price,
        seller_id=current_user.id
    )
    disc.stock -= sale.quantity
    
    db.add(db_sale)
    db.commit()
    db.refresh(db_sale)
=======
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from ..database import get_db
from .. import models, schemas, auth

router = APIRouter(prefix="/sales", tags=["sales"])

@router.get("/", response_model=List[schemas.SaleResponse])
def read_sales(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    sales = db.query(models.Sale).order_by(models.Sale.sold_at.desc()).all()
    return sales

@router.post("/", response_model=schemas.SaleResponse, status_code=status.HTTP_201_CREATED)
def create_sale(
    sale: schemas.SaleCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    disc = db.query(models.Disc).filter(models.Disc.id == sale.disc_id).first()
    if not disc:
        raise HTTPException(status_code=404, detail="Disc not found")

    if disc.stock < sale.quantity:
        raise HTTPException(
            status_code=400,
            detail=f"Not enough stock. Available: {disc.stock}"
        )

    total_price = disc.price * sale.quantity
    db_sale = models.Sale(
        disc_id=sale.disc_id,
        quantity=sale.quantity,
        total_price=total_price,
        seller_id=current_user.id
    )
    disc.stock -= sale.quantity
    
    db.add(db_sale)
    db.commit()
    db.refresh(db_sale)
>>>>>>> origin/feature/sales-and-devops
    return db_sale