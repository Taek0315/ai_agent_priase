from __future__ import annotations

import html
import os
import time
import re
import textwrap
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import streamlit as st


def _options_dict(*texts: str) -> Dict[str, str]:
    return {str(i + 1): text for i, text in enumerate(texts)}


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _now_perf() -> float:
    return time.perf_counter()


def _session_id_for_item_number(item_number: int) -> int:
    if 1 <= item_number <= 5:
        return 1
    if 6 <= item_number <= 10:
        return 2
    return 3


_PLACEHOLDER_SUBSTRINGS: Tuple[str, ...] = (
    "(그래프 기준",
    "(요약문",
    "(계산상",
    "(연도별",
    "(요약",
    "(제시",
    "(제공",
    "TODO",
    "TBD",
    "예:",
)


def _is_dev_mode() -> bool:
    """
    Dev-only logging for stimulus QA.
    Enable by setting env `COVNOX_DEV=1`.
    """
    return str(os.getenv("COVNOX_DEV", "")).strip().lower() in {"1", "true", "yes", "y", "on"}


def _validate_no_authoring_placeholders(items: List[Dict[str, Any]]) -> None:
    """
    Fail fast when any NCS item contains authoring placeholders.
    This prevents shipping broken stimuli (e.g., '(요약문 제공)').
    """

    def _check_string(item_id: str, field: str, value: str) -> None:
        if not value:
            return
        for token in _PLACEHOLDER_SUBSTRINGS:
            if token and token in value:
                raise ValueError(
                    f"[TASK] Authoring placeholder detected: item={item_id} field={field} token={token!r} value={value!r}"
                )

    def _scan_info_blocks(item_id: str, blocks: Any) -> None:
        if not blocks:
            return
        if not isinstance(blocks, list):
            return
        for i, blk in enumerate(blocks):
            if not isinstance(blk, dict):
                continue
            _check_string(item_id, f"info_blocks[{i}].title", str(blk.get("title") or ""))
            _check_string(item_id, f"info_blocks[{i}].text", str(blk.get("text") or ""))
            for j, b in enumerate(list(blk.get("bullets") or [])):
                _check_string(item_id, f"info_blocks[{i}].bullets[{j}]", str(b or ""))
            table = dict(blk.get("table") or {})
            _check_string(item_id, f"info_blocks[{i}].table.caption", str(table.get("caption") or ""))
            for col in list(table.get("columns") or []):
                if isinstance(col, str):
                    _check_string(item_id, f"info_blocks[{i}].table.columns[]", col)
            for row in list(table.get("rows") or []):
                if isinstance(row, (list, tuple)):
                    for cell in row:
                        if isinstance(cell, str):
                            _check_string(item_id, f"info_blocks[{i}].table.rows[]", cell)

    for it in items:
        item_id = str(it.get("id") or it.get("item_number") or "unknown")
        _check_string(item_id, "instruction", str(it.get("instruction") or ""))
        _check_string(item_id, "stimulus_text", str(it.get("stimulus_text") or ""))
        _check_string(item_id, "question", str(it.get("question") or ""))
        for k, v in dict(it.get("options") or {}).items():
            _check_string(item_id, f"options[{k}]", str(v or ""))
        _scan_info_blocks(item_id, it.get("info_blocks"))
        # Defensive scan of chart/table labels too (titles/headers).
        chart = dict(it.get("chart_spec") or {})
        _check_string(item_id, "chart_spec.title", str(chart.get("title") or ""))
        for row in list(chart.get("data") or []):
            if isinstance(row, dict):
                for ck, cv in row.items():
                    if isinstance(cv, str):
                        _check_string(item_id, f"chart_spec.data[{ck}]", cv)
        table = dict(it.get("table_spec") or {})
        for col in list(table.get("columns") or []):
            if isinstance(col, str):
                _check_string(item_id, "table_spec.columns[]", col)
        for row in list(table.get("rows") or []):
            if isinstance(row, (list, tuple)):
                for cell in row:
                    if isinstance(cell, str):
                        _check_string(item_id, "table_spec.rows[]", cell)


