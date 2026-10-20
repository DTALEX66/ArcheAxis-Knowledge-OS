const fs=require('node:fs'),path=require('node:path');
const lab=process.env.PILOT_LAB,{test,expect,chromium}=require(path.join(lab,'node_modules/@playwright/test'));
const AxeBuilder=require(path.join(lab,'node_modules/@axe-core/playwright')).default;
const out=process.env.PILOT_OUT,url=process.env.PILOT_URL;
test('capability center and external quiz: actual bundle, isolated synthetic bridge',async()=>{
 const checks=[],shots=[],axe=[],network=[],errors=[],profile=path.join(out,'browser-profile');let context;
 const write=(name,value)=>fs.writeFileSync(path.join(out,name),JSON.stringify(value,null,2));
 const check=async(name,fn)=>{const start=new Date().toISOString();try{const detail=await fn();checks.push({name,status:'PASS',start,end:new Date().toISOString(),detail});}catch(error){checks.push({name,status:'FAIL',start,end:new Date().toISOString(),error:String(error)});}write('checks.json',checks);};
 try{
  context=await chromium.launchPersistentContext(profile,{channel:'chrome',headless:true,viewport:{width:1280,height:900},deviceScaleFactor:1,locale:'zh-CN',timezoneId:'Asia/Shanghai',serviceWorkers:'block',args:['--disable-background-networking','--disable-component-update','--disable-sync','--no-first-run']});
  write('environment.json',{browser:context.browser().version(),viewport:{width:1280,height:900},DPR:1,locale:'zh-CN',timezone:'Asia/Shanghai',profile,workers:1,baseline:'none created or updated',evidence:'ACTUAL_FRONTEND_BUNDLE / SYNTHETIC_CORE'});
  await context.tracing.start({screenshots:true,snapshots:true,sources:false});
  await context.route('**/*',async route=>{const r=route.request(),u=new URL(r.url());if(u.origin!==url){network.push({url:r.url(),method:r.method(),action:'BLOCKED'});return route.abort('blockedbyclient');}if(u.pathname==='/api/v1/system/handshake')return route.fulfill({json:{product_id:'archeaxis-workspace',product_name:'ArcheAxis Knowledge',api_contract:'1.x',backend_version:'browser-smoke',source_commit:'SYNTHETIC',schema_version:15,runtime_mode:'browser-smoke',workspace_id:'browser-smoke',capabilities:[],migration_state:'ready'}});if(u.pathname.startsWith('/api/')||u.pathname.startsWith('/workspace/'))return route.fulfill({json:{items:[],count:0}});if(r.method()!=='GET'||!(u.pathname==='/'||u.pathname==='/index.html'||u.pathname.startsWith('/assets/')))return route.abort();return route.continue();});
  await context.addInitScript({path:path.join(out,'fixture.js')});const page=context.pages()[0];page.setDefaultTimeout(5000);
  page.on('pageerror',e=>errors.push(String(e)));page.on('console',m=>{if(m.type()==='error')errors.push(m.text());});
  const shot=async name=>{await page.screenshot({path:path.join(out,name+'.png'),fullPage:false,animations:'disabled'});shots.push({name,file:name+'.png',viewport:page.viewportSize(),theme:await page.locator('html').getAttribute('data-aaos-theme'),font:await page.locator('body').evaluate(e=>getComputedStyle(e).fontFamily),DPR:1});write('screenshots.json',shots);};
  const scan=async name=>{const r=await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21aa','wcag22aa']).analyze();axe.push({name,violations:r.violations,incomplete:r.incomplete,passes:r.passes.length});write('axe-results.json',axe);return r.violations.map(v=>({id:v.id,impact:v.impact,nodes:v.nodes.length}));};
  const nav=async id=>{await page.keyboard.press('Control+k');const d=page.getByRole('dialog',{name:'全局命令',exact:true});await expect(d).toBeVisible();await d.getByRole('searchbox',{name:'搜索空间或命令'}).fill('page='+id);await d.locator(`[data-entry-id="page:${id}"]`).click();await expect(page.locator('[data-current-page-id]').first()).toHaveAttribute('data-current-page-id',id);};
  const geometry=async()=>page.evaluate(()=>({width:innerWidth,scrollWidth:document.documentElement.scrollWidth,font:getComputedStyle(document.body).fontFamily,fonts:document.fonts.status}));
  await page.goto(url);await expect(page.locator('.app-shell')).toBeVisible();await page.evaluate(()=>document.fonts.ready);
  await check('capability catalog: filters/search/future details stay read-only',async()=>{
   await nav('17');await expect(page.getByRole('heading',{name:'能力中心',exact:true})).toBeVisible();
   await expect(page.locator('.capability-center-list button[data-entry-id^="CAP-"]')).toHaveCount(16);await shot('01-capability-center-desktop');await page.locator('.capability-center-list > li').first().scrollIntoViewIfNeeded();await shot('10-capability-cards-desktop');const card=page.locator('.capability-center-list > li').first();expect(await card.evaluate(e=>({display:getComputedStyle(e).display,direction:getComputedStyle(e).flexDirection}))).toEqual({display:'flex',direction:'column'});const bounds=await card.evaluate(e=>{const b=e.querySelector('button').getBoundingClientRect(),s=e.querySelector(':scope > span').getBoundingClientRect();return {buttonBottom:b.bottom,statusTop:s.top};});expect(bounds.statusTop).toBeGreaterThanOrEqual(bounds.buttonBottom);
   await page.getByRole('button',{name:'未来规划',exact:true}).click();await expect(page.locator('.capability-center-list button[data-entry-id^="CAP-"]')).toHaveCount(6);
   await page.getByLabel('查找能力',{exact:true}).fill('CAP-0080');await page.locator('.capability-center-list [data-entry-id="CAP-0080"]').click();
   await expect(page.getByRole('button',{name:'当前执行入口尚未提供'})).toBeDisabled();await shot('02-future-capability-details');
   return {axe:await scan('future-capability'),calls:await page.evaluate(()=>window.__PILOT__.calls.filter(c=>c.operation==='operation_readiness').length)};
  });
  await check('capability scoped state: history and partial model settings are explicit',async()=>{
   await page.getByRole('tab',{name:'目录与搜索',exact:true}).click();await page.getByRole('button',{name:'全部',exact:true}).click();await page.getByLabel('查找能力',{exact:true}).fill('CAP-0020');await page.locator('.capability-center-list [data-entry-id="CAP-0020"]').click();
   await expect(page.getByText(/仅观察「多格式转换」/)).toBeVisible();await expect(page.getByText(/历史可用登记/).first()).toBeVisible();
   await page.getByRole('heading',{name:'多格式转换',exact:true}).scrollIntoViewIfNeeded();await shot('03-scoped-capability-details');
   await page.getByRole('tab',{name:'目录与搜索',exact:true}).click();await page.getByLabel('查找能力',{exact:true}).fill('CAP-0150');await page.locator('.capability-center-list [data-entry-id="CAP-0150"]').click();
   await page.getByRole('button',{name:'查看现有模型配置',exact:true}).click();await expect(page.locator('[data-current-page-id]').first()).toHaveAttribute('data-current-page-id','19');
   return {modelCalls:await page.evaluate(()=>window.__PILOT__.calls.filter(c=>/infer|model_load/.test(c.operation||'')))};
  });
  const manifest={formatVersion:1,exportedAt:'2026-10-19T00:00:00Z',appVersion:'1.2.1',stage:{name:'证据与来源 · 中文长标题的外部测验候选与来源定位',createdAt:1,updatedAt:2},agents:[],mediaIndex:{},scenes:[{type:'quiz',title:'来源识别与自主复核',order:2,content:{type:'quiz',questions:[{id:'single',type:'single',question:'选择来源 <script>never()</script>',options:[{label:'原件与固定版本的来源记录',value:'source'},{label:'未经核对的猜测',value:'guess'}],answer:['source'],analysis:'参考答案仅代表外部课件内容，必须核对原件。'},{id:'multi',type:'multiple',question:'哪些对象需要保留？',options:[{label:'原字节',value:'bytes'},{label:'来源身份',value:'identity'}],answer:['bytes','identity']},{id:'short',type:'short_answer',question:'用自己的话说明来源边界',hasAnswer:false}]}}]};
  const upload=async value=>page.getByLabel('选择课程 manifest.json').setInputFiles({name:'manifest.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(value))});
  const panel=()=>page.locator('section[aria-label="外部课程候选"]');
  await check('course preview and keyboard reference practice do not write or execute HTML',async()=>{
   await nav('07');await page.locator('summary').filter({hasText:'外部课程与测验'}).click();await upload(manifest);
   await expect(panel().getByText(/预览就绪/)).toBeVisible();await expect(panel().getByRole('group',{name:'选择来源 <script>never()</script>',exact:true})).toBeVisible();
   expect(await page.evaluate(()=>window.__PILOT__.calls.filter(c=>c.operation==='source_import'||c.operation==='document_create'))).toHaveLength(0);
   const q=panel().getByRole('group',{name:'选择来源 <script>never()</script>',exact:true});await q.getByRole('radio').first().focus();await page.keyboard.press('Space');await page.keyboard.press('Tab');await expect(q.getByRole('button',{name:'核对课件参考答案'})).toBeFocused();await page.keyboard.press('Enter');
   await expect(q.getByText(/与课件参考答案一致/)).toBeVisible();expect(await page.evaluate(()=>typeof window.never)).toBe('undefined');
   await panel().getByRole('group',{name:'用自己的话说明来源边界',exact:true}).getByRole('button').click();await expect(panel().getByText(/此题未提供可用参考答案/)).toBeVisible();
   await panel().getByRole('heading',{level:4}).scrollIntoViewIfNeeded();await shot('04-course-preview-desktop');
   await q.scrollIntoViewIfNeeded();await shot('09-course-options-desktop');
   const options=await q.locator('.imported-course-option').evaluateAll(labels=>labels.map(label=>{const r=label.getBoundingClientRect(),i=label.querySelector('input').getBoundingClientRect();return {height:r.height,width:r.width,inputWidth:i.width,inputCenterOffset:Math.abs((i.y+i.height/2)-(r.y+r.height/2)),display:getComputedStyle(label).display};}));
   expect(options.length).toBe(2);for(const option of options){expect(option.height).toBeGreaterThanOrEqual(44);expect(option.inputWidth).toBeLessThan(30);expect(option.inputCenterOffset).toBeLessThan(4);expect(option.display).toBe('grid');}
   return {options,axe:await scan('course-preview'),geometry:await geometry()};
  });
  await check('unknown save keeps original request; synthetic reopen reparses the original',async()=>{
   await page.evaluate(()=>window.__PILOT__.fault='unknown-save');await panel().getByRole('button',{name:'保全原件并保存课程候选'}).click();await expect(panel().getByRole('alert')).toContainText('课程保存结果待核对');await shot('05-course-unknown-save');
   await panel().getByRole('button',{name:'同请求重试保存'}).click();await expect(panel().getByText(/候选已保存并读回核对/)).toBeVisible();
   const requests=await page.evaluate(()=>window.__PILOT__.calls.filter(c=>c.operation==='document_create').map(c=>c.requestId));expect(requests).toHaveLength(2);expect(requests[0]).toBe(requests[1]);
   await panel().getByRole('button',{name:'重新核对已保存课程'}).click();await expect(panel().getByText(/已从保存的原件与文档重新核对/)).toBeVisible();
   await panel().locator('summary').filter({hasText:'重新打开已保存候选'}).click();await panel().getByRole('button',{name:'浏览已保存文档'}).click();
   await panel().getByRole('button',{name:/打开 外部课程候选/}).click();await expect(panel().getByText(/已从保存的原件与文档重新核对/)).toBeVisible();
   return {requests,saved:await page.evaluate(()=>window.__PILOT__.documents.size),axe:await scan('course-reopened')};
  });
  await check('unsupported input and list failure never look successful',async()=>{
   await page.evaluate(()=>window.__PILOT__.fault='list-failure');await panel().getByRole('button',{name:'浏览已保存文档'}).click();await expect(panel().getByRole('alert')).toContainText('列表读取失败');
   const unsupported=structuredClone(manifest);unsupported.scenes[0].type='slide';await upload(unsupported);await expect(panel().getByRole('alert')).toContainText('首批仅支持 quiz');
   await expect(panel().getByRole('button',{name:'保全原件并保存课程候选'})).toHaveCount(0);await shot('06-course-explicit-failure');
   await page.evaluate(()=>window.__PILOT__.fault=null);await upload(manifest);return {axe:await scan('course-rejected')};
  });
  await check('narrow window and reduced motion: readable controls without horizontal page overflow',async()=>{
   await page.evaluate(()=>window.__PILOT__.fault=null);await upload(manifest);await page.setViewportSize({width:640,height:900});await page.emulateMedia({reducedMotion:'reduce'});await panel().getByRole('heading',{level:4}).scrollIntoViewIfNeeded();await shot('07-course-narrow');const course=await geometry();expect(course.scrollWidth).toBeLessThanOrEqual(course.width);
   await nav('17');await page.getByRole('tab',{name:'目录与搜索',exact:true}).click();await page.getByLabel('查找能力',{exact:true}).fill('');await page.getByRole('button',{name:'全部',exact:true}).click();await page.getByRole('heading',{name:'能力中心',exact:true}).scrollIntoViewIfNeeded();await shot('08-capability-center-narrow');await page.locator('.capability-center-list > li').first().scrollIntoViewIfNeeded();await shot('11-capability-cards-narrow');const card=page.locator('.capability-center-list > li').first();expect(await card.evaluate(e=>getComputedStyle(e).flexDirection)).toBe('column');expect(await card.evaluate(e=>e.scrollWidth<=e.clientWidth)).toBe(true);const hub=await geometry();expect(hub.scrollWidth).toBeLessThanOrEqual(hub.width);
   return {course,hub,axe:await scan('capability-center-narrow'),reducedMotion:await page.evaluate(()=>matchMedia('(prefers-reduced-motion: reduce)').matches)};
  });
  const coreCalls=await page.evaluate(()=>window.__PILOT__.calls);expect(coreCalls.filter(c=>/learning_review|knowledge_review|course_from_knowledge|machine_answer/.test(c.operation||''))).toEqual([]);
  const serious=axe.flatMap(s=>s.violations.filter(v=>['critical','serious'].includes(v.impact)).map(v=>({name:s.name,id:v.id,nodes:v.nodes.length})));
  write('browser-evidence.json',{checks,shots,axe,network,errors,coreCalls,notExecuted:['real Core bridge','native WebView2','installed journeys','screen reader','real upstream classroom sample','performance benchmarks']});
  write('summary.json',{status:checks.some(c=>c.status==='FAIL')||serious.length?'PARTIAL':'PASS',evidence:'REAL_CHROMIUM / ACTUAL_PRODUCTION_BUNDLE / SYNTHETIC_CORE',checks:checks.map(c=>({name:c.name,status:c.status})),serious});
  expect(checks.filter(c=>c.status==='FAIL').map(c=>({name:c.name,error:c.error}))).toEqual([]);expect(serious).toEqual([]);
 }finally{if(context){await context.tracing.stop({path:path.join(out,'trace.zip')});await context.close();}write('browser-shutdown.json',{closed:!!context,time:new Date().toISOString(),profile});}
});
