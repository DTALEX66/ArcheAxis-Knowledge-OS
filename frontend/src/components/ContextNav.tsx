import { AaosIcon } from "./AaosIcon";
import { RELATED } from "../spaces/related";
import { SPACES, spaceDescription, type SpaceId } from "../spaces/spaces";

export type LibrarySection = "sources" | "documents" | "anchors" | "versions";
export const LIBRARY_SECTIONS: { id: LibrarySection; label: string }[] = [
  { id: "sources", label: "来源原件" }, { id: "documents", label: "已保存文档" },
  { id: "anchors", label: "来源锚点" }, { id: "versions", label: "文档版本" },
];

export function ContextNav({ active, onNavigate, librarySection, onLibrarySection }: { active: SpaceId; onNavigate: (id: SpaceId) => void; librarySection?: LibrarySection; onLibrarySection?: (section: LibrarySection) => void }) {
  const current = SPACES.find((space) => space.id === active) ?? SPACES[0];
  return (
    <nav className="context-subnav" aria-label="当前空间导航">
      <header role="presentation">
        <span>当前空间</span>
        <h2>{current.label}</h2>
        <p>{spaceDescription(current)}</p>
      </header>
      {active === "library" && onLibrarySection ? <ul aria-label="资料库对象导航">{LIBRARY_SECTIONS.map(section => <li key={section.id}><button type="button" aria-current={librarySection === section.id ? "location" : undefined} onClick={() => onLibrarySection(section.id)}>{section.label}</button></li>)}</ul> : null}
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
      <footer>只显示已接入的产品空间</footer>
    </nav>
  );
}
