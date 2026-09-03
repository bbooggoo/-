# 클라우드 데모 (Artifact)

`wafer-spec-console.html`은 백엔드의 검증 로직(`backend/app/services/rules/max_value_by_group_rule.py`)과
집계 로직(`backend/app/services/aggregation.py`)을 브라우저에서 그대로 재현한 단일 HTML 데모입니다.
FastAPI 백엔드가 아니라 Claude Artifact(정적 페이지 + 실시간 공유 저장소 `db` 캐패빌리티)로 배포되어
로그인/설치 없이 링크만으로 열어볼 수 있습니다.

- 배포 링크: https://claude.ai/code/artifact/bff7ce68-9ec0-4b6e-a8fc-1569d3cd9c18
- 질의응답/수정 이력은 Artifact의 `db` 캐패빌리티(실시간 공유 문서 저장소)에 기록되어, 새로고침하거나
  다른 사람이 열어도 유지됩니다. 저장소에 연결하지 못하면 이 브라우저 세션에서만 유지되는 로컬 모드로
  자동 전환됩니다.
- 이 파일을 수정한 뒤 다시 배포하려면 Artifact 퍼블리시 도구로 같은 URL에 재배포하면 됩니다
  (이 리포지토리 자체에는 배포 기능이 없고, 이 파일은 소스 보관 + 재현용입니다).

데모에 쓰인 값은 `backend/scripts/generate_demo_data.py`가 만드는 실제 업로드용 엑셀과 동일한 수치를
쓰도록 맞춰뒀습니다 (둘 중 하나를 바꾸면 다른 쪽도 함께 맞춰주세요).
