# ──────────────────────────────────────────────────────────────────────────────
# 필요한 모듈
import streamlit as st
import time, random, json, os
from datetime import datetime
from utils.validation import validate_phone, validate_text  # 기존 유틸 사용

# ⚠️ save_to_csv는 gspread 미설치 환경에서 바로 import 시 오류가 날 수 있어
#    실제 저장 시점에 동적 import + 로컬 폴백을 사용한다.
def save_to_csv_safe(data: dict):
    try:
        from utils.save_data import save_to_csv  # 지연 import
        return save_to_csv(data)
    except Exception as e:
        # 로컬 테스트 폴백: JSONL로 저장
        base_dir = os.path.dirname(__file__)
        path = os.path.join(base_dir, "local_results.jsonl")
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(data, ensure_ascii=False) + "\n")
        return None

# 페이지 설정 (가장 먼저 호출)
st.set_page_config(page_title="AI 칭찬 연구 설문", layout="centered")

# 경로 상수
BASE_DIR = os.path.dirname(__file__)

# ──────────────────────────────────────────────────────────────────────────────
# 전역 스타일: 상단 UI 제거 + 상단/하단 패딩 완전 제거 + 제목/문단 마진 정리
COMPACT_CSS = """
<style>
#MainMenu, header, footer, [data-testid="stToolbar"] { display: none !important; }
:root{
  --block-container-padding-top: 0rem !important;
  --block-container-padding: 0rem 1rem 1.25rem !important;
}
html, body,
.stApp,
[data-testid="stAppViewContainer"],
[data-testid="stAppViewContainer"] > .main,
section.main { margin-top:0 !important; padding-top:0 !important; }
[data-testid="stAppViewContainer"] > .main > div,
.main .block-container,
section.main > div.block-container {
  padding-top:0 !important; padding-bottom:20px !important;
}
h1, .stMarkdown h1 { margin-top:0 !important; margin-bottom:12px !important; line-height:1.2; }
h2, .stMarkdown h2 { margin-top:0 !important; margin-bottom:10px !important; }
p, .stMarkdown p   { margin-top:0 !important; }
.anthro-title { margin-top:0 !important; }
html, body { overflow-x:hidden !important; }

/* 추론 문항 카드 */
.qcard{border:1px solid #2a2f35; border-radius:12px; padding:14px; background:#0f1115;}
.qhdr{font-weight:800; margin:0 0 8px; font-size:18px;}
.stem{font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      background:#171b22; border:1px solid #2a2f35; padding:10px 12px; border-radius:8px;}
.hint{color:#9aa3ad; font-size:13px; margin:8px 0 4px;}
.preview{background:#0b1a0f; border:1px solid #1e4428; color:#d9ffdf; padding:10px 12px; border-radius:8px;}
.sec-title{font-size:14px; font-weight:700; margin:10px 0 6px;}
.req{color:#66ff9c; font-weight:700; margin-left:6px; font-size:12px;}

/* MCP 전용 페이지(전체 화면 보장) */
.fullscreen-wrap{
  min-height: 88vh; display:flex; flex-direction:column;
  justify-content:center; align-items:center; gap:12px;
}
.covnox-title{ margin:0; text-align:center; font-size: clamp(28px, 5.4vw, 48px); font-weight:800; }
.covnox-sub{
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: clamp(12px, 2.4vw, 16px); opacity:.9; margin:6px 0 10px 0; text-align:center;
}
.mcp-done-card {
  border: 2px solid #2E7D32; border-radius: 14px; padding: 24px 20px;
  background: #F9FFF9; max-width: 820px; margin: 24px auto 10px;
}
.banner-ok{
  background:#0f3a17; color:#e6ffe6; border-radius:10px; padding:12px 14px;
  font-weight:700; margin:6px 0 12px; text-align:left;
}
.labelbox{
  border:2px solid #2E7D32; border-radius:12px; background:#F9FFF9; padding:12px 14px; margin:8px 0 12px;
  box-shadow:0 3px 10px rgba(46,125,50,.08);
}
.labelbox .label-hd{ font-weight:800; color:#1B5E20; font-size:15px; margin:0 0 6px 0; display:flex; gap:8px; align-items:center; }
.labelbox .label-bd{ color:#0f3a17; font-size:14.5px; line-height:1.65; }
.result-card{
  border:2px solid #4CAF50; border-radius:14px; padding:16px; background:#F9FFF9;
  box-shadow:0 6px 14px rgba(46,125,50,.08); animation: fadeUp .6s ease-out both;
}
.result-card h2{ text-align:left; margin:0 0 12px; color:#1B5E20; font-size:28px; }
@keyframes fadeUp{ from{opacity:0; transform:translateY(6px);} to{opacity:1; transform:none;} }
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
        <script id="goTop-{nonce}">
        (function(){{
          function goTop(){{
            try {{
              var pdoc = window.parent && window.parent.document;
              var sect = pdoc && pdoc.querySelector && pdoc.querySelector('section.main');
              if (sect && sect.scrollTo) sect.scrollTo({{top:0, left:0, behavior:'instant'}});
            }} catch(e) {{}}
            try {{
              window.scrollTo({{top:0, left:0, behavior:'instant'}});
              document.documentElement && document.documentElement.scrollTo && document.documentElement.scrollTo(0,0);
            }} catch(e) {{}}
          }}
          goTop(); if (window.requestAnimationFrame) requestAnimationFrame(goTop);
          setTimeout(goTop, 25); setTimeout(goTop, 80); setTimeout(goTop, 180); setTimeout(goTop, 320);
        }})();
        </script>
        """,
        unsafe_allow_html=True
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
    if not isinstance(feedback_sets, dict) or not feedback_sets:
        raise ValueError("feedback_sets.json 형식이 올바르지 않습니다.")
