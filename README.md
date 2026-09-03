# 반도체 제원(사양) 질의응답/검증 플랫폼

반도체 공장 생산장비의 **제원(스펙) 엑셀표**가 올바른지(유량 OVER, 성상값 미표준화 등)를
자동 규칙으로 1차 검증하고, **설계사가 질의를 올리면 대공정별/공종별 담당자가 답변·승인하는
역할 기반 질의응답**으로 확인/수정하며, 그 이력을 DB로 누적 관리해 향후 **자동 제원 수정**으로
발전시키는 것을 목표로 하는 플랫폼입니다.

- 백엔드: Python **FastAPI** + SQLAlchemy (SQLite 기본, `DATABASE_URL`로 교체 가능)
- 프론트엔드: **React** (Vite)
- 현재 단계: 로그인 없이 화면에서 "현재 작업자"만 선택하는 데모 인증 (역할: 관리자/기술팀 담당자/설계사)

## 로드맵과 현재 구현 범위

| 단계 | 내용 | 상태 |
|---|---|---|
| 1 | 엑셀 제원표 업로드/보존, 대공정·건설코드·설비모듈 분류 | ✅ 구현 (업로드는 관리자 전용) |
| 1 | 규칙 기반 자동 검증 (플러그인 엔진) | ✅ 구현 (성상별 유량 OVER, 성상명 표준화 별칭 규칙 포함, 기본 규칙 자동 시드) |
| 1 | 대분류별 제원 총량 집계 + GCS 종수 | ✅ 구현 (POWER/WATER/UPW/CHEMICAL/GAS·AIR/SPECIALITY GAS/폐액/WASTE WATER/EXHAUST) |
| 1 | 역할 기반(관리자/기술팀/설계사) 질의응답 — 자동/수동 2트랙 승인 워크플로우 | ✅ 구현 |
| 1 | 담당자별 제원 SUMMARY 대시보드 | ✅ 구현 |
| 1 | Q&A로 반영된 수정 이력 축적 | ✅ 구현 (`SpecCorrection` 테이블) |
| 2 | Q&A 이력 기반 **자동 제원 수정 제안/반영** | 🔜 자동 질의(AUTO) 트랙으로 1차 구현, 고도화는 진행 중 |

## 엑셀 헤더 구조 (실제 예시 반영)

실제 제원표 헤더 예시를 받아 확인한 구조는 다음과 같습니다.

- **1행 = 대분류** (UTILITY / GAS·AIR / POWER / EXHAUST / SPECIALITY GAS / WATER / CHEMICAL / UPW / 폐액 / WASTE WATER ...)
- **2행 = 세부 항목** — UTILITY 대분류 아래 공통 항목(위치/라인/층/대공정/PRC/MODEL/MAKER/건설코드/설비대수 —
  PRC=장비 버전, MODEL=모델명, MAKER=제조사)과, 대분류마다 반복되는 항목(유량/성상명/압력/배관수량/배관재질/
  설비모듈/전력값/부하전류/전압 등)
- **3행~ = 데이터** — 같은 사이트(건설코드)가 여러 행에 걸쳐 나올 수 있고, 건설코드 셀은 그룹의 첫 행에만
  채워지고 그 아래 행은 비어 있는 "carry-down" 관례를 따릅니다.

대공정/건설코드/설비모듈 3개 분류축 중 대공정은 업로드 시에도 지정하지만(담당자 배정용
메타데이터), UTILITY 공통 항목에 **"대공정" 열**도 있어서 시트 데이터 자체에도 같은 값이
기록됩니다(업로드 시 선택값과 시트 값이 다르면 교차 확인에 쓸 수 있음). **건설코드와
설비모듈은 시트 데이터에서 직접 읽습니다.** 특히 설비모듈은 대분류마다 별도 열로 존재하므로
(GAS·AIR용 설비모듈, POWER용 설비모듈 ...) 제원표 전체의 단일 값이 아닙니다.

`backend/app/services/excel_import.py`의 `parse_grouped_excel()`이 이 구조의 기본 파서입니다:

- 각 열의 field_name은 `대분류_세부항목` 형태로 조합됩니다 (예: `GAS/AIR_유량`, `UPW_성상명`).
  공통 항목(위치/라인/층/대공정/PRC/MODEL/MAKER/건설코드/설비대수)은 대분류 접두어 없이 그대로 사용합니다.