def load_ncs_items() -> List[Dict[str, Any]]:
    """
    Returns the 15 NCS items (3 sessions) as a list of dicts.
    Text is exact per spec; do not translate.
    """
    items: List[Dict[str, Any]] = [
        # -------------------------
        # SESSION 1 (1–5)
        # -------------------------
        {
            "id": "ncs_s1_q1",
            "item_number": 1,
            "session_id": 1,
            "domain": "session1",
            "instruction": "서비스 운영 업무를 진행 중이다. \n 고객 CS 문의로 ‘결제 오류 발생으로 인한 환불 요청’이라고 문의가 들어왔다.",
            "stimulus_type": "text",
            "stimulus_text": "",
            "info_blocks": [
                {
                    "title": "",
                    "bullets": ["결제 오류는 관리부에서 담당한다.", "모든 업무 요청은 ‘업무 티켓’으로 전달한다.",
                    "환불은 서비스 운영에 있어 1순위 처리 업무다."],
                },
            ],
            "table_spec": {},
            "question": "다음 중 가장 먼저해야할 행동은 무엇인가?",
            "options": _options_dict(
                "1순위 처리 업무이기 때문에 관리부에 전화로 전달한다.",
                "관리부에 업무 티켓으로 문의 내용을 전달한다.",
                "고객에게 후속 처리 단계에 대한 안내 메일을 발송한다.",
                "고객 요청에 따라 바로 환불을 진행한다.",
                "결과 오류는 관리부 소관이기 때문에 무시한다.",
            ),
            "answer_key": "2",
        },
        {
            "id": "ncs_s1_q2",
            "item_number": 2,
            "session_id": 1,
            "domain": "session1",
            "instruction": "배송 관련 확인 요청이 왔다. \n 다만 문의 요청이 밀려있어 순차적으로 문의를 처리해야한다.",
            "stimulus_type": "text",
            "stimulus_text": "",
            "info_blocks": [
                {
                    "title": "B 배송사 문의 처리 순서",
                    "bullets": ["문의 요청 시 출고 순서별로 가장 먼저 처리한다.", "출고 순서가 같다면 결제일이 가장 빠른순으로 처리한다."],
                },
            ],
            "table_spec": {},
            "question": "다음 주문 중 가장 먼저 처리해야하는 주문은 무엇인가?",
            "options": _options_dict(
                "주문 A(오늘 출고/12월 21일)",
                "주문 B(모레 출고/12월 21일)",
                "주문 C(내일 출고/12월 19일)",
                "주문 D(오늘 출고/12월 19일)",
                "주문 E(내일 출고/12월 03일)",
            ),
            "answer_key": "4",
        },
        {
            "id": "ncs_s1_q3",
            "item_number": 3,
            "session_id": 1,
            "domain": "session1",
            "instruction": "지금 당장 협력사에 계약을 위한 관련 자료를 전달해야한다. \n 해당 자료가 누락되면 계약 진행에 어려움이 있다.\n 다만 자료안에 개인 정보가 포함되어 있다.",
            "stimulus_type": "text",
            "stimulus_text": "",
            "info_blocks": [
                {
                    "title": "",
                    "bullets": ["개인정보는 ‘보안 전송 링크’로만 보낸다.", "보안 전송 링크는 생성에 2일이 소요된다.", "긴급한 사항일 경우 개인 정보는 마스킹 처리 후 팩스로 보낸다."],
                },
            ],
            "table_spec": {},
            "question": "다음 중 가장 적절한 행동은 무엇인가?",
            "options": _options_dict(
                "개인 정보가 포함되어 있기 때문에 보안 전송 링크로 보낸다.",
                "계약 진행으로 인해 긴급한 상황이기에 마스킹 된 팩스 자료를 전달한다.",
                "보안 링크 결재에 시간이 걸리기 때문에 협력사에게 들어오라고 한다.",
                "믿을 수 있는 업체를 사용하여 퀵으로 보낸다.",
                "관련 자료를 직접 들고 협력사로 전달한다.",
            ),
            "answer_key": "2",
        },
        {
            "id": "ncs_s1_q4",
            "item_number": 4,
            "session_id": 1,
            "domain": "session1",
            "instruction": "웹사이트 유지보수를 위해 SI 업체 1곳을 골라야 한다.",
            "stimulus_type": "text",
            "stimulus_text": "",
            "info_blocks": [
                {
                    "title": "",
                    "bullets": ["기간이 18개월 이상 중 ‘견적’이 가장 낮은 곳을 고른다."],
                },
            ],
            "table_spec": {},
            "question": "다음중 가장 적절한 업체는 무엇인가?",
            "options": _options_dict(
                "가 업체: 24개월/120만원",
                "나 업체: 18개월/95만원",
                "다 업체: 24개월/108만원",
                "라 업체: 18개월/97만원",
                "마 업체: 15개월/90만원",
            ),
            "answer_key": "2",
        },
        {
            "id": "ncs_s1_q5",
            "item_number": 5,
            "session_id": 1,
            "domain": "session1",
            "instruction": "오늘 수행할 작업에 대해 계획을 세우고 있다",
            "stimulus_type": "text",
            "stimulus_text": "",
            "info_blocks": [
                {
                    "title": "",
                    "bullets": ["A: 우선 순위 중 / 단독 처리", "B: 우선 순위 상 / 동시 처리 가능", "C: 우선 순위 상 / 단독 처리", "D: 우선 순위 하 / 동시 처리 가능"],
                },
            ],
            "table_spec": {},
            "question": "가장 효율적인 작업 순서는 무엇인가?",
            "options": _options_dict(
                "C → B → A → D",
                "C → A → B&D",
                "B → C → A → D",
                "A → B → C → D",
                "C → B&D → A",
            ),
            "answer_key": "5",
        },
        # -------------------------
        # SESSION 2 (6–10)
        # -------------------------
        {
            "id": "ncs_s2_q6",
            "item_number": 6,
            "session_id": 2,
            "domain": "session2",
            "instruction": "D는 오후만 가능하다. 회의 일정 1개를 확정한다.",
            "stimulus_type": "text",
            "stimulus_text": "",
            "info_blocks": [
                {
                    "title": "",
                    "bullets": [
                        "필수: B·D 참석 / 회의실은 오전만 사용",
                        "예외: D가 오후만 가능하면 ‘오후 온라인’으로 진행",
                    ],
                },
            ],
            "table_spec": {},
            "question": "조건에 따라 가장 적절한 행동은 무엇인가?",
            "options": _options_dict(
                "오전 회의실로 잡는다(B·D 참석).",
                "오후 온라인으로 잡는다(B·D 참석).",
                "오전 온라인으로 잡는다(B·D 참석).",
                "오후 회의실로 잡는다(B·D 참석).",
                "일정을 미룬다.",
            ),
            "answer_key": "2",
        },
        {
            "id": "ncs_s2_q7",
            "item_number": 7,
            "session_id": 2,
            "domain": "session2",
            "instruction": "구매 요청 1건을 지금 승인한다.",
            "stimulus_type": "text",
            "stimulus_text": "",
            "info_blocks": [
                {
                    "title": "",
                    "bullets": [
                        "필수: 30만원 이하 / 부서 확인 O",
                        "예외: 안전 문제면 금액 조건을 무시하고 그 건을 승인",
                    ],
                },
            ],
            "table_spec": {},
            "question": "조건에 따라 가장 적절한 행동은 무엇인가?",
            "options": _options_dict(
                "요청 A(안전 O/50만원/확인 O)를 승인한다.",
                "요청 B(안전 X/20만원/확인 O)를 승인한다.",
                "요청 C(안전 X/20만원/확인 X)를 승인한다.",
                "요청 D(안전 O/50만원/확인 X)를 승인한다.",
                "요청 E(안전 X/40만원/확인 O)를 승인한다.",
            ),
            "answer_key": "1",
        },
        {
            "id": "ncs_s2_q8",
            "item_number": 8,
            "session_id": 2,
            "domain": "session2",
            "instruction": "장애는 이미 정상화됐다. 공지 문구 1개를 보낸다.",
            "stimulus_type": "text",
            "stimulus_text": "",
            "info_blocks": [
                {
                    "title": "",
                    "bullets": [
                        "필수: 원인 단정 금지 / 문의처 포함",
                        "예외: 정상화된 경우 ‘정상화’ 표현은 허용",
                    ],
                },
            ],
            "table_spec": {},
            "question": "조건에 따라 가장 적절한 행동은 무엇인가?",
            "options": _options_dict(
                "“현재 정상화되었습니다. 문의: help@company.com”",
                "“원인은 서버 오류로 확인되었습니다. 문의: help@company.com”",
                "“현재 정상화되었습니다.”",
                "“오늘 15:00에 정상화됩니다. 문의: help@company.com”",
                "“원인은 미정입니다. 문의처는 없습니다.”",
            ),
            "answer_key": "1",
        },
        {
            "id": "ncs_s2_q9",
            "item_number": 9,
            "session_id": 2,
            "domain": "session2",
            "instruction": "로그 조회 요청 1건을 승인한다.",
            "stimulus_type": "text",
            "stimulus_text": "",
            "info_blocks": [
                {
                    "title": "",
                    "bullets": [
                        "필수: 업무 목적 O / 7일 이내",
                        "예외: 사고 조사면 30일까지 허용",
                    ],
                },
            ],
            "table_spec": {},
            "question": "조건에 따라 가장 적절한 행동은 무엇인가?",
            "options": _options_dict(
                "요청 A(사고 O/30일/목적 O)를 승인한다.",
                "요청 B(사고 X/14일/목적 O)를 승인한다.",
                "요청 C(사고 X/7일/목적 X)를 승인한다.",
                "요청 D(사고 O/30일/목적 X)를 승인한다.",
                "요청 E(사고 X/3일/목적 X)를 승인한다.",
            ),
            "answer_key": "1",
        },
        {
            "id": "ncs_s2_q10",
            "item_number": 10,
            "session_id": 2,
            "domain": "session2",
            "instruction": "초과근무 신청 1건을 처리한다.",
            "stimulus_type": "text",
            "stimulus_text": "",
            "info_blocks": [
                {
                    "title": "",
                    "bullets": [
                        "필수: 사전 신청 O / 팀장 승인 O",
                        "예외: 긴급 장애 대응이면 사전 신청 없이도 처리",
                    ],
                },
            ],
            "table_spec": {},
            "question": "조건에 따라 가장 적절한 행동은 무엇인가?",
            "options": _options_dict(
                "신청 A(긴급 O/사전 X/승인 O)를 승인한다.",
                "신청 B(긴급 X/사전 O/승인 X)를 승인한다.",
                "신청 C(긴급 X/사전 X/승인 O)를 승인한다.",
                "신청 D(긴급 O/사전 X/승인 X)를 승인한다.",
                "신청 E(긴급 X/사전 O/승인 X)를 승인한다.",
            ),
            "answer_key": "1",
        },
        # -------------------------
        # SESSION 3 (11–15)
        # -------------------------
        {
            "id": "ncs_s3_q11",
            "item_number": 11,
            "session_id": 3,
            "domain": "session3",
            "instruction": "비정상 다운로드가 감지됐다.",
            "stimulus_type": "text",
            "stimulus_text": "",
            "info_blocks": [
                {
                    "title": "",
                    "bullets": ["확산 차단을 먼저 한다.", "로그를 보존한 뒤 보안팀에 보고한다."],
                },
            ],
            "table_spec": {},
            "question": "조건에 따라 가장 적절한 행동은 무엇인가?",
            "options": _options_dict(
                "접근을 차단하고 로그를 보존한 뒤 보안팀에 보고한다.",
                "로그를 지우고 재시작한다.",
                "외부에 먼저 알린다.",
                "로그만 보고 차단은 하지 않는다.",
                "아무 조치도 하지 않는다.",
            ),
            "answer_key": "1",
        },
        {
            "id": "ncs_s3_q12",
            "item_number": 12,
            "session_id": 3,
            "domain": "session3",
            "instruction": "알림 5개 중 1개만 먼저 본다.",
            "stimulus_type": "text",
            "stimulus_text": "",
            "info_blocks": [
                {
                    "title": "",
                    "bullets": ["개인정보 위험을 먼저 본다.", "같으면 더 이른 시각을 먼저 본다."],
                },
            ],
            "table_spec": {},
            "question": "조건에 따라 가장 적절한 행동은 무엇인가?",
            "options": _options_dict(
                "A(성능/02:13)를 먼저 본다.",
                "B(개인정보/02:17)를 먼저 본다.",
                "C(결제/02:15)를 먼저 본다.",
                "D(로그인/02:12)를 먼저 본다.",
                "E(개인정보/02:19)를 먼저 본다.",
            ),
            "answer_key": "2",
        },
        {
            "id": "ncs_s3_q13",
            "item_number": 13,
            "session_id": 3,
            "domain": "session3",
            "instruction": "오늘 처리할 요청 1건을 고른다.",
            "stimulus_type": "text",
            "stimulus_text": "",
            "info_blocks": [
                {
                    "title": "",
                    "bullets": ["되돌리기 쉬운 것을 우선한다.", "같으면 고객 영향이 큰 것을 우선한다."],
                },
            ],
            "table_spec": {},
            "question": "조건에 따라 가장 적절한 행동은 무엇인가?",
            "options": _options_dict(
                "요청 A(되돌림 쉬움/영향 높음)를 선택한다.",
                "요청 B(되돌림 어려움/영향 높음)를 선택한다.",
                "요청 C(되돌림 쉬움/영향 낮음)를 선택한다.",
                "요청 D(되돌림 어려움/영향 낮음)를 선택한다.",
                "요청 E(되돌림 쉬움/영향 중간)를 선택한다.",
            ),
            "answer_key": "1",
        },
        {
            "id": "ncs_s3_q14",
            "item_number": 14,
            "session_id": 3,
            "domain": "session3",
            "instruction": "지연 안내 메시지 1개를 고른다.",
            "stimulus_type": "text",
            "stimulus_text": "",
            "info_blocks": [
                {
                    "title": "",
                    "bullets": ["확정 시간은 쓰지 않는다.", "다음 안내 시점을 포함한다."],
                },
            ],
            "table_spec": {},
            "question": "조건에 따라 가장 적절한 행동은 무엇인가?",
            "options": _options_dict(
                "“지연이 발생했습니다. 다음 안내는 오늘 오후에 드리겠습니다.”",
                "“지연이 발생했습니다. 15:00에 다시 안내하겠습니다.”",
                "“지연이 발생했습니다.”",
                "“지연 원인은 시스템 오류입니다. 다음 안내는 오늘 오후에 드리겠습니다.”",
                "“곧 안내하겠습니다.”",
            ),
            "answer_key": "1",
        },
        {
            "id": "ncs_s3_q15",
            "item_number": 15,
            "session_id": 3,
            "domain": "session3",
            "instruction": "새 시스템 전환 계획 1개를 고른다.",
            "stimulus_type": "text",
            "stimulus_text": "",
            "info_blocks": [
                {
                    "title": "",
                    "bullets": ["가이드 배포를 포함한다.", "지원 창구(담당자)를 지정한다."],
                },
            ],
            "table_spec": {},
            "question": "조건에 따라 가장 적절한 행동은 무엇인가?",
            "options": _options_dict(
                "계획 A(가이드 O/지원창구 O)를 선택한다.",
                "계획 B(가이드 X/지원창구 O)를 선택한다.",
                "계획 C(가이드 O/지원창구 X)를 선택한다.",
                "계획 D(가이드 X/지원창구 X)를 선택한다.",
                "계획 E(가이드 O/지원창구 X)를 선택한다.",
            ),
            "answer_key": "1",
        },
    ]

    # Ensure session_id is consistent with item_number.
    for it in items:
        it["session_id"] = _session_id_for_item_number(_safe_int(it.get("item_number")))
    _validate_no_authoring_placeholders(items)
    return items


