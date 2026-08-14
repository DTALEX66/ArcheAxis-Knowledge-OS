import { SpaceId, SPACES } from "../spaces/spaces";

// Left rail — the six product spaces (task pack §15.3).
export function SpaceRail({
  active,
  onNavigate,
  spaces,
}: {
  active: SpaceId;
  onNavigate: (id: SpaceId) => void;
  spaces: readonly { id: SpaceId; label: string; icon: string }[];
}) {
  return (
    <nav className="space-rail" aria-label="主空间导航">
      <ul className="space-rail-list">
        {spaces.map((s) => (
          <li key={s.id}>
            <button
              type="button"
              className="space-rail-item"
              aria-current={active === s.id ? "page" : undefined}
              aria-label={s.label}
              onClick={() => onNavigate(s.id)}
            >
              <span className="space-rail-icon" aria-hidden="true">
                {s.icon}
              </span>
              <span className="space-rail-label">{s.label}</span>
            </button>
          </li>
        ))}
      </ul>
    </nav>
  );
}

export { SPACES };
