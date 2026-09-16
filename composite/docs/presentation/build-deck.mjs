import fs from 'node:fs/promises';
import path from 'node:path';
import { pathToFileURL, fileURLToPath } from 'node:url';
import { createRequire } from 'node:module';
import { parseArgs } from 'node:util';
import { createHash } from 'node:crypto';

// Editable Korean platform introduction. No generated pictures or flattened diagrams.
const { values:args }=parseArgs({options:{workspace:{type:'string'},output:{type:'string'},'skill-dir':{type:'string'},python:{type:'string'},'node-modules':{type:'string'},workflow:{type:'string'},engine:{type:'string'},'composite-engine':{type:'string'},'reference-deck':{type:'string'},revision:{type:'string'}}});
const SCRIPT_DIR=path.dirname(fileURLToPath(import.meta.url));
const ROOT=path.resolve(args.workspace||process.env.DECK_WORKSPACE||path.join(SCRIPT_DIR,'.build'));
const SKILL=args['skill-dir']||process.env.PRESENTATIONS_SKILL_DIR;
const PYTHON=args.python||process.env.RUNTIME_PYTHON;
const MODULES=args['node-modules']||process.env.RUNTIME_NODE_MODULES;
if(!SKILL||!PYTHON||!MODULES)throw new Error('Provide --skill-dir, --python and --node-modules using the bundled runtime paths from load_workspace_dependencies (or their documented environment variables).');
process.env.RUNTIME_NODE_MODULES=path.resolve(MODULES);
process.env.RUNTIME_NODE||=process.execPath;
process.env.RUNTIME_PYTHON=path.resolve(PYTHON);
const requireRuntime=createRequire(path.join(path.resolve(MODULES),'presentation-loader.cjs'));
const {Presentation,PresentationFile,FileBlob}=await import(pathToFileURL(requireRuntime.resolve('@oai/artifact-tool')).href);
const workflowPath=path.resolve(args.workflow||path.join(SCRIPT_DIR,'../../dist/workflow.mjs'));
const enginePath=path.resolve(args.engine||path.join(path.dirname(workflowPath),'engine.mjs'));
const referenceDeckPath=path.resolve(args['reference-deck']||path.join(SCRIPT_DIR,'../COMPOSITE_Platform_Introduction.pptx'));
const referenceSha256=createHash('sha256').update(await fs.readFile(referenceDeckPath)).digest('hex');
const {workflow,repairWorkflow}=await import(pathToFileURL(workflowPath).href);
if(workflow.length!==7||repairWorkflow.length!==6)throw new Error('Review the native business and BOX repair flowcharts against the current workflow model.');
const {room,sample,inspect,autoLayout}=await import(pathToFileURL(enginePath).href);
const compositeEnginePath=path.resolve(args['composite-engine']||path.join(path.dirname(workflowPath),'composite-engine.mjs'));
const {sampleComposite,inspectComposite,proposeComposite,utMatrix}=await import(pathToFileURL(compositeEnginePath).href);
const compositeSample=sampleComposite();
const compositeMovement=proposeComposite(compositeSample,'movement');
const compositeConnection=proposeComposite(compositeSample,'connection');
if(!compositeMovement.ok||!compositeConnection.ok)throw new Error('A composite sample proposal failed. Review slides 10 and 11 before rebuilding.');
const compositeEvidence={count:compositeSample.objects.length,before:inspectComposite(compositeSample).length,movement:compositeMovement.metrics,connection:compositeConnection.metrics,ut:utMatrix(compositeSample)};
const sampleItems=sample(),sampleResult=autoLayout(sampleItems,1);
if(!sampleResult.ok)throw new Error('The current sample no longer yields a successful automatic layout. Review slide 11 before rebuilding.');
const evidence={equipment:sampleItems.length,before:inspect(sampleItems,1).length,after:inspect(sampleResult.items,1).length,moved:sampleResult.moved};
const REV=args.revision||process.env.DECK_REVISION||'dwg-v1';
const { finalizePresentation, resolvePresentationFont, applyPresentationChartFont } = await import(pathToFileURL(path.join(SKILL,'container_tools/artifact_tool_utils.mjs')).href);
const FONT = resolvePresentationFont({fontFamily:'Malgun Gothic', availableFonts:['Malgun Gothic']});
const C={navy:'#152A37',teal:'#67E8BA',darkTeal:'#13755B',slate:'#526776',line:'#D1DDE3',light:'#F2F6F8',white:'#FFFFFF',amber:'#B96724',paleAmber:'#FFF5E7'};
const W=1280,H=720;
const p=Presentation.create({slideSize:{width:W,height:H}});
const slides=[];
const sourceNote='Sources: dist/cad-model.mjs, dist/dwg-parser-worker.mjs, dist/box-repair.mjs, server/worker.mjs, the design studio UI, dist/workflow.mjs, dist/engine.mjs and dist/composite-engine.mjs. Parser: @mlightcad/libredwg-web 0.7.10 in a browser worker. Original DWG files use server object storage (R2) and extracted/current entity records use a server database (D1). DWG read support is limited to supported parser/geometry cases. Original DWG, extraction data and edited data are separate. DB editing does not write changes back into DWG. Native writeback, full BIM solids, routed utility engineering, organizational approval and internal Samsung standards are not claimed. The built-in equipment and composite calculations remain separate illustrative samples. Implementation verification reported by the implementation task: 44 automated tests passed; public DWG with 6 entities parsed through the browser pipeline, server storage, actual CAD dragging, saved revision and reloaded coordinates verified. BOX repair synthetic case: 0.01 m gap at 0.02 m tolerance, closure and BUILD_CODE to FAB-101 normalization proposed/applied; 7 missing-code warnings remained. These are limited public/synthetic fixtures; no actual Samsung project DWG was supplied and file-picker automation did not complete.';
const refs={samsungModel:'https://www.dbpia.co.kr/journal/articleDetail?nodeId=NODE12869219',samsungP2:'https://journal-kibim.apub.co.kr/articles/xml/d4Mn/',utilityPatent:'https://patents.google.com/patent/KR101600068B1/ko',skM16:'https://news.skhynix.co.kr/meet-the-protagonists-of-the-m16-construction/',skUT:'https://news.skhynix.co.kr/people-who-build/',skPoC:'https://news.sktelecom.com/en/3077',skNvidia:'https://news.skhynix.com/en/multi-year-tech-partnership-with-nvidia/'};
function text(s,value,x,y,w,h,size=24,color=C.navy,bold=false,align='left'){
 const sh=s.shapes.add({geometry:'textbox',name:value.split('\n')[0].slice(0,48),position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});
 sh.text=value;
 sh.text.style={typeface:FONT,fontSize:size,color,bold,alignment:align,verticalAlignment:'top',autoFit:'none',wrap:'square',insets:{left:0,right:0,top:0,bottom:0}};
 return sh;
}
function line(s,x,y,w,color=C.line,width=1){return s.shapes.add({geometry:'line',position:{left:x,top:y,width:w,height:0},fill:'none',line:{fill:color,width,style:'solid'}});}
function base(title,subtitle,dark=false){
 const s=p.slides.add();s.background.fill=dark?C.navy:C.light;slides.push(s);
 if(title)text(s,title,64,48,1152,64,44,dark?C.white:C.navy,true);
 if(subtitle)text(s,subtitle,64,121,1152,65,24,dark?'#BBD0D9':C.slate);
 if(title)line(s,64,188,1152,dark?'#3A5363':C.line,1);
 text(s,String(slides.length).padStart(2,'0'),1156,671,60,24,16,dark?'#8CA8B8':C.slate,false,'right');
 s.speakerNotes.textFrame.setText(sourceNote);
 return s;
}
function node(s,label,x,y,w,h,kind='current',geom='rect',size=23){
 const palette=kind==='planned'?{fill:C.white,line:C.slate,color:C.slate}:kind==='manual'?{fill:C.paleAmber,line:C.amber,color:C.navy}:{fill:'#DEF8ED',line:C.darkTeal,color:C.navy};
 const sh=s.shapes.add({geometry:geom,name:label.split('\n')[0],position:{left:x,top:y,width:w,height:h},fill:palette.fill,line:{fill:palette.line,width:1.5,style:kind==='planned'?'dashed':'solid'}});
 sh.text=label;sh.text.style={typeface:FONT,fontSize:size,color:palette.color,bold:true,alignment:'center',verticalAlignment:'middle',autoFit:'none',wrap:'square',insets:{top:10,bottom:10,left:12,right:12}};
 return sh;
}
function connect(s,a,b,from='right',to='left',color=C.darkTeal,kind='straight',arrow=true){
 return s.shapes.connect(a,b,{kind,fromSide:from,toSide:to,line:{fill:color,width:2.3,style:color===C.amber?'dashed':'solid'},tail:{type:arrow?'triangle':'none',width:'med',length:'med'}});
}
function anchor(s,x,y){return s.shapes.add({geometry:'rect',name:'Editable connector bend',position:{left:x,top:y,width:1,height:1},fill:'none',line:{fill:'none',width:0}});}
function table(s,values,x,y,w,h,widths,bodySize=22){
 const t=s.tables.add({rows:values.length,columns:values[0].length,left:x,top:y,width:w,height:h,columnWidths:widths,values});
 t.styleOptions={headerRow:true,bandedRows:false};
 t.borders.assign({fill:C.line,width:1,style:'solid'});
 for(let r=0;r<values.length;r++){
  t.rows[r].height=r===0?55:(h-55)/(values.length-1);
  for(let c=0;c<values[0].length;c++){
   const cell=t.getCell(r,c);cell.fill=r===0?C.navy:(r%2===0?'#EAF0F3':C.white);
   cell.text.style={typeface:FONT,fontSize:r===0?22:bodySize,color:r===0?C.white:C.navy,bold:r===0||c===0,verticalAlignment:'middle',autoFit:'none',insets:{left:14,right:14,top:12,bottom:12}};
  }
 }
 return t;
}

