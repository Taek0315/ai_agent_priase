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
# 전역 스타일: 상단 UI 제거 + 상단/하단 패딩 완전 제거 + 제목/문단 마진 정리
COMPACT_CSS = """
<style>
/* 0) Streamlit 기본 UI 제거 (공간까지 없앰) */
#MainMenu, header, footer, [data-testid="stToolbar"] { display: none !important; }

/* 1) 최신 Streamlit은 block padding을 CSS 변수로도 관리 → 변수 자체를 0으로 */
:root{
  --block-container-padding-top: 0rem !important;
  --block-container-padding: 0rem 1rem 1.25rem !important; /* top right/left bottom */
}

/* 2) 상단 여백이 생길 수 있는 모든 래퍼에 top 패딩/마진 0 강제 */
html, body,
.stApp,
[data-testid="stAppViewContainer"],
[data-testid="stAppViewContainer"] > .main,
section.main {
  margin-top: 0 !important;
  padding-top: 0 !important;
}

/* 3) 실제 컨테이너(.block-container) top 패딩 제거(버전별 경로 모두) */
[data-testid="stAppViewContainer"] > .main > div,
.main .block-container,
section.main > div.block-container {
  padding-top: 0 !important;
  padding-bottom: 20px !important; /* 하단은 적당히 */
}

/* 4) 제목/문단 top 마진 정돈 */
h1, .stMarkdown h1 { margin-top: 0 !important; margin-bottom: 12px !important; line-height: 1.2; }
h2, .stMarkdown h2 { margin-top: 0 !important; margin-bottom: 10px !important; }
p, .stMarkdown p   { margin-top: 0 !important; }

/* 5) 사용자 정의 제목 클래스(anthro 등)도 상단 마진 제거 */
.anthro-title { margin-top: 0 !important; }

/* 6) 불필요한 수평 스크롤 방지 */
html, body { overflow-x: hidden !important; }

/* 7) 라디오 위젯 세부 안정화: 초기/선택 후 동일 높이 유지 */
[data-testid="stRadio"]{ padding: 0 !important; margin: 0 !important; }
[data-testid="stRadio"] > label{ margin-bottom: 0 !important; }
[data-testid="stRadio"] div[role="radiogroup"]{
  display:flex !important; gap:14px !important; flex-wrap:wrap !important; align-items:center !important;
  min-height: 34px; /* 선택 전/후 높이 동일화 */
}
/* 8) 문항 한 줄(row) 레이아웃 고정 */
.item-row{ padding:10px 0 12px; border-bottom: 1px solid #F3F4F6; }
.item-q{ font-weight: 500; line-height:1.6; }
.item-opts{ display:block; }
@media (max-width:720px){
  .item-row{ padding:10px 0 14px; }
}
</style>
"""
st.markdown(COMPACT_CSS, unsafe_allow_html=True)

# 스크롤 상단 함수
def scroll_top_js(nonce: int | None = None):
    try:
        if nonce is None:
            nonce = int(st.session_state.get("_scroll_nonce", 0))
        else:
            nonce = int(nonce)
    except Exception:
        nonce = 0
    st.session_state["_scroll_nonce"] = nonce

    html_tmpl = """
    <!-- nonce:$NONCE$ -->
    <div id="__scroll_top_anchor_$NONCE$"></div>
    <script>
    (function(){
      function goTop(){
        try{
          var el = document.getElementById("__scroll_top_anchor_$NONCE$");
          if (el && el.scrollIntoView) el.scrollIntoView(true);
          window.scrollTo(0, 0);
          if (document.documentElement) document.documentElement.scrollTop = 0;
          if (document.body) document.body.scrollTop = 0;
        }catch(e){}
        try{
          var pdoc = window.parent && window.parent.document;
          if (pdoc){
            var sect =
              pdoc.querySelector("section.main") ||
              pdoc.querySelector('[data-testid="stAppViewContainer"] .main') ||
              pdoc.querySelector('[data-testid="stAppViewContainer"]');
            if (sect){
              if (sect.scrollTo) sect.scrollTo(0, 0);
              else sect.scrollTop = 0;
            } else if (window.parent && window.parent.scrollTo){
              window.parent.scrollTo(0, 0);
            }
          }
        }catch(e){}
      }
      goTop();
      if (window.requestAnimationFrame) requestAnimationFrame(goTop);
      setTimeout(goTop, 50);
      setTimeout(goTop, 120);
      setTimeout(goTop, 240);
      setTimeout(goTop, 360);
    })();
    </script>
    """
    html = html_tmpl.replace("$NONCE$", str(nonce))
    components.html(html, height=0, scrolling=False)

def rerun_with_scroll_top():
    st.session_state["_scroll_nonce"] = int(st.session_state.get("_scroll_nonce", 0)) + 1
    try:
        st.rerun()
    except Exception:
        st.experimental_rerun()

# ──────────────────────────────────────────────────────────────────────────────
# 상태 초기화
if "phase" not in st.session_state:
    st.session_state.phase = "start"
    st.session_state.data = {}
    st.session_state.current_kw_index = 0
    st.session_state.writing_answers = []
    st.session_state.feedback_set_key = random.choice(["set1", "set2"])
    st.session_state["_scroll_nonce"] = 0

