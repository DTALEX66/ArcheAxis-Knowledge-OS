"""
Learning API endpoints for FSRS-based spaced repetition
"""
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from archeaxis.learning.fsrs_scheduler import FSRSScheduler, Rating, Card


router = APIRouter(prefix="/api/v1/learning", tags=["learning"])
scheduler = FSRSScheduler()


class ReviewRequest(BaseModel):
    card_id: str
    rating: int  # 1=again, 2=hard, 3=good, 4=easy


class ReviewResponse(BaseModel):
    card_id: str
    next_interval_days: int
    next_due: str
    stability: float
    difficulty: float


class CardState(BaseModel):
    card_id: str
    stability: float
    difficulty: float
    elapsed_days: int
    scheduled_days: int
    reps: int
    lapses: int
    last_review: Optional[str]
    due: Optional[str]


# 临时内存存储（生产环境应使用数据库）
cards_db = {}


@router.post("/cards/{card_id}/review", response_model=ReviewResponse)
async def review_card(card_id: str, request: ReviewRequest):
    """
    复习一张卡片并获取下次复习时间
    """
    # 验证评分
    try:
        rating = Rating(request.rating)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid rating: {request.rating}. Must be 1-4."
        )

    # 获取或创建卡片
    if card_id not in cards_db:
        card = scheduler.init_card()
        cards_db[card_id] = card
    else:
        card = cards_db[card_id]

    # 执行复习
    now = datetime.now()
    card = scheduler.review_card(card, rating, now)
    cards_db[card_id] = card

    return ReviewResponse(
        card_id=card_id,
        next_interval_days=card.scheduled_days,
        next_due=card.due.isoformat() if card.due else None,
        stability=card.stability,
        difficulty=card.difficulty
    )


@router.get("/cards/{card_id}", response_model=CardState)
async def get_card_state(card_id: str):
    """
    获取卡片当前状态
    """
    if card_id not in cards_db:
        raise HTTPException(status_code=404, detail="Card not found")

    card = cards_db[card_id]
    return CardState(
        card_id=card_id,
        stability=card.stability,
        difficulty=card.difficulty,
        elapsed_days=card.elapsed_days,
        scheduled_days=card.scheduled_days,
        reps=card.reps,
        lapses=card.lapses,
        last_review=card.last_review.isoformat() if card.last_review else None,
        due=card.due.isoformat() if card.due else None
    )


@router.get("/cards/due", response_model=List[str])
async def get_due_cards(limit: int = 20):
    """
    获取到期需要复习的卡片列表
    """
    now = datetime.now()
    due_cards = [
        card_id
        for card_id, card in cards_db.items()
        if card.due and card.due <= now
    ]
    return due_cards[:limit]


@router.post("/cards", response_model=CardState)
async def create_card(card_id: str):
    """
    创建新的学习卡片
    """
    if card_id in cards_db:
        raise HTTPException(status_code=400, detail="Card already exists")

    card = scheduler.init_card()
    cards_db[card_id] = card

    return CardState(
        card_id=card_id,
        stability=card.stability,
        difficulty=card.difficulty,
        elapsed_days=card.elapsed_days,
        scheduled_days=card.scheduled_days,
        reps=card.reps,
        lapses=card.lapses,
        last_review=None,
        due=None
    )


@router.get("/stats")
async def get_learning_stats():
    """
    获取学习统计数据
    """
    now = datetime.now()

    total_cards = len(cards_db)
    due_count = sum(1 for card in cards_db.values() if card.due and card.due <= now)
    reviewed_count = sum(1 for card in cards_db.values() if card.reps > 0)

    return {
        "total_cards": total_cards,
        "due_today": due_count,
        "reviewed_cards": reviewed_count,
        "new_cards": total_cards - reviewed_count
    }
