"""
그럴듯한 반도체 제원표 데모 엑셀 생성 (대공정별 시트, 시트당 100~150행 규모).

실제 받은 헤더 구조(1행 대분류 / 2행 세부항목)를 그대로 따르고, 사용자 피드백을
반영해 아래 관례로 데이터를 채운다.

  1. UTILITY에 "대공정" 열을 추가. 값은 업로드 시 선택하는 대공정과 같아야 한다
     (시트 데이터 자체에도 기록해서 교차 확인 가능).
  2. 대공정별로 시트(엑셀 탭)가 따로 있고, 시트 1개당 100~150행 규모다. 이 파일은
     app/models.py에 시드된 13개 대공정 각각에 대해 시트 1개씩(총 13개 탭)을 만든다.
  3. UTILITY의 설비대수는 항상 1.
  4. MAIN 설비 + 거기 붙는 부대설비들은 같은 "가족"이지만 서로 다른 건설코드를
     쓴다 (예: PD000102-01 = MAIN, -02/-03 = 부대설비). 시트마다 여러 "가족"이
     반복돼서 100~150행을 채운다.
  5. 성상명/자재명은 전부 영어(또는 화학식) 표기이고, 카테고리별로 7~8종류를
     섞어 쓴다 (GAS/AIR·WATER·CHEMICAL·폐액·WASTE WATER 성상명/자재명,
     SPECIALITY GAS 자재명). 단, UPW의 성상명(HOT DI/COOL DI/HIGH DI)과 POWER의
     전원종류(NOR/UPS)는 사용자가 지정한 값이 전부이므로 그대로 고정.
  6. EXHAUST의 성상명은 PFC/DE-PFC/ACID/ALKALI/GDM/HEAT-GEN/RECOVERY 중에서만 사용.
  7. 행이 한 번 작성되면 그 행의 UTILITY 칸(위치/라인/층/대공정/건설코드/설비대수)은
     모두 채운다 (건설코드 carry-down으로 빈칸을 남기지 않는다).

유량 OVER(성상별 기준 초과)와 표준화 안 된 성상값(GAS/AIR에 가끔 섞이는 비표준 표기)은
의도적으로 남겨서, 시드된 기본 검증 규칙(app/seed.py의 DEFAULT_VALIDATION_RULES)이
실제로 이슈를 잡아내는 걸 보여준다.

실행: (backend/ 에서) python -m scripts.generate_demo_data [출력경로.xlsx] [--rows-min N] [--rows-max N]
"""
import random
import sys
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # backend/ 를 경로에 추가
from app.models import MAJOR_PROCESS_SEED  # noqa: E402

