from __future__ import annotations

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

    for it in items:
        item_id = str(it.get("id") or it.get("item_number") or "unknown")
        _check_string(item_id, "instruction", str(it.get("instruction") or ""))
        _check_string(item_id, "stimulus_text", str(it.get("stimulus_text") or ""))
        _check_string(item_id, "question", str(it.get("question") or ""))
        for k, v in dict(it.get("options") or {}).items():
            _check_string(item_id, f"options[{k}]", str(v or ""))
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
            "domain": "의사소통능력 · 기초 자료해석",
            "instruction": "다음은 사내 교육 프로그램에 대한 공고문이다. 내용을 읽고 물음에 답하시오.",
            "stimulus_type": "text",
            "stimulus_text": "「2026년 신입사원 직무역량 강화 교육」은 3월 15일(금) 오전 10시부터 오후 4시까지 본사 2층 대회의실에서 진행된다. 교육 신청은 3월 10일(월)까지 인사팀 이메일로 접수해야 하며, 점심 식사는 회사에서 제공한다.",
            "question": "위 공고문의 내용과 일치하는 것은 무엇인가?",
            "options": _options_dict(
                "교육은 오전 9시에 시작한다",
                "교육 장소는 본사 1층이다",
                "신청 마감일은 3월 10일이다",
                "점심 식사는 개인 부담이다",
                "교육은 이틀간 진행된다",
            ),
            "answer_key": "3",
        },
        {
            "id": "ncs_s1_q2",
            "item_number": 2,
            "session_id": 1,
            "domain": "의사소통능력 · 기초 자료해석",
            "instruction": "다음은 부서별 월간 보고서 제출 건수를 나타낸 막대그래프이다.",
            "stimulus_type": "chart",
            "chart_spec": {
                "data": [
                    {"부서": "인사팀", "제출건수": 12},
                    {"부서": "재무팀", "제출건수": 9},
                    {"부서": "영업팀", "제출건수": 15},
                    {"부서": "개발팀", "제출건수": 11},
                    {"부서": "고객지원팀", "제출건수": 8},
                ],
                "x": "부서",
                "y": "제출건수",
                "title": "부서별 월간 보고서 제출 건수",
            },
            "question": "그래프를 보고 제출 건수가 가장 많은 부서는 어디인가?",
            "options": _options_dict("인사팀", "재무팀", "영업팀", "개발팀", "고객지원팀"),
            "answer_key": "3",
        },
        {
            "id": "ncs_s1_q3",
            "item_number": 3,
            "session_id": 1,
            "domain": "의사소통능력 · 기초 자료해석",
            "instruction": "다음 두 문장을 읽고 결론으로 가장 적절한 것을 고르시오.",
            "stimulus_type": "text",
            "stimulus_text": "모든 팀 회의는 팀장이 참석해야 한다.\n\n오늘 회의에는 팀장이 참석하지 않았다.",
            "question": "위 문장으로부터 도출할 수 있는 결론은 무엇인가?",
            "options": _options_dict(
                "오늘 회의는 팀 회의이다",
                "오늘 회의는 취소되었다",
                "오늘 회의는 팀 회의가 아니다",
                "팀장은 다른 회의에 참석했다",
                "모든 회의에는 팀장이 필요 없다",
            ),
            "answer_key": "3",
        },
        {
            "id": "ncs_s1_q4",
            "item_number": 4,
            "session_id": 1,
            "domain": "의사소통능력 · 기초 자료해석",
            "instruction": "다음은 비즈니스 이메일의 일부이다. 가장 적절한 수정이 필요한 부분을 고르시오.",
            "stimulus_type": "text",
            "stimulus_text": "“회의 자료는 첨부파일로 보내드렸으며, 검토 후 회신 부탁드립니다. 감사합니다.”",
            "question": "위 문장에서 수정이 필요한 부분은 무엇인가?",
            "options": _options_dict(
                "회의 자료",
                "첨부파일로",
                "보내드렸으며",
                "검토 후 회신 부탁드립니다",
                "수정할 부분이 없다",
            ),
            "answer_key": "5",
        },
        {
            "id": "ncs_s1_q5",
            "item_number": 5,
            "session_id": 1,
            "domain": "의사소통능력 · 기초 자료해석",
            "instruction": "다음 표는 두 부서의 월별 소모품 비용이다.",
            "stimulus_type": "table",
            "table_spec": {
                "columns": ["부서", "1월", "2월"],
                "rows": [
                    ["A부서", "120,000원", "150,000원"],
                    ["B부서", "100,000원", "130,000원"],
                ],
            },
            "question": "A부서의 1월과 2월 소모품 비용의 합계는 얼마인가?",
            "options": _options_dict(
                "250,000원",
                "260,000원",
                "270,000원",
                "280,000원",
                "300,000원",
            ),
            "answer_key": "3",
        },
        # -------------------------
        # SESSION 2 (6–10)
        # -------------------------
        {
            "id": "ncs_s2_q6",
            "item_number": 6,
            "session_id": 2,
            "domain": "자원관리능력 · 상황판단",
            "instruction": "아래 조건을 모두 만족하는 회의 일정(시간/회의실/참석 인원)을 고르시오.",
            "stimulus_type": "text",
            "stimulus_text": "\n".join(
                [
                    "- 팀원은 총 5명(A,B,C,D,E)이며 최소 4명이 참석해야 한다.",
                    "- A는 오전만 가능",
                    "- B는 오전·오후 모두 가능",
                    "- C는 오후만 가능",
                    "- D는 오후만 가능",
                    "- E는 오전·오후 모두 가능",
                    "- 회의실 A는 오전만 사용 가능 / 회의실 B는 오후만 사용 가능",
                    "- 참석 1인당 비용은 12만 원이며, 총 비용은 50만 원을 초과할 수 없다.",
                ]
            ),
            "question": "조건을 모두 만족하는 일정은 무엇인가?",
            "options": _options_dict(
                "오전 / 회의실 A / A,B,C,E 참석",
                "오전 / 회의실 A / A,B,E,D 참석",
                "오후 / 회의실 B / C,D,E,B 참석",
                "오후 / 회의실 B / C,D,E,A 참석",
                "오후 / 회의실 A / C,D,E,A 참석",
            ),
            "answer_key": "3",
        },
        {
            "id": "ncs_s2_q7",
            "item_number": 7,
            "session_id": 2,
            "domain": "자원관리능력 · 상황판단",
            "instruction": "다음은 후보지 3곳의 평가 점수(1~10점)이다. 가중치를 반영해 종합점수가 가장 높은 후보지를 고르시오.",
            "stimulus_type": "table",
            "stimulus_text": "\n".join(
                [
                    "- 임대료(낮을수록 유리): 40%",
                    "- 접근성: 35%",
                    "- 공간 크기: 25%",
                    "",
                    "※ 임대료는 “낮을수록 유리”이므로, 표의 ‘임대료 점수’는 이미 “낮을수록 높은 점수”로 환산된 값이다(그대로 사용).",
                ]
            ),
            "table_spec": {
                "columns": ["후보지", "임대료 점수", "접근성", "공간 크기"],
                "rows": [
                    ["A", 7, 6, 8],
                    ["B", 6, 9, 7],
                    ["C", 8, 5, 7],
                ],
            },
            "question": "가중치를 반영한 종합점수가 가장 높은 후보지는?",
            "options": _options_dict("A", "B", "C", "A와 C", "모두 동일"),
            "answer_key": "2",
        },
        {
            "id": "ncs_s2_q8",
            "item_number": 8,
            "session_id": 2,
            "domain": "자원관리능력 · 상황판단",
            "instruction": "다음 조건을 모두 참으로 만들 수 있는 선택지를 고르시오.",
            "stimulus_type": "text",
            "stimulus_text": "\n".join(
                [
                    "1) A가 참이면 B는 거짓이다.",
                    "2) B가 거짓이면 C는 참이다.",
                    "3) C가 참이면 D는 거짓이다.",
                    "4) D는 참이다.",
                ]
            ),
            "question": "위 조건을 모두 만족하는 판단은 무엇인가?",
            "options": _options_dict(
                "A는 참이다",
                "B는 참이다",
                "C는 참이다",
                "A와 C는 모두 참이다",
                "만족하는 조건이 없다",
            ),
            "answer_key": "5",
        },
        {
            "id": "ncs_s2_q9",
            "item_number": 9,
            "session_id": 2,
            "domain": "자원관리능력 · 상황판단",
            "instruction": "다음은 회사 출장비 규정이다.",
            "stimulus_type": "text",
            "stimulus_text": "\n".join(
                [
                    "- 원칙: 출장비는 ‘사전 승인’ 후 지급한다.",
                    "- 예외: 아래 두 조건을 모두 만족하면 사후 지급을 허용한다.",
                    "  (i) 천재지변 또는 ‘대체 불가능한 긴급 상황’",
                    "  (ii) 사전 승인 절차를 진행할 ‘현실적 시간’이 없었음이 기록으로 남아야 함",
                ]
            ),
            "question": "다음 중 예외 지급 대상에 해당하는 사례는 무엇인가?",
            "options": _options_dict(
                "개인 일정 변경으로 당일 출장으로 변경(승인 없이 출발)",
                "사전 승인 후 출장(정상 절차)",
                "태풍으로 인한 설비 긴급 점검 요청으로 즉시 현장 출동(메일/메신저 기록 존재)",
                "출장 후 개인 사유로 비용 항목 추가 요청",
                "승인 절차를 누락했으나 긴급 상황 기록이 없는 일반 출장",
            ),
            "answer_key": "3",
        },
        {
            "id": "ncs_s2_q10",
            "item_number": 10,
            "session_id": 2,
            "domain": "자원관리능력 · 상황판단",
            "instruction": "총 예산 1,000만 원을 7개 사업(A~G)에 배분한다.",
            "stimulus_type": "text",
            "stimulus_text": "\n".join(
                [
                    "- 필수 사업 A,B,C는 각각 최소 200만 원 이상 배정해야 한다.",
                    "- 사업 D,E는 각각 최소 50만 원 이상 배정해야 한다.",
                    "- 사업 F,G는 선택 사업이며, 배정 시 각각 최소 100만 원 이상이어야 한다.",
                    "- 예산을 ‘가능한 한 많이’ 집행하여 잔여 예산이 최소가 되도록 할 때, 가능한 배분안 중 잔여 예산이 가장 적은 것은?",
                ]
            ),
            "question": "가능한 배분안 중 잔여 예산이 가장 적은 것은?",
            "options": _options_dict(
                "A200 B200 C200 D50 E50 F100 G100 (잔여 100만 원)",
                "A250 B200 C200 D50 E50 F100 G100 (잔여 50만 원)",
                "A200 B200 C200 D50 E50 F0 G0 (잔여 300만 원)",
                "A300 B300 C200 D50 E50 F100 G0 (잔여 0만 원)",
                "조건을 만족하는 배분안은 없다",
            ),
            "answer_key": "4",
        },
        # -------------------------
        # SESSION 3 (11–15)
        # -------------------------
        {
            "id": "ncs_s3_q11",
            "item_number": 11,
            "session_id": 3,
            "domain": "문제해결능력 · 논리추론",
            "instruction": "다음 대화를 읽고 논리적 오류가 포함된 발언을 고르시오.",
            "stimulus_type": "text",
            "stimulus_text": "",
            "question": "논리적 오류가 포함된 발언을 고르시오.",
            "options": _options_dict(
                "“이번 프로젝트가 실패했으니, 앞으로도 우리는 항상 실패할 것이다.”",
                "“자료가 부족하니 추가 조사가 필요하다.”",
                "“한 번의 결과로 전체를 판단할 수 없다.”",
                "“원인을 분석하면 개선할 수 있다.”",
                "“실패는 다음 전략에 도움이 된다.”",
            ),
            "answer_key": "1",
        },
        {
            "id": "ncs_s3_q12",
            "item_number": 12,
            "session_id": 3,
            "domain": "문제해결능력 · 논리추론",
            "instruction": "다음은 최근 5년간 매출 변화이다.",
            "stimulus_type": "chart",
            "chart_spec": {
                "data": [
                    {"연도": "2021", "매출(억원)": 120},
                    {"연도": "2022", "매출(억원)": 126},
                    {"연도": "2023", "매출(억원)": 131},
                    {"연도": "2024", "매출(억원)": 137},
                    {"연도": "2025", "매출(억원)": 142},
                ],
                "x": "연도",
                "y": "매출(억원)",
                "title": "최근 5년간 매출 변화",
            },
            "question": "현재 추세가 유지될 경우, 다음 해에 가장 합리적으로 예측되는 결과는?",
            "options": _options_dict(
                "급격한 감소",
                "변화 없음",
                "소폭 증가",
                "급격한 증가",
                "예측 불가",
            ),
            "answer_key": "3",
        },
        {
            "id": "ncs_s3_q13",
            "item_number": 13,
            "session_id": 3,
            "domain": "문제해결능력 · 논리추론",
            "instruction": "다음 업무 중 처리 우선순위를 정하려 한다.",
            "stimulus_type": "text",
            "stimulus_text": "업무 A: 마감 오늘, 영향도 중간\n업무 B: 마감 내일, 영향도 높음\n업무 C: 마감 오늘, 영향도 낮음",
            "question": "가장 합리적인 처리 순서는?",
            "options": _options_dict(
                "C → A → B",
                "A → C → B",
                "A → B → C",
                "B → A → C",
                "B → C → A",
            ),
            "answer_key": "3",
        },
        {
            "id": "ncs_s3_q14",
            "item_number": 14,
            "session_id": 3,
            "domain": "문제해결능력 · 논리추론",
            "instruction": "다음은 사업 실패 요약 보고서이다.",
            "stimulus_type": "text",
            "stimulus_text": "“시장 조사 부족과 일정 관리 미흡으로 목표를 달성하지 못함.”",
            "question": "위 보고서에서 제시된 핵심 원인으로 가장 적절한 것은?",
            "options": _options_dict(
                "인력 부족",
                "예산 부족",
                "시장 분석 미흡",
                "외부 환경 변화",
                "기술 경쟁력 부족",
            ),
            "answer_key": "3",
        },
        {
            "id": "ncs_s3_q15",
            "item_number": 15,
            "session_id": 3,
            "domain": "문제해결능력 · 논리추론",
            "instruction": "다음 상황을 읽고 부작용을 최소화할 대안을 고르시오.",
            "stimulus_type": "text",
            "stimulus_text": "“신규 시스템 도입으로 일부 직원의 업무 혼란이 예상된다.”",
            "question": "가장 적절한 대응 방안은?",
            "options": _options_dict(
                "즉시 전면 도입",
                "도입 계획 철회",
                "사전 교육 후 단계적 도입",
                "관리자에게만 안내",
                "기존 시스템 유지",
            ),
            "answer_key": "3",
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
    st.caption(str(item.get("domain", "")))

    # Instruction + stimulus
    instruction = str(item.get("instruction", "") or "")
    if instruction:
        st.markdown(f"**{instruction}**")

    stimulus_type = str(item.get("stimulus_type", "text") or "text")
    stimulus_text = str(item.get("stimulus_text", "") or "")

    if stimulus_type in {"text", "table+chart"} and stimulus_text:
        st.markdown(stimulus_text)

    if stimulus_type in {"table", "table+chart"}:
        spec = dict(item.get("table_spec") or {})
        columns = list(spec.get("columns") or [])
        rows = list(spec.get("rows") or [])
        if columns and rows:
            df = pd.DataFrame(rows, columns=columns)
            st.dataframe(df, use_container_width=True, hide_index=True)

    if stimulus_type in {"chart", "table+chart"}:
        spec = dict(item.get("chart_spec") or {})
        data = list(spec.get("data") or [])
        x = spec.get("x")
        y = spec.get("y")
        title = spec.get("title") or ""
        if data and x and y:
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

    # Question + options
    question_text = str(item.get("question", "") or "")
    if question_text:
        st.markdown(f"**{question_text}**")

    options: Dict[str, str] = dict(item.get("options") or {})
    option_keys = list(options.keys())

    _allocation_token_re = re.compile(r"([A-G])\s*([0-9]+)")

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
        "정답을 선택하세요",
        options=option_keys,
        index=None,
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

