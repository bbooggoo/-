"""
Q&A로 실제 반영된 수정 이력 조회.
2단계(자동 수정 제안) 로드맵을 위한 데이터 소스 - 지금은 조회 API만 제공.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import schemas
from ..database import get_db
from ..models import SpecCorrection

router = APIRouter(prefix="/api/corrections", tags=["corrections"])


@router.get("", response_model=list[schemas.SpecCorrectionOut])
def list_corrections(field_name: str | None = None, db: Session = Depends(get_db)):
    q = db.query(SpecCorrection)
    if field_name:
        q = q.filter(SpecCorrection.field_name == field_name)
    return q.order_by(SpecCorrection.applied_at.desc()).all()
