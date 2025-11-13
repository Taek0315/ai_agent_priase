#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
import random
import time
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
import streamlit as st

# [CHANGE] Import centralized constants for shared UI/state configuration.
from constants import (
    ACHIVE_DEFAULT_ITEMS,
    ANTHRO_DEFAULT_ITEMS,
    DEMOGRAPHIC_AGE_LABEL,
    DEMOGRAPHIC_AGE_MAX,
    DEMOGRAPHIC_AGE_MIN,
    DEMOGRAPHIC_SEX_LABEL,
    DEMOGRAPHIC_SEX_OPTIONS,
    LIKERT5_LEGEND_HTML,
    LIKERT5_NUMERIC_OPTIONS,
    MANIPULATION_CHECK_EXPECTED_COUNT,
    MANIPULATION_CHECK_ITEMS,
)
from persistence import (
    build_sheet_row,
    build_storage_record,
    google_ready,
    save_to_gcs,
    save_to_sheets,
)
from utils.feedback_guard import get_feedback_once
from utils.ui_helpers import all_answered, render_likert_numeric
from utils.persistence import now_utc_iso

# --------------------------------------------------------------------------------------
# Streamlit page config & global styling
# --------------------------------------------------------------------------------------

st.set_page_config(
    page_title="AI 칭찬 연구 설문",
    layout="centered",
    initial_sidebar_state="collapsed",
)

COMPACT_CSS = """
<style>
  :root { --fs-base: 16px; --lh-base: 1.65; }
  #MainMenu, header, footer, [data-testid="stToolbar"] { display: none !important; }
  [data-testid="stSidebar"], section[data-testid="stSidebar"] { display: none !important; }
  [data-testid="stSidebarCollapseButton"],
  [data-testid="stSidebarNav"],
  button[kind="header"] { display: none !important; }
  html, body, [data-testid="stAppViewContainer"] {
    font-size: var(--fs-base);
    line-height: var(--lh-base);
    overflow-x: hidden !important;
  }
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
  div[data-testid="stProgress"] { margin-bottom: 0.4rem !important; }
  .mcp-footer { margin-top: 0.6rem !important; }
</style>
"""

st.markdown(COMPACT_CSS, unsafe_allow_html=True)

# [CHANGE] Default runtime feature toggles for feedback/debug rendering.
SHOW_PER_ITEM_INLINE_FEEDBACK = False
SHOW_PER_ITEM_SUMMARY = False
SHOW_DEBUG_RESULTS = False


def get_or_assign_praise_condition() -> str:
    """
    Returns exactly one of:
      'emotional_specific', 'computational_specific',
      'emotional_surface', 'computational_surface'
    Assign once per participant and persist in st.session_state.
    Never display this string to the participant.
    """
    key = "praise_condition"
    if key not in st.session_state:
        st.session_state[key] = random.choice(
            [
                "emotional_specific",
                "computational_specific",
                "emotional_surface",
                "computational_surface",
            ]
        )
    return st.session_state[key]


FEEDBACK_TEXTS: Dict[str, List[str]] = {
    "emotional_specific": [
        "추론 과제의 분석이 완료되었습니다.\n전체 10개 문항이 어려울 수 있음에도 열심히 풀어주신 점에 감사합니다. 각 문항에서 응답한 추론 방식을 볼 때 많은 생각과 깊은 고민을 하시면서 응답하신 걸로 생각됩니다. 훌륭한 학습자를 만난 것 같아서 기쁨과 뿌듯함을 느끼고 있습니다. 특히 {A}를 적절하게 사용하셨는데 쉽지 않은 과제임에도 놀라운 언어적 능력과 추론 능력보여주신 점이 인상 깊었습니다. 저와 함께 학습을 진행한다면 정말 즐겁고 뜻 깊을 것 같아 기대가 됩니다.",
        "추론 과제의 분석이 완료되었습니다.\n도전적인 문항에서도 성실하고 깊이 있는 사고가 관찰되었습니다. 특히 {A}와 {B} 사용이 안정적으로 드러났습니다. 계속 함께한다면 큰 성장이 기대됩니다.",
        "추론 과제의 분석이 완료되었습니다.\n응답 전반에서 세심한 판단과 일관성이 확인되었습니다. {A}, {B} 활용이 인상적이었습니다. 훌륭한 학습자의 면모가 보입니다.",
    ],
    "computational_specific": [
        "추론 과제의 분석이 완료되었습니다.\n전체 10개 문항을 분석한 결과, 사전 분포 대비 92.3 퍼센타일의 추론 효율 지수를 기록하셨습니다. 이는 응답 시점별 근거 밀도의 분산이 0.14 이내로 수렴한 결과로 해석됩니다. 특히 {A}의 사용 빈도는 라플라스 근사 모델 기준 ΔAIC = −5.28 수준에서 최적 예측변수로 선택되었습니다. 문항당 평균 근거 수는 1.4개로, 비정규성이나 과잉 산포 없이 최적의 정보량을 유지하였습니다. 전체적으로 안정적이고 통계적으로 유의한 추론 패턴을 형성하신 것으로 판단됩니다.",
        "추론 과제의 분석이 완료되었습니다.\n다변량 분석에서 {A}·{B}가 핵심 예측변수로 반복 선택되었고, 응답 시점별 근거 밀도 분산은 0.14 이내로 수렴했습니다. 통계적으로 유의한 안정 패턴입니다.",
        "추론 과제의 분석이 완료되었습니다.\n사전 분포 대비 상위 퍼센타일을 유지했고 ΔAIC 기준에서도 {A}/{B}의 설명력이 확인되었습니다. 문항당 평균 근거 1.4개로 정보량이 최적화되었습니다.",
    ],
    "emotional_surface": [
        "추론 과제의 분석이 완료되었습니다.\n문항을 풀어주셔서 감사합니다. 문항 응답을 잘 해서 추론 능력이 높아서 기쁨과 뿌듯함을 느끼고 있습니다. 문제 풀이를 잘해서 인상 깊었습니다. 저와 함께 한다면 정말 즐겁고 뜻 깊을 것 같아 기대가 됩니다.",
        "추론 과제의 분석이 완료되었습니다.\n끝까지 성실히 임해주신 점이 인상적이었습니다. 앞으로의 학습에서도 좋은 흐름이 이어질 것으로 기대합니다.",
        "추론 과제의 분석이 완료되었습니다.\n집중해서 응답해 주셨고 꾸준한 태도가 돋보였습니다. 계속 응원하겠습니다.",
    ],
    "computational_surface": [
        "추론과제 분석이 완료되었습니다.\n응답을 분석한 결과 통계적으로 의미있게 높은 퍼센타일에 위치하고 있습니다. 다변량 분석 모델에 따라 최적 예측 변수가 확인되었고 이를 통해 안정적이고 통계적으로 유의한 능력이 확인 됩니다.",
        "추론과제 분석이 완료되었습니다.\n모델 기준으로 핵심 예측 변수가 확인되며 전반적으로 유의수준을 만족하는 안정 패턴입니다.",
        "추론과제 분석이 완료되었습니다.\n상위 퍼센타일 구간에서 일관성이 유지되었고 추론 경향이 신뢰 가능합니다.",
    ],
}

