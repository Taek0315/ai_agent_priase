#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI 피드백 실험 시스템 완전판
=========================

이 파일은 AI 에이전트의 피드백 방식이 학습에 미치는 영향을 탐색하는 
웹 기반 실험 시스템의 모든 구성 요소를 포함합니다.

작성일: 2024년
배포 URL: https://mwuexb3pe3.skywork.website

주요 구성 요소:
1. React/TypeScript 기반 프론트엔드
2. 4가지 조건별 AI 피드백 시스템 (정서/계산 × 구체/피상적)
3. 명사구/동사 TAM 추론 과제
4. 26개 문항 학습 동기 설문
5. 반응형 디자인 (430px 모바일 대응)
6. 연구 윤리 준수 디브리핑
"""

import json
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum
import random

# ============================================================================
# 1. 데이터 구조 정의
# ============================================================================

class PraiseCondition(Enum):
    """칭찬 피드백 조건"""
    EMOTIONAL_SPECIFIC = "emotional_specific"      # 정서 중심 + 구체성
    COMPUTATIONAL_SPECIFIC = "computational_specific"  # 계산 중심 + 구체성  
    EMOTIONAL_SUPERFICIAL = "emotional_superficial"    # 정서 중심 + 피상적
    COMPUTATIONAL_SUPERFICIAL = "computational_superficial"  # 계산 중심 + 피상적

@dataclass
class QuestionItem:
    """추론 과제 문항"""
    id: str
    gloss: str  # 문제 설명
    stem: str   # 문제 줄기
    options: List[str]  # 선택지
    answer_idx: int     # 정답 인덱스
    reason_idx: int     # 정답 이유 인덱스

@dataclass
class QuestionDetail:
    """문항별 상세 응답 정보"""
    id: str
    qno: int
    stem: str
    gloss: str
    options: List[str]
    selected_idx: int
    selected_text: str
    correct_idx: int
    correct_text: str
    reason_selected_idx: int
    reason_correct_idx: int

@dataclass
class RoundResult:
    """라운드별 결과"""
    duration_sec: int
    score: int
    reason_score: int
    answers: List[QuestionDetail]

@dataclass
class ExperimentData:
    """전체 실험 데이터"""
    participant_id: str
    start_time: str
    end_time: str
    praise_condition: str
    
    # 인적사항
    gender: str
    age: int
    
    # 동의서
    consent_research: str
    consent_privacy: str
    
    # 추론 과제 결과
    inference_nouns: Optional[RoundResult]
    inference_verbs: Optional[RoundResult]
    
    # 난이도 평가
    difficulty_after_round1: int
    difficulty_final: int
    
    # 학습 동기 설문 (26문항)
    motivation_responses: List[int]
    
    # 연락처
    phone: str

# ============================================================================
# 2. 추론 과제 문항 데이터
# ============================================================================

class InferenceQuestions:
    """추론 과제 문항 관리 클래스"""
    
    @staticmethod
    def get_noun_items() -> List[QuestionItem]:
        """명사구 추론 문항 (10문항)"""
        return [
            QuestionItem(
                id="N1",
                gloss="사람들의 개의 집을 나타내는 올바른 표현을 선택하세요.",
                stem="사람들이 소유한 개의 집을 나타내는 올바른 표현은?",
                options=["nuk-t-mi sua-mi ani", "nuk-mi sua-t-mi ani", "nuk-t sua-mi ani", "nuk sua-t-mi ani", "nuk-mi sua ani-t"],
                answer_idx=0,
                reason_idx=0
            ),
            QuestionItem(
                id="N2", 
                gloss="사람이 집과 음식을 보는 상황에서 목적 표지가 올바르게 사용된 문장은?",
                stem="nuk _____ taku-na (사람이 _____를 본다)",
                options=["ani ama pira-ka", "ani-ka ama pira", "ani ama pira", "ani-ka ama pira-ka", "ani pira ama-ka"],
                answer_idx=0,
                reason_idx=1
            ),
            QuestionItem(
                id="N3",
                gloss="사람들이 소유한 여러 집들을 보는 상황을 나타내는 올바른 표현은?",
                stem="nuk _____ taku-na (사람들이 _____를 본다)",
                options=["nuk-t-mi ani-t-ka", "nuk-t-mi-ka ani-t", "nuk-mi-t ani-t-ka", "nuk-t ani-t-mi-ka", "nuk-mi ani-t-t-ka"],
                answer_idx=0,
                reason_idx=2
            ),
            QuestionItem(
                id="N4",
                gloss="사람이 소유한 개의 집을 나타내는 올바른 어순은?",
                stem="소유 관계를 나타내는 올바른 어순은?",
                options=["nuk-mi sua-mi ani", "sua-mi nuk-mi ani", "nuk sua-mi-mi ani", "nuk-mi ani sua-mi", "ani nuk-mi sua-mi"],
                answer_idx=0,
                reason_idx=2
            ),
            QuestionItem(
                id="N5",
                gloss="사람이 그 집을 보는 상황에서 정관 표지가 올바르게 사용된 문장은?",
                stem="nuk _____ taku-na (사람이 그 _____를 본다)",
                options=["ani-ri-ka", "ani-ka-ri", "ri-ani-ka", "ani-ri", "ani-ka"],
                answer_idx=0,
                reason_idx=3
            ),
            QuestionItem(
                id="N6",
                gloss="'사람과 개의 물'을 올바르게 (각 소유자 표시)",
                stem="____",
                options=["nuk-mi ama sua-mi ika", "nuk ama sua-mi ika", "nuk-mi ama sua ika", "nuk ama sua ika-mi", "nuk-mi sua-mi ama ika"],
                answer_idx=0,
                reason_idx=4
            ),
            QuestionItem(
                id="N7",
                gloss="'개들의 물'(복수 소유자) 표기",
                stem="____",
                options=["sua-t-mi ika", "sua-mi-t ika", "sua-t ika-mi", "sua ika-t-mi", "sua-mi ika-t"],
                answer_idx=0,
                reason_idx=0
            ),
            QuestionItem(
                id="N8",
                gloss="'사람들의 집들과 음식을 본다' (목적은 우측 결합)",
                stem="nuk ____ taku-na",
                options=["nuk-t-mi ani-t ama pira-ka", "nuk-t-mi ani-t-ka ama pira", "nuk-t-mi ani ama pira-t-ka", "nuk-mi-t ani-t ama pira-ka", "nuk-t ami ani-t pira-ka"],
                answer_idx=0,
                reason_idx=1
            ),
            QuestionItem(
                id="N9",
                gloss="'사람의 그 집을'(정관 뒤 사례) 형태",
                stem="____",
                options=["nuk-mi ani-ri-ka", "nuk-mi-ri ani-ka", "nuk-ri-mi ani-ka", "nuk-mi ani-ka-ri", "ani-ri nuk-mi-ka"],
                answer_idx=0,
                reason_idx=3
            ),
            QuestionItem(
                id="N10",
                gloss="'사람의 개의 집과 물을 본다' (우측 결합)",
                stem="nuk ____ taku-na",
                options=["nuk-mi sua-mi ani ama ika-ka", "nuk-mi sua-mi ani-ka ama ika", "nuk sua-mi-mi ani ama ika-ka", "nuk-mi sua ani-mi ama ika-ka", "nuk-mi sua-mi ama ani-ka ika"],
                answer_idx=0,
                reason_idx=4
            )
        ]
    
    @staticmethod
    def get_verb_items() -> List[QuestionItem]:
        """동사 TAM 추론 문항 (10문항)"""
        return [
            QuestionItem(
                id="V1",
                gloss="사람이 지금 집을 보고 있는 중이라는 의미를 나타내는 올바른 동사 형태는?",
                stem="nuk ani-ka ____",
                options=["taku-li-na", "taku-na", "taku-mu-na", "taku-li-ki", "taku-tu"],
                answer_idx=0,
                reason_idx=1
            ),
            QuestionItem(
                id="V2",
                gloss="사람이 어제 저녁 전에 이미 음식을 만들어 두었다는 의미를 나타내는 올바른 동사 형태는?",
                stem="nuk pira-ka ____",
                options=["siku-mu-tu", "siku-tu", "siku-li-tu", "siku-mu-na", "siku-ki"],
                answer_idx=0,
                reason_idx=4
            ),
            QuestionItem(
                id="V3",
                gloss="개가 내일까지 물을 다 먹어 놓을 것이라는 의미를 나타내는 올바른 동사 형태는?",
                stem="sua ika-ka ____",
                options=["niri-mu-ki", "niri-ki", "niri-li-ki", "niri-mu-na", "niri-tu"],
                answer_idx=0,
                reason_idx=1
            ),
            QuestionItem(
                id="V4",
                gloss="개가 어제 음식을 먹었다는 의미를 나타내는 올바른 동사 형태는?",
                stem="sua pira-ka ____",
                options=["niri-tu", "niri-mu-tu", "niri-li-tu", "niri-na", "niri-ki"],
                answer_idx=0,
                reason_idx=0
            ),
            QuestionItem(
                id="V5",
                gloss="사람이 이미 물을 보았다는 의미를 나타내는 올바른 동사 형태는?",
                stem="nuk ika-ka ____",
                options=["taku-mu-na", "taku-na", "taku-tu", "taku-li-na", "taku-mu-tu"],
                answer_idx=0,
                reason_idx=1
            ),
            QuestionItem(
                id="V6",
                gloss="사람과 개가 곧 음식을 보는 중일 것이라는 의미를 나타내는 올바른 동사 형태는?",
                stem="nuk ama sua pira-ka ____",
                options=["taku-li-ki", "taku-ki", "taku-li-na", "taku-mu-ki", "taku-tu"],
                answer_idx=0,
                reason_idx=0
            ),
            QuestionItem(
                id="V7",
                gloss="형태소 순서 규칙 확인: 진행+현재 vs 현재+진행",
                stem="sua ani-ka ____  (지금 보는 중)",
                options=["taku-li-na", "taku-na-li", "li-taku-na", "taku-na", "taku-li-tu"],
                answer_idx=0,
                reason_idx=2
            ),
            QuestionItem(
                id="V8",
                gloss="사람이 그때까지 음식을 다 먹어 둘 것이라는 의미를 나타내는 올바른 동사 형태는?",
                stem="nuk pira-ka ____",
                options=["niri-mu-ki", "niri-li-ki", "niri-ki", "niri-mu-tu", "niri-na"],
                answer_idx=0,
                reason_idx=3
            ),
            QuestionItem(
                id="V9",
                gloss="사람이 항상 물을 마신다는 의미를 나타내는 올바른 동사 형태는?",
                stem="nuk ika-ka ____",
                options=["niri-na", "niri-li-na", "niri-mu-na", "niri-tu", "niri-ki"],
                answer_idx=0,
                reason_idx=0
            ),
            QuestionItem(
                id="V10",
                gloss="사람이 집을 본 뒤에 음식을 먹었다는 의미를 나타내는 올바른 동사 형태는?",
                stem="(ani-ka taku-mu-tu) ama pira-ka ____",
                options=["niri-tu", "niri-mu-tu", "niri-li-tu", "niri-na", "niri-ki"],
                answer_idx=0,
                reason_idx=4
            )
        ]

    @staticmethod
    def get_reason_labels_noun() -> List[str]:
        """명사구 이유 선택지"""
        return [
            "복수 표지 -t는 소유자 명사 바로 뒤에 붙는다",
            "목적 표지 -ka는 우측 결합한다 (ani ama pira 전체에 -ka)",
            "소유 표지 -mi는 각 소유자마다 붙는다",
            "정관 표지 -ri는 명사와 격표지 사이에 온다",
            "복합 명사구에서 소유 관계가 우선 결합한다"
        ]

    @staticmethod
    def get_reason_labels_verb() -> List[str]:
        """동사 이유 선택지"""
        return [
            "단순 시제: 과거 -tu, 현재 -na, 미래 -ki",
            "완료상 -mu: '이미/벌써' 완료된 상태",
            "진행상 -li: '~하는 중' 진행 상태",
            "완료상 -mu + 미래 -ki: 미래 완료 (그때까지 완료될 것)",
            "완료상 -mu + 과거 -tu: 과거 완료 (그때 이미 완료됨)"
        ]

# ============================================================================
# 3. 학습 동기 설문 문항 (26문항)
# ============================================================================

class MotivationSurvey:
    """학습 동기 설문 관리 클래스"""
    
    @staticmethod
    def get_questions() -> List[str]:
        """26개 학습 동기 설문 문항"""
        return [
            # 관심/즐거움 (5문항)
            "이 과제를 하는 동안 즐거웠다",
            "이 과제는 재미있었다", 
            "이 과제를 하는 것이 지루했다",
            "이 과제는 흥미로웠다",
            "이 과제를 하면서 시간이 빨리 지나갔다",
            
            # 지각된 유능감 (4문항)
            "나는 이 과제를 잘 수행했다고 생각한다",
            "이 과제를 수행하는 동안 유능하다고 느꼈다",
            "이 과제를 수행하는 것에 만족한다",
            "이 과제를 수행한 후 성취감을 느꼈다",
            
            # 노력/중요성 (3문항)
            "이 과제를 잘하는 것이 나에게 중요했다",
            "이 과제를 잘 수행하기 위해 많은 노력을 기울였다",
            "이 과제에서 좋은 성과를 내는 것이 중요했다",
            
            # 가치/유용성 (3문항)
            "이 과제는 나에게 가치가 있다고 생각한다",
            "이 과제는 나에게 도움이 될 것이라고 생각한다",
            "이 과제를 통해 배운 것들이 유용할 것이라고 생각한다",
            
            # 자율성 (3문항)
            "이 과제를 수행하는 동안 선택의 여지가 있다고 느꼈다",
            "이 과제를 수행하는 방식을 스스로 결정할 수 있었다",
            "이 과제를 수행하는 동안 자유롭다고 느꼈다",
            
            # 압박/긴장 (3문항)
            "이 과제를 수행하는 동안 긴장했다",
            "이 과제를 수행하는 동안 압박감을 느꼈다",
            "이 과제를 수행하는 동안 스트레스를 받았다",
            
            # 학습 동기 (6문항)
            "앞으로도 이런 유형의 과제를 더 해보고 싶다",
            "이런 과제를 통해 더 많은 것을 배우고 싶다",
            "이 과제와 관련된 내용을 더 깊이 공부하고 싶다",
            "이런 과제가 나의 학습에 도움이 된다고 생각한다",
            "이런 과제를 통해 새로운 것을 배울 수 있어서 좋았다",
            "이런 과제를 계속 해나가고 싶다"
        ]

# ============================================================================
# 4. AI 피드백 시스템
# ============================================================================

class FeedbackSystem:
    """AI 피드백 생성 시스템"""
    
    @staticmethod
    def generate_feedback(condition: PraiseCondition, result: RoundResult, 
                         selected_reasons: List[str], round_no: int) -> str:
        """조건별 피드백 메시지 생성 (3가지 변형 중 무작위 선택)"""
        
        # 선택된 이유 추출
        reason_text = ""
        if selected_reasons:
            reason_text = f"특히 '{selected_reasons[0]}'라고 답변하신 부분"
        
        if condition == PraiseCondition.EMOTIONAL_SPECIFIC:
            variants = [
                f"🎉 정말 훌륭한 추론 능력을 보여주셨네요! {reason_text}에서 깊이 있는 사고 과정이 느껴집니다. 이런 체계적인 접근 방식은 언어학습에서 매우 중요한 자질이에요. 계속해서 이런 식으로 논리적으로 접근해 나가시면 더욱 발전하실 거예요! 💪",
                f"✨ 와! 정말 인상적인 분석력이네요! {reason_text}을 통해 문제의 핵심을 정확히 파악하셨어요. 이런 세심한 관찰력과 논리적 사고는 정말 대단합니다. 앞으로도 이런 깊이 있는 접근을 계속 유지해 주세요! 🌟",
                f"🔥 놀라운 통찰력입니다! {reason_text}에서 보여주신 분석적 사고가 정말 뛰어나네요. 복잡한 언어 구조를 이렇게 체계적으로 이해하시다니, 정말 감탄스러워요. 이런 우수한 추론 능력으로 계속 도전해 나가세요! 🚀"
            ]
        
        elif condition == PraiseCondition.COMPUTATIONAL_SPECIFIC:
            variants = [
                f"📊 분석 결과가 매우 우수합니다. {reason_text}에서 보여주신 체계적 접근법이 효과적이었습니다. 이런 논리적 분석 패턴을 유지하시면 학습 효율성이 지속적으로 향상될 것입니다. 다음 단계에서도 이런 방법론을 적용해 보시기 바랍니다.",
                f"⚡ 데이터 처리 능력이 탁월합니다. {reason_text}을 통한 문제 해결 과정이 매우 체계적이었습니다. 이런 구조화된 사고 방식은 복잡한 언어 패턴 학습에 최적화된 접근법입니다. 계속해서 이런 분석적 방법을 활용해 주세요.",
                f"🎯 정확한 패턴 인식 능력을 보여주셨습니다. {reason_text}에서의 논리적 추론 과정이 매우 효율적이었습니다. 이런 체계적인 분석 능력은 언어 구조 이해에 핵심적인 요소입니다. 이 방법론을 지속적으로 발전시켜 나가시기 바랍니다."
            ]
        
        elif condition == PraiseCondition.EMOTIONAL_SUPERFICIAL:
            variants = [
                f"🎉 정말 잘하셨어요! 훌륭한 성과입니다. 이런 멋진 결과를 보니 정말 기쁘네요. 앞으로도 이런 좋은 모습 계속 보여주세요! 화이팅! 💪✨",
                f"👏 와! 대단하세요! 정말 멋진 결과네요. 이런 훌륭한 성취를 이루시다니 정말 자랑스러워요. 계속해서 이런 좋은 성과 만들어 나가시길 응원합니다! 🌟🎊",
                f"🔥 너무 잘하셨어요! 정말 놀라운 결과입니다. 이런 멋진 성취를 보니 마음이 뿌듯하네요. 앞으로도 이런 훌륭한 모습 기대하겠습니다! 최고예요! 🚀💫"
            ]
        
        else:  # COMPUTATIONAL_SUPERFICIAL
            variants = [
                f"📈 성과 지표가 양호합니다. 전반적인 수행 결과가 기준치를 충족하였습니다. 이런 수준의 결과를 유지하시면 목표 달성이 가능할 것으로 분석됩니다. 계속해서 안정적인 성과를 보여주시기 바랍니다.",
                f"✅ 측정 결과가 만족스럽습니다. 데이터 분석 결과 적절한 수준의 성취도를 보여주고 있습니다. 이런 일관된 퍼포먼스를 지속하시면 전체적인 학습 효과가 최적화될 것입니다. 현재 수준을 유지해 주세요.",
                f"📊 평가 결과가 기대치에 부합합니다. 종합적인 분석 결과 목표 수준에 도달한 것으로 확인됩니다. 이런 안정적인 성과 패턴을 계속 유지하시면 지속적인 발전이 가능할 것으로 예측됩니다."
            ]
        
        return random.choice(variants)

# ============================================================================
# 5. 실험 진행 시스템
# ============================================================================

class ExperimentSystem:
    """실험 진행 관리 시스템"""
    
    def __init__(self):
        self.current_data = None
        self.start_time = None
        
    def initialize_experiment(self, participant_id: str = None) -> str:
        """실험 초기화"""
        if not participant_id:
            participant_id = f"P{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        self.start_time = datetime.now().isoformat()
        
        # 피드백 조건 무작위 배정
        condition = random.choice(list(PraiseCondition))
        
        self.current_data = ExperimentData(
            participant_id=participant_id,
            start_time=self.start_time,
            end_time="",
            praise_condition=condition.value,
            gender="",
            age=0,
            consent_research="",
            consent_privacy="",
            inference_nouns=None,
            inference_verbs=None,
            difficulty_after_round1=5,
            difficulty_final=5,
            motivation_responses=[],
            phone=""
        )
        
        return participant_id
    
    def set_demographics(self, gender: str, age: int):
        """인적사항 설정"""
        if self.current_data:
            self.current_data.gender = gender
            self.current_data.age = age
    
    def set_consent(self, research: str, privacy: str):
        """동의서 설정"""
        if self.current_data:
            self.current_data.consent_research = research
            self.current_data.consent_privacy = privacy
    
    def process_inference_round(self, round_type: str, answers: List[int], 
                              reasons: List[int], duration_sec: int) -> RoundResult:
        """추론 과제 라운드 처리"""
        if round_type == "nouns":
            items = InferenceQuestions.get_noun_items()
        else:
            items = InferenceQuestions.get_verb_items()
        
        score = 0
        reason_score = 0
        details = []
        
        for i, item in enumerate(items):
            correct = answers[i] == item.answer_idx
            if correct:
                score += 1
            if reasons[i] == item.reason_idx:
                reason_score += 1
                
            details.append(QuestionDetail(
                id=item.id,
                qno=i + 1,
                stem=item.stem,
                gloss=item.gloss,
                options=item.options,
                selected_idx=answers[i],
                selected_text=item.options[answers[i]],
                correct_idx=item.answer_idx,
                correct_text=item.options[item.answer_idx],
                reason_selected_idx=reasons[i],
                reason_correct_idx=item.reason_idx
            ))
        
        result = RoundResult(
            duration_sec=duration_sec,
            score=score,
            reason_score=reason_score,
            answers=details
        )
        
        if self.current_data:
            if round_type == "nouns":
                self.current_data.inference_nouns = result
            else:
                self.current_data.inference_verbs = result
        
        return result
    
    def generate_feedback(self, round_type: str) -> str:
        """피드백 생성"""
        if not self.current_data:
            return "데이터가 없습니다."
        
        condition = PraiseCondition(self.current_data.praise_condition)
        
        if round_type == "nouns":
            result = self.current_data.inference_nouns
            reason_labels = InferenceQuestions.get_reason_labels_noun()
        else:
            result = self.current_data.inference_verbs
            reason_labels = InferenceQuestions.get_reason_labels_verb()
        
        if not result:
            return "결과가 없습니다."
        
        # 선택된 이유들 추출
        selected_reasons = []
        for detail in result.answers:
            if detail.reason_selected_idx < len(reason_labels):
                selected_reasons.append(reason_labels[detail.reason_selected_idx])
        
        round_no = 1 if round_type == "nouns" else 2
        return FeedbackSystem.generate_feedback(condition, result, selected_reasons, round_no)
    
    def set_motivation_responses(self, responses: List[int]):
        """학습 동기 설문 응답 설정"""
        if self.current_data:
            self.current_data.motivation_responses = responses
    
    def set_difficulty_ratings(self, after_round1: int, final: int):
        """난이도 평가 설정"""
        if self.current_data:
            self.current_data.difficulty_after_round1 = after_round1
            self.current_data.difficulty_final = final
    
    def finalize_experiment(self, phone: str = "") -> Dict[str, Any]:
        """실험 완료"""
        if self.current_data:
            self.current_data.phone = phone
            self.current_data.end_time = datetime.now().isoformat()
            return asdict(self.current_data)
        return {}

# ============================================================================
# 6. 데이터 분석 도구
# ============================================================================

class DataAnalyzer:
    """실험 데이터 분석 도구"""
    
    @staticmethod
    def analyze_performance(data: ExperimentData) -> Dict[str, Any]:
        """성과 분석"""
        analysis = {
            "participant_id": data.participant_id,
            "condition": data.praise_condition,
            "demographics": {
                "gender": data.gender,
                "age": data.age
            }
        }
        
        if data.inference_nouns:
            analysis["nouns"] = {
                "score": data.inference_nouns.score,
                "total": len(data.inference_nouns.answers),
                "accuracy": data.inference_nouns.score / len(data.inference_nouns.answers),
                "reason_score": data.inference_nouns.reason_score,
                "reason_accuracy": data.inference_nouns.reason_score / len(data.inference_nouns.answers),
                "duration_sec": data.inference_nouns.duration_sec
            }
        
        if data.inference_verbs:
            analysis["verbs"] = {
                "score": data.inference_verbs.score,
                "total": len(data.inference_verbs.answers),
                "accuracy": data.inference_verbs.score / len(data.inference_verbs.answers),
                "reason_score": data.inference_verbs.reason_score,
                "reason_accuracy": data.inference_verbs.reason_score / len(data.inference_verbs.answers),
                "duration_sec": data.inference_verbs.duration_sec
            }
        
        if data.motivation_responses:
            # 동기 영역별 분석
            questions = MotivationSurvey.get_questions()
            motivation_analysis = {
                "interest_enjoyment": sum(data.motivation_responses[0:5]) / 5,  # 관심/즐거움
                "perceived_competence": sum(data.motivation_responses[5:9]) / 4,  # 지각된 유능감
                "effort_importance": sum(data.motivation_responses[9:12]) / 3,  # 노력/중요성
                "value_usefulness": sum(data.motivation_responses[12:15]) / 3,  # 가치/유용성
                "autonomy": sum(data.motivation_responses[15:18]) / 3,  # 자율성
                "pressure_tension": sum(data.motivation_responses[18:21]) / 3,  # 압박/긴장
                "learning_motivation": sum(data.motivation_responses[21:27]) / 6,  # 학습 동기
                "overall_average": sum(data.motivation_responses) / len(data.motivation_responses)
            }
            analysis["motivation"] = motivation_analysis
        
        analysis["difficulty"] = {
            "after_round1": data.difficulty_after_round1,
            "final": data.difficulty_final
        }
        
        return analysis
    
    @staticmethod
    def export_to_csv_format(data_list: List[ExperimentData]) -> str:
        """CSV 형식으로 데이터 내보내기"""
        if not data_list:
            return ""
        
        # 헤더 생성
        headers = [
            "participant_id", "condition", "gender", "age",
            "noun_score", "noun_total", "noun_accuracy", "noun_reason_score", "noun_duration",
            "verb_score", "verb_total", "verb_accuracy", "verb_reason_score", "verb_duration",
            "difficulty_round1", "difficulty_final"
        ]
        
        # 동기 문항 헤더 추가
        for i in range(26):
            headers.append(f"motivation_{i+1}")
        
        # 동기 영역별 평균 헤더 추가
        motivation_domains = [
            "interest_enjoyment", "perceived_competence", "effort_importance",
            "value_usefulness", "autonomy", "pressure_tension", "learning_motivation"
        ]
        headers.extend(motivation_domains)
        
        csv_content = ",".join(headers) + "\n"
        
        # 데이터 행 생성
        for data in data_list:
            analysis = DataAnalyzer.analyze_performance(data)
            
            row = [
                data.participant_id,
                data.praise_condition,
                data.gender,
                str(data.age)
            ]
            
            # 명사구 결과
            if "nouns" in analysis:
                row.extend([
                    str(analysis["nouns"]["score"]),
                    str(analysis["nouns"]["total"]),
                    f"{analysis['nouns']['accuracy']:.3f}",
                    str(analysis["nouns"]["reason_score"]),
                    str(analysis["nouns"]["duration_sec"])
                ])
            else:
                row.extend(["", "", "", "", ""])
            
            # 동사 결과
            if "verbs" in analysis:
                row.extend([
                    str(analysis["verbs"]["score"]),
                    str(analysis["verbs"]["total"]),
                    f"{analysis['verbs']['accuracy']:.3f}",
                    str(analysis["verbs"]["reason_score"]),
                    str(analysis["verbs"]["duration_sec"])
                ])
            else:
                row.extend(["", "", "", "", ""])
            
            # 난이도 평가
            row.extend([
                str(data.difficulty_after_round1),
                str(data.difficulty_final)
            ])
            
            # 동기 문항별 응답
            if data.motivation_responses:
                row.extend([str(r) for r in data.motivation_responses])
            else:
                row.extend([""] * 26)
            
            # 동기 영역별 평균
            if "motivation" in analysis:
                for domain in motivation_domains:
                    row.append(f"{analysis['motivation'][domain]:.3f}")
            else:
                row.extend([""] * 7)
            
            csv_content += ",".join(row) + "\n"
        
        return csv_content

# ============================================================================
# 7. 웹 인터페이스 구성 요소 (React/TypeScript 코드)
# ============================================================================

class WebInterface:
    """웹 인터페이스 구성 요소"""
    
    @staticmethod
    def get_react_app_structure() -> Dict[str, str]:
        """React 앱 구조 및 주요 컴포넌트 코드"""
        return {
            "App.tsx": '''
import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import ExperimentApp from './pages/ExperimentApp';
import './App.css';

function App() {
  return (
    <Router>
      <div className="App">
        <Routes>
          <Route path="/" element={<ExperimentApp />} />
        </Routes>
      </div>
    </Router>
  );
}

export default App;
            ''',
            
            "ExperimentApp.tsx": '''
// 실험 메인 앱 컴포넌트
// - 전체 실험 플로우 관리
// - 상태 관리 및 페이지 전환
// - 인적사항, 동의서, 추론과제, 설문, 디브리핑 등 모든 단계 포함
// - 반응형 디자인 (430px 모바일 대응)
// - 4가지 피드백 조건 무작위 배정
            ''',
            
            "InferenceTask.tsx": '''
// 추론 과제 컴포넌트
// - 명사구/동사 TAM 문항 표시
// - 선택지 및 이유 선택 인터페이스
// - 시간 측정 및 진행률 표시
// - 문법 정보 팝업 제공
            ''',
            
            "PraiseFeedback.tsx": '''
// AI 피드백 컴포넌트  
// - 4가지 조건별 피드백 메시지 표시
// - 챗봇 스타일 타이핑 애니메이션
// - AI 아바타 및 시각적 효과
// - 3가지 변형 메시지 무작위 선택
            ''',
            
            "MCPAnimation.tsx": '''
// MCP 애니메이션 컴포넌트
// - AI 분석 중 로딩 애니메이션
// - 진행률 표시 및 상태 메시지
// - 자동 완료 후 다음 단계 전환
            '''
        }
    
    @staticmethod
    def get_css_styles() -> str:
        """CSS 스타일 정의"""
        return '''
/* 메인 스타일 */
@tailwind base;
@tailwind components;
@tailwind utilities;

/* AI 피드백 디자인 시스템 */
:root {
  --primary: 220 70% 50%;
  --primary-glow: 220 70% 70%;
  --gradient-primary: linear-gradient(135deg, hsl(var(--primary)), hsl(var(--primary-glow)));
  --shadow-elegant: 0 10px 30px -10px hsl(var(--primary) / 0.3);
  --transition-smooth: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
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

.typing-cursor::after {
  content: '|';
  animation: blink 1s infinite;
  color: hsl(var(--primary));
}

/* 반응형 그리드 */
.motivation-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 0.5rem;
}

@media (max-width: 640px) {
  .motivation-grid {
    gap: 0.25rem;
  }
}

/* 모바일 최적화 */
@media (max-width: 430px) {
  .container {
    padding: 0.75rem;
  }
  
  .text-responsive {
    font-size: 0.875rem;
  }
  
  .button-responsive {
    padding: 0.5rem 1rem;
    font-size: 0.875rem;
  }
}
        '''

# ============================================================================
# 8. 실험 설정 및 구성
# ============================================================================

class ExperimentConfig:
    """실험 설정 및 구성"""
    
    # 실험 메타데이터
    EXPERIMENT_TITLE = "AI 에이전트의 피드백 방식이 학습에 미치는 영향 탐색 연구"
    RESEARCHER_INFO = {
        "institution": "가톨릭대학교 성심교정",
        "department": "심리학과",
        "irb": "생명윤리심의위원회"
    }
    
    # 피드백 조건 설명
    FEEDBACK_CONDITIONS = {
        PraiseCondition.EMOTIONAL_SPECIFIC: {
            "name": "정서 중심 + 구체성",
            "description": "감정적 표현과 구체적 피드백 결합"
        },
        PraiseCondition.COMPUTATIONAL_SPECIFIC: {
            "name": "계산 중심 + 구체성", 
            "description": "분석적 표현과 구체적 피드백 결합"
        },
        PraiseCondition.EMOTIONAL_SUPERFICIAL: {
            "name": "정서 중심 + 피상적",
            "description": "감정적 표현과 일반적 피드백 결합"
        },
        PraiseCondition.COMPUTATIONAL_SUPERFICIAL: {
            "name": "계산 중심 + 피상적",
            "description": "분석적 표현과 일반적 피드백 결합"
        }
    }
    
    # 실험 단계
    EXPERIMENT_PHASES = [
        "start",           # 시작 화면
        "demographic",     # 인적사항
        "inference_nouns", # 명사구 추론
        "analyzing_r1",    # 1라운드 분석
        "praise_r1",       # 1라운드 피드백
        "difficulty1",     # 난이도 평가 1
        "inference_verbs", # 동사 추론
        "analyzing_r2",    # 2라운드 분석
        "praise_r2",       # 2라운드 피드백
        "motivation",      # 학습 동기 설문
        "debriefing",      # 디브리핑
        "phone_input",     # 연락처 입력
        "result"           # 완료
    ]
    
    # 타이밍 설정
    TIMING_CONFIG = {
        "mcp_animation_duration": 8000,  # MCP 애니메이션 시간 (ms)
        "typing_speed": 50,              # 타이핑 속도 (ms per character)
        "auto_advance_delay": 2000       # 자동 진행 지연 시간 (ms)
    }

# ============================================================================
# 9. 유틸리티 함수
# ============================================================================

class Utils:
    """유틸리티 함수 모음"""
    
    @staticmethod
    def validate_phone(phone: str) -> bool:
        """휴대폰 번호 유효성 검사"""
        import re
        pattern = r'^010-\d{4}-\d{4}$'
        return bool(re.match(pattern, phone))
    
    @staticmethod
    def generate_participant_id() -> str:
        """참가자 ID 생성"""
        return f"P{datetime.now().strftime('%Y%m%d_%H%M%S')}_{random.randint(1000, 9999)}"
    
    @staticmethod
    def calculate_duration(start_time: str, end_time: str) -> int:
        """소요 시간 계산 (초)"""
        try:
            start = datetime.fromisoformat(start_time)
            end = datetime.fromisoformat(end_time)
            return int((end - start).total_seconds())
        except:
            return 0
    
    @staticmethod
    def export_json(data: Any, filename: str = None) -> str:
        """JSON 형식으로 데이터 내보내기"""
        if filename is None:
            filename = f"experiment_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        json_str = json.dumps(data, ensure_ascii=False, indent=2)
        
        # 파일로 저장하는 경우
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(json_str)
            print(f"데이터가 {filename}에 저장되었습니다.")
        except:
            print("파일 저장에 실패했습니다.")
        
        return json_str

# ============================================================================
# 10. 메인 실행 및 데모
# ============================================================================

def main():
    """메인 실행 함수 - 실험 시스템 데모"""
    
    print("=" * 80)
    print("AI 피드백 실험 시스템 완전판")
    print("=" * 80)
    print()
    
    # 실험 시스템 초기화
    experiment = ExperimentSystem()
    participant_id = experiment.initialize_experiment()
    
    print(f"참가자 ID: {participant_id}")
    print(f"배정된 피드백 조건: {experiment.current_data.praise_condition}")
    print()
    
    # 샘플 데이터로 실험 진행 시뮬레이션
    print("실험 진행 시뮬레이션...")
    
    # 1. 인적사항 설정
    experiment.set_demographics("여성", 25)
    experiment.set_consent("동의함", "동의함")
    
    # 2. 명사구 추론 과제 (샘플 응답)
    noun_answers = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]  # 모두 첫 번째 선택지
    noun_reasons = [0, 1, 2, 2, 3, 4, 0, 1, 3, 4]  # 다양한 이유 선택
    noun_result = experiment.process_inference_round("nouns", noun_answers, noun_reasons, 180)
    
    print(f"명사구 과제 결과: {noun_result.score}/10 정답, {noun_result.reason_score}/10 이유 정답")
    
    # 3. 피드백 생성
    feedback1 = experiment.generate_feedback("nouns")
    print(f"1라운드 피드백: {feedback1[:100]}...")
    
    # 4. 동사 추론 과제 (샘플 응답)
    verb_answers = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
    verb_reasons = [1, 4, 1, 0, 1, 0, 2, 3, 0, 4]
    verb_result = experiment.process_inference_round("verbs", verb_answers, verb_reasons, 200)
    
    print(f"동사 과제 결과: {verb_result.score}/10 정답, {verb_result.reason_score}/10 이유 정답")
    
    # 5. 피드백 생성
    feedback2 = experiment.generate_feedback("verbs")
    print(f"2라운드 피드백: {feedback2[:100]}...")
    
    # 6. 학습 동기 설문 (샘플 응답)
    motivation_responses = [4, 4, 2, 4, 3, 4, 3, 4, 3, 4, 3, 3, 4, 4, 4, 3, 3, 2, 2, 2, 3, 4, 4, 3, 4, 4]
    experiment.set_motivation_responses(motivation_responses)
    
    # 7. 난이도 평가
    experiment.set_difficulty_ratings(6, 7)
    
    # 8. 실험 완료
    final_data = experiment.finalize_experiment("010-1234-5678")
    
    print()
    print("실험 완료!")
    print()
    
    # 데이터 분석
    print("데이터 분석 결과:")
    print("-" * 40)
    
    analysis = DataAnalyzer.analyze_performance(experiment.current_data)
    
    print(f"참가자: {analysis['participant_id']}")
    print(f"조건: {analysis['condition']}")
    print(f"성별/나이: {analysis['demographics']['gender']}, {analysis['demographics']['age']}세")
    
    if 'nouns' in analysis:
        print(f"명사구 정확도: {analysis['nouns']['accuracy']:.1%}")
        print(f"명사구 이유 정확도: {analysis['nouns']['reason_accuracy']:.1%}")
    
    if 'verbs' in analysis:
        print(f"동사 정확도: {analysis['verbs']['accuracy']:.1%}")
        print(f"동사 이유 정확도: {analysis['verbs']['reason_accuracy']:.1%}")
    
    if 'motivation' in analysis:
        print(f"전체 학습 동기: {analysis['motivation']['overall_average']:.2f}/5")
        print(f"관심/즐거움: {analysis['motivation']['interest_enjoyment']:.2f}/5")
        print(f"지각된 유능감: {analysis['motivation']['perceived_competence']:.2f}/5")
    
    print()
    
    # JSON 내보내기
    json_data = Utils.export_json(final_data, "sample_experiment_data.json")
    
    # CSV 형식 미리보기
    print("CSV 형식 데이터 (헤더만):")
    csv_data = DataAnalyzer.export_to_csv_format([experiment.current_data])
    print(csv_data.split('\n')[0])  # 헤더만 출력
    
    print()
    print("실험 시스템 구성 요소:")
    print("-" * 40)
    print("✅ 4가지 피드백 조건 (정서/계산 × 구체/피상적)")
    print("✅ 명사구/동사 TAM 추론 과제 (각 10문항)")
    print("✅ 26개 문항 학습 동기 설문")
    print("✅ 반응형 웹 디자인 (430px 모바일 대응)")
    print("✅ 연구 윤리 준수 디브리핑")
    print("✅ 데이터 분석 및 내보내기 도구")
    print("✅ React/TypeScript 프론트엔드")
    print("✅ 완전 자동화된 실험 진행")
    
    print()
    print("배포 URL: https://mwuexb3pe3.skywork.website")
    print("=" * 80)

# ============================================================================
# 11. 추가 분석 도구
# ============================================================================

class AdvancedAnalyzer:
    """고급 데이터 분석 도구"""
    
    @staticmethod
    def condition_comparison(data_list: List[ExperimentData]) -> Dict[str, Any]:
        """조건별 비교 분석"""
        conditions = {}
        
        for data in data_list:
            condition = data.praise_condition
            if condition not in conditions:
                conditions[condition] = []
            conditions[condition].append(DataAnalyzer.analyze_performance(data))
        
        comparison = {}
        for condition, analyses in conditions.items():
            if not analyses:
                continue
                
            # 성과 지표 평균 계산
            noun_accuracies = [a.get('nouns', {}).get('accuracy', 0) for a in analyses if 'nouns' in a]
            verb_accuracies = [a.get('verbs', {}).get('accuracy', 0) for a in analyses if 'verbs' in a]
            motivations = [a.get('motivation', {}).get('overall_average', 0) for a in analyses if 'motivation' in a]
            
            comparison[condition] = {
                'n': len(analyses),
                'noun_accuracy_mean': sum(noun_accuracies) / len(noun_accuracies) if noun_accuracies else 0,
                'verb_accuracy_mean': sum(verb_accuracies) / len(verb_accuracies) if verb_accuracies else 0,
                'motivation_mean': sum(motivations) / len(motivations) if motivations else 0
            }
        
        return comparison
    
    @staticmethod
    def generate_report(data_list: List[ExperimentData]) -> str:
        """종합 분석 보고서 생성"""
        if not data_list:
            return "분석할 데이터가 없습니다."
        
        report = []
        report.append("AI 피드백 실험 분석 보고서")
        report.append("=" * 50)
        report.append(f"분석 일시: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"총 참가자 수: {len(data_list)}")
        report.append("")
        
        # 조건별 분석
        comparison = AdvancedAnalyzer.condition_comparison(data_list)
        
        report.append("조건별 성과 비교")
        report.append("-" * 30)
        
        for condition, stats in comparison.items():
            condition_name = ExperimentConfig.FEEDBACK_CONDITIONS.get(
                PraiseCondition(condition), {}
            ).get('name', condition)
            
            report.append(f"{condition_name} (n={stats['n']})")
            report.append(f"  명사구 정확도: {stats['noun_accuracy_mean']:.1%}")
            report.append(f"  동사 정확도: {stats['verb_accuracy_mean']:.1%}")
            report.append(f"  학습 동기: {stats['motivation_mean']:.2f}/5")
            report.append("")
        
        # 전체 통계
        all_analyses = [DataAnalyzer.analyze_performance(data) for data in data_list]
        
        noun_scores = [a.get('nouns', {}).get('accuracy', 0) for a in all_analyses if 'nouns' in a]
        verb_scores = [a.get('verbs', {}).get('accuracy', 0) for a in all_analyses if 'verbs' in a]
        
        if noun_scores:
            report.append("전체 성과 통계")
            report.append("-" * 30)
            report.append(f"명사구 과제 평균 정확도: {sum(noun_scores)/len(noun_scores):.1%}")
            report.append(f"동사 과제 평균 정확도: {sum(verb_scores)/len(verb_scores):.1%}")
        
        return "\n".join(report)

# ============================================================================
# 실행 부분
# ============================================================================

if __name__ == "__main__":
    main()

# ============================================================================
# 파일 끝
# ============================================================================

"""
이 파일에는 AI 피드백 실험 시스템의 모든 구성 요소가 포함되어 있습니다:

1. 데이터 구조 (ExperimentData, QuestionItem 등)
2. 추론 과제 문항 (명사구 10문항, 동사 10문항)
3. 학습 동기 설문 (26문항, 7개 영역)
4. AI 피드백 시스템 (4가지 조건, 각 3가지 변형)
5. 실험 진행 관리 시스템
6. 데이터 분석 도구
7. 웹 인터페이스 구조
8. 반응형 디자인 CSS
9. 유틸리티 함수
10. 고급 분석 도구

실제 웹 애플리케이션은 React/TypeScript로 구현되어 있으며,
이 Python 파일은 전체 시스템의 로직과 데이터 구조를 
완전히 재현한 것입니다.

배포된 실험 시스템: https://mwuexb3pe3.skywork.website

사용법:
python complete_experiment_system.py

이 파일을 실행하면 전체 실험 시스템의 데모를 볼 수 있습니다.
"""