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
        (function(){
          function goTop() {
            try {
              // 부모 문서(스트림릿 실제 뷰) 스크롤
              var pdoc = window.parent && window.parent.document;
              var sect = pdoc && pdoc.querySelector && pdoc.querySelector('section.main');
              if (sect && sect.scrollTo) sect.scrollTo({top:0, left:0, behavior:'instant'});
            } catch(e) {}

            try {
              // iframe 내부(백업) 스크롤
              window.scrollTo({top:0, left:0, behavior:'instant'});
              document.documentElement && document.documentElement.scrollTo && document.documentElement.scrollTo(0,0);
              document.body && document.body.scrollTo && document.body.scrollTo(0,0);
            } catch(e) {}
          }

          // 즉시 실행 + 렌더 타이밍 대비 다회 실행
          goTop();
          if (window.requestAnimationFrame) requestAnimationFrame(goTop);
          setTimeout(goTop, 25);
          setTimeout(goTop, 80);
          setTimeout(goTop, 180);
          setTimeout(goTop, 320);
        })();
        </script>
        """,
        unsafe_allow_html=True
    )

    def rerun_with_scroll_top():
        """
        스크립트가 매번 새로 실행되도록 nonce 올리고 바로 rerun.
        """
        st.session_state["_scroll_nonce"] = st.session_state.get("_scroll_nonce", 0) + 1
        st.rerun()


# ──────────────────────────────────────────────────────────────────────────────
# 상태 초기화
if "phase" not in st.session_state:
    st.session_state.phase = "start"
    st.session_state.data = {}
    st.session_state.feedback_set_key = random.choice(["set1", "set2"])  # 레거시 호환

# ──────────────────────────────────────────────────────────────────────────────
# MCP용 가짜 로그 + 애니메이션 화면 (항상 단독 화면)
fake_logs = [
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

def run_mcp_motion():
    # 중앙 배치 여백
    st.markdown("<div style='height:18vh;'></div>", unsafe_allow_html=True)

    st.markdown(
        """
        <style>
        .covnox-title{ margin:0; text-align:center;
          font-size: clamp(26px, 5.2vw, 46px); font-weight:800;
        }
        .covnox-sub{
          font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
          font-size: clamp(12px, 2.4vw, 16px); opacity:.9; margin:6px 0 10px 0; text-align:center;
        }
        </style>
    """,
        unsafe_allow_html=True,
    )

    # 로고(있을 때만)
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
        total = 8.0  # 총 8초 애니메이션
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
                    unsafe_allow_html=True,
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
# (기존 본문은 그대로 유지)
# ─────────────────────────────────────────────

CONSENT_HTML = """
<div class="consent-wrap">

  <h1>연구대상자 설명문</h1>

  <div class="subtitle"><strong>제목: </strong>인공지능 에이전트의 피드백 방식이 학습에 미치는 영향 탐색 연구</div>

  <h2>1. 연구 목적</h2>
  <p>최근 과학기술의 발전과 함께 인공지능(AI)은 교육, 상담, 서비스 등 다양한 환경에서 폭넓게 활용되고 있습니다. 특히 학습 환경에서 AI 에이전트는 단순 정보 전달자 역할을 넘어, 학습자의 성취와 노력을 평가하고 동기를 촉진하는 상호작용 주체로 주목받고 있습니다.</p>
  <p>본 연구는 학습 상황에서 AI 에이전트가 제공하는 칭찬(피드백) 방식이 학습자의 학습 동기에 어떠한 영향을 미치는지를 경험적으로 검증하고자 합니다. 또한, 참여자가 AI 에이전트를 얼마나 ‘인간처럼’ 지각하는지(지각된 의인화 수준)가 이 관계를 조절하는지를 함께 탐구합니다. 학습 동기는 과제의 지속 의지, 어려운 과제에 대한 도전 성향, 과제를 통한 성취감 등 다양한 심리적 요인을 바탕으로 측정되며, 이를 통해 AI 기반 학습 환경 설계에 필요한 심리적·교육적 시사점을 도출하고자 합니다.</p>

  <h2>2. 연구 참여 대상</h2>
  <p>참여 대상: 만 18세 이상 성인으로 한국어 사용자를 대상으로 합니다.</p>
  <p>단, 한국어 사용이 미숙하여 주어진 문장을 이해하기 어렵거나, 단어를 파악하지 못하는 경우 연구 대상에서 제외됩니다.</p>

  <h2>3. 연구 방법</h2>
  <p>연구 참여에 동의하신다면 다음과 같은 과정을 통해 연구가 진행됩니다. 일반적인 의인화 경향성을 알아보는 문항과 성취목표지향성에 대한 문항 총 56개를 진행하고 추론 과제를 진행하게 됩니다. 추론 과제 이후에 AI 에이전트의 평가 문장을 받아볼 수 있습니다. 추론 과제는 총 2회 진행됩니다. 마지막으로 학습에 관한 문항에 응답을 하며 연구 참여가 종료됩니다</p>
  <p>전체 연구 참여 시간은 10분에서 15분 정도 진행됩니다.</p>

  <h2>4. 연구 참여 기간</h2>
  <p>연구 참여는 접속 링크가 살아있는 기간 언제든 참여가 가능하지만, 참여 가능 횟수는 1회입니다.</p>

  <h2>5. 연구 참여에 따른 이익 및 보상</h2>
  <p>연구 참여를 해주신 연구 대상자 분들에게는 1500원 상당의 기프티콘이 발송됩니다. 기프티콘 발송을 위해 핸드폰 번호를 기입해주셔야 하며, 핸드폰 번호를 기입하지 않을 경우 답례품 제공이 어려울 수 있습니다.</p>
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
# 공통 CSS (문서용)
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
# 2) 연구 동의 & 개인정보 동의 → 인적사항 → 의인화 → 성취
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
        @media (max-width: 420px) { .nav-row .stButton > button { min-width: auto; } }
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
            st.session_state.phase = "anthro"
            st.rerun()

