// AXW-UI-804: accessible placeholder shared by the six spaces.
export function SpacePlaceholder({
  title,
  description,
  hint,
}: {
  title: string;
  description: string;
  hint?: string;
}) {
  return (
    <section className="space-view" aria-labelledby={`space-${title}`}>
      <h2 id={`space-${title}`} className="space-title">
        {title}
      </h2>
      <p className="space-description">{description}</p>
      {hint ? <p className="space-hint">{hint}</p> : null}
    </section>
  );
}
