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
            "instruction": "당신은 오늘 처리해야 할 업무를 정리하고 있다. 아래 우선순위 규칙에 따라 ‘지금 가장 먼저’ 처리할 업무를 선택하시오.",
            "stimulus_type": "text",
            "stimulus_text": "",
            "info_blocks": [
                {
                    "title": "필수 조건",
                    "bullets": ["규칙: 마감 시간이 가장 이른 업무를 먼저 처리한다."],
                },
                {
                    "title": "업무 목록",
                    "table": {
                        "columns": ["업무", "마감", "예상 소요", "요청 부서"],
                        "rows": [
                            ["업무 A", "11:30", "30분", "인사팀"],
                            ["업무 B", "10:00", "40분", "재무팀"],
                            ["업무 C", "15:00", "20분", "개발팀"],
                            ["업무 D", "13:00", "15분", "영업팀"],
                            ["업무 E", "16:30", "10분", "고객지원팀"],
                        ],
                    },
                },
            ],
            "question": "규칙에 따라 지금 가장 먼저 처리해야 할 업무는 무엇인가?",
            "options": _options_dict(
                "업무 A",
                "업무 B",
                "업무 C",
                "업무 D",
                "업무 E",
            ),
            "answer_key": "2",
        },
        {
            "id": "ncs_s1_q2",
            "item_number": 2,
            "session_id": 1,
            "domain": "의사소통능력 · 기초 자료해석",
            "instruction": "당신은 납품 지연을 막기 위해 ‘가장 먼저 확인/대응해야 할 발주처’를 찾고 있다. 아래 그래프는 발주처별 ‘납품까지 남은 일수’이다.",
            "stimulus_type": "chart",
            "stimulus_text": "",
            "chart_spec": {
                "data": [
                    {"발주처": "A사", "남은일수": 6},
                    {"발주처": "B사", "남은일수": 3},
                    {"발주처": "C사", "남은일수": 8},
                    {"발주처": "D사", "남은일수": 5},
                    {"발주처": "E사", "남은일수": 4},
                ],
                "x": "발주처",
                "y": "남은일수",
                "title": "발주처별 납품까지 남은 일수",
            },
            "question": "그래프 기준으로, 지금 가장 먼저 확인/대응해야 할 발주처는 어디인가?",
            "options": _options_dict("A사", "B사", "C사", "D사", "E사"),
            "answer_key": "2",
        },
        {
            "id": "ncs_s1_q3",
            "item_number": 3,
            "session_id": 1,
            "domain": "의사소통능력 · 기초 자료해석",
            "instruction": "다음은 협력사로 파일을 전송할 때의 내부 규정이다. 규정에 따라 물음에 답하시오.",
            "stimulus_type": "text",
            "stimulus_text": "",
            "info_blocks": [
                {
                    "title": "필수 조건",
                    "bullets": [
                        "개인정보(이름/전화번호 등)가 포함된 파일은 외부(협력사) 전송 전에 반드시 암호화해야 한다.",
                        "암호화가 된 경우에만 외부 전송이 허용된다.",
                    ],
                },
                {
                    "title": "상황",
                    "bullets": [
                        "지금 보내려는 파일에는 고객 이름과 전화번호가 포함되어 있다.",
                        "암호화 기능을 사용할 수 있다.",
                    ],
                },
            ],
            "question": "규정에 따라 가장 적절한 조치는 무엇인가?",
            "options": _options_dict(
                "개인정보가 포함되어 있으므로 외부 전송을 즉시 금지한다(암호화 여부와 무관).",
                "암호화를 하지 않고 협력사로 전송한다.",
                "파일을 암호화한 뒤 협력사로 전송한다.",
                "협력사로 먼저 전송한 뒤, 나중에 암호화본을 다시 전송한다.",
                "개인정보가 포함되어 있어도 파일 용량이 작으면 외부 전송이 허용된다.",
            ),
            "answer_key": "3",
        },
        {
            "id": "ncs_s1_q4",
            "item_number": 4,
            "session_id": 1,
            "domain": "의사소통능력 · 기초 자료해석",
            "instruction": "당신은 외주 업체를 선정해야 한다. 아래 ‘필수 조건’을 만족하는 업체를 선택하시오.",
            "stimulus_type": "table",
            "stimulus_text": "",
            "info_blocks": [
                {
                    "title": "필수 조건",
                    "bullets": ["A/S 기간이 ‘18개월 이상’인 업체만 선택한다. (18개월은 포함됨)"],
                }
            ],
            "table_spec": {
                "columns": ["업체", "A/S 기간", "견적(만원)", "납기(일)"],
                "rows": [
                    ["가업체", "12개월", 90, 7],
                    ["나업체", "18개월", 110, 10],
                    ["다업체", "6개월", 70, 5],
                    ["라업체", "15개월", 95, 6],
                    ["마업체", "9개월", 80, 8],
                ],
            },
            "question": "필수 조건을 만족하는 업체는 무엇인가?",
            "options": _options_dict("가업체", "나업체", "다업체", "라업체", "마업체"),
            "answer_key": "2",
        },
        {
            "id": "ncs_s1_q5",
            "item_number": 5,
            "session_id": 1,
            "domain": "의사소통능력 · 기초 자료해석",
            "instruction": "당신은 주간 보고서에 업무 처리 시간을 정리하려 한다. 다음 표는 한 팀의 업무 처리 시간이다.",
            "stimulus_type": "table",
            "stimulus_text": "",
            "table_spec": {
                "columns": ["업무", "월", "화"],
                "rows": [
                    ["업무 A", "45분", "35분"],
                    ["업무 B", "30분", "25분"],
                ],
            },
            "question": "보고서에 기록할 ‘업무 A의 월요일+화요일 총 처리 시간’은 얼마인가?",
            "options": _options_dict(
                "70분",
                "75분",
                "80분",
                "85분",
                "90분",
            ),
            "answer_key": "4",
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
                    "당신은 팀 회의 일정을 오늘 안에 확정해야 한다.",
                    "아래 제약을 모두 만족하는 ‘시간/회의실/참석자(4명)’ 조합을 선택하시오.",
                ]
            ),
            "stimulus_type": "text",
            "stimulus_text": "",
            "info_blocks": [
                {
                    "title": "상황",
                    "bullets": [
                        "팀원은 총 5명(A, B, C, D, E)이다.",
                        "회의는 ‘오전’ 또는 ‘오후’ 중 한 번 진행한다.",
                    ],
                },
                {
                    "title": "제약(반드시 만족)",
                    "bullets": [
                        "참석 인원: 4명(예산상 최대 4명까지 가능)",
                        "회의실 A: 오전만 사용 가능",
                        "회의실 B: 오후만 사용 가능",
                        "참석 1인당 비용: 12만 원",
                        "총 비용: 50만 원 초과 불가 (4명 참석 시 48만 원)",
                    ],
                },
                {
                    "title": "참석 가능 시간(팀원별)",
                    "table": {
                        "columns": ["팀원", "가능 시간"],
                        "rows": [
                            ["A", "오전만"],
                            ["B", "오전·오후 모두"],
                            ["C", "오후만"],
                            ["D", "오후만"],
                            ["E", "오전·오후 모두"],
                        ],
                    },
                },
                {
                    "title": "결정 목표",
                    "bullets": ["제약을 모두 만족하는 조합 1개를 고른다."],
                },
            ],
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
            "instruction": "\n".join(
                [
                    "당신은 신규 사무공간 후보지 3곳(A, B, C) 중 한 곳을 최종 추천해야 한다.",
                    "회사 기준(가중치)을 반영한 ‘종합점수’가 가장 높은 후보지를 선택하시오.",
                ]
            ),
            "stimulus_type": "table",
            "stimulus_text": "",
            "info_blocks": [
                {
                    "title": "상황",
                    "bullets": ["각 후보지의 평가 점수(1~10점)가 주어진다."],
                },
                {
                    "title": "제약(가중치)",
                    "table": {
                        "columns": ["항목", "가중치"],
                        "rows": [
                            ["임대료 점수(낮을수록 유리)", "40%"],
                            ["접근성", "35%"],
                            ["공간 크기", "25%"],
                        ],
                    },
                },
                {
                    "title": "추가 규칙",
                    "bullets": [
                        "임대료는 “낮을수록 유리”이므로, 표의 ‘임대료 점수’는 이미 “낮을수록 높은 점수”로 환산된 값이다(그대로 사용)."
                    ],
                },
                {
                    "title": "종합점수(가중치 반영·계산됨)",
                    "table": {
                        "columns": ["후보지", "종합점수"],
                        "rows": [
                            ["A", "6.90"],
                            ["B", "7.30"],
                            ["C", "6.70"],
                        ],
                        "caption": "※ 계산 과정은 생략하고 결과만 제시합니다.",
                    },
                },
            ],
            "table_spec": {
                "columns": ["후보지", "임대료 점수", "접근성", "공간 크기"],
                "rows": [
                    ["A", 7, 6, 8],
                    ["B", 6, 9, 7],
                    ["C", 8, 5, 7],
                ],
            },
            "question": "기준에 따라 최종 추천할 후보지는 어디인가?",
            "options": _options_dict("A", "B", "C", "A와 C", "모두 동일"),
            "answer_key": "2",
        },
        {
            "id": "ncs_s2_q8",
            "item_number": 8,
            "session_id": 2,
            "domain": "자원관리능력 · 상황판단",
            "instruction": "\n".join(
                [
                    "당신은 서비스 점검 공지를 배포하려 한다.",
                    "아래 내부 커뮤니케이션 규정을 확인한 뒤, 지금 가장 적절한 다음 조치를 선택하시오.",
                ]
            ),
            "stimulus_type": "text",
            "stimulus_text": "",
            "info_blocks": [
                {
                    "title": "상황",
                    "bullets": [
                        "오늘 오후 4시에 서비스 점검 공지를 배포해야 한다.",
                        "현재 작성된 공지 초안에는 ‘점검 시간 확정’ 문구가 포함되어 있다.",
                    ],
                },
                {
                    "title": "규정(반드시 준수)",
                    "table": {
                        "columns": ["규정", "내용"],
                        "rows": [
                            ["1", "공지에 고객 영향(다운타임/중단)이 포함되면 ‘법무 검토’ 후 배포한다."],
                            ["2", "법무 검토가 불가능한 경우, 공지는 ‘임시 안내’로만 배포한다."],
                            ["3", "임시 안내에는 ‘점검 시간 확정’ 문구를 포함할 수 없다."],
                            ["4", "오늘은 법무 검토를 받을 수 없다."],
                        ],
                    },
                },
                {
                    "title": "결정 목표",
                    "bullets": [
                        "규정을 위반하지 않으면서도 혼선을 최소화하는 다음 조치를 고른다.",
                        "규정을 충족할 수 없는 상태라면, 배포를 멈추고 즉시 보고/조정한다.",
                    ],
                },
            ],
            "question": "지금 가장 적절한 다음 조치는 무엇인가?",
            "options": _options_dict(
                "초안을 그대로 ‘공지’로 배포한다(법무 검토 없이 진행).",
                "법무 검토가 불가능하더라도 ‘공지’로 배포한다(예외 처리).",
                "‘임시 안내’로 배포하되, ‘점검 시간 확정’ 문구를 그대로 포함한다.",
                "‘공지’와 ‘임시 안내’를 동시에 배포해 혼선을 줄인다.",
                "규정 충족이 불가능하므로 배포를 중단하고 즉시 보고/조정한다.",
            ),
            "answer_key": "5",
        },
        {
            "id": "ncs_s2_q9",
            "item_number": 9,
            "session_id": 2,
            "domain": "자원관리능력 · 상황판단",
            "instruction": "\n".join(
                [
                    "다음은 회사 출장비 지급 규정이다.",
                    "아래 사례 중에서 ‘예외적으로 사후 지급이 허용되는 경우’를 선택하시오.",
                    "예외는 제시된 조건을 모두 만족해야 한다(하나라도 빠지면 예외 인정 불가).",
                ]
            ),
            "stimulus_type": "text",
            "stimulus_text": "",
            "info_blocks": [
                {
                    "title": "상황",
                    "bullets": ["출장비 지급이 ‘원칙’에 해당하는지, 또는 ‘예외’로 사후 지급이 허용되는지 판단한다."],
                },
                {
                    "title": "제약(원칙)",
                    "bullets": ["출장비는 ‘사전 승인’ 후 지급한다."],
                },
                {
                    "title": "제약(예외: 두 조건을 모두 만족해야 함)",
                    "table": {
                        "columns": ["조건", "내용"],
                        "rows": [
                            ["(i)", "천재지변 또는 ‘대체 불가능한 긴급 상황’"],
                            ["(ii)", "사전 승인 절차를 진행할 ‘현실적 시간’이 없었음이 기록으로 남아야 함"],
                        ],
                    },
                },
                {
                    "title": "추가 규칙",
                    "bullets": ["예외는 (i)와 (ii)를 모두 만족해야 하며, 하나만 만족하면 예외로 인정되지 않는다."],
                },
            ],
            "question": "규정에 따라 ‘예외 사후 지급’을 승인할 수 있는 사례는 무엇인가?",
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
            "instruction": "\n".join(
                [
                    "당신은 총 예산 1,000만 원을 7개 사업(A~G)에 배분해야 한다.",
                    "규정을 만족하는 배분안 중에서, 예산을 가능한 한 많이 집행하는 안(= 잔여 예산이 최소인 안)을 선택하시오.",
                ]
            ),
            "stimulus_type": "text",
            "stimulus_text": "",
            "info_blocks": [
                {
                    "title": "상황",
                    "bullets": ["총 예산 1,000만 원을 사업 A~G에 배분한다."],
                },
                {
                    "title": "제약(필수 조건)",
                    "bullets": [
                        "총 예산: 1,000만 원",
                        "필수 사업 A, B, C: 각각 최소 200만 원 이상",
                        "사업 D, E: 각각 최소 50만 원 이상",
                    ],
                },
                {
                    "title": "제약(선택 조건)",
                    "bullets": [
                        "사업 F, G는 선택 사업이다.",
                        "단, 배정한다면 각각 최소 100만 원 이상이어야 한다.",
                    ],
                },
                {
                    "title": "추가 규칙(목표)",
                    "bullets": ["먼저 ‘규정 충족 여부’를 확인한 뒤, 충족한다면 잔여 예산이 최소인 안을 고른다."],
                },
            ],
            "question": "규정을 만족하면서 잔여 예산이 가장 적은 배분안은 무엇인가?",
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
            "instruction": "회의에서 프로젝트 결과를 두고 의견이 오가고 있다. 아래 발언 중, 사실 확인 없이 결론을 일반화해 판단을 흐릴 수 있는 발언을 고르시오.",
            "stimulus_type": "text",
            "stimulus_text": "",
            "question": "당신이 바로잡아야 할 발언은 무엇인가?",
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
            "instruction": "당신은 내년 매출 목표(전망)를 제안해야 한다. 다음은 최근 5년간 매출 변화이다.",
            "stimulus_type": "chart",
            "stimulus_text": "",
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
            "question": "현재 추세가 유지될 경우, 다음 해에 가장 합리적으로 예상되는 변화는 무엇인가?",
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
            "instruction": "당신은 제한된 시간 안에 처리할 업무 순서를 정해야 한다. 아래 정보를 바탕으로 가장 합리적인 처리 순서를 선택하시오.",
            "stimulus_type": "text",
            "stimulus_text": "",
            "info_blocks": [
                {
                    "title": "업무 정보",
                    "table": {
                        "columns": ["업무", "마감", "영향도"],
                        "rows": [
                            ["업무 A", "오늘", "중간"],
                            ["업무 B", "내일", "높음"],
                            ["업무 C", "오늘", "낮음"],
                        ],
                    },
                }
            ],
            "question": "마감과 영향도를 함께 고려할 때, 가장 합리적인 처리 순서는 무엇인가?",
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
            "instruction": "당신은 실패 요인을 정리해 다음 프로젝트에 반영하려 한다. 다음은 사업 실패 요약 보고서(발췌)이다.",
            "stimulus_type": "text",
            "stimulus_text": "",
            "info_blocks": [
                {
                    "title": "요약 보고서(발췌)",
                    "text": "“시장 조사 부족과 일정 관리 미흡으로 목표를 달성하지 못함.”",
                }
            ],
            "question": "다음 프로젝트에서 우선적으로 개선해야 할 ‘핵심 원인’으로 가장 적절한 것은 무엇인가?",
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
            "instruction": "신규 시스템 도입을 앞두고 부작용(혼란)을 최소화하려 한다. 다음 상황에서 가장 적절한 다음 조치를 선택하시오.",
            "stimulus_type": "text",
            "stimulus_text": "",
            "info_blocks": [
                {
                    "title": "상황",
                    "text": "“신규 시스템 도입으로 일부 직원의 업무 혼란이 예상된다.”",
                }
            ],
            "question": "부작용을 최소화하기 위해 지금 해야 할 가장 적절한 대응은 무엇인가?",
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

