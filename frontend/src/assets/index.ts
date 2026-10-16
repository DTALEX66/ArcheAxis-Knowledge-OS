export const BRAND_ASSETS = {
  logo: {
    white: '/src/assets/brand/archeaxis-logo-white.svg',
    mark: '/src/assets/brand/archeaxis-mark.svg',
  },
  xiaoqi: {
    idle: '/src/assets/xiaoqi/idle.png',
    thinking: '/src/assets/xiaoqi/thinking.png',
    speaking: '/src/assets/xiaoqi/speaking.png',
    listening: '/src/assets/xiaoqi/listening.png',
    completed: '/src/assets/xiaoqi/completed.png',
  },
} as const;

export type XiaoqiState = 'idle' | 'thinking' | 'speaking' | 'listening' | 'completed';
