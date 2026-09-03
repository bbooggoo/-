from io import BytesIO

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
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
from ..services.aggregation import compute_aggregation
from ..services.excel_export import export_spec_sheet
from ..services.excel_import import (
    GroupedImportConfig,
    ImportConfig,
    ParsedCell,
    parse_excel,
    parse_grouped_excel,
)
from ..services.validation_engine import run_validation

router = APIRouter(prefix="/api/spec-sheets", tags=["spec-sheets"])


def _open_issue_count(sheet: SpecSheet) -> int:
    return sum(
        1
        for r in sheet.validation_results
        if r.status not in (ValidationResultStatus.RESOLVED, ValidationResultStatus.DISMISSED)
    )


def _to_list_out(sheet: SpecSheet) -> schemas.SpecSheetListOut:
    item = schemas.SpecSheetListOut.model_validate(sheet)
    item.open_issue_count = _open_issue_count(sheet)
    return item


def _to_detail_out(sheet: SpecSheet) -> schemas.SpecSheetDetailOut:
    item = schemas.SpecSheetDetailOut.model_validate(sheet)
    item.open_issue_count = _open_issue_count(sheet)
    return item


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
    return [_to_list_out(s) for s in sheets]


@router.get("/{sheet_id}", response_model=schemas.SpecSheetDetailOut)
def get_spec_sheet(sheet_id: int, db: Session = Depends(get_db)):
    sheet = db.get(SpecSheet, sheet_id)
    if sheet is None:
        raise HTTPException(status_code=404, detail="제원표를 찾을 수 없습니다.")
    return _to_detail_out(sheet)


def _next_version(db: Session, construction_code: str, major_process_id: int) -> int:
    latest_version = (
        db.query(func.max(SpecSheet.version))
        .filter(
            SpecSheet.construction_code == construction_code,
            SpecSheet.major_process_id == major_process_id,
        )
        .scalar()
    )
    return (latest_version or 0) + 1


def _persist_sheet(
    db: Session,
    *,
    mp: MajorProcess,
    construction_code: str,
    equipment_module: str | None,
    title: str | None,
    source_filename: str,
    sheet_name: str,
    uploaded_by: str | None,
    import_config: dict,
    cells: list[ParsedCell],
) -> SpecSheet:
    version = _next_version(db, construction_code, mp.id)
    sheet = SpecSheet(
        major_process_id=mp.id,
        construction_code=construction_code,
        equipment_module=equipment_module,
        title=title or f"{mp.name} {construction_code}" + (f" ({equipment_module})" if equipment_module else ""),
        source_filename=source_filename,
        sheet_name=sheet_name,
        version=version,
        status=SpecSheetStatus.UPLOADED,
        uploaded_by=uploaded_by,
        import_config=import_config,
    )
    db.add(sheet)
    db.flush()

    for c in cells:
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
    db.flush()
    return sheet


def _resolve_group_major_process(
    db: Session,
    default_mp: MajorProcess,
    major_process_raw: str | None,
    mp_by_key: dict[str, MajorProcess],
    warnings: list[str],
    construction_code: str,
) -> MajorProcess:
    """건설코드 그룹의 실제 대공정을 판별한다.

    시트에 "대공정" 값이 없으면 업로드 시 선택한 대공정(default_mp)을 그대로 쓴다
    (대공정별로 파일이 따로 오는 일반적인 경우). 값이 있으면 대소문자/공백을 무시하고
    이름 또는 코드로 매칭해서, 한 파일에 여러 대공정이 섞여 들어온 경우에도 건설코드
    그룹마다 올바른 대공정으로 배정한다. 매칭되지 않으면 경고를 남기고 default_mp로
    처리한다.
    """
    if not major_process_raw:
        return default_mp
    resolved = mp_by_key.get(major_process_raw.strip().upper())
    if resolved is not None:
        return resolved
    warnings.append(
        f"'{construction_code}' 그룹의 대공정 표기 '{major_process_raw}'를 인식하지 못해 "
        f"업로드 시 선택한 대공정({default_mp.name})으로 처리했습니다."
    )
    return default_mp


