import { ASTRYN_CONVERSATION_STATES, ASTRYN_TASK_STATES } from '@astryn/contracts';
import type { AstrynAvatarFrame, AstrynAvatarRenderer, AstrynAvatarViewProfile, AstrynVisibleState } from '@astryn/contracts';

import idleImage from '../../assets/character/upgraded/v1/xiaoqi_state_idle_sleepwear_v1.png';
import listeningImage from '../../assets/character/upgraded/v1/xiaoqi_state_listening_sleepwear_v1.png';
import speakingImage from '../../assets/character/upgraded/v1/xiaoqi_state_speaking_sleepwear_v1.png';
import interruptedImage from '../../assets/character/upgraded/v1/xiaoqi_state_interrupted_sleepwear_v1.png';
import awaitingApprovalImage from '../../assets/character/upgraded/v1/xiaoqi_state_awaiting_approval_sleepwear_v1.png';
import executingImage from '../../assets/character/upgraded/v1/xiaoqi_state_executing_sleepwear_v1.png';
// thinking/completed/failed 三张由本地派生去背（derived-alpha）：来源与算法登记在
// assets/character/STATE-ASSET-INDEX.json 的 derived 节，属显式标注的过渡件。
import thinkingImage from '../../assets/character/upgraded/v1/derived-alpha/xiaoqi_state_thinking_sleepwear_v1.png';
import completedImage from '../../assets/character/upgraded/v1/derived-alpha/xiaoqi_state_completed_sleepwear_v1.png';
import failedImage from '../../assets/character/upgraded/v1/derived-alpha/xiaoqi_state_failed_sleepwear_v1.png';

const SUPPORTED: readonly AstrynVisibleState[] = [
  ...ASTRYN_CONVERSATION_STATES,
  ...ASTRYN_TASK_STATES.filter((state) => state !== 'none')
];

/** 九态 → 交付位图（GF03 v2）。键集合与契约九态一致：少一态在测试中变红。 */
const STATE_IMAGES: Readonly<Record<AstrynVisibleState, string>> = {
  idle: idleImage,
  listening: listeningImage,
  thinking: thinkingImage,
  speaking: speakingImage,
  interrupted: interruptedImage,
  awaiting_approval: awaitingApprovalImage,
  executing: executingImage,
  completed: completedImage,
  failed: failedImage
};

export interface XiaoqiRasterProps {
  readonly frame: AstrynAvatarFrame;
  readonly size?: number | undefined;
  /** 呈现档只映射宽度（各槽位尺寸令牌链）；方形/圆形裁切由呈现层的 CSS 负责（见 astryn.css 的 [data-avatar-view="avatar"] 规则）。 */
  readonly view?: AstrynAvatarViewProfile | undefined;
}

/**
 * 小栖 v2 渲染驱动：MINIMAX DESIGN 交付的九态位图（外部 AI 生产，平台条款授权）。
 * 静帧驱动：无口型帧、无环境动画，reducedMotion 天然满足。
 *
 * 不变量：写入 DOM 的字符串只由内部常量、构建期资源 URL 与数值拼装，
 * 任何外部文本（模型正文、宿主摘要、文件名）都不得进入这里。
 */
export function XiaoqiRasterImage({ frame, size, view }: XiaoqiRasterProps): string {
  // 未登记的可见状态直接抛错：绝不把 undefined 拼进 src 产出坏图（回退由上层 AvatarView 负责）。
  if (!(frame.visibleState in STATE_IMAGES)) {
    throw new Error(`未登记的可见状态：${String(frame.visibleState)}`);
  }
  const src = STATE_IMAGES[frame.visibleState];
  const width = size ?? view?.width ?? 240;
  return `<img data-testid="astryn-avatar" data-visible-state="${frame.visibleState}" data-motion="off"
     src="${src}" width="${width}" alt="小栖当前状态：${frame.visibleState}" />`;
}

export const xiaoqiRasterRenderer: AstrynAvatarRenderer = {
  rendererId: 'xiaoqi-raster-v2',
  displayName: '小栖 · 九态位图（AI 生成）',
  provenance: {
    origin: 'ai-generated',
    license: 'MINIMAX DESIGN 平台条款（生成并交付使用）；逐文件来源、哈希与派生链登记于 assets/character/STATE-ASSET-INDEX.json',
    note: '外部 AI 生产位图，非原创手绘；thinking/completed/failed 为本地派生去背（derived-alpha）；未使用真人参考素材；生成种子/参数未暴露（已知缺口）。'
  },
  budget: { compositedOnly: true, respectReducedMotion: true, maxAmbientAnimations: 0 },
  supportedStates: SUPPORTED,
  supports: (state) => state in STATE_IMAGES,
  renderMarkup: (frame, size, view) => XiaoqiRasterImage({ frame, size, view }),
  createFrame: (): AstrynAvatarFrame => ({
    characterId: 'xiaoqi',
    sessionId: '',
    visibleState: 'idle',
    expressionFrame: 0,
    streamedText: '',
    taskStep: null,
    failureMessage: null,
    reducedMotion: false
  }),
  describe: (frame) => ({
    visibleState: frame.visibleState,
    media: 'raster-2d-still',
    expressionDriver: 'state-still-image',
    image: STATE_IMAGES[frame.visibleState],
    motion: false
  })
};

export function renderXiaoqiRasterMarkup(frame: AstrynAvatarFrame, size?: number, view?: AstrynAvatarViewProfile): string {
  return XiaoqiRasterImage({ frame, size, view });
}
