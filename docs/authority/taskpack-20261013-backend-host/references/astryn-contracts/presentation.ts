/**
 * 多形态呈现契约。声明全部目标形态，但只有 implementedInM0=true 的形态
 * 才算本轮交付；浏览器预览不等于原生悬浮窗或桌宠。
 */

export const ASTRYN_PRESENTATION_MODES = [
  'embedded',
  'panel',
  'floating',
  'pet',
  'voice-only'
] as const;
export type AstrynPresentationMode = (typeof ASTRYN_PRESENTATION_MODES)[number];

export type AstrynWindowRequirement = 'none' | 'browser-overlay' | 'native-window' | 'audio-only';

export interface AstrynPresentationModeSpec {
  readonly mode: AstrynPresentationMode;
  readonly label: string;
  readonly windowRequirement: AstrynWindowRequirement;
  readonly implementedInM0: boolean;
  readonly blockedBy: string | null;
}

export const ASTRYN_PRESENTATION_MODE_SPECS: readonly AstrynPresentationModeSpec[] = [
  { mode: 'embedded', label: '嵌入 AAOS 页面', windowRequirement: 'none', implementedInM0: true, blockedBy: null },
  { mode: 'panel', label: '侧栏角色与对话', windowRequirement: 'none', implementedInM0: true, blockedBy: null },
  { mode: 'floating', label: '独立悬浮角色窗口', windowRequirement: 'native-window', implementedInM0: false, blockedBy: '需要 Tauri 窗口与置顶/穿透能力，属 P2' },
  { mode: 'pet', label: '低干扰桌面宠物', windowRequirement: 'native-window', implementedInM0: false, blockedBy: '需要原生窗口、托盘与拖拽，属 P2' },
  { mode: 'voice-only', label: '仅语音与状态反馈', windowRequirement: 'audio-only', implementedInM0: false, blockedBy: '需要 AAOS ASR/TTS 服务，属 P2' }
];

export function modeSpec(mode: AstrynPresentationMode): AstrynPresentationModeSpec {
  const found = ASTRYN_PRESENTATION_MODE_SPECS.find((spec) => spec.mode === mode);
  if (!found) throw new Error(`unknown presentation mode: ${mode}`);
  return found;
}
