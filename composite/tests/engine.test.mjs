import test from 'node:test';
import assert from 'node:assert/strict';
import {sample,overlap,distance,inspect,autoLayout} from '../dist/engine.mjs';
const a={id:'A',name:'A',x:1,y:1,w:2,h:2,locked:false};
test('contact is allowed at zero clearance; containment is overlap',()=>{
 assert.equal(overlap(a,{...a,x:3}),false);
 assert.equal(overlap(a,{...a,x:1.5,y:1.5,w:.5,h:.5}),true);
 assert.equal(inspect([a,{...a,id:'B',x:3}],0).length,0);
 assert.equal(inspect([a,{...a,id:'B',x:3}],1)[0].type,'clearance');
});
test('exact threshold and diagonal shortest distance',()=>{
 const b={...a,id:'B',x:4,y:3};
 assert.equal(inspect([a,b],1).length,0);
 assert.equal(inspect([a,{...b,x:3.999}],1).length,1);
 assert.ok(Math.abs(distance(a,{...b,x:4,y:4})-Math.SQRT2)<1e-9);
});
test('boundary and aisle are detected',()=>{
 assert.ok(inspect([{...a,x:-.1}],0).some(i=>i.type==='boundary'));
 assert.ok(inspect([{...a,y:17}],0).some(i=>i.b==='AISLE'));
});
test('auto layout resolves demo, preserves locks, is deterministic and does not mutate source',()=>{
 const original=sample(),before=structuredClone(original),result=autoLayout(original,1);
 assert.equal(inspect(original,1).length,6);
 assert.equal(result.ok,true);
 assert.equal(inspect(result.items,1).length,0);
 assert.deepEqual(original,before);
 assert.deepEqual(result.items.find(i=>i.locked),before.find(i=>i.locked));
 assert.deepEqual(autoLayout(original,1),result);
 assert.equal(autoLayout(result.items,1).moved,0);
});
test('fixed collisions and no-fit search leave original layout intact',()=>{
 for(const items of [[{...a,locked:true},{...a,id:'B',locked:true}],[{...a,w:60,h:36}]]){
  const before=structuredClone(items),result=autoLayout(items,1);
  assert.equal(result.ok,false);assert.deepEqual(result.items,before);assert.deepEqual(items,before);
 }
});