# ──────────────────────────────────────────────────────────────────────────────
# 피드백 세트 로드 (안전 로드 + 폴백)
feedback_path = os.path.join(BASE_DIR, "data", "feedback_sets.json")
try:
    with open(feedback_path, "r", encoding="utf-8") as f:
        feedback_sets = json.load(f)
    if not isinstance(feedback_sets, dict) or not feedback_sets:
        raise ValueError("feedback_sets.json 형식이 올바르지 않습니다.")
except Exception as e:
    st.warning(f"피드백 세트를 불러오지 못했습니다. 기본 세트를 사용합니다. (원인: {e})")
    feedback_sets = {
        "set1": ["참여해 주셔서 감사합니다. 추론 과정에서의 꾸준한 시도가 인상적이었습니다."],
        "set2": ["핵심 단서를 파악하고 일관된 결론을 도출한 점이 돋보였습니다."]
    }

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

# MCP 애니메이션
def run_mcp_motion():
    st.markdown("<div style='height:18vh;'></div>", unsafe_allow_html=True)
    st.markdown("""
        <style>
        .covnox-title{ margin:0; text-align:center;
          font-size: clamp(26px, 5.2vw, 46px); font-weight:800;
        }
        .covnox-sub{
          font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
          font-size: clamp(12px, 2.4vw, 16px); opacity:.9; margin:6px 0 10px 0; text-align:center;
        }
        </style>
    """, unsafe_allow_html=True)

    try:
        base_dir = os.getcwd()
        logo_path = os.path.join(base_dir, "covnox.png")
        if os.path.exists(logo_path):
            st.image(logo_path, width=80)
    except Exception:
        pass

    st.markdown("<h1 class='covnox-title'>🧩 COVNOX: Inference Pattern Analysis</h1>", unsafe_allow_html=True)

    holder = st.container()
    with holder:
        log_placeholder = st.empty()
        progress_placeholder = st.empty()
        progress = progress_placeholder.progress(0, text=None)

        start = time.time()
        total = 8.0
        step = 0

        try:
            while True:
                t = time.time() - start
                if t >= total:
                    break
                progress.progress(min(t/total, 1.0), text=None)
                msg = fake_logs[step % len(fake_logs)]
                timestamp = time.strftime("%H:%M:%S")
                log_placeholder.markdown(
                    f"<div class='covnox-sub'>[{timestamp}] {msg}</div>",
                    unsafe_allow_html=True
                )
                step += 1
                time.sleep(0.4)
            progress.progress(1.0, text=None)
        finally:
            progress_placeholder.empty()
            log_placeholder.empty()
            holder.empty()

# ─────────────────────────────────────────────
# 문서/동의서 HTML
CONSENT_HTML = """<div class="consent-wrap"><h1>연구대상자 설명문</h1> ... (생략 없이 기존 본문 사용) ... </div>""".replace(" ... (생략 없이 기존 본문 사용) ... ", """
  <div class="subtitle"><strong>제목: </strong>AI 에이전트의 피드백 방식이 학습에 미치는 영향 탐색 연구</div>
  <h2>1. 연구 목적</h2>
  <p>최근 과학기술의 발전과 함께 인공지능(AI)은 ...</p>
  <p>본 연구는 ... 시사점을 도출하고자 합니다.</p>
  <h2>2. 연구 참여 대상</h2>
  <p>참여 대상: 만 18세 이상 성인으로 한국어 사용자를 대상으로 합니다.</p>
  <p>단, 한국어 사용이 미숙하여 ... 제외됩니다.</p>
  <h2>3. 연구 방법</h2>
  <p>... 전체 10~15분 ...</p>
  <h2>4. 연구 참여 기간</h2>
  <p>... 1회 ...</p>
  <h2>5. 연구 참여에 따른 이익 및 보상</h2>
  <p>... 기프티콘 ...</p>
  <h2>6. 연구 과정에서의 부작용 또는 위험요소 및 조치</h2>
  <p>... 언제든 중단 ...</p>
  <h2>7. 개인정보와 비밀보장</h2>
  <p>... 3년 보관 ...</p>
  <h2>8. 자발적 연구 참여와 중지</h2>
  <p>... 자발적 참여 ...</p>
  <h2>* 연구 문의</h2>
  <p>가톨릭대학교 ...</p>
  <p>IRB 사무국: 02-2164-4827</p>
""")

