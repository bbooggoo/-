"""
엑셀(CAD형 레이아웃) 제원표 파서.

실제 제원표 헤더 예시를 받아 확인한 실제 구조 (2025-09):

  1행 = 대분류 (예: UTILITY / GAS·AIR / POWER / EXHAUST / SPECIALITY GAS /
                 WATER / CHEMICAL / UPW / 폐액 / WASTE WATER ...)
  2행 = 세부 항목 (예: 위치/라인/층/대공정/건설코드/설비대수 - UTILITY 공통 항목,
                   유량/성상명/압력/배관수량/배관재질/설비모듈 - 대분류별 반복 항목)
  3행~ = 데이터. 같은 건설코드를 쓰는 여러 행이 이어질 수 있고, 건설코드 셀은
         그룹의 첫 행에만 채워지고 그 아래 행들은 비어 있다(carry-down 관례).

"대공정/건설코드/설비모듈" 3개 분류축 중 대공정은 업로드 시에도 지정하지만(어느 대공정
담당자가 검토할지 배정하는 메타데이터), UTILITY 공통 항목에 "대공정" 열도 있어서 시트
데이터 안에도 같은 값이 기록된다(교차 확인용). 건설코드/설비모듈은 시트 안의 데이터에서
직접 읽어야 한다. 설비모듈은 대분류(UTILITY 대분류)마다 각각 별도 열로 존재한다
(GAS·AIR용, POWER용 ...).

`parse_grouped_excel()` 이 이 실제 구조를 처리하는 기본 파서다. 건설코드 단위로
행을 그룹핑해서, 건설코드 1개당 SpecSheet 1건이 생성되도록 그룹 리스트를 반환한다.

과거 버전에서 쓰던 단순 "라벨열/값열/단위열" 파서(`parse_excel`)는 다른 형식의
파일이 들어올 경우를 대비해 그대로 남겨뒀다 (업로드 화면에서 "단순 라벨-값 표"
모드로 선택 가능).
"""
import re
from dataclasses import dataclass, field
from io import BytesIO

from openpyxl import load_workbook

from ..schemas import validate_construction_code

# 헤더 라벨에 "필드명(단위)" 형태로 단위가 괄호로 붙어있는 경우 분리 (예: "유량(LPM)")
_UNIT_SUFFIX_RE = re.compile(r"^(?P<label>.*?)\((?P<unit>[^()]+)\)\s*$")


@dataclass
class ParsedCell:
    row: int
    col: int
    value: str
    field_name: str | None = None
    unit: str | None = None


# ---------------------------------------------------------------------------
# 단순 라벨/값/단위 열 파서 (레거시/대체 모드)
# ---------------------------------------------------------------------------


@dataclass
class ImportConfig:
    sheet_name: str | None = None      # None이면 첫 번째 시트
    header_row: int = 1                # 라벨-값 파싱을 시작할 행 (1-indexed), 이 행부터 끝까지 스캔
    label_col: int = 1                 # 라벨 열 (1-indexed, A=1)
    value_col: int = 2                 # 값 열
    unit_col: int | None = 3           # 단위 열 (선택)


@dataclass
class ParsedSheet:
    sheet_name: str
    cells: list[ParsedCell] = field(default_factory=list)


def parse_excel(file_bytes: bytes, config: ImportConfig) -> ParsedSheet:
    wb = load_workbook(BytesIO(file_bytes), data_only=True)
    ws = wb[config.sheet_name] if config.sheet_name else wb.worksheets[0]

    cells: list[ParsedCell] = []
    label_by_row: dict[int, str] = {}

    for row in ws.iter_rows(min_row=1):
        for cell in row:
            if cell.value is None or str(cell.value).strip() == "":
                continue
            text = str(cell.value).strip()

            if cell.row >= config.header_row and cell.column == config.label_col:
                label_by_row[cell.row] = text

            cells.append(ParsedCell(row=cell.row, col=cell.column, value=text))

    # 라벨/값/단위 매핑 채우기
    unit_by_row: dict[int, str] = {}
    if config.unit_col:
        for c in cells:
            if c.col == config.unit_col and c.row in label_by_row:
                unit_by_row[c.row] = c.value

    for c in cells:
        if c.col == config.value_col and c.row in label_by_row:
            c.field_name = label_by_row[c.row]
            c.unit = unit_by_row.get(c.row)

    return ParsedSheet(sheet_name=ws.title, cells=cells)


# ---------------------------------------------------------------------------
# 2단 헤더(대분류/세부항목) + 건설코드 그룹핑 파서 (기본 모드)
# ---------------------------------------------------------------------------

DEFAULT_COMMON_FIELD_NAMES = ("위치", "라인", "층", "대공정", "건설코드", "설비대수")
DEFAULT_CONSTRUCTION_CODE_FIELD = "건설코드"
DEFAULT_EQUIPMENT_MODULE_FIELD = "설비모듈"


