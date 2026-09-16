import {viewItems,footprints,roleOf} from './cad-model.mjs';

export const defaultCodeAliases='건설코드,CONSTRUCTION_CODE,BUILD_CODE,EQUIPMENT_CODE,설비코드';
const distance=(a,b)=>Math.hypot(a.x-b.x,a.y-b.y);
const validPoint=p=>p&&Number.isFinite(p.x)&&Number.isFinite(p.y);
const key=s=>String(s).normalize('NFKC').replace(/[\s_-]/g,'').toLowerCase();
const code=s=>typeof s==='string'?s.normalize('NFKC').trim():'';
const looksLikeCode=s=>s.length>=3&&s.length<=80&&/^[\p{L}\p{N}_./-]+$/u.test(s)&&/\p{L}/u.test(s)&&/\p{N}/u.test(s);
const cross=(a,b,c)=>(b.x-a.x)*(c.y-a.y)-(b.y-a.y)*(c.x-a.x);
function simplePolygon(v,tolerance){
 if(v.length<3||v.some(p=>!validPoint(p)))return false;
 let area=0;for(let i=0;i<v.length;i++){const a=v[i],b=v[(i+1)%v.length];if(distance(a,b)<=Math.max(1e-9,tolerance*.01))return false;area+=a.x*b.y-b.x*a.y;}
 if(Math.abs(area)<Math.max(1e-12,tolerance*tolerance))return false;
 for(let i=0;i<v.length;i++)for(let j=i+1;j<v.length;j++){
  if(j===i+1||(i===0&&j===v.length-1))continue;
  const a=v[i],b=v[(i+1)%v.length],c=v[j],d=v[(j+1)%v.length];
  if(Math.max(a.x,b.x)+1e-9<Math.min(c.x,d.x)||Math.max(c.x,d.x)+1e-9<Math.min(a.x,b.x)||Math.max(a.y,b.y)+1e-9<Math.min(c.y,d.y)||Math.max(c.y,d.y)+1e-9<Math.min(a.y,b.y))continue;
  if(cross(a,b,c)*cross(a,b,d)<=0&&cross(c,d,a)*cross(c,d,b)<=0)return false;
 }
 return true;
}
function aliasValues(data,aliases){
 const hits=[];let visited=0;
 const walk=(o,path,depth)=>{if(!o||typeof o!=='object'||depth>6||++visited>2000)return;
  if(typeof (o.tag||o.attrTag)==='string'&&aliases.has(key(o.tag||o.attrTag))){const value=code(typeof o.text==='object'?o.text.text:o.text??o.value);if(value)hits.push({value,path:`${path}.${o.tag||o.attrTag}`});}
  for(const [k,v] of Object.entries(o)){if(k==='vertices'||k==='entities'||k==='blocks'||k==='header')continue;if(aliases.has(key(k))&&typeof v==='string'&&code(v))hits.push({value:code(v),path:`${path}.${k}`});if(v&&typeof v==='object')walk(v,`${path}.${k}`,depth+1);}
 };walk(data,'data',0);return hits;
}
function rectDistance(p,b){return Math.hypot(Math.max(b.x-p.x,0,p.x-b.maxX),Math.max(b.y-p.y,0,p.y-b.maxY));}
function rectangular(item){const paths=item.primitives?.filter(p=>p.kind==='path'&&p.closed)||[];if(item.type==='BOX_GROUP')return !!item._repairRectangle;if(paths.length!==1)return false;const p=paths[0].points,b=item.bounds;return p.every(q=>(Math.abs(q.x-b.x)<1e-6||Math.abs(q.x-b.maxX)<1e-6)&&(Math.abs(q.y-b.y)<1e-6||Math.abs(q.y-b.maxY)<1e-6));}

