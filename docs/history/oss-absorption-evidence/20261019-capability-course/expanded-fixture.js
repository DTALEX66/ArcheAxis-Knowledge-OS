
(() => {
  // Enough of a Tauri host for the formal surfaces to mount. The app decides it is on the desktop
  // host by the presence of `window.__TAURI__.core.invoke`, and the recovery contract decides
  // whether it shows the shell or the recovery screen; nothing here claims to be the native host.
  const bodies = {
    sources_list: { sources: [{"source_id": "src_a0_nav3", "source_revision": "sha256:de81c167a8e05757e6fba2e6", "sha256": "de81c167a8e05757e6fba2e6123703873fb3d4219cb3a3ef01b55af7cbfb471e", "original_name": "a0-nav3-sample.txt", "imported_at": "2026-10-08T00:00:00Z"}] },
    documents_list: { documents: [], next_cursor: null, snapshot_count: [].length },
    learning_items: { items: [], count: 0 },
    capabilities_list: { capabilities: [] },
    anchors_list: { anchors: [] },
    source_original: {"source_id": "src_a0_nav3", "name": "a0-nav3-sample.txt", "media_type": "text/plain", "sha256": "de81c167a8e05757e6fba2e6123703873fb3d4219cb3a3ef01b55af7cbfb471e", "content_base64": "YTAg6Zeo56aB5qC35p2/5Y6f5Lu277ya5LuF5L6b5a6/5Li75Zue6K+75a+86Iiq5bGC57qn5L2/55So"},
    workspace_backups: { backups: [] },
    system_version: { runtime: "archeaxis-api", contract: "0.1.0-outline", schema_version: 1,
                      sqlite_version: "3.51.3" },
  };
  // A declared outage, not a silent one: the named operations answer with this status so the gate
  // can read what the surface claims when a Core read cannot be finished.
  const faults = {};
  
  const current = new Map(), history = new Map(), calls = [];
  const copy = value => structuredClone(value);
  const text = node => node.text ?? (node.content ?? []).map(text).join("\n");
  async function makeDocument(id, title, editor, version) {
    editor = copy(editor);
    editor.content.forEach((node, ordinal) => {node.attrs = {...node.attrs, block_id:node.attrs?.block_id ?? `a0_p${ordinal + 1}`};});
    const projection = text(editor);
    const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(JSON.stringify(editor)));
    return {document_id:id,source_id:null,source_revision:null,title,version,editor_json:copy(editor),
      text_projection:projection,content_sha256:[...new Uint8Array(digest)].map(n=>n.toString(16).padStart(2,"0")).join(""),blocks:editor.content.map((node,ordinal)=>({block_id:node.attrs.block_id,kind:node.type,ordinal,node_json:copy(node),text_projection:text(node),codec_status:"known"}))};
  }
  function retain(doc) { current.set(doc.document_id,copy(doc)); history.set(`${doc.document_id}:${doc.version}`,copy(doc)); }
  const ready = Promise.all([1,2,3].map(async n => retain(await makeDocument(`a0_target_${n}`,
    `引用目标 ${n} · 独立历史正文`,{type:"doc",content:[{type:"paragraph",content:[{type:"text",text:`绑定历史正文 ${n} v1`}]}]},1))));
  window.__A0_DOCUMENT_FIXTURE__ = {calls, snapshot:()=>copy([...current.values()]), advance:async()=>{
    await ready;
    for (const n of [1,2,3]) retain(await makeDocument(`a0_target_${n}`,`引用目标 ${n} · 独立历史正文`,
      {type:"doc",content:[{type:"paragraph",content:[{type:"text",text:`当前新正文 ${n} v2`}]}]},2));
  }};
  const documentFixture = async (operation,payload) => {
    await ready; calls.push({operation,payload:copy(payload)});
    if (operation === "documents_list") return {status:200,body:{documents:[...current.values()].map(d=>({
      document_id:d.document_id,source_id:d.source_id,source_revision:d.source_revision,title:d.title,version:d.version,content_sha256:d.content_sha256})),next_cursor:null,snapshot_count:current.size}};
    if (operation === "document_create") {
      const digest=await crypto.subtle.digest("SHA-256",new TextEncoder().encode(payload.body.create_request_id));
      const id="doc_req_"+[...new Uint8Array(digest)].map(n=>n.toString(16).padStart(2,"0")).join("");
      if(current.has(id)) return {status:201,body:copy(current.get(id))};
      const doc=await makeDocument(id,payload.body.title,payload.body.editor_json,1); retain(doc);
      return {status:201,body:copy(doc)};
    }
    if (operation === "document_draft") {
      const prior=current.get(payload.document_id);
      if (!prior) return {status:404,body:{}};
      if (prior.version !== payload.body.expected_version) return {status:409,body:{}};
      const doc=await makeDocument(prior.document_id,prior.title,payload.body.editor_json,prior.version+1); retain(doc);
      return {status:200,body:copy(doc)};
    }
    if (operation === "document_get" || operation === "document_version") {
      const doc=operation === "document_get" ? current.get(payload.document_id) : history.get(`${payload.document_id}:${payload.version}`);
      return doc ? {status:200,body:copy(doc)} : {status:404,body:{}};
    }
    return null;
  };

  // Explicit SIMULATED journal: new desktop startup must read a valid Core
  // working-state contract. An absent fixture is not a product persistence ACK.
  const copyJournal=value=>JSON.parse(JSON.stringify(value));
  const emptyJournal=()=>({drafts:{},opened_documents:[],active_document:null,page_id:null,pending_original:null});
  let journal={schema:"archeaxis.ui-working-state/v1",workspace_id:"a".repeat(32),restore_epoch:"initial",state_revision:0,
    state:emptyJournal(),draft_digests:{},pending_document_id:null,recovery_candidates:null,recovery_requires_confirmation:false};
  async function journalHash(value) {
    const hash=await crypto.subtle.digest("SHA-256",new TextEncoder().encode(value));
    return [...new Uint8Array(hash)].map(n=>n.toString(16).padStart(2,"0")).join("");
  }
  async function journalFixture(operation,payload) {
    if(operation==="ui_state_read")return {status:200,body:copyJournal(journal)};
    if(!["ui_state_write","ui_state_clear_saved","ui_state_recover"].includes(operation))return null;
    const body=payload.body;
    if(!body||body.workspace_id!==journal.workspace_id||body.restore_epoch!==journal.restore_epoch||body.state_revision!==journal.state_revision)
      return {status:409,body:{error:"UI_STATE_CONFLICT",workspace_id:journal.workspace_id,restore_epoch:journal.restore_epoch,state_revision:journal.state_revision}};
    if(operation==="ui_state_recover")return {status:409,body:{error:"NO_SIMULATED_RECOVERY_CANDIDATE"}};
    let state;
    if(operation==="ui_state_write") {
      state=copyJournal(body.state);
      if(journal.state.pending_original&&state.pending_original&&JSON.stringify(journal.state.pending_original)!==JSON.stringify(state.pending_original))return {status:422,body:{error:"FROZEN_ORIGINAL_CHANGED"}};
    } else {
      const draft=journal.state.drafts[body.document_id];
      const saved=window.__A0_DOCUMENT_FIXTURE__?.snapshot().find(doc=>doc.document_id===body.document_id);
      if(!draft||!saved||draft.base_version!==body.base_version||body.saved_version!==body.base_version+1||saved.version!==body.saved_version
        ||journal.draft_digests[body.document_id]!==body.content_sha256||JSON.stringify(saved.editor_json)!==JSON.stringify(draft.editor_json))return {status:409,body:{error:"SIMULATED_CLEAR_REFUSED"}};
      state=copyJournal(journal.state);delete state.drafts[body.document_id];
    }
    const digests={};for(const [id,draft] of Object.entries(state.drafts))digests[id]=await journalHash(JSON.stringify(draft.editor_json));
    journal={...journal,state_revision:journal.state_revision+1,state,draft_digests:digests,
      pending_document_id:state.pending_original?"doc_req_"+await journalHash(state.pending_original.create_request_id):null};
    return {status:200,body:copyJournal(journal)};
  }
  window.__TAURI__ = {
    core: {
      invoke: async (command, request) => {
        if (command === "recovery_status") {
          return { state: "ready", safe_mode: false, backend_available: true,
                   message: "browser smoke host", backups: [], external_dev: false };
        }
        if (command === "core_command") {
          const operation = request?.request?.operation;
          if (Object.prototype.hasOwnProperty.call(faults, operation)) {
            return { status: faults[operation], body: {} };
          }
          const journalAnswer=await journalFixture(operation,request?.request?.payload??{});
          if(journalAnswer)return journalAnswer;
          if(operation==="source_jobs") {
            const sourceId=request?.request?.payload?.source_id;
            return bodies.sources_list.sources.some(source=>source.source_id===sourceId)
              ? {status:200,body:{source_id:sourceId,jobs:[],jobs_capped:false}}
              : {status:404,body:{error:"SOURCE_NOT_FOUND"}};
          }
          if (documentFixture) {
            const answer = await documentFixture(operation, request?.request?.payload ?? {});
            if (answer) return answer;
          }
          return { status: 200, body: bodies[operation] ?? {} };
        }
        return null;
      },
    },
  };
})();

