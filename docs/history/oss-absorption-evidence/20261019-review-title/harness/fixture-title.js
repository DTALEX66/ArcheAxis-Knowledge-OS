// Only this task's isolated synthetic bridge; never calls Core, DB or model.
(() => {
 const base=window.__TAURI__.core.invoke;
 const keys=[`course:${'a'.repeat(64)}:artifact:${'b'.repeat(64)}`,`course:${'c'.repeat(64)}:artifact:${'d'.repeat(64)}`];
 const title=Array.from('中文复习标题与来源固定版本的长文本'.repeat(8)).slice(0,80).join('');
 window.__TITLE_PILOT__={keys,title,calls:[],mode:'current'};
 window.__TAURI__.core.invoke=async(command,request)=>{
  const op=request?.request?.operation,p=request?.request?.payload??{},pilot=window.__TITLE_PILOT__;
  pilot.calls.push({operation:op,item_key:p.item_key});
  if(op==='learning_items')return pilot.mode==='failure'?{status:503,body:{error:'SYNTHETIC_QUEUE_FAILURE'}}:{status:200,body:{items:keys.map(item_key=>({item_key,next_review:'2020-01-01T00:00:00Z',...(pilot.mode==='legacy'?{}:{display_title:title})})),count:2}};
  if(op==='learning_state')return {status:200,body:{item_key:p.item_key,learner:{event_count:0,correct_streak:0,scheduled_events:0,unscheduled_events:0,assessment:{assessment_id:'synthetic-'+p.item_key,item_key:p.item_key,question:'请独立说明如何保留原始证据。',content:'固定版本的核对内容。',knowledge_id:'synthetic-fixed',knowledge_version:'synthetic-fixed',source_id:null,anchor_id:null}},machine:{status:'not_recorded'}}};
  if(op==='learning_history')return {status:200,body:{events:[],count:0}};
  return base(command,request);
 };
})();
