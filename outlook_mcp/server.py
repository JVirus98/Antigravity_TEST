# -*- coding: utf-8 -*-
"""
dailyreport MCP Server
======================
Outlook 메일 조회 + 일일/주간보고 관리 도구를 MCP 프로토콜로 노출합니다.

실행:
  python mcp/server.py

MCP 설정 (claude_desktop_config.json 또는 AG_RULES.md 등):
  {
    "mcpServers": {
      "dailyreport": {
        "command": "python",
        "args": ["c:/TEST/dailyreport/mcp/server.py"]
      }
    }
  }

제공 Tools:
  [Outlook]
  - get_today_sent      : 오늘(또는 특정 날짜) 보낸 메일 → today_sent.md 저장
  - get_sent_emails     : 특정 날짜 보낸 메일 목록 JSON 반환
  - check_my_report     : 본인 일일보고 확인 → my_daily_report.txt 저장

  [Reports]
  - save_reports        : 신규 일일보고를 RAG 아카이브에 증분 저장
  - force_reports       : 현재 반기 RAG 아카이브 전체 재생성
  - read_report_index   : reports/_index.md 반환
  - read_daily_draft    : output/daily_report_draft.txt 반환
  - read_weekly_report  : output/weekly_report_YYYY-WNN.md 반환
"""

import json
import sys
import os

# 프로젝트 루트 경로 설정
_MCP_DIR = os.path.dirname(__file__)
_ROOT    = os.path.dirname(_MCP_DIR)
_SCRIPTS = os.path.join(_ROOT, "scripts")
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types

from outlook_mcp.tools.outlook import (
    run_get_today_sent,
    run_get_sent_emails,
    run_check_my_report,
)
from outlook_mcp.tools.reports import (
    run_save_reports,
    run_read_report_index,
    run_read_daily_draft,
    run_read_weekly_report,
)

# ────────────────────────────────────────────────
# 서버 생성
# ────────────────────────────────────────────────
server = Server("dailyreport")


# ════════════════════════════════════════════════
# Tool 목록 정의
# ════════════════════════════════════════════════

@server.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        # ── Outlook 조회 ──────────────────────────
        types.Tool(
            name="get_today_sent",
            description=(
                "오늘(또는 특정 날짜) Outlook 보낸 메일을 조회하여 today_sent.md로 저장합니다. "
                "일일보고 초안 작성 전 업무 내역 정리에 사용하세요."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "조회 날짜 (YYYY-MM-DD 형식). 생략하면 오늘.",
                    }
                },
                "required": [],
            },
        ),
        types.Tool(
            name="get_sent_emails",
            description=(
                "특정 날짜에 Outlook 보낸 메일함에서 메일 목록을 JSON으로 반환합니다. "
                "제목, 수신자, 발송 시각, 본문 미리보기, 첨부파일 목록을 포함합니다."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "조회 날짜 (YYYY-MM-DD). 생략하면 오늘.",
                    },
                    "max_body_length": {
                        "type": "integer",
                        "description": "본문 미리보기 최대 길이 (기본값 500).",
                        "default": 500,
                    },
                },
                "required": [],
            },
        ),
        types.Tool(
            name="check_my_report",
            description=(
                "Outlook 전체 폴더에서 본인(김정균) 일일보고를 검색하여 "
                "my_daily_report.txt로 저장합니다. 기본값은 어제 날짜입니다."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "조회 날짜 (YYYY-MM-DD). 생략하면 어제.",
                    }
                },
                "required": [],
            },
        ),
        # ── 보고서 관리 ───────────────────────────
        types.Tool(
            name="save_reports",
            description=(
                "Outlook에서 신규 일일보고를 조회하여 반기별 RAG 아카이브 "
                "(reports/YYYY_H?.md)에 증분 저장합니다. "
                "매일 퇴근 후 1회 실행하세요."
            ),
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
        types.Tool(
            name="force_reports",
            description=(
                "현재 반기 RAG 아카이브를 Outlook에서 전체 재조회하여 재생성합니다. "
                "포맷 변경 후 기존 파일을 전면 갱신할 때 사용합니다."
            ),
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
        types.Tool(
            name="read_report_index",
            description=(
                "reports/_index.md 파일을 읽어 반기별 아카이브 목록과 상태를 반환합니다."
            ),
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
        types.Tool(
            name="read_daily_draft",
            description=(
                "output/daily_report_draft.txt (AI가 작성한 일일보고 초안)을 읽어 반환합니다. "
                "CRM 입력 전 검토 및 수정에 사용하세요."
            ),
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
        types.Tool(
            name="read_weekly_report",
            description=(
                "output/weekly_report_YYYY-WNN.md 파일을 읽어 반환합니다. "
                "week를 생략하면 가장 최신 주간보고를 반환합니다."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "week": {
                        "type": "string",
                        "description": "주차 지정 (YYYY-WNN 형식, 예: 2026-W09). 생략하면 최신.",
                    }
                },
                "required": [],
            },
        ),
    ]


# ════════════════════════════════════════════════
# Tool 실행 핸들러
# ════════════════════════════════════════════════

@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    try:
        if name == "get_today_sent":
            result = run_get_today_sent(date=arguments.get("date"))

        elif name == "get_sent_emails":
            result = run_get_sent_emails(
                date=arguments.get("date"),
                max_body_length=arguments.get("max_body_length", 500),
            )

        elif name == "check_my_report":
            result = run_check_my_report(date=arguments.get("date"))

        elif name == "save_reports":
            result = run_save_reports(force=False)

        elif name == "force_reports":
            result = run_save_reports(force=True)

        elif name == "read_report_index":
            result = run_read_report_index()

        elif name == "read_daily_draft":
            result = run_read_daily_draft()

        elif name == "read_weekly_report":
            result = run_read_weekly_report(week=arguments.get("week"))

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
