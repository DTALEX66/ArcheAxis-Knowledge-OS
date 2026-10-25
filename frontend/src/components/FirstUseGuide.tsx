import { useEffect, useRef, useState } from "react";
import { AaosDialog } from "../design-system/AaosPrimitives";
import "./FirstUseGuide.css";

const OPEN_EVENT = "archeaxis-open-first-use-guide";
export const FIRST_USE_GUIDE_STORAGE_KEY = "archeaxis.first-use-guide.v1";
export function requestFirstUseGuide() { window.dispatchEvent(new Event(OPEN_EVENT)); }

export const FIRST_USE_STEPS = [
  { id: "import", label: "带入第一份资料", description: "先选一份可测试的本地资料，保留原件，再查看处理结果。", check: "核对导入记录、原件名称和处理状态；失败时从同一任务重试，不把原件保存当成内容已识别。", routes: [{ page: "16", label: "打开导入导出" }] },
  { id: "read", label: "阅读、定位与保存", description: "检查识别后的正文、图片或时间位置，尝试保存一段自己的笔记。", check: "对照原件查看识别损失和引用位置；普通笔记、草稿可先保存，不要求模型或知识审批。", routes: [{ page: "03", label: "打开阅读与编辑" }, { page: "20", label: "查看来源与版本" }] },
  { id: "research", label: "搜索并比较证据", description: "围绕一个问题建立研究专题，比较自己的资料与合法可取得的外部来源。", check: "分别查看百科、社区与科研来源的实际结果；保存支持、反对、冲突及不确定性，并能回到原文。未连接的通道不能算已搜索。", routes: [{ page: "05", label: "打开研究空间" }] },
  { id: "knowledge", label: "整理为自己的知识", description: "把研究结论与原件、引用和版本关联，区分笔记、候选与已接纳知识。", check: "确认依据和适用范围后，再执行页面提供的明确接纳操作；AI 回答不会自动成为权威。", routes: [{ page: "02", label: "打开知识库" }] },
  { id: "learning", label: "学习、练习与复习", description: "从已保存内容建立学习路径，尝试一次练习或用自己的话讲解。", check: "按实际作答记录反馈和修订，再回到学习路径继续复习；展示过内容不等于已经掌握。", routes: [{ page: "06", label: "打开学习路径" }, { page: "11", label: "开始练习" }, { page: "12", label: "查看反馈与修订" }, { page: "21", label: "打开画布表达" }] },
  { id: "model", label: "连接本地 AI", description: "需要 AI 时，再到设置连接已有的本地模型服务。基础阅读和保存可先使用。", check: "核对用途与连接状态；提问前检查所用资料、版本及授权。云端真实推理留后续接通，配置界面不代表已经可用。", routes: [{ page: "19", label: "打开模型与连接" }] },
  { id: "ai-assets", label: "审查 AI 经验与授权", description: "AI 的经验、记忆和知识先作为候选，保留来源与证据。", check: "先保存候选，再核对去重、冲突、适用范围和逐项人工评审；明确采用对应版本后，按用途建立授权上下文。外部运行记忆未连接时保留未连接状态。", routes: [{ page: "13", label: "打开 AI 资产与上下文" }] },
  { id: "retest", label: "纠正回答并复测", description: "对实际回答指出问题，补充依据，并为修订后的知识建立独立复测授权。", check: "保留原问题、原回答、纠正与复测结果；查看任务中的失败、取消或未知状态，不以请求成功替代质量判断。", routes: [{ page: "14", label: "打开纠正与复测" }, { page: "22", label: "查看任务与记录" }] },
  { id: "recovery", label: "重开、导出与恢复", description: "保存工作后关闭并重新打开，确认资料、草稿、学习和 AI 资产仍可找到。", check: "在设置创建备份并核对产物；用隔离测试工作区验证恢复，保留原数据和回退路径。引导本身不会替你恢复或覆盖资料。", routes: [{ page: "19", label: "打开工作区与恢复" }, { page: "16", label: "打开导出与互通" }] },
  { id: "discover", label: "发现全部能力与蓝图", description: "最后浏览完整目录，了解内置能力、可接入扩展和未来规划。", check: "查看具体子项、依赖与证据状态；规划卡片表示方向，不表示功能已实现。", routes: [{ page: "17", label: "打开完整能力目录" }] },
] as const;

