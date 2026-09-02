import { RELATED } from "../spaces/related";
import { SPACES, type SpaceId } from "../spaces/spaces";

export function ContextNav({ active, onNavigate }: { active: SpaceId; onNavigate: (id: SpaceId) => void }) {
  const current = SPACES.find((space) => space.id === active) ?? SPACES[0];
  return (
    <nav className="context-subnav" aria-label="当前空间导航">
      <header role="presentation">
        <span>当前空间</span>
        <h2>{current.label}</h2>
        <p>{current.description}</p>
      </header>
      <ul>
        {RELATED[active].filter((id) => id !== active).map((id) => {
          const space = SPACES.find((item) => item.id === id)!;
          return (
            <li key={id}>
              <button
                type="button"
                onClick={() => onNavigate(id)}
              >
                <span aria-hidden="true" style={{ width: 18, opacity: 0.7 }}>{space.icon}</span>
                <span>
                  <b>{space.label}</b>
                  <small>{space.description}</small>
                </span>
              </button>
            </li>
          );
        })}
      </ul>
      <footer>只显示已接入的产品空间</footer>
    </nav>
  );
}
