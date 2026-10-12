import { useEffect, useRef, useState } from "react";
import { Extension, Node, type JSONContent } from "@tiptap/core";
import { EditorContent, useEditor } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import { ApiError } from "../api/client";
import { DocumentJournalError } from "../presentation/documentSaveStage";
import "./DocumentConflictComparison.css";

export type DocumentConflictRead = {
  base: { version: number; editor_json: JSONContent };
  current: { version: number; editor_json: JSONContent; content_sha256: string };
};
function previewText(node:JSONContent):string {
  if(typeof node.text==="string")return node.text;
  return (node.content??[]).map(previewText).join(node.type==="doc"?"\n":"");
}
function SnapshotComparison({label,value}:{label:string;value:JSONContent}) {
  return <section aria-label={label}><h3>{label}</h3><pre>{previewText(value)}</pre><details><summary>完整结构记录</summary><pre>{JSON.stringify(value,null,2)}</pre></details></section>;
}

const knownNodes = new Set(["doc", "paragraph", "heading", "blockquote", "codeBlock", "bulletList", "orderedList", "listItem", "horizontalRule", "hardBreak", "text", "evidenceReference"]);
const knownMarks = new Set(["bold", "italic", "strike", "code", "underline", "link"]);
const blockTypes = [...knownNodes].filter((name) => !["doc", "hardBreak", "text", "evidenceReference"].includes(name));
const EvidenceReference = Node.create({
  name: "evidenceReference", inline: true, group: "inline", atom: true,
  addAttributes() { return Object.fromEntries(["anchor_id", "source_id", "source_revision", "page", "position", "excerpt"].map((name) => [name, { default: null, rendered: false }])); },
  parseHTML() { return [{ tag: "span[data-evidence-reference]" }]; },
  renderHTML({ node }) { return ["span", { "data-evidence-reference": "true", role: "button", tabindex: "0", "data-page": node.attrs.page }, `引用：${node.attrs.excerpt || `第 ${node.attrs.page} 页`}`]; },
});
const BlockIdentity = Extension.create({
  name: "blockIdentity",
  addGlobalAttributes() { return [{ types: blockTypes, attributes: {
    block_id: { default: null },
    originalAttrs: { default: null, rendered: false },
  } }, {types:["doc"],attributes:{originalAttrs:{default:null,rendered:false}}}]; },
});
const PreservedUnknown = Node.create({
  name: "preservedUnknown",
  group: "block", atom: true,
  addAttributes() { return { raw: { default: null, rendered: false } }; },
  parseHTML() { return [{ tag: "div[data-preserved-node]" }]; },
  renderHTML() { return ["div", { "data-preserved-node": "true", contenteditable: "false" }, "未支持的内容节点已保留；保存不会丢弃其原始内容。"]; },
});

function unsupported(node: JSONContent): boolean {
  return !knownNodes.has(node.type ?? "") || Boolean(node.marks?.some((mark) => !knownMarks.has(mark.type))) || Boolean(node.content?.some(unsupported));
}
function decodeNode(node: JSONContent): JSONContent {
  return { ...node, ...(node.attrs ? { attrs: { ...node.attrs, originalAttrs: node.attrs } } : {}), ...(node.content ? { content: node.content.map(decodeNode) } : {}) };
}
export function decodeEditorContent(content: JSONContent): JSONContent {
  return { ...content, ...(content.attrs?{attrs:{originalAttrs:content.attrs}}:{}), content: (content.content ?? []).map((node) => unsupported(node)
    ? { type: "preservedUnknown", attrs: { raw: node } } : decodeNode(node)) };
}
export function encodeEditorContent(content: JSONContent): JSONContent {
  if (content.type === "preservedUnknown") return content.attrs?.raw as JSONContent;
  const { attrs: nodeAttrs, ...node } = content;
  const { originalAttrs, ...attrs } = nodeAttrs ?? {};
  const merged = { ...(originalAttrs ?? {}), ...attrs };
  for (const key of Object.keys(merged)) if (merged[key] === null) delete merged[key];
  // Absent attributes must stay absent across JSON/native transport. An own
  // undefined key disappears on the wire and would falsely fail journal ACKs.
  return { ...node, ...(Object.keys(merged).length ? { attrs: merged } : {}), ...(content.content ? { content: content.content.map(encodeEditorContent) } : {}) };
}

