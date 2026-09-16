import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import path from 'node:path';
import {LibreDwg} from '@mlightcad/libredwg-web';
import {captureNativeEntities,compareNativeEntities} from '../dist/native-audit.mjs';
import {normalizeDatabase,geometry} from '../dist/cad-model.mjs';
test('real binary DWGs decode exact LINE coordinates and audit unsupported native types',async()=>{
 const lib=await LibreDwg.create(path.resolve('node_modules/@mlightcad/libredwg-web/wasm'));
 for(const filename of ['tests/fixtures/2018__Line.dwg','dist/sample_2018.dwg','tests/fixtures/example_2018.dwg']){
  const bytes=await readFile(filename);lib.FS.writeFile('test.dwg',bytes);const result=lib.dwg_read_file('test.dwg');assert.ok(result.data);assert.ok(result.error<128);
  try{const native=captureNativeEntities(lib,result.data),{database,stats}=lib.convertEx(result.data),audit=compareNativeEntities(native,database),p=normalizeDatabase(database,{readError:result.error,unknownEntityCount:stats.unknownEntityCount,auditMissingCount:audit.missing.length,auditFailures:audit.failures.length});
   if(filename.includes('Line')){assert.equal(database.entities.length,1);const e=database.entities[0];assert.equal(e.type,'LINE');assert.ok(Math.abs(e.startPoint.x-21.607766723)<1e-8);assert.equal(audit.missing.length,0);assert.equal(geometry(p.records[0],p.records,p.metadata).warnings.length,0);}
   if(filename.includes('sample')){assert.equal(database.entities.length,6);assert.equal(audit.missing.length,0);assert.equal(result.error,0);assert.equal(p.metadata.units,4);}
   if(filename.includes('example')){assert.equal(stats.unknownEntityCount,0);assert.equal(audit.missing.length,14);assert.ok(audit.missing.some(e=>e.nativeType==='REGION'));assert.equal(result.error,68);}
  }finally{lib.dwg_free(result.data);lib.FS.unlink('test.dwg');}
 }
});
