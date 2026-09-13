# 프로젝트 작업 지침

## Artifact ↔ git 동기화 (항상 지킬 것)

`demo/spec-qa-workflow.html`은 Claude Artifact로 배포된 "제원 질의 데스크"
(https://claude.ai/code/artifact/fb3bc871-7c09-439d-88cd-0a6d971ef58c) 의
git 백업본입니다. **이 아티팩트를 수정해서 게시(publish)할 때마다, 같은 세션
안에서 반드시 `demo/spec-qa-workflow.html`도 최신 게시본과 동일하게 동기화하고
커밋·푸시까지 마친다** — "나중에 물어보고 동기화" 하지 않고 항상 그 자리에서
끝낸다.

- 특히 **업무 가이드(업무 프로세스) 관련 변경**은 절대 누락하지 않는다:
  - 질의응답 상태 머신(OPEN/VALUE_PROPOSED/ANSWERED/RESOLVED/REJECTED 등 상태와
    전이 함수: decideAuto/convertAutoToProposal/quickConfirmAsIs/proposeValue/
    proposeChanges/decideFinal/submitNarrativeAnswer/decideNarrativeAnswer 등)
  - 질의 분류 기준(queryNature: SPEC/NON_SPEC 등)
  - "업무 가이드" 탭의 플로우차트(`buildFlowSvg`/`buildNonSpecFlowSvg`,
    `DEFAULT_NODE_LABELS`/`DEFAULT_EDGE_LABELS`)와 단계별 설명
    (`DEFAULT_GUIDE_STEPS`)
  - 위 항목들과 짝을 이루는 필터/통계 로직(`techActionCategory`/
    `designerActionCategory`, `computeGuideStats`)
- 동기화 순서: (1) 로컬 작업 파일을 완성하고 `node --check`로 문법 검증 →
  (2) 라이브 아티팩트 URL로 게시(publish) → (3) 같은 파일을 그대로
  `demo/spec-qa-workflow.html`에 복사 → (4) git commit & push. 세 번째·네 번째
  단계를 빠뜨리고 "다음에 물어보고 하겠다"며 넘어가지 않는다.
- 재배포/재동기화 전에는 아티팩트 게시 규칙상 라이브 버전 전체를 먼저 읽어야
  하므로, 게시 전에 `Artifact` 도구의 `read` 액션으로 현재 게시본을 확인한다.
- `demo/README.md`에 이 아티팩트의 배포 링크와 기능 변경 이력이 정리되어
  있으니, 업무 프로세스가 바뀌면 그 문서도 함께 갱신하는 것을 고려한다(필수는
  아니지만 권장).

## PPT 업데이트 요청 시 (항상 지킬 것)

사용자가 "PPT 업데이트해줘"라고 요청하면(PPT 내용/프롬프트 자체는 사용자가 별도로
전달함), 그 응답에는 반드시 **GIT 저장소에 커밋되는 문서**로 다음을 포함한다:
- 제원 질의 데스크의 각 탭(대시보드/제원 DB/제원표 업로드/제원 수기입력/
  질의응답/SUMMARY/그래프 만들기/검증 결과/업무 가이드 등, 실제 존재하는 탭
  기준)에 있는 기능 설명.
- **업무 가이드 탭의 플로우차트에 대한 설명은 필수로 포함한다** — 절대
  누락하지 않는다.

이 문서는 `demo/README.md`(또는 그에 준하는 신설 문서)에 정리하고 git
commit·push까지 마친다.

- **프로세스(업무 흐름·상태 전이 등 순서가 있는 절차)를 나타내는 내용은 PPT
  안에서 항상 플로우차트(도형+화살표로 그린 시각적 다이어그램)로 표현한다** —
  표나 글머리 기호 목록으로 프로세스 단계를 나열하지 않는다. 표는 비교·항목별
  상세 목록에만 쓴다.
- PPT 파일을 새로 만들거나 갱신했다면, 그 파일의 GitHub 링크를 답변 마지막에
  포함한다(아래 "답변 형식" 참고).

## 코드 변수명 언급 금지 (항상 지킬 것)

사용자에게 보여주는 모든 결과물(대화 답변, PPT, README 등 git에 커밋되는 문서
포함)에는 함수명·변수명·DB 컬렉션명 등 **코드 식별자를 그대로 쓰거나 설명하지
않는다** — 기능/프로세스는 항상 평범한 한국어 업무 용어로 설명한다. (단, 이
CLAUDE.md 자체는 내가 놓치지 말아야 할 코드 위치를 특정하기 위한 내부 작업
지침이므로 예외로, 기존처럼 함수명을 유지한다.)

## 답변 형식 (항상 지킬 것)

모든 답변의 마지막에는 다음 링크를 반드시 포함한다:
- 제원 질의 데스크(Artifact) 링크: https://claude.ai/code/artifact/fb3bc871-7c09-439d-88cd-0a6d971ef58c
- 이 저장소(GitHub) 링크: 작업 중인 브랜치가 있으면 그 브랜치 링크
  (예: https://github.com/bbooggoo/-/tree/<branch>), 없으면 저장소 루트 링크
  (https://github.com/bbooggoo/-)
- **PPT를 업데이트한 세션이라면**, 그 PPT 파일의 GitHub 링크(예:
  `https://github.com/bbooggoo/-/blob/<branch>/demo/<파일명>.pptx`)도 함께
  포함한다.