// Synthetic bridge only; never forwards writes to an HTTP API or real database.
(() => {
 const base=window.__TAURI__.core.invoke,copy=v=>structuredClone(v),documents=new Map(),sources=new Map();
 const hash=async bytes=>[...new Uint8Array(await crypto.subtle.digest('SHA-256',bytes))].map(b=>b.toString(16).padStart(2,'0')).join('');
 window.__PILOT__={calls:[],fault:null,documents,sources};
 window.__TAURI__.core.invoke=async(command,request)=>{
  const op=request?.request?.operation,p=request?.request?.payload??{},pilot=window.__PILOT__;
  pilot.calls.push({command,operation:op,requestId:p.body?.create_request_id});
  if(op==='layout_read')return {status:200,body:{workspace_id:'a'.repeat(32),device_id:p.device_id,restore_epoch:'initial',revision:0,layout:{schema_version:1,preset_id:'default',registered_panels:['01'],dock_tree:{kind:'tabs',panels:['01'],active:'01'},floating_bounds:{}},recovery_reason:null}};
  if(op==='operation_readiness'){const now=Date.now(),expires=now+30000;return {status:200,body:{schema:'archeaxis.operation-readiness/v1',scope:p.body.scope,observed_at_ms:now,expires_at_ms:expires,aggregate:'UNVERIFIED',network_performed:false,models_loaded:false,execution_authorized:false,operations:p.body.operations.map(operation=>({operation,implementation:'IMPLEMENTED',dependencies:'AVAILABLE',connection:'UNKNOWN',qualification:'UNVERIFIED',permission:'ENABLED',status:'UNVERIFIED',reasons:['SYNTHETIC_SCOPE_ONLY'],expires_at_ms:expires}))}};}
  if(op==='source_import'){
   const bytes=Uint8Array.from(atob(p.body.content_base64),c=>c.charCodeAt(0)),digest=await hash(bytes),id='src_synthetic_'+digest;
   const duplicate=sources.has(id);sources.set(id,{source_id:id,name:p.body.name,media_type:'application/json',sha256:digest,content_base64:p.body.content_base64});
   return {status:202,body:{source_id:id,sha256:digest,duplicate}};
  }
  if(op==='source_original'&&sources.has(p.source_id))return {status:200,body:copy(sources.get(p.source_id))};
  if(op==='document_create'&&String(p.body.create_request_id).startsWith('course_import_')){
   const id='doc_req_'+await hash(new TextEncoder().encode(p.body.create_request_id));
   if(!documents.has(id)){const text=p.body.editor_json.content.map(b=>b.content.map(t=>t.text).join('')).join('\n');documents.set(id,{document_id:id,source_id:p.body.source_id,source_revision:p.body.source_revision,title:p.body.title,editor_json:copy(p.body.editor_json),version:1,content_sha256:await hash(new TextEncoder().encode(JSON.stringify(p.body.editor_json))),text_projection:text,blocks:[]});}
   if(pilot.fault==='unknown-save'){pilot.fault=null;return {status:503,body:{error:'SYNTHETIC_LOST_WRITE_ACK'}};}
   return {status:201,body:copy(documents.get(id))};
  }
  if(op==='document_get'&&documents.has(p.document_id))return {status:200,body:copy(documents.get(p.document_id))};
  if(op==='documents_list'&&documents.size){if(pilot.fault==='list-failure')return {status:503,body:{error:'SYNTHETIC_LIST_FAILURE'}};return {status:200,body:{documents:[...documents.values()].map(d=>({document_id:d.document_id,source_id:d.source_id,source_revision:d.source_revision,title:d.title,version:1,content_sha256:d.content_sha256})),next_cursor:null,snapshot_count:documents.size}};}
  return base(command,request);
 };
})();
