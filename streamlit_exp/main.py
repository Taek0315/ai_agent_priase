import streamlit as st
import time
import random
import json
import os
from datetime import datetime
from utils.validation import validate_phone, validate_text
from utils.save_data import save_to_csv

BASE_DIR = os.path.dirname(__file__)

st.set_page_config(page_title="AI 칭찬 연구 설문", layout="centered")

hide_streamlit_style = """
    <style>
    #MainMenu {visibility: hidden;} 
    footer {visibility: hidden;} 
    header {visibility: hidden;}
    </style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

if "phase" not in st.session_state:
    st.session_state.phase = "start"
    st.session_state.data = {}
    st.session_state.current_kw_index = 0
    st.session_state.writing_answers = []
    st.session_state.feedback_set_key = random.choice(["set1", "set2"])

# ==== COVNOX log lines (EN) ====
fake_logs = [
    "[INFO][COVNOX] Initializing… booting inference-pattern engine",
    "[INFO][COVNOX] Loading rule set: possessive(-mi), plural(-t), object(-ka), tense(-na/-tu), connector(ama)",
    "[INFO][COVNOX] Collecting responses… building 10-item choice hash",
    "[OK][COVNOX] Response hash map constructed",
    "[INFO][COVNOX] Running grammatical marker detection",
    "[OK][COVNOX] Marker usage log: -mi/-t/-ka/-na/-tu/ama",
    "[INFO][COVNOX] Parsing rationale tags (multi-select)",
    "[OK][COVNOX] Rationale normalization complete",
    "[INFO][COVNOX] Computing rule-match consistency",
    "[OK][COVNOX] Consistency matrix updated",
    "[INFO][COVNOX] Testing elimination-of-incorrect-options strategy",
    "[OK][COVNOX] Comparison/contrast pattern detected",
    "[INFO][COVNOX] Checking tense/object conflicts",
    "[OK][COVNOX] No critical conflicts · reasoning path stable",
    "[INFO][COVNOX] Analyzing response time (persistence index)",
    "[OK][COVNOX] Persistence index calculated",
    "[INFO][COVNOX] Scoring diversity of rule application",
    "[OK][COVNOX] Diversity score updated",
    "[INFO][COVNOX] Synthesizing overall inference profile (ability/effort emphasis)",
    "[OK][COVNOX] Profile composed · selecting feedback template",
    "[INFO][COVNOX] Natural language phrasing optimization",
    "[OK][COVNOX] Fluency/consistency checks passed",
    "[INFO][COVNOX] Preparing feedback delivery",
    "[✔][COVNOX] Analysis complete. Rendering results…"
]

# ==== Motion (duration unchanged) ====
def run_mcp_motion():
    import os

    # 1) 로고 경로 (우선순위대로 탐색)
    LOGO_PATHS = [
        "./covnox.png",                 # main.py와 같은 폴더
        os.path.join(os.getcwd(), "covnox.png")
    ]
    logo_path = next((p for p in LOGO_PATHS if os.path.exists(p)), None)

    # 2) 로고 + 타이틀
    with st.container():
        # 로고를 정확히 가운데에 배치
        left, mid, right = st.columns([1, 2, 1])
        with mid:
            if logo_path:
                st.image(logo_path, width=180)
        st.markdown("""
            <h1 style="text-align: center; margin-top: 8px;">
                🧩 COVNOX: Inference Pattern Analysis
            </h1>
        """, unsafe_allow_html=True)

    # 3) 프로그레스 + 로그 (동일)
    log_placeholder = st.empty()
    progress_bar = st.progress(0)

    start_time = time.time()
    elapsed = 0.0
    step = 0
    total_duration = 8  # seconds

    while elapsed < total_duration:
        progress = min(elapsed / total_duration, 1.0)
        progress_bar.progress(progress)

        log_message = fake_logs[step % len(fake_logs)]
        timestamp = time.strftime("%H:%M:%S")
        log_placeholder.text(f"[{timestamp}] {log_message}")

        step += 1
        time.sleep(0.4)
        elapsed = time.time() - start_time

    progress_bar.progress(1.0)

feedback_path = os.path.join(BASE_DIR, "data", "feedback_sets.json")
with open(feedback_path, encoding="utf-8") as f:
    feedback_sets = json.load(f)

# -------------------
# 1. 연구 동의 페이지 (2단계)
# -------------------
if st.session_state.phase == "start":
    # 로고
    logo_path = os.path.join(BASE_DIR, "logo.png")
    if os.path.exists(logo_path):
        st.image(logo_path, width=150)
    st.title("연구 참여 동의서")

    # 내부 스텝 상태 초기화
    if "consent_step" not in st.session_state:
        st.session_state.consent_step = "explain"   # "explain" → "agree"

    # 파일 경로
    EXPLAIN_IMG = os.path.join(BASE_DIR, "explane.png")   # 연구대상자 설명문
    AGREE_IMG   = os.path.join(BASE_DIR, "agree.png")     # 연구 동의서(온라인용)
    PRIV_IMG    = os.path.join(BASE_DIR, "privinfo.png")  # 개인정보 수집·이용 동의

    # -------------------
    # STEP 1: 설명문 페이지
    # -------------------
    if st.session_state.consent_step == "explain":
        st.subheader("연구대상자 설명문")
        if os.path.exists(EXPLAIN_IMG):
            st.image(EXPLAIN_IMG, use_container_width=True)
        else:
            st.info("설명문 이미지를 찾을 수 없습니다. 경로/파일명을 확인하세요.")

        st.markdown("<div style='height:12px;'></div>", unsafe_allow_html=True)
        # 다음 버튼 (단독)
        if st.button("다음", key="consent_to_agree_btn", use_container_width=True):
            st.session_state.consent_step = "agree"
            st.rerun()

    # -------------------
    # STEP 2: 동의서 + 개인정보 동의
    # -------------------
    elif st.session_state.consent_step == "agree":
        # 연구 동의서
        st.subheader("연구 동의서")
        if os.path.exists(AGREE_IMG):
            st.image(AGREE_IMG, use_container_width=True)
        else:
            st.info("연구 동의서 이미지를 찾을 수 없습니다. 경로/파일명을 확인하세요.")

        # 연구 동의 라디오 (이미지 바로 아래)
        consent_research = st.radio(
            label="연구 참여에 동의하십니까?",
            options=["동의함", "동의하지 않음"],
            horizontal=True,
            key="consent_research_radio"
        )

        st.markdown("<div style='height:18px;'></div>", unsafe_allow_html=True)

        # 개인정보 수집·이용 동의서
        st.subheader("개인정보 수집·이용에 대한 동의")
        if os.path.exists(PRIV_IMG):
            st.image(PRIV_IMG, use_container_width=True)
        else:
            st.info("개인정보 동의 이미지를 찾을 수 없습니다. 경로/파일명을 확인하세요.")

        # 개인정보 동의 라디오 (이미지 바로 아래)
        consent_privacy = st.radio(
            label="개인정보 수집·이용에 동의하십니까?",
            options=["동의함", "동의하지 않음"],
            horizontal=True,
            key="consent_privacy_radio"
        )

        st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
        st.divider()
        st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)

        # 하단 내비게이션: 좌/우 끝에 작게 배치 (기본 크기 버튼)
        left_col, spacer, right_col = st.columns([1, 8, 1])
        with left_col:
            if st.button("이전", key="consent_prev_btn"):
                st.session_state.consent_step = "explain"
                st.rerun()
        with right_col:
            if st.button("다음", key="consent_next_btn"):
                if consent_research != "동의함":
                    st.warning("연구 참여에 ‘동의함’을 선택해야 계속 진행할 수 있습니다.")
                elif consent_privacy != "동의함":
                    st.warning("개인정보 수집·이용에 ‘동의함’을 선택해야 계속 진행할 수 있습니다.")
                else:
                    # 저장
                    st.session_state.data.update({
                        "consent": "동의함",
                        "consent_research": consent_research,
                        "consent_privacy": consent_privacy,
                        "startTime": datetime.now().isoformat()
                    })
                    # 다음 전체 단계로 이동
                    st.session_state.phase = "demographic"
                    st.rerun()



# -------------------
# 1-1. 인적사항 입력 페이지
# -------------------
elif st.session_state.phase == "demographic":
    logo_path = os.path.join(BASE_DIR, "logo.png")
    st.image(logo_path, width=150)
    st.title("인적사항 입력")

    gender = st.radio("성별", ["남자", "여자"])
    age_group = st.selectbox("연령대", ["10대", "20대", "30대", "40대", "50대", "60대 이상"])

    if st.button("설문 시작"):
        if not gender or not age_group:
            st.warning("성별과 연령을 모두 입력해 주세요.")
        else:
            st.session_state.data.update({
                "gender": gender,
                "age": age_group
            })
            st.session_state.phase = "anthro"
            st.rerun()
########################################################
# 2. 의인화 척도
########################################################
elif st.session_state.phase == "anthro":
    anthro_path = os.path.join(BASE_DIR, "data", "questions_anthro.json")
    with open(anthro_path, encoding="utf-8") as f:
        questions = json.load(f)

    # 제목
    st.markdown("<h2 style='text-align:center; font-weight:bold;'>의인화 척도 설문</h2>", unsafe_allow_html=True)

    # 점수 의미 안내 (10점 척도)
    st.markdown("""
    <div style='display:flex; justify-content:center; flex-wrap:nowrap; font-size:16px; margin-bottom:18px; white-space:nowrap;'>
        <b>1점</b> : 전혀 그렇지 않다 &nbsp;&nbsp; — &nbsp;&nbsp;
        <b>5점</b> : 보통이다 &nbsp;&nbsp; — &nbsp;&nbsp;
        <b>10점</b> : 매우 그렇다
    </div>
    <div style='text-align:center; color:#777; font-size:13px; margin-top:-6px; margin-bottom:24px;'>
        ※ 초기값 <b>0</b>은 "<b>미응답</b>"을 의미합니다. 슬라이더를 움직여 1~10점 중 하나를 선택해 주세요.
    </div>
    """, unsafe_allow_html=True)

    responses = []

    for i, q in enumerate(questions, start=1):
        # 문항 + 슬라이더 (0은 미응답)
        val = st.slider(
            label=f"{i}. {q}",
            min_value=0, max_value=10, value=0, step=1,  # ⭐ 초기값 0=미응답
            format="%d점",
            key=f"anthro_{i}",
            help="0은 미응답을 의미합니다. 1~10점 중에서 선택해 주세요."
        )
        responses.append(val)

        # 문항 간 여백
        st.markdown("<div style='margin-bottom:12px;'></div>", unsafe_allow_html=True)

    # 다음 버튼
    if st.button("다음 (추론 과제)"):
        if any(v == 0 for v in responses):
            st.warning("모든 문항을 1~10점 중 하나로 선택해 주세요. (0은 미응답)")
        else:
            st.session_state.data["anthro_responses"] = responses  # 1~10점
            st.session_state.phase = "writing_intro"
            st.rerun()




# -------------------
# 2-1. 추론 기반 객관식 과제 지시문 페이지
# -------------------
elif st.session_state.phase == "writing_intro":
    st.markdown("<h2 style='text-align:center; font-weight:bold;'>추론 기반 객관식 과제 안내</h2>", unsafe_allow_html=True)

    st.markdown("""
    이번 단계에서는 **이누이트 언어(Inuktut-like)**의 간단한 규칙을 읽고,  
    총 **10개**의 객관식 문항에 답하는 **추론 과제**를 수행합니다.

    이 과제의 목표는 **정답률 자체가 아니라 ‘낯선 규칙에서 끝까지 추론하려는 과정’**을 관찰하는 것입니다.  
    즉, 정답을 모두 맞추는 것보다 **단서를 찾고, 비교하고, 일관된 근거로 선택**하는 과정이 더 중요합니다.

    **왜 중요한가요?**
    - 연구는 **문제 해결에서의 추론 전략**(패턴, 근거 사용, 오답 소거 등)을 분석합니다.
    - 여러분의 응답은 COVNOX라는 **추론 패턴 분석 도구**로 처리되어,  
      **능력 중심(추론 역량)** 또는 **노력 중심(추론 태도)** 관점의 피드백으로 제시됩니다.
    - 분석은 개인 식별 없이 **연구 목적**으로만 사용됩니다.

    **진행 방식**
    1) 간단한 어휘/어법 규칙을 읽습니다.  
    2) 객관식 문항 10개에 **모두 응답**합니다. (정답보다 **추론 근거**가 중요)  
    3) 제출하면 AI가 분석 애니메이션과 함께 결과 피드백을 보여줍니다.  
    4) 이후 설문으로 이어집니다.

    **성실히 참여하면 좋아요**
    - 문항마다 ‘가장 그럴듯한’ 선택을 고르고, 가능하면 **적용한 규칙**을 함께 떠올려 보세요.  
    - **끝까지 응답을 완성**하는 것이 중요합니다. 빈 문항 없이 제출해 주세요.  
    - 오답이어도 괜찮습니다. **추론 경로**가 분석의 핵심입니다.

    **유의사항**
    - 과제 도중 뒤로 가기/새로고침은 기록 손실을 일으킬 수 있습니다.  
    - 개인 피드백은 연구용으로 제공되며 점수화된 평가가 목적이 아닙니다.
    """)

    if st.button("추론 과제 시작"):
        st.session_state.phase = "writing"
        st.rerun()

# -------------------
# 3. 추론 기반 객관식 과제 (가상 언어 학습)
# -------------------
elif st.session_state.phase == "writing":
    import time

    # ⏱ 시작 시각 기록(한 번만)
    if "inference_started_ts" not in st.session_state:
        st.session_state.inference_started_ts = time.time()

    st.title("추론 과제 1/1 · 이누이트 언어 학습(Inuktut-like)")

    # 1) 학습 설명문 (간단한 어휘/어법 규칙)
    with st.expander("📘 과제 안내 · 간단 규칙(반드시 읽어주세요)", expanded=True):
        st.markdown("""
        이 과제는 **정답 여부보다 '어려운 조건에서 끝까지 추론하려는 노력'**을 봅니다.
        아래의 간단한 규칙을 참고해 10개의 객관식 문항에 답해주세요.

        **어휘 예시**
        - *ani* = 집,  *nuk* = 사람,  *sua* = 개,  *ika* = 물,  *pira* = 음식  
        - *taku* = 보다,  *niri* = 먹다,  *siku* = 만들다

        **어법 규칙(간단화)**
        1) **소유**: 명사 뒤에 `-mi` → “~의”  (예: *nuk-mi ani* = 사람의 집)
        2) **복수**: 명사 뒤에 `-t`  (예: *nuk-t* = 사람들)
        3) **목적 표시**: 목적어에 `-ka`  (예: *pira-ka niri* = 음식을 먹다)
        4) **시제**: 동사 뒤에 `-na`(현재), `-tu`(과거)  
        5) **연결**: 문장 연결에 *ama* = 그리고
        """)

    # 2) 10문항 객관식 (정답은 기록만, 노력 평가 목적 안내 포함)
    questions = [
        {"q": "Q1. ‘사람의 집(단수)’에 가장 가까운 것은?",
         "options": ["ani-mi nuk", "nuk-mi ani", "nuk-t ani", "ani-ka nuk"], "ans": 1},
        {"q": "Q2. ‘개가 물을 마신다(현재)’과 가장 가까운 구조는?  ※ niri=먹다(유사 동작), siku=만들다, taku=보다",
         "options": ["ika-ka sua niri-na", "sua-ka ika niri-tu", "sua taku-na ika-ka", "ika sua-ka niri-na"], "ans": 0},
        {"q": "Q3. ‘사람들이 음식을 만들었다(과거)’에 가장 가까운 것은?",
         "options": ["nuk-t pira-ka siku-tu", "nuk pira-ka siku-na", "pira nuk-t-ka siku-na", "nuk-mi pira siku-tu"], "ans": 0},
        {"q": "Q4. ‘개와 사람이 집을 본다(현재)’와 가장 가까운 것은?",
         "options": ["sua ama nuk ani-ka taku-na", "sua-ka ama nuk-ka ani taku-na", "ani-ka sua ama nuk taku-tu", "sua ama nuk-mi ani taku-na"], "ans": 0},
        {"q": "Q5. ‘사람의 개들이 음식을 본다(현재)’에 가장 가까운 것은?",
         "options": ["nuk-mi sua-t pira-ka taku-na", "nuk-t-mi sua pira-ka taku-na", "sua-t nuk pira-ka taku-na", "nuk-mi sua pira taku-na"], "ans": 0},
        {"q": "Q6. ‘사람들이 개의 집을 보았다(과거)’에 가장 가까운 것은?",
         "options": ["nuk-t sua-mi ani-ka taku-tu", "nuk sua-mi ani-ka taku-na", "nuk-t sua ani-ka taku-tu", "sua-mi nuk-t ani-ka taku-na"], "ans": 0},
        {"q": "Q7. ‘사람의 개가 물을 만들었다(과거)’에 가장 가까운 것은?",
         "options": ["nuk-mi sua ika-ka siku-tu", "sua-mi nuk ika-ka siku-na", "nuk-mi sua-ka ika siku-tu", "nuk-t sua ika-ka siku-tu"], "ans": 0},
        {"q": "Q8. ‘사람과 개가 음식을 먹는다(현재)’에 가장 가까운 것은?",
         "options": ["nuk ama sua pira-ka niri-na", "nuk pira-ka ama sua niri-na", "nuk ama sua pira niri-tu", "nuk-t ama sua pira-ka niri-na"], "ans": 0},
        {"q": "Q9. ‘사람들이 물과 음식을 본다(현재)’에 가장 가까운 것은?",
         "options": ["nuk-t ika ama pira-ka taku-na", "nuk-t ika-ka ama pira-ka taku-na", "nuk ika ama pira-ka taku-na", "nuk-t ika ama pira taku-na"], "ans": 0},
        {"q": "Q10. ‘개들이 사람의 집을 만들었다(과거)’에 가장 가까운 것은?",
         "options": ["sua-t nuk-mi ani-ka siku-tu", "sua nuk-mi ani-ka siku-na", "sua-t nuk ani-ka siku-tu", "sua-t nuk-mi ani siku-na"], "ans": 0},
    ]

    st.markdown(
        "<div style='margin:6px 0 16px; padding:10px; border-radius:8px; background:#202b20;'>"
        "※ 모든 문항은 <b>정답보다 '추론하려는 과정'</b>을 봅니다. 끝까지 선택해 주세요."
        "</div>", unsafe_allow_html=True
    )

    # 공통 근거 태그(응답자의 추론 근거 체크) — 칭찬/분석용으로 저장
    rationale_tags = ["소유(-mi)", "복수(-t)", "목적표시(-ka)", "시제(-na/-tu)", "연결어(ama)"]

    selections, rationales = [], []
    for i, item in enumerate(questions):
        st.markdown(f"### {item['q']}")
        st.caption("이 문항은 **정답이 전부가 아닙니다.** 규칙을 참고해 가장 그럴듯한 선택지를 고르세요.")
        choice = st.radio(
            label=f"문항 {i+1} 선택",
            options=list(range(len(item["options"]))),
            format_func=lambda idx, opts=item["options"]: opts[idx],
            key=f"mcq_{i}",
            horizontal=False,
            index=None  # ✅ 기본 선택 해제
        )
        selections.append(choice)  # None 가능 (아직 선택 전)
        # 🔎 선택 근거(복수 선택 가능) — 추론 패턴 기록용
        rationale = st.multiselect(
            f"문항 {i+1}에서 참고한 규칙(선택적)",
            options=rationale_tags,
            key=f"mcq_rationale_{i}"
        )
        rationales.append(rationale)

    # 2-1) 모든 문항 응답 확인
    def validate_mcq(sel_list):
        return all(s is not None for s in sel_list) and len(sel_list) == len(questions)

    # 제출 버튼
    if st.button("제출"):
        if not validate_mcq(selections):
            st.warning("10개 문항 모두 선택해 주세요.")
        else:
            # 선택값을 저장 시점에만 정수로 변환
            selected_idx = [int(s) for s in selections]

            # ⏱ 소요시간 기록
            st.session_state.inference_duration_sec = int(time.time() - st.session_state.inference_started_ts)

            # 정답 집계(참고용)
            score = sum(int(selected_idx[i] == q["ans"]) for i, q in enumerate(questions))

            # 저장: 기존 파이프라인과 충돌 없게 별도 키 사용
            st.session_state.inference_answers = [
                {
                    "q": questions[i]["q"],
                    "options": questions[i]["options"],
                    "selected_idx": selected_idx[i],
                    "correct_idx": int(questions[i]["ans"]),
                    "rationales": rationales[i]  # 추론 근거 기록
                }
                for i in range(len(questions))
            ]
            st.session_state.inference_score = int(score)

            # 🔄 분석 화면으로 전환하고 즉시 재렌더 (배경 잔상 방지)
            st.session_state.phase = "analyzing"
            st.experimental_rerun()


# -------------------
# 4. MCP 분석 모션 (MCP만 표시 → 종료 후 피드백으로)
# -------------------
elif st.session_state.phase == "analyzing":
    # MCP 애니메이션만 렌더
    run_mcp_motion()

    # 끝나면 다음 단계로 전환
    st.session_state.phase = "ai_feedback"
    st.experimental_rerun()
    st.stop()

# -------------------
# 5. AI 피드백 화면
# -------------------
elif st.session_state.phase == "ai_feedback":
    st.success("AI 분석 완료!")

    # 1) 피드백 1개 선택
    feedback = random.choice(feedback_sets[st.session_state.feedback_set_key])

    # 2) 추론 피드백용 하이라이트 문구(능력/노력 공통 포함)
    highlight_words = [
        # 공통
        "추론 패턴을 분석해본 결과",

        # 노력(과정) 측면
        "끝까지 답을 도출하려는 꾸준한 시도와 인내심",
        "여러 단서를 활용해 끊임없이 결론을 모색하려는 태도",
        "실패를 두려워하지 않고 반복적으로 추론을 시도한 흔적",
        "과정 중 발생한 시행착오를 극복하고 대안을 탐색한 노력",
        "여러 방법을 모색하고 끝까지 결론을 도출하려는 태도",

        # 능력(성과) 측면
        "단서를 빠르게 이해하고 논리적으로 연결하는 뛰어난 추론 능력",
        "여러 선택지 중 핵심 단서를 식별하고 일관된 결론으로 이끄는 분석적 사고력",
        "구조적 일관성을 유지하며 논리적 결론을 도출하는 추론 능력",
        "단서 간의 관계를 정확히 파악하고 체계적으로 연결하는 능력",
        "상황을 분석하고 적절한 결론을 선택하는 높은 수준의 판단력"
    ]

    # 3) 겹침/부분일치 오류 없이 하이라이트 적용
    import re
    def apply_highlight(text: str, phrases: list[str]) -> str:
        for p in sorted(set(phrases), key=len, reverse=True):
            # 문구 뒤에 공백/구두점/문장끝이 오면 매칭 (, . ! ? : ;) — 원문 보존
            pattern = re.escape(p) + r'(?=[\s,\.\!\?\:\;]|$)'
            text = re.sub(pattern, f"<b style='color:#2E7D32;'>{p}</b>", text)
        return text

    feedback = apply_highlight(feedback, highlight_words)
    feedback_with_breaks = feedback.replace("\n", "<br>")

    # 4) 카드 렌더
    feedback_html = f"""
    <div style='border: 2px solid #4CAF50; border-radius: 12px; padding: 20px; background-color: #F9FFF9;'>
        <h2 style='text-align:center; color:#2E7D32; margin-bottom:10px;'>📢 AI 평가 결과</h2>
        <p style='font-size:16px; line-height:1.6; text-align:left; color:#333;'>
            {feedback_with_breaks}
        </p>
    </div>
    """
    st.markdown(feedback_html, unsafe_allow_html=True)

    # 5) 여백 + 다음 단계
    st.markdown("<div style='margin-top:30px;'></div>", unsafe_allow_html=True)

    if st.button("학습동기 설문으로 이동"):
        # (기존 저장 키 유지)
        st.session_state.data["writing"] = st.session_state.writing_answers
        st.session_state.data["feedback_set"] = st.session_state.feedback_set_key
        st.session_state.phase = "motivation"
        st.rerun()

####################################################
# 6. 학습 동기 설문
####################################################
elif st.session_state.phase == "motivation":
    st.markdown("<h2 style='text-align:center; font-weight:bold;'>학습동기 설문</h2>", unsafe_allow_html=True)

    # 상단 점수 설명
    st.markdown("""
    <div style='display:flex; justify-content:center; flex-wrap:nowrap; font-size:16px; margin-bottom:30px; white-space:nowrap;'>
        <b>1점</b> : 전혀 그렇지 않다 &nbsp;&nbsp; - &nbsp;&nbsp;
        <b>3점</b> : 보통이다 &nbsp;&nbsp; - &nbsp;&nbsp;
        <b>5점</b> : 매우 그렇다
    </div>
    """, unsafe_allow_html=True)

    motivation_q = [
        "1. 이번 추론 과제와 비슷한 과제를 기회가 있다면 한 번 더 해보고 싶다.",
        "2. 앞으로도 추론 과제가 있다면 참여할 의향이 있다.",
        "3. 더 어려운 추론 과제가 주어져도 도전할 의향이 있다.",
        "4. 추론 과제의 난이도가 높아져도 시도해 볼 의향이 있다.",
        "5. 이번 과제를 통해 성취감을 느꼈다.",
        "6. 추론 과제를 통해 새로운 시각이나 아이디어를 배울 수 있었다.",
        "7. 이런 과제를 수행하는 것은 나의 추론 능력을 발전시키는 데 가치가 있다."
    ]

    motivation_responses = []

    for i, q in enumerate(motivation_q, start=1):
        choice = st.radio(
            label=f"{i}. {q}",
            options=list(range(1, 6)),
            index=None,
            horizontal=True,
            key=f"motivation_{i}",
            label_visibility="visible"
        )
        motivation_responses.append(choice)

        # 문항 간 여백
        st.markdown("<div style='margin-bottom:20px;'></div>", unsafe_allow_html=True)

    # 제출 버튼
    if st.button("설문 완료"):
        if None in motivation_responses:
            st.warning("모든 문항에 응답해 주세요.")
        else:
            st.session_state.data["motivation_responses"] = motivation_responses
            st.session_state.phase = "phone_input"
            st.rerun()




# -------------------
# 6-1. 휴대폰 번호 입력 단계
# -------------------
elif st.session_state.phase == "phone_input":
    st.title("휴대폰 번호 입력")
    st.markdown("""
    연구 참여가 완료되었습니다. 감사합니다.  
    연구 답례품을 받을 휴대폰 번호를 입력해 주세요. (선택 사항)  
    입력하지 않아도 제출이 가능합니다. 다만, 미입력 시 답례품 전달이 어려울 수 있습니다.
    """)
    phone = st.text_input("휴대폰 번호", placeholder="010-1234-5678")

    if st.button("제출"):
        if phone.strip() and not validate_phone(phone):
            st.warning("올바른 형식이 아닙니다. (예: 010-1234-5678)")
        else:
            st.session_state.data["phone"] = phone.strip()
            st.session_state.data["endTime"] = datetime.now().isoformat()
            save_to_csv(st.session_state.data)
            st.session_state.phase = "result"
            st.rerun()

# -------------------
# 7. 완료 화면
# -------------------
elif st.session_state.phase == "result":
    if "result_submitted" not in st.session_state:
        st.success("모든 과제가 완료되었습니다. 감사합니다!")
        st.write("연구에 참여해주셔서 감사합니다. 하단의 제출 버튼을 꼭 눌러주세요. 미제출시 답례품 제공이 어려울 수 있습니다.")

        if st.button("제출"):
            st.session_state.result_submitted = True
            st.rerun()
    else:
        st.success("응답이 저장되었습니다.")
        st.markdown("""
        <div style='font-size:16px; padding-top:10px;'>
            설문 응답이 성공적으로 저장되었습니다.<br>
            <b>이 화면은 자동으로 닫히지 않으니, 브라우저 탭을 수동으로 닫아 주세요.</b><br><br>
            ※ 본 연구에서 제공된 AI의 평가는 사전에 생성된 예시 대화문으로, 
            귀하의 실제 글쓰기 능력을 직접 평가한 것이 아님을 알려드립니다.
        </div>
        """, unsafe_allow_html=True)