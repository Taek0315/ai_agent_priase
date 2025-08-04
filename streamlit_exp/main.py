import streamlit as st
import time
import random
import json
from datetime import datetime
from utils.validation import validate_phone, validate_text
from utils.save_data import save_to_csv

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
    st.session_state.phase = "start"  # 현재 단계
    st.session_state.data = {}  # 전체 응답 저장
    st.session_state.current_kw_index = 0  # 현재 글쓰기 번호 (0~2)
    st.session_state.writing_answers = []  # 글쓰기 응답 저장
    st.session_state.feedback_set_key = random.choice(["set1", "set2"])  # AI 피드백 세트 랜덤 선택

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
    total_duration = 7  # 총 7초 동안 실행

    while elapsed < total_duration:
        # 진행률 계산
        progress = min((elapsed / total_duration), 1.0)
        progress_bar.progress(progress)

        # 순차적으로 로그 표시 (실제 처리 순서처럼)
        log_message = fake_logs[step % len(fake_logs)]
        timestamp = time.strftime("%H:%M:%S")
        log_placeholder.text(f"[{timestamp}] {log_message}")

        step += 1
        time.sleep(0.5)  # 0.5초마다 새로운 로그 표시
        elapsed = time.time() - start_time

    progress_bar.progress(1.0)

# -------------------
# AI 피드백 세트
# -------------------
with open("data/feedback_sets.json", encoding="utf-8") as f:
    feedback_sets = json.load(f)

# -------------------
# 1. 연구 동의 페이지
# -------------------
if st.session_state.phase == "start":
    st.image("logo.png", width=150)
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
    st.image("logo.png", width=150)
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
    with open("data/questions_anthro.json", encoding="utf-8") as f:
        questions = json.load(f)
    st.title("의인화 척도 설문")
    responses = []
    for q in questions:
        responses.append(st.slider(q, 1, 7, 4))
    if st.button("다음 (창의적 글쓰기)"):
        st.session_state.data["anthro_responses"] = responses
        st.session_state.phase = "writing"
        st.rerun()

# -------------------
# 3. 창의적 글쓰기
# -------------------
elif st.session_state.phase == "writing":
    with open("data/keywords.json", encoding="utf-8") as f:
        keywords_list = json.load(f)
    current_keywords = keywords_list[st.session_state.current_kw_index]

    st.title(f"창의적 글쓰기 과제 {st.session_state.current_kw_index + 1}/3")
    
    # 줄바꿈을 포함한 안내문
    st.markdown(
        f"""
        다음 단어를 모두 포함하여 **최소 20자 이상** 작성하세요:

        **{ ' / '.join(current_keywords) }**
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
    
    # JSON 안의 \n을 Markdown 줄바꿈으로 변환
    feedback_with_breaks = feedback.replace("\n", "  \n")
    
    st.markdown(f"### 📢 AI 평가 결과\n\n> {feedback_with_breaks}")

    if st.session_state.current_kw_index < 2:
        if st.button("다음 글쓰기로 이동"):
            st.session_state.current_kw_index += 1
            st.session_state.phase = "writing"
            st.rerun()
    else:
        if st.button("학습동기 설문으로 이동"):
            # 모든 글쓰기 저장
            st.session_state.data["writing"] = st.session_state.writing_answers
            st.session_state.data["feedback_set"] = st.session_state.feedback_set_key
            st.session_state.phase = "motivation"
            st.rerun()

# -------------------
# 6. 학습동기 설문
# -------------------
elif st.session_state.phase == "motivation":
    st.title("학습동기 설문")
    motivation_q = [
    # 과제 지속 의향
    "이번 글쓰기와 비슷한 과제를 앞으로도 계속 해보고 싶다.",
    "앞으로도 글쓰기 과제를 자발적으로 선택해 수행할 가능성이 높다.",
    
    # 도전 의향
    "다음에는 이번보다 더 어려운 글쓰기 과제에 도전해보고 싶다.",
    "글쓰기 과제의 난이도가 높아져도 시도해 볼 의향이 있다.",
    
    # 성취·배움 가치
    "이번 과제를 통해 느낀 성취감은 나에게 중요하다.",
    "글쓰기 과제를 통해 새로운 시각이나 아이디어를 배울 수 있었다.",
    "이런 과제를 수행하는 것은 나의 글쓰기 능력을 발전시키는 데 가치가 있다."
]
    motivation_responses = []
    for q in motivation_q:
        motivation_responses.append(st.slider(q, 1, 10, 5))

    if st.button("설문 완료"):
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
    입력하지 않아도 제출이 가능합니다. 다만, 미입력시 답례품 전달이 어려울 수 있습니다.
    """)
    phone = st.text_input("휴대폰 번호", placeholder="010-1234-5678")

    if st.button("제출"):
        # 번호를 입력했다면 형식 검증
        if phone.strip() and not validate_phone(phone):
            st.warning("올바른 형식이 아닙니다. (예: 010-1234-5678)")
        else:
            # 번호가 없으면 빈 문자열로 저장
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
