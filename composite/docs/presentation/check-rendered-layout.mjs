import fs from 'node:fs/promises';
import path from 'node:path';
const qa=path.resolve(process.argv[2]);
const report={scope:'Top-level text boxes, native charts and tables. Native connectors and intentional text inside native shapes are excluded from pair checks. Visual review remains necessary.',slides:[],unexpectedOverlaps:[],outOfBounds:[]};
const slideNumbers=(await fs.readdir(qa)).map(name=>/^slide-(\d+)\.layout\.json$/.exec(name)).filter(Boolean).map(match=>Number(match[1])).sort((a,b)=>a-b);
if(!slideNumbers.length)throw new Error('No rendered slide layout JSON files were found.');
for(const n of slideNumbers){
 const data=JSON.parse(await fs.readFile(path.join(qa,`slide-${n}.layout.json`),'utf8'));
 const elements=data.elements.filter(e=>e.bbox && (e.text?.trim() || ['chart','table'].includes(e.kind)));
 report.slides.push({slide:n,checkedObjects:elements.length});
 for(const e of elements){
  const [x,y,w,h]=e.bbox;
  if(x<-.1||y<-.1||x+w>1280.1||y+h>720.1)report.outOfBounds.push({slide:n,name:e.name,bbox:e.bbox});
 }
 for(let i=0;i<elements.length;i++)for(let j=i+1;j<elements.length;j++){
  const a=elements[i],b=elements[j],A=a.bbox,B=b.bbox;
  const w=Math.min(A[0]+A[2],B[0]+B[2])-Math.max(A[0],B[0]);
  const h=Math.min(A[1]+A[3],B[1]+B[3])-Math.max(A[1],B[1]);
  if(w>2&&h>2)report.unexpectedOverlaps.push({slide:n,first:a.name,second:b.name,intersection:[w,h]});
 }
}
report.passed=!report.unexpectedOverlaps.length&&!report.outOfBounds.length;
await fs.writeFile(path.join(qa,'overlap-check.json'),JSON.stringify(report,null,2));
console.log(JSON.stringify(report,null,2));
if(!report.passed)process.exitCode=1;
