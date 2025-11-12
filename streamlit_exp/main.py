#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import random
import time
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from textwrap import dedent
from typing import Any, Dict, List, Optional

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

# --------------------------------------------------------------------------------------
# Streamlit page config & global styling
# --------------------------------------------------------------------------------------

st.set_page_config(page_title="AI 칭찬 연구 설문", layout="centered")

GLOBAL_CSS = dedent(
    """
    <style>
    :root { --fs-base: 16px; --lh-base: 1.65; }
    #MainMenu, header, footer, [data-testid="stToolbar"] { display: none !important; }
    html, body,
    .stApp,
    [data-testid="stAppViewContainer"],
    [data-testid="stAppViewContainer"] > .main,
    section.main {
      margin-top: 0 !important;
      padding-top: 0 !important;
    }
    [data-testid="stAppViewContainer"] > .main > div,
    .main .block-container,
    section.main > div.block-container {
      padding-top: 0 !important;
      padding-bottom: 20px !important;
    }
    h1, .stMarkdown h1 { margin-top: 0 !important; margin-bottom: 12px !important; line-height: 1.2; }
    h2, .stMarkdown h2 { margin-top: 0 !important; margin-bottom: 10px !important; }
    p, .stMarkdown p   { margin-top: 0 !important; }
    .anthro-title { margin-top: 0 !important; }
    html, body { overflow-x: hidden !important; }
    div[data-testid="stProgress"] { margin-bottom: 0.4rem !important; }
    .mcp-footer { margin-top: 0.6rem !important; }
    </style>
    """
)

st.markdown(GLOBAL_CSS, unsafe_allow_html=True)

BASE_DIR = Path(__file__).resolve().parent

# --------------------------------------------------------------------------------------
# Data classes and experiment content (ported 1:1 from skywork.py)
# --------------------------------------------------------------------------------------


class PraiseCondition(Enum):
    EMOTIONAL_SPECIFIC = "emotional_specific"
    COMPUTATIONAL_SPECIFIC = "computational_specific"
    EMOTIONAL_SUPERFICIAL = "emotional_superficial"
    COMPUTATIONAL_SUPERFICIAL = "computational_superficial"


@dataclass
class Question:
    id: str
    gloss: str
    stem: str
    options: List[str]
    answer_idx: int
    reason_idx: int
    category: str = "inference"


@dataclass
class SurveyQuestion:
    id: str
    text: str
    scale: int = 7
    reverse: bool = False
    category: str = "motivation"


@dataclass
class ExperimentData:
    participant_id: str
    condition: str  # emotional_specific, computational_specific, emotional_superficial, computational_superficial
    demographic: Dict[str, Any]
    inference_responses: List[Dict[str, Any]]
    survey_responses: List[Dict[str, Any]]
    feedback_messages: List[str]
    timestamps: Dict[str, str]
    completion_time: float


NOUN_QUESTIONS: List[Question] = [
    Question(
        id="N1",
        gloss="사람들이 소유한 개의 집을 나타내는 올바른 표현을 선택하세요.",
        stem="사람들이 소유한 개의 집을 나타내는 올바른 표현은 무엇입니까?",
        options=[
            "nuk-t-mi sua-mi ani",
            "nuk-mi sua-t-mi ani",
            "nuk-t sua-mi ani",
            "nuk-mi sua-mi ani",
            "nuk sua-t-mi ani",
        ],
        answer_idx=0,
        reason_idx=1,
    ),
    Question(
        id="N2",
        gloss="사람이 집과 음식을 보는 상황에서 목적 표지가 올바르게 사용된 문장을 선택하세요.",
        stem="'nuk _____ taku-na' (사람이 _____를 본다)에서 빈 칸에 들어갈 올바른 표현은?",
        options=[
            "ani-ka ama pira-ka",
            "ani-ka ama pira",
            "ani ama pira-ka",
            "ani ama pira",
            "ani-ka ama pira-t",
        ],
        answer_idx=0,
        reason_idx=2,
    ),
    Question(
        id="N3",
        gloss="사람의 개들이 소유한 물을 나타내는 올바른 표현을 선택하세요.",
        stem="사람의 개들이 소유한 물을 나타내는 올바른 표현은 무엇입니까?",
        options=[
            "nuk-mi sua-t-mi ika",
            "nuk-t-mi sua-mi ika",
            "nuk-mi sua-mi ika",
            "nuk sua-t-mi ika",
            "nuk-t sua-mi ika",
        ],
        answer_idx=0,
        reason_idx=3,
    ),
    Question(
        id="N4",
        gloss="사람이 개의 집들을 보는 상황을 나타내는 올바른 표현을 선택하세요.",
        stem="'nuk _____ taku-na' (사람이 _____를 본다)에서 빈 칸에 들어갈 올바른 표현은?",
        options=[
            "sua-mi ani-t-mi",
            "sua-t-mi ani-mi",
            "sua-mi ani-mi",
            "sua-t ani-mi",
            "sua ani-t-mi",
        ],
        answer_idx=0,
        reason_idx=0,
    ),
    Question(
        id="N5",
        gloss="사람들의 개가 소유한 집을 나타내는 올바른 표현을 선택하세요.",
        stem="사람들의 개가 소유한 집을 나타내는 올바른 표현은 무엇입니까?",
        options=[
            "nuk-t-mi sua-mi ani",
            "nuk-mi sua-t-mi ani",
            "nuk-mi sua-mi ani",
            "nuk-t sua-mi ani",
            "nuk sua-t-mi ani",
        ],
        answer_idx=0,
        reason_idx=4,
    ),
    Question(
        id="N6",
        gloss="사람과 개가 각각 소유한 물을 나타내는 올바른 표현을 선택하세요.",
        stem="사람과 개가 각각 소유한 물을 나타내는 올바른 표현은 무엇입니까?",
        options=[
            "nuk-mi ama sua-mi ika",
            "nuk-t-mi ama sua-t-mi ika",
            "nuk-mi ama sua-t-mi ika",
            "nuk ama sua ika",
            "nuk-t ama sua-t ika",
        ],
        answer_idx=0,
        reason_idx=1,
    ),
    Question(
        id="N7",
        gloss="개들이 소유한 물을 나타내는 올바른 표현을 선택하세요.",
        stem="개들이 소유한 물을 나타내는 올바른 표현은 무엇입니까?",
        options=[
            "sua-t-mi ika",
            "sua-mi ika",
            "sua-t ika",
            "sua ika-mi",
            "sua ika-t",
        ],
        answer_idx=0,
        reason_idx=2,
    ),
    Question(
        id="N8",
        gloss="사람들이 집들과 음식을 보는 상황을 나타내는 올바른 표현을 선택하세요.",
        stem="'nuk ____ taku-na' (사람들이 ____를 본다)에서 빈 칸에 들어갈 올바른 표현은?",
        options=[
            "ani-t-mi ama pira-ka",
            "ani-mi ama pira-ka",
            "ani-t ama pira-ka",
            "ani-t-mi ama pira",
            "ani ama pira-ka",
        ],
        answer_idx=0,
        reason_idx=3,
    ),
    Question(
        id="N9",
        gloss="사람이 소유한 그 집을 나타내는 올바른 표현을 선택하세요.",
        stem="사람이 소유한 그 집을 나타내는 올바른 표현은 무엇입니까?",
        options=[
            "nuk-mi ani na",
            "nuk-t-mi ani na",
            "nuk ani na",
            "nuk-mi ani-t na",
            "nuk-t ani na",
        ],
        answer_idx=0,
        reason_idx=0,
    ),
    Question(
        id="N10",
        gloss="사람이 소유한 개의 집과 물을 보는 상황을 나타내는 올바른 표현을 선택하세요.",
        stem="'nuk ____ taku-na' (사람이 ____를 본다)에서 빈 칸에 들어갈 올바른 표현은?",
        options=[
            "sua-mi ani-ka ama ika-ka",
            "sua-t-mi ani-ka ama ika-ka",
            "sua-mi ani ama ika",
            "sua-mi ani-ka ama ika",
            "sua ani-ka ama ika-ka",
        ],
        answer_idx=0,
        reason_idx=4,
    ),
    Question(
        id="N11",
        gloss="여러 사람들의 각각 다른 개들을 나타내는 올바른 표현을 선택하세요.",
        stem="여러 사람들의 각각 다른 개들을 나타내는 올바른 표현은 무엇입니까?",
        options=[
            "nuk-t-mi sua-t-mi",
            "nuk-mi sua-mi",
            "nuk-t-mi sua-mi",
            "nuk-mi sua-t-mi",
            "nuk-t sua-t",
        ],
        answer_idx=0,
        reason_idx=1,
    ),
    Question(
        id="N12",
        gloss="사람이 개들의 집들을 모두 보는 상황을 나타내는 올바른 표현을 선택하세요.",
        stem="'nuk ____ taku-na' (사람이 ____를 본다)에서 빈 칸에 들어갈 올바른 표현은?",
        options=[
            "sua-t-mi ani-t-mi",
            "sua-mi ani-mi",
            "sua-t-mi ani-mi",
            "sua-mi ani-t-mi",
            "sua-t ani-t",
        ],
        answer_idx=0,
        reason_idx=2,
    ),
]

