import { readTemplateState, type Definition, type TemplateAction, type TemplateState } from "./templateLifecycle";

/** Uses the same center's readback; owns no registry, worker or install directory. */
export function T3LifecycleControls({row,disabled,onChange}:{row:unknown;disabled:boolean;onChange:(state:TemplateState,action:TemplateAction,target?:Definition)=>void}) {
  let state:TemplateState;
  try { state=readTemplateState(row); } catch {return <p>学习与实践模板状态未确认；已有文档仍可读取，请重新读取能力。</p>;}
  return <section aria-label="学习与实践模板管理"><h4>学习与实践 · 内置数据模板</h4>
    <p>定义 v{state.definition.version} · {state.installed?(state.enabled?"已启用":"已停用"):"已卸载"}。MIT 自有模板，不安装外部程序；课程功能单独检查权限与依赖。</p>
    <p>停用和卸载保留已有文档、引用与学习记录；更新及回退只影响后续新建，旧对象固定使用原定义。</p>
    {state.installed?<>
      <button disabled={disabled} onClick={()=>onChange(state,state.enabled?"disable":"enable")}>{state.enabled?"停用学习与实践模板":"启用学习与实践模板"}</button>
      {state.available_definitions.filter(d=>d.version!==state.definition.version).map(target=><button key={target.version} disabled={disabled} onClick={()=>onChange(state,target.version>state.definition.version?"update":"rollback",target)}>{target.version>state.definition.version?"更新":"回退"}到模板 v{target.version}</button>)}
      <button disabled={disabled} onClick={()=>onChange(state,"uninstall")}>卸载学习与实践模板</button>
    </>:state.available_definitions.map(target=><button key={target.version} disabled={disabled} onClick={()=>onChange(state,"install",target)}>安装内置模板 v{target.version}</button>)}
  </section>;
}
