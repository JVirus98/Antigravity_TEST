# -*- coding: utf-8 -*-
"""
tools/mode.py — NotebookLM MCP ON/OFF 전환 도구

포함 tool:
  - get_mode : 현재 모드(ON/OFF) 및 설정 상태 조회
  - set_mode : ON 또는 OFF 로 전환 + notebook_url 설정
"""

import json
import os
from datetime import datetime

# ── 경로 설정 ─────────────────────────────────────────
_TOOLS_DIR  = os.path.dirname(__file__)
_NLM_DIR    = os.path.dirname(_TOOLS_DIR)
CONFIG_FILE = os.path.join(_NLM_DIR, "mode.config.json")
# ────────────────────────────────────────────────────


# ════════════════════════════════════════════════════
# 내부 유틸
# ════════════════════════════════════════════════════

def _load_config() -> dict:
    """mode.config.json을 읽어 반환합니다."""
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_config(config: dict) -> None:
    """mode.config.json에 설정을 저장합니다."""
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


# ════════════════════════════════════════════════════
# get_mode tool
# ════════════════════════════════════════════════════

def run_get_mode() -> dict:
    """
    현재 NotebookLM MCP 모드 및 설정 상태를 반환합니다.

    Returns:
        {
          "status": "ok",
          "mode": "OFF" | "ON",
          "notebook_url": "...",
          "last_switched": "...",
          "last_upload": "...",
          "description": "..."
        }
    """
    config = _load_config()
    mode   = config.get("notebooklm_mode", "OFF")

    return {
        "status":        "ok",
        "mode":          mode,
        "notebook_url":  config.get("notebook_url", ""),
        "last_switched": config.get("last_switched", ""),
        "last_upload":   config.get("last_upload", ""),
        "description":   config.get("description", {}).get(mode, ""),
        "summary": (
            f"[MODE: {mode}] "
            + ("NotebookLM MCP 활성화됨 ✅" if mode == "ON" else "Antigravity 단독 처리 중 🔵")
        ),
    }


# ════════════════════════════════════════════════════
# set_mode tool
# ════════════════════════════════════════════════════

def run_set_mode(mode: str, notebook_url: str | None = None) -> dict:
    """
    NotebookLM MCP 모드를 ON 또는 OFF로 전환합니다.

    Args:
        mode         : "ON" 또는 "OFF" (대소문자 무관)
        notebook_url : ON 모드 시 연동할 NotebookLM 노트북 URL (선택)

    Returns:
        {"status": "ok", "mode": "ON"|"OFF", "message": "..."}
    """
    mode = mode.upper().strip()
    if mode not in ("ON", "OFF"):
        return {
            "status":  "error",
            "message": f"mode는 'ON' 또는 'OFF'만 허용됩니다. 입력값: '{mode}'",
        }

    config = _load_config()
    prev_mode = config.get("notebooklm_mode", "OFF")

    config["notebooklm_mode"] = mode
    config["last_switched"]   = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if notebook_url:
        config["notebook_url"] = notebook_url.strip()

    # ON 전환 시 notebook_url 검증
    if mode == "ON" and not config.get("notebook_url"):
        return {
            "status":  "warning",
            "message": (
                "MODE를 ON으로 전환했지만 notebook_url이 설정되지 않았습니다. "
                "set_mode(mode='ON', notebook_url='https://notebooklm.google.com/...')로 "
                "URL을 설정해주세요."
            ),
            "mode": mode,
        }

    _save_config(config)

    return {
        "status":  "ok",
        "mode":    mode,
        "prev":    prev_mode,
        "message": (
            f"✅ MODE 전환 완료: {prev_mode} → {mode}\n"
            + (
                f"   NotebookLM URL: {config['notebook_url']}"
                if mode == "ON" else
                "   Antigravity 단독 처리 모드로 전환되었습니다."
            )
        ),
    }