VERB_QUESTIONS: List[Question] = [
    Question(
        id="V1",
        gloss="사람이 지금 집을 보고 있는 중이라는 의미를 나타내는 올바른 동사 형태를 선택하세요.",
        stem="'nuk ani-ka ____' (사람이 집을 ____)에서 빈 칸에 들어갈 올바른 동사 형태는?",
        options=["taku-li-na", "taku-na", "taku-mu-na", "taku-li-ki", "taku-tu"],
        answer_idx=0,
        reason_idx=1,
    ),
    Question(
        id="V2",
        gloss="사람이 어제 저녁 전에 이미 음식을 만들어 두었다는 의미를 나타내는 올바른 동사 형태를 선택하세요.",
        stem="'nuk pira-ka ____' (사람이 음식을 ____)에서 빈 칸에 들어갈 올바른 동사 형태는?",
        options=["siku-mu-tu", "siku-tu", "siku-li-tu", "siku-mu-na", "siku-ki"],
        answer_idx=0,
        reason_idx=4,
    ),
    Question(
        id="V3",
        gloss="개가 내일까지 물을 다 먹어 놓을 것이라는 의미를 나타내는 올바른 동사 형태를 선택하세요.",
        stem="'sua ika-ka ____' (개가 물을 ____)에서 빈 칸에 들어갈 올바른 동사 형태는?",
        options=["niri-mu-ki", "niri-ki", "niri-li-ki", "niri-mu-na", "niri-tu"],
        answer_idx=0,
        reason_idx=1,
    ),
    Question(
        id="V4",
        gloss="개가 어제 음식을 먹었다는 의미를 나타내는 올바른 동사 형태를 선택하세요.",
        stem="'sua pira-ka ____' (개가 음식을 ____)에서 빈 칸에 들어갈 올바른 동사 형태는?",
        options=["niri-tu", "niri-mu-tu", "niri-li-tu", "niri-na", "niri-ki"],
        answer_idx=0,
        reason_idx=0,
    ),
    Question(
        id="V5",
        gloss="사람이 이미 물을 보았다는 의미를 나타내는 올바른 동사 형태를 선택하세요.",
        stem="'nuk ika-ka ____' (사람이 물을 ____)에서 빈 칸에 들어갈 올바른 동사 형태는?",
        options=["taku-mu-na", "taku-na", "taku-tu", "taku-li-na", "taku-mu-tu"],
        answer_idx=0,
        reason_idx=1,
    ),
    Question(
        id="V6",
        gloss="사람과 개가 곧 음식을 보는 중일 것이라는 의미를 나타내는 올바른 동사 형태를 선택하세요.",
        stem="'nuk ama sua pira-ka ____' (사람과 개가 음식을 ____)에서 빈 칸에 들어갈 올바른 동사 형태는?",
        options=["taku-li-ki", "taku-ki", "taku-li-na", "taku-mu-ki", "taku-tu"],
        answer_idx=0,
        reason_idx=0,
    ),
    Question(
        id="V7",
        gloss="개가 지금 집을 보는 중이라는 의미를 나타내는 올바른 동사 형태를 선택하세요.",
        stem="'sua ani-ka ____' (개가 집을 ____)에서 빈 칸에 들어갈 올바른 동사 형태는?",
        options=["taku-li-na", "taku-na-li", "li-taku-na", "taku-na", "taku-li-tu"],
        answer_idx=0,
        reason_idx=2,
    ),
    Question(
        id="V8",
        gloss="사람이 그때까지 음식을 다 먹어 둘 것이라는 의미를 나타내는 올바른 동사 형태를 선택하세요.",
        stem="'nuk pira-ka ____' (사람이 음식을 ____)에서 빈 칸에 들어갈 올바른 동사 형태는?",
        options=["niri-mu-ki", "niri-li-ki", "niri-ki", "niri-mu-tu", "niri-na"],
        answer_idx=0,
        reason_idx=3,
    ),
    Question(
        id="V9",
        gloss="사람이 항상 물을 마신다는 의미를 나타내는 올바른 동사 형태를 선택하세요.",
        stem="'nuk ika-ka ____' (사람이 물을 ____)에서 빈 칸에 들어갈 올바른 동사 형태는?",
        options=["niri-na", "niri-li-na", "niri-mu-na", "niri-tu", "niri-ki"],
        answer_idx=0,
        reason_idx=0,
    ),
    Question(
        id="V10",
        gloss="사람이 집을 본 뒤에 음식을 먹었다는 의미를 나타내는 올바른 동사 형태를 선택하세요.",
        stem="'(ani-ka taku-mu-tu) ama pira-ka ____' (집을 본 뒤에 음식을 ____)에서 빈 칸에 들어갈 올바른 동사 형태는?",
        options=["niri-tu", "niri-mu-tu", "niri-li-tu", "niri-na", "niri-ki"],
        answer_idx=0,
        reason_idx=4,
    ),
    Question(
        id="V11",
        gloss="개들이 동시에 물을 마시고 있는 중이라는 의미를 나타내는 올바른 동사 형태를 선택하세요.",
        stem="'sua-t-mi ika-ka ____' (개들이 물을 ____)에서 빈 칸에 들어갈 올바른 동사 형태는?",
        options=["niri-li-na", "niri-na", "niri-li-tu", "niri-mu-na", "niri-ki"],
        answer_idx=0,
        reason_idx=1,
    ),
    Question(
        id="V12",
        gloss="사람이 내일 아침까지 집을 다 지어 놓을 것이라는 의미를 나타내는 올바른 동사 형태를 선택하세요.",
        stem="'nuk ani-ka ____' (사람이 집을 ____)에서 빈 칸에 들어갈 올바른 동사 형태는?",
        options=["siku-mu-ki", "siku-ki", "siku-li-ki", "siku-mu-tu", "siku-na"],
        answer_idx=0,
        reason_idx=3,
    ),
]

ALL_INFERENCE_QUESTIONS = NOUN_QUESTIONS + VERB_QUESTIONS

MOTIVATION_QUESTIONS: List[SurveyQuestion] = [
    SurveyQuestion(
        "IE1", "이 과제를 하는 동안 즐거웠다.", category="interest_enjoyment"
    ),
    SurveyQuestion("IE2", "이 과제는 재미있었다.", category="interest_enjoyment"),
    SurveyQuestion(
        "IE3", "이 과제가 지루했다.", reverse=True, category="interest_enjoyment"
    ),
    SurveyQuestion(
        "IE4", "이 과제를 하는 것이 흥미로웠다.", category="interest_enjoyment"
    ),
    SurveyQuestion(
        "IE5", "이 과제를 하면서 시간이 빨리 지나갔다.", category="interest_enjoyment"
    ),
    SurveyQuestion("IE6", "이 과제에 몰입할 수 있었다.", category="interest_enjoyment"),
    SurveyQuestion(
        "IE7",
        "이 과제를 계속 하고 싶다는 생각이 들었다.",
        category="interest_enjoyment",
    ),
    SurveyQuestion(
        "PC1", "이 과제를 잘 수행했다고 생각한다.", category="perceived_competence"
    ),
    SurveyQuestion(
        "PC2", "이 과제에서 만족스러운 결과를 얻었다.", category="perceived_competence"
    ),
    SurveyQuestion(
        "PC3", "이 과제를 수행하는 데 능숙했다.", category="perceived_competence"
    ),
    SurveyQuestion(
        "PC4", "이 과제가 너무 어려웠다.", reverse=True, category="perceived_competence"
    ),
    SurveyQuestion(
        "PC5",
        "이 과제를 완수할 수 있다는 자신감이 있었다.",
        category="perceived_competence",
    ),
    SurveyQuestion(
        "PC6", "이 과제에서 좋은 성과를 낼 수 있었다.", category="perceived_competence"
    ),
    SurveyQuestion(
        "EI1", "이 과제에 많은 노력을 기울였다.", category="effort_importance"
    ),
    SurveyQuestion(
        "EI2", "이 과제를 잘 수행하는 것이 중요했다.", category="effort_importance"
    ),
    SurveyQuestion("EI3", "이 과제에 최선을 다했다.", category="effort_importance"),
    SurveyQuestion(
        "EI4", "이 과제에 집중하려고 노력했다.", category="effort_importance"
    ),
    SurveyQuestion(
        "EI5", "이 과제를 대충 했다.", reverse=True, category="effort_importance"
    ),
    SurveyQuestion(
        "VU1", "이 과제는 나에게 가치가 있었다.", category="value_usefulness"
    ),
    SurveyQuestion(
        "VU2", "이 과제를 통해 유용한 것을 배웠다.", category="value_usefulness"
    ),
    SurveyQuestion(
        "VU3", "이 과제는 나에게 도움이 되었다.", category="value_usefulness"
    ),
    SurveyQuestion(
        "VU4", "이 과제는 시간 낭비였다.", reverse=True, category="value_usefulness"
    ),
    SurveyQuestion(
        "AU1", "이 과제를 수행하는 방식을 스스로 선택할 수 있었다.", category="autonomy"
    ),
    SurveyQuestion(
        "AU2", "이 과제를 하면서 자유롭게 행동할 수 있었다.", category="autonomy"
    ),
    SurveyQuestion("PT1", "이 과제를 하는 동안 긴장했다.", category="pressure_tension"),
    SurveyQuestion(
        "PT2", "이 과제를 하면서 스트레스를 받았다.", category="pressure_tension"
    ),
]

MOTIVATION_BY_ID = {q.id: q for q in MOTIVATION_QUESTIONS}

# --------------------------------------------------------------------------------------
# Feedback + analysis tooling (ported from skywork.py)
# --------------------------------------------------------------------------------------


