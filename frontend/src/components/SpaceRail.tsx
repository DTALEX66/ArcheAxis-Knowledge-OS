import type { KeyboardEvent } from "react";
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
  const moveWithKeyboard = (event: KeyboardEvent<HTMLButtonElement>, currentId: SpaceId) => {
    const currentIndex = spaces.findIndex((space) => space.id === currentId);
    if (currentIndex === -1) return;
    let targetIndex: number;
    switch (event.key) {
      case "ArrowDown":
      case "ArrowRight":
        targetIndex = (currentIndex + 1) % spaces.length;
        break;
      case "ArrowUp":
      case "ArrowLeft":
        targetIndex = (currentIndex - 1 + spaces.length) % spaces.length;
        break;
      case "Home":
        targetIndex = 0;
        break;
      case "End":
        targetIndex = spaces.length - 1;
        break;
      default:
        return;
    }
    event.preventDefault();
    const next = spaces[targetIndex];
    const rail = event.currentTarget.closest("[data-space-rail]");
    rail?.querySelector<HTMLButtonElement>(`button[data-space-id="${next.id}"]`)?.focus();
    onNavigate(next.id);
  };

  return (
    <nav className="space-rail" aria-label="主空间导航" data-space-rail>
      <ul className="space-rail-list">
        {spaces.map((s) => (
          <li key={s.id}>
            <button
              type="button"
              className="space-rail-item"
              aria-current={active === s.id ? "page" : undefined}
              aria-label={s.label}
              data-space-id={s.id}
              onClick={() => onNavigate(s.id)}
              onKeyDown={(event) => moveWithKeyboard(event, s.id)}
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
