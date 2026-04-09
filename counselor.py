"""
CBT + Positive Psychology 상담 엔진

감정 분석 결과를 바탕으로:
1. 감정 온도 계산
2. 핵심 키워드 추출
3. 심리적 통찰 (인지 오류 탐지)
4. Positive Reframing
5. Micro-habit 제안
"""
import re
import logging
from dataclasses import dataclass
from sentiment import SentimentResult

logger = logging.getLogger(__name__)

# 인지 오류 패턴 (CBT)
COGNITIVE_DISTORTIONS = {
    "이분법적 사고": ["항상", "절대", "전혀", "모두", "완전히", "무조건", "100%"],
    "과잉일반화": ["매번", "언제나", "늘", "항상 그래", "다 그래"],
    "파국화": ["최악", "끔찍", "망했", "다 끝났", "어떡하", "어쩌지"],
    "독심술": ["분명히 나를", "날 싫어할", "무시할 것", "날 이상하게"],
    "감정적 추론": ["느낌이 그렇", "그냥 그런 것 같", "기분이 안 좋으니"],
    "자기비난": ["내 잘못", "나 때문에", "내가 문제", "내가 부족", "왜 나는"],
}

REFRAMING_TEMPLATES = {
    "슬픔": [
        "지금 느끼는 슬픔은 당신이 무언가를 깊이 사랑했다는 증거예요. 그 감수성이 오히려 당신의 강점입니다.",
        "이 아픔을 온전히 느끼는 것 자체가 용기입니다. 슬픔 뒤에는 반드시 새벽이 옵니다.",
    ],
    "분노": [
        "분노는 '이건 옳지 않다'는 당신 내면의 정의감에서 비롯됩니다. 그 에너지를 변화의 동력으로 바꿀 수 있어요.",
        "화가 나는 건 당신이 자신을 소중히 여기기 때문입니다. 그 경계선은 지켜질 자격이 있어요.",
    ],
    "불안": [
        "불안은 '이게 나에게 중요하다'는 신호입니다. 중요하기 때문에 걱정하는 거예요.",
        "걱정되는 만큼 준비하고 싶은 마음이 담겨 있어요. 그 세심함이 당신을 지켜왔을 거예요.",
    ],
    "무기력": [
        "쉬고 싶다는 마음은 몸과 마음이 충전이 필요하다는 신호입니다. 멈추는 것도 전진의 일부예요.",
        "아무것도 못 하는 날도 살아낸 날입니다. 오늘도 여기 있는 당신, 충분합니다.",
    ],
    "기쁨": [
        "이 기쁨의 순간을 온전히 누리세요. 좋은 감정도 충분히 느낄 자격이 있습니다.",
        "이 행복이 어디서 왔는지 기억해 두세요. 그게 바로 당신이 소중히 여기는 것의 지도예요.",
    ],
    "평온": [
        "평온함 속에서 자신을 가장 잘 들을 수 있어요. 이 고요함이 다음 한 걸음의 에너지가 됩니다.",
        "잔잔한 날도 소중한 날입니다. 매일 드라마틱할 필요는 없어요.",
    ],
    "희망": [
        "희망을 품는 것 자체가 이미 변화의 시작입니다. 당신의 그 꿈을 믿어요.",
        "기대하는 마음이 있다는 건 아직 포기하지 않았다는 뜻이에요. 그 불씨를 살려가세요.",
    ],
}