// 1. Minimal title slide.
{
 const s=base(null,null,true);
 text(s,'COMPOSITE',64,72,1152,70,64,C.teal,true);
 text(s,'삼성전자향 FAB 설계',64,223,1152,92,62,C.white,true);
 text(s,'DWG 객체 DB와 Bay 기반 통합 설계 스튜디오',68,337,1100,62,32,'#BBD0D9');
 line(s,68,475,1148,'#3A5363',1);
 text(s,'실제 CAD 형상 검수와 객체 편집을 서버 데이터로 연결',68,506,1080,45,26,C.white);
 text(s,'공개 자료를 참고한 플랫폼입니다. 도면·Bay·공종 기준은 실제 프로젝트에서 확정합니다.',68,565,1080,60,22,'#BBD0D9');
}

// 2. Native scope table distinguishes source DWG from DB edits.
{
 const s=base('현재 구현 범위','DWG 원본과 추출 객체를 보존하고, 검수한 편집 결과를 서버에 저장');
 table(s,[
  ['구분','현재 제공','적용 범위와 경계'],
  ['DWG 데이터','DWG 파싱, 업로드, 객체 DB 추출','20 MB 이하 도면, 최대 1만 객체'],
  ['서버 저장','원본 도면, 추출값, 수정값·변경 이력','저장 실패를 성공으로 처리하지 않음'],
  ['통합 스튜디오','실제 CAD 형상 표시와 객체 이동','생산설비·인프라 레이어 분류·검수'],
  ['Bay 검토','Bay 경계와 설계 조건 편집','프로젝트 기준으로 생산·인프라 검토'],
  ['설계 계산','기존 설비·컴포짓 샘플 계산 유지','실제 DWG의 자동 설계 성능과 구분'],
 ],64,216,1152,384,[188,505,459],22);
 text(s,'DB 편집은 원본 DWG 재기록과 별도입니다. DWG 파일에 수정값을 반영하는 기능은 아직 제공하지 않습니다.',64,623,1152,38,21,C.slate);
}

