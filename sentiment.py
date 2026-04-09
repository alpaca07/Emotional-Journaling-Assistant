"""
감정 분석 모듈
- Primary: HuggingFace Transformers (한국어 감정 분류)
- Fallback: 키워드 기반 규칙 분류 (모델 로드 실패 시)
"""
import re
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# 한국어 감정 키워드 사전
EMOTION_LEXICON = {
    "기쁨": [
        "기쁘", "행복", "즐거", "신나", "설레", "좋", "웃", "감사", "사랑", "뿌듯",
        "흐뭇", "유쾌", "재밌", "재미있", "신기", "고마", "소중", "따뜻", "포근",
        "기분 좋", "기분좋", "최고", "훌륭", "대박", "완벽", "만족", "황홀", "기특",
    ],
    "슬픔": [
        "슬프", "우울", "눈물", "힘들", "외롭", "그립", "허전", "상실", "서글", "울고",
        "슬픔", "처량", "비참", "쓸쓸", "공허", "텅 빈", "허탈", "상심", "가슴 아프",
    ],
    "분노": [
        "화나", "짜증", "열받", "억울", "분하", "답답", "화가", "불만", "불쾌", "미워",
        "싫어", "열받", "분노", "화남", "빡치", "욱", "울화", "억압", "부당",
    ],
    "불안": [
        "불안", "걱정", "두려", "무서", "떨려", "긴장", "공황", "초조", "염려", "겁나",
        "두근", "조마조마", "불확실", "무섭", "무서워", "망설", "두려움",
    ],
    "무기력": [
        "지쳐", "피곤", "무기력", "귀찮", "포기", "아무것도", "의미없", "허무",
        "지침", "탈진", "번아웃", "아무 의미", "무감각", "무감동",
    ],
    "평온": [
        "괜찮", "평온", "차분", "안정", "여유", "고요", "무난", "잘 지", "편안",
        "평화", "여유롭", "고즈넉", "잔잔", "느긋", "안도",
    ],
    "희망": [
        "희망", "기대", "꿈", "도전", "변화", "성장", "가능", "할 수 있", "노력",
        "목표", "계획", "의지", "다짐", "결심", "해낼", "극복", "미래",
    ],
}

HIGH_RISK_KEYWORDS = [
    "죽고 싶", "자살", "죽어버리", "사라지고 싶", "없어지고 싶", "끝내고 싶",
    "자해", "손목", "목 매", "뛰어내리", "죽을 것 같", "더 이상 못 살",
    "죽이고 싶", "해치고 싶", "폭력", "복수"
]


@dataclass
class SentimentResult:
    primary_emotion: str
    secondary_emotions: list[dict]
    sentiment_score: float        # -1.0 ~ 1.0
    is_high_risk: bool
    model_used: str


class SentimentAnalyzer:
    def __init__(self, model_name: str = "snunlp/KR-FinBert-SC"):
        self._pipeline = None
        self._model_name = model_name
        self._load_model()

    def _load_model(self):
        try:
            from transformers import pipeline
            self._pipeline = pipeline(
                "text-classification",
                model=self._model_name,
                top_k=5,
                truncation=True,
                max_length=512,
            )
            logger.info(f"[Sentiment] Model loaded: {self._model_name}")
        except Exception as e:
            logger.warning(f"[Sentiment] Model load failed, using fallback: {e}")
            self._pipeline = None

    def _check_high_risk(self, text: str) -> bool:
        return any(kw in text for kw in HIGH_RISK_KEYWORDS)

    def _fallback_analyze(self, text: str) -> SentimentResult:
        """키워드 기반 규칙 분류 (fallback)"""
        scores: dict[str, int] = {emotion: 0 for emotion in EMOTION_LEXICON}

        for emotion, keywords in EMOTION_LEXICON.items():
            for kw in keywords:
                if kw in text:
                    scores[emotion] += 1

        sorted_emotions = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        primary = sorted_emotions[0][0] if sorted_emotions[0][1] > 0 else "평온"

        # 감성 점수: 긍정/희망/평온 → 양수, 슬픔/분노/불안/무기력 → 음수
        positive_emotions = {"기쁨", "평온", "희망"}
        total = sum(s for _, s in sorted_emotions) or 1
        pos_score = sum(s for e, s in sorted_emotions if e in positive_emotions) / total
        neg_score = 1.0 - pos_score
        sentiment_score = round(pos_score - neg_score, 2)

        secondary = [
            {"label": e, "score": round(s / total, 2)}
            for e, s in sorted_emotions[1:4]
            if s > 0
        ]

        return SentimentResult(
            primary_emotion=primary,
            secondary_emotions=secondary,
            sentiment_score=sentiment_score,
            is_high_risk=self._check_high_risk(text),
            model_used="fallback-keyword",
        )

    def analyze(self, text: str) -> SentimentResult:
        is_high_risk = self._check_high_risk(text)

        if self._pipeline is None:
            result = self._fallback_analyze(text)
            result.is_high_risk = is_high_risk
            return result

        try:
            raw = self._pipeline(text[:512])
            predictions = raw[0] if raw else []

            # KR-FinBert-SC label mapping
            label_map = {
                "positive": "기쁨",
                "negative": "슬픔",
                "neutral": "평온",
            }

            if predictions:
                top = predictions[0]
                primary_emotion = label_map.get(top["label"].lower(), top["label"])
                sentiment_score = top["score"] if "positive" in top["label"].lower() else -top["score"]
                secondary = [
                    {"label": label_map.get(p["label"].lower(), p["label"]), "score": round(p["score"], 3)}
                    for p in predictions[1:3]
                ]
            else:
                return self._fallback_analyze(text)

            # fallback으로 세부 감정 보완
            fallback = self._fallback_analyze(text)
            if primary_emotion in ("슬픔", "평온"):
                primary_emotion = fallback.primary_emotion

            return SentimentResult(
                primary_emotion=primary_emotion,
                secondary_emotions=secondary,
                sentiment_score=round(sentiment_score, 2),
                is_high_risk=is_high_risk,
                model_used=self._model_name,
            )

        except Exception as e:
            logger.error(f"[Sentiment] Inference error: {e}")
            result = self._fallback_analyze(text)
            result.is_high_risk = is_high_risk
            return result


# 싱글톤
_analyzer: SentimentAnalyzer | None = None


def get_analyzer() -> SentimentAnalyzer:
    global _analyzer
    if _analyzer is None:
        import os
        model_name = os.getenv("MODEL_NAME", "snunlp/KR-FinBert-SC")
        _analyzer = SentimentAnalyzer(model_name)
    return _analyzer