MICRO_HABITS = {
    "슬픔": [
        "오늘 밤, 따뜻한 음료를 한 잔 마시며 5분간 '오늘 내가 잘 버텼던 순간' 한 가지만 떠올려 보세요.",
        "내일 아침, 일어나자마자 햇빛이 드는 창가에 1분만 서 있어보세요. 빛이 몸에 닿는 감각에 집중해 보세요.",
        "지금 당장, 사랑하는 사람 한 명에게 '잘 지내?' 문자 한 통을 보내보세요.",
    ],
    "분노": [
        "지금 바로 '4-7-8 호흡법'을 해보세요: 4초 들이쉬고, 7초 참고, 8초에 내쉬기. 3회 반복.",
        "내일, 화가 났던 상황을 제3자의 시선으로 글로 써보세요. 단 3문장이면 충분해요.",
        "오늘 안에 몸을 쓰는 활동(산책 15분, 스트레칭)으로 감정 에너지를 방출해 보세요.",
    ],
    "불안": [
        "지금 이 순간, '5-4-3-2-1 그라운딩'을 해보세요: 보이는 것 5가지, 만져지는 것 4가지, 들리는 것 3가지를 천천히 세어보세요.",
        "내일 아침, 걱정 목록을 종이에 적고 '내가 통제할 수 있는 것'과 '없는 것'으로 나눠보세요.",
        "오늘 밤, 자기 전 '지금 당장 괜찮은 것' 3가지를 말해보세요.",
    ],
    "무기력": [
        "딱 2분만 - 지금 당장 몸을 일으켜 물 한 잔 마시는 것부터 시작해요. 아주 작은 것도 움직임이에요.",
        "내일, 해야 할 일 목록에서 가장 쉬운 것 하나만 골라 그것만 하기로 해보세요.",
        "오늘 밤, 좋아하는 음악 한 곡만 틀어놓고 아무것도 안 해도 되는 10분을 자신에게 허락하세요.",
    ],
    "기쁨": [
        "지금 이 기쁨을 일기나 메모에 구체적으로 기록해 두세요. 나중에 힘들 때 꺼내 볼 수 있도록.",
        "내일, 이 기쁨을 함께 느꼈으면 하는 한 사람에게 공유해 보세요.",
        "이 좋은 감정이 어디서 왔는지 생각해보고, 그것을 한 번 더 경험할 수 있는 방법을 계획해 보세요.",
    ],
    "평온": [
        "이 차분한 상태에서 오래 미뤄온 것 하나를 5분만 시작해 보세요. 평온할 때가 가장 좋은 시작점이에요.",
        "내일, 이 고요함을 유지하는 루틴(명상 3분, 산책, 차 한 잔)을 하나 만들어보세요.",
        "오늘의 평온함에 감사하는 마음으로 '감사 일기' 3줄을 써보세요.",
    ],
    "희망": [
        "지금 당장, 그 꿈이나 목표를 구체적으로 적어보세요. 글로 써야 비로소 현실이 됩니다.",
        "내일, 그 목표를 향한 가장 작은 첫 걸음 하나를 실행해 보세요. 단 5분짜리라도 괜찮아요.",
        "이 희망을 응원해 줄 사람 한 명에게 당신의 계획을 공유해 보세요.",
    ],
}

HIGH_RISK_MESSAGE = """⚠️ **긴급 안내 - 전문가 도움이 필요합니다**

일기에서 자신이나 타인을 해칠 수 있는 신호가 감지되었습니다.
지금 당장 아래 기관에 연락하거나 가까운 응급실을 방문해 주세요.

- **정신건강 위기상담 전화**: ☎ 1577-0199 (24시간)
- **자살예방 상담전화**: ☎ 1393 (24시간)
- **응급신고**: ☎ 119

당신의 생명은 소중합니다. 혼자 버티지 않아도 괜찮아요. 💙"""


def _detect_cognitive_distortions(text: str) -> list[str]:
    found = []
    for distortion, keywords in COGNITIVE_DISTORTIONS.items():
        if any(kw in text for kw in keywords):
            found.append(distortion)
    return found


def _extract_keywords(text: str, primary_emotion: str) -> list[str]:
    """감정 관련 핵심 키워드 3개 추출"""
    from sentiment import EMOTION_LEXICON
    found_keywords = []

    for emotion, keywords in EMOTION_LEXICON.items():
        for kw in keywords:
            if kw in text and kw not in found_keywords:
                found_keywords.append(kw)

    # 부족하면 감정명으로 채움
    if primary_emotion not in found_keywords:
        found_keywords.insert(0, primary_emotion)

    return found_keywords[:3] if len(found_keywords) >= 3 else (found_keywords + ["감정", "성찰", "회복"])[:3]


def _calculate_temperature(sentiment_score: float, is_high_risk: bool) -> float:
    """
    감정 온도: 0.0(매우 부정) ~ 10.0(매우 긍정)
    sentiment_score: -1.0 ~ 1.0
    """
    if is_high_risk:
        return 1.0
    temp = (sentiment_score + 1.0) / 2.0 * 10.0
    return round(max(0.0, min(10.0, temp)), 1)