// 3. The unified studio and the database remain separate from the business process.
{
 const s=base('설계 스튜디오와 두 지원 탭','배치와 컴포짓을 한 스튜디오에서 검토하고 DB·업무 절차를 별도로 확인');
 table(s,[
  ['작업 공간','사용자가 확인하고 실행하는 항목'],
  ['설계 스튜디오','실제 CAD 형상, 생산설비 BOX와 인프라 레이어 검토\nBay 경계·분류·배치 확인, 객체 이동과 DB 반영'],
  ['DWG 데이터베이스','도면 업로드, 파싱 상태와 추출 객체 확인\n원본 추출값과 현재 수정값 비교, DB 편집과 이력 확인'],
  ['업무 프로세스','DWG 등록부터 설계 검토까지 단계별 담당과 산출물\n현재 제공 기능, 설계자 업무, DWG 재기록 예정 범위 구분'],
 ],64,220,1152,360,[268,884],24);
 text(s,'서버에 저장한 DWG·객체 데이터와 내장 예시의 임시 배치 상태를 구분합니다.',64,618,1152,48,21,C.slate);
}

// 4. Native editable ingestion and data lineage flow.
{
 const s=base('DWG 업로드와 객체 DB 편집','원본을 보존하고 추출·검수·저장 단계를 거쳐 수정 결과를 재조회');
 const a=node(s,'DWG 파일 선택',64,250,244,88);
 const b=node(s,'브라우저 파싱\n객체·레이어 추출',364,250,244,88);
 const c=node(s,'원본 보관\n서버 파일 저장',664,250,244,88);
 const d=node(s,'DB 등록\n추출값 보존',972,250,244,88);
 const e=node(s,'객체 확인\n분류·단위·Bay',972,458,244,88,'manual');
 const f=node(s,'도면 객체 이동\n또는 DB 편집',664,458,244,88);
 const g=node(s,'DB 저장\n수정값·이력',364,458,244,88);
 const h=node(s,'재조회\n저장 결과 확인',64,458,244,88);
 connect(s,a,b);connect(s,b,c);connect(s,c,d);connect(s,d,e,'bottom','top');connect(s,e,f,'left','right');connect(s,f,g,'left','right');connect(s,g,h,'left','right');
 text(s,'지원하지 않는 객체는 별도 표시',664,371,552,37,22,C.amber,true);
 text(s,'파싱 실패와 저장 실패는 실패 상태로 안내합니다. 부분 추출은 전체 도면 검수 완료를 의미하지 않습니다.',64,609,1152,58,21,C.slate);
}