class AIFeedbackSystem:
    def __init__(self) -> None:
        self.feedback_templates: Dict[str, List[str]] = {
            "emotional_specific": [
                "🎉 정말 훌륭해요! 특히 '{reason}'라고 생각하신 부분이 매우 인상적입니다. 이런 깊이 있는 사고방식은 언어학습에서 중요한 능력이에요.",
                "👏 와, 정말 대단하세요! '{reason}'라는 추론 과정이 너무나 논리적이고 체계적이네요. 차근차근 분석하는 능력이 특별한 재능입니다.",
                "🌟 놀라운 통찰력이에요! '{reason}'라고 판단하신 근거가 탁월합니다. 이런 관찰력과 분석력은 언어 전문가의 자질을 보여줍니다.",
            ],
            "computational_specific": [
                "📊 분석 결과가 매우 우수합니다. '{reason}'라는 추론 패턴이 언어 규칙 체계와 94.7% 일치도를 보입니다.",
                "🔍 데이터 처리 성능이 탁월합니다. '{reason}'라는 논리 경로는 정확도 지표에서 상위 8.3% 수준입니다.",
                "⚙️ 인지 처리 메커니즘이 최적 상태입니다. '{reason}'라는 분석 프로세스는 규칙 데이터와 97.2% 매칭률을 기록했습니다.",
            ],
            "emotional_superficial": [
                "🎉 정말 훌륭한 답변이에요! 언어 감각이 뛰어나네요. 계속 이런 멋진 모습 보여주세요!",
                "👏 와, 정말 대단해요! 언어에 대한 감각이 예리합니다. 앞으로도 놀라운 실력 기대할게요!",
                "💫 정말 인상적이에요! 독특한 사고방식이 돋보였습니다. 이런 창의적 접근법은 보기 드문 능력입니다.",
            ],
            "computational_superficial": [
                "📊 시스템 분석 결과 우수한 성능을 보였습니다. 패턴 인식 능력이 최적화된 상태입니다.",
                "🔍 데이터 처리 효율성이 크게 개선되었습니다. 정확도와 속도가 동시에 향상되었습니다.",
                "⚙️ 인지 처리 시스템이 안정적으로 작동했습니다. 전체 처리 효율성이 개선되었습니다.",
            ],
        }

    @staticmethod
    def _key_of(condition: Any) -> str:
        if isinstance(condition, PraiseCondition):
            return condition.value
        return str(condition)

    def generate_feedback(self, condition: Any, selected_reason: str) -> str:
        key = self._key_of(condition)
        templates = (
            self.feedback_templates.get(key)
            or self.feedback_templates["emotional_specific"]
        )
        template = random.choice(templates)
        return (
            template.format(reason=selected_reason) if "specific" in key else template
        )


class ExperimentManager:
    def __init__(self) -> None:
        self.feedback_system = AIFeedbackSystem()
        self.current_participant: Optional[Dict[str, Any]] = None

    def create_participant(
        self,
        demographic_data: Dict[str, Any],
        assigned_condition: Optional[PraiseCondition] = None,
    ) -> str:
        participant_id = (
            f"P_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{random.randint(1000, 9999)}"
        )
        condition_enum = assigned_condition or random.choice(list(PraiseCondition))
        condition = condition_enum.value
        self.current_participant = {
            "id": participant_id,
            "condition": condition,
            "demographic": demographic_data,
            "start_time": time.time(),
            "inference_responses": [],
            "survey_responses": [],
            "feedback_messages": [],
        }
        return participant_id

    def process_inference_response(
        self,
        question_id: str,
        selected_option: int,
        selected_reason: str,
        response_time: float,
    ) -> str:
        if not self.current_participant:
            raise ValueError("참가자 정보가 초기화되지 않았습니다.")
        record = {
            "question_id": question_id,
            "selected_option": selected_option,
            "selected_reason": selected_reason,
            "response_time": response_time,
            "timestamp": datetime.now().isoformat(),
        }
        self.current_participant["inference_responses"].append(record)
        feedback = self.feedback_system.generate_feedback(
            self.current_participant["condition"], selected_reason
        )
        self.current_participant["feedback_messages"].append(feedback)
        return feedback

    def process_survey_response(self, question_id: str, rating: int) -> None:
        if not self.current_participant:
            raise ValueError("참가자 정보가 초기화되지 않았습니다.")
        self.current_participant["survey_responses"].append(
            {
                "question_id": question_id,
                "rating": rating,
                "timestamp": datetime.now().isoformat(),
            }
        )

    def complete_experiment(self) -> ExperimentData:
        if not self.current_participant:
            raise ValueError("참가자 정보가 초기화되지 않았습니다.")
        completion_time = time.time() - self.current_participant["start_time"]
        data = ExperimentData(
            participant_id=self.current_participant["id"],
            condition=self.current_participant["condition"],
            demographic=self.current_participant["demographic"],
            inference_responses=self.current_participant["inference_responses"],
            survey_responses=self.current_participant["survey_responses"],
            feedback_messages=self.current_participant["feedback_messages"],
            timestamps={
                "start": datetime.fromtimestamp(
                    self.current_participant["start_time"]
                ).isoformat(),
                "end": datetime.now().isoformat(),
            },
            completion_time=completion_time,
        )
        self.current_participant = None
        return data


class DataAnalyzer:
    def __init__(self, experiment_data: List[ExperimentData]) -> None:
        self.data = experiment_data

    def get_motivation_scores(self) -> Dict[str, Dict[str, float]]:
        scores: Dict[str, Dict[str, List[float]]] = {}
        for d in self.data:
            key = d.condition
            scores.setdefault(
                key,
                {
                    "interest_enjoyment": [],
                    "perceived_competence": [],
                    "effort_importance": [],
                    "value_usefulness": [],
                    "autonomy": [],
                    "pressure_tension": [],
                },
            )
            for response in d.survey_responses:
                question = MOTIVATION_BY_ID.get(response["question_id"])
                if question:
                    rating = response["rating"]
                    if question.reverse:
                        rating = question.scale + 1 - rating
                    scores[key][question.category].append(rating)
        return {
            condition: {
                cat: (sum(vals) / len(vals) if vals else 0.0)
                for cat, vals in categories.items()
            }
            for condition, categories in scores.items()
        }


# --------------------------------------------------------------------------------------
# Consent / instructions HTML (from main_1110ver orgin.py)
# --------------------------------------------------------------------------------------

COMMON_CSS = """
<style>
  :root { --fs-base:16px; --lh-base:1.65; }
  .consent-wrap, .agree-wrap, .privacy-wrap{
    box-sizing:border-box; max-width:920px; margin:0 auto 10px;
    padding:18px 16px 22px; background:#fff; border:1px solid #E5E7EB; border-radius:12px;
    font-size:var(--fs-base); line-height:var(--lh-base); color:#111827; word-break:keep-all;
  }
  @media (max-width:640px){
    .consent-wrap, .agree-wrap, .privacy-wrap{ padding:14px 12px 18px; border-radius:10px; }
  }
  .consent-wrap h1, .privacy-wrap h1{ font-size:1.5em; margin:0 0 12px; font-weight:800; letter-spacing:.2px; }
  .agree-wrap .agree-title{ font-weight:800; text-align:center; margin-bottom:12px; font-size:1.25em; }
  .consent-wrap .subtitle{ font-size:1.0em; color:#374151; margin-bottom:14px; }
  .consent-wrap h2, .privacy-wrap h2{ font-size:1.2em; margin:20px 0 8px; font-weight:700; border-top:1px solid #F3F4F6; padding-top:14px; }
  .consent-wrap p, .agree-wrap p, .privacy-wrap p{ margin:6px 0; }
  .agree-list{ margin:10px 0 0 0; padding-left:0; list-style:none; }
  .agree-list li{ margin:10px 0; }
  .agree-num{ font-weight:800; margin-right:6px; }
  .inline-label{ font-weight:600; }
  .privacy-table{ width:100%; border-collapse:collapse; table-layout:fixed; border:2px solid #111827; margin-bottom:14px; }
  .privacy-table th, .privacy-table td{ border:1px solid #111827; padding:10px 12px; vertical-align:top; }
  .privacy-table th{ width:30%; background:#F3F4F6; text-align:left; font-weight:700; }
  .privacy-note{ margin:10px 0; padding:10px 12px; border:1px solid #111827; background:#F9FAFB; }
  .privacy-bullets{ margin-top:12px; padding-left:18px; }
  .privacy-bullets li{ margin:4px 0; }
  @media print{
    .consent-wrap, .agree-wrap, .privacy-wrap{ border:none; max-width:100%; }
    .stSlider, .stButton, .stAlert{ display:none !important; }
  }
</style>
"""

CONSENT_HTML = """
<div class="consent-wrap">
  <h1>연구대상자 설명문</h1>
  <div class="subtitle"><strong>제목: </strong>인공지능 에이전트의 피드백 방식이 학습에 미치는 영향 탐색 연구</div>
  <h2>1. 연구 목적</h2>
  <p>최근 과학기술의 발전과 함께 인공지능(AI)은 다양한 학습 환경에서 활용되고 있습니다. 본 연구는 AI 에이전트가 제공하는 칭찬(피드백) 방식이 학습자의 학습 동기에 어떠한 영향을 미치는지 경험적으로 검증합니다.</p>
  <h2>2. 연구 참여 대상</h2>
  <p>만 18세 이상 한국어 사용자를 대상으로 하며, 문장 이해가 어려운 경우 제외될 수 있습니다.</p>
  <h2>3. 연구 방법</h2>
  <p>의인화 및 성취 관련 설문 56문항, 추론 과제 2회차, AI 피드백 확인, 학습 동기 설문, 연락처 입력 순으로 진행되며 약 10~15분 소요됩니다.</p>
  <h2>4. 연구 참여 기간</h2>
  <p>링크가 활성화된 기간 내 1회 참여 가능합니다.</p>
  <h2>5. 연구 참여 보상</h2>
  <p>1500원 상당의 기프티콘이 발송되며, 휴대폰 번호를 입력하지 않으면 보상이 어려울 수 있습니다.</p>
  <h2>6. 위험요소 및 조치</h2>
  <p>지루함, AI 평가에 대한 불편감 등 경미한 불편감을 느낄 수 있으며, 언제든지 연구를 중단할 수 있습니다.</p>
  <h2>7. 개인정보와 비밀보장</h2>
  <p>성별, 연령, 휴대폰 번호를 수집하며 연구 종료 후 3년간 안전하게 보관 후 폐기됩니다.</p>
  <h2>8. 자발적 참여와 중지</h2>
  <p>자발적으로 참여하며 언제든 중단할 수 있습니다. 연구 중단 시 불이익이 없습니다.</p>
  <h2>* 문의</h2>
  <p>가톨릭대학교 발달심리학 오현택 (010-6532-3161, toh315@gmail.com)</p>
</div>
"""

