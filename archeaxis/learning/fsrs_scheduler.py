"""
FSRS (Free Spaced Repetition Scheduler) Implementation
基于FSRS-5算法的学习调度器
"""
from datetime import datetime, timedelta
from typing import Optional
from enum import Enum


class Rating(Enum):
    """复习评分"""
    AGAIN = 1  # 完全忘记
    HARD = 2   # 困难
    GOOD = 3   # 良好
    EASY = 4   # 简单


class Card:
    """学习卡片状态"""
    def __init__(self):
        self.stability: float = 0.0  # 记忆稳定性
        self.difficulty: float = 0.0  # 难度
        self.elapsed_days: int = 0   # 已过天数
        self.scheduled_days: int = 0  # 计划间隔天数
        self.reps: int = 0           # 复习次数
        self.lapses: int = 0         # 遗忘次数
        self.last_review: Optional[datetime] = None
        self.due: Optional[datetime] = None


class FSRSScheduler:
    """FSRS调度器"""

    def __init__(self):
        # FSRS-5 默认参数
        self.w = [
            0.40255, 1.18385, 3.173, 15.69105, 7.1949,
            0.5345, 1.4604, 0.0046, 1.54575, 0.1192,
            1.01925, 1.9395, 0.11, 0.29605, 2.2698,
            0.2315, 2.9898, 0.51655, 0.6621
        ]
        self.request_retention = 0.9  # 目标记忆保持率
        self.maximum_interval = 36500  # 最大间隔天数
        self.enable_fuzz = True  # 启用随机化

    def init_card(self) -> Card:
        """初始化新卡片"""
        card = Card()
        card.difficulty = self.w[4]
        card.stability = self.w[0]
        return card

    def next_interval(self, card: Card, rating: Rating) -> int:
        """计算下次复习间隔"""
        if card.reps == 0:
            # 新卡片的间隔
            intervals = {
                Rating.AGAIN: 1,
                Rating.HARD: 5,
                Rating.GOOD: 10,
                Rating.EASY: 30
            }
            return intervals.get(rating, 1)

        # 使用FSRS公式计算
        new_stability = self._calculate_stability(card, rating)
        interval = self._stability_to_interval(new_stability)

        return min(interval, self.maximum_interval)

    def _calculate_stability(self, card: Card, rating: Rating) -> float:
        """计算新的记忆稳定性"""
        if rating == Rating.AGAIN:
            # 遗忘后的稳定性
            new_s = (
                self.w[11] *
                pow(card.difficulty, -self.w[12]) *
                (pow(card.stability + 1, self.w[13]) - 1) *
                pow(2.718281828, self.w[14] * (1 - self._get_retrievability(card)))
            )
            return max(0.1, new_s)
        else:
            # 成功复习后的稳定性
            hard_penalty = 1.0 if rating == Rating.HARD else 1.0
            easy_bonus = 1.3 if rating == Rating.EASY else 1.0

            new_s = (
                card.stability *
                (1 +
                 pow(2.718281828, self.w[8]) *
                 (11 - card.difficulty) *
                 pow(card.stability, -self.w[9]) *
                 (pow(2.718281828, self.w[10] * (1 - self._get_retrievability(card))) - 1)) *
                hard_penalty * easy_bonus
            )
            return new_s

    def _get_retrievability(self, card: Card) -> float:
        """计算当前可提取性（记忆强度）"""
        if card.elapsed_days == 0:
            return 1.0
        return pow(
            1 + card.elapsed_days / (9 * card.stability),
            -1
        )

    def _stability_to_interval(self, stability: float) -> int:
        """将稳定性转换为间隔天数"""
        interval = stability / self.w[17] * (
            pow(self.request_retention, 1 / self.w[18]) - 1
        )
        return max(1, round(interval))

    def review_card(self, card: Card, rating: Rating, now: datetime) -> Card:
        """复习卡片并更新状态"""
        # 计算经过的天数
        if card.last_review:
            card.elapsed_days = (now - card.last_review).days
        else:
            card.elapsed_days = 0

        # 更新难度
        if rating == Rating.AGAIN:
            card.difficulty = min(10, card.difficulty + 1)
            card.lapses += 1
        elif rating == Rating.EASY:
            card.difficulty = max(1, card.difficulty - 0.5)

        # 计算新的稳定性和间隔
        card.stability = self._calculate_stability(card, rating)
        interval_days = self.next_interval(card, rating)

        # 更新卡片状态
        card.scheduled_days = interval_days
        card.last_review = now
        card.due = now + timedelta(days=interval_days)
        card.reps += 1

        return card


# 使用示例
if __name__ == "__main__":
    scheduler = FSRSScheduler()
    card = scheduler.init_card()

    # 第一次复习 - 良好
    now = datetime.now()
    card = scheduler.review_card(card, Rating.GOOD, now)
    print(f"第1次复习后，下次间隔: {card.scheduled_days}天")

    # 第二次复习 - 简单
    now += timedelta(days=card.scheduled_days)
    card = scheduler.review_card(card, Rating.EASY, now)
    print(f"第2次复习后，下次间隔: {card.scheduled_days}天")

    # 第三次复习 - 遗忘
    now += timedelta(days=card.scheduled_days)
    card = scheduler.review_card(card, Rating.AGAIN, now)
    print(f"第3次复习后(遗忘)，下次间隔: {card.scheduled_days}天")