- **건설코드 값을 기준으로 행을 자동 그룹핑**해서, 건설코드 1개당 SpecSheet(제원표) 1건을 생성합니다.
  업로드 화면(`/upload`)에서 엑셀 1개를 올리면 여러 건설코드가 섞여 있는 경우 여러 제원표가 한 번에
  생성될 수 있습니다.
- 건설코드가 비어 있는 행은 바로 위 행의 건설코드로 이어받습니다(carry-down). 파일 전체에 건설코드가
  하나도 없으면 업로드 화면의 "건설코드 대체값"으로 지정할 수 있습니다.
- **헤더 행 번호(대분류/세부항목/데이터 시작)를 지정하지 않으면 자동으로 인식합니다** —
  `_detect_header_rows()`가 알려진 라벨(공통 항목 + 관찰된 세부항목 이름)과 가장 많이 일치하는 행을
  찾습니다. 제목행이 하나 더 있거나 헤더가 몇 칸 밀린 파일도 대체로 알아서 처리하고, 확신이 낮을 때만
  경고를 남깁니다. 물론 직접 행 번호를 지정하면 그 값이 우선합니다.
- **한 엑셀에 대공정이 여러 개 섞여 들어와도 처리합니다** — 대공정별로 파일이 따로 오는 경우(업로드 시
  선택한 대공정을 그대로 적용)와, 한 파일에 여러 대공정 행이 섞여 오는 경우(시트의 "대공정" 열 값을
  건설코드 그룹마다 읽어서 실제 대공정을 판별, 이 값도 건설코드처럼 carry-down 허용) 둘 다 지원합니다.
  값이 대소문자/공백만 다르거나 등록된 대공정 이름·코드와 일치하면 자동 매칭되고, 인식하지 못하는
  표기는 업로드 시 선택한 대공정으로 대체하면서 경고를 남깁니다.
- 원본 레이아웃(대분류/세부항목 헤더 2행 포함)은 항상 셀 좌표 그대로 `SpecField`에 보존되므로 CAD 형태
  그대로 다시 내보낼 수 있습니다.
- 다른 형식의 파일이 들어올 경우를 대비해, 기존 "라벨 열 / 값 열 / 단위 열" 단순 파서(`parse_excel`)도
  업로드 화면에서 "단순 표" 모드로 선택해 계속 쓸 수 있습니다.

이 정도 변형(헤더 위치, 대공정 혼재)은 자동으로 흡수하지만, 완전히 다른 표 구조(대분류 행 자체가 없는
표, 세로형 레이아웃 등)까지 알아서 알아내지는 못합니다 — 그런 경우 "단순 표" 모드를 쓰거나
`parse_grouped_excel()`에 파싱 로직을 추가해야 합니다.

## 검증 규칙 (플러그인 엔진)

`backend/app/services/rules/`: `base.py`의 `@register("규칙타입키")` 데코레이터로 규칙 함수를
등록하는 구조입니다. 규칙은 DB(`ValidationRule`)에 저장되므로 재배포 없이 대공정/설비모듈별로
다르게 운영할 수 있고, 화면의 "검증 규칙"(`/rules`) 메뉴에서 등록·수정·삭제합니다.

- `max_value_rule.py` — 수치 상한/하한 (전역 단일 기준)
- `standardized_enum_rule.py` — 허용값 목록 검증 (예: 성상값 표준화)
- `max_value_by_group_rule.py` — **성상(가스 종류)별로 다른 상한값**을 적용하는 유량 OVER 검사.
  "유량 OVER 기준이 성상마다 다르다(N2 10 SLPM, O2 6 SLPM, Ar 12 SLPM 등)"는 요청에 맞춰 추가했습니다.
  검사 대상 필드(`GAS/AIR_유량`)와 같은 행의 `GAS/AIR_성상명` 값을 찾아(`RuleContext.sibling()`)
  그 값에 해당하는 기준을 적용합니다. `params.thresholds`에 성상별 기준을 딕셔너리로 지정합니다.

`app/seed.py`의 `DEFAULT_VALIDATION_RULES`에 기본값(N2=10, O2=6, Ar=12, CDA=15, He=8, H2=6 SLPM)을
넣어뒀습니다 — DB가 완전히 비어있는 최초 실행 시에만 자동으로 심어지고, 이후로는 화면에서 자유롭게
수정/삭제할 수 있습니다. **실제 기준값은 이 예시일 뿐이니 확정된 값으로 교체해 주세요.**