// 5. Native classification and QC table.
{
 const s=base('생산설비 BOX와 인프라 레이어 검수','도면의 객체 형상과 레이어를 프로젝트 분류 기준에 맞춰 확인');
 table(s,[
  ['분류','설계 스튜디오의 검토 대상','확인할 항목'],
  ['생산설비 BOX','닫힌 형상·블록·검수한 BOX 그룹','예상 BOX 수, 크기·위치, Bay 배정'],
  ['전기분전반·VMB','전기·가스 공급 및 분배 설비','도면 레이어와 객체 분류 일치'],
  ['배관·덕트','유체·공조 인프라 형상','지원 형상 여부와 실제 표시 결과'],
  ['전기 모듈랙·인동선','전기 지원 공간과 사람의 이동 영역','Bay와 생산설비의 공간 관계'],
  ['검수 상태','미지원 객체, 단위, 분류·수량','검수 미완료 항목을 명시적으로 표시'],
 ],64,216,1152,384,[268,432,452],22);
 text(s,'분류와 검수는 실제 도면 기준으로 확정합니다. 공개되지 않은 삼성전자 레이어 규칙을 가정하지 않습니다.',64,623,1152,38,21,C.slate);
}

// 6. Bay-based design review is expressed as editable evidence.
{
 const s=base('Bay 기반 생산설비와 인프라 검토','Bay를 기본 검토 단위로 사용하고 경계·조건을 프로젝트에 맞게 편집');
 table(s,[
  ['Bay 검토 항목','사용자가 정하는 입력','검토·반영 결과'],
  ['경계와 기준','Bay 이름, 경계, 설계 조건','도면과 대조한 검토 영역'],
  ['생산설비 배치','BOX 위치·분류, 예상 수량, 최소 이격','Bay 대안 생성, BOX·인동선 재검사'],
  ['인프라 배치','선택형 인프라 구역의 방향·폭','구역 안에 인프라, 생산설비 BOX는 밖에 배치'],
  ['편집 결과','Bay 대안 적용·도면 이동·DB 수정','저장 후 재조회하는 객체 좌표·이력'],
 ],64,216,1152,376,[246,468,438],22);
 text(s,'실제 CAD 검사는 2D 경계·BOX 이격·인동선 기준입니다. 공종 간 3D 간섭과 실제 유틸리티 경로 해석은 미구현입니다.',64,619,1152,50,21,C.slate);
}

// 7. Native source/current/history table.
{
 const s=base('원본 추출값과 현재 수정값','원본 도면과 추출 결과를 남겨 편집·검수 이력을 추적');
 table(s,[
  ['데이터 구분','보존·표시하는 내용','사용자가 확인하는 기준'],
  ['원본 DWG','서버에 보관한 업로드 도면','DB 편집으로 원본 파일을 덮어쓰지 않음'],
  ['원본 추출값','객체 식별자, 타입·레이어와 추출 형상','파서가 읽은 값과 지원 여부'],
  ['현재 수정값','분류·Bay와 사용자가 편집한 객체 값','저장 후 서버에서 다시 읽은 값'],
  ['변경 이력','변경 사유·이전값·수정값·시간','개정 충돌 시 재조회 후 수정'],
  ['상태 표시','부분 지원, 검수 대기, 파싱·저장 실패','실패·미완료 상태를 확인한 후 재작업'],
 ],64,216,1152,384,[226,464,462],22);
 text(s,'조직별 승인·권한 관리와 원본 DWG 재기록은 별도 기능입니다.',64,623,1152,38,21,C.slate);
}

// 8. Native repair table: three requested error classes and safe treatment.
{
 const s=base('BOX 자동 보정: 세 가지 오류 정리','수정 후보를 먼저 확인하고, 원본을 보존한 채 현재 객체 DB에 반영');
 table(s,[
  ['오류 유형','자동 보정하는 조건과 결과','자동 처리에서 남기는 항목'],
  ['끊어진 BOX 선','허용오차 안의 유일한 끝점 연결\nLINE 그룹·열린 폴리라인의 단순 폐합','분기·교차·중복·고정·곡선 폐합\n모호한 연결은 확인 대상으로 유지'],
  ['서로 다른 코드 속성란','객체·INSERT 속성의 별칭 검색\n공통 _constructionCode에 값 복사','원래 속성은 보존\n서로 다른 코드 값은 충돌로 표시'],
  ['BOX 밖의 건설코드','유일하게 연결되는 문자만 귀속\n들어갈 크기의 문자를 BOX 안으로 이동','근접 BOX가 여럿이거나 코드 누락\n회전 문자·크기 부적합은 수동 확인'],
 ],64,216,1152,365,[225,465,462],22);
 text(s,'없는 코드는 만들지 않습니다. 공유 코드의 중복 허용은 프로젝트에서 선택하며, 문자 폭은 근사값이므로 대조가 필요합니다.',64,610,1152,58,21,C.slate);
 s.speakerNotes.textFrame.setText(sourceNote+'\nRepair workflow from the shared implementation model:\n'+repairWorkflow.map(x=>x.title+': '+x.description).join('\n')+'\nNo company-specific construction-code standard is inferred. Original DWG bytes and original extracted fields are preserved.');
}