AGREE_HTML = """
<div class="agree-wrap">
  <div class="agree-title">동 의 서</div>
  <p><strong>연구제목:</strong> 인공지능 에이전트의 피드백 방식이 학습에 미치는 영향 탐색 연구</p>
  <ol class="agree-list">
    <li><span class="agree-num">1.</span>연구 설명문을 충분히 이해하였습니다.</li>
    <li><span class="agree-num">2.</span>연구 참여 시 발생할 위험과 이득을 숙지하였습니다.</li>
    <li><span class="agree-num">3.</span>자발적으로 연구 참여에 동의합니다.</li>
    <li><span class="agree-num">4.</span>연구에서 수집되는 개인정보 처리에 동의합니다.</li>
    <li><span class="agree-num">5.</span>연구 관련 자료 열람 가능성에 동의합니다.</li>
    <li><span class="agree-num">6.</span>언제든 참여를 철회할 수 있으며 불이익이 없음을 이해합니다.</li>
  </ol>
</div>
"""

PRIVACY_HTML = """
<div class="privacy-wrap">
  <h1>연구참여자 개인정보 수집∙이용 동의서</h1>
  <h2>[ 개인정보 수집∙이용에 대한 동의 ]</h2>
  <table class="privacy-table">
    <tr>
      <th>수집 개인정보</th>
      <td>성별, 나이, 휴대폰 번호</td>
    </tr>
    <tr>
      <th>수집 및 이용목적</th>
      <td>
        <p>연구 수행 및 논문 작성을 위한 기초 데이터</p>
        <ol>
          <li>연구 수행: 성별, 나이, 휴대폰 번호</li>
          <li>민감정보는 수집하지 않습니다.</li>
        </ol>
      </td>
    </tr>
    <tr>
      <th>제3자 제공 및 목적 외 이용</th>
      <td>법적 요구 또는 IRB 검증 목적에 한해 자료를 열람할 수 있습니다.</td>
    </tr>
    <tr>
      <th>보유 및 이용기간</th>
      <td>연구 종료 후 3년간 보관 후 안전하게 폐기합니다.</td>
    </tr>
  </table>
  <p class="privacy-note">※ 동의를 거부할 수 있으나, 그 경우 연구 참여가 어려울 수 있습니다.</p>
</div>
"""

GRAMMAR_INFO_MD = r"""
**어휘 예시**  
- *ani* = 집,  *nuk* = 사람,  *sua* = 개,  *ika* = 물,  *pira* = 음식  
- *taku* = 보다,  *niri* = 먹다,  *siku* = 만들다

**명사구(NP) 규칙**  
- 소유: 명사 뒤 `-mi` (예: *nuk-mi ani* = 사람의 집)  
- 복수: `-t`; 복수+소유는 `-t-mi`  
- 목적 표지: NP 오른쪽 끝에 `-ka` (등위 구조에서도 마지막 항만)  
- 어순: 바깥 소유자 → 안쪽 소유자 → 머리 명사  
- 정관 `-ri`: NP 말단, `-ka` 앞 위치

**동사 시제·상(TAM)**  
- 시제: `-na`(현재), `-tu`(과거), `-ki`(미래)  
- 상: `-mu`(완료), `-li`(진행)  
- 순서: 동사 + 상 + 시제 (예: *niri-mu-tu*)  
- 맥락 단서: 이미/항상/어제/내일까지 등으로 시제·상을 결정
"""

REASON_NOUN_LABELS = [
    "소유 연쇄 어순(바깥→안쪽→머리)",
    "복수·소유 결합(…-t-mi)",
    "우측 결합 목적 표지(-ka)",
    "정관(-ri) 위치",
    "등위 구조에서의 표지 배치",
]

REASON_VERB_LABELS = [
    "시제 단서 해석(어제/내일/항상)",
    "상(완료·진행) 단서 해석(이미/…하는 중)",
    "형태소 순서: 동사+상+시제",
    "‘…까지/후/전’ 단서에 따른 완료 선택",
    "연결문에서 시제 일관성 유지",
]

# --------------------------------------------------------------------------------------
# JS helpers (scroll + MCP animation) kept from scaffold
# --------------------------------------------------------------------------------------


def scroll_top_js(nonce: Optional[int] = None) -> None:
    nonce = nonce or st.session_state.get("_scroll_nonce", 0)
    st.session_state["_scroll_nonce"] = nonce + 1
    script = """
        <script id="goTop-{nonce}">
        (function(){{
          function goTop(){{
            try {{
              var pdoc = window.parent && window.parent.document;
              var sect = pdoc && pdoc.querySelector && pdoc.querySelector('section.main');
              if (sect && sect.scrollTo) sect.scrollTo({{top:0,left:0,behavior:'instant'}});
            }} catch(e) {{}}
            try {{
              window.scrollTo({{top:0,left:0,behavior:'instant'}});
              document.documentElement && document.documentElement.scrollTo && document.documentElement.scrollTo(0,0);
              document.body && document.body.scrollTo && document.body.scrollTo(0,0);
            }} catch(e) {{}}
          }}
          goTop();
          if (window.requestAnimationFrame) requestAnimationFrame(goTop);
          setTimeout(goTop, 25);
          setTimeout(goTop, 80);
          setTimeout(goTop, 180);
          setTimeout(goTop, 320);
        }})();
        </script>
    """.replace(
        "{nonce}", str(nonce)
    )
    st.markdown(script, unsafe_allow_html=True)


def run_mcp_motion(round_no: int) -> None:
    logs = [
        "[INFO][COVNOX] Initializing… booting inference-pattern engine",
        "[INFO][COVNOX] Loading rule set: possessive(-mi), plural(-t), object(-ka), tense(-na/-tu/-ki), connector(ama)",
        "[INFO][COVNOX] Collecting responses… building 12-item choice hash",
        "[OK][COVNOX] Response hash map constructed",
        "[INFO][COVNOX] Running grammatical marker detection",
        "[OK][COVNOX] Marker usage log: -mi/-t/-ka/-na/-tu/-ki/ama",
        "[INFO][COVNOX] Parsing rationale tags (single-select)",
        "[OK][COVNOX] Rationale normalization complete",
        "[INFO][COVNOX] Computing rule-match consistency",
        "[OK][COVNOX] Consistency matrix updated",
        "[INFO][COVNOX] Checking tense/object conflicts",
        "[OK][COVNOX] No critical conflicts · reasoning path stable",
        "[INFO][COVNOX] Analyzing response time (persistence index)",
        "[OK][COVNOX] Persistence index calculated",
        "[INFO][COVNOX] Synthesizing overall inference profile",
        "[OK][COVNOX] Profile composed · selecting feedback template",
        "[INFO][COVNOX] Natural language phrasing optimization",
        "[OK][COVNOX] Fluency/consistency checks passed",
        "[✔][COVNOX] Analysis complete. Rendering results…",
    ]
    html = """
    <style>
      html,body{margin:0;padding:0;background:#0b0f1a;color:#e6edf3;}
      .mcp-overlay{position:fixed;inset:0;z-index:9999;background:#0b0f1a;
        display:flex;flex-direction:column;align-items:center;justify-content:flex-start;padding-top:12vh;
        font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto;}
      .covnox-title{margin:0;text-align:center;font-weight:800;font-size:clamp(26px,5.2vw,46px);}
      .covnox-sub{font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
        font-size:clamp(12px,2.4vw,16px);opacity:.9;margin:14px 0 20px 0;text-align:center;}
      .mcp-bar{width:min(820px,86vw);height:8px;background:#1b2330;border-radius:999px;overflow:hidden;}
      .mcp-fill{height:100%;width:0%;background:#2f81f7;transition:width .38s linear;}
    </style>
    <div class="mcp-overlay" id="mcp-overlay">
      <h1 class="covnox-title">🧩 COVNOX: Inference Pattern Analysis</h1>
      <div class="covnox-sub" id="mcp-log">Initializing…</div>
      <div class="mcp-bar"><div class="mcp-fill" id="mcp-fill"></div></div>
    </div>
    <script>
    (function(){
      var msgs = __LOGS__;
      var round = __ROUND__;
      var logEl = document.getElementById('mcp-log');
      var fill  = document.getElementById('mcp-fill');
      var overlay = document.getElementById('mcp-overlay');
      var i=0, t=0, total=8000, step=400;
      function tick(){
        var now=new Date(); var ts=now.toTimeString().split(' ')[0];
        logEl.textContent = "["+ts+"] " + msgs[i % msgs.length];
        i++; t += step;
        fill.style.width = Math.min(100, Math.round((t/total)*100)) + "%";
        if (t >= total){
          clearInterval(timer);
          setTimeout(function(){
            try { window.parent && window.parent.postMessage({type:'covnox_done', round: round}, '*'); } catch(_){}
            if(overlay&&overlay.parentNode) overlay.parentNode.removeChild(overlay);
          }, 200);
        }
      }
      tick();
      var timer = setInterval(tick, step);
    })();
    </script>
    """.replace(
        "__LOGS__", json.dumps(logs, ensure_ascii=False)
    ).replace(
        "__ROUND__", str(round_no)
    )
    components.html(html, height=640, scrolling=False)