COLUMNS = [
    ("UTILITY", "위치"), ("UTILITY", "라인"), ("UTILITY", "층"), ("UTILITY", "대공정"),
    ("UTILITY", "건설코드"), ("UTILITY", "설비대수"),
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

# ---------------------------------------------------------------------------
# 값 풀 (성상명/자재명은 7~8종류. UPW 성상명/POWER 전원종류는 사용자가 지정한 값이 전부라 고정)
# ---------------------------------------------------------------------------

# GAS/AIR: 표준 6종(검증 규칙의 기준값 딕셔너리와 동일) + 비표준 표기 2종(표준화 WARN 데모용) = 8종
GAS_AIR_STANDARD = ["N2", "O2", "AR", "CDA", "HE", "H2"]
GAS_AIR_NONSTANDARD = ["GN2", "LN2"]
GAS_AIR_POOL = GAS_AIR_STANDARD + GAS_AIR_NONSTANDARD
GAS_MAX = {"N2": 10, "O2": 6, "AR": 12, "CDA": 15, "HE": 8, "H2": 6}  # app/seed.py 기본값과 동일

WATER_POOL = ["PCW", "RCW", "RO", "CW", "HW", "SW", "FW", "DW"]  # 8종
CHEMICAL_POOL = [
    "IPA", "SULFURIC ACID", "HYDROFLUORIC ACID", "PHOSPHORIC ACID",
    "AMMONIA", "HYDROGEN PEROXIDE", "NITRIC ACID", "ACETONE",
]  # 8종
WASTE_LIQUID_POOL = [
    "ACID WASTE", "ALKALI WASTE", "ORGANIC WASTE", "SOLVENT WASTE",
    "FLUORIDE WASTE", "COPPER WASTE", "SLURRY WASTE", "PHOTORESIST WASTE",
]  # 8종
WASTE_WATER_POOL = ["IWW1", "IWW2", "IWW3", "AKWW", "ARWW", "ORWW", "FWW", "CWW"]  # 8종
SPECIALITY_GAS_POOL = ["SiH4", "PH3", "WF6", "B2H6", "AsH3", "GeH4", "NF3", "TEOS"]  # 8종
EXHAUST_POOL = ["PFC", "DE-PFC", "ACID", "ALKALI", "GDM", "HEAT-GEN", "RECOVERY"]  # 7종 (지정받은 그대로)

UPW_POOL = ["HOT DI", "COOL DI", "HIGH DI"]  # 고정 (사용자가 쓴 종류가 전부)
POWER_TYPES = ["NOR", "UPS"]  # 고정 (사용자가 쓴 종류가 전부)

MODULES = ["SCRUBBER", "MAIN", "CONTROLLER", "GAS CABINET"]
MATERIALS = ["SUS316L", "SUS304", "PVC", "PFA"]

SITES = [  # (위치, 라인, 층) - 대공정 인덱스에 따라 순환
    ("평택", "P4", "2F"), ("평택", "P4", "3F"), ("평택", "P4", "4F"),
    ("평택", "P3", "2F"), ("평택", "P3", "3F"), ("화성", "P1", "1F"),
]


def col_index(category, label, occurrence=0):
    hits = [i for i, (c, l) in enumerate(COLUMNS, start=1) if c == category and l == label]
    return hits[occurrence]


def write_row(ws, r, utility, item_values):
    ws.cell(r, col_index("UTILITY", "위치"), utility["위치"])
    ws.cell(r, col_index("UTILITY", "라인"), utility["라인"])
    ws.cell(r, col_index("UTILITY", "층"), utility["층"])
    ws.cell(r, col_index("UTILITY", "대공정"), utility["대공정"])
    ws.cell(r, col_index("UTILITY", "건설코드"), utility["건설코드"])
    ws.cell(r, col_index("UTILITY", "설비대수"), 1)  # 항상 1

    for key, value in item_values.items():
        if len(key) == 3:
            category, label, occ = key
        else:
            category, label = key
            occ = 0
        ws.cell(r, col_index(category, label, occ), value)


# ---------------------------------------------------------------------------
# 아이템(행) 생성기
# ---------------------------------------------------------------------------


def gas_air_item(rng, species):
    max_v = GAS_MAX.get(species)
    flow = rng.randint(2, (max_v + 4) if max_v else 10)  # ~30%가량 기준 초과하도록
    return {
        ("GAS/AIR", "설비모듈"): "SCRUBBER", ("GAS/AIR", "유량"): flow, ("GAS/AIR", "성상명"): species,
        ("GAS/AIR", "배관수량"): rng.randint(1, 3), ("GAS/AIR", "압력"): round(rng.uniform(2.5, 4.5), 1),
        ("GAS/AIR", "배관재질"): rng.choice(MATERIALS),
    }


def power_item(rng, ptype, module):
    power = rng.randint(3, 8) if ptype == "UPS" else rng.randint(20, 80)
    voltage = 24 if ptype == "UPS" else rng.choice([220, 380])
    return {
        ("POWER", "전력값"): power, ("POWER", "설비모듈"): module,
        ("POWER", "부하전류"): round(power * 1.4, 1), ("POWER", "전압"): voltage,
        ("POWER", "차단기전류"): power * 2 + 10, ("POWER", "전원종류"): ptype,
    }


def exhaust_item(rng, species):
    return {
        ("EXHAUST", "풍량"): rng.randint(6, 22), ("EXHAUST", "설비모듈"): rng.choice(["MAIN", "SCRUBBER"]),
        ("EXHAUST", "성상명"): species, ("EXHAUST", "포트 수량"): rng.randint(1, 4),
    }


def speciality_gas_item(rng, material):
    return {
        ("SPECIALITY GAS", "배관수량"): rng.randint(1, 2), ("SPECIALITY GAS", "설비모듈"): "GAS CABINET",
        ("SPECIALITY GAS", "유량"): rng.randint(1, 3), ("SPECIALITY GAS", "자재명"): material,
    }


def water_item(rng, species):
    return {
        ("WATER", "성상명"): species, ("WATER", "설비모듈"): rng.choice(["MAIN", "SCRUBBER"]),
        ("WATER", "배관수량"): rng.randint(1, 3), ("WATER", "유량"): rng.randint(15, 45),
        ("WATER", "압력"): round(rng.uniform(3.5, 6.0), 1),
    }


def chemical_item(rng, species):
    return {("CHEMICAL", "실사용량"): round(rng.uniform(20, 150), 1), ("CHEMICAL", "성상명"): species}


def upw_item(rng, species):
    return {
        ("UPW", "실사용량"): round(rng.uniform(0.5, 10.0), 1), ("UPW", "설비모듈"): "MAIN",
        ("UPW", "성상명"): species,
    }


def waste_liquid_item(rng, material):
    return {("폐액", "자재명"): material, ("폐액", "실사용량"): round(rng.uniform(0.5, 4.0), 1)}


def waste_water_item(rng, species):
    return {
        ("WASTER WATER", "성상명"): species, ("WASTER WATER", "유량"): rng.randint(5, 30),
        ("WASTER WATER", "설비모듈"): "MAIN", ("WASTER WATER", "배관수량"): rng.randint(1, 2),
    }


def build_main_rows(rng):
    """MAIN 설비(챔버 본체): 가스/전원/배기/특수가스."""
    rows = []
    for species in rng.sample(GAS_AIR_POOL, k=rng.randint(2, 4)):
        rows.append(gas_air_item(rng, species))
    rows.append(power_item(rng, "NOR", "MAIN"))
    if rng.random() < 0.5:
        rows.append(power_item(rng, "UPS", "CONTROLLER"))
    rows.append(exhaust_item(rng, rng.choice(EXHAUST_POOL)))
    if rng.random() < 0.7:
        rows.append(speciality_gas_item(rng, rng.choice(SPECIALITY_GAS_POOL)))
    return rows


def build_aux_rows(rng):
    """MAIN에 붙는 부대설비(Water/Chemical/UPW/폐수 스키드 등) - 매번 다른 조합."""
    rows = []
    if rng.random() < 0.7:
        rows.append(water_item(rng, rng.choice(WATER_POOL)))
    if rng.random() < 0.6:
        rows.append(chemical_item(rng, rng.choice(CHEMICAL_POOL)))
    for species in rng.sample(UPW_POOL, k=rng.randint(1, len(UPW_POOL))):
        if rng.random() < 0.7:
            rows.append(upw_item(rng, species))
    if rng.random() < 0.6:
        rows.append(waste_liquid_item(rng, rng.choice(WASTE_LIQUID_POOL)))
    if rng.random() < 0.7:
        rows.append(waste_water_item(rng, rng.choice(WASTE_WATER_POOL)))
    if not rows:  # 최소 1개는 보장
        rows.append(water_item(rng, rng.choice(WATER_POOL)))
    return rows


def build_sheet(ws, major_process_name, rng, target_rows):
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

    site = SITES[rng.randrange(len(SITES))]
    utility_base = {"위치": site[0], "라인": site[1], "층": site[2], "대공정": major_process_name}

    r = 3
    family_no = 1
    code_prefix = f"PD{rng.randint(100000, 899999):06d}"[:8]  # P + 7자리
    code_base_num = int(code_prefix[2:])

    while r - 3 < target_rows:
        code_base = f"PD{(code_base_num + family_no * 10) % 900000 + 100000:06d}"

        # MAIN (-01)
        for items in [build_main_rows(rng) for _ in range(1)]:
            for item in items:
                write_row(ws, r, dict(utility_base, 건설코드=f"{code_base}-01"), item)
                r += 1

        # 부대설비 1~3개 (-02, -03, ...)
        for sub_idx in range(2, rng.randint(3, 5)):
            for item in build_aux_rows(rng):
                write_row(ws, r, dict(utility_base, 건설코드=f"{code_base}-{sub_idx:02d}"), item)
                r += 1

        family_no += 1

    ws.freeze_panes = "A3"
    for col_idx in range(1, len(COLUMNS) + 1):
        ws.column_dimensions[ws.cell(1, col_idx).column_letter].width = 12

    return r - 3  # 실제로 쓰인 데이터 행 수


def build(rows_min=100, rows_max=150, seed=42):
    wb = Workbook()
    wb.remove(wb.active)

    rng_master = random.Random(seed)
    summary = []
    for code, name in MAJOR_PROCESS_SEED:
        ws = wb.create_sheet(title=name[:31])
        sheet_rng = random.Random(rng_master.randint(0, 1_000_000))
        target = sheet_rng.randint(rows_min, rows_max)
        actual = build_sheet(ws, name, sheet_rng, target)
        summary.append((name, actual))

    return wb, summary


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    out_path = Path(args[0]) if args else Path(__file__).parent / "demo_spec_sheet.xlsx"
    wb, summary = build()
    wb.save(out_path)
    print(f"saved: {out_path}")
    for name, count in summary:
        print(f"  - {name}: {count}행")
