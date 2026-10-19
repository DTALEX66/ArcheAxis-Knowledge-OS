import {xiaoqiImages} from '../companion/xiaoqiAssets';
export const BRAND_ASSETS = {
  logo: {
    white: '/src/assets/brand/archeaxis-logo-white.svg',
    mark: '/src/assets/brand/archeaxis-mark.svg',
  },
  xiaoqi: xiaoqiImages,
} as const;

export type {XiaoqiState} from '../companion/xiaoqiAssets';
