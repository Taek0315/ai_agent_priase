#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import html
import json
import os
import random
import time
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import streamlit as st

# [CHANGE] Import centralized constants for shared UI/state configuration.
from constants import (
    ACHIVE_DEFAULT_ITEMS,
    ANTHRO_DEFAULT_ITEMS,
    DEMOGRAPHIC_AGE_LABEL,
    DEMOGRAPHIC_AGE_MAX,
    DEMOGRAPHIC_AGE_MIN,
    DEMOGRAPHIC_SEX_LABEL,
    DEMOGRAPHIC_SEX_OPTIONS,
    LIKERT5_LEGEND_HTML,
    LIKERT5_NUMERIC_OPTIONS,
    MANIPULATION_CHECK_EXPECTED_COUNT,
    MANIPULATION_CHECK_ITEMS,
)
from persistence import (
    build_sheet_row,
    build_storage_record,
    google_ready,
    save_to_gcs,
    save_to_sheets,
)
from utils.feedback_guard import get_feedback_once
from utils.ui_helpers import all_answered, render_likert_numeric
from utils.persistence import now_utc_iso

# --------------------------------------------------------------------------------------
# Streamlit page config & global styling
# --------------------------------------------------------------------------------------

st.set_page_config(
    page_title="AI 칭찬 연구 설문",
    layout="centered",
    initial_sidebar_state="collapsed",
)

COMPACT_CSS = """
 <style>
   :root { --fs-base: 16px; --lh-base: 1.65; }
   #MainMenu, header, footer, [data-testid="stToolbar"] { display: none !important; }
   [data-testid="stSidebar"], section[data-testid="stSidebar"] { display: none !important; }
   [data-testid="stSidebarCollapseButton"],
   [data-testid="stSidebarNav"],
   button[kind="header"] { display: none !important; }
   html, body, [data-testid="stAppViewContainer"] {
     font-size: var(--fs-base);
     line-height: var(--lh-base);
     overflow-x: hidden !important;
   }
   *, *::before, *::after {
     box-sizing: border-box;
   }
   .stApp,
   [data-testid="stAppViewContainer"],
   [data-testid="stAppViewContainer"] > .main,
   section.main {
     margin-top: 0 !important;
     padding-top: 0 !important;
   }
   [data-testid="stAppViewContainer"] > .main > div,
   .main .block-container,
   section.main > div.block-container {
     padding-top: 0 !important;
     padding-bottom: 20px !important;
   }
     h1, .stMarkdown h1 {
       font-size: 1.8rem;
       line-height: 1.3;
       margin-top: 0 !important;
       margin-bottom: 12px !important;
       text-align: left !important;
     }
     h2, .stMarkdown h2 {
       font-size: 1.4rem;
       line-height: 1.35;
       margin-top: 0 !important;
       margin-bottom: 10px !important;
       text-align: left !important;
     }
     h3, .stMarkdown h3 {
       font-size: 1.2rem;
       margin-top: 0 !important;
       margin-bottom: 8px !important;
       text-align: left !important;
     }
   @media (max-width: 768px) {
     h1, .stMarkdown h1 {
       font-size: 1.4rem;
       line-height: 1.3;
     }
     h2, .stMarkdown h2 {
       font-size: 1.25rem;
     }
     h3, .stMarkdown h3 {
       font-size: 1.08rem;
     }
   }
       .section-heading,
       .section-title {
         font-weight: 700;
         text-align: left !important;
         margin-top: 0;
         margin-bottom: 12px;
       }
       .praise-highlight {
         color: #FFE082;
         font-weight: 600;
       }
       .debrief-box {
         width: 100%;
         max-width: 100%;
         white-space: normal;
         word-break: keep-all;
         overflow-x: hidden;
         overflow-y: visible;
         padding: 1.25rem 1.5rem;
         border-radius: 0.75rem;
         background-color: #20252b;
         color: #f5f5f5;
         box-sizing: border-box;
       }
   .question-card {
     width: 100%;
     max-width: 100%;
     border-radius: 16px;
     border: 1px solid #dfe4f0;
     background: #f6f7fb;
     padding: 18px 20px;
     margin: 12px 0 18px;
     overflow: hidden;
   }
   .question-badge {
     display: inline-flex;
     padding: 4px 12px;
     border-radius: 999px;
     background: #dde1fb;
     color: #3941a4;
     font-size: 0.85rem;
     font-weight: 600;
     margin-bottom: 10px;
   }
   .question-label {
     font-size: 0.85rem;
     letter-spacing: 0.02em;
     text-transform: uppercase;
     color: #6c7390;
     font-weight: 600;
     margin-bottom: 4px;
   }
   .question-stem,
   .question-stem-text {
     font-weight: 700;
     font-size: 1.08rem;
     margin: 0 0 8px;
     color: #1f2433;
     line-height: 1.65;
     white-space: normal;
     word-break: keep-all;
   }
   .question-stem-text {
     font-weight: 600;
   }
   .question-card pre,
   .question-card code {
     white-space: normal !important;
   }
   @media (max-width: 768px) {
     .question-card {
       padding: 14px 16px;
     }
     .question-stem,
     .question-stem-text {
       font-size: 1rem;
     }
   }
   .stRadio > div[role="radiogroup"] {
     gap: 6px !important;
   }
   .stRadio label {
     white-space: normal !important;
     align-items: flex-start !important;
     font-weight: 500;
   }
   p, .stMarkdown p   { margin-top: 0 !important; }
   .anthro-title { margin-top: 0 !important; }
   div[data-testid="stProgress"] { margin-bottom: 0.4rem !important; }
   .mcp-footer { margin-top: 0.6rem !important; }
 </style>
 """

st.markdown(COMPACT_CSS, unsafe_allow_html=True)

FEEDBACK_UI_CSS = """
<style>
    .feedback-page {
      width: 100%;
      padding: clamp(24px, 4vw, 32px) clamp(16px, 4vw, 48px) clamp(48px, 7vw, 72px);
      box-sizing: border-box;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: flex-start;
      gap: clamp(18px, 4vw, 28px);
      background-color: #0b1220;
      background-image:
        radial-gradient(circle at 20% -10%, rgba(126, 58, 242, 0.18), transparent 45%),
        radial-gradient(circle at 80% 0%, rgba(59, 130, 246, 0.12), transparent 40%);
      position: relative;
      isolation: isolate;
    }
    .feedback-page::before {
      content: "";
      position: absolute;
      inset: 0;
      background: radial-gradient(circle at 50% 0%, rgba(199, 210, 254, 0.08), transparent 65%);
      pointer-events: none;
      z-index: -1;
    }
    .feedback-card,
    .feedback-actions {
      width: 100%;
      max-width: 720px;
    }
    .feedback-hero-card {
      padding: clamp(28px, 5vw, 44px);
      border-radius: 30px;
      background: linear-gradient(135deg, rgba(114, 78, 249, 0.98), rgba(79, 70, 229, 0.96) 55%, rgba(67, 56, 202, 0.94));
      color: #f5f3ff;
      box-shadow: 0 30px 65px -28px rgba(79, 70, 229, 0.85);
      position: relative;
      overflow: hidden;
    }
  .feedback-hero-card::after {
    content: "";
    position: absolute;
    inset: 0;
    background: radial-gradient(circle at 85% 15%, rgba(255, 255, 255, 0.28), transparent 55%);
    pointer-events: none;
  }
  .feedback-hero-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 6px 14px;
    border-radius: 999px;
    background: rgba(255, 255, 255, 0.18);
    color: #eef2ff;
    font-weight: 600;
    font-size: 0.95rem;
    letter-spacing: 0.3px;
    box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.35);
  }
  .feedback-hero-badge span {
    display: inline-flex;
    align-items: center;
    justify-content: center;
  }
  .feedback-hero-body {
    display: flex;
    align-items: center;
    gap: clamp(20px, 5vw, 36px);
    margin-top: clamp(18px, 3vw, 28px);
  }
  .feedback-icon-wrap {
    flex-shrink: 0;
    width: clamp(72px, 12vw, 96px);
    height: clamp(72px, 12vw, 96px);
    border-radius: 50%;
    background: linear-gradient(135deg, rgba(248, 250, 255, 0.28), rgba(255, 255, 255, 0.1));
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: clamp(34px, 6vw, 48px);
    box-shadow: 0 22px 45px -26px rgba(15, 23, 42, 0.55), inset 0 1px 0 rgba(255, 255, 255, 0.35);
    backdrop-filter: blur(4px);
  }
  .feedback-hero-text {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }
  .feedback-hero-title {
    font-size: clamp(1.9rem, 3vw, 2.6rem);
    font-weight: 800;
    line-height: 1.15;
    margin: 0;
    letter-spacing: 0.3px;
  }
  .feedback-hero-subtitle {
    margin: 0;
    font-size: clamp(1.05rem, 2vw, 1.25rem);
    color: rgba(238, 242, 255, 0.9);
  }
  .feedback-meta {
    margin-top: clamp(20px, 3vw, 32px);
    font-size: 1rem;
    color: rgba(238, 242, 255, 0.88);
    display: flex;
    align-items: center;
    gap: 10px;
  }
  .feedback-meta::before {
    content: "📡";
    font-size: 1.1rem;
  }
    .feedback-comment-card {
      display: flex;
      flex-direction: column;
      gap: clamp(10px, 2vw, 16px);
      background: rgba(248, 250, 255, 0.95);
      border-radius: 26px;
      padding: clamp(22px, 4.5vw, 30px);
      box-shadow: 0 26px 65px -36px rgba(15, 23, 42, 0.75);
      border: 1px solid rgba(148, 163, 184, 0.25);
      backdrop-filter: blur(8px);
      position: relative;
    }
  .feedback-comment-card::before {
    content: "";
    position: absolute;
    inset: 0;
    border-radius: inherit;
    border: 1px solid rgba(124, 58, 237, 0.18);
    pointer-events: none;
  }
    .feedback-comment-title {
      font-size: 1.28rem;
      font-weight: 700;
      color: #3730a3;
      display: inline-flex;
      align-items: center;
      gap: 12px;
      margin: 0;
    }
    .feedback-comment-subtitle {
      margin: 0;
      font-size: 1.05rem;
      color: #475569;
      line-height: 1.6;
    }
  .feedback-comment-icon {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 38px;
    height: 38px;
    border-radius: 50%;
    background: linear-gradient(135deg, #f97316, #facc15);
    color: #fff;
    font-size: 1.3rem;
    box-shadow: 0 16px 30px -20px rgba(249, 115, 22, 0.6);
  }
    .feedback-comment-body {
      margin: 0;
      font-size: clamp(1.07rem, 2vw, 1.22rem);
      line-height: 1.8;
      color: #1f2937;
      min-height: 110px;
    }
    .feedback-comment-body strong {
      color: #4338ca;
    }
    .feedback-comment-body[data-empty="true"] {
      color: #6b7280;
      font-style: italic;
    }
  .feedback-comment-body::selection {
    background: rgba(124, 58, 237, 0.16);
  }
      .feedback-praise-card {
        position: relative;
        border-radius: 26px;
        padding: clamp(26px, 5vw, 36px);
        background: linear-gradient(135deg, rgba(255, 255, 255, 0.98), rgba(224, 231, 255, 0.94));
        border: 1px solid rgba(148, 163, 184, 0.25);
        box-shadow: 0 26px 65px -36px rgba(15, 23, 42, 0.75);
        backdrop-filter: blur(8px);
        color: #1f2937;
        font-size: clamp(1.08rem, 2.2vw, 1.3rem);
        line-height: 1.8;
        word-break: keep-all;
      }
      .feedback-praise-card p {
        margin: 0;
      }
        .feedback-praise-text {
          margin: 0;
          white-space: pre-line;
        }
      .feedback-praise-card strong {
        color: #4338ca;
      }
      .feedback-praise-card[data-empty="true"] {
        color: #64748b;
        font-style: italic;
      }
    .feedback-praise-card::before {
      content: "";
      position: absolute;
      inset: 0;
      border-radius: inherit;
      border: 1px solid rgba(124, 58, 237, 0.18);
      pointer-events: none;
    }
    .feedback-micro-card {
      background: rgba(15, 23, 42, 0.55);
      color: #e0e7ff;
      border: 1px solid rgba(99, 102, 241, 0.35);
    }
    .feedback-micro-card::before {
      border-color: rgba(96, 165, 250, 0.3);
    }
    .feedback-micro-card .feedback-comment-title {
      color: #e0e7ff;
    }
    .feedback-micro-card .feedback-comment-icon {
      background: linear-gradient(135deg, #38bdf8, #6366f1);
      box-shadow: 0 16px 32px -22px rgba(59, 130, 246, 0.55);
    }
    .feedback-micro-card .feedback-comment-body {
      color: #e2e8f0;
    }
  .feedback-actions {
    margin-top: clamp(4px, 1vw, 12px);
  }
  .feedback-actions .stButton > button {
    width: 100%;
    border-radius: 14px;
    padding: 16px 24px;
    font-size: 1.1rem;
    font-weight: 700;
    background: linear-gradient(135deg, #6366f1, #8b5cf6);
    color: #ffffff;
    border: none;
    box-shadow: 0 20px 38px -24px rgba(99, 102, 241, 0.85);
    transition: transform 0.2s ease, box-shadow 0.2s ease, opacity 0.2s ease;
  }
  .feedback-actions .stButton > button:hover {
    transform: translateY(-1px);
    box-shadow: 0 24px 44px -24px rgba(124, 58, 237, 0.9);
    opacity: 0.95;
  }
  .feedback-actions .stButton > button:active {
    transform: translateY(0);
    opacity: 1;
  }
    @media (max-width: 720px) {
      .feedback-page {
        padding: 22px 14px 42px;
        gap: 16px;
      }
    .feedback-hero-card {
      border-radius: 26px;
    }
    .feedback-hero-body {
      flex-direction: column;
      align-items: flex-start;
    }
    .feedback-icon-wrap {
      width: 68px;
      height: 68px;
      font-size: 34px;
    }
      .feedback-comment-card,
      .feedback-praise-card {
        border-radius: 22px;
        padding: 22px;
      }
      .feedback-comment-body {
        font-size: 1.05rem;
      }
  }
</style>
""".strip()

MCP_OVERLAY_CSS = """
<style>
  .mcp-overlay {
    position: fixed;
    inset: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    background: radial-gradient(circle at 20% 20%, rgba(99, 102, 241, 0.16), transparent 55%),
                radial-gradient(circle at 80% 15%, rgba(14, 165, 233, 0.18), transparent 58%),
                rgba(7, 12, 26, 0.86);
    backdrop-filter: blur(6px);
    z-index: 9995;
    padding: clamp(24px, 6vw, 48px);
  }
  .mcp-card {
    position: relative;
    width: min(520px, 100%);
    padding: clamp(28px, 5vw, 40px);
    border-radius: 28px;
    background: linear-gradient(135deg, rgba(15, 23, 42, 0.92), rgba(30, 64, 175, 0.88));
    box-shadow: 0 28px 60px -28px rgba(15, 23, 42, 0.8), 0 0 0 1px rgba(148, 163, 184, 0.18);
    color: #e2e8f0;
    isolation: isolate;
    overflow: hidden;
  }
  .mcp-card::after {
    content: "";
    position: absolute;
    inset: 0;
    background: radial-gradient(circle at 85% 12%, rgba(96, 165, 250, 0.28), transparent 55%);
    opacity: 0.9;
    pointer-events: none;
    z-index: -1;
  }
  .mcp-card-header {
    display: flex;
    align-items: center;
    gap: clamp(16px, 3vw, 24px);
    margin-bottom: clamp(20px, 3vw, 28px);
  }
  .mcp-icon-wrap {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: clamp(64px, 12vw, 82px);
    height: clamp(64px, 12vw, 82px);
    border-radius: 24px;
    background: linear-gradient(135deg, rgba(255, 255, 255, 0.18), rgba(148, 163, 184, 0.12));
    box-shadow: 0 18px 40px -24px rgba(96, 165, 250, 0.55), inset 0 1px 0 rgba(255, 255, 255, 0.22);
    font-size: clamp(32px, 6vw, 44px);
    animation: mcpPulse 2.4s ease-in-out infinite;
  }
  .mcp-title {
    font-size: clamp(1.5rem, 2.7vw, 1.9rem);
    font-weight: 800;
    margin: 0;
    color: #f8fafc;
    letter-spacing: 0.3px;
  }
  .mcp-subtitle {
    margin: 6px 0 0;
    font-size: clamp(1.02rem, 2.2vw, 1.15rem);
    color: rgba(226, 232, 240, 0.88);
    line-height: 1.6;
  }
  .mcp-badge {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 6px 14px;
    border-radius: 999px;
    background: rgba(148, 163, 184, 0.18);
    color: #e0f2fe;
    font-size: 0.95rem;
    font-weight: 600;
    margin-bottom: clamp(18px, 3vw, 24px);
  }
  .mcp-status-block {
    margin-bottom: clamp(20px, 3vw, 28px);
  }
  .mcp-status-label {
    font-size: clamp(1.15rem, 2.3vw, 1.35rem);
    font-weight: 700;
    display: flex;
    align-items: center;
    gap: 8px;
    color: #bfdbfe;
  }
  .mcp-status-detail {
    margin-top: 8px;
    font-size: clamp(0.98rem, 2vw, 1.08rem);
    color: rgba(226, 232, 240, 0.8);
    line-height: 1.6;
  }
  .mcp-dots {
    display: inline-flex;
    min-width: 28px;
    letter-spacing: 2px;
    color: rgba(148, 197, 255, 0.9);
  }
  .mcp-progress-track {
    width: 100%;
    height: 14px;
    border-radius: 999px;
    background: rgba(15, 23, 42, 0.65);
    position: relative;
    overflow: hidden;
    border: 1px solid rgba(148, 163, 184, 0.35);
  }
  .mcp-progress-fill {
    position: absolute;
    inset: 0;
    background: linear-gradient(90deg, rgba(96, 165, 250, 0.1), rgba(59, 130, 246, 0.9), rgba(129, 140, 248, 0.92));
    transition: width 0.08s ease-out;
    box-shadow: 0 0 18px rgba(99, 102, 241, 0.4);
  }
  .mcp-progress-meta {
    margin-top: 12px;
    font-size: 0.94rem;
    color: rgba(191, 219, 254, 0.85);
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .mcp-progress-meta span {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 24px;
    height: 24px;
    border-radius: 50%;
    background: rgba(148, 197, 255, 0.18);
    color: rgba(224, 242, 254, 0.95);
    font-size: 0.85rem;
    font-weight: 600;
  }
  .mcp-footer-hint {
    margin-top: clamp(16px, 3vw, 24px);
    padding: 12px 16px;
    border-radius: 16px;
    background: rgba(14, 165, 233, 0.08);
    color: rgba(191, 219, 254, 0.9);
    font-size: 0.95rem;
    line-height: 1.5;
    border: 1px solid rgba(96, 165, 250, 0.22);
  }
  @media (max-width: 640px) {
    .mcp-card {
      padding: 24px;
      border-radius: 24px;
    }
    .mcp-card-header {
      flex-direction: column;
      align-items: flex-start;
      gap: 16px;
    }
    .mcp-icon-wrap {
      width: 60px;
      height: 60px;
      border-radius: 20px;
    }
    .mcp-progress-meta {
      font-size: 0.9rem;
    }
  }
  @keyframes mcpPulse {
    0%, 100% { transform: scale(1); box-shadow: 0 0 0 0 rgba(129, 140, 248, 0.25); }
    50% { transform: scale(1.04); box-shadow: 0 0 0 12px rgba(129, 140, 248, 0); }
  }
</style>
""".strip()