def render_ncs_item(
    item: Dict[str, Any], item_index: int, total_items: int
) -> Tuple[Optional[str], List[str], Dict[str, Any]]:
    """
    Render one NCS item.

    Returns:
      - selected_option_key: "1".."5" or None
      - selected_rationales: list[str] (always empty; rationale selection removed)
      - response_meta: dict with timing + validity flags
    """
    # Stable per-item keys (avoid collisions across reruns)
    item_id = str(item.get("id") or f"item_{item_index+1}")
    ss_prefix = f"ncs_{item_id}"

    if _is_dev_mode():
        print(
            f"[NCS_RENDER] session={item.get('session_id')} item_number={item.get('item_number')} id={item_id} stimulus_type={item.get('stimulus_type')}"
        )

    st.header(f"문항 {item_index + 1} / {total_items}")

    def _escape(s: Any) -> str:
        return html.escape(str(s or ""), quote=True)

    def _render_card(label: str, content: str, *, badge: Optional[str] = None) -> None:
        badge_html = f'<div class="question-badge">{_escape(badge)}</div>' if badge else ""
        content_html = _escape(content).replace("\n", "<br/>")
        st.markdown(
            f"""
<div class="question-card">
  {badge_html}
  <div class="question-label">{_escape(label)}</div>
  <p class="question-stem">{content_html}</p>
</div>
""",
            unsafe_allow_html=True,
        )

    def _render_small_table(columns: List[Any], rows: List[Any], *, caption: str = "") -> None:
        safe_cols = [_escape(c) for c in list(columns or [])]
        safe_rows: List[List[str]] = []
        for r in list(rows or []):
            if isinstance(r, dict):
                safe_rows.append([_escape(r.get(c, "")) for c in columns])
            elif isinstance(r, (list, tuple)):
                safe_rows.append([_escape(c) for c in list(r)])
            else:
                safe_rows.append([_escape(r)])

        caption_html = f"<div class='task-table-caption'>{_escape(caption)}</div>" if caption else ""
        head_html = "".join([f"<th>{c}</th>" for c in safe_cols]) if safe_cols else ""
        body_html = ""
        for rr in safe_rows:
            tds = "".join([f"<td>{c}</td>" for c in rr])
            body_html += f"<tr>{tds}</tr>"

        st.markdown(
            f"""
{caption_html}
<div class="task-table-wrap">
  <table class="task-table">
    {'<thead><tr>' + head_html + '</tr></thead>' if head_html else ''}
    <tbody>
      {body_html}
    </tbody>
  </table>
</div>
""",
            unsafe_allow_html=True,
        )

    def _render_info_block(block: Dict[str, Any]) -> None:
        title = str(block.get("title") or "").strip()
        text = str(block.get("text") or "").strip()
        bullets = list(block.get("bullets") or [])
        table = dict(block.get("table") or {})

        body_parts: List[str] = []
        if text:
            body_parts.append(f'<div class="task-quote">{_escape(text)}</div>')
        if bullets:
            items_html = "".join([f"<li>{_escape(b)}</li>" for b in bullets if str(b or "").strip()])
            body_parts.append(f'<ul class="task-bullets">{items_html}</ul>')

        title_html = f'<div class="task-block-title">{_escape(title)}</div>' if title else ""
        st.markdown(
            f"""
<div class="task-block">
  {title_html}
  <div class="task-block-body">
    {''.join(body_parts) if body_parts else ''}
  </div>
</div>
""",
            unsafe_allow_html=True,
        )

        if table:
            _render_small_table(
                list(table.get("columns") or []),
                list(table.get("rows") or []),
                caption=str(table.get("caption") or ""),
            )

    # Instruction (card)
    instruction = str(item.get("instruction", "") or "").strip()
    if instruction:
        _render_card("상황", instruction)

    stimulus_type = str(item.get("stimulus_type", "text") or "text")
    stimulus_text = str(item.get("stimulus_text", "") or "")
    info_blocks: List[Dict[str, Any]] = list(item.get("info_blocks") or [])

    # Conditions (structured blocks)
    if info_blocks or stimulus_text:
        for blk in info_blocks:
            if isinstance(blk, dict):
                _render_info_block(blk)

        # Legacy fallback: render remaining stimulus text only when it's short.
        # (Avoid dense paragraphs; prefer authoring via info_blocks.)
        if stimulus_text and not info_blocks:
            lines = [ln.strip() for ln in stimulus_text.splitlines() if ln.strip()]
            if len(lines) <= 3:
                _render_info_block({"title": "Information", "bullets": lines})
            else:
                _render_info_block(
                    {"title": "Information", "bullets": lines[:8] + (["(… 생략 …)"] if len(lines) > 8 else [])}
                )

    if stimulus_type in {"table", "table+chart"}:
        spec = dict(item.get("table_spec") or {})
        columns = list(spec.get("columns") or [])
        rows = list(spec.get("rows") or [])
        if columns and rows:
            st.markdown('<div class="task-section-title">자료 (표)</div>', unsafe_allow_html=True)
            _render_small_table(columns, rows)

    if stimulus_type in {"chart", "table+chart"}:
        spec = dict(item.get("chart_spec") or {})
        data = list(spec.get("data") or [])
        x = spec.get("x")
        y = spec.get("y")
        title = spec.get("title") or ""
        if data and x and y:
            st.markdown('<div class="task-section-title">자료 (그래프)</div>', unsafe_allow_html=True)
            # Altair is used to keep charts responsive and consistent.
            import altair as alt

            df = pd.DataFrame(data)
            chart = (
                alt.Chart(df, title=title)
                .mark_bar()
                .encode(
                    x=alt.X(str(x), sort=None),
                    y=alt.Y(str(y)),
                    tooltip=[alt.Tooltip(str(x)), alt.Tooltip(str(y))],
                )
            )
            st.altair_chart(chart, use_container_width=True)

    # Question (card) + options
    question_text = str(item.get("question", "") or "")
    if question_text:
        _render_card("질문", question_text)

    options: Dict[str, str] = dict(item.get("options") or {})
    option_keys = list(options.keys())

    _allocation_token_re = re.compile(r"([A-G])\s*([0-9]+)")
    _schedule_option_re = re.compile(r"^\s*(오전|오후)\s*/\s*회의실\s*([A-Z])\s*/\s*([A-E](?:\s*,\s*[A-E])*)\s*참석\s*$")

    def _format_option_value_for_display(raw: str) -> str:
        """
        Improve readability of long/structured options without changing content.
        - Keeps semantics identical (adds only line breaks/spacing).
        - Special-cases resource allocation patterns like: "A200 B200 ... (잔여 100만 원)".
        """
        text = str(raw or "").strip()
        if not text:
            return ""
        if "\n" in text:
            return text

        # Meeting schedule option (e.g., Session 2 item 6): add line breaks + labels.
        m = _schedule_option_re.match(text)
        if m:
            time_of_day = m.group(1)
            room = m.group(2)
            attendees = m.group(3).replace(" ", "")
            return "\n".join(
                [
                    f"시간: {time_of_day}",
                    f"회의실: {room}",
                    f"참석: {attendees}",
                ]
            )

        # Allocation-style option (e.g., Session 2 item 10).
        tokens = _allocation_token_re.findall(text)
        token_map = {k: v for k, v in tokens}
        if len(tokens) >= 5 and {"A", "B", "C"}.issubset(set(token_map.keys())):
            tail_note = ""
            m = re.search(r"\(([^)]*)\)\s*$", text)
            if m:
                tail_note = m.group(1).strip()

            # Align amounts for faster visual scanning.
            amount_by_letter: Dict[str, str] = {}
            for letter in "ABCDEFG":
                if letter in token_map:
                    try:
                        amount = int(token_map[letter])
                        amount_by_letter[letter] = f"{amount:,}"
                    except Exception:
                        amount_by_letter[letter] = str(token_map[letter])
            width = max((len(v) for v in amount_by_letter.values()), default=0)

            lines: List[str] = []
            for letter in "ABCDEFG":
                if letter in amount_by_letter:
                    amt = amount_by_letter[letter].rjust(width)
                    lines.append(f"{letter}: {amt}만 원")
            if tail_note:
                if tail_note.startswith("잔여") and not tail_note.startswith("잔여:"):
                    tail_note = tail_note.replace("잔여", "잔여:", 1)
                lines.append(tail_note)
            return "\n".join(lines)

        # Generic long-text wrapping (keeps wording; adds line breaks only).
        if len(text) >= 55:
            return textwrap.fill(
                text,
                width=34,
                break_long_words=False,
                break_on_hyphens=False,
            )

        return text

    inputs_disabled = bool(st.session_state.get("in_mcp", False)) or bool(
        st.session_state.get("ncs_inputs_disabled", False)
    )

    selected_key = st.radio(
        "선택지",
        options=option_keys,
        index=None,
        label_visibility="collapsed",
        format_func=lambda k: (
            f"{k})\n{_format_option_value_for_display(options.get(str(k), ''))}"
            if "\n" in _format_option_value_for_display(options.get(str(k), ""))
            else f"{k}) {_format_option_value_for_display(options.get(str(k), ''))}"
        ),
        key=f"{ss_prefix}_answer",
        disabled=inputs_disabled,
    )
    selected_key = str(selected_key) if selected_key is not None else None
    answer_valid = bool(selected_key) and selected_key in options

    # NOTE: Rationale selection is intentionally removed for NCS-style tasks.
    # Keep return signature stable (selected_rationales stays empty) so callers can
    # safely persist legacy fields as blanks without changing storage schema.
    return selected_key, [], {
        "answer_valid": bool(answer_valid),
    }


