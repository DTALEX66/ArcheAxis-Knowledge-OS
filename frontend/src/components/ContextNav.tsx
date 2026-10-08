import { AaosIcon } from "./AaosIcon";
import { RELATED } from "../spaces/related";
import { SPACES, spaceDescription, type SpaceId } from "../spaces/spaces";
import type { SpaceSectionDef } from "../presentation/spaceSections";

export function ContextNav({
  active,
  onNavigate,
  sections,
  activeSection,
  onSection,
}: {
  active: SpaceId;
  onNavigate: (id: SpaceId) => void;
  sections: readonly SpaceSectionDef[];
  activeSection?: string;
  onSection?: (section: SpaceSectionDef) => void;
}) {
  const current = SPACES.find((space) => space.id === active) ?? SPACES[0];
  return (
    <nav className="context-subnav" aria-label="当前空间导航">
      <header role="presentation">
        <span>当前空间</span>
        <h2>{current.label}</h2>
        <p>{spaceDescription(current)}</p>
      </header>
      <div className="space-section-group" role="group" aria-labelledby="space-section-heading">
        <h3 id="space-section-heading">对象分组</h3>
        <ul aria-label={`${current.label}对象导航`}>
          {sections.map((section) => (
            <li key={section.id}>
              {section.state === "ready" ? (
                <button
                  type="button"
                  className="space-section-button"
                  aria-current={activeSection === section.id ? "location" : undefined}
                  onClick={() => onSection?.(section)}
                >
                  <b>{section.label}</b>
                  <small>{section.goto ? `转到 ${SPACES.find((space) => space.id === section.goto!.space)?.label ?? section.goto.section}` : section.description}</small>
                </button>
              ) : (
                <div className="space-section-todo">
                  <b>{section.label}<span className="space-section-badge">待开发</span></b>
                  <small>{section.reason}</small>
                </div>
              )}
            </li>
          ))}
        </ul>
      </div>
      <ul aria-label="相关空间">
        {RELATED[active].filter((id) => id !== active).map((id) => {
          const space = SPACES.find((item) => item.id === id)!;
          return (
            <li key={id}>
              <button
                type="button"
                onClick={() => onNavigate(id)}
              >
                <span aria-hidden="true" style={{ width: 18, opacity: 0.7 }}><AaosIcon name={space.icon} /></span>
                <span>
                  <b>{space.label}</b>
                  <small>{spaceDescription(space)}</small>
                </span>
              </button>
            </li>
          );
        })}
      </ul>
      <footer>待开发项只显示缺少的合同，不提供假入口</footer>
    </nav>
  );
}
