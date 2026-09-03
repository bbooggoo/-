# 반도체 제원(사양) 질의응답/검증 플랫폼

반도체 공장 생산장비의 **제원(스펙) 엑셀표**가 올바른지(유량 OVER, 성상값 미표준화 등)를
자동 규칙으로 1차 검증하고, 대공정별 담당자가 **질의응답**으로 확인/수정하며, 그 이력을
쌓아 향후 **자동 제원 수정**으로 발전시키는 것을 목표로 하는 플랫폼입니다.

- 백엔드: Python **FastAPI** + SQLAlchemy (SQLite 기본, `DATABASE_URL`로 교체 가능)
- 프론트엔드: **React** (Vite)
- 현재 단계: 로그인 없이 화면에서 "현재 작업자"만 선택하는 데모 인증

## 로드맵과 현재 구현 범위

| 단계 | 내용 | 상태 |
|---|---|---|
| 1 | 엑셀 제원표 업로드/보존, 대공정·건설코드·설비모듈 분류 | ✅ 구현 |
| 1 | 규칙 기반 자동 검증 (플러그인 엔진) | ✅ 뼈대 구현 (예시 규칙 2종) |
| 1 | 대공정별 담당자 배정 + 질의응답(Q&A) | ✅ 구현 |
| 1 | Q&A로 반영된 수정 이력 축적 | ✅ 구현 (`SpecCorrection` 테이블) |
| 2 | Q&A 이력 기반 **자동 제원 수정 제안/반영** | 🔜 데이터만 축적 중 (모델/로직 없음) |

## 아직 안 받은 두 가지 → 확장 포인트로 설계

요청하신 대로 아래 두 가지는 별도로 받기로 하여, 코드를 열어서 바로 끼워 넣을 수 있는
형태로만 뼈대를 잡아뒀습니다.

1. **엑셀 헤더 레이아웃**: `backend/app/services/excel_import.py`
   - 지금은 "라벨 열 / 값 열 / 단위 열"이 반복되는 단순 CAD형 레이아웃을 가정한 파서입니다.
   - 실제 헤더 예시를 주시면 이 파일의 파싱 로직만 교체하면 됩니다. (모든 셀은 좌표(row, col)
     그대로 `SpecField`에 저장되므로 원본 레이아웃은 항상 보존됩니다.)
2. **제원 검증 로직**: `backend/app/services/rules/`
   - `base.py`의 `@register("규칙타입키")` 데코레이터로 규칙 함수를 등록하는 플러그인 구조입니다.
   - 지금은 예시로 `max_value_rule.py`(수치 상한/하한, "유량값 OVER" 대응), `standardized_enum_rule.py`
     (허용값 목록 검증, "성상값 표준화" 대응) 두 개만 있습니다.
   - 실제 로직을 받으면 같은 패턴으로 새 파일을 추가하고 `rules/__init__.py`에 import만 추가하면,
     화면의 "검증 규칙" 메뉴에서 대공정/설비모듈/필드명 패턴별로 바로 등록해서 쓸 수 있습니다.
   - 규칙은 DB에 저장되므로 재배포 없이 대공정별로 다르게 운영할 수 있습니다.

## 데이터 모델 개요

```
MajorProcess(대공정) ──┬── owners (담당자, M:N)
                        └── spec_sheets (제원표)
                              ├── fields (SpecField, 셀 단위, CAD 좌표 보존)
                              ├── validation_results (규칙 실행 결과)
                              └── qa_threads (질의응답 스레드)
                                    ├── messages (QUESTION/ANSWER/COMMENT)
                                    └── (해결 시) spec_corrections 기록 ← 2단계 학습 데이터
```

- **건설코드**: `P` + 영숫자 7자리(총 8자리) 정규식 검증
  (`backend/app/schemas.py`의 `CONSTRUCTION_CODE_REGEX` — 실제 규칙 확정 시 한 곳만 수정)
- **대공정**: PHOTO, CVD, ETCH, METAL, CMP, IMP, DIFF, PMTC, EDS, ANALYSIS, 제조환경설비, 물류자동화, CLN (시드됨)
- **설비모듈**: 자유 입력 (GAS/SCRUBBER/MAIN 등)

## 대공정별 담당자 분리 (데모 인증)

로그인이 아직 없으므로, 프론트엔드 상단에서 "현재 작업자"를 선택하면 모든 API 요청에
`X-User-Id` 헤더로 실려 전달됩니다. 서버는 QA 스레드의 **답변/해결** 요청에 대해서만
"선택된 사용자가 해당 대공정 담당자로 등록되어 있는지"를 검사합니다(`app/deps.py`).
질문 등록이나 조회는 누구나 가능합니다. 실제 인증 붙일 때는 `get_current_owner` 의존성만
교체하면 나머지 라우터는 그대로 동작합니다.

## 실행 방법

### 백엔드

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

최초 실행 시 대공정 시드 데이터가 자동 생성됩니다 (`app/seed.py`).
DB는 기본적으로 `backend/spec_qa.db` (SQLite) 파일에 저장됩니다.

테스트:

```bash
pip install -r requirements-dev.txt
pytest
```

### 프론트엔드

```bash
cd frontend
npm install
npm run dev
```

`http://localhost:5173` 접속 (Vite dev 서버가 `/api`를 8000번 백엔드로 프록시합니다).

## 주요 화면/API

- **대시보드** (`/`): 대공정/상태별 제원표 목록, 미해결 이슈 건수
- **제원표 업로드** (`/upload`): 대공정/건설코드/설비모듈 지정 후 엑셀 업로드
- **제원표 상세** (`/spec-sheets/:id`): CAD 레이아웃 그대로의 셀 그리드(이슈 셀 색상 표시),
  규칙 검증 실행, 이슈에서 바로 질의 등록, Q&A 스레드 답변/해결(담당자만), 엑셀 재출력(색상 하이라이트)
- **검증 규칙** (`/rules`): 대공정/설비모듈/필드명 패턴별 규칙 등록·관리
- **담당자 관리** (`/owners`): 담당자별 대공정 배정
- **수정 이력** (`/corrections`): Q&A로 반영된 수정 이력 (2단계 자동화의 데이터 소스)

REST API 전체 목록은 백엔드 실행 후 `http://localhost:8000/docs` (Swagger UI)에서 확인할 수 있습니다.

## 다음 단계 제안

1. 실제 제원표 엑셀 헤더 예시 전달 → `excel_import.py` 파서 정교화
2. 실제 검증 로직 전달 → `services/rules/`에 규칙 함수 추가
3. 실제 사내 인증(SSO 등) 연동 → `app/deps.py`의 `get_current_owner` 교체
4. `spec_corrections` 데이터가 충분히 쌓이면, 자동 제원 수정 제안(2단계) 설계 착수
