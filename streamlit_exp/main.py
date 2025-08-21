# ──────────────────────────────────────────────────────────────────────────────
# 필요한 모듈
import streamlit as st
import streamlit.components.v1 as components
import time, random, json, os
from datetime import datetime
from utils.validation import validate_phone, validate_text
from utils.save_data import save_to_csv

# 페이지 설정 (가장 먼저 호출)
st.set_page_config(page_title="AI 칭찬 연구 설문", layout="centered")

# 경로 상수
BASE_DIR = os.path.dirname(__file__)

# ──────────────────────────────────────────────────────────────────────────────
# 전역 스타일: 상단 UI 제거 + 상단/하단 패딩 축소 + 제목 마진 정리
st.markdown("""
<style>
/* 스트림릿 기본 UI 제거 (공간까지 없앰) */
#MainMenu, header, footer { display: none !important; }

/* 컨테이너 상단/하단 패딩 축소 (버전별 선택자 모두 커버) */
[data-testid="stAppViewContainer"] > .main > div,
.main .block-container,
section.main > div.block-container {
  padding-top: 6px !important;   /* 필요시 0~12px로 조정 */
  padding-bottom: 24px !important;
}

/* 루트 상단 패딩/마진 방지 */
.stApp { padding-top: 0 !important; }

/* 제목 마진 최적화 */
h1, .stMarkdown h1 {
  margin-top: 4px !important;
  margin-bottom: 12px !important;
  line-height: 1.2;
}
h2, .stMarkdown h2 {
  margin-top: 8px !important;
  margin-bottom: 8px !important;
}
</style>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────────────────
# 공통: 스크롤 항상 최상단 (components로 확실히 실행)
def scroll_top_js():
    components.html(
        """
        <script>
        (function(){
          try {
            // Streamlit이 iframe 안/밖에 있을 수 있어 양쪽 모두 시도
            const parentSect = window.parent?.document?.querySelector('section.main');
            if (parentSect) parentSect.scrollTo({top:0, left:0, behavior:'instant'});
            const selfSect = document.querySelector('section.main');
            if (selfSect) selfSect.scrollTo({top:0, left:0, behavior:'instant'});
            window.parent?.scrollTo({top:0, left:0, behavior:'instant'});
            window.scrollTo({top:0, left:0, behavior:'instant'});
          } catch(e) {}
        })();
        </script>
        """,
        height=0,  # 화면 공간 차지하지 않음
    )

# ──────────────────────────────────────────────────────────────────────────────
# 상태 초기화
if "phase" not in st.session_state:
    st.session_state.phase = "start"
    st.session_state.data = {}
    st.session_state.current_kw_index = 0
    st.session_state.writing_answers = []
    st.session_state.feedback_set_key = random.choice(["set1", "set2"])

# ──────────────────────────────────────────────────────────────────────────────
# 피드백 세트 로드 (안전 로드 + 폴백)
feedback_path = os.path.join(BASE_DIR, "data", "feedback_sets.json")
try:
    with open(feedback_path, "r", encoding="utf-8") as f:
        feedback_sets = json.load(f)
    # 최소 형태 검증
    if not isinstance(feedback_sets, dict) or not feedback_sets:
        raise ValueError("feedback_sets.json 형식이 올바르지 않습니다.")
except Exception as e:
    # 폴백 세트(간단 문구)로라도 앱이 멈추지 않도록 처리
    st.warning(f"피드백 세트를 불러오지 못했습니다. 기본 세트를 사용합니다. (원인: {e})")
    feedback_sets = {
        "set1": ["참여해 주셔서 감사합니다. 추론 과정에서의 꾸준한 시도가 인상적이었습니다."],
        "set2": ["핵심 단서를 파악하고 일관된 결론을 도출한 점이 돋보였습니다."]
    }
# ──────────────────────────────────────────────────────────────────────────────

# ──────────────────────────────────────────────────────────────────────────────
# COVNOX 로그 (EN)
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

# MCP 애니메이션 (정중앙)
def run_mcp_motion():
    st.markdown("""
        <style>
        .covnox-stage{
          min-height:92vh; display:flex; flex-direction:column;
          align-items:center; justify-content:center; gap:8px;
        }
        .covnox-title{ margin:0; text-align:center;
          font-size: clamp(26px, 5.2vw, 46px); font-weight:800;
        }
        .covnox-sub{
          font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
          font-size: clamp(12px, 2.4vw, 16px); opacity:.9; margin:6px 0 10px 0; text-align:center;
        }
        .covnox-bar{ width:min(920px, 92vw); margin-top:4px; }
        </style>
        <div class='covnox-stage'>
    """, unsafe_allow_html=True)

    # 로고(있으면)
    try:
        base_dir = os.getcwd()
        logo_path = os.path.join(base_dir, "covnox.png")
        if os.path.exists(logo_path):
            st.image(logo_path, width=80)
    except Exception:
        pass

    st.markdown("<h1 class='covnox-title'>🧩 COVNOX: Inference Pattern Analysis</h1>", unsafe_allow_html=True)

    log_placeholder = st.empty()
    progress = st.progress(0, text=None)

    start = time.time()
    total = 8.0
    step = 0
    while True:
        t = time.time() - start
        if t >= total: break
        progress.progress(min(t/total, 1.0), text=None)
        msg = fake_logs[step % len(fake_logs)]
        timestamp = time.strftime("%H:%M:%S")
        log_placeholder.markdown(f"<div class='covnox-sub'>[{timestamp}] {msg}</div>", unsafe_allow_html=True)
        step += 1
        time.sleep(0.4)

    progress.progress(1.0, text=None)
    st.markdown("</div>", unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────────────────
# 1. 연구 동의 페이지
if st.session_state.phase == "start":
    scroll_top_js()

    # ── 페이지 상단/하단 패딩 & 제목 마진 조정 ─────────────────────────────
    st.markdown("""
    <style>
      /* 메인 컨테이너 상단/하단 패딩 축소 */
      section.main > div.block-container, .main .block-container {
        padding-top: 6px !important;   /* 필요시 0~24px로 조정 */
        padding-bottom: 24px !important;
      }
      /* 큰 제목/부제목 위아래 마진 최적화 */
      h1, .stMarkdown h1 { 
        margin-top: 4px !important; 
        margin-bottom: 12px !important; 
        line-height: 1.2;
      }
      h2, .stMarkdown h2 { 
        margin-top: 10px !important; 
        margin-bottom: 8px !important; 
      }
    </style>
    """, unsafe_allow_html=True)
    # ────────────────────────────────────────────────────────────────────────

    # 제목 변경
    st.title("AI 에이전트의 칭찬 방식이 학습 동기에 미치는 영향 연구")

    if "consent_step" not in st.session_state:
        st.session_state.consent_step = "explain"

    EXPLAIN_IMG = os.path.join(BASE_DIR, "explane.png")
    AGREE_IMG   = os.path.join(BASE_DIR, "agree.png")
    PRIV_IMG    = os.path.join(BASE_DIR, "privinfo.png")

    if st.session_state.consent_step == "explain":
        st.subheader("연구대상자 설명문")
        if os.path.exists(EXPLAIN_IMG):
            st.image(EXPLAIN_IMG, use_container_width=True)
        else:
            st.info("설명문 이미지를 찾을 수 없습니다. 경로/파일명을 확인하세요.")

        st.markdown("<div style='height:12px;'></div>", unsafe_allow_html=True)
        if st.button("다음", key="consent_to_agree_btn", use_container_width=True):
            st.session_state.consent_step = "agree"
            st.rerun()

    elif st.session_state.consent_step == "agree":
        st.subheader("연구 동의서")
        if os.path.exists(AGREE_IMG):
            st.image(AGREE_IMG, use_container_width=True)
        else:
            st.info("연구 동의서 이미지를 찾을 수 없습니다. 경로/파일명을 확인하세요.")

        consent_research = st.radio("연구 참여에 동의하십니까?", ["동의함", "동의하지 않음"],
                                    horizontal=True, key="consent_research_radio")

        st.markdown("<div style='height:18px;'></div>", unsafe_allow_html=True)

        st.subheader("개인정보 수집·이용에 대한 동의")
        if os.path.exists(PRIV_IMG):
            st.image(PRIV_IMG, use_container_width=True)
        else:
            st.info("개인정보 동의 이미지를 찾을 수 없습니다. 경로/파일명을 확인하세요.")

        consent_privacy = st.radio("개인정보 수집·이용에 동의하십니까?", ["동의함", "동의하지 않음"],
                                   horizontal=True, key="consent_privacy_radio")

        st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
        st.divider()
        st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)

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
                    st.session_state.data.update({
                        "consent": "동의함",
                        "consent_research": consent_research,
                        "consent_privacy": consent_privacy,
                        "startTime": datetime.now().isoformat()
                    })
                    st.session_state.phase = "demographic"
                    st.rerun()


# ──────────────────────────────────────────────────────────────────────────────
# 1-1. 인적사항
elif st.session_state.phase == "demographic":
    scroll_top_js()

    logo_path = os.path.join(BASE_DIR, "logo.png")
    if os.path.exists(logo_path):
        st.image(logo_path, width=150)
    st.title("인적사항 입력")

    gender = st.radio("성별", ["남자", "여자"])
    age_group = st.selectbox("연령대", ["10대", "20대", "30대", "40대", "50대", "60대 이상"])

    if st.button("설문 시작"):
        if not gender or not age_group:
            st.warning("성별과 연령을 모두 입력해 주세요.")
        else:
            st.session_state.data.update({"gender": gender, "age": age_group})
            st.session_state.phase = "anthro"
            st.rerun()

# ──────────────────────────────────────────────────────────────────────────────
# 2. 의인화 척도 (10점 슬라이더) — 10문항 단위 페이지네이션
elif st.session_state.phase == "anthro":
    scroll_top_js()

    # 질문 로드
    anthro_path = os.path.join(BASE_DIR, "data", "questions_anthro.json")
    with open(anthro_path, encoding="utf-8") as f:
        questions = json.load(f)

    total_items = len(questions)  # 기대: 30
    page_size = 10
    total_pages = (total_items + page_size - 1) // page_size  # 30 -> 3

    # 페이지 상태 & 임시 응답 버퍼 초기화
    if "anthro_page" not in st.session_state:
        st.session_state["anthro_page"] = 1
    if "anthro_responses" not in st.session_state or len(st.session_state["anthro_responses"]) != total_items:
        # 전체 길이(30)로 0(미응답) 초기화
        st.session_state["anthro_responses"] = [0] * total_items

    page = st.session_state["anthro_page"]
    start_idx = (page - 1) * page_size
    end_idx = min(start_idx + page_size, total_items)
    slice_questions = questions[start_idx:end_idx]

    # 상단 안내(유지)
    st.markdown("""
        <style>
        .anthro-title{ text-align:center; font-weight:800;
           font-size:clamp(28px, 6vw, 56px); line-height:1.15; margin:8px 0 6px 0;}
        .scale-guide{ display:flex; justify-content:center; align-items:center; gap:12px;
           flex-wrap:wrap; text-align:center; font-size:clamp(14px, 2.8vw, 20px); line-height:1.6; margin-bottom:10px;}
        .scale-guide span{ white-space:nowrap; }
        .scale-note{ text-align:center; color:#9aa3ad; font-size:clamp(12px, 2.6vw, 16px);
           line-height:1.6; margin-bottom:18px;}
        .progress-note{ text-align:center; color:#6b7480; font-size:14px; margin-bottom:18px;}
        </style>
        <h2 class="anthro-title">의인화 척도 설문</h2>
        <div class="scale-guide">
          <span><b>1점</b>: 전혀 그렇지 않다</span><span>—</span>
          <span><b>5점</b>: 보통이다</span><span>—</span>
          <span><b>10점</b>: 매우 그렇다</span>
        </div>
        <div class="scale-note">※ 초깃값 0은 <b>“미응답”</b>을 의미합니다. 슬라이더를 움직여 1~10점 중 하나를 선택해 주세요.</div>
    """, unsafe_allow_html=True)

    # 진행도 표기 (예: 1페이지 1~10 / 총 30)
    st.markdown(
        f"<div class='progress-note'>문항 {start_idx+1}–{end_idx} / 총 {total_items}문항 (페이지 {page}/{total_pages})</div>",
        unsafe_allow_html=True
    )

    # 현재 페이지의 슬라이더 렌더링
    for local_i, q in enumerate(slice_questions, start=1):
        global_idx = start_idx + local_i - 1  # 0-based
        current_value = st.session_state["anthro_responses"][global_idx]
        # 고유 키는 전체 문항 번호 기반으로 (안정 유지)
        slider_key = f"anthro_{global_idx+1}"

        val = st.slider(
            label=f"{global_idx+1}. {q}",
            min_value=0,
            max_value=10,
            value=int(current_value) if isinstance(current_value, int) else 0,
            step=1,
            format="%d점",
            key=slider_key,
            help="0은 미응답을 의미합니다. 1~10점 중에서 선택해 주세요."
        )
        # 상태에 즉시 반영
        st.session_state["anthro_responses"][global_idx] = val
        st.markdown("<div style='margin-bottom:12px;'></div>", unsafe_allow_html=True)

    # 네비게이션 버튼 영역
    col_prev, col_info, col_next = st.columns([1, 2, 1])

    with col_prev:
        if page > 1:
            if st.button("← 이전"):
                st.session_state["anthro_page"] = page - 1
                st.rerun()

    with col_next:
        # 현재 페이지 유효성(모두 1~10 선택)
        current_slice = st.session_state["anthro_responses"][start_idx:end_idx]
        all_answered = all((v is not None and isinstance(v, int) and 1 <= v <= 10) for v in current_slice)

        if page < total_pages:
            # 중간 페이지: 다음 10문항으로
            if st.button("다음 →"):
                if not all_answered:
                    st.warning("현재 페이지 모든 문항을 1~10점 중 하나로 선택해 주세요. (0은 미응답)")
                else:
                    st.session_state["anthro_page"] = page + 1
                    st.rerun()
        else:
            # 마지막 페이지: 다음 단계로
            if st.button("다음 (추론 과제)"):
                # 마지막 페이지 슬라이스뿐 아니라 전체 검사 (안전)
                full_ok = all((v is not None and isinstance(v, int) and 1 <= v <= 10)
                              for v in st.session_state["anthro_responses"])
                if not full_ok:
                    st.warning("모든 문항을 1~10점 중 하나로 선택해 주세요. (0은 미응답)")
                else:
                    # 최종 저장 후 다음 단계
                    st.session_state.data["anthro_responses"] = st.session_state["anthro_responses"]
                    # 페이지 인덱스 초기화(재방문 대비)
                    st.session_state["anthro_page"] = 1
                    st.session_state.phase = "writing_intro"
                    st.rerun()


# ──────────────────────────────────────────────────────────────────────────────
# 2-1. 추론 과제 지시문
elif st.session_state.phase == "writing_intro":
    scroll_top_js()

    st.markdown("<h2 style='text-align:center; font-weight:bold;'>추론 기반 객관식 과제 안내</h2>", unsafe_allow_html=True)
    st.markdown("""
    이번 단계에서는 **이누이트 언어(Inuktut-like)**의 간단한 규칙을 읽고,  
    총 **10개**의 객관식 문항에 답하는 **추론 과제**를 수행합니다.

    이 과제의 목표는 **정답률 자체가 아니라 ‘낯선 규칙에서 끝까지 추론하려는 과정’**을 관찰하는 것입니다.  
    즉, 정답을 모두 맞추는 것보다 **단서를 찾고, 비교하고, 일관된 근거로 선택**하는 과정이 더 중요합니다.

    **진행 방식**
    1) 간단한 어휘/어법 규칙을 읽습니다.  
    2) 객관식 문항 10개에 **모두 응답**합니다. (정답보다 **추론 근거**가 중요)  
    3) 응답을 제출하면 딥러닝 기반 추론 패턴 분석을 진행합니다.  
    4) 딥러닝 기반 분석 후 AI의 피드백을 확인할 수 있습니다..

    **성실히 참여하면 좋아요**
    - 문항마다 ‘가장 그럴듯한’ 선택을 고르고, 가능하면 **적용한 규칙**을 함께 떠올려 보세요.  
    - **끝까지 응답을 완성**하는 것이 중요합니다. 빈 문항 없이 제출해 주세요.  
    - 오답이어도 괜찮습니다. **추론 경로**가 분석의 핵심입니다.
    """)
    if st.button("추론 과제 시작"):
        st.session_state.phase = "writing"
        st.rerun()

# ──────────────────────────────────────────────────────────────────────────────
# 3. 추론 기반 객관식 과제
elif st.session_state.phase == "writing":
    scroll_top_js()

    if "inference_started_ts" not in st.session_state:
        st.session_state.inference_started_ts = time.time()

    page = st.empty()
    with page.container():
        st.title("추론 과제 1/1 · 이누이트 언어 학습(Inuktut-like)")

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
                index=None
            )
            selections.append(choice)
            rationale = st.multiselect(
                f"문항 {i+1}에서 참고한 규칙(최소 1개 이상)",
                options=rationale_tags,
                key=f"mcq_rationale_{i}",
                help="최소 1개 이상 선택해야 제출할 수 있습니다."
            )
            rationales.append(rationale)

        # ---- 검증: ① 모든 문항 선택, ② 각 문항 근거 규칙 최소 1개 ----
        def validate_mcq(sel_list, rat_list):
            missing_sel = [i+1 for i, s in enumerate(sel_list) if s is None]
            missing_rat = [i+1 for i, r in enumerate(rat_list) if not r]
            all_selected = (len(sel_list) == len(questions)) and not missing_sel
            all_rationale = (len(rat_list) == len(questions)) and not missing_rat
            return (all_selected and all_rationale), missing_sel, missing_rat

        if st.button("제출"):
            valid, miss_sel, miss_rat = validate_mcq(selections, rationales)
            if not valid:
                msgs = []
                if miss_sel:
                    msgs.append(f"미선택 문항: {', '.join(map(str, miss_sel))}")
                if miss_rat:
                    msgs.append(f"근거 규칙 미선택 문항: {', '.join(map(str, miss_rat))}")
                st.warning(" · ".join(msgs) if msgs else "모든 문항을 확인해 주세요.")
            else:
                selected_idx = [int(s) for s in selections]
                duration = int(time.time() - st.session_state.inference_started_ts)
                score = sum(int(selected_idx[i] == q["ans"]) for i, q in enumerate(questions))
                accuracy = round(score / len(questions), 3)

                # 세부 응답 저장(문항별 근거 포함)
                detail = [{
                    "q": questions[i]["q"],
                    "options": questions[i]["options"],
                    "selected_idx": selected_idx[i],
                    "correct_idx": int(questions[i]["ans"]),
                    "rationales": rationales[i]  # ✅ 각 문항 근거 최소 1개 보장
                } for i in range(len(questions))]

                st.session_state.inference_answers = detail
                st.session_state.inference_score = int(score)
                st.session_state.inference_duration_sec = duration

                # 🔸 저장 버퍼에 즉시 기록
                st.session_state.data["inference_answers"] = detail
                st.session_state.data["inference_score"] = int(score)
                st.session_state.data["inference_duration_sec"] = duration
                st.session_state.data["inference_accuracy"] = accuracy

                # 다음 단계
                page.empty()
                st.session_state["_mcp_started"] = False
                st.session_state["_mcp_done"] = False
                st.session_state.phase = "analyzing"
                st.rerun()


# ──────────────────────────────────────────────────────────────────────────────
# 4. MCP 분석 모션 (완전 분리)
elif st.session_state.phase == "analyzing":
    scroll_top_js()

    page = st.empty()
    with page.container():
        st.markdown("""
            <style>
            body { overflow-x:hidden; }
            .mcp-screen { min-height: 78vh; display:flex; align-items:center; justify-content:center; }
            .mcp-done-card {
                border: 2px solid #2E7D32; border-radius: 14px; padding: 28px;
                background: #F9FFF9; max-width: 820px; margin: 48px auto;
            }
            </style>
        """, unsafe_allow_html=True)

        # 1) 애니메이션 1회 실행
        if not st.session_state.get("_mcp_started", False):
            st.session_state["_mcp_started"] = True
            st.markdown("<div class='mcp-screen'>", unsafe_allow_html=True)
            run_mcp_motion()
            st.markdown("</div>", unsafe_allow_html=True)
            st.session_state["_mcp_done"] = True
            st.rerun()

        # 2) 완료 안내
        if st.session_state.get("_mcp_done", False):
            st.markdown("""
                <div class='mcp-done-card'>
                  <h2 style="text-align:center; color:#2E7D32; margin-top:0;">✅ 분석이 완료되었습니다</h2>
                  <p style="font-size:16px; line-height:1.7; color:#222; text-align:center; margin: 6px 0 0;">
                    COVNOX가 응답의 추론 패턴을 분석했습니다. <b>결과 보기</b>를 눌러 피드백을 확인하세요.
                  </p>
                </div>
            """, unsafe_allow_html=True)
            _, mid, _ = st.columns([1,2,1])
            with mid:
                if st.button("결과 보기", use_container_width=True):
                    page.empty()
                    st.session_state["_mcp_started"] = False
                    st.session_state["_mcp_done"] = False
                    st.session_state.phase = "ai_feedback"
                    st.rerun()

# ──────────────────────────────────────────────────────────────────────────────
# 5. AI 피드백
elif st.session_state.phase == "ai_feedback":
    scroll_top_js()

    st.success("AI 분석 완료!")

    feedback = random.choice(feedback_sets[st.session_state.feedback_set_key])

    # 정확 일치 구절 하이라이트(세트 문장 기반)
    highlight_words = [
        # set1(노력)
        "끝까지 답을 도출하려는 꾸준한 시도와 인내심",
        "여러 단서를 활용해 끊임없이 결론을 모색하려는 태도",
        "지속적인 탐색과 시도",
        "실패를 두려워하지 않고 반복적으로 추론을 시도한 흔적",
        "과정 중 발생한 시행착오를 극복하고 대안을 탐색한 노력",
        "여러 방법을 모색하고 끝까지 결론을 도출하려는 태도",
        # set2(능력)
        "단서를 빠르게 이해하고 논리적으로 연결하는 뛰어난 추론 능력",
        "여러 선택지 중 핵심 단서를 식별하고 일관된 결론으로 이끄는 분석적 사고력",
        "구조적 일관성을 유지하며 논리적 결론을 도출하는 추론 능력",
        "단서 간의 관계를 정확히 파악하고 체계적으로 연결하는 능력",
        "상황을 분석하고 적절한 결론을 선택하는 높은 수준의 판단력",
    ]
    for phrase in highlight_words:
        feedback = feedback.replace(phrase, f"<b style='color:#2E7D32;'>{phrase}</b>")

    feedback_with_breaks = feedback.replace("\n", "<br>")
    st.markdown(
        f"""
        <div style='border: 2px solid #4CAF50; border-radius: 12px; padding: 20px; background-color: #F9FFF9;'>
            <h2 style='text-align:center; color:#2E7D32; margin-bottom:10px;'>📢 AI 평가 결과</h2>
            <p style='font-size:16px; line-height:1.6; text-align:left; color:#333;'>{feedback_with_breaks}</p>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown("<div style='margin-top:30px;'></div>", unsafe_allow_html=True)
    if st.button("학습동기 설문으로 이동"):
        st.session_state.data["feedback_set"] = st.session_state.feedback_set_key
        st.session_state.phase = "motivation"
        st.rerun()

