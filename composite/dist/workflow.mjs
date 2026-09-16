export const drawingSource={format:'DWG',nativeImport:true,nativeExport:false,mode:'실제 DWG 평면 · 서버 객체 DB · 별도 2.5D 예시'};
export const workflow=[
 {id:'receive',number:'01',title:'DWG 수령·추출',status:'구현',owner:'설계 담당 · DWG 엔진',input:'실제 DWG 원본',output:'원본 파일·객체 DB·누락 경고',description:'DWG를 브라우저에서 해석하고 원본과 객체를 서버에 저장합니다. 원시 Handle 대조로 변환 누락을 탐지하며 미완료 저장을 성공으로 처리하지 않습니다.'},
 {id:'normalize',number:'02',title:'레이어·BOX·코드 정리',status:'구현 · 후보 검토',owner:'설계 담당 · 정리 엔진',input:'BOX·인프라 레이어, 건설코드',output:'닫힌 BOX·공통 코드·확인 항목',description:'레이어를 분류하고 작은 선 틈을 허용오차 안에서 연결합니다. 다른 속성란의 건설코드를 통합하고 유일하게 연결되는 외부 문자를 BOX 안으로 옮깁니다. 모호하거나 누락된 코드는 확인 대상으로 남깁니다.'},
 {id:'constraints',number:'03',title:'Bay·검수 기준 설정',status:'구현',owner:'설계 담당',input:'도면 단위·예상 BOX 수·Bay 기준',output:'Bay 경계·인프라 구역·이격 조건',description:'프로젝트의 Bay 경계, 인프라 구역, BOX 최소 이격, 고정 상태를 설정합니다. 삼성전자향으로 구성하지만 공개되지 않은 사내 치수는 기본값으로 단정하지 않습니다.'},
 {id:'inspect',number:'04',title:'평면 검수·간섭 확인',status:'구현 · 2D 범위',owner:'검사 엔진 · 설계 담당',input:'실제 CAD 형상과 현재 기준',output:'단위·누락·BOX·코드·Bay 위반',description:'모델 표시 누락, 레이어 미분류, BOX 수·이격·인동선, Bay 및 인프라 구역을 검사합니다. 실제 배관·덕트 높이 간섭은 포함하지 않습니다.'},
 {id:'layout',number:'05',title:'이동·Bay 배치 제안',status:'구현',owner:'설계 담당 · 배치 엔진',input:'현재 배치와 고정 조건',output:'변경 위치·재검사한 배치 후보',description:'CAD 형상을 직접 끌거나 좌표로 이동합니다. 배치 제안은 고정 객체를 유지하며 Bay와 지정 인프라 구역을 탐색합니다. 제한 탐색이므로 최적해를 보장하지 않습니다.'},
 {id:'review',number:'06',title:'DB 저장·재검수',status:'구현 · 수동 대조',owner:'서버 · 설계 담당',input:'변경안·사유·현재 개정',output:'원본/수정본·변경 이력·검수 기록',description:'개정 충돌을 확인하고 수정값과 사유를 저장합니다. 여러 저장 묶음은 각각 개정을 남깁니다. 원본 도면과 대조한 뒤 조건을 통과한 현재 개정만 검수 완료로 기록합니다.'},
 {id:'issue',number:'07',title:'CAD 반영·도면 발행',status:'연동 예정',owner:'CAD 담당 · 승인자',input:'검토한 변경 DB',output:'개정 DWG·실제 설계 승인',description:'현재 원본 DWG 다운로드만 지원합니다. 수정 DB의 DWG 재기록·현장 승인·도면 발행은 구현하지 않았습니다.'}
];
export const repairWorkflow=[
 {title:'1. 단위·허용오차 확인',description:'도면 단위를 확인한 뒤 선 틈 허용오차, 외부 코드 검색거리, 속성란 별칭을 입력합니다. 값은 프로젝트 기준이며 회사 표준값을 추정하지 않습니다.'},
 {title:'2. 끊어진 BOX 선 연결',description:'생산설비 BOX 레이어의 열린 폴리라인과 LINE을 검사합니다. 허용오차 안의 유일한 끝점만 맞추고 단순 폐합을 확인합니다. 분기·교차·중복·고정 형상과 곡선 폐합은 자동 처리에서 제외합니다.'},
 {title:'3. 서로 다른 속성란 통합',description:'개별 객체와 INSERT 속성의 건설코드 별칭을 검색해 공통 _constructionCode 필드에 복사합니다. 원래 속성란과 원본 추출값은 보존합니다. 서로 다른 값이 발견되면 충돌로 표시합니다.'},
 {title:'4. BOX 밖 코드 귀속·이동',description:'속성 코드와 문자 후보를 대조합니다. 검색거리 안에서 관계가 유일한 문자만 BOX와 연결하고, 들어갈 크기의 회전 없는 문자를 직사각 BOX 안으로 이동합니다. 문자 폭은 근사값이므로 원본 대조가 필요합니다.'},
 {title:'5. 누락·모호한 값 분리',description:'인접 BOX가 여러 개이거나 코드가 없으면 값을 만들지 않습니다. 공유 건설코드의 중복 허용 여부는 프로젝트에서 선택합니다. 객체 속성의 공통 건설코드를 수동 보완하고 다시 검사합니다.'},
 {title:'6. 후보 적용·저장·재검사',description:'대상 Handle, 수정 종류, 이동량과 보류 사유를 보고 적용합니다. 분석 후 도면이 바뀌면 다시 분석해야 합니다. DB 저장 시 사유와 변경 전후를 남기고 현재 개정의 BOX·코드·Bay를 재검수합니다. 원본 DWG에는 재기록하지 않습니다.'}
];
export function reviewState(issues){return issues.length?{title:`잔여 간섭 ${issues.length}건`,detail:'조건을 수정하고 재검사하세요.',state:'needs-review'}:{title:'현재 2D 검사 조건 통과',detail:'설계자 검토와 DWG 반영은 별도 단계입니다.',state:'clear'};}
export function selectedView(hash){return ['#workflow','#database'].includes(hash)?hash.slice(1):'studio';}