except Exception as e:
    st.warning(f"피드백 세트를 불러오지 못했습니다. 기본 세트를 사용합니다. (원인: {e})")
    feedback_sets = {
        "set1": ["참여해 주셔서 감사합니다. 추론 과정에서의 꾸준한 시도가 인상적이었습니다."],
        "set2": ["핵심 단서를 파악하고 일관된 결론을 도출한 점이 돋보였습니다."]
    }

# ──────────────────────────────────────────────────────────────────────────────
# MCP 로그
fake_logs = [
    "[INFO][COVNOX] Initializing… booting inference-pattern engine",
    "[INFO][COVNOX] Loading rule set: possessive(-mi), plural(-t), object(-ka), tense(-na/-tu), connector(ama)",
    "[INFO][COVNOX] Collecting responses… building choice cache",
    "[OK][COVNOX] Response hash constructed",
    "[INFO][COVNOX] Running grammatical marker detection",
    "[OK][COVNOX] Marker usage log: -mi/-t/-ka/-na/-tu/ama",
    "[INFO][COVNOX] Parsing rationale tags",
    "[OK][COVNOX] Rationale normalization complete",
    "[INFO][COVNOX] Computing rule-match consistency",
    "[OK][COVNOX] Consistency matrix updated",
    "[INFO][COVNOX] Testing elimination-of-incorrect-options strategy",
    "[OK][COVNOX] Comparison/contrast pattern detected",
    "[INFO][COVNOX] Checking tense/object conflicts",
    "[OK][COVNOX] No critical conflicts · reasoning path stable",
    "[INFO][COVNOX] Synthesizing overall inference profile",
    "[✔][COVNOX] Analysis complete. Rendering results…"
]

def run_mcp_motion_fullscreen(total: float = 8.0):
    """전용 페이지(전체 화면)에서만 보이는 MCP 애니메이션."""
    scroll_top_js()
    st.markdown("<div class='fullscreen-wrap'>", unsafe_allow_html=True)
    # 로고(있을 때만)
    try:
        logo_path = os.path.join(os.getcwd(), "covnox.png")
        if os.path.exists(logo_path):
            st.image(logo_path, width=86)
    except Exception:
        pass
    st.markdown("<h1 class='covnox-title'>🧩 COVNOX: Inference Pattern Analysis</h1>", unsafe_allow_html=True)

    log_placeholder = st.empty()
    bar_placeholder = st.empty()
    progress = bar_placeholder.progress(0, text=None)

    start = time.time()
    step = 0
    try:
        while True:
            t = time.time() - start
            if t >= total: break
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
        pass
    st.markdown("</div>", unsafe_allow_html=True)

def render_mcp_gate(next_phase: str, button_label: str = "결과 보기"):
    """애니메이션 완료 후 결과 버튼만 표시."""
    st.markdown("""
        <div class='mcp-done-card'>
          <h3 style="text-align:center; color:#2E7D32; margin:0 0 6px 0;">✅ 분석이 완료되었습니다</h3>
          <p style="font-size:16px; line-height:1.7; color:#222; text-align:center; margin:6px 0 0;">
            COVNOX가 응답의 추론 패턴을 분석했습니다. <b>결과 보기</b>를 눌러 피드백을 확인하세요.
          </p>
        </div>
    """, unsafe_allow_html=True)
    _, mid, _ = st.columns([1,2,1])
    with mid:
        if st.button(button_label, use_container_width=True):
            st.session_state.phase = next_phase
            st.rerun()

# ─────────────────────────────────────────────
# ① 연구대상자 설명문 / ② 연구 동의서 / ③ 개인정보 수집·이용 동의서
CONSENT_HTML = """
<div class="consent-wrap">
  <h1>연구대상자 설명문</h1>
  <div class="subtitle"><strong>제목: </strong>인공지능 에이전트의 피드백 방식이 학습에 미치는 영향 탐색 연구</div>
  <h2>1. 연구 목적</h2>
  <p>최근 과학기술의 발전과 함께 … (원문 그대로) …</p>
  <h2>2. 연구 참여 대상</h2>
  <p>…</p>
  <h2>3. 연구 방법</h2>
  <p>…</p>
  <h2>4. 연구 참여 기간</h2>
  <p>…</p>
  <h2>5. 연구 참여에 따른 이익 및 보상</h2>
  <p>…</p>
  <h2>6. 연구 과정에서의 부작용 또는 위험요소 및 조치</h2>
  <p>…</p>
  <h2>7. 개인정보와 비밀보장</h2>
  <p>…</p>
  <h2>8. 자발적 연구 참여와 중지</h2>
  <p>…</p>
</div>
""".strip()

AGREE_HTML = """
<div class="agree-wrap">
  <div class="agree-title">동 의 서</div>
  <p><strong>연구제목: </strong></p>
  <ol class="agree-list">
    <li><span class="agree-num">1.</span>나는 이 연구의 설명문을 읽고 충분히 이해하였습니다.</li>
    <li><span class="agree-num">2.</span>나는 이 연구에 참여함으로써 발생할 위험과 이득을 숙지하였습니다.</li>
    <li><span class="agree-num">3.</span>나는 이 연구에 자발적으로 동의합니다.</li>
    <li><span class="agree-num">4.</span>…</li>
    <li><span class="agree-num">5.</span>…</li>
    <li><span class="agree-num">6.</span>…</li>
  </ol>
</div>
""".strip()