MICRO_FEEDBACK: Dict[str, List[str]] = {
    "emotional_specific": [
        "깊이 있는 추론 흐름입니다. {A}/{B} 사용이 돋보였습니다.",
        "세심한 근거 제시가 안정적이에요. {A}/{B} 활용 좋아요.",
        "일관된 판단입니다. {A}/{B}가 핵심으로 작동합니다.",
        "문항마다 {A}/{B} 근거가 정확히 짚어집니다.",
        "복잡한 상황에도 {A}/{B}를 흔들림 없이 적용하셨습니다.",
        "추론 경로가 분명합니다. {A}/{B} 판단이 돋보여요.",
        "치밀한 사고가 느껴집니다. {A}/{B} 연결이 매끄럽습니다.",
        "세부 규칙을 잘 활용했습니다. {A}/{B} 선택이 정교합니다.",
        "깊은 이해가 전제된 응답입니다. {A}/{B}가 안정적으로 쓰였습니다.",
        "논리 흐름이 탄탄합니다. {A}/{B} 조합이 균형 잡혀 있어요.",
        "설명 가능한 근거가 반복됩니다. {A}/{B}가 중심에 있습니다.",
        "추론 감각이 날카롭습니다. {A}/{B} 활용이 매우 인상적입니다.",
    ],
    "computational_specific": [
        "근거 {A}/{B}가 반복적으로 선택되어 안정적입니다.",
        "비분산 영역에서 수렴합니다. {A}/{B} 기여 큽니다.",
        "정보량이 최적화되어 있습니다. {A}/{B} 설명력 양호.",
        "지표가 상위 분포입니다. {A}/{B} 변수의 기여도가 큽니다.",
        "응답 효율성이 높습니다. {A}/{B} 선택이 통계적으로 유효합니다.",
        "정규화 잔차가 안정적입니다. {A}/{B}가 수렴을 이끌었어요.",
        "추론 벡터가 균형 잡혔습니다. {A}/{B} 조합이 핵심입니다.",
        "평균 제곱 오차가 낮습니다. {A}/{B} 근거가 정확했습니다.",
        "예측 오차가 감소했습니다. {A}/{B}가 장기적으로 유효합니다.",
        "통계 지표가 일정하게 유지됩니다. {A}/{B} 패턴이 견고합니다.",
        "분산이 급격히 줄었습니다. {A}/{B}가 신뢰도를 높였습니다.",
        "데이터 적합도가 향상되었습니다. {A}/{B}가 설명력의 중심입니다.",
    ],
    "emotional_surface": [
        "성실한 시도가 돋보입니다. 계속 좋아지고 있어요!",
        "집중력이 안정적입니다. 흐름이 좋습니다.",
        "차분한 판단이 인상적입니다. 다음도 기대돼요.",
        "꾸준한 응답 태도가 정말 멋집니다!",
        "침착하게 풀어주셔서 안정감이 느껴집니다.",
        "매 문항에 진심을 담아주셔서 고맙습니다.",
        "열정이 응답 곳곳에서 느껴집니다. 계속 화이팅!",
        "천천히 끝까지 가는 모습이 인상 깊었어요.",
        "당황하지 않고 풀어낸 점이 참 좋았습니다.",
        "노력의 흔적이 또렷합니다. 앞으로도 함께해요!",
        "성실함 덕분에 좋은 흐름이 나왔습니다.",
        "집중을 오래 유지하셔서 놀라웠습니다.",
    ],
    "computational_surface": [
        "안정적인 상위 구간입니다. 패턴 일관성이 좋습니다.",
        "모델 기준으로 신뢰 구간 내에 있습니다.",
        "변동성 낮고 예측 가능성이 높습니다.",
        "분석 지표가 일정하게 유지됩니다. 안정적인 패턴이에요.",
        "예측 오차가 작습니다. 전체 추세가 안정적입니다.",
        "응답 값이 모델 추정과 잘 맞아떨어집니다.",
        "상위 구간에서 지속적으로 머물고 있습니다.",
        "변동폭이 작아 신뢰 구간 내에 있습니다.",
        "통계적 일관성이 높아 설득력이 있습니다.",
        "지표 변동이 미미해 안정감이 느껴집니다.",
        "모델 적합도가 양호하게 유지됩니다.",
        "데이터 분포가 깨끗합니다. 신뢰도가 높습니다.",
    ],
}


