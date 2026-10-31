/** Local display preferences only. This never changes a session or a Core object. */
export type CharacterPresentation = 'avatar' | 'portrait' | 'figure';
export const CHARACTER_PRESENTATION_EVENT = 'aaos:companion-presentation';
const PREFIX = 'aaos.companion.presentation.v1';

export function isCharacterPresentation(value: unknown): value is CharacterPresentation {
  return value === 'avatar' || value === 'portrait' || value === 'figure';
}

function preferenceKey(workspaceId?: string) {
  return `${PREFIX}:${encodeURIComponent(workspaceId || 'local-device')}`;
}

export function readCharacterPresentation(workspaceId?: string): CharacterPresentation | null {
  try {
    const value = localStorage.getItem(preferenceKey(workspaceId));
    return isCharacterPresentation(value) ? value : null;
  } catch {
    return null;
  }
}

export function rememberCharacterPresentation(value: CharacterPresentation, workspaceId?: string) {
  try { localStorage.setItem(preferenceKey(workspaceId), value); }
  catch { /* The selected view still works when WebView storage is unavailable. */ }
}
