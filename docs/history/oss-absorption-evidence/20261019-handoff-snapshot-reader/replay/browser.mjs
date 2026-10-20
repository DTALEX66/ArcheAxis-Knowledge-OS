import {createRequire} from 'node:module';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {resolve,join} from 'node:path';
import {mkdir,writeFile,readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import assert from 'node:assert/strict';
const base=fileURLToPath(new URL('.',import.meta.url)),root=resolve(base,'../../..');
const attempt=process.argv[2]??'v2';assert(/^[a-z0-9-]+$/.test(attempt));const out=join(base,'browser-'+attempt);await mkdir(out,{recursive:true});
const tool='C:/Users/ALEX/.codex/tools/visual-tool-lab';
const req=createRequire(join(root,'frontend/package.json'));
const {createServer}=await import(pathToFileURL(join(root,'frontend/node_modules/vite/dist/node/index.js')));
const {default:react}=await import(pathToFileURL(join(root,'frontend/node_modules/@vitejs/plugin-react/dist/index.js')));
const lab=createRequire(join(tool,'package.json'));
const {chromium}=lab('@playwright/test');
const {default:AxeBuilder}=await import(pathToFileURL(lab.resolve('@axe-core/playwright')));
const site=join(out,'site'),visual=join(out,'visual');await mkdir(site,{recursive:true});await mkdir(visual,{recursive:true});
const source=path=>JSON.stringify(join(root,'frontend/src',path).replaceAll('\\','/'));
await writeFile(join(site,'index.html'),'<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>AAOS 固定引用隔离审计</title></head><body><main id="root"></main><script type="module" src="/entry.tsx"></script></body></html>');
await writeFile(join(site,'entry.tsx'),`import React from 'react';import {createRoot} from 'react-dom/client';
import {SpaceView} from ${source('spaces/SpaceView.tsx')};import {ThemeProvider} from ${source('design-system/ThemeProvider.tsx')};import {applyTheme} from ${source('design-system/theme.ts')};
import ${source('design-system/tokens.css')};import ${source('design-system/themes.css')};import ${source('design-system/primitives.css')};import ${source('spaces/ui-first.css')};import ${source('design-system/ui-polish.css')};import ${source('design-system/glass-cabin.css')};import ${source('styles/critical-layout-fixes.css')};
applyTheme('cosmic');createRoot(document.getElementById('root')!).render(<ThemeProvider><SpaceView spaceId="exchange" uiPageId="16" onInspect={()=>{}} onNavigate={()=>{}}/></ThemeProvider>);`);
const report={scope:'actual SpaceView page16 and reader source; SYNTHETIC finite invoke, no real API/model/native UI',started_at:new Date().toISOString(),pid:process.pid,cwd:root,command:process.argv,checks:[],violations:[],incomplete:[],console_errors:[],request_log:[]};
let server,context;
function check(name,value,detail){report.checks.push({name,pass:!!value,detail});assert(value,name);}
try{
 server=await createServer({configFile:false,root:site,cacheDir:join(out,'vite-cache'),plugins:[react()],resolve:{alias:{react:join(root,'frontend/node_modules/react'),'react-dom':join(root,'frontend/node_modules/react-dom')}},server:{host:'127.0.0.1',port:0,strictPort:true,hmr:false,fs:{strict:true,allow:[join(root,'frontend'),site]}}});
 await server.listen();const port=server.httpServer.address().port;report.port=port;report.origin=`http://127.0.0.1:${port}`;
 context=await chromium.launchPersistentContext(join(out,'browser-profile'),{channel:'chrome',headless:true,viewport:{width:1280,height:900},deviceScaleFactor:1,reducedMotion:'reduce',args:['--disable-background-networking','--disable-component-update','--no-first-run','--disable-default-apps']});
 report.browser_version=context.browser()?.version()??'UNKNOWN';
 await context.route('**/*',route=>{const url=route.request().url();report.request_log.push(url);return url.startsWith(report.origin+'/')||url.startsWith('data:')?route.continue():route.abort();});
 await context.addInitScript(()=>{
  const canonical=v=>Array.isArray(v)?v.map(canonical):v&&typeof v==='object'?Object.fromEntries(Object.entries(v).sort(([a],[b])=>a<b?-1:a>b?1:0).map(([k,x])=>[k,canonical(x)])):v;
  const sha=async p=>Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode('archeaxis.project-handoff/v1\0'+JSON.stringify(canonical(p)))))).map(x=>x.toString(16).padStart(2,'0')).join('');
  window.__snapshotAudit={calls:[],mode:'normal',proposal:()=>{const now=Date.now();return {schema:'archeaxis.project-handoff/v1',protocol:'archeaxis.project-observer/v1',idempotency_key:'1'.repeat(32),producer:{namespace:'archeaxis',workspace_id:'2'.repeat(32),restore_epoch:'initial'},consumer:{namespace:'work-lab',instance_id:'3'.repeat(32)},created_at_ms:now,expires_at_ms:now+30000,authority:'PREPARATION_ONLY',payload:{kind:'context',source:{reference:{document_id:'synthetic_snapshot',version:2,content_sha256:'a'.repeat(64)},selection:{kind:'text_range',block_id:'unverified_block',start_utf16:1,end_utf16:5},selection_qualification:'UNVERIFIED'},purpose:'research',authorization_scope:'REFERENCE_METADATA_ONLY'}};}};
  window.__TAURI__={core:{invoke:async(command,{request})=>{
   if(command!=='core_command')throw Error('SYNTHETIC command denied');const {operation:op,payload}=request;window.__snapshotAudit.calls.push(op);
   if(op==='teaching_list')return {status:200,body:{items:[],next_cursor:null}};
   if(op==='sources_list')return {status:200,body:{sources:[]}};
   if(op==='documents_list')return {status:200,body:{documents:[],next_cursor:null,snapshot_count:0}};
   const p=payload?.body;
   if(op==='project_handoff_preview')return {status:200,body:{schema:'archeaxis.project-handoff-preview/v1',checked_at_ms:Date.now(),expires_at_ms:p.expires_at_ms,proposal:p,proposal_sha256:await sha(p),reference_state:'CURRENT',source_authentication:'UNVERIFIED',authority:'REFERENCE_METADATA_ONLY',navigation:'UNAVAILABLE',grants_execution:false,grants_knowledge_acceptance:false}};
   if(op==='project_handoff_snapshot')return window.__snapshotAudit.mode==='error'?{status:409,body:{code:'HANDOFF_SNAPSHOT_IDENTITY_MISMATCH'}}:{status:200,body:{schema:'archeaxis.project-handoff-snapshot/v1',checked_at_ms:Date.now(),expires_at_ms:p.expires_at_ms,proposal_sha256:await sha(p),producer:p.producer,reference:p.payload.source.reference,reference_state:'STALE',source_authentication:'UNVERIFIED',selection_qualification:'UNVERIFIED',scope:'LOCAL_HUMAN_READ_ONLY',editor_json:{type:'doc',content:[{type:'paragraph',content:[{type:'text',text:'SYNTHETIC 固定版本全文\n'+('中文长文本与未核验选区。'.repeat(80))+' https://example.invalid/'+('long'.repeat(90))}]}]},grants_execution:false,grants_knowledge_acceptance:false}};
   return {status:503,body:{code:'SYNTHETIC_OPERATION_NOT_ALLOWED'}};
  }}};
 });
 const page=context.pages()[0];page.on('pageerror',error=>report.console_errors.push(String(error)));
 await context.tracing.start({screenshots:true,snapshots:true,sources:false});await page.goto(report.origin);await page.getByRole('heading',{name:'导入、导出与互通'}).waitFor();
 const opener=page.getByRole('button',{name:'预览跨项目引用'});
 for(const [name,width,height] of [['wide',1280,900],['narrow',390,844]]){
  await page.setViewportSize({width,height});await opener.click();await page.getByRole('textbox',{name:'上下文提案 JSON'}).fill(await page.evaluate(()=>JSON.stringify(window.__snapshotAudit.proposal())));
  await page.getByRole('button',{name:'预览引用信息'}).click();await page.getByRole('button',{name:'打开固定版本全文'}).waitFor();
  await page.getByRole('button',{name:'打开固定版本全文'}).click();await page.getByLabel('固定版本全文',{exact:true}).waitFor();
  check(name+'-stale-truth',await page.getByText('读取时当前保存版本已变化；这里保留并显示引用的旧版全文。').isVisible());
  const metrics=await page.getByRole('dialog').evaluate(el=>({client:el.clientWidth,scroll:el.scrollWidth,rect:{x:el.getBoundingClientRect().x,width:el.getBoundingClientRect().width},viewport:innerWidth,fonts:document.fonts.status}));
  report.checks.push({name:name+'-no-horizontal-overflow',pass:metrics.scroll<=metrics.client+1,detail:metrics});
  await page.screenshot({path:join(visual,name+'.png'),fullPage:true});
  const axe=await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21aa']).analyze();
  report.violations.push(...axe.violations.map(x=>({viewport:name,id:x.id,impact:x.impact,nodes:x.nodes.map(n=>({target:n.target,summary:n.failureSummary}))})));report.incomplete.push(...axe.incomplete.map(x=>({viewport:name,id:x.id,nodes:x.nodes.length})));
  await page.keyboard.press('Escape');await page.getByRole('dialog').waitFor({state:'hidden'});check(name+'-focus-return',await opener.evaluate(el=>el===document.activeElement));
 }
 await page.evaluate(()=>window.__snapshotAudit.mode='error');await opener.click();await page.getByRole('textbox',{name:'上下文提案 JSON'}).fill(await page.evaluate(()=>JSON.stringify(window.__snapshotAudit.proposal())));await page.getByRole('button',{name:'预览引用信息'}).click();await page.getByRole('button',{name:'打开固定版本全文'}).click();
 check('identity-error-readable',await page.getByRole('alert').filter({hasText:'工作区身份或恢复版本'}).isVisible());check('failed-read-has-no-body',await page.getByLabel('固定版本全文',{exact:true}).count()===0);await page.screenshot({path:join(visual,'identity-error.png'),fullPage:true});
 await page.keyboard.press('Escape');await page.getByRole('dialog').waitFor({state:'hidden'});check('actual-exchange-still-mounted',await page.getByRole('heading',{name:'导入、导出与互通'}).isVisible());
 report.finite_operations=await page.evaluate(()=>window.__snapshotAudit.calls);
 check('only-fixed-reader-and-existing-read-only-startup-operations',report.finite_operations.every(x=>['sources_list','documents_list','teaching_list','project_handoff_preview','project_handoff_snapshot'].includes(x)),report.finite_operations);
 await context.tracing.stop({path:join(visual,'trace.zip')});
 report.status=report.checks.every(x=>x.pass)&&report.violations.length===0&&report.console_errors.length===0?'PASS_SYNTHETIC_BROWSER':'PARTIAL';
}catch(error){report.status='FAIL';report.error=String(error);throw error;}
finally{
 if(context)await context.close();if(server)await server.close();report.ended_at=new Date().toISOString();report.owned_browser_closed=!!context;report.owned_server_closed=!!server;
 for(const file of ['wide.png','narrow.png','identity-error.png']){try{const bytes=await readFile(join(visual,file));report[file]={bytes:bytes.length,sha256:createHash('sha256').update(bytes).digest('hex')};}catch{}}
 await writeFile(join(out,'browser-results.json'),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify({status:report.status,checks:report.checks,violations:report.violations.length,incomplete:report.incomplete.length,console_errors:report.console_errors,port:report.port}));
}