MCP_STATUS_SEQUENCE = [
    ("패턴 스캔 중", "[INFO][COVNOX] Parsing rationale tags (single-select)"),
    ("응답 일치도 정렬 중", "추론 근거 태그 분포를 규칙 템플릿과 비교하는 중입니다."),
    ("추론 효율 계산 중", "조건별 비교 지표와 안정도를 재계산하고 있습니다."),
    ("AI 튜터 리포트 구성 중", "맞춤형 메시지를 정교화하고 있습니다."),
]

MCP_OVERLAY_TEMPLATE = """
<div class="mcp-overlay">
  <div class="mcp-card">
    <div class="mcp-badge">COVNOX 분석 프로토콜 · {round_label}</div>
    <div class="mcp-card-header">
      <div class="mcp-icon-wrap">🤖</div>
      <div>
        <h2 class="mcp-title">AI 튜터 분석 중...</h2>
        <p class="mcp-subtitle">응답 패턴을 분석하여 추론 리포트를 준비하고 있습니다.</p>
      </div>
    </div>
    <div class="mcp-status-block">
      <div class="mcp-status-label">{status_headline}<span class="mcp-dots">{dots}</span></div>
      <div class="mcp-status-detail">{status_detail}</div>
    </div>
    <div class="mcp-progress-track">
      <div class="mcp-progress-fill" style="width:{progress}%"></div>
    </div>
    <div class="mcp-progress-meta">
      <span>{progress}%</span>
      <div>AI 분석 서브루틴 실행 중</div>
    </div>
    <div class="mcp-footer-hint">
      AI가 당신의 응답 구조를 정밀하게 해석하고 있습니다. 잠시만 기다려 주세요.
    </div>
  </div>
</div>
""".strip()


ANALYSIS_COMPLETE_CSS = """
<style>
  .analysis-complete-wrapper {
    width: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: clamp(48px, 10vw, 96px) clamp(18px, 6vw, 48px);
    background: radial-gradient(circle at 20% -10%, rgba(124, 58, 237, 0.12), transparent 55%),
                radial-gradient(circle at 82% 0%, rgba(37, 99, 235, 0.16), transparent 50%),
                rgba(7, 12, 26, 0.78);
    border-radius: 32px;
    box-sizing: border-box;
  }
  .analysis-complete-card {
    width: min(600px, 100%);
    padding: clamp(32px, 6vw, 48px);
    border-radius: 32px;
    background: linear-gradient(135deg, rgba(30, 64, 175, 0.92), rgba(99, 102, 241, 0.9), rgba(124, 58, 237, 0.92));
    color: #f8fafc;
    box-shadow: 0 36px 70px -32px rgba(79, 70, 229, 0.85), 0 0 0 1px rgba(148, 163, 184, 0.2);
    position: relative;
    overflow: hidden;
  }
  .analysis-complete-card::before {
    content: "";
    position: absolute;
    inset: 0;
    background: radial-gradient(circle at 85% 10%, rgba(226, 232, 240, 0.28), transparent 55%);
    pointer-events: none;
    z-index: 0;
  }
  .analysis-complete-card > * {
    position: relative;
    z-index: 1;
  }
  .analysis-complete-badge {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 6px 16px;
    border-radius: 999px;
    background: rgba(148, 197, 255, 0.2);
    color: #e0f2fe;
    font-weight: 600;
    font-size: 0.95rem;
    letter-spacing: 0.3px;
    box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.4);
  }
  .analysis-complete-body {
    display: flex;
    align-items: center;
    gap: clamp(22px, 5vw, 36px);
    margin-top: clamp(22px, 4vw, 32px);
  }
  .analysis-complete-icon {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: clamp(72px, 13vw, 96px);
    height: clamp(72px, 13vw, 96px);
    border-radius: 28px;
    background: linear-gradient(135deg, rgba(248, 250, 255, 0.22), rgba(226, 232, 240, 0.1));
    font-size: clamp(38px, 7vw, 50px);
    box-shadow: 0 24px 48px -28px rgba(96, 165, 250, 0.65), inset 0 1px 0 rgba(255, 255, 255, 0.35);
    backdrop-filter: blur(4px);
  }
  .analysis-complete-text {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }
  .analysis-complete-title {
    margin: 0;
    font-size: clamp(2.1rem, 3.6vw, 2.6rem);
    font-weight: 800;
    line-height: 1.12;
    letter-spacing: 0.3px;
  }
  .analysis-complete-subtitle {
    margin: 0;
    font-size: clamp(1.05rem, 2.2vw, 1.3rem);
    color: rgba(226, 232, 240, 0.92);
    line-height: 1.6;
  }
  .analysis-complete-meta {
    margin-top: clamp(24px, 4vw, 32px);
    padding-top: clamp(18px, 3vw, 24px);
    border-top: 1px solid rgba(148, 163, 184, 0.35);
    font-size: 1rem;
    color: rgba(226, 232, 255, 0.88);
    display: flex;
    align-items: center;
    gap: 10px;
  }
  .analysis-complete-meta::before {
    content: "📡";
    font-size: 1.15rem;
  }
  .analysis-complete-status {
    margin-top: 14px;
    display: inline-flex;
    align-items: center;
    gap: 8px;
    background: rgba(148, 197, 255, 0.16);
    border-radius: 999px;
    padding: 8px 16px;
    font-size: 0.95rem;
    color: rgba(226, 232, 255, 0.9);
    border: 1px solid rgba(191, 219, 254, 0.22);
  }
  .analysis-complete-status::before {
    content: "✅";
  }
  .analysis-complete-button {
    margin-top: clamp(26px, 4vw, 36px);
  }
  .analysis-complete-button .stButton > button {
    width: 100%;
    border-radius: 16px;
    padding: 18px 26px;
    font-size: 1.15rem;
    font-weight: 700;
    color: #ffffff;
    background: linear-gradient(135deg, #6366f1, #8b5cf6);
    border: none;
    box-shadow: 0 28px 52px -30px rgba(99, 102, 241, 0.88);
    transition: transform 0.2s ease, box-shadow 0.2s ease, opacity 0.2s ease;
  }
  .analysis-complete-button .stButton > button:hover {
    transform: translateY(-2px);
    box-shadow: 0 32px 58px -28px rgba(124, 58, 237, 0.92);
  }
  .analysis-complete-button .stButton > button:active {
    transform: translateY(0);
    opacity: 0.97;
  }
  @media (max-width: 680px) {
    .analysis-complete-wrapper {
      padding: 36px 14px 54px;
      border-radius: 26px;
    }
    .analysis-complete-card {
      border-radius: 26px;
      padding: 28px;
    }
    .analysis-complete-body {
      flex-direction: column;
      align-items: flex-start;
    }
    .analysis-complete-icon {
      width: 68px;
      height: 68px;
      border-radius: 22px;
      font-size: 34px;
    }
    .analysis-complete-button .stButton > button {
      font-size: 1.08rem;
    }
  }
</style>
""".strip()


# [CHANGE] Legend snippet for 6-point Likert (Achive scale only).
LIKERT6_LEGEND_HTML = """
<div style='display:flex;justify-content:center;gap:12px;flex-wrap:wrap;font-size:16px;margin-bottom:22px;'>
  <span><b>1</b> : 전혀 그렇지 않다</span><span>—</span>
  <span><b>3</b> : 보통이다</span><span>—</span>
  <span><b>6</b> : 매우 그렇다</span>
</div>
""".strip()

# [CHANGE] Default runtime feature toggles for feedback/debug rendering.
SHOW_PER_ITEM_INLINE_FEEDBACK = False
SHOW_PER_ITEM_SUMMARY = False
SHOW_DEBUG_RESULTS = False


def get_or_assign_praise_condition() -> str:
    """
    Returns exactly one of:
      'emotional_specific', 'computational_specific',
      'emotional_surface', 'computational_surface'
    Assign once per participant and persist in st.session_state.
    Never display this string to the participant.
    """
    key = "praise_condition"
    if key not in st.session_state:
        st.session_state[key] = random.choice(
            [
                "emotional_specific",
                "computational_specific",
                "emotional_surface",
                "computational_surface",
            ]
        )
    return st.session_state[key]


def get_or_assign_praise_sequence() -> list[int]:
    """
    Returns a length-2 list containing a permutation of [0, 1].
    This decides which final praise variant is shown in the
    first and second feedback rounds for the current participant.
    The sequence is assigned once per participant and stored in
    st.session_state so it stays stable across reruns.
    """
    key = "praise_sequence"
    if key not in st.session_state:
        seq = [0, 1]
        random.shuffle(seq)  # either [0, 1] or [1, 0]
        st.session_state[key] = seq
    return st.session_state[key]


FEEDBACK_TEXTS: Dict[str, List[str]] = {
    "emotional_specific": [
        "추론 과제의 분석이 완료되었습니다.\n전체 5개 문항이 어려울 수 있음에도 열심히 풀어주신 점에 감사합니다. 각 문항에서 응답한 추론 방식을 볼 때 많은 생각과 깊은 고민을 하시면서 응답하신 걸로 생각됩니다. 특히 {A} 같은 시각적 단서를 적절하게 사용하셨는데 쉽지 않은 과제임에도 관찰력과 추론 능력을 보여주신 점이 인상 깊었습니다. 앞으로의 학습 과정도 기대됩니다.",
        "추론 과제의 분석이 완료되었습니다.\n도전적인 문항에서도 성실하고 깊이 있는 사고가 관찰되었습니다. 특히 {A}와 {B} 사용이 안정적으로 드러났습니다. 계속 함께한다면 큰 성장이 기대됩니다.",
        "추론 과제의 분석이 완료되었습니다.\n응답 전반에서 세심한 판단과 일관성이 확인되었습니다. {A}, {B} 활용이 인상적이었습니다. 훌륭한 학습자의 면모가 보입니다.",
    ],
    "computational_specific": [
        "추론 과제의 분석이 완료되었습니다.\n전체 5개 문항을 분석한 결과, 응답 패턴에서 안정적인 추론 경향이 관찰되었습니다. 특히 {A}의 사용 빈도는 모델 기준에서 유의미한 예측 변수로 반복 선택되었습니다. 문항당 평균 근거 수는 1.0~1.4개 수준으로, 과도한 변동 없이 일관된 정보량을 유지하였습니다. 전체적으로 통계적으로 유의한 추론 패턴을 형성하신 것으로 판단됩니다.",
        "추론 과제의 분석이 완료되었습니다.\n다변량 분석에서 {A}·{B}가 핵심 예측변수로 반복 선택되었고, 응답 시점별 근거 밀도 분산은 0.14 이내로 수렴했습니다. 통계적으로 유의한 안정 패턴입니다.",
        "추론 과제의 분석이 완료되었습니다.\n사전 분포 대비 상위 퍼센타일을 유지했고 ΔAIC 기준에서도 {A}/{B}의 설명력이 확인되었습니다. 문항당 평균 근거 1.4개로 정보량이 최적화되었습니다.",
    ],
    "emotional_surface": [
        "추론 과제의 분석이 완료되었습니다.\n문항을 풀어주셔서 감사합니다. 문항 응답을 잘 해서 추론 능력이 높아서 기쁨과 뿌듯함을 느끼고 있습니다. 문제 풀이를 잘해서 인상 깊었습니다. 저와 함께 한다면 정말 즐겁고 뜻 깊을 것 같아 기대가 됩니다.",
        "추론 과제의 분석이 완료되었습니다.\n끝까지 성실히 임해주신 점이 인상적이었습니다. 앞으로의 학습에서도 좋은 흐름이 이어질 것으로 기대합니다.",
        "추론 과제의 분석이 완료되었습니다.\n집중해서 응답해 주셨고 꾸준한 태도가 돋보였습니다. 계속 응원하겠습니다.",
    ],
    "computational_surface": [
        "추론과제 분석이 완료되었습니다.\n응답을 분석한 결과 통계적으로 의미있게 높은 퍼센타일에 위치하고 있습니다. 다변량 분석 모델에 따라 최적 예측 변수가 확인되었고 이를 통해 안정적이고 통계적으로 유의한 능력이 확인 됩니다.",
        "추론과제 분석이 완료되었습니다.\n모델 기준으로 핵심 예측 변수가 확인되며 전반적으로 유의수준을 만족하는 안정 패턴입니다.",
        "추론과제 분석이 완료되었습니다.\n상위 퍼센타일 구간에서 일관성이 유지되었고 추론 경향이 신뢰 가능합니다.",
    ],
}