// 9. Editable six-stage repair workflow with unresolved-warning recheck.
{
 const s=base('BOX 보정의 적용·재검수 흐름','분석 이후 도면이 바뀌면 제안을 다시 만들고, 미해결 경고를 확인');
 const a=node(s,'1. 단위·허용오차\n프로젝트 조건 확인',64,245,310,92,'manual', 'rect',24);
 const b=node(s,'2. BOX 선 연결\n유일한 단순 폐합',485,245,310,92);
 const c=node(s,'3. 코드 속성란 통합\n원래 값 보존',906,245,310,92);
 const d=node(s,'4. 외부 문자 귀속·이동\n유일한 BOX만 연결',906,438,310,92);
 const e=node(s,'5. 누락·모호함 분리\n설계자 수동 보완',485,438,310,92,'manual');
 const f=node(s,'6. 후보 확인·적용\nDB 저장·재검수',64,438,310,92);
 connect(s,a,b);connect(s,b,c);connect(s,c,d,'bottom','top');connect(s,d,e,'left','right');connect(s,e,f,'left','right');
 connect(s,f,a,'top','bottom',C.amber);
 text(s,'잔여 경고: 보완 후 재분석',252,367,430,33,20,C.amber,true);
 text(s,'대상 객체·수정 종류·이동량·보류 사유를 확인한 후 적용합니다.',64,568,1152,38,23,C.navy,true);
 text(s,'변경 전후와 사유를 서버에 기록합니다. 미해결 경고가 있으면 검수 완료를 막으며, 원본 DWG에는 재기록하지 않습니다.',64,621,1152,48,21,C.slate);
 s.speakerNotes.textFrame.setText(sourceNote+'\n'+repairWorkflow.map(x=>x.title+': '+x.description).join('\n')+'\nRepair warnings are persisted in metadata and block QC until reanalysis. Proposals become stale after model changes. Editable shapes and connectors represent the six shared repairWorkflow stages.');
}

// 10. Samsung evidence and project-specific interpretation are kept separate.
{
 const s=base('삼성전자 참여 연구와 관련 공개 특허','연구·특허의 개념을 샘플 규칙에 연결하고 실제 적용 실적과 구분');
 table(s,[
  ['공개 근거와 성격','자료에서 확인한 내용','플랫폼에 반영한 해석'],
  ['삼성전자 공저 연구\n2026.04\n개념모델 연구','필수 제약과 선호 목표를 구분\n박스·이격 기반 검토\n유틸리티 연결 KPI 대안 제시','필수 조건을 먼저 검사\n통과 후보의 이동량과\n연결거리 우선순위 비교'],
  ['삼성전자·삼성물산\nP2 FAB 연구 2022.12\n업무지원 시제품','Revision·Hold 변경 관리\nShop·AFC·준공도면 정합성\n현장 이슈 피드백','고정·Hold와 개정 메타데이터\n입력 변경 후 재검사\n기존 후보·검토 상태 무효화'],
  ['삼성물산·삼우\n2016.03 공개 특허\nBay 유틸리티 공간','Bay별 배관·덕트·케이블\n설치 공간의 분할과\n유틸리티 모듈 구성','공종별 높이 구간과\n유지보수 예약 공간을\n프로젝트 예시 제약으로 구성'],
 ],64,212,1152,396,[272,458,422],21);
 text(s,'출처: 대한건축학회·한국BIM학회 연구, KR101600068B1. 특허의 삼성전자 적용 실적은 확인하지 않았습니다.',64,627,1152,38,19,C.slate);
 s.speakerNotes.textFrame.setText(sourceNote+'\nSamsung-coauthored 2026.04 conceptual-model research, indexed abstract and paper metadata: '+refs.samsungModel+' . Indexed academic PDF: https://conf.aik.or.kr/pdfs/output/paper_260316135314675.pdf (direct retrieval unavailable). Evidence describes a generalized model and alternative KPIs, not a deployed internal solver.\nSamsung Electronics and Samsung C&T P2 FAB prototype study, 2022-12-31, DOI 10.13161/kibim.2022.12.4.001: '+refs.samsungP2+' . Revision/Hold, drawing consistency and issue feedback are reported research/workflow subjects.\nGoogle Patents primary patent document KR101600068B1, 2016.03: '+refs.utilityPatent+' . Assignees are Samsung C&T and Samoo. Bay utility spatial separation and modules are patent concepts, not evidence of Samsung Electronics adoption or its internal standards. Our implementation is an independent sample interpretation.');
}

