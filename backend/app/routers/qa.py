"""
질의응답 API.

두 트랙:
  AUTO   - services/auto_query.py 가 일괄 생성. /qa-threads/{id}/auto-decision 로
           기술팀이 승인(즉시 반영)/미승인 한 번에 끝낸다.
  MANUAL - 설계사가 /spec-sheets/{id}/qa-threads 로 서술형 질의를 등록하면,
           OPEN -> (기술팀 답변) TECH_ANSWERED -> (설계사 승인) ANSWER_APPROVED
                -> (기술팀 값 제안, 검증 통과 필수) VALUE_PROPOSED
                -> (설계사 최종 승인) RESOLVED  순서로 진행한다.
           각 단계는 아래 전용 엔드포인트로만 전이한다:
             POST .../messages          (OPEN 에서 기술팀 서술형 답변 -> TECH_ANSWERED)
             POST .../answer-decision   (TECH_ANSWERED 에서 설계사 승인/반려)
             POST .../propose-value     (ANSWER_APPROVED 에서 기술팀이 검증된 새 값 제안)
             POST .../final-decision    (VALUE_PROPOSED 에서 설계사 최종 승인/반려 -> DB 반영)
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import schemas
from ..database import get_db
from ..deps import get_current_owner, require_discipline_access, require_major_process_access
from ..models import (
    CorrectionSource,
    Discipline,
    Owner,
    OwnerRole,
    QAMessage,
    QAMessageRole,
    QAThread,
    QAThreadStatus,
    QAThreadTarget,
    QueryType,
    SpecCorrection,
    SpecField,
    SpecSheet,
    SpecSheetStatus,
    ValidationResult,
    ValidationResultStatus,
)
from ..services.auto_query import generate_auto_queries
from ..services.validation_engine import run_validation, validate_candidate_value

router = APIRouter(tags=["qa"])

_TERMINAL = (QAThreadStatus.RESOLVED, QAThreadStatus.REJECTED)


# ---------------------------------------------------------------------------
# 응답 변환 (QAThreadTarget에 스키마상 파생 필드가 있어 수동으로 조립한다)
# ---------------------------------------------------------------------------


def _target_out(t: QAThreadTarget) -> schemas.QAThreadTargetOut:
    return schemas.QAThreadTargetOut(
        id=t.id,
        spec_field_id=t.spec_field_id,
        validation_result_id=t.validation_result_id,
        spec_field=schemas.SpecFieldOut.model_validate(t.spec_field),
        spec_sheet_id=t.spec_field.spec_sheet_id,
        construction_code=t.spec_field.spec_sheet.construction_code,
    )


def _thread_out(t: QAThread) -> schemas.QAThreadOut:
    return schemas.QAThreadOut(
        id=t.id,
        query_type=t.query_type,
        major_process=schemas.MajorProcessOut.model_validate(t.major_process),
        discipline=schemas.DisciplineOut.model_validate(t.discipline) if t.discipline else None,
        field_name=t.field_name,
        to_be_value=t.to_be_value,
        title=t.title,
        status=t.status,
        assigned_owner=schemas.OwnerOut.model_validate(t.assigned_owner) if t.assigned_owner else None,
        created_by=t.created_by,
        created_at=t.created_at,
        updated_at=t.updated_at,
        messages=[schemas.QAMessageOut.model_validate(m) for m in t.messages],
        targets=[_target_out(tg) for tg in t.targets],
    )


# ---------------------------------------------------------------------------
# 시트 상태 동기화 (스레드가 여러 시트에 걸칠 수 있어, 영향받은 시트를 전부 재계산한다)
# ---------------------------------------------------------------------------


def _threads_for_sheet(db: Session, sheet_id: int) -> list[QAThread]:
    return (
        db.query(QAThread)
        .join(QAThreadTarget, QAThreadTarget.qa_thread_id == QAThread.id)
        .join(SpecField, SpecField.id == QAThreadTarget.spec_field_id)
        .filter(SpecField.spec_sheet_id == sheet_id)
        .distinct()
        .all()
    )


def _sync_sheet_status(db: Session, sheet: SpecSheet) -> None:
    threads = _threads_for_sheet(db, sheet.id)
    open_threads = any(t.status not in _TERMINAL for t in threads)
    open_issues = any(
        r.status not in (ValidationResultStatus.RESOLVED, ValidationResultStatus.DISMISSED)
        for r in sheet.validation_results
    )
    if threads and open_threads:
        sheet.status = SpecSheetStatus.IN_QA
    elif sheet.status != SpecSheetStatus.UPLOADED and not open_issues:
        # "검증은 이미 한 번 이상 받았고(=UPLOADED가 아님) 이제 이슈가 없다" - 재검증으로
        # validation_results 가 통째로 비어버린 경우(예: 자동 교정 후 재검증)도 포함해야 해서
        # 리스트 길이가 아니라 status로 "검증 이력이 있는지"를 판단한다.
        sheet.status = SpecSheetStatus.RESOLVED
    # else: UPLOADED 그대로 (아직 검증 전)


def _sync_sheets_for_thread(db: Session, thread: QAThread) -> None:
    sheet_ids = {t.spec_field.spec_sheet_id for t in thread.targets}
    for sid in sheet_ids:
        sheet = db.get(SpecSheet, sid)
        if sheet:
            _sync_sheet_status(db, sheet)


def _apply_to_be_value(thread: QAThread, applied_by: str, db: Session) -> None:
    """thread.to_be_value 를 모든 대상 SpecField에 반영하고 이력을 남긴다.

    값이 바뀐 필드에 이 스레드가 겨냥한 검증 결과 외에 다른 규칙의 결과(예: 같은 필드에
    "표준화 안 됨" WARN 과 "자동 교정 제안" 이 동시에 걸려있던 경우)가 남아있을 수 있어,
    영향받은 시트는 호출부(_sync_sheets_for_thread 이후)에서 재검증해 정리한다.
    """
    source = CorrectionSource.AUTO_SUGGESTED if thread.query_type == QueryType.AUTO else CorrectionSource.MANUAL
    for target in thread.targets:
        field = target.spec_field
        old_value = field.value
        if thread.to_be_value is not None and old_value != thread.to_be_value:
            field.value = thread.to_be_value
            db.add(
                SpecCorrection(
                    qa_thread_id=thread.id,
                    spec_field_id=field.id,
                    field_name=field.field_name,
                    old_value=old_value,
                    new_value=thread.to_be_value,
                    source=source,
                    applied_by=applied_by,
                )
            )
        if target.validation_result:
            target.validation_result.status = ValidationResultStatus.RESOLVED


def _revalidate_sheets_for_thread(db: Session, thread: QAThread) -> None:
    """값 반영 후 영향받은 시트들을 재검증해서, 같은 필드에 남아있을 수 있는 다른 규칙의
    낡은(값이 바뀌기 전 기준) 결과를 정리한다."""
    sheet_ids = {t.spec_field.spec_sheet_id for t in thread.targets}
    for sid in sheet_ids:
        sheet = db.get(SpecSheet, sid)
        if sheet:
            run_validation(db, sheet)


# ---------------------------------------------------------------------------
# 조회
# ---------------------------------------------------------------------------


@router.get("/api/spec-sheets/{sheet_id}/qa-threads", response_model=list[schemas.QAThreadOut])
def list_threads_for_sheet(sheet_id: int, db: Session = Depends(get_db)):
    sheet = db.get(SpecSheet, sheet_id)
    if sheet is None:
        raise HTTPException(status_code=404, detail="제원표를 찾을 수 없습니다.")
    return [_thread_out(t) for t in _threads_for_sheet(db, sheet_id)]


@router.get("/api/qa-threads", response_model=list[schemas.QAThreadOut])
def list_threads(
    major_process_id: int | None = None,
    discipline_id: int | None = None,
    status: QAThreadStatus | None = None,
    query_type: QueryType | None = None,
    assigned_owner_id: int | None = None,
    open_only: bool = False,
    db: Session = Depends(get_db),
):
    """item 7: open_only=true 로 기술팀 담당자 화면에서 미해결 항목만 보여줄 수 있다."""
    q = db.query(QAThread)
    if major_process_id:
        q = q.filter(QAThread.major_process_id == major_process_id)
    if discipline_id:
        q = q.filter(QAThread.discipline_id == discipline_id)
    if status:
        q = q.filter(QAThread.status == status)
    if query_type:
        q = q.filter(QAThread.query_type == query_type)
    if assigned_owner_id:
        q = q.filter(QAThread.assigned_owner_id == assigned_owner_id)
    if open_only:
        q = q.filter(~QAThread.status.in_(_TERMINAL))
    threads = q.order_by(QAThread.created_at.desc()).all()
    return [_thread_out(t) for t in threads]


@router.get("/api/qa-threads/{thread_id}", response_model=schemas.QAThreadOut)
def get_thread(thread_id: int, db: Session = Depends(get_db)):
    thread = db.get(QAThread, thread_id)
    if thread is None:
        raise HTTPException(status_code=404, detail="질의를 찾을 수 없습니다.")
    return _thread_out(thread)


# ---------------------------------------------------------------------------
# 자동 질의 일괄 생성 (items 1, 2)
# ---------------------------------------------------------------------------


@router.post("/api/qa-threads/generate-auto", response_model=list[schemas.QAThreadOut])
def generate_auto(db: Session = Depends(get_db)):
    """suggested_value 가 있는 미해결 검증 이슈를 (대공정/규칙/필드/제안값) 기준으로 묶어
    자동 제원 질의를 일괄 생성한다. 이미 배치된 항목은 다시 배치하지 않아 여러 번 호출해도
    안전하다 - 새 이슈가 쌓였을 때 다시 눌러주면 된다."""
    threads = generate_auto_queries(db)
    for thread in threads:
        _sync_sheets_for_thread(db, thread)
    db.commit()
    for t in threads:
        db.refresh(t)
    return [_thread_out(t) for t in threads]


# ---------------------------------------------------------------------------
# 수동 질의 등록 (설계사)
# ---------------------------------------------------------------------------


@router.post("/api/spec-sheets/{sheet_id}/qa-threads", response_model=schemas.QAThreadOut)
def create_thread(sheet_id: int, payload: schemas.QAThreadCreateIn, db: Session = Depends(get_db)):
    sheet = db.get(SpecSheet, sheet_id)
    if sheet is None:
        raise HTTPException(status_code=404, detail="제원표를 찾을 수 없습니다.")

    discipline = db.get(Discipline, payload.discipline_id)
    if discipline is None:
        raise HTTPException(status_code=400, detail="존재하지 않는 공종입니다.")

    field_ids = payload.spec_field_ids or ([payload.spec_field_id] if payload.spec_field_id else [])
    fields: list[SpecField] = []
    if field_ids:
        fields = (
            db.query(SpecField)
            .filter(SpecField.id.in_(field_ids), SpecField.spec_sheet_id == sheet_id)
            .all()
        )
        if len(fields) != len(set(field_ids)):
            raise HTTPException(status_code=400, detail="일부 항목을 이 제원표에서 찾을 수 없습니다.")

    assigned_owner_id = payload.assigned_owner_id
    if assigned_owner_id is None:
        candidates = [o for o in sheet.major_process.owners if o.role == OwnerRole.TECH_LEAD]
        if len(candidates) == 1:
            assigned_owner_id = candidates[0].id

    thread = QAThread(
        query_type=QueryType.MANUAL,
        major_process_id=sheet.major_process_id,
        discipline_id=payload.discipline_id,
        field_name=fields[0].field_name if fields else None,
        title=payload.title,
        status=QAThreadStatus.OPEN,
        assigned_owner_id=assigned_owner_id,
        created_by=payload.author_name,
    )
    db.add(thread)
    db.flush()

    for i, f in enumerate(fields):
        db.add(
            QAThreadTarget(
                qa_thread_id=thread.id,
                spec_field_id=f.id,
                validation_result_id=payload.validation_result_id if i == 0 else None,
            )
        )

    db.add(
        QAMessage(
            thread_id=thread.id, author_name=payload.author_name, role=QAMessageRole.QUESTION,
            content=payload.question,
        )
    )

    if payload.validation_result_id:
        vr = db.get(ValidationResult, payload.validation_result_id)
        if vr:
            vr.status = ValidationResultStatus.IN_QA

    _sync_sheet_status(db, sheet)
    db.commit()
    db.refresh(thread)
    return _thread_out(thread)


# ---------------------------------------------------------------------------
# AUTO: 승인/미승인 한 번으로 끝
# ---------------------------------------------------------------------------


@router.post("/api/qa-threads/{thread_id}/auto-decision", response_model=schemas.QAThreadOut)
def auto_decision(
    thread_id: int,
    payload: schemas.QAThreadDecisionIn,
    db: Session = Depends(get_db),
    current_owner: Owner | None = Depends(get_current_owner),
):
    thread = db.get(QAThread, thread_id)
    if thread is None:
        raise HTTPException(status_code=404, detail="질의를 찾을 수 없습니다.")
    if thread.query_type != QueryType.AUTO:
        raise HTTPException(status_code=400, detail="자동 질의가 아닙니다.")
    if thread.status != QAThreadStatus.OPEN:
        raise HTTPException(status_code=400, detail=f"현재 상태({thread.status.value})에서는 처리할 수 없습니다.")

    require_major_process_access(current_owner, thread.major_process_id)

    if payload.approve:
        _apply_to_be_value(thread, payload.decided_by, db)
        db.flush()
        _revalidate_sheets_for_thread(db, thread)
        thread.status = QAThreadStatus.RESOLVED
        note = payload.note or f"자동 질의 승인. TO-BE '{thread.to_be_value}' 반영됨 (대상 {len(thread.targets)}건)."
    else:
        for target in thread.targets:
            if target.validation_result:
                target.validation_result.status = ValidationResultStatus.OPEN
        thread.status = QAThreadStatus.REJECTED
        note = payload.note or "자동 질의 미승인."

    db.add(QAMessage(thread_id=thread.id, author_name=payload.decided_by, role=QAMessageRole.COMMENT, content=note))
    db.flush()  # _sync_sheets_for_thread가 새로 조회를 날리므로 status 변경을 먼저 반영해둔다
    _sync_sheets_for_thread(db, thread)
    db.commit()
    db.refresh(thread)
    return _thread_out(thread)


# ---------------------------------------------------------------------------
# MANUAL: 4단계 흐름
# ---------------------------------------------------------------------------


@router.post("/api/qa-threads/{thread_id}/messages", response_model=schemas.QAThreadOut)
def add_message(
    thread_id: int,
    payload: schemas.QAMessageIn,
    db: Session = Depends(get_db),
    current_owner: Owner | None = Depends(get_current_owner),
):
    thread = db.get(QAThread, thread_id)
    if thread is None:
        raise HTTPException(status_code=404, detail="질의를 찾을 수 없습니다.")

    if payload.role == QAMessageRole.ANSWER:
        require_major_process_access(current_owner, thread.major_process_id)
        if thread.query_type == QueryType.MANUAL and thread.status == QAThreadStatus.OPEN:
            thread.status = QAThreadStatus.TECH_ANSWERED

    db.add(
        QAMessage(thread_id=thread_id, author_name=payload.author_name, role=payload.role, content=payload.content)
    )
    db.commit()
    db.refresh(thread)
    return _thread_out(thread)


@router.post("/api/qa-threads/{thread_id}/answer-decision", response_model=schemas.QAThreadOut)
def answer_decision(
    thread_id: int,
    payload: schemas.QAThreadDecisionIn,
    db: Session = Depends(get_db),
    current_owner: Owner | None = Depends(get_current_owner),
):
    """설계사가 기술팀의 서술형 답변을 승인(-> 값 수정 가능)하거나 반려(-> 재답변 요청)한다."""
    thread = db.get(QAThread, thread_id)
    if thread is None:
        raise HTTPException(status_code=404, detail="질의를 찾을 수 없습니다.")
    if thread.query_type != QueryType.MANUAL or thread.status != QAThreadStatus.TECH_ANSWERED:
        raise HTTPException(status_code=400, detail=f"현재 상태({thread.status.value})에서는 처리할 수 없습니다.")

    require_discipline_access(current_owner, thread.discipline_id)

    thread.status = QAThreadStatus.ANSWER_APPROVED if payload.approve else QAThreadStatus.OPEN
    note = payload.note or ("답변 승인 - 기술팀이 값을 수정할 수 있습니다." if payload.approve else "답변 반려 - 다시 답변해 주세요.")
    db.add(QAMessage(thread_id=thread.id, author_name=payload.decided_by, role=QAMessageRole.COMMENT, content=note))
    db.commit()
    db.refresh(thread)
    return _thread_out(thread)


@router.post("/api/qa-threads/{thread_id}/propose-value", response_model=schemas.QAThreadOut)
def propose_value(
    thread_id: int,
    payload: schemas.QAThreadProposeValueIn,
    db: Session = Depends(get_db),
    current_owner: Owner | None = Depends(get_current_owner),
):
    """기술팀이 실제 제원 값을 제안한다. 검증 룰셋(성상명/자재명 허용값, 유량 상한 등)을
    통과해야만 등록되고, 등록되어도 아직 DB에는 반영되지 않는다(설계사 최종 승인 후 반영)."""
    thread = db.get(QAThread, thread_id)
    if thread is None:
        raise HTTPException(status_code=404, detail="질의를 찾을 수 없습니다.")
    if thread.query_type != QueryType.MANUAL or thread.status != QAThreadStatus.ANSWER_APPROVED:
        raise HTTPException(status_code=400, detail=f"현재 상태({thread.status.value})에서는 처리할 수 없습니다.")

    require_major_process_access(current_owner, thread.major_process_id)

    all_errors: list[str] = []
    all_warnings: list[str] = []
    for target in thread.targets:
        errors, warnings = validate_candidate_value(db, target.spec_field, payload.new_value)
        all_errors.extend(errors)
        all_warnings.extend(warnings)
    if all_errors:
        raise HTTPException(
            status_code=400,
            detail={"message": "제안한 값이 검증 규칙을 통과하지 못했습니다.", "errors": all_errors, "warnings": all_warnings},
        )

    thread.to_be_value = payload.new_value
    thread.status = QAThreadStatus.VALUE_PROPOSED
    note = f"값 제안: '{payload.new_value}'" + (f" (경고: {'; '.join(all_warnings)})" if all_warnings else "")
    db.add(QAMessage(thread_id=thread.id, author_name=payload.proposed_by, role=QAMessageRole.ANSWER, content=note))
    db.commit()
    db.refresh(thread)
    return _thread_out(thread)


@router.post("/api/qa-threads/{thread_id}/final-decision", response_model=schemas.QAThreadOut)
def final_decision(
    thread_id: int,
    payload: schemas.QAThreadDecisionIn,
    db: Session = Depends(get_db),
    current_owner: Owner | None = Depends(get_current_owner),
):
    """설계사가 기술팀이 고친 값을 최종 승인하면 그때 DB에 반영된다."""
    thread = db.get(QAThread, thread_id)
    if thread is None:
        raise HTTPException(status_code=404, detail="질의를 찾을 수 없습니다.")
    if thread.query_type != QueryType.MANUAL or thread.status != QAThreadStatus.VALUE_PROPOSED:
        raise HTTPException(status_code=400, detail=f"현재 상태({thread.status.value})에서는 처리할 수 없습니다.")

    require_discipline_access(current_owner, thread.discipline_id)

    if payload.approve:
        _apply_to_be_value(thread, payload.decided_by, db)
        db.flush()
        _revalidate_sheets_for_thread(db, thread)
        thread.status = QAThreadStatus.RESOLVED
        note = payload.note or f"최종 승인. TO-BE '{thread.to_be_value}' 로 제원표가 수정되었습니다."
    else:
        thread.status = QAThreadStatus.ANSWER_APPROVED
        note = payload.note or "최종 반려 - 값을 다시 제안해 주세요."

    db.add(QAMessage(thread_id=thread.id, author_name=payload.decided_by, role=QAMessageRole.COMMENT, content=note))
    db.flush()
    _sync_sheets_for_thread(db, thread)
    db.commit()
    db.refresh(thread)
    return _thread_out(thread)
