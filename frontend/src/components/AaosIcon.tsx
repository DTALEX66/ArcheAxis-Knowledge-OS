// Geometry reused verbatim from apps/ArcheAxis.Desktop/AaosIcon.axaml.cs.
// The established AAOS VI uses a 24-unit viewBox and 1.7-unit strokes.
const paths = {
  "Workspace": "M3,4 L10,4 L10,10 L3,10 Z M14,4 L21,4 L21,10 L14,10 Z M3,14 L10,14 L10,20 L3,20 Z M14,14 L21,14 L21,20 L14,20 Z M10,7 L14,7 M6.5,10 L6.5,14 M17.5,10 L17.5,14 M10,17 L14,17",
  "Source": "M4,3 L15,3 L20,8 L20,21 L4,21 Z M15,3 L15,8 L20,8 M8,12 L16,12 M8,16 L16,16",
  "Import": "M12,3 L12,15 M7,10 L12,15 L17,10 M4,17 L4,21 L20,21 L20,17",
  "Knowledge": "M2,4 C5,3 9,4 12,6 C15,4 19,3 22,4 L22,20 C18,18 15,19 12,21 C9,19 6,18 2,20 Z M12,6 L12,21",
  "Evidence": "M5,2 L15,2 L20,7 L20,22 L5,22 Z M15,2 L15,7 L20,7 M8,12 L17,12 M8,16 L17,16",
  "Review": "M5,3 L19,3 L21,6 L21,21 L3,21 L3,6 Z M8,3 L8,7 M16,3 L16,7 M3,10 L21,10 M7,15 L10,18 L16,13",
  "HumanAi": "M8,11 A4,4 0 1,1 8,3 A4,4 0 1,1 8,11 M1,21 C1,17 4,14 8,14 C12,14 15,17 15,21 M17,12 A3,3 0 1,0 17,6 M17,15 C20,15 22,17 22,20",
  "Connection": "M12,4 L6,16 M12,4 L18,16 M6,18 L18,18 M12,2 A2,2 0 1,1 12,6 A2,2 0 1,1 12,2 M6,16 A2,2 0 1,1 6,20 A2,2 0 1,1 6,16 M18,16 A2,2 0 1,1 18,20 A2,2 0 1,1 18,16",
  "Settings": "M12,2 L13.5,5.2 L17,4.5 L18,8 L21.5,9.5 L20,13 L21.5,16.5 L18,18 L17,21.5 L13.5,20 L12,22 L10.5,20 L7,21.5 L6,18 L2.5,16.5 L4,13 L2.5,9.5 L6,8 L7,4.5 L10.5,5.2 Z M12,9 A4,4 0 1,0 12,17 A4,4 0 1,0 12,9"
} as const;

export type AaosIconName = keyof typeof paths;

export function AaosIcon({ name, size = 20 }: { name: AaosIconName; size?: number }) {
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none"
    stroke="currentColor" strokeWidth={1.7} strokeLinecap="round" strokeLinejoin="round"
    aria-hidden="true" focusable="false" data-aaos-icon={name}>
    <path d={paths[name]} />
  </svg>;
}
