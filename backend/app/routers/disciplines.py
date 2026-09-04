from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import schemas
from ..database import get_db
from ..models import Discipline

router = APIRouter(prefix="/api/disciplines", tags=["disciplines"])


@router.get("", response_model=list[schemas.DisciplineOut])
def list_disciplines(db: Session = Depends(get_db)):
    return db.query(Discipline).order_by(Discipline.id).all()
