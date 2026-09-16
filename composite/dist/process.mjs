import {workflow,drawingSource,reviewState,selectedView} from './workflow.mjs';
const $=id=>document.getElementById(id);
let activeStep='receive';
function showStep(id){
 const step=workflow.find(s=>s.id===id);if(!step)return;
 activeStep=id;
 document.querySelectorAll('[data-step]').forEach(button=>button.setAttribute('aria-pressed',String(button.dataset.step===id)));
 $('step-number').textContent=`STEP ${step.number}`;$('step-title').textContent=step.title;$('step-status').textContent=step.status;
 $('step-description').textContent=step.description;$('step-owner').textContent=step.owner;$('step-input').textContent=step.input;$('step-output').textContent=step.output;
 $('step-open-studio').hidden=!['constraints','inspect','layout','review'].includes(id);
}
function setView(view,focus=false){
 for(const name of ['studio','composite','workflow']){
  const tab=$(`tab-${name}`),panel=$(`panel-${name}`),active=view===name;
  tab.setAttribute('aria-selected',String(active));tab.tabIndex=active?0:-1;panel.hidden=!active;
 }
 if(focus)$(`tab-${view}`).focus();
 $('export').hidden=view!=='studio';
}
function openView(view){const hash='#'+view;history.replaceState(null,'',hash);setView(view);}
export function initProcess(){
 $('drawing-basis').textContent=`${drawingSource.format} 기반 설계`;
 const stages=$('flow-stages');
 for(const step of workflow){
  const button=document.createElement('button');button.className='flow-stage';button.dataset.step=step.id;button.type='button';button.setAttribute('aria-pressed','false');
  const number=document.createElement('span');number.className='flow-number';number.textContent=step.number;
  const title=document.createElement('strong');title.textContent=step.title;
  const status=document.createElement('span');status.className=`flow-state ${step.status==='샘플 실행 가능'?'available':''}`;status.textContent=step.status;
  button.append(number,title,status);button.onclick=()=>showStep(step.id);stages.append(button);
 }
 const tbody=$('process-table-body');
 for(const step of workflow){const row=document.createElement('tr');for(const value of [`${step.number} ${step.title}`,step.owner,step.input,step.output,step.status]){const cell=document.createElement('td');cell.textContent=value;row.append(cell);}tbody.append(row);}
 for(const name of ['studio','composite','workflow']){
  const tab=$(`tab-${name}`);tab.onclick=()=>openView(name);
  tab.addEventListener('keydown',e=>{if(!['ArrowLeft','ArrowRight','Home','End'].includes(e.key))return;e.preventDefault();const views=['studio','composite','workflow'];const next=e.key==='Home'?views[0]:e.key==='End'?views[2]:views[(views.indexOf(name)+(e.key==='ArrowRight'?1:2))%3];openView(next);setView(next,true);});
 }
 window.addEventListener('hashchange',()=>setView(selectedView(location.hash)));
 $('step-open-studio').onclick=()=>{openView('studio');setView('studio',true);};
 setView(selectedView(location.hash));showStep(activeStep);
}
export function updateProcess(issues){const review=reviewState(issues);$('process-result').textContent=review.title;$('process-result-detail').textContent=review.detail;$('process-review').dataset.state=review.state;}
