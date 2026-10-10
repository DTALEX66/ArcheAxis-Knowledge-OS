import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { PdfPageRecognition } from "../components/PdfPageRecognition";

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
