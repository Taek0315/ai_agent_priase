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
    items: List[Dict[str, Any]] = [
        # -------------------------
        # SESSION 1 (1–5) : 난이도 [하] - 직관적 일치 확인
        # -------------------------
        {
            "id": "ncs_s1_q1",
            "item_number": 1,
            "session_id": 1,
            "instruction": "고객으로부터 이중 결제 환불 요청 문의가 접수되었습니다.",
            "info_blocks": [
                {
                    "title": "업무 매뉴얼",
                    "bullets": [
                        "결제 오류: '결제 담당자'에게 티켓 전달",
                        "단순 변심: '물류 담당자'에게 티켓 전달",
                    ],
                },
            ],
            "question": "가장 적절한 초기 대응은 무엇인가?",
            "options": _options_dict(
                "물류 담당자에게 전화로 상황을 설명한다.",
                "결제 담당자에게 문의 내용을 티켓으로 전달한다.",
                "고객에게 직접 연락하여 결제 취소 방법을 안내한다.",
                "담당 부서가 아니므로 문의를 즉시 종료한다.",
                "직접 환불 처리 후 담당자에게 사후 보고한다.",
            ),
            "answer_key": "2",
        },
        {
            "id": "ncs_s1_q2",
            "item_number": 2,
            "session_id": 1,
            "instruction": "배송 문의를 처리하려고 합니다. 처리 우선순위 규칙은 다음과 같습니다.",
            "info_blocks": [
                {
                    "title": "우선순위",
                    "bullets": [
                        "1순위: 도착 예정일이 오늘인 문의",
                        "2순위: 도착 예정일이 내일인 문의",
                        "동일 조건 시 '주문일'이 빠른 순서로 처리",
                    ],
                },
            ],
            "question": "가장 먼저 처리해야 하는 문의는?",
            "options": _options_dict(
                "A (내일 도착 / 12월 01일 주문)",
                "B (오늘 도착 / 12월 10일 주문)",
                "C (모레 도착 / 12월 05일 주문)",
                "D (오늘 도착 / 12월 08일 주문)",
                "E (내일 도착 / 12월 03일 주문)",
            ),
            "answer_key": "4",
        },
        {
            "id": "ncs_s1_q3",
            "item_number": 3,
            "session_id": 1,
            "instruction": "단톡방에 영수증 사진을 공유해야 합니다. 사진에는 개인 연락처가 포함되어 있습니다.",
            "info_blocks": [
                {
                    "title": "보안 수칙",
                    "bullets": [
                        "개인정보(연락처 등)는 반드시 마스킹(*) 처리 후 공유한다.",
                        "편집이 불가능한 경우 공유하지 않는다.",
                    ],
                },
            ],
            "question": "가장 적절한 행동은?",
            "options": _options_dict(
                "시간이 없으므로 일단 원본 사진을 올린다.",
                "이미지 편집기로 연락처를 가린 뒤 사진을 올린다.",
                "연락처는 개인정보가 아니므로 그대로 올린다.",
                "나중에 삭제할 것을 약속하고 사진을 올린다.",
                "전화번호만 가리고 이름은 그대로 노출하여 올린다.",
            ),
            "answer_key": "2",
        },
        {
            "id": "ncs_s1_q4",
            "item_number": 4,
            "session_id": 1,
            "instruction": "휴대폰 수리점을 선택하려고 합니다. 다음 기준을 모두 만족해야 합니다.",
            "info_blocks": [
                {
                    "title": "선택 기준",
                    "bullets": [
                        "보증 기간: 6개월 이상",
                        "수리비: 7만 원 이하",
                    ],
                },
            ],
            "question": "가장 적절한 수리점은?",
            "options": _options_dict(
                "A: 보증 3개월 / 4만 원",
                "B: 보증 6개월 / 8만 원",
                "C: 보증 5개월 / 5만 원",
                "D: 보증 12개월 / 7만 원",
                "E: 보증 4개월 / 6만 원",
            ),
            "answer_key": "4",
        },
        {
            "id": "ncs_s1_q5",
            "item_number": 5,
            "session_id": 1,
            "instruction": "오늘의 업무 리스트입니다. 한 번에 하나만 처리할 수 있습니다.",
            "info_blocks": [
                {
                    "title": "업무 목록",
                    "bullets": [
                        "A: 보통 / 1시간 소요",
                        "B: 긴급 / 2시간 소요",
                        "C: 매우 긴급 / 1시간 소요",
                    ],
                },
            ],
            "question": "가장 효율적인 처리 순서는?",
            "options": _options_dict(
                "A → B → C",
                "B → C → A",
                "C → B → A",
                "C → A → B",
                "B → A → C",
            ),
            "answer_key": "3",
        },

        # -------------------------
        # SESSION 2 (6–10) : 난이도 [상] - 추론 및 예외 처리
        # -------------------------
        {
            "id": "ncs_s2_q6",
            "item_number": 6,
            "session_id": 2,
            "instruction": "3명의 팀원이 회의 시간을 정하고 있습니다. 모두가 가능한 시간을 찾으세요.",
            "info_blocks": [
                {
                    "title": "개인별 가능 시간",
                    "bullets": [
                        "A: 월요일 전체 가능, 화요일 오후 가능",
                        "B: 월요일 오전 불가, 화요일 전체 가능",
                        "C: 월요일 오후 불가, 화요일 오후 불가",
                    ],
                },
            ],
            "question": "모두가 모일 수 있는 시간은?",
            "options": _options_dict(
                "월요일 오전",
                "월요일 오후",
                "화요일 오전",
                "화요일 오후",
                "가능한 시간이 없다.",
            ),
            "answer_key": "5",
        },
        {
            "id": "ncs_s2_q7",
            "item_number": 7,
            "session_id": 2,
            "instruction": "구매 요청 결재 건을 검토 중입니다. 예산은 30만 원입니다.",
            "info_blocks": [
                {
                    "title": "결재 원칙",
                    "bullets": [
                        "원칙: 예산(30만 원) 초과 시 반려",
                        "예외: '안전 보강' 목적의 경우 예산과 관계없이 승인",
                        "필수: 모든 요청은 '부서장 서명'이 있어야 함",
                    ],
                },
            ],
            "question": "다음 중 '승인' 대상인 것은?",
            "options": _options_dict(
                "사무용품 구매(20만 원 / 서명 없음)",
                "노후 설비 교체(안전 목적 / 100만 원 / 서명 있음)",
                "워크숍 간식(40만 원 / 서명 있음)",
                "안전 가드 설치(안전 목적 / 50만 원 / 서명 없음)",
                "정기 간행물 구독(10만 원 / 서명 없음)",
            ),
            "answer_key": "2",
        },
        {
            "id": "ncs_s2_q8",
            "item_number": 8,
            "session_id": 2,
            "instruction": "서버 점검 공지문을 작성해야 합니다. 다음 조건을 모두 만족해야 합니다.",
            "info_blocks": [
                {
                    "title": "공지문 조건",
                    "bullets": [
                        "1. 점검 시간(시작~종료) 명시",
                        "2. 점검 중 '이용 불가 서비스' 명시",
                        "3. 담당자 연락처 포함",
                    ],
                },
            ],
            "question": "가장 적절한 공지문은?",
            "options": _options_dict(
                "14시부터 서버 점검이 있습니다. 불편을 드려 죄송합니다.",
                "14:00~15:00 서버 점검으로 로그인이 불가능합니다. 문의: 02-123-4567",
                "점검 시간 동안 모든 서비스가 중단됩니다. 담당자에게 연락 주세요.",
                "15:00까지 점검을 마칠 예정입니다. 게시판 이용이 안 됩니다.",
                "서버 최적화를 위해 1시간 동안 점검합니다. 문의는 메일로 주세요.",
            ),
            "answer_key": "2",
        },
        {
            "id": "ncs_s2_q9",
            "item_number": 9,
            "session_id": 2,
            "instruction": "기밀 자료 열람 권한을 승인하려고 합니다.",
            "info_blocks": [
                {
                    "title": "승인 기준",
                    "bullets": [
                        "대상: 근속 3년 이상 직원",
                        "목적: 프로젝트 수행 목적 한정",
                        "예외: 신입사원이라도 '팀장 동행' 시 열람 가능",
                    ],
                },
            ],
            "question": "열람 승인이 가능한 경우는?",
            "options": _options_dict(
                "근속 5년 차 직원이 개인 학습을 위해 열람 요청",
                "근속 1년 차 직원이 프로젝트 수행을 위해 단독 요청",
                "근속 4년 차 직원이 프로젝트 수행을 위해 열람 요청",
                "신입사원이 팀장 동행 없이 프로젝트를 위해 열람 요청",
                "근속 10년 차 직원이 단순 호기심으로 열람 요청",
            ),
            "answer_key": "3",
        },
        {
            "id": "ncs_s2_q10",
            "item_number": 10,
            "session_id": 2,
            "instruction": "초과근무 수당을 계산해야 합니다. (기본 시급 1만 원)",
            "info_blocks": [
                {
                    "title": "수당 규정",
                    "bullets": [
                        "기본 근무: 주 40시간",
                        "초과 근무: 주 40시간 초과분은 시급의 1.5배 지급",
                        "최대 근무 가능 시간: 주 52시간(초과분 12시간까지만 인정)",
                    ],
                },
            ],
            "question": "이번 주 55시간을 근무한 직원이 받을 '총 급여'는?",
            "options": _options_dict(
                "55만 원 (55시간 x 1만 원)",
                "62.5만 원 (40만 원 + 15시간 x 1.5만 원)",
                "58만 원 (40만 원 + 12시간 x 1.5만 원)",
                "52만 원 (최대 근무 시간인 52만 원만 지급)",
                "60만 원 (전부 기본 시급으로 계산)",
            ),
            "answer_key": "3",
        },

        # -------------------------
        # SESSION 3 (11–15) : 난이도 [중] - 다중 조건 매칭
        # -------------------------
        {
            "id": "ncs_s3_q11",
            "item_number": 11,
            "session_id": 3,
            "instruction": "의심스러운 로그인 알림을 받았습니다. 보안 매뉴얼에 따라 대응해야 합니다.",
            "info_blocks": [
                {
                    "title": "보안 매뉴얼 필수 단계",
                    "bullets": [
                        "1단계: 비밀번호 변경",
                        "2단계: 모든 기기 로그아웃",
                        "3단계: 2단계 인증 설정",
                    ],
                },
            ],
            "question": "매뉴얼을 모두 준수한 대응은?",
            "options": _options_dict(
                "비밀번호를 변경하고 고객센터에 전화한다.",
                "비밀번호 변경 후 모든 기기에서 로그아웃하고, 2단계 인증을 활성화한다.",
                "2단계 인증만 설정하고 로그인을 유지한다.",
                "비밀번호를 변경하고 범인을 잡기 위해 로그인을 유지한다.",
                "모든 기기에서 로그아웃한 뒤 비밀번호는 나중에 바꾼다.",
            ),
            "answer_key": "2",
        },
        {
            "id": "ncs_s3_q12",
            "item_number": 12,
            "session_id": 3,
            "instruction": "문의 알림 5개가 쌓여 있습니다. 다음 기준에 따라 4번째로 처리할 업무를 고르세요.",
            "info_blocks": [
                {
                    "title": "처리 우선순위",
                    "bullets": [
                        "1순위: 보안/결제 사고 (긴급)",
                        "2순위: 일반 문의",
                        "동일 순위 내에서는 '접수 시각'이 빠른 순서",
                    ],
                },
            ],
            "question": "4번째(4순위)로 처리하게 될 업무는?",
            "options": _options_dict(
                "A (보안 사고 / 09:00)",
                "B (결제 오류 / 10:00)",
                "C (일반 문의 / 08:30)",
                "D (일반 문의 / 11:00)",
                "E (일반 문의 / 13:00)",
            ),
            "answer_key": "4",
        },
        {
            "id": "ncs_s3_q13",
            "item_number": 13,
            "session_id": 3,
            "instruction": "배달 경로를 최단 거리로 짜려고 합니다.",
            "info_blocks": [
                {
                    "title": "위치 정보",
                    "bullets": [
                        "현위치에서 A: 1km / A에서 B: 2km",
                        "현위치에서 B: 2km / B에서 A: 2km",
                    ],
                },
            ],
            "question": "모든 지점(A, B)을 방문하고 현위치로 돌아올 때 가장 짧은 경로는?",
            "options": _options_dict(
                "현위치 → A → B → 현위치",
                "현위치 → B → A → 현위치",
                "두 경로의 거리는 5km로 같다.",
                "두 경로의 거리는 4km로 같다.",
                "방문 순서와 상관없이 거리는 항상 6km이다.",
            ),
            "answer_key": "3",
        },
        {
            "id": "ncs_s3_q14",
            "item_number": 14,
            "session_id": 3,
            "instruction": "지각 상황에서 상사에게 보낼 메시지를 작성해야 합니다.",
            "info_blocks": [
                {
                    "title": "메시지 작성 원칙",
                    "bullets": [
                        "1. 구체적인 도착 예정 시간 포함",
                        "2. 지각 사유 명시",
                        "3. 감정적 호소(예: 너무 슬퍼요 등) 금지",
                    ],
                },
            ],
            "question": "모든 원칙을 준수한 메시지는?",
            "options": _options_dict(
                "차가 너무 막혀서 늦을 것 같습니다. 죄송합니다.",
                "지하철 연착으로 15분 정도 늦을 것 같습니다. 정말 죄송합니다.",
                "사고가 나서 늦는데, 마음이 너무 무겁고 눈물이 나네요. 곧 갑니다.",
                "오늘 조금 늦을 것 같습니다. 10분 뒤에 뵙겠습니다.",
                "늦어서 죄송합니다. 최대한 빨리 가겠습니다!",
            ),
            "answer_key": "2",
        },
        {
            "id": "ncs_s3_q15",
            "item_number": 15,
            "session_id": 3,
            "instruction": "워크숍 숙소를 정해야 합니다. 예산은 100만 원입니다.",
            "info_blocks": [
                {
                    "title": "선택 기준",
                    "bullets": [
                        "1. 예산 100만 원 이하",
                        "2. 회의실 보유 필수",
                        "3. 위 조건 만족 시 가격이 가장 저렴한 곳",
                    ],
                },
            ],
            "question": "가장 적절한 숙소는?",
            "options": _options_dict(
                "A: 100만 원 / 회의실 있음",
                "B: 80만 원 / 회의실 없음",
                "C: 110만 원 / 회의실 있음",
                "D: 90만 원 / 회의실 있음",
                "E: 85만 원 / 회의실 없음",
            ),
            "answer_key": "4",
        },
    ]

    # 세션 ID 할당 및 검증 로직은 동일
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

