"""제원표에 활성화된 검증 규칙들을 실행하는 엔진."""
import re

from sqlalchemy.orm import Session

from ..models import (
    RuleSeverity,
    SpecField,
    SpecSheet,
    ValidationResult,
    ValidationResultStatus,
    ValidationRule,
)
from .rules import RULE_REGISTRY, RuleContext


def _applicable_rules(db: Session, spec_sheet: SpecSheet) -> list[ValidationRule]:
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
    return [
        r
        for r in rules
        if not r.equipment_module
        or (spec_sheet.equipment_module and r.equipment_module.strip().upper() in spec_sheet.equipment_module.upper())
    ]


def run_validation(db: Session, spec_sheet: SpecSheet) -> list[ValidationResult]:
    """
    spec_sheet 에 적용 가능한 활성 규칙들을 모두 돌려서 ValidationResult 를 생성한다.

    이미 Q&A로 처리 중/완료된(RESOLVED/IN_QA) 결과는 유지하고, 아직 미해결(OPEN)인
    이전 결과만 재검증 전에 정리한 뒤 새로 채운다 (같은 이슈 중복 방지, 이력은 보존).
    """
    # 미해결 이전 결과 제거 (재실행 시 중복 누적 방지).
    # spec_sheet.validation_results 컬렉션에서 직접 remove() 해야
    # cascade="all, delete-orphan"이 DB에서도 지우고, 이미 이 세션에서 이 컬렉션을
    # 읽어간 다른 코드(예: 시트 상태 재계산)에도 곧바로 반영된다. db.delete(r)만
    # 쓰면 DB에서는 지워져도 이미 로드된 spec_sheet.validation_results 파이썬
    # 리스트에는 그대로 남아 있어(세션이 만료/새로고침되기 전까지) 낡은 상태로 보인다.
    stale = [r for r in spec_sheet.validation_results if r.status == ValidationResultStatus.OPEN]
    for r in stale:
        spec_sheet.validation_results.remove(r)
    db.flush()

    rules = _applicable_rules(db, spec_sheet)

    # 행(row_index)별 {field_name: value} 맵 - 같은 행의 다른 항목(예: 성상명)을
    # 참조해야 하는 규칙(max_value_by_group 등)을 위해 미리 만들어둔다.
    rows_by_index: dict[int, dict[str, str]] = {}
    for f in spec_sheet.fields:
        if not f.field_name:
            continue
        rows_by_index.setdefault(f.row_index, {})[f.field_name] = f.value or ""

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
                RuleContext(
                    spec_field=field,
                    params=rule.params or {},
                    default_severity=rule.severity,
                    siblings=rows_by_index.get(field.row_index, {}),
                )
            )
            if outcome is None:
                continue

            result = ValidationResult(
                spec_field_id=field.id,
                rule_id=rule.id,
                severity=outcome.severity or rule.severity or RuleSeverity.ERROR,
                message=outcome.message,
                status=ValidationResultStatus.OPEN,
                suggested_value=outcome.suggested_value,
            )
            # append(관계)로 추가해야 spec_sheet_id도 자동으로 채워지고, 이미 로드된
            # spec_sheet.validation_results 컬렉션도 곧바로 최신 상태를 반영한다
            # (위 stale 제거와 같은 이유).
            spec_sheet.validation_results.append(result)
            created.append(result)

    db.flush()
    return created


def validate_candidate_value(db: Session, spec_field: SpecField, candidate_value: str) -> tuple[list[str], list[str]]:
    """수동 제원 질의에서 기술팀이 제안하는 새 값이 검증 규칙(성상명/자재명 허용값,
    유량 상한 등)을 통과하는지 확인한다 (item 3: "제원 입력 오류 안되게 룰셋").

    같은 행의 다른 필드(형제 필드)는 현재 DB 값을 그대로 쓰고, 검사 대상 필드 자신만
    candidate_value 로 바꿔서 판단한다. ERROR 등급 위반은 errors(제출 차단), WARN 등급은
    warnings(통과는 시키되 사용자에게 보여줌)로 나눠 반환한다.

    반환값이 비어있으면(둘 다 빈 리스트) 통과.
    """
    spec_sheet = spec_field.spec_sheet
    rules = _applicable_rules(db, spec_sheet)

    rows_by_index: dict[str, str] = {}
    for f in spec_sheet.fields:
        if not f.field_name or f.row_index != spec_field.row_index:
            continue
        rows_by_index[f.field_name] = f.value or ""
    if spec_field.field_name:
        rows_by_index[spec_field.field_name] = candidate_value

    candidate_field = SpecField(
        spec_sheet_id=spec_field.spec_sheet_id,
        row_index=spec_field.row_index,
        col_index=spec_field.col_index,
        field_name=spec_field.field_name,
        value=candidate_value,
        unit=spec_field.unit,
    )

    errors: list[str] = []
    warnings: list[str] = []
    for rule in rules:
        fn = RULE_REGISTRY.get(rule.rule_type)
        if fn is None or not spec_field.field_name:
            continue
        try:
            pattern = re.compile(rule.field_name_pattern, re.IGNORECASE)
        except re.error:
            continue
        if not pattern.search(spec_field.field_name):
            continue

        outcome = fn(
            RuleContext(
                spec_field=candidate_field,
                params=rule.params or {},
                default_severity=rule.severity,
                siblings=rows_by_index,
            )
        )
        if outcome is None:
            continue
        severity = outcome.severity or rule.severity or RuleSeverity.ERROR
        (errors if severity == RuleSeverity.ERROR else warnings).append(outcome.message)

    return errors, warnings