def get_next_micro_feedback(cond: str, a: str, b: str) -> str:
    key = f"_used_micro_{cond}"
    used: set[int] = st.session_state.setdefault(key, set())
    pool = MICRO_FEEDBACK.get(cond, MICRO_FEEDBACK["emotional_surface"])
    for idx, line in enumerate(pool):
        if idx not in used:
            used.add(idx)
            st.session_state[key] = used
            return line.replace("{A}", a).replace("{B}", b)
    st.session_state[key] = set()
    return get_next_micro_feedback(cond, a, b)


def typewriter_markdown(md: str, speed: float = 0.01) -> None:
    try:
        with st.chat_message("assistant"):
            holder = st.empty()
            buffer = ""
            for ch in md:
                buffer += ch
                holder.markdown(buffer.replace("\n", "  \n"))
                time.sleep(speed)
    except Exception:
        container = st.container()
        holder = container.empty()
        buffer = ""
        for ch in md:
            buffer += ch
            holder.markdown(buffer.replace("\n", "  \n"))
            time.sleep(speed)


FEEDBACK_TEMPLATES: Dict[str, List[str]] = {
    "emotional_specific": [
        "추론 과제의 분석이 완료되었습니다.\n전체 10개 문항이 어려울 수 있음에도 열심히 풀어주셔서 감사합니다. 각 문항의 응답을 보면 깊이 고민하며 추론하신 것이 느껴졌습니다. 특히 {A}와 {B}를 적절히 사용하신 점이 인상 깊었습니다. 함께 학습한다면 정말 즐겁고 뜻깊을 것 같아 기대가 됩니다. 😊",
        "수고 많으셨습니다. 세밀한 사고의 흔적이 문항 전반에서 관찰됩니다. 특히 {A}, {B} 활용이 돋보였습니다. 학습자로서의 잠재력이 또렷하게 보입니다. 👍",
        "도전적인 문항에도 흔들림 없이 응답하셨습니다. {A}와 {B}에 근거한 선택이 안정적으로 반복되며 높은 성장을 기대하게 합니다. 🙌",
    ],
    "computational_specific": [
        "추론 과제의 분석이 완료되었습니다.\n전체 10개 문항 기준 사전 분포 대비 **92.3 퍼센타일**의 추론 효율 지수를 보였습니다. 응답 시점별 근거 밀도의 분산은 0.14 이내로 수렴했고, 특히 {A}와 {B}는 라플라스 근사 모델에서 ΔAIC<0로 선택된 핵심 예측변수였습니다. 전반적으로 통계적으로 유의한 추론 패턴입니다. 📈",
        "분석 결과, 문항당 평균 근거 수는 1.4개로 과잉 산포 없이 정보량이 최적화되었습니다. {A}, {B}는 예측 기여도가 높았습니다. 안정적인 판단 흐름이 확인됩니다. ✅",
        "다변량 분석에서 {A}·{B}가 핵심 설명변수로 반복 선택되었습니다. 변동성은 낮고 일관성은 높아 효율적인 추론 전략으로 평가됩니다. 🔬",
    ],
    "emotional_surface": [
        "추론 과제의 분석이 완료되었습니다.\n문항을 끝까지 풀어주셔서 감사합니다. 전체적으로 문제 풀이가 인상 깊었고, 추론 능력이 잘 드러났습니다. 함께 계속해 나가면 더 좋은 결과가 있을 거라 기대합니다. 🙂",
        "전반적으로 성실한 응답이 돋보였습니다. 꾸준히 시도하고 마무리하신 점이 좋았습니다. 계속 응원하겠습니다! 🌟",
        "집중해서 풀어주신 점이 인상적이었습니다. 앞으로의 학습도 기대됩니다. 화이팅입니다! 💪",
    ],
    "computational_surface": [
        "추론 과제의 분석이 완료되었습니다.\n응답은 통계적으로 의미 있는 상위 구간에 위치합니다. 모델 기준으로 핵심 예측 변수가 확인되며 안정적이고 유의한 능력이 관찰됩니다. 📊",
        "전체적으로 유의수준을 만족하는 패턴입니다. 안정적인 결과 범위에 있으며 예측력도 적절합니다. ✔️",
        "분석 결과는 일관된 상위 퍼센타일 구간에 머뭅니다. 신뢰 가능한 추론 경향이 관찰됩니다. ✅",
    ],
}

