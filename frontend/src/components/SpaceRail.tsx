import type { SpaceDef, SpaceId } from "../spaces/spaces";

export function SpaceRail({
  active,
  onNavigate,
  spaces,
}: {
  active: SpaceId;
  onNavigate: (id: SpaceId) => void;
  spaces: readonly SpaceDef[];
}) {
  return (
    <nav className="space-rail" aria-label="产品空间">
      <ul className="space-rail-list" role="list">
        {spaces.map((space) => (
          <li key={space.id}>
            <button
              type="button"
              className="space-rail-item"
              aria-current={space.id === active ? "page" : undefined}
              onClick={() => onNavigate(space.id)}
              title={space.description}
            >
              <span className="space-rail-icon" aria-hidden="true">{space.icon}</span>
              <span>{space.label}</span>
            </button>
          </li>
        ))}
      </ul>
    </nav>
  );
}