export function DocumentEditor({ content, version, onSave, onReadConflict, onRetryWorkingState, onDirtyChange, onDraftChange, onCreateReference, onReferenceActivate }: {
  content: JSONContent;
  version: number;
  onSave: (content: JSONContent, expectedVersion: number) => Promise<{ content: JSONContent; version: number; workingStateConfirmed?:boolean }>;
  onRetryWorkingState?:()=>Promise<boolean>;
  onReadConflict?: (baseVersion: number) => Promise<DocumentConflictRead>;
  onDirtyChange?: (dirty: boolean) => void;
  onDraftChange?: (content: JSONContent, baseVersion: number) => void;
  onCreateReference?: () => Promise<JSONContent>;
  onReferenceActivate?: (attributes: Record<string, unknown>) => void;
}) {
  const [status, setStatus] = useState("已保存");
  const [failure, setFailure] = useState(false);
  const [changes, setChanges] = useState(0);
  const composing = useRef(false);
  const saving = useRef(false);
  const journalPending=useRef(false);
  const saveTimer=useRef<number|null>(null);
  const acknowledgedContent=useRef<string|null>(null);
  const blocked=useRef<"conflict"|"permission"|"journal"|null>(null);
  const editSerial=useRef(0);
  const comparisonFlight=useRef(false);
  const merging=useRef(false);
  const [comparison,setComparison]=useState<DocumentConflictRead|null>(null);
  const [mergeMode,setMergeMode]=useState(false);
  const citing = useRef(false);
  const currentVersion = useRef(version);
  const mounted = useRef(true);
  const callbacks = useRef({ onSave, onReadConflict, onRetryWorkingState, onDirtyChange, onDraftChange, onCreateReference, onReferenceActivate });
  callbacks.current = { onSave, onReadConflict, onRetryWorkingState, onDirtyChange, onDraftChange, onCreateReference, onReferenceActivate };
  const editor = useEditor({
    extensions: [StarterKit.configure({ link: { openOnClick: false } }), BlockIdentity, PreservedUnknown, EvidenceReference],
    content: decodeEditorContent(content),
    editorProps: {
      attributes: { role: "textbox", "aria-label": "文档草稿", "aria-multiline": "true", spellcheck: "false" },
      handleDOMEvents: {
        click(view,event) {
          const target=(event.target as HTMLElement).closest("[data-evidence-reference]");
          if(!target||!view.dom.contains(target))return false;
          const node=view.state.doc.nodeAt(view.posAtDOM(target,0));
          if(node?.type.name!=="evidenceReference")return false;
          callbacks.current.onReferenceActivate?.(node.attrs);
          event.preventDefault();return true;
        },
      },
      handleClickOn(_view, _position, node) {
        if (node.type.name !== "evidenceReference") return false;
        callbacks.current.onReferenceActivate?.(node.attrs);
        return true;
      },
      handleKeyDown(view, event) {
        if (event.key !== "Enter" && event.key !== " ") return false;
        const target = event.target as HTMLElement;
        const reference=target.closest("[data-evidence-reference]");
        if (!reference||!view.dom.contains(reference)) return false;
        const node = view.state.doc.nodeAt(view.posAtDOM(reference,0));
        if (node?.type.name !== "evidenceReference") return false;
        callbacks.current.onReferenceActivate?.(node.attrs);
        return true;
      },
    },
    onUpdate({ editor }) {
      editSerial.current++;
      if(!merging.current)setComparison(null);
      const transaction = editor.state.tr;
      editor.state.doc.descendants((node, position) => {
        if (blockTypes.includes(node.type.name) && !node.attrs.block_id) transaction.setNodeMarkup(position, undefined, { ...node.attrs, block_id: crypto.randomUUID() });
      });
      if (transaction.docChanged) editor.view.dispatch(transaction);
      callbacks.current.onDraftChange?.(encodeEditorContent(editor.getJSON()), currentVersion.current);
      journalPending.current=false;
      setStatus(blocked.current==="conflict"?"版本冲突：草稿仍保留；请比较后明确决定。":blocked.current==="permission"?"身份拒绝：草稿仍保留；不会自动重试正文。":blocked.current==="journal"?"工作草稿保全待核对；输入仍保留，正文不会自动重试。":"尚未保存");
      setFailure(Boolean(blocked.current));
      setChanges((value) => value + 1);
      callbacks.current.onDirtyChange?.(true);
    },
  });
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; }; }, []);
  async function save(resolvedVersion?:number) {
    if (!editor || composing.current || saving.current || journalPending.current) return;
    if(blocked.current==="conflict"&&resolvedVersion===undefined)return;
    if(resolvedVersion!==undefined) {
      if(!comparison||resolvedVersion!==comparison.current.version)return;
      currentVersion.current=resolvedVersion;
      callbacks.current.onDraftChange?.(encodeEditorContent(editor.getJSON()),resolvedVersion);
    }
    if(saveTimer.current!==null){window.clearTimeout(saveTimer.current);saveTimer.current=null;}
    const sent = encodeEditorContent(editor.getJSON());
    if(resolvedVersion===undefined&&acknowledgedContent.current===JSON.stringify(sent))return;
    saving.current = true;
    setStatus("正在保存…");
    try {
      const saved = await callbacks.current.onSave(sent, currentVersion.current);
      if (!mounted.current) return;
      currentVersion.current = saved.version;
      blocked.current=null;setComparison(null);merging.current=false;setMergeMode(false);
      acknowledgedContent.current=JSON.stringify(sent);
      if(saved.workingStateConfirmed===false) {
        journalPending.current=true;
        if(JSON.stringify(encodeEditorContent(editor.getJSON()))!==JSON.stringify(sent))callbacks.current.onDraftChange?.(encodeEditorContent(editor.getJSON()),saved.version);
        setStatus("正文已保存；工作草稿保全尚未确认，请核对工作状态。");setFailure(true);
        callbacks.current.onDirtyChange?.(true);return;
      }
      if (JSON.stringify(encodeEditorContent(editor.getJSON())) === JSON.stringify(sent)) {
        editor.commands.setContent(decodeEditorContent(saved.content), { emitUpdate: false });
        setStatus("已保存");
        setFailure(false);
        callbacks.current.onDirtyChange?.(false);
      } else {
        callbacks.current.onDraftChange?.(encodeEditorContent(editor.getJSON()), saved.version);
        setStatus("尚未保存");
        setChanges((value) => value + 1);
      }
    } catch(error) {
      if (mounted.current) {
        if(error instanceof DocumentJournalError) {
          blocked.current=error.failure instanceof ApiError&&[401,403].includes(error.failure.status)?"permission":"journal";
          setStatus(blocked.current==="permission"?"身份拒绝：工作草稿保全未获许可，输入仍保留，正文未发送。":"工作草稿保全尚未确认，请核对工作状态；输入仍保留，正文未发送。");
        } else if(error instanceof ApiError&&error.status===409) {
          blocked.current="conflict";setComparison(null);merging.current=false;setMergeMode(false);
          setStatus("版本冲突：原草稿和保存基准保留；请读取当前版本并比较。正文不会自动重试。");
        } else if(error instanceof ApiError&&(error.status===403||error.status===401)) {
          blocked.current="permission";setStatus("身份拒绝：原草稿仍保留；权限未改变，正文不会自动重试。");
        } else setStatus("草稿尚未保存；内容仍保留，请重试。版本冲突时请先保留当前文字。");
        setFailure(true);
      }
    } finally { saving.current = false; }
  }
  async function readConflict() {
    if(!editor||!callbacks.current.onReadConflict||comparisonFlight.current||saving.current)return;
    comparisonFlight.current=true;
    setComparison(null);merging.current=false;setMergeMode(false);
    const serial=editSerial.current,base=currentVersion.current;
    try {
      const value=await callbacks.current.onReadConflict(base);
      if(!mounted.current)return;
      if(serial!==editSerial.current||base!==currentVersion.current) {
        setStatus("比较读取期间新增输入已保留；请重新读取当前版本并比较。");setFailure(true);return;
      }
      setComparison(value);merging.current=false;setMergeMode(false);
      setStatus("比较已读取；未覆盖草稿或改变保存基准。请明确保留本稿或人工合并。");
    }catch(error){if(mounted.current){setComparison(null);setFailure(true);setStatus(error instanceof ApiError&&(error.status===403||error.status===401)?"身份拒绝：比较未读取，原草稿仍保留。":"比较未确认：原草稿与基准仍保留，请重新读取。");}}
    finally{comparisonFlight.current=false;}
  }
  async function retryJournal() {
    if(saving.current)return;
    saving.current=true;
    try {
      const cleared=await callbacks.current.onRetryWorkingState?.();
      if(!mounted.current)return;
      journalPending.current=false;
      setFailure(false);setStatus(cleared?"已保存":"工作草稿已保全；仍有后续编辑尚未保存。");
      if(cleared)callbacks.current.onDirtyChange?.(false);
    }catch{if(mounted.current){setStatus("工作草稿保全仍未确认；正文版本不会重复写入。");setFailure(true);}}
    finally{saving.current=false;}
  }
  async function cite() {
    if (citing.current) return;
    citing.current = true;
    try {
      const reference = await callbacks.current.onCreateReference?.();
      if (reference && mounted.current) editor?.chain().focus().insertContent(reference).run();
    } catch { setStatus("引用尚未保存；请重试。"); setFailure(true); }
    finally { citing.current = false; }
  }
  useEffect(() => {
    if (!changes) return;
    saveTimer.current = window.setTimeout(() => { saveTimer.current=null;if (!composing.current&&!blocked.current) void save(); }, 900);
    return () => {if(saveTimer.current!==null){window.clearTimeout(saveTimer.current);saveTimer.current=null;}};
    // Editor identity and callbacks are stable refs; updates debounce committed input.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [changes]);
  return <section className="document-editor" aria-label="版本化草稿编辑器">
    <nav aria-label="草稿工具栏">
      <button type="button" onClick={() => editor?.chain().focus().toggleBold().run()}>加粗</button>
      <button type="button" onClick={() => editor?.chain().focus().undo().run()}>撤销</button>
      <button type="button" onClick={() => editor?.chain().focus().redo().run()}>重做</button>
      <button type="button" disabled={journalPending.current||blocked.current==="conflict"} onClick={() => void save()}>保存草稿</button>
      {journalPending.current&&onRetryWorkingState?<button type="button" onClick={()=>void retryJournal()}>仅核对工作草稿保全</button>:null}
      {onCreateReference ? <button type="button" onClick={() => void cite()}>引用当前页</button> : null}
    </nav>
    <div onCompositionStart={() => { composing.current = true; }} onCompositionEnd={() => { composing.current = false; setChanges((value) => value + 1); }}>
      <EditorContent editor={editor} />
    </div>
    {blocked.current==="conflict"&&onReadConflict?<section aria-label="文档版本冲突恢复">
      <button type="button" onClick={()=>void readConflict()}>读取当前版本并比较（保留草稿）</button>
      {comparison?<>
        <p>合并前原稿尚未归档为永久历史；编辑会更新独立工作草稿，明确保存才写入正文版本。</p>
        <p>原基准 v{comparison.base.version} · 当前已保存 v{comparison.current.version} · 我的草稿正文仍可编辑</p>
        <div className="document-conflict-comparison">
          <SnapshotComparison label="原基准" value={comparison.base.editor_json}/>
          <SnapshotComparison label="当前已保存" value={comparison.current.editor_json}/>
          <SnapshotComparison label="我的草稿" value={editor?encodeEditorContent(editor.getJSON()):content}/>
        </div>
        <button type="button" onClick={()=>{merging.current=true;setMergeMode(true);editor?.commands.focus();}}>编辑合并稿</button>
        <button type="button" onClick={()=>void save(comparison.current.version)}>{mergeMode?"明确采用合并稿并按已比较版本保存":"明确保留本稿并按已比较版本保存"}</button>
      </>:null}
    </section>:null}
    <p role={failure ? "alert" : "status"}>{status} · 当前持久化版本 {currentVersion.current}</p>
  </section>;
}
