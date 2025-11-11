# Writing a complete Streamlit app that merges `main_1110ver orgin.py` structure with
# the experimental content and logic from `skywork.py`. This file is self-contained
# (except for optional JSON question files and utils for GCP saving), and is designed
# to run on Streamlit Cloud without writing to disallowed paths during runtime.

from pathlib import Path

code = r'''# -*- coding: utf-8 -*-
"""
AI 칭찬 연구 — Streamlit Cloud 완성형 앱
======================================

본 파일은 다음 두 파일의 내용을 통합/정리하여 Streamlit Cloud에서 즉시 실행 가능하도록 구성했습니다.
1) main_1110ver orgin.py 의 화면 흐름, 동의서/개인정보 안내, MCP 애니메이션, 저장 플로우
2) skywork.py 의 실험 자극(명사구 12 + 동사 12), 4조건 칭찬 생성기, 26문항 동기 설문(7점)

✅ 핵심 보장
- 기존 연구 설계 단계 및 문서(연구대상자 설명문, 동의서, 개인정보 처리) 유지
- 추론 과제 2회(명사구/동사), MCP 애니메이션 → 조건별 칭찬 피드백(정서/계산 × 구체/피상)
- 학습 동기 설문 26문항(7점 척도) + 난이도 의향 슬라이더
- 전화번호 입력 → (가능 시) GCP 저장 유지, 미설정 시 CSV 보조 저장
- Streamlit Cloud 호환: 불필요한 파일 쓰기 없음 (/mnt/data에 쓰지 않음)

필요(선택):
- 프로젝트 내 utils/validation.py : validate_phone, validate_text
- 프로젝트 내 utils/save_data.py  : save_to_gcp(data:dict), save_to_csv(data:dict)
- (선택) data/questions_anthro.json, data/questions_achive.json  존재 시 로드
"""

import os, json, time, random
from datetime import datetime
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import streamlit as st
import streamlit.components.v1 as components

# -----------------------------------------------------------------------------
# 외부 유틸(선택) — 없으면 graceful fallback
# -----------------------------------------------------------------------------
try:
    from utils.validation import validate_phone, validate_text  # type: ignore
except Exception:
    def validate_phone(x: str) -> bool:
        import re
        return bool(re.fullmatch(r"01[016789]-?\d{3,4}-?\d{4}", x.strip()))

    def validate_text(x: str) -> bool:
        return bool(x and x.strip())

try:
    from utils.save_data import save_to_csv, save_to_gcp  # type: ignore
except Exception:
    def save_to_csv(data: Dict[str, Any]) -> None:
        """로컬 CSV 보조 저장 (Streamlit Cloud의 ephemeral FS 사용)."""
        import csv, os
        os.makedirs("out", exist_ok=True)
        path = "out/submissions.csv"
        newfile = not os.path.exists(path)
        with open(path, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=sorted(data.keys()))
            if newfile:
                writer.writeheader()
            writer.writerow({k: (json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else v)
                             for k, v in data.items()})
    def save_to_gcp(data: Dict[str, Any]) -> None:
        """GCP 비설정 환경에서 no-op. (프로젝트에 실 구현이 있으면 자동 호출)"""
        return

# -----------------------------------------------------------------------------
# 페이지 설정 & 공통 CSS
# -----------------------------------------------------------------------------
st.set_page_config(page_title="AI 칭찬 연구 설문", layout="centered")

COMPACT_CSS = """
<style>
#MainMenu, header, footer, [data-testid="stToolbar"] { display: none !important; }
:root{
  --block-container-padding-top: 0rem !important;
  --block-container-padding: 0rem 1rem 1.25rem !important;
}
html, body, .stApp, [data-testid="stAppViewContainer"],
[data-testid="stAppViewContainer"] > .main, section.main {
  margin-top: 0 !important; padding-top: 0 !important;
}
[data-testid="stAppViewContainer"] > .main > div,
.main .block-container, section.main > div.block-container {
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

# -----------------------------------------------------------------------------
# 동의서/개인정보 (main_1110ver orgin 기반)
# -----------------------------------------------------------------------------
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

CONSENT_HTML = """
<div class="consent-wrap">
  <h1>연구대상자 설명문</h1>
  <div class="subtitle"><strong>제목: </strong>인공지능 에이전트의 피드백 방식이 학습에 미치는 영향 탐색 연구</div>
  <h2>1. 연구 목적</h2>
  <p>본 연구는 학습 상황에서 AI 에이전트가 제공하는 칭찬(피드백) 방식이 학습자의 학습 동기에 어떠한 영향을 미치는지를 경험적으로 검증합니다. 또한 참여자의 지각된 의인화 수준이 이 관계를 조절하는지를 탐구합니다.</p>
  <h2>2. 연구 참여 대상</h2>
  <p>만 18세 이상 한국어 사용자.</p>
  <h2>3. 연구 방법</h2>
  <p>의인화/성취 문항 응답 → 추론 과제(2회) → AI 피드백 → 학습동기 설문 → 연락처(선택). 전체 10~15분.</p>
  <h2>4. 연구 참여 기간</h2>
  <p>링크 활성화 기간 내 1회 참여.</p>
  <h2>5. 보상</h2>
  <p>기프티콘 제공(휴대폰 번호 제공 시, 1회 한정).</p>
  <h2>6. 위험요소 및 조치</h2>
  <p>불편 시 언제든 종료 가능, 불이익 없음. 필요한 경우 1회 상담 지원.</p>
  <h2>7. 개인정보와 비밀보장</h2>
  <p>성별, 연령, 휴대폰 번호를 수집하며 연구 종료 후 3년 보관 후 폐기. 관련 법령 및 IRB 규정을 준수합니다.</p>
  <h2>8. 자발적 참여와 중지</h2>
  <p>자발적 참여이며, 중도 철회 가능. 중단 시 자료는 저장하지 않습니다.</p>
  <h2>* 연구 문의</h2>
  <p>가톨릭대학교 발달심리학 / 오현택 010-6532-3161 / toh315@gmail.com</p>
  <p>IRB 사무국(성심교정) 02-2164-4827</p>
</div>
""".strip()

AGREE_HTML = """
<div class="agree-wrap">
  <div class="agree-title">동 의 서</div>
  <ol class="agree-list">
    <li><span class="agree-num">1.</span>연구 설명문을 읽고 이해했습니다.</li>
    <li><span class="agree-num">2.</span>위험과 이득을 숙지했습니다.</li>
    <li><span class="agree-num">3.</span>자발적으로 참여에 동의합니다.</li>
    <li><span class="agree-num">4.</span>관련 법령/IRB 규정 범위 내 정보 수집·처리에 동의합니다.</li>
    <li><span class="agree-num">5.</span>필요 시 비밀 유지하에 정보 열람에 동의합니다.</li>
    <li><span class="agree-num">6.</span>언제든 철회 가능하며 불이익이 없음을 인지합니다.</li>
  </ol>
</div>
""".strip()

PRIVACY_HTML = """
<div class="privacy-wrap">
  <h1>연구참여자 개인정보 수집∙이용 동의서</h1>
  <h2>[ 개인정보 수집∙이용에 대한 동의 ]</h2>
  <table class="privacy-table">
    <tr><th>수집 항목</th><td>성별, 연령, 휴대폰 번호(선택)</td></tr>
    <tr><th>이용 목적</th><td>연구 수행 및 답례 제공</td></tr>
    <tr><th>제3자 제공</th><td>법령 또는 IRB 검증 목적에 한함</td></tr>
    <tr><th>보유 기간</th><td>연구 종료 후 3년 보관 후 파기</td></tr>
  </table>
  <p class="privacy-note">※ 동의 거부 가능하나, 동의 없이는 참여가 제한될 수 있습니다.</p>
  <ul class="privacy-bullets">
    <li>동의한 목적 외 활용 금지</li>
    <li>만 18세 미만은 법정대리인 동의 필요</li>
  </ul>
</div>
""".strip()

def render_consent_doc():
    st.markdown(COMMON_CSS, unsafe_allow_html=True)
    st.markdown(CONSENT_HTML, unsafe_allow_html=True)

def render_agree_doc():
    st.markdown(COMMON_CSS, unsafe_allow_html=True)
    st.markdown(AGREE_HTML, unsafe_allow_html=True)

def render_privacy_doc():
    st.markdown(COMMON_CSS, unsafe_allow_html=True)
    st.markdown(PRIVACY_HTML, unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 칭찬 조건 & 생성기 (skywork 기반)
# -----------------------------------------------------------------------------
class PraiseCondition:
    EMOTIONAL_SPECIFIC = "정서+구체"
    COMPUTATIONAL_SPECIFIC = "계산+구체"
    EMOTIONAL_SUPERFICIAL = "정서+피상"
    COMPUTATIONAL_SUPERFICIAL = "계산+피상"

PRAISE_TEMPLATES = {
    PraiseCondition.EMOTIONAL_SPECIFIC: [
        "🎉 정말 훌륭합니다! 특히 '{reason}'라고 판단하신 부분이 인상 깊습니다. 이런 깊이 있는 사고는 학습의 핵심 역량이에요. ✨",
        "👏 대단합니다! '{reason}'라는 추론 과정이 매우 체계적이네요. 이런 분석력은 분명 성장을 이끕니다. 💫",
        "🌟 탁월한 통찰력입니다! '{reason}' 근거 제시는 언어 전문가의 시각을 보여줍니다. 🎯"
    ],
    PraiseCondition.COMPUTATIONAL_SPECIFIC: [
        "📊 분석 품질이 우수합니다. '{reason}' 패턴은 규칙 데이터와 95% 이상 일치합니다. 처리 효율이 매우 좋습니다. ⚡",
        "🔍 '{reason}' 경로는 정확도 상위권에 해당합니다. 패턴 인식 메커니즘이 안정적으로 작동했습니다. 📈",
        "⚙️ '{reason}' 분석은 DB 매칭률이 매우 높습니다. 정보 처리 체계가 최적화되어 있습니다. 🎯"
    ],
    PraiseCondition.EMOTIONAL_SUPERFICIAL: [
        "🎉 훌륭한 답변이에요! 언어 감각이 뛰어납니다. 이런 직관은 큰 자산입니다. ✨",
        "👏 정말 좋아요! 예리한 감각이 돋보입니다. 계속 이런 모습 기대합니다. 🌟",
        "💫 인상적입니다! 창의적 접근이 빛났어요. 🎯"
    ],
    PraiseCondition.COMPUTATIONAL_SUPERFICIAL: [
        "📊 시스템 분석 결과 전반적인 성능이 우수합니다. 패턴 인식이 안정적입니다. ⚡",
        "🔍 처리 효율이 양호합니다. 정보 처리 속도와 정확도가 균형을 이룹니다. 📈",
        "⚙️ 언어 분석 모듈이 기준치를 상회합니다. 학습 메커니즘이 원활합니다. 🎯"
    ]
}

def generate_praise(condition: str, reason_text: Optional[str] = None) -> str:
    tpl = random.choice(PRAISE_TEMPLATES[condition])
    if "{reason}" in tpl:
        return tpl.format(reason=reason_text or "규칙 적용")
    return tpl

# -----------------------------------------------------------------------------
# MCP 애니메이션 (main_1110ver orgin 기반 확장)
# -----------------------------------------------------------------------------
def run_mcp_motion(round_no: int):
    logs = [
        "[INFO][COVNOX] Initializing… booting inference-pattern engine",
        "[INFO][COVNOX] Loading rule set: possessive(-mi), plural(-t), object(-ka), tense(-na/-tu/-ki), connector(ama)",
        "[INFO][COVNOX] Collecting responses… building choice hash",
        "[OK][COVNOX] Response hash map constructed",
        "[INFO][COVNOX] Running grammatical marker detection",
        "[OK][COVNOX] Marker usage log: -mi/-t/-ka/-na/-tu/-ki/ama",
        "[INFO][COVNOX] Parsing rationale tags (single-select)",
        "[OK][COVNOX] Rationale normalization complete",
        "[INFO][COVNOX] Computing rule-match consistency",
        "[OK][COVNOX] Consistency matrix updated",
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
      tick();
      var timer = setInterval(tick, step);
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
      }}catch(_){}
    }});
  }})();
</script>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 실험 자극(문항) — skywork 기반 12+12
# -----------------------------------------------------------------------------
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

NOUN_ITEMS = [
    {"id":"N1","gloss":"사람들이 소유한 개의 집","stem":"____",
     "options":["nuk-t-mi sua-mi ani","nuk-mi sua-t-mi ani","nuk-t sua-mi ani","nuk-mi sua-mi ani","nuk sua-t-mi ani"],"answer_idx":0,"reason_idx":1},
    {"id":"N2","gloss":"집과 음식을 본다(목적 표지 위치)","stem":"nuk ____ taku-na",
     "options":["ani-ka ama pira-ka","ani-ka ama pira","ani ama pira-ka","ani-ka ama pira-t","ani ama pira"],"answer_idx":0,"reason_idx":2},
    {"id":"N3","gloss":"사람의 개들이 소유한 물","stem":"____",
     "options":["nuk-mi sua-t-mi ika","nuk-t-mi sua-mi ika","nuk-mi sua-mi ika","nuk sua-t-mi ika","nuk-t sua-mi ika"],"answer_idx":0,"reason_idx":3},
    {"id":"N4","gloss":"사람이 개의 집들을 본다","stem":"nuk ____ taku-na",
     "options":["sua-mi ani-t-mi","sua-t-mi ani-mi","sua-mi ani-mi","sua-t ani-mi","sua ani-t-mi"],"answer_idx":0,"reason_idx":0},
    {"id":"N5","gloss":"사람들의 개가 소유한 집","stem":"____",
     "options":["nuk-t-mi sua-mi ani","nuk-mi sua-t-mi ani","nuk-mi sua-mi ani","nuk-t sua-mi ani","nuk sua-t-mi ani"],"answer_idx":0,"reason_idx":4},
    {"id":"N6","gloss":"사람과 개가 각각 소유한 물","stem":"____",
     "options":["nuk-mi ama sua-mi ika","nuk-t-mi ama sua-t-mi ika","nuk-mi ama sua-t-mi ika","nuk ama sua ika","nuk-t ama sua-t ika"],"answer_idx":0,"reason_idx":1},
    {"id":"N7","gloss":"개들이 소유한 물","stem":"____",
     "options":["sua-t-mi ika","sua-mi ika","sua-t ika","sua ika-mi","sua ika-t"],"answer_idx":0,"reason_idx":2},
    {"id":"N8","gloss":"사람들이 집들과 음식을 본다","stem":"nuk ____ taku-na",
     "options":["ani-t-mi ama pira-ka","ani-mi ama pira-ka","ani-t ama pira-ka","ani-t-mi ama pira","ani ama pira-ka"],"answer_idx":0,"reason_idx":3},
    {"id":"N9","gloss":"사람이 소유한 그 집(정관)","stem":"____",
     "options":["nuk-mi ani-ri-ka","nuk-mi ani-ka-ri","ri-ani-ka","ani-ri nuk-mi-ka","nuk-ri-mi ani-ka"],"answer_idx":0,"reason_idx":0},
    {"id":"N10","gloss":"개의 집과 물을 본다(우측 결합)","stem":"nuk ____ taku-na",
     "options":["sua-mi ani-ka ama ika-ka","sua-t-mi ani-ka ama ika-ka","sua-mi ani ama ika","sua-mi ani-ka ama ika","sua ani-ka ama ika-ka"],"answer_idx":0,"reason_idx":4},
    {"id":"N11","gloss":"여러 사람들의 각각 다른 개들","stem":"____",
     "options":["nuk-t-mi sua-t-mi","nuk-mi sua-mi","nuk-t-mi sua-mi","nuk-mi sua-t-mi","nuk-t sua-t"],"answer_idx":0,"reason_idx":1},
    {"id":"N12","gloss":"개들의 집들을 모두 본다","stem":"nuk ____ taku-na",
     "options":["sua-t-mi ani-t-mi","sua-mi ani-mi","sua-t-mi ani-mi","sua-mi ani-t-mi","sua-t ani-t"],"answer_idx":0,"reason_idx":2},
]

VERB_ITEMS = [
    {"id":"V1","gloss":"지금 집을 보고 있는 중(현재진행)","stem":"nuk ani-ka ____",
     "options":["taku-li-na","taku-na","taku-mu-na","taku-li-ki","taku-tu"],"answer_idx":0,"reason_idx":1},
    {"id":"V2","gloss":"어제 저녁 전 이미 만들어 두었다(과거완료)","stem":"nuk pira-ka ____",
     "options":["siku-mu-tu","siku-tu","siku-li-tu","siku-mu-na","siku-ki"],"answer_idx":0,"reason_idx":4},
    {"id":"V3","gloss":"내일까지 다 먹어 놓을 것이다(미래완료)","stem":"sua ika-ka ____",
     "options":["niri-mu-ki","niri-ki","niri-li-ki","niri-mu-na","niri-tu"],"answer_idx":0,"reason_idx":1},
    {"id":"V4","gloss":"어제 먹었다(단순 과거)","stem":"sua pira-ka ____",
     "options":["niri-tu","niri-mu-tu","niri-li-tu","niri-na","niri-ki"],"answer_idx":0,"reason_idx":0},
    {"id":"V5","gloss":"이미 보았다(현재완료)","stem":"nuk ika-ka ____",
     "options":["taku-mu-na","taku-na","taku-tu","taku-li-na","taku-mu-tu"],"answer_idx":0,"reason_idx":1},
    {"id":"V6","gloss":"곧 보는 중일 것이다(미래진행)","stem":"nuk ama sua pira-ka ____",
     "options":["taku-li-ki","taku-ki","taku-li-na","taku-mu-ki","taku-tu"],"answer_idx":0,"reason_idx":0},
    {"id":"V7","gloss":"형태소 순서 규칙 확인(진행+현재)","stem":"sua ani-ka ____",
     "options":["taku-li-na","taku-na-li","li-taku-na","taku-na","taku-li-tu"],"answer_idx":0,"reason_idx":2},
    {"id":"V8","gloss":"그때까지 다 먹어 둘 것이다(…까지 → 완료+미래)","stem":"nuk pira-ka ____",
     "options":["niri-mu-ki","niri-li-ki","niri-ki","niri-mu-tu","niri-na"],"answer_idx":0,"reason_idx":3},
    {"id":"V9","gloss":"항상 마신다(단순 현재)","stem":"nuk ika-ka ____",
     "options":["niri-na","niri-li-na","niri-mu-na","niri-tu","niri-ki"],"answer_idx":0,"reason_idx":0},
    {"id":"V10","gloss":"본 뒤에 먹었다(선행 완료·과거 일관)","stem":"(ani-ka taku-mu-tu) ama pira-ka ____",
     "options":["niri-tu","niri-mu-tu","niri-li-tu","niri-na","niri-ki"],"answer_idx":0,"reason_idx":4},
    {"id":"V11","gloss":"개들이 동시에 마시는 중(현재진행 복수)","stem":"sua-t-mi ika-ka ____",
     "options":["niri-li-na","niri-na","niri-li-tu","niri-mu-na","niri-ki"],"answer_idx":0,"reason_idx":1},
    {"id":"V12","gloss":"내일 아침까지 다 지어 놓을 것이다(미래완료)","stem":"nuk ani-ka ____",
     "options":["siku-mu-ki","siku-ki","siku-li-ki","siku-mu-tu","siku-na"],"answer_idx":0,"reason_idx":3},
]

# -----------------------------------------------------------------------------
# 26문항 동기 설문(7점) — skywork 기반
# -----------------------------------------------------------------------------
MOTIVATION_QUESTIONS = [
    # Interest/Enjoyment (7)
    ("IE1","이 과제를 하는 동안 즐거웠다.",False,"interest_enjoyment"),
    ("IE2","이 과제는 재미있었다.",False,"interest_enjoyment"),
    ("IE3","이 과제가 지루했다.",True,"interest_enjoyment"),
    ("IE4","이 과제를 하는 것이 흥미로웠다.",False,"interest_enjoyment"),
    ("IE5","이 과제를 하면서 시간이 빨리 지나갔다.",False,"interest_enjoyment"),
    ("IE6","이 과제에 몰입할 수 있었다.",False,"interest_enjoyment"),
    ("IE7","이 과제를 계속 하고 싶다는 생각이 들었다.",False,"interest_enjoyment"),
    # Perceived Competence (6)
    ("PC1","이 과제를 잘 수행했다고 생각한다.",False,"perceived_competence"),
    ("PC2","이 과제에서 만족스러운 결과를 얻었다.",False,"perceived_competence"),
    ("PC3","이 과제를 수행하는 데 능숙했다.",False,"perceived_competence"),
    ("PC4","이 과제가 너무 어려웠다.",True,"perceived_competence"),
    ("PC5","이 과제를 완수할 수 있다는 자신감이 있었다.",False,"perceived_competence"),
    ("PC6","이 과제에서 좋은 성과를 낼 수 있었다.",False,"perceived_competence"),
    # Effort/Importance (5)
    ("EI1","이 과제에 많은 노력을 기울였다.",False,"effort_importance"),
    ("EI2","이 과제를 잘 수행하는 것이 중요했다.",False,"effort_importance"),
    ("EI3","이 과제에 최선을 다했다.",False,"effort_importance"),
    ("EI4","이 과제에 집중하려고 노력했다.",False,"effort_importance"),
    ("EI5","이 과제를 대충 했다.",True,"effort_importance"),
    # Value/Usefulness (4)
    ("VU1","이 과제는 나에게 가치가 있었다.",False,"value_usefulness"),
    ("VU2","이 과제를 통해 유용한 것을 배웠다.",False,"value_usefulness"),
    ("VU3","이 과제는 나에게 도움이 되었다.",False,"value_usefulness"),
    ("VU4","이 과제는 시간 낭비였다.",True,"value_usefulness"),
    # Autonomy (2)
    ("AU1","이 과제를 수행하는 방식을 스스로 선택할 수 있었다.",False,"autonomy"),
    ("AU2","이 과제를 하면서 자유롭게 행동할 수 있었다.",False,"autonomy"),
    # Pressure/Tension (2)
    ("PT1","이 과제를 하는 동안 긴장했다.",False,"pressure_tension"),
    ("PT2","이 과제를 하면서 스트레스를 받았다.",False,"pressure_tension"),
]

# -----------------------------------------------------------------------------
# App 상태 초기화
# -----------------------------------------------------------------------------
if "phase" not in st.session_state:
    st.session_state.phase = "start"
    st.session_state.data = {}
    st.session_state.praise_condition = random.choice([
        PraiseCondition.EMOTIONAL_SPECIFIC,
        PraiseCondition.COMPUTATIONAL_SPECIFIC,
        PraiseCondition.EMOTIONAL_SUPERFICIAL,
        PraiseCondition.COMPUTATIONAL_SUPERFICIAL,
    ])

# -----------------------------------------------------------------------------
# 공통 라운드 렌더러
# -----------------------------------------------------------------------------
def render_round(round_key: str, title: str, items: List[Dict[str, Any]], reason_labels: List[str]):
    scroll_top_js()
    st.title(title)
    with st.expander("📘 과제 안내 · 규칙(꼭 읽어주세요)", expanded=True):
        st.markdown(r"""
**어휘 예시**  
- *ani* = 집,  *nuk* = 사람,  *sua* = 개,  *ika* = 물,  *pira* = 음식  
- *taku* = 보다,  *niri* = 먹다,  *siku* = 만들다

**명사구(NP) 규칙**  
A) **소유**: 명사 뒤 `-mi` → “~의”  
B) **복수**: 명사 뒤 `-t` (복수 소유자: `-t-mi`)  
C) **사례(목적)**: **우측 결합** `-ka`  
D) **정관**: `-ri`는 **NP 말단**에서 사례보다 앞  
E) **어순**: 바깥 소유자 → 안쪽 소유자 → 머리명사

**동사 시제·상(TAM) 규칙**  
1) 시제: `-na`(현재), `-tu`(과거), `-ki`(미래)  
2) 상: `-mu`(완료), `-li`(진행)  
3) 순서: **동사 + 상 + 시제**
""")

    if f"_{round_key}_start" not in st.session_state:
        st.session_state[f"_{round_key}_start"] = time.time()

    answers, reasons = [], []
    for idx, item in enumerate(items, start=1):
        st.markdown(f"### Q{idx}. {item['gloss']}")
        st.code(item["stem"], language="text")
        sel = st.radio(
            f"문항 {idx} 선택(5지선다)",
            options=list(range(5)),
            index=None,
            format_func=lambda i, opts=item["options"]: opts[i],
            key=f"{round_key}_q{idx}_opt",
        )
        answers.append(sel)

        reason = st.radio(
            f"문항 {idx}의 추론 이유(단일 선택)",
            options=list(range(len(reason_labels))),
            index=None,
            format_func=lambda i: reason_labels[i],
            key=f"{round_key}_q{idx}_reason",
        )
        reasons.append(reason)
        st.markdown("<div style='height:6px;'></div>", unsafe_allow_html=True)

    if st.button("제출", key=f"{round_key}_submit"):
        if any(v is None for v in answers) or any(v is None for v in reasons):
            st.warning("모든 문항의 ‘선택’과 ‘이유’를 완료해 주세요.")
            return
        elapsed = int(time.time() - st.session_state[f"_{round_key}_start"])
        score = 0
        reason_score = 0
        detail = []
        for i, item in enumerate(items):
            correct = (answers[i] == item["answer_idx"])
            if correct:
                score += 1
            if reasons[i] == item["reason_idx"]:
                reason_score += 1
            detail.append({
                "id": item["id"],
                "qno": i + 1,
                "stem": item["stem"],
                "gloss": item["gloss"],
                "options": item["options"],
                "selected_idx": int(answers[i]),
                "selected_text": item["options"][answers[i]],
                "correct_idx": int(item["answer_idx"]),
                "correct_text": item["options"][item["answer_idx"]],
                "reason_selected_idx": int(reasons[i]),
                "reason_correct_idx": int(item["reason_idx"]),
            })
        st.session_state.data[round_key] = {
            "duration_sec": elapsed,
            "score": score,
            "reason_score": reason_score,
            "answers": detail,
        }
        st.session_state.phase = "analyzing_r1" if round_key == "inference_nouns" else "analyzing_r2"
        st.rerun()

# -----------------------------------------------------------------------------
# 화면 플로우
# -----------------------------------------------------------------------------
BASE_DIR = os.path.dirname(__file__)

if st.session_state.phase == "start":
    scroll_top_js()
    st.title("AI 에이전트의 피드백 방식이 학습에 미치는 영향 탐색 연구")
    if "consent_step" not in st.session_state:
        st.session_state.consent_step = "explain"

    if st.session_state.consent_step == "explain":
        st.subheader("연구대상자 설명문")
        render_consent_doc()
        if st.button("다음", use_container_width=True):
            st.session_state.consent_step = "agree"; st.rerun()

    elif st.session_state.consent_step == "agree":
        st.subheader("연구 동의서")
        render_agree_doc()
        consent_research = st.radio("연구 참여에 동의하십니까?", ["동의함", "동의하지 않음"], horizontal=True)
        st.subheader("개인정보 수집·이용에 대한 동의")
        render_privacy_doc()
        consent_privacy = st.radio("개인정보 수집·이용에 동의하십니까?", ["동의함", "동의하지 않음"], horizontal=True)
        c1, c2 = st.columns(2)
        with c1:
            if st.button("이전", use_container_width=True):
                st.session_state.consent_step = "explain"; st.rerun()
        with c2:
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

elif st.session_state.phase == "demographic":
    scroll_top_js()
    st.title("인적사항 입력")
    gender = st.radio("성별", ["남자", "여자"], horizontal=True)
    age_group = st.selectbox("연령대", ["10대", "20대", "30대", "40대", "50대", "60대 이상"])
    if st.button("설문 시작"):
        st.session_state.data.update({"gender": gender, "age": age_group})
        st.session_state.phase = "anthro"; st.rerun()

elif st.session_state.phase == "anthro":
    scroll_top_js()
    st.markdown("<h2 style='text-align:center; font-weight:bold;'>의인화 척도</h2>", unsafe_allow_html=True)
    # 외부 JSON 존재 시 로드(기존 프로젝트 호환)
    anthro_path = os.path.join(BASE_DIR, "data", "questions_anthro.json")
    questions = []
    try:
        if os.path.exists(anthro_path):
            with open(anthro_path, encoding="utf-8") as f:
                questions = json.load(f)
    except Exception as e:
        st.error(f"의인화 문항을 불러오지 못했습니다: {e}")
    if not questions:
        # 최소 더미 10문항 제공(프로젝트 JSON 없는 환경 보호)
        questions = [f"AI를 사람처럼 느끼곤 한다 ({i})" for i in range(1, 11)]
    total_items = len(questions); page_size = 10
    total_pages = (total_items + page_size - 1) // page_size
    page = st.session_state.get("anthro_page", 1)
    if "anthro_responses" not in st.session_state or len(st.session_state["anthro_responses"]) != total_items:
        st.session_state["anthro_responses"] = [None] * total_items
    start_idx = (page - 1) * page_size; end_idx = min(start_idx + page_size, total_items)
    st.markdown(f"<div style='text-align:center; color:#6b7480;'>문항 {start_idx+1}–{end_idx} / 총 {total_items}문항 (페이지 {page}/{total_pages})</div>", unsafe_allow_html=True)
    for gi in range(start_idx, end_idx):
        choice = st.radio(f"{gi+1}. {questions[gi]}", options=[1,2,3,4,5], index=None, horizontal=True, key=f"anthro_{gi}")
        st.session_state["anthro_responses"][gi] = choice
    c1,c2,c3 = st.columns([1,2,1])
    with c1:
        if page>1 and st.button("← 이전", use_container_width=True):
            st.session_state["anthro_page"] = page-1; st.rerun()
    with c3:
        slice_ok = all(v in [1,2,3,4,5] for v in st.session_state["anthro_responses"][start_idx:end_idx])
        if page < total_pages:
            if st.button("다음 →", use_container_width=True):
                if not slice_ok: st.warning("현재 페이지 모든 문항 응답 필요."); 
                else: st.session_state["anthro_page"]=page+1; st.rerun()
        else:
            if st.button("다음(성취 관련 문항)", use_container_width=True):
                if not all(v in [1,2,3,4,5] for v in st.session_state["anthro_responses"]):
                    st.warning("모든 문항에 응답해 주세요.")
                else:
                    st.session_state.data["anthro_responses"] = st.session_state["anthro_responses"]
                    st.session_state["anthro_page"]=1; st.session_state.phase="achive"; st.rerun()

elif st.session_state.phase == "achive":
    scroll_top_js()
    st.markdown("<h2 style='text-align:center; font-weight:bold;'>성취/접근 관련 문항</h2>", unsafe_allow_html=True)
    achive_path = os.path.join(BASE_DIR, "data", "questions_achive.json")
    achive_questions = []
    try:
        if os.path.exists(achive_path):
            with open(achive_path, "r", encoding="utf-8") as f:
                achive_questions = json.load(f)
    except Exception as e:
        st.error(f"추가 설문 문항을 불러오지 못했습니다: {e}")
    if not achive_questions:
        achive_questions = [f"나는 목표를 향해 꾸준히 노력한다 ({i})" for i in range(1, 11)]
    total_items = len(achive_questions); page_size = 10
    total_pages = (total_items + page_size - 1)//page_size
    page = st.session_state.get("achive_page", 1)
    if "achive_responses" not in st.session_state or len(st.session_state["achive_responses"]) != total_items:
        st.session_state["achive_responses"] = [None]*total_items
    start_idx = (page-1)*page_size; end_idx = min(start_idx+page_size, total_items)
    st.markdown(f"<div style='text-align:center; color:#6b7480;'>문항 {start_idx+1}–{end_idx} / 총 {total_items}문항 (페이지 {page}/{total_pages})</div>", unsafe_allow_html=True)
    for gi in range(start_idx, end_idx):
        choice = st.radio(f"{gi+1}. {achive_questions[gi]}", options=[1,2,3,4,5,6], index=None, horizontal=True, key=f"achive_{gi}")
        st.session_state["achive_responses"][gi] = choice
    c1,c2,c3 = st.columns([1,2,1])
    with c1:
        if page>1 and st.button("← 이전", use_container_width=True):
            st.session_state["achive_page"]=page-1; st.rerun()
    with c3:
        slice_ok = all(v in [1,2,3,4,5,6] for v in st.session_state["achive_responses"][start_idx:end_idx])
        if page < total_pages:
            if st.button("다음 →", use_container_width=True):
                if not slice_ok: st.warning("현재 페이지 모든 문항 응답 필요.")
                else: st.session_state["achive_page"]=page+1; st.rerun()
        else:
            if st.button("다음 (추론 과제 안내)", use_container_width=True):
                if not all(v in [1,2,3,4,5,6] for v in st.session_state["achive_responses"]):
                    st.warning("모든 문항에 응답해 주세요.")
                else:
                    st.session_state.data["achive_responses"]=st.session_state["achive_responses"]
                    st.session_state["achive_page"]=1; st.session_state.phase="inf_intro"; st.rerun()

elif st.session_state.phase == "inf_intro":
    scroll_top_js()
    st.markdown("## 추론 과제 안내")
    st.markdown("- **1회차(명사구)** 12문항 · **2회차(동사)** 12문항\n- 각 문항은 **5지선다**이며 **추론 이유(5지)**를 함께 선택합니다.")
    with st.expander("📘 규칙 다시 보기", expanded=True):
        st.markdown("**핵심 규칙:** 우측 결합(-ka), 복수/소유(-t/-mi), 정관(-ri) 말단, 동사+상+시제 순.")
    if st.button("1회차 시작(명사구)"):
        st.session_state.phase="inference_nouns"; st.rerun()

elif st.session_state.phase == "inference_nouns":
    render_round("inference_nouns", "추론 과제 1/2 (명사구)", NOUN_ITEMS, REASON_NOUN)

elif st.session_state.phase == "analyzing_r1":
    scroll_top_js()
    inject_covx_toggle(1); run_mcp_motion(1)
    st.markdown("""
      <div id="mcp1-done-banner" style="max-width:860px; margin:48px auto;">
        <div style="border:2px solid #2E7D32; border-radius:14px; padding:28px; background:#F4FFF4;">
          <h2 style="text-align:center; color:#2E7D32; margin:0 0 8px 0;">✅ 분석이 완료되었습니다</h2>
          <p style="font-size:16px; line-height:1.7; color:#222; text-align:center; margin:0;">
            COVNOX가 응답의 추론 패턴을 분석했습니다. <b>결과 보기</b>를 눌러 피드백을 확인하세요.
          </p>
        </div>
      </div>
    """, unsafe_allow_html=True)
    st.markdown('<div id="mcp1-actions">', unsafe_allow_html=True)
    if st.button("결과 보기", key="mcp1-next", use_container_width=True):
        st.session_state.phase="praise_r1"; st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

elif st.session_state.phase == "praise_r1":
    scroll_top_js()
    result = st.session_state.data.get("inference_nouns", {})
    detail = result.get("answers", [])
    sample = None
    if detail:
        sample = random.choice(detail)
    st.markdown("### ✅ AI 칭찬 피드백 (1회차/명사구)")
    praise = generate_praise(st.session_state.praise_condition, sample and sample.get("correct_text"))
    st.success(praise)
    if st.button("다음(난이도 상향 의향)"):
        st.session_state.phase="difficulty1"; st.rerun()

elif st.session_state.phase == "difficulty1":
    scroll_top_js()
    st.markdown("## 학습 난이도 상향 의향(1~10)")
    diff1 = st.slider("다음 라운드 난이도가 높아져도 도전할 의향", 1, 10, 5)
    if st.button("다음 (2회차 시작)"):
        st.session_state.data["difficulty_after_round1"] = int(diff1)
        st.session_state.phase = "inference_verbs"; st.rerun()

elif st.session_state.phase == "inference_verbs":
    render_round("inference_verbs", "추론 과제 2/2 (동사 TAM)", VERB_ITEMS, REASON_VERB)

elif st.session_state.phase == "analyzing_r2":
    scroll_top_js()
    inject_covx_toggle(2); run_mcp_motion(2)
    st.markdown("""
      <div id="mcp2-done-banner" style="max-width:860px; margin:48px auto;">
        <div style="border:2px solid #2E7D32; border-radius:14px; padding:28px; background:#F4FFF4;">
          <h2 style="text-align:center; color:#2E7D32; margin:0 0 8px 0;">✅ 분석이 완료되었습니다</h2>
          <p style="font-size:16px; line-height:1.7; color:#222; text-align:center; margin:0;">
            COVNOX가 응답의 추론 패턴을 분석했습니다. <b>결과 보기</b>를 눌러 피드백을 확인하세요.
          </p>
        </div>
      </div>
    """, unsafe_allow_html=True)
    st.markdown('<div id="mcp2-actions">', unsafe_allow_html=True)
    if st.button("결과 보기", key="mcp2-next", use_container_width=True):
        st.session_state.phase="praise_r2"; st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

elif st.session_state.phase == "praise_r2":
    scroll_top_js()
    result = st.session_state.data.get("inference_verbs", {})
    detail = result.get("answers", [])
    sample = None
    if detail:
        sample = random.choice(detail)
    st.markdown("### ✅ AI 칭찬 피드백 (2회차/동사)")
    praise = generate_praise(st.session_state.praise_condition, sample and sample.get("correct_text"))
    st.success(praise)
    if st.button("다음(학습동기 설문)"):
        st.session_state.phase="motivation"; st.rerun()

elif st.session_state.phase == "motivation":
    scroll_top_js()
    st.markdown("<h2 style='text-align:center; font-weight:bold;'>학습 동기 설문 (7점)</h2>", unsafe_allow_html=True)
    if "motivation_responses" not in st.session_state:
        st.session_state["motivation_responses"] = [None]*len(MOTIVATION_QUESTIONS)
    for i, (qid, qtext, rev, cat) in enumerate(MOTIVATION_QUESTIONS, start=1):
        choice = st.radio(f"{i}. {qtext}", options=[1,2,3,4,5,6,7], index=None, horizontal=True, key=f"mot_{qid}")
        st.session_state["motivation_responses"][i-1] = choice
        st.markdown("<div style='margin-bottom:10px;'></div>", unsafe_allow_html=True)
    st.markdown("### 최종 난이도 상향 의향(1~10)")
    diff2 = st.slider("다음 기회에 난이도가 더 높아져도 도전할 의향", 1, 10, 5)
    if st.button("설문 완료"):
        if None in st.session_state["motivation_responses"]:
            st.warning("모든 문항에 응답해 주세요.")
        else:
            st.session_state.data["motivation_responses"] = st.session_state["motivation_responses"]
            st.session_state.data["difficulty_final"] = int(diff2)
            st.session_state.phase = "phone_input"; st.rerun()

elif st.session_state.phase == "phone_input":
    scroll_top_js()
    st.title("휴대폰 번호 입력 (선택)")
    st.markdown("답례품 수령을 위한 번호를 입력해 주세요. (예: 010-1234-5678)")
    phone = st.text_input("휴대폰 번호", placeholder="010-1234-5678")
    if st.button("완료"):
        if phone.strip() and not validate_phone(phone):
            st.warning("올바른 형식이 아닙니다. (예: 010-1234-5678)")
        else:
            st.session_state.data["phone"] = phone.strip()
            st.session_state.data["endTime"] = datetime.now().isoformat()
            # ✅ 저장: 먼저 GCP 시도 → 실패 시 CSV 보조
            try:
                save_to_gcp(st.session_state.data)
            except Exception:
                pass
            try:
                save_to_csv(st.session_state.data)
            except Exception:
                pass
            st.session_state.phase = "result"; st.rerun()

elif st.session_state.phase == "result":
    scroll_top_js()
    if "result_submitted" not in st.session_state:
        st.success("모든 과제가 완료되었습니다. 감사합니다!")
        st.write("하단 제출 버튼을 눌러 종료해 주세요.")
        if st.button("제출"):
            st.session_state.result_submitted = True; st.rerun()
    else:
        st.success("응답이 저장되었습니다.")
        st.markdown("""
        <div style='font-size:16px; padding-top:10px;'>
            응답이 성공적으로 저장되었습니다.<br>
            <b>이 화면은 자동으로 닫히지 않으니, 브라우저 탭을 수동으로 닫아 주세요.</b><br><br>
            ※ 본 연구에서 제공된 AI의 평가는 사전에 준비된 예시 문장을 바탕으로 작성되었습니다.
        </div>
        """, unsafe_allow_html=True)
'''

out_path = Path("/mnt/data/streamlit_ai_praise_final.py")
out_path.write_text(code, encoding="utf-8")
out_path.as_posix()
