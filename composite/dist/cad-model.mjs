export const MAX_ENTITIES=10000,MAX_BYTES=20*1024*1024;
export const categories={box:'생산설비 BOX',panel:'전기분전반',vmb:'VMB',pipe:'배관',duct:'덕트',rack:'전기 모듈랙',aisle:'인동선',reference:'참조 도면',unclassified:'미분류'};
export const colors={box:'#67e8ba',panel:'#edc878',vmb:'#e6a0dd',pipe:'#7ec9ef',duct:'#aeacf5',rack:'#eda879',aisle:'#94b49c',reference:'#718896',unclassified:'#d5e0e7'};
export function guessCategory(name){const s=name.toLowerCase();for(const [kind,re] of [['box',/box|생산설비|equipment/],['panel',/분전|배전|panel/],['vmb',/vmb/],['rack',/모듈|module|rack|랙/],['duct',/덕트|duct/],['pipe',/배관|pipe|piping/],['aisle',/인동선|동선|통로|aisle/]])if(re.test(s))return kind;return 'unclassified';}
export function normalizeDatabase(database,info){
 const records=[],seen=new Set();
 const add=(e,space)=>{const key=`${space}:${e.handle}`;if(seen.has(key))return;seen.add(key);records.push({handle:String(e.handle||records.length),type:e.type,space,layer:e.layer||'0',data:e,classification:guessCategory(e.layer||'')});};
 for(const e of database.entities||[])add(e,'model');
 const blocks=[];for(const b of database.tables?.BLOCK_RECORD?.entries||[]){blocks.push({...b,entities:undefined});if(b.name==='*Model_Space')continue;for(const e of b.entities||[])add(e,`block:${b.name}`);}
 if(records.length>MAX_ENTITIES)throw new Error(`객체가 ${MAX_ENTITIES.toLocaleString()}개를 넘습니다. Bay별 도면으로 분리해 주세요.`);
 if(!records.length)throw new Error('추출된 객체가 없습니다. 비어 있거나 지원하지 않는 도면입니다.');
 return {metadata:{...info,layers:database.tables?.LAYER?.entries||[],blocks,header:database.header||{},originalUnits:database.header?.INSUNITS||0,units:[1,2,4,5,6].includes(database.header?.INSUNITS)?database.header.INSUNITS:0,layerMap:{},bays:[],groups:[],codeLinks:[],clearance:0,expectedBoxes:0,unitsConfirmed:false},records};
}
const point=p=>p&&Number.isFinite(p.x)&&Number.isFinite(p.y),tau=Math.PI*2;
const identity=[1,0,0,1,0,0];
const transform=(p,m)=>({x:m[0]*p.x+m[2]*p.y+m[4],y:m[1]*p.x+m[3]*p.y+m[5]});
const multiply=(a,b)=>[a[0]*b[0]+a[2]*b[1],a[1]*b[0]+a[3]*b[1],a[0]*b[2]+a[2]*b[3],a[1]*b[2]+a[3]*b[3],a[0]*b[4]+a[2]*b[5]+a[4],a[1]*b[4]+a[3]*b[5]+a[5]];
function arcPoints(center,rx,ry,rotation,start,end){if(![rx,ry,rotation,start,end].every(Number.isFinite))return [];let span=(end-start)%tau;if(span<=0)span+=tau;const steps=Math.max(8,Math.ceil(span/tau*96));return Array.from({length:steps+1},(_,i)=>{const t=start+span*i/steps,x=rx*Math.cos(t),y=ry*Math.sin(t);return {x:center.x+x*Math.cos(rotation)-y*Math.sin(rotation),y:center.y+x*Math.sin(rotation)+y*Math.cos(rotation)};});}
function bulgePoints(a,b,bulge){if(!bulge)return [a,b];const length=Math.hypot(b.x-a.x,b.y-a.y);if(!length)return [a];const angle=4*Math.atan(bulge),r=length*(1+bulge*bulge)/(4*Math.abs(bulge)),h=length*(1-bulge*bulge)/(4*bulge),center={x:(a.x+b.x)/2-(b.y-a.y)/length*h,y:(a.y+b.y)/2+(b.x-a.x)/length*h},start=Math.atan2(a.y-center.y,a.x-center.x),steps=Math.max(4,Math.ceil(Math.abs(angle)/tau*96));return Array.from({length:steps+1},(_,i)=>({x:center.x+r*Math.cos(start+angle*i/steps),y:center.y+r*Math.sin(start+angle*i/steps)}));}
function geometryContext(records){const byBlock=new Map();for(const r of records)if(r.space.startsWith('block:')){const name=r.space.slice(6);if(!byBlock.has(name))byBlock.set(name,[]);byBlock.get(name).push(r);}return {byBlock,points:0};}
export function geometry(record,records,metadata,context=geometryContext(records)){
 const primitives=[],warnings=[],byBlock=context.byBlock;let calls=0,localPoints=0;
 function draw(e,m,stack=[],inheritedLayer=record.layer){
  if(++calls>5000||localPoints>25000||context.points>150000){if(!warnings.includes("표시 복잡도 한도 초과"))warnings.push("표시 복잡도 한도 초과");return;}
  const layer=!e.layer||e.layer==='0'?inheritedLayer:e.layer;
  if(e.isVisible===false)return;
  const n=e.extrusionDirection;if(n&&((n.x||0)!==0||(n.y||0)!==0||(n.z??1)<0)){warnings.push(`${e.type}: 비평면 OCS`);return;}
  const line=(points,closed=false)=>{localPoints+=points.length;context.points+=points.length;if(localPoints>25000||context.points>150000){warnings.push('표시 복잡도 한도 초과');return;}const world=points.filter(point).map(p=>transform(p,m));if(points.length&&world.length===points.length&&world.every(point))primitives.push({kind:'path',points:world,closed,layer});else warnings.push(`${e.type}: 좌표 없음`);};
  switch(e.type){
   case 'LINE':line([e.startPoint,e.endPoint]);break;
   case 'POINT':if(point(e.position||e.point))primitives.push({kind:'point',layer,...transform(e.position||e.point,m)});else warnings.push('POINT 좌표');break;
   case 'LWPOLYLINE':case 'POLYLINE2D':case 'POLYLINE3D':{const v=e.vertices||[];if(v.length>12000||!v.every(point)){warnings.push('폴리선 좌표·복잡도 한도');break;}const closed=!!((e.flag||e.flags||0)&1),pts=[];for(let i=0;i<v.length-(closed?0:1);i++)pts.push(...bulgePoints(v[i],v[(i+1)%v.length],v[i].bulge||0));line(pts,closed);break;}
   case 'CIRCLE':case 'ARC':if(point(e.center)&&e.radius>0)line(arcPoints(e.center,e.radius,e.radius,0,e.type==='CIRCLE'?0:e.startAngle,e.type==='CIRCLE'?tau:e.endAngle),e.type==='CIRCLE');else warnings.push(`${e.type}: 형상 없음`);break;
   case 'ELLIPSE':if(point(e.center)&&point(e.majorAxisEndPoint)){const a=e.majorAxisEndPoint,r=Math.hypot(a.x,a.y);line(arcPoints(e.center,r,r*e.axisRatio,Math.atan2(a.y,a.x),e.startAngle||0,e.endAngle||tau),Math.abs((e.endAngle||tau)-(e.startAngle||0)-tau)<1e-6);}else warnings.push('ELLIPSE 좌표');break;
   case 'TEXT':case 'MTEXT':case 'ATTRIB':case 'ATTDEF':{const t=typeof e.text==='object'?e.text:e,p=t.startPoint||t.insertionPoint;if(point(p)){const xy=transform(p,m),text=String(t.text||'').replace(/\\P/g,'\n').replace(/\\[A-Za-z][^;]*;/g,'').replace(/[{}]/g,'');primitives.push({kind:'text',layer,...xy,text,height:Math.max(.001,t.textHeight||1)*Math.hypot(m[0],m[1]),rotation:(t.rotation||0)+Math.atan2(m[1],m[0])});}else warnings.push(`${e.type}: 문자 좌표`);break;}
   case 'INSERT':{if(stack.includes(e.name)||stack.length>8){warnings.push('순환·깊은 블록 참조');break;}const block=metadata.blocks?.find(b=>b.name===e.name),children=byBlock.get(e.name);if(!children||!point(e.insertionPoint)){warnings.push(`미해결 블록 ${e.name}`);break;}if((e.columnCount||0)>1||(e.rowCount||0)>1){warnings.push('다중 INSERT 배열');break;}const p=e.insertionPoint,b=block?.basePoint||{x:0,y:0},r=e.rotation||0,sx=e.xScale??1,sy=e.yScale??1,c=Math.cos(r),s=Math.sin(r),local=[sx*c,sx*s,-sy*s,sy*c,p.x-sx*c*b.x+sy*s*b.y,p.y-sx*s*b.x-sy*c*b.y];for(const child of children)draw(child.data,multiply(m,local),[...stack,e.name],layer);for(const a of e.attribs||[])draw(a,m,stack,layer);break;}
   case 'SOLID':case '3DFACE':case 'TRACE':{if(e.type!=='3DFACE')warnings.push(`${e.type}: 면 정점 순서 원본 대조 필요`);const pts=e.vertices||(e.type==='3DFACE'?[e.corner1,e.corner2,e.corner3,e.corner4]:[e.corner1,e.corner2,e.corner4,e.corner3]).filter(Boolean);line(pts,true);break;}
   default:warnings.push(`${e.type}: 표시 미지원`);
  }
 }
 const offset=record.data._placement||{x:0,y:0};try{draw(record.data,[1,0,0,1,offset.x||0,offset.y||0]);}catch{warnings.push(`${record.type}: 유효하지 않은 형상 데이터`);}
 let bounds=null;const spatial=primitives.some(p=>p.kind==='path')?primitives.filter(p=>p.kind!=='text'):primitives;for(const p of spatial){const pts=p.kind==='path'?p.points:p.kind==='text'?[p,{x:p.x+p.height*Math.max(1,p.text.length)*.6,y:p.y+p.height}]:[p];for(const q of pts){if(!point(q)){warnings.push('표시 좌표 범위 오류');continue;}if(!bounds)bounds={x:q.x,y:q.y,maxX:q.x,maxY:q.y};else{bounds.x=Math.min(bounds.x,q.x);bounds.y=Math.min(bounds.y,q.y);bounds.maxX=Math.max(bounds.maxX,q.x);bounds.maxY=Math.max(bounds.maxY,q.y);}}}if(bounds){bounds.w=bounds.maxX-bounds.x;bounds.h=bounds.maxY-bounds.y;}

 return {primitives,warnings,bounds,closed:primitives.some(p=>p.closed)};
}
export function roleOf(r,m){return r.data._classificationOverride?r.classification:(m.layerMap?.[r.layer]||r.classification||guessCategory(r.layer));}
export function viewItems(records,m){const context=geometryContext(records);return records.filter(r=>r.space==='model').map(r=>({...r,category:roleOf(r,m),...geometry(r,records,m,context)}));}
export function drawingBounds(items){const b=items.map(i=>i.bounds).filter(Boolean);if(!b.length)return {x:0,y:0,w:100,h:100};const x=Math.min(...b.map(a=>a.x)),y=Math.min(...b.map(a=>a.y));return {x,y,w:Math.max(1,Math.max(...b.map(a=>a.maxX))-x),h:Math.max(1,Math.max(...b.map(a=>a.maxY))-y)};}
export const contains=(bay,b)=>b.x>=bay.x-1e-6&&b.y>=bay.y-1e-6&&b.maxX<=bay.x+bay.w+1e-6&&b.maxY<=bay.y+bay.h+1e-6;
export function footprints(items,m){const grouped=new Set((m.groups||[]).flatMap(g=>g.memberIds));const boxes=items.filter(i=>!grouped.has(i.id)&&i.category==='box'&&i.bounds&&(i.closed||i.type==='INSERT'));for(const g of m.groups||[]){const members=items.filter(i=>g.memberIds.includes(i.id)),b=drawingBounds(members);if(members.length)boxes.push({id:g.id,handle:g.name,type:'BOX_GROUP',space:'model',category:'box',closed:true,bounds:{...b,maxX:b.x+b.w,maxY:b.y+b.h},data:{_locked:members.some(i=>i.data._locked)},memberIds:g.memberIds});}return boxes;}
const overlap=(a,b,gap=0)=>a.x<b.maxX+gap-1e-7&&a.maxX>b.x-gap+1e-7&&a.y<b.maxY+gap-1e-7&&a.maxY>b.y-gap+1e-7;
export function inspectDrawing(records,m){
 const items=viewItems(records,m),issues=[],boxes=footprints(items,m);
 const unclassified=[...new Set(items.flatMap(i=>[...(i.category==='unclassified'?[i.layer]:[]),...i.primitives.filter(p=>p.layer!==i.layer&&!m.layerMap?.[p.layer]&&guessCategory(p.layer)==='unclassified').map(p=>p.layer)]))],unsupported=items.filter(i=>i.warnings.length);
 if(!m.unitsConfirmed||!m.units)issues.push({type:'units',message:'도면 단위를 확인하세요.'});
 if(m.readError||m.unknownEntityCount||m.auditMissingCount||m.auditFailures)issues.push({type:'parser',message:`변환 경고 ${m.readError||0}, 미해석 ${m.unknownEntityCount||0}개 · 누락 ${m.auditMissingCount||0}개 · 대조 오류 ${m.auditFailures||0}개`});
 if(unsupported.length)issues.push({type:'unsupported',message:`표시를 완전히 지원하지 않는 객체 ${unsupported.length}개`});
 if(unclassified.length)issues.push({type:'layers',message:`미분류 레이어 ${unclassified.length}개`});
 if(!Number.isInteger(m.expectedBoxes)||m.expectedBoxes<1||boxes.length!==m.expectedBoxes)issues.push({type:'boxes',message:`BOX 후보 ${boxes.length}개 / 예상 ${m.expectedBoxes||'미입력'}개. 닫힌 형상·블록을 확인하세요.`});
 if(m.repairFindingCount)issues.push({type:'repair',message:`BOX 자동 정리 확인 ${m.repairFindingCount}건 — 원본 대조·수동 보완 후 수정 후보를 다시 분석하세요.`});
 if(m.requireConstructionCodes){const codes=new Map();for(const b of footprints(items,m)){const members=records.filter(r=>(b.memberIds||[b.id]).includes(r.id)),values=[...new Set(members.map(r=>r.data._constructionCode).filter(Boolean))];if(values.length!==1)issues.push({type:'code',id:b.id,message:`BOX ${b.handle}: 건설코드 ${values.length?'불일치':'미입력'}`});else codes.set(values[0],(codes.get(values[0])||0)+1);}if(m.repairSettings?.uniqueCodes)for(const [code,count] of codes)if(count>1)issues.push({type:'code',message:`건설코드 ${code}: ${count}개 BOX 중복`});}
 const assigned=[...items.filter(i=>i.bounds&&!['reference','unclassified'].includes(i.category)),...footprints(items,m).filter(i=>i.type==='BOX_GROUP')];
 if(!m.bays?.length)issues.push({type:'bay',message:'Bay 경계를 등록하세요.'});
 for(const i of assigned)if(!m.bays?.some(b=>contains(b,i.bounds)))issues.push({type:'bay',id:i.id,message:`${i.handle}: 단일 Bay 경계 밖`});
 for(const i of assigned){const bay=m.bays?.find(b=>contains(b,i.bounds)),lane=bay&&serviceLane(bay);if(lane&&['pipe','duct','rack','panel','vmb'].includes(i.category)&&!contains(lane,i.bounds))issues.push({type:'service',id:i.id,message:`${i.handle}: Bay 인프라 구역 밖`});if(lane&&i.category==='box'&&overlap(i.bounds,{...lane,maxX:lane.x+lane.w,maxY:lane.y+lane.h}))issues.push({type:'service',id:i.id,message:`${i.handle}: Bay 인프라 구역 침범`});}
 const ordered=[...boxes].sort((a,b)=>a.bounds.x-b.bounds.x),aisles=items.filter(i=>i.category==='aisle'&&i.closed&&i.bounds);let detailCount=0,comparisons=0,truncated=false;
 pairs:for(let i=0;i<ordered.length;i++)for(let j=i+1;j<ordered.length;j++){if(ordered[j].bounds.x>=ordered[i].bounds.maxX+(m.clearance||0))break;if(++comparisons>500000){truncated=true;break pairs;}if(overlap(ordered[i].bounds,ordered[j].bounds,m.clearance||0)){issues.push({type:'collision',id:ordered[i].id,message:`BOX ${ordered[i].handle} ↔ ${ordered[j].handle}: 겹침·이격 위반`});if(++detailCount>=300){truncated=true;break pairs;}}}
 aislesCheck:for(const b of boxes)for(const a of aisles){if(++comparisons>500000){truncated=true;break aislesCheck;}if(overlap(b.bounds,a.bounds)){issues.push({type:'aisle',id:b.id,message:`BOX ${b.handle}: 인동선 침범`});if(++detailCount>=300){truncated=true;break aislesCheck;}}}
 if(truncated)issues.push({type:'limit',message:'검수 상세·계산 한도에 도달했습니다. 표시된 문제를 해결하거나 Bay별로 분리 후 재검사하세요.'});

 return {issues,boxes:boxes.length,unsupported:unsupported.length,unclassified,items};
}
export function serviceLane(bay){const width=bay.serviceWidth||0;if(!width)return null;const side=bay.serviceSide||'right';if(side==='left')return {...bay,w:width};if(side==='right')return {...bay,x:bay.x+bay.w-width,w:width};if(side==='bottom')return {...bay,h:width};return {...bay,y:bay.y+bay.h-width,h:width};}
export function proposeBay(records,m){
 if(!m.bays?.length||!m.unitsConfirmed||!m.units)throw new Error('단위를 확인하고 Bay 경계를 등록하세요.');
 const result=structuredClone(records),initial=inspectDrawing(records,m);if(initial.issues.some(i=>['parser','unsupported','layers','boxes','limit','code','repair'].includes(i.type)))throw new Error('레이어·BOX·변환 검수를 먼저 완료하세요.');
 const items=initial.items,grouped=new Set((m.groups||[]).flatMap(g=>g.memberIds)),placed=[],moves=[],obstacles=items.filter(i=>i.category==='aisle'&&i.closed&&i.bounds),candidates=[...footprints(items,m),...items.filter(i=>!grouped.has(i.id)&&i.bounds&&['panel','vmb','rack','pipe','duct'].includes(i.category))];
 if(candidates.length>200)throw new Error('자동 제안은 한 번에 200개 배치 객체까지 지원합니다. Bay별 DWG로 나누세요.');let attempts=0;
 for(const item of candidates.sort((a,b)=>Number(!!b.data._locked)-Number(!!a.data._locked)||(b.bounds.w*b.bounds.h)-(a.bounds.w*a.bounds.h))){
  if(item.data._locked){if(!m.bays.some(b=>contains(b,item.bounds)))throw new Error(`고정 객체 ${item.handle}의 Bay 경계를 먼저 확인하세요.`);placed.push(item);continue;}
  const options=[];
  for(const bay of m.bays){const lane=serviceLane(bay),area=item.category==='box'?bay:lane||bay,step=Math.max((m.clearance||0),Math.min(area.w,area.h)/30),xs=new Set([item.bounds.x]),ys=new Set([item.bounds.y]);
   for(let x=area.x;x<=area.x+area.w-item.bounds.w+1e-6;x+=step)xs.add(x);for(let y=area.y;y<=area.y+area.h-item.bounds.h+1e-6;y+=step)ys.add(y);
   for(const x of xs)for(const y of ys){if(++attempts>1500000)throw new Error('배치 탐색 한도에 도달했습니다. Bay·객체 범위를 줄여주세요.');const b={...item.bounds,x,y,maxX:x+item.bounds.w,maxY:y+item.bounds.h};if(!contains(area,b))continue;if(item.category==='box'&&(placed.some(p=>p.category==='box'&&overlap(b,p.bounds,m.clearance||0))||obstacles.some(p=>overlap(b,p.bounds))||(lane&&overlap(b,{...lane,maxX:lane.x+lane.w,maxY:lane.y+lane.h}))))continue;options.push({x,y,cost:Math.hypot(x-item.bounds.x,y-item.bounds.y)});}
  }
  options.sort((a,b)=>a.cost-b.cost);if(!options.length)throw new Error(`Bay에 ${item.handle}을 배치할 공간을 찾지 못했습니다.`);const p=options[0],dx=p.x-item.bounds.x,dy=p.y-item.bounds.y;
  if(Math.hypot(dx,dy)>1e-6)for(const memberId of [...(item.memberIds||[item.id]),...(m.codeLinks||[]).filter(l=>l.boxId===item.id).map(l=>l.entityId)]){const r=result.find(r=>r.id===memberId);r.data._placement={x:(r.data._placement?.x||0)+dx,y:(r.data._placement?.y||0)+dy};moves.push({id:r.id,handle:r.handle,dx,dy});}placed.push({...item,bounds:{...item.bounds,x:p.x,y:p.y,maxX:p.x+item.bounds.w,maxY:p.y+item.bounds.h}});
 }
 const check=inspectDrawing(result,m);if(check.issues.length)throw new Error(`대안 재검사 ${check.issues.length}건 미충족: ${check.issues[0].message}`);return {records:result,moves};
}
