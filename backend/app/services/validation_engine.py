"""제원표에 활성화된 검증 규칙들을 실행하는 엔진."""
import re

from sqlalchemy.orm import Session

from ..models import (
    RuleSeverity,
    SpecSheet,
    ValidationResult,
    ValidationResultStatus,
    ValidationRule,
)
from .rules import RULE_REGISTRY, RuleContext


def run_validation(db: Session, spec_sheet: SpecSheet) -> list[ValidationResult]:
    """
    spec_sheet 에 적용 가능한 활성 규칙들을 모두 돌려서 ValidationResult 를 생성한다.

    이미 Q&A로 처리 중/완료된(RESOLVED/IN_QA) 결과는 유지하고, 아직 미해결(OPEN)인
    이전 결과만 재검증 전에 정리한 뒤 새로 채운다 (같은 이슈 중복 방지, 이력은 보존).
    """
    # 미해결 이전 결과 제거 (재실행 시 중복 누적 방지)
    stale = [r for r in spec_sheet.validation_results if r.status == ValidationResultStatus.OPEN]
    for r in stale:
        db.delete(r)
    db.flush()

    rules = (
        db.query(ValidationRule)
        .filter(ValidationRule.active.is_(True))
        .filter(
            (ValidationRule.major_process_id.is_(None))
            | (ValidationRule.major_process_id == spec_sheet.major_process_id)
        )
        .all()
    )
    # equipment_module 매칭은 대소문자 무시 부분 문자열로 처리.
    # SpecSheet.equipment_module 은 이제 참고용 요약 문자열(비어있을 수 있음)이라,
    # 특정 설비모듈을 조건으로 거는 규칙은 이 요약에 해당 문자열이 없으면 건너뛴다.
    # (설비모듈별로 더 정밀하게 걸고 싶다면 field_name_pattern 에 대분류를 포함시키면 된다,
    #  예: "GAS/AIR_유량")
    rules = [
        r
        for r in rules
        if not r.equipment_module
        or (spec_sheet.equipment_module and r.equipment_module.strip().upper() in spec_sheet.equipment_module.upper())
    ]

    created: list[ValidationResult] = []

    for rule in rules:
        fn = RULE_REGISTRY.get(rule.rule_type)
        if fn is None:
            continue  # 알 수 없는 rule_type은 조용히 skip (등록 안 된 플러그인)

        try:
            pattern = re.compile(rule.field_name_pattern, re.IGNORECASE)
        except re.error:
            continue

        for field in spec_sheet.fields:
            if not field.field_name or not pattern.search(field.field_name):
                continue

            outcome = fn(
                RuleContext(spec_field=field, params=rule.params or {}, default_severity=rule.severity)
            )
            if outcome is None:
                continue

            result = ValidationResult(
                spec_sheet_id=spec_sheet.id,
                spec_field_id=field.id,
                rule_id=rule.id,
                severity=outcome.severity or rule.severity or RuleSeverity.ERROR,
                message=outcome.message,
                status=ValidationResultStatus.OPEN,
            )
            db.add(result)
            created.append(result)

    db.flush()
    return created
