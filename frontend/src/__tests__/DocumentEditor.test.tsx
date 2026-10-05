import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { DocumentEditor, decodeEditorContent, encodeEditorContent } from "../components/DocumentEditor";

describe("versioned content editor", () => {
  const content = { type: "doc", content: [{ type: "paragraph", attrs: { block_id: "p1" }, content: [{ type: "text", text: "原文" }] }] };
  it("preserves unknown nodes through the editor codec", () => {
    const original = { type: "doc", content: [{ type: "futureSpatialNode", attrs: { block_id: "future", private_property: 42 }, content: [{ type: "text", text: "未来节点正文" }] }] };
    expect(encodeEditorContent(decodeEditorContent(original))).toEqual(original);
  });
  it("does not save during Chinese composition, then saves committed text and reports failures without clearing it", async () => {
    const save = vi.fn().mockRejectedValue(new Error("conflict"));
    render(<DocumentEditor content={content} version={1} onSave={save} />);
    const editor = await screen.findByRole("textbox", { name: "文档草稿" });
    fireEvent.compositionStart(editor);
    editor.querySelector("p")!.textContent = "中文写作";
    fireEvent.input(editor);
    fireEvent.click(screen.getByRole("button", { name: "保存草稿" }));
    expect(save).not.toHaveBeenCalled();
    fireEvent.compositionEnd(editor);
    fireEvent.click(screen.getByRole("button", { name: "保存草稿" }));
    await waitFor(() => expect(save).toHaveBeenCalled());
    expect(await screen.findByRole("alert")).toHaveTextContent("草稿尚未保存");
    expect(editor).toHaveTextContent("中文写作");
  });
});