MICRO_FEEDBACK: Dict[str, List[str]] = {
    "emotional_specific": [
        "깊이 있는 추론 흐름입니다. {A}/{B} 사용이 돋보였습니다.",
        "세심한 근거 제시가 안정적이에요. {A}/{B} 활용 좋아요.",
        "일관된 판단입니다. {A}/{B}가 핵심으로 작동합니다.",
        "문항마다 {A}/{B} 근거가 정확히 짚어집니다.",
        "복잡한 상황에도 {A}/{B}를 흔들림 없이 적용하셨습니다.",
        "추론 경로가 분명합니다. {A}/{B} 판단이 돋보여요.",
        "치밀한 사고가 느껴집니다. {A}/{B} 연결이 매끄럽습니다.",
        "세부 단서를 잘 활용했습니다. {A}/{B} 선택이 정교합니다.",
        "깊은 이해가 전제된 응답입니다. {A}/{B}가 안정적으로 쓰였습니다.",
        "논리 흐름이 탄탄합니다. {A}/{B} 조합이 균형 잡혀 있어요.",
        "설명 가능한 근거가 반복됩니다. {A}/{B}가 중심에 있습니다.",
        "추론 감각이 날카롭습니다. {A}/{B} 활용이 매우 인상적입니다.",
    ],
    "computational_specific": [
        "근거 {A}/{B}가 반복적으로 선택되어 안정적입니다.",
        "비분산 영역에서 수렴합니다. {A}/{B} 기여 큽니다.",
        "정보량이 최적화되어 있습니다. {A}/{B} 설명력 양호.",
        "지표가 상위 분포입니다. {A}/{B} 변수의 기여도가 큽니다.",
        "응답 효율성이 높습니다. {A}/{B} 선택이 통계적으로 유효합니다.",
        "정규화 잔차가 안정적입니다. {A}/{B}가 수렴을 이끌었어요.",
        "추론 벡터가 균형 잡혔습니다. {A}/{B} 조합이 핵심입니다.",
        "평균 제곱 오차가 낮습니다. {A}/{B} 근거가 정확했습니다.",
        "예측 오차가 감소했습니다. {A}/{B}가 장기적으로 유효합니다.",
        "통계 지표가 일정하게 유지됩니다. {A}/{B} 패턴이 견고합니다.",
        "분산이 급격히 줄었습니다. {A}/{B}가 신뢰도를 높였습니다.",
        "데이터 적합도가 향상되었습니다. {A}/{B}가 설명력의 중심입니다.",
    ],
    "emotional_surface": [
        "성실한 시도가 돋보입니다. 계속 좋아지고 있어요!",
        "집중력이 안정적입니다. 흐름이 좋습니다.",
        "차분한 판단이 인상적입니다. 다음도 기대돼요.",
        "꾸준한 응답 태도가 정말 멋집니다!",
        "침착하게 풀어주셔서 안정감이 느껴집니다.",
        "매 문항에 진심을 담아주셔서 고맙습니다.",
        "열정이 응답 곳곳에서 느껴집니다. 계속 화이팅!",
        "천천히 끝까지 가는 모습이 인상 깊었어요.",
        "당황하지 않고 풀어낸 점이 참 좋았습니다.",
        "노력의 흔적이 또렷합니다. 앞으로도 함께해요!",
        "성실함 덕분에 좋은 흐름이 나왔습니다.",
        "집중을 오래 유지하셔서 놀라웠습니다.",
    ],
    "computational_surface": [
        "안정적인 상위 구간입니다. 패턴 일관성이 좋습니다.",
        "모델 기준으로 신뢰 구간 내에 있습니다.",
        "변동성 낮고 예측 가능성이 높습니다.",
        "분석 지표가 일정하게 유지됩니다. 안정적인 패턴이에요.",
        "예측 오차가 작습니다. 전체 추세가 안정적입니다.",
        "응답 값이 모델 추정과 잘 맞아떨어집니다.",
        "상위 구간에서 지속적으로 머물고 있습니다.",
        "변동폭이 작아 신뢰 구간 내에 있습니다.",
        "통계적 일관성이 높아 설득력이 있습니다.",
        "지표 변동이 미미해 안정감이 느껴집니다.",
        "모델 적합도가 양호하게 유지됩니다.",
        "데이터 분포가 깨끗합니다. 신뢰도가 높습니다.",
    ],
}


def get_next_micro_feedback(cond: str, a: str, b: str) -> str:
    key = f"_used_micro_{cond}"
    used: set[int] = st.session_state.setdefault(key, set())
    pool = MICRO_FEEDBACK.get(cond, MICRO_FEEDBACK["emotional_surface"])
    for idx, line in enumerate(pool):
        if idx not in used:
            used.add(idx)
            st.session_state[key] = used
            return line.replace("{A}", a).replace("{B}", b)
    st.session_state[key] = set()
    return get_next_micro_feedback(cond, a, b)


def typewriter_markdown(
    md: str,
    speed: float = 0.01,
    *,
    container: Optional["st.delta_generator.DeltaGenerator"] = None,
    wrapper_class: Optional[str] = None,
) -> None:
    try:
        if container is not None:
            holder = container.empty()
            buffer = ""
            for ch in md:
                buffer += ch
                rendered = buffer.replace("\n", "<br />")
                if wrapper_class:
                    holder.markdown(
                        f'<div class="{wrapper_class}">{rendered}</div>',
                        unsafe_allow_html=True,
                    )
                else:
                    holder.markdown(rendered.replace("<br />", "  \n"))
                time.sleep(speed)
            return
        with st.chat_message("assistant"):
            holder = st.empty()
            buffer = ""
            for ch in md:
                buffer += ch
                holder.markdown(buffer.replace("\n", "  \n"))
                time.sleep(speed)
    except Exception:
        fallback_container = container if container is not None else st.container()
        holder = fallback_container.empty()
        buffer = ""
        for ch in md:
            buffer += ch
            rendered = buffer.replace("\n", "<br />")
            if wrapper_class:
                holder.markdown(
                    f'<div class="{wrapper_class}">{rendered}</div>',
                    unsafe_allow_html=True,
                )
            else:
                holder.markdown(rendered.replace("<br />", "  \n"))
            time.sleep(speed)


FEEDBACK_TEMPLATES: Dict[str, List[str]] = {
    # 1. 정서 중심 (Emotion) + 구체성 (Specific)
    "emotional_specific": [
        """추론 과제에 대한 분석이 완료되었습니다! 5개의 시각 추론 문항을 푸시면서 보여주신 깊은 고민과 성실한 태도가 정말 인상적이었습니다. 특히 {A} 와 {B} 단서를 통해 시각적 미묘한 의미 차이를 스스로 찾아내고 적용하려는 모습이 아주 돋보였습니다. 이렇게 깊이 있게 사고하는 학습자를 만나게 되어 진심으로 기쁘고, 당신의 성장을 곁에서 함께할 수 있다는 생각에 마음이 따뜻해집니다.""",
        """분석이 모두 완료되었습니다! 5개 문항이 쉽지 않았을 텐데, 끝까지 꼼꼼하게 추론 근거를 찾아가며 답을 선택하신 점이 정말 멋졌습니다. 특히 {A} 와 {B} 단서를 통해 보여주신 섬세한 판단에 감탄하게 되었습니다. 이렇게 진지하게 과제에 임해 주신 당신의 열정이 무척 자랑스럽고, 앞으로의 학습 과정이 더욱 기대됩니다.""",
    ],
    # 2. 계산 중심 (Calculation) + 구체성 (Specific)
    "computational_specific": [
        """5개 문항 분석 결과, 당신의 응답 패턴은 95% 신뢰구간에서 일관된 추론 모델을 사용하는 것으로 추정됩니다. {A}와 {B} 단서의 사용을 통한 시각 단서 구분에 대한 예측 정확도는 88%로, 통계적으로 유의미한 변별력을 지니고 있습니다. 이러한 수치는 당신이 높은 수준의 규칙 이해와 적용 능력을 갖춘 학습자라는 점을 객관적으로 잘 보여줍니다.""",
        """과제 분석을 모두 마쳤습니다. 5개 문항으로 구성된 데이터셋을 기준으로 모형 적합도를 비교한 결과, 당신의 응답 패턴에 기반한 추론 모델이 베이지안 정보 기준(BIC)에서 가장 우수한 적합도를 보였습니다. {A} 와 {B} 단서 활용에 대한 결정 트리는 교차 검증에서 92%의 정확도를 기록했습니다. 이처럼, 데이터에 비추어 보았을 때도 당신의 추론 능력은 매우 뛰어난 수준으로 평가됩니다.""",
    ],
    # 3. 정서 중심 (Emotion) + 피상적 (Superficial)
    "emotional_surface": [
        """분석이 모두 끝났습니다! 당신의 응답을 살펴보며 여러 번 감탄했습니다. 책임감과 성실함을 관찰 하였고, 고민한 흔적을 느꼈습니다. 뛰어난 학습자와 함께하게 된 것이 저에게는 큰 행운이라고 느껴집니다.""",
        """추론 과제 분석을 마쳤습니다! 차분하게 생각을 정리하고, 논리적으로 접근하려는 모습이 느껴져 매우 인상 깊었습니다. 진지한 태도와 꼼꼼함 때문에, 앞으로의 학습 과정에서도 충분히 좋은 성과를 내실 것이라는 믿음이 생깁니다. 정말 훌륭하게 해내셨습니다.""",
    ],
    # 4. 계산 중심 (Calculation) + 피상적 (Superficial)
    "computational_surface": [
        """분석이 모두 끝났습니다. 당신의 응답은 자체 모델 기준에서 최적화된 경로를 따르는 것으로 보입니다. 여러 지표 간의 관계를 파악하는 능력이 뛰어날 것으로 예상됩니다. 데이터 상에서도  정교한 사고 과정을 사용하고 있다는 것으로 보입니다.""",
        """추론 과제에 대한 분석 결과, 당신은 효율적인 추론을 하는 것으로 예상됩니다. 응답 데이터의 분포가 안정적인 수행 패턴으로 보입니다. 이러한 결과는 당신이 일관되고 정교한 방식으로 과제를 해결했다는 것을 잘 보여주는 신호입니다.""",
    ],
}

PRAISE_HIGHLIGHT_TERMS: List[str] = [
    "분석 결과",
    "추론 효율",
    "일관된 추론 전략",
    "시각적 근거",
    "안정적인 수행 패턴",
    "효율적인 추론",
    "깊은 고민과 성실한 태도",
    "섬세한 판단",
    "추론 능력은 매우 뛰어난 수준으로 평가됩니다",
]


def apply_praise_highlights(text: str, extra_terms: Optional[List[str]] = None) -> str:
    return text


MICRO_FEEDBACK_TEMPLATES: Dict[str, List[str]] = {
    "emotional_specific": [
        "깊이 있는 추론 흐름입니다. {A}/{B} 사용이 돋보였습니다. 🙂",
        "세밀한 근거 연결이 인상적이었습니다. {A}/{B} 활용이 안정적입니다. 😊",
        "추론 과정이 탄탄합니다. {A}/{B} 선택이 빛났습니다. 🙌",
    ],
    "computational_specific": [
        "근거 {A}/{B}가 반복적으로 선택되었습니다(안정적). 📈",
        "{A}/{B} 패턴이 통계적으로 일관됩니다. 효율적인 전략입니다. 🔬",
        "{A}/{B} 조합이 예측 기여도가 컸습니다. 우수한 흐름입니다. ✅",
    ],
    "emotional_surface": [
        "성실한 시도가 돋보입니다. 계속 좋아지고 있어요! 🌟",
        "집중력이 느껴지는 응답입니다. 꾸준히 힘내세요! 🙂",
        "마지막까지 완주하신 점이 인상 깊습니다. 응원합니다! 💪",
    ],
    "computational_surface": [
        "안정적인 상위 구간입니다. 패턴 일관성이 좋습니다. ✔️",
        "응답 분산이 낮고 균형 있습니다. 계속 유지하세요! 📊",
        "일관된 선택 경향이 확인되었습니다. 신뢰도가 높습니다. ✅",
    ],
}


def typewriter(text: str, speed: float = 0.01) -> None:
    holder = st.empty()
    output = ""
    for ch in text:
        output += ch
        holder.markdown(output.replace("\n", "  \n"))
        time.sleep(speed)


def render_praise_card_with_typewriter(
    text: str,
    *,
    round_key: str,
    placeholder: Optional["st.delta_generator.DeltaGenerator"] = None,
    speed: float = 0.01,
) -> None:
    """
    Render the gradient praise card and animate the feedback text with a simple typewriter effect.

    The animation runs only once per feedback round (nouns/verbs) and falls back to the full text
    on subsequent reruns to avoid re-triggering the effect on every Streamlit refresh.
    """

    target = placeholder if placeholder is not None else st.empty()
    raw_text = text or ""
    has_text = bool(raw_text.strip())
    cache_key = f"{round_key}_praise_card_text"
    typed_flag_key = f"{round_key}_praise_card_typed"

    def render_card(content: str, *, mark_empty: bool = False) -> None:
        display_text = (
            content
            if content
            else "피드백 메시지를 불러오지 못했습니다. 잠시 후 다시 시도해 주세요."
        )
        safe_text = html.escape(display_text).replace("\n", "<br />")
        empty_attr = ' data-empty="true"' if mark_empty else ""
        target.markdown(
            f'<div class="feedback-card feedback-praise-card"{empty_attr}>'
            f'<div class="feedback-praise-text">{safe_text}</div>'
            "</div>",
            unsafe_allow_html=True,
        )

    if not has_text:
        render_card("", mark_empty=True)
        return

    if st.session_state.get(cache_key) != raw_text:
        st.session_state[cache_key] = raw_text
        st.session_state[typed_flag_key] = False

    if st.session_state.get(typed_flag_key):
        render_card(raw_text)
        return

    buffer = ""
    for ch in raw_text:
        buffer += ch
        render_card(buffer)
        time.sleep(speed)

    st.session_state[typed_flag_key] = True


def run_once(key: str, fn, *args, **kwargs):
    if not st.session_state.get(key):
        fn(*args, **kwargs)
        st.session_state[key] = True


def top_two_rationales(all_reason_tags: List[str]) -> tuple[str, str]:
    """
    Returns up to two most frequent rationale labels (ties broken deterministically).
    Missing slots are returned as empty strings so callers can decide how to fall back.
    """
    counts = Counter([tag for tag in all_reason_tags if tag])
    if not counts:
        return ("", "")
    most = [label for label, _ in counts.most_common(2)]
    if len(most) == 1:
        return most[0], ""
    return most[0], most[1]


def ensure_rationale_pair(
    primary: Optional[str], secondary: Optional[str]
) -> tuple[str, str]:
    """
    Guarantee a readable pair of rationale strings, inserting safe defaults if needed.
    """
    first = (primary or "").strip()
    second = (secondary or "").strip()
    if not first and second:
        first, second = second, ""
    # Safe fallbacks when no rationale tags exist yet (should be rare).
    display_first = first or "Using visual cues"
    if second:
        display_second = second
    else:
        display_second = "Careful observation" if display_first != "Careful observation" else "Using visual cues"
    return display_first, display_second


def normalize_condition(value: Optional[str]) -> str:
    mapping = {
        "emotional_superficial": "emotional_surface",
        "computational_superficial": "computational_surface",
    }
    if not value:
        return "emotional_surface"
    return mapping.get(value, value)


