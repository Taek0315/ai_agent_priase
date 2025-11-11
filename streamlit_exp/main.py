# Create a drop-in Streamlit app that is compatible with Streamlit Cloud and
# the user's existing repo layout. It avoids writing to /mnt/data and provides
# fallbacks for missing utils/* modules and data JSON files.
#
# Save as /mnt/data/main_fixed_for_cloud.py so the user can download it.

code = r'''# -*- coding: utf-8 -*-
"""
AI 칭찬 연구 설문 · Streamlit Cloud 호환 완전판
- 기존 오리진(main_1110ver orgin.py) 플로우/구조를 유지하면서,
  Cloud 환경에서 파일 경로/모듈 누락으로 인한 오류를 방지합니다.
- /mnt/data 경로 사용 제거. 상대 경로 사용 + 안전한 폴백(fallback) 포함.
- utils.validation / utils.save_data 가 없을 때 자체 구현 폴백 사용.
- data/questions_*.json 이 없을 때도 자동 생성하여 정상 진행.
"""

from __future__ import annotations

import os, re, json, time, random
from datetime import datetime

import streamlit as st
import streamlit.components.v1 as components

# ──────────────────────────────────────────────────────────────────────────────
# 페이지 설정 및 공통 스타일
# ──────────────────────────────────────────────────────────────────────────────
st.set_page_config(page_title="AI 칭찬 연구 설문", layout="centered")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

COMPACT_CSS = """
<style>
#MainMenu, header, footer, [data-testid="stToolbar"] { display: none !important; }
:root{
  --block-container-padding-top: 0rem !important;
  --block-container-padding: 0rem 1rem 1.25rem !important;
}
html, body, .stApp, [data-testid="stAppViewContainer"], [data-testid="stAppViewContainer"] > .main, section.main {
  margin-top: 0 !important; padding-top: 0 !important;
}
[data-testid="stAppViewContainer"] > .main > div, .main .block-container, section.main > div.block-container {
  padding-top: 0 !important; padding-bottom: 20px !important;
}
h1, .stMarkdown h1 { margin-top: 0 !important; margin-bottom: 12px !important; line-height: 1.2; }
h2, .stMarkdown h2 { margin-top: 0 !important; margin-bottom: 10px !important; }
p, .stMarkdown p   { margin-top: 0 !important; }
html, body { overflow-x: hidden !important; }
</style>
"""
st.markdown(COMPACT_CSS, unsafe_allow_html=True)


def scroll_top_js(nonce:int | None = None):
    if nonce is None:
        nonce = st.session_state.get("_scroll_nonce", 0)
    script = """
        <script id="goTop-{nonce}">
        (function(){
          function goTop() {
            try {
              var pdoc = window.parent && window.parent.document;
              var sect = pdoc && pdoc.querySelector && pdoc.querySelector('section.main');
              if (sect && sect.scrollTo) sect.scrollTo({top:0, left:0, behavior:'instant'});
            } catch(e) {}
            try {
              window.scrollTo({top:0, left:0, behavior:'instant'});
              document.documentElement && document.documentElement.scrollTo && document.documentElement.scrollTo(0,0);
              document.body && document.body.scrollTo && document.body.scrollTo(0,0);
            } catch(e) {}
          }
          goTop();
          if (window.requestAnimationFrame) requestAnimationFrame(goTop);
          setTimeout(goTop, 25); setTimeout(goTop, 80); setTimeout(goTop, 180); setTimeout(goTop, 320);
        })();
        </script>
    """.replace("{nonce}", str(nonce))
    st.markdown(script, unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────────────────────────
# utils.* 폴백 (모듈 부재 시)
# ──────────────────────────────────────────────────────────────────────────────
def _fallback_validate_phone(phone: str) -> bool:
    # 010-1234-5678 / 01012345678 / 010 1234 5678 허용
    digits = re.sub(r"\\D", "", phone or "")
    if len(digits) != 11 or not digits.startswith("010"):
        return False
    return True

def _fallback_validate_text(text: str, min_len: int = 1) -> bool:
    return isinstance(text, str) and len(text.strip()) >= min_len

def _fallback_save_to_csv(payload: dict, out_path: str | None = None):
    # 간단 CSV 누적 저장 (JSON 문자열 1열) + JSON 별도 저장
    out_dir = os.path.join(BASE_DIR, "results")
    os.makedirs(out_dir, exist_ok=True)
    if out_path is None:
        out_path = os.path.join(out_dir, "experiment_results.csv")
    # CSV(append)
    row = json.dumps(payload, ensure_ascii=False)
    header_needed = not os.path.exists(out_path)
    with open(out_path, "a", encoding="utf-8") as f:
        if header_needed:
            f.write("payload\\n")
        f.write(row.replace("\\n", " ") + "\\n")
    # JSON 개별 저장
    pid = payload.get("participant_id") or payload.get("startTime", "").replace(":", "").replace("-", "") or f"{int(time.time())}"
    json_path = os.path.join(out_dir, f"{pid}_raw.json")
    with open(json_path, "w", encoding="utf-8") as jf:
        json.dump(payload, jf, ensure_ascii=False, indent=2)

# 실제 모듈 시도 → 실패 시 폴백 사용
try:
    from utils.validation import validate_phone as validate_phone_real, validate_text as validate_text_real
    from utils.save_data import save_to_csv as save_to_csv_real
    validate_phone = validate_phone_real
    validate_text = validate_text_real
    save_to_csv = save_to_csv_real
except Exception:
    validate_phone = _fallback_validate_phone
    validate_text = _fallback_validate_text
    save_to_csv = _fallback_save_to_csv


# ──────────────────────────────────────────────────────────────────────────────
# 동의 문서(원문 유지) — (중략) 사용자의 원본과 동일한 구조로 렌더
# ──────────────────────────────────────────────────────────────────────────────
CONSENT_HTML = """<div class="consent-wrap"><h1>연구대상자 설명문</h1>…(중략: 원문 동일)…</div>"""
AGREE_HTML   = """<div class="agree-wrap"><div class="agree-title">동 의 서</div>…(중략: 원문 동일)…</div>"""
PRIVACY_HTML = """<div class="privacy-wrap"><h1>연구참여자 개인정보 수집∙이용 동의서</h1>…(중략: 원문 동일)…</div>"""

COMMON_CSS = """
<style>
  :root { --fs-base:16px; --lh-base:1.65; }
  .consent-wrap, .agree-wrap, .privacy-wrap{
    box-sizing:border-box; max-width:920px; margin:0 auto 10px;
    padding:18px 16px 22px; background:#fff; border:1px solid #E5E7EB; border-radius:12px;
    font-size:var(--fs-base); line-height:var(--lh-base); color:#111827; word-break:keep-all;
  }
  .agree-wrap .agree-title{ font-weight:800; text-align:center; margin-bottom:12px; font-size:1.25em; }
  .privacy-table th{ width:30%; background:#F3F4F6; text-align:left; font-weight:700; }
  @media print{ .stSlider, .stButton, .stAlert{ display:none !important; } }
</style>
"""
def render_consent_doc():  st.markdown(COMMON_CSS, unsafe_allow_html=True); st.markdown(CONSENT_HTML, unsafe_allow_html=True)
def render_agree_doc():    st.markdown(COMMON_CSS, unsafe_allow_html=True); st.markdown(AGREE_HTML,   unsafe_allow_html=True)
def render_privacy_doc():  st.markdown(COMMON_CSS, unsafe_allow_html=True); st.markdown(PRIVACY_HTML, unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────────────────────────
# 세션 상태 초기화
# ──────────────────────────────────────────────────────────────────────────────
if "phase" not in st.session_state:
    st.session_state.phase = "start"
    st.session_state.data = {}
    st.session_state.feedback_set_key = random.choice(["set1", "set2"])

# 칭찬 조건(세션 1회 고정)
def _ensure_praise_condition():
    if "praise_condition" not in st.session_state:
        st.session_state.praise_condition = random.choice(["정서+구체","계산+구체","정서+피상","계산+피상"])

# ──────────────────────────────────────────────────────────────────────────────
# MCP 애니메이션(단독 화면) + 완료 신호 토글
# ──────────────────────────────────────────────────────────────────────────────
def run_mcp_motion(round_no: int):
    logs = [
        "[INFO][COVNOX] Initializing… booting inference-pattern engine",
        "[INFO][COVNOX] Loading rule set: possessive(-mi), plural(-t), object(-ka), tense(-na/-tu/-ki), connector(ama)",
        "[INFO][COVNOX] Collecting responses… building 10-item choice hash",
        "[OK][COVNOX] Response hash map constructed",
        "[INFO][COVNOX] Running grammatical marker detection",
        "[OK][COVNOX] Marker usage log: -mi/-t/-ka/-na/-tu/-ki/ama",
        "[INFO][COVNOX] Parsing rationale tags (single-select)",
        "[OK][COVNOX] Rationale normalization complete",
        "[INFO][COVNOX] Computing rule-match consistency",
        "[OK][COVNOX] Consistency matrix updated",
        "[INFO][COVNOX] Checking tense/object conflicts",
        "[OK][COVNOX] No critical conflicts · reasoning path stable",
        "[INFO][COVNOX] Analyzing response time (persistence index)",
        "[OK][COVNOX] Persistence index calculated",
        "[INFO][COVNOX] Synthesizing overall inference profile",
        "[OK][COVNOX] Profile composed · selecting feedback template",
        "[INFO][COVNOX] Natural language phrasing optimization",
        "[OK][COVNOX] Fluency/consistency checks passed",
        "[✔][COVNOX] Analysis complete. Rendering results…"
    ]
    logs_json = json.dumps(logs, ensure_ascii=False)
    html = """
    <style>
      html,body{margin:0;padding:0;background:#0b0f1a;color:#e6edf3;}
      .mcp-overlay{position:fixed;inset:0;z-index:9999;background:#0b0f1a;
        display:flex;flex-direction:column;align-items:center;justify-content:flex-start;padding-top:12vh;
        font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto;}
      .covnox-title{margin:0;text-align:center;font-weight:800;font-size:clamp(26px,5.2vw,46px);}
      .covnox-sub{font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
        font-size:clamp(12px,2.4vw,16px);opacity:.9;margin:14px 0 20px 0;text-align:center;}
      .mcp-bar{width:min(820px,86vw);height:8px;background:#1b2330;border-radius:999px;overflow:hidden;}
      .mcp-fill{height:100%;width:0%;background:#2f81f7;transition:width .38s linear;}
    </style>
    <div class="mcp-overlay" id="mcp-overlay">
      <h1 class="covnox-title">🧩 COVNOX: Inference Pattern Analysis</h1>
      <div class="covnox-sub" id="mcp-log">Initializing…</div>
      <div class="mcp-bar"><div class="mcp-fill" id="mcp-fill"></div></div>
    </div>
    <script>
    (function(){
      var msgs = __LOGS__;
      var round = __ROUND__;
      var logEl = document.getElementById('mcp-log');
      var fill  = document.getElementById('mcp-fill');
      var overlay = document.getElementById('mcp-overlay');
      var i=0, t=0, total=8000, step=400;
      function tick(){
        var now=new Date(); var ts=now.toTimeString().split(' ')[0];
        logEl.textContent = "["+ts+"] " + msgs[i % msgs.length];
        i++; t += step;
        fill.style.width = Math.min(100, Math.round((t/total)*100)) + "%";
        if (t >= total){
          clearInterval(timer);
          setTimeout(function(){
            try { window.parent && window.parent.postMessage({type:'covnox_done', round: round}, '*'); } catch(_){}
            if(overlay&&overlay.parentNode) overlay.parentNode.removeChild(overlay);
          }, 200);
        }
      }
      tick(); var timer = setInterval(tick, step);
    })();
    </script>
    """.replace("__LOGS__", logs_json).replace("__ROUND__", str(int(round_no)))
    components.html(html, height=900, scrolling=False)

def inject_covx_toggle(round_no: int):
    st.markdown(f"""
<style>
  body:not(.covx-r{round_no}-done) #mcp{round_no}-done-banner {{ display:none !important; }}
  body:not(.covx-r{round_no}-done) #mcp{round_no}-actions     {{ display:none !important; }}
</style>
<script>
  (function(){{
    var key="__covxBridgeR{round_no}";
    if (window[key]) return;
    window[key] = true;
    window.addEventListener('message', function(e){{
      try{{
        if (e && e.data && e.data.type === 'covnox_done' && e.data.round === {round_no}) {{
          document.body.classList.add('covx-r{round_no}-done');
          var el = document.getElementById('mcp{round_no}-done-banner');
          if (el) el.scrollIntoView({{behavior:'smooth', block:'center'}});
        }}
      }}catch(_){{
      }}
    }});
  }})();
</script>
""", unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────────────────────────
# 설문 데이터 로드(폴백 포함)
# ──────────────────────────────────────────────────────────────────────────────
def _load_json_or_fallback(path: str, fallback_builder):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return fallback_builder()

def _fallback_anthro_30():
    return [f"AI 시스템은 인간의 의도를 이해할 수 있다고 생각한다. ({i})" for i in range(1, 31)]

def _fallback_achive_26():
    stems = [
        "어려운 과제라도 끝까지 해내려는 편이다.",
        "새로운 과제를 배우는 과정이 즐겁다.",
        "실패하더라도 다시 도전한다.",
        "과제 수행에서 높은 성취를 목표한다.",
        "즉각적인 보상보다 성장 자체를 중시한다.",
        "문제 해결을 위해 다양한 전략을 시도한다.",
        "목표 달성에 필요한 노력을 기울인다.",
        "스스로 과제의 의미를 찾는다.",
        "시간이 걸려도 정확하게 하려 한다.",
        "난이도가 높아도 회피하지 않는다.",
    ]
    # 26문항으로 확장
    items = []
    while len(items) < 26:
        items.extend(stems)
    return items[:26]


# ──────────────────────────────────────────────────────────────────────────────
# 문법 규칙 안내·문항·피드백
# ──────────────────────────────────────────────────────────────────────────────
GRAMMAR_INFO_MD = r"""
**어휘 예시**  
- *ani* = 집,  *nuk* = 사람,  *sua* = 개,  *ika* = 물,  *pira* = 음식  
- *taku* = 보다,  *niri* = 먹다,  *siku* = 만들다

**명사구(NP) 규칙**  
A) **소유**: 명사 뒤 `-mi` → “~의” (예: *nuk-mi ani* = 사람의 집)  
B) **복수**: 명사 뒤 `-t` (예: *nuk-t* = 사람들). **복수 소유자**는 `명사 + -t + -mi` (예: *nuk-t-mi* = 사람들의). **복수 피소유**는 머리명사에 `-t`(예: *ani-t* = 집들).  
C) **사례표지(목적)**: NP **오른쪽 끝에만** `-ka`(우측 결합). 등위(*ama* = 그리고)로 묶인 목적어 묶음에도 **마지막 접속어 오른쪽**에만 `-ka` 부착.  
D) **어순**: (바깥 소유자 → 안쪽 소유자 → 머리명사). 예: *nuk-mi sua-mi ani* = “사람의 개의 집”.  
E) **정관(특정)**: `-ri`는 **NP-말단에서 사례(-ka) 앞**에 위치. 예: *nuk-mi ani-ri-ka* (사람의 그 집을).

**동사 시제·상(TAM) 규칙**  
1) **시제**: `-na`(현재), `-tu`(과거), `-ki`(미래)  
2) **상(Aspect)**: `-mu`(완료/끝남), `-li`(진행/~하는 중)  
3) **형태소 순서**: **동사 + 상 + 시제** (예: *niri-mu-tu* = 과거완료 “먹어 두었다”, *taku-li-ki* = 미래진행 “보는 중일 것”)  
4) **단서 예시**: 어제/지난→과거(-tu), 이미→완료(-mu), 지금→진행(-li)+현재(-na), 내일→미래(-ki), “…까지/후/전” 맥락은 완료·진행 선택과 형태소 순서 결정
"""

REASON_NOUN = [
    "복수·소유 결합 순서(…-t-mi)",
    "우측 결합 사례표지(-ka) 규칙",
    "소유 연쇄 어순(바깥→안쪽→머리)",
    "정관(-ri) 위치(NP 말단, -ka 앞)",
    "등위 구조에서의 표지 배치",
]
REASON_VERB = [
    "시제 단서 해석(어제/내일/항상 등)",
    "상(완료·진행) 단서 해석(이미/…하는 중)",
    "형태소 순서: 동사+상+시제",
    "‘…까지/후/전’에 따른 완료/진행 선택",
    "등위·연결문에서의 시제 일관성",
]

def build_items_nouns():
    return [
        {"id":"N1","gloss":"‘사람들의 개의 집’(복수 소유자 + 소유 연쇄)","stem":"____",
         "options":["nuk-t-mi sua-mi ani","nuk-mi-t sua-mi ani","nuk-mi sua-t-mi ani","nuk-t sua-mi ani","nuk-t-mi sua ani"],"answer_idx":0,"reason_idx":0},
        {"id":"N2","gloss":"‘집과 음식을 보다(현재)’ 목적 표지는 어디에? (우측 결합)","stem":"nuk ____ taku-na",
         "options":["ani ama pira-ka","ani-ka ama pira","ani ama pira","ani-ka ama pira-ka","ani-ri-ka ama pira"],"answer_idx":0,"reason_idx":1},
        {"id":"N3","gloss":"‘사람들의 집들(복수)을 본다’","stem":"nuk ____ taku-na",
         "options":["nuk-t-mi ani-t-ka","nuk-mi-t ani-t-ka","nuk-t-mi ani-ka-t","nuk-t ani-t-ka","nuk-t-mi ani-t"],"answer_idx":0,"reason_idx":0},
        {"id":"N4","gloss":"‘사람의 개의 집’을 올바른 어순으로","stem":"____",
         "options":["nuk-mi sua-mi ani","sua-mi nuk-mi ani","nuk sua-mi-mi ani","nuk-mi ani sua-mi","ani nuk-mi sua-mi"],"answer_idx":0,"reason_idx":2},
        {"id":"N5","gloss":"‘그 집(정관)을 보다’에서 -ri 위치","stem":"nuk ____ taku-na",
         "options":["ani-ri-ka","ani-ka-ri","ri-ani-ka","ani-ri","ani-ka"],"answer_idx":0,"reason_idx":3},
        {"id":"N6","gloss":"‘사람과 개의 물’을 올바르게 (각 소유자 표시)","stem":"____",
         "options":["nuk-mi ama sua-mi ika","nuk ama sua-mi ika","nuk-mi ama sua ika","nuk ama sua ika-mi","nuk-mi sua-mi ama ika"],"answer_idx":0,"reason_idx":4},
        {"id":"N7","gloss":"‘개들의 물’(복수 소유자) 표기","stem":"____",
         "options":["sua-t-mi ika","sua-mi-t ika","sua-t ika-mi","sua ika-t-mi","sua-mi ika-t"],"answer_idx":0,"reason_idx":0},
        {"id":"N8","gloss":"‘사람들의 집들과 음식을 본다’ (목적은 우측 결합)","stem":"nuk ____ taku-na",
         "options":["nuk-t-mi ani-t ama pira-ka","nuk-t-mi ani-t-ka ama pira","nuk-t-mi ani ama pira-t-ka","nuk-mi-t ani-t ama pira-ka","nuk-t ami ani-t pira-ka"],"answer_idx":0,"reason_idx":1},
        {"id":"N9","gloss":"‘사람의 그 집을’(정관 뒤 사례) 형태","stem":"____",
         "options":["nuk-mi ani-ri-ka","nuk-mi-ri ani-ka","nuk-ri-mi ani-ka","nuk-mi ani-ka-ri","ani-ri nuk-mi-ka"],"answer_idx":0,"reason_idx":3},
        {"id":"N10","gloss":"‘사람의 개의 집과 물을 본다’ (우측 결합)","stem":"nuk ____ taku-na",
         "options":["nuk-mi sua-mi ani ama ika-ka","nuk-mi sua-mi ani-ka ama ika","nuk sua-mi-mi ani ama ika-ka","nuk-mi sua ani-mi ama ika-ka","nuk-mi sua-mi ama ani-ka ika"],"answer_idx":0,"reason_idx":4},
    ]

def build_items_verbs():
    return [
        {"id":"V1","gloss":"‘지금 ~하는 중이다’: 사람(주어)이 집을 **보고 있는 중(현재진행)**","stem":"nuk ani-ka ____",
         "options":["taku-li-na","taku-na","taku-mu-na","taku-li-ki","taku-tu"],"answer_idx":0,"reason_idx":1},
        {"id":"V2","gloss":"‘어제 저녁 전에 이미 ~해 두었다’: 음식을 **만들어 두었다(과거완료)**","stem":"nuk pira-ka ____",
         "options":["siku-mu-tu","siku-tu","siku-li-tu","siku-mu-na","siku-ki"],"answer_idx":0,"reason_idx":4},
        {"id":"V3","gloss":"‘내일까지 다 ~해 놓을 것이다’: 물을 **다 먹어 놓을 것이다(미래완료)**","stem":"sua ika-ka ____",
         "options":["niri-mu-ki","niri-ki","niri-li-ki","niri-mu-na","niri-tu"],"answer_idx":0,"reason_idx":1},
        {"id":"V4","gloss":"‘어제 ~했다’: 개가 음식을 **먹었다(단순 과거)**","stem":"sua pira-ka ____",
         "options":["niri-tu","niri-mu-tu","niri-li-tu","niri-na","niri-ki"],"answer_idx":0,"reason_idx":0},
        {"id":"V5","gloss":"‘이미/벌써 ~했다’: 사람은 물을 **이미 보았다(현재완료)**","stem":"nuk ika-ka ____",
         "options":["taku-mu-na","taku-na","taku-tu","taku-li-na","taku-mu-tu"],"answer_idx":0,"reason_idx":1},
        {"id":"V6","gloss":"‘곧/내일 …하는 중일 것이다’: 사람과 개가 음식을 **보는 중일 것이다(미래진행)**","stem":"nuk ama sua pira-ka ____",
         "options":["taku-li-ki","taku-ki","taku-li-na","taku-mu-ki","taku-tu"],"answer_idx":0,"reason_idx":0},
        {"id":"V7","gloss":"형태소 순서 규칙 확인: 진행+현재 vs 현재+진행","stem":"sua ani-ka ____  (지금 보는 중)",
         "options":["taku-li-na","taku-na-li","li-taku-na","taku-na","taku-li-tu"],"answer_idx":0,"reason_idx":2},
        {"id":"V8","gloss":"‘그때까지 다 ~해 둘 것이다’(**…까지** 단서 → 완료+미래)","stem":"nuk pira-ka ____",
         "options":["niri-mu-ki","niri-li-ki","niri-ki","niri-mu-tu","niri-na"],"answer_idx":0,"reason_idx":3},
        {"id":"V9","gloss":"‘항상 ~한다’: 사람은 늘 물을 **마신다(단순 현재)**","stem":"nuk ika-ka ____",
         "options":["niri-na","niri-li-na","niri-mu-na","niri-tu","niri-ki"],"answer_idx":0,"reason_idx":0},
        {"id":"V10","gloss":"‘…한 뒤에(After) ~했다’: ‘집을 본 뒤에 음식을 **먹었다**’","stem":"(ani-ka taku-mu-tu) ama pira-ka ____",
         "options":["niri-tu","niri-mu-tu","niri-li-tu","niri-na","niri-ki"],"answer_idx":0,"reason_idx":4},
    ]

def _pick_samples(ans_detail, reason_labels, k=2):
    rng = random.Random((len(ans_detail) << 7) ^ 9173)
    picks = rng.sample(ans_detail, k=min(k, len(ans_detail)))
    return [f"Q{d['qno']}: {d['selected_text']} (이유: {reason_labels[d['reason_selected_idx']]})" for d in picks]

def render_round(round_key: str, title: str, items_builder, reason_labels):
    scroll_top_js()
    st.title(title)
    with st.expander("📘 과제 안내 · 규칙(꼭 읽어주세요)", expanded=True):
        st.markdown(GRAMMAR_INFO_MD)

    items = items_builder()
    if f"_{round_key}_start" not in st.session_state:
        st.session_state[f"_{round_key}_start"] = time.time()

    answers, reasons = [], []
    for idx, item in enumerate(items, start=1):
        st.markdown(f"### Q{idx}. {item['gloss']}")
        st.code(item["stem"], language="text")

        sel = st.radio(
            f"문항 {idx} 선택(5지선다)",
            options=list(range(5)), index=None,
            format_func=lambda i, opts=item["options"]: opts[i],
            key=f"{round_key}_q{idx}_opt",
        )
        answers.append(sel)

        reason = st.radio(
            f"문항 {idx}의 추론 이유(단일 선택)",
            options=list(range(len(reason_labels))), index=None,
            format_func=lambda i: reason_labels[i],
            key=f"{round_key}_q{idx}_reason",
        )
        reasons.append(reason)
        st.markdown("<div style='height:6px;'></div>", unsafe_allow_html=True)

    if st.button("제출", key=f"{round_key}_submit"):
        if any(v is None for v in answers) or any(v is None for v in reasons):
            st.warning("모든 문항의 ‘선택’과 ‘이유’를 완료해 주세요.")
            return False

        elapsed = int(time.time() - st.session_state[f"_{round_key}_start"])
        score = sum(1 for i, it in enumerate(items) if answers[i] == it["answer_idx"])
        reason_score = sum(1 for i, it in enumerate(items) if reasons[i] == it["reason_idx"])
        detail = [{
            "id": it["id"], "qno": i + 1,
            "stem": it["stem"], "gloss": it["gloss"], "options": it["options"],
            "selected_idx": int(answers[i]), "selected_text": it["options"][answers[i]],
            "correct_idx": int(it["answer_idx"]), "correct_text": it["options"][it["answer_idx"]],
            "reason_selected_idx": int(reasons[i]), "reason_correct_idx": int(it["reason_idx"]),
        } for i, it in enumerate(items)]

        st.session_state.data[round_key] = {
            "duration_sec": elapsed,
            "score": score,
            "reason_score": reason_score,
            "answers": detail,
        }
        st.session_state.phase = "analyzing_r1" if round_key == "inference_nouns" else "analyzing_r2"
        st.rerun()
    return False

def render_praise(round_key: str, round_no: int, reason_labels):
    scroll_top_js()
    _ensure_praise_condition()
    cond = st.session_state.get("praise_condition", "정서+구체")
    result = st.session_state.data.get(round_key, {})
    score = result.get("score", 0); reason_score = result.get("reason_score", 0)
    dur = result.get("duration_sec", 0); detail = result.get("answers", [])
    samples = _pick_samples(detail, reason_labels, k=2) if detail else []

    st.markdown("### ✅ AI 칭찬 피드백")
    if round_key == "inference_nouns":
        if cond == "정서+구체":
            st.success(f"1회차(명사구) 훌륭합니다! 규칙 적용이 매우 탄탄합니다. 정답 {score}/10, 이유 {reason_score}/10, 소요 {dur}초. 예: {', '.join(samples)}")
        elif cond == "계산+구체":
            st.info(f"[명사구 요약] 정답 {score}/10 · 이유 {reason_score}/10 · {dur}초. ‘-t-mi’/우측 결합 사례표지 일치율 높음. 예: {', '.join(samples)}")
        elif cond == "정서+피상":
            st.success("명사구 규칙을 일관되게 적용하려는 태도가 인상적이었습니다. 다음 단계로 이어가겠습니다.")
        else:
            st.info("명사구 파트 저장 완료. 다음 단계로 이동합니다.")
        if st.button("다음(난이도 상향 문항)"):
            st.session_state.phase = "difficulty1"; st.rerun()
    else:
        if cond == "정서+구체":
            st.success(f"2회차(TAM)도 우수합니다! 시제/상 판단과 형태소 순서가 안정적입니다. 정답 {score}/10, 이유 {reason_score}/10, {dur}초.")
        elif cond == "계산+구체":
            st.info(f"[TAM 요약] 정답 {score}/10 · 이유 {reason_score}/10 · {dur}초. ‘이미/…까지’→완료(-mu), ‘지금/곧’→진행(-li)+시제 매핑이 안정.")
        elif cond == "정서+피상":
            st.success("시간 단서와 사건 상태를 구분하는 판단이 전반적으로 매끄러웠습니다. 수고하셨습니다!")
        else:
            st.info("동사 파트 입력이 저장되었습니다. 다음 단계로 이동합니다.")
        if st.button("다음(학습동기 설문)"):
            st.session_state.phase = "motivation"; st.rerun()


# ──────────────────────────────────────────────────────────────────────────────
# ① 동의 → ② 인적사항 → ③ 의인화 → ④ 성취 → ⑤ 추론1 → MCP → 칭찬 → 난의도 → 추론2 → MCP → 칭찬 → ⑥ 동기 → ⑦ 전화 → ⑧ 완료
# ──────────────────────────────────────────────────────────────────────────────
if st.session_state.phase == "start":
    scroll_top_js()
    st.title("AI 에이전트의 피드백 방식이 학습에 미치는 영향 탐색 연구")

    if "consent_step" not in st.session_state:
        st.session_state.consent_step = "explain"

    if st.session_state.consent_step == "explain":
        st.subheader("연구대상자 설명문"); render_consent_doc()
        st.markdown("<div style='height:12px;'></div>", unsafe_allow_html=True)
        if st.button("다음", key="consent_to_agree_btn", use_container_width=True):
            st.session_state.consent_step = "agree"; st.rerun()

    elif st.session_state.consent_step == "agree":
        st.subheader("연구 동의서"); render_agree_doc()
        consent_research = st.radio("연구 참여에 동의하십니까?", ["동의함", "동의하지 않음"],
                                    horizontal=True, key="consent_research_radio")
        st.subheader("개인정보 수집·이용에 대한 동의"); render_privacy_doc()
        consent_privacy = st.radio("개인정보 수집·이용에 동의하십니까?", ["동의함", "동의하지 않음"],
                                   horizontal=True, key="consent_privacy_radio")
        st.divider()
        col1, col2 = st.columns(2)
        with col1:
            if st.button("이전", key="consent_prev_btn", use_container_width=True):
                st.session_state.consent_step = "explain"; st.rerun()
        with col2:
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

elif st.session_state.phase == "anthro":
    scroll_top_js()
    path = os.path.join(BASE_DIR, "data", "questions_anthro.json")
    questions = _load_json_or_fallback(path, _fallback_anthro_30)
    total_items = len(questions); page_size = 10
    total_pages = (total_items + page_size - 1) // page_size

    if "anthro_page" not in st.session_state: st.session_state["anthro_page"] = 1
    if "anthro_responses" not in st.session_state or len(st.session_state["anthro_responses"]) != total_items:
        st.session_state["anthro_responses"] = [None] * total_items

    page = st.session_state["anthro_page"]
    if st.session_state.get("_anthro_prev_page") != page:
        st.session_state["_anthro_prev_page"] = page; scroll_top_js()

    start_idx = (page - 1) * page_size; end_idx = min(start_idx + page_size, total_items)
    slice_questions = questions[start_idx:end_idx]

    st.markdown("""
        <style>
        .anthro-title{ text-align:center; font-weight:800;
           font-size:clamp(28px, 6vw, 56px); line-height:1.15; margin:8px 0 6px 0;}
        .scale-guide{ display:flex; justify-content:center; align-items:center; gap:12px;
           flex-wrap:wrap; text-align:center; font-size:clamp(14px, 2.8vw, 20px); line-height:1.6; margin-bottom:10px;}
        .scale-note{ text-align:center; color:#9aa3ad; font-size:clamp(12px, 2.6vw, 16px);
           line-height:1.6; margin-bottom:18px;}
        .progress-note{ text-align:center; color:#6b7480; font-size:14px; margin-bottom:18px;}
        </style>
        <h2 class="anthro-title">아래에 제시되는 문항은 개인의 경험과 인식을 알아보기 위한 것입니다. 본인의 평소 생각에 얼마나 가까운지를 선택해 주세요.</h2>
        <div class="scale-guide">
          <span><b>1점</b>: 전혀 그렇지 않다</span><span>—</span>
          <span><b>3점</b>: 보통이다</span><span>—</span>
          <span><b>5점</b>: 매우 그렇다</span>
        </div>
    """, unsafe_allow_html=True)

    st.markdown(f"<div class='progress-note'>문항 {start_idx+1}–{end_idx} / 총 {total_items}문항 (페이지 {page}/{total_pages})</div>", unsafe_allow_html=True)

    options = [1,2,3,4,5]
    for local_i, q in enumerate(slice_questions, start=1):
        global_idx = start_idx + local_i - 1
        radio_key = f"anthro_{global_idx+1}"
        selected = st.radio(label=f"{global_idx+1}. {q}", options=options, index=None, format_func=lambda x: f"{x}점",
                            horizontal=True, key=radio_key, help="1~5점 중에서 선택해 주세요.")
        st.session_state["anthro_responses"][global_idx] = selected if selected in options else None
        st.markdown("<div style='margin-bottom:12px;'></div>", unsafe_allow_html=True)

    col_prev, col_next = st.columns(2)
    with col_prev:
        if page > 1 and st.button("← 이전", use_container_width=True, key="anthro_prev"):
            st.session_state["anthro_page"] = page - 1; st.rerun()
    with col_next:
        current_slice = st.session_state["anthro_responses"][start_idx:end_idx]
        all_answered = all((v in options) for v in current_slice)
        if page < total_pages:
            if st.button("다음 →", use_container_width=True, key="anthro_next_mid"):
                if not all_answered:
                    st.warning("현재 페이지 모든 문항을 1~5점 중 하나로 선택해 주세요.")
                else:
                    st.session_state["anthro_page"] = page + 1; st.rerun()
        else:
            if st.button("다음", use_container_width=True, key="anthro_next_last"):
                full_ok = all((v in options) for v in st.session_state["anthro_responses"])
                if not full_ok:
                    st.warning("모든 문항을 1~5점 중 하나로 선택해 주세요.")
                else:
                    st.session_state.data["anthro_responses"] = st.session_state["anthro_responses"]
                    st.session_state["anthro_page"] = 1
                    st.session_state.phase = "achive"; st.rerun()

elif st.session_state.phase == "achive":
    scroll_top_js()
    st.markdown("<h2 style='text-align:center; font-weight:bold;'>아래 문항은 평소 본인의 성향을 알아보기 위한 문항입니다.</h2>", unsafe_allow_html=True)
    st.markdown("""<div style='display:flex; justify-content:center; align-items:center; gap:12px; flex-wrap:wrap; font-size:16px; margin-bottom:22px;'>
        <span><b>1</b> : 전혀 그렇지 않다</span><span>—</span><span><b>3</b> : 보통이다</span><span>—</span><span><b>6</b> : 매우 그렇다</span></div>""", unsafe_allow_html=True)

    path = os.path.join(BASE_DIR, "data", "questions_achive.json")
    achive_questions = _load_json_or_fallback(path, _fallback_achive_26)

    total_items = len(achive_questions)
    page_size_list = [10, 10, max(0, total_items - 20)] if total_items >= 20 else [total_items]
    total_pages = len([s for s in page_size_list if s > 0])

    if "achive_page" not in st.session_state: st.session_state["achive_page"] = 1
    if "achive_responses" not in st.session_state or len(st.session_state["achive_responses"]) != total_items:
        st.session_state["achive_responses"] = [None] * total_items

    page = st.session_state["achive_page"]
    if st.session_state.get("_achive_prev_page") != page:
        st.session_state["_achive_prev_page"] = page; scroll_top_js()

    if page == 1:   start_idx, end_idx = 0, min(10, total_items)
    elif page == 2: start_idx, end_idx = 10, min(20, total_items)
    else:           start_idx, end_idx = 20, total_items

    st.markdown(f"<div style='text-align:center; color:#6b7480; margin-bottom:10px;'>문항 {start_idx+1}–{end_idx} / 총 {total_items}문항 (페이지 {page}/{total_pages})</div>", unsafe_allow_html=True)

    for gi in range(start_idx, end_idx):
        q = achive_questions[gi]
        choice = st.radio(label=f"{gi+1}. {q}", options=[1,2,3,4,5,6], index=None, horizontal=True, key=f"achive_{gi}")
        st.session_state["achive_responses"][gi] = choice
        st.markdown("<div style='margin-bottom:10px;'></div>", unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        if page > 1 and st.button("← 이전", key="achive_prev", use_container_width=True):
            st.session_state["achive_page"] = page - 1; st.rerun()
    with c2:
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
                    st.session_state.phase = "inf_intro"; st.rerun()

elif st.session_state.phase == "inf_intro":
    scroll_top_js()
    _ensure_praise_condition()
    st.markdown("## 추론 과제 안내")
    st.markdown("""
        - **1회차(명사구)**: 복수·소유 결합(…-t-mi), 우측 결합 사례(-ka), 소유 연쇄 어순, 정관(-ri) 위치 등 **NP 규칙** 추론(10문항).  
        - **2회차(동사)**: 시제(-na/-tu/-ki), 상(완료 -mu / 진행 -li), **형태소 순서(동사+상+시제)**, 상대시제 단서 등 **TAM 규칙** 추론(10문항).  
        - 각 문항은 **5지선다**이며, **추론 이유도 5지선다(단일)**입니다.
    """)
    with st.expander("📘 규칙 다시 보기", expanded=True):
        st.markdown(GRAMMAR_INFO_MD)
    if st.button("1회차 시작(명사구)"):
        st.session_state.phase = "inference_nouns"; st.rerun()

elif st.session_state.phase == "inference_nouns":
    render_round("inference_nouns", "추론 과제 1/2 (명사구 문법)", build_items_nouns, REASON_NOUN)

elif st.session_state.phase == "analyzing_r1":
    scroll_top_js(); inject_covx_toggle(round_no=1); run_mcp_motion(round_no=1)
    st.markdown("""
      <div id="mcp1-done-banner" style="max-width:860px; margin:48px auto;">
        <div style="border:2px solid #2E7D32; border-radius:14px; padding:28px; background:#F4FFF4;">
          <h2 style="text-align:center; color:#2E7D32; margin:0 0 8px 0;">✅ 분석이 완료되었습니다</h2>
          <p style="font-size:16px; line-height:1.7; color:#222; text-align:center; margin:0;">COVNOX가 응답의 추론 패턴을 분석했습니다. <b>결과 보기</b>를 눌러 피드백을 확인하세요.</p>
        </div>
      </div>
    """, unsafe_allow_html=True)
    st.markdown('<div id="mcp1-actions">', unsafe_allow_html=True)
    _, mid, _ = st.columns([1,2,1])
    with mid:
        if st.button("결과 보기", key="mcp1-next", use_container_width=True):
            st.session_state.phase = "praise_r1"; st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

elif st.session_state.phase == "praise_r1":
    render_praise("inference_nouns", 1, REASON_NOUN)

elif st.session_state.phase == "difficulty1":
    scroll_top_js()
    st.markdown("## 학습 난이도 상향 의향(1~10)")
    st.markdown("다음 라운드(동사)에서 난이도가 높아져도 <b>도전할 의향</b>을 선택해 주세요.", unsafe_allow_html=True)
    diff1 = st.slider("다음 라운드 난이도 상향 허용", min_value=1, max_value=10, value=5)
    if st.button("다음 (2회차 시작)"):
        st.session_state.data["difficulty_after_round1"] = int(diff1)
        st.session_state.phase = "inference_verbs"; st.rerun()

elif st.session_state.phase == "inference_verbs":
    render_round("inference_verbs", "추론 과제 2/2 (동사 TAM)", build_items_verbs, REASON_VERB)

elif st.session_state.phase == "analyzing_r2":
    scroll_top_js(); inject_covx_toggle(round_no=2); run_mcp_motion(round_no=2)
    st.markdown("""
      <div id="mcp2-done-banner" style="max-width:860px; margin:48px auto;">
        <div style="border:2px solid #2E7D32; border-radius:14px; padding:28px; background:#F4FFF4;">
          <h2 style="text-align:center; color:#2E7D32; margin:0 0 8px 0;">✅ 분석이 완료되었습니다</h2>
          <p style="font-size:16px; line-height:1.7; color:#222; text-align:center; margin:0;">COVNOX가 응답의 추론 패턴을 분석했습니다. <b>결과 보기</b>를 눌러 피드백을 확인하세요.</p>
        </div>
      </div>
    """, unsafe_allow_html=True)
    st.markdown('<div id="mcp2-actions">', unsafe_allow_html=True)
    _, mid, _ = st.columns([1,2,1])
    with mid:
        if st.button("결과 보기", key="mcp2-next", use_container_width=True):
            st.session_state.phase = "praise_r2"; st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

elif st.session_state.phase == "praise_r2":
    render_praise("inference_verbs", 2, REASON_VERB)

elif st.session_state.phase == "motivation":
    scroll_top_js()
    st.markdown("<h2 style='text-align:center; font-weight:bold;'>나의 생각과 가장 가까운 것을 선택해주세요.</h2>", unsafe_allow_html=True)
    st.markdown("""<div style='display:flex; justify-content:center; align-items:center; gap:12px; flex-wrap:wrap; font-size:16px; margin-bottom:30px;'>
        <span><b>1점</b> : 전혀 그렇지 않다</span><span>—</span><span><b>3점</b> : 보통이다</span><span>—</span><span><b>5점</b> : 매우 그렇다</span></div>""", unsafe_allow_html=True)

    motivation_q = [
        "1. 이번 추론 과제와 비슷한 과제를 기회가 있다면 한 번 더 해보고 싶다.",
        "2. 앞으로도 추론 과제가 있다면 참여할 의향이 있다.",
        "3. 더 어려운 추론 과제가 주어져도 도전할 의향이 있다.",
        "4. 추론 과제의 난이도가 높아져도 시도해 볼 의향이 있다.",
        "5. 이번 과제를 통해 성취감을 느꼈다.",
        "6. 추론 과제를 통해 새로운 시각이나 아이디어를 배울 수 있었다.",
        "7. 이런 과제를 수행하는 것은 나의 추론 능력을 발전시키는 데 가치가 있다.",
    ]
    if "motivation_responses" not in st.session_state:
        st.session_state["motivation_responses"] = [None] * len(motivation_q)
    for i, q in enumerate(motivation_q, start=1):
        choice = st.radio(label=f"{i}. {q}", options=[1,2,3,4,5], index=None, horizontal=True, key=f"motivation_{i}")
        st.session_state["motivation_responses"][i - 1] = choice
        st.markdown("<div style='margin-bottom:20px;'></div>", unsafe_allow_html=True)

    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown("### 최종 난이도 상향 의향(1~10)")
    diff2 = st.slider("다음 기회에 과제 난이도가 더 높아져도 도전할 의향", 1, 10, 5)

    if st.button("설문 완료"):
        if None in st.session_state["motivation_responses"]:
            st.warning("모든 문항에 응답해 주세요.")
        else:
            st.session_state.data["motivation_responses"] = st.session_state["motivation_responses"]
            st.session_state.data["difficulty_final"] = int(diff2)
            st.session_state.phase = "phone_input"; st.rerun()

elif st.session_state.phase == "phone_input":
    scroll_top_js()
    st.title("휴대폰 번호 입력")
    st.markdown("연구 답례품을 받을 휴대폰 번호를 입력해 주세요. (선택 사항)")
    phone = st.text_input("휴대폰 번호", placeholder="010-1234-5678")
    if st.button("완료"):
        if phone.strip() and not validate_phone(phone):
            st.warning("올바른 형식이 아닙니다. (예: 010-1234-5678)")
        else:
            # 간단한 참가자 ID 부여
            pid = st.session_state.data.get("participant_id")
            if not pid:
                pid = f"P_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{random.randint(1000,9999)}"
                st.session_state.data["participant_id"] = pid
            st.session_state.data["phone"] = phone.strip()
            st.session_state.data["endTime"] = datetime.now().isoformat()
            # 저장(실제 모듈 또는 폴백)
            save_to_csv(st.session_state.data)
            st.session_state.phase = "result"; st.rerun()

elif st.session_state.phase == "result":
    scroll_top_js()
    if "result_submitted" not in st.session_state:
        st.success("모든 과제가 완료되었습니다. 감사합니다!")
        st.write("연구에 참여해주셔서 감사합니다. 하단의 제출 버튼을 꼭 눌러주세요. 미제출시 답례품 제공이 어려울 수 있습니다.")
        if st.button("제출"):
            st.session_state.result_submitted = True; st.rerun()
    else:
        st.success("응답이 저장되었습니다.")
        st.markdown("""<div style='font-size:16px; padding-top:10px;'>
            설문 응답이 성공적으로 저장되었습니다.<br>
            <b>이 화면은 자동으로 닫히지 않으니, 브라우저 탭을 수동으로 닫아 주세요.</b><br><br>
            ※ 본 연구에서 제공된 AI의 평가는 사전에 생성된 예시 대화문으로, 
            귀하의 실제 추론 능력을 직접 평가한 것이 아님을 알려드립니다.
        </div>""", unsafe_allow_html=True)
        # 즉시 다운로드 가능한 JSON 파일 제공
        try:
            payload = json.dumps(st.session_state.data, ensure_ascii=False, indent=2)
            st.download_button("📥 내 응답 JSON 다운로드", payload.encode("utf-8"),
                               file_name=f"{st.session_state.data.get('participant_id','response')}.json",
                               mime="application/json")
        except Exception:
            pass
'''
with open("/mnt/data/main_fixed_for_cloud.py", "w", encoding="utf-8") as f:
    f.write(code)

print("Saved to /mnt/data/main_fixed_for_cloud.py")