def _build_insight(text: str, primary_emotion: str, distortions: list[str]) -> str:
    distortion_text = ""
    if distortions:
        distortion_text = (
            f"\n\n또한 글 속에서 **{', '.join(distortions)}** 같은 사고 패턴이 느껴지는데, "
            "이는 힘들 때 우리 마음이 자주 빠지는 함정이에요. 알아채는 것만으로도 절반은 벗어난 거예요."
        )

    emotion_insights = {
        "슬픔": "글 속에서 깊은 슬픔과 상처가 느껴져요. 이 감정은 당신이 소중하게 여기는 무언가와 연결되어 있을 거예요.",
        "분노": "분노 이면에는 상처받은 마음, 또는 충족되지 않은 기대가 숨어 있는 경우가 많아요. 무엇이 가장 많이 아팠나요?",
        "불안": "불안은 미래에 대한 걱정에서 오는 경우가 많아요. 지금 당신이 가장 두려워하는 것이 무엇인지 살펴볼 필요가 있어요.",
        "무기력": "모든 것이 의미 없게 느껴지는 이 상태, 몸과 마음이 한계에 다다랐다는 신호일 수 있어요. 충분히 쉬어야 할 때예요.",
        "기쁨": "오늘 기쁨을 느낄 수 있었다는 것 자체가 축복이에요. 그 순간들이 당신의 삶에 빛을 더해주고 있어요.",
        "평온": "잔잔하고 차분한 하루를 보내셨군요. 이런 날이 쌓여 내면의 든든한 토대가 만들어져요.",
        "희망": "희망을 품고 계시는군요. 그 에너지가 글 속에서도 느껴져요. 지금이 무언가를 시작하기 좋은 때예요.",
    }

    base = emotion_insights.get(primary_emotion, "오늘 하루도 많은 감정을 경험하셨군요. 그 모든 감정이 다 의미 있어요.")
    return base + distortion_text


def _select_reframing(primary_emotion: str) -> str:
    import random
    templates = REFRAMING_TEMPLATES.get(primary_emotion, REFRAMING_TEMPLATES["평온"])
    return random.choice(templates)


def _select_micro_habit(primary_emotion: str) -> str:
    import random
    habits = MICRO_HABITS.get(primary_emotion, MICRO_HABITS["평온"])
    return random.choice(habits)


@dataclass
class CounselingResult:
    emotion_temperature: float
    emotion_summary: str
    emotion_keywords: list[str]
    insight: str
    reframing: str
    micro_habit: str
    is_high_risk: bool


def counsel(text: str, sentiment: SentimentResult) -> CounselingResult:
    if sentiment.is_high_risk:
        return CounselingResult(
            emotion_temperature=1.0,
            emotion_summary="지금 매우 위험한 상태로 감지됩니다. 즉시 전문가의 도움이 필요합니다.",
            emotion_keywords=["위기", "긴급", "도움필요"],
            insight=HIGH_RISK_MESSAGE,
            reframing=HIGH_RISK_MESSAGE,
            micro_habit=HIGH_RISK_MESSAGE,
            is_high_risk=True,
        )

    distortions = _detect_cognitive_distortions(text)
    keywords = _extract_keywords(text, sentiment.primary_emotion)
    temperature = _calculate_temperature(sentiment.sentiment_score, sentiment.is_high_risk)

    temp_label = (
        "매우 힘든" if temperature < 3 else
        "다소 힘든" if temperature < 5 else
        "보통의" if temperature < 7 else
        "비교적 좋은" if temperature < 9 else
        "매우 좋은"
    )

    summary = f"오늘은 {temp_label} 하루였군요. 마음속에 '{sentiment.primary_emotion}'의 감정이 가장 크게 자리잡고 있어요."

    return CounselingResult(
        emotion_temperature=temperature,
        emotion_summary=summary,
        emotion_keywords=keywords,
        insight=_build_insight(text, sentiment.primary_emotion, distortions),
        reframing=_select_reframing(sentiment.primary_emotion),
        micro_habit=_select_micro_habit(sentiment.primary_emotion),
        is_high_risk=False,
    )
