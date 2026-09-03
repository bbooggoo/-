"""
그럴듯한 반도체 제원표 데모 엑셀 생성.

실제 받은 헤더 구조(1행 대분류 / 2행 세부항목)를 그대로 따르고, 건설코드 2건
(PD000101, PD000102)에 대해 대분류별로 현실적인 값을 채운다. 일부러 유량
OVER(O2 8 SLPM > 기준 6 SLPM)와 표준화 안 된 성상값("질소"라는 한글 표기)을
섞어서, 시드된 기본 검증 규칙(app/seed.py의 DEFAULT_VALIDATION_RULES)이 실제로
이슈를 잡아내는 걸 보여준다.

실행: (backend/ 에서) python -m scripts.generate_demo_data [출력경로.xlsx]
"""
import sys
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment

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

COMMON = {"위치", "라인", "층", "건설코드", "설비대수"}


def col_index(category, label, occurrence=0):
    hits = [i for i, (c, l) in enumerate(COLUMNS, start=1) if c == category and l == label]
    return hits[occurrence]


def set_row(ws, r, values: dict):
    """values: {(category, label[, occurrence]): value}"""
    for key, value in values.items():
        if len(key) == 3:
            category, label, occ = key
        else:
            category, label = key
            occ = 0
        ws.cell(r, col_index(category, label, occ), value)


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

    # ------------------------------------------------------------------
    # PD000101: 평택 P4 3F - CVD 장비 A동
    # ------------------------------------------------------------------
    set_row(ws, r, {
        ("UTILITY", "위치"): "평택", ("UTILITY", "라인"): "P4", ("UTILITY", "층"): "3F",
        ("UTILITY", "건설코드"): "PD000101", ("UTILITY", "설비대수"): 1,
        ("GAS/AIR", "설비모듈", 0): "SCRUBBER", ("GAS/AIR", "유량"): 9, ("GAS/AIR", "성상명"): "N2",
        ("GAS/AIR", "배관수량", 0): 1, ("GAS/AIR", "배관수량", 1): 1, ("GAS/AIR", "압력"): 3.5, ("GAS/AIR", "배관재질"): "SUS316L",
        ("POWER", "전력값"): 45, ("POWER", "설비모듈"): "MAIN", ("POWER", "부하전류"): 68, ("POWER", "전압"): 380,
        ("POWER", "차단기전류"): 100, ("POWER", "전원종류"): "AC",
        ("EXHAUST", "풍량"): 12, ("EXHAUST", "설비모듈"): "MAIN", ("EXHAUST", "성상명"): "FUME", ("EXHAUST", "포트 수량"): 2,
        ("SPECIALITY GAS", "배관수량"): 1, ("SPECIALITY GAS", "설비모듈"): "GAS CABINET", ("SPECIALITY GAS", "유량"): 2, ("SPECIALITY GAS", "자재명"): "SiH4",
        ("WATER", "성상명"): "PCW", ("WATER", "설비모듈"): "MAIN", ("WATER", "배관수량"): 2, ("WATER", "유량"): 40, ("WATER", "압력"): 5,
        ("CHEMICAL", "실사용량"): 120, ("CHEMICAL", "성상명"): "IPA",
        ("UPW", "실사용량"): 8.5, ("UPW", "설비모듈"): "MAIN", ("UPW", "성상명"): "HOT DI",
        ("폐액", "자재명"): "산폐액", ("폐액", "실사용량"): 2.4,
        ("WASTER WATER", "성상명"): "IWW1", ("WASTER WATER", "유량"): 25, ("WASTER WATER", "설비모듈"): "MAIN", ("WASTER WATER", "배관수량"): 1,
    })
    r += 1

    # 같은 건설코드, 두 번째 가스: O2 8 SLPM (기준 6 초과 -> OVER 데모)
    set_row(ws, r, {
        ("GAS/AIR", "설비모듈", 0): "SCRUBBER", ("GAS/AIR", "유량"): 8, ("GAS/AIR", "성상명"): "O2",
        ("GAS/AIR", "배관수량", 0): 1, ("GAS/AIR", "배관수량", 1): 0, ("GAS/AIR", "압력"): 3.0, ("GAS/AIR", "배관재질"): "SUS316L",
        ("POWER", "전력값"): 15, ("POWER", "설비모듈"): "SUB", ("POWER", "부하전류"): 22, ("POWER", "전압"): 220,
        ("POWER", "차단기전류"): 30, ("POWER", "전원종류"): "AC",
        ("UPW", "실사용량"): 3.2, ("UPW", "설비모듈"): "MAIN", ("UPW", "성상명"): "COOL DI",
        ("WASTER WATER", "성상명"): "IWW2", ("WASTER WATER", "유량"): 10, ("WASTER WATER", "설비모듈"): "MAIN", ("WASTER WATER", "배관수량"): 1,
    })
    r += 1

    # 세 번째 가스: CDA 6 SLPM (기준 15, 정상), + DC 전원, + UPW 고압DI
    set_row(ws, r, {
        ("GAS/AIR", "설비모듈", 0): "SCRUBBER", ("GAS/AIR", "유량"): 6, ("GAS/AIR", "성상명"): "CDA",
        ("GAS/AIR", "배관수량", 0): 1, ("GAS/AIR", "배관수량", 1): 1, ("GAS/AIR", "압력"): 4.0, ("GAS/AIR", "배관재질"): "SUS316L",
        ("POWER", "전력값"): 5, ("POWER", "설비모듈"): "MAIN", ("POWER", "부하전류"): 8, ("POWER", "전압"): 24,
        ("POWER", "차단기전류"): 10, ("POWER", "전원종류"): "DC",
        ("UPW", "실사용량"): 1.1, ("UPW", "설비모듈"): "MAIN", ("UPW", "성상명"): "고압 DI",
        ("SPECIALITY GAS", "배관수량"): 1, ("SPECIALITY GAS", "설비모듈"): "GAS CABINET", ("SPECIALITY GAS", "유량"): 1, ("SPECIALITY GAS", "자재명"): "PH3",
    })
    r += 1

    # 네 번째 가스: 성상명 표기가 표준(N2/O2/AR/CDA/HE/H2)을 안 따름 -> 표준화 WARN 데모
    set_row(ws, r, {
        ("GAS/AIR", "설비모듈", 0): "SCRUBBER", ("GAS/AIR", "유량"): 4, ("GAS/AIR", "성상명"): "질소",
        ("GAS/AIR", "배관수량", 0): 1, ("GAS/AIR", "배관수량", 1): 1, ("GAS/AIR", "압력"): 3.2, ("GAS/AIR", "배관재질"): "SUS316L",
    })
    r += 1

    r += 1  # 그룹 사이 여백

    # ------------------------------------------------------------------
    # PD000102: 평택 P4 4F - ETCH 장비 B동 (모두 기준 이내 -> 정상 데모)
    # ------------------------------------------------------------------
    set_row(ws, r, {
        ("UTILITY", "위치"): "평택", ("UTILITY", "라인"): "P4", ("UTILITY", "층"): "4F",
        ("UTILITY", "건설코드"): "PD000102", ("UTILITY", "설비대수"): 2,
        ("GAS/AIR", "설비모듈", 0): "SCRUBBER", ("GAS/AIR", "유량"): 7, ("GAS/AIR", "성상명"): "AR",
        ("GAS/AIR", "배관수량", 0): 2, ("GAS/AIR", "배관수량", 1): 1, ("GAS/AIR", "압력"): 3.8, ("GAS/AIR", "배관재질"): "SUS316L",
        ("POWER", "전력값"): 60, ("POWER", "설비모듈"): "MAIN", ("POWER", "부하전류"): 90, ("POWER", "전압"): 380,
        ("POWER", "차단기전류"): 125, ("POWER", "전원종류"): "AC",
        ("EXHAUST", "풍량"): 15, ("EXHAUST", "설비모듈"): "MAIN", ("EXHAUST", "성상명"): "VOC", ("EXHAUST", "포트 수량"): 3,
        ("WATER", "성상명"): "PCW", ("WATER", "설비모듈"): "MAIN", ("WATER", "배관수량"): 3, ("WATER", "유량"): 35, ("WATER", "압력"): 5.5,
        ("CHEMICAL", "실사용량"): 80, ("CHEMICAL", "성상명"): "황산",
        ("UPW", "실사용량"): 6.0, ("UPW", "설비모듈"): "MAIN", ("UPW", "성상명"): "HOT DI",
        ("폐액", "자재명"): "산폐액", ("폐액", "실사용량"): 1.8,
        ("WASTER WATER", "성상명"): "AKWW", ("WASTER WATER", "유량"): 18, ("WASTER WATER", "설비모듈"): "MAIN", ("WASTER WATER", "배관수량"): 1,
    })
    r += 1

    set_row(ws, r, {
        ("GAS/AIR", "설비모듈", 0): "SCRUBBER", ("GAS/AIR", "유량"): 5, ("GAS/AIR", "성상명"): "H2",
        ("GAS/AIR", "배관수량", 0): 1, ("GAS/AIR", "배관수량", 1): 1, ("GAS/AIR", "압력"): 3.0, ("GAS/AIR", "배관재질"): "SUS316L",
        ("SPECIALITY GAS", "배관수량"): 1, ("SPECIALITY GAS", "설비모듈"): "GAS CABINET", ("SPECIALITY GAS", "유량"): 1, ("SPECIALITY GAS", "자재명"): "WF6",
    })
    r += 1

    ws.freeze_panes = "A3"
    for col_idx in range(1, len(COLUMNS) + 1):
        ws.column_dimensions[ws.cell(1, col_idx).column_letter].width = 12

    return wb


if __name__ == "__main__":
    out_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent / "demo_spec_sheet.xlsx"
    wb = build()
    wb.save(out_path)
    print(f"saved: {out_path}")