// Proposals only. Original entities and the original DWG are never modified here.
export function proposeBoxRepairs(input,metadata,settings){
 const tolerance=Number(settings.tolerance),searchDistance=Number(settings.searchDistance);
 if(!metadata.unitsConfirmed||!metadata.units)throw new Error('도면 단위를 먼저 확인하세요. 허용오차는 도면 단위입니다.');
 if(!Number.isFinite(tolerance)||tolerance<0||!Number.isFinite(searchDistance)||searchDistance<0)throw new Error('선 틈 허용오차와 코드 검색거리를 확인하세요.');
 const records=structuredClone(input),m=structuredClone(metadata),changes=[],warnings=[],changed=new Set(),aliases=new Set((settings.aliases||defaultCodeAliases).split(',').map(key));aliases.add('constructioncode');
 const note=(ids,type,detail)=>{ids.forEach(id=>changed.add(id));changes.push({ids,type,detail});};
 const grouped=new Set((m.groups||[]).flatMap(g=>g.memberIds));
 const candidates=records.filter(r=>r.space==='model'&&roleOf(r,m)==='box'&&!grouped.has(r.id));
 if(candidates.length>1200)throw new Error('BOX 자동 정리는 한 번에 1,200개 원시 형상까지 지원합니다. Bay별로 나눠주세요.');
 for(const r of candidates.filter(r=>r.type==='LWPOLYLINE'&&!(r.data.flag&1))){
  const v=r.data.vertices||[];
  if(v.length<4||v.length>128||v.some(p=>!validPoint(p)||p.bulge)||(r.data.flag&6))continue;
  const gap=distance(v[0],v.at(-1));if(gap>tolerance){warnings.push(`${r.handle}: 닫힘 틈 ${gap.toFixed(4)} — 허용오차 초과`);continue;}
  if(r.data._locked){warnings.push(`${r.handle}: 고정 객체 — 선 연결 수정 제외`);continue;}
  const points=v.slice(0,-1).map(p=>({...p}));points[0]={...points[0],x:(v[0].x+v.at(-1).x)/2,y:(v[0].y+v.at(-1).y)/2};
  if(!simplePolygon(points,tolerance)){warnings.push(`${r.handle}: 자기교차·퇴화 형상 — 자동 닫기 제외`);continue;}
  r.data.vertices=points;if(r.data.numberOfVertices!==undefined)r.data.numberOfVertices=points.length;r.data.flag=(r.data.flag||0)|1;note([r.id],'선 연결',`${r.handle}: 끝점 틈 ${gap.toFixed(4)} 닫기`);
 }
 const lines=candidates.filter(r=>r.type==='LINE'&&validPoint(r.data.startPoint)&&validPoint(r.data.endPoint)&&Math.abs((r.data.startPoint.z||0)-(r.data.endPoint.z||0))<1e-8);
 const ends=lines.flatMap((r,index)=>{const off=r.data._placement||{x:0,y:0};return ['startPoint','endPoint'].map(field=>({index,field,x:r.data[field].x+off.x,y:r.data[field].y+off.y,z:r.data[field].z||0}));});
 const peers=ends.map(()=>[]);for(let i=0;i<ends.length;i++)for(let j=i+1;j<ends.length;j++)if(ends[i].index!==ends[j].index&&lines[ends[i].index].layer===lines[ends[j].index].layer&&Math.abs(ends[i].z-ends[j].z)<1e-8&&distance(ends[i],ends[j])<=tolerance+1e-10){peers[i].push(j);peers[j].push(i);}
 const visited=new Set();let groupNumber=0;
 for(let start=0;start<lines.length;start++){
  if(visited.has(start))continue;const queue=[start],component=new Set();while(queue.length){const n=queue.pop();if(component.has(n))continue;component.add(n);for(const e of [n*2,n*2+1])for(const p of peers[e])queue.push(ends[p].index);}
  component.forEach(n=>visited.add(n));const members=[...component].map(n=>lines[n]);
  if(component.size<3||component.size>128||[...component].some(n=>peers[n*2].length!==1||peers[n*2+1].length!==1)||members.some(r=>r.data._locked)){warnings.push(`${members.map(r=>r.handle).slice(0,3).join(', ')}: 분기·미연결·고정 선 — 수동 확인`);continue;}
  const polygon=[];let e=start*2;const sequence=[];
  do{const match=peers[e][0],a=ends[e],b=ends[match];polygon.push({x:(a.x+b.x)/2,y:(a.y+b.y)/2});sequence.push([e,match]);e=match^1;}while(e!==start*2&&sequence.length<=component.size);
  if(e!==start*2||sequence.length!==component.size||!simplePolygon(polygon,tolerance)){warnings.push(`${members[0].handle}: 교차·중복 선 — 자동 연결 제외`);continue;}
  let maxMove=0;for(let i=0;i<sequence.length;i++)for(const index of sequence[i]){const endpoint=ends[index],r=lines[endpoint.index],off=r.data._placement||{x:0,y:0};maxMove=Math.max(maxMove,distance(endpoint,polygon[i]));r.data[endpoint.field]={...r.data[endpoint.field],x:polygon[i].x-off.x,y:polygon[i].y-off.y};}
  let groupId;do{groupId=`repair-box-${++groupNumber}`;}while(m.groups.some(g=>g.id===groupId));
  const x=Math.min(...polygon.map(p=>p.x)),y=Math.min(...polygon.map(p=>p.y)),maxX=Math.max(...polygon.map(p=>p.x)),maxY=Math.max(...polygon.map(p=>p.y));
  m.groups.push({id:groupId,name:`연결 BOX ${groupNumber}`,memberIds:members.map(r=>r.id),repairRectangle:polygon.every(p=>(Math.abs(p.x-x)<1e-6||Math.abs(p.x-maxX)<1e-6)&&(Math.abs(p.y-y)<1e-6||Math.abs(p.y-maxY)<1e-6))});
  note(members.map(r=>r.id),'선 연결',`${members.length}개 선 → 닫힌 BOX 그룹 · 최대 이동 ${maxMove.toFixed(4)}`);
 }
 const items=viewItems(records,m),boxes=footprints(items,m).map(b=>({...b,_repairRectangle:m.groups.find(g=>g.id===b.id)?.repairRectangle}));
 const boxData=boxes.map(box=>{const members=records.filter(r=>(box.memberIds||[box.id]).includes(r.id));const hits=members.flatMap(r=>aliasValues(r.data,aliases).map(h=>({...h,recordId:r.id}))),values=[...new Set(hits.map(h=>h.value))];return {box,members,hits,values,assigned:values.length===1?values[0]:null,blocked:values.length>1};});
 const texts=[];for(const r of records.filter(r=>r.space==='model')){
  const append=(data,attributeIndex=null)=>{const t=typeof data.text==='object'?data.text:data,p=t.startPoint||t.insertionPoint,text=code(t.text);if(!validPoint(p)||!looksLikeCode(text))return;const off=r.data._placement||{x:0,y:0};texts.push({r,t,text,attributeIndex,x:p.x+off.x,y:p.y+off.y,pointField:t.startPoint?'startPoint':'insertionPoint',height:Math.max(.001,t.textHeight||1)});};
  if(['TEXT','MTEXT','ATTRIB'].includes(r.type))append(r.data);if(r.type==='INSERT')for(const [i,a] of (r.data.attribs||[]).entries())append(a,i);
 }
 for(const b of boxData)if(b.assigned&&texts.some(t=>rectDistance(t,b.box.bounds)===0&&t.text!==b.assigned)){b.blocked=true;warnings.push(`${b.box.handle}: 속성 코드와 BOX 내부 문자 코드 불일치`);}
 const matches=new Map();for(const t of texts){const fitting=boxData.filter(b=>!b.blocked&&(!b.assigned||b.assigned===t.text)&&rectDistance(t,b.box.bounds)<=searchDistance&&(!(t.r.type==='INSERT')||b.members.some(r=>r.id===t.r.id)));
  if(fitting.length===1){const b=fitting[0];if(!matches.has(b))matches.set(b,[]);matches.get(b).push(t);}else if(fitting.length>1)warnings.push(`${t.text}: 가까운 BOX가 ${fitting.length}개 — 자동 귀속 제외`);
 }
 for(const b of boxData){if(b.blocked){warnings.push(`${b.box.handle}: 속성란의 건설코드 충돌 (${b.values.join(', ')})`);continue;}const nearby=matches.get(b)||[],values=[...new Set([...(b.assigned?[b.assigned]:[]),...nearby.map(t=>t.text)])];
  if(values.length===1)b.assigned=values[0];else{b.blocked=true;warnings.push(`${b.box.handle}: ${values.length?'여러 건설코드 후보':'건설코드 누락'} — 수동 확인`);}}
 const counts=new Map();for(const b of boxData)if(b.assigned&&!b.blocked)counts.set(b.assigned,(counts.get(b.assigned)||0)+1);
 for(const b of boxData){if(b.blocked)continue;if(settings.uniqueCodes&&counts.get(b.assigned)>1){warnings.push(`${b.assigned}: 서로 다른 BOX의 중복 코드 — 자동 정리 제외`);continue;}
  const modified=b.members.filter(r=>r.data._constructionCode!==b.assigned);if(modified.length){for(const r of modified)r.data._constructionCode=b.assigned;note(modified.map(r=>r.id),'코드 정규화',`${b.box.handle}: ${b.assigned} → 공통 건설코드 필드`);}
  const labels=(matches.get(b)||[]).filter(t=>t.text===b.assigned);if(labels.length>1){warnings.push(`${b.assigned}: 중복 문자 — 위치 자동 수정 제외`);continue;}
  for(const t of labels){m.codeLinks=m.codeLinks||[];if(t.attributeIndex===null&&!m.codeLinks.some(l=>l.boxId===b.box.id&&l.entityId===t.r.id))m.codeLinks.push({boxId:b.box.id,entityId:t.r.id});const bb=b.box.bounds,w=t.text.length*t.height*.6,h=t.height,inside=t.x>=bb.x&&t.y>=bb.y&&t.x+w<=bb.maxX&&t.y+h<=bb.maxY;if(inside)continue;
   if(t.r.data._locked||!rectangular(b.box)||w>bb.w*.9||h>bb.h*.9||Math.abs(t.t.rotation||0)>1e-8||(t.t.halign||0)!==0||(t.t.valign||0)!==0||t.r.type==='MTEXT'){warnings.push(`${t.text}: 문자 크기·회전·BOX 형상·고정 상태를 확인하세요.`);continue;}
   const target={x:bb.x+(bb.w-w)/2,y:bb.y+(bb.h-h)/2};if(t.attributeIndex===null){t.r.data._placement={x:(t.r.data._placement?.x||0)+target.x-t.x,y:(t.r.data._placement?.y||0)+target.y-t.y};}else{const p=t.t[t.pointField];t.t[t.pointField]={...p,x:p.x+target.x-t.x,y:p.y+target.y-t.y};}
   note([t.r.id],'코드 위치',`${t.text}: BOX 내부로 이동 (문자 폭은 근사값, 원본 대조 필요)`);
  }
 }
 m.repairFindings=warnings.slice(0,1000);m.repairFindingCount=warnings.length;m.requireConstructionCodes=true;m.repairSettings={tolerance,searchDistance,aliases:settings.aliases||defaultCodeAliases,uniqueCodes:!!settings.uniqueCodes};
 return {records,metadata:m,changes,warnings,changedIds:[...changed],boxCount:boxes.length};
}