AGREE_HTML = """
<div class="agree-wrap">
  <div class="agree-title">동 의 서</div>
  <p><strong>연구제목: </strong></p>
  <ol class="agree-list">
    <li><span class="agree-num">1.</span>나는 이 연구의 설명문을 읽고 충분히 이해하였습니다.</li>
    <li><span class="agree-num">2.</span>나는 이 연구에 참여함으로써 발생할 위험과 이득을 숙지하였습니다.</li>
    <li><span class="agree-num">3.</span>나는 이 연구에 참여하는 것에 대하여 자발적으로 동의합니다. </li>
    <li><span class="agree-num">4.</span>나는 이 연구에서 얻어진 나에 대한 정보를 현행 법률과 가톨릭대학교 성심교정 생명윤리심의위원회 규정이 허용하는 범위 내에서 연구자가 수집하고 처리하는데 동의합니다.</li>
    <li><span class="agree-num">5.</span>나는 담당 연구자나 위임 받은 대리인이 연구를 진행하거나 결과 관리를 하는 경우와 연구기관, 연구비지원기관 및 가톨릭대학교 성심교정 생명윤리심의위원회가 실태 조사를 하는 경우에는 비밀로 유지되는 나의 개인 신상 정보를 직접적으로 열람하는 것에 동의합니다.</li>
    <li><span class="agree-num">6.</span>나는 언제라도 이 연구의 참여를 철회할 수 있고 이러한 결정이 나에게 어떠한 해도 되지 않을 것이라는 것을 압니다. </li>
  </ol>
</div>
""".strip()

PRIVACY_HTML = """
<div class="privacy-wrap">
  <h1>연구참여자 개인정보 수집∙이용 동의서</h1>
  <h2>[ 개인정보 수집∙이용에 대한 동의 ]</h2>
  <table class="privacy-table">
    <tr><th>수집하는<br>개인정보 항목</th><td>성별, 나이, 핸드폰 번호</td></tr>
    <tr><th>개인정보의<br>수집 및<br>이용목적</th><td><p>제공하신 정보는 연구수행 및 논문작성 등을 위해서 사용합니다.</p><ol><li>연구수행: 성별, 나이, 핸드폰 번호</li><li>민감정보는 수집하지 않습니다.</li></ol></td></tr>
    <tr><th>개인정보의 <br>제3자 제공 및 목적 외 이용</th><td>법이 요구하거나 IRB가 연구자료를 열람할 수 있습니다.</td></tr>
    <tr><th>개인정보의<br>보유 및 이용기간</th><td>연구종료 후 3년 보관 후 파기합니다.</td></tr>
  </table>
  <p class="privacy-note">※ 동의 거부 가능하나, 미동의 시 연구 참여가 제한될 수 있습니다.</p>
  <ul class="privacy-bullets">
    <li>※ 동의한 목적 외 활용하지 않음</li>
    <li>※ 만 18세 미만은 법정대리인 동의 필요</li>
    <li>「개인정보보호법」에 의거 상기 내용에 동의함.</li>
  </ul>
</div>
""".strip()

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
# 공통: 안정형 리커트 문항 렌더 함수 (라벨/선택지 분리)
def render_likert_row(idx:int, text:str, options:list[int], key:str, current_val:int|None=None):
    """
    - 질문 텍스트와 라디오를 분리 렌더 → 선택 전후 위젯 높이 동일
    - 라디오 라벨 숨김(label_visibility='collapsed')
    - columns 고정 배치 + CSS로 radiogroup 높이/정렬 보정
    """
    with st.container():
        st.markdown('<div class="item-row">', unsafe_allow_html=True)
        qcol, rcol = st.columns([7,5])
        with qcol:
            st.markdown(f"<div class='item-q'>{idx}. {text}</div>", unsafe_allow_html=True)
        with rcol:
            index_val = options.index(current_val) if current_val in options else None
            selected = st.radio(
                label="",
                options=options,
                index=index_val,                   # 초기 미선택 허용
                horizontal=True,
                key=key,
                label_visibility="collapsed",
            )
        st.markdown("</div>", unsafe_allow_html=True)
    return selected

