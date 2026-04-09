from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Float, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from database import Base


class Journal(Base):
    __tablename__ = "journals"

    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    analysis = relationship("Analysis", back_populates="journal", uselist=False, cascade="all, delete-orphan")


class Analysis(Base):
    __tablename__ = "analyses"

    id = Column(Integer, primary_key=True, index=True)
    journal_id = Column(Integer, ForeignKey("journals.id"), nullable=False, unique=True)

    # 감정 온도
    emotion_temperature = Column(Float, nullable=False)  # 0.0 ~ 10.0
    emotion_summary = Column(String(200), nullable=False)
    emotion_keywords = Column(JSON, nullable=False)       # ["키워드1", "키워드2", "키워드3"]

    # 감정 분류
    primary_emotion = Column(String(50), nullable=False)
    secondary_emotions = Column(JSON, nullable=True)      # [{"label": "...", "score": 0.xx}]
    sentiment_score = Column(Float, nullable=False)       # -1.0 (부정) ~ 1.0 (긍정)

    # 상담 결과
    insight = Column(Text, nullable=False)                # 마음 들여다보기
    reframing = Column(Text, nullable=False)              # 빛나는 관점
    micro_habit = Column(Text, nullable=False)            # 작은 발걸음

    # 위험 신호
    is_high_risk = Column(Integer, default=0)             # 0: normal, 1: high-risk

    created_at = Column(DateTime, default=datetime.utcnow)

    journal = relationship("Journal", back_populates="analysis")
