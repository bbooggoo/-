import {room,fixedZones,sample,inspect,autoLayout} from './engine.mjs';
import {initProcess,updateProcess} from './process.mjs';
let items=sample(),selected=items[1].id,clearance=1,history=[],showClearance=false,drag=null;
const $=id=>document.getElementById(id),ns='http://www.w3.org/2000/svg';
function el(tag,attrs={},text){const n=document.createElementNS(ns,tag);for(const[k,v]of Object.entries(attrs))n.setAttribute(k,String(v));if(text!==undefined)n.textContent=text;return n;}
function flash(text){$('feedback').textContent=text;clearTimeout(flash.timer);flash.timer=setTimeout(()=>$('feedback').textContent='',6500);}
function remember(){history.push({items:structuredClone(items),clearance});if(history.length>30)history.shift();}
function choose(id){selected=id;render();}
function draw(issues){
 const svg=$('plan');svg.replaceChildren();
 const defs=el('defs');const grid=el('pattern',{id:'grid',width:1,height:1,patternUnits:'userSpaceOnUse'});grid.append(el('path',{d:'M 1 0 L 0 0 0 1',fill:'none',stroke:'#243c4a','stroke-width':.035}));defs.append(grid);const hatch=el('pattern',{id:'hatch',width:1,height:1,patternUnits:'userSpaceOnUse',patternTransform:'rotate(45)'});hatch.append(el('line',{x1:0,y1:0,x2:0,y2:1,stroke:'#476170','stroke-width':.14}));defs.append(hatch);svg.append(defs);
 svg.append(el('rect',{x:0,y:0,width:room.w,height:room.h,fill:'url(#grid)',stroke:'#8096a6','stroke-width':.1}));
 for(let x=0;x<=60;x+=10){svg.append(el('text',{x,y:-1,'text-anchor':'middle',fill:'#8ba1b1','font-size':.8},String(x)));}
 for(let y=0;y<=36;y+=6){svg.append(el('text',{x:-1,y:y+.25,'text-anchor':'end',fill:'#8ba1b1','font-size':.8},String(y)));}
 for(const z of fixedZones){svg.append(el('rect',{x:z.x,y:z.y,width:z.w,height:z.h,fill:z.kind==='aisle'?'#1c3340':'url(#hatch)',stroke:'#617785','stroke-width':.09,'stroke-dasharray':z.kind==='aisle'?'.5 .4':'0'}));if(z.kind==='aisle')svg.append(el('text',{x:30,y:18.35,'text-anchor':'middle',fill:'#91a7b5','font-size':.8,'letter-spacing':.1},'주 통로 · 4 m · 배치 금지'));}
 for(const a of items){
  const bad=issues.some(i=>i.a===a.id||i.b===a.id),active=a.id===selected;
  const g=el('g',{'data-id':a.id,class:`plan-object ${active?'selected':''}`,tabindex:0,role:'button','aria-label':`${a.id}, ${a.name}, ${a.x}, ${a.y} m${a.locked?', 고정':''}`});
  if(showClearance&&clearance>0)g.append(el('rect',{x:a.x-clearance/2,y:a.y-clearance/2,width:a.w+clearance,height:a.h+clearance,rx:clearance/2,fill:'#67e8ba',opacity:.08,stroke:'#67e8ba','stroke-width':.08,'stroke-dasharray':'.3 .25'}));
  g.append(el('rect',{class:'body',x:a.x,y:a.y,width:a.w,height:a.h,rx:.12,fill:bad?'#674448':'#2c5062',stroke:bad?'#f09282':'#91b9cc','stroke-width':.12}));
  g.append(el('path',{d:`M ${a.x+.4} ${a.y+.4} H ${a.x+a.w-.4} V ${a.y+a.h-.4} H ${a.x+.4} Z`,fill:'none',stroke:bad?'#956a6a':'#507889','stroke-width':.05}));
  g.append(el('text',{x:a.x+a.w/2,y:a.y+a.h/2-.15,'text-anchor':'middle',fill:'#f2f8fb','font-size':.68,'font-weight':500},a.id));
  g.append(el('text',{x:a.x+a.w/2,y:a.y+a.h/2+.9,'text-anchor':'middle',fill:bad?'#e5b1a8':'#a1bfce','font-size':.59},`${a.w} × ${a.h} m${a.locked?' · 고정':''}`));
  g.addEventListener('click',()=>choose(a.id));g.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();choose(a.id);}});svg.append(g);
 }
}
function render(){
 const issues=inspect(items,clearance),overlaps=issues.filter(i=>i.type==='overlap').length;
 $('equipment-count').innerHTML=`${items.length} <small>대</small>`;$('overlap-count').textContent=overlaps;$('clearance-count').textContent=issues.length-overlaps;$('area-count').innerHTML=`${(items.reduce((s,a)=>s+a.w*a.h,0)/2160*100).toFixed(1)} <small>%</small>`;
 $('object-count').textContent=`${items.length}개`;$('issue-total').textContent=`${issues.length}건`;$('undo').disabled=!history.length;$('clearance').value=clearance;
 $('equipment-list').replaceChildren();
 for(const a of items){const b=document.createElement('button');b.className=`equipment-item ${a.id===selected?'selected':''} ${issues.some(i=>i.a===a.id||i.b===a.id)?'has-issue':''}`;b.setAttribute('aria-pressed',String(a.id===selected));b.innerHTML=`<span class="equipment-swatch">▥</span><span class="equipment-label"><b>${a.id}</b><small>${a.name}</small></span>${a.locked?'<span class="fixed-badge">고정</span>':''}`;b.onclick=()=>choose(a.id);$('equipment-list').append(b);}
 $('issues').replaceChildren();
 issues.forEach((i,k)=>{const b=document.createElement('button');b.className=`issue-card ${i.type==='clearance'?'clearance':''}`;b.innerHTML=`<span class="issue-top"><span>${i.type==='overlap'?'영역 겹침':i.type==='boundary'?'경계 위반':'이격 부족'}</span><span>${String(k+1).padStart(2,'0')}</span></span><b>${i.a}${i.b?' / '+i.b:''}</b><p>${i.message}</p>`;b.onclick=()=>choose(i.a);$('issues').append(b);});
 if(!issues.length)$('issues').innerHTML='<div class="issue-empty"><span>✓</span><b>검출된 간섭이 없습니다</b><p>현재 2D 검사 조건을 충족합니다.</p></div>';
 const a=items.find(i=>i.id===selected);$('selected-name').textContent=a.id;for(const k of ['x','y','w','h'])$('properties').elements[k].value=a[k];$('properties').elements.locked.checked=a.locked;
 draw(issues);
 updateProcess(issues);
}
function optimize(){const result=autoLayout(items,clearance);if(!result.ok){flash(result.reason);return {ok:false,reason:result.reason};}remember();items=result.items;render();flash(`${result.moved}개 설비 이동 · 잔여 간섭 ${result.issues.length}건. 0.5 m 격자 기반 배치 제안입니다.`);return {ok:true,moved:result.moved,remainingIssues:result.issues.length};}
$('optimize').onclick=optimize;
$('undo').onclick=()=>{const prev=history.pop();if(prev){items=prev.items;clearance=prev.clearance;render();flash('직전 변경을 되돌렸습니다.');}};
$('reset').onclick=()=>{remember();items=sample();clearance=1;render();flash('예시 배치로 초기화했습니다. 실행 취소로 복원할 수 있습니다.');};
$('clearance-toggle').onclick=()=>{showClearance=!showClearance;$('clearance-toggle').setAttribute('aria-pressed',String(showClearance));render();};
$('clearance').onchange=e=>{const value=Number(e.target.value);if(!e.target.value||!Number.isFinite(value)||value<0||value>3){e.target.value=clearance;flash('최소 이격은 0~3 m 범위로 입력해 주세요.');return;}remember();clearance=value;render();};
$('properties').onsubmit=e=>{e.preventDefault();const form=e.currentTarget;const change={};for(const k of ['x','y','w','h']){change[k]=Number(form.elements[k].value);if(!Number.isFinite(change[k]))return;}if(change.w<.5||change.w>60||change.h<.5||change.h>36){flash('설비 크기를 확인해 주세요.');return;}const a=items.find(i=>i.id===selected);if(a.locked&&form.elements.locked.checked&&['x','y','w','h'].some(k=>a[k]!==change[k])){flash('위치 고정을 해제한 후 좌표·크기를 변경해 주세요.');render();return;}remember();Object.assign(a,change,{locked:form.elements.locked.checked});render();flash('설비 속성을 반영했습니다.');};
function point(event){const p=new DOMPoint(event.clientX,event.clientY);return p.matrixTransform($('plan').getScreenCTM().inverse());}
$('plan').addEventListener('pointerdown',e=>{const target=e.target.closest('[data-id]');if(!target)return;const a=items.find(i=>i.id===target.dataset.id);selected=a.id;if(a.locked){render();return;}const p=point(e);drag={id:a.id,start:structuredClone(items),dx:p.x-a.x,dy:p.y-a.y,moved:false};$('plan').setPointerCapture(e.pointerId);e.preventDefault();});
$('plan').addEventListener('pointermove',e=>{if(!drag)return;const a=items.find(i=>i.id===drag.id),p=point(e);const x=Math.round((p.x-drag.dx)*10)/10,y=Math.round((p.y-drag.dy)*10)/10;if(x!==a.x||y!==a.y){a.x=x;a.y=y;drag.moved=true;draw(inspect(items,clearance));}});
function endDrag(){if(!drag)return;if(drag.moved){history.push({items:drag.start,clearance});if(history.length>30)history.shift();}drag=null;render();}
$('plan').addEventListener('pointerup',endDrag);$('plan').addEventListener('pointercancel',()=>{if(drag){items=drag.start;drag=null;render();}});
$('export').onclick=()=>{
 const svg=$('plan').cloneNode(true);svg.setAttribute('xmlns',ns);svg.setAttribute('width','1320');svg.setAttribute('height','840');
 svg.insertBefore(el('rect',{x:-3,y:-3,width:66,height:42,fill:'#11232f'}),svg.firstChild);
 svg.append(el('text',{x:0,y:38,'font-size':.7,fill:'#afc5d0'},`COMPOSITE | FAB-01 Bay A | m | Clearance ${clearance} m | Issues ${inspect(items,clearance).length} | 2D DEMO`));
 for(const node of svg.querySelectorAll('[tabindex]')){node.removeAttribute('tabindex');node.removeAttribute('role');}
 const blob=new Blob(['<?xml version="1.0" encoding="UTF-8"?>\n',new XMLSerializer().serializeToString(svg)],{type:'image/svg+xml;charset=utf-8'});
 const url=URL.createObjectURL(blob),link=document.createElement('a');link.href=url;link.download='composite-fab-01-layout.svg';document.body.append(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);flash('SVG 도면 다운로드를 요청했습니다. CAD 원본 형식은 아닙니다.');
};
initProcess();
render();
const context=document.modelContext;
if(context?.registerTool){
 const lifecycle=new AbortController();
 const validate=input=>{if(!input||typeof input!=='object'||Array.isArray(input)||Object.keys(input).length)throw new Error('인수 없는 빈 객체를 사용해 주세요.');};
 const definitions=[
  {name:'inspect_fab_layout',title:'FAB 배치 및 간섭 읽기',description:'현재 탭의 설비 위치, 고정 상태와 2D 간섭 결과를 읽습니다.',inputSchema:{type:'object',properties:{},additionalProperties:false},annotations:{readOnlyHint:true,untrustedContentHint:false},execute(input){validate(input);return {unit:'m',clearance,items:structuredClone(items),issues:inspect(items,clearance)};}},
  {name:'apply_auto_layout',title:'자동 배치 적용',description:'현재 탭의 이동 가능한 설비를 0.5 m 격자로 재배치합니다. 고정 설비를 유지하며 성공한 배치만 적용합니다. 실행 취소로 복원할 수 있습니다.',inputSchema:{type:'object',properties:{},additionalProperties:false},annotations:{readOnlyHint:false,untrustedContentHint:false},execute(input){validate(input);return optimize();}}
 ];
 for(const tool of definitions){try{Promise.resolve(context.registerTool(tool,{signal:lifecycle.signal})).catch(()=>{});}catch{}}
 window.addEventListener('pagehide',()=>lifecycle.abort(),{once:true});
}