# ──────────────────────────────────────────────────────────────────────────────
# 2) 연구 동의 페이지
if st.session_state.phase == "start":
    scroll_top_js(st.session_state.get("_scroll_nonce"))

    st.title("AI 에이전트의 피드백 방식이 학습에 미치는 영향 탐색 연구")

    if "consent_step" not in st.session_state:
        st.session_state.consent_step = "explain"

    if st.session_state.consent_step == "explain":
        scroll_top_js(st.session_state.get("_scroll_nonce"))
        st.subheader("연구대상자 설명문")
        render_consent_doc()

        st.markdown("<div style='height:12px;'></div>", unsafe_allow_html=True)
        if st.button("다음", key="consent_to_agree_btn", use_container_width=True):
            st.session_state.consent_step = "agree"
            rerun_with_scroll_top()

    elif st.session_state.consent_step == "agree":
        scroll_top_js(st.session_state.get("_scroll_nonce"))
        st.subheader("연구 동의서")
        render_agree_doc()

        consent_research = st.radio(
            "연구 참여에 동의하십니까?",
            ["동의함", "동의하지 않음"],
            horizontal=True, key="consent_research_radio"
        )

        st.markdown("<div style='height:18px;'></div>", unsafe_allow_html=True)

        st.subheader("개인정보 수집·이용에 대한 동의")
        render_privacy_doc()

        consent_privacy = st.radio(
            "개인정보 수집·이용에 동의하십니까?",
            ["동의함", "동의하지 않음"],
            horizontal=True, key="consent_privacy_radio"
        )

        st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
        st.divider()
        st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)

        st.markdown("""
        <style>
        .nav-row .stButton > button { width: 100%; min-width: 120px; }
        @media (max-width: 420px){ .nav-row .stButton > button { min-width: auto; } }
        </style>
        """, unsafe_allow_html=True)

        st.markdown('<div class="nav-row">', unsafe_allow_html=True)
        left_col, right_col = st.columns([1, 1])

        with left_col:
            if st.button("이전", key="consent_prev_btn", use_container_width=True):
                st.session_state.consent_step = "explain"
                rerun_with_scroll_top()

        with right_col:
            if st.button("다음", key="consent_next_btn", use_container_width=True):
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
                    rerun_with_scroll_top()
        st.markdown('</div>', unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────────────────
# 1-1. 인적사항
elif st.session_state.phase == "demographic":
    scroll_top_js(st.session_state.get("_scroll_nonce"))

    st.title("인적사항 입력")

    gender = st.radio("성별", ["남자", "여자"])
    age_group = st.selectbox("연령대", ["10대", "20대", "30대", "40대", "50대", "60대 이상"])

    if st.button("설문 시작"):
        if not gender or not age_group:
            st.warning("성별과 연령을 모두 입력해 주세요.")
        else:
            st.session_state.data.update({"gender": gender, "age": age_group})
            st.session_state.phase = "anthro"
            rerun_with_scroll_top()

# ──────────────────────────────────────────────────────────────────────────────
# 2. 의인화 척도 (5점 리커트) — 10문항 단위 페이지네이션
elif st.session_state.phase == "anthro":
    scroll_top_js(st.session_state.get("_scroll_nonce"))

    # 질문 로드
    anthro_path = os.path.join(BASE_DIR, "data", "questions_anthro.json")
    with open(anthro_path, encoding="utf-8") as f:
        questions = json.load(f)

    total_items = len(questions)  # 기대: 30
    page_size = 10
    total_pages = (total_items + page_size - 1) // page_size  # 30 -> 3

    if "anthro_page" not in st.session_state:
        st.session_state["anthro_page"] = 1
    if "anthro_responses" not in st.session_state or len(st.session_state["anthro_responses"]) != total_items:
        st.session_state["anthro_responses"] = [None] * total_items

    page = st.session_state["anthro_page"]

    if st.session_state.get("_anthro_prev_page") != page:
        st.session_state["_anthro_prev_page"] = page
        scroll_top_js(st.session_state.get("_scroll_nonce"))

    start_idx = (page - 1) * page_size
    end_idx = min(start_idx + page_size, total_items)
    slice_questions = questions[start_idx:end_idx]

    st.markdown("""
        <style>
        .anthro-title{ text-align:center; font-weight:800;
           font-size:clamp(28px, 6vw, 56px); line-height:1.15; margin:8px 0 6px 0;}
        .scale-guide{ display:flex; justify-content:center; align-items:center; gap:12px;
           flex-wrap:wrap; text-align:center; font-size:clamp(14px, 2.8vw, 20px); line-height:1.6; margin-bottom:10px;}
        .scale-guide span{ white-space:nowrap; }
        .progress-note{ text-align:center; color:#6b7480; font-size:14px; margin-bottom:12px;}
        </style>
        <h2 class="anthro-title">아래에 제시되는 문항은 개인의 경험과 인식을 알아보기 위한 것입니다. 본인의 평소 생각에 얼마나 가까운지를 선택해 주세요.</h2>
        <div class="scale-guide">
          <span><b>1점</b>: 전혀 그렇지 않다</span><span>—</span>
          <span><b>3점</b>: 보통이다</span><span>—</span>
          <span><b>5점</b>: 매우 그렇다</span>
        </div>
    """, unsafe_allow_html=True)

    st.markdown(
        f"<div class='progress-note'>문항 {start_idx+1}–{end_idx} / 총 {total_items}문항 (페이지 {page}/{total_pages})</div>",
        unsafe_allow_html=True
    )

    options5 = [1, 2, 3, 4, 5]
    for local_i, q in enumerate(slice_questions, start=1):
        gi = start_idx + local_i - 1
        cur = st.session_state["anthro_responses"][gi]
        sel = render_likert_row(gi+1, q, options5, key=f"anthro_{gi}", current_val=cur)
        st.session_state["anthro_responses"][gi] = sel

    st.markdown("""
    <style>
    .nav-row .stButton > button { width: 100%; min-width: 120px; }
    @media (max-width: 420px){ .nav-row .stButton > button { min-width: auto; } }
    </style>
    """, unsafe_allow_html=True)

    with st.container():
        st.markdown('<div class="nav-row">', unsafe_allow_html=True)
        col_prev, col_info, col_next = st.columns([1, 2, 1])

        with col_prev:
            if page > 1:
                if st.button("← 이전", use_container_width=True, key="anthro_prev"):
                    st.session_state["anthro_page"] = page - 1
                    rerun_with_scroll_top()

        with col_info:
            pass

        with col_next:
            current_slice = st.session_state["anthro_responses"][start_idx:end_idx]
            all_answered = all((v in options5) for v in current_slice)

            if page < total_pages:
                if st.button("다음 →", use_container_width=True, key="anthro_next_mid"):
                    if not all_answered:
                        st.warning("현재 페이지 모든 문항을 1~5점 중 하나로 선택해 주세요.")
                    else:
                        st.session_state["anthro_page"] = page + 1
                        rerun_with_scroll_top()
            else:
                if st.button("다음", use_container_width=True, key="anthro_next_last"):
                    full_ok = all((v in options5) for v in st.session_state["anthro_responses"])
                    if not full_ok:
                        st.warning("모든 문항을 1~5점 중 하나로 선택해 주세요.")
                    else:
                        st.session_state.data["anthro_responses"] = st.session_state["anthro_responses"]
                        st.session_state["anthro_page"] = 1
                        st.session_state.phase = "achive"
                        rerun_with_scroll_top()
        st.markdown('</div>', unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────────────────
# 2-1. 성취/접근 관련 추가 설문(6점 리커트) — 10/10/6 페이지네이션
elif st.session_state.phase == "achive":
    scroll_top_js(st.session_state.get("_scroll_nonce"))

    st.markdown("<h2 style='text-align:center; font-weight:bold;'>아래에 제시되는 문항은 평소 본인의 성향을 알아보기 위한 문항입니다. 나의 성향과 얼마나 가까운지를 선택해 주세요.</h2>", unsafe_allow_html=True)
    st.markdown("""
    <div style='display:flex; justify-content:center; align-items:center; gap:12px; flex-wrap:wrap;
                font-size:16px; margin-bottom:16px;'>
        <span style="white-space:nowrap;"><b>1</b> : 전혀 그렇지 않다</span>
        <span>—</span>
        <span style="white-space:nowrap;"><b>3</b> : 보통이다</span>
        <span>—</span>
        <span style="white-space:nowrap;"><b>6</b> : 매우 그렇다</span>
    </div>
    """, unsafe_allow_html=True)

    achive_path = os.path.join(BASE_DIR, "data", "questions_achive.json")
    try:
        with open(achive_path, "r", encoding="utf-8") as f:
            achive_questions = json.load(f)
    except Exception as e:
        st.error(f"추가 설문 문항을 불러오지 못했습니다: {e}")
        achive_questions = []

    total_items = len(achive_questions)  # 기대: 26
    page_size_list = [10, 10, total_items - 20] if total_items >= 20 else [total_items]
    total_pages = len(page_size_list)

    if "achive_page" not in st.session_state:
        st.session_state["achive_page"] = 1
    if "achive_responses" not in st.session_state or len(st.session_state["achive_responses"]) != total_items:
        st.session_state["achive_responses"] = [None] * total_items

    page = st.session_state["achive_page"]

    if st.session_state.get("_achive_prev_page") != page:
        st.session_state["_achive_prev_page"] = page
        scroll_top_js(st.session_state.get("_scroll_nonce"))

    if page == 1:
        start_idx, end_idx = 0, min(10, total_items)
    elif page == 2:
        start_idx, end_idx = 10, min(20, total_items)
    else:
        start_idx, end_idx = 20, total_items

    st.markdown(
        f"<div style='text-align:center; color:#6b7480; margin-bottom:10px;'>문항 {start_idx+1}–{end_idx} / 총 {total_items}문항 (페이지 {page}/{total_pages})</div>",
        unsafe_allow_html=True
    )

    options6 = [1, 2, 3, 4, 5, 6]
    for gi in range(start_idx, end_idx):
        q = achive_questions[gi]
        cur = st.session_state["achive_responses"][gi]
        sel = render_likert_row(gi+1, q, options6, key=f"achive_{gi}", current_val=cur)
        st.session_state["achive_responses"][gi] = sel

    st.markdown("""
    <style>
    .nav-row .stButton > button { width: 100%; min-width: 120px; }
    @media (max-width: 420px){ .nav-row .stButton > button { min-width: auto; } }
    </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="nav-row">', unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 2, 1])

    with c1:
        if page > 1:
            if st.button("← 이전", key="achive_prev", use_container_width=True):
                st.session_state["achive_page"] = page - 1
                rerun_with_scroll_top()

    with c2:
        pass

    with c3:
        curr_slice = st.session_state["achive_responses"][start_idx:end_idx]
        all_answered = all(v in options6 for v in curr_slice)

        if page < total_pages:
            if st.button("다음 →", key="achive_next", use_container_width=True):
                if not all_answered:
                    st.warning("현재 페이지의 모든 문항에 1~6 중 하나를 선택해 주세요.")
                else:
                    st.session_state["achive_page"] = page + 1
                    rerun_with_scroll_top()
        else:
            if st.button("다음 (추론 과제 안내)", key="achive_done", use_container_width=True):
                full_ok = all(v in options6 for v in st.session_state["achive_responses"])
                if not full_ok:
                    st.warning("모든 문항에 응답해 주세요. (1~6)")
                else:
                    st.session_state.data["achive_responses"] = st.session_state["achive_responses"]
                    st.session_state["achive_page"] = 1
                    st.session_state.phase = "writing_intro"
                    rerun_with_scroll_top()
    st.markdown('</div>', unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────────────────
# 2-2. 추론 과제 지시문
elif st.session_state.phase == "writing_intro":
    scroll_top_js(st.session_state.get("_scroll_nonce"))

    st.markdown("<h2 style='text-align:center; font-weight:bold;'>추론 기반 객관식 과제 안내</h2>", unsafe_allow_html=True)
    st.markdown("""
    이번 단계에서는 **이누이트 언어(Inuktut-like)**의 간단한 규칙을 읽고,  
    총 **10개**의 객관식 문항에 답하는 **추론 과제**를 수행합니다.

    이 과제의 목표는 **정답률 자체가 아니라 ‘낯선 규칙에서 끝까지 추론하려는 과정’**을 관찰하는 것입니다.  
    즉, 정답을 모두 맞추는 것보다 **단서를 찾고, 비교하고, 일관된 근거로 선택**하는 과정이 더 중요합니다.

    **진행 방식**
    1) 간단한 어휘/어법 규칙을 읽습니다.  
    2) 객관식 문항 10개과 추론에 사용한 규칙에 **모두 응답**합니다.  
    3) 응답을 제출하면 딥러닝 기반 추론 패턴 분석을 진행합니다.  
    4) 분석 후 AI의 피드백을 확인할 수 있습니다.
    """)
    if st.button("추론 과제 시작"):
        st.session_state.phase = "writing"
        rerun_with_scroll_top()

# ──────────────────────────────────────────────────────────────────────────────
# 3. 추론 기반 객관식 과제
elif st.session_state.phase == "writing":
    scroll_top_js(st.session_state.get("_scroll_nonce"))

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
            st.caption("정답이 전부가 아닙니다. 규칙을 참고해 가장 그럴듯한 선택지를 고르세요.")
            choice = st.radio(
                label="",
                options=list(range(len(item["options"]))),
                format_func=lambda idx, opts=item["options"]: opts[idx],
                key=f"mcq_{i}",
                horizontal=False,
                index=None,
                label_visibility="collapsed",
            )
            selections.append(choice)
            rationale = st.multiselect(
                f"문항 {i+1}에서 참고한 규칙(최소 1개 이상)",
                options=rationale_tags,
                key=f"mcq_rationale_{i}",
                help="최소 1개 이상 선택해야 제출할 수 있습니다."
            )
            rationales.append(rationale)

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
                if miss_sel: msgs.append(f"미선택 문항: {', '.join(map(str, miss_sel))}")
                if miss_rat: msgs.append(f"근거 규칙 미선택 문항: {', '.join(map(str, miss_rat))}")
                st.warning(" · ".join(msgs) if msgs else "모든 문항을 확인해 주세요.")
            else:
                selected_idx = [int(s) for s in selections]
                duration = int(time.time() - st.session_state.inference_started_ts)
                score = sum(int(selected_idx[i] == q["ans"]) for i, q in enumerate(questions))
                accuracy = round(score / len(questions), 3)

                detail = [{
                    "q": questions[i]["q"],
                    "options": questions[i]["options"],
                    "selected_idx": selected_idx[i],
                    "correct_idx": int(questions[i]["ans"]),
                    "rationales": rationales[i]
                } for i in range(len(questions))]

                st.session_state.inference_answers = detail
                st.session_state.inference_score = int(score)
                st.session_state.inference_duration_sec = duration
                st.session_state.data["inference_answers"] = detail
                st.session_state.data["inference_score"] = int(score)
                st.session_state.data["inference_duration_sec"] = duration
                st.session_state.data["inference_accuracy"] = accuracy

                page.empty()
                st.session_state["_mcp_started"] = False
                st.session_state["_mcp_done"] = False
                st.session_state.phase = "analyzing"
                rerun_with_scroll_top()

# ──────────────────────────────────────────────────────────────────────────────
# 4. MCP 분석 모션
elif st.session_state.phase == "analyzing":
    scroll_top_js(st.session_state.get("_scroll_nonce"))
    page = st.empty()
    with page.container():
        st.markdown("""
            <style>
            body { overflow-x:hidden; }
            .mcp-done-card {
                border: 2px solid #2E7D32; border-radius: 14px; padding: 28px;
                background: #F9FFF9; max-width: 820px; margin: 48px auto;
            }
            </style>
        """, unsafe_allow_html=True)

        if not st.session_state.get("_mcp_started", False):
            st.session_state["_mcp_started"] = True
            run_mcp_motion()
            st.session_state["_mcp_done"] = True
            rerun_with_scroll_top()

        if st.session_state.get("_mcp_done", False):
            st.markdown("""
                <div class='mcp-done-card'>
                  <h2 style="text-align:center; color:#2E7D32; margin-top:0;">✅ 분석이 완료되었습니다</h2>
                  <p style="font-size:16px; line-height:1.7; color:#222; text-align:center; margin:6px 0 0;">
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
                    rerun_with_scroll_top()

