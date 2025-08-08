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

fake_logs = [
    "[INFO] Loading dataset from secure storage... s3://ai-engine/empathy_scores.csv (34KB)",
    "[INFO] Preprocessing text input... removing stopwords & normalizing case",
    "[INFO] Tokenizing text into semantic units (precision mode)",
    "[OK] Semantic token map generated: 412 unique tokens",
    "[INFO] Running sentiment polarity analysis (multi-model ensemble)",
    "[OK] Sentiment polarity: +0.732 (Positive)",
    "[INFO] Vectorizing content using contextual embeddings (BERT-large)",
    "[OK] Embedding vector length: 1024 | Norm: 0.987",
    "[INFO] Initializing deep neural inference pipeline...",
    "[INFO] Layer 1: Convolutional feature extraction",
    "[INFO] Layer 2: Recurrent sequence modeling (BiLSTM)",
    "[INFO] Layer 3: Attention mechanism alignment",
    "[INFO] Running multi-head attention (8 heads)...",
    "[OK] Attention weights normalized",
    "[INFO] Cross-checking results with reinforcement learning agent",
    "[OK] Policy score: 0.884 | Confidence: High",
    "[INFO] Performing emotional tone classification (7 categories)",
    "[OK] Classified tone: Empathetic & Encouraging",
    "[INFO] Generating personalized feedback template...",
    "[INFO] Optimizing phrasing for clarity and motivational impact",
    "[OK] Final feedback text compiled",
    "[INFO] Validating output consistency against linguistic rules",
    "[OK] Grammar check passed | No critical issues",
    "[INFO] Saving inference report to temporary buffer...",
    "[OK] Report size: 2.8KB",
    "[✔] AI analysis complete. Preparing feedback delivery..."
]

def run_mcp_motion():
    st.markdown("""
        <h1 style="text-align: center; margin-top: 80px;">
            🧠 AI Analysing...
        </h1>
    """, unsafe_allow_html=True)

    log_placeholder = st.empty()
    progress_bar = st.progress(0)

    start_time = time.time()
    elapsed = 0
    step = 0
    total_duration = 8

    while elapsed < total_duration:
        progress = min((elapsed / total_duration), 1.0)
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
# 1. 연구 동의 페이지
# -------------------
if st.session_state.phase == "start":
    logo_path = os.path.join(BASE_DIR, "logo.png")
    st.image(logo_path, width=150)
    st.title("연구 참여 동의서")

    st.markdown("""
    #### 연구 목적
    본 연구는 인공지능 칭찬 유형과 의인화가 학습 동기에 미치는 영향을 탐구하기 위한 것입니다.

    #### 연구 절차
    - 의인화 설문
    - 창의적 글쓰기 과제
    - AI 피드백 경험
    - 학습동기 설문

    #### 개인정보 처리
    - 응답 내용은 익명으로 처리됩니다.
    - 전화번호 입력은 선택 사항이며, 연구 종료 후 즉시 폐기됩니다.

    #### 참여 조건
    - 만 18세 이상
    - 본 연구 절차에 동의한 경우에만 참여 가능합니다.
    """)

    consent = st.radio("연구에 참여하시겠습니까?", ["동의함", "동의하지 않음"])

    if st.button("다음"):
        if consent != "동의함":
            st.warning("연구 동의가 필요합니다.")
        else:
            st.session_state.data.update({
                "consent": consent,
                "startTime": datetime.now().isoformat()
            })
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

    # 점수 의미 안내
    st.markdown("""
    <div style='display:flex; justify-content:center; flex-wrap:nowrap; font-size:16px; margin-bottom:30px; white-space:nowrap;'>
        <b>1점</b> : 전혀 그렇지 않다 &nbsp;&nbsp; ----- &nbsp;&nbsp;
        <b>4점</b> : 보통이다 &nbsp;&nbsp; ----- &nbsp;&nbsp;
        <b>7점</b> : 매우 그렇다
    </div>
    """, unsafe_allow_html=True)

    responses = []

    for i, q in enumerate(questions, start=1):
        # 문항 + 라디오 버튼 (한 줄로)
        choice = st.radio(
            label=f"{i}. {q}",
            options=list(range(1, 8)),
            index=None,
            horizontal=True,
            key=f"anthro_{i}",
            label_visibility="visible"
        )
        responses.append(choice)

        # 문항 간 여백
        st.markdown("<div style='margin-bottom:20px;'></div>", unsafe_allow_html=True)

    # 다음 버튼
    if st.button("다음 (창의적 글쓰기 지시문)"):
        if None in responses:
            st.warning("모든 문항에 응답해 주세요.")
        else:
            st.session_state.data["anthro_responses"] = responses
            st.session_state.phase = "writing_intro"
            st.rerun()





# -------------------
# 2-1. 창의적 글쓰기 지시문 페이지
# -------------------
elif st.session_state.phase == "writing_intro":
    st.markdown("<h2 style='text-align:center; font-weight:bold;'>창의적 글쓰기 과제 안내</h2>", unsafe_allow_html=True)
    st.markdown("""
    다음 단계에서는 세 번의 창의적 글쓰기 과제를 수행하게 됩니다.  
    각 과제에서는 **세 개의 주어진 단어**를 모두 포함하여 글을 작성해야 합니다.  
    자유롭게 작성하되, **최소 10자 이상** 작성해야 제출이 가능합니다.  

    - 각 과제 작성 후 AI의 분석과 피드백을 받게 됩니다.
    - 피드백 확인 후 다음 과제로 진행됩니다.
    - 총 3회의 과제가 모두 끝나면 학습동기 설문으로 넘어갑니다.
    """)
    if st.button("과제 시작"):
        st.session_state.phase = "writing"
        st.rerun()