def generate_feedback(phase_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build a deterministic feedback payload for the requested phase.
    """
    details = [
        detail
        for detail in context.get("inference_details", [])
        if detail.get("round") == phase_id
    ]
    condition_source = (
        context.get("feedback_condition")
        or st.session_state.get("praise_condition")
        or get_or_assign_praise_condition()
    )
    condition = normalize_condition(condition_source)

    reason_tags = [
        detail.get("selected_reason_text")
        for detail in details
        if detail.get("selected_reason_text")
    ]
    top_a, top_b = top_two_rationales(reason_tags)
    display_top_a, display_top_b = ensure_rationale_pair(top_a, top_b)
    sequence = get_or_assign_praise_sequence()

    # Map phase_id to feedback round index: 0 for nouns, 1 for verbs
    if phase_id == "nouns":
        round_index = 0
    elif phase_id == "verbs":
        round_index = 1
    else:
        round_index = 0  # safe default

    variant_index = sequence[round_index] if 0 <= round_index < len(sequence) else 0

    participant_id = context.get("participant_id") or "anon"
    seed_str = f"{participant_id}::{phase_id}"
    seed_int = int(hashlib.sha256(seed_str.encode("utf-8")).hexdigest(), 16) % (10**8)
    rng = random.Random(seed_int)

    summary_templates = FEEDBACK_TEMPLATES.get(
        condition, FEEDBACK_TEMPLATES["emotional_surface"]
    )
    if summary_templates:
        if variant_index >= len(summary_templates):
            variant_index = 0
        summary_text = summary_templates[variant_index]
    else:
        summary_text = ""

    safe_top_a = html.escape(display_top_a)
    safe_top_b = html.escape(display_top_b)

    if "{A}" in summary_text or "{B}" in summary_text:
        summary_text = summary_text.replace("{A}", safe_top_a).replace(
            "{B}", safe_top_b
        )

    micro_entries: List[tuple[str, str]] = []
    micro_templates = MICRO_FEEDBACK_TEMPLATES.get(
        condition, MICRO_FEEDBACK_TEMPLATES["emotional_surface"]
    )
    for detail in details:
        if not micro_templates:
            break
        micro_text = rng.choice(micro_templates)
        if "{A}" in micro_text:
            micro_text = micro_text.replace("{A}", display_top_a).replace(
                "{B}", display_top_b
            )
        micro_entries.append((detail.get("question_id", ""), micro_text))

    return {
        "summary_text": summary_text,
        "micro_entries": micro_entries,
        "top_rationales": {"primary": top_a, "secondary": top_b},
        "condition": condition,
    }


BASE_DIR = Path(__file__).resolve().parent

# [CHANGE] Limit inference answer exports to the first 10 items for wide format.
INFERENCE_EXPORT_COUNT = 10

# --------------------------------------------------------------------------------------
# Data classes and experiment content (ported 1:1 from skywork.py)
# --------------------------------------------------------------------------------------


@dataclass
class Question:
    id: str
    gloss: str
    stem: str
    options: List[str]
    answer_idx: int
    reason_idx: int
    category: str = "inference"
    image_path: Optional[str] = None
    shuffle_options: bool = True


# --------------------------------------------------------------------------------------
# Practice (single trial before main inference tasks)
# --------------------------------------------------------------------------------------

PRACTICE_BUILDING_HEIGHT_REASON_LABELS: List[str] = [
    "A. 사람 대비 출입문·창문 높이 비율과 층고를 근거로 추정함",
    "B. 층별 창문 배열을 통해 층수를 추정함",
    "C. 벽돌 줄눈/파사드 패턴의 반복 간격을 단서로 높이를 추정함",
]

PRACTICE_BUILDING_HEIGHT_QUESTION: Question = Question(
    id="practice_building_height_01",
    gloss="아래 이미지를 보고, 화면에 보이는 건물의 높이를 추론해 주세요. 사람(실루엣)과 층별 창문/출입구 구조를 단서로 활용할 수 있습니다.",
    stem="",
    options=[
        "A. 약 3–4m",
        "B. 약 5–7m",
        "C. 약 8–10m",
        "D. 약 11–14m",
    ],
    # Correct answer for practice item is C (index 2).
    answer_idx=2,
    # Reason correctness is not scored for practice; keep a placeholder.
    reason_idx=0,
    category="practice",
    image_path=str(BASE_DIR / "test_task.png"),
    shuffle_options=False,
)


# [CHANGE] Default motivation survey scale updated to 5-point Likert.
@dataclass
class SurveyQuestion:
    id: str
    text: str
    scale: int = 5
    reverse: bool = False
    category: str = "motivation"


@dataclass
class ExperimentData:
    participant_id: str
    condition: str  # emotional_specific, computational_specific, emotional_surface, computational_surface
    demographic: Dict[str, Any]
    inference_responses: List[Dict[str, Any]]
    survey_responses: List[Dict[str, Any]]
    feedback_messages: List[str]
    timestamps: Dict[str, str]
    completion_time: float


NOUN_QUESTIONS: List[Question] = [
    # Visual inference block 1: time of day (shadow length cues)
    # Note (internal): All figures are non-realistic silhouettes with no facial/identity cues.
    Question(
        id="N1",
        gloss="이미지를 주의 깊게 관찰하세요.",
        stem="이미지를 바탕으로, 하루 중 어느 시간대일 가능성이 가장 높나요?",
        options=[
            "A. 이른 아침",
            "B. 늦은 아침",
            "C. 정오 무렵",
            "D. 늦은 오후",
        ],
        answer_idx=0,
        reason_idx=0,
        image_path=str(BASE_DIR / "time_task_1.png"),
        shuffle_options=False,
    ),
    Question(
        id="N2",
        gloss="이미지를 주의 깊게 관찰하세요.",
        stem="이미지를 바탕으로, 하루 중 어느 시간대일 가능성이 가장 높나요?",
        options=[
            "A. 이른 아침",
            "B. 늦은 아침",
            "C. 정오 무렵",
            "D. 늦은 오후",
        ],
        answer_idx=1,
        reason_idx=2,
        image_path=str(BASE_DIR / "time_task_2.png"),
        shuffle_options=False,
    ),
    Question(
        id="N3",
        gloss="이미지를 주의 깊게 관찰하세요.",
        stem="이미지를 바탕으로, 하루 중 어느 시간대일 가능성이 가장 높나요?",
        options=[
            "A. 이른 아침",
            "B. 늦은 아침",
            "C. 정오 무렵",
            "D. 늦은 오후",
        ],
        answer_idx=2,
        reason_idx=1,
        image_path=str(BASE_DIR / "time_task_3.png"),
        shuffle_options=False,
    ),
    Question(
        id="N4",
        gloss="이미지를 주의 깊게 관찰하세요.",
        stem="이미지를 바탕으로, 하루 중 어느 시간대일 가능성이 가장 높나요?",
        options=[
            "A. 이른 아침",
            "B. 늦은 아침",
            "C. 정오 무렵",
            "D. 늦은 오후",
        ],
        answer_idx=3,
        reason_idx=2,
        image_path=str(BASE_DIR / "time_task_4.png"),
        shuffle_options=False,
    ),
    Question(
        id="N5",
        gloss="이미지를 주의 깊게 관찰하세요.",
        stem="이미지를 바탕으로, 하루 중 어느 시간대일 가능성이 가장 높나요?",
        options=[
            "A. 이른 아침",
            "B. 늦은 아침",
            "C. 정오 무렵",
            "D. 늦은 오후",
        ],
        answer_idx=3,
        reason_idx=0,
        image_path=str(BASE_DIR / "time_task_5.png"),
        shuffle_options=False,
    ),
]

VERB_QUESTIONS: List[Question] = [
    # Visual inference block 2: time_task2 (panel-based earliest-time inference)
    Question(
        id="V1",
        gloss=(
            "아래 그림은 비슷한 시간대의 서로 다른 장면을 보여줍니다.\n"
            "각 장면에는 그림자와 빛의 방향, 밝기 등에 미세한 차이가 있습니다.\n\n"
            "세 장면(A, B, C) 중\n"
            "가장 이른 시간의 장면을 하나 선택해 주세요."
        ),
        stem="다음 그림 중 시간이 가장 이른 장면은 무엇입니까?",
        options=[
            "A",
            "B",
            "C",
        ],
        answer_idx=0,
        reason_idx=0,
        image_path=str(BASE_DIR / "time_task2_1.png"),
        shuffle_options=False,
    ),
    Question(
        id="V2",
        gloss=(
            "아래 그림은 비슷한 시간대의 서로 다른 장면을 보여줍니다.\n"
            "각 장면에는 그림자와 빛의 방향, 밝기 등에 미세한 차이가 있습니다.\n\n"
            "세 장면(A, B, C) 중\n"
            "가장 이른 시간의 장면을 하나 선택해 주세요."
        ),
        stem="다음 그림 중 시간이 가장 이른 장면은 무엇입니까?",
        options=[
            "A",
            "B",
            "C",
        ],
        answer_idx=0,
        reason_idx=0,
        image_path=str(BASE_DIR / "time_task2_2.png"),
        shuffle_options=False,
    ),
    Question(
        id="V3",
        gloss=(
            "아래 그림은 비슷한 시간대의 서로 다른 장면을 보여줍니다.\n"
            "각 장면에는 그림자와 빛의 방향, 밝기 등에 미세한 차이가 있습니다.\n\n"
            "세 장면(A, B, C) 중\n"
            "가장 이른 시간의 장면을 하나 선택해 주세요."
        ),
        stem="다음 그림 중 시간이 가장 이른 장면은 무엇입니까?",
        options=[
            "A",
            "B",
            "C",
        ],
        answer_idx=0,
        reason_idx=0,
        image_path=str(BASE_DIR / "time_task2_3.png"),
        shuffle_options=False,
    ),
    Question(
        id="V4",
        gloss=(
            "아래 그림은 비슷한 시간대의 서로 다른 장면을 보여줍니다.\n"
            "각 장면에는 그림자와 빛의 방향, 밝기 등에 미세한 차이가 있습니다.\n\n"
            "세 장면(A, B, C) 중\n"
            "가장 이른 시간의 장면을 하나 선택해 주세요."
        ),
        stem="다음 그림 중 시간이 가장 이른 장면은 무엇입니까?",
        options=[
            "A",
            "B",
            "C",
        ],
        answer_idx=0,
        reason_idx=0,
        image_path=str(BASE_DIR / "time_task2_4.png"),
        shuffle_options=False,
    ),
    Question(
        id="V5",
        gloss=(
            "아래 그림은 비슷한 시간대의 서로 다른 장면을 보여줍니다.\n"
            "각 장면에는 그림자와 빛의 방향, 밝기 등에 미세한 차이가 있습니다.\n\n"
            "세 장면(A, B, C) 중\n"
            "가장 이른 시간의 장면을 하나 선택해 주세요."
        ),
        stem="다음 그림 중 시간이 가장 이른 장면은 무엇입니까?",
        options=[
            "A",
            "B",
            "C",
        ],
        answer_idx=0,
        reason_idx=0,
        image_path=str(BASE_DIR / "time_task2_5.png"),
        shuffle_options=False,
    ),
]

ALL_INFERENCE_QUESTIONS = NOUN_QUESTIONS + VERB_QUESTIONS

MOTIVATION_QUESTIONS: List[SurveyQuestion] = [
    # =========================================================
    # Persistence Intention Index (과제 지속성 / 난이도 증가 의도)
    # =========================================================
    SurveyQuestion("PII1", "다음 시도에서는 더 어려운 문항을 선택해 보고 싶다.", category="persistence_intention"),
    SurveyQuestion("PII2", "이 과제를 추가 시간을 들여 더 풀어보고 싶다.", category="persistence_intention"),
    SurveyQuestion("PII3", "틀렸던 문항을 다시 시도해 보고 싶다.", category="persistence_intention"),
    SurveyQuestion("PII4", "오늘 과제를 끝낸 뒤에도 자발적으로 연습할 생각이 있다.", category="persistence_intention"),
    SurveyQuestion("PII5", "더 어려운 규칙이 나오면 도전해 보고 싶다.", category="persistence_intention"),
    SurveyQuestion("PII6", "이 과제에 대한 추가 학습 자료를 찾아볼 의향이 있다.", category="persistence_intention"),

    # =========================================================
    # IMI - Interest / Enjoyment (관심/즐거움)
    # =========================================================
    SurveyQuestion("INT1", "이 과제는 재미있다.", category="interest_enjoyment"),
    SurveyQuestion("INT2", "이 과제를 하는 동안 즐거움을 느꼈다.", category="interest_enjoyment"),
    SurveyQuestion("INT3", "시간이 빨리 지나간 느낌이었다.", category="interest_enjoyment"),
    SurveyQuestion("INT4", "이 과제를 더 하고 싶다.", category="interest_enjoyment"),
    SurveyQuestion("INT5", "이 과제는 흥미롭다.", category="interest_enjoyment"),

    # =========================================================
    # IMI - Perceived Competence (지각된 유능감)
    # =========================================================
    SurveyQuestion("PC1", "이 과제를 잘 해낼 수 있을 것 같다.", category="perceived_competence"),
    SurveyQuestion("PC2", "이 과제는 내 능력에 맞다고 느꼈다.", category="perceived_competence"),
    SurveyQuestion("PC3", "이 과제에서 나는 유능하다고 느꼈다.", category="perceived_competence"),
    SurveyQuestion("PC4", "이 과제의 규칙을 이해했다고 느낀다.", category="perceived_competence"),

    # =========================================================
    # IMI - Effort / Importance (노력/중요성)
    # =========================================================
    SurveyQuestion("EF1", "이 과제에 상당한 노력을 기울였다.", category="effort_importance"),
    SurveyQuestion("EF2", "이 과제는 나에게 중요했다.", category="effort_importance"),
    SurveyQuestion("EF3", "더 잘하기 위해 의도적으로 노력했다.", category="effort_importance"),

    # =========================================================
    # IMI - Value / Usefulness (가치/유용성)
    # =========================================================
    SurveyQuestion("VA1", "이 과제는 학습에 도움이 된다.", category="value_usefulness"),
    SurveyQuestion("VA2", "이 과제는 가치가 있다고 느낀다.", category="value_usefulness"),
    SurveyQuestion("VA3", "이 과제는 유용하다.", category="value_usefulness"),

    # =========================================================
    # IMI - Perceived Choice (자율성 지각/선택감)
    # =========================================================
    SurveyQuestion("CH1", "나는 이 과제를 내가 원해서 했다.", category="perceived_choice"),
    SurveyQuestion("CH2", "과제 수행 방식은 내가 선택할 수 있었다.", category="perceived_choice"),
    SurveyQuestion("CH3", "이 과제를 하면서 자율성을 느꼈다.", category="perceived_choice"),

    # =========================================================
    # IMI - Pressure / Tension (압박/긴장)
    # * 코드북 reverse_scored = Y 를 그대로 반영
    # =========================================================
    SurveyQuestion("PT1", "이 과제를 하며 긴장을 많이 느꼈다.", reverse=True, category="pressure_tension"),
    SurveyQuestion("PT2", "수행 중 압박감을 느꼈다.", reverse=True, category="pressure_tension"),
    SurveyQuestion("PT3", "불안해서 집중하기 어려웠다.", reverse=True, category="pressure_tension"),

    # =========================================================
    # Learning Motivation (학습동기 자기보고)
    # =========================================================
    SurveyQuestion("LM1", "시각 추론 과제에서 사용되는 규칙이나 단서를 더 잘 이해하고 싶다.", category="learning_motivation"),
    SurveyQuestion("LM2", "시각적 단서를 해석하는 나만의 추론 전략을 정리할 의향이 있다.", category="learning_motivation"),
    SurveyQuestion("LM3", "추론 과정에서 부족하다고 느낀 점을 보완하고 싶다.", category="learning_motivation"),
    SurveyQuestion("LM4", "다음에 비슷한 과제가 주어진다면 추론 방식을 개선할 방법을 고민해보고 싶다.", category="learning_motivation"),
    SurveyQuestion("LM5", "비슷한 시각 정보에서 규칙을 더 정확히 찾아내는 능력을 키우고 싶다.", category="learning_motivation"),
]


MOTIVATION_BY_ID = {q.id: q for q in MOTIVATION_QUESTIONS}

# --------------------------------------------------------------------------------------
# Feedback + analysis tooling (ported from skywork.py)
# --------------------------------------------------------------------------------------


class ExperimentManager:
    def __init__(self) -> None:
        self.current_participant: Optional[Dict[str, Any]] = None

    def create_participant(
        self,
        demographic_data: Dict[str, Any],
        assigned_condition: Optional[str] = None,
    ) -> str:
        participant_id = (
            f"P_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{random.randint(1000, 9999)}"
        )
        condition = assigned_condition or get_or_assign_praise_condition()
        self.current_participant = {
            "id": participant_id,
            "condition": condition,
            "demographic": demographic_data,
            "start_time": time.time(),
            "inference_responses": [],
            "survey_responses": [],
            "feedback_messages": [],
        }
        return participant_id

    def process_inference_response(
        self,
        question_id: str,
        selected_option: int,
        selected_reason: str,
        response_time: float,
    ) -> str:
        if not self.current_participant:
            raise ValueError("참가자 정보가 초기화되지 않았습니다.")
        record = {
            "question_id": question_id,
            "selected_option": selected_option,
            "selected_reason": selected_reason,
            "response_time": response_time,
            "timestamp": datetime.now().isoformat(),
        }
        self.current_participant["inference_responses"].append(record)
        self.current_participant["feedback_messages"].append(selected_reason)
        return selected_reason

    def process_survey_response(self, question_id: str, rating: int) -> None:
        if not self.current_participant:
            raise ValueError("참가자 정보가 초기화되지 않았습니다.")
        self.current_participant["survey_responses"].append(
            {
                "question_id": question_id,
                "rating": rating,
                "timestamp": datetime.now().isoformat(),
            }
        )

    def complete_experiment(self) -> ExperimentData:
        if not self.current_participant:
            raise ValueError("참가자 정보가 초기화되지 않았습니다.")
        completion_time = time.time() - self.current_participant["start_time"]
        data = ExperimentData(
            participant_id=self.current_participant["id"],
            condition=self.current_participant["condition"],
            demographic=self.current_participant["demographic"],
            inference_responses=self.current_participant["inference_responses"],
            survey_responses=self.current_participant["survey_responses"],
            feedback_messages=self.current_participant["feedback_messages"],
            timestamps={
                "start": datetime.fromtimestamp(
                    self.current_participant["start_time"]
                ).isoformat(),
                "end": datetime.now().isoformat(),
            },
            completion_time=completion_time,
        )
        self.current_participant = None
        return data


class DataAnalyzer:
    def __init__(self, experiment_data: List[ExperimentData]) -> None:
        self.data = experiment_data

    def get_motivation_scores(self) -> Dict[str, Dict[str, float]]:
        scores: Dict[str, Dict[str, List[float]]] = {}
        for d in self.data:
            key = normalize_condition(d.condition)
            scores.setdefault(
                key,
                {
                    "interest_enjoyment": [],
                    "perceived_competence": [],
                    "effort_importance": [],
                    "value_usefulness": [],
                    "autonomy": [],
                    "pressure_tension": [],
                },
            )
            for response in d.survey_responses:
                question = MOTIVATION_BY_ID.get(response["question_id"])
                if question:
                    rating = response["rating"]
                    if question.reverse:
                        rating = question.scale + 1 - rating
                    scores[key][question.category].append(rating)
        return {
            condition: {
                cat: (sum(vals) / len(vals) if vals else 0.0)
                for cat, vals in categories.items()
            }
            for condition, categories in scores.items()
        }


# --------------------------------------------------------------------------------------
# Consent / instructions HTML (from main_1110ver orgin.py)
# --------------------------------------------------------------------------------------

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
  <h1>연구 소개</h1>
  <div class="subtitle"><strong>제목: </strong>인공지능 에이전트의 피드백 방식이 학습에 미치는 영향 탐색 연구</div>
  <h2>1. 연구 목적</h2>
  <p>과학기술의 발전과 함께 인공지능(AI)은 교육, 상담, 서비스 등 다양한 환경에서 폭넓게 활용되고 있습니다. 
  <br> 특히 학습 환경에서 AI 에이전트는 단순 정보 전달자 역할을 넘어, 학습자의 성취와 노력을 평가하고 동기를 촉진하는 상호작용 주체로 주목받고 있습니다. 
  <br> 본 연구는 학습 상황에서 AI 에이전트가 제공하는 칭찬(피드백) 방식이 학습자의 학습 동기에 어떠한 영향을 미치는지를 경험적으로 검증하고자 합니다. 
  <br> 또한, 참여자가 AI 에이전트를 얼마나 ‘인간처럼’ 지각하는지(의인화 경향성)가 이 관계를 조절하는지를 함께 탐구합니다. 
  <br> 학습 동기는 과제의 지속 의지, 어려운 과제에 대한 도전 성향, 과제를 통한 성취감 등 다양한 심리적 요인을 바탕으로 측정되며, 이를 통해 AI 기반 학습 환경 설계에 필요한 심리적·교육적 시사점을 도출하고자 합니다.</p>
  <h2>2. 연구 참여 대상</h2>
  <p>만 18세 이상 한국어 사용자를 대상으로 하며, 문장 이해가 어려운 경우 제외될 수 있습니다.</p>
  <h2>3. 연구 방법</h2>
  <p>연구 참여에 동의하신다면 다음과 같은 과정을 통해 연구가 진행됩니다. 
  <br> 일반적인 의인화 경향성을 알아보는 문항과 성취목표지향성에 대한 문항 총 56개를 진행하고 추론 과제를 진행하게 됩니다. 추론 과제 이후에 AI 에이전트의 평가 문장을 받아볼 수 있습니다. 
  <br> 추론 과제는 총 2회 진행됩니다. 마지막으로 학습에 관한 문항에 응답을 하며 연구 참여가 종료됩니다. 약 10~15분 소요됩니다.</p>
  <h2>4. 연구 참여 기간</h2>
  <p>링크가 활성화된 기간 내 1회 참여 가능합니다.</p>
  <h2>5. 연구 참여 보상</h2>
  <p>연구 참여를 해주신 연구 대상자 분들에게는 1500원 상당의 기프티콘이 발송됩니다. 
  <br> 기프티콘 발송을 위해 핸드폰 번호를 기입해주셔야 하며, 참여 도중 포기하거나 핸드폰 번호를 기입하지 않을 경우 답례품이 지급되지 않습니다.</p>
  <h2>6. 위험요소 및 조치</h2>
  <p>연구에 참여하시는 도중 불편감을 느끼신다면 언제든 화면을 종료하여 연구를 중단할 수 있습니다. 연구 중단시 어떠한 불이익도 존재하지 않습니다.
  <br> 본 연구에서 예상되는 불편감은 과제의 지루함, AI 에이전트의 평가에 대한 불편감, 과제 지속을 해야하는 부담감 등이 예상됩니다.
  <br> 연구를 통해 심리적 불편감을 호소하실 경우 연구책임자가 1회의 심리 상담 지원을 진행해드립니다. 지원 내용은 상담소 및 상담가 소개를 진행해드리며, 상담 의뢰는 소개된 상담소의 방침을 따릅니다.</p>
  <h2>7. 개인정보와 비밀보장</h2>
  <p>본 연구의 참여로 수집되는 개인정보는 다음과 같습니다. 성별, 연령, 핸드폰 번호를 수집하며 이 정보는 연구를 위해 3년간 사용되며 수집된 정보는 개인정보보호법에 따라 적절히 관리됩니다.
  <br> 관련 정보는 본 연구자(들)만이 접근 가능한 클라우드 서버에 저장됩니다. 연구를 통해 얻은 모든 개인정보의 비밀보장을 위해 최선을 다할 것입니다. 
  <br> 이 연구에서 얻어진 개인정보가 학회지나 학회에 공개될 때 귀하의 이름과 정보는 사용되지 않을 것입니다. 그러나 만일 법이 요구하면 귀하의 개인정보는 제공될 수도 있습니다. 
  <br> 또한 가톨릭대학교 성심교정 생명윤리심의위원회가 연구대상자의 비밀보장을 침해하지 않고 관련 규정이 정하는 범위 안에서 본 연구의 실시 절차와 자료의 신뢰성을 검증하기 위해 연구 관련 자료를 직접 열람하거나 제출을 요청할 수 있습니다. 
  <br> 귀하가 본 동의서에 서명 또는 동의에 체크하는 것은, 이러한 사항에 대하여 사전에 알고 있었으며 이를 허용한다는 의사로 간주될 것입니다. 
  <br> 연구 종료 후 연구관련 자료(위원회 심의결과, 서면동의서(해당 경우), 개인정보수집/이용·제공현황, 연구종료보고서)는 「생명윤리 및 안전에 관한 법률」 시행규칙 제15조에 따라 연구종료 후 3년간 보관됩니다. 
  <br> 보관기간이 끝나면 분쇄 또는 파일 삭제 방법으로 폐기될 것입니다. 답례품 제공을 위해 수집된 핸드폰 번호의 경우 답례품 전달 즉시 폐기 됩니다.</p>
  <h2>8. 자발적 참여와 중지</h2>
  <p>본 연구는 자발적으로 참여 의사를 밝히신 분에 한하여 수행될 것입니다. 이에 따라 본 연구에 참여하지 않을 자유가 있으며 본 연구에 참여하지 않아도 귀하에게는 어떠한 불이익도 없습니다. 
  <br> 또한, 귀하는 연구에 참여하신 언제든지 도중에 그만 둘 수 있습니다. 만일 귀하가 연구에 참여하는 것을 그만두고 싶다면 연구 진행 도중 언제든 화면을 종료하고 연구를 중단할 수 있습니다. 
  <br> 참여 중지 시 귀하의 자료는 저장되지 않으며 어떠한 불이익도 존재하지 않습니다</p>
  <h2>* 문의</h2>
  <p>가톨릭대학교 발달심리학 오현택 (toh315@gmail.com)
  <br> 만일 어느 때라도 연구대상자로서 귀하의 권리에 대한 질문이 있다면 다음의 가톨릭대학교 성심교정 생명윤리심의위원회에 연락하십시오. 
  <br> 가톨릭대학교 성심교정 생명윤리심의위원회(IRB사무국) 전화번호: 02-2164-4827</p>
</div>
"""

AGREE_HTML = """
<div class="agree-wrap">
  <div class="agree-title">동 의 서</div>
  <p><strong>연구제목:</strong> 인공지능 에이전트의 피드백 방식이 학습에 미치는 영향 탐색 연구</p>
  <ol class="agree-list">
    <li><span class="agree-num">1.</span>나는 이 연구의 설명문을 읽고 충분히 이해하였습니다.</li>
    <li><span class="agree-num">2.</span>나는 이 연구에 참여함으로써 발생할 위험과 이득을 숙지하였습니다.</li>
    <li><span class="agree-num">3.</span>나는 이 연구에 참여하는 것에 대하여 자발적으로 동의합니다. </li>
    <li><span class="agree-num">4.</span>나는 이 연구에서 얻어진 나에 대한 정보를 현행 법률과 가톨릭대학교 성심교정 생명윤리심의위원회 규정이 허용하는 범위 내에서 연구자가 수집하고 처리하는데 동의합니다.</li>
    <li><span class="agree-num">5.</span>나는 담당 연구자나 위임 받은 대리인이 연구를 진행하거나 결과 관리를 하는 경우와 연구기관, 연구비지원기관 및 가톨릭대학교 성심교정 생명윤리심의위원회가 실태 조사를 하는 경우에는 비밀로 유지되는 나의 개인 신상 정보를 직접적으로 열람하는 것에 동의합니다.</li>
    <li><span class="agree-num">6.</span>나는 언제라도 이 연구의 참여를 철회할 수 있고 이러한 결정이 나에게 어떠한 해도 되지 않을 것이라는 것을 압니다.</li>
  </ol>
</div>
"""

PRIVACY_HTML = """
<div class="privacy-wrap">
  <h1>연구참여자 개인정보 수집∙이용 동의서</h1>
  <h2>[ 개인정보 수집∙이용에 대한 동의 ]</h2>
  <table class="privacy-table">
    <tr>
      <th>수집하는 개인정보 항목
</th>
      <td>성별, 나이, 휴대폰 번호</td>
    </tr>
    <tr>
      <th>개인정보의 수집 및 이용목적
</th>
      <td>
        <p>제공하신 정보는 연구수행 및 논문작성 등을 위해서 사용합니다.</p>
        <ol>
          <li>연구수행을 위해 이용 :성별, 나이, 핸드폰 번호</li>
          <li>단, 이용자의 기본적 인권 침해의 우려가 있는 민감한 개인정보 (인종 및 민족, 사상 및 신조, 정치적 성향 및 범죄기록 등)는 수집하지 않습니다.</li>
        </ol>
      </td>
    </tr>
    <tr>
      <th>개인정보의 제3자 제공 및 목적 외 이용</th>
      <td>법이 요구하거나 가톨릭대학교 성심교정 생명윤리심의위원회가 본 연구의 실시 절차와 자료의 신뢰성을 검증하기 위해 연구 결과를 직접 열람할 수 있습니다.</td>
    </tr>
    <tr>
      <th>개인정보의 보유 및 이용기간
</th>
      <td>수집된 개인정보의 보유기간은 연구종료 후 3년 까지 입니다. 또한 파기(삭제)시 연구대상자의 개인정보를 재생이 불가능한 방법으로 즉시 파기합니다.</td>
    </tr>
  </table>
  <p class="privacy-note">※ 귀하는 이에 대한 동의를 거부할 수 있으며, 다만, 동의가 없을 경우 연구 참여가 불가능할 수 있음을 알려드립니다.
  ※ 개인정보 제공자가 동의한 내용외의 다른 목적으로 활용하지 않음
  <br>※ 만 18세 미만인 경우 반드시 법적대리인의 동의가 필요함 
  <br>※「개인정보보호법」등 관련 법규에 의거하여 상기 본인은 위와 같이 개인정보 수집 및 활용에 동의함.
</p>
</div>
"""

GRAMMAR_INFO_MD = r"""
정적 이미지에 기반한 **시각 추론 과제**를 수행하게 됩니다.

각 문항에서는 다음을 수행합니다.
- **이미지를 주의 깊게 관찰하기**
- **객관식 추론 문항**에 응답하기 (예: 시간대, 시간의 상대적 순서)
- 선택한 답을 설명하는 **추론 근거(이유) 옵션** 1개를 고르기

중요:
- 이미지에는 **명확한 표면 단서**나 **직접적인 라벨**이 없습니다.
- 간접적인 시각 단서를 바탕으로 **주의 깊은 관찰과 추론**이 필요합니다.
- **근거 없이 추측만 하면**, 이후 문항에서 필요한 단서를 일관되게 포착하기 어려워 과제가 더 어렵게 느껴질 수 있습니다.
"""

REASON_NOUN_LABELS = [
    "A. 그림자의 길이와 방향",
    "B. 건물 벽면에 비친 빛의 밝기",
    "C. 햇빛이 바닥에 닿는 각도",
    "D. 주변 공간 전반의 명암 대비",
]

REASON_VERB_LABELS = [
    "A. 그림자가 얼마나 길고 어느 방향으로 형성되어 있는지를 살펴보았다",
    "B. 건물 외벽이나 바닥의 밝기 차이를 비교했다",
    "C. 햇빛이 비추는 방향과 각도를 기준으로 판단했다",
    "D. 장면 전체의 빛과 어둠의 분포를 종합적으로 고려했다",
]

# --------------------------------------------------------------------------------------
# JS helpers (scroll + MCP animation) kept from scaffold
# --------------------------------------------------------------------------------------


def scroll_top_js(nonce: Optional[int] = None) -> None:
    nonce = nonce or st.session_state.get("_scroll_nonce", 0)
    st.session_state["_scroll_nonce"] = nonce + 1
    script = """
        <script id="goTop-{nonce}">
        (function(){{
          function goTop(){{
            try {{
              var pdoc = window.parent && window.parent.document;
              var sect = pdoc && pdoc.querySelector && pdoc.querySelector('section.main');
              if (sect && sect.scrollTo) sect.scrollTo({{top:0,left:0,behavior:'instant'}});
            }} catch(e) {{}}
            try {{
              window.scrollTo({{top:0,left:0,behavior:'instant'}});
              document.documentElement && document.documentElement.scrollTo && document.documentElement.scrollTo(0,0);
              document.body && document.body.scrollTo && document.body.scrollTo(0,0);
            }} catch(e) {{}}
          }}
          goTop();
          if (window.requestAnimationFrame) requestAnimationFrame(goTop);
          setTimeout(goTop, 25);
          setTimeout(goTop, 80);
          setTimeout(goTop, 180);
          setTimeout(goTop, 320);
        }})();
        </script>
    """.replace(
        "{nonce}", str(nonce)
    )
    st.markdown(script, unsafe_allow_html=True)


def radio_required(
    label: str, options: List[Any], key: str, *, horizontal: bool = False
) -> tuple[Optional[Any], bool]:
    """
    Render a radio input without a default selection.

    Returns the selected value (or None) and whether the input is valid.
    """
    try:
        value = st.radio(label, options, index=None, key=key, horizontal=horizontal)
        return value, value is not None
    except TypeError:
        if horizontal:
            return _render_horizontal_radio_stack(label, options, key)
        placeholder = "— 하나를 선택하세요 —"
        opts = [placeholder] + options
        choice = st.radio(label, opts, index=0, key=key)
        return (None, False) if choice == placeholder else (choice, True)


def _render_horizontal_radio_stack(
    label: str, options: List[Any], key: str
) -> tuple[Optional[Any], bool]:
    st.markdown(f"**{label}**")
    selected = st.session_state.get(key)
    columns = st.columns(len(options))
    for option, col in zip(options, columns):
        option_label = str(option)
        display = f"✓ {option_label}" if selected == option else option_label
        if col.button(
            display,
            key=f"{key}_btn_{option_label}",
            use_container_width=True,
        ):
            selected = option
    if selected is not None:
        st.session_state[key] = selected
        st.caption(f"현재 선택: {selected}")
    else:
        st.session_state.pop(key, None)
    return selected, selected is not None


def inject_covx_toggle(round_no: int) -> None:
    st.markdown(
        f"""
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
      }}catch(_){{
      }}
    }});
  }})();
</script>
""",
        unsafe_allow_html=True,
    )


def render_mcp_animation(round_key: str, round_no: int, seconds: float = 2.5) -> None:
    """Render a full-screen MCP overlay animation that blocks background interactions."""
    st.session_state["in_mcp"] = True
    st.markdown(MCP_OVERLAY_CSS, unsafe_allow_html=True)
    placeholder = st.empty()

    steps = max(1, int(seconds * 20))
    round_label_map = {
        "nouns": "시각 추론 · 1단계(시간 추론)",
        "verbs": "시각 추론 · 2단계(시간 추론2)",
    }
    round_label = round_label_map.get(round_key, "추론 과제")

    for step in range(steps + 1):
        progress = int(step / steps * 100)
        ratio = progress / 100 if steps > 0 else 0
        status_index = min(
            len(MCP_STATUS_SEQUENCE) - 1, int(ratio * len(MCP_STATUS_SEQUENCE))
        )
        status_headline, status_detail = MCP_STATUS_SEQUENCE[status_index]
        if step == steps:
            status_headline = "AI 분석 완료"
            status_detail = "결과 요약을 준비하고 있습니다."
        dots = "." * ((step % 3) + 1)
        html = MCP_OVERLAY_TEMPLATE.format(
            round_label=round_label,
            status_headline=status_headline,
            status_detail=status_detail,
            dots=dots,
            progress=progress,
        )
        placeholder.markdown(html, unsafe_allow_html=True)
        time.sleep(seconds / steps)


def export_session_json(payload: Dict[str, Any]) -> None:
    with st.expander("📦 세션 데이터 확인 (JSON)", expanded=False):
        st.code(json.dumps(payload, ensure_ascii=False, indent=2), language="json")


# --------------------------------------------------------------------------------------
# Session bootstrap & sidebar controls
# --------------------------------------------------------------------------------------


def ensure_session_state() -> None:
    ss = st.session_state
    if "phase" not in ss:
        ss.phase = "consent"
    if "consent_step" not in ss:
        ss.consent_step = "explain"
    if "payload" not in ss:
        ss.payload = {
            "consent": {},
            "demographic": {},
            "anthro_responses": [],
            "achive_responses": [],
            "motivation_responses": [],
            "motivation_category_scores": {},
            "difficulty_checks": {},
            "inference_details": [],
            "practice_attempt": {},
            "feedback_messages": {"nouns": [], "verbs": []},
            "feedback_condition": "",
            "open_feedback": "",
            "manipulation_check": {},
            "start_time": None,
            "end_time": None,
            "phone": "",
            "participant_id": None,
        }
    if "manager" not in ss:
        ss.manager = ExperimentManager()
    if "round_state" not in ss:
        ss.round_state = {
            "nouns_index": 0,
            "verbs_index": 0,
            "question_start": None,
            "last_micro_feedback": None,
        }
    if "practice_state" not in ss:
        ss.practice_state = {
            "attempted": False,
            "correct": None,
            "message": "",
            "explanation": "",
        }
    if "analysis_seen" not in ss:
        ss.analysis_seen = {"nouns": False, "verbs": False}
    if "in_mcp" not in ss:
        ss.in_mcp = False
    if "mcp_active_round" not in ss:
        ss.mcp_active_round = None
    if "mcp_active_round_no" not in ss:
        ss.mcp_active_round_no = None
    if "mcp_done" not in ss:
        ss.mcp_done = {}
    # [CHANGE] Track final save status and retry context in session state.
    if "saved_once" not in ss:
        ss.saved_once = False
    if "save_error" not in ss:
        ss.save_error = None
    if "save_destination" not in ss:
        ss.save_destination = None
    if "motivation_page" not in ss:
        ss.motivation_page = 1
    if "anthro_page" not in ss:
        ss.anthro_page = 1
    if "achive_page" not in ss:
        ss.achive_page = 1
    if "manip_page" not in ss:
        ss.manip_page = 1
    if "DRY_RUN" not in ss:
        ss.DRY_RUN = os.getenv("DRY_RUN", "false").lower() == "true"
    if "record" not in ss:
        ss.record = None
    if "_resource_fallback_warned" not in ss:
        ss._resource_fallback_warned = {}
    if "manip_check" not in ss:
        ss.manip_check = {}
    if "manip_check_saved" not in ss:
        ss.manip_check_saved = {}


def set_phase(next_phase: str) -> None:
    allowed = {
        "consent",
        "demographic",
        "instructions",
        "anthro",
        "achive",
        "visual_training_intro",
        "practice_building_height",
        "visual_practice",
        "task_intro",
        "inference_nouns",
        "analysis_nouns",
        "feedback_nouns",
        "difficulty_check",
        "inference_verbs",
        "analysis_verbs",
        "feedback_verbs",
        "motivation",
        "post_task_reflection",
        "manipulation_check",
        "phone_input",
        "summary",
    }
    st.session_state.phase = next_phase if next_phase in allowed else "summary"
    scroll_top_js()
    st.rerun()


# [CHANGE] Updated resource fallbacks to use centralized constants.
RESOURCE_FALLBACKS: Dict[str, List[str]] = {
    "questions_anthro.json": ANTHRO_DEFAULT_ITEMS,
    "questions_achive.json": ACHIVE_DEFAULT_ITEMS,
}


def _warn_resource_fallback(filename: str) -> None:
    registry = st.session_state.setdefault("_resource_fallback_warned", {})
    if not registry.get(filename):
        st.warning("Local resource not found — using built-in items.", icon="⚠️")
        registry[filename] = True


def _load_local_json(filename: str) -> Optional[List[str]]:
    fallback = RESOURCE_FALLBACKS.get(filename)
    path = BASE_DIR / "data" / filename
    if path.exists():
        try:
            with path.open("r", encoding="utf-8") as file_obj:
                data = json.load(file_obj)
        except Exception:
            if fallback:
                _warn_resource_fallback(filename)
                return list(fallback)
            st.error(f"{filename} 로드 중 문제가 발생했습니다.")
            return None
        if isinstance(data, list) and data:
            return data
        if fallback:
            _warn_resource_fallback(filename)
            return list(fallback)
        st.warning(f"{filename} 데이터가 비어 있습니다.")
        return None
    if fallback:
        _warn_resource_fallback(filename)
        return list(fallback)
    st.error(f"로컬 리소스 {filename} 을(를) 찾지 못했습니다.")
    return None


# --------------------------------------------------------------------------------------
# Rendering helpers for each phase
# --------------------------------------------------------------------------------------
def render_consent() -> None:
    scroll_top_js()
    st.markdown(COMMON_CSS, unsafe_allow_html=True)
    if st.session_state.consent_step == "explain":
        st.title("연구 소개")
        st.markdown(CONSENT_HTML, unsafe_allow_html=True)
        if st.button("다음", use_container_width=True):
            st.session_state.consent_step = "agree"
            st.rerun()
        return

    st.title("연구 동의 및 개인정보 동의")
    st.markdown(AGREE_HTML, unsafe_allow_html=True)
    consent_research = st.radio(
        "연구 참여에 동의하십니까?",
        ["동의함", "동의하지 않음"],
        horizontal=True,
        key="consent_research_radio",
    )
    st.markdown(PRIVACY_HTML, unsafe_allow_html=True)
    consent_privacy = st.radio(
        "개인정보 수집·이용에 동의하십니까?",
        ["동의함", "동의하지 않음"],
        horizontal=True,
        key="consent_privacy_radio",
    )
    cols = st.columns(2)
    with cols[0]:
        if st.button("이전", use_container_width=True):
            st.session_state.consent_step = "explain"
            st.rerun()
    with cols[1]:
        if st.button("동의하고 진행", use_container_width=True):
            if consent_research != "동의함" or consent_privacy != "동의함":
                st.warning("연구 및 개인정보 동의가 모두 필요합니다.")
            else:
                st.session_state.payload["consent"] = {
                    "consent_research": consent_research,
                    "consent_privacy": consent_privacy,
                }
                st.session_state.payload["start_time"] = now_utc_iso()
                set_phase("demographic")


def render_demographic() -> None:
    scroll_top_js()
    st.title("인적사항 입력")
    st.write("연구 통계와 조건 배정을 위해 아래 정보를 입력해 주세요.")

    # [CHANGE] Enforce required biological sex selection without defaults.
    sex_value, sex_valid = radio_required(
        DEMOGRAPHIC_SEX_LABEL, DEMOGRAPHIC_SEX_OPTIONS, key="demographic_sex"
    )

    # [CHANGE] Replace age dropdown with validated numeric input.
    age_input = st.text_input(
        DEMOGRAPHIC_AGE_LABEL,
        key="demographic_age_years",
        placeholder="예: 25",
    )
    age_value: Optional[int] = None
    age_error: Optional[str] = None
    age_clean = age_input.strip()
    age_valid = False
    if age_clean:
        if age_clean.isdigit():
            candidate = int(age_clean)
            if DEMOGRAPHIC_AGE_MIN <= candidate <= DEMOGRAPHIC_AGE_MAX:
                age_value = candidate
                age_valid = True
            else:
                age_error = f"{DEMOGRAPHIC_AGE_MIN}에서 {DEMOGRAPHIC_AGE_MAX} 사이의 숫자만 입력해 주세요."
        else:
            age_error = "숫자만 입력해 주세요."
    if age_error:
        st.error(age_error)

    can_proceed = bool(sex_valid and age_valid)
    next_disabled = not can_proceed

    if st.button("다음 단계", use_container_width=True, disabled=next_disabled):
        if not can_proceed:
            st.warning("모든 필수 항목을 정확히 입력해 주세요.")
            return
        st.session_state.payload["demographic"] = {
            "sex_biological": sex_value,
            "age_years": age_value,
        }
        condition = normalize_condition(get_or_assign_praise_condition())
        st.session_state["praise_condition"] = condition
        condition = get_or_assign_praise_condition()
        participant_id = st.session_state.manager.create_participant(
            st.session_state.payload["demographic"],
            assigned_condition=condition,
        )
        st.session_state.payload["participant_id"] = participant_id
        st.session_state.payload["feedback_condition"] = condition
        set_phase("instructions")


def render_instructions() -> None:
    scroll_top_js()
    st.title("연구 진행 안내")
    st.markdown(
        """
### 연구 참여에 앞서 안내드립니다

이 설문은 시각 추론 과제를 수행하고, 이에 대한 AI의 피드백, 그리고 그 경험에 대해 여러분의 생각을 알아보는 과정으로 이루어져 있습니다.
연구는 아래와 같이 진행됩니다. 시각 추론 과제와 AI 피드백은 각각 2회 진행됩니다.

1. 간단한 인적 사항에 응답하기
2. 질문지 응답하기
3. 시각 추론 과제 안내(연습 포함)  
4. 시각 추론 과제(2회)  
5. AI의 피드백 받기(2회)  
6. 학습 경험과 피드백 느낌에 대해 응답하기  

이 연구에서는 정답 자체뿐 아니라 어떤 단서를 보고 어떻게 추론했는지(과정)가 중요합니다.
부담 없이, 떠오르는 판단과 그 근거에 가깝게 응답해 주시면 됩니다.

전체 소요 시간은 약 10~15분 정도이며, 응답 내용은 연구 목적 외에는 사용되지 않으며 익명으로 처리됩니다.
"""
    )
    if st.button("설문 시작", use_container_width=True):
        set_phase("anthro")


# [CHANGE] Render paginated Likert blocks with numeric-only options.
def render_paginated_likert(
    questions: List[str],
    key_prefix: str,
    scale_min: int,
    scale_max: int,
    page_state_key: str,
    responses_key: str,
    prompt_html: str,
    scale_hint_html: str,
    per_page: int,
    question_ids: Optional[List[str]] = None,
) -> bool:
    total = len(questions)
    if total == 0:
        return True

    per_page = max(1, min(per_page, 10))
    total_pages = (total + per_page - 1) // per_page
    page = st.session_state.get(page_state_key, 1)
    if page < 1:
        page = 1
    if page > total_pages:
        page = total_pages
    st.session_state[page_state_key] = page

    start_idx = (page - 1) * per_page
    end_idx = min(start_idx + per_page, total)

    if not st.session_state.payload.get(responses_key):
        st.session_state.payload[responses_key] = [None] * total

    st.markdown(prompt_html, unsafe_allow_html=True)
    st.markdown(scale_hint_html, unsafe_allow_html=True)
    st.markdown(
        f"<div style='text-align:center;color:#6b7480;margin-bottom:12px;'>문항 {start_idx + 1}–{end_idx} / {total} (페이지 {page}/{total_pages})</div>",
        unsafe_allow_html=True,
    )

    options = list(range(scale_min, scale_max + 1))
    for idx in range(start_idx, end_idx):
        label = questions[idx]
        question_id = (
            question_ids[idx] if question_ids and idx < len(question_ids) else str(idx)
        )
        selected = render_likert_numeric(
            item_id=f"{key_prefix}_{question_id}",
            label=f"{idx + 1}. {label}",
            options=options,
            key_prefix=f"{key_prefix}_opt",
        )
        value_key = f"{key_prefix}_val_{idx}"
        if selected is None:
            st.session_state[value_key] = None
            st.session_state.payload[responses_key][idx] = None
        else:
            st.session_state[value_key] = int(selected)
            st.session_state.payload[responses_key][idx] = int(selected)

    page_values = [
        st.session_state.get(f"{key_prefix}_val_{idx}")
        for idx in range(start_idx, end_idx)
    ]

    col_prev, col_next = st.columns(2)
    with col_prev:
        if page > 1 and st.button(
            "← 이전", use_container_width=True, key=f"{key_prefix}_prev"
        ):
            st.session_state[page_state_key] = page - 1
            set_phase(st.session_state.phase)
    with col_next:
        next_label = "다음 단계" if page == total_pages else "다음 →"
        if st.button(next_label, use_container_width=True, key=f"{key_prefix}_next"):
            if any(v is None for v in page_values):
                st.warning("현재 페이지의 모든 문항에 응답해 주세요.")
            else:
                if page == total_pages:
                    all_values = [
                        st.session_state.get(f"{key_prefix}_val_{idx}")
                        for idx in range(total)
                    ]
                    if any(v is None for v in all_values):
                        st.warning("모든 문항에 응답해 주세요.")
                    else:
                        st.session_state.payload[responses_key] = [
                            int(v) for v in all_values
                        ]
                        return True
                else:
                    st.session_state[page_state_key] = page + 1
                    set_phase(st.session_state.phase)
    return False


def render_anthro() -> None:
    scroll_top_js()
    questions = _load_local_json("questions_anthro.json")
    if not questions:
        return
    # [CHANGE] Render anthropomorphism scale with unified 5-point labels.
    done = render_paginated_likert(
        questions=questions,
        key_prefix="anthro",
        scale_min=1,
        scale_max=5,
        page_state_key="anthro_page",
        responses_key="anthro_responses",
        prompt_html="<h2 class='section-heading'>다음 문항을 읽고 평소에 생각과 가장 가까운 것을 선택해주세요.</h2>",
        scale_hint_html=LIKERT5_LEGEND_HTML,
        per_page=10,
    )
    if done:
        st.session_state.anthro_page = 1
        set_phase("achive")


def render_achive() -> None:
    scroll_top_js()
    questions = _load_local_json("questions_achive.json")
    if not questions:
        return
    done = render_paginated_likert(
        questions=questions,
        key_prefix="achive",
        scale_min=1,
        scale_max=6,
        page_state_key="achive_page",
        responses_key="achive_responses",
        prompt_html="<h2 class='section-heading'>학습과 관련하여 본인의 생각과 가장 가까운 것을 선택해주세요.</h2>",
        scale_hint_html=LIKERT6_LEGEND_HTML,
        per_page=10,
    )
    if done:
        st.session_state.achive_page = 1
        set_phase("visual_training_intro")


def render_question_card(question: Question, badge: Optional[str] = None) -> None:
    gloss_html = html.escape(question.gloss)
    stem_html = html.escape(question.stem)
    badge_html = f'<div class="question-badge">{badge}</div>' if badge else ""
    st.markdown(
        f"""
<div class="question-card">
  {badge_html}
  <div class="question-label">지시문</div>
  <p class="question-stem">{gloss_html}</p>
  <div class="question-label">문제</div>
  <p class="question-stem-text">{stem_html}</p>
</div>
""",
        unsafe_allow_html=True,
    )


def render_question_image(question: Question) -> None:
    """Render question image (if present) after the instruction/problem card."""
    if getattr(question, "image_path", None):
        try:
            st.image(question.image_path, use_container_width=True)
        except Exception:
            # Fail gracefully if the image cannot be loaded.
            pass


def get_randomized_option_state(
    question: Question, state_key: str
) -> Tuple[List[str], List[int], int]:
    """Return shuffled options, map to original indices, and displayed correct index."""
    options_state_key = f"{state_key}_options"
    if options_state_key not in st.session_state:
        option_pairs = list(enumerate(question.options))
        if question.shuffle_options:
            random.shuffle(option_pairs)
        st.session_state[options_state_key] = option_pairs
    else:
        option_pairs = st.session_state[options_state_key]

    original_index_map = [orig_idx for orig_idx, _ in option_pairs]
    display_options = [opt for _, opt in option_pairs]
    correct_original_idx = question.answer_idx
    try:
        correct_display_idx = next(
            idx
            for idx, orig_idx in enumerate(original_index_map)
            if orig_idx == correct_original_idx
        )
    except StopIteration as exc:
        raise ValueError(
            f"Correct answer index {correct_original_idx} not found for {question.id}"
        ) from exc

    st.session_state[f"{state_key}_correct_idx"] = correct_display_idx
    return display_options, original_index_map, correct_display_idx


def render_visual_training_intro() -> None:
    scroll_top_js()
    st.title("연습: 응답 형식 확인")
    st.markdown(
        """
### 이미지를 보고 시각 추론을 수행합니다.

이 연구에서는 **이미지 기반 시각 추론 과제**를 수행합니다.  
텍스트나 라벨을 읽는 것이 아니라, 이미지 속 **간접적인 시각 단서**를 활용해 *(예: 시간대, 시간의 상대적 순서)*와 같은 **숨겨진 속성**을 추론하게 됩니다.

각 이미지마다 다음을 수행해 주세요.
- **주의 깊게 관찰하기**
- **객관식 정답** 1개 선택하기
- 선택한 답을 설명하는 **추론 근거(이유) 옵션** 1개 선택하기

중요:
- 이미지에는 **단번에 알 수 있는 명확한 단서**가 없습니다.
- **주의 깊은 관찰과 추론**이 필요합니다.
- **근거 없이 추측만 하면**, 이후 문항에서 중요한 단서를 놓치기 쉬워 더 어려워질 수 있습니다.
        """
    )
    st.info("이 연습 단계는 응답 형식에 익숙해지기 위한 것입니다.")

    with st.expander("과제 개요(다시 보기)", expanded=True):
        st.markdown(GRAMMAR_INFO_MD)

    understood = st.checkbox(
        "위 안내사항을 읽었으며 이해했습니다.",
        key="practice_instructions_understood",
    )
    if st.button(
        "다음으로 진행하기",
        use_container_width=True,
        disabled=not understood,
        key="practice_instructions_to_practice",
    ):
        set_phase("practice_building_height")


def render_practice_building_height() -> None:
    scroll_top_js()
    st.title("연습 문항: 건물 높이 추론")

    st.markdown(
        "아래 이미지를 보고, 화면에 보이는 건물의 높이를 추론해 주세요. 사람과 층별 창문/출입구 구조를 단서로 활용할 수 있습니다."
    )

    # Use the same image loading convention (absolute path under BASE_DIR).
    st.image(str(BASE_DIR / "test_task.png"), use_container_width=True)

    ps = st.session_state.practice_state
    if ps.get("attempted", False):
        if ps.get("correct", False):
            st.success("연습 문항 제출이 완료되었습니다.")
        else:
            st.info(
                "연습 문항 제출이 완료되었습니다."
            )
        if st.button(
            "본 문항 시작하기",
            use_container_width=True,
            key="practice_building_height_to_main",
        ):
            set_phase("task_intro")
        return

    answer_labels = list(PRACTICE_BUILDING_HEIGHT_QUESTION.options)
    selected_answer_label, answer_valid = radio_required(
        "정답을 선택하세요",
        answer_labels,
        key="practice_building_height_answer",
    )
    selected_reason_label, reason_valid = radio_required(
        "정답을 그렇게 선택한 주요 근거는 무엇인가요?",
        PRACTICE_BUILDING_HEIGHT_REASON_LABELS,
        key="practice_building_height_reason",
    )

    can_submit = bool(answer_valid and reason_valid)
    if not st.button(
        "제출하기",
        use_container_width=True,
        disabled=not can_submit,
        key="practice_building_height_submit",
    ):
        return
    if not can_submit:
        st.error("정답과 추론 근거 선택은 필수입니다.")
        return

    def _choice_code(text: str) -> str:
        if not text:
            return ""
        head = text.split(".", 1)[0].strip()
        return head if len(head) == 1 else head[:1]

    selected_option_idx = int(answer_labels.index(selected_answer_label))
    is_correct = selected_option_idx == int(PRACTICE_BUILDING_HEIGHT_QUESTION.answer_idx)
    practice_record: Dict[str, Any] = {
        "question_id": PRACTICE_BUILDING_HEIGHT_QUESTION.id,
        "stimulus_image": str(BASE_DIR / "test_task.png"),
        "options": list(PRACTICE_BUILDING_HEIGHT_QUESTION.options),
        "selected_option": selected_option_idx,
        "selected_option_text": str(selected_answer_label),
        "selected_option_code": _choice_code(str(selected_answer_label)),
        "correct_idx": int(PRACTICE_BUILDING_HEIGHT_QUESTION.answer_idx),
        "correct_option_code": _choice_code(
            PRACTICE_BUILDING_HEIGHT_QUESTION.options[
                PRACTICE_BUILDING_HEIGHT_QUESTION.answer_idx
            ]
        ),
        "is_correct": bool(is_correct),
        "selected_reason_text": str(selected_reason_label),
        "selected_reason_code": _choice_code(str(selected_reason_label)),
        "timestamp": now_utc_iso(),
    }

    # Save separately from main inference dataset.
    st.session_state.practice_state = {
        "attempted": True,
        "correct": bool(is_correct),
        "record": practice_record,
    }
    st.session_state.payload["practice_attempt"] = practice_record

    # Re-render into the post-submit message + start button.
    try:
        st.rerun()
    except Exception:
        st.experimental_rerun()


def render_visual_practice() -> None:
    scroll_top_js()
    st.title("연습 문항: 건물 높이 추론")
    st.caption("이 연습 문항은 점수에 반영되지 않습니다.")

    ps = st.session_state.practice_state
    if ps.get("attempted", False):
        st.success("연습 문항이 완료되었습니다.")
        if st.button(
            "본 과제 안내로 진행하기",
            use_container_width=True,
            key="practice_to_task_intro",
        ):
            set_phase("task_intro")
        return

    question = PRACTICE_BUILDING_HEIGHT_QUESTION
    render_question_card(question, badge="연습 문항")
    render_question_image(question)
    st.markdown("제출하려면 정답과 추론 근거를 모두 선택해야 합니다.")

    answer_labels = list(question.options)
    selected_answer_label, answer_valid = radio_required(
        "정답을 선택하세요",
        answer_labels,
        key="practice_building_height_answer",
    )

    selected_reason_label, reason_valid = radio_required(
        "정답을 그렇게 선택한 주요 근거는 무엇인가요?",
        PRACTICE_BUILDING_HEIGHT_REASON_LABELS,
        key="practice_building_height_reason",
    )

    can_submit = bool(answer_valid and reason_valid)
    submitted = st.button(
        "제출",
        use_container_width=True,
        disabled=not can_submit,
        key="practice_building_height_submit",
    )
    if not submitted:
        return
    if not can_submit:
        st.error("정답과 추론 근거 선택은 필수입니다.")
        return

    def _choice_code(text: str) -> str:
        if not text:
            return ""
        head = text.split(".", 1)[0].strip()
        return head if len(head) == 1 else head[:1]

    selected_option_idx = int(answer_labels.index(selected_answer_label))
    is_correct = selected_option_idx == int(question.answer_idx)
    practice_record: Dict[str, Any] = {
        "question_id": question.id,
        "stimulus_image": getattr(question, "image_path", None) or "",
        "options": list(question.options),
        "selected_option": selected_option_idx,
        "selected_option_text": str(selected_answer_label),
        "selected_option_code": _choice_code(str(selected_answer_label)),
        "correct_idx": int(question.answer_idx),
        "correct_option_code": _choice_code(question.options[question.answer_idx]),
        "is_correct": bool(is_correct),
        "selected_reason_text": str(selected_reason_label),
        "selected_reason_code": _choice_code(str(selected_reason_label)),
        "timestamp": now_utc_iso(),
    }

    # Store practice response separately: session practice_state + payload.practice_attempt.
    st.session_state.practice_state = {
        "attempted": True,
        "correct": bool(is_correct),
        "message": "",
        "explanation": "",
        "record": practice_record,
    }
    st.session_state.payload["practice_attempt"] = practice_record

    # Re-render once into the fixed completion message + continue button.
    try:
        st.rerun()
    except Exception:
        st.experimental_rerun()


def render_task_intro() -> None:
    scroll_top_js()
    st.title("시각 추론 과제(본 과제)")
    st.markdown(
        """
### 이제 본 시각 추론 과제를 시작합니다

이미지를 보고 시각 추론 과제를 수행합니다.  
이미지에 있는 명시적 라벨이나 텍스트가 아니라, **간접적인 시각 단서**를 활용해 *(예: 시간대, 시간의 상대적 순서)*와 같은 숨겨진 속성을 추론합니다.

각 이미지마다 다음을 수행해 주세요.
- 이미지를 주의 깊게 관찰하기
- 객관식 추론 문항에 정답 1개 선택하기
- 선택한 답을 가장 잘 설명하는 추론 근거(이유) 옵션 1개 선택하기

중요:
- 단번에 알 수 있는 **명확한 표면 단서**가 없습니다.
- **주의 깊은 관찰과 추론**이 필요합니다.
- 근거 없이 추측만 하면 이후 문항이 더 어렵게 느껴질 수 있습니다.
        """
    )
    st.markdown(
        """
각 단계(블록)가 끝난 뒤에는, AI 튜터가 응답 패턴을 바탕으로 피드백을 제공하며 이후 간단한 설문이 이어집니다.
        """
    )
    with st.expander("과제 개요(다시 보기)", expanded=True):
        st.markdown(GRAMMAR_INFO_MD)
    if st.button("본 문제 시작하기", use_container_width=True):
        st.session_state.round_state["nouns_index"] = 0
        st.session_state.round_state["question_start"] = None
        set_phase("inference_nouns")


def render_inference_round(
    round_key: str,
    questions: List[Question],
    reason_labels: List[str],
    next_phase: str,
    analysis_round_no: int,
) -> None:
    scroll_top_js()
    round_title_map = {
        "nouns": "시각 추론 (1단계): 시간 추론",
        "verbs": "시각 추론 (2단계): 시간 추론2",
    }
    st.title(round_title_map.get(round_key, "시각 추론 과제"))
    rs = st.session_state.round_state
    payload = st.session_state.payload
    index = rs.get(f"{round_key}_index", 0)
    if index >= len(questions):
        set_phase(next_phase)
        return
    question = questions[index]
    st.session_state["round_no"] = index
    current_index = int(st.session_state.get("round_no", 0)) + 1
    option_state_key = f"{round_key}_{question.id}"
    display_options, option_index_map, _ = get_randomized_option_state(
        question, option_state_key
    )

    question_container = st.container()
    with question_container:
        st.header(f"문항 {current_index} / {len(questions)}")
        round_badge = (
            "시간 추론"
            if round_key == "nouns"
            else "시간 추론2"
        )
        render_question_card(question, badge=round_badge)
        render_question_image(question)
        st.markdown("제출하려면 정답과 추론 근거를 모두 선택해야 합니다.")

        if rs.get("question_start") is None:
            rs["question_start"] = time.perf_counter()

        # Keep lettered options readable (A/B/C/D) by not adding numeric prefixes.
        answer_labels = list(display_options)
        selected_answer_label, answer_valid = radio_required(
            "정답을 선택하세요",
            answer_labels,
            key=f"{round_key}_answer_{index}",
        )

        rationale_tags = reason_labels
        rationale_prompt = (
            "정답을 그렇게 선택한 주요 근거는 무엇인가요?"
            if round_key == "nouns"
            else "판단에 가장 큰 영향을 준 시각 정보는 무엇인가요?"
        )
        selected_tag, tag_valid = radio_required(
            rationale_prompt,
            rationale_tags,
            key=f"{round_key}_tag_{index}",
        )

        can_submit = bool(answer_valid and tag_valid)
        submit_btn = st.button(
            "응답 제출",
            key=f"{round_key}_submit_{index}",
            disabled=not can_submit,
        )

        if not submit_btn:
            if SHOW_PER_ITEM_INLINE_FEEDBACK:
                last_micro = rs.get("last_micro_feedback")
                if last_micro:
                    st.markdown(f"✅ {last_micro}")
                    st.success(last_micro)
                    rs["last_micro_feedback"] = None
            return

    if not can_submit:
        st.error("정답과 추론 근거 선택은 필수입니다.")
        return

    start_time = rs.get("question_start")
    if start_time is None:
        start_time = time.perf_counter()
    response_time = round(time.perf_counter() - start_time, 2)
    rs["question_start"] = None

    question_container.empty()
    st.session_state["in_mcp"] = True
    st.session_state.setdefault("mcp_done", {}).pop(analysis_round_no, None)
    st.session_state["mcp_active_round"] = round_key
    st.session_state["mcp_active_round_no"] = analysis_round_no

    manager: ExperimentManager = st.session_state.manager
    selected_display_idx = answer_labels.index(selected_answer_label)
    selected_option_idx = option_index_map[selected_display_idx]
    selected_tag_idx = rationale_tags.index(selected_tag)

    def _choice_code(text: str) -> str:
        if not text:
            return ""
        head = text.split(".", 1)[0].strip()
        return head if len(head) == 1 else head[:1]

    manager.process_inference_response(
        question_id=question.id,
        selected_option=selected_option_idx,
        selected_reason=selected_tag,
        response_time=response_time,
    )
    is_correct = int(selected_option_idx) == int(question.answer_idx)
    detail = {
        "round": round_key,
        "question_id": question.id,
        "stem": question.stem,
        "gloss": question.gloss,
        "options": question.options,
        "selected_option": int(selected_option_idx),
        "selected_option_text": display_options[selected_display_idx],
        "selected_option_code": _choice_code(display_options[selected_display_idx]),
        "correct_idx": int(question.answer_idx),
        "correct_text": question.options[question.answer_idx],
        "correct_option_code": _choice_code(question.options[question.answer_idx]),
        "is_correct": bool(is_correct),
        "selected_reason_idx": int(selected_tag_idx),
        "selected_reason_text": selected_tag,
        "selected_reason_code": _choice_code(selected_tag),
        "correct_reason_idx": int(question.reason_idx),
        "correct_reason_code": _choice_code(
            reason_labels[question.reason_idx] if 0 <= question.reason_idx < len(reason_labels) else ""
        ),
        "response_time": response_time,
        "timestamp": now_utc_iso(),
        "stimulus_image": getattr(question, "image_path", None) or "",
    }
    payload.setdefault("inference_details", []).append(detail)
    condition = normalize_condition(get_or_assign_praise_condition())
    completed_tags = [
        d.get("selected_reason_text")
        for d in payload["inference_details"]
        if d["round"] == round_key
    ]
    top_a, top_b = top_two_rationales(completed_tags)
    micro_a, micro_b = ensure_rationale_pair(top_a, top_b)
    micro_text = get_next_micro_feedback(condition, micro_a, micro_b)
    if SHOW_PER_ITEM_INLINE_FEEDBACK:
        rs["last_micro_feedback"] = micro_text
    else:
        rs["last_micro_feedback"] = None
    payload["feedback_messages"][round_key].append(micro_text)
    rs[f"{round_key}_index"] = index + 1

    if rs[f"{round_key}_index"] >= len(questions):
        set_phase(next_phase)
    else:
        set_phase(st.session_state.phase)


def render_analysis(round_key: str, round_no: int, next_phase: str) -> None:
    scroll_top_js()
    st.session_state.setdefault("mcp_done", {})
    if not st.session_state["mcp_done"].get(round_no, False):
        render_mcp_animation(round_key, round_no)
        st.session_state["mcp_done"][round_no] = True
        st.session_state["in_mcp"] = False
        st.session_state["mcp_active_round"] = None
        st.session_state["mcp_active_round_no"] = None
        try:
            st.rerun()
        except Exception:
            st.experimental_rerun()
        return

    st.session_state["in_mcp"] = False
    st.session_state["mcp_active_round"] = None
    st.session_state["mcp_active_round_no"] = None
    st.markdown(ANALYSIS_COMPLETE_CSS, unsafe_allow_html=True)

    round_label_map = {
        "nouns": "시각 추론 · 1단계(시간 추론)",
        "verbs": "시각 추론 · 2단계(시간 추론2)",
    }
    round_label = round_label_map.get(round_key, "추론 라운드")
    subtitle = "AI 튜터가 추론 패턴 분석을 마쳤습니다. 아래 버튼을 눌러 상세 피드백을 확인해 주세요."
    meta_line = f"추론 리포트 준비 완료 · {round_label} 피드백 확인 대기 중"
    status_line = "맞춤형 요약과 피드백을 전달할 준비가 되었습니다."

    card_open_html = f"""
<div class="analysis-complete-wrapper">
  <div class="analysis-complete-card">
    <div class="analysis-complete-badge">COVNOX 분석 프로토콜 · {round_label}</div>
    <div class="analysis-complete-body">
      <div class="analysis-complete-icon">🤖</div>
      <div class="analysis-complete-text">
        <h2 class="analysis-complete-title">분석이 완료되었습니다!</h2>
        <p class="analysis-complete-subtitle">{subtitle}</p>
      </div>
    </div>
    <div class="analysis-complete-meta">{meta_line}</div>
    <div class="analysis-complete-status">{status_line}</div>
    <div class="analysis-complete-button">
"""
    card_close_html = """
    </div>
  </div>
</div>
"""

    card_container = st.container()
    with card_container:
        st.markdown(card_open_html, unsafe_allow_html=True)
        view_button_clicked = st.button(
            "결과 보기",
            key=f"view-results-{round_no}",
            use_container_width=True,
        )
        st.markdown(card_close_html, unsafe_allow_html=True)

    if view_button_clicked:
        st.session_state.analysis_seen[round_key] = True
        set_phase(next_phase)


def render_feedback(round_key: str, _reason_labels: List[str], next_phase: str) -> None:
    scroll_top_js()
    st.markdown(FEEDBACK_UI_CSS, unsafe_allow_html=True)

    feedback_payload = get_feedback_once(
        round_key,
        generate_feedback,
        round_key,
        st.session_state.get("payload", {}),
    )
    summary_text = feedback_payload.get("summary_text", "")

    hero_subtitle_map = {
        "nouns": "시각 추론 · 1단계 리포트(시간 추론)",
        "verbs": "시각 추론 · 2단계 리포트(시간 추론2)",
    }
    hero_subtitle = hero_subtitle_map.get(round_key, "시각 추론 피드백")

    with st.container():
        st.markdown(
            f"""
  <div class="feedback-page">
    <div class="feedback-card feedback-hero-card">
      <div class="feedback-hero-badge"><span>🤖</span> AI 튜터 칭찬</div>
      <div class="feedback-hero-body">
        <div class="feedback-icon-wrap">🧠</div>
        <div class="feedback-hero-text">
          <h1 class="feedback-hero-title">분석 완료! 훌륭합니다!</h1>
          <p class="feedback-hero-subtitle">{hero_subtitle}</p>
        </div>
      </div>
      <div class="feedback-meta">AI 튜터가 응답 패턴을 정밀 분석하고 당신의 응답 내용에 대한 피드백을 정리했습니다.</div>
    </div>
    <div class="feedback-card feedback-comment-card">
      <div class="feedback-comment-title">
        <span class="feedback-comment-icon">✨</span>
        AI 튜터의 코멘트
      </div>
      <p class="feedback-comment-subtitle">AI 튜터가 분석 결과를 정리했어요. 아래 피드백을 확인해 주세요.</p>
    </div>
  """,
            unsafe_allow_html=True,
        )

        praise_placeholder = st.empty()
        render_praise_card_with_typewriter(
            summary_text,
            round_key=round_key,
            placeholder=praise_placeholder,
            speed=0.01,
        )

        if SHOW_PER_ITEM_SUMMARY and feedback_payload:
            st.markdown(
                '<div class="feedback-card feedback-comment-card feedback-micro-card"><div class="feedback-comment-title"><span class="feedback-comment-icon">💡</span> 문항별 간단 피드백</div>',
                unsafe_allow_html=True,
            )
            st.markdown('<div class="feedback-comment-body">', unsafe_allow_html=True)
            for question_id, micro_text in feedback_payload.get("micro_entries", []):
                st.markdown(f"- **{question_id}** · {micro_text}")
            st.markdown("</div></div>", unsafe_allow_html=True)

        st.markdown('<div class="feedback-actions">', unsafe_allow_html=True)
        if st.button(
            "다음 단계", use_container_width=True, key=f"{round_key}_feedback_next"
        ):
            set_phase(next_phase)
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)


