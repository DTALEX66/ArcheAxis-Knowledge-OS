// Adapted from ASTRYN 3115378b src/avatar/xiaoqi-raster-renderer.ts.
// Nine static AI-generated state images; provenance and byte hashes: PROVENANCE.json.
import idle from './assets/idle.png';
import listening from './assets/listening.png';
import thinking from './assets/thinking.png';
import speaking from './assets/speaking.png';
import interrupted from './assets/interrupted.png';
import awaitingApproval from './assets/awaiting_approval.png';
import executing from './assets/executing.png';
import completed from './assets/completed.png';
import failed from './assets/failed.png';

export const xiaoqiImages = {idle, listening, thinking, speaking, interrupted,
  awaiting_approval: awaitingApproval, executing, completed, failed} as const;
export type XiaoqiState = keyof typeof xiaoqiImages;
export const xiaoqiStateLabels: Record<XiaoqiState, string> = {
  idle: '待命', listening: '聆听', thinking: '思考中', speaking: '表达中',
  interrupted: '已中断', awaiting_approval: '等待确认', executing: '执行中',
  completed: '已完成', failed: '失败',
};