PRIVACY_HTML = """
<div class="privacy-wrap">
  <h1>연구참여자 개인정보 수집∙이용 동의서</h1>
  <h2>[ 개인정보 수집∙이용에 대한 동의 ]</h2>
  <table class="privacy-table">
    <tr><th>수집하는<br>개인정보 항목</th><td>성별, 나이, 핸드폰 번호</td></tr>
    <tr><th>개인정보의<br>수집 및<br>이용목적</th>
      <td><p>연구수행 및 논문작성을 위한 활용</p></td></tr>
    <tr><th>개인정보의 <br>제3자 제공 및 목적 외 이용</th>
      <td>법령 또는 IRB 검증 목적</td></tr>
    <tr><th>보유 및 이용기간</th><td>연구종료 후 3년</td></tr>
  </table>
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
  @media (max-width:640px){ .consent-wrap, .agree-wrap, .privacy-wrap{ padding:14px 12px 18px; border-radius:10px; } }
  .consent-wrap h1, .privacy-wrap h1{ font-size:1.5em; margin:0 0 12px; font-weight:800; }
  .agree-wrap .agree-title{ font-weight:800; text-align:center; margin-bottom:12px; font-size:1.25em; }
  .privacy-table{ width:100%; border-collapse:collapse; table-layout:fixed; border:2px solid #111827; margin-bottom:14px; }
  .privacy-table th, .privacy-table td{ border:1px solid #111827; padding:10px 12px; vertical-align:top; }
  .privacy-table th{ width:30%; background:#F3F4F6; text-align:left; font-weight:700; }
  @media print{ .consent-wrap, .agree-wrap, .privacy-wrap{ border:none; max-width:100%; }
    .stSlider, .stButton, .stAlert{ display:none !important; } }
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

# ──────────────────────────────────────────────────────────────────────────────
# 2) 연구 동의 페이지
if st.session_state.phase == "start":
    scroll_top_js()
    st.title("AI 에이전트의 피드백 방식이 학습에 미치는 영향 탐색 연구")

    if "consent_step" not in st.session_state:
        st.session_state.consent_step = "explain"

    if st.session_state.consent_step == "explain":
        render_consent_doc()
        st.markdown("<div style='height:12px;'></div>", unsafe_allow_html=True)
        if st.button("다음", key="consent_to_agree_btn", use_container_width=True):
            st.session_state.consent_step = "agree"; st.rerun()

    elif st.session_state.consent_step == "agree":
        st.subheader("연구 동의서"); render_agree_doc()
        consent_research = st.radio("연구 참여에 동의하십니까?", ["동의함", "동의하지 않음"],
                                    horizontal=True, key="consent_research_radio")
        st.markdown("<div style='height:18px;'></div>", unsafe_allow_html=True)
        st.subheader("개인정보 수집·이용에 대한 동의"); render_privacy_doc()
        consent_privacy = st.radio("개인정보 수집·이용에 동의하십니까?", ["동의함", "동의하지 않음"],
                                   horizontal=True, key="consent_privacy_radio")
        st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True); st.divider()
        st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)

        st.markdown("""
        <style>.nav-row .stButton > button { width:100%; min-width:120px; }
        @media (max-width:420px){ .nav-row .stButton > button { min-width:auto; } }</style>
        """, unsafe_allow_html=True)
        st.markdown('<div class="nav-row">', unsafe_allow_html=True)
        left_col, right_col = st.columns([1, 1])
        with left_col:
            if st.button("이전", key="consent_prev_btn", use_container_width=True):
                st.session_state.consent_step = "explain"; st.rerun()
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
                    st.session_state.phase = "demographic"; st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────────────────
# 1-1. 인적사항
elif st.session_state.phase == "demographic":
    scroll_top_js()
    st.title("인적사항 입력")
    gender = st.radio("성별", ["남자", "여자"])
    age_group = st.selectbox("연령대", ["10대", "20대", "30대", "40대", "50대", "60대 이상"])
    if st.button("설문 시작"):
        if not gender or not age_group:
            st.warning("성별과 연령을 모두 입력해 주세요.")
        else:
            st.session_state.data.update({"gender": gender, "age": age_group})
            st.session_state.phase = "anthro"; st.rerun()

# ──────────────────────────────────────────────────────────────────────────────
# 2. 의인화 척도 (5점 리커트 라디오)
elif st.session_state.phase == "anthro":
    scroll_top_js()
    anthro_path = os.path.join(BASE_DIR, "data", "questions_anthro.json")
    with open(anthro_path, encoding="utf-8") as f:
        questions = json.load(f)
    total_items = len(questions)
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

    st.markdown("""
        <style>
        .anthro-title{ text-align:center; font-weight:800;
           font-size:clamp(28px, 6vw, 56px); line-height:1.15; margin:8px 0 6px 0;}
        .scale-guide{ display:flex; justify-content:center; align-items:center; gap:12px;
           flex-wrap:wrap; text-align:center; font-size:clamp(14px, 2.8vw, 20px); line-height:1.6; margin-bottom:10px;}
        </style>
        <h2 class="anthro-title">아래 문항은 개인의 경험과 인식을 알아보기 위한 것입니다. 본인의 평소 생각과 가까운 정도를 선택해 주세요.</h2>
        <div class="scale-guide">
          <span><b>1점</b>: 전혀 그렇지 않다</span><span>—</span>
          <span><b>3점</b>: 보통이다</span><span>—</span>
          <span><b>5점</b>: 매우 그렇다</span>
        </div>        
    """, unsafe_allow_html=True)

    st.markdown(
        f"<div style='text-align:center; color:#6b7480; margin-bottom:18px;'>문항 {start_idx+1}–{end_idx} / 총 {total_items}문항 (페이지 {page}/{total_pages})</div>",
        unsafe_allow_html=True
    )

    options = [1, 2, 3, 4, 5]
    for local_i, q in enumerate(slice_questions, start=1):
        global_idx = start_idx + local_i - 1
        current_value = st.session_state["anthro_responses"][global_idx]
        index_val = (options.index(current_value) if current_value in options else None)
        selected = st.radio(
            label=f"{global_idx+1}. {q}",
            options=options,
            index=index_val,
            format_func=lambda x: f"{x}점",
            horizontal=True,
            key=f"anthro_{global_idx+1}",
        )
        st.session_state["anthro_responses"][global_idx] = selected if selected in options else None
        st.markdown("<div style='margin-bottom:12px;'></div>", unsafe_allow_html=True)

    st.markdown("""
    <style>.nav-row .stButton > button { width:100%; min-width:120px; }
    @media (max-width: 420px){ .nav-row .stButton > button { min-width:auto; } }</style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="nav-row">', unsafe_allow_html=True)
    col_prev, col_info, col_next = st.columns([1, 2, 1])
    with col_prev:
        if page > 1:
            if st.button("← 이전", use_container_width=True, key="anthro_prev"):
                st.session_state["anthro_page"] = page - 1; st.rerun()
    with col_info:
        pass
    with col_next:
        current_slice = st.session_state["anthro_responses"][start_idx:end_idx]
        all_answered = all((v is not None and isinstance(v, int) and 1 <= v <= 5) for v in current_slice)
        if page < total_pages:
            if st.button("다음 →", use_container_width=True, key="anthro_next_mid"):
                if not all_answered:
                    st.warning("현재 페이지 모든 문항을 1~5점 중 하나로 선택해 주세요.")
                else:
                    st.session_state["anthro_page"] = page + 1; st.rerun()
        else:
            if st.button("다음", use_container_width=True, key="anthro_next_last"):
                full_ok = all((v is not None and isinstance(v, int) and 1 <= v <= 5)
                              for v in st.session_state["anthro_responses"])
                if not full_ok:
                    st.warning("모든 문항을 1~5점 중 하나로 선택해 주세요.")
                else:
                    st.session_state.data["anthro_responses"] = st.session_state["anthro_responses"]
                    st.session_state["anthro_page"] = 1
                    st.session_state.phase = "achive"; st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────────────────
