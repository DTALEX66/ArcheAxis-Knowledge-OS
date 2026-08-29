import { afterEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ExchangeSpace } from "../spaces/ExchangeSpace";
import * as api from "../api/workspace";

vi.mock("../api/workspace", () => ({
  exportExchange: vi.fn(),
  verifyExchange: vi.fn(),
}));

const mocked = vi.mocked(api);

afterEach(() => {
  vi.clearAllMocks();
});

describe("ExchangeSpace", () => {
  it("exports an exchange package and shows the receipt", async () => {
    const user = userEvent.setup();
    mocked.exportExchange.mockResolvedValue({
      destination: "D:/data/exchange/course",
      item_count: 42,
      manifest_sha256: "e".repeat(64),
    });
    render(<ExchangeSpace />);

    await user.clear(screen.getByRole("textbox", { name: "交换包名称" }));
    await user.type(screen.getByRole("textbox", { name: "交换包名称" }), "course");
    await user.click(screen.getByRole("button", { name: "导出" }));

    expect(await screen.findByText("已导出 42 项知识交换包")).toBeInTheDocument();
    expect(screen.getByText("42", { exact: true })).toBeInTheDocument();
    expect(screen.getByText(/^e{16}…$/)).toBeInTheDocument();
    expect(mocked.exportExchange).toHaveBeenCalledWith("course", false);
  });

  it("verifies an exchange package and reports pass/fail truthfully", async () => {
    const user = userEvent.setup();
    mocked.verifyExchange.mockResolvedValue({ valid: true, verified_items: 5 });
    render(<ExchangeSpace />);

    await user.click(screen.getByRole("button", { name: "验证" }));

    expect(await screen.findByText("交换包验证通过：清单与全部文件哈希一致。")).toBeInTheDocument();
    expect(screen.getByText(/通过 · 5 项/)).toBeInTheDocument();
  });

  it("surfaces a failed verification as an error, never as success", async () => {
    const user = userEvent.setup();
    mocked.verifyExchange.mockRejectedValue(new Error("manifest.json missing (partial export?)"));
    render(<ExchangeSpace />);

    await user.click(screen.getByRole("button", { name: "验证" }));

    expect(await screen.findByText(/本地数据暂时不可用/)).toBeInTheDocument();
    expect(screen.queryByText("交换包验证通过")).not.toBeInTheDocument();
  });
});