실제 검증 로직을 더 받으면 같은 패턴으로 새 파일을 추가하고 `rules/__init__.py`에 import만
추가하면 됩니다.

## 제원 총량 집계

`backend/app/services/aggregation.py`: 업로드된 제원표(건설코드 1건) 안에서 대분류(성상군)별로
아래 로직에 따라 총량을 계산합니다. 대분류+행(row_index) 하나를 아이템 한 건으로 보고, 아이템의
그룹 필드(성상명/전원종류/자재명)로 묶어서 합산합니다.

| 대분류 | 그룹 기준 | 계산식 | 단위 |
|---|---|---|---|
| POWER | 전원종류 | SUM(전력값) | KW |
| WATER | 성상명 | SUM(유량 × 배관수량) | SLPM |
| WASTE WATER | 성상명 | SUM(유량 × 배관수량) | SLPM |
| UPW | 성상명 | SUM(실사용량) | TON/DAY |
| CHEMICAL | 자재명(없으면 성상명) | SUM(실사용량) | LITER/DAY |
| GAS/AIR | 성상명 | SUM(배관수량 × 유량) | SLPM |
| SPECIALITY GAS | 자재명 | SUM(배관수량) | EA |
| 폐액 | 자재명 | SUM(실사용량) | TON/DAY |
| EXHAUST | 성상명 | SUM(포트 수량 × 풍량) | CMM |

`GET /api/spec-sheets/{id}/aggregation`으로 조회하고, 제원표 상세 화면(`/spec-sheets/:id`)의
"제원 총량 집계" 패널에 표시됩니다. 실제 헤더 샘플에서 한 대분류 안에 같은 라벨(예: GAS/AIR의
"배관수량")이 두 열 존재하는 경우가 있어, 같은 행·같은 라벨 값은 모두 더한 뒤 계산에 사용합니다.

## 데모 데이터

`backend/scripts/generate_demo_data.py`가 그럴듯한 값을 채운 데모 엑셀을 생성합니다. 실제 현장
관례에 맞춰 **대공정별로 시트(엑셀 탭)를 따로** 만들고(시드된 13개 대공정 전부, 탭 이름 = 대공정
이름), **시트 1개당 100~150행 규모**로 채웁니다. 각 시트는 다음 규칙을 따릅니다:

- UTILITY에 **"대공정" 열**을 추가 — 값은 그 시트의 대공정 이름과 동일 (업로드 시 선택값과의
  교차 확인용)
- UTILITY의 설비대수는 항상 1
- **라인은 전부 P4**, **층은 3F/4F/5F 중에서 다양하게** 섞음 (위치는 평택/화성)
- UTILITY에 **PRC(장비 버전)/MODEL(모델명)/MAKER(제조사)** 열을 추가 — 건설코드 그룹(장비 한 대)
  단위로 하나씩 정해서 그 그룹의 모든 행에 동일하게 적용 (PRC: V1.0~V3.0, MAKER: AMAT/Lam
  Research/TEL/ASML/KLA/Hitachi High-Tech/ASM International/Veeco, MODEL: 제조사 약어+숫자로
  합성한 모델 코드)
- MAIN 설비와 거기 붙는 부대설비는 같은 "가족"이지만 서로 다른 건설코드를 씀 — 예:
  `PD339007-01`(MAIN) / `PD339007-02`(부대설비)처럼 접미사로 구분되고, 건설코드 1개당 제원표
  1건이 생성되므로 시트 1개(100~150행)가 업로드되면 제원표 30여 건으로 자동 분리됨
- 성상명/자재명은 전부 영어 표기이고 카테고리별로 7~8종류를 무작위로 섞어 씀
  (GAS/AIR: N2/O2/AR/CDA/HE/H2 + 비표준 표기 GN2/LN2, WATER: PCW/RCW/RO/CW/HW/SW/FW/DW,
  CHEMICAL: IPA/SULFURIC ACID/HYDROFLUORIC ACID 등 8종, 폐액: ACID WASTE 등 8종,
  WASTE WATER: IWW1~3/AKWW/ARWW/ORWW/FWW/CWW, SPECIALITY GAS: SiH4/PH3/WF6 등 8종).
  단 **UPW의 성상명(HOT DI/COOL DI/HIGH DI)과 POWER의 전원종류(NOR/UPS)는 지정된 값이 전부라
  그대로 고정**
