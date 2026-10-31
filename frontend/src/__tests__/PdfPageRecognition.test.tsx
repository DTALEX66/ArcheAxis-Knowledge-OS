import {createHash,webcrypto} from "node:crypto";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { PdfPageRecognition } from "../components/PdfPageRecognition";
vi.mock("../components/JobContent", () => ({ JobContent: (props: {sourceId:string;sourceRevision:string;name:string}) => <div aria-label="页面识别执行身份">{JSON.stringify(props)}</div> }));

vi.mock("../components/OcrImageReader",()=>({OcrImageReader:(props:unknown)=><div aria-label="已核对页图参数">{JSON.stringify(props)}</div>}));

const bridge = vi.hoisted(() => ({ call: vi.fn() }));
vi.mock("../api/core", () => ({ coreCommand: bridge.call }));

const readPage = {
  page: 3, source_id: "src-page-3", origin_ref: "src-pdf#page-3",
  original_name: "report-page-3.png", sha256: "a".repeat(64),
  recognised: true, text: "半径 6371 千米", job_id: "job-pdf-page-3",
};
const blindPage = {
  page: 4, source_id: "src-page-4", origin_ref: "src-pdf#page-4",
  original_name: "report-page-4.png", sha256: "b".repeat(64),
  recognised: false, text: null, job_id: null,
};
const pages = {
  pdf_source_id: "src-pdf", page_count: 2, recognised_count: 1,
  pages: [readPage, blindPage],
  note: "只列出此来源被渲染出的页面。",
};

