import { useState } from 'react';
import { XiaoqiAvatar } from './XiaoqiAvatar';
import type { XiaoqiState } from '../assets/index';
import './XiaoqiPanel.css';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

interface XiaoqiPanelProps {
  isOpen: boolean;
  onClose: () => void;
  currentContext?: string;
}

export function XiaoqiPanel({ isOpen, onClose, currentContext }: XiaoqiPanelProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [xiaoqiState, setXiaoqiState] = useState<XiaoqiState>('idle');

  const handleSend = async () => {
    if (!input.trim()) return;

    const userMessage: Message = {
      role: 'user',
      content: input,
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setXiaoqiState('thinking');

    // TODO: 实际调用AI接口
    setTimeout(() => {
      const assistantMessage: Message = {
        role: 'assistant',
        content: '这是小栖的回复示例。实际回复将通过AI接口获取。',
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, assistantMessage]);
      setXiaoqiState('idle');
    }, 1500);
  };

  if (!isOpen) return null;

  return (
    <div className="xiaoqi-panel">
      <div className="xiaoqi-panel-header">
        <div className="xiaoqi-header-left">
          <XiaoqiAvatar state={xiaoqiState} size="sm" />
          <div>
            <h3>小栖</h3>
            {currentContext && (
              <p className="xiaoqi-context">当前上下文：{currentContext}</p>
            )}
          </div>
        </div>
        <button
          className="xiaoqi-close-btn"
          onClick={onClose}
          aria-label="关闭小栖面板"
        >
          ×
        </button>
      </div>

      <div className="xiaoqi-messages">
        {messages.length === 0 ? (
          <div className="xiaoqi-welcome">
            <p>你好！我是小栖，你的AI知识助手。</p>
            <p>有什么我可以帮助你的吗？</p>
          </div>
        ) : (
          messages.map((msg, idx) => (
            <div
              key={idx}
              className={`xiaoqi-message ${msg.role === 'user' ? 'user' : 'assistant'}`}
            >
              {msg.role === 'assistant' && (
                <XiaoqiAvatar state="idle" size="sm" />
              )}
              <div className="message-content">
                <p>{msg.content}</p>
                <span className="message-time">
                  {msg.timestamp.toLocaleTimeString('zh-CN', {
                    hour: '2-digit',
                    minute: '2-digit'
                  })}
                </span>
              </div>
            </div>
          ))
        )}
      </div>

      <div className="xiaoqi-input-area">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyPress={(e) => e.key === 'Enter' && handleSend()}
          placeholder="向小栖提问..."
          className="xiaoqi-input"
        />
        <button
          onClick={handleSend}
          disabled={!input.trim()}
          className="xiaoqi-send-btn"
        >
          发送
        </button>
      </div>
    </div>
  );
}