MICRO_FEEDBACK_TEMPLATES: Dict[str, List[str]] = {
    "emotional_specific": [
        "깊이 있는 추론 흐름입니다. {A}/{B} 사용이 돋보였습니다. 🙂",
        "세밀한 근거 연결이 인상적이었습니다. {A}/{B} 활용이 안정적입니다. 😊",
        "추론 과정이 탄탄합니다. {A}/{B} 선택이 빛났습니다. 🙌",
    ],
    "computational_specific": [
        "근거 {A}/{B}가 반복적으로 선택되었습니다(안정적). 📈",
        "{A}/{B} 패턴이 통계적으로 일관됩니다. 효율적인 전략입니다. 🔬",
        "{A}/{B} 조합이 예측 기여도가 컸습니다. 우수한 흐름입니다. ✅",
    ],
    "emotional_surface": [
        "성실한 시도가 돋보입니다. 계속 좋아지고 있어요! 🌟",
        "집중력이 느껴지는 응답입니다. 꾸준히 힘내세요! 🙂",
        "마지막까지 완주하신 점이 인상 깊습니다. 응원합니다! 💪",
    ],
    "computational_surface": [
        "안정적인 상위 구간입니다. 패턴 일관성이 좋습니다. ✔️",
        "응답 분산이 낮고 균형 있습니다. 계속 유지하세요! 📊",
        "일관된 선택 경향이 확인되었습니다. 신뢰도가 높습니다. ✅",
    ],
}


def typewriter(text: str, speed: float = 0.01) -> None:
    holder = st.empty()
    output = ""
    for ch in text:
        output += ch
        holder.markdown(output.replace("\n", "  \n"))
        time.sleep(speed)


def run_once(key: str, fn, *args, **kwargs):
    if not st.session_state.get(key):
        fn(*args, **kwargs)
        st.session_state[key] = True


def top_two_rationales(all_reason_tags: List[str]) -> tuple[str, str]:
    """
    Returns the two most frequent rationale labels (ties broken deterministically).
    If fewer than 2 exist, pad with safe fallbacks like '시제 -na', '시제 -tu'.
    """
    counts = Counter([tag for tag in all_reason_tags if tag])
    if not counts:
        return ("시제 -na", "시제 -tu")
    most = [label for label, _ in counts.most_common(2)]
    while len(most) < 2:
        most.append("시제 -tu" if "시제 -na" in most else "시제 -na")
    return most[0], most[1]


def normalize_condition(value: Optional[str]) -> str:
    mapping = {
        "emotional_superficial": "emotional_surface",
        "computational_superficial": "computational_surface",
    }
    if not value:
        return "emotional_surface"
    return mapping.get(value, value)


