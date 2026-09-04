from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import schemas
from ..database import get_db
from ..models import Discipline, MajorProcess, Owner

router = APIRouter(prefix="/api/owners", tags=["owners"])


def _apply_role_scoped_assignments(db: Session, owner: Owner, payload: schemas.OwnerIn) -> None:
    """역할에 맞는 소속만 반영한다 (TECH_LEAD -> 대공정, DESIGNER -> 공종, ADMIN -> 둘 다 없음)."""
    owner.major_processes = (
        db.query(MajorProcess).filter(MajorProcess.id.in_(payload.major_process_ids)).all()
        if payload.role == schemas.OwnerRole.TECH_LEAD
        else []
    )
    owner.disciplines = (
        db.query(Discipline).filter(Discipline.id.in_(payload.discipline_ids)).all()
        if payload.role == schemas.OwnerRole.DESIGNER
        else []
    )


@router.get("", response_model=list[schemas.OwnerOut])
def list_owners(db: Session = Depends(get_db)):
    return db.query(Owner).order_by(Owner.id).all()


@router.post("", response_model=schemas.OwnerOut)
def create_owner(payload: schemas.OwnerIn, db: Session = Depends(get_db)):
    owner = Owner(name=payload.name, email=payload.email, role=payload.role)
    db.add(owner)
    db.flush()
    _apply_role_scoped_assignments(db, owner, payload)
    db.commit()
    db.refresh(owner)
    return owner


@router.put("/{owner_id}", response_model=schemas.OwnerOut)
def update_owner(owner_id: int, payload: schemas.OwnerIn, db: Session = Depends(get_db)):
    owner = db.get(Owner, owner_id)
    if owner is None:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")
    owner.name = payload.name
    owner.email = payload.email
    owner.role = payload.role
    _apply_role_scoped_assignments(db, owner, payload)
    db.commit()
    db.refresh(owner)
    return owner
