"""
ORM 모델.

용어 매핑 (한글 -> 영문 테이블/필드):
  대공정   -> MajorProcess
  건설코드 -> SpecSheet.construction_code (엑셀 데이터에서 자동 추출, 건설코드 단위로 SpecSheet 1건)
  설비모듈 -> 대분류별로 SpecField 여러 건 (SpecSheet.equipment_module 은 요약 표시용)
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
# 공종 (Discipline) - 설계사가 소속된 분야. 대공정과는 별개 축.
# 자동/수동 질의를 이 축으로도 분류해서, 설계사가 자기 공종 질의만 관리할 수 있게 한다.
# ---------------------------------------------------------------------------

DISCIPLINE_SEED = [
    ("PIPING", "공종배관"),
    ("HVAC", "HVAC"),
    ("UPW", "UPW"),
    ("ELECTRIC", "전기"),
    ("ARCH", "건축"),
    ("SPECIALITY_GAS", "SPECIALITY GAS"),
    ("CCSS", "CCSS"),
]

# 제원 대분류 -> 공종 자동 추론 매핑. 자동 질의를 생성할 때 이 표로 공종을 붙인다.
# ※ 추정 매핑이라 실제 조직 구성과 다르면 이 표만 고치면 된다 (건축은 매칭되는
#   대분류가 없어 자동 추론되지 않고, 수동 질의에서 설계사가 직접 선택하는 용도).
CATEGORY_TO_DISCIPLINE_CODE = {
    "GAS/AIR": "PIPING",
    "WATER": "PIPING",
    "WASTER WATER": "PIPING",
    "EXHAUST": "HVAC",
    "UPW": "UPW",
    "POWER": "ELECTRIC",
    "CHEMICAL": "CCSS",
    "폐액": "CCSS",
    "SPECIALITY GAS": "SPECIALITY_GAS",
}

# "GCS" = SPECIALITY GAS + CCSS(폐액) 를 묶어 부르는 현장 용어. 종수(자재명 개수)가
# 중요한 지표라 요약/집계에서 이 두 대분류를 합쳐 별도로 센다.
GCS_CATEGORIES = ("SPECIALITY GAS", "폐액")


class Discipline(Base):
    __tablename__ = "disciplines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(64))

    designers: Mapped[list["Owner"]] = relationship(
        secondary="owner_disciplines", back_populates="disciplines"
    )


# ---------------------------------------------------------------------------
# 담당자/사용자 (Owner) - 역할 3종
#   ADMIN      : 전체 데이터 열람 + 제원표 업로드는 관리자만 가능
#   TECH_LEAD  : 대공정별 담당자, 질의에 답변/승인 (major_processes M:N)
#   DESIGNER   : 공종별 설계사, 질의를 제기하고 답변/최종값을 승인 (disciplines M:N)
# ---------------------------------------------------------------------------


class OwnerRole(str, enum.Enum):
    ADMIN = "ADMIN"
    DESIGNER = "DESIGNER"
    TECH_LEAD = "TECH_LEAD"


owner_major_processes = Table(
    "owner_major_processes",
    Base.metadata,
    Column("owner_id", ForeignKey("owners.id"), primary_key=True),
    Column("major_process_id", ForeignKey("major_processes.id"), primary_key=True),
)

owner_disciplines = Table(
    "owner_disciplines",
    Base.metadata,
    Column("owner_id", ForeignKey("owners.id"), primary_key=True),
    Column("discipline_id", ForeignKey("disciplines.id"), primary_key=True),
)


class Owner(Base):
    __tablename__ = "owners"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(64))
    email: Mapped[str | None] = mapped_column(String(128), nullable=True)
    role: Mapped[OwnerRole] = mapped_column(Enum(OwnerRole), default=OwnerRole.TECH_LEAD)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=now)

    major_processes: Mapped[list["MajorProcess"]] = relationship(
        secondary=owner_major_processes, back_populates="owners"
    )
    disciplines: Mapped[list["Discipline"]] = relationship(
        secondary=owner_disciplines, back_populates="designers"
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
    construction_code: Mapped[str] = mapped_column(String(16), index=True)  # 예: PD000001

    # 설비모듈은 시트 구조상 대분류(UTILITY/GAS·AIR/POWER...)마다 별도 열로 존재하므로
    # 여기서는 업로드시 파싱된 "요약 표시용" 값일 뿐, 식별자로 쓰지 않는다
    # (예: "GAS/AIR:SCRUBBER, POWER:MAIN"). 개별 설비모듈 값은 SpecField 로 저장된다.
    equipment_module: Mapped[str | None] = mapped_column(String(255), nullable=True)

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
    # QAThread는 이제 이 시트 하나에 속하지 않는다 (자동 질의는 여러 시트에 걸친 항목을
    # 하나로 묶으므로). 이 시트를 건드리는 스레드가 필요하면
    # QAThread.join(QAThreadTarget).join(SpecField).filter(spec_sheet_id=...) 로 조회한다
    # (routers/qa.py의 list_threads_for_sheet 참고).

    __table_args__ = (
        UniqueConstraint(
            "construction_code", "major_process_id", "version", name="uq_spec_identity_version"
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
    # 규칙이 명확한 교정 로직을 갖고 있어 대체값을 스스로 계산해낸 경우에만 채워진다
    # (예: alias_correction 규칙). 이 값이 있는 건만 "자동 제원 질의" 일괄 생성 대상이 된다 -
    # services/auto_query.py 참고.
    suggested_value: Mapped[str | None] = mapped_column(String(255), nullable=True)

    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=now)

    spec_sheet: Mapped["SpecSheet"] = relationship(back_populates="validation_results")
    spec_field: Mapped["SpecField | None"] = relationship(back_populates="validation_results")
    rule: Mapped["ValidationRule | None"] = relationship()


# ---------------------------------------------------------------------------
# 질의응답 — 설계사가 질의하고 대공정별 기술팀 담당자가 답변/승인한다.
#
# 두 종류의 질의:
#   AUTO   - 로직이 명확해 시스템이 AS-IS -> TO-BE(suggested_value)를 스스로 계산해서
#            일괄 생성한다 (services/auto_query.py). 기술팀은 승인/미승인 한 번이면 끝.
#            동일한 교정(같은 대공정 + 같은 규칙 + 같은 필드 + 같은 TO-BE)은 하나의
#            QAThread 로 묶이고, 대상 SpecField 들은 QAThreadTarget 으로 여러 건 연결된다
#            (그래야 수천 건짜리 반복 이슈가 질의 수천 개로 안 늘어난다).
#   MANUAL - 로직이 없어 설계사가 서술형으로 직접 질의한다. 2단계 설계사 승인이 필요:
#            (1) 기술팀의 서술형 답변을 설계사가 승인해야 기술팀이 실제 값을 고칠 수 있고,
#            (2) 기술팀이 고친 값(검증 룰셋 통과 필수)을 설계사가 최종 승인해야 DB에 반영된다.
#
# 상태 전이:
#   AUTO:   OPEN -> RESOLVED(승인, 즉시 DB 반영) | REJECTED(미승인)
#   MANUAL: OPEN -> TECH_ANSWERED(기술팀 서술형 답변)
#                -> ANSWER_APPROVED(설계사가 답변 승인, 반려하면 OPEN 으로 되돌아감)
#                -> VALUE_PROPOSED(기술팀이 검증된 새 값 입력, 반려하면 ANSWER_APPROVED 로)
#                -> RESOLVED(설계사 최종 승인, DB 반영) | REJECTED
# ---------------------------------------------------------------------------


class QueryType(str, enum.Enum):
    AUTO = "AUTO"
    MANUAL = "MANUAL"


class QAThreadStatus(str, enum.Enum):
    OPEN = "OPEN"
    TECH_ANSWERED = "TECH_ANSWERED"
    ANSWER_APPROVED = "ANSWER_APPROVED"
    VALUE_PROPOSED = "VALUE_PROPOSED"
    RESOLVED = "RESOLVED"
    REJECTED = "REJECTED"


class QAThread(Base):
    __tablename__ = "qa_threads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    query_type: Mapped[QueryType] = mapped_column(Enum(QueryType), default=QueryType.MANUAL)
    major_process_id: Mapped[int] = mapped_column(ForeignKey("major_processes.id"))
    discipline_id: Mapped[int | None] = mapped_column(ForeignKey("disciplines.id"), nullable=True)
    rule_id: Mapped[int | None] = mapped_column(ForeignKey("validation_rules.id"), nullable=True)

    # 배치 그룹의 대표 필드명 (예: "GAS/AIR_성상명") - 목록 표시/그룹핑 참고용.
    field_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # 제안/확정 값. AUTO는 생성 시점부터, MANUAL은 기술팀이 propose-value 할 때 채워진다.
    to_be_value: Mapped[str | None] = mapped_column(Text, nullable=True)

    title: Mapped[str] = mapped_column(String(255))
    status: Mapped[QAThreadStatus] = mapped_column(Enum(QAThreadStatus), default=QAThreadStatus.OPEN)

    assigned_owner_id: Mapped[int | None] = mapped_column(ForeignKey("owners.id"), nullable=True)
    created_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=now)
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=now, onupdate=now)

    major_process: Mapped["MajorProcess"] = relationship()
    discipline: Mapped["Discipline | None"] = relationship()
    rule: Mapped["ValidationRule | None"] = relationship()
    assigned_owner: Mapped["Owner | None"] = relationship()
    targets: Mapped[list["QAThreadTarget"]] = relationship(
        back_populates="thread", cascade="all, delete-orphan"
    )
    messages: Mapped[list["QAMessage"]] = relationship(
        back_populates="thread", cascade="all, delete-orphan", order_by="QAMessage.created_at"
    )


class QAThreadTarget(Base):
    """QAThread 1건이 가리키는 실제 제원 항목(들). 자동 질의는 동일한 교정이 여러 SpecField에
    걸쳐 있을 수 있어 다대다처럼 여러 건이 달릴 수 있고, 수동 질의는 보통 1건이다."""

    __tablename__ = "qa_thread_targets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    qa_thread_id: Mapped[int] = mapped_column(ForeignKey("qa_threads.id"))
    spec_field_id: Mapped[int] = mapped_column(ForeignKey("spec_fields.id"))
    validation_result_id: Mapped[int | None] = mapped_column(ForeignKey("validation_results.id"), nullable=True)

    thread: Mapped["QAThread"] = relationship(back_populates="targets")
    spec_field: Mapped["SpecField"] = relationship()
    validation_result: Mapped["ValidationResult | None"] = relationship()


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