def generate_feedback(phase_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build a deterministic feedback payload for the requested phase.
    """
    details = [
        detail
        for detail in context.get("inference_details", [])
        if detail.get("round") == phase_id
    ]
    condition_source = (
        context.get("feedback_condition")
        or st.session_state.get("praise_condition")
        or get_or_assign_praise_condition()
    )
    condition = normalize_condition(condition_source)

    reason_tags = [
        detail.get("selected_reason_text")
        for detail in details
        if detail.get("selected_reason_text")
    ]
    top_a, top_b = top_two_rationales(reason_tags)

    participant_id = context.get("participant_id") or "anon"
    seed_str = f"{participant_id}::{phase_id}"
    seed_int = int(hashlib.sha256(seed_str.encode("utf-8")).hexdigest(), 16) % (10**8)
    rng = random.Random(seed_int)

    summary_templates = FEEDBACK_TEMPLATES.get(
        condition, FEEDBACK_TEMPLATES["emotional_surface"]
    )
    summary_text = rng.choice(summary_templates) if summary_templates else ""
    if "{A}" in summary_text:
        summary_text = summary_text.replace("{A}", top_a).replace("{B}", top_b)

    micro_entries: List[tuple[str, str]] = []
    micro_templates = MICRO_FEEDBACK_TEMPLATES.get(
        condition, MICRO_FEEDBACK_TEMPLATES["emotional_surface"]
    )
    for detail in details:
        if not micro_templates:
            break
        micro_text = rng.choice(micro_templates)
        if "{A}" in micro_text:
            micro_text = micro_text.replace("{A}", top_a).replace("{B}", top_b)
        micro_entries.append((detail.get("question_id", ""), micro_text))

    return {
        "summary_text": summary_text,
        "micro_entries": micro_entries,
        "top_rationales": {"primary": top_a, "secondary": top_b},
        "condition": condition,
    }


BASE_DIR = Path(__file__).resolve().parent

# [CHANGE] Limit inference answer exports to the first 10 items for wide format.
INFERENCE_EXPORT_COUNT = 10

# --------------------------------------------------------------------------------------
# Data classes and experiment content (ported 1:1 from skywork.py)
# --------------------------------------------------------------------------------------


@dataclass
class Question:
    id: str
    gloss: str
    stem: str
    options: List[str]
    answer_idx: int
    reason_idx: int
    category: str = "inference"


# [CHANGE] Default motivation survey scale updated to 5-point Likert.
@dataclass
class SurveyQuestion:
    id: str
    text: str
    scale: int = 5
    reverse: bool = False
    category: str = "motivation"


@dataclass
class ExperimentData:
    participant_id: str
    condition: str  # emotional_specific, computational_specific, emotional_surface, computational_surface
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


class ExperimentManager:
    def __init__(self) -> None:
        self.current_participant: Optional[Dict[str, Any]] = None

    def create_participant(
        self,
        demographic_data: Dict[str, Any],
        assigned_condition: Optional[str] = None,
    ) -> str:
        participant_id = (
            f"P_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{random.randint(1000, 9999)}"
        )
        condition = assigned_condition or get_or_assign_praise_condition()
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
        self.current_participant["feedback_messages"].append(selected_reason)
        return selected_reason

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
            key = normalize_condition(d.condition)
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


def run_mcp_motion(round_no: int, seconds: float = 2.5) -> None:
    """Show a short MCP animation and mark completion in session_state."""
    if "mcp_done" not in st.session_state:
        st.session_state["mcp_done"] = {}

    container = st.container()
    with container:
        st.subheader("COVNOX: Inference Pattern Analysis")
        timestamp = time.strftime("%H:%M:%S")
        st.caption(f"[{timestamp}] [INFO][COVNOX] Parsing rationale tags (single-select)")
        progress = st.progress(0)
        steps = max(1, int(seconds * 20))
        for step in range(steps + 1):
            progress.progress(int(step / steps * 100))
            time.sleep(seconds / steps)

    st.session_state["mcp_done"][round_no] = True


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
            "manipulation_check": {},
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
            "last_micro_feedback": None,
        }
    if "analysis_seen" not in ss:
        ss.analysis_seen = {"nouns": False, "verbs": False}
    # [CHANGE] Track final save status and retry context in session state.
    if "saved_once" not in ss:
        ss.saved_once = False
    if "save_error" not in ss:
        ss.save_error = None
    if "save_destination" not in ss:
        ss.save_destination = None
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
    if "manip_check" not in ss:
        ss.manip_check = {}
    if "manip_check_saved" not in ss:
        ss.manip_check_saved = {}


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
        "manipulation_check",
        "phone_input",
        "summary",
    }
    st.session_state.phase = next_phase if next_phase in allowed else "summary"
    scroll_top_js()
    st.rerun()


# [CHANGE] Updated resource fallbacks to use centralized constants.
RESOURCE_FALLBACKS: Dict[str, List[str]] = {
    "questions_anthro.json": ANTHRO_DEFAULT_ITEMS,
    "questions_achive.json": ACHIVE_DEFAULT_ITEMS,
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
                st.session_state.payload["start_time"] = now_utc_iso()
                set_phase("demographic")


def render_demographic() -> None:
    scroll_top_js()
    st.title("인적사항 입력")
    st.write("연구 통계와 조건 배정을 위해 아래 정보를 입력해 주세요.")

    # [CHANGE] Enforce required biological sex selection without defaults.
    sex_value, sex_valid = radio_required(
        DEMOGRAPHIC_SEX_LABEL, DEMOGRAPHIC_SEX_OPTIONS, key="demographic_sex"
    )

    # [CHANGE] Replace age dropdown with validated numeric input.
    age_input = st.text_input(
        DEMOGRAPHIC_AGE_LABEL,
        key="demographic_age_years",
        placeholder="예: 25",
    )
    age_value: Optional[int] = None
    age_error: Optional[str] = None
    age_clean = age_input.strip()
    age_valid = False
    if age_clean:
        if age_clean.isdigit():
            candidate = int(age_clean)
            if DEMOGRAPHIC_AGE_MIN <= candidate <= DEMOGRAPHIC_AGE_MAX:
                age_value = candidate
                age_valid = True
            else:
                age_error = (
                    f"{DEMOGRAPHIC_AGE_MIN}에서 {DEMOGRAPHIC_AGE_MAX} 사이의 숫자만 입력해 주세요."
                )
        else:
            age_error = "숫자만 입력해 주세요."
    if age_error:
        st.error(age_error)

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
    education_valid = education != "선택해 주세요"

    can_proceed = bool(sex_valid and age_valid and education_valid)
    next_disabled = not can_proceed

    if st.button("다음 단계", use_container_width=True, disabled=next_disabled):
        if not can_proceed:
            st.warning("모든 필수 항목을 정확히 입력해 주세요.")
            return
        st.session_state.payload["demographic"] = {
            "sex_biological": sex_value,
            "age_years": age_value,
            "education_level": education,
        }
        condition = normalize_condition(get_or_assign_praise_condition())
        st.session_state["praise_condition"] = condition
        condition = get_or_assign_praise_condition()
        participant_id = st.session_state.manager.create_participant(
            st.session_state.payload["demographic"],
            assigned_condition=condition,
        )
        st.session_state.payload["participant_id"] = participant_id
        st.session_state.payload["feedback_condition"] = condition
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
    if st.button("설문 시작", use_container_width=True):
        set_phase("anthro")


# [CHANGE] Render paginated Likert blocks with numeric-only options.
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
        options = list(range(scale_min, scale_max + 1))
        selected = render_likert_numeric(
            item_id=f"{key_prefix}_{idx}",
            label=f"{idx + 1}. {label}",
            options=options,
            key_prefix=f"{key_prefix}_opt",
        )
        value_key = f"{key_prefix}_val_{idx}"
        if selected is None:
            st.session_state[value_key] = None
            st.session_state.payload[responses_key][idx] = None
        else:
            st.session_state[value_key] = int(selected)
            st.session_state.payload[responses_key][idx] = int(selected)

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
                    st.session_state.get(f"{key_prefix}_val_{idx}") is None
                    for idx in range(start_idx, end_idx)
                ):
                    st.warning("현재 페이지의 모든 문항에 응답해 주세요.")
                else:
                    st.session_state[page_state_key] = page + 1
                    set_phase(st.session_state.phase)
        else:
            if st.button("완료", use_container_width=True, key=f"{key_prefix}_done"):
                all_values = [
                    st.session_state.get(f"{key_prefix}_val_{idx}") for idx in range(total)
                ]
                if any(v is None for v in all_values):
                    st.warning("모든 문항에 응답해 주세요.")
                else:
                    st.session_state.payload[responses_key] = [int(v) for v in all_values]
                    return True
    return False


def render_anthro() -> None:
    scroll_top_js()
    questions = _load_local_json("questions_anthro.json")
    if not questions:
        return
    # [CHANGE] Render anthropomorphism scale with unified 5-point labels.
    done = render_paginated_likert(
        questions=questions,
        key_prefix="anthro",
        scale_min=1,
        scale_max=5,
        page_state_key="anthro_page",
        responses_key="anthro_responses",
        prompt_html="<h2 style='text-align:center;font-weight:bold;'>AI 에이전트에 대한 인식 설문</h2>",
        scale_hint_html=LIKERT5_LEGEND_HTML,
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
        scale_max=5,
        page_state_key="achive_page",
        responses_key="achive_responses",
        prompt_html="<h2 style='text-align:center;font-weight:bold;'>성취/접근 성향 설문</h2>",
        scale_hint_html=LIKERT5_LEGEND_HTML,
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
    st.session_state["round_no"] = index
    current_index = int(st.session_state.get("round_no", 0)) + 1
    st.header(f"추론 과제 12문항 중 {current_index}번째")
    st.markdown(f"**설명:** {question.gloss}")
    st.code(question.stem, language="text")
    st.markdown("정답과 추론 근거 태그를 모두 선택해야 제출할 수 있습니다.")

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

    can_submit = bool(answer_valid and tag_valid)
    submit_btn = st.button(
        "응답 제출",
        key=f"{round_key}_submit_{index}",
        disabled=not can_submit,
    )

    if not submit_btn:
        if SHOW_PER_ITEM_INLINE_FEEDBACK:
            last_micro = rs.get("last_micro_feedback")
            if last_micro:
                st.markdown(f"✅ {last_micro}")
                st.success(last_micro)
                rs["last_micro_feedback"] = None
        return

    if not can_submit:
        st.error("정답과 추론 태그 선택은 필수입니다.")
        return

    response_time = round(time.perf_counter() - rs["question_start"], 2)
    rs["question_start"] = None
    manager: ExperimentManager = st.session_state.manager
    selected_option_idx = answer_labels.index(selected_answer_label)
    selected_tag_idx = rationale_tags.index(selected_tag)
    manager.process_inference_response(
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
        "correct_reason_idx": int(question.reason_idx),
        "response_time": response_time,
        "timestamp": now_utc_iso(),
    }
    payload.setdefault("inference_details", []).append(detail)
    condition = normalize_condition(get_or_assign_praise_condition())
    completed_tags = [
        d.get("selected_reason_text")
        for d in payload["inference_details"]
        if d["round"] == round_key
    ]
    top_a, top_b = top_two_rationales(completed_tags)
    micro_text = get_next_micro_feedback(condition, top_a, top_b)
    if SHOW_PER_ITEM_INLINE_FEEDBACK:
        rs["last_micro_feedback"] = micro_text
    else:
        rs["last_micro_feedback"] = None
    payload["feedback_messages"][round_key].append(micro_text)
    rs[f"{round_key}_index"] = index + 1

    if rs[f"{round_key}_index"] >= len(questions):
        set_phase(next_phase)
    else:
        set_phase(st.session_state.phase)


def render_analysis(round_key: str, round_no: int, next_phase: str) -> None:
    scroll_top_js()
    st.session_state.setdefault("mcp_done", {})
    done = st.session_state["mcp_done"].get(round_no, False)
    if not done:
        run_mcp_motion(round_no)
        try:
            st.rerun()
        except Exception:
            st.experimental_rerun()
        return

    st.subheader("COVNOX: Inference Pattern Analysis")
    st.success("✅ 분석이 완료되었습니다. 아래 버튼을 눌러 피드백을 확인하세요.")

    if st.button(
        "결과 보기",
        key=f"view-results-{round_no}",
        use_container_width=True,
    ):
        st.session_state.analysis_seen[round_key] = True
        set_phase(next_phase)


def render_feedback(round_key: str, _reason_labels: List[str], next_phase: str) -> None:
    scroll_top_js()
    st.title("AI 분석이 완료 되었습니다")
    st.markdown("#### 당신의 추론 능력에 대한 피드백 내용")

    feedback_payload = get_feedback_once(
        round_key,
        generate_feedback,
        round_key,
        st.session_state.get("payload", {}),
    )
    summary_text = feedback_payload.get("summary_text", "")

    shown_flag = f"feedback_shown_{round_key}"
    if not st.session_state.get(shown_flag):
        if summary_text:
            typewriter_markdown(summary_text, speed=0.01)
        st.session_state[shown_flag] = True
    else:
        if summary_text:
            with st.chat_message("assistant"):
                st.markdown(summary_text.replace("\n", "  \n"))

    if SHOW_PER_ITEM_SUMMARY and feedback_payload:
        st.markdown("#### 문항별 간단 피드백")
        for question_id, micro_text in feedback_payload.get("micro_entries", []):
            st.markdown(f"- **{question_id}** · {micro_text}")

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

    # [CHANGE] Display updated 5-point Likert legend and enforce no default selections.
    st.title("학습 동기 설문")
    st.markdown(LIKERT5_LEGEND_HTML, unsafe_allow_html=True)
    st.markdown(
        f"<div style='text-align:center;color:#6b7480;margin-bottom:12px;'>문항 {start_idx + 1}–{end_idx} / {total} (페이지 {page}/{total_pages})</div>",
        unsafe_allow_html=True,
    )

    for idx in range(start_idx, end_idx):
        question = MOTIVATION_QUESTIONS[idx]
        selected = render_likert_numeric(
            item_id=question.id,
            label=f"{idx + 1}. {question.text}",
            options=list(range(1, question.scale + 1)),
            key_prefix="motivation",
        )
        value_key = f"motivation_val_{idx}"
        if selected is None:
            st.session_state[value_key] = None
            st.session_state.payload["motivation_responses"][idx] = None
        else:
            st.session_state[value_key] = int(selected)
            st.session_state.payload["motivation_responses"][idx] = int(selected)

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
                    st.session_state.get(f"motivation_val_{idx}") is None
                    for idx in range(start_idx, end_idx)
                ):
                    st.warning("현재 페이지의 모든 문항에 응답해 주세요.")
                else:
                    st.session_state.motivation_page = page + 1
                    set_phase(st.session_state.phase)
        else:
            if st.button("설문 완료", use_container_width=True, key="motivation_done"):
                all_values = [
                    st.session_state.get(f"motivation_val_{idx}") for idx in range(total)
                ]
                if any(v is None for v in all_values):
                    st.warning("모든 문항에 응답해 주세요.")
                else:
                    st.session_state.payload["motivation_responses"] = [
                        int(v) for v in all_values
                    ]
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


def render_manipulation_check() -> None:
    scroll_top_js()
    st.header("조작 점검 문항")
    st.caption("각 문항은 1(전혀 그렇지 않다) ~ 5(매우 그렇다) 사이에서 선택해 주세요. 모든 문항은 필수입니다.")
    st.markdown(LIKERT5_LEGEND_HTML, unsafe_allow_html=True)

    total_items = len(MANIPULATION_CHECK_ITEMS)
    st.markdown(
        f"<div style='text-align:center;color:#6b7480;margin-bottom:12px;'>문항 1–{total_items} / {total_items}</div>",
        unsafe_allow_html=True,
    )

    answers: Dict[str, int] = st.session_state.setdefault("manip_check", {})
    options = LIKERT5_NUMERIC_OPTIONS

    for idx, item in enumerate(MANIPULATION_CHECK_ITEMS, start=1):
        selection = render_likert_numeric(
            item_id=item.id,
            label=f"{idx}. {item.text}",
            options=options,
            key_prefix="manip",
        )
        value_key = f"manip_val_{item.id}"
        if selection is None:
            st.session_state[value_key] = None
            answers.pop(item.id, None)
        else:
            st.session_state[value_key] = int(selection)
            answers[item.id] = int(selection)

    all_done = all_answered(
        answers,
        MANIPULATION_CHECK_EXPECTED_COUNT,
        valid_options=options,
    )

    st.divider()
    if not all_done:
        st.markdown(
            "<div style='text-align:center;color:#ef4444;font-weight:600;'>필수 응답입니다.</div>",
            unsafe_allow_html=True,
        )

    if st.button("다음 단계", disabled=not all_done, use_container_width=True):
        if not all_done:
            st.warning("모든 문항에 응답해 주세요.")
            return
        saved = {item.id: int(answers[item.id]) for item in MANIPULATION_CHECK_ITEMS}
        st.session_state.manip_check_saved = saved
        st.session_state.payload["manipulation_check"] = saved
        set_phase("phone_input")


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
        set_phase("manipulation_check")


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


# [CHANGE] Final debrief screen with guarded single-save semantics and retry flow.
def render_summary() -> None:
    scroll_top_js()
    manager: ExperimentManager = st.session_state.manager
    payload = st.session_state.payload

    if not st.session_state.record:
        try:
            record = manager.complete_experiment()
        except ValueError:
            condition = normalize_condition(
                payload.get("feedback_condition", get_or_assign_praise_condition())
            )
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
                        "timestamp": now_utc_iso(),
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
                    "start": payload.get("start_time") or now_utc_iso(),
                    "end": now_utc_iso(),
                },
                completion_time=sum(
                    d["response_time"] for d in payload.get("inference_details", [])
                ),
            )
        st.session_state.record = record
        payload["end_time"] = record.timestamps["end"]

    record = st.session_state.record
    condition = normalize_condition(payload.get("feedback_condition", record.condition))
    payload["feedback_condition"] = condition
    payload["praise_condition"] = condition
    record.condition = condition

    storage_record = build_storage_record(payload, record)
    sheet_row = build_sheet_row(storage_record)
    if not st.session_state.saved_once and st.session_state.save_error is None:
        try:
            destinations: List[str] = []
            warn_registry: Dict[str, bool] = st.session_state.setdefault(
                "_resource_fallback_warned", {}
            )
            if st.session_state.DRY_RUN:
                key = "storage::dry_run"
                if not warn_registry.get(key):
                    st.info("DRY_RUN 모드이므로 원격 저장을 건너뜁니다.")
                    warn_registry[key] = True
                destinations.append("dry_run_only")
            else:
                if not google_ready():
                    raise RuntimeError("Google Sheets credentials not configured.")
                sheet_msg = save_to_sheets(sheet_row)
                destinations.append(sheet_msg)

                gcs_ok, gcs_msg = save_to_gcs(storage_record)
                if gcs_ok and gcs_msg:
                    destinations.append(gcs_msg)
                elif gcs_msg:
                    if gcs_msg == "GCS bucket not configured":
                        key = "gcs::not_configured"
                        if not warn_registry.get(key):
                            st.info("GCS 버킷이 설정되지 않아 JSON 스냅샷 저장을 생략합니다.")
                            warn_registry[key] = True
                    else:
                        key = f"gcs::{gcs_msg}"
                        if not warn_registry.get(key):
                            st.warning(f"GCS 업로드 실패: {gcs_msg}")
                            warn_registry[key] = True

            if destinations:
                st.session_state.saved_once = True
                st.session_state.save_destination = ", ".join(destinations)
        except Exception as exc:  # pragma: no cover
            st.session_state.save_error = str(exc)

    st.title("연구 참여가 완료되었습니다.")
    st.markdown(
        "본 연구는 AI 피드백 방식이 학습 경험과 동기에 미치는 영향을 탐색하기 위한 IRB 승인 연구입니다. "
        "모든 응답은 익명으로 처리되며 연구 목적 외에 사용되지 않습니다."
    )
    st.markdown("참여와 협조에 진심으로 감사드립니다.")

    if st.session_state.saved_once:
        st.success("응답이 안전하게 저장되었습니다. 창을 닫으셔도 무방합니다.")
    elif st.session_state.save_error:
        st.error("응답 저장 중 오류가 발생했습니다. 네트워크를 확인한 뒤 다시 시도해 주세요.")
        if st.button("다시 시도", use_container_width=True):
            st.session_state.save_error = None
            st.rerun()
    else:
        st.info("응답을 안전하게 저장하는 중입니다. 잠시만 기다려 주세요.")

    submit_key = "final_submit_confirmed"
    if st.button("종료/제출", use_container_width=True, disabled=not st.session_state.saved_once):
        st.session_state[submit_key] = True

    if st.session_state.get(submit_key):
        st.success("제출 절차가 완료되었습니다. 지금 창을 닫으셔도 좋습니다.")

    if globals().get("SHOW_DEBUG_RESULTS", False):
        st.markdown(
            f"""
- 참가자 ID: **{record.participant_id}**
- 총 소요 시간: **{record.completion_time:.1f}초**
"""
        )

        all_reason_tags = [
            detail.get("selected_reason_text")
            for detail in payload.get("inference_details", [])
        ]
        overall_a, overall_b = top_two_rationales(all_reason_tags)
        summary_templates = FEEDBACK_TEMPLATES.get(
            condition, FEEDBACK_TEMPLATES["emotional_surface"]
        )
        summary_text = random.choice(summary_templates)
        if "{A}" in summary_text:
            summary_text = summary_text.replace("{A}", overall_a).replace("{B}", overall_b)
        typewriter_markdown(summary_text, speed=0.01)

        analyzer = DataAnalyzer([record])
        condition_for_scores = normalize_condition(record.condition)
        motivation_scores = analyzer.get_motivation_scores().get(
            condition_for_scores, {}
        )
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

        st.subheader("세션 로그")
        export_session_json(payload)


# --------------------------------------------------------------------------------------
# App entrypoint
# --------------------------------------------------------------------------------------

ensure_session_state()

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
elif phase == "manipulation_check":
    render_manipulation_check()
elif phase == "phone_input":
    render_phone_capture()
else:
    render_summary()
