import {useState} from 'react';
import {xiaoqiImages, xiaoqiStateLabels, type XiaoqiState} from '../companion/xiaoqiAssets';

interface XiaoqiAvatarProps {
  state?: XiaoqiState;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
  onInteract?: () => void;
}

/** AAOS state presentation only; static frames do not imply speech or a second AI runtime. */
export function XiaoqiAvatar({
  state = 'idle',
  size = 'md',
  className = '',
  onInteract
}: XiaoqiAvatarProps) {
  const [failedSource, setFailedSource] = useState<string | null>(null);
  const src = xiaoqiImages[state];
  const label = `小栖：${xiaoqiStateLabels[state]}`;
  const pixels = {sm: 48, md: 64, lg: 96}[size];
  const picture = failedSource === src
    ? <span role="img" aria-label={`${label}，图像暂不可用`}>{xiaoqiStateLabels[state]}</span>
    : <img key={src} src={src} alt={onInteract ? '' : label} width={pixels} height={pixels}
        style={{objectFit: 'contain'}} onError={() => setFailedSource(src)}/>;
  return onInteract
    ? <button type="button" className={`xiaoqi-avatar ${className}`} aria-label={`与小栖互动：${xiaoqiStateLabels[state]}`}
        data-visible-state={state} data-media="raster-2d-still" onClick={onInteract}>{picture}</button>
    : <span className={`xiaoqi-avatar ${className}`} data-visible-state={state} data-media="raster-2d-still">{picture}</span>;
}
