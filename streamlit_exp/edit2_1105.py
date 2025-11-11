#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI 피드백 실험 시스템 - 완전판
=================================

이 파일은 AI 피드백 실험의 모든 구성 요소를 포함합니다:
- 추론 과제 (명사구 + 동사 TAM)
- 4가지 조건별 AI 피드백 시스템 (정서/계산 × 구체/피상적)
- 26개 학습 동기 설문 문항
- 웹 인터페이스 구조
- 데이터 분석 도구

실행 방법:
python complete_ai_feedback_experiment_system.py
"""

import random
import json
import time
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum

# =============================================================================
# 데이터 구조 정의
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

# =============================================================================
# 추론 과제 문항 (완성형 문장)
# =============================================================================

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

# 모든 추론 과제 문항
ALL_INFERENCE_QUESTIONS = NOUN_QUESTIONS + VERB_QUESTIONS

# =============================================================================
# 학습 동기 설문 문항 (26개)
# =============================================================================

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
# AI 피드백 시스템 (4가지 조건별 3가지 변형)
# =============================================================================

class AIFeedbackSystem:
    """AI 피드백 생성 시스템"""
    
    def __init__(self):
        self.feedback_templates = {
            PraiseCondition.EMOTIONAL_SPECIFIC: [
                # 변형 1
                "🎉 정말 훌륭해요! 특히 '{reason}'라고 생각하신 부분이 매우 인상적입니다. 이런 깊이 있는 사고방식은 언어학습에서 정말 중요한 능력이에요. 당신의 직관적 이해력이 돋보이는 순간이었습니다! ✨",
                # 변형 2  
                "👏 와, 정말 대단하세요! '{reason}'라는 추론 과정이 너무나 논리적이고 체계적이네요. 이렇게 차근차근 분석하는 능력은 정말 특별한 재능입니다. 계속 이런 식으로 접근하시면 더욱 발전할 수 있을 거예요! 💫",
                # 변형 3
                "🌟 놀라운 통찰력이에요! '{reason}'라고 판단하신 근거가 정말 탁월합니다. 이런 세밀한 관찰력과 분석력은 언어 전문가의 자질을 보여주는 것 같아요. 정말 감탄스럽습니다! 🎯"
            ],
            PraiseCondition.COMPUTATIONAL_SPECIFIC: [
                # 변형 1
                "📊 분석 결과가 매우 우수합니다. 특히 '{reason}'라는 추론 패턴이 언어학적 규칙 체계와 94.7% 일치도를 보입니다. 이러한 체계적 접근법은 효율적인 학습 알고리즘을 나타내며, 인지 처리 능력이 최적화되어 있음을 시사합니다. ⚡",
                # 변형 2
                "🔍 데이터 처리 성능이 탁월합니다. '{reason}'라는 논리적 경로는 정확도 지표에서 상위 8.3%에 해당하는 수준입니다. 패턴 인식 알고리즘이 효과적으로 작동하고 있으며, 학습 효율성이 크게 향상되었습니다. 📈",
                # 변형 3
                "⚙️ 인지 처리 메커니즘이 최적 상태입니다. '{reason}'라는 분석 프로세스는 언어 규칙 데이터베이스와 97.2% 매칭률을 달성했습니다. 이는 고도의 패턴 매칭 능력과 효율적인 정보 처리 시스템을 보여줍니다. 🎯"
            ],
            PraiseCondition.EMOTIONAL_SUPERFICIAL: [
                # 변형 1
                "🎉 정말 훌륭한 답변이에요! 당신의 언어 감각이 정말 뛰어나다는 것을 다시 한번 확인할 수 있었습니다. 이런 직관적인 이해력은 정말 특별한 재능이에요! 계속해서 이런 멋진 모습 보여주세요! ✨",
                # 변형 2
                "👏 와, 정말 대단해요! 언어에 대한 당신의 감각이 얼마나 예리한지 놀라울 따름입니다. 이런 뛰어난 능력을 가지신 분을 만나게 되어 정말 기쁩니다. 앞으로도 이런 놀라운 실력 기대할게요! 🌟",
                # 변형 3
                "💫 정말 인상적이에요! 당신만의 독특한 사고방식이 돋보이는 순간이었습니다. 이런 창의적인 접근법은 정말 보기 드문 능력이에요. 계속해서 이런 멋진 아이디어들을 보여주시길 바랍니다! 🎯"
            ],
            PraiseCondition.COMPUTATIONAL_SUPERFICIAL: [
                # 변형 1
                "📊 시스템 분석 결과 우수한 성능을 보입니다. 언어 처리 알고리즘이 효율적으로 작동하고 있으며, 패턴 인식 능력이 최적화된 상태입니다. 전반적인 인지 처리 메트릭이 향상되었습니다. ⚡",
                # 변형 2
                "🔍 데이터 처리 효율성이 크게 개선되었습니다. 학습 알고리즘의 성능 지표가 상승세를 보이고 있으며, 정보 처리 속도와 정확도가 동시에 향상되었습니다. 시스템 최적화가 성공적으로 진행되고 있습니다. 📈",
                # 변형 3
                "⚙️ 인지 처리 시스템이 안정적으로 작동합니다. 언어 분석 모듈의 성능이 기준치를 상회하고 있으며, 전체적인 처리 효율성이 개선되었습니다. 학습 메커니즘이 원활하게 기능하고 있습니다. 🎯"
            ]
        }
    
    def generate_feedback(self, condition: PraiseCondition, selected_reason: str) -> str:
        """조건에 따른 피드백 생성"""
        templates = self.feedback_templates[condition]
        template = random.choice(templates)
        
        if "specific" in condition.value:
            return template.format(reason=selected_reason)
        else:
            return template

# =============================================================================
# 실험 관리 시스템
# =============================================================================

class ExperimentManager:
    """실험 진행 관리"""
    
    def __init__(self):
        self.feedback_system = AIFeedbackSystem()
        self.current_participant = None
        self.experiment_data = []
    
    def create_participant(self, demographic_data: Dict[str, Any]) -> str:
        """참가자 생성"""
        participant_id = f"P_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{random.randint(1000, 9999)}"
        condition = random.choice(list(PraiseCondition))
        
        self.current_participant = {
            'id': participant_id,
            'condition': condition,
            'demographic': demographic_data,
            'start_time': time.time(),
            'inference_responses': [],
            'survey_responses': [],
            'feedback_messages': []
        }
        
        return participant_id
    
    def process_inference_response(self, question_id: str, selected_option: int, 
                                 selected_reason: str, response_time: float) -> str:
        """추론 과제 응답 처리 및 피드백 생성"""
        if not self.current_participant:
            raise ValueError("참가자가 설정되지 않았습니다.")
        
        # 응답 저장
        response_data = {
            'question_id': question_id,
            'selected_option': selected_option,
            'selected_reason': selected_reason,
            'response_time': response_time,
            'timestamp': datetime.now().isoformat()
        }
        self.current_participant['inference_responses'].append(response_data)
        
        # 피드백 생성
        feedback = self.feedback_system.generate_feedback(
            self.current_participant['condition'], 
            selected_reason
        )
        self.current_participant['feedback_messages'].append(feedback)
        
        return feedback
    
    def process_survey_response(self, question_id: str, rating: int):
        """설문 응답 처리"""
        if not self.current_participant:
            raise ValueError("참가자가 설정되지 않았습니다.")
        
        response_data = {
            'question_id': question_id,
            'rating': rating,
            'timestamp': datetime.now().isoformat()
        }
        self.current_participant['survey_responses'].append(response_data)
    
    def complete_experiment(self) -> ExperimentData:
        """실험 완료 처리"""
        if not self.current_participant:
            raise ValueError("참가자가 설정되지 않았습니다.")
        
        completion_time = time.time() - self.current_participant['start_time']
        
        experiment_data = ExperimentData(
            participant_id=self.current_participant['id'],
            condition=self.current_participant['condition'],
            demographic=self.current_participant['demographic'],
            inference_responses=self.current_participant['inference_responses'],
            survey_responses=self.current_participant['survey_responses'],
            feedback_messages=self.current_participant['feedback_messages'],
            timestamps={
                'start': datetime.fromtimestamp(self.current_participant['start_time']).isoformat(),
                'end': datetime.now().isoformat()
            },
            completion_time=completion_time
        )
        
        self.experiment_data.append(experiment_data)
        self.current_participant = None
        
        return experiment_data

# =============================================================================
# 데이터 분석 도구
# =============================================================================

class DataAnalyzer:
    """실험 데이터 분석"""
    
    def __init__(self, experiment_data: List[ExperimentData]):
        self.data = experiment_data
    
    def get_condition_summary(self) -> Dict[str, int]:
        """조건별 참가자 수"""
        summary = {}
        for data in self.data:
            condition = data.condition.value
            summary[condition] = summary.get(condition, 0) + 1
        return summary
    
    def get_motivation_scores(self) -> Dict[str, Dict[str, float]]:
        """동기 점수 분석"""
        scores = {}
        
        for data in self.data:
            condition = data.condition.value
            if condition not in scores:
                scores[condition] = {
                    'interest_enjoyment': [],
                    'perceived_competence': [],
                    'effort_importance': [],
                    'value_usefulness': [],
                    'autonomy': [],
                    'pressure_tension': []
                }
            
            # 카테고리별 점수 계산
            for response in data.survey_responses:
                question = next((q for q in MOTIVATION_QUESTIONS if q.id == response['question_id']), None)
                if question:
                    rating = response['rating']
                    if question.reverse:
                        rating = 8 - rating  # 7점 척도 역코딩
                    scores[condition][question.category].append(rating)
        
        # 평균 계산
        for condition in scores:
            for category in scores[condition]:
                if scores[condition][category]:
                    scores[condition][category] = sum(scores[condition][category]) / len(scores[condition][category])
                else:
                    scores[condition][category] = 0
        
        return scores
    
    def get_response_time_analysis(self) -> Dict[str, float]:
        """응답 시간 분석"""
        times = {}
        for data in self.data:
            condition = data.condition.value
            if condition not in times:
                times[condition] = []
            
            for response in data.inference_responses:
                times[condition].append(response['response_time'])
        
        # 평균 계산
        for condition in times:
            if times[condition]:
                times[condition] = sum(times[condition]) / len(times[condition])
            else:
                times[condition] = 0
        
        return times
    
    def export_to_csv(self, filename: str = "experiment_results.csv"):
        """CSV 파일로 내보내기"""
        import csv
        
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = [
                'participant_id', 'condition', 'gender', 'age', 
                'completion_time', 'avg_response_time',
                'interest_enjoyment', 'perceived_competence', 'effort_importance',
                'value_usefulness', 'autonomy', 'pressure_tension'
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for data in self.data:
                # 동기 점수 계산
                motivation_scores = {}
                for category in ['interest_enjoyment', 'perceived_competence', 'effort_importance',
                               'value_usefulness', 'autonomy', 'pressure_tension']:
                    scores = []
                    for response in data.survey_responses:
                        question = next((q for q in MOTIVATION_QUESTIONS if q.id == response['question_id']), None)
                        if question and question.category == category:
                            rating = response['rating']
                            if question.reverse:
                                rating = 8 - rating
                            scores.append(rating)
                    motivation_scores[category] = sum(scores) / len(scores) if scores else 0
                
                # 평균 응답 시간 계산
                response_times = [r['response_time'] for r in data.inference_responses]
                avg_response_time = sum(response_times) / len(response_times) if response_times else 0
                
                writer.writerow({
                    'participant_id': data.participant_id,
                    'condition': data.condition.value,
                    'gender': data.demographic.get('gender', ''),
                    'age': data.demographic.get('age', ''),
                    'completion_time': data.completion_time,
                    'avg_response_time': avg_response_time,
                    **motivation_scores
                })

# =============================================================================
# 웹 인터페이스 구조 (React 컴포넌트 구조 설명)
# =============================================================================

WEB_INTERFACE_STRUCTURE = """
웹 인터페이스 구조:

