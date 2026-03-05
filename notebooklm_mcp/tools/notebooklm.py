# -*- coding: utf-8 -*-
from __future__ import annotations
"""
tools/notebooklm.py — NotebookLM MCP 연동 도구

포함 tool:
  - upload_reports      : reports/ 마크다운 파일을 NotebookLM에 업로드 (MODE ON 전용)
  - query_notebooklm    : NotebookLM에 질문하고 Gemini 2.5 답변 수신 (MODE ON 전용)
  - compare_modes       : Antigravity 단독(OFF) vs NotebookLM(ON) 결과 나란히 비교

NOTE:
  실제 NotebookLM 연동은 외부 MCP 서버(npx notebooklm-mcp@latest)를 통해 이루어집니다.
  이 파일은 mode.config.json을 참조하여 분기 처리 및 결과 포맷을 담당합니다.
"""

import json
import os
import glob
from datetime import datetime

# ── 경로 설정 ─────────────────────────────────────────
_TOOLS_DIR   = os.path.dirname(__file__)
_NLM_DIR     = os.path.dirname(_TOOLS_DIR)
_ROOT        = os.path.dirname(_NLM_DIR)
_REPORTS_DIR = os.path.join(_ROOT, "reports")
_OUTPUT_DIR  = os.path.join(_ROOT, "output")
CONFIG_FILE  = os.path.join(_NLM_DIR, "mode.config.json")
# ────────────────────────────────────────────────────


# ════════════════════════════════════════════════════
# 내부 유틸
# ════════════════════════════════════════════════════

def _load_config() -> dict:
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_config(config: dict) -> None:
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def _check_mode_on() -> tuple[bool, dict | None]:
    """
    현재 MODE가 ON인지 확인합니다.
    OFF면 에러 dict를 반환합니다.

    Returns:
        (is_on: bool, error_dict: dict | None)
    """
    config = _load_config()
    if config.get("notebooklm_mode", "OFF") != "ON":
        return False, {
            "status": "error",
            "message": (
                "현재 MODE가 OFF입니다. NotebookLM MCP 기능을 사용하려면\n"
                "set_mode(mode='ON', notebook_url='...')로 먼저 ON으로 전환하세요."
            ),
        }
    if not config.get("notebook_url"):
        return False, {
            "status": "error",
            "message": "notebook_url이 설정되지 않았습니다. set_mode로 URL을 설정해주세요.",
        }
    return True, None


def _get_report_files() -> list[str]:
    """reports/ 폴더의 마크다운 파일 목록을 반환합니다."""
    pattern = os.path.join(_REPORTS_DIR, "*.md")
    files   = sorted(glob.glob(pattern))
    # _index.md 제외
    return [f for f in files if not os.path.basename(f).startswith("_")]


# ════════════════════════════════════════════════════
# upload_reports tool
# ════════════════════════════════════════════════════