// 9. SK hynix official sources distinguish actual construction, PoC and plans.
{
 const s=base('SK하이닉스 공개 사례에서 참고한 방식','실제 시공 사례, 디지털 트윈 실증, 개발 계획을 구분');
 table(s,[
  ['공개 근거와 성격','자료에서 확인한 내용','플랫폼에 반영한 해석'],
  ['M16 건설 공식 사례\n2021.02\n실제 시공 경험','BIM 배관·덕트·케이블 트레이\n층 내부·층 사이 간섭 예측\n전기실 배치와 거리 검토','공종별 XY·Z 범위 검사\n높이 구간과 제외 영역\n연결거리 비교'],
  ['FAB 건설 업무 소개\n2019.12\n공식 직무 사례','Layout·UT Matrix 변경\n공종 간 조정과 반복되는\n설계·구매·시공 협의','샘플 UT POC 수요·용량\n개정 이력과 재검사 흐름'],
  ['디지털 트윈\n2026.06 공식 발표\nPoC 완료·개발 계획','2025 FAB PoC 완료 발표\n가상 배치·변경 시나리오\nNVIDIA 협력 개발 진행','복수 후보를 사전 비교\n실제 공정 시뮬레이션은\n향후 별도 개발 범위'],
 ],64,212,1152,396,[272,458,422],21);
 text(s,'출처: SK하이닉스 뉴스룸(2019·2021·2026), SK텔레콤 뉴스룸(2026). 회사별 상세 기준은 공개 확인 범위 밖입니다.',64,627,1152,38,19,C.slate);
 s.speakerNotes.textFrame.setText(sourceNote+'\nSK hynix official M16 construction account, 2021-02-01: '+refs.skM16+' . Search-indexed official content describes BIM piping/ducts/cable trays, within/between-floor clash prediction and electrical room distance/layout review. Direct website access returned 403 during research.\nSK hynix official role account, 2019-12-03: '+refs.skUT+' . Layout and UT Matrix changes, cross-trade coordination and repeated design/procurement/construction work.\nSK Telecom official, 2026-06-01: '+refs.skPoC+' . States a 2025 SK hynix FAB digital twin PoC was completed and commercialization planned. Virtual equipment-layout and process-change scenarios are discussed.\nSK hynix official NVIDIA partnership, 2026-06-08: '+refs.skNvidia+' . FAB digital twin under development with Omniverse/OpenUSD. This does not establish completed automatic DWG composite coordination.');
}

// 10. Native rule table keeps engineering limits visible.
{
 const s=base('내장 컴포짓 샘플의 검사 규칙','실제 CAD 객체 DB와 별도로 제공하는 예시 박스·UT 계산의 범위');
 table(s,[
  ['구분','현재 검사·비교 항목','해석 범위'],
  ['필수 조건\n형상·구역','XY 겹침과 Z 높이 범위\n공종별 높이 구간, 제외 공간','직사각형 박스 기반 검사\nBIM 솔리드 형상 검사는 미구현'],
  ['필수 조건\n변경 제한','고정·Hold 대상의 위치 유지\n경계·이격 등 지정 조건','프로젝트 샘플 기준 사용\n현장 규정 검증은 별도'],
  ['UT 연결 검사','설비 POC와 공급 지점 연결\n샘플 수요와 용량의 적합성','수리·전기 계산과 실제 경로\n자동 생성은 미구현'],
  ['선호 목표','이동 최소 후보와 연결거리 우선 후보\n필수 조건을 통과한 후보만 적용','가중 비용으로 후보 순위 산정\n전역 최적해 보장 없음'],
 ],64,212,1152,392,[206,532,414],22);
 text(s,`배관·덕트·케이블 트레이 ${compositeEvidence.count}개 박스를 사용하는 프로젝트 예시입니다. 회사별 설계 수치는 사용하지 않습니다.`,64,626,1152,38,20,C.slate);
}

