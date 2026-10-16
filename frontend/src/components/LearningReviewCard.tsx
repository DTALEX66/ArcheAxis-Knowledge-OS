import { useState } from 'react';
import { XiaoqiAvatar } from './XiaoqiAvatar';
import '../styles/learning-review.css';

interface ReviewCard {
  id: string;
  question: string;
  answer: string;
  hint?: string;
  context?: string;
}

interface LearningReviewCardProps {
  card: ReviewCard;
  currentIndex: number;
  totalCards: number;
  onRate: (difficulty: 'hard' | 'good' | 'easy') => void;
  onNext: () => void;
}

export function LearningReviewCard({
  card,
  currentIndex,
  totalCards,
  onRate,
  onNext
}: LearningReviewCardProps) {
  const [isFlipped, setIsFlipped] = useState(false);
  const [showXiaoqiTip, setShowXiaoqiTip] = useState(true);

  const handleShowAnswer = () => {
    setIsFlipped(true);
    setShowXiaoqiTip(false);
  };

  const handleRate = (difficulty: 'hard' | 'good' | 'easy') => {
    onRate(difficulty);
    setIsFlipped(false);
    setTimeout(() => {
      onNext();
      setShowXiaoqiTip(true);
    }, 300);
  };

  return (
    <div className="learning-review-container">
      {/* Context Bar */}
      {card.context && (
        <div className="learning-context-bar">
          <div className="learning-context-icon">📄</div>
          <div className="learning-context-text">
            <strong>当前上下文</strong>
            <span>{card.context}</span>
          </div>
        </div>
      )}

      {/* Review Card */}
      <div className={`review-card ${isFlipped ? 'flipped' : ''}`}>
        <div className="review-card-inner">
          {/* Front */}
          <div className="review-card-face review-card-front">
            <div className="review-card-header">
              <span className="review-card-label">问题</span>
              <span className="review-card-progress">
                {currentIndex + 1} / {totalCards}
              </span>
            </div>
            <div className="review-card-content">
              <div className="review-card-question">{card.question}</div>
            </div>
            {card.hint && (
              <div className="review-card-hint">
                💡 提示：{card.hint}
              </div>
            )}
          </div>

          {/* Back */}
          <div className="review-card-face review-card-back">
            <div className="review-card-header">
              <span className="review-card-label">答案</span>
              <span className="review-card-progress">
                {currentIndex + 1} / {totalCards}
              </span>
            </div>
            <div className="review-card-content">
              <div className="review-card-answer">{card.answer}</div>
            </div>
          </div>
        </div>
      </div>

      {/* Actions */}
      <div className="review-actions">
        {!isFlipped ? (
          <button
            className="review-action-btn show-answer"
            onClick={handleShowAnswer}
          >
            显示答案
          </button>
        ) : (
          <>
            <button
              className="review-action-btn rate rate-hard"
              onClick={() => handleRate('hard')}
            >
              困难
            </button>
            <button
              className="review-action-btn rate rate-good"
              onClick={() => handleRate('good')}
            >
              一般
            </button>
            <button
              className="review-action-btn rate rate-easy"
              onClick={() => handleRate('easy')}
            >
              简单
            </button>
          </>
        )}
      </div>

      {/* Xiaoqi Helper */}
      {showXiaoqiTip && !isFlipped && (
        <div className="learning-xiaoqi-helper">
          <div className="xiaoqi-speech-bubble">
            <p>先回忆要点，想不起来可以查看提示哦~</p>
          </div>
          <XiaoqiAvatar state="idle" size="lg" />
        </div>
      )}
    </div>
  );
}
