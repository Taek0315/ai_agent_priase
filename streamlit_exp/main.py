# ──────────────────────────────────────────────────────────────────────────────
# 필요한 모듈
import streamlit as st
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
section.main > div.block-container { padding-top:0 !important; padding-bottom:20px !important; }
h1, .stMarkdown h1 { margin-top:0 !important; margin-bottom:12px !important; line-height:1.2; }
h2, .stMarkdown h2 { margin-top:0 !important; margin-bottom:10px !important; }
p, .stMarkdown p   { margin-top:0 !important; }
.anthro-title { margin-top:0 !important; }
html, body { overflow-x:hidden !important; }
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
            try{{var p=window.parent?.document?.querySelector('section.main'); p?.scrollTo({{top:0,left:0,behavior:'instant'}})}}catch(e){{}}
            try{{window.scrollTo({{top:0,left:0,behavior:'instant'}})}}catch(e){{}}
          }}
          goTop(); if(window.requestAnimationFrame) requestAnimationFrame(goTop);
          setTimeout(goTop,25); setTimeout(goTop,80); setTimeout(goTop,180); setTimeout(goTop,320);
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
    st.session_state.feedback_set_key = random.choice(["set1", "set2"])
    st.session_state.praise_condition = random.choice(["정서+구체","계산+구체","정서+피상","계산+피상"])

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
    "[INFO][COVNOX] Loading rule set: possessive(-mi), plural(-t), object(-ka), tense(-na/-tu/-ki), aspect(-mu/-li)",
    "[INFO][COVNOX] Collecting responses… building choice cache",
    "[OK][COVNOX] Choice cache constructed",
    "[INFO][COVNOX] Running grammatical marker detection",
    "[OK][COVNOX] Marker usage: -mi/-t/-ka/-na/-tu/-ki/-mu/-li",
    "[INFO][COVNOX] Computing rule-match consistency",
    "[OK][COVNOX] Consistency matrix updated",
    "[INFO][COVNOX] Testing elimination-of-incorrect-options strategy",
    "[OK][COVNOX] Comparison/contrast pattern detected",
    "[INFO][COVNOX] Checking tense/aspect conflicts",
    "[OK][COVNOX] No critical conflicts · reasoning path stable",
    "[INFO][COVNOX] Analyzing response time (persistence index)",
    "[OK][COVNOX] Persistence index calculated",
    "[INFO][COVNOX] Natural language phrasing optimization",
    "[OK][COVNOX] Fluency/consistency checks passed",
    "[INFO][COVNOX] Preparing feedback delivery",
    "[✔][COVNOX] Analysis complete. Rendering results…"
]

def run_mcp_motion():
    # 중앙 여백
    st.markdown("<div style='height:10vh;'></div>", unsafe_allow_html=True)
    st.markdown("""
        <style>
          .covnox-title{ text-align:center; font-size: clamp(28px,4.8vw,56px); font-weight:800; margin:0; }
          .covnox-sub{ font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
                       font-size: clamp(12px,2.2vw,16px); opacity:.92; margin:10px 0 16px; text-align:center; }
        </style>
    """, unsafe_allow_html=True)
    st.markdown("<h1 class='covnox-title'>🧩 COVNOX: Inference Pattern Analysis</h1>", unsafe_allow_html=True)

    holder = st.container()
    with holder:
        log_ph = st.empty()
        bar = st.progress(0, text=None)
        start = time.time()
        total = 8.0
        i = 0
        try:
            while True:
                t = time.time() - start
                if t >= total: break
                bar.progress(min(t/total, 1.0), text=None)
                msg = fake_logs[i % len(fake_logs)]
                timestamp = time.strftime("%H:%M:%S")
                log_ph.markdown(f"<div class='covnox-sub'>[{timestamp}] {msg}</div>", unsafe_allow_html=True)
                i += 1
                time.sleep(0.4)
            bar.progress(1.0, text=None)
        finally:
            bar.empty()
            log_ph.empty()
            holder.empty()

