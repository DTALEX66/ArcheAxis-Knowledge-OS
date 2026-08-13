const $=selector=>document.querySelector(selector),$$=selector=>[...document.querySelectorAll(selector)];
const storedInspectorState=localStorage.getItem('aa-inspector');
const state={theme:localStorage.getItem('aa-theme')||'apple-light',page:'overview',module:localStorage.getItem('aa-module')||'home',intakeTrigger:null,subnavOpen:false,subnavTrigger:null,inspectorTrigger:null,inspectorCollapsed:storedInspectorState==='collapsed'||(window.matchMedia('(max-width: 960px)').matches&&storedInspectorState!=='open'),dockCollapsed:localStorage.getItem('aa-dock')==='collapsed'};
const icons={home:'M3 11l9-8 9 8v10a1 1 0 0 1-1 1h-5v-7h-6v7H4a1 1 0 0 1-1-1z',folder:'M3 6h6l2 2h10v12H3z',search:'M10 18a8 8 0 1 1 0-16 8 8 0 0 1 0 16zm11 3-5-5',shield:'M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z',book:'M4 4h6a4 4 0 0 1 4 4v12a3 3 0 0 0-3-3H4zM20 4h-6',brain:'M8 4a4 4 0 0 0-4 4v1a4 4 0 0 0 0 8v1a4 4 0 0 0 4 4h1V4zM16 4a4 4 0 0 1 4 4v1a4 4 0 0 1 0 8v1a4 4 0 0 1-4 4h-1V4z',eye:'M2 12s4-7 10-7 10 7 10 7-4 7-10 7-10-7-10-7zm10 3a3 3 0 1 0 0-6 3 3 0 0 0 0 6z',layers:'M12 2 2 7l10 5 10-5zM2 17l10 5 10-5M2 12l10 5 10-5',cpu:'M6 6h12v12H6zM9 1v5M15 1v5M9 18v5M15 18v5M1 9h5M1 15h5M18 9h5M18 15h5',zap:'M13 2 3 14h8l-1 8 10-12h-8z',clock:'M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18zm0-13v5l3 2',tool:'M14 7a4 4 0 0 1 5-5l-3 3 2 2 3-3a4 4 0 0 1-5 5L7 18a2 2 0 0 1-3-3z',settings:'M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6zm8-3a8 8 0 0 0-.2-1.8l2-1.6-2-3.4-2.4 1a8 8 0 0 0-3-1.8L14 2h-4l-.4 2.4a8 8 0 0 0-3 1.8l-2.4-1-2 3.4 2 1.6A8 8 0 0 0 4 12c0 .6.1 1.2.2 1.8l-2 1.6 2 3.4 2.4-1a8 8 0 0 0 3 1.8L10 22h4l.4-2.4a8 8 0 0 0 3-1.8l2 1.6c.1-.6.2-1.2.2-1.8z',activity:'M3 12h4l3 8 4-16 3 8h4',archive:'M3 4h18v5H3zm2 5v11h14V9M10 13h4',map:'M9 4 3 6v14l6-2 6 2 6-2V4l-6 2zm0 0v14m6-12v14',play:'M5 3l16 9-16 9z',list:'M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01'};
function iconElement(name){const namespace='http://www.w3.org/2000/svg';const svg=document.createElementNS(namespace,'svg');svg.setAttribute('viewBox','0 0 24 24');svg.setAttribute('aria-hidden','true');const path=document.createElementNS(namespace,'path');path.setAttribute('d',icons[name]||icons.folder);svg.append(path);return svg}
const nav=[['首页',[['overview','工作台总览','Overview','home'],['vault','Vault 工作台','Vault','folder'],['projects','项目','Projects','folder'],['runtime','知行任务执行','Runtime','zap'],['delivery','投递回执','Delivery','archive']]],['资料与知识',[['research','察微研究','Research','search'],['evidence','证据中心','Evidence','shield'],['knowledge','藏识知识','Knowledge','archive'],['canvas','认知画布','Canvas','layers']]],['学习',[['learning','学习路线','Learning','map'],['evolution','知新评估进化','Evolution','activity'],['machine','知衡机器知识','Machine','cpu']]],['系统',[['diagnostics','系统诊断','Diagnostics','activity'],['audit','审计记录','Audit','shield'],['settings','设置','Settings','settings']]]];
const routeStatus={overview:'available',vault:'available',projects:'planned',runtime:'partial',delivery:'partial',research:'available',evidence:'available',knowledge:'available',canvas:'available',learning:'partial',evolution:'partial',machine:'partial',agents:'planned',skills:'planned',models:'planned','workflow-builder':'planned','workflow-runs':'planned',integrations:'planned',mcp:'planned',diagnostics:'available',audit:'planned',settings:'planned'};
const routeStatusLabels={available:'已接入',partial:'部分接入',planned:'规划中',blocked:'已阻断'};
const pageModule={overview:'home',vault:'home',projects:'home',runtime:'home',delivery:'home',research:'knowledge',evidence:'knowledge',knowledge:'knowledge',canvas:'knowledge',learning:'learning',evolution:'learning',machine:'learning',agents:'ai',skills:'ai',models:'ai','workflow-builder':'ai','workflow-runs':'ai',integrations:'ai',mcp:'ai',diagnostics:'system',audit:'system',settings:'system'};
const groupModule={'首页':'home','资料与知识':'knowledge','学习':'learning','AI':'ai','系统':'system'};
function renderNav(){const target=$('#nav');target.textContent='';state.module=pageModule[state.page]||state.module;localStorage.setItem('aa-module',state.module);$$('.rail-item').forEach(button=>{const active=button.dataset.module===state.module;button.classList.toggle('active',active);button.setAttribute('aria-current',active?'page':'false')});nav.forEach(([group,items])=>{const section=document.createElement('section');section.className='nav-group';section.dataset.module=groupModule[group];section.classList.toggle('active-group',section.dataset.module===state.module);const title=document.createElement('div');title.className='nav-title';const groupName=document.createElement('span');groupName.textContent=group;const separator=document.createElement('span');separator.textContent='—';title.append(groupName,separator);section.append(title);items.forEach(item=>{const button=document.createElement('button');const active=state.page===item[0];button.type='button';button.className=`nav-item ${active?'active':''}`;button.dataset.page=item[0];button.title=item[1];if(active)button.setAttribute('aria-current','page');const chinese=document.createElement('span');chinese.className='cn';chinese.textContent=item[1];const english=document.createElement('span');english.className='en';english.textContent=item[2];const stateBadge=document.createElement('span');const status=routeStatus[item[0]]||'planned';stateBadge.className=`route-state route-state-${status}`;stateBadge.textContent=routeStatusLabels[status];stateBadge.title=`状态：${routeStatusLabels[status]}`;button.dataset.routeState=status;button.append(iconElement(item[3]),chinese,english,stateBadge);section.append(button)});target.append(section)})}
function setTheme(theme){const selected=['violet-core','apple-light','yaojin','deepspace'].includes(theme)?theme:'apple-light';state.theme=selected;localStorage.setItem('aa-theme',selected);document.body.dataset.theme=selected;$$('.theme button').forEach(button=>{const active=button.dataset.theme===selected;button.classList.toggle('active',active);button.setAttribute('aria-pressed',String(active));button.type='button'})}
function metric(label,value,detail,tone='info'){const card=document.createElement('div');card.className='card metric';const name=document.createElement('span');name.textContent=label;const number=document.createElement('b');number.textContent=String(value);const note=document.createElement('span');note.className=`delta ${tone}`;note.textContent=detail;card.append(name,number,note);return card}
const capabilityLabels={asynchronous_worker:'异步Worker',outbox_dispatcher:'Outbox投递器',server_sent_events:'实时事件流',interactive_job_center:'交互式Job Center',asr_transcription:'ASR转写'};
const capabilityStates=new Set(['available','dependency_required','not_implemented']);
const productRoutes=new Set([...nav.flatMap(([,items])=>items.map(([page])=>page)),'unavailable']);
const isRecord=value=>value!==null&&typeof value==='object'&&!Array.isArray(value);
function validateStatus(payload){if(!isRecord(payload)||payload.schema_version!=='v1'||typeof payload.observed_at!=='string'||Number.isNaN(Date.parse(payload.observed_at))||!isRecord(payload.counts)||!isRecord(payload.capabilities)||!isRecord(payload.release)||!isRecord(payload.components)||!isRecord(payload.migrations))throw new Error('invalid workspace status');for(const groupName of ['research','jobs','outbox','learning','machine_knowledge']){const group=payload.counts[groupName];if(!isRecord(group)||Object.values(group).some(value=>!Number.isInteger(value)||value<0))throw new Error('invalid workspace counts')}for(const key of Object.keys(capabilityLabels)){if(!capabilityStates.has(payload.capabilities[key]))throw new Error('invalid workspace capabilities')}if(typeof payload.release.version!=='string'||!payload.release.version||typeof payload.release.status!=='string'||!payload.release.status||payload.components.api!=='available'||payload.components.database!=='available'||Object.keys(payload.migrations).length===0||Object.values(payload.migrations).some(value=>!Number.isInteger(value)||value<0))throw new Error('invalid workspace status projection');return payload}
function total(group){return Object.values(group).reduce((sum,value)=>sum+value,0)}
function renderStatus(payload){const target=$('#status-summary');target.textContent='';const counts=payload.counts;target.append(metric('待审核研究',(counts.research.candidate||0)+(counts.research.ready_for_review||0),'来自本地候选研究'),metric('已记录任务',total(counts.jobs),'同步持久化记录'),metric('待投递事件',counts.outbox.pending||0,'按需投递器等待操作','warn'),metric('版本',payload.release.version,payload.release.status));const capabilities=$('#capability-summary');capabilities.textContent='';Object.entries(capabilityLabels).forEach(([key,label])=>{const row=document.createElement('div');row.className='row';const main=document.createElement('div');main.className='row-main';const name=document.createElement('b');name.textContent=label;const value=document.createElement('span');value.textContent=payload.capabilities[key]==='available'?'已接入':'尚未实现';main.append(name,value);row.append(main);capabilities.append(row)})}
function renderStatusUnavailable(){const target=$('#status-summary');target.textContent='';target.append(metric('真实状态','不可用','本地状态读取失败','bad'));const capabilities=$('#capability-summary');capabilities.textContent='';const row=document.createElement('div');row.className='row';const main=document.createElement('div');main.className='row-main';const name=document.createElement('b');name.textContent='能力状态';const value=document.createElement('span');value.textContent='不可用';main.append(name,value);row.append(main);capabilities.append(row)}
function renderDiagnostics(payload){const target=$('#diagnostics-summary');target.textContent='';const health=payload.components.api==='available'?'正常':'不可用';const database=payload.components.database==='available'?'可读':'不可用';const migrations=Object.entries(payload.migrations).map(([name,count])=>`${name} ${count}`).join(' · ')||'不可用';target.append(metric('API',health,'本地回环服务'),metric('数据库',database,'只读聚合探针'),metric('迁移',migrations,'迁移状态实时读取'),metric('发布',payload.release.version,payload.release.status))}
async function fetchJson(path){const response=await fetch(path);if(!response.ok)throw new Error(`${path} unavailable`);return response.json()}
async function exchangeCommand(path, body){const result=$('#exchange-result');result.textContent='执行中…';try{const response=await fetch(path,body?{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}:undefined);const data=await response.json();if(!response.ok)throw new Error(data.detail||`${path} failed (${response.status})`);result.textContent=JSON.stringify(data,null,2)}catch(err){result.textContent='操作失败: '+err.message}}
async function refreshStatus(){try{renderStatus(validateStatus(await fetchJson('/workspace/api/status')))}catch{renderStatusUnavailable()}}
async function refreshDiagnostics(){try{renderDiagnostics(validateStatus(await fetchJson('/workspace/api/status')))}catch{const target=$('#diagnostics-summary');target.textContent='';target.append(metric('系统状态','不可用','本地状态读取失败','bad'))}}
function validateJobs(payload){if(!isRecord(payload)||payload.schema_version!=='v1'||!Array.isArray(payload.jobs))throw new Error('invalid workspace jobs');for(const job of payload.jobs){if(!isRecord(job)||Object.keys(job).length!==4||typeof job.activity!=='string'||typeof job.state!=='string'||typeof job.delivery_state!=='string'||typeof job.updated_at!=='string'||Number.isNaN(Date.parse(job.updated_at)))throw new Error('invalid workspace job')}return payload}
function renderJobs(payload){const target=$('#job-center');target.textContent='';if(!payload.jobs.length){const row=document.createElement('div');row.className='row';const main=document.createElement('div');main.className='row-main';const name=document.createElement('b');name.textContent='暂无任务记录';const detail=document.createElement('span');detail.textContent='导入资料后会在这里显示真实同步记录';main.append(name,detail);row.append(main);target.append(row);return}payload.jobs.forEach(job=>{const row=document.createElement('div');row.className='row';const main=document.createElement('div');main.className='row-main';const name=document.createElement('b');name.textContent=job.activity;const detail=document.createElement('span');detail.textContent=`状态：${job.state} · 投递：${job.delivery_state} · 更新：${new Date(job.updated_at).toLocaleString('zh-CN')}`;main.append(name,detail);const button=document.createElement('button');button.className='btn';button.type='button';button.dataset.action='task-select';button.dataset.activity=job.activity;button.textContent='查看驾驶舱';row.append(main,button);target.append(row)})}
function renderJobsUnavailable(){const target=$('#job-center');target.textContent='';const row=document.createElement('div');row.className='row';const main=document.createElement('div');main.className='row-main';const name=document.createElement('b');name.textContent='任务记录不可用';const detail=document.createElement('span');detail.textContent='本地任务状态读取失败';main.append(name,detail);row.append(main);target.append(row)}
async function refreshJobs(){try{renderJobs(validateJobs(await fetchJson('/workspace/api/jobs')))}catch{renderJobsUnavailable()}}
function validateDelivery(payload){if(!isRecord(payload)||payload.schema_version!=='v1'||typeof payload.dispatcher!=='string'||!isRecord(payload.summary)||!Array.isArray(payload.items))throw new Error('invalid workspace delivery');if(!Number.isInteger(payload.summary.jobs)||payload.summary.jobs<0||!isRecord(payload.summary.outbox)||!isRecord(payload.summary.receipts))throw new Error('invalid workspace delivery summary');for(const item of payload.items){if(!isRecord(item)||typeof item.activity!=='string'||typeof item.job_state!=='string'||typeof item.outbox_state!=='string'||typeof item.receipt_state!=='string'||!Number.isInteger(item.job_attempts)||!Number.isInteger(item.outbox_attempts))throw new Error('invalid workspace delivery item')}return payload}
function renderDelivery(payload){const target=$('#delivery-center');target.textContent='';const summary=document.createElement('div');summary.className='row';const main=document.createElement('div');main.className='row-main';const title=document.createElement('b');title.textContent=`投递器：${payload.dispatcher}`;const detail=document.createElement('span');detail.textContent=`任务：${payload.summary.jobs} · Outbox pending：${payload.summary.outbox.pending||0} · Receipt recorded：${payload.summary.receipts.recorded||0} · Receipt missing：${payload.summary.receipts.missing||0}`;main.append(title,detail);if((payload.summary.outbox.pending||0)>0){const button=document.createElement('button');button.className='btn';button.type='button';button.dataset.action='delivery-dispatch';button.textContent='投递下一条';main.append(button)}if((payload.summary.outbox.failed||0)>0){const button=document.createElement('button');button.className='btn';button.type='button';button.dataset.action='delivery-retry';button.textContent='重试失败投递';main.append(button)}summary.append(main);target.append(summary);payload.items.forEach(item=>{const row=document.createElement('div');row.className='row';const itemMain=document.createElement('div');itemMain.className='row-main';const name=document.createElement('b');name.textContent=item.activity;const detail=document.createElement('span');detail.textContent=`Job：${item.job_state}（尝试 ${item.job_attempts}） · Outbox：${item.outbox_state}（尝试 ${item.outbox_attempts}） · Receipt：${item.receipt_state}`;itemMain.append(name,detail);row.append(itemMain);target.append(row)})}
async function refreshDelivery(){try{renderDelivery(validateDelivery(await fetchJson('/workspace/api/delivery')))}catch{$('#delivery-center').textContent='投递与回执状态读取失败'}}
function renderTaskCockpit(job,lifecycle){if(!job)return;$('#cockpit-task-name').textContent=job.activity;$('#cockpit-task-state').textContent=`任务状态：${job.state}`;$('#cockpit-delivery-state').textContent=job.delivery_state;$('#cockpit-delivery-detail').textContent=`最近更新：${new Date(job.updated_at).toLocaleString('zh-CN')}`;const execution=lifecycle?.stages?.execution||{};const trace=lifecycle?.stages?.trace||{};const evaluation=lifecycle?.stages?.evaluation||{};const lesson=lifecycle?.stages?.lesson||{};$('#cockpit-lifecycle-state').textContent=execution.state||'不可用';$('#cockpit-lifecycle-detail').textContent=`追踪 ${trace.runs||0} · 评估候选 ${evaluation.candidates||0} · 教训 ${lesson.items||0}`;const target=$('#cockpit-timeline');target.textContent='';[['执行',execution.state||'未记录'],['追踪',trace.state||'未记录'],['评估',evaluation.state||'未记录'],['机器教训',lesson.state||'未记录']].forEach(([title,state])=>{const row=document.createElement('div');row.className='row';const main=document.createElement('div');main.className='row-main';const name=document.createElement('b');name.textContent=title;const detail=document.createElement('span');detail.textContent=`状态：${state}`;main.append(name,detail);row.append(main);target.append(row)})}
async function refreshTaskCockpit(){try{const [jobs,lifecycle]=await Promise.all([fetchJson('/workspace/api/jobs').then(validateJobs),fetchJson('/workspace/api/lifecycle').then(validateLifecycle)]);const selected=jobs.jobs[0];if(selected)renderTaskCockpit(selected,lifecycle)}catch{$('#cockpit-task-state').textContent='真实任务状态读取失败';$('#cockpit-lifecycle-state').textContent='不可用'}}
async function selectTask(activity){try{const [jobs,lifecycle]=await Promise.all([fetchJson('/workspace/api/jobs').then(validateJobs),fetchJson('/workspace/api/lifecycle').then(validateLifecycle)]);renderTaskCockpit(jobs.jobs.find(job=>job.activity===activity),lifecycle)}catch{$('#cockpit-task-state').textContent='任务详情读取失败'}}
async function refreshRuntime(){await Promise.all([refreshJobs(),refreshDelivery(),refreshTaskCockpit()])}
function commandId(prefix){return `${prefix}-${crypto.randomUUID()}`}
function renderResearch(payload){const target=$('#research-queue');target.textContent='';if(!isRecord(payload)||payload.schema_version!=='v1'||!Array.isArray(payload.items))throw new Error('invalid research queue');if(!payload.items.length){const row=document.createElement('div');row.className='row';row.textContent='暂无待人工审核的资料';target.append(row);return}payload.items.forEach(item=>{if(!isRecord(item)||typeof item.source!=='string'||!Number.isInteger(item.claim_count)||!Number.isInteger(item.evidence_count)||typeof item.verification!=='string')throw new Error('invalid research queue');const row=document.createElement('div');row.className='row';const main=document.createElement('div');main.className='row-main';const name=document.createElement('b');name.textContent=item.source;const detail=document.createElement('span');detail.textContent=`候选要点：${item.claim_count} · 证据：${item.evidence_count} · 核验：${item.verification}`;main.append(name,detail);const button=document.createElement('button');button.className='btn';button.type='button';button.dataset.action='research-approve';button.dataset.source=item.source;button.textContent='批准进入知识候选';row.append(main,button);target.append(row)})}
async function refreshResearch(){try{renderResearch(await fetchJson('/workspace/api/research'))}catch{$('#research-queue').textContent='本地待审核资料读取失败'}}
function renderKnowledge(payload){const target=$('#knowledge-queue');target.textContent='';if(!isRecord(payload)||payload.schema_version!=='v1'||!Array.isArray(payload.items))throw new Error('invalid knowledge queue');if(!payload.items.length){target.textContent='暂无已批准的知识候选';return}payload.items.forEach(item=>{if(!isRecord(item)||typeof item.source!=='string'||!Number.isInteger(item.claim_count)||!Number.isInteger(item.source_count)||typeof item.lifecycle!=='string')throw new Error('invalid knowledge item');const row=document.createElement('div');row.className='row';const main=document.createElement('div');main.className='row-main';const name=document.createElement('b');name.textContent=item.source;const detail=document.createElement('span');detail.textContent=`候选要点：${item.claim_count} · 来源：${item.source_count} · 生命周期：${item.lifecycle}`;main.append(name,detail);const button=document.createElement('button');button.className='btn';button.type='button';button.dataset.action='knowledge-start-learning';button.dataset.source=item.source;button.textContent='开始学习';row.append(main,button);target.append(row)})}
async function refreshKnowledge(){try{renderKnowledge(await fetchJson('/workspace/api/knowledge'))}catch{$('#knowledge-queue').textContent='本地知识候选读取失败'}}
function renderLearning(payload){const target=$('#learning-queue');target.textContent='';if(!isRecord(payload)||payload.schema_version!=='v1'||!Array.isArray(payload.items))throw new Error('invalid learning queue');if(!payload.items.length){target.textContent='暂无学习产物；先在藏识知识中开始学习';return}payload.items.forEach(item=>{if(!isRecord(item)||typeof item.source!=='string'||typeof item.status!=='string'||typeof item.statement!=='string'||!Number.isInteger(item.card_count)||!Number.isInteger(item.practice_count))throw new Error('invalid learning item');const row=document.createElement('div');row.className='row';const main=document.createElement('div');main.className='row-main';const name=document.createElement('b');name.textContent=item.source;const detail=document.createElement('span');detail.textContent=`${item.statement||'已生成学习卡片'} · 卡片：${item.card_count} · 练习：${item.practice_count} · 状态：${item.status}`;main.append(name,detail);const button=document.createElement('button');button.className='btn';button.type='button';button.dataset.action='learning-practice';button.dataset.source=item.source;button.textContent='记录练习';row.append(main,button);target.append(row)})}
async function refreshLearning(){try{renderLearning(await fetchJson('/workspace/api/learning'))}catch{$('#learning-queue').textContent='本地学习产物读取失败'}}
function renderEvolution(payload){const target=$('#evolution-summary');target.textContent='';if(!isRecord(payload)||payload.schema_version!=='v1'||!isRecord(payload.mastery)||!isRecord(payload.machine_knowledge))throw new Error('invalid evolution projection');target.append(metric('Mastery 信号',payload.mastery.signals,'真实练习计算'),metric('已掌握',payload.mastery.mastered,'仅来自真实信号','ok'),metric('机器候选',payload.machine_knowledge.candidate||0,'尚未进入 Runtime','warn'),metric('Runtime 已批准',payload.machine_knowledge.approved||0,'approved-only'))}
async function refreshEvolution(){try{renderEvolution(await fetchJson('/workspace/api/evolution'))}catch{$('#evolution-summary').textContent='本地评估状态读取失败'}}
function renderMachine(payload){const target=$('#machine-queue');target.textContent='';if(!isRecord(payload)||payload.schema_version!=='v1'||!Array.isArray(payload.items))throw new Error('invalid runtime knowledge');if(!payload.items.length){target.textContent='暂无机器知识候选；只有通过治理的内容才会进入 Runtime';return}payload.items.forEach(item=>{if(!isRecord(item)||typeof item.title!=='string'||typeof item.content!=='string'||!['candidate','approved'].includes(item.lifecycle))throw new Error('invalid runtime item');const row=document.createElement('div');row.className='row';const main=document.createElement('div');main.className='row-main';const name=document.createElement('b');name.textContent=item.title;const detail=document.createElement('span');detail.textContent=`${item.content} · 生命周期：${item.lifecycle}`;main.append(name,detail);if(item.lifecycle==='candidate'){const button=document.createElement('button');button.className='btn';button.type='button';button.dataset.action='runtime-approve';button.dataset.title=item.title;button.textContent='批准进入 Runtime';row.append(main,button)}else{row.append(main)}target.append(row)})}
async function refreshMachine(){try{renderMachine(await fetchJson('/workspace/api/runtime/candidates'))}catch{$('#machine-queue').textContent='机器知识治理状态读取失败'}}
function renderCanvas(canvas){const board=$('#canvas-board');board.textContent='';const nodes=Array.isArray(canvas?.nodes)?canvas.nodes:[];const edges=Array.isArray(canvas?.edges)?canvas.edges:[];if(!nodes.length){board.textContent='当前画布暂无已治理节点；候选研究不会自动进入画布';return}const positions=new Map();nodes.forEach(node=>{const x=Number(node.x)||0;const y=Number(node.y)||0;positions.set(node.id,{x,y});const card=document.createElement('article');card.className='canvas-node';card.style.left=`${x}px`;card.style.top=`${y}px`;const title=document.createElement('b');title.textContent=node.title||'已治理对象';const meta=document.createElement('span');meta.textContent=node.object_type||'card';card.append(title,meta);board.append(card)});edges.forEach(edge=>{const source=positions.get(edge.source_node_id);const target=positions.get(edge.target_node_id);if(!source||!target)return;const line=document.createElement('div');line.className='canvas-edge';const dx=target.x-source.x;const dy=target.y-source.y;line.style.left=`${source.x+80}px`;line.style.top=`${source.y+24}px`;line.style.width=`${Math.sqrt(dx*dx+dy*dy)}px`;line.style.transform=`rotate(${Math.atan2(dy,dx)}rad)`;line.title=edge.label||'已治理连接';board.append(line)})}
function renderCanvasList(payload){const target=$('#canvas-list');target.textContent='';const items=Array.isArray(payload?.canvases)?payload.canvases:[];if(!items.length){target.textContent='暂无画布；创建后才会写入本地 SQLite';return}items.forEach((item,index)=>{const row=document.createElement('div');row.className='row';const main=document.createElement('div');main.className='row-main';const name=document.createElement('b');name.textContent=item.name||'未命名画布';const detail=document.createElement('span');detail.textContent=`节点 ${item.node_count||0} · 位置已持久化`;main.append(name,detail);const button=document.createElement('button');button.className='btn';button.type='button';button.dataset.action='canvas-select';button.dataset.index=String(index);button.textContent='打开';row.append(main,button);target.append(row)})}
async function refreshCanvas(){try{const payload=await fetchJson('/kb/canvas');renderCanvasList(payload);const items=Array.isArray(payload.canvases)?payload.canvases:[];if(items[0])renderCanvas(await fetchJson(`/kb/canvas/${encodeURIComponent(items[0].id)}`));const lifecycle=await fetchJson('/workspace/api/lifecycle');const execution=lifecycle.stages?.execution||{};$('#canvas-replay').textContent=`执行回放：${execution.state||'未记录'} · 运行 ${execution.runs||0}` }catch{$('#canvas-list').textContent='认知画布读取失败';$('#canvas-board').textContent='真实画布数据不可用';$('#canvas-replay').textContent='执行回放不可用'}}
async function selectCanvas(index){try{const payload=await fetchJson('/kb/canvas');const item=(payload.canvases||[])[Number(index)];if(item)renderCanvas(await fetchJson(`/kb/canvas/${encodeURIComponent(item.id)}`))}catch{$('#canvas-board').textContent='画布读取失败'}}
async function createCanvas(){const name=$('#canvas-name').value.trim();if(!name)return;try{await fetch(`/kb/canvas?name=${encodeURIComponent(name)}`,{method:'POST'});$('#canvas-name').value='';await refreshCanvas()}catch{$('#canvas-list').textContent='画布创建失败；未确认写入结果'}}
function validateLifecycle(payload){if(!isRecord(payload)||payload.schema_version!=='v1'||payload.privacy!=='aggregate_only'||!isRecord(payload.stages))throw new Error('invalid lifecycle evidence');const stageNames=['permission','execution','trace','evaluation','lesson'];for(const name of stageNames){const stage=payload.stages[name];if(!isRecord(stage)||typeof stage.state!=='string')throw new Error(`invalid lifecycle stage: ${name}`);if(name==='permission'&&(!Number.isInteger(stage.gates)||!Number.isInteger(stage.blocked)))throw new Error('invalid lifecycle permission');if(name==='execution'&&!Number.isInteger(stage.runs))throw new Error('invalid lifecycle execution');if(name==='trace'&&!Number.isInteger(stage.runs))throw new Error('invalid lifecycle trace');if(name==='evaluation'&&(!Number.isInteger(stage.candidates)||!Number.isInteger(stage.approved)))throw new Error('invalid lifecycle evaluation');if(name==='lesson'&&!Number.isInteger(stage.items))throw new Error('invalid lifecycle lesson')}return payload}
function renderLifecycle(payload){const stages=payload.stages;const permission=stages.permission;$('#lifecycle-permission').textContent='';const permTone=permission.state==='blocked'?'bad':permission.state==='recorded'?'ok':'info';$('#lifecycle-permission').append(metric('权限门禁',permission.state,`门禁：${permission.gates} · 阻断：${permission.blocked}`,permTone));function stageRow(name,data){const target=$(name);target.textContent='';if(!data)return;let lines;if(name==='#lifecycle-execution')lines=[`状态：${data.state}`,'记录的执行事件'];else if(name==='#lifecycle-trace')lines=[`状态：${data.state}`,'记录的追踪事件'];else if(name==='#lifecycle-evaluation')lines=[`状态：${data.state}`,'评估候选治理'];else if(name==='#lifecycle-lesson')lines=[`状态：${data.state}`,'持久化机器教训'];const row=document.createElement('div');row.className='row';const main=document.createElement('div');main.className='row-main';const nameEl=document.createElement('b');const states=name==='#lifecycle-evaluation'?`候选：${data.candidates} · 批准：${data.approved}`:name==='#lifecycle-lesson'?`教训：${data.items}`:name==='#lifecycle-trace'||name==='#lifecycle-execution'?`记录：${data.runs}`:'';nameEl.textContent=states;const detail=document.createElement('span');detail.textContent=lines?lines[0]:'';main.append(nameEl,detail);row.append(main);target.append(row)}
stageRow('#lifecycle-execution',stages.execution);stageRow('#lifecycle-trace',stages.trace);stageRow('#lifecycle-evaluation',stages.evaluation);stageRow('#lifecycle-lesson',stages.lesson)}
function renderLifecycleUnavailable(){const permission=$('#lifecycle-permission');permission.textContent='';permission.append(metric('权限门禁','不可用','本地生命周期读取失败','bad'));for(const id of['#lifecycle-execution','#lifecycle-trace','#lifecycle-evaluation','#lifecycle-lesson']){const target=$(id);target.textContent='';const row=document.createElement('div');row.className='row';const main=document.createElement('div');main.className='row-main';const name=document.createElement('b');name.textContent='生命周期不可用';const detail=document.createElement('span');detail.textContent='本地生命周期读取失败';main.append(name,detail);row.append(main);target.append(row)}}
async function refreshLifecycle(){try{renderLifecycle(validateLifecycle(await fetchJson('/workspace/api/lifecycle')))}catch{renderLifecycleUnavailable()}}
function labelFor(page){for(const [,items] of nav){const item=items.find(candidate=>candidate[0]===page);if(item)return item[1]}return '功能尚未接入'}
const mobileSubnavQuery=window.matchMedia('(max-width: 960px)');
function activeModuleTrigger(){return $(`.rail-item[data-module="${state.module}"]`)}
function syncSubnavAccessibility(){const mobile=mobileSubnavQuery.matches;const open=mobile&&state.subnavOpen;const target=$('#nav');if(target){target.toggleAttribute('inert',mobile&&!open);target.setAttribute('aria-hidden',String(mobile&&!open))}$$('.rail-item[data-module]').forEach(button=>button.setAttribute('aria-expanded',String(mobile?open&&button===state.subnavTrigger:button===activeModuleTrigger())))}
function closeSubnav({restoreFocus=false}={}){const wasOpen=state.subnavOpen;const trigger=state.subnavTrigger;state.subnavOpen=false;document.body.classList.remove('subnav-open');syncSubnavAccessibility();if(restoreFocus&&wasOpen&&trigger?.isConnected)trigger.focus()}
function handleSubnavBreakpointChange(event){const target=$('#nav');state.subnavOpen=false;document.body.classList.remove('subnav-open');if(event.matches&&target?.contains(document.activeElement))activeModuleTrigger()?.focus();applyShellState();syncSubnavAccessibility()}
mobileSubnavQuery.addEventListener('change',handleSubnavBreakpointChange);
async function refreshVault(){const root=$('#vault-root')?.value.trim();if(!root)return;try{const response=await fetch('/workspace/api/vault/inspect',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({root})});if(!response.ok)throw new Error('vault inspect failed');const payload=await response.json();$('#vault-files').textContent=payload.files.map(item=>`${item.relative_path} · ${item.kind} · ${item.file_size} B`).join('\n')||'Vault 为空';$('#vault-loss').textContent=payload.loss_report.length?JSON.stringify(payload.loss_report):'未发现损失报告'}catch{$('#vault-files').textContent='Vault 读取失败；请确认根目录和本地权限';$('#vault-loss').textContent='不可用'}}
async function searchVault(){const root=$('#vault-root')?.value.trim();const query=$('#vault-query')?.value.trim();if(!root||!query)return;try{const response=await fetch('/workspace/api/vault/search',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({root,query})});if(!response.ok)throw new Error('vault search failed');const payload=await response.json();$('#vault-results').textContent=payload.results.map(item=>`${item.relative_path}\n${item.snippet}`).join('\n\n')||'没有匹配结果'}catch{$('#vault-results').textContent='搜索失败；请确认 Vault 根目录'}}
async function openVaultFile(){const root=$('#vault-root')?.value.trim();const relativePath=$('#vault-edit-file')?.value.trim();if(!root||!relativePath)return;const status=$('#vault-save-status'),btn=$('#vault-save-btn'),editor=$('#vault-editor');status.textContent='读取中…';try{const response=await fetch('/workspace/api/vault/file',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({root,relative_path:relativePath})});if(!response.ok)throw new Error('vault file failed');const payload=await response.json();editor.value=payload.raw_text;state.vaultOpenHash=payload.source_hash;state.vaultOpenPath=relativePath;btn.disabled=false;status.textContent=`已打开 · 磁盘哈希 ${payload.source_hash.slice(0,12)}…`}catch{editor.value='';state.vaultOpenHash=null;btn.disabled=true;status.textContent='打开失败；请确认相对路径和 Vault 根目录'}}
async function saveVaultFile(){const root=$('#vault-root')?.value.trim();if(!root||!state.vaultOpenHash)return;const status=$('#vault-save-status');status.textContent='保存中…';try{const response=await fetch('/workspace/api/vault/write',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({root,relative_path:state.vaultOpenPath,content:$('#vault-editor').value,expected_hash:state.vaultOpenHash})});if(response.status===409){const detail=(await response.json()).detail;status.textContent=`冲突：文件已在磁盘被修改（当前哈希 ${String(detail.current_hash).slice(0,12)}…）；已拒绝写入，请重新打开`;return}if(!response.ok)throw new Error('vault write failed');const payload=await response.json();state.vaultOpenHash=payload.source_hash;status.textContent=`已保存 · 新哈希 ${payload.source_hash.slice(0,12)}… · 备份 ${payload.backup_path.split('\\').pop()}`;void refreshVault()}catch{status.textContent='保存失败；请确认 Vault 权限'}}
async function listVaultBackups(){const root=$('#vault-root')?.value.trim();const relativePath=$('#vault-edit-file')?.value.trim();const status=$('#vault-restore-status');if(!root||!relativePath){status.textContent='请先输入相对路径';return}status.textContent='加载中…';try{const response=await fetch('/workspace/api/vault/backups',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({root,relative_path:relativePath})});if(!response.ok)throw new Error('vault backups failed');const payload=await response.json();const select=$('#vault-backups');select.textContent='';if(!payload.backups.length){const empty=document.createElement('option');empty.value='';empty.textContent='（无备份）';select.appendChild(empty);$('#vault-restore-btn').disabled=true;status.textContent='该文件暂无备份';return}payload.backups.forEach(backup=>{const option=document.createElement('option');option.value=backup.backup_name;option.textContent=`${backup.backup_name} · ${Math.round(backup.file_size)} B`;select.appendChild(option)});$('#vault-restore-btn').disabled=false;status.textContent=`找到 ${payload.backups.length} 个备份`}catch{status.textContent='备份列表加载失败'}}
async function restoreVaultBackup(){const root=$('#vault-root')?.value.trim();const relativePath=$('#vault-edit-file')?.value.trim();const backupName=$('#vault-backups')?.value;const status=$('#vault-restore-status');if(!root||!relativePath||!backupName){status.textContent='请先选择备份';return}status.textContent='恢复中…';try{const response=await fetch('/workspace/api/vault/restore',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({root,relative_path:relativePath,backup_name:backupName})});if(!response.ok)throw new Error('vault restore failed');const payload=await response.json();status.textContent=`已恢复 ${payload.restored_from} · 新哈希 ${payload.source_hash.slice(0,12)}…`;state.vaultOpenHash=payload.source_hash;const opened=await fetch('/workspace/api/vault/file',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({root,relative_path:relativePath})});if(opened.ok){const filePayload=await opened.json();$('#vault-editor').value=filePayload.raw_text;$('#vault-save-status').textContent=`已重新加载 · 哈希 ${filePayload.source_hash.slice(0,12)}…`;state.vaultOpenHash=filePayload.source_hash}void refreshVault();void listVaultBackups()}catch{status.textContent='恢复失败；请确认备份文件与权限'}}
function openPage(requestedPage){const page=productRoutes.has(requestedPage)?requestedPage:'unavailable';const requested=document.getElementById(`page-${page}`);const visible=requested||document.getElementById('page-unavailable');state.page=page;closeSubnav();renderNav();$$('.page').forEach(section=>section.classList.toggle('active',section===visible));if(visible.id==='page-unavailable')$('#unavailable-title').textContent=labelFor(page);history.replaceState(null,'',`#${page}`);if(page==='overview')void refreshStatus();if(page==='vault')void refreshVault();if(page==='diagnostics')void refreshDiagnostics();if(page==='runtime')void refreshRuntime();if(page==='research')void refreshResearch();if(page==='knowledge')void refreshKnowledge();if(page==='canvas')void refreshCanvas();if(page==='learning')void refreshLearning();if(page==='evolution')void refreshEvolution();if(page==='machine')void refreshMachine();if(page==='evidence')void refreshLifecycle()}
function openIntake(trigger){const modal=$('#intake-modal'),result=$('#intake-result');state.intakeTrigger=trigger;result.textContent='';result.style.display='none';modal.setAttribute('aria-hidden','false');modal.classList.add('open');$('#intake-url').focus()}
function closeIntake(){const modal=$('#intake-modal');if(!modal.classList.contains('open'))return;modal.classList.remove('open');modal.setAttribute('aria-hidden','true');const trigger=state.intakeTrigger;state.intakeTrigger=null;if(trigger?.isConnected)trigger.focus()}
function trapIntakeFocus(event){if(event.key!=='Tab'||!$('#intake-modal').classList.contains('open'))return;const focusable=$$('#intake-modal button:not([disabled]),#intake-modal input:not([disabled])');if(!focusable.length)return;const first=focusable[0],last=focusable.at(-1);if(event.shiftKey&&document.activeElement===first){event.preventDefault();last.focus()}else if(!event.shiftKey&&document.activeElement===last){event.preventDefault();first.focus()}}
function validateIntakeResult(payload){const sourceTypes=new Set(['file','web','github_repository']);if(!isRecord(payload)||!sourceTypes.has(payload.source_type)||typeof payload.requires_human_review!=='boolean')throw new Error('invalid intake result');if(payload.source_type==='file'){if(!['file_name','format','engine'].every(key=>typeof payload[key]==='string'&&payload[key].trim())||!Number.isInteger(payload.char_count)||payload.char_count<0||(payload.content_preview!==undefined&&typeof payload.content_preview!=='string'))throw new Error('invalid file intake result')}else if(!['source_count','claim_count','evidence_count'].every(key=>Number.isInteger(payload[key])&&payload[key]>=0))throw new Error('invalid source intake result');return payload}
function intakeFailureDetail(payload){return isRecord(payload)&&typeof payload.detail==='string'&&payload.detail.trim()?payload.detail:'请检查资料后重试'}
async function showIntakeResult(response){const result=$('#intake-result');let payload;try{payload=await response.json()}catch{result.textContent=`处理失败\n${response.ok?'本地服务返回无效结果':'无法读取处理结果'}`;return}if(!response.ok){result.textContent=`处理失败\n${intakeFailureDetail(payload)}`;return}try{payload=validateIntakeResult(payload)}catch{result.textContent='处理失败\n本地服务返回无效结果';return}const lines=['处理完成'];const sourceNames={file:'本地文件',web:'网页',github_repository:'GitHub仓库'};lines.push(`来源：${sourceNames[payload.source_type]}`);if(payload.format)lines.push(`格式：${payload.format}`);if(payload.engine)lines.push(`引擎：${payload.engine}`);if(Number.isInteger(payload.char_count))lines.push(`内容长度：${payload.char_count} 字符`);if(Number.isInteger(payload.source_count))lines.push(`来源记录：${payload.source_count}`);if(Number.isInteger(payload.claim_count))lines.push(`候选要点：${payload.claim_count}`);if(Number.isInteger(payload.evidence_count))lines.push(`证据记录：${payload.evidence_count}`);if(payload.requires_human_review)lines.push('下一步：等待人工复核');if(typeof payload.content_preview==='string'&&payload.content_preview.trim())lines.push(`内容预览：${payload.content_preview.trim()}`);result.textContent=lines.join('\n');await Promise.all([refreshStatus(),refreshActivityDock()]);if(state.page==='runtime')await refreshRuntime()}
async function runIntake(requestFactory){const result=$('#intake-result'),buttons=$$('#intake-modal button[type="submit"]');if(buttons.some(button=>button.disabled))return;result.style.display='block';result.textContent='处理中…';buttons.forEach(button=>{button.disabled=true});try{await showIntakeResult(await requestFactory())}catch{result.textContent='处理失败\n无法连接本地服务，请重试'}finally{buttons.forEach(button=>{button.disabled=false})}}
document.addEventListener('click',event=>{const theme=event.target.closest('button[data-theme]');if(theme){setTheme(theme.dataset.theme);return}const page=event.target.closest('[data-page]');if(page){const restoreNavFocus=page.classList.contains('nav-item');const mobileTrigger=restoreNavFocus&&window.matchMedia('(max-width: 960px)').matches?state.subnavTrigger:null;openPage(page.dataset.page);if(mobileTrigger?.isConnected)mobileTrigger.focus();else if(restoreNavFocus)$(`.nav-item[data-page="${page.dataset.page}"]`)?.focus();return}const action=event.target.closest('[data-action]');if(!action)return;if(action.dataset.action==='task-select'){void selectTask(action.dataset.activity);return}if(action.dataset.action==='canvas-select'){void selectCanvas(action.dataset.index);return}if(action.dataset.action==='canvas-create'){void createCanvas();return}if(action.dataset.action==='intake')openIntake(action);if(action.dataset.action==='vault-refresh')void refreshVault();if(action.dataset.action==='vault-search')void searchVault();if(action.dataset.action==='vault-open')void openVaultFile();if(action.dataset.action==='vault-save')void saveVaultFile();if(action.dataset.action==='vault-list-backups')void listVaultBackups();if(action.dataset.action==='vault-restore')void restoreVaultBackup();if(action.dataset.action==='intake-close')closeIntake();if(action.dataset.action==='refresh'){void refreshDiagnostics();void refreshStatus()}if(action.dataset.action==='jobs-refresh')void refreshRuntime();if(action.dataset.action==='research-refresh')void refreshResearch();if(action.dataset.action==='knowledge-refresh')void refreshKnowledge();if(action.dataset.action==='learning-refresh')void refreshLearning();if(action.dataset.action==='evolution-refresh')void refreshEvolution();if(action.dataset.action==='machine-refresh')void refreshMachine();if(action.dataset.action==='lifecycle-refresh')void refreshLifecycle();if(action.dataset.action==='delivery-dispatch'){fetch('/workspace/api/delivery/dispatch',{method:'POST'}).then(response=>{if(!response.ok)throw new Error('delivery failed');return refreshRuntime()}).catch(()=>{$('#delivery-center').textContent='投递失败；请刷新状态后重试'})}if(action.dataset.action==='delivery-retry'){fetch('/workspace/api/delivery/retry',{method:'POST'}).then(response=>{if(!response.ok)throw new Error('retry failed');return refreshRuntime()}).catch(()=>{$('#delivery-center').textContent='重试失败；请刷新状态后重试'})}if(action.dataset.action==='research-approve'){fetch('/workspace/api/research/approve',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({command_id:commandId('research-review'),source:action.dataset.source})}).then(response=>{if(!response.ok)throw new Error('approval failed');return Promise.all([refreshResearch(),refreshKnowledge()])}).catch(()=>{$('#research-queue').textContent='批准失败；请刷新队列后重试'})}if(action.dataset.action==='knowledge-start-learning'){fetch('/workspace/api/knowledge/start-learning',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({command_id:commandId('learning-start'),source:action.dataset.source})}).then(response=>{if(!response.ok)throw new Error('learning start failed');return Promise.all([refreshKnowledge(),refreshLearning()])}).catch(()=>{$('#knowledge-queue').textContent='开始学习失败；请刷新后重试'})}if(action.dataset.action==='learning-practice'){fetch('/workspace/api/learning/practice',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({command_id:commandId('learning-practice'),source:action.dataset.source,quality:5})}).then(response=>{if(!response.ok)throw new Error('practice failed');return Promise.all([refreshLearning(),refreshEvolution(),refreshMachine()])}).catch(()=>{$('#learning-queue').textContent='记录练习失败；请刷新后重试'})}if(action.dataset.action==='runtime-approve'){fetch('/workspace/api/runtime/approve',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({command_id:commandId('runtime-approve'),title:action.dataset.title})}).then(response=>{if(!response.ok)throw new Error('runtime approval failed');return Promise.all([refreshMachine(),refreshEvolution()])}).catch(()=>{$('#machine-queue').textContent='Runtime 治理批准失败；请刷新后重试'})}});
document.addEventListener('keydown',event=>{trapIntakeFocus(event);if(event.key==='Escape'){closeIntake();closeSubnav({restoreFocus:true})}});
$('#intake-modal').addEventListener('click',event=>{if(event.target.id==='intake-modal')closeIntake()});
$('#intake-url-form').addEventListener('submit',async event=>{event.preventDefault();const url=new FormData(event.currentTarget).get('url');await runIntake(()=>fetch('/workspace/api/intake/url',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({url})}))});
$('#intake-file-form').addEventListener('submit',async event=>{event.preventDefault();await runIntake(()=>fetch('/workspace/api/intake/upload',{method:'POST',body:new FormData(event.currentTarget)}))});
window.addEventListener('hashchange',()=>openPage(location.hash.slice(1)||'overview'));
setTheme(state.theme);openPage(location.hash.slice(1)||'overview');setInterval(()=>{$('#clock').textContent=new Date().toLocaleTimeString('zh-CN',{hour:'2-digit',minute:'2-digit',second:'2-digit'})},1000);setInterval(()=>{if(state.page==='runtime')void refreshRuntime();if(state.page==='canvas')void refreshCanvas();if(state.page==='evidence')void refreshLifecycle()},3000);

