from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime

from database import get_db
from models import Journal, Analysis
from schemas import JournalCreate, JournalResponse, JournalWithAnalysis
from sentiment import get_analyzer
from counselor import counsel

router = APIRouter(prefix="/journals", tags=["Journals"])


@router.post("/", response_model=dict, status_code=status.HTTP_201_CREATED)
def create_journal(payload: JournalCreate, db: Session = Depends(get_db)):
    """일기 작성 + 즉시 감정 분석"""
    # 1. 일기 저장
    journal = Journal(content=payload.content)
    db.add(journal)
    db.flush()

    # 2. 감정 분석
    analyzer = get_analyzer()
    sentiment = analyzer.analyze(payload.content)

    # 3. 상담 결과 생성
    from counselor import counsel
    result = counsel(payload.content, sentiment)

    # 4. 분석 결과 저장
    analysis = Analysis(
        journal_id=journal.id,
        emotion_temperature=result.emotion_temperature,
        emotion_summary=result.emotion_summary,
        emotion_keywords=result.emotion_keywords,
        primary_emotion=sentiment.primary_emotion,
        secondary_emotions=sentiment.secondary_emotions,
        sentiment_score=sentiment.sentiment_score,
        insight=result.insight,
        reframing=result.reframing,
        micro_habit=result.micro_habit,
        is_high_risk=1 if result.is_high_risk else 0,
    )
    db.add(analysis)
    db.commit()
    db.refresh(journal)
    db.refresh(analysis)

    return {
        "success": True,
        "data": {
            "journal_id": journal.id,
            "created_at": journal.created_at.isoformat(),
            "counseling": {
                "오늘의 감정 온도": {
                    "score": analysis.emotion_temperature,
                    "summary": analysis.emotion_summary,
                    "keywords": analysis.emotion_keywords,
                },
                "마음 들여다보기": analysis.insight,
                "빛나는 관점": analysis.reframing,
                "작은 발걸음": analysis.micro_habit,
                "is_high_risk": bool(analysis.is_high_risk),
            },
        },
    }


@router.get("/", response_model=list[dict])
def list_journals(skip: int = 0, limit: int = 20, db: Session = Depends(get_db)):
    """일기 목록 조회"""
    journals = (
        db.query(Journal)
        .order_by(Journal.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return [
        {
            "id": j.id,
            "content_preview": j.content[:80] + "..." if len(j.content) > 80 else j.content,
            "created_at": j.created_at.isoformat(),
            "emotion_temperature": j.analysis.emotion_temperature if j.analysis else None,
            "primary_emotion": j.analysis.primary_emotion if j.analysis else None,
        }
        for j in journals
    ]


@router.get("/{journal_id}", response_model=dict)
def get_journal(journal_id: int, db: Session = Depends(get_db)):
    """일기 상세 조회 (분석 결과 포함)"""
    journal = db.query(Journal).filter(Journal.id == journal_id).first()
    if not journal:
        raise HTTPException(status_code=404, detail="Journal not found")

    response = {
        "id": journal.id,
        "content": journal.content,
        "created_at": journal.created_at.isoformat(),
    }

    if journal.analysis:
        a = journal.analysis
        response["counseling"] = {
            "오늘의 감정 온도": {
                "score": a.emotion_temperature,
                "summary": a.emotion_summary,
                "keywords": a.emotion_keywords,
            },
            "마음 들여다보기": a.insight,
            "빛나는 관점": a.reframing,
            "작은 발걸음": a.micro_habit,
            "is_high_risk": bool(a.is_high_risk),
        }

    return response


@router.delete("/{journal_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_journal(journal_id: int, db: Session = Depends(get_db)):
    """일기 삭제"""
    journal = db.query(Journal).filter(Journal.id == journal_id).first()
    if not journal:
        raise HTTPException(status_code=404, detail="Journal not found")
    db.delete(journal)
    db.commit()