# 2-1. 성취/접근 관련 설문(6점 리커트)
elif st.session_state.phase == "achive":
    scroll_top_js()
    st.markdown("<h2 style='text-align:center; font-weight:bold;'>아래 문항은 평소 본인의 성향을 알아보기 위한 문항입니다.</h2>", unsafe_allow_html=True)
    st.markdown("""
    <div style='display:flex; justify-content:center; align-items:center; gap:12px; flex-wrap:wrap;
                font-size:16px; margin-bottom:22px;'>
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

    total_items = len(achive_questions)
    page_size_list = [10, 10, max(0, total_items - 20)] if total_items >= 20 else [total_items]
    total_pages = len([s for s in page_size_list if s > 0])

    if "achive_page" not in st.session_state:
        st.session_state["achive_page"] = 1
    if "achive_responses" not in st.session_state or len(st.session_state["achive_responses"]) != total_items:
        st.session_state["achive_responses"] = [None] * total_items

    page = st.session_state["achive_page"]
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

    for gi in range(start_idx, end_idx):
        q = achive_questions[gi]
        choice = st.radio(
            label=f"{gi+1}. {q}",
            options=[1, 2, 3, 4, 5, 6],
            index=None,
            horizontal=True,
            key=f"achive_{gi}"
        )
        st.session_state["achive_responses"][gi] = choice
        st.markdown("<div style='margin-bottom:10px;'></div>", unsafe_allow_html=True)

    st.markdown("""
    <style>.nav-row .stButton > button { width:100%; min-width:120px; }
    @media (max-width:420px){ .nav-row .stButton > button{ min-width:auto; } }</style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="nav-row">', unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 2, 1])
    with c1:
        if page > 1:
            if st.button("← 이전", key="achive_prev", use_container_width=True):
                st.session_state["achive_page"] = page - 1; st.rerun()
    with c2:
        pass
    with c3:
        curr_slice = st.session_state["achive_responses"][start_idx:end_idx]
        all_answered = all(v in [1,2,3,4,5,6] for v in curr_slice)
        if page < total_pages:
            if st.button("다음 →", key="achive_next", use_container_width=True):
                if not all_answered:
                    st.warning("현재 페이지의 모든 문항에 1~6 중 하나를 선택해 주세요.")
                else:
                    st.session_state["achive_page"] = page + 1; st.rerun()
        else:
            if st.button("다음 (추론 과제 안내)", key="achive_done", use_container_width=True):
                full_ok = all(v in [1,2,3,4,5,6] for v in st.session_state["achive_responses"])
                if not full_ok:
                    st.warning("모든 문항에 응답해 주세요. (1~6)")
                else:
                    st.session_state.data["achive_responses"] = st.session_state["achive_responses"]
                    st.session_state["achive_page"] = 1
                    st.session_state.phase = "writing_intro"; st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────────────────
# 2-2. 추론 과제 지시문
elif st.session_state.phase == "writing_intro":
    scroll_top_js()
    st.markdown("<h2 style='text-align:center; font-weight:bold;'>추론 기반 객관식 과제 안내</h2>", unsafe_allow_html=True)
    st.markdown("""
    이번 단계에서는 **이누이트 언어(Inuktut-like)**의 규칙을 읽고,  
    총 **20개(명사 10, 동사 10)**의 **빈칸 채우기** 문항에 답합니다.

    - 각 문항은 **문장(빈칸)** ➜ **선택지(빈칸에 들어갈 말)** ➜ **완성 미리보기** ➜ **추론 근거(단일)** 순서로 구성됩니다.
    - 정답률보다 **일관된 추론 근거**가 중요합니다.
    """)
    if st.button("1회차 시작(명사구)"):
        st.session_state.phase = "inference_nouns"; st.rerun()

# ──────────────────────────────────────────────────────────────────────────────
# 3. 추론 기반 객관식 과제 (빈칸 채우기 + 근거 단일)
elif st.session_state.phase in ["inference_nouns", "inference_verbs"]:
    scroll_top_js()

    # 규칙 설명
    GRAMMAR_INFO_MD = r"""
**어휘 예시**  
- *ani* = 집,  *nuk* = 사람,  *sua* = 개,  *ika* = 물,  *pira* = 음식  
- *taku* = 보다,  *niri* = 먹다,  *siku* = 만들다

**명사구(NP) 규칙**  
A) **소유**: 명사 뒤 `-mi` → “~의” (예: *nuk-mi ani*)  
B) **복수**: `-t` (예: *nuk-t*). **복수 소유자**: `…-t-mi`. **복수 피소유**: 머리명사 `-t`.  
C) **사례(목적)**: **우측 결합** `-ka` (NP 말단, 등위 묶음의 **오른쪽 끝**).  
D) **어순**: 바깥 소유자 → 안쪽 소유자 → 머리명사.  
E) **정관**: `-ri`는 **NP 말단에서 `-ka` 앞**.

**동사 시제·상(TAM)**  
1) 시제: `-na`(현재) / `-tu`(과거) / `-ki`(미래)  
2) 상: `-mu`(완료) / `-li`(진행)  
3) 순서: **동사 + 상 + 시제** (예: *niri-mu-tu*, *taku-li-ki*).
"""

    REASON_NOUN = [
        "복수·소유 결합 순서(…-t-mi)",
        "우측 결합 사례표지(-ka)",
        "소유 연쇄 어순(바깥→안쪽→머리)",
        "정관(-ri) 위치(NP 말단, -ka 앞)",
        "등위 구조에서의 표지 배치"
    ]
    REASON_VERB = [
        "시제 단서 해석(어제/내일/항상 등)",
        "상(완료·진행) 단서 해석(이미/…하는 중)",
        "형태소 순서: 동사+상+시제",
        "‘…까지/후/전’에 따른 완료/진행 선택",
        "등위/연결문에서의 시제 일관성"
    ]

    def build_items_nouns():
        return [
            {"id":"N1","gloss":"‘사람들의 개의 집’(복수 소유자 + 소유 연쇄)",
             "stem":"____",
             "options":["nuk-t-mi sua-mi ani","nuk-mi-t sua-mi ani","nuk-mi sua-t-mi ani","nuk-t sua-mi ani","nuk-t-mi sua ani"],
             "answer_idx":0,"reason_idx":0},
            {"id":"N2","gloss":"‘집과 음식을 보다(현재)’ 목적 표시는 우측 결합.",
             "stem":"nuk ____ taku-na",
             "options":["ani ama pira-ka","ani-ka ama pira","ani ama pira","ani-ka ama pira-ka","ani-ri-ka ama pira"],
             "answer_idx":0,"reason_idx":1},
            {"id":"N3","gloss":"‘사람들의 집들(복수)을 본다’",
             "stem":"nuk ____ taku-na",
             "options":["nuk-t-mi ani-t-ka","nuk-mi-t ani-t-ka","nuk-t-mi ani-ka-t","nuk-t ani-t-ka","nuk-t-mi ani-t"],
             "answer_idx":0,"reason_idx":0},
            {"id":"N4","gloss":"‘사람의 개의 집’ 어순",
             "stem":"____",
             "options":["nuk-mi sua-mi ani","sua-mi nuk-mi ani","nuk sua-mi-mi ani","nuk-mi ani sua-mi","ani nuk-mi sua-mi"],
             "answer_idx":0,"reason_idx":2},
            {"id":"N5","gloss":"‘그 집(정관)을 보다’에서 -ri 위치",
             "stem":"nuk ____ taku-na",
             "options":["ani-ri-ka","ani-ka-ri","ri-ani-ka","ani-ri","ani-ka"],
             "answer_idx":0,"reason_idx":3},
            {"id":"N6","gloss":"‘사람과 개의 물’(각 소유자 표시)",
             "stem":"____",
             "options":["nuk-mi ama sua-mi ika","nuk ama sua-mi ika","nuk-mi ama sua ika","nuk ama sua ika-mi","nuk-mi sua-mi ama ika"],
             "answer_idx":0,"reason_idx":4},
            {"id":"N7","gloss":"‘개들의 물’(복수 소유자)",
             "stem":"____",
             "options":["sua-t-mi ika","sua-mi-t ika","sua-t ika-mi","sua ika-t-mi","sua-mi ika-t"],
             "answer_idx":0,"reason_idx":0},
            {"id":"N8","gloss":"‘사람들의 집들과 음식을 본다’ (등위 목적 묶음의 우측 결합)",
             "stem":"nuk ____ taku-na",
             "options":["nuk-t-mi ani-t ama pira-ka","nuk-t-mi ani-t-ka ama pira","nuk-t-mi ani ama pira-t-ka","nuk-mi-t ani-t ama pira-ka","nuk-t ami ani-t pira-ka"],
             "answer_idx":0,"reason_idx":1},
            {"id":"N9","gloss":"‘사람의 그 집을’(정관 뒤 사례)",
             "stem":"____",
             "options":["nuk-mi ani-ri-ka","nuk-mi-ri ani-ka","nuk-ri-mi ani-ka","nuk-mi ani-ka-ri","ani-ri nuk-mi-ka"],
             "answer_idx":0,"reason_idx":3},
            {"id":"N10","gloss":"‘사람의 개의 집과 물을 본다’(우측 결합)",
             "stem":"nuk ____ taku-na",
             "options":["nuk-mi sua-mi ani ama ika-ka","nuk-mi sua-mi ani-ka ama ika","nuk sua-mi-mi ani ama ika-ka","nuk-mi sua ani-mi ama ika-ka","nuk-mi sua-mi ama ani-ka ika"],
             "answer_idx":0,"reason_idx":4},
        ]

    def build_items_verbs():
        return [
            {"id":"V1","gloss":"현재진행: 사람이 집을 **보고 있는 중**",
             "stem":"nuk ani-ka ____",
             "options":["taku-li-na","taku-na","taku-mu-na","taku-li-ki","taku-tu"],
             "answer_idx":0,"reason_idx":1},
            {"id":"V2","gloss":"과거완료: 어제 저녁 전에 이미 **만들어 두었다**",
             "stem":"nuk pira-ka ____",
             "options":["siku-mu-tu","siku-tu","siku-li-tu","siku-mu-na","siku-ki"],
             "answer_idx":0,"reason_idx":4},
            {"id":"V3","gloss":"미래완료: 내일까지 다 **먹어 놓을 것이다**",
             "stem":"sua ika-ka ____",
             "options":["niri-mu-ki","niri-ki","niri-li-ki","niri-mu-na","niri-tu"],
             "answer_idx":0,"reason_idx":1},
            {"id":"V4","gloss":"단순 과거: 개가 음식을 **먹었다**",
             "stem":"sua pira-ka ____",
             "options":["niri-tu","niri-mu-tu","niri-li-tu","niri-na","niri-ki"],
             "answer_idx":0,"reason_idx":0},
            {"id":"V5","gloss":"현재완료: 사람은 물을 **이미 보았다**",
             "stem":"nuk ika-ka ____",
             "options":["taku-mu-na","taku-na","taku-tu","taku-li-na","taku-mu-tu"],
             "answer_idx":0,"reason_idx":1},
            {"id":"V6","gloss":"미래진행: 곧/내일 **보는 중일 것이다**",
             "stem":"nuk ama sua pira-ka ____",
             "options":["taku-li-ki","taku-ki","taku-li-na","taku-mu-ki","taku-tu"],
             "answer_idx":0,"reason_idx":0},
            {"id":"V7","gloss":"형태소 순서 규칙 확인",
             "stem":"sua ani-ka ____  (지금 보는 중)",
             "options":["taku-li-na","taku-na-li","li-taku-na","taku-na","taku-li-tu"],
             "answer_idx":0,"reason_idx":2},
            {"id":"V8","gloss":"‘…까지’ 단서 → 완료+미래",
             "stem":"nuk pira-ka ____",
             "options":["niri-mu-ki","niri-li-ki","niri-ki","niri-mu-tu","niri-na"],
             "answer_idx":0,"reason_idx":3},
            {"id":"V9","gloss":"항상 ~한다(단순 현재)",
             "stem":"nuk ika-ka ____",
             "options":["niri-na","niri-li-na","niri-mu-na","niri-tu","niri-ki"],
             "answer_idx":0,"reason_idx":0},
            {"id":"V10","gloss":"‘…한 뒤에’ → 선행사건 완료·과거 일관",
             "stem":"(ani-ka taku-mu-tu) ama pira-ka ____",
             "options":["niri-tu","niri-mu-tu","niri-li-tu","niri-na","niri-ki"],
             "answer_idx":0,"reason_idx":4},
        ]

    def _pick_samples(ans_detail, reason_labels, k=2):
        rng = random.Random((len(ans_detail)<<7) ^ 9173)
        picks = rng.sample(ans_detail, k=min(k, len(ans_detail)))
        return [f"Q{d['qno']}: {d['completed']} (이유: {reason_labels[d['reason_selected_idx']]})" for d in picks]

    def render_round(round_key:str, title:str, items_builder, reason_labels):
        st.title(title)
        with st.expander("📘 규칙(꼭 읽어주세요) · 힌트", expanded=True):
            st.markdown(GRAMMAR_INFO_MD)

        items = items_builder()
        if f"_{round_key}_start" not in st.session_state:
            st.session_state[f"_{round_key}_start"] = time.time()

        answers, reasons, completed_texts = [], [], []

        for idx, item in enumerate(items, start=1):
            with st.container():
                st.markdown(f"<div class='qcard'>", unsafe_allow_html=True)
                st.markdown(f"<div class='qhdr'>Q{idx}. {item['gloss']}</div>", unsafe_allow_html=True)
                st.markdown(f"<div class='sec-title'>문장(빈칸)</div>", unsafe_allow_html=True)
                st.markdown(f"<div class='stem'>{item['stem']}</div>", unsafe_allow_html=True)
                st.markdown(f"<div class='hint'>아래 선택지는 <b>빈칸(____)</b>에 들어갈 <b>한 개의 표현</b>입니다.</div>", unsafe_allow_html=True)

                sel = st.radio(
                    "선택지(빈칸에 들어갈 말 한 개 선택)", options=list(range(5)), index=None,
                    format_func=lambda i, opts=item["options"]: opts[i],
                    key=f"{round_key}_q{idx}_opt",
                )
                answers.append(sel)

                completed = None
                if sel is not None:
                    completed = item["stem"].replace("____", item["options"][sel])
                completed_texts.append(completed)

                st.markdown(f"<div class='sec-title'>내 선택 미리보기</div>", unsafe_allow_html=True)
                st.markdown(
                    f"<div class='preview'>{completed if completed else '선택지를 고르면 완성 문장이 표시됩니다.'}</div>",
                    unsafe_allow_html=True
                )

                reason = st.radio(
                    label=f"추론 근거(단일 선택) <span class='req'>(필수)</span>",
                    options=list(range(len(reason_labels))),
                    index=None,
                    format_func=lambda i: reason_labels[i],
                    key=f"{round_key}_q{idx}_reason",
                )
                reasons.append(reason)
                st.markdown("</div>", unsafe_allow_html=True)
                st.markdown("<div style='height:12px;'></div>", unsafe_allow_html=True)

        if st.button("제출"):
            if any(v is None for v in answers):
                st.warning("모든 문항의 ‘빈칸에 들어갈 말’을 선택해 주세요."); return False
            if any(v is None for v in reasons):
                st.warning("모든 문항의 ‘추론 근거(단일)’를 선택해 주세요."); return False

            elapsed = int(time.time() - st.session_state[f"_{round_key}_start"])
            score = 0; reason_score = 0; detail = []
            for i, item in enumerate(items):
                correct = (answers[i] == item["answer_idx"])
                if correct: score += 1
                if reasons[i] == item["reason_idx"]: reason_score += 1
                comp = (item["stem"].replace("____", item["options"][answers[i]])
                        if answers[i] is not None else item["stem"])
                detail.append({
                    "id": item["id"], "qno": i+1,
                    "stem": item["stem"], "gloss": item["gloss"],
                    "options": item["options"],
                    "selected_idx": int(answers[i]),
                    "selected_text": item["options"][answers[i]],
                    "correct_idx": int(item["answer_idx"]),
                    "correct_text": item["options"][item["answer_idx"]],
                    "completed": comp,
                    "reason_selected_idx": int(reasons[i]),
                    "reason_correct_idx": int(item["reason_idx"]),
                })

            st.session_state.data[round_key] = {
                "duration_sec": elapsed,
                "score": score,
                "reason_score": reason_score,
                "answers": detail
            }
            # ✅ 각 피드백 전에 전용 MCP 페이지로 이동
            st.session_state.phase = "analyzing_r1" if round_key=="inference_nouns" else "analyzing_r2"
            st.rerun()
        return False

    if st.session_state.phase == "inference_nouns":
        render_round("inference_nouns","추론 과제 1/2 (명사구: 빈칸 채우기)", build_items_nouns, REASON_NOUN)
    else:
        render_round("inference_verbs","추론 과제 2/2 (동사 TAM: 빈칸 채우기)", build_items_verbs, REASON_VERB)

# ──────────────────────────────────────────────────────────────────────────────
# MCP 전용 페이지들 (피드백 앞에 항상 등장)
elif st.session_state.phase in ["analyzing_r1", "analyzing_r2", "analyzing_final"]:
    scroll_top_js()
    # 전체 화면 애니메이션만 렌더
    run_mcp_motion_fullscreen(total=8.0)

    # 각 단계별 다음 화면 결정
    if st.session_state.phase == "analyzing_r1":
        render_mcp_gate(next_phase="praise_r1", button_label="1회차 피드백 보기")
    elif st.session_state.phase == "analyzing_r2":
        render_mcp_gate(next_phase="praise_r2", button_label="2회차 피드백 보기")
    else:
        render_mcp_gate(next_phase="ai_feedback", button_label="최종 평가 보기")

# ──────────────────────────────────────────────────────────────────────────────
# 라운드별 칭찬 피드백
elif st.session_state.phase in ["praise_r1", "praise_r2"]:
    scroll_top_js()

    def _pick_samples(ans_detail, reason_labels, k=2):
        rng = random.Random((len(ans_detail)<<7) ^ 9173)
        picks = rng.sample(ans_detail, k=min(k, len(ans_detail)))
        return [f"Q{d['qno']}: {d['completed']} (이유: {reason_labels[d['reason_selected_idx']]})" for d in picks]

    if st.session_state.phase == "praise_r1":
        REASON_NOUN = [
            "복수·소유 결합 순서(…-t-mi)", "우측 결합 사례표지(-ka)", "소유 연쇄 어순(바깥→안쪽→머리)",
            "정관(-ri) 위치(NP 말단, -ka 앞)", "등위 구조에서의 표지 배치"
        ]
        result = st.session_state.data.get("inference_nouns", {})
        score = result.get("score",0); reason_score = result.get("reason_score",0); dur = result.get("duration_sec",0)
        samples = _pick_samples(result.get("answers",[]), REASON_NOUN, k=2)
        st.markdown("### ✅ AI 칭찬 피드백(1회차·명사구)")
        st.success(
            f"복수·소유(…-t-mi), 우측 결합 사례(-ka), 정관(-ri) 위치를 잘 적용했습니다. "
            f"정답 {score}/10 · 이유 {reason_score}/10 · {dur}초. 샘플: {', '.join(samples)}"
        )
        if st.button("다음(2회차 시작)", use_container_width=True):
            st.session_state.phase = "inference_verbs"; st.rerun()

    else:
        REASON_VERB = [
            "시제 단서 해석(어제/내일/항상 등)", "상(완료·진행) 단서 해석(이미/…하는 중)",
            "형태소 순서: 동사+상+시제", "‘…까지/후/전’에 따른 완료/진행 선택", "등위/연결문에서의 시제 일관성"
        ]
        result = st.session_state.data.get("inference_verbs", {})
        score = result.get("score",0); reason_score = result.get("reason_score",0); dur = result.get("duration_sec",0)
        samples = _pick_samples(result.get("answers",[]), REASON_VERB, k=2)
        st.markdown("### ✅ AI 칭찬 피드백(2회차·동사 TAM)")
        st.success(
            f"시제 단서와 상(-mu/-li)의 매핑, ‘동사+상+시제’ 순서를 안정적으로 적용했습니다. "
            f"정답 {score}/10 · 이유 {reason_score}/10 · {dur}초. 샘플: {', '.join(samples)}"
        )
        if st.button("다음(최종 분석 애니메이션)", use_container_width=True):
            st.session_state.phase = "analyzing_final"; st.rerun()

# ──────────────────────────────────────────────────────────────────────────────
# 최종 AI 피드백(도넛 차트 + 서술)
elif st.session_state.phase == "ai_feedback":
    scroll_top_js()
    st.markdown("<div class='banner-ok'>AI 분석 완료!</div>", unsafe_allow_html=True)

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
    <div class="result-card" id="analysis-start"><h2>📊 추론 결과 분석</h2></div>
    """, unsafe_allow_html=True)

    labels = ["논리적 사고", "패턴 발견", "창의성", "주의 집중", "끈기"]
    CHART_PRESETS = {
        "set1": { "base": [18, 24, 20, 40, 36], "colors": ["#CDECCB","#7AC779","#B1E3AE","#5BAF5A","#92D091"]},
        "set2": { "base": [32, 36, 38, 18, 24], "colors": ["#A5D6A7","#66BB6A","#81C784","#43A047","#2E7D32"]},
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
        fig = px.pie(values=values, names=labels, hole=0.55, color=labels, color_discrete_sequence=palette)
        fig.update_traces(textinfo="percent+label", hovertemplate="<b>%{label}</b><br>점수: %{value}점<extra></extra>",
                          marker=dict(line=dict(width=1, color="white")))
        fig.update_layout(height=340, margin=dict(l=10, r=10, t=10, b=10),
                          showlegend=True, legend=dict(orientation="h", y=-0.1),
                          uniformtext_minsize=12, uniformtext_mode="hide")
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False, "displaylogo": False})
    except Exception:
        st.info("시각화를 준비 중입니다.")

    # 서술 피드백
    feedback_path = os.path.join(BASE_DIR, "data", "feedback_sets.json")
    try:
        with open(feedback_path, "r", encoding="utf-8") as f:
            fs = json.load(f)
        if not isinstance(fs, dict) or not fs: raise ValueError
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

    if st.button("학습동기 설문으로 이동"):
        st.session_state.data["feedback_set"] = set_key
        st.session_state.phase = "motivation"; st.rerun()

# ──────────────────────────────────────────────────────────────────────────────
# 6. 학습 동기 설문
elif st.session_state.phase == "motivation":
    scroll_top_js()
    st.markdown("<h2 style='text-align:center; font-weight:bold;'>나의 생각과 가장 가까운 것을 선택해주세요.</h2>", unsafe_allow_html=True)
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
            st.session_state.phase = "phone_input"; st.rerun()

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

    if st.button("완료"):
        if phone.strip() and not validate_phone(phone):
            st.warning("올바른 형식이 아닙니다. (예: 010-1234-5678)")
        else:
            st.session_state.data["phone"] = phone.strip()
            st.session_state.data["endTime"] = datetime.now().isoformat()
            save_to_csv_safe(st.session_state.data)   # 안전 저장
            st.session_state.phase = "result"; st.rerun()

# ──────────────────────────────────────────────────────────────────────────────
# 7. 완료 화면
elif st.session_state.phase == "result":
    scroll_top_js()
    if "result_submitted" not in st.session_state:
        st.success("모든 과제가 완료되었습니다. 감사합니다!")
        st.write("연구에 참여해주셔서 감사합니다. 하단의 제출 버튼을 꼭 눌러주세요. 미제출시 답례품 제공이 어려울 수 있습니다.")
        if st.button("제출"):
            st.session_state.result_submitted = True; st.rerun()
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
