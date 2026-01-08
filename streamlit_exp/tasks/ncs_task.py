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
        # SESSION 1 (1–5) : 조건 1~2개
        # -------------------------
        {
            "id": "ncs_s1_q1",
            "item_number": 1,
            "session_id": 1,
            "domain": "session1",
            "instruction": "온라인 쇼핑몰을 이용했는데 결제가 두 번 된 것 같다는 문의가 왔다. 고객은 환불을 요청했다.",
            "stimulus_type": "text",
            "stimulus_text": "",
            "info_blocks": [
                {
                    "title": "처리 기준",
                    "bullets": [
                        "결제 오류 관련 처리는 ‘결제 담당’에게 전달한다.",
                        "요청 전달은 반드시 ‘문의 티켓’으로 남긴다.",
                        "환불은 고객 문의 중 높은 우선 순위를 가진다."
                    ],
                },
            ],
            "table_spec": {},
            "question": "가장 먼저 해야 할 행동으로 적절한 것은 무엇인가?",
            "options": _options_dict(
                "고객에게 ‘확인 중’이라고 먼저 답장을 보낸다.",
                "결제 담당에게 문의 내용을 ‘문의 티켓’으로 전달한다.",
                "환불이 급하므로 운영자가 먼저 환불 처리한다.",
                "결제 오류는 담당 부서 일이므로 문의를 종료한다.",
                "전화로 결제 담당에게 전달하고 티켓은 나중에 남긴다.",
            ),
            "answer_key": "2",
        },
        {
            "id": "ncs_s1_q2",
            "item_number": 2,
            "session_id": 1,
            "domain": "session1",
            "instruction": "택배 관련 문의를 처리 중이다. 오늘 처리할 ‘배송 관련 문의’가 여러 건 쌓였다.",
            "stimulus_type": "text",
            "stimulus_text": "",
            "info_blocks": [
                {
                    "title": "처리 기준",
                    "bullets": [
                        "‘도착 예정이 빠른’ 문의를 먼저 처리한다.",
                        "도착 예정이 같다면 ‘주문일이 더 빠른’ 문의를 먼저 처리한다.",
                    ],
                },
            ],
            "table_spec": {},
            "question": "다음 중 가장 먼저 처리해야 하는 문의는 무엇인가?",
            "options": _options_dict(
                "문의 A(내일 도착/주문 12월 10일)",
                "문의 B(오늘 도착/주문 12월 21일)",
                "문의 C(모레 도착/주문 12월 01일)",
                "문의 D(오늘 도착/주문 12월 19일)",
                "문의 E(내일 도착/주문 12월 03일)",
            ),
            "answer_key": "4",
        },
        {
            "id": "ncs_s1_q3",
            "item_number": 3,
            "session_id": 1,
            "domain": "session1",
            "instruction": "동아리 회계 정산을 위해 단체 채팅방에 영수증 사진을 공유하려고 한다. \n 사진에 연락처를 포함한 개인정보가 함께 찍혀 있다. \n 회계 정산 마감일이 지나서 빠르게 전달해야한다.",
            "stimulus_type": "text",
            "stimulus_text": "",
            "info_blocks": [
                {
                    "title": "공유 기준",
                    "bullets": [
                        "연락처 등 개인정보가 보이면 공유 전 가려서(마스킹) 올린다.",
                        "마스킹은 마스킹 규칙에 따라 '*' 표 처리를 진행한다."                        
                    ],
                },
            ],
            "table_spec": {},
            "question": "가장 적절한 행동은 무엇인가?",
            "options": _options_dict(
                "일정이 급하기 때문에 공유 후 양해를 구한다.",
                "연락처가 보이는 부분을 이미지 편집 기능을 통해 가린 뒤 사진을 올린다.",
                "단체 채팅방 대신 메일을 통해 공유한다.",
                "연락처가 보이니 정산 공유를 하지 않는다.",
                "대체가 가능한 자료를 우선 전달하고 추후 보완하겠다고 한다.",
            ),
            "answer_key": "5",
        },
        {
            "id": "ncs_s1_q4",
            "item_number": 4,
            "session_id": 1,
            "domain": "session1",
            "instruction": "휴대폰 수리를 맡기려고 한다. 비슷한 조건의 수리점 5곳 중 한 곳을 골라야 한다.",
            "stimulus_type": "text",
            "stimulus_text": "",
            "info_blocks": [
                {
                    "title": "선택 기준",
                    "bullets": [
                        "수리 보증 기간이 6개월 이상",
                        "보증 기간이 같다면 가격이 가장 낮은 곳.",
                    ],
                },
            ],
            "table_spec": {},
            "question": "기준에 따라 가장 적절한 선택은 무엇인가?",
            "options": _options_dict(
                "가 수리점: 보증 3개월/4만 원",
                "나 수리점: 보증 6개월/7만 원",
                "다 수리점: 보증 12개월/8만 원",
                "라 수리점: 보증 6개월/6만 원",
                "마 수리점: 보증 12개월/7만 원",
            ),
            "answer_key": "4",
        },
        {
            "id": "ncs_s1_q5",
            "item_number": 5,
            "session_id": 1,
            "domain": "session1",
            "instruction": "오늘 해야 할 집안일을 정리하고 있다.",
            "stimulus_type": "text",
            "stimulus_text": "",
            "info_blocks": [
                {
                    "title": "작업 정보",
                    "bullets": [
                        "A: 보통 / 단독 처리",
                        "B: 급함 / 동시 처리 가능",
                        "C: 급함 / 단독 처리",
                        "D: 급하지 않음 / 동시 처리 가능",
                    ],
                },
            ],
            "table_spec": {},
            "question": "가장 효율적인 작업 순서는 무엇인가?",
            "options": _options_dict(
                "A → B → C → D",
                "B → A → C → D",
                "A → B & D → C",
                "B & D → A → C",
                "C → B & D → A",
            ),
            "answer_key": "5",
        },

        # -------------------------
        # SESSION 2 (6–10) : 조건 3개
        # -------------------------
        {
            "id": "ncs_s2_q6",
            "item_number": 6,
            "session_id": 2,
            "domain": "session2",
            "instruction": "친구 3명과 팀플 회의 약속을 잡고 있다. 모두가 가능한 시간을 찾아야 한다.",
            "stimulus_type": "text",
            "stimulus_text": "",
            "info_blocks": [
                {
                    "title": "약속 기준",
                    "bullets": [
                        "A는 월 저녁, 화 점심, 목 저녁 가능, 수 온라인 가능",
                        "B는 화 점심, 수 저녁, 목 점심 가능, 월 온라인 가능",
                        "C는 월 저녁, 화 점심, 수 저녁 가능, 화 온라인 가능",
                        "A와 B는 만나지 않아야 하며, B와 C는 같이 만나야 한다."
                    ],
                },
            ],
            "table_spec": {},
            "question": "조건에 따라 가장 알맞은 약속 시간은 언제인가?",
            "options": _options_dict(
                "월요일 저녁",
                "화요일 점심",
                "수요일 저녁",
                "목요일 점심",
                "수요일 점심",
            ),
            "answer_key": "3",
        },
        {
            "id": "ncs_s2_q7",
            "item_number": 7,
            "session_id": 2,
            "domain": "session2",
            "instruction": "회사에서 소모품과 비품을 구매 하고자 하는 구매 요청을 결재해야 한다. \n 남은 예산이 한정되어 있기 때문에 전부 결재해줄 수 없다.",
            "stimulus_type": "text",
            "stimulus_text": "",
            "info_blocks": [
                {
                    "title": "결재 기준",
                    "bullets": [
                        "예산 범위: 30만 원",
                        "각 팀별 부서장의 확인 필수",
                        "단, 안전 문제 해결 목적이면 금액 기준 만을 무시하고 승인",
                    ],
                },
            ],
            "table_spec": {},
            "question": "기준에 따라 승인할 요청은 무엇인가?",
            "options": _options_dict(
                "요청 A(안전 O/50만 원/확인 O)를 승인한다.",
                "요청 B(안전 X/20만 원/확인 O)를 승인한다.",
                "요청 C(안전 X/20만 원/확인 X)를 승인한다.",
                "요청 D(안전 O/50만 원/확인 X)를 승인한다.",
                "요청 E(안전 X/40만 원/확인 O)를 승인한다.",
            ),
            "answer_key": "1",
        },
        {
            "id": "ncs_s2_q8",
            "item_number": 8,
            "session_id": 2,
            "domain": "session2",
            "instruction": "공동 구매 채팅방에 ‘배송 지연’ 공지를 올리려 한다. \n 배송 지연 관련 문제는 현재 해결된 상태다.",
            "stimulus_type": "text",
            "stimulus_text": "",
            "info_blocks": [
                {
                    "title": "공지 작성 기준",
                    "bullets": [
                        "원인을 단정하지 않는다.",
                        "문의처(연락 수단)를 포함한다.",
                        "정상화된 경우 ‘정상화’에 대한 정확한 표현 전달 필요.",
                    ],
                },
            ],
            "table_spec": {},
            "question": "기준에 따라 가장 적절한 공지는 무엇인가?",
            "options": _options_dict(
                "서버 오류로 지연된 배송 문제는 현재 정상화되었습니다. 문의: help@company.com",
                "배송 지연 관련 문제의 원인은 서버 오류로 확인되었습니다. 문의: help@company.com",
                "배송 지연로 공동 구매 배송에 문제가 있습니다. 문의: help@company.com",
                "배송 지연 문제는 오늘 15:00에 정상화 되었습니다. 문의: help@company.com",
                "배송 지연 문제 해결되었습니다. 원인은 미정입니다.",
            ),
            "answer_key": "4",
        },
        {
            "id": "ncs_s2_q9",
            "item_number": 9,
            "session_id": 2,
            "domain": "session2",
            "instruction": "PC 사용 기록(로그) 조회 요청 1건을 처리해야 한다.",
            "stimulus_type": "text",
            "stimulus_text": "",
            "info_blocks": [
                {
                    "title": "조회 승인 기준",
                    "bullets": [
                        "필수: 업무 목적이 명확해야 한다(O).",
                        "필수: 조회 기간은 최근 7일 이내",
                        "예외: 사고 조사 목적이면 최대 30일까지 허용",
                    ],
                },
            ],
            "table_spec": {},
            "question": "기준에 따라 가장 적절한 행동은 무엇인가?",
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
            "instruction": "알바 근무표에서 초과근무 신청 1건을 처리해야 한다.",
            "stimulus_type": "text",
            "stimulus_text": "",
            "info_blocks": [
                {
                    "title": "초과근무 처리 기준",
                    "bullets": [
                        "필수: 사전 신청(O)",
                        "필수: 관리자 승인(O)",
                        "예외: 긴급한 고객 대응이면 사전 신청이 없어도 처리 가능",
                    ],
                },
            ],
            "table_spec": {},
            "question": "기준에 따라 가장 적절한 행동은 무엇인가?",
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
        # SESSION 3 (11–15) : 조건 2개
        # -------------------------
        {
            "id": "ncs_s3_q11",
            "item_number": 11,
            "session_id": 3,
            "domain": "session3",
            "instruction": "내 계정에서 평소와 다른 ‘의심스러운 로그인’ 알림을 받았다.",
            "stimulus_type": "text",
            "stimulus_text": "",
            "info_blocks": [
                {
                    "title": "대응 기준",
                    "bullets": [
                        "추가 피해를 막는 조치를 먼저 한다.",
                        "확인 가능한 기록(알림/시간 등)을 남긴다.",
                    ],
                },
            ],
            "table_spec": {},
            "question": "가장 적절한 행동은 무엇인가?",
            "options": _options_dict(
                "비밀번호를 변경하고 알림 화면을 저장한 뒤 고객센터/보안 문의에 전달한다.",
                "알림이 귀찮으니 알림을 끄고 아무 조치도 하지 않는다.",
                "기록은 남기지 않고 비밀번호만 변경한다.",
                "기록만 남기고 비밀번호 변경은 하지 않는다.",
                "주변 사람에게 먼저 공유하고 대응은 나중에 한다.",
            ),
            "answer_key": "1",
        },
        {
            "id": "ncs_s3_q12",
            "item_number": 12,
            "session_id": 3,
            "domain": "session3",
            "instruction": "휴대폰에 알림이 5개 쌓였다. 지금은 1개만 먼저 확인할 수 있다.",
            "stimulus_type": "text",
            "stimulus_text": "",
            "info_blocks": [
                {
                    "title": "확인 기준",
                    "bullets": [
                        "개인정보/보안 위험 알림을 먼저 확인한다.",
                        "같은 유형이면 더 이른 시각의 알림을 먼저 확인한다.",
                    ],
                },
            ],
            "table_spec": {},
            "question": "가장 먼저 확인해야 할 알림은 무엇인가?",
            "options": _options_dict(
                "A(성능/02:13)",
                "B(개인정보/02:17)",
                "C(결제/02:15)",
                "D(로그인/02:12)",
                "E(개인정보/02:19)",
            ),
            "answer_key": "2",
        },
        {
            "id": "ncs_s3_q13",
            "item_number": 13,
            "session_id": 3,
            "domain": "session3",
            "instruction": "오늘 처리할 집안일 1가지를 먼저 고르려 한다.",
            "stimulus_type": "text",
            "stimulus_text": "",
            "info_blocks": [
                {
                    "title": "선택 기준",
                    "bullets": [
                        "되돌리기(수정) 쉬운 일을 우선한다.",
                        "같으면 생활 영향이 큰 일을 우선한다.",
                    ],
                },
            ],
            "table_spec": {},
            "question": "기준에 따라 가장 적절한 선택은 무엇인가?",
            "options": _options_dict(
                "일 A(되돌림 쉬움/영향 큼)",
                "일 B(되돌림 어려움/영향 큼)",
                "일 C(되돌림 쉬움/영향 작음)",
                "일 D(되돌림 어려움/영향 작음)",
                "일 E(되돌림 쉬움/영향 중간)",
            ),
            "answer_key": "1",
        },
        {
            "id": "ncs_s3_q14",
            "item_number": 14,
            "session_id": 3,
            "domain": "session3",
            "instruction": "약속 시간에 늦을 것 같아 상대에게 안내 메시지 1개를 보내야 한다.",
            "stimulus_type": "text",
            "stimulus_text": "",
            "info_blocks": [
                {
                    "title": "메시지 기준",
                    "bullets": [
                        "확정된 도착 시간을 단정해서 쓰지 않는다.",
                        "다음 안내 시점을 포함한다.",
                    ],
                },
            ],
            "table_spec": {},
            "question": "기준에 따라 가장 적절한 메시지는 무엇인가?",
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
            "instruction": "동아리에서 새 공지 방식(새 시스템)을 도입하려 한다. 실행 계획 1개를 고르려 한다.",
            "stimulus_type": "text",
            "stimulus_text": "",
            "info_blocks": [
                {
                    "title": "계획 기준",
                    "bullets": [
                        "사용 가이드(간단 안내)를 배포한다.",
                        "문의/지원 창구(담당자)를 지정한다.",
                    ],
                },
            ],
            "table_spec": {},
            "question": "기준에 따라 가장 적절한 계획은 무엇인가?",
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

