import { afterEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { SpaceView } from "../spaces/SpaceView";

// AXW-UI-802: SpaceView is the routing contract between the desktop shell and
// the web dev mode. The audit found the desktop branch routes several ids to
// canonical surfaces, so these tests mock every child and pin WHICH child each
// id resolves to in each context - the router, not the children.
vi.mock("../spaces/WorkspaceSpace", () => ({ WorkspaceSpace: () => <div>WEB-workspace</div> }));
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

describe("SpaceView routing", () => {
  it("wraps the active space in the space-view container", () => {
    webMode();
    const { container } = render(<SpaceView spaceId="library" {...props} />);
    const view = container.querySelector(".space-view");
    expect(view).not.toBeNull();
    expect(view).toHaveAttribute("data-motion", "enter");
  });

  it("uses the web spaces when there is no Tauri shell", () => {
    webMode();
    render(<SpaceView spaceId="settings" {...props} />);
    expect(screen.getByText("WEB-settings")).toBeInTheDocument();
    expect(screen.queryByText("CANON-capabilities")).not.toBeInTheDocument();
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

  it("routes workspace and settings to the canonical capabilities surface, with the backup panel only on workspace", () => {
    desktopMode();
    const workspace = render(<SpaceView spaceId="workspace" {...props} />);
    expect(screen.getByText("CANON-capabilities")).toBeInTheDocument();
    expect(screen.getByText("BACKUP")).toBeInTheDocument();
    workspace.unmount();

    render(<SpaceView spaceId="settings" {...props} />);
    expect(screen.getByText("CANON-capabilities")).toBeInTheDocument();
    expect(screen.queryByText("CANON-learning")).not.toBeInTheDocument();
  });
});