// 11. Native chart; verified demonstration numbers only.
{
 const s=base('내장 설비·컴포짓 샘플 결과',`${room.w} × ${room.h} m 설비 공간과 유틸리티 박스 ${compositeEvidence.count}개를 각각 검사`);
 text(s,`설비 ${evidence.equipment}대, 이격 1.0 m`,64,220,646,40,27,C.navy,true);
 text(s,'컴포짓 후보 비교',786,220,430,40,27,C.navy,true);
 const ch=s.charts.add('bar',{
  position:{left:62,top:278,width:648,height:275},categories:['자동배치 전','자동배치 후'],
  series:[{name:'검출 이슈 수',values:[evidence.before,evidence.after],fill:C.darkTeal,points:[{idx:0,fill:C.navy},{idx:1,fill:C.darkTeal}],valuesFormatCode:'0"건"'}],
  barOptions:{direction:'column',grouping:'clustered',gapWidth:130},hasLegend:false,
  xAxis:{visible:true,textStyle:{fontSize:24,fill:C.navy,typeface:FONT},line:{fill:C.line,width:1}},
  yAxis:{visible:true,min:0,max:Math.max(evidence.before,evidence.after)+1,majorUnit:2,numberFormatCode:'0',textStyle:{fontSize:19,fill:C.slate,typeface:FONT},majorGridlines:{fill:C.line,width:1}},
  dataLabels:{showValue:true,position:'outEnd',textStyle:{typeface:FONT,fontSize:34,bold:true,fill:C.navy}},chartFill:'none',plotAreaFill:'none',chartLine:{fill:'none',width:0},plotAreaLine:{fill:'none',width:0},
 });
 applyPresentationChartFont(ch,{fontFamily:FONT});
 table(s,[['후보','이동량','POC 거리'],['이동 최소',`${compositeEvidence.movement.movement.toFixed(1)} m`,`${compositeEvidence.movement.connection.toFixed(1)} m`],['연결거리 우선',`${compositeEvidence.connection.movement.toFixed(1)} m`,`${compositeEvidence.connection.connection.toFixed(1)} m`]],786,275,430,195,[178,126,126],20);
 text(s,`초기 위반 ${compositeEvidence.before}건, 두 후보 모두 ${compositeEvidence.movement.issues}건\n이동 객체 ${compositeEvidence.movement.moved}개·${compositeEvidence.connection.moved}개, 고정 객체 유지`,786,494,430,64,21,C.navy);
 text(s,`설비 ${evidence.moved}대 이동, 전체 조건 재검사`,64,573,646,35,21,C.slate);
 text(s,'POC 거리: 박스까지 맨해튼 거리 합계\n실제 경로 길이 계산은 미구현',786,572,430,58,20,C.slate);
 text(s,'프로젝트 예시의 실행 결과입니다. 실제 DWG 성능이나 회사별 설계 기준을 의미하지 않습니다.',64,641,1152,31,20,C.slate);
 s.speakerNotes.textFrame.setText(sourceNote+` Equipment sample result is calculated by inspect(sample(),1), autoLayout(sample(),1), then inspect(result.items,1). Before: ${evidence.before} issues. After: ${evidence.after} issues. Moved: ${evidence.moved} of ${evidence.equipment} equipment. Composite sample result is calculated from sampleComposite(), inspectComposite(), and proposeComposite() with movement and connection strategies. ${JSON.stringify(compositeEvidence)} . Movement is summed Euclidean displacement. POC distance is summed minimum Manhattan distance between supply points and envelopes, a proxy rather than a routed length. These are sample demonstration results, not performance guarantees.`);
}

// 12. Native business flow with explicit pass/fail and implementation status.
{
 const s=base('DWG 기반 업무 흐름','원본·객체 DB를 기준으로 설계 검토와 도면 발행의 책임을 구분');
 const a=node(s,'DWG 원본 등록',64,252,244,94);
 const b=node(s,'객체 추출·BOX 정리',364,252,244,94);
 const c=node(s,'Bay·레이어\n배치 조건 설정',664,252,244,94);
 const d=node(s,'통합 스튜디오 검토',972,252,244,94);
 const e=node(s,'객체 이동·DB 편집',972,454,244,94);
 const f=node(s,'재검사',692,432,188,138,'current','diamond',23);
 const g=node(s,'설계자 검토·승인',364,454,244,94,'manual');
 const h=node(s,'DWG 재기록·발행\n(연동 예정)',64,454,244,94,'planned', 'rect',22);
 connect(s,a,b);connect(s,b,c);connect(s,c,d);connect(s,d,e,'bottom','top');connect(s,e,f,'left','right');connect(s,f,g,'left','right');connect(s,g,h,'left','right');
 connect(s,f,c,'top','bottom',C.amber);
 text(s,'불합격: 조건 수정',789,377,179,35,18,C.amber,true);
 text(s,'합격',614,469,63,30,19,C.darkTeal,true);
 text(s,'녹색: 현재 제공 기능',64,209,275,29,19,C.darkTeal,true);
 text(s,'주황색: 사람이 수행하는 업무',364,209,391,29,19,C.amber,true);
 text(s,'점선: 연동 예정',972,209,244,29,19,C.slate,true);
 text(s,'실제 CAD 검수와 내장 샘플 계산의 범위를 구분합니다. DWG 재기록·발행과 조직 승인 연동은 미구현입니다.',64,613,1152,48,21,C.slate);
}

