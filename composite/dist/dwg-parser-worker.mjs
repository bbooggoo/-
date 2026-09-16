// GPL-3.0 parser runs in its own worker; sources and notices are linked in the UI.
import {captureNativeEntities,compareNativeEntities} from './native-audit.mjs';
import {LibreDwg} from '@mlightcad/libredwg-web';
import {normalizeDatabase,MAX_BYTES} from './cad-model.mjs';
self.onmessage=async ({data:{bytes}})=>{
 let lib,ptr;
 try{
  if(!(bytes instanceof ArrayBuffer)||bytes.byteLength>MAX_BYTES)throw new Error('20 MB 이하 DWG 파일이 필요합니다.');
  if(!/^AC10\d\d$/.test(new TextDecoder().decode(bytes.slice(0,6))))throw new Error('파일 확장자와 DWG 서명이 일치하지 않습니다.');
  self.postMessage({stage:'DWG 변환 엔진 로딩'});lib=await LibreDwg.create(new URL('./vendor',self.location.href).href);
  lib.FS.writeFile('input.dwg',new Uint8Array(bytes));self.postMessage({stage:'DWG 객체·레이어 추출'});
  const result=lib.dwg_read_file('input.dwg');ptr=result.data;
  if(result.error&8192){lib.dwg_abandon(ptr);ptr=null;throw new Error('DWG 변환 메모리가 부족합니다. Bay별 도면으로 분리해 주세요.');}
  if(!ptr||result.error>=128)throw new Error(`DWG를 해석하지 못했습니다 (코드 ${result.error}).`);
  const native=captureNativeEntities(lib,ptr),{database,stats}=lib.convertEx(ptr),version=lib.dwg_get_version_type(ptr),audit=compareNativeEntities(native,database);
  const payload=normalizeDatabase(database,{parser:'@mlightcad/libredwg-web 0.7.10',version,readError:result.error,unknownEntityCount:stats.unknownEntityCount,auditMissingCount:audit.missing.length,auditFailures:audit.failures.length,auditMissing:audit.missing.slice(0,200)});
  self.postMessage({payload});
 }catch(error){self.postMessage({error:error.message||'DWG 추출 실패'});}finally{if(lib&&ptr)lib.dwg_free(ptr);if(lib?.FS.analyzePath('input.dwg').exists)lib.FS.unlink('input.dwg');}
};
