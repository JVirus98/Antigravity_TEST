# -*- coding: utf-8 -*-
"""
notebooklm MCP Server
=====================
NotebookLM MCP ON/OFF 전환 및 보고서 연동 도구를 MCP 프로토콜로 노출합니다.
outlook_mcp/server.py 와 동일한 패턴으로 구성되어 있습니다.

실행:
  python notebooklm_mcp/server.py

MCP 설정 (.gemini/settings.json 또는 AG_RULES.md):
  {
    "mcpServers": {
      "notebooklm": {
        "command": "python",
        "args": ["c:/TEST/dailyreport/notebooklm_mcp/server.py"]
      }
    }
  }

제공 Tools:
  [모드 관리]
  - get_mode            : 현재 ON/OFF 상태 및 설정 조회
  - set_mode            : ON 또는 OFF로 전환 (notebook_url 설정 포함)

  [NotebookLM 연동 - MODE ON 전용]
  - upload_reports      : reports/ 마크다운 파일 업로드 안내
  - query_notebooklm    : NotebookLM에 질문 전송 안내

  [비교]
  - compare_modes       : Antigravity(OFF) vs NotebookLM(ON) 결과 비교 구조 반환
"""

import json
import sys
import os

# 프로젝트 루트 경로 설정
_NLM_DIR = os.path.dirname(__file__)
_ROOT    = os.path.dirname(_NLM_DIR)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types

from notebooklm_mcp.tools.mode import (
    run_get_mode,
    run_set_mode,
)
from notebooklm_mcp.tools.notebooklm import (
    run_upload_reports,
    run_query_notebooklm,
    run_compare_modes,
)

# ────────────────────────────────────────────────
# 서버 생성
# ────────────────────────────────────────────────
server = Server("notebooklm")


# ════════════════════════════════════════════════
# Tool 목록 정의
# ════════════════════════════════════════════════

@server.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        # ── 모드 관리 ─────────────────────────────
        types.Tool(
            name="get_mode",
            description=(
                "NotebookLM MCP 현재 모드(ON/OFF)와 설정 상태를 조회합니다. "
                "OFF: Antigravity 단독 처리 | ON: NotebookLM MCP 경유 처리"
            ),
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
        types.Tool(
            name="set_mode",
            description=(
                "NotebookLM MCP 모드를 ON 또는 OFF로 전환합니다. "
                "ON으로 전환 시 notebook_url(NotebookLM 노트북 URL)을 함께 설정하세요."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "mode": {
                        "type": "string",
                        "description": "전환할 모드: 'ON' 또는 'OFF'",
                        "enum": ["ON", "OFF", "on", "off"],
                    },
                    "notebook_url": {
                        "type": "string",
                        "description": "연동할 NotebookLM 노트북 URL (ON 모드 시 필수)",
                    },
                },
                "required": ["mode"],
            },
        ),
        # ── NotebookLM 연동 (MODE ON 전용) ────────
        types.Tool(
            name="upload_reports",
            description=(
                "[MODE ON 전용] reports/ 폴더의 마크다운 파일을 "
                "NotebookLM 소스로 업로드하기 위한 파일 목록과 안내를 반환합니다. "
                "실제 업로드는 notebooklm-mcp MCP 서버가 수행합니다."
            ),
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
        types.Tool(
            name="query_notebooklm",
            description=(
                "[MODE ON 전용] NotebookLM에 질문을 전송하기 위한 정보를 반환합니다. "
                "Gemini 2.5 기반으로 보고서 내용에 근거한 인용 출처 포함 답변을 받습니다."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "NotebookLM에게 보낼 질문 내용",
                    }
                },
                "required": ["query"],
            },
        ),
        # ── 비교 ──────────────────────────────────
        types.Tool(
            name="compare_modes",
            description=(
                "동일한 질문에 대해 MODE OFF(Antigravity 단독)와 "
                "MODE ON(NotebookLM MCP) 결과를 나란히 비교하는 구조를 반환합니다. "
                "두 방식의 답변 품질, 인용 출처, 깊이를 비교할 때 사용하세요."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "두 모드로 비교할 질문 내용",
                    }
                },
                "required": ["query"],
            },
        ),
    ]


# ════════════════════════════════════════════════
# Tool 실행 핸들러
# ════════════════════════════════════════════════

@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    try:
        if name == "get_mode":
            result = run_get_mode()

        elif name == "set_mode":
            result = run_set_mode(
                mode=arguments.get("mode", "OFF"),
                notebook_url=arguments.get("notebook_url"),
            )

        elif name == "upload_reports":
            result = run_upload_reports()

        elif name == "query_notebooklm":
            result = run_query_notebooklm(
                query=arguments.get("query", "")
            )

        elif name == "compare_modes":
            result = run_compare_modes(
                query=arguments.get("query", "")
            )

        else:
            result = {"status": "error", "message": f"알 수 없는 tool: {name}"}

    except Exception as e:
        result = {"status": "error", "message": str(e)}

    return [types.TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]


# ════════════════════════════════════════════════
# 메인 진입점
# ════════════════════════════════════════════════

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