def run_upload_reports() -> dict:
    """
    reports/ 폴더의 마크다운 파일 목록을 반환하고
    NotebookLM 업로드를 위한 안내를 제공합니다.

    MODE가 OFF이면 에러를 반환합니다.
    실제 업로드는 notebooklm-mcp MCP 서버(외부)가 수행합니다.
    이 tool은 업로드 대상 파일 목록과 notebook_url을 확인하는 역할입니다.

    Returns:
        {
          "status": "ok",
          "notebook_url": "...",
          "files_to_upload": [...],
          "instruction": "..."  ← Antigravity가 notebooklm-mcp에 전달할 지시
        }
    """
    is_on, err = _check_mode_on()
    if not is_on:
        assert err is not None
        return err

    config       = _load_config()
    notebook_url = config["notebook_url"]
    report_files = _get_report_files()

    if not report_files:
        return {
            "status":  "error",
            "message": f"reports/ 폴더에 업로드할 마크다운 파일이 없습니다. 경로: {_REPORTS_DIR}",
        }

    # 업로드 시간 기록
    config["last_upload"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    _save_config(config)

    return {
        "status":         "ok",
        "notebook_url":   notebook_url,
        "files_to_upload": report_files,
        "file_count":     len(report_files),
        "instruction": (
            f"NotebookLM({notebook_url})에 다음 {len(report_files)}개 파일을 소스로 추가하세요:\n"
            + "\n".join(f"  - {os.path.basename(f)}" for f in report_files)
        ),
        "note": (
            "실제 업로드는 notebooklm-mcp MCP 서버를 통해 수행됩니다. "
            "Antigravity가 notebooklm-mcp의 add_source tool을 호출합니다."
        ),
    }


# ════════════════════════════════════════════════════
# query_notebooklm tool
# ════════════════════════════════════════════════════

def run_query_notebooklm(query: str) -> dict:
    """
    NotebookLM에 질문을 전송하기 위한 정보를 반환합니다.

    MODE가 OFF이면 에러를 반환합니다.
    실제 질의는 notebooklm-mcp MCP 서버(외부)가 수행합니다.

    Args:
        query: NotebookLM에게 보낼 질문 내용

    Returns:
        {
          "status": "ok",
          "query": "...",
          "notebook_url": "...",
          "instruction": "..."  ← Antigravity가 notebooklm-mcp에 전달할 지시
        }
    """
    is_on, err = _check_mode_on()
    if not is_on:
        assert err is not None
        return err

    if not query or not query.strip():
        return {
            "status":  "error",
            "message": "query가 비어있습니다. 질문 내용을 입력해주세요.",
        }

    config       = _load_config()
    notebook_url = config["notebook_url"]

    return {
        "status":       "ok",
        "query":        query.strip(),
        "notebook_url": notebook_url,
        "instruction": (
            f"NotebookLM({notebook_url})에 다음 질문을 전송하세요:\n"
            f'  "{query.strip()}"\n'
            "답변을 받은 후 인용 출처(날짜, 파일명)와 함께 반환해주세요."
        ),
        "note": (
            "notebooklm-mcp의 query_notebook tool을 호출하여 "
            "Gemini 2.5 기반 답변을 수신합니다."
        ),
    }


# ════════════════════════════════════════════════════
# compare_modes tool
# ════════════════════════════════════════════════════

def run_compare_modes(query: str) -> dict:
    """
    동일한 질문에 대해 두 모드의 답변 비교 구조를 반환합니다.

    - MODE OFF 결과: Antigravity가 reports/ 마크다운을 직접 분석한 결과
    - MODE ON 결과:  NotebookLM MCP를 통해 Gemini 2.5가 처리한 결과

    Args:
        query: 비교할 질문 내용

    Returns:
        {
          "status": "ok",
          "query": "...",
          "instructions": {
            "step1_off": "...",   ← Antigravity 직접 분석 지시
            "step2_on":  "...",   ← NotebookLM 질의 지시 (MODE ON인 경우)
            "step3_compare": "..."← 비교 리포트 작성 지시
          }
        }
    """
    if not query or not query.strip():
        return {
            "status":  "error",
            "message": "query가 비어있습니다. 비교할 질문 내용을 입력해주세요.",
        }

    config       = _load_config()
    current_mode = config.get("notebooklm_mode", "OFF")
    notebook_url = config.get("notebook_url", "")
    report_files = _get_report_files()

    # 비교용 출력 파일 경로
    compare_file = os.path.join(
        _OUTPUT_DIR,
        f"compare_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    )

    return {
        "status":       "ok",
        "query":        query.strip(),
        "current_mode": current_mode,
        "instructions": {
            "step1_off": (
                f"[MODE OFF - Antigravity 단독]\n"
                f"다음 파일들을 직접 분석하여 질문에 답하세요:\n"
                + "\n".join(f"  - {os.path.basename(f)}" for f in report_files)
                + f"\n\n질문: {query.strip()}"
            ),
            "step2_on": (
                f"[MODE ON - NotebookLM MCP]\n"
                + (
                    f"NotebookLM({notebook_url})에 동일한 질문을 전송하세요:\n"
                    f'  "{query.strip()}"'
                    if notebook_url else
                    "⚠️ notebook_url이 설정되지 않아 NotebookLM 질의를 건너뜁니다."
                )
            ),
            "step3_compare": (
                f"두 답변을 다음 형식으로 비교 리포트를 작성하고\n"
                f"{compare_file} 에 저장하세요:\n\n"
                "| 항목 | MODE OFF (Antigravity) | MODE ON (NotebookLM) |\n"
                "|------|----------------------|--------------------|\n"
                "| 응답 내용 | ... | ... |\n"
                "| 인용 출처 | 없음 | 날짜/파일명 |\n"
                "| 답변 깊이 | ... | ... |\n"
                "| 특이사항 | ... | ... |"
            ),
        },
        "output_file": compare_file,
    }
