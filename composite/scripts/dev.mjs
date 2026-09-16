// Local-only adapter: injects a local test identity before the production Worker.
import {Miniflare} from 'miniflare';
import {createServer} from 'node:http';
import {readFile,readdir} from 'node:fs/promises';
import path from 'node:path';
const root=path.resolve(import.meta.dirname,'..');
const mf=new Miniflare({modules:true,scriptPath:path.join(root,'dist/server/index.js'),compatibilityDate:'2026-05-15',d1Databases:['DB'],r2Buckets:['BUCKET'],d1Persist:path.join(root,'.local-data/d1'),r2Persist:path.join(root,'.local-data/r2'),assets:{directory:path.join(root,'dist/client'),binding:'ASSETS',routerConfig:{has_user_worker:true,invoke_user_worker_ahead_of_assets:true}}});
const db=await mf.getD1Database('DB');await db.prepare('CREATE TABLE IF NOT EXISTS _local_migrations (name TEXT PRIMARY KEY)').run();
for(const file of (await readdir(path.join(root,'drizzle'))).filter(n=>n.endsWith('.sql')).sort()){if(await db.prepare('SELECT name FROM _local_migrations WHERE name=?').bind(file).first())continue;const sql=await readFile(path.join(root,'drizzle',file),'utf8');await db.batch(sql.split('--> statement-breakpoint').map(s=>s.trim()).filter(Boolean).map(s=>db.prepare(s)));await db.prepare('INSERT INTO _local_migrations VALUES (?)').bind(file).run();}
const server=createServer(async(req,res)=>{try{const chunks=[];for await(const chunk of req)chunks.push(chunk);const headers={...req.headers,'oai-authenticated-user-id':'local-developer'};delete headers['content-length'];const response=await mf.dispatchFetch(`http://127.0.0.1:4317${req.url}`,{method:req.method,headers,body:['GET','HEAD'].includes(req.method)?undefined:Buffer.concat(chunks)});res.writeHead(response.status,Object.fromEntries(response.headers));res.end(Buffer.from(await response.arrayBuffer()));}catch(error){res.writeHead(500);res.end(error.message);}});
server.listen(4317,'127.0.0.1',()=>console.log('Local: http://127.0.0.1:4317/'));
process.on('SIGINT',async()=>{server.close();await mf.dispose();process.exit(0);});