describe("PDF page recognition write-back", () => {
  beforeEach(() => bridge.call.mockReset());

  it.each(["foreign-source", "bad-hash", "duplicate-page", "count-mismatch"])("refuses %s page evidence without exposing recognition actions", async (mutation) => {
    const value = structuredClone(pages);
    if (mutation === "foreign-source") value.pdf_source_id = "another-source";
    if (mutation === "bad-hash") value.pages[0].sha256 = "not-a-digest";
    if (mutation === "duplicate-page") value.pages[1].source_id = value.pages[0].source_id;
    if (mutation === "count-mismatch") value.page_count = 3;
    bridge.call.mockResolvedValue(value);
    render(<PdfPageRecognition sourceId="src-pdf" />);
    await userEvent.click(screen.getByRole("button", {name:"读取页面与识别文本"}));
    expect(await screen.findByRole("status")).toHaveTextContent("页面识别回写读取失败");
    expect(screen.queryByRole("button", {name:/第 3 页/})).not.toBeInTheDocument();
    expect(screen.queryByRole("button", {name:"处理此页识别文本"})).not.toBeInTheDocument();
  });

  it("opens an explicit page-bound recognition action without executing on selection", async () => {
    bridge.call.mockImplementation(async () => pages);
    render(<PdfPageRecognition sourceId="src-pdf" />);
    await userEvent.click(screen.getByRole("button", {name:"读取页面与识别文本"}));
    await userEvent.click(await screen.findByRole("button", {name:/第 4 页/}));
    expect(screen.queryByLabelText("页面识别执行身份")).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", {name:"处理此页识别文本"}));
    expect(JSON.parse(screen.getByLabelText("页面识别执行身份").textContent!)).toEqual({sourceId:blindPage.source_id,sourceRevision:blindPage.sha256,name:blindPage.original_name});
    expect(bridge.call.mock.calls.every(([operation]) => operation === "source_pages")).toBe(true);
    await userEvent.click(screen.getByRole("button", {name:/第 3 页/}));
    expect(screen.queryByLabelText("页面识别执行身份")).not.toBeInTheDocument();
  });

  it("reads each page and shows only the page that was opened", async () => {
    bridge.call.mockImplementation(async (operation: string) => {
      if (operation === "source_pages") return pages;
      return {};
    });
    render(<PdfPageRecognition sourceId="src-pdf" />);
    await userEvent.click(screen.getByRole("button", { name: "读取页面与识别文本" }));

    expect(await screen.findByRole("status")).toHaveTextContent("已读取 2 个页面，其中 1 页有识别文本");
    expect(screen.getByText("页面 2 · 已识别 1 · 未识别 1")).toBeInTheDocument();
    expect(screen.getByText("只列出此来源被渲染出的页面。")).toBeInTheDocument();
    expect(screen.queryByRole("textbox")).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: /第 3 页/ }));
    expect(await screen.findByRole("textbox", { name: /第 3 页的识别文本/ })).toHaveValue("半径 6371 千米");
  });

  it("states a page with no recognised text instead of leaving it blank", async () => {
    bridge.call.mockImplementation(async (operation: string) => (operation === "source_pages" ? pages : {}));
    render(<PdfPageRecognition sourceId="src-pdf" />);
    await userEvent.click(screen.getByRole("button", { name: "读取页面与识别文本" }));
    await userEvent.click(screen.getByRole("button", { name: /第 4 页/ }));

    expect(await screen.findByRole("status")).toHaveTextContent("第 4 页没有识别文本");
    expect(screen.getByText(/未识别（无文本）/)).toBeInTheDocument();
    expect(screen.getByText(/无作业/)).toBeInTheDocument();
    expect(screen.queryByRole("textbox")).not.toBeInTheDocument();
  });

  it("calls an unrendered source a fact rather than an error", async () => {
    bridge.call.mockImplementation(async (operation: string) => (operation === "source_pages"
      ? { pdf_source_id: "src-pdf", page_count: 0, recognised_count: 0, pages: [], note: "只列出此来源被渲染出的页面。" }
      : {}));
    render(<PdfPageRecognition sourceId="src-pdf" />);
    await userEvent.click(screen.getByRole("button", { name: "读取页面与识别文本" }));

    expect(await screen.findByRole("status")).toHaveTextContent("此来源没有被渲染过的页面");
    expect(screen.queryByRole("list")).not.toBeInTheDocument();
  });

  it("refuses a payload whose page entry is missing the recognised flag", async () => {
    bridge.call.mockImplementation(async (operation: string) => (operation === "source_pages"
      ? { ...pages, pages: [{ ...readPage, recognised: undefined }] }
      : {}));
    render(<PdfPageRecognition sourceId="src-pdf" />);
    await userEvent.click(screen.getByRole("button", { name: "读取页面与识别文本" }));

    expect(await screen.findByRole("status")).toHaveTextContent("读取失败");
    expect(screen.queryByRole("list")).not.toBeInTheDocument();
  });

  it("keeps what was already read when a later read fails", async () => {
    bridge.call.mockResolvedValueOnce(pages);
    render(<PdfPageRecognition sourceId="src-pdf" />);
    await userEvent.click(screen.getByRole("button", { name: "读取页面与识别文本" }));
    expect(await screen.findByRole("list")).toBeInTheDocument();

    bridge.call.mockRejectedValueOnce(new Error("本地核心未能完成 source_pages（500）。"));
    await userEvent.click(screen.getByRole("button", { name: "读取页面与识别文本" }));

    expect(await screen.findByRole("status")).toHaveTextContent("未替换已有内容");
    expect(screen.getByRole("list")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /第 3 页/ }));
    expect(await screen.findByRole("textbox", { name: /第 3 页的识别文本/ })).toHaveValue("半径 6371 千米");
  });
});