# 2. 의인화 척도 (5점 리커트 라디오) — 10문항 단위 페이지네이션
elif st.session_state.phase == "anthro":
    scroll_top_js()

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
        <h2 class="anthro-title">아래에 제시되는 문항은 개인의 경험과 인식을 알아보기 위한 것입니다. 본인의 평소 생각에 얼마나 가까운지를선택해 주세요.</h2>
        <div class="scale-guide">
          <span><b>1점</b>: 전혀 그렇지 않다</span><span>—</span>
          <span><b>3점</b>: 보통이다</span><span>—</span>
          <span><b>5점</b>: 매우 그렇다</span>
        </div>        
    """, unsafe_allow_html=True)

    st.markdown(
        f"<div class='progress-note'>문항 {start_idx+1}–{end_idx} / 총 {total_items}문항 (페이지 {page}/{total_pages})</div>",
        unsafe_allow_html=True,
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
            help="1~5점 중에서 선택해 주세요.",
        )

        st.session_state["anthro_responses"][global_idx] = selected if selected in options else None
        st.markdown("<div style='margin-bottom:12px;'></div>", unsafe_allow_html=True)

    st.markdown(
        """
    <style>
    .nav-row .stButton > button { width: 100%; min-width: 120px; }
    @media (max-width: 420px) { .nav-row .stButton > button { min-width: auto; } }
    </style>
    """,
        unsafe_allow_html=True,
    )

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
            all_answered = all((v is not None and isinstance(v, int) and 1 <= v <= 5) for v in current_slice)

            if page < total_pages:
                if st.button("다음 →", use_container_width=True, key="anthro_next_mid"):
                    if not all_answered:
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

# 2-1. 성취/접근 관련 추가 설문(6점 리커트) — 10/10/나머지 페이지네이션
elif st.session_state.phase == "achive":
    scroll_top_js()

    st.markdown("<h2 style='text-align:center; font-weight:bold;'>아래에 제시되는 문항은 평소 본인의 성향을 알아보기 위한 문항입니다. 나의 성향과 얼마나 가까운지를 선택해 주세요.</h2>", unsafe_allow_html=True)
    st.markdown(
        """
    <div style='display:flex; justify-content:center; align-items:center; gap:12px; flex-wrap:wrap;\
                font-size:16px; margin-bottom:22px;'>
        <span style="white-space:nowrap;"><b>1</b> : 전혀 그렇지 않다</span>
        <span>—</span>
        <span style="white-space:nowrap;"><b>3</b> : 보통이다</span>
        <span>—</span>
        <span style="white-space:nowrap;"><b>6</b> : 매우 그렇다</span>
    </div>
    """,
        unsafe_allow_html=True,
    )

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
        unsafe_allow_html=True,
    )

    for gi in range(start_idx, end_idx):
        q = achive_questions[gi]
        choice = st.radio(
            label=f"{gi+1}. {q}",
            options=[1, 2, 3, 4, 5, 6],
            index=None,
            horizontal=True,
            key=f"achive_{gi}",
        )
        st.session_state["achive_responses"][gi] = choice
        st.markdown("<div style='margin-bottom:10px;'></div>", unsafe_allow_html=True)

    st.markdown(
        """
    <style>
    .nav-row .stButton > button { width: 100%; min-width: 120px; }
    @media (max-width: 420px) { .nav-row .stButton > button { min-width: auto; } }
    </style>
    """,
        unsafe_allow_html=True,
    )

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
        all_answered = all(v in [1, 2, 3, 4, 5, 6] for v in curr_slice)

        if page < total_pages:
            if st.button("다음 →", key="achive_next", use_container_width=True):
                if not all_answered:
                    st.warning("현재 페이지의 모든 문항에 1~6 중 하나를 선택해 주세요.")
                else:
                    st.session_state["achive_page"] = page + 1
                    st.rerun()
        else:
            if st.button("다음 (추론 과제 안내)", key="achive_done", use_container_width=True):
                full_ok = all(v in [1, 2, 3, 4, 5, 6] for v in st.session_state["achive_responses"])
                if not full_ok:
                    st.warning("모든 문항에 응답해 주세요. (1~6)")
                else:
                    st.session_state.data["achive_responses"] = st.session_state["achive_responses"]
                    st.session_state["achive_page"] = 1
                    st.session_state.phase = "inf_intro"  # ✅ 새로운 추론 과제 플로우로 진입
                    st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────────────────────────
# 3) 추론 과제 (2회차 구성: 명사구 → 동사 TAM)
# ──────────────────────────────────────────────────────────────────────────────

# 칭찬 조건(정서/계산 × 구체/피상) — 세션 전체에 1회 고정
if st.session_state.phase in {"inf_intro","inference_nouns","praise_r1","difficulty1","inference_verbs","praise_r2","analyzing_r1","analyzing_r2","motivation"}:
    if "praise_condition" not in st.session_state:
        st.session_state.praise_condition = random.choice([
            "정서+구체","계산+구체","정서+피상","계산+피상"
        ])

# 규칙 안내 (마크다운)
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

# 이유 보기(명사/동사)
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

# 1R 항목: 명사구

def build_items_nouns():
    items = [
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
    return items

# 2R 항목: 동사 TAM

def build_items_verbs():
    items = [
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
        {"id":"V10","gloss":"‘…한 뒤에(After) ~했다’: ‘집을 본 뒤에 음식을 **먹었다**’ (선행사건 완료·과거 일관)","stem":"(ani-ka taku-mu-tu) ama pira-ka ____",
         "options":["niri-tu","niri-mu-tu","niri-li-tu","niri-na","niri-ki"],"answer_idx":0,"reason_idx":4},
    ]
    return items

# 샘플 텍스트 뽑기

def _pick_samples(ans_detail, reason_labels, k=2):
    rng = random.Random((len(ans_detail) << 7) ^ 9173)
    picks = rng.sample(ans_detail, k=min(k, len(ans_detail)))
    return [
        f"Q{d['qno']}: {d['selected_text']} (이유: {reason_labels[d['reason_selected_idx']]})"
        for d in picks
    ]

# 공통 라운드 렌더러

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
            return False

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

        # 결과 저장
        st.session_state.data[round_key] = {
            "duration_sec": elapsed,
            "score": score,
            "reason_score": reason_score,
            "answers": detail,
        }

        # 다음: MCP 애니메이션 페이지로 이동 (라운드별 구분)
        st.session_state.phase = "analyzing_r1" if round_key == "inference_nouns" else "analyzing_r2"
        st.rerun()
    return False

# 피드백(조건별·라운드별)

def render_praise(round_key: str, round_no: int, reason_labels):
    scroll_top_js()
    cond = st.session_state.get("praise_condition", "정서+구체")
    result = st.session_state.data.get(round_key, {})
    score = result.get("score", 0)
    reason_score = result.get("reason_score", 0)
    dur = result.get("duration_sec", 0)
    detail = result.get("answers", [])
    samples = _pick_samples(detail, reason_labels, k=2) if detail else []

    st.markdown("### ✅ AI 칭찬 피드백")
    if round_key == "inference_nouns":
        if cond == "정서+구체":
            st.success(
                f"1회차(명사구) 정말 훌륭합니다! **복수·소유 결합(…-t-mi)**, **우측 결합 사례(-ka)**, **정관(-ri) 말단 배치**까지 정확히 추론하셨어요. "
                f"정답 {score}/10, 이유 {reason_score}/10, 소요 {dur}초. 예: {', '.join(samples)}"
            )
        elif cond == "계산+구체":
            st.info(
                f"[명사구 요약] 정답 {score}/10 · 이유 {reason_score}/10 · {dur}초. "
                f"‘-t-mi’ 결합과 우측 결합 사례표지에서 높은 일치. 정관 위치는 소수 문항에서 개선 여지. "
                f"응답 샘플: {', '.join(samples)}"
            )
        elif cond == "정서+피상":
            st.success("명사구 규칙을 일관되게 적용하려는 태도가 인상적이었습니다. 다음 단계로 이어가겠습니다.")
        else:
            st.info("명사구 파트 저장 완료. 다음 단계로 이동합니다.")
        if st.button("다음(난이도 상향 문항)"):
            st.session_state.phase = "difficulty1"
            st.rerun()
    else:
        if cond == "정서+구체":
            st.success(
                f"2회차(동사 TAM)도 좋습니다! **시제 단서 해석**과 **상(완료/진행) 선택**, 그리고 **형태소 순서(동사+상+시제)** 추론이 탄탄합니다. "
                f"정답 {score}/10, 이유 {reason_score}/10, 소요 {dur}초. 예: {', '.join(samples)}"
            )
        elif cond == "계산+구체":
            st.info(
                f"[TAM 요약] 정답 {score}/10 · 이유 {reason_score}/10 · {dur}초. "
                f"‘이미/…까지’→완료(-mu), ‘지금/곧’→진행(-li) + 시제(-na/-tu/-ki) 매핑이 안정적입니다."
            )
        elif cond == "정서+피상":
            st.success("시간 단서와 사건 상태를 구분하는 판단이 전반적으로 매끄러웠습니다. 수고하셨습니다!")
        else:
            st.info("동사 파트 입력이 저장되었습니다. 다음 단계로 이동합니다.")
        if st.button("다음(학습동기 설문)"):
            st.session_state.phase = "motivation"
            st.rerun()

# 진입 안내
if st.session_state.phase == "inf_intro":
    scroll_top_js()
    st.markdown("## 추론 과제 안내")
    st.markdown(
        """
        - **1회차(명사구)**: 복수·소유 결합(…-t-mi), 우측 결합 사례(-ka), 소유 연쇄 어순, 정관(-ri) 위치 등 **NP 규칙** 추론(10문항).  
        - **2회차(동사)**: 시제(-na/-tu/-ki), 상(완료 -mu / 진행 -li), **형태소 순서(동사+상+시제)**, 상대시제 단서(이미/어제/내일/…까지) 등 **TAM 규칙** 추론(10문항).  
        - 각 문항은 **5지선다**이며, **추론 이유도 5지선다(단일)**입니다.
        """
    )
    with st.expander("📘 규칙 다시 보기", expanded=True):
        st.markdown(GRAMMAR_INFO_MD)
    if st.button("1회차 시작(명사구)"):
        st.session_state.phase = "inference_nouns"
        st.rerun()

elif st.session_state.phase == "inference_nouns":
    render_round("inference_nouns", "추론 과제 1/2 (명사구 문법)", build_items_nouns, REASON_NOUN)

elif st.session_state.phase == "analyzing_r1":
    scroll_top_js()
    page = st.empty()
    with page.container():
        if not st.session_state.get("_mcp1_started", False):
            st.session_state["_mcp1_started"] = True
            run_mcp_motion()
            st.session_state["_mcp1_done"] = True
            st.rerun()
        if st.session_state.get("_mcp1_done", False):
            st.markdown(
                """
                <div class='mcp-done-card' style="border:2px solid #2E7D32; border-radius:14px; padding:28px; background:#F9FFF9; max-width:820px; margin:48px auto;">
                  <h2 style="text-align:center; color:#2E7D32; margin-top:0;">✅ 분석이 완료되었습니다</h2>
                  <p style="font-size:16px; line-height:1.7; color:#222; text-align:center; margin:6px 0 0;">
                    COVNOX가 응답의 추론 패턴을 분석했습니다. <b>결과 보기</b>를 눌러 피드백을 확인하세요.
                  </p>
                </div>
                """,
                unsafe_allow_html=True,
            )
            _, mid, _ = st.columns([1, 2, 1])
            with mid:
                if st.button("결과 보기", use_container_width=True):
                    page.empty()
                    st.session_state["_mcp1_started"], st.session_state["_mcp1_done"] = False, False
                    st.session_state.phase = "praise_r1"
                    st.rerun()

elif st.session_state.phase == "praise_r1":
    render_praise("inference_nouns", 1, REASON_NOUN)

elif st.session_state.phase == "difficulty1":
    scroll_top_js()
    st.markdown("## 학습 난이도 상향 의향(1~10)")
    st.markdown("다음 라운드(동사)에서 난이도가 높아져도 <b>도전할 의향</b>을 선택해 주세요.", unsafe_allow_html=True)
    diff1 = st.slider("다음 라운드 난이도 상향 허용", min_value=1, max_value=10, value=5)
    if st.button("다음 (2회차 시작)"):
        st.session_state.data["difficulty_after_round1"] = int(diff1)
        st.session_state.phase = "inference_verbs"
        st.rerun()

elif st.session_state.phase == "inference_verbs":
    render_round("inference_verbs", "추론 과제 2/2 (동사 TAM)", build_items_verbs, REASON_VERB)

elif st.session_state.phase == "analyzing_r2":
    scroll_top_js()
    page = st.empty()
    with page.container():
        if not st.session_state.get("_mcp2_started", False):
            st.session_state["_mcp2_started"] = True
            run_mcp_motion()
            st.session_state["_mcp2_done"] = True
            st.rerun()
        if st.session_state.get("_mcp2_done", False):
            st.markdown(
                """
                <div class='mcp-done-card' style="border:2px solid #2E7D32; border-radius:14px; padding:28px; background:#F9FFF9; max-width:820px; margin:48px auto;">
                  <h2 style="text-align:center; color:#2E7D32; margin-top:0;">✅ 분석이 완료되었습니다</h2>
                  <p style="font-size:16px; line-height:1.7; color:#222; text-align:center; margin:6px 0 0;">
                    COVNOX가 응답의 추론 패턴을 분석했습니다. <b>결과 보기</b>를 눌러 피드백을 확인하세요.
                  </p>
                </div>
                """,
                unsafe_allow_html=True,
            )
            _, mid, _ = st.columns([1, 2, 1])
            with mid:
                if st.button("결과 보기", use_container_width=True):
                    page.empty()
                    st.session_state["_mcp2_started"], st.session_state["_mcp2_done"] = False, False
                    st.session_state.phase = "praise_r2"
                    st.rerun()

elif st.session_state.phase == "praise_r2":
    render_praise("inference_verbs", 2, REASON_VERB)

# ──────────────────────────────────────────────────────────────────────────────
# 4) 학습 동기 설문 + 최종 난이도 상향 의향(1~10)
# ──────────────────────────────────────────────────────────────────────────────
elif st.session_state.phase == "motivation":
    scroll_top_js()

    st.markdown("<h2 style='text-align:center; font-weight:bold;'>나의 생각과 가장 가까운 것을 선택해주세요.</h2>", unsafe_allow_html=True)

    st.markdown(
        """
    <div style='display:flex; justify-content:center; align-items:center; gap:12px; flex-wrap:wrap;\
                font-size:16px; margin-bottom:30px;'>
        <span style="white-space:nowrap;"><b>1점</b> : 전혀 그렇지 않다</span>
        <span>—</span>
        <span style="white-space:nowrap;"><b>3점</b> : 보통이다</span>
        <span>—</span>
        <span style="white-space:nowrap;"><b>5점</b> : 매우 그렇다</span>
    </div>
    """,
        unsafe_allow_html=True,
    )

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
        choice = st.radio(
            label=f"{i}. {q}",
            options=list(range(1, 6)),
            index=None,
            horizontal=True,
            key=f"motivation_{i}",
            label_visibility="visible",
        )
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
            st.session_state.phase = "phone_input"
            st.rerun()

# ──────────────────────────────────────────────────────────────────────────────
# 5) 휴대폰 번호 입력 → 저장 → 종료 안내
# ──────────────────────────────────────────────────────────────────────────────
elif st.session_state.phase == "phone_input":
    scroll_top_js()

    st.title("휴대폰 번호 입력")
    st.markdown(
        """
    연구 참여가 완료되었습니다. 감사합니다.  
    연구 답례품을 받을 휴대폰 번호를 입력해 주세요. (선택 사항)  
    입력하지 않아도 제출이 가능합니다. 다만, 미입력 시 답례품 전달이 어려울 수 있습니다.
    """
    )
    phone = st.text_input("휴대폰 번호", placeholder="010-1234-5678")

    if st.button("완료"):
        if phone.strip() and not validate_phone(phone):
            st.warning("올바른 형식이 아닙니다. (예: 010-1234-5678)")
        else:
            st.session_state.data["phone"] = phone.strip()
            st.session_state.data["endTime"] = datetime.now().isoformat()
            save_to_csv(st.session_state.data)
            st.session_state.phase = "result"
            st.rerun()

# ──────────────────────────────────────────────────────────────────────────────
# 6) 완료 화면
# ──────────────────────────────────────────────────────────────────────────────
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
        st.markdown(
            """
        <div style='font-size:16px; padding-top:10px;'>
            설문 응답이 성공적으로 저장되었습니다.<br>
            <b>이 화면은 자동으로 닫히지 않으니, 브라우저 탭을 수동으로 닫아 주세요.</b><br><br>
            ※ 본 연구에서 제공된 AI의 평가는 사전에 생성된 예시 대화문으로, 
            귀하의 실제 추론 능력을 직접 평가한 것이 아님을 알려드립니다.
        </div>
        """,
            unsafe_allow_html=True,
        )
