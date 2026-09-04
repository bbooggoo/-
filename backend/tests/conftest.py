"""공용 pytest fixture. 테스트마다 격리된 SQLite DB로 앱을 새로 띄운다."""
import sys

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def raw_client(monkeypatch, tmp_path):
    """앱 시작시 seed()가 심는 기본 검증 규칙/관리자 계정이 그대로 남아있는 클라이언트."""
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")

    # database 모듈이 환경변수를 import 시점에 읽으므로 매 테스트마다 재로딩
    for mod in list(sys.modules):
        if mod.startswith("app"):
            del sys.modules[mod]

    from app.main import app

    with TestClient(app) as c:
        # 제원표 업로드가 관리자 전용이 된 뒤로, 대부분의 테스트가 "누군가 업로드해야"
        # 시작되므로 시드된 관리자 계정을 기본 인증으로 걸어둔다. 특정 사용자 권한을
        # 테스트하는 곳(담당자 답변 거부 등)은 그 호출에서 X-User-Id를 직접 넘기면
        # (요청별 헤더가 클라이언트 기본 헤더를 덮어쓰므로) 그대로 의도대로 동작한다.
        admin = c.get("/api/owners").json()[0]
        c.headers["X-User-Id"] = str(admin["id"])
        yield c


@pytest.fixture()
def client(raw_client):
    """기본 시드 검증 규칙을 지워서, 각 테스트가 직접 등록한 규칙만으로 결정적으로 동작하게 한다.
    (시드되는 관리자 계정 등 다른 데이터는 그대로 둔다.)"""
    for rule in raw_client.get("/api/validation-rules").json():
        raw_client.delete(f"/api/validation-rules/{rule['id']}")
    return raw_client
