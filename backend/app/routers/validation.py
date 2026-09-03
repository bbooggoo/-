from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import schemas
from ..database import get_db
from ..models import SpecSheet, ValidationRule
from ..services.rules import RULE_REGISTRY

router = APIRouter(prefix="/api/validation-rules", tags=["validation"])


@router.get("", response_model=list[schemas.ValidationRuleOut])
def list_rules(db: Session = Depends(get_db)):
    return db.query(ValidationRule).order_by(ValidationRule.id).all()


@router.get("/rule-types")
def list_rule_types():
    """현재 플러그인 레지스트리에 등록된 규칙 타입 키 목록."""
    return sorted(RULE_REGISTRY.keys())


@router.post("", response_model=schemas.ValidationRuleOut)
def create_rule(payload: schemas.ValidationRuleIn, db: Session = Depends(get_db)):
    if payload.rule_type not in RULE_REGISTRY:
        raise HTTPException(
            status_code=400,
            detail=f"알 수 없는 rule_type 입니다. 사용 가능: {sorted(RULE_REGISTRY.keys())}",
        )
    rule = ValidationRule(**payload.model_dump())
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


@router.put("/{rule_id}", response_model=schemas.ValidationRuleOut)
def update_rule(rule_id: int, payload: schemas.ValidationRuleIn, db: Session = Depends(get_db)):
    rule = db.get(ValidationRule, rule_id)
    if rule is None:
        raise HTTPException(status_code=404, detail="규칙을 찾을 수 없습니다.")
    for k, v in payload.model_dump().items():
        setattr(rule, k, v)
    db.commit()
    db.refresh(rule)
    return rule


@router.delete("/{rule_id}")
def delete_rule(rule_id: int, db: Session = Depends(get_db)):
    rule = db.get(ValidationRule, rule_id)
    if rule is None:
        raise HTTPException(status_code=404, detail="규칙을 찾을 수 없습니다.")
    db.delete(rule)
    db.commit()
    return {"ok": True}
