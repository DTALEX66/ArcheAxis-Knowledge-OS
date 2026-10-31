import {
  AudioLines, BookOpen, Bot, BrainCircuit, CalendarCheck, Download, Files, FileText, FileUp,
  FlaskConical, GraduationCap, Grid2X2, House, LayoutDashboard, LockKeyhole,
  Network, Orbit, PanelsTopLeft, Puzzle, Route, Search, Settings, SquarePen, Waypoints, X,
} from "lucide-react";
import licenseUrl from "./lucide-NOTICE.txt?url";

// Preserve the public AAOS icon names while using one standard SVG family.
const icons = {
  Home: House, ImportDocument: FileUp, Write: SquarePen, Lock: LockKeyhole,
  Workspace: LayoutDashboard, Source: FileText, Import: Download,
  Knowledge: BookOpen, Evidence: Files, Review: CalendarCheck, HumanAi: Bot,
  Connection: Network, Settings, Search, Close: X, Apps: Grid2X2,
  Research: FlaskConical, Learning: GraduationCap, Extension: Puzzle,
  Voice: AudioLines, Spatial: Orbit, Workflow: Waypoints,
  LearningPath: Route, Canvas: PanelsTopLeft, Context: BrainCircuit,
} as const;
export type AaosIconName = keyof typeof icons;
export function AaosIcon({ name, size = 20 }: { name: AaosIconName; size?: number }) {
  const Icon = icons[name];
  return <Icon size={size} strokeWidth={1.7} aria-hidden="true" focusable="false"
    data-aaos-icon={name} data-icon-license={licenseUrl} />;
}
