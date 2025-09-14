# ──────────────────────────────────────────────────────────────────────────────
# 필요한 모듈
import streamlit as st
import time, random, json, os
from datetime import datetime
from utils.validation import validate_phone
from utils.save_data import save_to_csv

# 페이지 설정
st.set_page_config(page_title="AI 칭찬 연구 설문", layout="centered")

# 경로 상수
BASE_DIR = os.path.dirname(__file__)

# ──────────────────────────────────────────────────────────────────────────────
# 전역 스타일: 상단 UI 제거 + 여백 최소화
COMPACT_CSS = """
<style>
#MainMenu, header, footer, [data-testid="stToolbar"] { display: none !important; }
:root {
  --block-container-padding-top: 0rem !important;
  --block-container-padding: 0rem 1rem 1.25rem !important;
}
html, body, .stApp, [data-testid="stAppViewContainer"],
[data-testid="stAppViewContainer"] > .main, section.main {
  margin-top: 0 !important;
  padding-top: 0 !important;
}
[data-testid="stAppViewContainer"] > .main > div,
.main .block-container, section.main > div.block-container {
  padding-top: 0 !important;
  padding-bottom: 20px !important;
}
h1, .stMarkdown h1 { margin-top: 0 !important; margin-bottom: 12px !important; line-height: 1.2; }
h2, .stMarkdown h2 { margin-top: 0 !important; margin-bottom: 10px !important; }
p, .stMarkdown p   { margin-top: 0 !important; }
html, body { overflow-x: hidden !important; }
</style>
"""
st.markdown(COMPACT_CSS, unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────────────────
# 공통: 스크롤 항상 최상단
def scroll_top_js(nonce: int | None = None):
    if nonce is None:
        nonce = st.session_state.get("_scroll_nonce", 0)
    st.markdown(
        f"""
        <script id="goTop-{nonce}">(function(){{
          function goTop() {{
            try {{
              var pdoc = window.parent && window.parent.document;
              var sect = pdoc && pdoc.querySelector && pdoc.querySelector('section.main');
              if (sect && sect.scrollTo) sect.scrollTo({{top:0, left:0, behavior:'instant'}});
            }} catch(e) {{}}
            try {{
              window.scrollTo({{top:0, left:0, behavior:'instant'}});
              document.documentElement.scrollTo(0,0);
              document.body.scrollTo(0,0);
            }} catch(e) {{}}
          }}
          goTop();
          if (window.requestAnimationFrame) requestAnimationFrame(goTop);
          setTimeout(goTop, 25); setTimeout(goTop, 80);
        }})();</script>
        """,
        unsafe_allow_html=True
    )

# ──────────────────────────────────────────────────────────────────────────────
# 상태 초기화
if "phase" not in st.session_state:
    st.session_state.phase = "start"
    st.session_state.data = {}
    st.session_state.feedback_set_key = random.choice(["set1", "set2"])
    st.session_state.praise_once = False
    st.session_state.used_feedback_indices = set()
    st.session_state.round1_started_ts = None
    st.session_state.round2_started_ts = None

# ──────────────────────────────────────────────────────────────────────────────
# 피드백 세트 로드
feedback_path = os.path.join(BASE_DIR, "data", "feedback_sets.json")
try:
    with open(feedback_path, "r", encoding="utf-8") as f:
        feedback_sets = json.load(f)
    if not isinstance(feedback_sets, dict) or not feedback_sets:
        raise ValueError("feedback_sets.json 형식 오류")
except Exception:
    feedback_sets = {
        "set1": ["참여해 주셔서 감사합니다. 추론 과정에서의 꾸준한 시도가 인상적이었습니다."],
        "set2": ["핵심 단서를 파악하고 일관된 결론을 도출한 점이 돋보였습니다."]
    }

def pick_feedback_text(set_key: str) -> str:
    fs = feedback_sets.get(set_key, [])
    if not fs:
        return "수고하셨습니다."
    remaining = [i for i in range(len(fs)) if i not in st.session_state.used_feedback_indices]
    idx = random.choice(remaining) if remaining else random.randrange(len(fs))
    st.session_state.used_feedback_indices.add(idx)
    return fs[idx]

# ─────────────────────────────────────────────
# 연구 동의 / 개인정보 동의 HTML 문서
# ─────────────────────────────────────────────
CONSENT_HTML = """
<div class="consent-wrap">
  <h1>연구대상자 설명문</h1>
  <div class="subtitle"><strong>제목: </strong>AI 에이전트의 피드백 방식이 학습에 미치는 영향 탐색 연구</div>

  <h2>1. 연구 목적</h2>
  <p>본 연구는 학습 상황에서 AI 에이전트가 제공하는 칭찬 방식(과정 귀인 vs 능력 귀인)이 학습자의 학습 동기에 미치는 영향을 검증하고, 
     AI를 얼마나 인간처럼 지각하는지(의인화 수준)가 이 관계를 조절하는지 탐구하는 것을 목적으로 합니다.</p>

  <h2>2. 연구 참여 대상</h2>
  <p>만 18세 이상의 한국어 사용자.</p>

  <h2>3. 연구 방법</h2>
  <p>의인화 문항(30개), 성취 문항(26개), 추론 과제(2회차), 학습동기 문항(7개), 선택적 전화번호 입력.</p>

  <h2>4. 연구 참여 시간</h2>
  <p>약 10~15분 소요.</p>

  <h2>5. 보상</h2>
  <p>참여자에게 1천원 상당의 기프티콘 제공 (전화번호 기재 시).</p>

  <h2>6. 위험 및 중단</h2>
  <p>연구 참여 중 언제든 불편 시 종료 가능하며, 불이익 없음.</p>

  <h2>7. 개인정보와 비밀보장</h2>
  <p>성별, 연령, 전화번호를 수집하며 연구 종료 후 3년간 보관 후 파기.</p>

  <h2>* 연구 문의</h2>
  <p>가톨릭대학교 발달심리학 전공 오현택 (010-6532-3161 / toh315@gmail.com)</p>
</div>
"""

AGREE_HTML = """
<div class="agree-wrap">
  <div class="agree-title">연구 동의서</div>
  <ol class="agree-list">
    <li>연구 설명문을 읽고 충분히 이해하였습니다.</li>
    <li>연구 참여로 인한 위험과 이득을 숙지하였습니다.</li>
    <li>자발적으로 연구 참여에 동의합니다.</li>
    <li>연구자가 개인정보를 법과 규정에 따라 수집/처리함에 동의합니다.</li>
    <li>연구자가 연구 관련 자료를 열람할 수 있음에 동의합니다.</li>
    <li>언제든 참여를 철회할 수 있으며, 불이익이 없음을 이해합니다.</li>
  </ol>
</div>
"""

PRIVACY_HTML = """
<div class="privacy-wrap">
  <h1>개인정보 수집·이용 동의서</h1>
  <table class="privacy-table">
    <tr><th>수집 항목</th><td>성별, 연령, 전화번호(선택)</td></tr>
    <tr><th>이용 목적</th><td>연구 수행 및 결과 분석, 보상 지급</td></tr>
    <tr><th>보관 기간</th><td>연구 종료 후 3년</td></tr>
  </table>
  <p class="privacy-note">※ 동의하지 않으면 연구 참여가 불가합니다.</p>
</div>
"""

COMMON_CSS = """
<style>
  .consent-wrap, .agree-wrap, .privacy-wrap {
    max-width: 900px; margin: 0 auto 20px; padding: 16px;
    border: 1px solid #E5E7EB; border-radius: 12px; background: #fff;
  }
  .agree-title { text-align: center; font-weight: 800; margin-bottom: 12px; }
  .privacy-table { width: 100%; border-collapse: collapse; margin: 10px 0; }
  .privacy-table th, .privacy-table td {
    border: 1px solid #333; padding: 8px; text-align: left;
  }
  .privacy-table th { background: #f3f3f3; width: 30%; }
</style>
"""

def render_consent_doc():
    st.markdown(COMMON_CSS, unsafe_allow_html=True)
    st.markdown(CONSENT_HTML, unsafe_allow_html=True)

def render_agree_doc():
    st.markdown(COMMON_CSS, unsafe_allow_html=True)
    st.markdown(AGREE_HTML, unsafe_allow_html=True)

def render_privacy_doc():
    st.markdown(COMMON_CSS, unsafe_allow_html=True)
    st.markdown(PRIVACY_HTML, unsafe_allow_html=True)

# ─────────────────────────────────────────────
# 연구 동의 페이지
# ─────────────────────────────────────────────
if st.session_state.phase == "start":
    scroll_top_js()
    st.title("AI 칭찬 연구 설문")

    if "consent_step" not in st.session_state:
        st.session_state.consent_step = "explain"

    if st.session_state.consent_step == "explain":
        st.subheader("연구대상자 설명문")
        render_consent_doc()
        if st.button("다음"):
            st.session_state.consent_step = "agree"
            st.rerun()

    elif st.session_state.consent_step == "agree":
        st.subheader("연구 동의서")
        render_agree_doc()
        consent_research = st.radio("연구 참여 동의 여부", ["동의함", "동의하지 않음"], horizontal=True, index=None)

        st.subheader("개인정보 수집·이용 동의")
        render_privacy_doc()
        consent_privacy = st.radio("개인정보 동의 여부", ["동의함", "동의하지 않음"], horizontal=True, index=None)

        if st.button("다음 단계로"):
            if consent_research != "동의함":
                st.warning("연구 참여에 동의해야 진행할 수 있습니다.")
            elif consent_privacy != "동의함":
                st.warning("개인정보 수집·이용에 동의해야 진행할 수 있습니다.")
            else:
                st.session_state.data.update({
                    "consent": "동의함",
                    "consent_research": consent_research,
                    "consent_privacy": consent_privacy,
                    "startTime": datetime.now().isoformat()
                })
                st.session_state.phase = "demographic"
                st.rerun()

# ─────────────────────────────────────────────
# 인적사항 입력
# ─────────────────────────────────────────────
elif st.session_state.phase == "demographic":
    scroll_top_js()
    st.title("인적사항 입력")

    gender = st.radio("성별", ["남자", "여자"], index=None)
    age_group = st.radio("연령대", ["10대", "20대", "30대", "40대", "50대", "60대 이상"], index=None)

    if st.button("설문 시작"):
        if not gender or not age_group:
            st.warning("성별과 연령을 모두 입력해야 합니다.")
        else:
            st.session_state.data.update({"gender": gender, "age": age_group})
            st.session_state.phase = "anthro"
            st.rerun()
# ─────────────────────────────────────────────
# 의인화 척도 (5점 리커트, 30문항 → 10문항씩 3페이지)
# ─────────────────────────────────────────────
elif st.session_state.phase == "anthro":
    scroll_top_js()

    anthro_path = os.path.join(BASE_DIR, "data", "questions_anthro.json")
    with open(anthro_path, encoding="utf-8") as f:
        questions = json.load(f)

    total_items = len(questions)  # 30개 예상
    page_size = 10
    total_pages = (total_items + page_size - 1) // page_size

    if "anthro_page" not in st.session_state:
        st.session_state["anthro_page"] = 1
    if "anthro_responses" not in st.session_state or len(st.session_state["anthro_responses"]) != total_items:
        st.session_state["anthro_responses"] = [None] * total_items

    page = st.session_state["anthro_page"]
    start_idx = (page - 1) * page_size
    end_idx = min(start_idx + page_size, total_items)
    slice_questions = questions[start_idx:end_idx]

    st.markdown("<h2 style='text-align:center;'>의인화 척도</h2>", unsafe_allow_html=True)
    st.caption("1=전혀 그렇지 않다 · 3=보통이다 · 5=매우 그렇다")

    for i, q in enumerate(slice_questions, start=start_idx + 1):
        choice = st.radio(
            f"{i}. {q}", options=[1, 2, 3, 4, 5],
            index=None, horizontal=True, key=f"anthro_{i}"
        )
        st.session_state["anthro_responses"][i-1] = choice

    col1, col2 = st.columns([1, 1])
    with col1:
        if page > 1 and st.button("← 이전"):
            st.session_state["anthro_page"] -= 1
            st.rerun()
    with col2:
        if page < total_pages:
            if st.button("다음 →"):
                if None in st.session_state["anthro_responses"][start_idx:end_idx]:
                    st.warning("모든 문항에 응답해야 합니다.")
                else:
                    st.session_state["anthro_page"] += 1
                    st.rerun()
        else:
            if st.button("성취 문항으로 이동"):
                if None in st.session_state["anthro_responses"]:
                    st.warning("모든 문항에 응답해야 합니다.")
                else:
                    st.session_state.data["anthro_responses"] = st.session_state["anthro_responses"]
                    st.session_state["anthro_page"] = 1
                    st.session_state.phase = "achive"
                    st.rerun()

# ─────────────────────────────────────────────
# 성취 문항 (6점 리커트, 26문항 → 10/10/6 페이지)
# ─────────────────────────────────────────────
elif st.session_state.phase == "achive":
    scroll_top_js()

    achive_path = os.path.join(BASE_DIR, "data", "questions_achive.json")
    with open(achive_path, "r", encoding="utf-8") as f:
        achive_questions = json.load(f)

    total_items = len(achive_questions)  # 26개 예상
    page_sizes = [10, 10, total_items - 20]
    total_pages = len(page_sizes)

    if "achive_page" not in st.session_state:
        st.session_state["achive_page"] = 1
    if "achive_responses" not in st.session_state or len(st.session_state["achive_responses"]) != total_items:
        st.session_state["achive_responses"] = [None] * total_items

    page = st.session_state["achive_page"]
    start_idx = sum(page_sizes[:page-1])
    end_idx = start_idx + page_sizes[page-1]

    st.markdown("<h2 style='text-align:center;'>성취 문항</h2>", unsafe_allow_html=True)
    st.caption("1=전혀 그렇지 않다 · 3=보통이다 · 6=매우 그렇다")

    for i, q in enumerate(achive_questions[start_idx:end_idx], start=start_idx + 1):
        choice = st.radio(
            f"{i}. {q}", options=[1, 2, 3, 4, 5, 6],
            index=None, horizontal=True, key=f"achive_{i}"
        )
        st.session_state["achive_responses"][i-1] = choice

    col1, col2 = st.columns([1, 1])
    with col1:
        if page > 1 and st.button("← 이전"):
            st.session_state["achive_page"] -= 1
            st.rerun()
    with col2:
        if page < total_pages:
            if st.button("다음 →"):
                if None in st.session_state["achive_responses"][start_idx:end_idx]:
                    st.warning("모든 문항에 응답해야 합니다.")
                else:
                    st.session_state["achive_page"] += 1
                    st.rerun()
        else:
            if st.button("추론 과제 안내로 이동"):
                if None in st.session_state["achive_responses"]:
                    st.warning("모든 문항에 응답해야 합니다.")
                else:
                    st.session_state.data["achive_responses"] = st.session_state["achive_responses"]
                    st.session_state["achive_page"] = 1
                    st.session_state.phase = "writing_intro"
                    st.rerun()

# ─────────────────────────────────────────────
# 추론 과제 안내
# ─────────────────────────────────────────────
elif st.session_state.phase == "writing_intro":
    scroll_top_js()

    st.markdown("<h2 style='text-align:center;'>추론 과제 안내</h2>", unsafe_allow_html=True)
    st.markdown("""
    이번 단계에서는 **이누이트어(Inuktut-like)** 규칙을 기반으로 한 추론 과제를 **2회** 수행합니다.  

    - 1차 과제: 10문항 → MCP 분석 모션 → AI 피드백 → 난이도 선택  
    - 2차 과제: 10문항 → MCP 분석 모션 → AI 피드백 → 학습동기 설문  

    ⚠️ 정답률보다 **끝까지 추론하는 과정**이 더 중요합니다.  
    """)
    if st.button("1차 추론 과제 시작"):
        st.session_state.phase = "writing_round1"
        st.session_state.round1_started_ts = time.time()
        st.rerun()
# ─────────────────────────────────────────────
# 추론 과제 문항 생성 함수 (10문항)
# ─────────────────────────────────────────────
def build_inference_questions():
    return [
        {"q": "Q1. ‘사람의 집(단수)’에 가장 가까운 것은?",
         "options": ["ani-mi nuk", "nuk-mi ani", "nuk-t ani", "ani-ka nuk"], "ans": 1},
        {"q": "Q2. ‘개가 물을 마신다(현재)’와 가장 가까운 구조는?",
         "options": ["ika-ka sua niri-na", "sua-ka ika niri-tu", "sua taku-na ika-ka", "ika sua-ka niri-na"], "ans": 0},
        {"q": "Q3. ‘사람들이 음식을 만들었다(과거)’와 가장 가까운 것은?",
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

RATIONALE_TAGS = ["소유(-mi)", "복수(-t)", "목적(-ka)", "시제(-na/-tu)", "연결어(ama)"]

# ─────────────────────────────────────────────
# 추론 과제 라운드 렌더링
# ─────────────────────────────────────────────
def render_inference_round(round_no: int):
    scroll_top_js()
    st.title(f"추론 과제 {round_no}/2")

    st.caption("⚠️ 정답률보다 끝까지 추론하는 과정이 더 중요합니다.")

    questions = build_inference_questions()
    selections, rationales = [], []

    for i, item in enumerate(questions, start=1):
        st.markdown(f"### {item['q']}")
        choice = st.radio(
            f"문항 {i} 선택",
            options=list(range(len(item["options"]))),
            format_func=lambda idx, opts=item["options"]: opts[idx],
            key=f"round{round_no}_mcq_{i}",
            horizontal=False, index=None
        )
        selections.append(choice)

        rationale = st.multiselect(
            f"문항 {i} 근거 규칙",
            options=RATIONALE_TAGS,
            key=f"round{round_no}_rat_{i}"
        )
        rationales.append(rationale)

    if st.button("제출", key=f"submit_round{round_no}"):
        if None in selections or any(len(r) == 0 for r in rationales):
            st.warning("모든 문항에 선택과 근거를 입력해야 합니다.")
        else:
            score = sum(int(selections[i] == q["ans"]) for i, q in enumerate(questions))
            duration = int(time.time() - (st.session_state.round1_started_ts if round_no == 1 else st.session_state.round2_started_ts))

            st.session_state.data[f"inference_round{round_no}"] = {
                "answers": selections,
                "rationales": rationales,
                "score": score,
                "duration_sec": duration
            }
            st.session_state.phase = f"analyzing_round{round_no}"
            st.rerun()

# ─────────────────────────────────────────────
# 추론 과제 단계
# ─────────────────────────────────────────────
if st.session_state.phase == "writing_round1":
    render_inference_round(1)

elif st.session_state.phase == "writing_round2":
    if not st.session_state.get("round2_started_ts"):
        st.session_state.round2_started_ts = time.time()
    render_inference_round(2)

# ─────────────────────────────────────────────
# MCP 분석 모션
# ─────────────────────────────────────────────
elif st.session_state.phase in ["analyzing_round1", "analyzing_round2"]:
    scroll_top_js()
    round_no = 1 if st.session_state.phase.endswith("round1") else 2

    if not st.session_state.get(f"_mcp_done_{round_no}"):
        run_mcp_motion(6.0)
        st.session_state[f"_mcp_done_{round_no}"] = True
        st.rerun()
    else:
        st.success("✅ 분석이 완료되었습니다.")
        if st.button("결과 보기"):
            st.session_state.phase = f"ai_feedback_round{round_no}"
            st.rerun()

# ─────────────────────────────────────────────
# AI 피드백
# ─────────────────────────────────────────────
elif st.session_state.phase in ["ai_feedback_round1", "ai_feedback_round2"]:
    scroll_top_js()
    round_no = 1 if "round1" in st.session_state.phase else 2
    set_key = st.session_state.get("feedback_set_key", "set1")

    st.markdown(f"### 🤖 AI 피드백 ({'노력 칭찬' if set_key=='set1' else '능력 칭찬'})")

    feedback = pick_feedback_text(set_key)
    st.info(feedback)

    if round_no == 1:
        if st.button("다음 과제 난이도 선택"):
            st.session_state.phase = "difficulty_after_fb1"
            st.rerun()
    else:
        if st.button("학습동기 설문으로 이동"):
            st.session_state.phase = "motivation"
            st.rerun()
# ─────────────────────────────────────────────
# 1차 피드백 직후 난이도 선택
# ─────────────────────────────────────────────
elif st.session_state.phase == "difficulty_after_fb1":
    scroll_top_js()
    st.subheader("👉 다음 과제 난이도를 선택해 주세요 (1~10)")
    diff_choice = st.radio(
        "2차 과제 난이도",
        list(range(1, 11)),
        index=None,
        horizontal=True,
        key="diff_choice_round2"
    )

    if st.button("확인 후 2차 과제로 이동"):
        if diff_choice is None:
            st.warning("난이도를 선택해야 합니다.")
        else:
            st.session_state.data["difficulty_after_fb1"] = int(diff_choice)
            st.session_state.phase = "writing_round2"
            st.session_state.round2_started_ts = time.time()
            st.rerun()

# ─────────────────────────────────────────────
# 학습 동기 설문 (7문항)
# ─────────────────────────────────────────────
elif st.session_state.phase == "motivation":
    scroll_top_js()
    st.markdown("<h2 style='text-align:center;'>📋 학습 동기 설문</h2>", unsafe_allow_html=True)
    st.caption("※ 각 문항은 1점(전혀 그렇지 않다) ~ 5점(매우 그렇다) 사이에서 선택해주세요.")

    motivation_q = [
        "1. 이번 추론 과제와 비슷한 과제를 기회가 있다면 한 번 더 해보고 싶다.",
        "2. 앞으로도 추론 과제가 있다면 참여할 의향이 있다.",
        "3. 더 어려운 추론 과제가 주어져도 도전할 의향이 있다.",
        "4. 추론 과제의 난이도가 높아져도 시도해 볼 의향이 있다.",
        "5. 이번 과제를 통해 성취감을 느꼈다.",
        "6. 추론 과제를 통해 새로운 시각이나 아이디어를 배울 수 있었다.",
        "7. 이런 과제를 수행하는 것은 나의 추론 능력을 발전시키는 데 가치가 있다."
    ]

    if "motivation_responses" not in st.session_state:
        st.session_state.motivation_responses = [None] * len(motivation_q)

    for i, q in enumerate(motivation_q):
        choice = st.radio(
            q,
            options=list(range(1, 6)),
            index=None,
            horizontal=True,
            key=f"motivation_{i}"
        )
        st.session_state.motivation_responses[i] = choice

    if st.button("다음 (휴대폰 입력)"):
        if None in st.session_state.motivation_responses:
            st.warning("모든 문항에 응답해야 합니다.")
        else:
            st.session_state.data["motivation_responses"] = st.session_state.motivation_responses
            st.session_state.phase = "phone_input"
            st.rerun()

# ─────────────────────────────────────────────
# 휴대폰 번호 입력 (선택)
# ─────────────────────────────────────────────
elif st.session_state.phase == "phone_input":
    scroll_top_js()
    st.title("📱 휴대폰 번호 입력 (선택)")

    st.markdown("""
    연구 참여에 감사드립니다.  
    답례품(기프티콘)을 원하시면 휴대폰 번호를 입력해 주세요.  
    (입력하지 않아도 연구는 정상적으로 종료됩니다.)
    """)

    phone = st.text_input("휴대폰 번호", placeholder="010-1234-5678", key="phone_input_value")

    if st.button("다음 (추가 난이도 선택)"):
        if phone.strip() and not validate_phone(phone):
            st.warning("올바른 형식이 아닙니다. (예: 010-1234-5678)")
        else:
            st.session_state.data["phone"] = phone.strip()
            st.session_state.phase = "difficulty_final"
            st.rerun()

# ─────────────────────────────────────────────
# 최종 추가 난이도 선택
# ─────────────────────────────────────────────
elif st.session_state.phase == "difficulty_final":
    scroll_top_js()
    st.subheader("마지막 추가 과제 난이도를 선택해 주세요 (1~10)")
    diff2 = st.radio(
        "추가 난이도",
        list(range(1, 11)),
        index=None,
        horizontal=True,
        key="final_diff_radio"
    )

    if st.button("확인 후 마무리"):
        if diff2 is None:
            st.warning("난이도를 선택해 주세요.")
        else:
            st.session_state.data["difficulty_final"] = int(diff2)
            st.session_state.phase = "result"
            st.rerun()

# ─────────────────────────────────────────────
# 최종 디브리핑 & 자동 저장
# ─────────────────────────────────────────────
elif st.session_state.phase == "result":
    scroll_top_js()

    if "result_submitted" not in st.session_state:
        st.session_state.data["endTime"] = datetime.now().isoformat()
        try:
            save_to_csv(st.session_state.data)
            st.session_state.result_submitted = True
        except Exception as e:
            st.error(f"저장 중 오류 발생: {e}")

    st.success("✅ 모든 과제가 완료되었습니다. 감사합니다!")

    st.markdown("""
    <div style='font-size:16px; padding-top:10px;'>
        ※ 본 연구에서 제공된 AI의 평가는 <b>사전에 준비된 예시 문구</b>를 기반으로 제공된 것이며,  
        실제 추론 능력을 직접 평가한 것은 아닙니다.<br><br>
        연구에 참여해주셔서 진심으로 감사합니다.<br>
        <b>이 화면은 자동으로 닫히지 않으니, 브라우저 탭을 직접 닫아주세요.</b>
    </div>
    """, unsafe_allow_html=True)
