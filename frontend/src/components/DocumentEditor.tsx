import { useEffect, useRef, useState } from "react";
import { Extension, Node, type JSONContent } from "@tiptap/core";
import { EditorContent, useEditor } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";

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
  const { originalAttrs, ...attrs } = content.attrs ?? {};
  const merged = { ...(originalAttrs ?? {}), ...attrs };
  for (const key of Object.keys(merged)) if (merged[key] === null) delete merged[key];
  return { ...content, ...(Object.keys(merged).length ? { attrs: merged } : { attrs: undefined }), ...(content.content ? { content: content.content.map(encodeEditorContent) } : {}) };
}

export function DocumentEditor({ content, version, onSave, onRetryWorkingState, onDirtyChange, onDraftChange, onCreateReference, onReferenceActivate }: {
  content: JSONContent;
  version: number;
  onSave: (content: JSONContent, expectedVersion: number) => Promise<{ content: JSONContent; version: number; workingStateConfirmed?:boolean }>;
  onRetryWorkingState?:()=>Promise<boolean>;
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
  const citing = useRef(false);
  const currentVersion = useRef(version);
  const mounted = useRef(true);
  const callbacks = useRef({ onSave, onRetryWorkingState, onDirtyChange, onDraftChange, onCreateReference, onReferenceActivate });
  callbacks.current = { onSave, onRetryWorkingState, onDirtyChange, onDraftChange, onCreateReference, onReferenceActivate };
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
      const transaction = editor.state.tr;
      editor.state.doc.descendants((node, position) => {
        if (blockTypes.includes(node.type.name) && !node.attrs.block_id) transaction.setNodeMarkup(position, undefined, { ...node.attrs, block_id: crypto.randomUUID() });
      });
      if (transaction.docChanged) editor.view.dispatch(transaction);
      callbacks.current.onDraftChange?.(encodeEditorContent(editor.getJSON()), currentVersion.current);
      journalPending.current=false;
      setStatus("尚未保存");
      setFailure(false);
      setChanges((value) => value + 1);
      callbacks.current.onDirtyChange?.(true);
    },
  });
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; }; }, []);
  async function save() {
    if (!editor || composing.current || saving.current || journalPending.current) return;
    if(saveTimer.current!==null){window.clearTimeout(saveTimer.current);saveTimer.current=null;}
    const sent = encodeEditorContent(editor.getJSON());
    if(acknowledgedContent.current===JSON.stringify(sent))return;
    saving.current = true;
    setStatus("正在保存…");
    try {
      const saved = await callbacks.current.onSave(sent, currentVersion.current);
      if (!mounted.current) return;
      currentVersion.current = saved.version;
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
    } catch {
      if (mounted.current) { setStatus("草稿尚未保存；内容仍保留，请重试。版本冲突时请先保留当前文字。"); setFailure(true); }
    } finally { saving.current = false; }
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
    saveTimer.current = window.setTimeout(() => { saveTimer.current=null;if (!composing.current) void save(); }, 900);
    return () => {if(saveTimer.current!==null){window.clearTimeout(saveTimer.current);saveTimer.current=null;}};
    // Editor identity and callbacks are stable refs; updates debounce committed input.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [changes]);
  return <section className="document-editor" aria-label="版本化草稿编辑器">
    <nav aria-label="草稿工具栏">
      <button type="button" onClick={() => editor?.chain().focus().toggleBold().run()}>加粗</button>
      <button type="button" onClick={() => editor?.chain().focus().undo().run()}>撤销</button>
      <button type="button" onClick={() => editor?.chain().focus().redo().run()}>重做</button>
      <button type="button" disabled={journalPending.current} onClick={() => void save()}>保存草稿</button>
      {journalPending.current&&onRetryWorkingState?<button type="button" onClick={()=>void retryJournal()}>仅核对工作草稿保全</button>:null}
      {onCreateReference ? <button type="button" onClick={() => void cite()}>引用当前页</button> : null}
    </nav>
    <div onCompositionStart={() => { composing.current = true; }} onCompositionEnd={() => { composing.current = false; setChanges((value) => value + 1); }}>
      <EditorContent editor={editor} />
    </div>
    <p role={failure ? "alert" : "status"}>{status} · 当前持久化版本 {currentVersion.current}</p>
  </section>;
}