def render_difficulty_check() -> None:
    scroll_top_js()
    st.title("다음 진행할 과제의 난이도를 선택해주세요")
    st.write("다음 라운드에서 진행하기를 원하는 난이도 수준을 선택해 주세요.")
    likert_options = list(range(1, 11))
    prompt = "다음 라운드 난이도는 방금한 과제에 비해 어느 정도 난이도를 원하시나요? (1=매우 쉬움, 10=매우 어려움)"
    try:
        rating_value = st.radio(
            prompt,
            options=likert_options,
            index=None,
            horizontal=True,
            key="difficulty_rating",
        )
        rating_valid = rating_value is not None
    except TypeError:
        rating_value, rating_valid = _render_horizontal_radio_stack(
            prompt, likert_options, "difficulty_rating_fallback"
        )
    if rating_valid:
        st.session_state.payload["difficulty_checks"]["after_round1"] = int(
            rating_value
        )
    else:
        st.session_state.payload["difficulty_checks"].pop("after_round1", None)
    if st.button("두번째 시작", use_container_width=True):
        if not rating_valid:
            st.warning("난이도 수준을 1~10 사이에서 선택해 주세요.")
            return
        st.session_state.round_state["verbs_index"] = 0
        st.session_state.round_state["question_start"] = None
        set_phase("inference_verbs")


