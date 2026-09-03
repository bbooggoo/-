"""
엑셀(CAD형 레이아웃) 제원표 파서.

===========================================================================
확장 포인트: 실제 엑셀 헤더 예시를 받으면 이 파일의 매핑 로직을 정교화하세요.
===========================================================================

현재 MVP 방식:
  - 시트의 모든 비어있지 않은 셀을 좌표(row, col) 그대로 SpecField 로 저장한다
    (원본 CAD 레이아웃을 그대로 보존 -> 나중에 export 시 원형 복원 가능).
  - 그중 "라벨열(label_col) / 값열(value_col) / 단위열(unit_col, 선택)" 로 지정된
    조합에 해당하는 셀만 field_name(=라벨 텍스트) 과 unit 이 채워져서 검증 규칙이
    참조할 수 있는 "속성"이 된다. 그 외 셀들은 field_name=None 인 원본 그리드 데이터.
  - 실제 서식이 여러 블록/여러 라벨-값 쌍이 한 행에 반복되는 CAD 표라면,
    label_col/value_col/unit_col 을 리스트로 여러 개 받도록 확장하면 된다
    (지금은 단일 컬럼 세트만 지원하는 단순 버전).
"""
from dataclasses import dataclass, field
from io import BytesIO

from openpyxl import load_workbook


@dataclass
class ImportConfig:
    sheet_name: str | None = None      # None이면 첫 번째 시트
    header_row: int = 1                # 라벨-값 파싱을 시작할 행 (1-indexed), 이 행부터 끝까지 스캔
    label_col: int = 1                 # 라벨 열 (1-indexed, A=1)
    value_col: int = 2                 # 값 열
    unit_col: int | None = 3           # 단위 열 (선택)


@dataclass
class ParsedCell:
    row: int
    col: int
    value: str
    field_name: str | None = None
    unit: str | None = None


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
