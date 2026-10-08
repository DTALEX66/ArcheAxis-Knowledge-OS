// UI-02 tertiary level: the object path for what is actually open. Each level is a
// real navigation target, so the trail is a route, not a caption of one.
export type ObjectTrailLevel = {
  id: string;
  label: string;
  detail?: string;
  region?: string;
};

export function NavTrail({ levels, onJump }: { levels: readonly ObjectTrailLevel[]; onJump: (region: string) => void }) {
  if (levels.length === 0) return null;
  const lastIndex = levels.length - 1;
  return (
    <nav className="nav-trail" aria-label="对象导航路径">
      <ol className="nav-trail-list">
        {levels.map((level, index) => (
          <li className="nav-trail-item" key={level.id}>
            {index > 0 ? <span className="nav-trail-separator" aria-hidden="true">›</span> : null}
            {index < lastIndex && level.region ? (
              <button type="button" className="nav-trail-link" onClick={() => onJump(level.region as string)}>
                {level.label}
                {level.detail ? <small className="nav-trail-detail">{level.detail}</small> : null}
              </button>
            ) : (
              <span className="nav-trail-current" aria-current="location">
                {level.label}
                {level.detail ? <small className="nav-trail-detail">{level.detail}</small> : null}
              </span>
            )}
          </li>
        ))}
      </ol>
    </nav>
  );
}
