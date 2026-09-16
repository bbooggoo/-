import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile,readdir} from 'node:fs/promises';
import {Miniflare} from 'miniflare';
test('real D1/R2 API: authentication, ownership, import gating, immutable source, revisions, audit and review',async()=>{
 const mf=new Miniflare({modules:true,scriptPath:'dist/server/index.js',compatibilityDate:'2026-05-15',d1Databases:['DB'],r2Buckets:['BUCKET']});
 try{
  const db=await mf.getD1Database('DB');for(const file of (await readdir('drizzle')).filter(n=>n.endsWith('.sql'))){const sql=await readFile(`drizzle/${file}`,'utf8');await db.batch(sql.split('--> statement-breakpoint').map(s=>s.trim()).filter(Boolean).map(s=>db.prepare(s)));}
  const request=async(url,body,owner='owner-a')=>{const req=new Request(`https://example.test/api${url}`,{method:body===undefined?'GET':'POST',headers:{...(owner?{'oai-authenticated-user-id':owner}:{}),...(body instanceof FormData?{}:{'Content-Type':'application/json'})},body:body===undefined?undefined:body instanceof FormData?body:JSON.stringify(body)});return mf.dispatchFetch(req.url,{method:req.method,headers:Object.fromEntries(req.headers),body:body===undefined?undefined:await req.arrayBuffer()});};
  assert.equal((await request('/drawings',undefined,null)).status,401);
  assert.equal((await mf.dispatchFetch('https://example.test/api/drawings',{method:'POST',headers:{'oai-authenticated-user-id':'owner-a',origin:'https://other.test'}})).status,403);
  const metadata={units:4,unitsConfirmed:true,expectedBoxes:1,clearance:0,blocks:[],groups:[],codeLinks:[],layerMap:{},bays:[{name:'BAY-A',x:0,y:0,w:100,h:100}],readError:0,unknownEntityCount:0,auditMissingCount:0,auditFailures:0};
  const bytes=await readFile('dist/sample_2018.dwg'),form=new FormData();form.append('file',new Blob([bytes]),'test.dwg');form.append('manifest',JSON.stringify({metadata,count:1}));const created=await request('/drawings',form);assert.equal(created.status,201);const {id}=await created.json();
  assert.equal((await request(`/drawings/${id}/finish`,{})).status,409);
  assert.equal((await request(`/drawings/${id}`,undefined,'owner-b')).status,404);
  assert.equal((await request('/drawings',undefined,'owner-b')).status,200);
  assert.equal((await (await request('/drawings',undefined,'owner-b')).json()).drawings.length,0);
  const original={type:'LWPOLYLINE',handle:'ABC',layer:'BOX',flag:1,vertices:[{x:1,y:1},{x:11,y:1},{x:11,y:11},{x:1,y:11}]},r={type:original.type,handle:'ABC',layer:'BOX',space:'model',classification:'box',data:original};
  for(let i=0;i<2;i++)assert.equal((await request(`/drawings/${id}/entities`,{offset:0,records:[r]})).status,200);
  assert.equal((await request(`/drawings/${id}/finish`,{})).status,200);
  const records=(await (await request(`/drawings/${id}/entities`)).json()).entities;assert.equal(records.length,1);assert.equal(records[0].original,undefined);
  assert.deepEqual(Buffer.from(await (await request(`/drawings/${id}/original`)).arrayBuffer()),bytes);
  assert.equal((await request(`/drawings/${id}/review`,{revision:1})).status,200);
  const changed={id:records[0].id,version:1,data:{...original,_placement:{x:5,y:0},_constructionCode:'FAB-101'},layer:'BOX',classification:'box',notes:'QC memo'},change={revision:1,reason:'BOX/code repair',changes:[changed]};
  assert.equal((await request(`/drawings/${id}/change`,change)).status,200);
  assert.equal((await request(`/drawings/${id}/change`,change)).status,409);
  const stored=(await (await request(`/drawings/${id}`)).json()).drawing;assert.equal(stored.revision,2);assert.equal(stored.reviewed_revision,null);
  assert.deepEqual((await (await request(`/drawings/${id}/source?entity=${records[0].id}`)).json()).original,original);
  const edits=(await (await request(`/drawings/${id}/history`)).json()).edits,edit=edits.find(e=>e.reason==='BOX/code repair');assert.equal(JSON.parse(edit.after_data).notes,'QC memo');assert.equal(JSON.parse(edit.after_data).data._constructionCode,'FAB-101');
  assert.equal((await request(`/drawings/${id}/change`,{revision:2,reason:'invalid movement',changes:[{...changed,version:2,data:{...changed.data,_placement:{x:null,y:0}}}]})).status,400);
  assert.equal((await request(`/drawings/${id}/change`,{revision:2,reason:'forged group',changes:[],metadata:{...metadata,groups:[{id:'x',name:'x',memberIds:['missing-1','missing-2']}]}})).status,400);
  const outside={...changed,version:2,data:{...changed.data,_placement:{x:200,y:0}}};assert.equal((await request(`/drawings/${id}/change`,{revision:2,reason:'move outside',changes:[outside]})).status,200);assert.equal((await request(`/drawings/${id}/review`,{revision:3})).status,422);
 }finally{await mf.dispose();}
});