const STEP_HELP: Record<typeof FIRST_USE_STEPS[number]["id"], { todo: readonly string[]; where: string; retry: string; terms: readonly [string, string][] }> = {
  import: { todo: ["打开导入页，选择一份 TXT、Markdown 或已有文档。", "等到出现导入记录，再点击这份原件查看内容。"], where: "原件保存在本地资料库；识别、转换的状态仍在对应任务中。", retry: "保存结果未确认时，先检查本地工作区连接，再点“重试这一次原件导入”；转换问题从对应任务核对。", terms: [["原件", "导入时保留的原始文件。"], ["识别", "把文件里的文字、图片或语音转成能阅读和定位的内容。"]] },
  read: { todo: ["从已保存文档列表选一份内容；还没有内容时，先导入或新建笔记。", "对照原件阅读，写下自己的笔记并查看保存状态。"], where: "保存后的正文在知识库中；旧版可从“版本、来源与历史”重开。", retry: "列表读取失败先点“刷新资料列表”；保存结果未确认时保留草稿并核对原请求。", terms: [["引用定位", "记录这段内容来自哪份原件、哪个位置。"], ["版本", "某次保存后的内容记录，便于找回和比较。"]] },
  research: { todo: ["先写一个具体问题，例如“这两份资料的结论为什么不同？”", "添加实际材料，再分别记录支持、反对或还没弄清的地方；最后保存研究草稿。"], where: "保存在本地研究文档；展开“研究文档与版本”可再次打开。", retry: "公开检索未接通时，仍可比较本地资料；保存未确认时用“重试原保存请求”，不要另建一份。", terms: [["证据", "用来支持或反对某个说法的材料和出处。"], ["未决", "暂时没有答案、还需要查证的问题。"]] },
  knowledge: { todo: ["回到知识库打开自己的笔记和研究结论，检查来源与版本。", "普通笔记直接保存；要成为正式知识时，再按页面流程审查和接纳。"], where: "普通内容仍在知识库；正式知识保留自己的状态与依据。", retry: "依据不足时先保留笔记或候选，补充材料后再决定是否接纳。", terms: [["候选", "已保留但仍需检查的内容。"], ["接纳", "检查后明确采用对应版本；不会自动采用 AI 的所有回答。"]] },
  learning: { todo: ["从已保存内容选择一个小主题，建立学习路径。", "完成一次练习或用自己的话讲解，再记录反馈并安排复习。"], where: "学习路径、练习和反馈保留在各自页面，可重开继续。", retry: "还没有学习条目时，先回到已保存内容选择材料；没有实际作答时保留未完成。", terms: [["Teach-back", "用自己的话讲给别人听，检查哪里还没弄懂。"], ["复习", "隔一段时间再次回忆和作答，而不只是重看。"]] },
  model: { todo: ["在设置中核对已有的本地模型连接，不需要先配置云端。", "需要提问时回到材料页，预览本次允许使用的内容再确认执行。"], where: "连接保留在本地设置；问题、回答和请求状态在原会话或任务中。", retry: "连接失败时确认本地服务已运行，再重试连接；材料阅读和普通保存可继续。", terms: [["本地模型", "在这台电脑的模型服务中运行的 AI。"], ["授权", "明确允许本次请求使用哪些资料、版本和用途。"]] },
  "ai-assets": { todo: ["先保存一条带来源的 AI 经验候选，检查是否重复、冲突或只适用于特定场景。", "在对应版本完成逐项人工评审，再明确采用并建立允许用途的上下文。"], where: "AI 资产与上下文保留候选、评审、采用状态及授权版本。", retry: "评审或依据不完整时继续保留候选；不要跳过评审，也不要借用别的版本授权。", terms: [["AI 资产", "供 AI 按授权使用的经验、记忆或知识。"], ["上下文", "本次回答实际获准读取的材料。"]] },
  retest: { todo: ["选取一次真实回答，指出具体问题并附上可核对的依据。", "对修订内容建立独立复测授权，查看新的结果和任务状态。"], where: "纠正、评测与复测页保留旅程；任务与记录页查看执行状态。", retry: "失败、取消或结果未知时，先查询原请求；没有复测结果就保留未完成。", terms: [["复测", "修正之后再用问题检验效果。"], ["结果未知", "还不能确认请求是否完成，先查询，避免重复执行。"]] },
  recovery: { todo: ["保存工作，关闭后重新打开，检查刚才的内容是否仍在。", "在设置创建备份并核对结果；用隔离测试工作区验证恢复。"], where: "备份位置和产物以设置中的实际回执为准；导出内容在导出结果中查看。", retry: "没有完整备份回执时先核对产物；恢复失败保留原工作区与回退路径。", terms: [["导出", "把选定内容写成可供其他工具使用的文件。"], ["备份", "保留可用于恢复工作区的资料副本。"]] },
  discover: { todo: ["打开完整目录，用想完成的事情搜索能力或具体子项。", "查看当前可用、接入条件和未来规划，再选择实际入口。"], where: "目录用于发现已有页面与蓝图；不会另外复制你的业务内容。", retry: "规划项或缺少依赖的能力先查看说明，返回已接通的页面继续当前任务。", terms: [["能力子项", "一个大类中更具体的功能。"], ["规划中", "保留在蓝图里，当前不能据此当作已实现。"]] },
};

