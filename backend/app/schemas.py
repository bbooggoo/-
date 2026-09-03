"""Pydantic 스키마 (요청/응답 모델)."""
import datetime
import re

from pydantic import BaseModel, ConfigDict, field_validator

from .models import (
    CorrectionSource,
    QAMessageRole,
    QAThreadStatus,
    RuleSeverity,
    SpecSheetStatus,
    ValidationResultStatus,
)

# 건설코드 형식: P 로 시작하는 8자리 영숫자, 뒤에 "-01" 같은 2자리 일련번호가 붙을 수 있다.
# MAIN 설비 + 거기 붙는 부대설비들이 같은 건설코드를 공유하면서 각자 별도 항목(따라서 별도
# 제원표)으로 추적돼야 해서, 실제로는 PD000102-01(MAIN)/-02/-03(부대설비) 처럼 일련번호가 붙어
# 반복된다. 접미사가 없는 순수 8자리 코드도 계속 허용한다 (하위 호환).
# ※ 예시로 받은 "PDXXXXX" 표기와 "8글자" 설명이 정확히 일치하지 않아, 우선 8자리로 구현.
#   실제 규칙 확정되면 이 정규식 한 곳만 수정하면 됨.
CONSTRUCTION_CODE_REGEX = re.compile(r"^P[A-Za-z0-9]{7}(-\d{2})?$")


class MajorProcessOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    code: str
    name: str


class OwnerIn(BaseModel):
    name: str
    email: str | None = None
    major_process_ids: list[int] = []


class OwnerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    email: str | None
    major_processes: list[MajorProcessOut] = []


class SpecFieldOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    row_index: int
    col_index: int
    field_name: str | None
    value: str | None
    unit: str | None


class ValidationResultOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    spec_field_id: int | None
    rule_id: int | None
    severity: RuleSeverity
    message: str
    status: ValidationResultStatus
    created_at: datetime.datetime


class SpecSheetListOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    major_process: MajorProcessOut
    construction_code: str
    equipment_module: str | None
    title: str
    version: int
    status: SpecSheetStatus
    uploaded_by: str | None
    uploaded_at: datetime.datetime
    open_issue_count: int = 0


class SpecSheetDetailOut(SpecSheetListOut):
    fields: list[SpecFieldOut] = []
    validation_results: list[ValidationResultOut] = []


class SpecSheetUploadResultOut(BaseModel):
    """업로드 1건이 건설코드별로 여러 SpecSheet 로 나뉠 수 있어 목록 + 경고로 반환."""

    created: list[SpecSheetDetailOut] = []
    warnings: list[str] = []


class ValidationRuleIn(BaseModel):
    name: str
    rule_type: str
    major_process_id: int | None = None
    equipment_module: str | None = None
    field_name_pattern: str
    params: dict = {}
    severity: RuleSeverity = RuleSeverity.ERROR
    active: bool = True


class ValidationRuleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    rule_type: str
    major_process_id: int | None
    equipment_module: str | None
    field_name_pattern: str
    params: dict
    severity: RuleSeverity
    active: bool


class QAMessageIn(BaseModel):
    author_name: str
    role: QAMessageRole
    content: str


class QAMessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    author_name: str
    role: QAMessageRole
    content: str
    created_at: datetime.datetime


class QAThreadCreateIn(BaseModel):
    title: str
    spec_field_id: int | None = None
    validation_result_id: int | None = None
    assigned_owner_id: int | None = None
    question: str
    author_name: str = "익명"


class QAThreadOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    spec_sheet_id: int
    spec_field_id: int | None
    validation_result_id: int | None
    major_process: MajorProcessOut
    title: str
    status: QAThreadStatus
    assigned_owner: OwnerOut | None
    created_by: str | None
    created_at: datetime.datetime
    updated_at: datetime.datetime
    messages: list[QAMessageOut] = []


class QAThreadResolveIn(BaseModel):
    resolver_name: str
    new_value: str | None = None  # 값이 있으면 SpecField.value 갱신 + SpecCorrection 기록
    note: str | None = None


class SpecCorrectionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    qa_thread_id: int
    field_name: str | None
    old_value: str | None
    new_value: str | None
    source: CorrectionSource
    applied_by: str | None
    applied_at: datetime.datetime


class CategoryAggregationOut(BaseModel):
    category: str
    unit: str
    group_by: str
    totals: dict[str, float]


def validate_construction_code(value: str) -> str:
    if not CONSTRUCTION_CODE_REGEX.match(value):
        raise ValueError(
            "건설코드는 'P'로 시작하는 8자리 영숫자여야 합니다 (뒤에 '-01' 같은 2자리 일련번호는 선택). "
            "예: PD000001 또는 PD000001-01"
        )
    return value
