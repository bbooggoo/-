from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import schemas
from ..database import get_db
from ..models import MajorProcess, Owner

router = APIRouter(prefix="/api/owners", tags=["owners"])


@router.get("", response_model=list[schemas.OwnerOut])
def list_owners(db: Session = Depends(get_db)):
    return db.query(Owner).order_by(Owner.id).all()


@router.post("", response_model=schemas.OwnerOut)
def create_owner(payload: schemas.OwnerIn, db: Session = Depends(get_db)):
    owner = Owner(name=payload.name, email=payload.email)
    if payload.major_process_ids:
        owner.major_processes = (
            db.query(MajorProcess).filter(MajorProcess.id.in_(payload.major_process_ids)).all()
        )
    db.add(owner)
    db.commit()
    db.refresh(owner)
    return owner


@router.put("/{owner_id}", response_model=schemas.OwnerOut)
def update_owner(owner_id: int, payload: schemas.OwnerIn, db: Session = Depends(get_db)):
    owner = db.get(Owner, owner_id)
    if owner is None:
        raise HTTPException(status_code=404, detail="담당자를 찾을 수 없습니다.")
    owner.name = payload.name
    owner.email = payload.email
    owner.major_processes = (
        db.query(MajorProcess).filter(MajorProcess.id.in_(payload.major_process_ids)).all()
    )
    db.commit()
    db.refresh(owner)
    return owner