# ──────────────────────────────────────────────────────────────────────────────
# 6. 학습 동기 설문
elif st.session_state.phase == "motivation":
    scroll_top_js()

    st.markdown("<h2 style='text-align:center; font-weight:bold;'>학습동기 설문</h2>", unsafe_allow_html=True)

    # 가로 폭 축소 시 잘림 방지
    st.markdown("""
    <div style='display:flex; justify-content:center; align-items:center; gap:12px; flex-wrap:wrap;
                font-size:16px; margin-bottom:30px;'>
        <span style="white-space:nowrap;"><b>1점</b> : 전혀 그렇지 않다</span>
        <span>—</span>
        <span style="white-space:nowrap;"><b>3점</b> : 보통이다</span>
        <span>—</span>
        <span style="white-space:nowrap;"><b>5점</b> : 매우 그렇다</span>
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
        st.markdown("<div style='margin-bottom:20px;'></div>", unsafe_allow_html=True)

    if st.button("설문 완료"):
        if None in motivation_responses:
            st.warning("모든 문항에 응답해 주세요.")
        else:
            st.session_state.data["motivation_responses"] = motivation_responses
            st.session_state.phase = "phone_input"
            st.rerun()

# ──────────────────────────────────────────────────────────────────────────────
# 6-1. 휴대폰 번호 입력
elif st.session_state.phase == "phone_input":
    scroll_top_js()

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

# ──────────────────────────────────────────────────────────────────────────────
# 7. 완료 화면
elif st.session_state.phase == "result":
    scroll_top_js()

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
