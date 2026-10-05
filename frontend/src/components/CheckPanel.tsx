import { useEffect, useRef, useState } from "react";
import { coreCommand } from "../api/core";
import { assertCoreDto, type DocumentDto, type DocumentCheckDto, type DocumentChecksDto, type RevisionBasisDto } from "../api/generated/core-contract";

const labels: Record<string,string> = {pending:"等待核验",unverified:"未核验",uncertain:"不确定",original_unclear:"原件不清晰",conflicting:"存在冲突",failed:"核验失败",faithful:"识别忠实",mismatch:"识别不一致",supported:"有依据支持",refuted:"依据不支持",passed:"核验通过"};
// Checks transport execution separately from the model's dimension-specific verdict.
export function checkExecutionLabel(value:DocumentCheckDto):string {
  if(value.execution_verified===false&&value.execution_state==="not_executed"&&value.status==="failed"&&value.reason==="not_configured")return "执行尝试已记录为失败：核验引擎未配置；没有发生云端核验。正文仍可保存。";
  if(value.execution_verified===false&&value.execution_state==="running"&&value.status==="pending")return "核验任务正在执行；尚无结论。正文仍可保存。";
  if(value.execution_verified===false&&value.execution_state==="failed"&&value.status==="failed"&&typeof value.reason==="string"&&value.reason.trim())return `核验执行失败：${value.reason}；不会把失败当作内容判断。正文仍可保存。`;
  const allowed=value.dimension==="recognition_fidelity"?["faithful","mismatch","uncertain","original_unclear","conflicting"]:["supported","refuted","uncertain","conflicting"];
  const engine=value.engine_receipt as Record<string,unknown>|null;
  if(value.execution_verified!==true||value.execution_state!=="executed"||!allowed.includes(value.status)||!engine
    ||["provider","requested_model","model"].some(field=>typeof engine[field]!=="string"||!String(engine[field]).trim()||/^(unknown|unverified)$/i.test(String(engine[field])))
    ||engine.finish_reason!=="stop"||![engine.prompt_sha256,engine.response_sha256].every(hash=>typeof hash==="string"&&/^[a-f0-9]{64}$/i.test(hash))
    ||!Number.isSafeInteger(engine.tokens_used)||Number(engine.tokens_used)<0||!Array.isArray(value.retrieval_receipts))throw new Error("unverified execution receipt");
  return `真实核验任务已执行：${labels[value.status]}；${value.dimension==="recognition_fidelity"?"识别忠实度":"专业依据"}与真人认可分别记录。正文仍可保存。`;
}
export function CheckPanel({document,onRevisionBasis}:{document:DocumentDto;onRevisionBasis:(basis:RevisionBasisDto)=>void}) {
  const identity=`${document.document_id}:${document.version}:${document.content_sha256}`;
  const currentIdentity=useRef(identity);currentIdentity.current=identity;
  const executionGeneration=useRef(0);
  const readGeneration=useRef(0);
  const [result,setResult]=useState<DocumentChecksDto|null>(null);
  const [version,setVersion]=useState(String(document.version));
  const [message,setMessage]=useState(""); const [busy,setBusy]=useState(false);
  const [reason,setReason]=useState(""); const [position,setPosition]=useState("");
  const [basis,setBasis]=useState(""); const [job,setJob]=useState(""); const [hash,setHash]=useState("");
  const [statuses,setStatuses]=useState({recognition_fidelity:"uncertain",professional_basis:"uncertain"}); const [rationale,setRationale]=useState("");
  async function read(target:number,offset=0) {
    const boundIdentity=identity;const generation=++readGeneration.current;
    const value=await coreCommand<DocumentChecksDto>("document_checks",{document_id:document.document_id,version:target,offset});
    assertCoreDto("DocumentChecksDto",value);
    if(value.document_id!==document.document_id||value.version!==target)throw new Error("check identity mismatch");
    if(currentIdentity.current===boundIdentity&&readGeneration.current===generation)setResult(value);
  }
  useEffect(()=>{let alive=true;executionGeneration.current++;readGeneration.current++;setBusy(false);setMessage("");setResult(null);setVersion(String(document.version));
    coreCommand<DocumentChecksDto>("document_checks",{document_id:document.document_id,version:document.version}).then(value=>{
      assertCoreDto("DocumentChecksDto",value);
      if(value.document_id!==document.document_id||value.version!==document.version||value.content_sha256!==document.content_sha256)throw new Error("check identity mismatch");
      if(alive)setResult(value);
    }).catch(()=>{if(alive)setMessage("核验记录暂未读取；正文仍可保存。");});return()=>{alive=false;};
  },[document.document_id,document.version,document.content_sha256]);
  async function record(dimension:DocumentCheckDto["dimension"],mode:"manual"|"cloud") {
    setBusy(true);
    try {
      const value=await coreCommand<DocumentCheckDto>("document_check_record",{document_id:document.document_id,body:{version:document.version,dimension,provider_mode:mode,
        ...(mode==="manual"?{status:statuses[dimension]}:{}),...(reason.trim()?{reason:reason.trim()}:{}),...(position.trim()?{position:{description:position.trim()}}:{}),
        ...(basis.trim()?{basis:basis.trim()}:{}),...(job.trim()?{recognition_job_id:job.trim()}:{}),...(hash.trim()?{recognition_result_sha256:hash.trim()}:{}),
      }});
      assertCoreDto("DocumentCheckDto",value);
      if(value.document_id!==document.document_id||value.version!==document.version||value.dimension!==dimension||value.provider_mode!==mode)throw new Error("check identity mismatch");
      setVersion(String(document.version)); await read(document.version);
      setMessage(mode==="cloud"&&!value.execution_verified?"申请已记录；云端核验尚未执行。":"核验记录已保存；不会替代知识认可。");
    } catch {setMessage("核验记录未确认，请保留填写内容重试；正文仍可保存。");}finally{setBusy(false);}
  }
  async function execute(item:DocumentCheckDto) {
    if(item.provider_mode!=="cloud"||item.version!==document.version||item.content_sha256!==document.content_sha256)return;
    const boundIdentity=identity;const generation=++executionGeneration.current;
    const current=()=>currentIdentity.current===boundIdentity&&executionGeneration.current===generation;
    setBusy(true);
    try {
      const requestId=typeof item.request_check_id==="string"?item.request_check_id:item.check_id;
      const retryId=typeof item.attempt_id==="string"?item.attempt_id:undefined;
      const value=await coreCommand<DocumentCheckDto>("document_check_execute",{document_id:document.document_id,body:{check_id:requestId,expected_content_sha256:document.content_sha256,...(retryId?{retry_of_task_id:retryId}:{})}});
      assertCoreDto("DocumentCheckDto",value);
      if(value.document_id!==document.document_id||value.version!==document.version||value.content_sha256!==document.content_sha256||value.dimension!==item.dimension||value.provider_mode!=="cloud"||value.request_check_id!==requestId||typeof value.attempt_id!=="string"||value.retry_of_task_id!==(retryId??null))throw new Error("execution identity mismatch");
      const executionMessage=checkExecutionLabel(value);
      const refreshed=await coreCommand<DocumentChecksDto>("document_checks",{document_id:document.document_id,version:document.version});
      assertCoreDto("DocumentChecksDto",refreshed);
      if(refreshed.document_id!==document.document_id||refreshed.version!==document.version||refreshed.content_sha256!==document.content_sha256)throw new Error("execution readback identity mismatch");
      if(!current())return;setResult(refreshed);setMessage(executionMessage);
    } catch {if(current())setMessage("执行回执未确认；不会标记核验成功。正文仍可保存。");} finally {if(current())setBusy(false);}
  }
  return <section aria-label="内容核验"><h4>内容核验</h4><p>核验与笔记保存独立；核验通过不等同人工认可。</p>
    <label>查看核验版本 <input type="number" min="1" max={document.version} value={version} onChange={event=>setVersion(event.target.value)}/></label>
    <button disabled={busy} onClick={()=>{const target=Number(version);if(Number.isInteger(target)&&target>0&&target<=document.version)void read(target).catch(()=>setMessage("该版本记录未读取；当前文档未改变。"));}}>读取版本记录</button>
    {result?.checks_capped?<p>此版本记录较多，当前仅显示有限记录。</p>:null}
    {result && "next_offset" in result && typeof result.next_offset==="number" ? <button disabled={busy} onClick={()=>void read(result.version,Number(result.next_offset)).catch(()=>setMessage("下一页记录未读取，请重试。"))}>读取下一页核验记录</button> : null}
    {result?.historical?<p>正在查看旧版本 {result.version}，当前正文仍为版本 {document.version}。</p>:null}
    {(["recognition_fidelity","professional_basis"] as const).map(dimension=><section key={dimension} aria-label={dimension==="recognition_fidelity"?"识别忠实度":"专业依据"}>
      <h5>{dimension==="recognition_fidelity"?"识别忠实度":"专业依据"}</h5>
      {result ? result.checks.filter(item=>item.dimension===dimension).length ? result.checks.filter(item=>item.dimension===dimension).map(item=><div key={item.check_id}>
        <p>{item.status==="passed"?"旧版通过标记（未细分核验维度）":labels[item.status]} · {item.provider_mode==="manual"?"手动记录":item.execution_verified&&item.execution_state==="executed"?"云端任务已执行":item.execution_state==="running"?"任务执行中":item.execution_state==="failed"?"任务执行失败":"云端尚未执行"}</p>
        {item.reason?<p>{item.reason==="worker_not_configured"?"该申请记录创建时引擎未配置；不代表当前配置状态，尚未执行。":item.reason}</p>:null}{item.basis?<p>依据：{String(item.basis)}</p>:null}
        {item.provider_mode==="cloud"&&result.next_offset==null&&(!item.attempt_id?!result.checks.some(other=>other.request_check_id===item.check_id&&typeof other.attempt_id==="string"):item.status==="failed"&&typeof item.attempt_id==="string"&&result.checks.slice().reverse().find(other=>other.request_check_id===item.request_check_id&&typeof other.attempt_id==="string")?.attempt_id===item.attempt_id)?<button disabled={busy||item.version!==document.version||item.content_sha256!==document.content_sha256} onClick={()=>void execute(item)}>{typeof item.attempt_id==="string"?"明确重试执行核验":"明确执行核验"}</button>:null}
        {item.execution_state==="failed"&&item.reported_status?<p>模型报告：{labels[String(item.reported_status)]??String(item.reported_status)}；任务失败，未验证执行成功。</p>:null}
        {item.execution_verified&&item.execution_state==="executed"&&item.engine_receipt?<details><summary>实际引擎与检索回执</summary><pre>{JSON.stringify({engine:item.engine_receipt,retrieval:item.retrieval_receipts},null,2)}</pre></details>:null}
        {typeof item.raw_response==="string"&&item.raw_response.length>0?<details><summary>查看模型原始响应</summary><pre>{item.raw_response}</pre></details>:null}
        {item.execution_state==="failed"&&item.engine_receipt?<details><summary>失败执行回执</summary><pre>{JSON.stringify(item.engine_receipt,null,2)}</pre></details>:null}
        {item.reason==="not_configured"?<p>执行尝试失败：核验引擎未配置，没有云端调用。</p>:null}
        <button disabled={!rationale.trim()} onClick={()=>{onRevisionBasis({rationale:rationale.trim(),reference_version:item.version,check_id:item.check_id,...(item.position&&typeof item.position==="object"&&!Array.isArray(item.position)?{position:item.position}: {})});setMessage("修订理由已选定，将随下一次正文保存记录。");}}>用于下一次修订</button>
      </div>):<p>该版本尚无核验记录。</p>:<p>核验状态尚未读取。</p>}
      <button disabled={busy} onClick={()=>void record(dimension,"cloud")}>申请{dimension==="recognition_fidelity"?"识别":"专业"}云端核验</button>
      <details><summary>手动记录{dimension==="recognition_fidelity"?"识别":"专业"}核验</summary>
        <label>核验结论 <select value={statuses[dimension]} onChange={event=>setStatuses(previous=>({...previous,[dimension]:event.target.value}))}>{["uncertain","original_unclear","conflicting","failed",...(dimension==="recognition_fidelity"?["faithful","mismatch"]:["supported","refuted"])].map(item=><option key={item} value={item}>{labels[item]}</option>)}</select></label>
        <button disabled={busy} onClick={()=>void record(dimension,"manual")}>明确提交手动核验记录</button>
      </details>
    </section>)}
    <details><summary>补充核验位置与依据</summary>
      <label>疑点位置 <input value={position} onChange={event=>setPosition(event.target.value)}/></label>
      <label>核验说明 <textarea value={reason} onChange={event=>setReason(event.target.value)}/></label>
      <label>参考依据 <textarea value={basis} onChange={event=>setBasis(event.target.value)}/></label>
      <label>已有识别任务 <input value={job} onChange={event=>setJob(event.target.value)}/></label>
      <label>已有结果指纹 <input value={hash} onChange={event=>setHash(event.target.value)}/></label>
    </details>
    <label>下一次修订理由 <textarea value={rationale} onChange={event=>setRationale(event.target.value)}/></label>
    {document.revision_basis?<details><summary>本版本修订依据</summary><pre>{JSON.stringify(document.revision_basis,null,2)}</pre></details>:null}
    {message?<p role="status">{message}</p>:null}
  </section>;
}
