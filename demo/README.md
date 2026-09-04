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

## 여러 명이 동시에 쓰는 워크플로우 데모 — `spec-qa-workflow.html`

`wafer-spec-console.html`이 검증·집계 로직만 보여주는 정적 미리보기라면, `spec-qa-workflow.html`은
백엔드에 구현된 **역할 기반(관리자/기술팀 담당자/설계사) 질의응답 워크플로우**(자동/수동 2트랙 승인,
SUMMARY 대시보드, GCS 종수, 담당자 전환 시 자동 필터링 등)를 같은 방식(Claude Artifact + `db`
캐패빌리티)으로 브라우저에 재현한, 여러 사람이 동시에 열어 실시간으로 함께 쓰도록 만든 버전입니다.

- 배포 링크: https://claude.ai/code/artifact/fb3bc871-7c09-439d-88cd-0a6d971ef58c
- 같은 조직에 로그인한 사용자 전원이 이 링크로 들어와 상단에서 자기 이름(사용자 관리 화면에서 미리
  등록)을 선택하면, 대시보드/SUMMARY/질의응답 데이터가 그 사람의 역할·담당 대공정(또는 공종)에 맞춰
  자동 필터링되고, 업로드는 관리자 계정에서만 열립니다. 질의 승인/값 수정/제원표 업로드는 모두 Artifact
  의 공유 `db` 저장소에 실시간으로 반영되어 다른 뷰어에게도 즉시 보입니다.
- 실제 FastAPI 백엔드보다 검증 규칙 범위(성상별 유량 OVER, 성상명 표준화·별칭 교정)가 단순화되어 있고
  검증 규칙 CRUD 화면은 없습니다 — 이 프로젝트의 실제 배포판(백엔드+프론트엔드, PR 참고)이 정식
  구현이고, 이 Artifact는 서버 호스팅 없이 여러 명이 같은 워크플로우를 바로 체험/운영해 볼 수 있는
  경량 버전입니다.
- 재배포 방법은 위 `wafer-spec-console.html`과 동일합니다 (Artifact 퍼블리시 도구로 같은 URL에 재배포).
