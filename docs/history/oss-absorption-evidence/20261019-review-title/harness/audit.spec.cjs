const fs=require('node:fs'),path=require('node:path');
const lab=process.env.PILOT_LAB,{test,expect,chromium}=require(path.join(lab,'node_modules/@playwright/test'));
const AxeBuilder=require(path.join(lab,'node_modules/@axe-core/playwright')).default;
const out=process.env.PILOT_OUT,url=process.env.PILOT_URL;
test('review titles preserve identity, legacy fallback and readable narrow layout',async()=>{
 const checks=[],shots=[],errors=[],network=[],axe=[];let context;
 const write=(name,value)=>fs.writeFileSync(path.join(out,name),JSON.stringify(value,null,2));
 const check=async(name,fn)=>{const started=new Date().toISOString();try{checks.push({name,status:'PASS',started,detail:await fn(),ended:new Date().toISOString()});}catch(e){checks.push({name,status:'FAIL',started,error:String(e),ended:new Date().toISOString()});}write('checks.json',checks);};
 try{
  context=await chromium.launchPersistentContext(path.join(out,'browser-profile'),{channel:'chrome',headless:true,viewport:{width:1280,height:900},deviceScaleFactor:1,locale:'zh-CN',timezoneId:'Asia/Shanghai',serviceWorkers:'block',args:['--disable-background-networking','--disable-component-update','--disable-sync','--no-first-run']});
  write('environment.json',{browser:context.browser().version(),viewport:{width:1280,height:900},DPR:1,locale:'zh-CN',workers:1,baseline:'none created or updated',evidence:'ACTUAL_PRODUCTION_BUNDLE / SYNTHETIC_CORE'});
  await context.tracing.start({screenshots:true,snapshots:true,sources:false});
  await context.route('**/*',async route=>{const r=route.request(),u=new URL(r.url());if(u.origin!==url){network.push({url:r.url(),action:'BLOCKED'});return route.abort();}if(u.pathname==='/api/v1/system/handshake')return route.fulfill({json:{product_id:'archeaxis-workspace',product_name:'ArcheAxis Knowledge',api_contract:'1.x',backend_version:'browser-smoke',source_commit:'SYNTHETIC',schema_version:15,runtime_mode:'browser-smoke',workspace_id:'browser-smoke',capabilities:[],migration_state:'ready'}});if(u.pathname.startsWith('/api/')||u.pathname.startsWith('/workspace/'))return route.fulfill({json:{items:[],count:0}});if(r.method()!=='GET'||!(u.pathname==='/'||u.pathname==='/index.html'||u.pathname.startsWith('/assets/')))return route.abort();return route.continue();});
  await context.addInitScript({path:path.join(out,'fixture.js')});
  const page=context.pages()[0];page.setDefaultTimeout(5000);page.on('pageerror',e=>errors.push(String(e)));
  const shot=async name=>{await page.screenshot({path:path.join(out,name+'.png'),animations:'disabled'});shots.push({name,file:name+'.png',viewport:page.viewportSize(),font:await page.locator('body').evaluate(e=>getComputedStyle(e).fontFamily),theme:await page.locator('html').getAttribute('data-aaos-theme'),DPR:1});write('screenshots.json',shots);};
  await page.goto(url);await expect(page.locator('.app-shell')).toBeVisible();await page.evaluate(()=>document.fonts.ready);
  await page.keyboard.press('Control+k');const dialog=page.getByRole('dialog',{name:'全局命令',exact:true});await dialog.getByRole('searchbox',{name:'搜索空间或命令'}).fill('page=06');await dialog.locator('[data-entry-id="page:06"]').click();
  const queue=page.getByRole('list',{name:'复习队列',exact:true});await expect(queue).toBeVisible();
  const data=await page.evaluate(()=>({keys:window.__TITLE_PILOT__.keys,title:window.__TITLE_PILOT__.title}));
  await check('same readable title selects each original identity using keyboard',async()=>{
   await expect(queue.getByRole('button',{name:data.title,exact:true})).toHaveCount(2);
   const buttons=queue.locator('button[data-learning-item-key]');await expect(buttons).toHaveCount(2);
   for(let i=0;i<2;i++){await buttons.nth(i).focus();await page.keyboard.press('Enter');await expect(page.getByLabel('学习项目键',{exact:true})).toHaveValue(data.keys[i]);await expect(page.getByLabel('本次答案',{exact:true})).toBeVisible();}
   await queue.scrollIntoViewIfNeeded();await shot('01-readable-title-desktop');
   const calls=await page.evaluate(()=>window.__TITLE_PILOT__.calls.filter(c=>c.operation==='learning_state').map(c=>c.item_key));
   expect(calls).toEqual(data.keys);
   return {keysSelected:calls,titleScalars:Array.from(data.title).length,selectionEcho:'no duplicate read; no write or inference'};
  });
  await check('640px reduced motion title wraps inside the queue without page overflow',async()=>{
   await page.setViewportSize({width:640,height:900});await page.emulateMedia({reducedMotion:'reduce'});await queue.scrollIntoViewIfNeeded();await shot('02-readable-title-narrow');
   const bounds=await queue.evaluate(e=>({queueWidth:e.clientWidth,queueScrollWidth:e.scrollWidth,pageWidth:innerWidth,pageScrollWidth:document.documentElement.scrollWidth,buttonWidths:[...e.querySelectorAll('button')].map(b=>({width:b.clientWidth,scrollWidth:b.scrollWidth,height:b.getBoundingClientRect().height})),reducedMotion:matchMedia('(prefers-reduced-motion: reduce)').matches}));
   expect(bounds.pageScrollWidth).toBeLessThanOrEqual(bounds.pageWidth);expect(bounds.queueScrollWidth).toBeLessThanOrEqual(bounds.queueWidth);for(const b of bounds.buttonWidths)expect(b.scrollWidth).toBeLessThanOrEqual(b.width);
   const result=await new AxeBuilder({page}).include('ul[aria-label="复习队列"]').withTags(['wcag2a','wcag2aa','wcag21aa','wcag22aa']).analyze();axe.push({name:'review-queue',violations:result.violations,incomplete:result.incomplete,passes:result.passes.length});write('axe-results.json',axe);expect(result.violations).toEqual([]);return bounds;
  });
  await check('older Core without title remains usable; read failure is explicit',async()=>{
   await page.evaluate(()=>window.__TITLE_PILOT__.mode='legacy');await page.getByRole('button',{name:'刷新学习队列',exact:true}).click();await expect(queue.getByRole('button',{name:'学习项目',exact:true})).toHaveCount(2);await queue.getByRole('button',{name:'学习项目',exact:true}).first().click();await expect(page.getByLabel('学习项目键',{exact:true})).toHaveValue(data.keys[0]);await queue.scrollIntoViewIfNeeded();await shot('03-legacy-title-fallback');
   await page.evaluate(()=>window.__TITLE_PILOT__.mode='failure');await page.getByRole('button',{name:'刷新学习队列',exact:true}).click();await expect(page.getByText('学习队列读取失败，请重试。',{exact:true})).toBeVisible();return {fallback:'学习项目',failure:'explicit, prior entries retained'};
  });
  const calls=await page.evaluate(()=>window.__TITLE_PILOT__.calls);const forbidden=calls.filter(c=>/learning_review|assessment_create|learning_reference|machine_answer|conversation_execute|course_from_knowledge/.test(c.operation||''));expect(forbidden).toEqual([]);
  write('summary.json',{status:checks.some(c=>c.status==='FAIL')?'PARTIAL':'PASS',evidence:'REAL_CHROME / PRODUCTION_BUNDLE / SYNTHETIC_CORE',checks,shots,errors,network,forbiddenCalls:forbidden,notExecuted:['real Core browser bridge','native host','installed runtime','screen reader','performance benchmark']});
  expect(checks.filter(c=>c.status==='FAIL')).toEqual([]);expect(errors).toEqual([]);
 }finally{if(context){await context.tracing.stop({path:path.join(out,'trace.zip')});await context.close();}write('browser-shutdown.json',{closed:!!context,ended:new Date().toISOString()});}
});