describe("SYNTHETIC PDF page original and fixed citation consumer",()=>{
  const bytes=Buffer.from("authored page image"),sha=createHash("sha256").update(bytes).digest("hex");
  const page={...readPage,sha256:sha};
  const original={source_id:page.source_id,sha256:sha,name:page.original_name,media_type:"image/png",content_base64:bytes.toString("base64")};
  const anchor={source_id:page.source_id,source_revision:sha,anchor_id:"page-anchor",position:"{}"};
  async function select(){
    await userEvent.click(screen.getByRole("button",{name:"读取页面与识别文本"}));
    await userEvent.click(screen.getByRole("button",{name:/第 3 页/}));
  }
  beforeEach(()=>{
    bridge.call.mockReset();
    vi.stubGlobal("crypto",webcrypto);
    bridge.call.mockImplementation(async(op:string)=>{
      if(op==="source_pages")return {...pages,pages:[page,blindPage]};
      if(op==="source_original")return original;
      if(op==="anchors_list")return {anchors:[anchor]};
      throw new Error("Unexpected "+op);
    });
  });
  it("opens verified page bytes and its anchors without executing OCR, and clears on changing pages",async()=>{
    const onPageSelect=vi.fn();render(<PdfPageRecognition sourceId="src-pdf" onPageSelect={onPageSelect}/>);
    await select();expect(onPageSelect).toHaveBeenLastCalledWith(3);
    expect(screen.queryByLabelText("已核对页图参数")).toBeNull();
    await userEvent.click(screen.getByRole("button",{name:"查看此页原图与引用"}));
    const value=JSON.parse((await screen.findByLabelText("已核对页图参数")).textContent!);
    expect(value).toMatchObject({sourceId:page.source_id,revision:sha,original,anchors:[anchor]});
    expect(bridge.call.mock.calls.every(([op])=>["source_pages","source_original","anchors_list"].includes(op))).toBe(true);
    await userEvent.click(screen.getByRole("button",{name:/第 4 页/}));
    expect(screen.queryByLabelText("已核对页图参数")).toBeNull();expect(onPageSelect).toHaveBeenLastCalledWith(4);
  });
  it.each(["wrong-source","wrong-bytes","foreign-anchor"])("refuses %s rather than exposing another page as verified",async kind=>{
    const previous=bridge.call.getMockImplementation()!;
    bridge.call.mockImplementation(async(op:string)=>{
      if(op==="source_original")return {...original,...(kind==="wrong-source"?{source_id:"foreign"}:kind==="wrong-bytes"?{content_base64:Buffer.from("other").toString("base64")}: {})};
      if(op==="anchors_list"&&kind==="foreign-anchor")return {anchors:[{...anchor,source_id:"foreign"}]};
      return previous(op);
    });
    render(<PdfPageRecognition sourceId="src-pdf"/>);await select();
    await userEvent.click(screen.getByRole("button",{name:"查看此页原图与引用"}));
    expect(await screen.findByRole("alert")).toHaveTextContent("此页原图与引用未核对");
    expect(screen.queryByLabelText("已核对页图参数")).toBeNull();
  });
  it("discards an old page read that resolves after another page is selected",async()=>{
    let resolve!:(v:unknown)=>void;const previous=bridge.call.getMockImplementation()!;
    bridge.call.mockImplementation((op:string)=>op==="source_original"?new Promise(r=>{resolve=r;}):previous(op));
    render(<PdfPageRecognition sourceId="src-pdf"/>);await select();
    fireEvent.click(screen.getByRole("button",{name:"查看此页原图与引用"}));
    await waitFor(()=>expect(resolve).toBeTypeOf("function"));
    fireEvent.click(screen.getByRole("button",{name:/第 4 页/}));
    await act(async()=>{resolve(original);});
    expect(screen.queryByLabelText("已核对页图参数")).toBeNull();
    expect(bridge.call.mock.calls.filter(([op])=>op==="anchors_list")).toHaveLength(0);
    expect(screen.getByRole("status")).toHaveTextContent("第 4 页没有识别文本");
  });
  it("clears the old image when the parent PDF control changes its page",async()=>{
    const view=render(<PdfPageRecognition sourceId="src-pdf" currentPage={3}/>);await select();
    await userEvent.click(screen.getByRole("button",{name:"查看此页原图与引用"}));
    await screen.findByLabelText("已核对页图参数");
    view.rerender(<PdfPageRecognition sourceId="src-pdf" currentPage={4}/>);
    expect(screen.queryByLabelText("已核对页图参数")).toBeNull();
    expect(screen.getByRole("status")).toHaveTextContent("第 4 页没有识别文本");
  });

  it("releases refresh admission when parent paging cancels an in-flight read",async()=>{
    let resolve!:(v:unknown)=>void;const view=render(<PdfPageRecognition sourceId="src-pdf" currentPage={3}/>);await select();
    bridge.call.mockImplementationOnce(()=>new Promise(r=>{resolve=r;}));
    fireEvent.click(screen.getByRole("button",{name:"读取页面与识别文本"}));
    expect(screen.getByRole("button",{name:"读取页面与识别文本"})).toBeDisabled();
    view.rerender(<PdfPageRecognition sourceId="src-pdf" currentPage={4}/>);
    await act(async()=>{resolve({...pages,pages:[page,blindPage]});});
    expect(screen.getByRole("button",{name:"读取页面与识别文本"})).toBeEnabled();
    expect(screen.getByRole("status")).toHaveTextContent("第 4 页没有识别文本");
    await userEvent.click(screen.getByRole("button",{name:"读取页面与识别文本"}));
    expect(screen.getByRole("status")).toHaveTextContent("已读取 2 个页面");
  });

});