# ──────────────────────────────────────────────────────────────────────────────
# 5. AI 피드백
elif st.session_state.phase == "ai_feedback":
    scroll_top_js(st.session_state.get("_scroll_nonce"))

    st.markdown("""
    <style>
      .banner-ok{
        background:#0f3a17; color:#e6ffe6; border-radius:10px; padding:12px 14px;
        font-weight:700; margin:6px 0 12px; text-align:left;
      }
      .labelbox{
        border: 2px solid #2E7D32; border-radius: 12px;
        background: #F9FFF9; padding: 12px 14px; margin: 8px 0 12px;
        box-shadow: 0 3px 10px rgba(46,125,50,.08);
      }
      .labelbox .label-hd{
        font-weight:800; color:#1B5E20; font-size:15px; margin:0 0 6px 0;
        display:flex; gap:8px; align-items:center;
      }
      .labelbox .label-bd{ color:#0f3a17; font-size:14.5px; line-height:1.65; }
      .result-card{
        border:2px solid #4CAF50; border-radius:14px; padding:16px; background:#F9FFF9;
        box-shadow:0 6px 14px rgba(46,125,50,.08);
        animation: fadeUp .6s ease-out both;
      }
      .result-card h2{ text-align:left; margin:0 0 12px; color:#1B5E20; font-size:28px; }
      @keyframes fadeUp{ from{opacity:0; transform:translateY(6px);} to{opacity:1; transform:none;} }
    </style>
    <div class="banner-ok">AI 분석 완료!</div>
    """, unsafe_allow_html=True)

    set_key = st.session_state.get("feedback_set_key", "set1")
    LABEL_MAP = {
        "set1": {"title": "뛰어난 노력", "desc": "추론 과정에서 성실히 노력한 흔적이 보입니다."},
        "set2": {"title": "뛰어난 능력", "desc": "추론 과정에서 뛰어난 추론 능력이 보입니다."}
    }
    label = LABEL_MAP.get(set_key, LABEL_MAP["set1"])

    st.markdown(f"""
    <div class="labelbox">
      <div class="label-hd">요약 결과</div>
      <div class="label-bd"><b>{label['title']}</b> — {label['desc']}</div>
    </div>
    <div class="result-card" id="analysis-start">
      <h2>📊 추론 결과 분석</h2>
    </div>
    """, unsafe_allow_html=True)

    labels = ["논리적 사고", "패턴 발견", "창의성", "주의 집중", "끈기"]
    CHART_PRESETS = {
        "set1": {"base": [18, 24, 20, 40, 36],
                 "colors": ["#CDECCB", "#7AC779", "#B1E3AE", "#5BAF5A", "#92D091"],},
        "set2": {"base": [32, 36, 38, 18, 24],
                 "colors": ["#A5D6A7", "#66BB6A", "#81C784", "#43A047", "#2E7D32"],},
    }
    preset = CHART_PRESETS.get(set_key, CHART_PRESETS["set1"])
    base = preset["base"]; palette = preset["colors"]

    if "chart_seed" not in st.session_state:
        st.session_state.chart_seed = random.randint(1_000, 9_999)
    rng = random.Random(st.session_state.chart_seed)
    jitter = [rng.randint(-2, 2) for _ in labels]
    values = [max(10, b + j) for b, j in zip(base, jitter)]

    try:
        import plotly.express as px
        fig = px.pie(values=values, names=labels, hole=0.55,
                     color=labels, color_discrete_sequence=palette)
        fig.update_traces(
            textinfo="percent+label",
            hovertemplate="<b>%{label}</b><br>점수: %{value}점<extra></extra>",
            marker=dict(line=dict(width=1, color="white"))
        )
        fig.update_layout(
            height=340, margin=dict(l=10, r=10, t=10, b=10),
            showlegend=True, legend=dict(orientation="h", y=-0.1),
            uniformtext_minsize=12, uniformtext_mode="hide"
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False, "displaylogo": False})
    except Exception:
        st.info("시각화를 준비 중입니다.")

    try:
        with open(feedback_path, "r", encoding="utf-8") as f:
            fs = json.load(f)
        if not isinstance(fs, dict) or not fs:
            raise ValueError
    except Exception:
        fs = {
            "set1": ["참여해 주셔서 감사합니다. 추론 과정에서의 꾸준한 시도가 인상적이었습니다."],
            "set2": ["핵심 단서를 파악하고 일관된 결론을 도출한 점이 돋보였습니다."]
        }

    feedback = random.choice(fs.get(set_key, fs["set1"]))
    for phrase in [
        "끝까지 답을 도출하려는 꾸준한 시도와 인내심",
        "여러 단서를 활용해 끊임없이 결론을 모색하려는 태도",
        "지속적인 탐색과 시도",
        "실패를 두려워하지 않고 반복적으로 추론을 시도한 흔적",
        "과정 중 발생한 시행착오를 극복하고 대안을 탐색한 노력",
        "여러 방법을 모색하고 끝까지 결론을 도출하려는 태도",
        "단서를 빠르게 이해하고 논리적으로 연결하는 뛰어난 추론 능력",
        "여러 선택지 중 핵심 단서를 식별하고 일관된 결론으로 이끄는 분석적 사고력",
        "구조적 일관성을 유지하며 논리적 결론을 도출하는 추론 능력",
        "단서 간의 관계를 정확히 파악하고 체계적으로 연결하는 능력",
        "상황을 분석하고 적절한 결론을 선택하는 높은 수준의 판단력",
    ]:
        feedback = feedback.replace(phrase, f"<b style='color:#2E7D32;'>{phrase}</b>")

    st.markdown(
        f"""
        <div class='result-card' style='margin-top:16px;'>
            <h2>📢 AI 평가 결과</h2>
            <p style='font-size:16px; line-height:1.7; color:#333; margin:0;'>{feedback.replace("\n","<br>")}</p>
        </div>
        """, unsafe_allow_html=True
    )

    st.markdown("&nbsp;", unsafe_allow_html=True)
    if st.button("학습동기 설문으로 이동"):
        st.session_state.data["feedback_set"] = set_key
        st.session_state.phase = "motivation"
        rerun_with_scroll_top()

