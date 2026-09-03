"""
그럴듯한 반도체 제원표 데모 엑셀 생성.

실제 받은 헤더 구조(1행 대분류 / 2행 세부항목)를 그대로 따르고, 사용자 피드백을
반영해 아래 관례로 데이터를 채운다.

  1. UTILITY의 설비대수는 항상 1.
  2. MAIN 설비 + 거기 붙는 부대설비들은 같은 "가족"이지만 서로 다른 건설코드를
     쓴다 (예: PD000102-01 = MAIN, -02/-03 = 부대설비). 그래서 이 파일은
     PD000101-01/-02, PD000102-01/-02/-03 총 5개 건설코드 그룹으로 나뉜다
     (건설코드 1개당 제원표 1건이 생성된다).
  3. 성상명/자재명은 전부 영어(또는 화학식) 표기. 단, "GN2"처럼 영어이지만
     표준 성상명 목록(N2/O2/AR/CDA/HE/H2)에는 없는 값을 하나 섞어서 표준화
     검증(WARN)이 실제로 잡아내는 걸 보여준다.
  4. 전원종류는 NOR(상용전원)/UPS(무정전전원) 두 가지만 사용.
  5. EXHAUST의 성상명은 PFC/DE-PFC/ACID/ALKALI/GDM/HEAT-GEN/RECOVERY 중에서만 사용.
  6. 행이 한 번 작성되면 그 행의 UTILITY 칸(위치/라인/층/건설코드/설비대수)은
     모두 채운다 (건설코드 carry-down으로 빈칸을 남기지 않는다).

유량 OVER(O2 8 SLPM > 기준 6 SLPM)와 표준화 안 된 성상값(GN2)은 의도적으로
남겨서, 시드된 기본 검증 규칙(app/seed.py의 DEFAULT_VALIDATION_RULES)이 실제로
이슈를 잡아내는 걸 보여준다.

실행: (backend/ 에서) python -m scripts.generate_demo_data [출력경로.xlsx]
"""
import sys
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill

COLUMNS = [
    ("UTILITY", "위치"), ("UTILITY", "라인"), ("UTILITY", "층"), ("UTILITY", "건설코드"), ("UTILITY", "설비대수"),
    ("GAS/AIR", "배관수량"), ("GAS/AIR", "설비모듈"), ("GAS/AIR", "유량"), ("GAS/AIR", "성상명"),
    ("GAS/AIR", "배관수량"), ("GAS/AIR", "압력"), ("GAS/AIR", "배관재질"),
    ("POWER", "전력값"), ("POWER", "설비모듈"), ("POWER", "부하전류"), ("POWER", "전압"),
    ("POWER", "차단기전류"), ("POWER", "전원종류"),
    ("EXHAUST", "풍량"), ("EXHAUST", "설비모듈"), ("EXHAUST", "성상명"), ("EXHAUST", "포트 수량"),
    ("SPECIALITY GAS", "배관수량"), ("SPECIALITY GAS", "설비모듈"), ("SPECIALITY GAS", "유량"), ("SPECIALITY GAS", "자재명"),
    ("WATER", "성상명"), ("WATER", "설비모듈"), ("WATER", "배관수량"), ("WATER", "유량"), ("WATER", "압력"),
    ("CHEMICAL", "실사용량"), ("CHEMICAL", "성상명"),
    ("UPW", "실사용량"), ("UPW", "설비모듈"), ("UPW", "성상명"),
    ("폐액", "자재명"), ("폐액", "실사용량"),
    ("WASTER WATER", "성상명"), ("WASTER WATER", "유량"), ("WASTER WATER", "설비모듈"), ("WASTER WATER", "배관수량"),
]

UTILITY_LABELS = ["위치", "라인", "층", "건설코드", "설비대수"]


def col_index(category, label, occurrence=0):
    hits = [i for i, (c, l) in enumerate(COLUMNS, start=1) if c == category and l == label]
    return hits[occurrence]


def write_row(ws, r, utility, item_values):
    """utility: {건설코드, 위치, 라인, 층} (설비대수는 항상 1로 자동 채움).
    item_values: {(category, label[, occurrence]): value} - 대분류 항목만."""
    ws.cell(r, col_index("UTILITY", "위치"), utility["위치"])
    ws.cell(r, col_index("UTILITY", "라인"), utility["라인"])
    ws.cell(r, col_index("UTILITY", "층"), utility["층"])
    ws.cell(r, col_index("UTILITY", "건설코드"), utility["건설코드"])
    ws.cell(r, col_index("UTILITY", "설비대수"), 1)  # 항상 1

    for key, value in item_values.items():
        if len(key) == 3:
            category, label, occ = key
        else:
            category, label = key
            occ = 0
        ws.cell(r, col_index(category, label, occ), value)


