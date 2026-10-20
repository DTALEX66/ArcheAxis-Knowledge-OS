import { beforeEach, describe, expect, it, vi } from "vitest";
import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { PdfReader } from "../components/PdfReader";

const pdf = vi.hoisted(() => ({ load: vi.fn(), page: vi.fn(), render: vi.fn(), destroy: vi.fn() }));
vi.mock("pdfjs-dist", () => ({ GlobalWorkerOptions: {}, getDocument: pdf.load }));
vi.mock("pdfjs-dist/build/pdf.worker.min.mjs?url", () => ({ default: "local-worker.mjs" }));

describe("local PDF reading", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue({} as CanvasRenderingContext2D);
    pdf.render.mockReturnValue({ promise: Promise.resolve(), cancel: vi.fn() });
    pdf.page.mockResolvedValue({ getViewport: ({ scale }: { scale: number }) => ({ width: 600 * scale, height: 800 * scale }), render: pdf.render });
    pdf.load.mockReturnValue({ promise: Promise.resolve({ numPages: 3, getPage: pdf.page }), destroy: pdf.destroy });
  });
  it("renders only the requested page, supports zoom and evidence jump with focus", async () => {
    const view = render(<PdfReader bytes={new Uint8Array([37, 80, 68, 70])} page={1} onPageChange={vi.fn()} />);
    await waitFor(() => expect(pdf.page).toHaveBeenCalledWith(1));
    expect(pdf.page).toHaveBeenCalledTimes(1);
    await userEvent.setup().click(screen.getByRole("button", { name: "放大" }));
    await waitFor(() => expect(pdf.render).toHaveBeenLastCalledWith(expect.objectContaining({ viewport: { width: 750, height: 1000 } })));
    view.rerender(<PdfReader bytes={new Uint8Array([37, 80, 68, 70])} page={3} onPageChange={vi.fn()} focusRequest={1} />);
    await waitFor(() => expect(pdf.page).toHaveBeenCalledWith(3));
    expect(screen.getByRole("region", { name: "PDF 原件阅读器" })).toHaveFocus();
    view.unmount();
    expect(pdf.destroy).toHaveBeenCalled();
  });
  it("reports rejected PDF instead of a blank successful reader", async () => {
    pdf.load.mockReturnValue({ promise: Promise.reject(new Error("broken PDF")), destroy: pdf.destroy });
    render(<PdfReader bytes={new Uint8Array([1])} page={1} onPageChange={vi.fn()} />);
    expect(await screen.findByRole("alert")).toHaveTextContent("无法读取此 PDF");
  });
  it("does not take focus from an adjacent draft when an ordinary render finishes late", async () => {
    let complete!: () => void;
    pdf.render.mockReturnValue({promise: new Promise<void>(resolve => {complete=resolve;}), cancel: vi.fn()});
    render(<><PdfReader bytes={new Uint8Array([1])} page={1} onPageChange={vi.fn()} /><input aria-label="旁边的草稿" /></>);
    await waitFor(() => expect(pdf.render).toHaveBeenCalledTimes(1));
    const draft=screen.getByRole("textbox",{name:"旁边的草稿"});
    await userEvent.setup().type(draft,"继续编辑");
    await act(async()=>complete());
    expect(draft).toHaveFocus();expect(draft).toHaveValue("继续编辑");
  });
  it("keeps keyboard focus on zoom and page controls after a consumed explicit jump", async () => {
    const bytes=new Uint8Array([1]),change=vi.fn();
    const view=render(<PdfReader bytes={bytes} page={1} onPageChange={change} focusRequest={1}/>);
    await waitFor(()=>expect(screen.getByRole("region",{name:"PDF 原件阅读器"})).toHaveFocus());
    const zoom=screen.getByRole("button",{name:"放大"});
    zoom.focus();await userEvent.setup().keyboard("{Enter}");
    await waitFor(()=>expect(pdf.render).toHaveBeenCalledTimes(2));
    expect(zoom).toHaveFocus();
    const next=screen.getByRole("button",{name:"下一页"});next.focus();
    await userEvent.setup().keyboard("{Enter}");expect(change).toHaveBeenCalledWith(2);
    view.rerender(<PdfReader bytes={bytes} page={2} onPageChange={change} focusRequest={1}/>);
    await waitFor(()=>expect(pdf.page).toHaveBeenLastCalledWith(2));
    expect(next).toHaveFocus();
  });
  it("honors a new same-page evidence jump but yields to subsequent keyboard focus", async () => {
    const bytes=new Uint8Array([1]);let complete!:()=>void;
    const view=render(<><PdfReader bytes={bytes} page={1} onPageChange={vi.fn()}/><input aria-label="继续输入"/></>);
    await waitFor(()=>expect(pdf.render).toHaveBeenCalledTimes(1));
    pdf.render.mockReturnValue({promise:new Promise<void>(resolve=>{complete=resolve;}),cancel:vi.fn()});
    view.rerender(<><PdfReader bytes={bytes} page={1} onPageChange={vi.fn()} focusRequest={1}/><input aria-label="继续输入"/></>);
    await waitFor(()=>expect(pdf.render).toHaveBeenCalledTimes(2));
    const draft=screen.getByRole("textbox",{name:"继续输入"});draft.focus();
    await act(async()=>complete());expect(draft).toHaveFocus();
    pdf.render.mockReturnValue({promise:Promise.resolve(),cancel:vi.fn()});
    view.rerender(<><PdfReader bytes={bytes} page={1} onPageChange={vi.fn()} focusRequest={2}/><input aria-label="继续输入"/></>);
    await waitFor(()=>expect(screen.getByRole("region",{name:"PDF 原件阅读器"})).toHaveFocus());
  });
});