# ──────────────────────────────────────────────────────────────────────────────
# 6. 학습 동기 설문 (5점 리커트, 안정 렌더)
elif st.session_state.phase == "motivation":
    scroll_top_js(st.session_state.get("_scroll_nonce"))

    st.markdown("<h2 style='text-align:center; font-weight:bold;'>나의 생각과 가장 가까운 것을 선택해주세요.</h2>", unsafe_allow_html=True)
    st.markdown("""
    <div style='display:flex; justify-content:center; align-items:center; gap:12px; flex-wrap:wrap;
                font-size:16px; margin-bottom:22px;'>
        <span style="white-space:nowrap;"><b>1점</b> : 전혀 그렇지 않다</span>
        <span>—</span>
        <span style="white-space:nowrap;"><b>3점</b> : 보통이다</span>
        <span>—</span>
        <span style="white-space:nowrap;"><b>5점</b> : 매우 그렇다</span>
    </div>
    """, unsafe_allow_html=True)

    motivation_q = [
        "이번 추론 과제와 비슷한 과제를 기회가 있다면 한 번 더 해보고 싶다.",
        "앞으로도 추론 과제가 있다면 참여할 의향이 있다.",
        "더 어려운 추론 과제가 주어져도 도전할 의향이 있다.",
        "추론 과제의 난이도가 높아져도 시도해 볼 의향이 있다.",
        "이번 과제를 통해 성취감을 느꼈다.",
        "추론 과제를 통해 새로운 시각이나 아이디어를 배울 수 있었다.",
        "이런 과제를 수행하는 것은 나의 추론 능력을 발전시키는 데 가치가 있다."
    ]

    if "motivation_responses" not in st.session_state:
        st.session_state["motivation_responses"] = [None]*len(motivation_q)

    options5 = [1,2,3,4,5]
    for i, q in enumerate(motivation_q, start=1):
        cur = st.session_state["motivation_responses"][i-1]
        sel = render_likert_row(i, q, options5, key=f"motivation_{i}", current_val=cur)
        st.session_state["motivation_responses"][i-1] = sel

    if st.button("설문 완료"):
        if any(v not in options5 for v in st.session_state["motivation_responses"]):
            st.warning("모든 문항에 응답해 주세요.")
        else:
            st.session_state.data["motivation_responses"] = st.session_state["motivation_responses"]
            st.session_state.phase = "phone_input"
            rerun_with_scroll_top()