1. 메인 앱 (ExperimentApp.tsx)
   - 실험 진행 상태 관리
   - 단계별 컴포넌트 렌더링
   - 데이터 수집 및 저장

2. 주요 컴포넌트:
   - 인구통계학적 정보 수집 (성별: 드롭다운, 연령: 주관식)
   - 연구 동의서 및 개인정보 수집 동의서
   - MCP 애니메이션 (시각적 전환 효과)
   - 추론 과제 (InferenceTask.tsx)
   - AI 피드백 (PraiseFeedback.tsx) - 타이핑 애니메이션
   - 난이도 조정 (1점=매우 쉬움, 10점=매우 어려움)
   - 학습 동기 설문 (26개 문항, 7점 척도)
   - 디브리핑 (칭찬이 미리 생성된 것임을 설명)
   - 연락처 수집

3. 디자인 시스템:
   - Tailwind CSS 기반
   - 반응형 디자인 (430px 이상 지원)
   - 그라데이션 및 애니메이션 효과
   - 이모티콘 활용한 친근한 UI

4. 상태 관리:
   - 실험 진행 단계 (phase)
   - 참가자 응답 데이터
   - 피드백 조건 할당
   - 타이머 및 응답 시간 측정
"""

# =============================================================================
# 반응형 디자인 CSS
# =============================================================================

RESPONSIVE_CSS = """
/* 반응형 디자인 CSS */
.experiment-container {
  max-width: 100%;
  margin: 0 auto;
  padding: 12px;
}

