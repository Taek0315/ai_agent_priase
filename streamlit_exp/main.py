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

/* 4) 첫 요소 margin-collapsing으로 남는 여백 차단: 제목/문단 top 마진 정돈 */
h1, .stMarkdown h1 { margin-top: 0 !important; margin-bottom: 12px !important; line-height: 1.2; }
h2, .stMarkdown h2 { margin-top: 0 !important; margin-bottom: 10px !important; }
p, .stMarkdown p   { margin-top: 0 !important; }

/* 5) 사용자 정의 제목 클래스(anthro 등)도 상단 마진 제거 */
.anthro-title { margin-top: 0 !important; }

/* 6) 불필요한 수평 스크롤 방지 */
html, body { overflow-x: hidden !important; }
</style>
"""
st.markdown(COMPACT_CSS, unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────────────────
# 공통: 스크롤 항상 최상단
def scroll_top_js(nonce: int | None = None):
    """
    페이지가 렌더될 때마다 최상단으로 스크롤.
    - 부모 문서(section.main)와 iframe 내부(window) 둘 다 시도
    - 여러 타이밍에 재시도 (즉시/RAF/지연)
    - nonce를 넣어 매 호출마다 '새 스크립트'로 인식되도록 함
    """
    if nonce is None:
        nonce = st.session_state.get("_scroll_nonce", 0)

    st.markdown(
        f"""
        <script id="goTop-{nonce}">
        (function(){{
          function goTop() {{
            try {{
              // 부모 문서(스트림릿 실제 뷰) 스크롤
              var pdoc = window.parent && window.parent.document;
              var sect = pdoc && pdoc.querySelector && pdoc.querySelector('section.main');
              if (sect && sect.scrollTo) sect.scrollTo({{top:0, left:0, behavior:'instant'}});
            }} catch(e) {{}}

            try {{
              // iframe 내부(백업) 스크롤
              window.scrollTo({{top:0, left:0, behavior:'instant'}});
              document.documentElement && document.documentElement.scrollTo && document.documentElement.scrollTo(0,0);
              document.body && document.body.scrollTo && document.body.scrollTo(0,0);
            }} catch(e) {{}}
          }}

          // 즉시 실행 + 렌더 타이밍 대비 다회 실행
          goTop();
          if (window.requestAnimationFrame) requestAnimationFrame(goTop);
          setTimeout(goTop, 25);
          setTimeout(goTop, 80);
          setTimeout(goTop, 180);
          setTimeout(goTop, 320);
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
    # ✅ 집단 무작위 배정(노력 set1 / 능력 set2). 성과와 무관하게 세션 내 고정.
    st.session_state.feedback_set_key = random.choice(["set1", "set2"])
    # ✅ 2회차 과제 및 피드백 중복 방지용 상태
    st.session_state.used_feedback_indices = set()
    st.session_state.praise_once = False
    st.session_state.round1_started_ts = None
    st.session_state.round2_started_ts = None

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
def run_mcp_motion(duration_sec: float = 8.0):
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
        total = float(duration_sec)
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
# ① 연구대상자 설명문 / ② 연구 동의서 / ③ 개인정보 수집·이용 동의서
# ─────────────────────────────────────────────

CONSENT_HTML = """
<div class="consent-wrap">

  <h1>연구대상자 설명문</h1>

  <div class="subtitle"><strong>제목: </strong>AI 에이전트의 피드백 방식이 학습에 미치는 영향 탐색 연구</div>

  <h2>1. 연구 목적</h2>
  <p>최근 과학기술의 발전과 함께 인공지능(AI)은 교육, 상담, 서비스 등 다양한 환경에서 폭넓게 활용되고 있습니다. 특히 학습 환경에서 AI 에이전트는 단순 정보 전달자 역할을 넘어, 학습자의 성취와 노력을 평가하고 동기를 촉진하는 상호작용 주체로 주목받고 있습니다.</p>
  <p>본 연구는 학습 상황에서 AI 에이전트가 제공하는 칭찬의 귀인 방식(과정 귀인 칭찬, 능력 귀인 칭찬)이 학습자의 학습 동기에 어떠한 영향을 미치는지를 경험적으로 검증하고자 합니다. 또한, 참여자가 AI 에이전트를 얼마나 ‘인간처럼’ 지각하는지(지각된 의인화 수준)가 이 관계를 조절하는지를 함께 탐구합니다. 학습 동기는 과제의 지속 의지, 어려운 과제에 대한 도전 성향, 과제를 통한 성취감 등 다양한 심리적 요인을 바탕으로 측정되며, 이를 통해 AI 기반 학습 환경 설계에 필요한 심리적·교육적 시사점을 도출하고자 합니다.</p>

  <h2>2. 연구 참여 대상</h2>
  <p>참여 대상: 만 18세 이상 성인으로 한국어 사용자를 대상으로 합니다.</p>
  <p>단, 한국어 사용이 미숙하여 주어진 문장을 이해하기 어렵거나, 단어를 파악하지 못하는 경우 연구 대상에서 제외됩니다.</p>

  <h2>3. 연구 방법</h2>
  <p>연구 참여에 동의하신다면 다음과 같은 과정을 통해 연구가 진행됩니다. 일반적인 의인화 경향성을 알아보는 문항 30개, 성취목표지향성 문항 26개를 진행하고 추론 과제를 진행합니다. 과제 이후에 AI 에이전트의 평가 문장을 받아볼 수 있습니다. 추론 과제 후 7문항의 학습 동기 문항에 응답을 하게 됩니다.</p>
  <p>전체 연구 참여 시간은 10분에서 15분 정도 진행됩니다.</p>

  <h2>4. 연구 참여 기간</h2>
  <p>연구 참여는 접속 링크가 살아있는 기간 언제든 참여가 가능하지만, 참여 가능 횟수는 1회입니다.</p>

  <h2>5. 연구 참여에 따른 이익 및 보상</h2>
  <p>연구 참여를 해주신 연구 대상자 분들에게는 1000원 상당의 기프티콘이 발송됩니다. 기프티콘 발송을 위해 핸드폰 번호를 기입해주셔야 하며, 핸드폰 번호를 기입하지 않을 경우 답례품 제공이 어려울 수 있습니다.</p>
  <p>답례품은 개인당 1회에 한하여 제공됩니다.</p>

  <h2>6. 연구 과정에서의 부작용 또는 위험요소 및 조치</h2>
  <p>연구에 참여하시는 도중 불편감을 느끼신다면 언제든 화면을 종료하여 연구를 중단할 수 있습니다. 연구 중단시 어떠한 불이익도 존재하지 않습니다.</p>
  <p>본 연구에서 예상되는 불편감은 과제의 지루함, AI 에이전트의 평가에 대한 불편감, 과제 지속을 해야하는 부담감 등이 예상됩니다.</p>
  <p>연구를 통해 심리적 불편감을 호소하실 경우 연구책임자가 1회의 심리 상담 지원을 진행해드립니다.</p>

  <h2>7. 개인정보와 비밀보장</h2>
  <p>본 연구의 참여로 수집되는 개인정보는 다음과 같습니다. 성별, 연령, 핸드폰 번호를 수집하며 이 정보는 연구를 위해 3년간 사용되며 수집된 정보는 개인정보보호법에 따라 적절히 관리됩니다. 관련 정보는 본 연구자(들)만이 접근 가능한 클라우드 서버에 저장됩니다. 연구를 통해 얻은 모든 개인정보의 비밀보장을 위해 최선을 다할 것입니다. 이 연구에서 얻어진 개인정보가 학회지나 학회에 공개될 때 귀하의 이름과 정보는 사용되지 않을 것입니다. 그러나 만일 법이 요구하면 귀하의 개인정보는 제공될 수도 있습니다. 또한 가톨릭대학교 성심교정 생명윤리심의위원회가 연구대상자의 비밀보장을 침해하지 않고 관련 규정이 정하는 범위 안에서 본 연구의 실시 절차와 자료의 신뢰성을 검증하기 위해 연구 관련 자료를 직접 열람하거나 제출을 요청할 수 있습니다. 귀하가 본 동의서에 서명 또는 동의에 체크하는 것은, 이러한 사항에 대하여 사전에 알고 있었으며 이를 허용한다는 의사로 간주될 것입니다. 연구 종료 후 연구관련 자료(위원회 심의결과, 서면동의서(해당 경우), 개인정보수집/이용·제공현황, 연구종료보고서)는 「생명윤리 및 안전에 관한 법률」 시행규칙 제15조에 따라 연구종료 후 3년간 보관됩니다. 보관기간이 끝나면 분쇄 또는 파일 삭제 방법으로 폐기될 것입니다. </p>

  <h2>8. 자발적 연구 참여와 중지</h2>
  <p>본 연구는 자발적으로 참여 의사를 밝히신 분에 한하여 수행될 것입니다. 이에 따라 본 연구에 참여하지 않을 자유가 있으며 본 연구에 참여하지 않아도 귀하에게는 어떠한 불이익도 없습니다. 또한, 귀하는 연구에 참여하신 언제든지 도중에 그만 둘 수 있습니다. 만일 귀하가 연구에 참여하는 것을 그만두고 싶다면 연구 진행 도중 언제든 화면을 종료하고 연구를 중단할 수 있습니다. 참여 중지 시 귀하의 자료는 저장되지 않으며 어떠한 불이익도 존재하지 않습니다.</p>

  <h2>* 연구 문의</h2>
  <p>
    가톨릭대학교<br>
    <span class="inline-label">전 공:</span> 발달심리학<br>
    <span class="inline-label">성 명:</span> 오현택<br>
    <span class="inline-label">전화번호:</span> 010-6532-3161<br>
    <span class="inline-label">이메일:</span> toh315@gmail.com
  </p>

  <p>만일 어느 때라도 연구대상자로서 귀하의 권리에 대한 질문이 있다면 다음의 가톨릭대학교 성심교정 생명윤리심의위원회에 연락하십시오.</p>
  <p>가톨릭대학교 성심교정 생명윤리심의위원회(IRB사무국) 전화번호: 02-2164-4827</p>

</div>
""".strip()

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
    <tr>
      <th>수집하는<br>개인정보 항목</th>
      <td>성별, 나이, 핸드폰 번호</td>
    </tr>
    <tr>
      <th>개인정보의<br>수집 및<br>이용목적</th>
      <td>
        <p>제공하신 정보는 연구수행 및 논문작성 등을 위해서 사용합니다.</p>
        <ol>
          <li>연구수행을 위해 이용 :성별, 나이, 핸드폰 번호</li>
          <li>단, 이용자의 기본적 인권 침해의 우려가 있는 민감한 개인정보 (인종 및 민족, 사상 및 신조, 정치적 성향 및 범죄기록 등)는 수집하지 않습니다.</li>
        </ol>
      </td>
    </tr>
    <tr>
      <th>개인정보의 <br>제3자 제공 및 목적 외 이용</th>
      <td>
        법이 요구하거나 가톨릭대학교 성심교정 생명윤리심의위원회가 본 연구의 실시 절차와
        자료의 신뢰성을 검증하기 위해 연구 결과를 직접 열람할 수 있습니다.
      </td>
    </tr>
    <tr>
      <th>개인정보의<br>보유 및 이용기간</th>
      <td>
        수집된 개인정보의 보유기간은 연구종료 후 3년 까지 입니다. 또한 파기(삭제)시 연구대상자의 개인정보를 재생이 불가능한 방법으로 즉시 파기합니다.
      </td>
    </tr>
  </table>

  <p class="privacy-note">
    ※ 귀하는 이에 대한 동의를 거부할 수 있으며, 다만, 동의가 없을 경우 연구 참여가 불가능할 수 있음을 알려드립니다. 
  </p>

  <ul class="privacy-bullets">
    <li>※ 개인정보 제공자가 동의한 내용외의 다른 목적으로 활용하지 않음</li>
    <li>※ 만 18세 미만인 경우 반드시 법적대리인의 동의가 필요함</li>
    <li>「개인정보보호법」등 관련 법규에 의거하여 상기 본인은 위와 같이 개인정보 수집 및 활용에 동의함.</li>
  </ul>

</div>
""".strip()

# ─────────────────────────────────────────────
# 공통 CSS (반응형 + 인쇄 최적화)
# ─────────────────────────────────────────────
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
  /* 개인정보 표 */
  .privacy-table{ width:100%; border-collapse:collapse; table-layout:fixed; border:2px solid #111827; margin-bottom:14px; }
  .privacy-table th, .privacy-table td{ border:1px solid #111827; padding:10px 12px; vertical-align:top; }
  .privacy-table th{ width:30%; background:#F3F4F6; text-align:left; font-weight:700; }
  .privacy-note{ margin:10px 0; padding:10px 12px; border:1px solid #111827; background:#F9FAFB; }
  .privacy-bullets{ margin-top:12px; padding-left:18px; }
  .privacy-bullets li{ margin:4px 0; }
  /* 인쇄 */
  @media print{
    .consent-wrap, .agree-wrap, .privacy-wrap{ border:none; max-width:100%; }
    .stSlider, .stButton, .stAlert{ display:none !important; }
  }
</style>
"""

# ──────────────────────────────────────────────────────────────────────────────
# 1) 렌더 함수
# ──────────────────────────────────────────────────────────────────────────────
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
# 도구/유틸: 피드백 문구 선택(중복 방지)
def pick_feedback_text(set_key: str) -> str:
    fs = feedback_sets.get(set_key, [])
    if not fs:
        return "수고하셨습니다. 추론 과정에서의 노력과 성찰이 돋보였습니다."
    # 아직 사용하지 않은 인덱스가 있으면 그 중에서, 아니면 아무거나
    remaining = [i for i in range(len(fs)) if i not in st.session_state.used_feedback_indices]
    if not remaining:
        idx = random.randrange(len(fs))
    else:
        idx = random.choice(remaining)
    st.session_state.used_feedback_indices.add(idx)
    return fs[idx]

# ──────────────────────────────────────────────────────────────────────────────
# 2) 연구 동의 페이지
# ──────────────────────────────────────────────────────────────────────────────
if st.session_state.phase == "start":
    scroll_top_js()

    st.title("AI 에이전트의 피드백 방식이 학습에 미치는 영향 탐색 연구")

    if "consent_step" not in st.session_state:
        st.session_state.consent_step = "explain"

    if st.session_state.consent_step == "explain":
        scroll_top_js()
        st.subheader("연구대상자 설명문")
        render_consent_doc()

        st.markdown("<div style='height:12px;'></div>", unsafe_allow_html=True)
        if st.button("다음", key="consent_to_agree_btn", use_container_width=True):
            st.session_state.consent_step = "agree"
            st.rerun()

    elif st.session_state.consent_step == "agree":
        scroll_top_js()
        st.subheader("연구 동의서")
        render_agree_doc()

        consent_research = st.radio(
            "연구 참여에 동의하십니까?",
            ["동의함", "동의하지 않음"],
            horizontal=True, key="consent_research_radio", index=None
        )

        st.markdown("<div style='height:18px;'></div>", unsafe_allow_html=True)

        st.subheader("개인정보 수집·이용에 대한 동의")
        render_privacy_doc()

        consent_privacy = st.radio(
            "개인정보 수집·이용에 동의하십니까?",
            ["동의함", "동의하지 않음"],
            horizontal=True, key="consent_privacy_radio", index=None
        )

        st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
        st.divider()
        st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)

        st.markdown("""
        <style>
        .nav-row .stButton > button {
        width: 100%;
        min-width: 120px;
        }
        @media (max-width: 420px) {
        .nav-row .stButton > button { min-width: auto; }
        }
        </style>
        """, unsafe_allow_html=True)

        st.markdown('<div class="nav-row">', unsafe_allow_html=True)
        left_col, right_col = st.columns([1, 1])

        with left_col:
            if st.button("이전", key="consent_prev_btn", use_container_width=True):
                st.session_state.consent_step = "explain"
                st.rerun()

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
                    st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────────────────
# 1-1. 인적사항
elif st.session_state.phase == "demographic":
    scroll_top_js()
    st.title("인적사항 입력")

    gender = st.radio("성별", ["남자", "여자"], index=None)
    age_group = st.radio("연령대", ["10대", "20대", "30대", "40대", "50대", "60대 이상"], index=None)

    if st.button("설문 시작"):
        if not gender or not age_group:
            st.warning("성별과 연령을 모두 입력해 주세요.")
        else:
            st.session_state.data.update({"gender": gender, "age": age_group})
            st.session_state.phase = "anthro"
            st.rerun()

# ──────────────────────────────────────────────────────────────────────────────
# 2. 의인화 척도 (5점 리커트 라디오) — 10문항 단위 페이지네이션
elif st.session_state.phase == "anthro":
    scroll_top_js()

    anthro_path = os.path.join(BASE_DIR, "data", "questions_anthro.json")
    with open(anthro_path, encoding="utf-8") as f:
        questions = json.load(f)

    total_items = len(questions)  # 30 예상
    page_size = 10
    total_pages = (total_items + page_size - 1) // page_size  # 3

    if "anthro_page" not in st.session_state:
        st.session_state["anthro_page"] = 1
    if "anthro_responses" not in st.session_state or len(st.session_state["anthro_responses"]) != total_items:
        st.session_state["anthro_responses"] = [None] * total_items

    page = st.session_state["anthro_page"]

    if st.session_state.get("_anthro_prev_page") != page:
        st.session_state["_anthro_prev_page"] = page
        scroll_top_js()

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

    st.markdown(
        f"<div class='progress-note'>문항 {start_idx+1}–{end_idx} / 총 {total_items}문항 (페이지 {page}/{total_pages})</div>",
        unsafe_allow_html=True
    )

    options = [1, 2, 3, 4, 5]
    for local_i, q in enumerate(slice_questions, start=1):
        global_idx = start_idx + local_i - 1
        current_value = st.session_state["anthro_responses"][global_idx]
        radio_key = f"anthro_{global_idx+1}"
        index_val = (options.index(current_value) if current_value in options else None)

        selected = st.radio(
            label=f"{global_idx+1}. {q}",
            options=options,
            index=index_val,
            format_func=lambda x: f"{x}점",
            horizontal=True,
            key=radio_key,
            help="1~5점 중에서 선택해 주세요."
        )

        st.session_state["anthro_responses"][global_idx] = selected if selected in options else None
        st.markdown("<div style='margin-bottom:12px;'></div>", unsafe_allow_html=True)

    st.markdown("""
    <style>
    .nav-row .stButton > button { width: 100%; min-width: 120px; }
    @media (max-width: 420px) { .nav-row .stButton > button { min-width: auto; } }
    </style>
    """, unsafe_allow_html=True)

    with st.container():
        st.markdown('<div class="nav-row">', unsafe_allow_html=True)
        col_prev, col_info, col_next = st.columns([1, 2, 1])

        with col_prev:
            if page > 1:
                if st.button("← 이전", use_container_width=True, key="anthro_prev"):
                    st.session_state["anthro_page"] = page - 1
                    st.rerun()

        with col_info:
            pass

        with col_next:
            current_slice = st.session_state["anthro_responses"][start_idx:end_idx]
            all_selected = all((v is not None and isinstance(v, int) and 1 <= v <= 5) for v in current_slice)

            if page < total_pages:
                if st.button("다음 →", use_container_width=True, key="anthro_next_mid"):
                    if not all_selected:
                        st.warning("현재 페이지 모든 문항을 1~5점 중 하나로 선택해 주세요.")
                    else:
                        st.session_state["anthro_page"] = page + 1
                        st.rerun()
            else:
                if st.button("다음", use_container_width=True, key="anthro_next_last"):
                    full_ok = all((v is not None and isinstance(v, int) and 1 <= v <= 5)
                                  for v in st.session_state["anthro_responses"])
                    if not full_ok:
                        st.warning("모든 문항을 1~5점 중 하나로 선택해 주세요.")
                    else:
                        st.session_state.data["anthro_responses"] = st.session_state["anthro_responses"]
                        st.session_state["anthro_page"] = 1
                        st.session_state.phase = "achive"
                        st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────────────────
# 2-1. 성취/접근 관련 추가 설문(6점 리커트) — 10/10/6 페이지네이션
elif st.session_state.phase == "achive":
    scroll_top_js()

    st.markdown("<h2 style='text-align:center; font-weight:bold;'>아래에 제시되는 문항은 평소 본인의 성향을 알아보기 위한 문항입니다. 나의 성향과 얼마나 가까운지를 선택해 주세요.</h2>", unsafe_allow_html=True)
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

    total_items = len(achive_questions)  # 26 예상
    page_size_list = [10, 10, total_items - 20] if total_items >= 20 else [total_items]
    total_pages = len(page_size_list)

    if "achive_page" not in st.session_state:
        st.session_state["achive_page"] = 1
    if "achive_responses" not in st.session_state or len(st.session_state["achive_responses"]) != total_items:
        st.session_state["achive_responses"] = [None] * total_items

    page = st.session_state["achive_page"]

    if st.session_state.get("_achive_prev_page") != page:
        st.session_state["_achive_prev_page"] = page
        scroll_top_js()

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
    <style>
    .nav-row .stButton > button {
    width: 100%;
    min-width: 120px;
    }
    @media (max-width: 420px) {
    .nav-row .stButton > button { min-width: auto; }
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="nav-row">', unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 2, 1])

    with c1:
        if page > 1:
            if st.button("← 이전", key="achive_prev", use_container_width=True):
                st.session_state["achive_page"] = page - 1
                st.rerun()

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
                    st.session_state["achive_page"] = page + 1
                    st.rerun()
        else:
            if st.button("다음 (추론 과제 안내)", key="achive_done", use_container_width=True):
                full_ok = all(v in [1,2,3,4,5,6] for v in st.session_state["achive_responses"])
                if not full_ok:
                    st.warning("모든 문항에 응답해 주세요. (1~6)")
                else:
                    st.session_state.data["achive_responses"] = st.session_state["achive_responses"]
                    st.session_state["achive_page"] = 1
                    st.session_state.phase = "writing_intro"
                    st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# 2-2. 추론 과제 지시문 (2회차 공지 포함)
elif st.session_state.phase == "writing_intro":
    scroll_top_js()

    st.markdown("<h2 style='text-align:center; font-weight:bold;'>추론 기반 객관식 과제 안내</h2>", unsafe_allow_html=True)
    st.markdown("""
    이번 단계에서는 **이누이트 언어(Inuktut-like)**의 간단한 규칙을 읽고,  
    총 **10개**의 객관식 문항에 답하는 **추론 과제**를 **2회** 수행합니다.

    이 과제의 목표는 **정답률 자체가 아니라 ‘낯선 규칙에서 끝까지 추론하려는 과정’**을 관찰하는 것입니다.  
    정답을 모두 맞추는 것보다 **단서를 찾고, 비교하고, 일관된 근거로 선택**하는 과정이 더 중요합니다.

    **진행 순서**
    1) 1차 과제(10문항) → 분석 모션 → AI 칭찬 피드백 → **다음 과제 난이도(1~10) 선택**
    2) 2차 과제(10문항) → 분석 모션 → AI 칭찬 피드백
    3) 학습동기 설문(7문항) → 휴대폰(선택) → **추가 난이도(1~10) 선택** → 최종 제출/디브리핑
    """)
    if st.button("1차 추론 과제 시작"):
        st.session_state.phase = "writing_round1"
        st.session_state.round1_started_ts = time.time()
        st.rerun()

# ──────────────────────────────────────────────────────────────────────────────
# 공통 문항(10개)
def build_questions():
    return [
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

RATIONALE_TAGS = ["소유(-mi)", "복수(-t)", "목적표시(-ka)", "시제(-na/-tu)", "연결어(ama)"]

def render_inference_round(round_no: int):
    scroll_top_js()
    st.title(f"추론 과제 {round_no}/2 · 이누이트 언어 학습(Inuktut-like)")

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

    questions = build_questions()

    st.markdown(
        "<div style='margin:6px 0 16px; padding:10px; border-radius:8px; background:#202b20; color:#fff;'>"
        "※ 모든 문항은 <b>정답보다 '추론하려는 과정'</b>을 봅니다. 각 문항에서 <b>선택지</b>와 <b>근거 규칙</b>을 모두 선택해 주세요."
        "</div>", unsafe_allow_html=True
    )

    selections, rationales = [], []
    for i, item in enumerate(questions):
        st.markdown(f"### {item['q']}")
        st.caption("이 문항은 **정답이 전부가 아닙니다.** 규칙을 참고해 가장 그럴듯한 선택지를 고르세요.")
        choice = st.radio(
            label=f"문항 {i+1} 선택",
            options=list(range(len(item["options"]))),
            format_func=lambda idx, opts=item["options"]: opts[idx],
            key=f"round{round_no}_mcq_{i}",
            horizontal=False,
            index=None
        )
        selections.append(choice)
        rationale = st.multiselect(
            f"문항 {i+1}에서 참고한 규칙(최소 1개 이상)",
            options=RATIONALE_TAGS,
            key=f"round{round_no}_rat_{i}",
            help="최소 1개 이상 선택해야 제출할 수 있습니다."
        )
        rationales.append(rationale)
        st.markdown("<div style='margin-bottom:8px;'></div>", unsafe_allow_html=True)

    # 검증
    def validate_mcq(sel_list, rat_list):
        missing_sel = [i+1 for i, s in enumerate(sel_list) if s is None]
        missing_rat = [i+1 for i, r in enumerate(rat_list) if not r]
        all_selected = (len(sel_list) == len(questions)) and not missing_sel
        all_rationale = (len(rat_list) == len(questions)) and not missing_rat
        return (all_selected and all_rationale), missing_sel, missing_rat

    if st.button("제출", key=f"submit_round{round_no}"):
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
            if round_no == 1:
                duration = int(time.time() - st.session_state.round1_started_ts) if st.session_state.round1_started_ts else None
            else:
                duration = int(time.time() - st.session_state.round2_started_ts) if st.session_state.round2_started_ts else None
            score = sum(int(selected_idx[i] == q["ans"]) for i, q in enumerate(questions))
            accuracy = round(score / len(questions), 3)

            detail = [{
                "q": questions[i]["q"],
                "options": questions[i]["options"],
                "selected_idx": selected_idx[i],
                "correct_idx": int(questions[i]["ans"]),
                "rationales": rationales[i]
            } for i in range(len(questions))]

            st.session_state.data[f"inference_round{round_no}"] = {
                "answers": detail,
                "score": int(score),
                "duration_sec": duration,
                "accuracy": accuracy
            }

            # 다음 단계: MCP 모션
            st.session_state[f"_mcp_started_{round_no}"] = False
            st.session_state[f"_mcp_done_{round_no}"] = False
            st.session_state.phase = f"analyzing_round{round_no}"
            st.rerun()

# ──────────────────────────────────────────────────────────────────────────────
# 3. 추론 과제 (1차/2차)
elif st.session_state.phase == "writing_round1":
    # 시작 시간 세팅은 writing_intro에서
    render_inference_round(1)

elif st.session_state.phase == "writing_round2":
    if not st.session_state.round2_started_ts:
        st.session_state.round2_started_ts = time.time()
    render_inference_round(2)

# ──────────────────────────────────────────────────────────────────────────────
# 4. MCP 분석 모션 (1차/2차)
elif st.session_state.phase in ["analyzing_round1", "analyzing_round2"]:
    scroll_top_js()
    round_no = 1 if st.session_state.phase.endswith("round1") else 2

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

        if not st.session_state.get(f"_mcp_started_{round_no}", False):
            st.session_state[f"_mcp_started_{round_no}"] = True
            run_mcp_motion(8.0)
            st.session_state[f"_mcp_done_{round_no}"] = True
            st.rerun()

        if st.session_state.get(f"_mcp_done_{round_no}", False):
            st.markdown(f"""
                <div class='mcp-done-card'>
                  <h2 style="text-align:center; color:#2E7D32; margin-top:0;">✅ 분석이 완료되었습니다</h2>
                  <p style="font-size:16px; line-height:1.7; color:#222; text-align:center; margin:6px 0 0;">
                    COVNOX가 응답의 추론 패턴을 분석했습니다. <b>결과 보기</b>를 눌러 피드백을 확인하세요.
                  </p>
                </div>
            """, unsafe_allow_html=True)
            _, mid, _ = st.columns([1,2,1])
            with mid:
                if st.button("결과 보기", use_container_width=True, key=f"see_feedback_{round_no}"):
                    page.empty()
                    st.session_state[f"_mcp_started_{round_no}"] = False
                    st.session_state[f"_mcp_done_{round_no}"] = False
                    st.session_state.phase = f"ai_feedback_round{round_no}"
                    st.rerun()

# ──────────────────────────────────────────────────────────────────────────────
# 5. AI 피드백 (세트 고정, 문구 중복 방지)
elif st.session_state.phase in ["ai_feedback_round1", "ai_feedback_round2"]:
    scroll_top_js()

    # ── 0) 집단(무작위 유지)
    if "feedback_set_key" not in st.session_state:
        st.session_state.feedback_set_key = random.choice(["set1", "set2"])
    set_key = st.session_state.get("feedback_set_key", "set1")
    round_no = 1 if st.session_state.phase.endswith("round1") else 2

    # ── 1) 칭찬 연출 테마 (라벨 노출 없이 색/아이콘/무드로만 구분)
    THEME = {
        "set1": {  # 노력 칭찬 → 따뜻한 축하 + 분석적 신뢰감
            "bg_grad": "linear-gradient(135deg,#0b3a1a 0%, #1e7a35 60%, #4caf50 100%)",
            "accent": "#1E7A35",
            "icon": "🫶",
            "confetti": True,
            "hl": "#0E6F2E"
        },
        "set2": {  # 능력 칭찬 → 반짝이는 축하 + 넓은 가능성
            "bg_grad": "linear-gradient(135deg,#162c6a 0%, #1565C0 60%, #6FA8FF 100%)",
            "accent": "#1565C0",
            "icon": "🌟",
            "confetti": True,
            "hl": "#0D47A1"
        }
    }
    theme = THEME.get(set_key, THEME["set1"])

    # ── 2) 스타일
    st.markdown(f"""
    <style>
      .praise-banner {{
        background:{theme["bg_grad"]};
        color:#fff; border-radius:16px; padding:18px 20px; margin:8px 0 14px;
        box-shadow:0 14px 28px rgba(0,0,0,.24), 0 10px 10px rgba(0,0,0,.22);
        font-weight:900; letter-spacing:.2px; display:flex; gap:10px; align-items:center;
        border:1px solid rgba(255,255,255,.16);
      }}
      .praise-banner .emoji {{ font-size:22px; filter: drop-shadow(0 1px 2px rgba(0,0,0,.25)); }}

      .praise-card {{
        position: relative;
        background: #FCFFFC;
        border-radius:18px; padding:18px 18px 16px; margin: 10px 0 16px;
        box-shadow: 0 10px 26px rgba(0,0,0,.12);
        border: 2px solid {theme["accent"]};
        overflow:hidden;
      }}
      .praise-ribbon {{
        position:absolute; top:14px; right:-10px;
        background:{theme["accent"]}; color:#fff; font-weight:800; font-size:12px;
        padding:6px 14px; transform: rotate(8deg); border-radius:8px;
        box-shadow:0 6px 14px rgba(0,0,0,.18);
      }}
      .praise-title {{
        margin:0 0 10px 0; font-size:22px; font-weight:900; color:#123;
        display:flex; align-items:center; gap:8px;
      }}
      .praise-quote {{
        position:relative; margin:4px 0 0; padding:10px 12px 8px 14px;
        background:#ffffff; border-left:6px solid {theme["accent"]};
        border-radius:10px;
      }}
      .praise-quote p {{
        font-size:16.5px; line-height:1.78; margin:0;
        color:#222 !important; white-space:pre-line;
      }}
      .hl {{ font-weight:800; color:{theme["hl"]}; }}
      .praise-sign {{ margin-top:10px; font-size:13.2px; color:#3a3a3a; opacity:.9; }}
      .result-card {{
        border:2px solid {theme["accent"]}; border-radius:14px; padding:16px; background:#F7FFF7;
        box-shadow:0 8px 18px rgba(0,0,0,.08); margin-top:12px;
      }}
      .result-card h2{{ text-align:left; margin:0 0 10px; color:#123; font-size:22px; }}
    </style>
    """, unsafe_allow_html=True)

    # ── 3) 축하 애니메이션 (과한 반복 방지)
    if theme["confetti"] and not st.session_state.get("praise_once"):
        st.balloons()
        st.session_state["praise_once"] = True

    # ── 4) 칭찬 배너 (최상단)
    st.markdown(f"""
    <div class="praise-banner">
      <span class="emoji">{theme["icon"]}</span>
      <div>AI가 당신의 풀이를 보며 <b>진심으로 칭찬</b>을 전합니다</div>
    </div>
    """, unsafe_allow_html=True)

    # ── 5) 피드백 텍스트 (세트 고정 + 중복 방지)
    feedback = pick_feedback_text(set_key)

    # ── 6) 세트별 하이라이트(라벨 노출 없이 색감으로만)
    HL = {
        "set1": ["충분한 시간", "시도→점검→수정", "꾸준한 노력", "집중", "검증", "예외 정리"],
        "set2": ["언어적 감각", "빠른 이해", "자연스럽게", "넓은 적용", "전반 역량", "매끄러운 흐름"]
    }
    for kw in HL.get(set_key, []):
        feedback = feedback.replace(kw, f"<span class='hl'>{kw}</span>")

    # ── 7) 칭찬 카드
    st.markdown(f"""
    <div class="praise-card">
      <div class="praise-ribbon">칭찬 드려요</div>
      <div class="praise-title">{theme["icon"]} 정말 잘하셨어요!</div>
      <div class="praise-quote">
        <p>{feedback}</p>
      </div>
      <div class="praise-sign">— 당신의 풀이를 옆에서 지켜본 AI가</div>
    </div>
    """, unsafe_allow_html=True)

    # ── 8) 간단 요약 후 분석 시각화 (도넛)
    st.markdown(f"""
    <div class="result-card" id="analysis-start">
      <h2>📊 분석 한눈에 보기</h2>
      <div style="font-size:14.5px; color:#203; margin:2px 0 8px;">
        칭찬의 근거를 간단히 시각화했습니다. (세부 점수는 연구 목적상 무작위 프리셋 기반)
      </div>
    </div>
    """, unsafe_allow_html=True)

    labels = ["규칙 가설화", "패턴 파악", "예외 정리", "집중 지속", "검증 반복"]
    CHART_PRESETS = {
        "set1": {"base":[22,21,38,36,38], "colors":["#CDECCB","#7AC779","#5BAF5A","#92D091","#B1E3AE"]},
        "set2": {"base":[34,38,22,20,28], "colors":["#B3D4FF","#80B6FF","#66A7FF","#3E8BFF","#1565C0"]},
    }
    preset = CHART_PRESETS.get(set_key, CHART_PRESETS["set1"])

    if "chart_seed" not in st.session_state:
        st.session_state.chart_seed = random.randint(1000,9999)
    rng = random.Random(st.session_state.chart_seed + (0 if round_no==1 else 1))
    jitter = [rng.randint(-2,2) for _ in labels]
    values = [max(10,b+j) for b,j in zip(preset["base"], jitter)]

    try:
        import plotly.express as px
        fig = px.pie(values=values, names=labels, hole=0.55, color=labels,
                     color_discrete_sequence=preset["colors"])
        fig.update_traces(textinfo="percent+label",
                          marker=dict(line=dict(width=1, color="white")),
                          hovertemplate="<b>%{label}</b><br>점수: %{value}점<extra></extra>")
        fig.update_layout(height=320, margin=dict(l=10,r=10,t=6,b=6),
                          showlegend=True, legend=dict(orientation="h", y=-0.1),
                          uniformtext_minsize=12, uniformtext_mode="hide")
        st.plotly_chart(fig, use_container_width=True,
                        config={"displayModeBar": False, "displaylogo": False})
    except Exception:
        st.info("시각화를 준비 중입니다.")

    # ── 9) 다음 단계 버튼
    st.markdown("&nbsp;", unsafe_allow_html=True)

    if round_no == 1:
        if st.button("다음 과제 난이도 선택 (1~10)"):
            st.session_state.data["feedback_set"] = set_key
            st.session_state.phase = "difficulty_after_fb1"
            st.rerun()
    else:
        if st.button("학습동기 설문으로 이동"):
            st.session_state.data["feedback_set"] = set_key
            st.session_state.phase = "motivation"
            st.rerun()

# ──────────────────────────────────────────────────────────────────────────────
# 5-1. 난이도 질문(1차 피드백 직후) — 기본값 없이 강제 선택
elif st.session_state.phase == "difficulty_after_fb1":
    scroll_top_js()
    st.subheader("다음 과제 난이도를 선택해 주세요 (1~10)")
    diff_choice = st.radio("다음(2차) 과제 난이도", list(range(1,11)), index=None, horizontal=True)
    if st.button("확인 후 2차 과제로 이동"):
        if diff_choice is None:
            st.warning("난이도를 선택해 주세요.")
        else:
            st.session_state.data["difficulty_after_fb1"] = int(diff_choice)
            st.session_state.phase = "writing_round2"
            st.session_state.round2_started_ts = time.time()
            st.rerun()

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

    if "motivation_responses" not in st.session_state:
        st.session_state.motivation_responses = [None]*len(motivation_q)

    for i, q in enumerate(motivation_q, start=1):
        choice = st.radio(
            label=f"{i}. {q}",
            options=list(range(1, 6)),
            index=None,
            horizontal=True,
            key=f"motivation_{i}",
            label_visibility="visible"
        )
        st.session_state.motivation_responses[i-1] = choice
        st.markdown("<div style='margin-bottom:12px;'></div>", unsafe_allow_html=True)

    if st.button("다음 (휴대폰 입력)"):
        if None in st.session_state.motivation_responses:
            st.warning("모든 문항에 응답해 주세요.")
        else:
            st.session_state.data["motivation_responses"] = st.session_state.motivation_responses
            st.session_state.phase = "phone_input"
            st.rerun()

# ──────────────────────────────────────────────────────────────────────────────
# 6-1. 휴대폰 번호 입력 (선택)
elif st.session_state.phase == "phone_input":
    scroll_top_js()

    st.title("휴대폰 번호 입력 (선택)")
    st.markdown("""
    연구 참여가 거의 완료되었습니다. 감사합니다.  
    연구 답례품을 받을 휴대폰 번호를 입력해 주세요. (선택 사항)  
    입력하지 않아도 다음 단계로 진행할 수 있으나, 미입력 시 답례품 전달이 어려울 수 있습니다.
    """)
    phone = st.text_input("휴대폰 번호", placeholder="010-1234-5678", key="phone_input_value")

    if st.button("다음 (추가 난이도 선택)"):
        if phone.strip() and not validate_phone(phone):
            st.warning("올바른 형식이 아닙니다. (예: 010-1234-5678)")
        else:
            st.session_state.data["phone"] = phone.strip()
            st.session_state.phase = "difficulty_final"
            st.rerun()

# ──────────────────────────────────────────────────────────────────────────────
# 6-2. 추가 난이도 문항 (최종 전 1~10) — 기본값 없이 강제 선택
elif st.session_state.phase == "difficulty_final":
    scroll_top_js()
    st.subheader("추가 과제가 있습니다. 사용자의 선택에 따라 난이도가 변경됩니다.난이도를 어느 정도로 하시겠습니까? (1~10)")
    diff2 = st.radio("추가 난이도 선택", list(range(1,11)), index=None, horizontal=True, key="final_diff_radio")
    if st.button("다음 과제 이동"):
        if diff2 is None:
            st.warning("난이도를 선택해 주세요.")
        else:
            st.session_state.data["difficulty_future_adaptive"] = int(diff2)
            st.session_state.phase = "result"
            st.rerun()

# ──────────────────────────────────────────────────────────────────────────────
# 7. 완료/디브리핑 (자동 저장)
elif st.session_state.phase == "result":
    scroll_top_js()

    # 아직 저장이 안 된 경우 자동 저장
    if "result_submitted" not in st.session_state:
        st.session_state.data["endTime"] = datetime.now().isoformat()
        try:
            save_to_csv(st.session_state.data)
            st.session_state.result_submitted = True
        except Exception as e:
            st.error(f"저장 중 오류가 발생했습니다: {e}")

    # 디브리핑 문구 (저장 후 안내만 표시)
    st.success("모든 과제가 완료되었습니다. 감사합니다!")
    st.markdown("""
    <div style='font-size:16px; padding-top:10px;'>
        ※ 본 연구에서 제공된 AI의 평가는 <b>사전에 생성된 예시 문구</b>를 기반으로 제공되었으며, 
        귀하의 실제 추론 능력을 직접 평가한 것이 아님을 알려드립니다.<br><br>
        설문 응답은 이미 저장되었습니다.<br>
        <b>이 화면은 자동으로 닫히지 않으니, 브라우저 탭을 직접 닫아 주세요.</b>
    </div>
    """, unsafe_allow_html=True)