- EXHAUST의 성상명은 PFC/DE-PFC/ACID/ALKALI/GDM/HEAT-GEN/RECOVERY 중에서만 사용
- 한 번 작성된 행은 UTILITY 칸(위치/라인/층/대공정/PRC/MODEL/MAKER/건설코드/설비대수)을 전부
  채움 (carry-down으로 빈칸을 남기지 않음)

일부러 성상별 유량 OVER와 GAS/AIR 성상값 미표준화(GN2/LN2) 이슈를 섞어놔서, 업로드하면 기본
검증 규칙이 실제로 잡아내는 걸 볼 수 있습니다. 건설코드에 `-01` 같은 2자리 접미사가 붙을 수 있다는
점은 `CONSTRUCTION_CODE_REGEX`(`backend/app/schemas.py`)에도 반영했습니다.

```bash
cd backend && source .venv/bin/activate
python -m scripts.generate_demo_data demo.xlsx
```

업로드 화면(`/upload`)에서 `sheet_name`에 원하는 대공정 이름(예: `CVD`)을 지정해서 시트 하나씩
올리면 됩니다 (한 번에 한 시트 = 한 대공정).

## 데이터 모델 개요

```
MajorProcess(대공정) ──┬── owners (기술팀 담당자, M:N)
                        └── spec_sheets (제원표)
                              ├── fields (SpecField, 셀 단위, CAD 좌표 보존)
                              └── validation_results (규칙 실행 결과, suggested_value 포함)

Discipline(공종) ──── owners (설계사, M:N)

QAThread(질의 스레드, query_type=AUTO|MANUAL) ──┬── targets (QAThreadTarget, N:M 조인 —
                                                │      spec_field + validation_result 참조,
                                                │      동일 교정을 여러 제원표에 걸쳐 일괄 승인하기 위해
                                                │      스레드가 제원표에 직접 종속되지 않음)
                                                ├── messages (QUESTION/ANSWER/COMMENT)
                                                └── (해결 시) spec_corrections 기록 ← 2단계 학습 데이터
```

- **건설코드**: `P` + 영숫자 7자리(총 8자리) 정규식 검증, 엑셀의 건설코드 열에서 자동 추출
  (`backend/app/schemas.py`의 `CONSTRUCTION_CODE_REGEX` — 실제 규칙 확정 시 한 곳만 수정). 형식이
  안 맞아도 업로드를 막지는 않고 경고만 남깁니다(실데이터가 항상 규칙과 맞으리라는 보장이 없어서).
- **대공정**: PHOTO, CVD, ETCH, METAL, CMP, IMP, DIFF, PMTC, EDS, ANALYSIS, 제조환경설비, 물류자동화, CLN (시드됨) —
  업로드 시 사람이 지정하는 메타데이터이자, UTILITY 공통 항목의 "대공정" 열로 시트 데이터에도 기록됨.
  실제로는 대공정별로 파일(시트)이 따로 있고 시트 1개에 100~150행 규모인 경우가 많음
- **설비모듈**: 대분류(UTILITY/GAS·AIR/POWER...)마다 시트 안에 별도 열로 존재. `SpecSheet.equipment_module`은
  참고용 요약 문자열일 뿐이고, 실제 값은 `SpecField`(예: field_name=`GAS/AIR_설비모듈`)에 저장됩니다.

## 역할 모델과 인증 (데모)

로그인이 아직 없으므로, 프론트엔드 상단에서 "현재 작업자"를 선택하면 모든 API 요청에
`X-User-Id` 헤더로 실려 전달됩니다(`app/deps.py`의 `get_current_owner`). 실제 인증을 붙일
때는 이 의존성만 교체하면 나머지 라우터는 그대로 동작합니다.

담당자(`Owner`)는 셋 중 하나의 역할(`role`)을 가집니다.

- **관리자(ADMIN)** — 모든 데이터를 조회할 수 있고, **제원표 업로드는 관리자만 가능**합니다
  (`require_admin`). 어떤 대공정/공종 검사도 통과하므로(`require_major_process_access`,
  `require_discipline_access`) 모든 질의에 답변·승인할 수 있습니다.
- **기술팀 담당자(TECH_LEAD)** — 하나 이상의 **대공정**(PHOTO/CVD/ETCH...)에 배정되고, 그
  대공정 제원표에 대한 질의에 답변·값 수정·자동 질의 승인을 담당합니다.
- **설계사(DESIGNER)** — 하나 이상의 **공종**(공종배관/HVAC/UPW/전기/건축/SPECIALITY
  GAS/CCSS, `Discipline` 테이블, `app/models.py`의 `DISCIPLINE_SEED`)에 배정되고, 질의를
  등록하고 기술팀 답변/제안값을 승인합니다.