def radio_required(
    label: str, options: List[str], key: str
) -> tuple[Optional[str], bool]:
    """
    Render a radio input without a default selection.

    Returns the selected value (or None) and whether the input is valid.
    """
    try:
        value = st.radio(label, options, index=None, key=key)
        return value, value is not None
    except TypeError:
        placeholder = "— Select one —"
        opts = [placeholder] + options
        choice = st.radio(label, opts, index=0, key=key)
        return (None, False) if choice == placeholder else (choice, True)


def inject_covx_toggle(round_no: int) -> None:
    st.markdown(
        f"""
<style>
  body:not(.covx-r{round_no}-done) #mcp{round_no}-done-banner {{ display:none !important; }}
  body:not(.covx-r{round_no}-done) #mcp{round_no}-actions     {{ display:none !important; }}
</style>
<script>
  (function(){{
    var key="__covxBridgeR{round_no}";
    if (window[key]) return;
    window[key] = true;
    window.addEventListener('message', function(e){{
      try{{
        if (e && e.data && e.data.type === 'covnox_done' && e.data.round === {round_no}) {{
          document.body.classList.add('covx-r{round_no}-done');
          var el = document.getElementById('mcp{round_no}-done-banner');
          if (el) el.scrollIntoView({{behavior:'smooth', block:'center'}});
        }}
      }}catch(_){{
      }}
    }});
  }})();
</script>
""",
        unsafe_allow_html=True,
    )


# --------------------------------------------------------------------------------------
# Storage helpers (Google Sheet + local CSV fallback)
# --------------------------------------------------------------------------------------


