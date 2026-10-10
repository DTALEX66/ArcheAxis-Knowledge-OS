import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { SpaceView } from "../spaces/SpaceView";

// AXW-UI-802: SpaceView is the routing contract between the desktop shell and
// the web dev mode. The audit found the desktop branch routes several ids to
// canonical surfaces, so these tests mock every child and pin WHICH child each
// id resolves to in each context - the router, not the children.
vi.mock("../spaces/CanonicalWorkspaceSpace", () => ({ CanonicalWorkspaceSpace: () => <div>CANON-workspace</div> }));
vi.mock("../spaces/LibrarySpace", () => ({ LibrarySpace: () => <div>WEB-library</div> }));
vi.mock("../spaces/IntakeSpace", () => ({ IntakeSpace: () => <div>WEB-intake</div> }));
vi.mock("../spaces/VaultSpace", () => ({ VaultSpace: () => <div>WEB-vault</div> }));
vi.mock("../spaces/EvidenceSpace", () => ({ EvidenceSpace: () => <div>WEB-evidence</div> }));
vi.mock("../spaces/LearningSpace", () => ({ LearningSpace: () => <div>WEB-learning</div> }));
vi.mock("../spaces/AiAssetsSpace", () => ({ AiAssetsSpace: () => <div>WEB-ai-assets</div> }));
vi.mock("../spaces/ExchangeSpace", () => ({ ExchangeSpace: () => <div>WEB-exchange</div> }));
vi.mock("../spaces/SettingsSpace", () => ({ SettingsSpace: () => <div>WEB-settings</div> }));
vi.mock("../spaces/CanonicalLibrarySpace", () => ({ CanonicalLibrarySpace: () => <div>CANON-library</div> }));
vi.mock("../spaces/CanonicalKnowledgeSpace", () => ({ CanonicalKnowledgeSpace: () => <div>CANON-knowledge</div> }));
vi.mock("../spaces/CanonicalLearningSpace", () => ({ CanonicalLearningSpace: () => <div>CANON-learning</div> }));
vi.mock("../spaces/CanonicalCapabilitiesSpace", () => ({ CanonicalCapabilitiesSpace: () => <div>CANON-capabilities</div> }));
vi.mock("../components/BackupPanel", () => ({ BackupPanel: () => <div>BACKUP</div> }));

vi.mock("../spaces/CanonicalLearningJourneySpace", () => ({ CanonicalLearningJourneySpace: () => <div>CANON-learning</div> }));

const noop = () => {};
const props = { onInspect: noop, onNavigate: noop };

function webMode() {
  delete (window as { __TAURI__?: unknown }).__TAURI__;
}

function desktopMode() {
  (window as { __TAURI__?: unknown }).__TAURI__ = { core: { invoke: () => Promise.resolve() } };
}

afterEach(() => {
  webMode();
});

describe("SpaceView motion interruption", () => {
  let originalAnimate: PropertyDescriptor | undefined;
  let preference: EventTarget & { matches: boolean };
  let cancel: ReturnType<typeof vi.fn>;
  let animate: ReturnType<typeof vi.fn>;
  beforeEach(() => {
    webMode();
    preference = Object.assign(new EventTarget(), { matches: false });
    vi.stubGlobal("matchMedia", () => preference);
    vi.spyOn(document, "hasFocus").mockReturnValue(true);
    vi.spyOn(document, "visibilityState", "get").mockReturnValue("visible");
    cancel = vi.fn();
    animate = vi.fn(() => ({ cancel }));
    originalAnimate = Object.getOwnPropertyDescriptor(HTMLElement.prototype, "animate");
    Object.defineProperty(HTMLElement.prototype, "animate", { configurable: true, value: animate });
  });
  afterEach(() => {
    if (originalAnimate) Object.defineProperty(HTMLElement.prototype, "animate", originalAnimate);
    else delete (HTMLElement.prototype as Partial<HTMLElement>).animate;
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });
  it.each(["blur", "hidden", "reduce"])("cancels an active transition on %s", (reason) => {
    const mounted = render(<SpaceView spaceId="library" {...props} />);
    expect(animate).toHaveBeenCalledTimes(1);
    if (reason === "blur") window.dispatchEvent(new Event("blur"));
    if (reason === "hidden") {
      vi.spyOn(document, "visibilityState", "get").mockReturnValue("hidden");
      document.dispatchEvent(new Event("visibilitychange"));
    }
    if (reason === "reduce") { preference.matches = true; preference.dispatchEvent(new Event("change")); }
    expect(cancel).toHaveBeenCalledTimes(1);
    mounted.unmount();
    const afterUnmount = cancel.mock.calls.length;
    window.dispatchEvent(new Event("blur"));
    document.dispatchEvent(new Event("visibilitychange"));
    preference.dispatchEvent(new Event("change"));
    expect(cancel).toHaveBeenCalledTimes(afterUnmount);
  });
  it.each(["unfocused", "hidden", "reduce"])("does not start decorative motion when %s", (reason) => {
    if (reason === "unfocused") vi.spyOn(document, "hasFocus").mockReturnValue(false);
    if (reason === "hidden") vi.spyOn(document, "visibilityState", "get").mockReturnValue("hidden");
    if (reason === "reduce") preference.matches = true;
    render(<SpaceView spaceId="library" {...props} />);
    expect(animate).not.toHaveBeenCalled();
  });
});

describe("SpaceView routing", () => {
  it("wraps the active space in the space-view container", () => {
    webMode();
    const { container } = render(<SpaceView spaceId="library" {...props} />);
    const view = container.querySelector(".space-view");
    expect(view).not.toBeNull();
    expect(view).toHaveAttribute("data-motion", "enter");
  });

  it("uses the same canonical page when there is no Tauri shell", () => {
    webMode();
    render(<SpaceView spaceId="settings" {...props} />);
    expect(screen.queryByText("WEB-settings")).not.toBeInTheDocument();
    expect(screen.getByText("CANON-capabilities")).toBeInTheDocument();
  });

  it("routes library to the canonical library surface inside the Tauri shell", () => {
    desktopMode();
    render(<SpaceView spaceId="library" {...props} />);
    expect(screen.getByText("CANON-library")).toBeInTheDocument();
    expect(screen.queryByText("WEB-library")).not.toBeInTheDocument();
  });

  it("routes intake and exchange to the canonical library surface and vault/evidence/ai-assets to canonical knowledge in Tauri", () => {
    desktopMode();
    for (const id of ["intake", "exchange"] as const) {
      const { unmount } = render(<SpaceView spaceId={id} {...props} />);
      expect(screen.getByText("CANON-library")).toBeInTheDocument();
      unmount();
    }
    for (const id of ["vault", "evidence", "ai-assets"] as const) {
      const { unmount } = render(<SpaceView spaceId={id} {...props} />);
      expect(screen.getByText("CANON-knowledge")).toBeInTheDocument();
      unmount();
    }
  });

  it("routes workspace to the actual workspace and settings to capability status", () => {
    desktopMode();
    const workspace = render(<SpaceView spaceId="workspace" {...props} />);
    expect(screen.getByText("CANON-workspace")).toBeInTheDocument();
    expect(screen.queryByText("BACKUP")).not.toBeInTheDocument();
    workspace.unmount();

    render(<SpaceView spaceId="settings" {...props} />);
    expect(screen.getByText("CANON-capabilities")).toBeInTheDocument();
    expect(screen.queryByText("CANON-learning")).not.toBeInTheDocument();
  });
});