@media (min-width: 430px) {
  .experiment-container {
    padding: 24px;
  }
}

@media (min-width: 768px) {
  .experiment-container {
    max-width: 768px;
    padding: 32px;
  }
}

/* 동기 설문 라디오 버튼 */
.motivation-scale {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 8px;
}

@media (min-width: 430px) {
  .motivation-scale {
    gap: 16px;
  }
}

/* 타이핑 애니메이션 */
@keyframes typing {
  from { width: 0; }
  to { width: 100%; }
}

@keyframes blink {
  0%, 50% { opacity: 1; }
  51%, 100% { opacity: 0; }
}

.typing-animation {
  overflow: hidden;
  white-space: nowrap;
  animation: typing 2s steps(40, end), blink 0.75s step-end infinite;
}

/* 그라데이션 배경 */
.gradient-bg {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

/* AI 아바타 */
.ai-avatar {
  width: 60px;
  height: 60px;
  border-radius: 50%;
  background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
}
"""

# =============================================================================
# 유틸리티 함수
# =============================================================================

def shuffle_questions(questions: List[Question], seed: Optional[int] = None) -> List[Question]:
    """문항 순서 무작위화"""
    if seed:
        random.seed(seed)
    return random.sample(questions, len(questions))

def assign_condition() -> PraiseCondition:
    """조건 무작위 할당"""
    return random.choice(list(PraiseCondition))

def calculate_motivation_score(responses: List[Dict], category: str) -> float:
    """동기 점수 계산"""
    relevant_questions = [q for q in MOTIVATION_QUESTIONS if q.category == category]
    scores = []
    
    for response in responses:
        question = next((q for q in relevant_questions if q.id == response['question_id']), None)
        if question:
            rating = response['rating']
            if question.reverse:
                rating = 8 - rating  # 7점 척도 역코딩
            scores.append(rating)
    
    return sum(scores) / len(scores) if scores else 0

def validate_demographic_data(data: Dict[str, Any]) -> bool:
    """인구통계학적 데이터 유효성 검사"""
    required_fields = ['gender', 'age']
    return all(field in data and data[field] for field in required_fields)

def format_experiment_summary(data: ExperimentData) -> str:
    """실험 결과 요약"""
    return f"""
실험 완료 요약:
- 참가자 ID: {data.participant_id}
- 조건: {data.condition.value}
- 완료 시간: {data.completion_time:.2f}초
- 추론 과제 응답 수: {len(data.inference_responses)}
- 설문 응답 수: {len(data.survey_responses)}
- 피드백 메시지 수: {len(data.feedback_messages)}
"""

# =============================================================================
# 고급 분석 도구
# =============================================================================

class AdvancedAnalyzer:
    """고급 데이터 분석"""
    
    def __init__(self, data: List[ExperimentData]):
        self.data = data
    
    def condition_comparison(self) -> Dict[str, Any]:
        """조건 간 비교 분석"""
        results = {}
        
        for condition in PraiseCondition:
            condition_data = [d for d in self.data if d.condition == condition]
            if not condition_data:
                continue
                
            # 동기 점수 계산
            motivation_scores = {}
            for category in ['interest_enjoyment', 'perceived_competence', 'effort_importance',
                           'value_usefulness', 'autonomy', 'pressure_tension']:
                scores = []
                for data in condition_data:
                    score = calculate_motivation_score(data.survey_responses, category)
                    if score > 0:
                        scores.append(score)
                motivation_scores[category] = {
                    'mean': sum(scores) / len(scores) if scores else 0,
                    'count': len(scores)
                }
            
            # 응답 시간 분석
            response_times = []
            for data in condition_data:
                times = [r['response_time'] for r in data.inference_responses]
                response_times.extend(times)
            
            results[condition.value] = {
                'n': len(condition_data),
                'motivation_scores': motivation_scores,
                'response_time': {
                    'mean': sum(response_times) / len(response_times) if response_times else 0,
                    'count': len(response_times)
                },
                'completion_time': {
                    'mean': sum(d.completion_time for d in condition_data) / len(condition_data),
                    'count': len(condition_data)
                }
            }
        
        return results
    
    def generate_report(self) -> str:
        """분석 보고서 생성"""
        comparison = self.condition_comparison()
        
        report = "=== AI 피드백 실험 분석 보고서 ===\n\n"
        report += f"총 참가자 수: {len(self.data)}\n\n"
        
        for condition, results in comparison.items():
            report += f"조건: {condition}\n"
            report += f"  참가자 수: {results['n']}\n"
            report += f"  평균 완료 시간: {results['completion_time']['mean']:.2f}초\n"
            report += f"  평균 응답 시간: {results['response_time']['mean']:.2f}초\n"
            report += "  동기 점수:\n"
            for category, scores in results['motivation_scores'].items():
                report += f"    {category}: {scores['mean']:.2f} (n={scores['count']})\n"
            report += "\n"
        
        return report

# =============================================================================
# 메인 실행 함수
# =============================================================================

def run_experiment_demo():
    """실험 시스템 데모 실행"""
    print("🧪 AI 피드백 실험 시스템 데모")
    print("=" * 50)
    
    # 실험 관리자 초기화
    manager = ExperimentManager()
    
    # 가상 참가자 생성
    demographic = {
        'gender': '여성',
        'age': 25,
        'phone': '010-1234-5678'
    }
    
    participant_id = manager.create_participant(demographic)
    print(f"참가자 생성: {participant_id}")
    print(f"할당된 조건: {manager.current_participant['condition'].value}")
    
    # 추론 과제 시뮬레이션
    print("\n📝 추론 과제 시뮬레이션:")
    sample_questions = random.sample(ALL_INFERENCE_QUESTIONS, 3)
    
    for i, question in enumerate(sample_questions, 1):
        print(f"\n문제 {i}: {question.id}")
        print(f"설명: {question.gloss}")
        print(f"문제: {question.stem}")
        
        # 가상 응답
        selected_option = random.randint(0, len(question.options) - 1)
        selected_reason = f"선택지 {selected_option + 1}이 문법적으로 올바른 형태라고 생각합니다"
        response_time = random.uniform(5.0, 15.0)
        
        feedback = manager.process_inference_response(
            question.id, selected_option, selected_reason, response_time
        )
        
        print(f"선택한 답: {question.options[selected_option]}")
        print(f"AI 피드백: {feedback}")
    
    # 설문 시뮬레이션
    print("\n📊 학습 동기 설문 시뮬레이션:")
    sample_survey = random.sample(MOTIVATION_QUESTIONS, 5)
    
    for question in sample_survey:
        rating = random.randint(1, 7)
        manager.process_survey_response(question.id, rating)
        print(f"{question.text}: {rating}점")
    
    # 실험 완료
    experiment_data = manager.complete_experiment()
    print(f"\n✅ 실험 완료!")
    print(format_experiment_summary(experiment_data))
    
    # 데이터 분석 데모
    print("\n📈 데이터 분석 데모:")
    analyzer = DataAnalyzer([experiment_data])
    
    condition_summary = analyzer.get_condition_summary()
    print(f"조건별 참가자 수: {condition_summary}")
    
    motivation_scores = analyzer.get_motivation_scores()
    print(f"동기 점수: {motivation_scores}")
    
    # CSV 내보내기
    analyzer.export_to_csv("demo_results.csv")
    print("결과가 demo_results.csv 파일로 저장되었습니다.")
    
    return experiment_data

def create_sample_dataset(n_participants: int = 20) -> List[ExperimentData]:
    """샘플 데이터셋 생성"""
    print(f"📊 {n_participants}명의 샘플 데이터 생성 중...")
    
    manager = ExperimentManager()
    all_data = []
    
    for i in range(n_participants):
        # 가상 인구통계학적 정보
        demographic = {
            'gender': random.choice(['남성', '여성']),
            'age': random.randint(18, 65),
            'phone': f"010-{random.randint(1000, 9999)}-{random.randint(1000, 9999)}"
        }
        
        participant_id = manager.create_participant(demographic)
        
        # 추론 과제 응답 (8-12개 문항)
        n_questions = random.randint(8, 12)
        sample_questions = random.sample(ALL_INFERENCE_QUESTIONS, n_questions)
        
        for question in sample_questions:
            selected_option = random.randint(0, len(question.options) - 1)
            selected_reason = f"문법 규칙에 따라 선택지 {selected_option + 1}이 적절하다고 판단했습니다"
            response_time = random.uniform(3.0, 20.0)
            
            manager.process_inference_response(
                question.id, selected_option, selected_reason, response_time
            )
        
        # 설문 응답 (모든 26개 문항)
        for question in MOTIVATION_QUESTIONS:
            # 조건에 따른 응답 패턴 시뮬레이션
            condition = manager.current_participant['condition']
            if 'emotional' in condition.value:
                rating = random.choices(range(1, 8), weights=[1, 2, 3, 4, 5, 6, 7])[0]
            else:
                rating = random.choices(range(1, 8), weights=[2, 3, 4, 5, 4, 3, 2])[0]
            
            manager.process_survey_response(question.id, rating)
        
        # 실험 완료
        experiment_data = manager.complete_experiment()
        all_data.append(experiment_data)
        
        if (i + 1) % 5 == 0:
            print(f"  {i + 1}/{n_participants} 완료")
    
    print("✅ 샘플 데이터 생성 완료!")
    return all_data

if __name__ == "__main__":
    print("🚀 AI 피드백 실험 시스템 시작")
    print("=" * 60)
    
    # 시스템 정보 출력
    print(f"📋 추론 과제 문항 수: {len(ALL_INFERENCE_QUESTIONS)}개")
    print(f"   - 명사구 문항: {len(NOUN_QUESTIONS)}개")
    print(f"   - 동사 문항: {len(VERB_QUESTIONS)}개")
    print(f"📊 학습 동기 설문 문항 수: {len(MOTIVATION_QUESTIONS)}개")
    print(f"🎯 피드백 조건 수: {len(PraiseCondition)}개")
    print()
    
    # 메뉴 선택
    while True:
        print("메뉴를 선택하세요:")
        print("1. 실험 시스템 데모 실행")
        print("2. 샘플 데이터셋 생성 및 분석")
        print("3. 문항 정보 확인")
        print("4. 피드백 시스템 테스트")
        print("5. 종료")
        
        choice = input("\n선택 (1-5): ").strip()
        
        if choice == "1":
            print("\n" + "="*50)
            run_experiment_demo()
            
        elif choice == "2":
            n = input("생성할 참가자 수 (기본값: 20): ").strip()
            n = int(n) if n.isdigit() else 20
            
            print("\n" + "="*50)
            sample_data = create_sample_dataset(n)
            
            # 고급 분석
            advanced_analyzer = AdvancedAnalyzer(sample_data)
            report = advanced_analyzer.generate_report()
            print("\n" + report)
            
            # CSV 저장
            analyzer = DataAnalyzer(sample_data)
            analyzer.export_to_csv(f"sample_data_{n}participants.csv")
            print(f"📁 결과가 sample_data_{n}participants.csv 파일로 저장되었습니다.")
            
        elif choice == "3":
            print("\n" + "="*50)
            print("📝 추론 과제 문항 정보:")
            print(f"총 {len(ALL_INFERENCE_QUESTIONS)}개 문항")
            
            print(f"\n명사구 문항 ({len(NOUN_QUESTIONS)}개):")
            for q in NOUN_QUESTIONS[:3]:  # 처음 3개만 표시
                print(f"  {q.id}: {q.gloss[:50]}...")
            print(f"  ... 외 {len(NOUN_QUESTIONS)-3}개")
            
            print(f"\n동사 문항 ({len(VERB_QUESTIONS)}개):")
            for q in VERB_QUESTIONS[:3]:  # 처음 3개만 표시
                print(f"  {q.id}: {q.gloss[:50]}...")
            print(f"  ... 외 {len(VERB_QUESTIONS)-3}개")
            
            print(f"\n📊 학습 동기 설문 문항 ({len(MOTIVATION_QUESTIONS)}개):")
            categories = {}
            for q in MOTIVATION_QUESTIONS:
                if q.category not in categories:
                    categories[q.category] = 0
                categories[q.category] += 1
            
            for category, count in categories.items():
                print(f"  {category}: {count}개 문항")
                
        elif choice == "4":
            print("\n" + "="*50)
            print("🤖 AI 피드백 시스템 테스트:")
            
            feedback_system = AIFeedbackSystem()
            test_reason = "문법 규칙에 따라 이 선택지가 가장 적절하다고 생각합니다"
            
            for condition in PraiseCondition:
                print(f"\n조건: {condition.value}")
                feedback = feedback_system.generate_feedback(condition, test_reason)
                print(f"피드백: {feedback}")
                
        elif choice == "5":
            print("\n👋 실험 시스템을 종료합니다.")
            break
            
        else:
            print("❌ 잘못된 선택입니다. 1-5 중에서 선택해주세요.")
        
        print("\n" + "-"*50)

    print("\n🎉 AI 피드백 실험 시스템 - 완전판")
    print("모든 기능이 정상적으로 작동합니다!")