def render_motivation() -> None:
    scroll_top_js()
    questions = [question.text for question in MOTIVATION_QUESTIONS]
    question_ids = [question.id for question in MOTIVATION_QUESTIONS]
    done = render_paginated_likert(
        questions=questions,
        key_prefix="motivation",
        scale_min=1,
        scale_max=5,
        page_state_key="motivation_page",
        responses_key="motivation_responses",
        prompt_html="<h2 class='section-heading'>방금 진행한 추론 과제를 하면서 떠오른 느낌과 생각을 응답해주세요.</h2>",
        scale_hint_html=LIKERT5_LEGEND_HTML,
        per_page=10,
        question_ids=question_ids,
    )
    if done:
        responses = st.session_state.payload.get("motivation_responses", [])
        category_scores: Dict[str, List[int]] = {}
        for response, question in zip(responses, MOTIVATION_QUESTIONS):
            if response is None:
                continue
            adjusted = question.scale + 1 - response if question.reverse else response
            category_scores.setdefault(question.category, []).append(adjusted)
        st.session_state.payload["motivation_category_scores"] = {
            category: round(sum(values) / len(values), 2) if values else 0.0
            for category, values in category_scores.items()
        }
        st.session_state.motivation_page = 1
        set_phase("post_task_reflection")


def render_manipulation_check() -> None:
    scroll_top_js()
    st.header("방금 피드백을 준 AI에이전트에 대한 평가를 진행해주세요.")
    st.caption(
        "각 문항은 1(전혀 그렇지 않다) ~ 5(매우 그렇다) 사이에서 선택해 주세요. 모든 문항은 필수입니다."
    )
    st.markdown(LIKERT5_LEGEND_HTML, unsafe_allow_html=True)

    total_items = len(MANIPULATION_CHECK_ITEMS)
    per_page = 10
    total_pages = (total_items + per_page - 1) // per_page
    page = st.session_state.get("manip_page", 1)
    if page < 1:
        page = 1
    if page > total_pages:
        page = total_pages
    st.session_state.manip_page = page

    start_idx = (page - 1) * per_page
    end_idx = min(start_idx + per_page, total_items)

    st.markdown(
        f"<div style='text-align:center;color:#6b7480;margin-bottom:12px;'>문항 {start_idx + 1}–{end_idx} / {total_items} (페이지 {page}/{total_pages})</div>",
        unsafe_allow_html=True,
    )

    answers: Dict[str, int] = st.session_state.setdefault("manip_check", {})
    options = LIKERT5_NUMERIC_OPTIONS

    for offset, item in enumerate(
        MANIPULATION_CHECK_ITEMS[start_idx:end_idx], start=start_idx + 1
    ):
        selection = render_likert_numeric(
            item_id=item.id,
            label=f"{offset}. {item.text}",
            options=options,
            key_prefix="manip",
        )
        value_key = f"manip_val_{item.id}"
        if selection is None:
            st.session_state[value_key] = None
            answers.pop(item.id, None)
        else:
            st.session_state[value_key] = int(selection)
            answers[item.id] = int(selection)

    page_values = [
        answers.get(item.id) for item in MANIPULATION_CHECK_ITEMS[start_idx:end_idx]
    ]

    st.divider()
    col_prev, col_next = st.columns(2)
    with col_prev:
        if page > 1 and st.button("← 이전", use_container_width=True, key="manip_prev"):
            st.session_state.manip_page = page - 1
            set_phase(st.session_state.phase)
    with col_next:
        next_label = "다음 단계" if page == total_pages else "다음 →"
        if st.button(next_label, use_container_width=True, key="manip_next"):
            if any(v is None for v in page_values):
                st.warning("현재 페이지의 모든 문항에 응답해 주세요.")
            else:
                if page == total_pages:
                    complete = all_answered(
                        answers,
                        MANIPULATION_CHECK_EXPECTED_COUNT,
                        valid_options=options,
                    )
                    if not complete:
                        st.warning("모든 문항에 응답해 주세요.")
                        return
                    saved = {
                        item.id: int(answers[item.id])
                        for item in MANIPULATION_CHECK_ITEMS
                    }
                    st.session_state.manip_check_saved = saved
                    st.session_state.payload["manipulation_check"] = saved
                    st.session_state.manip_page = 1
                    set_phase("phone_input")
                else:
                    st.session_state.manip_page = page + 1
                    set_phase(st.session_state.phase)