@router.post("/upload", response_model=schemas.SpecSheetUploadResultOut)
async def upload_spec_sheet(
    file: UploadFile = File(...),
    major_process_id: int = Form(...),
    uploaded_by: str | None = Form(None),
    sheet_name: str | None = Form(None),
    # 파싱 모드: "grouped"(기본, 2단 헤더 + 건설코드 자동 그룹핑) | "simple"(라벨/값/단위 열)
    layout: str = Form("grouped"),
    # grouped 모드 설정. 헤더 행 번호를 비워두면(None) 자동으로 인식한다.
    category_row: int | None = Form(None),
    label_row: int | None = Form(None),
    data_start_row: int | None = Form(None),
    construction_code_override: str | None = Form(None),
    # simple 모드 설정 (레거시)
    construction_code: str | None = Form(None),
    equipment_module: str | None = Form(None),
    title: str | None = Form(None),
    header_row: int = Form(1),
    label_col: int = Form(1),
    value_col: int = Form(2),
    unit_col: int | None = Form(3),
    db: Session = Depends(get_db),
):
    mp = db.get(MajorProcess, major_process_id)
    if mp is None:
        raise HTTPException(status_code=400, detail="존재하지 않는 대공정입니다.")

    content = await file.read()
    created: list[SpecSheet] = []
    warnings: list[str] = []

    if layout == "simple":
        if not construction_code:
            raise HTTPException(status_code=400, detail="단순 모드에서는 건설코드를 직접 입력해야 합니다.")
        code = construction_code.strip().upper()
        try:
            validate_construction_code(code)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

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

        sheet = _persist_sheet(
            db,
            mp=mp,
            construction_code=code,
            equipment_module=equipment_module,
            title=title,
            source_filename=file.filename or "unknown.xlsx",
            sheet_name=parsed.sheet_name,
            uploaded_by=uploaded_by,
            import_config={
                "layout": "simple",
                "header_row": header_row,
                "label_col": label_col,
                "value_col": value_col,
                "unit_col": unit_col,
            },
            cells=parsed.cells,
        )
        created.append(sheet)

    else:
        config = GroupedImportConfig(
            sheet_name=sheet_name or None,
            category_row=category_row,
            label_row=label_row,
            data_start_row=data_start_row,
            construction_code_override=(construction_code_override or "").strip().upper() or None,
        )
        try:
            parsed = parse_grouped_excel(content, config)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"엑셀 파싱 실패: {e}")

        warnings.extend(parsed.warnings)
        if not parsed.groups:
            raise HTTPException(
                status_code=400,
                detail="건설코드를 하나도 인식하지 못했습니다. "
                "'건설코드 대체값'을 입력하거나 시트의 건설코드 열을 확인해 주세요.",
            )
        # 시트 안에 대공정이 섞여 있는 경우를 위한 이름/코드 -> MajorProcess 조회 테이블
        all_mps = db.query(MajorProcess).all()
        mp_by_key = {}
        for m in all_mps:
            mp_by_key[m.name.strip().upper()] = m
            mp_by_key[m.code.strip().upper()] = m

        for group in parsed.groups:
            group_mp = _resolve_group_major_process(
                db, mp, group.major_process_raw, mp_by_key, warnings, group.construction_code
            )
            sheet = _persist_sheet(
                db,
                mp=group_mp,
                construction_code=group.construction_code,
                equipment_module=group.equipment_module_summary,
                title=None,
                source_filename=file.filename or "unknown.xlsx",
                sheet_name=parsed.sheet_name,
                uploaded_by=uploaded_by,
                import_config={
                    "layout": "grouped",
                    "category_row": category_row,
                    "label_row": label_row,
                    "data_start_row": data_start_row,
                    "header_rows_auto_detected": parsed.header_rows_auto_detected,
                    "row_range": list(group.row_range),
                },
                cells=group.cells,
            )
            created.append(sheet)

    db.commit()
    for sheet in created:
        db.refresh(sheet)

    return schemas.SpecSheetUploadResultOut(
        created=[_to_detail_out(s) for s in created], warnings=warnings
    )


@router.post("/{sheet_id}/validate", response_model=schemas.SpecSheetDetailOut)
def validate_spec_sheet(sheet_id: int, db: Session = Depends(get_db)):
    sheet = db.get(SpecSheet, sheet_id)
    if sheet is None:
        raise HTTPException(status_code=404, detail="제원표를 찾을 수 없습니다.")

    run_validation(db, sheet)
    sheet.status = SpecSheetStatus.VALIDATED
    db.commit()
    db.refresh(sheet)
    return _to_detail_out(sheet)


@router.get("/{sheet_id}/aggregation", response_model=list[schemas.CategoryAggregationOut])
def get_spec_sheet_aggregation(sheet_id: int, db: Session = Depends(get_db)):
    sheet = db.get(SpecSheet, sheet_id)
    if sheet is None:
        raise HTTPException(status_code=404, detail="제원표를 찾을 수 없습니다.")
    return [
        schemas.CategoryAggregationOut(category=a.category, unit=a.unit, group_by=a.group_by, totals=a.totals)
        for a in compute_aggregation(sheet)
    ]


@router.get("/{sheet_id}/export")
def export_spec_sheet_endpoint(sheet_id: int, db: Session = Depends(get_db)):
    sheet = db.get(SpecSheet, sheet_id)
    if sheet is None:
        raise HTTPException(status_code=404, detail="제원표를 찾을 수 없습니다.")
    data = export_spec_sheet(sheet)
    filename = f"{sheet.construction_code}_v{sheet.version}.xlsx"
    return StreamingResponse(
        BytesIO(data),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
