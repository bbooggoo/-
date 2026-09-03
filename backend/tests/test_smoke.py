"""
핵심 플로우 end-to-end 스모크 테스트:
업로드 -> 셀 파싱 -> 검증 규칙 실행(유량 OVER / 성상값 표준화) -> 이슈로부터 QA 스레드 생성
-> 담당자 아닌 사용자의 답변 거부(403) -> 담당자 답변/해결 -> SpecCorrection 기록 -> 엑셀 재출력.

실행: (backend/ 에서) pip install -r requirements-dev.txt && pytest
"""
from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from openpyxl import Workbook


@pytest.fixture()
def client(monkeypatch, tmp_path):
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


def _make_excel():
    wb = Workbook()
    ws = wb.active
    ws["A1"] = "유량"
    ws["B1"] = 150
    ws["C1"] = "LPM"
    ws["A2"] = "성상"
    ws["B2"] = "기체"
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
            "field_name_pattern": "성상",
            "params": {"allowed_values": ["GAS", "LIQUID", "SOLID"]},
            "severity": "WARN",
            "active": True,
        },
    )

    upload_res = client.post(
        "/api/spec-sheets/upload",
        data={
            "major_process_id": cvd["id"],
            "construction_code": "PD000001",
            "equipment_module": "GAS",
            "header_row": 1,
            "label_col": 1,
            "value_col": 2,
            "unit_col": 3,
        },
        files={"file": ("spec.xlsx", _make_excel(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert upload_res.status_code == 200
    sheet_id = upload_res.json()["id"]

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


def test_invalid_construction_code_rejected(client):
    mps = client.get("/api/major-processes").json()
    cvd = next(m for m in mps if m["code"] == "CVD")
    res = client.post(
        "/api/spec-sheets/upload",
        data={
            "major_process_id": cvd["id"],
            "construction_code": "XD000001",
            "equipment_module": "GAS",
        },
        files={"file": ("spec.xlsx", _make_excel(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert res.status_code == 400
