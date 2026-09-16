// Illustrative orthogonal envelopes. No company-specific design standards or DWG parser.
export const disciplines={pipe:{label:'배관',color:'#67e8ba',band:[3.7,4.7]},duct:{label:'덕트',color:'#79b9f5',band:[4.8,6.5]},tray:{label:'트레이',color:'#edc878',band:[6.7,7.8]}};
export const clone=value=>structuredClone(value);
const eps=1e-7,axes=[['x','sizeX'],['y','sizeY'],['z','sizeZ']];
export function sampleComposite(){
 const specs=[['PIPE-01','pipe',4,5,4,28,.5,.5,true,'UPW-A',35],['PIPE-02','pipe',7,5.2,4.2,15,.5,.5,false,'UPW-A',20],['DUCT-01','duct',16,2,4.1,3,20,1.2,false,'EXH-A',160],['DUCT-02','duct',32,4,5.1,3,22,1.2,false,'EXH-A',200],['TRAY-01','tray',3,8,4.2,34,.8,.4,false,'POWER-A',40],['TRAY-02','tray',25,10,6.2,25,.8,.4,false,'POWER-A',50]];
 return {bounds:{x:60,y:36,z:8},clearance:.2,bands:Object.fromEntries(Object.entries(disciplines).map(([k,v])=>[k,[...v.band]])),objects:specs.map(([id,kind,x,y,z,sizeX,sizeY,sizeZ,locked,pocId,demand])=>({id,kind,x,y,z,sizeX,sizeY,sizeZ,locked,hold:false,pocId,demand,bay:'SUBFAB-A',layer:`DEMO_${kind.toUpperCase()}`,sourceRevision:'DWG-R01 (예시)',owner:disciplines[kind].label})),obstacles:[{id:'유지보수 통로',x:0,y:16,z:0,sizeX:60,sizeY:4,sizeZ:3.2},...[10,30,50].map(x=>({id:`기둥-${x}`,x,y:28,z:0,sizeX:1.2,sizeY:1.2,sizeZ:8}))],supplies:[{id:'UPW-A',kind:'pipe',x:0,y:6,z:4,capacity:100,unit:'L/min'},{id:'EXH-A',kind:'duct',x:30,y:36,z:5.5,capacity:500,unit:'m³/min'},{id:'POWER-A',kind:'tray',x:60,y:18,z:7,capacity:120,unit:'kW'}]};
}
export function overlap3D(a,b){return axes.every(([p,s])=>Math.min(a[p]+a[s],b[p]+b[s])-Math.max(a[p],b[p])>eps);}
export function gap3D(a,b){return Math.hypot(...axes.map(([p,s])=>Math.max(0,a[p]-b[p]-b[s],b[p]-a[p]-a[s])));}
const finite=n=>typeof n==='number'&&Number.isFinite(n);
function validateBox(o){return o&&typeof o.id==='string'&&axes.every(([p,s])=>finite(o[p])&&finite(o[s])&&o[s]>0);}
export function validateModel(m){
 if(!m||!m.bounds||!['x','y','z'].every(p=>finite(m.bounds[p])&&m.bounds[p]>0)||!finite(m.clearance)||m.clearance<0||!Array.isArray(m.objects)||!Array.isArray(m.obstacles)||!Array.isArray(m.supplies))throw new Error('모델 크기·최소 이격·객체 형식이 올바르지 않습니다.');
 if(!m.bands||!Object.keys(disciplines).every(k=>Array.isArray(m.bands[k])&&m.bands[k].length===2&&m.bands[k].every(finite)&&m.bands[k][0]>=0&&m.bands[k][1]>m.bands[k][0]&&m.bands[k][1]<=m.bounds.z))throw new Error('공종 높이 구간을 확인하세요.');
 if(!m.objects.every(o=>validateBox(o)&&disciplines[o.kind]&&finite(o.demand)&&o.demand>=0&&typeof o.locked==='boolean'&&typeof o.hold==='boolean')||!m.obstacles.every(validateBox))throw new Error('객체 좌표·크기·수요를 확인하세요.');
 if(!m.supplies.every(s=>s&&typeof s.id==='string'&&disciplines[s.kind]&&['x','y','z'].every(p=>finite(s[p])&&s[p]>=0&&s[p]<=m.bounds[p])&&finite(s.capacity)&&s.capacity>=0))throw new Error('UT 공급점·용량을 확인하세요.');
 for(const list of [[...m.objects,...m.obstacles],m.supplies])if(new Set(list.map(o=>o.id)).size!==list.length)throw new Error('중복 객체 ID입니다.');
 return true;
}
function geometryIssues(o,others,m){
 const issues=[],add=(type,b,message)=>issues.push({type,a:o.id,b,message});
 if(axes.some(([p,s])=>o[p]<-eps||o[p]+o[s]>m.bounds[p]+eps))add('boundary','영역','영역 경계 초과');
 const [lo,hi]=m.bands[o.kind];if(o.z<lo-eps||o.z+o.sizeZ>hi+eps)add('band',o.kind,`공종 높이 구간 ${lo}–${hi} m 위반`);
 for(const b of others){if(overlap3D(o,b))add('clash',b.id,'체적 겹침');else if(gap3D(o,b)<m.clearance-eps)add('clearance',b.id,`최소 이격 ${m.clearance} m 미달`);}
 return issues;
}
export function utMatrix(m){return m.supplies.map(s=>{const connected=m.objects.filter(o=>o.pocId===s.id&&o.kind===s.kind),used=connected.reduce((v,o)=>v+o.demand,0);return {...s,used,remaining:s.capacity-used,objects:connected.map(o=>o.id)};});}
export function inspectComposite(m){
 validateModel(m);const issues=[];
 m.objects.forEach((o,i)=>{issues.push(...geometryIssues(o,[...m.obstacles,...m.objects.slice(0,i)],m));const s=m.supplies.find(s=>s.id===o.pocId);if(!s)issues.push({type:'ut-missing',a:o.id,b:o.pocId||'미연결',message:'UT 공급점 미연결'});else if(s.kind!==o.kind)issues.push({type:'ut-kind',a:o.id,b:s.id,message:'UT 공급 공종 불일치'});});
 for(const row of utMatrix(m))if(row.remaining<-eps)issues.push({type:'ut-capacity',a:row.id,b:row.objects.join(', '),message:`UT 수요 ${row.used} > 공급 ${row.capacity} ${row.unit}`});
 return issues;
}
// Minimum Manhattan distance to an envelope, a comparison proxy, not a routed length.
export function connectionDistance(o,s){return axes.reduce((sum,[p,size])=>sum+Math.max(0,o[p]-s[p],s[p]-o[p]-o[size]),0);}
export function metrics(m,baseline=m){return {moved:m.objects.filter((o,i)=>axes.some(([p])=>Math.abs(o[p]-baseline.objects[i][p])>eps)).length,movement:m.objects.reduce((v,o,i)=>v+Math.hypot(...axes.map(([p])=>o[p]-baseline.objects[i][p])),0),connection:m.objects.reduce((v,o)=>{const s=m.supplies.find(s=>s.id===o.pocId);return v+(s?connectionDistance(o,s):0);},0),issues:inspectComposite(m).length};}
export const fingerprint=m=>JSON.stringify(m);
export function proposeComposite(model,strategy='movement'){
 validateModel(model);if(!['movement','connection'].includes(strategy))throw new Error('알 수 없는 대안 기준');
 const base=clone(model),result=clone(model),source=fingerprint(model),fixed=result.objects.filter(o=>o.locked||o.hold),placed=[...fixed];
 const fail=reason=>({ok:false,strategy,source,reason,model:base,metrics:metrics(base)});
 if(inspectComposite(model).some(i=>i.type.startsWith('ut-')))return fail('UT 연결·공급 용량을 먼저 수정하세요.');
 for(let i=0;i<fixed.length;i++)if(geometryIssues(fixed[i],[...model.obstacles,...fixed.slice(0,i)],model).length)return fail('고정 또는 Hold 객체의 위반을 먼저 검토하세요.');
 const moving=result.objects.filter(o=>!o.locked&&!o.hold).sort((a,b)=>b.sizeX*b.sizeY*b.sizeZ-a.sizeX*a.sizeY*a.sizeZ||a.id.localeCompare(b.id));
 const offsets=[0,-1,1,-3,3,-6,6,-10,10];
 for(const o of moving){
  const [lo,hi]=model.bands[o.kind],s=model.supplies.find(s=>s.id===o.pocId),zs=new Set([o.z,lo,hi-o.sizeZ]);for(let z=lo;z<=hi-o.sizeZ+eps;z+=.2)zs.add(+z.toFixed(4));
  let best=null,score=Infinity;
  for(const dx of offsets)for(const dy of offsets)for(const z of zs){const trial={...o,x:o.x+dx,y:o.y+dy,z};if(geometryIssues(trial,[...model.obstacles,...placed],model).length)continue;const move=Math.hypot(dx,dy,z-o.z),connection=connectionDistance(trial,s),value=strategy==='movement'?move+connection*.001:connection+move*.15;if(value<score-eps){best=trial;score=value;}}
  if(!best)return fail(`${o.id}: 제한된 탐색 범위에서 유효한 위치를 찾지 못했습니다.`);Object.assign(o,best);placed.push(o);
 }
 if(inspectComposite(result).length)return fail('전체 재검사 실패');
 return {ok:true,strategy,source,model:result,metrics:metrics(result,model)};
}