// 13. Owner/input/output table with scoped statuses.
{
 const s=base('단계별 담당자와 산출물','담당 역할은 제안 기준이며 프로젝트 착수 시 책임자와 승인 기준을 확정');
 const rows=workflow.map(stage=>[stage.title,stage.owner.replaceAll(' · ','\n'),stage.input,stage.output,stage.status]);
 const t=table(s,[['업무 단계','담당 역할','입력','산출물','구현 상태'],...rows],64,198,1152,462,[230,178,248,276,220],18);
 for(let r=1;r<rows.length+1;r++)for(let c=0;c<5;c++)t.getCell(r,c).text.style={typeface:FONT,fontSize:18,color:C.navy,bold:c===0,verticalAlignment:'middle',autoFit:'none',insets:{left:12,right:12,top:4,bottom:4}};
}

// 14. Remaining scope and validation evidence, without an invented schedule.
{
 const s=base('실제 프로젝트 검증과 다음 개발 범위','DB 편집 결과의 설계 적합성과 원본 DWG 반영을 검증');
 const items=[
  ['01','프로젝트 검수','실제 도면 버전·단위·BOX 수·레이어·Bay 기준으로 대조'],
  ['02','CAD 지원 확대','미지원 객체와 복합 형상의 읽기·표시·편집 범위 확장'],
  ['03','DWG 재기록','DB 수정값을 원본에 반영하고 형상·좌표 정합성 검증'],
  ['04','협업·설계 승인','프로젝트 역할, 검수 책임, 승인·발행 이력 연동'],
 ];
 items.forEach((r,i)=>{const y=229+i*88;text(s,r[0],64,y,76,54,37,C.darkTeal,true);text(s,r[1],175,y+2,275,51,28,C.navy,true);text(s,r[2],467,y+3,749,54,24,C.slate);if(i<3)line(s,175,y+66,1041,C.line,1);});
 const link=text(s,'현재 플랫폼 열기',64,617,1152,38,22,C.darkTeal,true);
 link.text.get('현재 플랫폼 열기').link={uri:'https://composite-fab-layout-didwl.bbooggoo119.chatgpt.site/',isExternal:true};
 s.speakerNotes.textFrame.setText(sourceNote+' Private site access is required. Engineering workflow requires tests, source commit/push, exact source-version deployment and verification. No native DWG writeback, internal standard compliance or delivery schedule is promised.');
}

await fs.mkdir(path.join(ROOT,'build'),{recursive:true});await fs.mkdir(path.join(ROOT,'output'),{recursive:true});await fs.mkdir(path.join(ROOT,'qa'),{recursive:true});
await fs.writeFile(path.join(ROOT,'qa',`sample-evidence-${REV}.json`),JSON.stringify({equipment:evidence,composite:compositeEvidence},null,2));
const candidatePath=path.join(ROOT,'build',`candidate-${REV}.pptx`);
const finalPath=path.resolve(args.output||path.join(ROOT,'output',`COMPOSITE-FAB-플랫폼-소개-${REV}.pptx`));
await (await PresentationFile.exportPptx(p)).save(candidatePath);
await fs.writeFile(path.join(ROOT,'build',`presentation-${REV}.json`),JSON.stringify(p.toProto()));
const result=await finalizePresentation({workspaceDir:ROOT,candidatePath,finalPath,pythonExecutable:PYTHON,
 integrityValidatorPath:path.join(SKILL,'container_tools/inspect_presentation_package_integrity.py'),
 layoutValidatorPath:path.join(SKILL,'container_tools/inspect_presentation_layout_geometry.py'),
 layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-bullet-geometry','--validate-heading-fit',...[2,3,5,6,7,8,10,11,12,13,15].flatMap(n=>['--require-native-table-slide',String(n)])],
 explicitTotalSlideCount:16,requiredNativeTableOwnerSlides:[2,3,5,6,7,8,10,11,12,13,15],requiredNativeChartOwnerSlides:[13],materializeLiteralChartWorkbooks:true,
 fontPolicy:{basis:'reference',families:[FONT],referencePath:referenceDeckPath,referenceSha256},verifyArtifactToolImport:true,
 receiptPath:path.join(ROOT,'qa',`validation-${REV}.json`),
});
console.log(JSON.stringify(result,null,2));
const reimport=await PresentationFile.importPptx(await FileBlob.load(finalPath));
const importedSlides=reimport.slides.items;
for(let i=0;i<importedSlides.length;i++){
 const preview=await reimport.export({slide:importedSlides[i],format:'png',scale:1});
 await fs.writeFile(path.join(ROOT,'qa',`slide-${i+1}.png`),new Uint8Array(await preview.arrayBuffer()));
 const layout=await importedSlides[i].export({format:'layout'});
 await fs.writeFile(path.join(ROOT,'qa',`slide-${i+1}.layout.json`),await layout.text());
}
console.log(`FINAL_PPTX=${finalPath}`);
