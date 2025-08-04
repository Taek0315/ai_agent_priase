import streamlit as st
import time
import random
import json
import os
from datetime import datetime
from utils.validation import validate_phone, validate_text
from utils.save_data import save_to_csv

# -------------------
# 경로 설정 (main.py 기준 절대경로)
# -------------------
BASE_DIR = os.path.dirname(__file__)

# -------------------
# 초기 세팅
# -------------------
st.set_page_config(page_title="AI 칭찬 연구 설문", layout="centered")

# Streamlit 기본 UI 요소 제거 (우측 상단 메뉴, Footer 등)
hide_streamlit_style = """
    <style>
    #MainMenu {visibility: hidden;} 
    footer {visibility: hidden;} 
    header {visibility: hidden;}
    </style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# 세션 상태 초기화
if "phase" not in st.session_state:
    st.session_state.phase = "start"
    st.session_state.data = {}
    st.session_state.current_kw_index = 0
    st.session_state.writing_answers = []
    st.session_state.feedback_set_key = random.choice(["set1", "set2"])

# -------------------
# MCP 가짜 로그 (모션)
# -------------------
fake_logs = [
    "[INFO] 데이터셋 로드 중... s3://mcp-input/empathy_scores.csv (34KB)",
    "Gemini API 응답 시간: 113ms (OK)",
    "MCP::심볼릭 추상화 계층 정렬 중...",
    "행동 패턴 벡터 불러오는 중...",
    "언어 감성 엔트로피 분석 중...",
    "신경망 표현 겹침 시뮬레이션...",
    "잠재 인지 스키마 디코딩 (단계 3/7)...",
    "세맨틱 경로 매핑 중...",
    "심리 지표 매트릭스 정렬 Δ=0.039",
    "✔️ 공감 예측 엔진 수렴 완료",
    "임시 메모리 버퍼 정리 완료"
]

def run_mcp_motion():
    """7초 동안 AI 처리 시각 효과"""
    st.markdown("""
        <h1 style="text-align: center; margin-top: 100px;">
            🧠 AI analyzing what your TEXT...
        </h1>
    """, unsafe_allow_html=True)

    log_placeholder = st.empty()
    progress_bar = st.progress(0)
    start_time = time.time()
    elapsed = 0
    step = 0
    total_duration = 7

    while elapsed < total_duration:
        progress = min((elapsed / total_duration), 1.0)
        progress_bar.progress(progress)
        log_message = fake_logs[step % len(fake_logs)]
        timestamp = time.strftime("%H:%M:%S")
        log_placeholder.text(f"[{timestamp}] {log_message}")
        step += 1
        time.sleep(0.5)
        elapsed = time.time() - start_time

    progress_bar.progress(1.0)

# -------------------
# AI 피드백 세트 로드
# -------------------
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

# -------------------
# 2. 의인화 척도
# -------------------
elif st.session_state.phase == "anthro":
    anthro_path = os.path.join(BASE_DIR, "data", "questions_anthro.json")
    with open(anthro_path, encoding="utf-8") as f:
        questions = json.load(f)

    st.title("의인화 척도 설문")

    # 최상단 점수 의미 설명 (가로 한 줄, 모바일 대응)
    st.markdown("""
    <div style='display:flex; justify-content:center; flex-wrap:nowrap; font-size:16px; margin-bottom:20px; white-space:nowrap;'>
        <b>1점</b> : 전혀 그렇지 않다 &nbsp;&nbsp; ───────── &nbsp;&nbsp;
        <b>4점</b> : 보통이다 &nbsp;&nbsp; ───────── &nbsp;&nbsp;
        <b>7점</b> : 매우 그렇다
    </div>
    """, unsafe_allow_html=True)

    responses = []
    for i, q in enumerate(questions, start=1):
        # 문항 표시
        st.markdown(
            f"<p style='font-size:18px; font-weight:bold; margin-bottom:4px;'>{i}. {q}</p>",
            unsafe_allow_html=True
        )

        # 7점 리커트 척도 (기본값 없음, 버튼 하단에 숫자 표시)
        options_html = """
        <div style='display:flex; justify-content:center; gap:16px; margin-bottom:12px;'>
        """
        for num in range(1, 8):
            options_html += f"""
            <div style='text-align:center;'>
                <input type="radio" name="anthro_{i}" value="{num}" id="anthro_{i}_{num}" style="width:20px; height:20px;">
                <div style='margin-top:4px; font-size:14px;'>{num}</div>
            </div>
            """
        options_html += "</div>"

        st.markdown(options_html, unsafe_allow_html=True)

        # 실제 값 선택을 위해 Streamlit radio (숨김)
        choice = st.radio(
            label="",
            options=list(range(1, 8)),
            index=None,
            horizontal=True,
            key=f"anthro_{i}",
            label_visibility="collapsed"
        )
        responses.append(choice)

        # 5문항마다 구분선
        #if i % 5 == 0 and i != len(questions):
            #st.markdown("<hr style='border:1px solid #ccc; margin:20px 0;'>", unsafe_allow_html=True)

    # 필수 응답 체크
    if st.button("다음 (창의적 글쓰기)"):
        if None in responses:
            st.warning("모든 문항에 응답해 주세요.")
        else:
            st.session_state.data["anthro_responses"] = responses
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
    st.markdown(
        f"""
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
        """,
        unsafe_allow_html=True
    )

    text_input = st.text_area("글 작성", key=f"text_{st.session_state.current_kw_index}")

    if st.button("제출"):
        valid, msg = validate_text(text_input, current_keywords)
        if not valid:
            st.warning(msg)
        else:
            st.session_state.writing_answers.append({
                "keywords": current_keywords,
                "text": text_input
            })
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
    feedback_with_breaks = feedback.replace("\n", "  \n")
    st.markdown(f"### 📢 AI 평가 결과\n\n> {feedback_with_breaks}")

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

# -------------------
# 6. 학습동기 설문
# -------------------
elif st.session_state.phase == "motivation":
    st.title("학습동기 설문")

    # 최상단 점수 의미 설명 (가로 한 줄, 모바일 대응)
    st.markdown("""
    <div style='display:flex; justify-content:center; flex-wrap:nowrap; font-size:16px; margin-bottom:20px; white-space:nowrap;'>
        <b>1점</b> : 전혀 그렇지 않다 &nbsp;&nbsp; ───────── &nbsp;&nbsp;
        <b>5점</b> : 보통이다 &nbsp;&nbsp; ───────── &nbsp;&nbsp;
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
        # 문항 표시 (문항과 버튼 간격 줄임)
        st.markdown(
            f"<p style='font-size:18px; font-weight:bold; margin-bottom:4px;'>{i}. {q}</p>",
            unsafe_allow_html=True
        )

        # 버튼 + 숫자 표시 (가로 배치)
        options_html = "<div style='display:flex; justify-content:center; gap:16px; margin-bottom:12px;'>"
        for num in range(1, 11):
            options_html += f"""
            <div style='text-align:center;'>
                <input type="radio" name="motivation_{i}" value="{num}" id="motivation_{i}_{num}" style="width:20px; height:20px;">
                <div style='margin-top:4px; font-size:14px;'>{num}</div>
            </div>
            """
        options_html += "</div>"

        # HTML로 커스텀 버튼 표시
        st.markdown(options_html, unsafe_allow_html=True)

        # Streamlit이 값 저장할 수 있도록 숨김 라디오
        choice = st.radio(
            label="",
            options=list(range(1, 11)),
            index=None,
            horizontal=True,
            key=f"motivation_{i}",
            label_visibility="collapsed"
        )
        motivation_responses.append(choice)

    # 설문 완료 버튼
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
    st.success("모든 과제가 완료되었습니다. 감사합니다!")
    st.write("응답이 저장되었습니다.")
    if st.button("다시 시작"):
        st.session_state.clear()
        st.rerun()
