from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


# --- Journal ---

class JournalCreate(BaseModel):
    content: str = Field(..., min_length=10, max_length=5000, description="일기 내용 (10자 이상)")


class JournalResponse(BaseModel):
    id: int
    content: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# --- Analysis ---

class EmotionTemperature(BaseModel):
    score: float = Field(..., ge=0.0, le=10.0)
    summary: str
    keywords: list[str] = Field(..., min_length=3, max_length=3)


class AnalysisResponse(BaseModel):
    id: int
    journal_id: int
    emotion_temperature: EmotionTemperature
    primary_emotion: str
    secondary_emotions: Optional[list[dict]] = None
    sentiment_score: float
    insight: str
    reframing: str
    micro_habit: str
    is_high_risk: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# --- Combined ---

class JournalWithAnalysis(BaseModel):
    journal: JournalResponse
    analysis: Optional[AnalysisResponse] = None

    model_config = {"from_attributes": True}


# --- API Response wrapper ---

class APIResponse(BaseModel):
    success: bool = True
    message: str = "OK"
    data: Optional[dict] = None
