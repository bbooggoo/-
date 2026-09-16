export function captureNativeEntities(lib, ptr) {
  const entities = [];
  const failures = [];
  const count = lib.dwg_get_num_objects(ptr);
  if(count>100000)throw new Error("DWG 내부 객체가 100,000개를 넘습니다. Bay별로 분리해 주세요.");
  const hex = n => Number(n).toString(16).toUpperCase();
  for (let index = 0; index < count; index++) {
    try {
      const obj = lib.dwg_get_object(ptr, index);
      if (!obj) { failures.push({index,reason:'null-object'}); continue; }
      if (lib.dwg_object_get_supertype(obj) !== 0) continue;
      const entity = lib.dwg_object_to_entity(obj);
      entities.push({
        index,
        handle: hex(lib.dwg_object_get_handle_object(obj).value),
        ownerHandle: entity ? hex(lib.dwg_object_entity_get_ownerhandle_object(entity).absolute_ref) : null,
        nativeType: lib.dwg_object_get_dxfname(obj),
        fixedType: lib.dwg_object_get_fixedtype(obj)
      });
    } catch (error) { failures.push({index,reason:String(error)}); }
  }
  return {objectCount:count,nativeEntityCount:lib.dwg_get_num_entities(ptr),entities,failures};
}

export function compareNativeEntities(native, database) {
  const convertedHandles = new Set();
  const convertedEntities = new Map();
  const visit = entity => {
    if (entity?.handle) {
      const key = String(entity.handle).toUpperCase();
      convertedHandles.add(key);
      convertedEntities.set(key, entity);
    }
    (entity?.attribs || []).forEach(visit);
    (entity?.vertices || []).forEach(visit);
  };
  database.entities.forEach(visit);
  database.tables.BLOCK_RECORD.entries.forEach(block => block.entities.forEach(visit));
  const markers = new Set(['BLOCK','ENDBLK','SEQEND']);
  const embeddedVertex = new Set(['VERTEX_2D','VERTEX_3D','VERTEX']);
  const nativeVertexCounts = new Map();
  native.entities.filter(e => embeddedVertex.has(e.nativeType) && [10,11].includes(e.fixedType)).forEach(e => {
    nativeVertexCounts.set(e.ownerHandle, (nativeVertexCounts.get(e.ownerHandle) || 0) + 1);
  });
  const missing = native.entities.filter(e => {
    if (convertedHandles.has(e.handle) || markers.has(e.nativeType)) return false;
    // Two known vertex types are folded into converted polyline geometry. This
    // does not exempt mesh/polyface parents: those remain detectable omissions.
    const parent = convertedEntities.get(e.ownerHandle);
    if (embeddedVertex.has(e.nativeType) && [10,11].includes(e.fixedType) && parent &&
        ['POLYLINE2D','POLYLINE3D'].includes(parent.type) &&
        parent.vertices?.length >= nativeVertexCounts.get(e.ownerHandle)) return false;
    return true;
  });
  return {convertedHandleCount:convertedHandles.size,missing,failures:native.failures};
}
