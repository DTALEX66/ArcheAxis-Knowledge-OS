import { beforeEach, afterEach, expect, it, vi } from "vitest";
import { render, screen, fireEvent, waitFor, act } from "@testing-library/react";
import { webcrypto } from "node:crypto";
import { DocumentEmbeds } from "../components/DocumentEmbeds";
const bridge = vi.hoisted(() => ({ call: vi.fn() }));
vi.mock("../api/core", () => ({ coreCommand: bridge.call }));
const relation = (id: string, block?: string) => ({ id, kind: "related", label: `Embed ${id}`, presentation: "embed", target: { kind: "document", document_id: id, version: 1, ...(block ? { block_id: block } : {}) } });
const editor = (relations: unknown[]) => ({ type: "doc", attrs: { archeaxis_relations: { schema: "archeaxis.relations/v1", relations } }, content: [] });
const doc = (id: string) => ({ document_id: id, version: 1, title: `Title ${id}`, content_sha256: "b".repeat(64), text_projection: `Body ${id}`, blocks: [{ block_id: "selected", text_projection: `Block ${id}` }], editor_json: editor([relation("nested")]) });
beforeEach(() => { bridge.call.mockReset(); vi.stubGlobal("crypto", webcrypto); bridge.call.mockImplementation(async (_op, payload) => doc(payload.document_id)); });
afterEach(() => vi.unstubAllGlobals());
it("keeps imported provenance out of the heading without changing saved labels or user text", async () => {
  const label = `Original CAS ${"b".repeat(64)} · embed: peer#^named (human-selected block)`;
  const saved = editor([{...relation("one"), id:`ingest_${"c".repeat(64)}`, label}]);
  const before = JSON.stringify(saved);
  const view = render(<DocumentEmbeds editor={saved}/>);
  await screen.findByText("Body one");
  expect(screen.getByRole("heading", {name:"嵌入：peer#^named（已选定块）"})).toBeInTheDocument();
  expect(screen.getByText("原始关系说明")).toBeInTheDocument();
  expect(screen.getByText(label)).toBeInTheDocument();
  expect(JSON.stringify(saved)).toBe(before);
  view.rerender(<DocumentEmbeds editor={editor([{...relation("manual"), label}])}/>);
  await screen.findByText("Body manual");
  expect(screen.getByRole("heading", {name:label})).toBeInTheDocument();
});
it("renders explicit saved embeds at fixed versions/blocks, without writes, nested fetches or stealing focus", async () => {
  render(<><button autoFocus>Keep typing</button><DocumentEmbeds editor={editor([relation("old"), relation("block", "selected"), { id: "ordinary", kind: "related", label: "link", target: { kind: "document", document_id: "ordinary", version: 1 } }])}/></>);
  await screen.findByText("Body old"); await screen.findByText("Block block");
  expect(screen.queryByText("Body block")).not.toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Keep typing" })).toHaveFocus();
  expect(bridge.call.mock.calls).toEqual([["document_version", { document_id: "old", version: 1 }], ["document_version", { document_id: "block", version: 1 }]]);
});
it("bounds active reads and renders other embeds only on explicit pagination", async () => {
  render(<DocumentEmbeds editor={editor(["a", "b", "c", "d"].map(id => relation(id)))}/>);
  await screen.findByText("Body c"); expect(bridge.call).toHaveBeenCalledTimes(3);
  expect(screen.queryByText("Body d")).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "下一组嵌入" })); await screen.findByText("Body d");
  expect(screen.queryByText("Body a")).not.toBeInTheDocument();
});
it("rejects malformed relation metadata without guessing embed identity from labels", () => {
  render(<DocumentEmbeds editor={editor([{ ...relation("bad"), target: { kind: "document", document_id: "bad" } }])}/>);
  expect(screen.getByRole("alert")).toHaveTextContent("嵌入关系结构不可用"); expect(bridge.call).not.toHaveBeenCalled();
});
it("does not show a stale response after switching the saved envelope", async () => {
  let finish!: (value: unknown) => void;
  bridge.call.mockImplementation((_op, p) => p.document_id === "old" ? new Promise(resolve => { finish = resolve; }) : Promise.resolve(doc("new")));
  const view = render(<DocumentEmbeds editor={editor([relation("old")])}/>);
  view.rerender(<DocumentEmbeds editor={editor([relation("new")])}/>); await screen.findByText("Body new");
  await act(async () => finish(doc("old"))); await waitFor(() => expect(screen.queryByText("Body old")).not.toBeInTheDocument());
});
it("keeps failures visible and retries the same immutable target", async () => {
  bridge.call.mockRejectedValueOnce(new Error("offline")); render(<DocumentEmbeds editor={editor([relation("fixed")])}/>);
  const alert = await screen.findByRole("alert");
  expect(alert).toHaveTextContent("本地数据暂时不可用");
  expect(alert).not.toHaveTextContent("offline");
  expect(bridge.call).toHaveBeenCalledTimes(1);
  fireEvent.click(screen.getByRole("button", { name: "重试引用" }));
  await screen.findByText("Body fixed");
  expect(bridge.call.mock.calls).toEqual([
    ["document_version", {document_id: "fixed", version: 1}],
    ["document_version", {document_id: "fixed", version: 1}],
  ]);
});