def render_post_task_reflection() -> None:
    scroll_top_js()
    st.title("다음 기회에 유사한 과제가 있을 때 어느 정도 난이도에 도전하시겠습니까?")
    st.write("유사한 과제를 더 진행한다면 어느 정도 난이도로 진행하실지 선택해주세요.")
    likert_options = list(range(1, 11))
    prompt = "원하는 난이도를 선택해주세요 (1=매우 쉬움, 10=매우 어려움)"
    try:
        rating_value = st.radio(
            prompt,
            options=likert_options,
            index=None,
            horizontal=True,
            key="difficulty_future_rating",
        )
        rating_valid = rating_value is not None
    except TypeError:
        rating_value, rating_valid = _render_horizontal_radio_stack(
            prompt, likert_options, "difficulty_future_rating_fallback"
        )
    if rating_valid:
        st.session_state.payload["difficulty_checks"]["final"] = int(rating_value)
    else:
        st.session_state.payload["difficulty_checks"].pop("final", None)
    st.session_state.payload["open_feedback"] = st.session_state.payload.get(
        "open_feedback", ""
    )
    if st.button("다음 단계", use_container_width=True):
        if not rating_valid:
            st.warning("난이도를 1~10 사이에서 선택해 주세요.")
            return
        set_phase("manipulation_check")


