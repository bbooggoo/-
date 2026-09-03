"""
자동 제원 질의 일괄 생성.

"동일한 종류의 질의는 최대한 묶어서" 처리하기 위해, suggested_value 가 있는(=규칙이
스스로 고칠 값을 계산해낸) 미해결 ValidationResult 들을 (대공정, 규칙, 필드 세부항목,
제안값) 기준으로 묶어서 QAThread 1건 + QAThreadTarget 여러 건으로 만든다. 같은 교정이
시트 수십~수백 개에 걸쳐 반복돼도 기술팀은 이 배치 1건에 대해 승인/미승인 한 번만 누르면
전체에 반영된다.

대공정을 grouping key에 넣는 이유: 기술팀 담당자 권한(require_major_process_access)이
대공정 단위이므로, 한 배치가 여러 대공정에 걸치면 승인 권한자가 애매해진다. 그래서 같은
교정이라도 대공정이 다르면 별도 배치로 나눈다 (그래도 시트가 아니라 대공정 단위로 묶이므로
"시트당 수천 개" 문제는 해결된다).

실행: generate_auto_queries(db) 를 호출하면 새로 생긴 배치 목록을 반환한다. 이미 어떤
AUTO 스레드에 묶인 ValidationResult는 건너뛰어(중복 배치 방지) 여러 번 호출해도 안전하다
(POST /api/qa-threads/generate-auto 에서 사용).
"""
from sqlalchemy.orm import Session

from ..models import (
    CATEGORY_TO_DISCIPLINE_CODE,
    Discipline,
    MajorProcess,
    OwnerRole,
    QAThread,
    QAThreadStatus,
    QAThreadTarget,
    QueryType,
    ValidationResult,
    ValidationResultStatus,
)


def _infer_discipline_id(db: Session, field_name: str | None) -> int | None:
    if not field_name or "_" not in field_name:
        return None
    category = field_name.rsplit("_", 1)[0]
    code = CATEGORY_TO_DISCIPLINE_CODE.get(category)
    if not code:
        return None
    discipline = db.query(Discipline).filter(Discipline.code == code).first()
    return discipline.id if discipline else None


def generate_auto_queries(db: Session) -> list[QAThread]:
    already_targeted_vr_ids = {
        target.validation_result_id
        for thread in db.query(QAThread).filter(QAThread.query_type == QueryType.AUTO).all()
        for target in thread.targets
        if target.validation_result_id is not None
    }

    candidates = (
        db.query(ValidationResult)
        .filter(ValidationResult.suggested_value.isnot(None))
        .filter(ValidationResult.status == ValidationResultStatus.OPEN)
        .all()
    )

    groups: dict[tuple, list[ValidationResult]] = {}
    for vr in candidates:
        if vr.id in already_targeted_vr_ids or vr.spec_field is None or not vr.spec_field.field_name:
            continue
        base_label = vr.spec_field.field_name.rsplit("_", 1)[-1]
        key = (vr.spec_sheet.major_process_id, vr.rule_id, base_label, vr.suggested_value)
        groups.setdefault(key, []).append(vr)

    created: list[QAThread] = []
    for (major_process_id, rule_id, base_label, suggested_value), vrs in groups.items():
        mp = db.get(MajorProcess, major_process_id)
        tech_leads = [o for o in mp.owners if o.role == OwnerRole.TECH_LEAD]
        assigned_owner_id = tech_leads[0].id if len(tech_leads) == 1 else None

        sample_field = vrs[0].spec_field
        discipline_id = _infer_discipline_id(db, sample_field.field_name)
        as_is_sample = sample_field.value

        thread = QAThread(
            query_type=QueryType.AUTO,
            major_process_id=major_process_id,
            discipline_id=discipline_id,
            rule_id=rule_id,
            field_name=sample_field.field_name,
            to_be_value=suggested_value,
            title=f"[자동] {base_label} '{as_is_sample}' → '{suggested_value}' ({len(vrs)}건)",
            status=QAThreadStatus.OPEN,
            assigned_owner_id=assigned_owner_id,
            created_by="시스템(자동 생성)",
        )
        db.add(thread)
        db.flush()

        for vr in vrs:
            db.add(QAThreadTarget(qa_thread_id=thread.id, spec_field_id=vr.spec_field_id, validation_result_id=vr.id))
            vr.status = ValidationResultStatus.IN_QA

        created.append(thread)

    db.flush()
    return created