# ──────────────────────────────────────────────────────────────────────────────
# 6-1. 휴대폰 번호 입력
elif st.session_state.phase == "phone_input":
    scroll_top_js(st.session_state.get("_scroll_nonce"))

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
            rerun_with_scroll_top()

# ──────────────────────────────────────────────────────────────────────────────
# 7. 완료 화면
elif st.session_state.phase == "result":
    scroll_top_js(st.session_state.get("_scroll_nonce"))

    if "result_submitted" not in st.session_state:
        st.success("모든 과제가 완료되었습니다. 감사합니다!")
        st.write("연구에 참여해주셔서 감사합니다. 하단의 제출 버튼을 꼭 눌러주세요. 미제출시 답례품 제공이 어려울 수 있습니다.")
        if st.button("제출"):
            st.session_state.result_submitted = True
            rerun_with_scroll_top()
    else:
        st.success("응답이 저장되었습니다.")
        st.markdown("""
        <div style='font-size:16px; padding-top:10px;'>
            설문 응답이 성공적으로 저장되었습니다.<br>
            <b>이 화면은 자동으로 닫히지 않으니, 브라우저 탭을 수동으로 닫아 주세요.</b><br><br>
            ※ 본 연구에서 제공된 AI의 평가는 사전에 생성된 예시 대화문으로, 
            귀하의 실제 추론 능력을 직접 평가한 것이 아님을 알려드립니다.
        </div>
        """, unsafe_allow_html=True)
