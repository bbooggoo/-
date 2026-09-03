"""
엑셀(CAD형 레이아웃) 제원표 파서.

실제 제원표 헤더 예시를 받아 확인한 실제 구조 (2025-09):

  1행 = 대분류 (예: UTILITY / GAS·AIR / POWER / EXHAUST / SPECIALITY GAS /
                 WATER / CHEMICAL / UPW / 폐액 / WASTE WATER ...)
  2행 = 세부 항목 (예: 위치/라인/층/대공정/PRC/MODEL/MAKER/건설코드/설비대수 -
                   UTILITY 공통 항목, 유량/성상명/압력/배관수량/배관재질/설비모듈 -
                   대분류별 반복 항목)
  3행~ = 데이터. 같은 건설코드를 쓰는 여러 행이 이어질 수 있고, 건설코드 셀은
         그룹의 첫 행에만 채워지고 그 아래 행들은 비어 있다(carry-down 관례).

"대공정/건설코드/설비모듈" 3개 분류축 중 대공정은 업로드 시에도 지정하지만(어느 대공정
담당자가 검토할지 배정하는 메타데이터), UTILITY 공통 항목에 "대공정" 열도 있어서 시트
데이터 안에도 같은 값이 기록된다. 건설코드/설비모듈은 시트 안의 데이터에서 직접 읽어야
한다. 설비모듈은 대분류(UTILITY 대분류)마다 각각 별도 열로 존재한다(GAS·AIR용, POWER용 ...).

===========================================================================
현실 데이터는 항상 같은 양식으로 오지 않는다 — 이 파서가 스스로 처리하는 것들:
===========================================================================
  - **헤더 행 위치가 다를 수 있음**: category_row/label_row/data_start_row를 지정하지
    않으면(None) `_detect_header_rows()`가 알려진 라벨(공통 항목 + 대분류별 세부항목
    이름)이 가장 많이 매칭되는 행을 세부항목 행으로 자동 인식한다. 명시적으로 지정하면
    그 값을 그대로 쓴다(우선순위: 사용자 지정 > 자동 인식).
  - **한 파일에 대공정이 여러 개 섞여 들어올 수 있음**: 대공정별로 파일이 따로 오는 경우
    (업로드 시 지정한 대공정을 그대로 적용)와, 한 엑셀에 여러 대공정 행이 섞여 오는 경우
    (시트의 "대공정" 열 값을 읽어서 건설코드 그룹마다 실제 대공정을 판별) 둘 다 지원한다.
    "대공정" 열도 건설코드처럼 carry-down을 허용한다. 판별/매칭은 라우터(DB 조회 필요)에서
    한다 — 이 함수는 그룹별 원본 문자열(major_process_raw)만 반환한다.
  - **대소문자/공백 차이**: 라벨/대공정 값 비교는 모두 trim 후 비교한다.

이 정도의 변형은 흡수하지만, 완전히 다른 표 구조(예: 대분류 행 자체가 없는 표, 세로형
레이아웃)까지 자동으로 알아내지는 못한다 — 그런 경우 업로드 화면에서 "단순 표" 모드를
쓰거나 이 파일의 파싱 로직을 새로 추가해야 한다.
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

DEFAULT_COMMON_FIELD_NAMES = ("위치", "라인", "층", "대공정", "PRC", "MODEL", "MAKER", "건설코드", "설비대수")
DEFAULT_CONSTRUCTION_CODE_FIELD = "건설코드"
DEFAULT_MAJOR_PROCESS_FIELD = "대공정"
DEFAULT_EQUIPMENT_MODULE_FIELD = "설비모듈"

# 헤더 행 자동 인식에 쓰는 힌트 라벨 (공통 항목 + 대분류별로 실제 관찰된 세부항목 이름들).
# 실제 파일에 새로운 세부항목 이름이 나오면 이 목록에 추가하면 자동 인식 정확도가 올라간다.
HEADER_LABEL_HINTS = set(DEFAULT_COMMON_FIELD_NAMES) | {
    "유량", "성상명", "자재명", "압력", "배관수량", "배관재질", "설비모듈",
    "전력값", "부하전류", "전압", "차단기전류", "전원종류",
    "풍량", "포트 수량", "실사용량",
}


@dataclass
class GroupedImportConfig:
    sheet_name: str | None = None
    # None이면 자동 인식(_detect_header_rows). 지정하면 그 값을 그대로 쓴다.
    category_row: int | None = None
    label_row: int | None = None
    data_start_row: int | None = None
    construction_code_field: str = DEFAULT_CONSTRUCTION_CODE_FIELD
    major_process_field: str = DEFAULT_MAJOR_PROCESS_FIELD
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
    # 시트에 기록된 "대공정" 원문 (여러 값이 섞여 있으면 가장 많이 등장한 값). 값이 전혀
    # 없으면 None -> 업로드 시 선택한 대공정을 그대로 쓴다. DB 매칭은 라우터가 담당.
    major_process_raw: str | None = None


@dataclass
class GroupedParseResult:
    sheet_name: str
    groups: list[ParsedSpecGroup] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    header_rows_auto_detected: bool = False


def _split_unit(label_text: str) -> tuple[str, str | None]:
    m = _UNIT_SUFFIX_RE.match(label_text)
    if m:
        return m.group("label").strip(), m.group("unit").strip()
    return label_text, None


def _detect_header_rows(ws, max_scan_rows: int = 10) -> tuple[int, int, int, int]:
    """세부항목(label) 행을 자동으로 찾는다: 알려진 라벨과 가장 많이 일치하는 행을 고른다.

    대분류(category) 행은 보통 라벨 행 바로 위이므로 label_row - 1 로 가정하되, 그 행이
    비어있거나 라벨 행과 내용이 같으면(=대분류 행이 따로 없는 단일 헤더 표) category_row를
    label_row와 같게 둔다 (이 경우 대분류 접두어 없이 세부항목 이름만으로 필드명이 잡힌다).

    반환하는 네 번째 값(score)은 몇 개의 라벨이 매칭됐는지로, 호출하는 쪽에서 "자신있게
    인식했는지"를 판단하는 데 쓴다 (낮으면 사용자에게 확인을 요청하는 게 안전하다).
    """
    best_row, best_score = 1, -1
    for r in range(1, max_scan_rows + 1):
        texts = [str(c.value).strip() for c in ws[r] if c.value not in (None, "")]
        if not texts:
            continue
        score = sum(1 for t in texts if _split_unit(t)[0] in HEADER_LABEL_HINTS)
        if score > best_score:
            best_row, best_score = r, score

    label_row = best_row if best_score > 0 else 1
    category_row = label_row - 1 if label_row > 1 else label_row
    if category_row >= 1:
        cat_texts = {str(c.value).strip() for c in ws[category_row] if c.value not in (None, "")}
        label_texts = {str(c.value).strip() for c in ws[label_row] if c.value not in (None, "")}
        if not cat_texts or cat_texts == label_texts:
            category_row = label_row  # 대분류 행이 따로 없음 -> 단일 헤더로 취급
    data_start_row = label_row + 1
    return category_row, label_row, data_start_row, max(best_score, 0)


def parse_grouped_excel(file_bytes: bytes, config: GroupedImportConfig) -> GroupedParseResult:
    wb = load_workbook(BytesIO(file_bytes), data_only=True)
    ws = wb[config.sheet_name] if config.sheet_name else wb.worksheets[0]

    max_row = ws.max_row
    max_col = ws.max_column

    auto_detected = config.category_row is None or config.label_row is None or config.data_start_row is None
    det_category_row, det_label_row, det_data_start_row, det_score = _detect_header_rows(ws)
    category_row = config.category_row if config.category_row is not None else det_category_row
    label_row = config.label_row if config.label_row is not None else det_label_row
    data_start_row = config.data_start_row if config.data_start_row is not None else det_data_start_row
    # 자동 인식이 별로 확신이 없을 때만(매칭된 라벨이 2개 이하) 경고한다 - 확실하게 인식했으면
    # 조용히 진행한다. 낮은 확신도는 나중에 warnings 리스트에 추가된다.
    header_detection_low_confidence = auto_detected and det_score <= 2

    # 1) 열 헤더 해석: 대분류(category_row) + 세부항목(label_row) -> field_name / unit
    col_info: dict[int, dict] = {}
    for col in range(1, max_col + 1):
        raw_label = ws.cell(label_row, col).value
        if raw_label is None or str(raw_label).strip() == "":
            continue
        base_label, unit = _split_unit(str(raw_label).strip())

        raw_category = ws.cell(category_row, col).value if category_row != label_row else None
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
    mp_col = next(
        (c for c, info in col_info.items() if info["base_label"] == config.major_process_field),
        None,
    )

    # 2) 헤더 행은 원본 레이아웃 보존용으로 그대로 저장, 모든 그룹이 공유
    header_cells: list[ParsedCell] = []
    for row in ws.iter_rows(min_row=1, max_row=max(data_start_row - 1, 1), max_col=max_col):
        for cell in row:
            if cell.value is None or str(cell.value).strip() == "":
                continue
            header_cells.append(ParsedCell(row=cell.row, col=cell.column, value=str(cell.value).strip()))

    # 3) 건설코드/대공정 carry-down(빈 셀은 직전 값을 이어받음)으로 행 -> 값 매핑
    current_code = config.construction_code_override or None
    current_mp = None
    row_code: dict[int, str | None] = {}
    row_mp: dict[int, str | None] = {}
    for r in range(data_start_row, max_row + 1):
        code_text = ""
        if code_col is not None:
            raw = ws.cell(r, code_col).value
            code_text = str(raw).strip() if raw not in (None, "") else ""
        if code_text:
            current_code = code_text
        row_code[r] = current_code

        mp_text = ""
        if mp_col is not None:
            raw = ws.cell(r, mp_col).value
            mp_text = str(raw).strip() if raw not in (None, "") else ""
        if mp_text:
            current_mp = mp_text
        row_mp[r] = current_mp

    # 4) 행을 건설코드별로 그룹핑 (완전히 빈 행은 건너뜀)
    warnings: list[str] = []
    if header_detection_low_confidence:
        warnings.append(
            f"헤더 행을 확신 있게 인식하지 못했습니다 (추정: 대분류 {category_row}행 / 세부항목 "
            f"{label_row}행 / 데이터 {data_start_row}행부터). 결과가 이상하면 헤더 행 번호를 "
            "직접 입력해 주세요."
        )
    groups_order: list[str] = []
    group_rows: dict[str, list[int]] = {}
    ungrouped_rows: list[int] = []

    for r in range(data_start_row, max_row + 1):
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

    # 5) 그룹별로 데이터 셀 + 설비모듈 요약 + 대공정(다수결) 생성
    groups: list[ParsedSpecGroup] = []
    for code in groups_order:
        try:
            validate_construction_code(code)
        except ValueError:
            warnings.append(f"'{code}' 건설코드 형식이 규칙(P+영숫자7자리)과 다릅니다. 그대로 저장했습니다.")

        cells = list(header_cells)
        equip_values: list[str] = []
        mp_votes: dict[str, int] = {}
        rows = group_rows[code]
        for r in rows:
            if row_mp.get(r):
                mp_votes[row_mp[r]] = mp_votes.get(row_mp[r], 0) + 1
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

        major_process_raw = max(mp_votes, key=mp_votes.get) if mp_votes else None
        if len(mp_votes) > 1:
            warnings.append(
                f"'{code}' 그룹 안에 대공정 표기가 여러 개 섞여 있습니다({', '.join(mp_votes)}). "
                f"가장 많이 나온 '{major_process_raw}'로 처리했습니다."
            )

        groups.append(
            ParsedSpecGroup(
                construction_code=code,
                cells=cells,
                equipment_module_summary=", ".join(dict.fromkeys(equip_values)) or None,
                row_range=(min(rows), max(rows)),
                major_process_raw=major_process_raw,
            )
        )

    return GroupedParseResult(
        sheet_name=ws.title, groups=groups, warnings=warnings, header_rows_auto_detected=auto_detected
    )
