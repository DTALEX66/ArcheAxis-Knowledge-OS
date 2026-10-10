import { afterEach, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { LocalDocumentSearch } from "../components/LocalDocumentSearch";
import { reviewDeadline, workspaceReviews } from "../presentation/workspaceReview";
const bridge=vi.hoisted(()=>({call:vi.fn()}));
vi.mock("../api/core",()=>({coreCommand:bridge.call}));
afterEach(()=>{cleanup();bridge.call.mockReset();});
const row={document_id:"doc_real",title:"本地文档",version:3,content_sha256:"a".repeat(64),head:"真实正文",source_id:null};
function response(documents=[row]) {return {items:[],transforms:[],count:0,transform_count:0,documents,document_count:documents.length};}
function submit(value:string) {fireEvent.change(screen.getByRole("searchbox"),{target:{value}});fireEvent.click(screen.getByRole("button",{name:"搜索文档"}));}
it("SIMULATED: searches the local Core and opens its stable document ID with no AI operation",async()=>{
  bridge.call.mockResolvedValue(response());const open=vi.fn();render(<LocalDocumentSearch onOpenDocument={open}/>);submit("本地");
  fireEvent.click(await screen.findByRole("button",{name:"本地文档 · v3"}));
  expect(open).toHaveBeenCalledWith("doc_real");expect(bridge.call.mock.calls).toEqual([["search",{q:"本地",active_only:false}]]);
  expect(screen.getByText("真实正文")).toBeInTheDocument();
});
it("does not show a failed local search as zero matches",async()=>{
  bridge.call.mockRejectedValue(new Error("offline"));render(<LocalDocumentSearch/>);submit("内容");
  await screen.findByRole("alert");expect(screen.queryByText(/0 个文档结果/)).toBeNull();
});
it.each([response([row,row]),{...response(),document_count:2},{...response(),documents:undefined},response([{...row,content_sha256:"bad"}])])("refuses mismatched or ambiguous result identity",async result=>{
  bridge.call.mockResolvedValue(result);render(<LocalDocumentSearch/>);submit("文档");await screen.findByRole("alert");
  expect(screen.queryByRole("button",{name:"本地文档 · v3"})).toBeNull();
});
it("suppresses an old response after a newer query or clearing the input",async()=>{
  let finish!:(value:unknown)=>void;bridge.call.mockImplementationOnce(()=>new Promise(resolve=>{finish=resolve;})).mockResolvedValueOnce(response([]));
  render(<LocalDocumentSearch/>);submit("旧");submit("新");await screen.findByText(/“新” · 0/);
  finish(response());await waitFor(()=>expect(screen.queryByRole("button",{name:"本地文档 · v3"})).toBeNull());
  expect(screen.getByText(/“新” · 0/)).toBeInTheDocument();fireEvent.change(screen.getByRole("searchbox"),{target:{value:""}});
  expect(screen.queryByText(/个文档结果/)).toBeNull();
});
it("does not submit during composition and uses UTF-8 bytes for the Core query bound",async()=>{
  bridge.call.mockResolvedValue(response([]));render(<LocalDocumentSearch/>);const input=screen.getByRole("searchbox");
  fireEvent.change(input,{target:{value:"拼音"}});fireEvent.compositionStart(input);fireEvent.submit(input.closest("form")!);
  expect(bridge.call).not.toHaveBeenCalled();fireEvent.compositionEnd(input);fireEvent.submit(input.closest("form")!);
  await screen.findByText(/“拼音” · 0/);submit("中".repeat(171));await screen.findByRole("alert");expect(bridge.call).toHaveBeenCalledTimes(1);
});
it("orders only verified due deadlines and treats SQLite timestamps as UTC",()=>{
  expect(reviewDeadline("2026-10-10 00:00:00")).toBe(Date.parse("2026-10-10T00:00:00Z"));
  expect(reviewDeadline("2026-10-10T08:00:00.123456+08:00")).toBe(Date.parse("2026-10-10T00:00:00.123Z"));
  expect(reviewDeadline("2026-10-10T00:00:00.999999+00:00")).toBe(Date.parse("2026-10-10T00:00:00.999Z"));
  expect(reviewDeadline("2026-02-30T08:00:00.1+08:00")).toBeNull();
  expect(reviewDeadline("2026-10-10T00:00:00+24:00")).toBeNull();
  expect(reviewDeadline("2026-02-30 00:00:00")).toBeNull();expect(reviewDeadline("tomorrow")).toBeNull();
  expect(workspaceReviews([{item_key:"later",next_review:"2026-10-10 01:00:00"},{item_key:"first",next_review:"2026-10-09 00:00:00"},{item_key:"future",next_review:"2099-01-01T00:00:00Z"},{item_key:"none",next_review:null},{item_key:"bad",next_review:"yesterday"}],Date.parse("2026-10-10T02:00:00Z"))).toEqual({due:[{item_key:"first",next_review:"2026-10-09 00:00:00"},{item_key:"later",next_review:"2026-10-10 01:00:00"}],unscheduled:1,unverified:1});
});
