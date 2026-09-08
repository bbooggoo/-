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
