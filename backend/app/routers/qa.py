from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import schemas
from ..database import get_db
from ..deps import get_current_owner, require_major_process_access
from ..models import (
    Owner,
    QAMessage,
    QAMessageRole,
    QAThread,
    QAThreadStatus,
    SpecCorrection,
    SpecField,
    SpecSheet,
    SpecSheetStatus,
    ValidationResult,
    ValidationResultStatus,
)

router = APIRouter(tags=["qa"])


def _sync_sheet_status(db: Session, sheet: SpecSheet) -> None:
    """제원표 상태를 하위 스레드/검증결과 상태에 맞춰 재계산."""
    open_threads = any(t.status != QAThreadStatus.RESOLVED for t in sheet.qa_threads)
    open_issues = any(
        r.status not in (ValidationResultStatus.RESOLVED, ValidationResultStatus.DISMISSED)
        for r in sheet.validation_results
    )
    if sheet.qa_threads and open_threads:
        sheet.status = SpecSheetStatus.IN_QA
    elif not open_issues and sheet.validation_results:
        sheet.status = SpecSheetStatus.RESOLVED
    elif sheet.status == SpecSheetStatus.UPLOADED:
        pass  # 검증 전이면 그대로 둠


@router.get("/api/spec-sheets/{sheet_id}/qa-threads", response_model=list[schemas.QAThreadOut])
def list_threads_for_sheet(sheet_id: int, db: Session = Depends(get_db)):
    sheet = db.get(SpecSheet, sheet_id)
    if sheet is None:
        raise HTTPException(status_code=404, detail="제원표를 찾을 수 없습니다.")
    return sheet.qa_threads


@router.get("/api/qa-threads", response_model=list[schemas.QAThreadOut])
def list_threads(
    major_process_id: int | None = None,
    status: QAThreadStatus | None = None,
    assigned_owner_id: int | None = None,
    db: Session = Depends(get_db),
):
    q = db.query(QAThread)
    if major_process_id:
        q = q.filter(QAThread.major_process_id == major_process_id)
    if status:
        q = q.filter(QAThread.status == status)
    if assigned_owner_id:
        q = q.filter(QAThread.assigned_owner_id == assigned_owner_id)
    return q.order_by(QAThread.created_at.desc()).all()


@router.post("/api/spec-sheets/{sheet_id}/qa-threads", response_model=schemas.QAThreadOut)
def create_thread(
    sheet_id: int,
    payload: schemas.QAThreadCreateIn,
    db: Session = Depends(get_db),
):
    sheet = db.get(SpecSheet, sheet_id)
    if sheet is None:
        raise HTTPException(status_code=404, detail="제원표를 찾을 수 없습니다.")

    assigned_owner_id = payload.assigned_owner_id
    if assigned_owner_id is None:
        # 대공정에 담당자가 1명뿐이면 자동 배정
        candidates = [o for o in sheet.major_process.owners]
        if len(candidates) == 1:
            assigned_owner_id = candidates[0].id

    thread = QAThread(
        spec_sheet_id=sheet_id,
        spec_field_id=payload.spec_field_id,
        validation_result_id=payload.validation_result_id,
        major_process_id=sheet.major_process_id,
        title=payload.title,
        status=QAThreadStatus.OPEN,
        assigned_owner_id=assigned_owner_id,
        created_by=payload.author_name,
    )
    db.add(thread)
    db.flush()

    db.add(
        QAMessage(
            thread_id=thread.id,
            author_name=payload.author_name,
            role=QAMessageRole.QUESTION,
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
    return thread


@router.get("/api/qa-threads/{thread_id}", response_model=schemas.QAThreadOut)
def get_thread(thread_id: int, db: Session = Depends(get_db)):
    thread = db.get(QAThread, thread_id)
    if thread is None:
        raise HTTPException(status_code=404, detail="질의응답 스레드를 찾을 수 없습니다.")
    return thread


@router.post("/api/qa-threads/{thread_id}/messages", response_model=schemas.QAThreadOut)
def add_message(
    thread_id: int,
    payload: schemas.QAMessageIn,
    db: Session = Depends(get_db),
    current_owner: Owner | None = Depends(get_current_owner),
):
    thread = db.get(QAThread, thread_id)
    if thread is None:
        raise HTTPException(status_code=404, detail="질의응답 스레드를 찾을 수 없습니다.")

    if payload.role == QAMessageRole.ANSWER:
        # 답변은 해당 대공정 담당자만 (사용자를 선택한 경우에 한해 강제)
        require_major_process_access(current_owner, thread.major_process_id)
        thread.status = QAThreadStatus.ANSWERED

    db.add(
        QAMessage(
            thread_id=thread_id,
            author_name=payload.author_name,
            role=payload.role,
            content=payload.content,
        )
    )
    db.commit()
    db.refresh(thread)
    return thread


@router.post("/api/qa-threads/{thread_id}/resolve", response_model=schemas.QAThreadOut)
def resolve_thread(
    thread_id: int,
    payload: schemas.QAThreadResolveIn,
    db: Session = Depends(get_db),
    current_owner: Owner | None = Depends(get_current_owner),
):
    thread = db.get(QAThread, thread_id)
    if thread is None:
        raise HTTPException(status_code=404, detail="질의응답 스레드를 찾을 수 없습니다.")

    require_major_process_access(current_owner, thread.major_process_id)

    old_value = None
    if payload.new_value is not None and thread.spec_field_id:
        field = db.get(SpecField, thread.spec_field_id)
        if field:
            old_value = field.value
            field.value = payload.new_value
            db.add(
                SpecCorrection(
                    qa_thread_id=thread.id,
                    spec_field_id=field.id,
                    field_name=field.field_name,
                    old_value=old_value,
                    new_value=payload.new_value,
                    applied_by=payload.resolver_name,
                )
            )

    if thread.validation_result_id:
        vr = db.get(ValidationResult, thread.validation_result_id)
        if vr:
            vr.status = ValidationResultStatus.RESOLVED

    thread.status = QAThreadStatus.RESOLVED
    db.add(
        QAMessage(
            thread_id=thread.id,
            author_name=payload.resolver_name,
            role=QAMessageRole.COMMENT,
            content=payload.note or (
                f"해결됨. 값 변경: '{old_value}' -> '{payload.new_value}'" if payload.new_value else "해결됨."
            ),
        )
    )

    _sync_sheet_status(db, thread.spec_sheet)
    db.commit()
    db.refresh(thread)
    return thread
