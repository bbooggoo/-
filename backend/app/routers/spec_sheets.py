from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from io import BytesIO
from sqlalchemy import func
from sqlalchemy.orm import Session, selectinload

from .. import schemas
from ..database import get_db
from ..models import (
    MajorProcess,
    SpecField,
    SpecSheet,
    SpecSheetStatus,
    ValidationResultStatus,
)
from ..schemas import validate_construction_code
from ..services.excel_export import export_spec_sheet
from ..services.excel_import import ImportConfig, parse_excel
from ..services.validation_engine import run_validation

router = APIRouter(prefix="/api/spec-sheets", tags=["spec-sheets"])


def _with_open_issue_count(db: Session, sheets: list[SpecSheet]):
    out = []
    for s in sheets:
        open_count = sum(1 for r in s.validation_results if r.status != ValidationResultStatus.RESOLVED
                          and r.status != ValidationResultStatus.DISMISSED)
        item = schemas.SpecSheetListOut.model_validate(s)
        item.open_issue_count = open_count
        out.append(item)
    return out


@router.get("", response_model=list[schemas.SpecSheetListOut])
def list_spec_sheets(
    major_process_id: int | None = None,
    construction_code: str | None = None,
    status: SpecSheetStatus | None = None,
    db: Session = Depends(get_db),
):
    q = db.query(SpecSheet).options(
        selectinload(SpecSheet.major_process), selectinload(SpecSheet.validation_results)
    )
    if major_process_id:
        q = q.filter(SpecSheet.major_process_id == major_process_id)
    if construction_code:
        q = q.filter(SpecSheet.construction_code == construction_code)
    if status:
        q = q.filter(SpecSheet.status == status)
    sheets = q.order_by(SpecSheet.uploaded_at.desc()).all()
    return _with_open_issue_count(db, sheets)


@router.get("/{sheet_id}", response_model=schemas.SpecSheetDetailOut)
def get_spec_sheet(sheet_id: int, db: Session = Depends(get_db)):
    sheet = db.get(SpecSheet, sheet_id)
    if sheet is None:
        raise HTTPException(status_code=404, detail="제원표를 찾을 수 없습니다.")
    open_count = sum(
        1
        for r in sheet.validation_results
        if r.status not in (ValidationResultStatus.RESOLVED, ValidationResultStatus.DISMISSED)
    )
    out = schemas.SpecSheetDetailOut.model_validate(sheet)
    out.open_issue_count = open_count
    return out


@router.post("/upload", response_model=schemas.SpecSheetDetailOut)
async def upload_spec_sheet(
    file: UploadFile = File(...),
    major_process_id: int = Form(...),
    construction_code: str = Form(...),
    equipment_module: str = Form(...),
    title: str | None = Form(None),
    uploaded_by: str | None = Form(None),
    sheet_name: str | None = Form(None),
    header_row: int = Form(1),
    label_col: int = Form(1),
    value_col: int = Form(2),
    unit_col: int | None = Form(3),
    db: Session = Depends(get_db),
):
    construction_code = construction_code.strip().upper()
    try:
        validate_construction_code(construction_code)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    mp = db.get(MajorProcess, major_process_id)
    if mp is None:
        raise HTTPException(status_code=400, detail="존재하지 않는 대공정입니다.")

    content = await file.read()
    config = ImportConfig(
        sheet_name=sheet_name or None,
        header_row=header_row,
        label_col=label_col,
        value_col=value_col,
        unit_col=unit_col,
    )
    try:
        parsed = parse_excel(content, config)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"엑셀 파싱 실패: {e}")

    # 동일 (건설코드, 설비모듈) 조합의 기존 버전이 있으면 다음 버전으로 저장
    latest_version = (
        db.query(func.max(SpecSheet.version))
        .filter(
            SpecSheet.construction_code == construction_code,
            SpecSheet.equipment_module == equipment_module,
        )
        .scalar()
    )
    version = (latest_version or 0) + 1

    sheet = SpecSheet(
        major_process_id=major_process_id,
        construction_code=construction_code,
        equipment_module=equipment_module,
        title=title or f"{mp.name} {construction_code} {equipment_module}",
        source_filename=file.filename or "unknown.xlsx",
        sheet_name=parsed.sheet_name,
        version=version,
        status=SpecSheetStatus.UPLOADED,
        uploaded_by=uploaded_by,
        import_config={
            "header_row": header_row,
            "label_col": label_col,
            "value_col": value_col,
            "unit_col": unit_col,
        },
    )
    db.add(sheet)
    db.flush()

    for c in parsed.cells:
        db.add(
            SpecField(
                spec_sheet_id=sheet.id,
                row_index=c.row,
                col_index=c.col,
                field_name=c.field_name,
                value=c.value,
                unit=c.unit,
            )
        )
    db.commit()
    db.refresh(sheet)

    out = schemas.SpecSheetDetailOut.model_validate(sheet)
    out.open_issue_count = 0
    return out


@router.post("/{sheet_id}/validate", response_model=schemas.SpecSheetDetailOut)
def validate_spec_sheet(sheet_id: int, db: Session = Depends(get_db)):
    sheet = db.get(SpecSheet, sheet_id)
    if sheet is None:
        raise HTTPException(status_code=404, detail="제원표를 찾을 수 없습니다.")

    run_validation(db, sheet)
    sheet.status = SpecSheetStatus.VALIDATED
    db.commit()
    db.refresh(sheet)

    open_count = sum(
        1
        for r in sheet.validation_results
        if r.status not in (ValidationResultStatus.RESOLVED, ValidationResultStatus.DISMISSED)
    )
    out = schemas.SpecSheetDetailOut.model_validate(sheet)
    out.open_issue_count = open_count
    return out


@router.get("/{sheet_id}/export")
def export_spec_sheet_endpoint(sheet_id: int, db: Session = Depends(get_db)):
    sheet = db.get(SpecSheet, sheet_id)
    if sheet is None:
        raise HTTPException(status_code=404, detail="제원표를 찾을 수 없습니다.")
    data = export_spec_sheet(sheet)
    filename = f"{sheet.construction_code}_{sheet.equipment_module}_v{sheet.version}.xlsx"
    return StreamingResponse(
        BytesIO(data),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