def google_ready() -> bool:
    """Return True when remote Google Sheet credentials are available.

    We check both Streamlit secrets and GOOGLE_APPLICATION_CREDENTIALS_JSON for flexibility.
    """
    try:
        has_secrets = bool(getattr(st.secrets, "google_sheet", {}) or {})
    except Exception:
        has_secrets = False
    has_env = bool(os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON"))
    return has_secrets or has_env


def save_row(row: List[Any]) -> str:
    """Persist a response row remotely when possible, otherwise locally.

    Honors DRY_RUN mode and falls back to a /tmp CSV that works on Streamlit Cloud.
    """
    dry_run = st.session_state.get("DRY_RUN", False)
    if dry_run or not google_ready():
        import csv
        from pathlib import Path

        path = Path("/tmp/ai_praise_resp.csv")
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", newline="", encoding="utf-8") as file_obj:
            csv.writer(file_obj).writerow(row)
        return f"LOCAL::{path}"
    from utils.google_sheet import append_row_to_sheet  # noqa: PLC0415

    ws_conf = getattr(st.secrets, "google_sheet", {}) or {}
    worksheet = ws_conf.get("worksheet", "resp")
    append_row_to_sheet(row, worksheet=worksheet)
    return "REMOTE::GOOGLE_SHEET"


def build_export_row(payload: Dict[str, Any], record: ExperimentData) -> List[Any]:
    consent = payload.get("consent", {})
    demographic = payload.get("demographic", {})
    anthro = payload.get("anthro_responses", [])
    achive = payload.get("achive_responses", [])
    motivation = payload.get("motivation_responses", [])
    inference_details = payload.get("inference_details", [])
    feedback_condition = payload.get("feedback_condition", "")
    difficulty = payload.get("difficulty_checks", {})
    start_iso = payload.get("start_time")
    end_iso = payload.get("end_time")
    phone = payload.get("phone", "")
    open_feedback = payload.get("open_feedback", "")

    score = sum(
        1 for d in inference_details if d["selected_option"] == d["correct_idx"]
    )
    duration = sum(float(d["response_time"]) for d in inference_details)
    accuracy = f"{score / len(inference_details):.3f}" if inference_details else ""

    per_q_fields: List[Any] = []
    for item in inference_details:
        per_q_fields.extend(
            [
                item["selected_option"],
                item["correct_idx"],
                1 if item["selected_option"] == item["correct_idx"] else 0,
                item["selected_reason_text"],
            ]
        )

    metadata = json.dumps(
        {
            "participant_id": record.participant_id,
            "condition": record.condition,
            "difficulty": difficulty,
            "motivation_category_scores": payload.get("motivation_category_scores", {}),
            "open_feedback": open_feedback,
        },
        ensure_ascii=False,
    )

    return [
        datetime.fromisoformat(start_iso).strftime("%Y-%m-%d") if start_iso else "",
        consent.get("consent_research", ""),
        consent.get("consent_privacy", ""),
        demographic.get("gender", ""),
        demographic.get("age_group", ""),
        ",".join("" if v is None else str(v) for v in anthro),
        ",".join("" if v is None else str(v) for v in achive),
        round(duration, 2) if inference_details else "",
        score if inference_details else "",
        accuracy,
        *per_q_fields,
        feedback_condition,
        ",".join(str(v) for v in motivation),
        phone,
        start_iso or "",
        end_iso or "",
        metadata,
    ]


def export_session_json(payload: Dict[str, Any]) -> None:
    with st.expander("📦 세션 데이터 확인 (JSON)", expanded=False):
        st.code(json.dumps(payload, ensure_ascii=False, indent=2), language="json")


# --------------------------------------------------------------------------------------
# Session bootstrap & sidebar controls
# --------------------------------------------------------------------------------------


def ensure_session_state() -> None:
    ss = st.session_state
    if "phase" not in ss:
        ss.phase = "consent"
    if "consent_step" not in ss:
        ss.consent_step = "explain"
    if "payload" not in ss:
        ss.payload = {
            "consent": {},
            "demographic": {},
            "anthro_responses": [],
            "achive_responses": [],
            "motivation_responses": [],
            "motivation_category_scores": {},
            "difficulty_checks": {},
            "inference_details": [],
            "feedback_messages": {"nouns": [], "verbs": []},
            "feedback_condition": "",
            "open_feedback": "",
            "start_time": None,
            "end_time": None,
            "phone": "",
            "participant_id": None,
        }
    if "manager" not in ss:
        ss.manager = ExperimentManager()
    if "round_state" not in ss:
        ss.round_state = {
            "nouns_index": 0,
            "verbs_index": 0,
            "question_start": None,
            "last_feedback": None,
        }
    if "analysis_seen" not in ss:
        ss.analysis_seen = {"nouns": False, "verbs": False}
    if "exported" not in ss:
        ss.exported = False
    if "motivation_page" not in ss:
        ss.motivation_page = 1
    if "anthro_page" not in ss:
        ss.anthro_page = 1
    if "achive_page" not in ss:
        ss.achive_page = 1
    if "DRY_RUN" not in ss:
        ss.DRY_RUN = os.getenv("DRY_RUN", "false").lower() == "true"
    if "record" not in ss:
        ss.record = None
    if "_resource_fallback_warned" not in ss:
        ss._resource_fallback_warned = {}


def set_phase(next_phase: str) -> None:
    allowed = {
        "consent",
        "demographic",
        "instructions",
        "anthro",
        "achive",
        "task_intro",
        "inference_nouns",
        "analysis_nouns",
        "feedback_nouns",
        "difficulty_check",
        "inference_verbs",
        "analysis_verbs",
        "feedback_verbs",
        "motivation",
        "post_task_reflection",
        "phone_input",
        "summary",
    }
    st.session_state.phase = next_phase if next_phase in allowed else "summary"
    scroll_top_js()
    st.rerun()


def sidebar_controls() -> None:
    with st.sidebar:
        st.subheader("Session Controls")
        st.session_state.DRY_RUN = st.checkbox(
            "DRY_RUN (disable remote storage)",
            value=st.session_state.get("DRY_RUN", False),
        )
        ready = google_ready()
        remote_enabled = ready and not st.session_state.DRY_RUN
        st.caption(f"Remote storage: {'enabled' if remote_enabled else 'disabled'}")
        if not ready and not st.session_state.DRY_RUN:
            st.info(
                "Remote storage not configured. We will save to a local CSV fallback."
            )
        st.write("Current phase:")
        st.write(st.session_state.phase)
        if st.button("Restart from scratch"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()


DEFAULT_ANTHRO_ITEMS: List[str] = [
    "나는 AI 에이전트가 감정을 느낄 수 있다고 생각한다.",
    "AI가 자신의 의도를 설명할 수 있다면 사람과 비슷하게 느껴진다.",
    "AI의 반응을 보면 인간적인 성격이 느껴진다.",
    "AI와 대화하면 정서적으로 교감한다고 느낀다.",
    "AI는 사회적 상황에 맞춰 공감할 수 있다고 믿는다.",
    "AI 에이전트가 관계를 형성할 수 있다는 생각이 든다.",
    "AI의 행동에는 숨겨진 감정 상태가 있다고 본다.",
    "AI가 나를 이해하고 있다고 느낄 때가 있다.",
    "AI는 상황에 맞게 배려심 있게 행동할 수 있다.",
    "AI의 결정에는 인간과 비슷한 의도가 담겨 있다고 생각한다.",
    "AI가 실수했을 때 미안해한다고 느껴진다.",
    "AI는 인간과 장기적인 우정을 쌓을 수 있다고 본다.",
]

DEFAULT_ACHIVE_ITEMS: List[str] = [
    "나는 어려운 목표를 세우고 달성하는 편이다.",
    "성취감을 느끼기 위해 새로운 과제를 찾는다.",
    "실패해도 다시 도전하려는 의지가 강하다.",
    "많은 노력을 쏟아부은 작업은 끝까지 해내고 싶다.",
    "높은 기준을 스스로 설정하고 그것을 맞추려 한다.",
    "결과가 좋지 않아도 학습 경험을 중요하게 생각한다.",
    "다른 사람보다 더 잘해내기 위해 계획을 세운다.",
    "작은 성공을 기록하며 동기를 유지하는 편이다.",
    "어려운 문제일수록 해결하고 싶은 의욕이 생긴다.",
    "장기적인 보상을 위해 단기적인 불편을 감수한다.",
    "피드백을 바탕으로 실수를 고치려고 노력한다.",
    "내가 세운 목표를 달성하는 것이 큰 만족감을 준다.",
]

RESOURCE_FALLBACKS: Dict[str, List[str]] = {
    "questions_anthro.json": DEFAULT_ANTHRO_ITEMS,
    "questions_achive.json": DEFAULT_ACHIVE_ITEMS,
}


def _warn_resource_fallback(filename: str) -> None:
    registry = st.session_state.setdefault("_resource_fallback_warned", {})
    if not registry.get(filename):
        st.warning("Local resource not found — using built-in items.", icon="⚠️")
        registry[filename] = True


def _load_local_json(filename: str) -> Optional[List[str]]:
    fallback = RESOURCE_FALLBACKS.get(filename)
    path = BASE_DIR / "data" / filename
    if path.exists():
        try:
            with path.open("r", encoding="utf-8") as file_obj:
                data = json.load(file_obj)
        except Exception:
            if fallback:
                _warn_resource_fallback(filename)
                return list(fallback)
            st.error(f"{filename} 로드 중 문제가 발생했습니다.")
            return None
        if isinstance(data, list) and data:
            return data
        if fallback:
            _warn_resource_fallback(filename)
            return list(fallback)
        st.warning(f"{filename} 데이터가 비어 있습니다.")
        return None
    if fallback:
        _warn_resource_fallback(filename)
        return list(fallback)
    st.error(f"로컬 리소스 {filename} 을(를) 찾지 못했습니다.")
    return None


# --------------------------------------------------------------------------------------
# Rendering helpers for each phase
# --------------------------------------------------------------------------------------
def render_consent() -> None:
    scroll_top_js()
    st.markdown(COMMON_CSS, unsafe_allow_html=True)
    if st.session_state.consent_step == "explain":
        st.title("연구대상자 설명문")
        st.markdown(CONSENT_HTML, unsafe_allow_html=True)
        if st.button("다음", use_container_width=True):
            st.session_state.consent_step = "agree"
            st.rerun()
        return

    st.title("연구 동의 및 개인정보 동의")
    st.markdown(AGREE_HTML, unsafe_allow_html=True)
    consent_research = st.radio(
        "연구 참여에 동의하십니까?",
        ["동의함", "동의하지 않음"],
        horizontal=True,
        key="consent_research_radio",
    )
    st.markdown(PRIVACY_HTML, unsafe_allow_html=True)
    consent_privacy = st.radio(
        "개인정보 수집·이용에 동의하십니까?",
        ["동의함", "동의하지 않음"],
        horizontal=True,
        key="consent_privacy_radio",
    )
    cols = st.columns(2)
    with cols[0]:
        if st.button("이전", use_container_width=True):
            st.session_state.consent_step = "explain"
            st.rerun()
    with cols[1]:
        if st.button("동의하고 진행", use_container_width=True):
            if consent_research != "동의함" or consent_privacy != "동의함":
                st.warning("연구 및 개인정보 동의가 모두 필요합니다.")
            else:
                st.session_state.payload["consent"] = {
                    "consent_research": consent_research,
                    "consent_privacy": consent_privacy,
                }
                st.session_state.payload["start_time"] = datetime.utcnow().isoformat()
                set_phase("demographic")


def render_demographic() -> None:
    scroll_top_js()
    st.title("인적사항 입력")
    st.write("연구 통계와 조건 배정을 위해 아래 정보를 입력해 주세요.")
    gender = st.radio(
        "성별", ["남자", "여자", "기타/응답하지 않음"], key="demographic_gender"
    )
    age_group = st.selectbox(
        "연령대",
        ["선택해 주세요", "10대", "20대", "30대", "40대", "50대", "60대 이상"],
        key="demographic_age",
    )
    education = st.selectbox(
        "최종 학력",
        [
            "선택해 주세요",
            "고등학교 졸업 이하",
            "대학(재학/졸업)",
            "대학원(재학/졸업)",
            "기타",
        ],
        key="demographic_edu",
    )
    language = st.text_input("주 사용 언어 (선택 사항)", key="demographic_language")
    if st.button("다음 단계", use_container_width=True):
        if age_group == "선택해 주세요" or education == "선택해 주세요":
            st.warning("모든 필수 항목을 입력해 주세요.")
            return
        st.session_state.payload["demographic"] = {
            "gender": gender,
            "age_group": age_group,
            "education": education,
            "language": language.strip(),
        }
        condition = random.choice(list(PraiseCondition))
        participant_id = st.session_state.manager.create_participant(
            st.session_state.payload["demographic"],
            assigned_condition=condition,
        )
        st.session_state.payload["participant_id"] = participant_id
        st.session_state.payload["feedback_condition"] = condition.value
        set_phase("instructions")


def render_instructions() -> None:
    scroll_top_js()
    st.title("연구 진행 안내")
    st.markdown(
        """
- 전체 소요 시간은 약 **10~15분**입니다.
- 연구는 다음 순서로 진행됩니다.
  1. 의인화/성취 관련 설문 (56문항)
  2. 추론 과제 1회차 (명사구 12문항) + AI 피드백
  3. 추론 과제 2회차 (동사 시제·상 12문항) + AI 피드백
  4. 학습 동기 설문 (26문항)
  5. 연구 종료 안내 및 연락처 입력 (선택 사항)
- 화면의 버튼으로만 이동해 주세요.
"""
    )
    with st.expander("📘 추론 규칙 요약", expanded=True):
        st.markdown(GRAMMAR_INFO_MD)
    if st.button("설문 시작", use_container_width=True):
        set_phase("anthro")


def render_paginated_likert(
    questions: List[str],
    key_prefix: str,
    scale_min: int,
    scale_max: int,
    page_state_key: str,
    responses_key: str,
    prompt_html: str,
    scale_hint_html: str,
    per_page: int,
) -> bool:
    total = len(questions)
    total_pages = (total + per_page - 1) // per_page
    page = st.session_state.get(page_state_key, 1)
    start_idx = (page - 1) * per_page
    end_idx = min(start_idx + per_page, total)

    if not st.session_state.payload.get(responses_key):
        st.session_state.payload[responses_key] = [None] * total

    st.markdown(prompt_html, unsafe_allow_html=True)
    st.markdown(scale_hint_html, unsafe_allow_html=True)
    st.markdown(
        f"<div style='text-align:center;color:#6b7480;margin-bottom:12px;'>문항 {start_idx + 1}–{end_idx} / {total} (페이지 {page}/{total_pages})</div>",
        unsafe_allow_html=True,
    )

    for idx in range(start_idx, end_idx):
        label = questions[idx]
        current = st.session_state.payload[responses_key][idx]
        selected = st.radio(
            f"{idx + 1}. {label}",
            list(range(scale_min, scale_max + 1)),
            index=None if current is None else current - scale_min,
            format_func=lambda val: f"{val}점",
            horizontal=True,
            key=f"{key_prefix}_{idx}",
        )
        st.session_state.payload[responses_key][idx] = selected

    col_prev, col_next = st.columns(2)
    with col_prev:
        if page > 1 and st.button(
            "← 이전", use_container_width=True, key=f"{key_prefix}_prev"
        ):
            st.session_state[page_state_key] = page - 1
            set_phase(st.session_state.phase)
    with col_next:
        if page < total_pages:
            if st.button("다음 →", use_container_width=True, key=f"{key_prefix}_next"):
                if any(
                    v is None
                    for v in st.session_state.payload[responses_key][start_idx:end_idx]
                ):
                    st.warning("현재 페이지의 모든 문항에 응답해 주세요.")
                else:
                    st.session_state[page_state_key] = page + 1
                    set_phase(st.session_state.phase)
        else:
            if st.button("완료", use_container_width=True, key=f"{key_prefix}_done"):
                if any(v is None for v in st.session_state.payload[responses_key]):
                    st.warning("모든 문항에 응답해 주세요.")
                else:
                    return True
    return False


def render_anthro() -> None:
    scroll_top_js()
    questions = _load_local_json("questions_anthro.json")
    if not questions:
        return
    done = render_paginated_likert(
        questions=questions,
        key_prefix="anthro",
        scale_min=1,
        scale_max=5,
        page_state_key="anthro_page",
        responses_key="anthro_responses",
        prompt_html="<h2 style='text-align:center;font-weight:bold;'>AI 에이전트에 대한 인식 설문</h2>",
        scale_hint_html="""
<div style='display:flex;justify-content:center;gap:12px;flex-wrap:wrap;font-size:16px;margin-bottom:22px;'>
  <span><b>1점</b> : 전혀 그렇지 않다</span><span>—</span>
  <span><b>3점</b> : 보통이다</span><span>—</span>
  <span><b>5점</b> : 매우 그렇다</span>
</div>
""",
        per_page=10,
    )
    if done:
        set_phase("achive")


def render_achive() -> None:
    scroll_top_js()
    questions = _load_local_json("questions_achive.json")
    if not questions:
        return
    done = render_paginated_likert(
        questions=questions,
        key_prefix="achive",
        scale_min=1,
        scale_max=6,
        page_state_key="achive_page",
        responses_key="achive_responses",
        prompt_html="<h2 style='text-align:center;font-weight:bold;'>성취/접근 성향 설문</h2>",
        scale_hint_html="""
<div style='display:flex;justify-content:center;gap:12px;flex-wrap:wrap;font-size:16px;margin-bottom:22px;'>
  <span><b>1</b> : 전혀 그렇지 않다</span><span>—</span>
  <span><b>3</b> : 보통이다</span><span>—</span>
  <span><b>6</b> : 매우 그렇다</span>
</div>
""",
        per_page=10,
    )
    if done:
        set_phase("task_intro")


def render_task_intro() -> None:
    scroll_top_js()
    st.title("추론 과제 안내")
    st.markdown(
        """
- **1회차 (명사구 12문항)**: 소유, 복수, 목적 표지 등 규칙을 추론합니다.  
- **2회차 (동사 12문항)**: 시제(-na/-tu/-ki)와 상(-mu/-li)을 판별합니다.  
- 각 문항은 5지선다이며, **추론 이유**도 5지선다에서 선택합니다.  
- 제출 후 AI 에이전트가 조건 맞춤형 칭찬 피드백을 제공합니다.
"""
    )
    with st.expander("📘 규칙 다시 보기", expanded=True):
        st.markdown(GRAMMAR_INFO_MD)
    if st.button("1회차 시작", use_container_width=True):
        st.session_state.round_state["nouns_index"] = 0
        st.session_state.round_state["question_start"] = None
        set_phase("inference_nouns")


def render_inference_round(
    round_key: str,
    questions: List[Question],
    reason_labels: List[str],
    next_phase: str,
) -> None:
    scroll_top_js()
    rs = st.session_state.round_state
    payload = st.session_state.payload
    index = rs.get(f"{round_key}_index", 0)
    if index >= len(questions):
        set_phase(next_phase)
        return
    question = questions[index]
    st.title(
        f"추론 과제 {1 if round_key == 'nouns' else 2} / {len(questions)}문항 중 {index + 1}번째"
    )
    st.markdown(f"**설명:** {question.gloss}")
    st.code(question.stem, language="text")
    st.markdown("정답과 추론 근거 태그, 이유 서술을 모두 완료해야 제출할 수 있습니다.")

    if rs.get("question_start") is None:
        rs["question_start"] = time.perf_counter()

    answer_labels = [f"{idx + 1}. {opt}" for idx, opt in enumerate(question.options)]
    selected_answer_label, answer_valid = radio_required(
        "정답을 선택하세요",
        answer_labels,
        key=f"{round_key}_answer_{index}",
    )

    rationale_tags = reason_labels
    selected_tag, tag_valid = radio_required(
        "추론 근거 태그를 하나 선택하세요 (필수)",
        rationale_tags,
        key=f"{round_key}_tag_{index}",
    )

    reason_text = st.text_area(
        "선택 이유를 간단히 적어주세요 (필수)",
        key=f"{round_key}_reason_text_{index}",
    )
    reason_notes = reason_text.strip()

    can_submit = bool(answer_valid and tag_valid and reason_notes)
    submit_btn = st.button(
        "응답 제출",
        key=f"{round_key}_submit_{index}",
        disabled=not can_submit,
    )

    if not submit_btn:
        if rs.get("last_feedback"):
            st.info(f"이전 피드백: {rs['last_feedback']}")
        return

    if not can_submit:
        st.error("태그 선택과 이유 입력은 필수입니다.")
        return

    response_time = round(time.perf_counter() - rs["question_start"], 2)
    rs["question_start"] = None
    manager: ExperimentManager = st.session_state.manager
    selected_option_idx = answer_labels.index(selected_answer_label)
    selected_tag_idx = rationale_tags.index(selected_tag)
    feedback = manager.process_inference_response(
        question_id=question.id,
        selected_option=selected_option_idx,
        selected_reason=selected_tag,
        response_time=response_time,
    )
    detail = {
        "round": round_key,
        "question_id": question.id,
        "stem": question.stem,
        "gloss": question.gloss,
        "options": question.options,
        "selected_option": int(selected_option_idx),
        "selected_option_text": question.options[selected_option_idx],
        "correct_idx": int(question.answer_idx),
        "correct_text": question.options[question.answer_idx],
        "selected_reason_idx": int(selected_tag_idx),
        "selected_reason_text": selected_tag,
        "reason_notes": reason_notes,
        "correct_reason_idx": int(question.reason_idx),
        "response_time": response_time,
        "timestamp": datetime.utcnow().isoformat(),
        "feedback": feedback,
    }
    payload.setdefault("inference_details", []).append(detail)
    payload["feedback_messages"][round_key].append(feedback)
    rs[f"{round_key}_index"] = index + 1
    rs["last_feedback"] = feedback
    if rs[f"{round_key}_index"] >= len(questions):
        set_phase(next_phase)
    else:
        st.success("응답이 저장되었습니다. 다음 문항으로 이동합니다.")
        set_phase(st.session_state.phase)


def render_analysis(round_key: str, round_no: int, next_phase: str) -> None:
    scroll_top_js()
    flag_key = f"mcp_done_{round_key}"
    st.session_state.setdefault(flag_key, False)
    if st.session_state.get("_mcp_round") != round_key:
        st.session_state["_mcp_round"] = round_key
        st.session_state[flag_key] = False
    footer_ph = st.empty()
    inject_covx_toggle(round_no)
    run_mcp_motion(round_no)
    st.markdown(
        f"""
<div id="mcp{round_no}-done-banner" style="max-width:820px;margin:48px auto;">
  <div style="border:2px solid #2E7D32;border-radius:14px;padding:28px;background:#F4FFF4;">
    <h2 style="text-align:center;color:#2E7D32;margin:0 0 8px 0;">✅ 분석이 완료되었습니다</h2>
    <p style="font-size:16px;line-height:1.7;color:#222;text-align:center;margin:0;">
      COVNOX가 응답 패턴을 분석했습니다. 아래 버튼을 눌러 피드백을 확인하세요.
    </p>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )
    listener_value = components.html(
        f"""
<script>
(function(){{
  const targetRound = {round_no};
  function notifyDone(event){{
    if (!event || !event.data || event.data.type !== 'covnox_done' || event.data.round !== targetRound) {{
      return;
    }}
    window.removeEventListener('message', notifyDone);
    const streamlit = window.parent && window.parent.Streamlit;
    if (streamlit && streamlit.setComponentValue) {{
      streamlit.setComponentValue('done');
    }}
  }}
  window.addEventListener('message', notifyDone, false);
}})();
</script>
""",
        height=0,
        key=f"covx-listener-{round_key}",
    )
    if listener_value == "done":
        st.session_state[flag_key] = True
    if st.session_state.get(flag_key):
        with footer_ph:
            st.markdown(
                f'<div id="mcp{round_no}-actions" class="mcp-footer">',
                unsafe_allow_html=True,
            )
            if st.button(
                "결과 보기", use_container_width=True, key=f"{round_key}_analysis_next"
            ):
                st.session_state.analysis_seen[round_key] = True
                set_phase(next_phase)
            st.markdown("</div>", unsafe_allow_html=True)


def render_feedback(round_key: str, reason_labels: List[str], next_phase: str) -> None:
    scroll_top_js()
    details = [
        d
        for d in st.session_state.payload["inference_details"]
        if d["round"] == round_key
    ]
    total = len(details)
    score = sum(1 for d in details if d["selected_option"] == d["correct_idx"])
    reason_score = sum(
        1 for d in details if d["selected_reason_idx"] == d["correct_reason_idx"]
    )
    duration = sum(float(d["response_time"]) for d in details)

    st.title(f"AI 칭찬 피드백 ({'명사구' if round_key == 'nouns' else '동사 TAM'})")
    st.markdown(
        f"""
- 정답: **{score}/{total}**
- 추론 이유 일치: **{reason_score}/{total}**
- 총 소요 시간: **{duration:.1f}초**
"""
    )
    st.subheader("AI 메시지 하이라이트")
    for idx, msg in enumerate(
        st.session_state.payload["feedback_messages"][round_key][-3:], start=1
    ):
        st.write(f"{idx}. {msg}")

    st.subheader("응답 요약")
    df = pd.DataFrame(
        [
            {
                "문항": d["question_id"],
                "선택": d["selected_option_text"],
                "정답": d["correct_text"],
                "정답 여부": "O" if d["selected_option"] == d["correct_idx"] else "X",
                "이유": d["selected_reason_text"],
                "이유 정답": reason_labels[d["correct_reason_idx"]],
                "이유 서술": d.get("reason_notes", ""),
                "응답 시간(초)": d["response_time"],
            }
            for d in details
        ]
    )
    st.dataframe(df, hide_index=True, use_container_width=True)

    if st.button(
        "다음 단계", use_container_width=True, key=f"{round_key}_feedback_next"
    ):
        set_phase(next_phase)


def render_difficulty_check() -> None:
    scroll_top_js()
    st.title("난이도 조정 의향")
    st.write(
        "다음 라운드(동사 시제·상)를 위해 난이도가 높아져도 도전할 의향을 선택해 주세요."
    )
    slider = st.slider(
        "다음 라운드 난이도 상향 허용 (1=매우 꺼림, 10=매우 도전)", 1, 10, 5
    )
    st.session_state.payload["difficulty_checks"]["after_round1"] = slider
    if st.button("2회차 시작", use_container_width=True):
        st.session_state.round_state["verbs_index"] = 0
        st.session_state.round_state["question_start"] = None
        set_phase("inference_verbs")


def render_motivation() -> None:
    scroll_top_js()
    per_page = 6
    total = len(MOTIVATION_QUESTIONS)
    total_pages = (total + per_page - 1) // per_page
    page = st.session_state.motivation_page
    start_idx = (page - 1) * per_page
    end_idx = min(start_idx + per_page, total)

    if not st.session_state.payload["motivation_responses"]:
        st.session_state.payload["motivation_responses"] = [None] * total

    st.title("학습 동기 설문")
    st.markdown(
        "<div style='display:flex;justify-content:center;gap:12px;flex-wrap:wrap;font-size:16px;margin-bottom:22px;'>"
        "<span><b>1점</b> : 전혀 그렇지 않다</span><span>—</span>"
        "<span><b>4점</b> : 보통이다</span><span>—</span>"
        "<span><b>7점</b> : 매우 그렇다</span>"
        "</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<div style='text-align:center;color:#6b7480;margin-bottom:12px;'>문항 {start_idx + 1}–{end_idx} / {total} (페이지 {page}/{total_pages})</div>",
        unsafe_allow_html=True,
    )

    for idx in range(start_idx, end_idx):
        question = MOTIVATION_QUESTIONS[idx]
        current = st.session_state.payload["motivation_responses"][idx]
        selected = st.radio(
            f"{idx + 1}. {question.text}",
            list(range(1, question.scale + 1)),
            index=None if current is None else current - 1,
            format_func=lambda val: f"{val}점",
            horizontal=True,
            key=f"motivation_{question.id}",
        )
        st.session_state.payload["motivation_responses"][idx] = selected

    col_prev, col_next = st.columns(2)
    with col_prev:
        if page > 1 and st.button(
            "← 이전", use_container_width=True, key="motivation_prev"
        ):
            st.session_state.motivation_page = page - 1
            set_phase(st.session_state.phase)
    with col_next:
        if page < total_pages:
            if st.button("다음 →", use_container_width=True, key="motivation_next"):
                if any(
                    v is None
                    for v in st.session_state.payload["motivation_responses"][
                        start_idx:end_idx
                    ]
                ):
                    st.warning("현재 페이지의 모든 문항에 응답해 주세요.")
                else:
                    st.session_state.motivation_page = page + 1
                    set_phase(st.session_state.phase)
        else:
            if st.button("설문 완료", use_container_width=True, key="motivation_done"):
                if any(
                    v is None for v in st.session_state.payload["motivation_responses"]
                ):
                    st.warning("모든 문항에 응답해 주세요.")
                else:
                    category_scores: Dict[str, List[int]] = {}
                    for score, question in zip(
                        st.session_state.payload["motivation_responses"],
                        MOTIVATION_QUESTIONS,
                    ):
                        val = question.scale + 1 - score if question.reverse else score
                        category_scores.setdefault(question.category, []).append(val)
                    st.session_state.payload["motivation_category_scores"] = {
                        cat: round(sum(vals) / len(vals), 2) if vals else 0.0
                        for cat, vals in category_scores.items()
                    }
                    set_phase("post_task_reflection")


def render_post_task_reflection() -> None:
    scroll_top_js()
    st.title("마무리 질문")
    st.write("다음 기회에 더 어려운 과제가 주어져도 도전할 의향을 선택해 주세요.")
    slider = st.slider("난이도 상향 의향 (1=매우 꺼림, 10=매우 도전)", 1, 10, 5)
    st.session_state.payload["difficulty_checks"]["final"] = slider
    st.write(
        "연구 과정에서 느낀 점이나 연구진에게 전하고 싶은 메시지를 남겨주세요. (선택 사항)"
    )
    feedback_text = st.text_area("연구 참여 소감", key="open_feedback_area")
    st.session_state.payload["open_feedback"] = feedback_text.strip()
    if st.button("연락처 입력으로 이동", use_container_width=True):
        set_phase("phone_input")


def render_phone_capture() -> None:
    scroll_top_js()
    st.title("연락처 입력 (선택 사항)")
    st.write(
        "답례품(기프티콘) 발송을 위해 휴대폰 번호를 입력해 주세요. 입력하지 않아도 참여는 완료되지만 보상 제공이 어려울 수 있습니다."
    )
    phone = st.text_input("휴대폰 번호 (예: 010-1234-5678)")
    st.session_state.payload["phone"] = phone.strip()
    if st.button("제출하기", use_container_width=True):
        set_phase("summary")


def render_summary() -> None:
    scroll_top_js()
    manager: ExperimentManager = st.session_state.manager
    payload = st.session_state.payload

    if not st.session_state.record:
        try:
            record = manager.complete_experiment()
        except ValueError:
            condition = payload.get("feedback_condition", "emotional_specific")
            record = ExperimentData(
                participant_id=payload.get("participant_id")
                or f"manual_{int(time.time())}",
                condition=condition,
                demographic=payload.get("demographic", {}),
                inference_responses=[
                    {
                        "question_id": d["question_id"],
                        "selected_option": d["selected_option"],
                        "selected_reason": d["selected_reason_text"],
                        "response_time": d["response_time"],
                        "timestamp": d["timestamp"],
                    }
                    for d in payload.get("inference_details", [])
                ],
                survey_responses=[
                    {
                        "question_id": q.id,
                        "rating": score,
                        "timestamp": datetime.utcnow().isoformat(),
                    }
                    for q, score in zip(
                        MOTIVATION_QUESTIONS, payload.get("motivation_responses", [])
                    )
                ],
                feedback_messages=[
                    *payload.get("feedback_messages", {}).get("nouns", []),
                    *payload.get("feedback_messages", {}).get("verbs", []),
                ],
                timestamps={
                    "start": payload.get("start_time") or datetime.utcnow().isoformat(),
                    "end": datetime.utcnow().isoformat(),
                },
                completion_time=sum(
                    d["response_time"] for d in payload.get("inference_details", [])
                ),
            )
        st.session_state.record = record
        payload["end_time"] = record.timestamps["end"]
    record: ExperimentData = st.session_state.record

    st.title("연구 참여가 완료되었습니다")
    st.success("참여해 주셔서 감사합니다! 응답은 자동 저장되었습니다.")
    st.markdown(
        f"""
- 참가자 ID: **{record.participant_id}**
- 배정 조건: **{record.condition}**
- 총 소요 시간: **{record.completion_time:.1f}초**
"""
    )

    analyzer = DataAnalyzer([record])
    motivation_scores = analyzer.get_motivation_scores().get(record.condition, {})
    if motivation_scores:
        st.subheader("동기 카테고리 평균 점수")
        df = pd.DataFrame(
            [
                {"카테고리": cat, "평균 점수": round(score, 2)}
                for cat, score in motivation_scores.items()
            ]
        )
        st.bar_chart(df.set_index("카테고리"))
    else:
        st.info("설문 데이터가 충분하지 않아 동기 점수를 계산할 수 없습니다.")

    if not st.session_state.exported:
        row = build_export_row(payload, record)
        try:
            dest = save_row(row)
            if dest.startswith("REMOTE::"):
                st.success("Responses saved to Google Sheet.")
            else:
                st.success(
                    f"Saved locally (remote not set or DRY_RUN on): {dest.split('::', 1)[1]}"
                )
            st.session_state.exported = True
        except Exception as _exc:  # pragma: no cover
            st.error("Saving failed. Retrying local fallback…")
            try:
                dest = save_row(row)
                st.success(f"Local save success: {dest.split('::', 1)[1]}")
                st.session_state.exported = True
            except Exception as exc2:  # pragma: no cover
                st.exception(exc2)

    st.subheader("세션 로그")
    export_session_json(payload)
    st.markdown(
        """
#### 마지막 안내
- 본 연구에서 제공된 AI 피드백은 사전에 준비된 예시 문장입니다.  
- 브라우저 탭은 자동으로 닫히지 않으니 직접 종료해 주세요.
"""
    )


# --------------------------------------------------------------------------------------
# App entrypoint
# --------------------------------------------------------------------------------------

ensure_session_state()
sidebar_controls()

phase = st.session_state.phase
if phase == "consent":
    render_consent()
elif phase == "demographic":
    render_demographic()
elif phase == "instructions":
    render_instructions()
elif phase == "anthro":
    render_anthro()
elif phase == "achive":
    render_achive()
elif phase == "task_intro":
    render_task_intro()
elif phase == "inference_nouns":
    render_inference_round(
        "nouns", NOUN_QUESTIONS, REASON_NOUN_LABELS, "analysis_nouns"
    )
elif phase == "analysis_nouns":
    render_analysis("nouns", 1, "feedback_nouns")
elif phase == "feedback_nouns":
    render_feedback("nouns", REASON_NOUN_LABELS, "difficulty_check")
elif phase == "difficulty_check":
    render_difficulty_check()
elif phase == "inference_verbs":
    render_inference_round(
        "verbs", VERB_QUESTIONS, REASON_VERB_LABELS, "analysis_verbs"
    )
elif phase == "analysis_verbs":
    render_analysis("verbs", 2, "feedback_verbs")
elif phase == "feedback_verbs":
    render_feedback("verbs", REASON_VERB_LABELS, "motivation")
elif phase == "motivation":
    render_motivation()
elif phase == "post_task_reflection":
    render_post_task_reflection()
elif phase == "phone_input":
    render_phone_capture()
else:
    render_summary()
