# [CHANGE] Centralized shared survey and UI constants.
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


# [CHANGE] Standard 5-point Likert anchors used across surveys.
LIKERT5_ANCHORS: Dict[int, str] = {
    1: "전혀 그렇지 않다",
    2: "그렇지 않다",
    3: "보통이다",
    4: "그렇다",
    5: "매우 그렇다",
}


# [CHANGE] Pre-rendered legend snippet for compact 5-point Likert instructions.
LIKERT5_LEGEND_HTML: str = """
<div style='display:flex;justify-content:center;gap:12px;flex-wrap:wrap;font-size:16px;margin-bottom:22px;'>
  <span><b>1</b> : 전혀 그렇지 않다</span><span>—</span>
  <span><b>3</b> : 보통이다</span><span>—</span>
  <span><b>5</b> : 매우 그렇다</span>
</div>
""".strip()


# [CHANGE] Canonical numeric options for 5-point Likert radios.
LIKERT5_NUMERIC_OPTIONS: List[int] = [1, 2, 3, 4, 5]


# [CHANGE] Demographic form labels and constraints.
DEMOGRAPHIC_SEX_LABEL: str = "생물학적 성별을 선택해 주세요."
DEMOGRAPHIC_SEX_OPTIONS: List[str] = ["남자", "여자"]
DEMOGRAPHIC_AGE_LABEL: str = "만 나이를 입력해 주세요 (Enter your age in years, international age)."
DEMOGRAPHIC_AGE_MIN: int = 1
DEMOGRAPHIC_AGE_MAX: int = 120


# [CHANGE] Default fallback items for anthropomorphism and achievement surveys.
ANTHRO_DEFAULT_ITEMS: List[str] = [
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

ACHIVE_DEFAULT_ITEMS: List[str] = [
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


# [CHANGE] Manipulation check items (5-point Likert, required).
@dataclass(frozen=True)
class ManipulationCheckItem:
    id: str
    text: str


MANIPULATION_CHECK_ITEMS: List[ManipulationCheckItem] = [
    ManipulationCheckItem("mc_01", "피드백이 따뜻했다."),
    ManipulationCheckItem("mc_02", "격려/공감을 느꼈다."),
    ManipulationCheckItem("mc_03", "정서적 표현이 충분했다."),
    ManipulationCheckItem("mc_04", "기분이 좋아지도록 도와줬다."),
    ManipulationCheckItem("mc_05", "피드백이 분석적이었다."),
    ManipulationCheckItem("mc_06", "구체적인 근거 설명이 포함되었다."),
    ManipulationCheckItem("mc_07", "데이터나 지표가 언급되었다."),
    ManipulationCheckItem("mc_08", "논리적인 근거가 분명했다."),
    ManipulationCheckItem("mc_09", "친근한 표현이 많았다."),
    ManipulationCheckItem("mc_10", "정량적인 평가 항목이 제시되었다."),
    ManipulationCheckItem("mc_11", "기술적인 용어가 사용되었다."),
    ManipulationCheckItem("mc_12", "나의 노력을 인정하는 말이 있었다."),
    ManipulationCheckItem("mc_13", "감정을 고려한 표현이었다."),
    ManipulationCheckItem("mc_14", "객관적인 수치나 통계가 포함되었다."),
    ManipulationCheckItem("mc_15", "칭찬이 진심으로 느껴졌다."),
    ManipulationCheckItem("mc_16", "피드백의 어조가 중립적이었다."),
    ManipulationCheckItem("mc_17", "전략이나 방법에 대한 구체적 지침이 있었다."),
    ManipulationCheckItem("mc_18", "응답의 강점이 명확히 지적되었다."),
]

# [CHANGE] Expected item count for manipulation check validation.
MANIPULATION_CHECK_EXPECTED_COUNT: int = len(MANIPULATION_CHECK_ITEMS)
