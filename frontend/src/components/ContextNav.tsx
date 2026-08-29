import { SPACES, type SpaceId } from "../spaces/spaces";

const RELATED: Record<SpaceId, SpaceId[]> = {
  workspace: ["workspace", "library", "intake"],
  library: ["library", "intake", "evidence"],
  intake: ["intake", "library", "vault"],
  vault: ["vault", "intake", "library"],
  evidence: ["evidence", "library", "ai-assets"],
  learning: ["learning", "evidence", "ai-assets"],
  "ai-assets": ["ai-assets", "evidence", "learning"],
  exchange: ["exchange", "library", "settings"],
  settings: ["settings", "exchange", "library"],
};

export function ContextNav({ active, onNavigate }: { active: SpaceId; onNavigate: (id: SpaceId) => void }) {
  const current = SPACES.find((space) => space.id === active) ?? SPACES[0];
  return <nav className="context-subnav" aria-label="当前空间导航">
    <header role="presentation">
      <span>当前空间</span>
      <h2>{current.label}</h2>
      <p>{current.description}</p>
    </header>
    <ul>
      {RELATED[active].map((id) => {
        const space = SPACES.find((item) => item.id === id)!;
        return <li key={id}>
          <button
            type="button"
            aria-current={id === active ? "page" : undefined}
            onClick={() => onNavigate(id)}
          >
            <span aria-hidden="true">{space.icon}</span>
            <span><b>{space.label}</b><small>{space.description}</small></span>
          </button>
        </li>;
      })}
    </ul>
    <footer>只显示已接入的产品空间；规划能力不会进入普通导航。</footer>
  </nav>;
}
