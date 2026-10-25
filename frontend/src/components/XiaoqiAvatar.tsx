import {useState, type CSSProperties} from 'react';
import {xiaoqiImages, xiaoqiStateLabels, type XiaoqiState} from '../companion/xiaoqiAssets';
import studioStates from '../companion/assets/xiaoqi-studio-states-v2.png';
import './XiaoqiAvatar.css';

export type XiaoqiPresentation = 'avatar' | 'portrait' | 'figure';

interface XiaoqiAvatarProps {
  state?: XiaoqiState;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
  onInteract?: () => void;
  presentation?: XiaoqiPresentation;
}

/** AAOS state presentation only; static frames do not imply speech or a second AI runtime. */
export function XiaoqiAvatar({
  state = 'idle',
  size = 'md',
  className = '',
  onInteract,
  presentation = 'avatar'
}: XiaoqiAvatarProps) {
  const [failedSources, setFailedSources] = useState<Set<string>>(() => new Set());
  const studio = !failedSources.has(studioStates);
  const src = studio ? studioStates : xiaoqiImages[state];
  const stateIndex = ['idle', 'listening', 'thinking', 'speaking', 'interrupted', 'awaiting_approval', 'executing', 'completed', 'failed'].indexOf(state);
  const onImageError = () => setFailedSources(previous => new Set([...previous, src]));
  const label = `小栖：${xiaoqiStateLabels[state]}`;
  const pixels = {sm: 48, md: 64, lg: 96}[size];
  const raster = <img key={src} src={src} alt={onInteract ? '' : label} width={studio ? 1024 : 1696} height={studio ? 1536 : 2528}
    draggable={false} onError={onImageError}/>;
  const picture = failedSources.has(src)
    ? <span role="img" aria-label={`${label}，图像暂不可用`}>{xiaoqiStateLabels[state]}</span>
    : studio ? <span className="xiaoqi-sheet-cell">{raster}</span> : raster;
  const style = {'--xiaoqi-avatar-size': `${pixels}px`, '--xiaoqi-sheet-col': stateIndex % 3,
    '--xiaoqi-sheet-row': Math.floor(stateIndex / 3)} as CSSProperties;
  return onInteract
    ? <button type="button" className={`xiaoqi-avatar ${className}`} aria-label={`与小栖互动：${xiaoqiStateLabels[state]}`}
        data-visible-state={state} data-presentation={presentation} data-media="raster-2d-still" data-art={studio ? 'studio-v2' : 'original'} style={style} onClick={onInteract}>{picture}</button>
    : <span className={`xiaoqi-avatar ${className}`} data-visible-state={state} data-presentation={presentation} data-media="raster-2d-still" data-art={studio ? 'studio-v2' : 'original'} style={style}>{picture}</span>;
}
