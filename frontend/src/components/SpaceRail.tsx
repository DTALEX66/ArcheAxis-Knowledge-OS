import { useRef } from "react";
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
  const listRef = useRef<HTMLUListElement>(null);

  function focusIndex(index: number) {
    const buttons = listRef.current?.querySelectorAll<HTMLButtonElement>(
      "button[data-space-id]",
    );
    if (!buttons || buttons.length === 0) return;
    const next = (index + buttons.length) % buttons.length;
    buttons[next]?.focus();
    const id = buttons[next]?.dataset.spaceId as SpaceId | undefined;
    if (id) onNavigate(id);
  }

  function onKeyDown(event: React.KeyboardEvent, index: number) {
    switch (event.key) {
      case "ArrowDown":
        event.preventDefault();
        focusIndex(index + 1);
        break;
      case "ArrowUp":
        event.preventDefault();
        focusIndex(index - 1);
        break;
      case "Home":
        event.preventDefault();
        focusIndex(0);
        break;
      case "End":
        event.preventDefault();
        focusIndex(spaces.length - 1);
        break;
      default:
        break;
    }
  }

  return (
    <nav className="space-rail" aria-label="主空间导航">
      <ul ref={listRef} className="space-rail-list" role="list">
        {spaces.map((space, index) => (
          <li key={space.id}>
            <button
              type="button"
              data-space-id={space.id}
              className="space-rail-item"
              aria-current={space.id === active ? "page" : undefined}
              onClick={() => onNavigate(space.id)}
              onKeyDown={(event) => onKeyDown(event, index)}
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
