export const room = { w: 60, h: 36 };
export const fixedZones = [
  {id:'AISLE',name:'주 통로',x:0,y:16,w:60,h:4,kind:'aisle'},
  ...[10,30,50].flatMap((x,i)=>[6,28].map((y,j)=>({id:`COL-${i}${j}`,name:'구조 기둥',x,y,w:1.2,h:1.2,kind:'column'})))
];
export function sample(){return [
 {id:'LITHO-01',name:'노광 설비',x:3,y:3,w:6,h:5,locked:true},
 {id:'LITHO-02',name:'노광 설비',x:7.5,y:6,w:6,h:5,locked:false},
 {id:'ETCH-01',name:'식각 설비',x:20,y:3,w:5,h:6,locked:false},
 {id:'ETCH-02',name:'식각 설비',x:25.5,y:3,w:5,h:6,locked:false},
 {id:'CVD-01',name:'증착 설비',x:37,y:5,w:7,h:5,locked:false},
 {id:'CVD-02',name:'증착 설비',x:42,y:8,w:7,h:5,locked:false},
 {id:'CMP-01',name:'연마 설비',x:8,y:24,w:6,h:5,locked:false},
 {id:'CLEAN-01',name:'세정 설비',x:33,y:24,w:9,h:5,locked:false}
];}
const EPS=1e-8;
export function overlap(a,b){return a.x < b.x+b.w-EPS && a.x+a.w>b.x+EPS && a.y<b.y+b.h-EPS && a.y+a.h>b.y+EPS;}
export function distance(a,b){return Math.hypot(Math.max(0,a.x-b.x-b.w,b.x-a.x-a.w),Math.max(0,a.y-b.y-b.h,b.y-a.y-a.h));}
export function outside(a){return a.x < -EPS || a.y < -EPS || a.x+a.w>room.w+EPS || a.y+a.h>room.h+EPS;}
export function inspect(items,clearance){
 const issues=[];
 for(let i=0;i<items.length;i++){
  const a=items[i];
  if(outside(a))issues.push({type:'boundary',a:a.id,b:null,message:'FAB 영역 경계 밖에 있습니다.'});
  for(const b of fixedZones)if(overlap(a,b))issues.push({type:'overlap',a:a.id,b:b.id,message:`${b.name} 영역과 겹칩니다.`});
  for(let j=i+1;j<items.length;j++){
   const b=items[j],gap=distance(a,b);
   if(overlap(a,b))issues.push({type:'overlap',a:a.id,b:b.id,message:'설비 영역이 서로 겹칩니다.'});
   else if(gap<clearance-EPS)issues.push({type:'clearance',a:a.id,b:b.id,message:`현재 ${gap.toFixed(2)} m / 필요 ${clearance.toFixed(1)} m`,gap});
  }
 }
 return issues;
}
export function autoLayout(items,clearance){
 const original=items.map(i=>({...i}));
 const accepted=original.filter(i=>i.locked), movable=original.filter(i=>!i.locked).sort((a,b)=>b.w*b.h-a.w*a.h||a.id.localeCompare(b.id));
 const valid=(a)=>!outside(a)&&fixedZones.every(b=>!overlap(a,b))&&accepted.every(b=>!overlap(a,b)&&distance(a,b)>=clearance-EPS);
 for(const item of movable){
  if(valid(item)){accepted.push({...item});continue;}
  let best=null,bestScore=Infinity;
  for(let y=0;y<=room.h-item.h+EPS;y+=.5)for(let x=0;x<=room.w-item.w+EPS;x+=.5){
   const score=(x-item.x)**2+(y-item.y)**2;
   if(score<bestScore-EPS){const candidate={...item,x,y};if(valid(candidate)){best=candidate;bestScore=score;}}
  }
  if(!best)return {ok:false,items:original,failed:item.id,reason:'현재 0.5 m 격자 탐색에서 배치를 찾지 못했습니다. 기존 배치를 유지합니다.'};
  accepted.push(best);
 }
 const result=original.map(i=>accepted.find(j=>j.id===i.id));
 const issues=inspect(result,clearance);
 if(issues.length)return {ok:false,items:original,reason:'고정 설비의 간섭을 먼저 해제해야 합니다. 기존 배치를 유지합니다.',issues};
 return {ok:true,items:result,moved:result.filter((i,k)=>i.x!==original[k].x||i.y!==original[k].y).length,issues};
}
