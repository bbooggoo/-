"""
ORM 모델.

용어 매핑 (한글 -> 영문 테이블/필드):
  대공정   -> MajorProcess
  건설코드 -> SpecSheet.construction_code
  설비모듈 -> SpecSheet.equipment_module
  제원표   -> SpecSheet
  제원 항목(셀) -> SpecField
  담당자   -> Owner
  질의응답 -> QAThread / QAMessage
  자동수정용 축적 이력 -> SpecCorrection
"""
import datetime
import enum

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
    UniqueConstraint,
    Column,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def now() -> datetime.datetime:
    return datetime.datetime.utcnow()


# ---------------------------------------------------------------------------
# 대공정 (Major Process)
# ---------------------------------------------------------------------------

# 시드 데이터. 코드값은 시스템 전역에서 참조되는 안정적인 키이므로 seed.py 와 함께 관리.
MAJOR_PROCESS_SEED = [
    ("PHOTO", "PHOTO"),
    ("CVD", "CVD"),
    ("ETCH", "ETCH"),
    ("METAL", "METAL"),
    ("CMP", "CMP"),
    ("IMP", "IMP"),
    ("DIFF", "DIFF"),
    ("PMTC", "PMTC"),
    ("EDS", "EDS"),
    ("ANALYSIS", "ANALYSIS"),
    ("MFG_ENV", "제조환경설비"),
    ("LOGISTICS", "물류자동화"),
    ("CLN", "CLN"),
]


class MajorProcess(Base):
    __tablename__ = "major_processes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(64))

    owners: Mapped[list["Owner"]] = relationship(
        secondary="owner_major_processes", back_populates="major_processes"
    )
    spec_sheets: Mapped[list["SpecSheet"]] = relationship(back_populates="major_process")


# ---------------------------------------------------------------------------
# 담당자 (Owner) - 대공정별 담당자가 다르므로 M:N
# ---------------------------------------------------------------------------

owner_major_processes = Table(
    "owner_major_processes",
    Base.metadata,
    Column("owner_id", ForeignKey("owners.id"), primary_key=True),
    Column("major_process_id", ForeignKey("major_processes.id"), primary_key=True),
)


class Owner(Base):
    __tablename__ = "owners"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(64))
    email: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=now)

    major_processes: Mapped[list["MajorProcess"]] = relationship(
        secondary=owner_major_processes, back_populates="owners"
    )


# ---------------------------------------------------------------------------
# 제원표 (SpecSheet) - 엑셀 1건 업로드 = 1건 (버전 관리 가능)
# ---------------------------------------------------------------------------


class SpecSheetStatus(str, enum.Enum):
    UPLOADED = "UPLOADED"          # 업로드만 된 상태
    VALIDATED = "VALIDATED"        # 규칙 검증 실행됨 (이상 없음 또는 이상 존재)
    IN_QA = "IN_QA"                 # 질의응답 진행 중 (열린 스레드 있음)
    RESOLVED = "RESOLVED"           # 모든 이슈 해결 완료


class SpecSheet(Base):
    __tablename__ = "spec_sheets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    major_process_id: Mapped[int] = mapped_column(ForeignKey("major_processes.id"))
    construction_code: Mapped[str] = mapped_column(String(16), index=True)  # 예: PDXXXXX
    equipment_module: Mapped[str] = mapped_column(String(64), index=True)   # 예: GAS/SCRUBBER/MAIN

    title: Mapped[str] = mapped_column(String(255))
    source_filename: Mapped[str] = mapped_column(String(255))
    sheet_name: Mapped[str] = mapped_column(String(128))
    version: Mapped[int] = mapped_column(Integer, default=1)

    status: Mapped[SpecSheetStatus] = mapped_column(
        Enum(SpecSheetStatus), default=SpecSheetStatus.UPLOADED
    )

    uploaded_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    uploaded_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=now)

    # 업로드시 사용한 라벨/값/단위 열 매핑 (재현/재파싱 참고용)
    import_config: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    major_process: Mapped["MajorProcess"] = relationship(back_populates="spec_sheets")
    fields: Mapped[list["SpecField"]] = relationship(
        back_populates="spec_sheet", cascade="all, delete-orphan", order_by="SpecField.row_index, SpecField.col_index"
    )
    validation_results: Mapped[list["ValidationResult"]] = relationship(
        back_populates="spec_sheet", cascade="all, delete-orphan"
    )
    qa_threads: Mapped[list["QAThread"]] = relationship(
        back_populates="spec_sheet", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint(
            "construction_code", "equipment_module", "version", name="uq_spec_identity_version"
        ),
    )


class SpecField(Base):
    """
    엑셀 셀 하나에 대응. CAD형 레이아웃을 보존하기 위해 셀 좌표(row/col)를 그대로 저장.

    라벨열/값열 매핑에 해당하는 셀만 field_name/unit 이 채워져서 검증 규칙이 참조 가능한
    "속성"이 되고, 그 외 셀은 field_name=None 인 채로 원본 레이아웃 보존/재출력 용도로만 쓰인다.
    """

    __tablename__ = "spec_fields"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    spec_sheet_id: Mapped[int] = mapped_column(ForeignKey("spec_sheets.id"))

    row_index: Mapped[int] = mapped_column(Integer)
    col_index: Mapped[int] = mapped_column(Integer)

    field_name: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    value: Mapped[str | None] = mapped_column(Text, nullable=True)
    unit: Mapped[str | None] = mapped_column(String(32), nullable=True)

    spec_sheet: Mapped["SpecSheet"] = relationship(back_populates="fields")
    validation_results: Mapped[list["ValidationResult"]] = relationship(back_populates="spec_field")


# ---------------------------------------------------------------------------
# 검증 규칙 (플러그인 엔진) - services/rules 참고
# ---------------------------------------------------------------------------