function showShellToast(message){const toast=$('#toast');if(!toast)return;toast.textContent=message;toast.classList.add('show');window.clearTimeout(showShellToast.timer);showShellToast.timer=window.setTimeout(()=>toast.classList.remove('show'),2600)}
function applyShellState({restoreFocus=false}={}){document.body.classList.toggle('inspector-collapsed',state.inspectorCollapsed);document.body.classList.toggle('dock-collapsed',state.dockCollapsed);const inspector=$('.inspector');const mobile=mobileSubnavQuery.matches;const open=!state.inspectorCollapsed;if(inspector){inspector.classList.toggle('open',open);inspector.toggleAttribute('inert',mobile&&!open);inspector.setAttribute('aria-hidden',String(mobile&&!open))}$$('[data-action="inspector-toggle"]').forEach(button=>{button.setAttribute('aria-expanded',String(open));button.setAttribute('aria-label',open?'折叠上下文与证据检查器':'展开上下文与证据检查器')});const internal=$('.inspector-internal-trigger');if(internal)internal.textContent='×';const external=$('.inspector-external-trigger');if(external)external.textContent='◧';const dockButton=$('[data-action="dock-toggle"]');if(dockButton)dockButton.textContent=state.dockCollapsed?'⌃':'⌄';if(dockButton)dockButton.setAttribute('aria-label',state.dockCollapsed?'展开活动坞':'折叠活动坞');if(restoreFocus&&state.inspectorTrigger?.isConnected)state.inspectorTrigger.focus()}
function setModule(module,trigger){const group=nav.find(([name])=>groupModule[name]===module);if(!group)return;state.module=module;state.subnavTrigger=trigger||null;localStorage.setItem('aa-module',module);const firstPage=group[1][0][0];openPage(firstPage);$('.subnav')?.scrollTo({top:0,behavior:'smooth'});if(window.matchMedia('(max-width: 960px)').matches){state.subnavOpen=true;document.body.classList.add('subnav-open');syncSubnavAccessibility();const firstRoute=$(`.nav-group[data-module="${module}"] .nav-item`);firstRoute?.focus()}else syncSubnavAccessibility()}
async function refreshActivityDock(){try{const [jobs,delivery,research]=await Promise.all([fetchJson('/workspace/api/jobs').then(validateJobs),fetchJson('/workspace/api/delivery').then(validateDelivery),fetchJson('/workspace/api/research')]);if(!isRecord(research)||research.schema_version!=='v1'||!Array.isArray(research.items))throw new Error('invalid workspace research');const reviewCount=research.items.length;const pending=(delivery.summary.outbox?.pending||0)+(delivery.summary.outbox?.failed||0);$('#dock-jobs').textContent=String(jobs.jobs.length);$('#dock-delivery').textContent=`${pending} / ${delivery.summary.receipts?.recorded||0}`;$('#dock-review').textContent=String(reviewCount);$('#dock-summary').textContent=`${jobs.jobs.length} jobs · ${pending} pending/failed · ${reviewCount} review`;$('#inspector-status').textContent='本地 API 可读';$('#inspector-evidence').textContent=`${delivery.summary.receipts?.recorded||0} receipts`}catch{$('#dock-summary').textContent='真实活动读取失败';$('#dock-jobs').textContent='不可用';$('#dock-delivery').textContent='不可用';$('#dock-review').textContent='不可用';$('#inspector-status').textContent='不可用';$('#inspector-evidence').textContent='等待重新读取'}}
document.addEventListener('click',event=>{const rail=event.target.closest('.rail-item[data-module]');if(rail){setModule(rail.dataset.module,rail);return}const action=event.target.closest('[data-action]');if(!action)return;if(action.dataset.action==='inspector-toggle'){const closing=!state.inspectorCollapsed;if(!closing)state.inspectorTrigger=action;state.inspectorCollapsed=closing;localStorage.setItem('aa-inspector',state.inspectorCollapsed?'collapsed':'open');applyShellState({restoreFocus:closing});if(!closing)$('.inspector-internal-trigger')?.focus();return}if(action.dataset.action==='dock-toggle'){state.dockCollapsed=!state.dockCollapsed;localStorage.setItem('aa-dock',state.dockCollapsed?'collapsed':'open');applyShellState();return}});
applyShellState();syncSubnavAccessibility();void refreshActivityDock();setInterval(()=>void refreshActivityDock(),3000);