type Progress = { version: 1; shown: boolean; current: number; completed: string[] };
const blank = (): Progress => ({ version: 1, shown: false, current: 0, completed: [] });
function readProgress(): Progress {
  try {
    const value = JSON.parse(localStorage.getItem(FIRST_USE_GUIDE_STORAGE_KEY) ?? "null") as Partial<Progress> | null;
    if (!value || value.version !== 1 || typeof value.shown !== "boolean" || !Number.isInteger(value.current) || !Array.isArray(value.completed)) return blank();
    return { version: 1, shown: value.shown, current: Math.max(0, Math.min(FIRST_USE_STEPS.length - 1, value.current!)), completed: FIRST_USE_STEPS.filter(step => value.completed!.includes(step.id)).map(step => step.id) };
  } catch { return blank(); }
}

/** UI-only checklist. It never infers business success, writes knowledge, or changes model settings. */
export function FirstUseGuide({ onPage, enabled = true, autoOpen = true }: { onPage: (page: string) => boolean | void; enabled?: boolean; autoOpen?: boolean }) {
  const [progress, setProgress] = useState(readProgress);
  const [open, setOpen] = useState(false);
  const [notice, setNotice] = useState("");
  const [storageUnavailable, setStorageUnavailable] = useState(false);
  const latest = useRef(progress); latest.current = progress;
  const attempted = useRef(false);
  const closeTarget = useRef<HTMLElement | null>(null);
  const routeButton = useRef<HTMLButtonElement>(null);
  const navigating = useRef(false);
  function save(next: Progress) {
    latest.current = next; setProgress(next);
    try { localStorage.setItem(FIRST_USE_GUIDE_STORAGE_KEY, JSON.stringify(next)); }
    catch { setStorageUnavailable(true); }
  }
  useEffect(() => {
    if (!enabled || !autoOpen || attempted.current || latest.current.shown) return;
    const showWhenReady = () => {
      if (attempted.current || latest.current.shown || document.querySelector('.aaos-dialog-content,[role="alertdialog"],dialog[open]')) return;
      attempted.current = true;
      closeTarget.current = document.activeElement instanceof HTMLElement ? document.activeElement : null;
      save({ ...latest.current, shown: true }); setOpen(true);
    };
    showWhenReady();
    if (attempted.current) return;
    const observer = new MutationObserver(showWhenReady);
    observer.observe(document.body, { childList: true, subtree: true });
    return () => observer.disconnect();
  }, [enabled, autoOpen]);
  useEffect(() => {
    const show = () => {
      if (!enabled) return;
      closeTarget.current = document.activeElement instanceof HTMLElement ? document.activeElement : null;
      save({ ...latest.current, shown: true }); setNotice(""); setOpen(true);
    };
    window.addEventListener(OPEN_EVENT, show);
    return () => window.removeEventListener(OPEN_EVENT, show);
  }, [enabled]);
  useEffect(() => { if (!enabled) setOpen(false); }, [enabled]);
  const step = FIRST_USE_STEPS[progress.current];
  const help = STEP_HELP[step.id];
  const completed = progress.completed.includes(step.id);
  const allCompleted = progress.completed.length === FIRST_USE_STEPS.length;
  function go(page: string) {
    navigating.current = true;
    try {
      if (onPage(page) === false) { navigating.current = false; setNotice("当前页面暂未切换，请先处理保留的草稿或当前操作，再继续引导。"); return; }
      setOpen(false); setNotice("");
    } catch { navigating.current = false; setNotice("页面未能打开，当前引导进度已保留，可稍后重试。"); }
  }
  return <AaosDialog open={open} onOpenChange={setOpen} title="首次使用引导" description="从第一份资料开始，逐步走过人类学习与 AI 知识流程。可以随时暂停。"
    contentClassName="first-use-guide" overlayClassName="first-use-guide-overlay"
    onOpenAutoFocus={event => { event.preventDefault(); routeButton.current?.focus(); }}
    onCloseAutoFocus={event => {
      event.preventDefault();
      if (!navigating.current && closeTarget.current?.isConnected) closeTarget.current.focus();
      navigating.current = false;
    }}>
    <header className="first-use-guide-progress"><span>{progress.completed.length} / {FIRST_USE_STEPS.length} 步已手动记录</span><button type="button" onClick={() => setOpen(false)} aria-label="暂时跳过，暂停并关闭首次使用引导">暂时跳过</button></header>
    <p className="first-use-guide-resume">随时从顶部「使用引导」或设置中的「使用引导」继续。</p>
    <div className="first-use-guide-layout">
      <nav aria-label="引导步骤"><ol>{FIRST_USE_STEPS.map((entry, index) => <li key={entry.id}><button type="button" aria-current={progress.current === index ? "step" : undefined} onClick={() => { save({ ...progress, current: index }); setNotice(""); }}><span aria-hidden="true">{progress.completed.includes(entry.id) ? "✓" : index + 1}</span><span>{entry.label}</span>{progress.completed.includes(entry.id) ? <span className="aaos-sr-only">已手动记录</span> : null}</button></li>)}</ol></nav>
      <section className="first-use-guide-step" aria-labelledby="first-use-guide-step-title">
        <p className="first-use-guide-eyebrow">第 {progress.current + 1} 步</p><h3 id="first-use-guide-step-title">{step.label}</h3><p>{step.description}</p>
        <ol className="first-use-guide-todo" aria-label="现在做什么">{help.todo.map(item => <li key={item}>{item}</li>)}</ol>
        <dl className="first-use-guide-help"><div><dt>保存后在哪找</dt><dd>{help.where}</dd></div><div><dt>没有成功怎么办</dt><dd>{help.retry}</dd></div></dl>
        <details className="first-use-guide-check" key={step.id}><summary>核对结果与名词说明</summary><p>{step.check}</p><dl>{help.terms.map(([term, meaning]) => <div key={term}><dt>{term}</dt><dd>{meaning}</dd></div>)}</dl></details>
        <div className="first-use-guide-routes">{step.routes.map((route, index) => <button key={route.page} ref={index === 0 ? routeButton : undefined} type="button" onClick={() => go(route.page)}>{route.label}<span aria-hidden="true"> ↗</span></button>)}</div>
        <label className="first-use-guide-mark"><input type="checkbox" checked={completed} onChange={event => save({ ...progress, completed: event.target.checked ? [...progress.completed, step.id] : progress.completed.filter(id => id !== step.id) })}/>我已核对这一步（手动记录）</label>
        {notice ? <p role="status">{notice}</p> : null}
      </section>
    </div>
    <footer className="first-use-guide-footer"><p>勾选只保存你的引导进度，不代表业务成功或完整闭环验收通过。{storageUnavailable ? " 本机暂不能保存引导偏好，本次进度仅保留到窗口关闭。" : ""}</p><div><button type="button" disabled={progress.current === 0} onClick={() => save({ ...progress, current: progress.current - 1 })}>上一步</button>{progress.current < FIRST_USE_STEPS.length - 1 ? <button type="button" onClick={() => save({ ...progress, current: progress.current + 1 })}>下一步</button> : <button type="button" disabled={!allCompleted} onClick={() => setOpen(false)}>完成引导</button>}</div></footer>
  </AaosDialog>;
}