def compute_ncs_results(
    responses: List[Dict[str, Any]], items: List[Dict[str, Any]]
) -> Tuple[int, float, List[bool], Dict[str, Any]]:
    item_by_id = {str(it.get("id")): it for it in items}
    per_item_correct: List[bool] = []
    correct = 0
    for resp in responses:
        item_id = str(resp.get("item_id") or resp.get("id") or "")
        item = item_by_id.get(item_id, {})
        correct_key = str(item.get("answer_key") or resp.get("correct_answer_key") or "")
        selected_key = str(resp.get("participant_selected_key") or resp.get("selected_key") or "")
        is_ok = bool(selected_key and correct_key and selected_key == correct_key)
        per_item_correct.append(is_ok)
        if is_ok:
            correct += 1

    total = len(items) if items else 0
    accuracy = (correct / total) if total else 0.0
    summary = {
        "total_items": total,
        "correct_count": correct,
        "accuracy": round(accuracy, 4),
    }
    return correct, accuracy, per_item_correct, summary


def build_ncs_payload(
    responses: List[Dict[str, Any]],
    results: Tuple[int, float, List[bool], Dict[str, Any]],
    timing: Dict[str, Any],
    session_meta: Dict[str, Any],
) -> Dict[str, Any]:
    score, accuracy, per_item_correct, summary = results
    return {
        "task_type": "ncs_multi_session_v1",
        "ncs_summary": {
            **summary,
            "score": int(score),
            "accuracy": float(accuracy),
            "per_item_correct": list(per_item_correct),
        },
        "ncs_responses": list(responses),
        "timing": dict(timing or {}),
        "session_meta": dict(session_meta or {}),
    }