class RuleSeverity(str, enum.Enum):
    ERROR = "ERROR"
    WARN = "WARN"


class ValidationRule(Base):
    __tablename__ = "validation_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(128))

    # services/rules 레지스트리의 키 (예: "max_value", "standardized_enum")
    rule_type: Mapped[str] = mapped_column(String(64))

    # 규칙 적용 범위 (모두 NULL이면 전체 적용)
    major_process_id: Mapped[int | None] = mapped_column(ForeignKey("major_processes.id"), nullable=True)
    equipment_module: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # SpecField.field_name 에 대해 매칭할 정규식 (예: "유량|FLOW")
    field_name_pattern: Mapped[str] = mapped_column(String(255))

    # 규칙별 파라미터 (예: {"max": 120, "unit": "LPM"})
    params: Mapped[dict] = mapped_column(JSON, default=dict)

    severity: Mapped[RuleSeverity] = mapped_column(Enum(RuleSeverity), default=RuleSeverity.ERROR)
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=now)

    major_process: Mapped["MajorProcess | None"] = relationship()


class ValidationResultStatus(str, enum.Enum):
    OPEN = "OPEN"
    IN_QA = "IN_QA"
    RESOLVED = "RESOLVED"
    DISMISSED = "DISMISSED"


class ValidationResult(Base):
    __tablename__ = "validation_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    spec_sheet_id: Mapped[int] = mapped_column(ForeignKey("spec_sheets.id"))
    spec_field_id: Mapped[int | None] = mapped_column(ForeignKey("spec_fields.id"), nullable=True)
    rule_id: Mapped[int | None] = mapped_column(ForeignKey("validation_rules.id"), nullable=True)

    severity: Mapped[RuleSeverity] = mapped_column(Enum(RuleSeverity))
    message: Mapped[str] = mapped_column(Text)
    status: Mapped[ValidationResultStatus] = mapped_column(
        Enum(ValidationResultStatus), default=ValidationResultStatus.OPEN
    )

    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=now)

    spec_sheet: Mapped["SpecSheet"] = relationship(back_populates="validation_results")
    spec_field: Mapped["SpecField | None"] = relationship(back_populates="validation_results")
    rule: Mapped["ValidationRule | None"] = relationship()


# ---------------------------------------------------------------------------
# 질의응답 (대공정별 담당자가 응답)
# ---------------------------------------------------------------------------


class QAThreadStatus(str, enum.Enum):
    OPEN = "OPEN"
    ANSWERED = "ANSWERED"
    RESOLVED = "RESOLVED"


class QAThread(Base):
    __tablename__ = "qa_threads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    spec_sheet_id: Mapped[int] = mapped_column(ForeignKey("spec_sheets.id"))
    spec_field_id: Mapped[int | None] = mapped_column(ForeignKey("spec_fields.id"), nullable=True)
    validation_result_id: Mapped[int | None] = mapped_column(
        ForeignKey("validation_results.id"), nullable=True
    )
    major_process_id: Mapped[int] = mapped_column(ForeignKey("major_processes.id"))

    title: Mapped[str] = mapped_column(String(255))
    status: Mapped[QAThreadStatus] = mapped_column(Enum(QAThreadStatus), default=QAThreadStatus.OPEN)

    assigned_owner_id: Mapped[int | None] = mapped_column(ForeignKey("owners.id"), nullable=True)
    created_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=now)
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=now, onupdate=now)

    spec_sheet: Mapped["SpecSheet"] = relationship(back_populates="qa_threads")
    spec_field: Mapped["SpecField | None"] = relationship()
    validation_result: Mapped["ValidationResult | None"] = relationship()
    major_process: Mapped["MajorProcess"] = relationship()
    assigned_owner: Mapped["Owner | None"] = relationship()
    messages: Mapped[list["QAMessage"]] = relationship(
        back_populates="thread", cascade="all, delete-orphan", order_by="QAMessage.created_at"
    )


class QAMessageRole(str, enum.Enum):
    QUESTION = "QUESTION"
    ANSWER = "ANSWER"
    COMMENT = "COMMENT"


class QAMessage(Base):
    __tablename__ = "qa_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    thread_id: Mapped[int] = mapped_column(ForeignKey("qa_threads.id"))

    author_name: Mapped[str] = mapped_column(String(64))
    role: Mapped[QAMessageRole] = mapped_column(Enum(QAMessageRole))
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=now)

    thread: Mapped["QAThread"] = relationship(back_populates="messages")


# ---------------------------------------------------------------------------
# 자동 수정을 위한 이력 축적 (2단계 로드맵)
# ---------------------------------------------------------------------------


class CorrectionSource(str, enum.Enum):
    MANUAL = "MANUAL"                 # 사람이 Q&A 통해 직접 수정
    AUTO_SUGGESTED = "AUTO_SUGGESTED"  # (향후) 자동 제안 후 적용


class SpecCorrection(Base):
    """
    Q&A 를 통해 실제로 반영된 제원 수정 이력.
    2단계(자동 수정)에서 이 테이블을 학습/추천 데이터로 사용할 예정.
    """

    __tablename__ = "spec_corrections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    qa_thread_id: Mapped[int] = mapped_column(ForeignKey("qa_threads.id"))
    spec_field_id: Mapped[int | None] = mapped_column(ForeignKey("spec_fields.id"), nullable=True)

    field_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    old_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_value: Mapped[str | None] = mapped_column(Text, nullable=True)

    source: Mapped[CorrectionSource] = mapped_column(Enum(CorrectionSource), default=CorrectionSource.MANUAL)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)

    applied_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    applied_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=now)

    qa_thread: Mapped["QAThread"] = relationship()
    spec_field: Mapped["SpecField | None"] = relationship()