질문 등록이나 조회는 (관리자가 아니어도) 미선택 상태를 포함해 누구나 가능하고, 승인/답변 등
**상태를 바꾸는 액션만** 역할·소속 검사를 받습니다.

## 질의응답(Q&A) 워크플로우 — 자동/수동 2트랙

`QAThread`는 `query_type`으로 두 트랙 중 하나를 가지고, 대상 제원 셀은 `QAThreadTarget`
조인 테이블로 연결됩니다(같은 교정을 여러 제원표에 걸쳐 **일괄 승인**하기 위해 스레드가
제원표에 직접 종속되지 않는 구조입니다).

### 자동 제원 질의 (AUTO)

로직이 명확한 검증 규칙(현재는 `alias_correction` — 비표준 표기를 표준값으로 교정, 예:
GN2/LN2/질소/`N2 GAS` → `N2`)이 `ValidationResult.suggested_value`로 AS-IS→TO-BE를 스스로
계산해두면, `POST /api/qa-threads/generate-auto`가 이를 모아 질의를 생성합니다
(`app/services/auto_query.py`).

- **같은 대공정 + 같은 규칙 + 같은 AS-IS라벨 + 같은 제안값**을 가진 이슈는 하나의 스레드로
  **일괄 묶임**(수백~수천 건이 개별 질의로 쌓이지 않도록) — 대상 제원 셀은 `targets`에 여러 건
  달립니다.
- 이미 생성된 스레드의 대상은 다시 묶이지 않도록 멱등적으로 재생성 가능합니다.
- 기술팀 담당자는 **승인/미승인 버튼 한 번**(`POST /qa-threads/{id}/auto-decision`)으로 끝냅니다.
  승인 시 대상 제원 셀 전체가 TO-BE 값으로 갱신되고, 해당 제원표들을 재검증합니다.

### 수동 제원 질의 (MANUAL)

로직이 없어 설계사가 서술형으로 직접 질의하는 경우입니다. 같은 폼을 쓰되 4단계로 진행됩니다
(`app/routers/qa.py`의 `QAThreadStatus`: `OPEN → TECH_ANSWERED → ANSWER_APPROVED →
VALUE_PROPOSED → RESOLVED`/`REJECTED`):

1. 설계사가 공종을 지정해 질의 등록(`POST /spec-sheets/{id}/qa-threads`)
2. 기술팀이 서술형 답변 등록(`POST /qa-threads/{id}/messages`, role=ANSWER)
3. 설계사가 답변을 승인/반려(`POST /qa-threads/{id}/answer-decision`) — 반려 시 다시 답변 대기로
4. 승인되면 기술팀이 **새 값을 제안**(`POST /qa-threads/{id}/propose-value`) — 이때 기존 검증
   규칙 엔진을 그대로 재사용해(`validate_candidate_value`) 성상명/자재명이 허용값인지, 유량이
   상한을 넘지 않는지 등을 검사하고, 위반 시 제안 자체를 거부합니다(우회 수단 없음)
5. 설계사가 제안값을 최종 승인/반려(`POST /qa-threads/{id}/final-decision`) — 승인 시에만
   실제 `SpecField.value`가 갱신되고 `SpecCorrection`(수정 이력)이 남으며, 해당 제원표를
   재검증합니다

## 제원 SUMMARY 대시보드 · GCS 종수

`GET /api/summary?major_process_id=`(`app/services/aggregation.py`의 `compute_summary`)는
대공정 단위로 제원표 수, 미해결 검증 이슈, 미해결 자동/수동 질의 건수, 대분류별 총량 집계를
한 번에 돌려주고, 프론트엔드 `/summary` 화면에 표시됩니다. 담당자별 자동 필터링은 아래
"자동 필터링(담당자 전환 시)" 항목을 참고하세요.

- **GCS**: SPECIALITY GAS + 폐액(CCSS)을 합쳐 부르는 명칭입니다(`GCS_CATEGORIES` in
  `app/models.py`). 이 둘은 총량보다 **취급하는 자재명의 종수**가 중요한 지표라, 두 대분류의
  자재명을 합쳐 중복 제거한 개수(`gcs_material_count`)를 SUMMARY와 대분류별 집계
  (`distinct_count` 컬럼) 양쪽에 표시합니다.

### 자동 필터링(담당자 전환 시)

