import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { CanonicalCapabilitiesSpace } from "../spaces/CanonicalCapabilitiesSpace";
import { ABSORPTION_SURFACE_BY_CAPABILITY } from "../api/generated/absorption-surface";

const bridge = vi.hoisted(() => ({ call: vi.fn() }));
vi.mock("../api/core", () => ({ coreCommand: bridge.call }));

describe("existing capability donor projection", () => {
  beforeEach(() => { bridge.call.mockResolvedValue({ capabilities: [] }); });
  it("retains the existing11 source rows and shows its actual stable ID join", async () => {
    expect(Object.values(ABSORPTION_SURFACE_BY_CAPABILITY).flat()).toHaveLength(11);
    render(<CanonicalCapabilitiesSpace onNavigate={vi.fn()} selectedCapabilityId="CAP-0020"/>);
    expect(screen.getByText(/以下供体来源由现有稳定能力 ID 投影联接/)).toBeInTheDocument();
    expect(screen.getByText("SYSTRAN/faster-whisper")).toBeInTheDocument();
    expect(screen.queryByText(/供体映射未建立/)).not.toBeInTheDocument();
    await screen.findByText(/已读取当前 Core worker 握手/);
  });
  it("keeps unbound future capability honest without a guessed donor join", () => {
    render(<CanonicalCapabilitiesSpace onNavigate={vi.fn()} selectedCapabilityId="CAP-0080"/>);
    expect(screen.getByText(/供体映射未建立/)).toBeInTheDocument();
    expect(screen.queryByText(/以下供体来源由现有稳定能力 ID 投影联接/)).not.toBeInTheDocument();
  });
});