# -------------------
# 3. 창의적 글쓰기
# -------------------
elif st.session_state.phase == "writing":
    keywords_path = os.path.join(BASE_DIR, "data", "keywords.json")
    with open(keywords_path, encoding="utf-8") as f:
        keywords_list = json.load(f)
    current_keywords = keywords_list[st.session_state.current_kw_index]

    st.title(f"창의적 글쓰기 과제 {st.session_state.current_kw_index + 1}/3")
    st.markdown(f"""
        <h1 style="text-align: center; margin-top: 50px;">
            📋 주어진 단어 3개를 보고 글쓰기 과제를 진행합니다
        </h1>
        <p style="text-align: center; font-size: 18px;">
            주어진 <b>모든 단어</b>를 포함하여 자유롭게 작성해 주세요.<br>
            <b>최소 10자 이상</b> 작성해야 제출할 수 있습니다.
        </p>
        <p style="text-align: center; font-size: 20px; color: #4CAF50;">
            단어: <b>{' / '.join(current_keywords)}</b>
        </p>
        """, unsafe_allow_html=True)

    text_input = st.text_area("글 작성", key=f"text_{st.session_state.current_kw_index}")

    if st.button("제출"):
        valid, msg = validate_text(text_input, current_keywords)
        if not valid:
            st.warning(msg)
        else:
            st.session_state.writing_answers.append({"keywords": current_keywords, "text": text_input})
            st.session_state.phase = "analyzing"
            st.rerun()

# -------------------
# 4. MCP 분석 모션
# -------------------
elif st.session_state.phase == "analyzing":
    run_mcp_motion()
    st.session_state.phase = "ai_feedback"
    st.rerun()

# -------------------
# 5. AI 피드백 화면
# -------------------
elif st.session_state.phase == "ai_feedback":
    st.success("AI 분석 완료!")

    feedback = random.choice(feedback_sets[st.session_state.feedback_set_key])
    highlight_words = [
        "완성도 있는 결과", "끝까지 완성하려는 노력", "꾸준한 시도", "창의적인 접근",
        "높은 언어적 감각", "핵심 아이디어", "논리적인 확장", "매끄러운 구성"
    ]
    for word in highlight_words:
        feedback = feedback.replace(word, f"<b style='color:#2E7D32;'>{word}</b>")
    feedback_with_breaks = feedback.replace("\n", "<br>")

    feedback_html = f"""
    <div style='border: 2px solid #4CAF50; border-radius: 12px; padding: 20px; background-color: #F9FFF9;'>
        <h2 style='text-align:center; color:#2E7D32; margin-bottom:10px;'>📢 AI 평가 결과</h2>
        <p style='font-size:16px; line-height:1.6; text-align:left; color:#333;'>
            {feedback_with_breaks}
        </p>
    </div>
    """
    st.markdown(feedback_html, unsafe_allow_html=True)

    # ✅ 버튼과 피드백 사이에 여백
    st.markdown("<div style='margin-top:30px;'></div>", unsafe_allow_html=True)

    if st.session_state.current_kw_index < 2:
        if st.button("다음 글쓰기로 이동"):
            st.session_state.current_kw_index += 1
            st.session_state.phase = "writing"
            st.rerun()
    else:
        if st.button("학습동기 설문으로 이동"):
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
        <b>1점</b> : 전혀 그렇지 않다 &nbsp;&nbsp; ----- &nbsp;&nbsp;
        <b>5점</b> : 보통이다 &nbsp;&nbsp; ----- &nbsp;&nbsp;
        <b>10점</b> : 매우 그렇다
    </div>
    """, unsafe_allow_html=True)

    motivation_q = [
        "이번 글쓰기와 비슷한 과제를 기회가 있다면 한 번 더 해보고 싶다.",
        "앞으로도 글쓰기 과제가 있다면 참여할 의향이 있다.",
        "더 어려운 글쓰기 과제가 주어져도 도전할 의향이 있다.",
        "글쓰기 과제의 난이도가 높아져도 시도해 볼 의향이 있다.",
        "이번 과제를 통해 성취감을 느꼈다.",
        "글쓰기 과제를 통해 새로운 시각이나 아이디어를 배울 수 있었다.",
        "이런 과제를 수행하는 것은 나의 글쓰기 능력을 발전시키는 데 가치가 있다."
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
        st.write("연구에 참여해주셔서 감사합니다.")

        if st.button("제출 완료"):
            st.session_state.result_submitted = True
            st.rerun()
    else:
        st.success("응답이 저장되었습니다.")
        st.markdown("""
        <div style='font-size:16px; padding-top:10px;'>
            설문 응답이 성공적으로 저장되었습니다.<br>
            <b>이 화면은 자동으로 닫히지 않으니, 브라우저 탭을 수동으로 닫아 주세요.</b>
        </div>
        """, unsafe_allow_html=True)