/* AXW-022A PDF.js evidence viewer — content-addressed, read-only.
   Renders original PDF bytes from /workspace/api/pdf/<sha256:key>. */
(function(){
  if (typeof pdfjsLib === "undefined") { return; } // pdf.min.js not loaded; degrade silently
  const state = { doc: null, page: 1, zoom: 1.0, pending: 0, matchPage: -1 };
  // Configure the PDF.js worker lazily from the same-origin asset (CSP-safe).
  // Done at definition time inside the closure but only touches a static
  // string assignment (no network / no worker spawn until a PDF is opened).
  try { if (pdfjsLib) pdfjsLib.GlobalWorkerOptions.workerSrc = "/workspace/assets/pdf.worker.min.js"; } catch (e) {}
  const viewer = () => document.getElementById("pdf-viewer");
  const $info = () => document.getElementById("pdf-page-info");
  const $zinfo = () => document.getElementById("pdf-zoom-info");
  const $prev = () => document.getElementById("pdf-prev");
  const $next = () => document.getElementById("pdf-next");

  function setButtons() {
    if (!$prev() || !$next()) return;
    $prev().disabled = !state.doc || state.page <= 1;
    $next().disabled = !state.doc || state.page >= state.doc.numPages;
  }

  async function renderPage() {
    if (!state.doc) return;
    cachedSelection = "";
    const page = await state.doc.getPage(state.page);
    const base = page.getViewport({ scale: state.zoom });
    const container = viewer();
    container.textContent = "";
    // AXW-022B: the canvas paints the page; an overlay text layer makes the
    // text selectable so "批注为证据" can capture the selection.
    const canvas = document.createElement("canvas");
    const ctx = canvas.getContext("2d");
    const dpr = window.devicePixelRatio || 1;
    canvas.width = base.width * dpr;
    canvas.height = base.height * dpr;
    canvas.style.width = base.width + "px";
    canvas.style.height = base.height + "px";
    canvas.style.position = "absolute";
    canvas.style.top = "0";
    canvas.style.left = "0";
    await page.render({ canvasContext: ctx, viewport: base, transform: dpr !== 1 ? [dpr,0,0,dpr,0,0] : null }).promise;
    const textLayer = document.createElement("div");
    textLayer.className = "pdf-text-layer";
    textLayer.style.position = "absolute";
    textLayer.style.top = "0";
    textLayer.style.left = "0";
    textLayer.style.width = base.width + "px";
    textLayer.style.height = base.height + "px";
    textLayer.style.color = "transparent";
    textLayer.style.overflow = "hidden";
    textLayer.style.cursor = "text";
    const wrap = document.createElement("div");
    wrap.style.position = "relative";
    wrap.style.width = base.width + "px";
    wrap.style.height = base.height + "px";
    wrap.style.margin = "0 auto";
    wrap.appendChild(canvas);
    wrap.appendChild(textLayer);
    container.appendChild(wrap);
    const textContent = await page.getTextContent();
    for (const item of textContent.items) {
      const tx = pdfjsLib.Util.transform(
        pdfjsLib.Util.transform(base.transform, item.transform),
        [1, 0, 0, 1, 0, 0]
      );
      const span = document.createElement("span");
      span.textContent = item.str;
      span.style.position = "absolute";
      span.style.whiteSpace = "pre";
      span.style.transformOrigin = "0 0";
      span.style.transform = `translate(${tx[4]}px, ${tx[5]}px) scale(${tx[0]}, ${tx[3]})`;
      span.style.fontSize = "1px";
      textLayer.appendChild(span);
    }
    if ($info()) $info().textContent = `${state.page} / ${state.doc.numPages}`;
    setButtons();
  }

  async function loadPdf(key) {
    const input = document.getElementById("pdf-key-input");
    if (!input) return;
    const k = (key || input.value || "").trim();
    if (!/^sha256:[0-9a-f]{64}$/i.test(k)) { alert("内容键必须为 sha256:<64位hex>"); return; }
    const container = viewer();
    if (container) container.textContent = "加载 PDF 字节…";
    try {
      const resp = await fetch("/workspace/api/pdf/" + encodeURIComponent(k));
      if (!resp.ok) { throw new Error("HTTP " + resp.status); }
      const data = await resp.arrayBuffer();
      state.doc = await pdfjsLib.getDocument({ data: data }).promise;
      state.page = 1; state.zoom = 1.0; state.matchPage = -1;
      if ($zinfo()) $zinfo().textContent = "100%";
      await renderPage();
    } catch (err) {
      if (container) { container.textContent = ""; container.innerHTML = '<div class="empty"><b>PDF 加载失败</b><p>' + err.message + '</p></div>'; }
    }
  }

  async function searchPdf() {
    if (!state.doc) return;
    const q = (document.getElementById("pdf-search-input").value || "").trim();
    if (!q) { alert("请输入搜索词"); return; }
    state.matchPage = -1;
    for (let i = 1; i <= state.doc.numPages; i++) {
      const page = await state.doc.getPage(i);
      const text = await page.getTextContent();
      const hay = text.items.map(function(it){ return it.str || ""; }).join(" ");
      if (hay.indexOf(q) !== -1) { state.matchPage = i; break; }
    }
    if (state.matchPage > 0) { state.page = state.matchPage; await renderPage(); alert("在第 " + state.matchPage + " 页找到匹配"); }
    else { alert("未找到匹配：" + q); }
  }

  /* AXW-022B evidence annotation — pin a selection as a content-addressed
     EvidenceAnchor and jump back from a stored anchor_id. */
  function currentKey() {
    const input = document.getElementById("pdf-key-input");
    return (input && input.value || "").trim();
  }
  function selectedText() {
    const sel = window.getSelection();
    return (sel && sel.toString() || "").trim();
  }
  /* AXW-022B: enable the annotation button only when the user has an
     actual selection of PDF text; disable it again on selection loss.
     The selected text is cached because clicking the button clears the
     browser selection on mousedown before the click handler runs.
     (Regression-covered by scripts/a0_browser_smoke.py: exercise_pdf_reader;
      CI runs the full Chromium browser, local dev defaults to headless-shell;
      smoke entrypoint wraps failures into workflow annotations and anchors
      the repo root on sys.path for direct script runs; the anchor is
      grandfathered in scripts/check_architecture.py.) */
  let cachedSelection = "";
  function syncAnnotateEnabled() {
    const btn = document.getElementById("pdf-annotate");
    if (!btn) return;
    const text = selectedText();
    // Only refresh the cache on a real selection; mousedown on the button
    // clears the browser selection before the click handler runs, and we
    // must not let that erase the text we are about to annotate.
    if (text) cachedSelection = text;
    btn.disabled = !(state.doc && state.page && cachedSelection);
  }
  document.addEventListener("selectionchange", syncAnnotateEnabled);
  document.addEventListener("keyup", syncAnnotateEnabled);
  document.addEventListener("mouseup", syncAnnotateEnabled);
  async function annotateEvidence() {
    const $info = document.getElementById("pdf-anchor-info");
    if (!state.doc || !state.page) { alert("请先打开 PDF"); return; }
    const key = currentKey();
    if (!/^sha256:[0-9a-f]{64}$/i.test(key)) { alert("内容键无效"); return; }
    const text = cachedSelection || selectedText();
    if (!text) { alert("请先在页面中选中一段文本作为证据"); return; }
    if ($info) $info.textContent = "写入证据锚点…";
    try {
      const rawSha = key.slice("sha256:".length);
      const resp = await fetch("/workspace/api/evidence/anchor", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          raw_sha256: rawSha,
          source_revision: key,
          locator: { page: state.page, selection: text.slice(0, 200) }
        })
      });
      if (!resp.ok) { throw new Error("HTTP " + resp.status); }
      const data = await resp.json();
      if ($info) $info.textContent = "锚点 " + data.anchor_id;
      else alert("锚点 " + data.anchor_id);
    } catch (err) {
      if ($info) $info.textContent = "写入失败: " + err.message;
    }
  }
  async function jumpToAnchor() {
    const $info = document.getElementById("pdf-anchor-info");
    const input = document.getElementById("pdf-anchor-input");
    const id = (input && input.value || "").trim();
    if (!id) { alert("请输入证据锚点 id (ev...) "); return; }
    if ($info) $info.textContent = "解析锚点…";
    try {
      const resp = await fetch("/workspace/api/evidence/anchor/" + encodeURIComponent(id));
      if (!resp.ok) { throw new Error("HTTP " + resp.status); }
      const a = await resp.json();
      const page = a && a.locator && a.locator.page;
      if (state.doc && typeof page === "number" && page >= 1 && page <= state.doc.numPages) {
        state.page = page; await renderPage();
      }
      const loc = a && a.locator ? JSON.stringify(a.locator) : "";
      if ($info) $info.textContent = "已回跳页 " + (page || "?") + (loc ? " · " + loc : "");
    } catch (err) {
      if ($info) $info.textContent = "回跳失败: " + err.message;
    }
  }

  document.addEventListener("click", function(ev){
    const el = ev.target.closest("[data-action]");
    if (!el) return;
    switch (el.dataset.action) {
      case "pdf-load": void loadPdf(); break;
      case "pdf-prev": if (state.doc && state.page > 1) { state.page--; void renderPage(); } break;
      case "pdf-next": if (state.doc && state.page < state.doc.numPages) { state.page++; void renderPage(); } break;
      case "pdf-zoom-in": state.zoom = Math.min(3, Math.round((state.zoom + 0.25) * 100) / 100); if ($zinfo()) $zinfo().textContent = Math.round(state.zoom*100) + "%"; void renderPage(); break;
      case "pdf-zoom-out": state.zoom = Math.max(0.5, Math.round((state.zoom - 0.25) * 100) / 100); if ($zinfo()) $zinfo().textContent = Math.round(state.zoom*100) + "%"; void renderPage(); break;
      case "pdf-search": void searchPdf(); break;
      case "pdf-annotate": void annotateEvidence(); break;
      case "pdf-jump": void jumpToAnchor(); break;
      case "exchange-export": void exchangeCommand("/workspace/api/exchange/export", {}); break;
      case "exchange-verify": void exchangeCommand("/workspace/api/exchange/verify"); break;
      case "backup-create": void exchangeCommand("/workspace/api/backup/create", {}); break;
      case "backup-verify": void exchangeCommand("/workspace/api/backup/verify"); break;
    }
  });
})();
