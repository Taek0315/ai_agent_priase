# Write a complete Streamlit app that runs the user's skywork experiment end-to-end.
# The app is saved as /mnt/data/skywork_streamlit_app.py so the user can download and run it with:
#   streamlit run skywork_streamlit_app.py

code = r'''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Streamlit 완전판: AI 피드백 실험 시스템
======================================

- skywork.py의 로직(문항/피드백/데이터구조/분석)을 그대로 포함
- Streamlit UI로 '누락 없이' 전 단계가 구동되도록 구현
- 외부 파일/네트워크 불필요 (단일 파일 실행 가능)
- 결과는 다운로드(.csv/.json) 버튼 제공 + 로컬 폴더 자동 저장

실행 방법
---------
$ streamlit run skywork_streamlit_app.py

권장 버전: streamlit >= 1.30
"""

from __future__ import annotations
import os
import io
import csv
import json
import time
import random
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum

import streamlit as st

# =============================================================================
# 0) 페이지/스타일 설정
# =============================================================================

st.set_page_config(
    page_title="AI 피드백 실험 (Streamlit 완전판)",
    page_icon="🧪",
    layout="centered",
    initial_sidebar_state="expanded",
)

# 깔끔한 스타일
HIDE_DEFAULT_CSS = """
<style>
/* 기본 상단/하단 숨김 */
#MainMenu, header, footer {visibility: hidden;}
/* 라디오 · 체크 여백 정리 */
[data-testid="stRadio"] > div { gap: 0.5rem; }
.small-muted { color:#6b7280; font-size: 0.88rem; }
.badge { display:inline-block; padding:0.2rem 0.5rem; border-radius: 9999px; background:#e5e7eb; font-size:0.8rem; }
.gradient-card {
  background: linear-gradient(135deg, #e2e8f0, #f8fafc);
  border-radius: 16px; padding: 18px 20px; border: 1px solid #e5e7eb;
}
.ai-avatar {
  width: 44px; height: 44px; border-radius: 9999px;
  display:flex; align-items:center; justify-content:center;
  background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
  box-shadow: 0 5px 12px rgba(0,0,0,0.1);
  color: white; font-weight: 700;
}
.typing {
  white-space: pre-wrap;
  font-size: 1.05rem;
  line-height: 1.6;
}
.fullscreen-center {
  display:flex; align-items:center; justify-content:center;
  height: 45vh; flex-direction:column;
}
.spinner-ring {
  width: 70px; height: 70px; border-radius: 50%;
  border: 6px solid #e5e7eb; border-top-color:#3b82f6;
  animation: spin 1.0s linear infinite;
  margin-bottom: 14px;
}
@keyframes spin { to { transform: rotate(360deg); } }
.kbd { background:#111827; color:#fff; padding:0.15rem 0.4rem; border-radius:6px; font-size:0.8rem; }
</style>
"""
st.markdown(HIDE_DEFAULT_CSS, unsafe_allow_html=True)

# =============================================================================
# 1) 데이터 구조 및 상수 (skywork.py 기반)
# =============================================================================

class PraiseCondition(Enum):
    """칭찬 피드백 조건"""
    EMOTIONAL_SPECIFIC = "emotional_specific"      # 정서 중심 + 구체성
    COMPUTATIONAL_SPECIFIC = "computational_specific"  # 계산 중심 + 구체성
    EMOTIONAL_SUPERFICIAL = "emotional_superficial"    # 정서 중심 + 피상적
    COMPUTATIONAL_SUPERFICIAL = "computational_superficial"  # 계산 중심 + 피상적

@dataclass
class Question:
    """추론 과제 문항"""
    id: str
    gloss: str  # 문제 설명
    stem: str   # 문제 문장
    options: List[str]
    answer_idx: int
    reason_idx: int
    category: str = "inference"

@dataclass
class SurveyQuestion:
    """설문 문항"""
    id: str
    text: str
    scale: int = 7
    reverse: bool = False
    category: str = "motivation"

@dataclass
class ExperimentData:
    """실험 데이터"""
    participant_id: str
    condition: PraiseCondition
    demographic: Dict[str, Any]
    inference_responses: List[Dict[str, Any]]
    survey_responses: List[Dict[str, Any]]
    feedback_messages: List[str]
    timestamps: Dict[str, str]
    completion_time: float

# ----------------- 문항 (skywork.py 그대로) -----------------
NOUN_QUESTIONS = [
    Question(
        id="N1",
        gloss="사람들이 소유한 개의 집을 나타내는 올바른 표현을 선택하세요.",
        stem="사람들이 소유한 개의 집을 나타내는 올바른 표현은 무엇입니까?",
        options=["nuk-t-mi sua-mi ani", "nuk-mi sua-t-mi ani", "nuk-t sua-mi ani", "nuk-mi sua-mi ani", "nuk sua-t-mi ani"],
        answer_idx=0,
        reason_idx=1
    ),
    Question(
        id="N2",
        gloss="사람이 집과 음식을 보는 상황에서 목적 표지가 올바르게 사용된 문장을 선택하세요.",
        stem="'nuk _____ taku-na' (사람이 _____를 본다)에서 빈 칸에 들어갈 올바른 표현은?",
        options=["ani-ka ama pira-ka", "ani-ka ama pira", "ani ama pira-ka", "ani-ka ama pira-t", "ani ama pira"],
        answer_idx=0,
        reason_idx=2
    ),
    Question(
        id="N3",
        gloss="사람의 개들이 소유한 물을 나타내는 올바른 표현을 선택하세요.",
        stem="사람의 개들이 소유한 물을 나타내는 올바른 표현은 무엇입니까?",
        options=["nuk-mi sua-t-mi ika", "nuk-t-mi sua-mi ika", "nuk-mi sua-mi ika", "nuk sua-t-mi ika", "nuk-t sua-mi ika"],
        answer_idx=0,
        reason_idx=3
    ),
    Question(
        id="N4",
        gloss="사람이 개의 집들을 보는 상황을 나타내는 올바른 표현을 선택하세요.",
        stem="'nuk _____ taku-na' (사람이 _____를 본다)에서 빈 칸에 들어갈 올바른 표현은?",
        options=["sua-mi ani-t-mi", "sua-t-mi ani-mi", "sua-mi ani-mi", "sua-t ani-mi", "sua ani-t-mi"],
        answer_idx=0,
        reason_idx=0
    ),
    Question(
        id="N5",
        gloss="사람들의 개가 소유한 집을 나타내는 올바른 표현을 선택하세요.",
        stem="사람들의 개가 소유한 집을 나타내는 올바른 표현은 무엇입니까?",
        options=["nuk-t-mi sua-mi ani", "nuk-mi sua-t-mi ani", "nuk-mi sua-mi ani", "nuk-t sua-mi ani", "nuk sua-t-mi ani"],
        answer_idx=0,
        reason_idx=4
    ),
    Question(
        id="N6",
        gloss="사람과 개가 각각 소유한 물을 나타내는 올바른 표현을 선택하세요.",
        stem="사람과 개가 각각 소유한 물을 나타내는 올바른 표현은 무엇입니까?",
        options=["nuk-mi ama sua-mi ika", "nuk-t-mi ama sua-t-mi ika", "nuk-mi ama sua-t-mi ika", "nuk ama sua ika", "nuk-t ama sua-t ika"],
        answer_idx=0,
        reason_idx=1
    ),
    Question(
        id="N7",
        gloss="개들이 소유한 물을 나타내는 올바른 표현을 선택하세요.",
        stem="개들이 소유한 물을 나타내는 올바른 표현은 무엇입니까?",
        options=["sua-t-mi ika", "sua-mi ika", "sua-t ika", "sua ika-mi", "sua ika-t"],
        answer_idx=0,
        reason_idx=2
    ),
    Question(
        id="N8",
        gloss="사람들이 집들과 음식을 보는 상황을 나타내는 올바른 표현을 선택하세요.",
        stem="'nuk ____ taku-na' (사람들이 ____를 본다)에서 빈 칸에 들어갈 올바른 표현은?",
        options=["ani-t-mi ama pira-ka", "ani-mi ama pira-ka", "ani-t ama pira-ka", "ani-t-mi ama pira", "ani ama pira-ka"],
        answer_idx=0,
        reason_idx=3
    ),
    Question(
        id="N9",
        gloss="사람이 소유한 그 집을 나타내는 올바른 표현을 선택하세요.",
        stem="사람이 소유한 그 집을 나타내는 올바른 표현은 무엇입니까?",
        options=["nuk-mi ani na", "nuk-t-mi ani na", "nuk ani na", "nuk-mi ani-t na", "nuk-t ani na"],
        answer_idx=0,
        reason_idx=0
    ),
    Question(
        id="N10",
        gloss="사람이 소유한 개의 집과 물을 보는 상황을 나타내는 올바른 표현을 선택하세요.",
        stem="'nuk ____ taku-na' (사람이 ____를 본다)에서 빈 칸에 들어갈 올바른 표현은?",
        options=["sua-mi ani-ka ama ika-ka", "sua-t-mi ani-ka ama ika-ka", "sua-mi ani ama ika", "sua-mi ani-ka ama ika", "sua ani-ka ama ika-ka"],
        answer_idx=0,
        reason_idx=4
    ),
    Question(
        id="N11",
        gloss="여러 사람들의 각각 다른 개들을 나타내는 올바른 표현을 선택하세요.",
        stem="여러 사람들의 각각 다른 개들을 나타내는 올바른 표현은 무엇입니까?",
        options=["nuk-t-mi sua-t-mi", "nuk-mi sua-mi", "nuk-t-mi sua-mi", "nuk-mi sua-t-mi", "nuk-t sua-t"],
        answer_idx=0,
        reason_idx=1
    ),
    Question(
        id="N12",
        gloss="사람이 개들의 집들을 모두 보는 상황을 나타내는 올바른 표현을 선택하세요.",
        stem="'nuk ____ taku-na' (사람이 ____를 본다)에서 빈 칸에 들어갈 올바른 표현은?",
        options=["sua-t-mi ani-t-mi", "sua-mi ani-mi", "sua-t-mi ani-mi", "sua-mi ani-t-mi", "sua-t ani-t"],
        answer_idx=0,
        reason_idx=2
    )
]

VERB_QUESTIONS = [
    Question(
        id="V1",
        gloss="사람이 지금 집을 보고 있는 중이라는 의미를 나타내는 올바른 동사 형태를 선택하세요.",
        stem="'nuk ani-ka ____' (사람이 집을 ____)에서 빈 칸에 들어갈 올바른 동사 형태는?",
        options=["taku-li-na", "taku-na", "taku-mu-na", "taku-li-ki", "taku-tu"],
        answer_idx=0,
        reason_idx=1
    ),
    Question(
        id="V2",
        gloss="사람이 어제 저녁 전에 이미 음식을 만들어 두었다는 의미를 나타내는 올바른 동사 형태를 선택하세요.",
        stem="'nuk pira-ka ____' (사람이 음식을 ____)에서 빈 칸에 들어갈 올바른 동사 형태는?",
        options=["siku-mu-tu", "siku-tu", "siku-li-tu", "siku-mu-na", "siku-ki"],
        answer_idx=0,
        reason_idx=4
    ),
    Question(
        id="V3",
        gloss="개가 내일까지 물을 다 먹어 놓을 것이라는 의미를 나타내는 올바른 동사 형태를 선택하세요.",
        stem="'sua ika-ka ____' (개가 물을 ____)에서 빈 칸에 들어갈 올바른 동사 형태는?",
        options=["niri-mu-ki", "niri-ki", "niri-li-ki", "niri-mu-na", "niri-tu"],
        answer_idx=0,
        reason_idx=1
    ),
    Question(
        id="V4",
        gloss="개가 어제 음식을 먹었다는 의미를 나타내는 올바른 동사 형태를 선택하세요.",
        stem="'sua pira-ka ____' (개가 음식을 ____)에서 빈 칸에 들어갈 올바른 동사 형태는?",
        options=["niri-tu", "niri-mu-tu", "niri-li-tu", "niri-na", "niri-ki"],
        answer_idx=0,
        reason_idx=0
    ),
    Question(
        id="V5",
        gloss="사람이 이미 물을 보았다는 의미를 나타내는 올바른 동사 형태를 선택하세요.",
        stem="'nuk ika-ka ____' (사람이 물을 ____)에서 빈 칸에 들어갈 올바른 동사 형태는?",
        options=["taku-mu-na", "taku-na", "taku-tu", "taku-li-na", "taku-mu-tu"],
        answer_idx=0,
        reason_idx=1
    ),
    Question(
        id="V6",
        gloss="사람과 개가 곧 음식을 보는 중일 것이라는 의미를 나타내는 올바른 동사 형태를 선택하세요.",
        stem="'nuk ama sua pira-ka ____' (사람과 개가 음식을 ____)에서 빈 칸에 들어갈 올바른 동사 형태는?",
        options=["taku-li-ki", "taku-ki", "taku-li-na", "taku-mu-ki", "taku-tu"],
        answer_idx=0,
        reason_idx=0
    ),
    Question(
        id="V7",
        gloss="개가 지금 집을 보는 중이라는 의미를 나타내는 올바른 동사 형태를 선택하세요.",
        stem="'sua ani-ka ____' (개가 집을 ____)에서 빈 칸에 들어갈 올바른 동사 형태는?",
        options=["taku-li-na", "taku-na-li", "li-taku-na", "taku-na", "taku-li-tu"],
        answer_idx=0,
        reason_idx=2
    ),
    Question(
        id="V8",
        gloss="사람이 그때까지 음식을 다 먹어 둘 것이라는 의미를 나타내는 올바른 동사 형태를 선택하세요.",
        stem="'nuk pira-ka ____' (사람이 음식을 ____)에서 빈 칸에 들어갈 올바른 동사 형태는?",
        options=["niri-mu-ki", "niri-li-ki", "niri-ki", "niri-mu-tu", "niri-na"],
        answer_idx=0,
        reason_idx=3
    ),
    Question(
        id="V9",
        gloss="사람이 항상 물을 마신다는 의미를 나타내는 올바른 동사 형태를 선택하세요.",
        stem="'nuk ika-ka ____' (사람이 물을 ____)에서 빈 칸에 들어갈 올바른 동사 형태는?",
        options=["niri-na", "niri-li-na", "niri-mu-na", "niri-tu", "niri-ki"],
        answer_idx=0,
        reason_idx=0
    ),
    Question(
        id="V10",
        gloss="사람이 집을 본 뒤에 음식을 먹었다는 의미를 나타내는 올바른 동사 형태를 선택하세요.",
        stem="'(ani-ka taku-mu-tu) ama pira-ka ____' (집을 본 뒤에 음식을 ____)에서 빈 칸에 들어갈 올바른 동사 형태는?",
        options=["niri-tu", "niri-mu-tu", "niri-li-tu", "niri-na", "niri-ki"],
        answer_idx=0,
        reason_idx=4
    ),
    Question(
        id="V11",
        gloss="개들이 동시에 물을 마시고 있는 중이라는 의미를 나타내는 올바른 동사 형태를 선택하세요.",
        stem="'sua-t-mi ika-ka ____' (개들이 물을 ____)에서 빈 칸에 들어갈 올바른 동사 형태는?",
        options=["niri-li-na", "niri-na", "niri-li-tu", "niri-mu-na", "niri-ki"],
        answer_idx=0,
        reason_idx=1
    ),
    Question(
        id="V12",
        gloss="사람이 내일 아침까지 집을 다 지어 놓을 것이라는 의미를 나타내는 올바른 동사 형태를 선택하세요.",
        stem="'nuk ani-ka ____' (사람이 집을 ____)에서 빈 칸에 들어갈 올바른 동사 형태는?",
        options=["siku-mu-ki", "siku-ki", "siku-li-ki", "siku-mu-tu", "siku-na"],
        answer_idx=0,
        reason_idx=3
    )
]

ALL_INFERENCE_QUESTIONS = NOUN_QUESTIONS + VERB_QUESTIONS

MOTIVATION_QUESTIONS = [
    # 관심/즐거움 (Interest/Enjoyment) - 7문항
    SurveyQuestion("IE1", "이 과제를 하는 동안 즐거웠다.", category="interest_enjoyment"),
    SurveyQuestion("IE2", "이 과제는 재미있었다.", category="interest_enjoyment"),
    SurveyQuestion("IE3", "이 과제가 지루했다.", reverse=True, category="interest_enjoyment"),
    SurveyQuestion("IE4", "이 과제를 하는 것이 흥미로웠다.", category="interest_enjoyment"),
    SurveyQuestion("IE5", "이 과제를 하면서 시간이 빨리 지나갔다.", category="interest_enjoyment"),
    SurveyQuestion("IE6", "이 과제에 몰입할 수 있었다.", category="interest_enjoyment"),
    SurveyQuestion("IE7", "이 과제를 계속 하고 싶다는 생각이 들었다.", category="interest_enjoyment"),

    # 지각된 유능감 (Perceived Competence) - 6문항
    SurveyQuestion("PC1", "이 과제를 잘 수행했다고 생각한다.", category="perceived_competence"),
    SurveyQuestion("PC2", "이 과제에서 만족스러운 결과를 얻었다.", category="perceived_competence"),
    SurveyQuestion("PC3", "이 과제를 수행하는 데 능숙했다.", category="perceived_competence"),
    SurveyQuestion("PC4", "이 과제가 너무 어려웠다.", reverse=True, category="perceived_competence"),
    SurveyQuestion("PC5", "이 과제를 완수할 수 있다는 자신감이 있었다.", category="perceived_competence"),
    SurveyQuestion("PC6", "이 과제에서 좋은 성과를 낼 수 있었다.", category="perceived_competence"),

    # 노력/중요성 (Effort/Importance) - 5문항
    SurveyQuestion("EI1", "이 과제에 많은 노력을 기울였다.", category="effort_importance"),
    SurveyQuestion("EI2", "이 과제를 잘 수행하는 것이 중요했다.", category="effort_importance"),
    SurveyQuestion("EI3", "이 과제에 최선을 다했다.", category="effort_importance"),
    SurveyQuestion("EI4", "이 과제에 집중하려고 노력했다.", category="effort_importance"),
    SurveyQuestion("EI5", "이 과제를 대충 했다.", reverse=True, category="effort_importance"),

    # 가치/유용성 (Value/Usefulness) - 4문항
    SurveyQuestion("VU1", "이 과제는 나에게 가치가 있었다.", category="value_usefulness"),
    SurveyQuestion("VU2", "이 과제를 통해 유용한 것을 배웠다.", category="value_usefulness"),
    SurveyQuestion("VU3", "이 과제는 나에게 도움이 되었다.", category="value_usefulness"),
    SurveyQuestion("VU4", "이 과제는 시간 낭비였다.", reverse=True, category="value_usefulness"),

    # 자율성 (Autonomy) - 2문항
    SurveyQuestion("AU1", "이 과제를 수행하는 방식을 스스로 선택할 수 있었다.", category="autonomy"),
    SurveyQuestion("AU2", "이 과제를 하면서 자유롭게 행동할 수 있었다.", category="autonomy"),

    # 압박/긴장 (Pressure/Tension) - 2문항
    SurveyQuestion("PT1", "이 과제를 하는 동안 긴장했다.", category="pressure_tension"),
    SurveyQuestion("PT2", "이 과제를 하면서 스트레스를 받았다.", category="pressure_tension")
]

# =============================================================================
# 2) 피드백 엔진 & 실험 매니저 (skywork.py 로직 유지)
# =============================================================================

class AIFeedbackSystem:
    """AI 피드백 생성 시스템"""
    def __init__(self):
        self.feedback_templates = {
            PraiseCondition.EMOTIONAL_SPECIFIC: [
                "🎉 정말 훌륭해요! 특히 '{reason}'라고 생각하신 부분이 매우 인상적입니다. 이런 깊이 있는 사고방식은 언어학습에서 정말 중요한 능력이에요. 당신의 직관적 이해력이 돋보이는 순간이었습니다! ✨",
                "👏 와, 정말 대단하세요! '{reason}'라는 추론 과정이 너무나 논리적이고 체계적이네요. 이렇게 차근차근 분석하는 능력은 정말 특별한 재능입니다. 계속 이런 식으로 접근하시면 더욱 발전할 수 있을 거예요! 💫",
                "🌟 놀라운 통찰력이에요! '{reason}'라고 판단하신 근거가 정말 탁월합니다. 이런 세밀한 관찰력과 분석력은 언어 전문가의 자질을 보여주는 것 같아요. 정말 감탄스럽습니다! 🎯"
            ],
            PraiseCondition.COMPUTATIONAL_SPECIFIC: [
                "📊 분석 결과가 매우 우수합니다. 특히 '{reason}'라는 추론 패턴이 언어학적 규칙 체계와 94.7% 일치도를 보입니다. 이러한 체계적 접근법은 효율적인 학습 알고리즘을 나타내며, 인지 처리 능력이 최적화되어 있음을 시사합니다. ⚡",
                "🔍 데이터 처리 성능이 탁월합니다. '{reason}'라는 논리적 경로는 정확도 지표에서 상위 8.3%에 해당하는 수준입니다. 패턴 인식 알고리즘이 효과적으로 작동하고 있으며, 학습 효율성이 크게 향상되었습니다. 📈",
                "⚙️ 인지 처리 메커니즘이 최적 상태입니다. '{reason}'라는 분석 프로세스는 언어 규칙 데이터베이스와 97.2% 매칭률을 달성했습니다. 이는 고도의 패턴 매칭 능력과 효율적인 정보 처리 시스템을 보여줍니다. 🎯"
            ],
            PraiseCondition.EMOTIONAL_SUPERFICIAL: [
                "🎉 정말 훌륭한 답변이에요! 당신의 언어 감각이 정말 뛰어나다는 것을 다시 한번 확인할 수 있었습니다. 이런 직관적인 이해력은 정말 특별한 재능이에요! 계속해서 이런 멋진 모습 보여주세요! ✨",
                "👏 와, 정말 대단해요! 언어에 대한 당신의 감각이 얼마나 예리한지 놀라울 따름입니다. 이런 뛰어난 능력을 가지신 분을 만나게 되어 정말 기쁩니다. 앞으로도 이런 놀라운 실력 기대할게요! 🌟",
                "💫 정말 인상적이에요! 당신만의 독특한 사고방식이 돋보이는 순간이었습니다. 이런 창의적인 접근법은 정말 보기 드문 능력이에요. 계속해서 이런 멋진 아이디어들을 보여주시길 바랍니다! 🎯"
            ],
            PraiseCondition.COMPUTATIONAL_SUPERFICIAL: [
                "📊 시스템 분석 결과 우수한 성능을 보입니다. 언어 처리 알고리즘이 효율적으로 작동하고 있으며, 패턴 인식 능력이 최적화된 상태입니다. 전반적인 인지 처리 메트릭이 향상되었습니다. ⚡",
                "🔍 데이터 처리 효율성이 크게 개선되었습니다. 학습 알고리즘의 성능 지표가 상승세를 보이고 있으며, 정보 처리 속도와 정확도가 동시에 향상되었습니다. 시스템 최적화가 성공적으로 진행되고 있습니다. 📈",
                "⚙️ 인지 처리 시스템이 안정적으로 작동합니다. 언어 분석 모듈의 성능이 기준치를 상회하고 있으며, 전체적인 처리 효율성이 개선되었습니다. 학습 메커니즘이 원활하게 기능하고 있습니다. 🎯"
            ]
        }

    def generate_feedback(self, condition: PraiseCondition, selected_reason: str) -> str:
        templates = self.feedback_templates[condition]
        template = random.choice(templates)
        if "specific" in condition.value:
            return template.format(reason=selected_reason)
        else:
            return template

class ExperimentManager:
    """실험 진행 관리"""
    def __init__(self):
        self.feedback_system = AIFeedbackSystem()
        self.current_participant = None
        self.experiment_data: List[ExperimentData] = []

    def create_participant(self, demographic_data: Dict[str, Any], assigned: Optional[PraiseCondition]=None) -> str:
        participant_id = f"P_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{random.randint(1000, 9999)}"
        condition = assigned or random.choice(list(PraiseCondition))
        self.current_participant = {
            "id": participant_id,
            "condition": condition,
            "demographic": demographic_data,
            "start_time": time.time(),
            "inference_responses": [],
            "survey_responses": [],
            "feedback_messages": []
        }
        return participant_id

    def process_inference_response(self, question_id: str, selected_option: int, selected_reason: str, response_time: float) -> str:
        if not self.current_participant:
            raise ValueError("참가자가 설정되지 않았습니다.")
        response_data = {
            "question_id": question_id,
            "selected_option": selected_option,
            "selected_reason": selected_reason,
            "response_time": response_time,
            "timestamp": datetime.now().isoformat(),
        }
        self.current_participant["inference_responses"].append(response_data)
        feedback = self.feedback_system.generate_feedback(self.current_participant["condition"], selected_reason)
        self.current_participant["feedback_messages"].append(feedback)
        return feedback

    def process_survey_response(self, qid: str, rating: int):
        if not self.current_participant:
            raise ValueError("참가자가 설정되지 않았습니다.")
        self.current_participant["survey_responses"].append({
            "question_id": qid,
            "rating": rating,
            "timestamp": datetime.now().isoformat(),
        })

    def complete_experiment(self) -> ExperimentData:
        if not self.current_participant:
            raise ValueError("참가자가 설정되지 않았습니다.")
        completion_time = time.time() - self.current_participant["start_time"]
        data = ExperimentData(
            participant_id=self.current_participant["id"],
            condition=self.current_participant["condition"],
            demographic=self.current_participant["demographic"],
            inference_responses=self.current_participant["inference_responses"],
            survey_responses=self.current_participant["survey_responses"],
            feedback_messages=self.current_participant["feedback_messages"],
            timestamps={
                "start": datetime.fromtimestamp(self.current_participant["start_time"]).isoformat(),
                "end": datetime.now().isoformat(),
            },
            completion_time=completion_time,
        )
        self.experiment_data.append(data)
        self.current_participant = None
        return data

# =============================================================================
# 3) 유틸/분석 함수
# =============================================================================

def reverse_if_needed(question: SurveyQuestion, rating: int) -> int:
    """7점 리커트 역코딩"""
    return 8 - rating if question.reverse else rating

def calc_category_mean(responses: List[Dict[str, Any]], category: str) -> float:
    """카테고리별 평균"""
    relevant = [q for q in MOTIVATION_QUESTIONS if q.category == category]
    score_list: List[int] = []
    for r in responses:
        q = next((x for x in relevant if x.id == r["question_id"]), None)
        if q is not None:
            score_list.append(reverse_if_needed(q, r["rating"]))
    return sum(score_list) / len(score_list) if score_list else 0.0

def summarize_motivation(responses: List[Dict[str, Any]]) -> Dict[str, float]:
    cats = ["interest_enjoyment","perceived_competence","effort_importance","value_usefulness","autonomy","pressure_tension"]
    return {c: round(calc_category_mean(responses, c), 3) for c in cats}

def ensure_dir(path: str):
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)

def append_row_to_csv(path: str, fieldnames: List[str], row: Dict[str, Any]):
    file_exists = os.path.exists(path)
    with open(path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)

# =============================================================================
# 4) 세션 상태 초기화
# =============================================================================

DEFAULT_N_QUESTIONS = 10

def init_session():
    if "manager" not in st.session_state:
        st.session_state.manager = ExperimentManager()
    ss = st.session_state
    ss.setdefault("phase", "consent")  # consent -> demographic -> instructions -> task -> loading -> feedback -> survey -> debrief
    ss.setdefault("seed", None)
    ss.setdefault("assigned_condition", None)
    ss.setdefault("n_questions", DEFAULT_N_QUESTIONS)
    ss.setdefault("question_order", [])
    ss.setdefault("q_index", 0)
    ss.setdefault("trial_start_ts", None)
    ss.setdefault("selected_option", None)
    ss.setdefault("selected_reason", "")
    ss.setdefault("latest_feedback", "")
    ss.setdefault("participant_id", None)
    ss.setdefault("demographic", {})
    ss.setdefault("results_data", None)

init_session()

# =============================================================================
# 5) 사이드바 (설정/진행)
# =============================================================================

with st.sidebar:
    st.markdown("### ⚙️ 실험 설정")
    st.write("연구·테스트 용으로 항목 수/조건·시드 고정이 가능합니다.")
    seed_input = st.text_input("무작위 시드 (선택)", value=st.session_state.seed or "")
    assign = st.selectbox(
        "피드백 조건 고정 (선택)",
        ["무작위"] + [c.value for c in PraiseCondition],
        index=0
    )
    n_q = st.slider("출제 문항 수", min_value=6, max_value=len(ALL_INFERENCE_QUESTIONS), value=st.session_state.n_questions, step=1)

    colA, colB = st.columns(2)
    with colA:
        if st.button("설정 적용", use_container_width=True):
            st.session_state.seed = int(seed_input) if seed_input.strip().isdigit() else None
            st.session_state.n_questions = int(n_q)
            st.session_state.assigned_condition = None if assign == "무작위" else PraiseCondition(assign)
            st.success("설정이 적용되었습니다. (다음 실험 시작에 반영)")
    with colB:
        if st.button("처음으로", use_container_width=True):
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            init_session()
            st.experimental_rerun()

    st.divider()
    st.caption("Made for 연구용 • 파일 저장은 ./results/ 폴더")

# =============================================================================
# 6) 공용 렌더 함수
# =============================================================================

def heading(title: str, subtitle: Optional[str] = None):
    st.markdown(f"## {title}")
    if subtitle:
        st.markdown(f"<div class='small-muted'>{subtitle}</div>", unsafe_allow_html=True)

def show_mcp_animation(seconds: float = 1.8):
    """각 추론 과제 직후 1회만 호출되는 'MCP 느낌' 전환 애니메이션"""
    st.markdown("<div class='fullscreen-center'>", unsafe_allow_html=True)
    st.markdown("<div class='spinner-ring'></div>", unsafe_allow_html=True)
    st.markdown("<div class='small-muted'>분석 중입니다...</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
    # 단순 sleep 후 다음 페이즈로
    time.sleep(seconds)

def typing_effect(text: str, speed: float = 0.02):
    """AI 피드백 타이핑 애니메이션"""
    ph = st.empty()
    buf = []
    for ch in text:
        buf.append(ch)
        ph.markdown(f"<div class='typing'>{''.join(buf)}</div>", unsafe_allow_html=True)
        time.sleep(speed)

# =============================================================================
# 7) 페이즈별 화면
# =============================================================================

def page_consent():
    heading("연구 참여 동의", "본 실험은 익명으로 진행되며, 응답 데이터는 연구 목적으로만 사용됩니다.")
    with st.expander("상세 동의서 보기", expanded=False):
        st.write("""
        - 참여는 자발적이며 언제든 중단할 수 있습니다.
        - 수집 항목: 성별/연령, 과제 응답, 반응시간, 설문 응답
        - 데이터는 익명화되어 분석됩니다.
        """)
    agree = st.checkbox("위 내용을 이해하였으며 참여에 동의합니다.", value=False)
    if st.button("다음", type="primary", disabled=not agree):
        st.session_state.phase = "demographic"

def page_demographic():
    heading("기초 정보", "연구 결과 분석에 필요한 최소한의 정보를 수집합니다.")
    with st.form("demographic_form", clear_on_submit=False):
        gender = st.selectbox("성별", ["선택하세요", "남성", "여성", "응답하지 않음"])
        age = st.number_input("연령", min_value=18, max_value=80, step=1)
        phone = st.text_input("연락처 (선택)", help="인센티브 지급 등 사후 연락이 필요한 경우만 입력")

        submitted = st.form_submit_button("다음")
        if submitted:
            if gender == "선택하세요":
                st.warning("성별을 선택해 주세요.")
                return
            demo = {"gender": gender, "age": int(age)}
            if phone.strip():
                demo["phone"] = phone.strip()
            # 참가자 생성
            cond = st.session_state.assigned_condition
            pid = st.session_state.manager.create_participant(demo, assigned=cond)
            st.session_state.participant_id = pid
            st.session_state.demographic = demo

            # 문항 샘플링 & 순서
            if st.session_state.seed is not None:
                random.seed(st.session_state.seed)
            order = random.sample(ALL_INFERENCE_QUESTIONS, st.session_state.n_questions)
            st.session_state.question_order = order
            st.session_state.q_index = 0

            # 다음 단계
            st.session_state.phase = "instructions"

def page_instructions():
    heading("과제 안내", "다음과 같은 형식의 추론 과제를 풉니다.")
    st.markdown("""
    - 각 문항은 '설명', '문장', 그리고 5개의 선택지로 구성됩니다.
    - 정답·오답 여부는 **측정되지 않으며**, **해석 근거**를 함께 남겨 주세요.
    - 각 문항 제출 후, **분석 애니메이션(1회)** → **AI 피드백** → 다음 문항 순서로 진행됩니다.
    - 모든 문항 완료 후, 26문항 **학습동기 설문**이 진행됩니다.
    """)
    cond = st.session_state.manager.current_participant["condition"]
    st.info(f"현재 피드백 조건: **{cond.value}** (연구 목적상 자동/무작위 할당 또는 사이드바에서 고정).")

    if st.button("시작하기", type="primary"):
        st.session_state.phase = "task"
        st.session_state.trial_start_ts = time.time()

def page_task():
    q_index = st.session_state.q_index
    questions = st.session_state.question_order
    total = len(questions)
    if q_index >= total:
        # 모든 문항 완료 → 설문으로
        st.session_state.phase = "survey"
        return

    q: Question = questions[q_index]
    heading(f"추론 과제 {q_index+1} / {total}", f"문항 ID: {q.id}")
    st.markdown(f"**설명:** {q.gloss}")
    st.markdown(f"**문장:** {q.stem}")
    st.divider()

    # 선택지 + 근거
    with st.form(f"task_form_{q.id}", clear_on_submit=False):
        choice = st.radio("선택지를 고르세요.", options=list(range(len(q.options))),
                          format_func=lambda i: f"{i+1}. {q.options[i]}",
                          key=f"opt_{q.id}")
        reason = st.text_area("해석/선택 근거를 간단히 작성해 주세요.", key=f"reason_{q.id}")
        ok = st.form_submit_button("제출")

        if ok:
            if reason.strip() == "":
                st.warning("선택 근거를 입력해 주세요.")
                return
            # 반응시간
            start_ts = st.session_state.trial_start_ts or time.time()
            rt = time.time() - start_ts

            # 저장 + 다음 단계(애니메이션)
            st.session_state.selected_option = int(choice)
            st.session_state.selected_reason = reason.strip()
            st.session_state.latest_feedback = st.session_state.manager.process_inference_response(
                question_id=q.id,
                selected_option=int(choice),
                selected_reason=reason.strip(),
                response_time=rt,
            )
            st.session_state.phase = "loading"

def page_loading():
    # MCP 애니메이션 (한 번만)
    show_mcp_animation(seconds=1.6)
    # 다음 단계: feedback
    st.session_state.phase = "feedback"

def page_feedback():
    q_index = st.session_state.q_index
    questions = st.session_state.question_order
    q = questions[q_index]
    feedback = st.session_state.latest_feedback

    st.markdown("#### 🤖 AI 피드백")
    col1, col2 = st.columns([0.12, 0.88])
    with col1:
        st.markdown("<div class='ai-avatar'>AI</div>", unsafe_allow_html=True)
    with col2:
        # 타이핑 애니메이션 (길면 자동 축약)
        txt = feedback
        # 너무 긴 메시지는 타이핑 속도를 조금 빠르게
        spd = 0.015 if len(txt) > 150 else 0.02
        typing_effect(txt, speed=spd)

    st.divider()
    colA, colB = st.columns(2)
    with colA:
        if st.button("다음 문항", type="primary", use_container_width=True):
            st.session_state.q_index += 1
            st.session_state.trial_start_ts = time.time()
            st.session_state.phase = "task"
    with colB:
        remain = len(st.session_state.question_order) - (st.session_state.q_index + 1)
        st.button(f"남은 문항: {remain}개", disabled=True, use_container_width=True)

def page_survey():
    heading("학습 동기 설문 (26문항)", "각 문항에 대해 1(전혀 아니다) ~ 7(매우 그렇다)로 응답해 주세요.")
    with st.form("survey_form"):
        answers: Dict[str, int] = {}
        for q in MOTIVATION_QUESTIONS:
            key = f"sv_{q.id}"
            val = st.radio(
                label=f"{q.id}. {q.text}",
                options=list(range(1, q.scale + 1)),
                horizontal=True,
                key=key
            )
            answers[q.id] = int(val)
            st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

        submitted = st.form_submit_button("설문 제출")
        if submitted:
            # 저장
            for q in MOTIVATION_QUESTIONS:
                st.session_state.manager.process_survey_response(q.id, answers[q.id])
            # 완료 데이터
            data = st.session_state.manager.complete_experiment()
            st.session_state.results_data = data
            st.session_state.phase = "debrief"

def page_debrief():
    data: ExperimentData = st.session_state.results_data
    heading("참여 감사 안내", None)
    st.success("모든 절차가 완료되었습니다. 아래에서 요약과 데이터 저장을 확인하실 수 있습니다.")

    # 요약
    st.markdown("#### 📋 실험 요약")
    st.write(f"- 참가자 ID: {data.participant_id}")
    st.write(f"- 피드백 조건: {data.condition.value}")
    st.write(f"- 완료 시간: {data.completion_time:.2f}초")
    st.write(f"- 추론 과제 응답 수: {len(data.inference_responses)}")
    st.write(f"- 설문 응답 수: {len(data.survey_responses)}")

    # 동기 요약
    mot = summarize_motivation(data.survey_responses)
    st.markdown("#### 🔎 학습 동기 요약(평균)")
    st.json(mot)

    # CSV/JSON 다운로드 + 로컬 저장
    out_dir = os.path.join(os.getcwd(), "results")
    ensure_dir(out_dir)

    # 1) 행(요약) CSV 저장/다운로드
    csv_fields = [
        "participant_id","condition","gender","age","completion_time","avg_response_time",
        "interest_enjoyment","perceived_competence","effort_importance",
        "value_usefulness","autonomy","pressure_tension"
    ]
    resp_times = [r["response_time"] for r in data.inference_responses]
    avg_rt = sum(resp_times)/len(resp_times) if resp_times else 0.0
    row = {
        "participant_id": data.participant_id,
        "condition": data.condition.value,
        "gender": data.demographic.get("gender",""),
        "age": data.demographic.get("age",""),
        "completion_time": round(data.completion_time,3),
        "avg_response_time": round(avg_rt,3),
        **mot,
    }

    # 로컬 CSV 파일에 append
    csv_path = os.path.join(out_dir, "experiment_results.csv")
    append_row_to_csv(csv_path, csv_fields, row)

    # 메모리용 CSV
    csv_buf = io.StringIO()
    cw = csv.DictWriter(csv_buf, fieldnames=csv_fields)
    cw.writeheader()
    cw.writerow(row)
    st.download_button(
        "요약 CSV 다운로드",
        data=csv_buf.getvalue().encode("utf-8"),
        file_name=f"{data.participant_id}_summary.csv",
        mime="text/csv",
    )
    st.caption(f"로컬 저장: `./results/experiment_results.csv` 에 누적 저장")

    # 2) RAW JSON (전문)
    raw_dict = asdict(data)
    json_str = json.dumps(raw_dict, ensure_ascii=False, indent=2)
    json_path = os.path.join(out_dir, f"{data.participant_id}_raw.json")
    with open(json_path, "w", encoding="utf-8") as f:
        f.write(json_str)
    st.download_button(
        "원본 JSON 다운로드",
        data=json_str.encode("utf-8"),
        file_name=f"{data.participant_id}_raw.json",
        mime="application/json",
    )
    st.caption(f"로컬 저장: `./results/{data.participant_id}_raw.json`")

    st.divider()
    if st.button("새 실험 시작", type="primary"):
        # 핵심 상태만 남기고 초기화
        keep = {"seed": st.session_state.seed, "assigned_condition": st.session_state.assigned_condition, "n_questions": st.session_state.n_questions}
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        init_session()
        for k,v in keep.items():
            st.session_state[k] = v
        st.experimental_rerun()

# =============================================================================
# 8) 라우팅
# =============================================================================

PHASE_TO_PAGE = {
    "consent": page_consent,
    "demographic": page_demographic,
    "instructions": page_instructions,
    "task": page_task,
    "loading": page_loading,
    "feedback": page_feedback,
    "survey": page_survey,
    "debrief": page_debrief,
}

PHASE_LABEL = {
    "consent": "참여 동의",
    "demographic": "기초 정보",
    "instructions": "과제 안내",
    "task": "추론 과제",
    "loading": "분석중",
    "feedback": "AI 피드백",
    "survey": "학습 동기 설문",
    "debrief": "종료/저장",
}

st.markdown(f"<div class='badge'>현재 단계: {PHASE_LABEL.get(st.session_state.phase, st.session_state.phase)}</div>", unsafe_allow_html=True)
PHASE_TO_PAGE[st.session_state.phase]()

'''
