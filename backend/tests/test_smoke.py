"""
핵심 플로우 end-to-end 스모크 테스트.

test_end_to_end_flow: 실제 제원표 헤더 구조(대분류/세부항목 2단 헤더 + 건설코드
그룹핑)를 반영한 업로드 -> 셀 파싱 -> 검증 규칙 실행(유량 OVER / 성상값 표준화)
-> 이슈로부터 QA 스레드 생성 -> 담당자 아닌 사용자의 답변 거부(403) -> 담당자
답변/해결 -> SpecCorrection 기록 -> 엑셀 재출력까지 전체 플로우를 검증한다.

test_grouped_upload_splits_by_construction_code: 건설코드가 다른 여러 행이 섞인
파일 하나를 업로드하면 건설코드 단위로 SpecSheet 가 자동으로 나뉘는지 검증한다.

실행: (backend/ 에서) pip install -r requirements-dev.txt && pytest
"""
from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from openpyxl import Workbook


@pytest.fixture()
def raw_client(monkeypatch, tmp_path):
    """앱 시작시 seed()가 심는 기본 검증 규칙이 그대로 남아있는 클라이언트."""
    # 테스트마다 격리된 SQLite 파일 사용
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")

    # database 모듈이 환경변수를 import 시점에 읽으므로 매 테스트마다 재로딩
    import sys

    for mod in list(sys.modules):
        if mod.startswith("app"):
            del sys.modules[mod]

    from app.main import app

    with TestClient(app) as c:
        yield c


@pytest.fixture()
def client(raw_client):
    """기본 시드 규칙을 지워서, 각 테스트가 직접 등록한 규칙만으로 결정적으로 동작하게 한다."""
    for rule in raw_client.get("/api/validation-rules").json():
        raw_client.delete(f"/api/validation-rules/{rule['id']}")
    return raw_client


def _make_grouped_excel(rows: list[dict]):
    """실제 헤더 구조(1행 대분류/2행 세부항목)를 흉내낸 엑셀을 만든다.

    rows: 각 dict는 {"건설코드": ..., "GAS/AIR_유량": ..., "GAS/AIR_성상명": ...} 형태.
    건설코드가 없는(carry-down) 행은 dict에서 "건설코드" 키를 생략하면 된다.
    """
    wb = Workbook()
    ws = wb.active

    columns = [
        ("UTILITY", "위치"),
        ("UTILITY", "라인"),
        ("UTILITY", "건설코드"),
        ("GAS/AIR", "설비모듈"),
        ("GAS/AIR", "유량"),
        ("GAS/AIR", "성상명"),
    ]
    for col_idx, (category, label) in enumerate(columns, start=1):
        ws.cell(1, col_idx, category)
        ws.cell(2, col_idx, label)

    for r, row in enumerate(rows, start=3):
        ws.cell(r, 1, row.get("위치"))
        ws.cell(r, 2, row.get("라인"))
        ws.cell(r, 3, row.get("건설코드"))
        ws.cell(r, 4, row.get("설비모듈"))
        ws.cell(r, 5, row.get("유량"))
        ws.cell(r, 6, row.get("성상명"))

    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf


def _make_multi_category_excel(columns: list[tuple[str, str]], rows: list[dict]):
    """여러 대분류가 섞인 엑셀을 만든다.

    columns: [(대분류, 세부항목), ...] 열 순서 그대로.
    rows: 각 dict의 키는 "대분류_세부항목" (공통 항목은 접두어 없이 "위치" 처럼),
          값이 없는 열은 키를 생략하면 빈 셀로 남는다.
    """
    wb = Workbook()
    ws = wb.active
    for col_idx, (category, label) in enumerate(columns, start=1):
        ws.cell(1, col_idx, category)
        ws.cell(2, col_idx, label)

    common_labels = {"위치", "라인", "층", "건설코드", "설비대수"}
    for r, row in enumerate(rows, start=3):
        for col_idx, (category, label) in enumerate(columns, start=1):
            key = label if label in common_labels else f"{category}_{label}"
            if key in row:
                ws.cell(r, col_idx, row[key])

    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf


def test_end_to_end_flow(client):
    mps = client.get("/api/major-processes").json()
    assert len(mps) == 13
    cvd = next(m for m in mps if m["code"] == "CVD")

    owner = client.post(
        "/api/owners",
        json={"name": "김철수", "email": None, "major_process_ids": [cvd["id"]]},
    ).json()
    outsider = client.post(
        "/api/owners", json={"name": "박영희", "email": None, "major_process_ids": []}
    ).json()

    client.post(
        "/api/validation-rules",
        json={
            "name": "유량 OVER",
            "rule_type": "max_value",
            "major_process_id": cvd["id"],
            "field_name_pattern": "유량|FLOW",
            "params": {"max": 100, "unit": "LPM"},
            "severity": "ERROR",
            "active": True,
        },
    )
    client.post(
        "/api/validation-rules",
        json={
            "name": "성상 표준화",
            "rule_type": "standardized_enum",
            "major_process_id": cvd["id"],
            "field_name_pattern": "성상명",
            "params": {"allowed_values": ["GAS", "LIQUID", "SOLID"]},
            "severity": "WARN",
            "active": True,
        },
    )

    excel = _make_grouped_excel(
        [
            {"위치": "평택", "라인": "P4", "건설코드": "PD000001", "설비모듈": "SCRUBBER", "유량": 150, "성상명": "기체"},
        ]
    )
    upload_res = client.post(
        "/api/spec-sheets/upload",
        data={"major_process_id": cvd["id"], "uploaded_by": "업로더"},
        files={"file": ("spec.xlsx", excel, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert upload_res.status_code == 200
    upload_body = upload_res.json()
    assert upload_body["warnings"] == []
    assert len(upload_body["created"]) == 1
    sheet = upload_body["created"][0]
    assert sheet["construction_code"] == "PD000001"
    assert sheet["equipment_module"] == "GAS/AIR:SCRUBBER"
    field_names = {f["field_name"] for f in sheet["fields"] if f["field_name"]}
    assert "GAS/AIR_유량" in field_names
    assert "GAS/AIR_성상명" in field_names
    sheet_id = sheet["id"]

    detail = client.post(f"/api/spec-sheets/{sheet_id}/validate").json()
    assert detail["open_issue_count"] == 2

    flow_issue = next(r for r in detail["validation_results"] if r["severity"] == "ERROR")

    thread = client.post(
        f"/api/spec-sheets/{sheet_id}/qa-threads",
        json={
            "title": "유량 초과 확인",
            "spec_field_id": flow_issue["spec_field_id"],
            "validation_result_id": flow_issue["id"],
            "question": "150 LPM 맞습니까?",
            "author_name": "검토자",
        },
    ).json()
    assert thread["assigned_owner"]["id"] == owner["id"]  # 대공정 담당자 1명 -> 자동 배정

    # 담당자가 아닌 사용자는 답변 불가 (403)
    forbidden = client.post(
        f"/api/qa-threads/{thread['id']}/messages",
        json={"author_name": "박영희", "role": "ANSWER", "content": "임의 답변"},
        headers={"X-User-Id": str(outsider["id"])},
    )
    assert forbidden.status_code == 403

    ok = client.post(
        f"/api/qa-threads/{thread['id']}/messages",
        json={"author_name": "김철수", "role": "ANSWER", "content": "오기입입니다."},
        headers={"X-User-Id": str(owner["id"])},
    )
    assert ok.status_code == 200

    resolved = client.post(
        f"/api/qa-threads/{thread['id']}/resolve",
        json={"resolver_name": "김철수", "new_value": "100"},
        headers={"X-User-Id": str(owner["id"])},
    ).json()
    assert resolved["status"] == "RESOLVED"

    corrections = client.get("/api/corrections").json()
    assert len(corrections) == 1
    assert corrections[0]["old_value"] == "150"
    assert corrections[0]["new_value"] == "100"

    export_res = client.get(f"/api/spec-sheets/{sheet_id}/export")
    assert export_res.status_code == 200
    assert export_res.headers["content-type"].startswith("application/vnd.openxmlformats")


def test_grouped_upload_splits_by_construction_code(client):
    mps = client.get("/api/major-processes").json()
    cvd = next(m for m in mps if m["code"] == "CVD")

    # 두 번째 그룹은 건설코드가 첫 행에만 있고 다음 행은 carry-down(빈 칸)으로 이어진다.
    excel = _make_grouped_excel(
        [
            {"위치": "평택", "라인": "P4", "건설코드": "PD000001", "유량": 50, "성상명": "GAS"},
            {"위치": "평택", "라인": "P3", "건설코드": "PD000002", "유량": 30, "성상명": "GAS"},
            {"유량": 40, "성상명": "LIQUID"},  # PD000002 그룹에 이어지는 행 (건설코드 carry-down)
        ]
    )
    res = client.post(
        "/api/spec-sheets/upload",
        data={"major_process_id": cvd["id"]},
        files={"file": ("spec.xlsx", excel, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["warnings"] == []
    codes = sorted(s["construction_code"] for s in body["created"])
    assert codes == ["PD000001", "PD000002"]

    pd2 = next(s for s in body["created"] if s["construction_code"] == "PD000002")
    values = sorted(f["value"] for f in pd2["fields"] if f["field_name"] == "GAS/AIR_유량")
    assert values == ["30", "40"]  # carry-down된 세 번째 행도 PD000002 그룹에 포함됨


def test_ungrouped_rows_without_construction_code_are_reported(client):
    mps = client.get("/api/major-processes").json()
    cvd = next(m for m in mps if m["code"] == "CVD")

    excel = _make_grouped_excel([{"위치": "평택", "유량": 10}])  # 건설코드 없음
    res = client.post(
        "/api/spec-sheets/upload",
        data={"major_process_id": cvd["id"]},
        files={"file": ("spec.xlsx", excel, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert res.status_code == 400  # 그룹을 하나도 못 만들면 명확한 에러


def test_construction_code_override_fills_blank_rows(client):
    mps = client.get("/api/major-processes").json()
    cvd = next(m for m in mps if m["code"] == "CVD")

    excel = _make_grouped_excel([{"위치": "평택", "유량": 10}])  # 건설코드 없음
    res = client.post(
        "/api/spec-sheets/upload",
        data={"major_process_id": cvd["id"], "construction_code_override": "PD000009"},
        files={"file": ("spec.xlsx", excel, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert res.status_code == 200
    body = res.json()
    assert len(body["created"]) == 1
    assert body["created"][0]["construction_code"] == "PD000009"


def test_simple_layout_still_works(client):
    mps = client.get("/api/major-processes").json()
    cvd = next(m for m in mps if m["code"] == "CVD")

    wb = Workbook()
    ws = wb.active
    ws["A1"] = "유량"
    ws["B1"] = 80
    ws["C1"] = "LPM"
    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)

    res = client.post(
        "/api/spec-sheets/upload",
        data={
            "major_process_id": cvd["id"],
            "layout": "simple",
            "construction_code": "PD000001",
            "equipment_module": "GAS",
            "header_row": 1,
            "label_col": 1,
            "value_col": 2,
            "unit_col": 3,
        },
        files={"file": ("spec.xlsx", buf, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["created"][0]["equipment_module"] == "GAS"


def test_invalid_construction_code_in_simple_mode_rejected(client):
    mps = client.get("/api/major-processes").json()
    cvd = next(m for m in mps if m["code"] == "CVD")
    wb = Workbook()
    ws = wb.active
    ws["A1"] = "유량"
    ws["B1"] = 80
    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)

    res = client.post(
        "/api/spec-sheets/upload",
        data={
            "major_process_id": cvd["id"],
            "layout": "simple",
            "construction_code": "XD000001",
            "equipment_module": "GAS",
        },
        files={"file": ("spec.xlsx", buf, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert res.status_code == 400


GAS_AIR_COLUMNS = [
    ("UTILITY", "위치"),
    ("UTILITY", "건설코드"),
    ("GAS/AIR", "설비모듈"),
    ("GAS/AIR", "유량"),
    ("GAS/AIR", "성상명"),
    ("GAS/AIR", "배관수량"),
]


def test_seeded_gas_over_rule_uses_per_species_threshold(raw_client):
    """앱 기본 시드 규칙(성상별 유량 OVER 기준)이 성상마다 다른 기준으로 판정하는지 확인.

    시드 기준: N2=10, O2=6, AR=12 (SLPM). N2 12는 초과, O2 5는 정상, AR 20은 초과.
    """
    mps = raw_client.get("/api/major-processes").json()
    cvd = next(m for m in mps if m["code"] == "CVD")

    excel = _make_multi_category_excel(
        GAS_AIR_COLUMNS,
        [
            {"위치": "평택", "건설코드": "PD000001", "GAS/AIR_유량": 12, "GAS/AIR_성상명": "N2"},
            {"GAS/AIR_유량": 5, "GAS/AIR_성상명": "O2"},
            {"GAS/AIR_유량": 20, "GAS/AIR_성상명": "AR"},
        ],
    )
    res = raw_client.post(
        "/api/spec-sheets/upload",
        data={"major_process_id": cvd["id"]},
        files={"file": ("spec.xlsx", excel, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert res.status_code == 200
    sheet_id = res.json()["created"][0]["id"]

    detail = raw_client.post(f"/api/spec-sheets/{sheet_id}/validate").json()
    messages = {r["message"] for r in detail["validation_results"] if r["severity"] == "ERROR"}
    assert any("[N2]" in m and "OVER" in m for m in messages)
    assert any("[AR]" in m and "OVER" in m for m in messages)
    assert not any("[O2]" in m for m in messages)  # 5 SLPM은 O2 기준(6) 이내라 정상


def test_aggregation_matches_hand_calculated_totals(client):
    mps = client.get("/api/major-processes").json()
    mfg = next(m for m in mps if m["code"] == "MFG_ENV")

    columns = [
        ("UTILITY", "위치"),
        ("UTILITY", "건설코드"),
        ("GAS/AIR", "배관수량"),  # 대분류 안에 같은 라벨 열이 중복되는 실제 사례를 재현
        ("GAS/AIR", "유량"),
        ("GAS/AIR", "성상명"),
        ("GAS/AIR", "배관수량"),
        ("POWER", "전력값"),
        ("POWER", "전원종류"),
        ("EXHAUST", "포트 수량"),
        ("EXHAUST", "풍량"),
        ("EXHAUST", "성상명"),
    ]
    rows = [
        # GAS/AIR: N2 - 배관수량 두 열(2 + 3 = 5) * 유량 10 = 50 SLPM
        {"위치": "평택", "건설코드": "PD000001", "GAS/AIR_유량": 10, "GAS/AIR_성상명": "N2"},
        # 같은 컬럼에 두 값을 넣어야 하므로 별도 처리: 아래에서 셀 직접 채움
        # POWER: AC 3KW, DC 2KW, 다음 행에 AC 4KW 추가 -> AC 합계 7KW
        {"POWER_전력값": 3, "POWER_전원종류": "AC"},
        {"POWER_전력값": 2, "POWER_전원종류": "DC"},
        {"POWER_전력값": 4, "POWER_전원종류": "AC"},
        # EXHAUST: FUME 포트수량 2 * 풍량 5 = 10 CMM
        {"EXHAUST_포트 수량": 2, "EXHAUST_풍량": 5, "EXHAUST_성상명": "FUME"},
    ]
    excel = _make_multi_category_excel(columns, rows)

    # 중복된 "GAS/AIR_배관수량" 두 열에 각각 다른 값(2, 3)을 직접 채워넣는다
    # (dict 키가 겹쳐서 _make_multi_category_excel 헬퍼로는 표현 불가하므로 워크북을 직접 조작).
    from openpyxl import load_workbook

    wb = load_workbook(excel)
    ws = wb.active
    ws.cell(3, 3, 2)  # 첫 번째 GAS/AIR_배관수량 열
    ws.cell(3, 6, 3)  # 두 번째 GAS/AIR_배관수량 열
    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)

    res = client.post(
        "/api/spec-sheets/upload",
        data={"major_process_id": mfg["id"]},
        files={"file": ("spec.xlsx", buf, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert res.status_code == 200
    sheet_id = res.json()["created"][0]["id"]

    agg = client.get(f"/api/spec-sheets/{sheet_id}/aggregation").json()
    by_category = {a["category"]: a for a in agg}

    assert by_category["GAS/AIR"]["unit"] == "SLPM"
    assert by_category["GAS/AIR"]["totals"]["N2"] == pytest.approx(50.0)  # (2+3) * 10

    assert by_category["POWER"]["unit"] == "KW"
    assert by_category["POWER"]["totals"]["AC"] == pytest.approx(7.0)  # 3 + 4
    assert by_category["POWER"]["totals"]["DC"] == pytest.approx(2.0)

    assert by_category["EXHAUST"]["unit"] == "CMM"
    assert by_category["EXHAUST"]["totals"]["FUME"] == pytest.approx(10.0)  # 2 * 5
