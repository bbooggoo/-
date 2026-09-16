import test from 'node:test';
import assert from 'node:assert/strict';
import {workflow,drawingSource,reviewState,selectedView} from '../dist/workflow.mjs';
import {sample,inspect,autoLayout} from '../dist/engine.mjs';
test('workflow distinguishes DWG reading from pending rewriting',()=>{
 assert.equal(drawingSource.format,'DWG');assert.equal(drawingSource.nativeImport,true);assert.equal(drawingSource.nativeExport,false);
 assert.equal(workflow.find(s=>s.id==='normalize').status,'구현 · 후보 검토');assert.equal(workflow.find(s=>s.id==='issue').status,'연동 예정');
});
test('workflow review reflects the same engine result before and after layout',()=>{
 const original=sample();const initial=reviewState(inspect(original,1));assert.equal(initial.state,'needs-review');assert.match(initial.title,/6건/);
 const optimized=autoLayout(original,1);assert.equal(optimized.ok,true);const next=reviewState(inspect(optimized.items,1));assert.equal(next.state,'clear');assert.match(next.detail,/설계자/);
});
test('known workflow links select correct view; unknown hashes fall back to studio',()=>{
 assert.equal(selectedView('#workflow'),'workflow');assert.equal(selectedView('#composite'),'studio');for(const hash of ['', '#studio', '#unknown'])assert.equal(selectedView(hash),'studio');
});