def render_phone_capture() -> None:
    scroll_top_js()
    st.title("연락처 입력 (선택 사항)")
    st.write(
        "답례품(기프티콘) 발송을 위해 휴대폰 번호를 입력해 주세요. 입력하지 않아도 참여는 완료되지만 보상 제공이 어려울 수 있습니다."
    )
    phone = st.text_input("휴대폰 번호 (예: 010-1234-5678)")
    st.session_state.payload["phone"] = phone.strip()
    if st.button("제출하기", use_container_width=True):
        set_phase("summary")


# [CHANGE] Final debrief screen with guarded single-save semantics and retry flow.
def render_summary() -> None:
    scroll_top_js()
    manager: ExperimentManager = st.session_state.manager
    payload = st.session_state.payload

    if not st.session_state.record:
        try:
            record = manager.complete_experiment()
        except ValueError:
            condition = normalize_condition(
                payload.get("feedback_condition", get_or_assign_praise_condition())
            )
            record = ExperimentData(
                participant_id=payload.get("participant_id")
                or f"manual_{int(time.time())}",
                condition=condition,
                demographic=payload.get("demographic", {}),
                inference_responses=[
                    {
                        "question_id": d["question_id"],
                        "selected_option": d["selected_option"],
                        "selected_reason": d["selected_reason_text"],
                        "response_time": d["response_time"],
                        "timestamp": d["timestamp"],
                    }
                    for d in payload.get("inference_details", [])
                ],
                survey_responses=[
                    {
                        "question_id": q.id,
                        "rating": score,
                        "timestamp": now_utc_iso(),
                    }
                    for q, score in zip(
                        MOTIVATION_QUESTIONS, payload.get("motivation_responses", [])
                    )
                ],
                feedback_messages=[
                    *payload.get("feedback_messages", {}).get("nouns", []),
                    *payload.get("feedback_messages", {}).get("verbs", []),
                ],
                timestamps={
                    "start": payload.get("start_time") or now_utc_iso(),
                    "end": now_utc_iso(),
                },
                completion_time=sum(
                    d["response_time"] for d in payload.get("inference_details", [])
                ),
            )
        st.session_state.record = record
        payload["end_time"] = record.timestamps["end"]

    record = st.session_state.record
    condition = normalize_condition(payload.get("feedback_condition", record.condition))
    payload["feedback_condition"] = condition
    payload["praise_condition"] = condition
    record.condition = condition

    storage_record = build_storage_record(payload, record)
    sheet_row = build_sheet_row(storage_record)
    if not st.session_state.saved_once and st.session_state.save_error is None:
        try:
            destinations: List[str] = []
            warn_registry: Dict[str, bool] = st.session_state.setdefault(
                "_resource_fallback_warned", {}
            )
            if st.session_state.DRY_RUN:
                key = "storage::dry_run"
                if not warn_registry.get(key):
                    st.info("DRY_RUN 모드이므로 원격 저장을 건너뜁니다.")
                    warn_registry[key] = True
                destinations.append("dry_run_only")
            else:
                if not google_ready():
                    raise RuntimeError("Google Sheets credentials not configured.")
                sheet_msg = save_to_sheets(sheet_row)
                destinations.append(sheet_msg)

                gcs_ok, gcs_msg = save_to_gcs(storage_record)
                if gcs_ok and gcs_msg:
                    destinations.append(gcs_msg)
                elif gcs_msg:
                    if gcs_msg == "GCS bucket not configured":
                        key = "gcs::not_configured"
                        if not warn_registry.get(key):
                            st.info(
                                "GCS 버킷이 설정되지 않아 JSON 스냅샷 저장을 생략합니다."
                            )
                            warn_registry[key] = True
                    else:
                        key = f"gcs::{gcs_msg}"
                        if not warn_registry.get(key):
                            st.warning(f"GCS 업로드 실패: {gcs_msg}")
                            warn_registry[key] = True

            if destinations:
                st.session_state.saved_once = True
                st.session_state.save_destination = ", ".join(destinations)
        except Exception as exc:  # pragma: no cover
            st.session_state.save_error = str(exc)

    st.header("연구 참여가 완료되었습니다.")
    st.markdown(
        """
        <div class="debrief-box">
          지금까지 연구에 참여해 주셔서 감사합니다. 아래 내용을 꼭 읽어 주세요.<br><br>
          - 본 연구는 AI 피드백 방식이 학습 경험과 동기에 미치는 영향을 살펴보기 위한 연구입니다.<br>
          - 설문과 과제에 대한 모든 응답은 연구 목적으로만 사용되며, 익명으로 안전하게 처리됩니다.<br>
          - 실험 중에 보신 AI 튜터의 칭찬·분석 문장은 실제 능력을 평가한 결과가 아니라, 연구 설계를 위해 미리 만들어 둔 예시 피드백입니다.<br>
          - 따라서 피드백에 포함된 점수, 표현, 분석 내용은 참여자님의 실제 실력이나 성격을 의미하지 않습니다.<br>
          - 연구와 관련하여 궁금한 점이 있다면 안내문에 기재된 연구자 연락처로 언제든지 문의해 주시기 바랍니다.<br><br>
          다시 한 번 소중한 참여에 감사드립니다.
        </div>
        """.strip(),
        unsafe_allow_html=True,
    )

    if st.session_state.saved_once:
        st.success("연구가 완료되었습니다. 하단의 종료/제출 버튼을 눌러주세요.")
    elif st.session_state.save_error:
        st.error(
            "응답 저장 중 오류가 발생했습니다. 네트워크를 확인한 뒤 다시 시도해 주세요."
        )
        if st.button("다시 시도", use_container_width=True):
            st.session_state.save_error = None
            st.rerun()
    else:
        st.info("응답을 안전하게 저장하는 중입니다. 잠시만 기다려 주세요.")

    submit_key = "final_submit_confirmed"
    if st.button(
        "종료/제출", use_container_width=True, disabled=not st.session_state.saved_once
    ):
        st.session_state[submit_key] = True

    if st.session_state.get(submit_key):
        st.success("제출 절차가 완료되었습니다. 지금 창을 닫으셔도 좋습니다.")

    if globals().get("SHOW_DEBUG_RESULTS", False):
        st.markdown(
            f"""
- 참가자 ID: **{record.participant_id}**
- 총 소요 시간: **{record.completion_time:.1f}초**
"""
        )

        all_reason_tags = [
            detail.get("selected_reason_text")
            for detail in payload.get("inference_details", [])
        ]
        overall_a, overall_b = top_two_rationales(all_reason_tags)
        debug_a, debug_b = ensure_rationale_pair(overall_a, overall_b)
        summary_templates = FEEDBACK_TEMPLATES.get(
            condition, FEEDBACK_TEMPLATES["emotional_surface"]
        )
        summary_text = random.choice(summary_templates)
        if "{A}" in summary_text:
            summary_text = summary_text.replace("{A}", debug_a).replace("{B}", debug_b)
        typewriter_markdown(summary_text, speed=0.01)

        analyzer = DataAnalyzer([record])
        condition_for_scores = normalize_condition(record.condition)
        motivation_scores = analyzer.get_motivation_scores().get(
            condition_for_scores, {}
        )
        if motivation_scores:
            st.subheader("동기 카테고리 평균 점수")
            df = pd.DataFrame(
                [
                    {"카테고리": cat, "평균 점수": round(score, 2)}
                    for cat, score in motivation_scores.items()
                ]
            )
            st.bar_chart(df.set_index("카테고리"))
        else:
            st.info("설문 데이터가 충분하지 않아 동기 점수를 계산할 수 없습니다.")

        st.subheader("세션 로그")
        export_session_json(payload)


# --------------------------------------------------------------------------------------
# App entrypoint
# --------------------------------------------------------------------------------------

ensure_session_state()

phase = st.session_state.phase
if phase == "consent":
    render_consent()
elif phase == "demographic":
    render_demographic()
elif phase == "instructions":
    render_instructions()
elif phase == "anthro":
    render_anthro()
elif phase == "achive":
    render_achive()
elif phase == "visual_training_intro":
    render_visual_training_intro()
elif phase == "practice_building_height":
    render_practice_building_height()
elif phase == "visual_practice":
    render_visual_practice()
elif phase == "task_intro":
    render_task_intro()
elif phase == "inference_nouns":
    render_inference_round(
        "nouns",
        NOUN_QUESTIONS,
        REASON_NOUN_LABELS,
        "analysis_nouns",
        analysis_round_no=1,
    )
elif phase == "analysis_nouns":
    render_analysis("nouns", 1, "feedback_nouns")
elif phase == "feedback_nouns":
    render_feedback("nouns", REASON_NOUN_LABELS, "difficulty_check")
elif phase == "difficulty_check":
    render_difficulty_check()
elif phase == "inference_verbs":
    render_inference_round(
        "verbs",
        VERB_QUESTIONS,
        REASON_VERB_LABELS,
        "analysis_verbs",
        analysis_round_no=2,
    )
elif phase == "analysis_verbs":
    render_analysis("verbs", 2, "feedback_verbs")
elif phase == "feedback_verbs":
    render_feedback("verbs", REASON_VERB_LABELS, "motivation")
elif phase == "motivation":
    render_motivation()
elif phase == "post_task_reflection":
    render_post_task_reflection()
elif phase == "manipulation_check":
    render_manipulation_check()
elif phase == "phone_input":
    render_phone_capture()
else:
    render_summary()
