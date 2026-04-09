from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import Analysis

router = APIRouter(prefix="/analysis", tags=["Analysis"])


@router.get("/history")
def emotion_history(limit: int = 30, db: Session = Depends(get_db)):
    """감정 온도 히스토리 (최근 N일)"""
    records = (
        db.query(Analysis)
        .order_by(Analysis.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "journal_id": r.journal_id,
            "date": r.created_at.strftime("%Y-%m-%d"),
            "emotion_temperature": r.emotion_temperature,
            "primary_emotion": r.primary_emotion,
            "sentiment_score": r.sentiment_score,
        }
        for r in records
    ]


@router.get("/stats")
def emotion_stats(db: Session = Depends(get_db)):
    """전체 감정 통계"""
    records = db.query(Analysis).all()
    if not records:
        return {"message": "아직 분석된 일기가 없어요. 첫 번째 일기를 작성해 보세요!"}

    emotions = [r.primary_emotion for r in records]
    avg_temp = sum(r.emotion_temperature for r in records) / len(records)
    avg_sentiment = sum(r.sentiment_score for r in records) / len(records)

    emotion_count: dict[str, int] = {}
    for e in emotions:
        emotion_count[e] = emotion_count.get(e, 0) + 1

    most_common = max(emotion_count, key=emotion_count.get)

    return {
        "total_journals": len(records),
        "average_emotion_temperature": round(avg_temp, 1),
        "average_sentiment_score": round(avg_sentiment, 2),
        "most_frequent_emotion": most_common,
        "emotion_distribution": emotion_count,
    }