it("verifies source bytes before showing an attachment embed and never executes HTML", async () => {
  const text = "<script>unsafe()</script>";
  const digest = Array.from(new Uint8Array(await webcrypto.subtle.digest("SHA-256", new TextEncoder().encode(text)))).map(value => value.toString(16).padStart(2, "0")).join("");
  bridge.call.mockResolvedValue({source_id:"asset", sha256:digest, name:"sample.html", media_type:"text/html", content_base64:btoa(text)});
  render(<DocumentEmbeds editor={editor([{...relation("asset"),target:{kind:"source",source_id:"asset",sha256:digest}}])}/>);
  expect(await screen.findByText(text)).toBeInTheDocument(); expect(document.querySelector("script")).toBeNull();
  expect(bridge.call).toHaveBeenCalledWith("source_original",{source_id:"asset"});
});
it("shows budget errors without rendering oversized text or decoding oversized source bytes", async () => {
  bridge.call.mockResolvedValueOnce({...doc("large"),text_projection:"x".repeat(1024*1024+1)});
  const view=render(<DocumentEmbeds editor={editor([relation("large")])}/>);
  expect(await screen.findByRole("alert")).toHaveTextContent("阅读预算");
  bridge.call.mockResolvedValueOnce({source_id:"large-source",sha256:"a".repeat(64),name:"large.txt",media_type:"text/plain",content_base64:"A".repeat(4*Math.ceil(8*1024*1024/3)+4)});
  view.rerender(<DocumentEmbeds editor={editor([{...relation("large-source"),target:{kind:"source",source_id:"large-source",sha256:"a".repeat(64)}}])}/>);
  expect(await screen.findByRole("alert")).toHaveTextContent("8 MiB 预算");
});
it("opens and collapses the same fixed target while ordinary relations remain inert", async () => {
  const open=vi.fn();render(<DocumentEmbeds editor={editor([relation("one","selected")])} onOpenReference={open}/>);
  await screen.findByText("Block one");fireEvent.click(screen.getByRole("button",{name:"打开固定引用"}));
  expect(open).toHaveBeenCalledWith({kind:"document",document_id:"one",version:1,block_id:"selected"});
  fireEvent.click(screen.getByRole("button",{name:"收起嵌入"}));expect(screen.queryByText("Block one")).not.toBeInTheDocument();
  expect(document.activeElement).toHaveClass("ui-document-embed");
  fireEvent.click(screen.getByRole("button",{name:"展开嵌入 Embed one"}));await screen.findByText("Block one");
});

it("bounds an explicitly selected knowledge embed without reading another object", async () => {
 bridge.call.mockResolvedValue({knowledge_id:"bounded",body:"x".repeat(1024*1024+1),version:"revision_1",status:"candidate",source_id:null,anchor_id:null});
 render(<DocumentEmbeds editor={editor([{...relation("bounded"),target:{kind:"knowledge",knowledge_id:"bounded"}}])}/>);
 expect(await screen.findByRole("alert")).toHaveTextContent("知识正文超过");
 expect(bridge.call).toHaveBeenCalledWith("knowledge_get",{id:"bounded"});
 expect(bridge.call).toHaveBeenCalledTimes(1);
});
