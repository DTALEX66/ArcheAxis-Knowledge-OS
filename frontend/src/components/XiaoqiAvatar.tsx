import { useState } from 'react';
import type { XiaoqiState } from '../assets/index';

interface XiaoqiAvatarProps {
  state?: XiaoqiState;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
  onInteract?: () => void;
}

const stateImages: Record<XiaoqiState, string> = {
  idle: '/src/assets/xiaoqi/idle.png',
  thinking: '/src/assets/xiaoqi/thinking.png',
  speaking: '/src/assets/xiaoqi/speaking.png',
  listening: '/src/assets/xiaoqi/idle.png',
  completed: '/src/assets/xiaoqi/idle.png',
};

const sizeClasses = {
  sm: 'w-12 h-12',
  md: 'w-16 h-16',
  lg: 'w-24 h-24',
};

export function XiaoqiAvatar({
  state = 'idle',
  size = 'md',
  className = '',
  onInteract
}: XiaoqiAvatarProps) {
  const [isHovered, setIsHovered] = useState(false);

  return (
    <div
      className={`xiaoqi-avatar ${sizeClasses[size]} ${className}`}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      onClick={onInteract}
      role={onInteract ? 'button' : 'img'}
      aria-label="小栖 AI助手"
    >
      <img
        src={stateImages[state]}
        alt={`小栖 - ${state}`}
        className="w-full h-full object-cover rounded-full"
        style={{
          transition: 'transform 200ms ease-out',
          transform: isHovered ? 'scale(1.05)' : 'scale(1)',
        }}
      />
      {state === 'thinking' && (
        <div className="xiaoqi-thinking-indicator">
          <span className="dot"></span>
          <span className="dot"></span>
          <span className="dot"></span>
        </div>
      )}
    </div>
  );
}