상단에서 "현재 작업자"를 바꾸면 대시보드/SUMMARY/질의응답 화면이 **그 담당자의 소속으로
자동 필터링**됩니다 — 기술팀 담당자는 자기 대공정으로, 설계사는 자기 공종으로, 질의응답
화면은 추가로 "미해결만 보기"까지 자동 체크됩니다(기술팀 입장에서 처리할 질의만 보이도록).
필터를 직접 바꾸면 자동 적용은 해제됩니다. (이전에는 담당자를 바꿔도 하단 데이터가 갱신되지
않던 버그가 있었는데, 이 자동 필터링 로직으로 함께 해결했습니다.)

### 대공정↔공종 매핑 (확인 필요)

자동 질의를 생성할 때 대상 필드가 어느 공종 담당 설계사의 검토를 받아야 하는지 추정이
필요한데, 현재는 `app/models.py`의 `CATEGORY_TO_DISCIPLINE_CODE`로 엑셀 대분류(GAS/AIR,
UPW, POWER...)를 공종 코드에 1:1로 단순 매핑해뒀습니다(예: `GAS/AIR → PIPING`,
`POWER → ELECTRIC`, `SPECIALITY GAS → SPECIALITY_GAS`). **실제 현장에서 대분류-공종
대응이 이와 다르거나 대분류 하나가 여러 공종에 걸쳐 있다면 이 매핑을 조정해야 합니다.**

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

- **대시보드** (`/`): 대공정/상태별 제원표 목록, 미해결 이슈 건수 (기술팀 담당자로 전환 시 자기
  대공정으로 자동 필터링)
- **SUMMARY** (`/summary`): 담당자(대공정)별 제원 총량 집계 + 미해결 이슈/자동·수동 질의 건수 +
  GCS 종수를 한 장으로 표시
- **질의응답 관리** (`/queries`): 자동/수동 질의 목록 + 상세(AS-IS/TO-BE 대상 테이블, 메시지 로그,
  단계별 승인 폼). "자동 질의 일괄 생성" 버튼으로 `generate-auto` 호출. 기술팀/설계사로 전환 시
  자기 소속 + 미해결만 자동 필터링. 제원표 상세 화면의 질의 카드에서 `?thread=<id>`로 딥링크됨
- **제원표 업로드** (`/upload`, **관리자 전용**): 대공정 지정 후 엑셀 업로드. 기본 모드는 건설코드를
  시트에서 자동 추출해 건설코드별로 제원표를 나눠 생성하며, 다른 형식 파일을 위한 "단순 표" 모드도
  선택 가능
- **제원표 상세** (`/spec-sheets/:id`): CAD 레이아웃 그대로의 셀 그리드(이슈 셀 색상 표시),
  규칙 검증 실행, 이슈/셀에서 바로 수동 질의 등록(공종 지정), Q&A 스레드는 `/queries`로 이동해
  처리, 엑셀 재출력(색상 하이라이트)
- **검증 규칙** (`/rules`): 대공정/설비모듈/필드명 패턴별 규칙 등록·관리
- **담당자 관리** (`/owners`): 역할(관리자/기술팀/설계사) 지정 + 역할에 맞는 대공정(기술팀) 또는
  공종(설계사) 배정 (업로드와 달리 이 화면 자체는 관리자 전용으로 잠겨있지 않습니다 — 실제 인증
  도입 시 함께 검토해 주세요)
- **수정 이력** (`/corrections`): Q&A로 반영된 수정 이력 (2단계 자동화의 데이터 소스)

REST API 전체 목록은 백엔드 실행 후 `http://localhost:8000/docs` (Swagger UI)에서 확인할 수 있습니다.

## 클라우드 데모

`demo/` 폴더에 이 백엔드와 같은 검증·집계 로직을 브라우저에서 재현한 단일 HTML 데모(Claude
Artifact로 배포됨)의 소스를 보관합니다. 자세한 내용과 링크는 `demo/README.md` 참고.

## 다음 단계 제안

1. 실제 검증 로직 전달 → `services/rules/`에 규칙 함수 추가
2. 대공정마다 헤더 구조가 다르면(공정별로 다른 대분류/세부항목 구성) 공유해 주시면 파서에 반영
3. 실제 사내 인증(SSO 등) 연동 → `app/deps.py`의 `get_current_owner` 교체
4. `spec_corrections` 데이터가 충분히 쌓이면, 자동 제원 수정 제안(2단계) 설계 착수