@dataclass
class GroupedImportConfig:
    sheet_name: str | None = None
    category_row: int = 1     # 대분류 행
    label_row: int = 2        # 세부 항목 행
    data_start_row: int = 3   # 데이터 시작 행
    construction_code_field: str = DEFAULT_CONSTRUCTION_CODE_FIELD
    common_field_names: tuple[str, ...] = DEFAULT_COMMON_FIELD_NAMES
    # 시트에 건설코드가 비어있는 행(들)에 적용할 대체 값 (선택).
    # 그룹의 첫 행에서도 건설코드를 못 찾으면 이 값을 사용한다.
    construction_code_override: str | None = None


@dataclass
class ParsedSpecGroup:
    construction_code: str
    cells: list[ParsedCell]
    equipment_module_summary: str | None
    row_range: tuple[int, int]


@dataclass
class GroupedParseResult:
    sheet_name: str
    groups: list[ParsedSpecGroup] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def _split_unit(label_text: str) -> tuple[str, str | None]:
    m = _UNIT_SUFFIX_RE.match(label_text)
    if m:
        return m.group("label").strip(), m.group("unit").strip()
    return label_text, None


def parse_grouped_excel(file_bytes: bytes, config: GroupedImportConfig) -> GroupedParseResult:
    wb = load_workbook(BytesIO(file_bytes), data_only=True)
    ws = wb[config.sheet_name] if config.sheet_name else wb.worksheets[0]

    max_row = ws.max_row
    max_col = ws.max_column

    # 1) 열 헤더 해석: 대분류(row1) + 세부항목(row2) -> field_name / unit
    col_info: dict[int, dict] = {}
    for col in range(1, max_col + 1):
        raw_label = ws.cell(config.label_row, col).value
        if raw_label is None or str(raw_label).strip() == "":
            continue
        base_label, unit = _split_unit(str(raw_label).strip())

        raw_category = ws.cell(config.category_row, col).value
        category = str(raw_category).strip() if raw_category not in (None, "") else ""

        is_common = base_label in config.common_field_names
        if is_common or not category:
            field_name = base_label
        else:
            field_name = f"{category}_{base_label}"

        col_info[col] = {
            "field_name": field_name,
            "unit": unit,
            "base_label": base_label,
            "category": category,
        }

    code_col = next(
        (c for c, info in col_info.items() if info["base_label"] == config.construction_code_field),
        None,
    )

    # 2) 헤더 행(대분류/세부항목)은 원본 레이아웃 보존용으로 그대로 저장, 모든 그룹이 공유
    header_cells: list[ParsedCell] = []
    for row in ws.iter_rows(min_row=1, max_row=config.data_start_row - 1, max_col=max_col):
        for cell in row:
            if cell.value is None or str(cell.value).strip() == "":
                continue
            header_cells.append(ParsedCell(row=cell.row, col=cell.column, value=str(cell.value).strip()))

    # 3) 건설코드 carry-down(빈 셀은 직전 값을 이어받음)으로 행 -> 건설코드 매핑
    current_code = config.construction_code_override or None
    row_code: dict[int, str | None] = {}
    for r in range(config.data_start_row, max_row + 1):
        text = ""
        if code_col is not None:
            raw = ws.cell(r, code_col).value
            text = str(raw).strip() if raw not in (None, "") else ""
        if text:
            current_code = text
        row_code[r] = current_code

    # 4) 행을 건설코드별로 그룹핑 (완전히 빈 행은 건너뜀)
    warnings: list[str] = []
    groups_order: list[str] = []
    group_rows: dict[str, list[int]] = {}
    ungrouped_rows: list[int] = []

    for r in range(config.data_start_row, max_row + 1):
        row_has_data = any(ws.cell(r, c).value not in (None, "") for c in col_info)
        if not row_has_data:
            continue
        code = row_code[r]
        if not code:
            ungrouped_rows.append(r)
            continue
        if code not in group_rows:
            group_rows[code] = []
            groups_order.append(code)
        group_rows[code].append(r)

    if ungrouped_rows:
        warnings.append(
            f"건설코드를 확인할 수 없어 가져오지 못한 행: {ungrouped_rows} "
            "(업로드 시 '건설코드 대체값'을 입력하면 반영됩니다)"
        )

    # 5) 그룹별로 데이터 셀 + 설비모듈 요약 생성
    groups: list[ParsedSpecGroup] = []
    for code in groups_order:
        try:
            validate_construction_code(code)
        except ValueError:
            warnings.append(f"'{code}' 건설코드 형식이 규칙(P+영숫자7자리)과 다릅니다. 그대로 저장했습니다.")

        cells = list(header_cells)
        equip_values: list[str] = []
        rows = group_rows[code]
        for r in rows:
            for c, info in col_info.items():
                raw = ws.cell(r, c).value
                if raw is None or str(raw).strip() == "":
                    continue
                text = str(raw).strip()
                cells.append(
                    ParsedCell(row=r, col=c, value=text, field_name=info["field_name"], unit=info["unit"])
                )
                if info["base_label"] == DEFAULT_EQUIPMENT_MODULE_FIELD:
                    equip_values.append(f"{info['category']}:{text}" if info["category"] else text)

        groups.append(
            ParsedSpecGroup(
                construction_code=code,
                cells=cells,
                equipment_module_summary=", ".join(dict.fromkeys(equip_values)) or None,
                row_range=(min(rows), max(rows)),
            )
        )

    return GroupedParseResult(sheet_name=ws.title, groups=groups, warnings=warnings)
