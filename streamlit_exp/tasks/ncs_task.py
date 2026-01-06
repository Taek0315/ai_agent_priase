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
            "instruction": "\n".join(
                [
                    "상황: 고객지원센터로 미처리 문의가 동시에 접수되었다.",
                    "당신은 당직 담당자로서 센터 우선 처리 규칙을 적용해야 한다.",
                    "아래 조건과 자료를 근거로 지금 바로 처리할 1건을 고르시오.",
                ]
            ),
            "stimulus_type": "table",
            "stimulus_text": "",
            "info_blocks": [
                {
                    "title": "조건/규칙",
                    "bullets": [
                        "우선순위 1: SLA 남은 시간이 가장 짧은 문의부터 처리한다.",
                        "우선순위 2: SLA 남은 시간이 같다면 ‘결제 오류’ 유형을 먼저 처리한다.",
                        "지금은 1건만 선택해 처리에 착수할 수 있다.",
                    ],
                },
                {
                    "title": "상황 정보",
                    "bullets": [
                        "모든 문의는 아직 고객에게 1차 답변이 발송되지 않았다.",
                        "SLA는 ‘최초 응답’ 기준이며, 초과 시 민원 이관 가능성이 높아진다.",
                        "문의 내용은 표의 ‘유형’으로 요약되어 있다.",
                    ],
                },
            ],
            "table_spec": {
                "columns": ["문의", "유형", "SLA 남은시간(분)", "접수채널"],
                "rows": [
                    ["문의 A", "환불 문의", 45, "이메일"],
                    ["문의 B", "결제 오류", 20, "채팅"],
                    ["문의 C", "배송 문의", 35, "전화"],
                    ["문의 D", "계정 변경", 30, "앱"],
                    ["문의 E", "결제 오류", 55, "이메일"],
                ],
            },
            "question": "조건/규칙을 모두 고려할 때, 지금 처리에 착수해야 할 문의는 무엇인가?",
            "options": _options_dict(
                "문의 A",
                "문의 B",
                "문의 C",
                "문의 D",
                "문의 E",
            ),
            "answer_key": "2",
        },
        {
            "id": "ncs_s1_q2",
            "item_number": 2,
            "session_id": 1,
            "domain": "의사소통능력 · 기초 자료해석",
            "instruction": "\n".join(
                [
                    "상황: 물류팀에서 출고 지연을 막기 위해 발주처 확인 순서를 정하고 있다.",
                    "당신은 출고 담당자로서 규칙에 따라 가장 먼저 확인할 주문을 선택해야 한다.",
                    "아래 조건과 자료를 근거로 지금 우선 대응할 주문을 고르시오.",
                ]
            ),
            "stimulus_type": "table",
            "stimulus_text": "",
            "info_blocks": [
                {
                    "title": "조건/규칙",
                    "bullets": [
                        "우선순위 1: 출고 예정일이 가장 이른 주문부터 확인한다.",
                        "우선순위 2: 출고 예정일이 같다면 수량이 더 많은 주문부터 확인한다.",
                        "지금은 1건만 선택해 담당자에게 확인 전화를 걸 수 있다.",
                    ],
                },
                {
                    "title": "상황 정보",
                    "bullets": [
                        "표의 수량은 현재 창고에 준비 완료된 박스 수 기준이다.",
                        "확인 전화는 ‘출고 가능 여부’와 ‘특이 요청사항’ 점검 목적이다.",
                        "오늘은 주문 변경 접수가 많아 우선순위 기준을 반드시 적용한다.",
                    ],
                },
            ],
            "table_spec": {
                "columns": ["주문", "출고 예정일", "수량(박스)", "발주처"],
                "rows": [
                    ["주문 A", "01/07", 12, "A사"],
                    ["주문 B", "01/06", 8, "B사"],
                    ["주문 C", "01/06", 15, "C사"],
                    ["주문 D", "01/08", 10, "D사"],
                    ["주문 E", "01/07", 20, "E사"],
                ],
            },
            "question": "조건/규칙을 모두 고려할 때, 지금 가장 먼저 확인해야 할 주문은 무엇인가?",
            "options": _options_dict("주문 A", "주문 B", "주문 C", "주문 D", "주문 E"),
            "answer_key": "3",
        },
        {
            "id": "ncs_s1_q3",
            "item_number": 3,
            "session_id": 1,
            "domain": "의사소통능력 · 기초 자료해석",
            "instruction": "\n".join(
                [
                    "상황: 협력사에 고객 관련 자료를 오늘 중으로 전달해 달라는 요청이 들어왔다.",
                    "당신은 정보보안 준수 책임을 지는 실무 담당자이다.",
                    "아래 조건과 자료를 근거로 가장 적절한 전송 방법을 고르시오.",
                ]
            ),
            "stimulus_type": "table",
            "stimulus_text": "",
            "info_blocks": [
                {
                    "title": "조건/규칙",
                    "bullets": [
                        "개인정보가 포함된 자료는 ‘사내 승인된 외부 전송 채널’로만 전달할 수 있다.",
                        "개인정보 자료를 외부로 전달할 때는 비밀번호 설정과 열람 만료일 설정이 필요하다.",
                        "규칙을 지키면서 협력사가 즉시 열람할 수 있도록 안내해야 한다.",
                    ],
                },
                {
                    "title": "상황 정보",
                    "bullets": [
                        "요청 자료에는 고객 이름과 연락처가 포함되어 있다.",
                        "협력사는 사내 계정이 없어 내부 공유폴더에는 접근할 수 없다.",
                        "현재 사용 가능한 전송 방법의 기능은 표와 같다.",
                    ],
                },
            ],
            "table_spec": {
                "columns": ["전송 방법", "승인 채널", "비밀번호/만료 설정", "전송 형태"],
                "rows": [
                    ["보안 전송 링크", "O", "O", "링크 공유"],
                    ["일반 이메일", "X", "X", "첨부파일"],
                    ["개인 메신저", "X", "X", "파일 전송"],
                    ["USB 전달", "X", "O", "대면 전달"],
                    ["외부초대 공유폴더", "O", "X", "폴더 초대"],
                ],
            },
            "question": "조건/규칙을 모두 고려할 때, 가장 적절한 전송 방법은 무엇인가?",
            "options": _options_dict(
                "보안 전송 링크",
                "일반 이메일",
                "개인 메신저",
                "USB 전달",
                "외부초대 공유폴더",
            ),
            "answer_key": "1",
        },
        {
            "id": "ncs_s1_q4",
            "item_number": 4,
            "session_id": 1,
            "domain": "의사소통능력 · 기초 자료해석",
            "instruction": "\n".join(
                [
                    "상황: 사내 장비 유지보수 외주 업체 1곳을 선정해야 한다.",
                    "당신은 구매 담당자로서 계약 조건을 충족하는 업체를 선택해야 한다.",
                    "아래 조건과 자료를 근거로 최종 선정할 업체를 고르시오.",
                ]
            ),
            "stimulus_type": "table",
            "stimulus_text": "",
            "info_blocks": [
                {
                    "title": "조건/규칙",
                    "bullets": [
                        "필수 조건: A/S 기간이 18개월 이상인 업체만 선정할 수 있다.",
                        "필수 조건을 만족하는 업체 중 견적 금액이 가장 낮은 업체를 선정한다.",
                        "표의 견적은 동일 범위의 작업과 동일 부품 조건이다.",
                    ],
                },
                {
                    "title": "상황 정보",
                    "bullets": [
                        "납기는 모두 계약 후 영업일 기준으로 산정되어 있다.",
                        "긴급 장애 대응은 A/S 기간 내 무상 출동이 포함되어 있다.",
                        "오늘 18:00까지 업체를 확정해 계약 요청서를 올려야 한다.",
                    ],
                },
            ],
            "table_spec": {
                "columns": ["업체", "A/S 기간", "견적(만원)", "납기(일)"],
                "rows": [
                    ["가 업체", "24개월", 120, 7],
                    ["나 업체", "18개월", 105, 10],
                    ["다 업체", "12개월", 90, 5],
                    ["라 업체", "18개월", 115, 6],
                    ["마 업체", "15개월", 98, 8],
                ],
            },
            "question": "조건/규칙을 모두 고려할 때, 최종 선정해야 할 업체는 무엇인가?",
            "options": _options_dict("가 업체", "나 업체", "다 업체", "라 업체", "마 업체"),
            "answer_key": "2",
        },
        {
            "id": "ncs_s1_q5",
            "item_number": 5,
            "session_id": 1,
            "domain": "의사소통능력 · 기초 자료해석",
            "instruction": "\n".join(
                [
                    "상황: 주간 근무기록 제출 마감이 다가오는데 일부 기록에 누락이 발견되었다.",
                    "당신은 팀 기록 담당자로서 제출 전 규칙에 맞게 보완해야 한다.",
                    "아래 조건과 자료를 근거로 가장 먼저 확인·수정 요청할 항목을 고르시오.",
                ]
            ),
            "stimulus_type": "table",
            "stimulus_text": "",
            "info_blocks": [
                {
                    "title": "조건/규칙",
                    "bullets": [
                        "퇴근 기록이 누락된 날은 제출 전에 반드시 보완해야 한다.",
                        "누락이 ‘외근’과 관련된 날은 현장 담당 승인 확인 후 수정 요청을 진행한다.",
                        "지금은 1건만 선택해 확인/수정 요청을 시작할 수 있다.",
                    ],
                },
                {
                    "title": "상황 정보",
                    "bullets": [
                        "표의 ‘외근승인’은 현장 담당자가 결재한 상태를 의미한다.",
                        "‘정상’은 출퇴근 기록이 모두 확인된 상태이다.",
                        "제출 마감은 오늘 17:00이다.",
                    ],
                },
            ],
            "table_spec": {
                "columns": ["근무일", "퇴근기록", "외근승인", "비고"],
                "rows": [
                    ["월", "정상", "해당없음", "사무실 근무"],
                    ["화", "누락", "대기", "외근 처리 포함"],
                    ["수", "정상", "해당없음", "사무실 근무"],
                    ["목", "정상", "승인", "외근 처리 포함"],
                    ["금", "정상", "해당없음", "사무실 근무"],
                ],
            },
            "question": "조건/규칙을 모두 고려할 때, 가장 먼저 확인·수정 요청을 시작해야 할 항목은 무엇인가?",
            "options": _options_dict(
                "월",
                "화",
                "수",
                "목",
                "금",
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
                    "상황: 오늘 안에 4인 참석 회의 일정을 확정해 공지해야 한다.",
                    "당신은 일정 담당자로서 필수 참석자와 자원 제약을 모두 반영해야 한다.",
                    "아래 조건과 자료를 근거로 가능한 회의안을 1개 고르시오.",
                ]
            ),
            "stimulus_type": "table",
            "stimulus_text": "",
            "info_blocks": [
                {
                    "title": "조건/규칙",
                    "bullets": [
                        "필수 참석자: 팀장 B와 결재자 D는 반드시 참석해야 한다.",
                        "회의실 제약: 회의실 A는 오전만, 회의실 B는 오후만 사용할 수 있다.",
                        "참석자 4명 전원이 해당 시간에 참석 가능해야 한다.",
                    ],
                },
                {
                    "title": "상황 정보",
                    "bullets": [
                        "참석 가능 시간: A 오전만, B 오전·오후, C 오후만, D 오후만, E 오전·오후.",
                        "회의는 1회 60분이며, 표의 시간대는 고정된 선택지이다.",
                        "회의안은 표의 참석자 구성을 그대로 적용한다.",
                    ],
                },
            ],
            "table_spec": {
                "columns": ["회의안", "시간", "회의실", "참석자(4명)"],
                "rows": [
                    ["안 A", "오전", "A", "A,B,E,D"],
                    ["안 B", "오전", "A", "A,B,C,E"],
                    ["안 C", "오후", "B", "B,C,D,E"],
                    ["안 D", "오후", "B", "A,B,D,E"],
                    ["안 E", "오후", "A", "B,C,D,E"],
                ],
            },
            "question": "조건/규칙을 모두 고려할 때, 확정할 수 있는 회의안은 무엇인가?",
            "options": _options_dict("안 A", "안 B", "안 C", "안 D", "안 E"),
            "answer_key": "3",
        },
        {
            "id": "ncs_s2_q7",
            "item_number": 7,
            "session_id": 2,
            "domain": "자원관리능력 · 상황판단",
            "instruction": "\n".join(
                [
                    "상황: 행사 배너 200장을 외주 제작해야 하며 업체 1곳을 선정해야 한다.",
                    "당신은 구매 담당자로서 납기·보안 요건을 충족하면서 비용을 최소화해야 한다.",
                    "아래 조건과 자료를 근거로 선정할 업체를 고르시오.",
                ]
            ),
            "stimulus_type": "table",
            "stimulus_text": "",
            "info_blocks": [
                {
                    "title": "조건/규칙",
                    "bullets": [
                        "필수 조건: 보안서약(인증) 보유 업체만 선정할 수 있다.",
                        "필수 조건: 납기 3일 이내 업체만 선정할 수 있다.",
                        "필수 조건을 모두 만족하는 업체 중 단가가 가장 낮은 업체를 선정한다.",
                    ],
                },
                {
                    "title": "상황 정보",
                    "bullets": [
                        "발주 수량은 200장이며, 단가는 1장 기준이다.",
                        "디자인 파일에는 미공개 행사 정보가 포함되어 보안 요건을 적용한다.",
                        "표의 납기는 업체가 보장한 최종 납품 가능 일수이다.",
                    ],
                },
            ],
            "table_spec": {
                "columns": ["업체", "단가(천원)", "납기(일)", "인증"],
                "rows": [
                    ["가사", 6.2, 3, "O"],
                    ["나사", 5.8, 4, "O"],
                    ["다사", 6.0, 2, "X"],
                    ["라사", 6.5, 2, "O"],
                    ["마사", 5.9, 3, "O"],
                ],
            },
            "question": "조건/규칙을 모두 고려할 때, 선정해야 할 업체는 무엇인가?",
            "options": _options_dict("가사", "나사", "다사", "라사", "마사"),
            "answer_key": "5",
        },
        {
            "id": "ncs_s2_q8",
            "item_number": 8,
            "session_id": 2,
            "domain": "자원관리능력 · 상황판단",
            "instruction": "\n".join(
                [
                    "상황: 오늘 중 고객에게 시스템 점검 안내를 배포해야 한다.",
                    "당신은 대외 공지 담당자로서 법무 검토 없이 배포 가능한 문구를 선택해야 한다.",
                    "아래 조건과 자료를 근거로 그대로 발송 가능한 초안을 고르시오.",
                ]
            ),
            "stimulus_type": "table",
            "stimulus_text": "",
            "info_blocks": [
                {
                    "title": "조건/규칙",
                    "bullets": [
                        "오늘은 법무 검토가 불가능하므로 ‘임시 안내’ 문구만 배포할 수 있다.",
                        "임시 안내에는 서비스 중단·다운타임을 단정하는 표현을 포함할 수 없다.",
                        "임시 안내에는 확정된 점검 시간(구체 시간대)을 포함할 수 없으며 문의처는 포함해야 한다.",
                    ],
                },
                {
                    "title": "상황 정보",
                    "bullets": [
                        "점검 여부는 내부적으로 검토 중이며, 확정 시 별도 공지를 낼 예정이다.",
                        "고객 혼선을 줄이기 위해 초안은 수정 없이 그대로 발송하는 것이 원칙이다.",
                        "아래 표는 현재 승인 대기 중인 초안 문구의 구성 요소를 요약한 것이다.",
                    ],
                },
            ],
            "table_spec": {
                "columns": ["초안", "중단 표현", "확정 시간", "문의처 포함"],
                "rows": [
                    ["초안 A", "O", "X", "O"],
                    ["초안 B", "X", "O", "O"],
                    ["초안 C", "X", "X", "O"],
                    ["초안 D", "X", "X", "X"],
                    ["초안 E", "O", "O", "O"],
                ],
            },
            "question": "조건/규칙을 모두 고려할 때, 수정 없이 그대로 발송 가능한 초안은 무엇인가?",
            "options": _options_dict("초안 A", "초안 B", "초안 C", "초안 D", "초안 E"),
            "answer_key": "3",
        },
        {
            "id": "ncs_s2_q9",
            "item_number": 9,
            "session_id": 2,
            "domain": "자원관리능력 · 상황판단",
            "instruction": "\n".join(
                [
                    "상황: 출장비가 사전 승인 없이 발생하여 사후 지급(예외) 승인 여부를 검토해야 한다.",
                    "당신은 경비 담당자로서 예외 승인 요건을 모두 충족하는지 확인해야 한다.",
                    "아래 조건과 자료를 근거로 예외 승인 가능한 사례를 고르시오.",
                ]
            ),
            "stimulus_type": "table",
            "stimulus_text": "",
            "info_blocks": [
                {
                    "title": "조건/규칙",
                    "bullets": [
                        "원칙: 출장비는 사전 승인 후 집행한다.",
                        "예외 승인: 긴급 사유가 있고 사전 승인 절차 진행이 현실적으로 불가능했으며 사후 24시간 내 보고가 완료되어야 한다.",
                        "예외 요건을 모두 충족하는 1건만 승인할 수 있다.",
                    ],
                },
                {
                    "title": "상황 정보",
                    "bullets": [
                        "사전 승인 가능 여부는 출장 요청부터 출발까지의 시간 여유를 기준으로 기록된다.",
                        "긴급 사유는 설비 장애, 안전사고 등 대체 불가능한 상황에 한한다.",
                        "사후 보고는 메일 또는 결재 시스템 등록 여부로 판단한다.",
                    ],
                },
            ],
            "table_spec": {
                "columns": ["사례", "긴급 사유", "사전 승인 가능", "사후 보고(24h)"],
                "rows": [
                    ["사례 A", "O", "O", "O"],
                    ["사례 B", "X", "X", "O"],
                    ["사례 C", "O", "X", "O"],
                    ["사례 D", "O", "X", "X"],
                    ["사례 E", "X", "O", "X"],
                ],
            },
            "question": "조건/규칙을 모두 고려할 때, 예외 사후 지급 승인이 가능한 사례는 무엇인가?",
            "options": _options_dict("사례 A", "사례 B", "사례 C", "사례 D", "사례 E"),
            "answer_key": "3",
        },
        {
            "id": "ncs_s2_q10",
            "item_number": 10,
            "session_id": 2,
            "domain": "자원관리능력 · 상황판단",
            "instruction": "\n".join(
                [
                    "상황: 부서에서 장비/운영 관련 지출 요청이 5건 접수되었다.",
                    "당신은 예산 담당자로서 규정을 충족하는 요청 1건을 즉시 승인해야 한다.",
                    "아래 조건과 자료를 근거로 지금 승인해야 할 요청을 고르시오.",
                ]
            ),
            "stimulus_type": "table",
            "stimulus_text": "",
            "info_blocks": [
                {
                    "title": "조건/규칙",
                    "bullets": [
                        "이번 주 잔여 예산은 500만 원이며, 1건만 즉시 승인할 수 있다.",
                        "필수 요청은 우선 승인 대상이지만, 증빙이 없는 요청은 승인할 수 없다.",
                        "조건을 만족하는 요청이 여러 건이면 금액이 가장 낮은 요청을 승인한다.",
                    ],
                },
                {
                    "title": "상황 정보",
                    "bullets": [
                        "‘필수 여부’는 운영 중단 방지 또는 법정 의무 여부를 의미한다.",
                        "증빙은 견적서 또는 계약서 초안의 제출 여부이다.",
                        "모든 금액은 부가세 포함 기준이다.",
                    ],
                },
            ],
            "table_spec": {
                "columns": ["요청", "필수 여부", "금액(만원)", "증빙"],
                "rows": [
                    ["요청 A", "O", 480, "X"],
                    ["요청 B", "O", 300, "O"],
                    ["요청 C", "X", 120, "O"],
                    ["요청 D", "O", 520, "O"],
                    ["요청 E", "X", 90, "X"],
                ],
            },
            "question": "조건/규칙을 모두 고려할 때, 지금 즉시 승인해야 할 요청은 무엇인가?",
            "options": _options_dict("요청 A", "요청 B", "요청 C", "요청 D", "요청 E"),
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
            "instruction": "\n".join(
                [
                    "상황: 사내 시스템에서 비정상 다운로드가 감지되어 정보 유출이 의심되는 상황이다.",
                    "당신은 1차 대응 담당자로서 즉시 조치와 보고를 동시에 진행해야 한다.",
                    "아래 조건과 자료를 근거로 가장 적절한 초기 대응안을 고르시오.",
                ]
            ),
            "stimulus_type": "table",
            "stimulus_text": "",
            "info_blocks": [
                {
                    "title": "조건/규칙",
                    "bullets": [
                        "유출 의심 시 1차 대응의 우선순위는 확산 차단과 증거 보존이다.",
                        "로그/파일을 삭제하거나 임의로 수정하는 행위는 금지되며 보안팀에 즉시 보고해야 한다.",
                        "사실 확인 전에는 외부(고객/협력사)에게 원인을 단정하거나 공유할 수 없다.",
                    ],
                },
                {
                    "title": "상황 정보",
                    "bullets": [
                        "현재는 원인과 범위가 확정되지 않았으며, 내부 모니터링 알림만 존재한다.",
                        "업무 영향 최소화를 위해 필요한 최소 범위에서 격리 조치를 우선 검토한다.",
                        "아래 표는 제안된 5개 초기 대응안을 주요 요소별로 요약한 것이다.",
                    ],
                },
            ],
            "table_spec": {
                "columns": ["대응안", "시스템 격리", "로그 보존", "외부 공유"],
                "rows": [
                    ["안 A", "O", "O", "X"],
                    ["안 B", "X", "O", "X"],
                    ["안 C", "O", "X", "X"],
                    ["안 D", "O", "O", "O"],
                    ["안 E", "X", "X", "X"],
                ],
            },
            "question": "조건/규칙을 모두 고려할 때, 가장 적절한 초기 대응안은 무엇인가?",
            "options": _options_dict("안 A", "안 B", "안 C", "안 D", "안 E"),
            "answer_key": "1",
        },
        {
            "id": "ncs_s3_q12",
            "item_number": 12,
            "session_id": 3,
            "domain": "문제해결능력 · 논리추론",
            "instruction": "\n".join(
                [
                    "상황: 야간 모니터링 중 서로 다른 유형의 알림 5건이 동시에 발생했다.",
                    "당신은 온콜 담당자로서 우선순위 규칙에 따라 첫 조치를 결정해야 한다.",
                    "아래 조건과 자료를 근거로 가장 먼저 대응할 알림을 고르시오.",
                ]
            ),
            "stimulus_type": "table",
            "stimulus_text": "",
            "info_blocks": [
                {
                    "title": "조건/규칙",
                    "bullets": [
                        "우선순위 1: 개인정보 관련 위험 알림을 가장 먼저 대응한다.",
                        "우선순위 2: 다음으로 결제 등 핵심 기능 장애 알림을 우선 대응한다.",
                        "동일 우선순위에서는 발생 시각이 더 이른 알림을 먼저 대응한다.",
                    ],
                },
                {
                    "title": "상황 정보",
                    "bullets": [
                        "알림의 ‘영향’은 모니터링 시스템이 분류한 고객 영향 범주이다.",
                        "첫 조치는 담당 채널로의 즉시 확인/격리/에스컬레이션을 의미한다.",
                        "아래 표는 동일 시점에 들어온 알림을 시간순으로 정리한 것이다.",
                    ],
                },
            ],
            "table_spec": {
                "columns": ["알림", "유형", "영향", "발생 시각"],
                "rows": [
                    ["알림 A", "성능 저하", "일부 지연", "02:13"],
                    ["알림 B", "개인정보 위험", "접근 이상", "02:17"],
                    ["알림 C", "결제 장애", "결제 실패", "02:15"],
                    ["알림 D", "로그인 오류", "일부 실패", "02:12"],
                    ["알림 E", "개인정보 위험", "권한 이상", "02:19"],
                ],
            },
            "question": "조건/규칙을 모두 고려할 때, 가장 먼저 대응해야 할 알림은 무엇인가?",
            "options": _options_dict("알림 A", "알림 B", "알림 C", "알림 D", "알림 E"),
            "answer_key": "2",
        },
        {
            "id": "ncs_s3_q13",
            "item_number": 13,
            "session_id": 3,
            "domain": "문제해결능력 · 논리추론",
            "instruction": "\n".join(
                [
                    "상황: 운영팀에서 오늘 배포할 변경 요청 5건이 승인 대기 중이다.",
                    "당신은 변경관리 담당자로서 위험을 통제하면서 배포 가능한 건을 선택해야 한다.",
                    "아래 조건과 자료를 근거로 지금 배포에 착수할 변경 요청을 고르시오.",
                ]
            ),
            "stimulus_type": "table",
            "stimulus_text": "",
            "info_blocks": [
                {
                    "title": "조건/규칙",
                    "bullets": [
                        "당일 배포는 변경 승인 완료와 롤백 계획이 모두 갖춰진 요청만 가능하다.",
                        "보안 취약점 대응은 우선 처리 대상이지만, 승인 또는 롤백이 없으면 즉시 배포할 수 없다.",
                        "조건을 만족하는 요청이 여러 건이면 고객 영향이 더 큰 요청을 우선한다.",
                    ],
                },
                {
                    "title": "상황 정보",
                    "bullets": [
                        "승인 완료는 변경관리 시스템에서 승인 상태가 ‘완료’로 표시된 경우를 말한다.",
                        "롤백 계획은 배포 실패 시 복구 절차가 문서로 등록되어 있어야 한다.",
                        "표의 고객 영향은 운영팀이 분류한 예상 영향 범주이다.",
                    ],
                },
            ],
            "table_spec": {
                "columns": ["요청", "유형", "승인", "롤백/고객영향"],
                "rows": [
                    ["요청 A", "보안 패치", "완료", "있음/높음"],
                    ["요청 B", "기능 개선", "대기", "있음/중간"],
                    ["요청 C", "보안 패치", "완료", "없음/높음"],
                    ["요청 D", "오류 수정", "완료", "있음/낮음"],
                    ["요청 E", "환경 설정", "대기", "없음/중간"],
                ],
            },
            "question": "조건/규칙을 모두 고려할 때, 지금 배포에 착수해야 할 요청은 무엇인가?",
            "options": _options_dict("요청 A", "요청 B", "요청 C", "요청 D", "요청 E"),
            "answer_key": "1",
        },
        {
            "id": "ncs_s3_q14",
            "item_number": 14,
            "session_id": 3,
            "domain": "문제해결능력 · 논리추론",
            "instruction": "\n".join(
                [
                    "상황: 서비스 장애 공지 초안을 5개 버전으로 받았고, 한 개를 바로 게시해야 한다.",
                    "당신은 대외 커뮤니케이션 담당자로서 정확성과 재발 방지를 동시에 고려해야 한다.",
                    "아래 조건과 자료를 근거로 게시 가능한 최선의 공지 초안을 고르시오.",
                ]
            ),
            "stimulus_type": "table",
            "stimulus_text": "",
            "info_blocks": [
                {
                    "title": "조건/규칙",
                    "bullets": [
                        "공지에는 사실로 확인된 내용만 포함해야 하며 원인 추정이나 책임 단정 표현은 금지된다.",
                        "고객이 다음 행동을 할 수 있도록 현 상태와 다음 업데이트 예정 시각을 포함해야 한다.",
                        "조건을 만족하는 초안이 여러 개면 문장이 가장 간결한 초안을 선택한다.",
                    ],
                },
                {
                    "title": "상황 정보",
                    "bullets": [
                        "장애 원인은 아직 조사 중이며, 복구 진행 상황만 확인된 상태이다.",
                        "업데이트 예정 시각은 ‘30분 후’ 또는 ‘정각 기준’처럼 구체적으로 제시해야 한다.",
                        "표는 각 초안이 포함한 요소를 체크리스트 형태로 정리한 것이다.",
                    ],
                },
            ],
            "table_spec": {
                "columns": ["초안", "추정/단정", "현 상태", "업데이트 시각"],
                "rows": [
                    ["초안 A", "O", "O", "O"],
                    ["초안 B", "X", "O", "X"],
                    ["초안 C", "X", "O", "O"],
                    ["초안 D", "X", "X", "O"],
                    ["초안 E", "O", "O", "X"],
                ],
            },
            "question": "조건/규칙을 모두 고려할 때, 게시해야 할 공지 초안은 무엇인가?",
            "options": _options_dict("초안 A", "초안 B", "초안 C", "초안 D", "초안 E"),
            "answer_key": "3",
        },
        {
            "id": "ncs_s3_q15",
            "item_number": 15,
            "session_id": 3,
            "domain": "문제해결능력 · 논리추론",
            "instruction": "\n".join(
                [
                    "상황: 다음 달부터 신규 업무 시스템을 도입하는데, 현장 혼선을 최소화해야 한다.",
                    "당신은 도입 담당자로서 교육·지원 체계를 갖춘 전환 계획을 확정해야 한다.",
                    "아래 조건과 자료를 근거로 가장 적절한 도입 계획을 고르시오.",
                ]
            ),
            "stimulus_type": "table",
            "stimulus_text": "",
            "info_blocks": [
                {
                    "title": "조건/규칙",
                    "bullets": [
                        "전환 전에 사용자 가이드와 FAQ를 배포하고, 최소 1회 교육을 진행해야 한다.",
                        "전환 주간에는 전담 지원 창구를 운영해야 하며 문의 응답 책임자를 지정해야 한다.",
                        "조건을 만족하는 계획 중 사용자 업무 중단 위험이 가장 낮은 방식으로 전환한다.",
                    ],
                },
                {
                    "title": "상황 정보",
                    "bullets": [
                        "현장 사용자는 시스템 변경에 익숙하지 않아 초기 문의가 급증할 것으로 예상된다.",
                        "업무 중단 위험은 전환 방식에 따라 달라지며, 단계적 전환이 일반적으로 위험이 낮다.",
                        "표는 제안된 5개 도입 계획의 준비 상태를 요약한 것이다.",
                    ],
                },
            ],
            "table_spec": {
                "columns": ["계획", "가이드/FAQ", "지원창구", "전환 방식"],
                "rows": [
                    ["계획 A", "O", "O", "단계적"],
                    ["계획 B", "X", "O", "단계적"],
                    ["계획 C", "O", "X", "전면"],
                    ["계획 D", "O", "O", "전면"],
                    ["계획 E", "X", "X", "전면"],
                ],
            },
            "question": "조건/규칙을 모두 고려할 때, 확정해야 할 도입 계획은 무엇인가?",
            "options": _options_dict("계획 A", "계획 B", "계획 C", "계획 D", "계획 E"),
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

