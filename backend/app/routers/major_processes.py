from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import schemas
from ..database import get_db
from ..models import MajorProcess

router = APIRouter(prefix="/api/major-processes", tags=["major-processes"])


@router.get("", response_model=list[schemas.MajorProcessOut])
def list_major_processes(db: Session = Depends(get_db)):
    return db.query(MajorProcess).order_by(MajorProcess.id).all()
