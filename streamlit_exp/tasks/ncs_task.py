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
            "domain": "의사소통능력 · 기초 자료해석",
            "instruction": "\n".join(["상황: 당신은 고객센터 당직이다.", "지금 ‘결제 오류’ 문의가 들어왔다."]),
            "stimulus_type": "text",
            "stimulus_text": "",
            "info_blocks": [
                {
                    "title": "조건",
                    "bullets": ["‘결제 오류’는 즉시 결제 담당팀으로 에스컬레이션한다."],
                },
            ],
            "table_spec": {},
            "question": "조건에 따라 가장 적절한 행동은 무엇인가?",
            "options": _options_dict(
                "환불 안내를 먼저 보낸다.",
                "결제 담당팀에 즉시 에스컬레이션한다.",
                "내일 다시 확인한다.",
                "문의 내용을 삭제한다.",
                "배송 담당팀에 전달한다.",
            ),
            "answer_key": "2",
        },
        {
            "id": "ncs_s1_q2",
            "item_number": 2,
            "session_id": 1,
            "domain": "의사소통능력 · 기초 자료해석",
            "instruction": "\n".join(["상황: 출고 지연을 막기 위해 주문 확인 전화를 해야 한다.", "지금은 1건만 먼저 전화할 수 있다."]),
            "stimulus_type": "text",
            "stimulus_text": "",
            "info_blocks": [
                {
                    "title": "조건",
                    "bullets": ["‘오늘 출고 예정’ 주문을 최우선으로 확인한다."],
                },
            ],
            "table_spec": {},
            "question": "조건에 따라 가장 적절한 행동은 무엇인가?",
            "options": _options_dict(
                "다음 주 출고 주문부터 확인한다.",
                "수량이 가장 적은 주문부터 확인한다.",
                "오늘 출고 예정 주문을 먼저 전화로 확인한다.",
                "모든 주문을 메일로만 확인한다.",
                "임의로 한 건을 골라 출고부터 진행한다.",
            ),
            "answer_key": "3",
        },
        {
            "id": "ncs_s1_q3",
            "item_number": 3,
            "session_id": 1,
            "domain": "의사소통능력 · 기초 자료해석",
            "instruction": "\n".join(["상황: 협력사에 고객 연락처 파일을 보내야 한다.", "오늘 안에 전달해야 한다."]),
            "stimulus_type": "text",
            "stimulus_text": "",
            "info_blocks": [
                {
                    "title": "조건",
                    "bullets": ["개인정보 파일은 ‘보안 전송 링크’로만 보낸다."],
                },
            ],
            "table_spec": {},
            "question": "조건에 따라 가장 적절한 행동은 무엇인가?",
            "options": _options_dict(
                "보안 전송 링크로 보내고 비밀번호는 별도로 전달한다.",
                "일반 이메일에 첨부해 보낸다.",
                "개인 메신저로 파일을 보낸다.",
                "USB에 담아 전달한다.",
                "오픈 채팅방에 링크를 공유한다.",
            ),
            "answer_key": "1",
        },
        {
            "id": "ncs_s1_q4",
            "item_number": 4,
            "session_id": 1,
            "domain": "의사소통능력 · 기초 자료해석",
            "instruction": "\n".join(["상황: 장비 유지보수 업체 1곳을 지금 선정해야 한다."]),
            "stimulus_type": "text",
            "stimulus_text": "",
            "info_blocks": [
                {
                    "title": "조건",
                    "bullets": ["A/S 18개월 이상 중 ‘견적’이 가장 낮은 업체를 고른다."],
                },
            ],
            "table_spec": {},
            "question": "조건에 따라 가장 적절한 행동은 무엇인가?",
            "options": _options_dict(
                "가 업체(24개월/120만원)로 계약한다.",
                "나 업체(18개월/105만원)로 계약한다.",
                "다 업체(12개월/90만원)로 계약한다.",
                "라 업체(18개월/115만원)로 계약한다.",
                "마 업체(15개월/98만원)로 계약한다.",
            ),
            "answer_key": "2",
        },
        {
            "id": "ncs_s1_q5",
            "item_number": 5,
            "session_id": 1,
            "domain": "의사소통능력 · 기초 자료해석",
            "instruction": "\n".join(["상황: 오늘 근무기록 제출 전, 일부 기록에 누락이 있다."]),
            "stimulus_type": "text",
            "stimulus_text": "",
            "info_blocks": [
                {
                    "title": "조건",
                    "bullets": ["퇴근 기록이 ‘누락’된 날을 먼저 보완한다."],
                },
            ],
            "table_spec": {},
            "question": "조건에 따라 가장 적절한 행동은 무엇인가?",
            "options": _options_dict(
                "월(정상)부터 확인 요청한다.",
                "화(퇴근기록 누락)부터 보완 요청한다.",
                "수(정상)부터 확인 요청한다.",
                "목(정상)부터 확인 요청한다.",
                "금(정상)부터 확인 요청한다.",
            ),
            "answer_key": "2",
        },
        # -------------------------
        # SESSION 2 (6–10)
        # -------------------------
        {
            "id": "ncs_s2_q6",
            "item_number": 6,
            "session_id": 2,
            "domain": "자원관리능력 · 상황판단",
            "instruction": "\n".join(
                [
                    "상황: 4인 회의를 오늘 확정해야 한다.",
                    "참석 가능: A(오전만), C·D(오후만), B·E(오전·오후).",
                ]
            ),
            "stimulus_type": "text",
            "stimulus_text": "",
            "info_blocks": [
                {
                    "title": "조건",
                    "bullets": [
                        "B와 D는 반드시 참석한다.",
                        "회의실 A는 오전만, 회의실 B는 오후만 사용한다.",
                    ],
                },
            ],
            "table_spec": {},
            "question": "조건에 따라 가장 적절한 행동은 무엇인가?",
            "options": _options_dict(
                "오전 / 회의실 A / A,B,D,E 참석",
                "오전 / 회의실 A / A,B,C,E 참석",
                "오후 / 회의실 B / B,C,D,E 참석",
                "오후 / 회의실 B / A,B,D,E 참석",
                "오후 / 회의실 A / B,C,D,E 참석",
            ),
            "answer_key": "3",
        },
        {
            "id": "ncs_s2_q7",
            "item_number": 7,
            "session_id": 2,
            "domain": "자원관리능력 · 상황판단",
            "instruction": "\n".join(["상황: 행사 배너 200장을 외주로 맡기려 한다.", "업체 1곳을 지금 선택한다."]),
            "stimulus_type": "text",
            "stimulus_text": "",
            "info_blocks": [
                {
                    "title": "조건",
                    "bullets": [
                        "인증(O)이고 납기 3일 이내인 업체만 선택한다.",
                        "그중 단가가 가장 낮은 업체를 선택한다.",
                    ],
                },
            ],
            "table_spec": {},
            "question": "조건에 따라 가장 적절한 행동은 무엇인가?",
            "options": _options_dict(
                "가사(단가 6.2/납기 3일/인증 O)를 선택한다.",
                "나사(단가 5.8/납기 4일/인증 O)를 선택한다.",
                "다사(단가 6.0/납기 2일/인증 X)를 선택한다.",
                "라사(단가 6.5/납기 2일/인증 O)를 선택한다.",
                "마사(단가 5.9/납기 3일/인증 O)를 선택한다.",
            ),
            "answer_key": "5",
        },
        {
            "id": "ncs_s2_q8",
            "item_number": 8,
            "session_id": 2,
            "domain": "자원관리능력 · 상황판단",
            "instruction": "\n".join(["상황: 오늘 고객에게 ‘임시 안내’ 공지를 발송해야 한다."]),
            "stimulus_type": "text",
            "stimulus_text": "",
            "info_blocks": [
                {
                    "title": "조건",
                    "bullets": [
                        "서비스 중단을 단정하지 않는다.",
                        "확정 시간은 쓰지 않되, 문의처는 반드시 포함한다.",
                    ],
                },
            ],
            "table_spec": {},
            "question": "조건에 따라 가장 적절한 행동은 무엇인가?",
            "options": _options_dict(
                "“오늘 점검으로 서비스가 중단됩니다. 문의: help@company.com”",
                "“오늘 15:00~16:00 점검 예정입니다. 문의: help@company.com”",
                "“시스템 상태를 확인 중입니다. 문의: help@company.com”",
                "“시스템 상태를 확인 중입니다.”",
                "“오늘 15:00~16:00 점검으로 서비스가 중단됩니다. 문의: help@company.com”",
            ),
            "answer_key": "3",
        },
        {
            "id": "ncs_s2_q9",
            "item_number": 9,
            "session_id": 2,
            "domain": "자원관리능력 · 상황판단",
            "instruction": "\n".join(["상황: 사전 승인 없이 출장비가 발생했다.", "예외 승인 1건만 처리한다."]),
            "stimulus_type": "text",
            "stimulus_text": "",
            "info_blocks": [
                {
                    "title": "조건",
                    "bullets": [
                        "예외 승인: 긴급(O) + 사전 승인 불가(X) + 24시간 내 보고(O).",
                        "세 조건을 모두 만족하는 사례만 승인한다.",
                    ],
                },
            ],
            "table_spec": {},
            "question": "조건에 따라 가장 적절한 행동은 무엇인가?",
            "options": _options_dict(
                "사례 A(긴급 O / 사전승인 O / 24h보고 O)를 승인한다.",
                "사례 B(긴급 X / 사전승인 X / 24h보고 O)를 승인한다.",
                "사례 C(긴급 O / 사전승인 X / 24h보고 O)를 승인한다.",
                "사례 D(긴급 O / 사전승인 X / 24h보고 X)를 승인한다.",
                "사례 E(긴급 X / 사전승인 O / 24h보고 X)를 승인한다.",
            ),
            "answer_key": "3",
        },
        {
            "id": "ncs_s2_q10",
            "item_number": 10,
            "session_id": 2,
            "domain": "자원관리능력 · 상황판단",
            "instruction": "\n".join(["상황: 이번 주 잔여 예산은 500만 원이다.", "지출 요청 1건만 즉시 승인한다."]),
            "stimulus_type": "text",
            "stimulus_text": "",
            "info_blocks": [
                {
                    "title": "조건",
                    "bullets": [
                        "필수(O)이고 증빙(O)인 요청만 승인한다.",
                        "예산 500만 원을 넘는 요청은 승인하지 않는다.",
                    ],
                },
            ],
            "table_spec": {},
            "question": "조건에 따라 가장 적절한 행동은 무엇인가?",
            "options": _options_dict(
                "요청 A(필수 O / 480만 / 증빙 X)를 승인한다.",
                "요청 B(필수 O / 300만 / 증빙 O)를 승인한다.",
                "요청 C(필수 X / 120만 / 증빙 O)를 승인한다.",
                "요청 D(필수 O / 520만 / 증빙 O)를 승인한다.",
                "요청 E(필수 X / 90만 / 증빙 X)를 승인한다.",
            ),
            "answer_key": "2",
        },
        # -------------------------
        # SESSION 3 (11–15)
        # -------------------------
        {
            "id": "ncs_s3_q11",
            "item_number": 11,
            "session_id": 3,
            "domain": "문제해결능력 · 논리추론",
            "instruction": "\n".join(["상황: 비정상 다운로드가 감지되어 정보 유출이 의심된다."]),
            "stimulus_type": "text",
            "stimulus_text": "",
            "info_blocks": [
                {
                    "title": "조건",
                    "bullets": [
                        "우선: 확산 차단 + 증거(로그) 보존을 한다.",
                        "보안팀에 즉시 보고하고, 외부 공유는 하지 않는다.",
                    ],
                },
            ],
            "table_spec": {},
            "question": "조건에 따라 가장 적절한 행동은 무엇인가?",
            "options": _options_dict(
                "시스템을 최소 범위로 격리하고 로그를 보존한 뒤 보안팀에 즉시 보고한다.",
                "원인 파악을 위해 관련 로그를 삭제하고 재시작한다.",
                "외부(고객/협력사)에게 ‘유출 발생’이라고 먼저 알린다.",
                "격리·로그 보존 후, 외부에 원인을 단정해 공유한다.",
                "아무 조치 없이 상황을 지켜본다.",
            ),
            "answer_key": "1",
        },
        {
            "id": "ncs_s3_q12",
            "item_number": 12,
            "session_id": 3,
            "domain": "문제해결능력 · 논리추론",
            "instruction": "\n".join(["상황: 야간 모니터링 중 알림 5개가 동시에 떴다."]),
            "stimulus_type": "text",
            "stimulus_text": "",
            "info_blocks": [
                {
                    "title": "조건",
                    "bullets": [
                        "개인정보 위험 알림을 최우선으로 대응한다.",
                        "동일하면 발생 시각이 더 이른 알림을 먼저 대응한다.",
                    ],
                },
            ],
            "table_spec": {},
            "question": "조건에 따라 가장 적절한 행동은 무엇인가?",
            "options": _options_dict(
                "알림 A(성능 저하/02:13)를 먼저 대응한다.",
                "알림 B(개인정보 위험/02:17)를 먼저 대응한다.",
                "알림 C(결제 장애/02:15)를 먼저 대응한다.",
                "알림 D(로그인 오류/02:12)를 먼저 대응한다.",
                "알림 E(개인정보 위험/02:19)를 먼저 대응한다.",
            ),
            "answer_key": "2",
        },
        {
            "id": "ncs_s3_q13",
            "item_number": 13,
            "session_id": 3,
            "domain": "문제해결능력 · 논리추론",
            "instruction": "\n".join(["상황: 오늘 배포할 변경 요청 1건을 지금 선택한다."]),
            "stimulus_type": "text",
            "stimulus_text": "",
            "info_blocks": [
                {
                    "title": "조건",
                    "bullets": [
                        "승인 완료 + 롤백 계획이 있는 요청만 배포한다.",
                        "그중 고객 영향이 더 큰 요청을 우선한다.",
                    ],
                },
            ],
            "table_spec": {},
            "question": "조건에 따라 가장 적절한 행동은 무엇인가?",
            "options": _options_dict(
                "요청 A(승인 완료/롤백 있음/영향 높음)를 배포한다.",
                "요청 B(승인 대기/롤백 있음/영향 중간)를 배포한다.",
                "요청 C(승인 완료/롤백 없음/영향 높음)를 배포한다.",
                "요청 D(승인 완료/롤백 있음/영향 낮음)를 배포한다.",
                "요청 E(승인 대기/롤백 없음/영향 중간)를 배포한다.",
            ),
            "answer_key": "1",
        },
        {
            "id": "ncs_s3_q14",
            "item_number": 14,
            "session_id": 3,
            "domain": "문제해결능력 · 논리추론",
            "instruction": "\n".join(["상황: 서비스 장애 공지 초안 5개 중 1개를 바로 게시해야 한다."]),
            "stimulus_type": "text",
            "stimulus_text": "",
            "info_blocks": [
                {
                    "title": "조건",
                    "bullets": [
                        "원인 추정/책임 단정 표현은 금지한다.",
                        "현 상태 + 다음 업데이트 시각을 포함한 초안 중 가장 간결한 것을 고른다.",
                    ],
                },
            ],
            "table_spec": {},
            "question": "조건에 따라 가장 적절한 행동은 무엇인가?",
            "options": _options_dict(
                "“원인이 특정 팀의 실수로 확인되었습니다. 현재 복구 중이며 30분 후 업데이트하겠습니다.”",
                "“현재 복구 중입니다. 가능한 한 빨리 업데이트하겠습니다.”",
                "“현재 복구 중입니다. 30분 후 업데이트하겠습니다.”",
                "“30분 후 업데이트하겠습니다.”",
                "“원인은 아직 미정이지만 조치 중입니다. 가능한 한 빨리 업데이트하겠습니다.”",
            ),
            "answer_key": "3",
        },
        {
            "id": "ncs_s3_q15",
            "item_number": 15,
            "session_id": 3,
            "domain": "문제해결능력 · 논리추론",
            "instruction": "\n".join(["상황: 다음 달 신규 업무 시스템으로 전환한다.", "전환 계획 1개를 확정한다."]),
            "stimulus_type": "text",
            "stimulus_text": "",
            "info_blocks": [
                {
                    "title": "조건",
                    "bullets": [
                        "전환 전 가이드/FAQ 배포 + 교육 1회를 진행한다.",
                        "전환 주간 지원창구 + 책임자 지정을 포함한 계획 중 ‘단계적 전환’을 고른다.",
                    ],
                },
            ],
            "table_spec": {},
            "question": "조건에 따라 가장 적절한 행동은 무엇인가?",
            "options": _options_dict(
                "계획 A(가이드/FAQ O, 지원창구 O, 단계적 전환)를 확정한다.",
                "계획 B(가이드/FAQ X, 지원창구 O, 단계적 전환)를 확정한다.",
                "계획 C(가이드/FAQ O, 지원창구 X, 전면 전환)를 확정한다.",
                "계획 D(가이드/FAQ O, 지원창구 O, 전면 전환)를 확정한다.",
                "계획 E(가이드/FAQ X, 지원창구 X, 전면 전환)를 확정한다.",
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
    st.caption(str(item.get("domain", "")))

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

        st.markdown(
            f"""
<div class="task-block">
  <div class="task-block-title">{_escape(title)}</div>
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
        _render_card("지시문", instruction, badge=f"Session {item.get('session_id')}")

    stimulus_type = str(item.get("stimulus_type", "text") or "text")
    stimulus_text = str(item.get("stimulus_text", "") or "")
    info_blocks: List[Dict[str, Any]] = list(item.get("info_blocks") or [])

    # Information / Conditions (structured blocks)
    if info_blocks or stimulus_text:
        st.markdown('<div class="task-section-title">정보 / 조건</div>', unsafe_allow_html=True)
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
        _render_card("발문", question_text)

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

    st.markdown('<div class="task-section-title">답안 선택</div>', unsafe_allow_html=True)
    selected_key = st.radio(
        "선택지",
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

