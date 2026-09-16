# COMPOSITE 플랫폼 소개 PPT 재생성

`build-deck.mjs`는 16장 16:9 편집 가능한 PowerPoint를 생성합니다. 저장소에서는 이 소스를 `docs/presentation/build-deck.mjs`에 두고, 검증한 최종 파일을 `docs/COMPOSITE_Platform_Introduction.pptx`에 반영합니다.

- 업무 담당자 표는 `dist/workflow.mjs`의 7단계, 담당, 입력, 산출물, 상태를 읽습니다.
- BOX 자동 보정은 끊어진 선, 다른 코드 속성란, BOX 밖 코드의 3유형 표와 편집 가능한 6단계 흐름도로 설명합니다. `repairWorkflow`의 상세 설명을 발표자 노트에 포함하며, 잔여 경고와 변경 후 재분석·원본 보존을 명시합니다.
- 설비 샘플 차트는 `dist/engine.mjs`를 실행해 1.0 m 이격 조건의 배치 전후 이슈 수와 이동 설비 수를 계산합니다.
- 컴포짓 후보 표는 `dist/composite-engine.mjs`의 `sampleComposite()`, `inspectComposite()`, `proposeComposite()`를 실행해 이동량, POC 거리 대리지표와 잔여 이슈를 계산합니다. `utMatrix()` 결과도 QA 기록에 저장합니다.
- 삼성전자와 SK하이닉스의 공개 사례, 연구·개발 계획, 플랫폼의 샘플 해석을 구분합니다. 공개 자료의 URL과 근거 성격은 해당 슬라이드의 발표자 노트에 있습니다.
- DWG 업로드·추출·객체 DB·서버 저장, 통합 설계 스튜디오, 생산설비 BOX·인프라 레이어 검수, Bay 편집과 원본/수정값 구분은 실제 UI·서버 구현 및 테스트 결과에 맞춰 갱신합니다. 이 문구와 업무 흐름도는 정적이므로 기능 변경 시 함께 검토해야 합니다.
- 내장 샘플의 자동배치 수치를 실제 업로드 DWG의 처리 성능으로 표현하지 않습니다. DB 편집과 DWG 원본 재기록도 구분합니다.
- 표 11개, 차트 1개, DWG 데이터·BOX 자동 보정·업무 흐름도의 도형과 연결선은 네이티브 PowerPoint 개체입니다.
- 기존 네이비·민트 색상, 1280 × 720 캔버스, 맑은 고딕을 유지합니다. 사진, 래스터 이미지 등 별도 저작 자산은 없습니다.

## 실행 조건

Codex Presentations 스킬과 `load_workspace_dependencies`가 제공한 번들 Node, Python, `@oai/artifact-tool`을 사용합니다. 별도 패키지 설치가 필요하지 않습니다. 새 제작/편집 작업에서는 먼저 해당 스킬의 `mark_artifact_operation_started.mjs` 절차를 따릅니다.

환경 변수 `PRESENTATIONS_SKILL_DIR`, `RUNTIME_PYTHON`, `RUNTIME_NODE_MODULES`를 현재 런타임 경로로 지정하고 다음처럼 실행합니다. 일반 Node 대신 번들 Node 실행 파일을 사용합니다.

```text
<bundled-node> docs/presentation/build-deck.mjs --workspace <private-build-directory> --revision <new-revision>
```

같은 설정은 `--skill-dir`, `--python`, `--node-modules` 인자로 전달할 수 있습니다. `--workspace` 기본값은 소스 옆 `.build` 디렉터리이며 결과는 그 안의 `output/`에 생성됩니다. `--output`으로 결과 파일명을 지정할 경우에도 최종 검증 도구 요구에 따라 `--workspace` 내부 경로를 사용합니다. 이미 있는 최종 파일은 덮어쓰지 않으므로 새 revision 또는 파일명을 지정합니다.

기본 입력 경로는 소스 기준 `../../dist/workflow.mjs`, 그 옆 `engine.mjs`와 `composite-engine.mjs`입니다. `--workflow`, `--engine`, `--composite-engine`으로 변경할 수 있습니다. 참조 디자인과 폰트 검증은 `../COMPOSITE_Platform_Introduction.pptx`를 사용하며 `--reference-deck`으로 변경할 수 있습니다. 스크립트에는 사용자별 Temp 경로나 런타임 절대 경로를 고정하지 않았습니다.

## 검토와 저장소 반영

생성 스크립트는 최종 PPTX를 다시 읽어 `qa/slide-1.png`부터 `slide-16.png`와 개별 layout JSON을 생성합니다. `qa/validation-<revision>.json`에 패키지·폰트·표·차트 검증 결과를 남기고 `qa/sample-evidence-<revision>.json`에 사용한 내장 엔진 계산을 기록합니다. 개별 PNG를 전체 시각 검토의 기준으로 사용합니다.

모든 렌더링을 개별 크기로 확인하고, 표와 연결선의 의도하지 않은 겹침 및 잘림을 수정합니다. `check-rendered-layout.mjs <qa-directory>`는 폴더에 있는 모든 `slide-<number>.layout.json`을 읽어 상위 텍스트 개체·표·차트의 경계를 검사합니다. 렌더링과 파일 구조 검증은 PowerPoint 앱에서 열기·편집·저장 검증을 대신하지 않습니다.

검증한 PPTX를 `docs/COMPOSITE_Platform_Introduction.pptx`로 바이트 변경 없이 복사하고, 재생성 소스 및 필요한 검사 기록을 프로젝트 지침에 따라 커밋합니다.
