"""담당자별 제원 SUMMARY 장표 (item 4) - 대공정으로 필터링해 대분류별 총량/GCS 종수/
미해결 이슈·질의 건수를 한 번에 보여준다. 프론트엔드는 현재 선택된 사용자의 대공정에
맞춰 major_process_id 를 자동으로 넣어 호출한다 (item 5 수정과 짝을 이룬다)."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import schemas
from ..database import get_db
from ..models import QAThread, QAThreadStatus, QueryType, SpecSheet
from ..services.aggregation import compute_summary

router = APIRouter(prefix="/api/summary", tags=["summary"])

_OPEN_QUERY_STATUSES = [
    QAThreadStatus.OPEN,
    QAThreadStatus.TECH_ANSWERED,
    QAThreadStatus.ANSWER_APPROVED,
    QAThreadStatus.VALUE_PROPOSED,
]


@router.get("", response_model=schemas.SummaryOut)
def get_summary(major_process_id: int | None = None, db: Session = Depends(get_db)):
    sheets_q = db.query(SpecSheet)
    if major_process_id:
        sheets_q = sheets_q.filter(SpecSheet.major_process_id == major_process_id)
    sheets = sheets_q.all()

    result = compute_summary(sheets)

    threads_q = db.query(QAThread).filter(QAThread.status.in_(_OPEN_QUERY_STATUSES))
    if major_process_id:
        threads_q = threads_q.filter(QAThread.major_process_id == major_process_id)
    threads = threads_q.all()
    auto_count = sum(1 for t in threads if t.query_type == QueryType.AUTO)
    manual_count = sum(1 for t in threads if t.query_type == QueryType.MANUAL)

    return schemas.SummaryOut(
        sheet_count=result.sheet_count,
        open_issue_count=result.open_issue_count,
        open_auto_query_count=auto_count,
        open_manual_query_count=manual_count,
        categories=[
            schemas.CategoryAggregationOut(
                category=c.category, unit=c.unit, group_by=c.group_by,
                totals=c.totals, distinct_count=c.distinct_count,
            )
            for c in result.categories
        ],
        gcs_material_count=result.gcs_material_count,
        gcs_materials=result.gcs_materials,
    )