# ─────────────────────────────────────────────
# 문서 HTML/CSS
CONSENT_HTML = """<div class="consent-wrap"> ... (생략 없이 기존 본문 유지) ... </div>"""
AGREE_HTML = """<div class="agree-wrap"> ... (생략 없이 기존 본문 유지) ... </div>"""
PRIVACY_HTML = """<div class="privacy-wrap"> ... (생략 없이 기존 본문 유지) ... </div>"""

# ※ 위 세 블록은 질문에 준 원본 그대로 길어서 보기 편하게 표시만 줄였습니다.
#    실제 적용 시엔 기존 본문 그대로 두세요.

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
  .agree-list li{ margin:10px 0; } .agree-num{ font-weight:800; margin-right:6px; } .inline-label{ font-weight:600; }
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
# 규칙/아이템 정의 (라운드 1: 명사구, 라운드 2: 동사 TAM)
GRAMMAR_INFO_MD = r"""
**어휘 예시**  
- *ani* = 집,  *nuk* = 사람,  *sua* = 개,  *ika* = 물,  *pira* = 음식  
- *taku* = 보다,  *niri* = 먹다,  *siku* = 만들다

**명사구(NP) 규칙**  
A) **소유**: 명사 뒤 `-mi` → “~의” (예: *nuk-mi ani* = 사람의 집)  
B) **복수**: 명사 뒤 `-t` (예: *nuk-t* = 사람들). 복수 소유자: `명사 + -t + -mi` (예: *nuk-t-mi*), 복수 피소유: 머리명사에 `-t` (예: *ani-t*).  
C) **사례(목적)**: **NP 오른쪽 끝**에만 `-ka`(우측 결합). 등위(*ama*) 묶음에도 마지막에만 `-ka`.  
D) **어순**: 바깥 소유자 → 안쪽 소유자 → 머리명사.  
E) **정관**: `-ri`는 **NP-말단에서 사례(-ka) 앞**. 예: *nuk-mi ani-ri-ka*.

**동사 시제·상(TAM) 규칙**  
1) 시제: `-na`(현재), `-tu`(과거), `-ki`(미래)  
2) 상: `-mu`(완료), `-li`(진행)  
3) 순서: **동사 + 상 + 시제** (예: *niri-mu-ki*, *taku-li-na*)  
4) 단서: 어제/이미/지금/내일/…까지 등은 상/시제를 선택하는 힌트.
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
    "등위·연결문에서의 시제 일관성"
]

def build_items_nouns():
    # stem은 '____' 빈칸 포함. options는 빈칸에 들어갈 표현(문장 일부 또는 전체).
    return [
        {"id":"N1","title":"‘사람들의 개의 집’(복수 소유자 + 소유 연쇄)","stem":"____",
         "options":["nuk-t-mi sua-mi ani","nuk-mi-t sua-mi ani","nuk-mi sua-t-mi ani","nuk-t sua-mi ani","nuk-t-mi sua ani"],"answer_idx":0,"reason_idx":0},
        {"id":"N2","title":"‘집과 음식을 보다(현재)’ 목적 표지는 어디에? (우측 결합)","stem":"nuk ____ taku-na",
         "options":["ani ama pira-ka","ani-ka ama pira","ani ama pira","ani-ka ama pira-ka","ani-ri-ka ama pira"],"answer_idx":0,"reason_idx":1},
        {"id":"N3","title":"‘사람들의 집들(복수)을 본다’","stem":"nuk ____ taku-na",
         "options":["nuk-t-mi ani-t-ka","nuk-mi-t ani-t-ka","nuk-t-mi ani-ka-t","nuk-t ani-t-ka","nuk-t-mi ani-t"],"answer_idx":0,"reason_idx":0},
        {"id":"N4","title":"‘사람의 개의 집’을 올바른 어순으로","stem":"____",
         "options":["nuk-mi sua-mi ani","sua-mi nuk-mi ani","nuk sua-mi-mi ani","nuk-mi ani sua-mi","ani nuk-mi sua-mi"],"answer_idx":0,"reason_idx":2},
        {"id":"N5","title":"‘그 집(정관)을 보다’에서 -ri 위치","stem":"nuk ____ taku-na",
         "options":["ani-ri-ka","ani-ka-ri","ri-ani-ka","ani-ri","ani-ka"],"answer_idx":0,"reason_idx":3},
        {"id":"N6","title":"‘사람과 개의 물’을 올바르게 (각 소유자 표시)","stem":"____",
         "options":["nuk-mi ama sua-mi ika","nuk ama sua-mi ika","nuk-mi ama sua ika","nuk ama sua ika-mi","nuk-mi sua-mi ama ika"],"answer_idx":0,"reason_idx":4},
        {"id":"N7","title":"‘개들의 물’(복수 소유자) 표기","stem":"____",
         "options":["sua-t-mi ika","sua-mi-t ika","sua-t ika-mi","sua ika-t-mi","sua-mi ika-t"],"answer_idx":0,"reason_idx":0},
        {"id":"N8","title":"‘사람들의 집들과 음식을 본다’ (우측 결합)","stem":"nuk ____ taku-na",
         "options":["nuk-t-mi ani-t ama pira-ka","nuk-t-mi ani-t-ka ama pira","nuk-t-mi ani ama pira-t-ka","nuk-mi-t ani-t ama pira-ka","nuk-t ami ani-t pira-ka"],"answer_idx":0,"reason_idx":1},
        {"id":"N9","title":"‘사람의 그 집을’(정관 뒤 사례) 형태","stem":"____",
         "options":["nuk-mi ani-ri-ka","nuk-mi-ri ani-ka","nuk-ri-mi ani-ka","nuk-mi ani-ka-ri","ani-ri nuk-mi-ka"],"answer_idx":0,"reason_idx":3},
        {"id":"N10","title":"‘사람의 개의 집과 물을 본다’ (우측 결합)","stem":"nuk ____ taku-na",
         "options":["nuk-mi sua-mi ani ama ika-ka","nuk-mi sua-mi ani-ka ama ika","nuk sua-mi-mi ani ama ika-ka","nuk-mi sua ani-mi ama ika-ka","nuk-mi sua-mi ama ani-ka ika"],"answer_idx":0,"reason_idx":4},
    ]

def build_items_verbs():
    return [
        {"id":"V1","title":"현재진행: 집을 **보고 있는 중**","stem":"nuk ani-ka ____",
         "options":["taku-li-na","taku-na","taku-mu-na","taku-li-ki","taku-tu"],"answer_idx":0,"reason_idx":1},
        {"id":"V2","title":"과거완료: 어제 전에 **만들어 두었다**","stem":"nuk pira-ka ____",
         "options":["siku-mu-tu","siku-tu","siku-li-tu","siku-mu-na","siku-ki"],"answer_idx":0,"reason_idx":4},
        {"id":"V3","title":"미래완료: 내일까지 다 **먹어 놓을 것이다**","stem":"sua ika-ka ____",
         "options":["niri-mu-ki","niri-ki","niri-li-ki","niri-mu-na","niri-tu"],"answer_idx":0,"reason_idx":1},
        {"id":"V4","title":"단순 과거: **먹었다**","stem":"sua pira-ka ____",
         "options":["niri-tu","niri-mu-tu","niri-li-tu","niri-na","niri-ki"],"answer_idx":0,"reason_idx":0},
        {"id":"V5","title":"현재완료: **이미 보았다**","stem":"nuk ika-ka ____",
         "options":["taku-mu-na","taku-na","taku-tu","taku-li-na","taku-mu-tu"],"answer_idx":0,"reason_idx":1},
        {"id":"V6","title":"미래진행: 곧 **보는 중일 것이다**","stem":"nuk ama sua pira-ka ____",
         "options":["taku-li-ki","taku-ki","taku-li-na","taku-mu-ki","taku-tu"],"answer_idx":0,"reason_idx":0},
        {"id":"V7","title":"형태소 순서 확인(진행+현재 vs 현재+진행)","stem":"sua ani-ka ____  (지금 보는 중)",
         "options":["taku-li-na","taku-na-li","li-taku-na","taku-na","taku-li-tu"],"answer_idx":0,"reason_idx":2},
        {"id":"V8","title":"완료+미래: ‘그때까지 다 ~해 둘 것이다’","stem":"nuk pira-ka ____",
         "options":["niri-mu-ki","niri-li-ki","niri-ki","niri-mu-tu","niri-na"],"answer_idx":0,"reason_idx":3},
        {"id":"V9","title":"단순 현재: **늘 마신다**","stem":"nuk ika-ka ____",
         "options":["niri-na","niri-li-na","niri-mu-na","niri-tu","niri-ki"],"answer_idx":0,"reason_idx":0},
        {"id":"V10","title":"선행사건 완료 후 과거: ‘집을 본 뒤에 음식을 **먹었다**’","stem":"(ani-ka taku-mu-tu) ama pira-ka ____",
         "options":["niri-tu","niri-mu-tu","niri-li-tu","niri-na","niri-ki"],"answer_idx":0,"reason_idx":4},
    ]

# ─────────────────────────────────────────────
# 공통 라운드 렌더러 (빈칸 채우기 + 근거 단일 선택, 미리보기 없음)
def render_round(round_key:str, title:str, items_builder, reason_labels):
    scroll_top_js()
    st.title(title)
    with st.expander("📘 과제 안내 · 규칙(꼭 읽어주세요)", expanded=True):
        st.markdown(GRAMMAR_INFO_MD)

    items = items_builder()
    if f"_{round_key}_start" not in st.session_state:
        st.session_state[f"_{round_key}_start"] = time.time()

    answers, reasons = [], []
    for idx, it in enumerate(items, start=1):
        st.markdown(f"### Q{idx}. {it['title']}")
        # 빈칸 표시(읽기 전용)
        st.text_input("문장(빈칸)", it["stem"], key=f"{round_key}_stem_{idx}", disabled=True)
        st.caption("아래 선택지는 **빈칸(____)** 에 들어갈 **한 개**의 표현입니다.")

        sel = st.radio(
            "선택지(빈칸에 들어갈 한 개 선택)",
            options=list(range(len(it["options"]))),
            index=None,
            format_func=lambda i, opts=it["options"]: opts[i],
            key=f"{round_key}_q{idx}_opt",
            horizontal=False
        )
        answers.append(sel)

        reason = st.radio(
            "추론 근거(단일 선택) *필수*",
            options=list(range(len(reason_labels))),
            index=None,
            format_func=lambda i: reason_labels[i],
            key=f"{round_key}_q{idx}_reason",
            horizontal=False
        )
        reasons.append(reason)
        st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)

    if st.button("제출"):
        if any(v is None for v in answers) or any(v is None for v in reasons):
            st.warning("모든 문항의 ‘선택’과 ‘근거’를 완료해 주세요.")
            return

        elapsed = int(time.time() - st.session_state[f"_{round_key}_start"])
        score, reason_score, detail = 0, 0, []
        for i, it in enumerate(items):
            correct = (answers[i] == it["answer_idx"])
            if correct: score += 1
            if reasons[i] == it["reason_idx"]: reason_score += 1
            detail.append({
                "id": it["id"], "qno": i+1,
                "stem": it["stem"], "title": it["title"],
                "options": it["options"],
                "selected_idx": int(answers[i]),
                "selected_text": it["options"][answers[i]],
                "correct_idx": int(it["answer_idx"]),
                "correct_text": it["options"][it["answer_idx"]],
                "reason_selected_idx": int(reasons[i]),
                "reason_correct_idx": int(it["reason_idx"]),
            })

        st.session_state.data[round_key] = {
            "duration_sec": elapsed,
            "score": score,
            "reason_score": reason_score,
            "answers": detail
        }
        # 라운드 종료 → MCP 애니메이션 단계로 이동(라운드별 1회만)
        st.session_state.phase = "analyzing_r1" if round_key=="inference_nouns" else "analyzing_r2"
        st.rerun()

# ─────────────────────────────────────────────
# MCP 애니메이션 화면(라운드별 1회만, 단독 페이지)
def render_analyzing(analysis_id:str, next_phase:str, button_label:str):
    scroll_top_js()
    key_started = f"_{analysis_id}_started"
    key_done = f"_{analysis_id}_done"

    st.empty()  # 페이지 클린업

    if not st.session_state.get(key_started, False):
        st.session_state[key_started] = True
        run_mcp_motion()
        st.session_state[key_done] = True
        st.rerun()

    # 완료 카드
    st.markdown("""
        <div style="border:2px solid #2E7D32;border-radius:14px;padding:24px;background:#F9FFF9;max-width:860px;margin:24px auto;">
          <h2 style="text-align:center;color:#2E7D32;margin:0 0 8px;">✅ 분석이 완료되었습니다</h2>
          <p style="text-align:center;margin:0;">COVNOX가 응답의 추론 패턴을 분석했습니다. 아래 버튼을 눌러 피드백을 확인하세요.</p>
        </div>
    """, unsafe_allow_html=True)
    _, c, _ = st.columns([1,2,1])
    with c:
        if st.button(button_label, use_container_width=True):
            # 다음 단계로 이동(애니메이션은 각 라운드 1회만)
            st.session_state[key_started] = False
            st.session_state[key_done] = False
            st.session_state.phase = next_phase
            st.rerun()

# ─────────────────────────────────────────────
# 피드백 화면(라운드 2회만)
def _pick_samples(ans_detail, reason_labels, k=2):
    rng = random.Random((len(ans_detail)<<7) ^ 9173)
    picks = rng.sample(ans_detail, k=min(k, len(ans_detail)))
    return [f"Q{d['qno']}: {d['selected_text']} (이유: {reason_labels[d['reason_selected_idx']]})" for d in picks]

def render_praise(round_key:str, round_no:int, reason_labels):
    scroll_top_js()
    cond = st.session_state.get("praise_condition","정서+구체")
    result = st.session_state.data.get(round_key, {})
    score = result.get("score",0)
    reason_score = result.get("reason_score",0)
    dur = result.get("duration_sec",0)
    detail = result.get("answers",[])
    samples = _pick_samples(detail, reason_labels, k=2)

    st.markdown("""
    <style>
      .banner-ok{background:#0f3a17;color:#e6ffe6;border-radius:10px;padding:12px 14px;font-weight:700;margin:6px 0 12px;text-align:left;}
      .result-card{border:2px solid #4CAF50;border-radius:14px;padding:16px;background:#F9FFF9;
                   box-shadow:0 6px 14px rgba(46,125,50,.08);}
      .result-card h2{margin:0 0 12px;color:#1B5E20;}
    </style>
    """, unsafe_allow_html=True)
    st.markdown("<div class='banner-ok'>AI 분석 완료!</div>", unsafe_allow_html=True)

    if round_key == "inference_nouns":
        if cond == "정서+구체":
            st.success(f"1회차(명사구) 좋았습니다! 정답 {score}/10, 이유 {reason_score}/10, 소요 {dur}초. 예: {', '.join(samples)}")
        elif cond == "계산+구체":
            st.info(f"[명사구 요약] 정답 {score}/10 · 이유 {reason_score}/10 · {dur}초. ‘-t-mi’ 결합/우측결합 사례표지 일치가 높습니다.")
        elif cond == "정서+피상":
            st.success("명사구 규칙을 일관되게 적용하려는 태도가 인상적이었습니다.")
        else:
            st.info("명사구 파트 저장 완료. 다음 라운드로 이동합니다.")
        if st.button("다음(2회차: 동사 TAM)", use_container_width=True):
            st.session_state.phase = "inference_verbs"
            st.rerun()
    else:
        if cond == "정서+구체":
            st.success(f"2회차(동사 TAM)도 좋습니다! 정답 {score}/10, 이유 {reason_score}/10, 소요 {dur}초. 예: {', '.join(samples)}")
        elif cond == "계산+구체":
            st.info(f"[TAM 요약] 정답 {score}/10 · 이유 {reason_score}/10 · {dur}초. ‘이미/…까지’→완료, ‘지금/곧’→진행 선택과 시제 매핑이 안정적입니다.")
        elif cond == "정서+피상":
            st.success("시간 단서와 사건 상태를 구분하는 판단이 전반적으로 매끄러웠습니다.")
        else:
            st.info("동사 파트 입력이 저장되었습니다. 다음 단계로 이동합니다.")
        if st.button("다음(학습동기 설문)", use_container_width=True):
            st.session_state.phase = "motivation"
            st.rerun()

# ──────────────────────────────────────────────────────────────────────────────
# 0) 동의
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
        consent_research = st.radio("연구 참여에 동의하십니까?", ["동의함", "동의하지 않음"], horizontal=True, key="consent_research_radio")
        st.markdown("<div style='height:18px;'></div>", unsafe_allow_html=True)
        st.subheader("개인정보 수집·이용에 대한 동의"); render_privacy_doc()
        consent_privacy = st.radio("개인정보 수집·이용에 동의하십니까?", ["동의함", "동의하지 않음"], horizontal=True, key="consent_privacy_radio")
        st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
        left, right = st.columns(2)
        with left:
            if st.button("이전", use_container_width=True):
                st.session_state.consent_step = "explain"; st.rerun()
        with right:
            if st.button("다음", use_container_width=True):
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

# 1) 인적사항
elif st.session_state.phase == "demographic":
    scroll_top_js()
    st.title("인적사항 입력")
    gender = st.radio("성별", ["남자","여자"])
    age_group = st.selectbox("연령대", ["10대","20대","30대","40대","50대","60대 이상"])
    if st.button("설문 시작"):
        if not gender or not age_group:
            st.warning("성별과 연령을 모두 입력해 주세요.")
        else:
            st.session_state.data.update({"gender":gender, "age":age_group})
            st.session_state.phase = "anthro"; st.rerun()

# 2) 의인화 척도(5점) 10개씩 3페이지
elif st.session_state.phase == "anthro":
    scroll_top_js()
    path = os.path.join(BASE_DIR, "data", "questions_anthro.json")
    with open(path, encoding="utf-8") as f: questions = json.load(f)
    total, page_size = len(questions), 10
    if "anthro_page" not in st.session_state: st.session_state.anthro_page = 1
    if "anthro_responses" not in st.session_state or len(st.session_state["anthro_responses"])!=total:
        st.session_state["anthro_responses"] = [None]*total

    page = st.session_state.anthro_page
    start, end = (page-1)*page_size, min(page*page_size, total)
    st.markdown(f"<div style='text-align:center;color:#6b7480;margin-bottom:10px;'>문항 {start+1}–{end} / 총 {total}문항 (페이지 {page}/{(total+page_size-1)//page_size})</div>", unsafe_allow_html=True)
    opts = [1,2,3,4,5]
    for gi in range(start, end):
        idx_val = (opts.index(st.session_state["anthro_responses"][gi]) if st.session_state["anthro_responses"][gi] in opts else None)
        sel = st.radio(f"{gi+1}. {questions[gi]}", options=opts, index=idx_val, format_func=lambda x:f"{x}점", horizontal=True, key=f"anthro_{gi}")
        st.session_state["anthro_responses"][gi] = sel if sel in opts else None
        st.markdown("<div style='margin-bottom:10px;'></div>", unsafe_allow_html=True)

    left, right = st.columns(2)
    with left:
        if page>1 and st.button("← 이전", use_container_width=True):
            st.session_state.anthro_page -= 1; st.rerun()
    with right:
        current_slice = st.session_state["anthro_responses"][start:end]
        ok = all((v in opts) for v in current_slice)
        if page*page_size < total:
            if st.button("다음 →", use_container_width=True):
                if not ok: st.warning("현재 페이지 모든 문항을 1~5점 중 하나로 선택해 주세요.")
                else: st.session_state.anthro_page += 1; st.rerun()
        else:
            if st.button("다음", use_container_width=True):
                full_ok = all((v in opts) for v in st.session_state["anthro_responses"])
                if not full_ok: st.warning("모든 문항을 1~5점 중 하나로 선택해 주세요.")
                else:
                    st.session_state.data["anthro_responses"] = st.session_state["anthro_responses"]
                    st.session_state.anthro_page = 1
                    st.session_state.phase = "achive"; st.rerun()

# 3) 성취/접근 6점 (10/10/나머지)
elif st.session_state.phase == "achive":
    scroll_top_js()
    st.markdown("<h2 style='text-align:center;font-weight:bold;'>평소 본인의 성향에 가까운 정도를 선택해 주세요.</h2>", unsafe_allow_html=True)
    p = os.path.join(BASE_DIR, "data", "questions_achive.json")
    try:
        with open(p,"r",encoding="utf-8") as f: qs = json.load(f)
    except Exception as e:
        st.error(f"추가 설문 문항을 불러오지 못했습니다: {e}"); qs=[]
    total=len(qs); sizes=[10,10,total-20] if total>=20 else [total]
    if "achive_page" not in st.session_state: st.session_state.achive_page=1
    if "achive_responses" not in st.session_state or len(st.session_state["achive_responses"])!=total:
        st.session_state["achive_responses"]=[None]*total
    page=st.session_state.achive_page
    if page==1: start,end=0,min(10,total)
    elif page==2: start,end=10,min(20,total)
    else: start,end=20,total
    st.markdown(f"<div style='text-align:center;color:#6b7480;margin-bottom:10px;'>문항 {start+1}–{end} / 총 {total}문항 (페이지 {page}/{len(sizes)})</div>", unsafe_allow_html=True)
    for gi in range(start,end):
        sel=st.radio(f"{gi+1}. {qs[gi]}", options=[1,2,3,4,5,6], index=None, horizontal=True, key=f"achive_{gi}")
        st.session_state["achive_responses"][gi]=sel
        st.markdown("<div style='margin-bottom:10px;'></div>", unsafe_allow_html=True)
    left,right=st.columns(2)
    with left:
        if page>1 and st.button("← 이전", use_container_width=True):
            st.session_state.achive_page-=1; st.rerun()
    with right:
        cur=st.session_state["achive_responses"][start:end]; ok=all(v in [1,2,3,4,5,6] for v in cur)
        if page<len(sizes):
            if st.button("다음 →", use_container_width=True):
                if not ok: st.warning("현재 페이지의 모든 문항에 1~6 중 하나를 선택해 주세요.")
                else: st.session_state.achive_page+=1; st.rerun()
        else:
            if st.button("다음 (추론 과제 안내)", use_container_width=True):
                full_ok=all(v in [1,2,3,4,5,6] for v in st.session_state["achive_responses"])
                if not full_ok: st.warning("모든 문항에 응답해 주세요. (1~6)")
                else:
                    st.session_state.data["achive_responses"]=st.session_state["achive_responses"]
                    st.session_state.achive_page=1
                    st.session_state.phase="writing_intro"; st.rerun()

# 4) 추론 과제 안내
elif st.session_state.phase == "writing_intro":
    scroll_top_js()
    st.markdown("<h2 style='text-align:center;font-weight:bold;'>추론 기반 객관식 과제 안내</h2>", unsafe_allow_html=True)
    st.markdown("""
    이번 단계에서는 이누이트 계열 형태의 규칙을 보고 **빈칸 채우기** 형식의 문항을 풉니다.  
    - **1회차(명사구)** 10문항 → MCP 애니메이션 → **피드백(1)**  
    - **2회차(동사 TAM)** 10문항 → MCP 애니메이션 → **피드백(2)**
    각 문항은 **빈칸에 들어갈 표현 1개 선택** + **추론 근거 1개 선택**으로 구성됩니다.
    """)
    if st.button("1회차 시작(명사구)"):
        st.session_state.phase="inference_nouns"; st.rerun()

# 5) 추론 과제 1/2 (명사구)
elif st.session_state.phase == "inference_nouns":
    render_round("inference_nouns","추론 과제 1/2 (명사구 문법)", build_items_nouns, REASON_NOUN)

# 6) MCP 애니메이션(1회차 후)
elif st.session_state.phase == "analyzing_r1":
    render_analyzing("r1", next_phase="praise_r1", button_label="1회차 피드백 보기")

# 7) 피드백(1회차)
elif st.session_state.phase == "praise_r1":
    render_praise("inference_nouns", 1, REASON_NOUN)

# 8) 추론 과제 2/2 (동사 TAM)
elif st.session_state.phase == "inference_verbs":
    render_round("inference_verbs","추론 과제 2/2 (동사 TAM)", build_items_verbs, REASON_VERB)

# 9) MCP 애니메이션(2회차 후)
elif st.session_state.phase == "analyzing_r2":
    render_analyzing("r2", next_phase="praise_r2", button_label="2회차 피드백 보기")

# 10) 피드백(2회차)
elif st.session_state.phase == "praise_r2":
    render_praise("inference_verbs", 2, REASON_VERB)

# 11) 학습 동기 설문
elif st.session_state.phase == "motivation":
    scroll_top_js()
    st.markdown("<h2 style='text-align:center;font-weight:bold;'>나의 생각과 가장 가까운 것을 선택해주세요.</h2>", unsafe_allow_html=True)
    qs = [
        "1. 이번 추론 과제와 비슷한 과제를 기회가 있다면 한 번 더 해보고 싶다.",
        "2. 앞으로도 추론 과제가 있다면 참여할 의향이 있다.",
        "3. 더 어려운 추론 과제가 주어져도 도전할 의향이 있다.",
        "4. 추론 과제의 난이도가 높아져도 시도해 볼 의향이 있다.",
        "5. 이번 과제를 통해 성취감을 느꼈다.",
        "6. 추론 과제를 통해 새로운 시각이나 아이디어를 배울 수 있었다.",
        "7. 이런 과제를 수행하는 것은 나의 추론 능력을 발전시키는 데 가치가 있다."
    ]
    mot = []
    for i,q in enumerate(qs, start=1):
        sel=st.radio(q, options=[1,2,3,4,5], index=None, horizontal=True, key=f"motivation_{i}")
        mot.append(sel); st.markdown("<div style='margin-bottom:12px;'></div>", unsafe_allow_html=True)
    if st.button("설문 완료"):
        if None in mot: st.warning("모든 문항에 응답해 주세요.")
        else:
            st.session_state.data["motivation_responses"]=mot
            st.session_state.phase="phone_input"; st.rerun()

# 12) 휴대폰 번호 입력
elif st.session_state.phase == "phone_input":
    scroll_top_js()
    st.title("휴대폰 번호 입력")
    st.markdown("연구 답례품을 받을 휴대폰 번호를 입력해 주세요. (선택 사항)")
    phone = st.text_input("휴대폰 번호", placeholder="010-1234-5678")
    if st.button("완료"):
        if phone.strip() and not validate_phone(phone):
            st.warning("올바른 형식이 아닙니다. (예: 010-1234-5678)")
        else:
            st.session_state.data["phone"]=phone.strip()
            st.session_state.data["endTime"]=datetime.now().isoformat()
            # 저장은 실패해도 설문 흐름 지속
            try:
                save_to_csv(st.session_state.data)
            except Exception as e:
                st.warning(f"로컬 저장(또는 구글시트) 중 문제가 발생했지만 설문은 계속됩니다. 원인: {e}")
            st.session_state.phase="result"; st.rerun()

# 13) 완료 화면
elif st.session_state.phase == "result":
    scroll_top_js()
    if "result_submitted" not in st.session_state:
        st.success("모든 과제가 완료되었습니다. 감사합니다!")
        st.write("하단의 제출 버튼을 눌러 종료하세요. 미제출 시 답례품 제공이 어려울 수 있습니다.")
        if st.button("제출"):
            st.session_state.result_submitted=True; st.rerun()
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
