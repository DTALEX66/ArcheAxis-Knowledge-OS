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