def write_group(ws, start_row, code, site, item_rows):
    """같은 건설코드(code)를 쓰는 여러 행을 이어서 쓴다. site: {위치,라인,층}.
    모든 행에 UTILITY 칸을 전부 채운다 (carry-down 없이)."""
    utility = dict(site, 건설코드=code)
    r = start_row
    for items in item_rows:
        write_row(ws, r, utility, items)
        r += 1
    return r


def build():
    wb = Workbook()
    ws = wb.active
    ws.title = "제원표"

    header_fill = PatternFill(start_color="DDEBF7", end_color="DDEBF7", fill_type="solid")
    bold = Font(bold=True)
    for col_idx, (category, label) in enumerate(COLUMNS, start=1):
        c1 = ws.cell(1, col_idx, category)
        c2 = ws.cell(2, col_idx, label)
        c1.font = bold
        c2.font = bold
        c1.fill = header_fill
        c2.fill = header_fill
        c1.alignment = Alignment(horizontal="center")
        c2.alignment = Alignment(horizontal="center")

    r = 3
    CVD_SITE = {"위치": "평택", "라인": "P4", "층": "3F"}
    ETCH_SITE = {"위치": "평택", "라인": "P4", "층": "4F"}

    # ------------------------------------------------------------------
    # PD000101-01: CVD 장비 A동 MAIN (챔버 본체 - 가스/전원/배기/특수가스)
    # ------------------------------------------------------------------
    r = write_group(ws, r, "PD000101-01", CVD_SITE, [
        {
            ("GAS/AIR", "설비모듈"): "SCRUBBER", ("GAS/AIR", "유량"): 9, ("GAS/AIR", "성상명"): "N2",
            ("GAS/AIR", "배관수량"): 2, ("GAS/AIR", "압력"): 3.5, ("GAS/AIR", "배관재질"): "SUS316L",
            ("POWER", "전력값"): 45, ("POWER", "설비모듈"): "MAIN", ("POWER", "부하전류"): 68, ("POWER", "전압"): 380,
            ("POWER", "차단기전류"): 100, ("POWER", "전원종류"): "NOR",
            ("EXHAUST", "풍량"): 12, ("EXHAUST", "설비모듈"): "MAIN", ("EXHAUST", "성상명"): "PFC", ("EXHAUST", "포트 수량"): 2,
            ("SPECIALITY GAS", "배관수량"): 1, ("SPECIALITY GAS", "설비모듈"): "GAS CABINET", ("SPECIALITY GAS", "유량"): 2, ("SPECIALITY GAS", "자재명"): "SiH4",
        },
        # O2 8 SLPM: 기준(6) 초과 -> 유량 OVER 데모
        {
            ("GAS/AIR", "설비모듈"): "SCRUBBER", ("GAS/AIR", "유량"): 8, ("GAS/AIR", "성상명"): "O2",
            ("GAS/AIR", "배관수량"): 1, ("GAS/AIR", "압력"): 3.0, ("GAS/AIR", "배관재질"): "SUS316L",
            # 컨트롤러용 무정전전원(UPS)
            ("POWER", "전력값"): 5, ("POWER", "설비모듈"): "CONTROLLER", ("POWER", "부하전류"): 8, ("POWER", "전압"): 24,
            ("POWER", "차단기전류"): 10, ("POWER", "전원종류"): "UPS",
        },
        {
            ("GAS/AIR", "설비모듈"): "SCRUBBER", ("GAS/AIR", "유량"): 6, ("GAS/AIR", "성상명"): "CDA",
            ("GAS/AIR", "배관수량"): 2, ("GAS/AIR", "압력"): 4.0, ("GAS/AIR", "배관재질"): "SUS316L",
            ("SPECIALITY GAS", "배관수량"): 1, ("SPECIALITY GAS", "설비모듈"): "GAS CABINET", ("SPECIALITY GAS", "유량"): 1, ("SPECIALITY GAS", "자재명"): "PH3",
        },
        # "GN2"(영어 표기지만 표준 성상명 목록엔 없음) -> 표준화 WARN 데모
        {
            ("GAS/AIR", "설비모듈"): "SCRUBBER", ("GAS/AIR", "유량"): 4, ("GAS/AIR", "성상명"): "GN2",
            ("GAS/AIR", "배관수량"): 2, ("GAS/AIR", "압력"): 3.2, ("GAS/AIR", "배관재질"): "SUS316L",
        },
    ])

    # ------------------------------------------------------------------
    # PD000101-02: CVD 장비 A동 부대설비 (Water/Chemical/UPW/폐수 스키드)
    # ------------------------------------------------------------------
    r = write_group(ws, r, "PD000101-02", CVD_SITE, [
        {
            ("WATER", "성상명"): "PCW", ("WATER", "설비모듈"): "MAIN", ("WATER", "배관수량"): 2, ("WATER", "유량"): 40, ("WATER", "압력"): 5,
            ("CHEMICAL", "실사용량"): 120, ("CHEMICAL", "성상명"): "IPA",
            ("UPW", "실사용량"): 8.5, ("UPW", "설비모듈"): "MAIN", ("UPW", "성상명"): "HOT DI",
            ("폐액", "자재명"): "ACID WASTE", ("폐액", "실사용량"): 2.4,
            ("WASTER WATER", "성상명"): "IWW1", ("WASTER WATER", "유량"): 25, ("WASTER WATER", "설비모듈"): "MAIN", ("WASTER WATER", "배관수량"): 1,
        },
        {
            ("UPW", "실사용량"): 3.2, ("UPW", "설비모듈"): "MAIN", ("UPW", "성상명"): "COOL DI",
            ("WASTER WATER", "성상명"): "IWW2", ("WASTER WATER", "유량"): 10, ("WASTER WATER", "설비모듈"): "MAIN", ("WASTER WATER", "배관수량"): 1,
        },
        {
            ("UPW", "실사용량"): 1.1, ("UPW", "설비모듈"): "MAIN", ("UPW", "성상명"): "HIGH DI",
        },
    ])

    # ------------------------------------------------------------------
    # PD000102-01: ETCH 장비 B동 MAIN
    # ------------------------------------------------------------------
    r = write_group(ws, r, "PD000102-01", ETCH_SITE, [
        {
            ("GAS/AIR", "설비모듈"): "SCRUBBER", ("GAS/AIR", "유량"): 7, ("GAS/AIR", "성상명"): "AR",
            ("GAS/AIR", "배관수량"): 3, ("GAS/AIR", "압력"): 3.8, ("GAS/AIR", "배관재질"): "SUS316L",
            ("POWER", "전력값"): 60, ("POWER", "설비모듈"): "MAIN", ("POWER", "부하전류"): 90, ("POWER", "전압"): 380,
            ("POWER", "차단기전류"): 125, ("POWER", "전원종류"): "NOR",
            ("EXHAUST", "풍량"): 15, ("EXHAUST", "설비모듈"): "MAIN", ("EXHAUST", "성상명"): "DE-PFC", ("EXHAUST", "포트 수량"): 3,
            ("SPECIALITY GAS", "배관수량"): 1, ("SPECIALITY GAS", "설비모듈"): "GAS CABINET", ("SPECIALITY GAS", "유량"): 1, ("SPECIALITY GAS", "자재명"): "WF6",
        },
        {
            ("GAS/AIR", "설비모듈"): "SCRUBBER", ("GAS/AIR", "유량"): 5, ("GAS/AIR", "성상명"): "H2",
            ("GAS/AIR", "배관수량"): 2, ("GAS/AIR", "압력"): 3.0, ("GAS/AIR", "배관재질"): "SUS316L",
            ("POWER", "전력값"): 4, ("POWER", "설비모듈"): "CONTROLLER", ("POWER", "부하전류"): 6, ("POWER", "전압"): 24,
            ("POWER", "차단기전류"): 10, ("POWER", "전원종류"): "UPS",
        },
    ])

    # ------------------------------------------------------------------
    # PD000102-02: ETCH 장비 B동 부대설비1 (Scrubber/Exhaust 스키드)
    # ------------------------------------------------------------------
    r = write_group(ws, r, "PD000102-02", ETCH_SITE, [
        {
            ("EXHAUST", "풍량"): 9, ("EXHAUST", "설비모듈"): "SCRUBBER", ("EXHAUST", "성상명"): "ALKALI", ("EXHAUST", "포트 수량"): 2,
            ("WATER", "성상명"): "PCW", ("WATER", "설비모듈"): "SCRUBBER", ("WATER", "배관수량"): 2, ("WATER", "유량"): 20, ("WATER", "압력"): 4.5,
        },
    ])

    # ------------------------------------------------------------------
    # PD000102-03: ETCH 장비 B동 부대설비2 (Chemical/UPW/폐수 스키드)
    # ------------------------------------------------------------------
    r = write_group(ws, r, "PD000102-03", ETCH_SITE, [
        {
            ("CHEMICAL", "실사용량"): 80, ("CHEMICAL", "성상명"): "SULFURIC ACID",
            ("UPW", "실사용량"): 6.0, ("UPW", "설비모듈"): "MAIN", ("UPW", "성상명"): "HOT DI",
            ("폐액", "자재명"): "ACID WASTE", ("폐액", "실사용량"): 1.8,
            ("WASTER WATER", "성상명"): "AKWW", ("WASTER WATER", "유량"): 18, ("WASTER WATER", "설비모듈"): "MAIN", ("WASTER WATER", "배관수량"): 1,
        },
    ])

    ws.freeze_panes = "A3"
    for col_idx in range(1, len(COLUMNS) + 1):
        ws.column_dimensions[ws.cell(1, col_idx).column_letter].width = 12

    return wb


if __name__ == "__main__":
    out_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent / "demo_spec_sheet.xlsx"
    wb = build()
    wb.save(out_path)
    print(f"saved: {out_path}")
