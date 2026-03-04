# -*- coding: utf-8 -*-
"""
tools/reports.py — 일일보고 RAG 아카이브 MCP 도구 모음

포함 tool:
  - save_reports     : 현재 반기 파일에 신규 일일보고 추가 (기본 증분 모드)
  - force_reports    : 현재 반기 파일 전체 재생성 (--force 모드)
  - read_report_index: reports/_index.md 내용 반환
  - read_daily_draft : output/daily_report_draft.txt 내용 반환
"""

import os
import sys
from datetime import date as dt

# 프로젝트 루트 및 scripts/ 경로 설정
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
_SCRIPTS = os.path.join(_ROOT, "scripts")
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

from outlook_utils import connect_outlook

# ── 설정 ─────────────────────────────────────────
REPORTS_DIR        = os.path.join(_ROOT, "reports")
DRAFT_FILE         = os.path.join(_ROOT, "output", "daily_report_draft.txt")
WEEKLY_REPORT_DIR  = os.path.join(_ROOT, "output")
# ────────────────────────────────────────────────


def _import_save_all():
    """save_all_reports.py의 내부 함수를 동적 임포트합니다."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "save_all_reports",
        os.path.join(_ROOT, "scripts", "save_all_reports.py")
    )
    mod = importlib.util.load_from_spec(spec)  # type: ignore
    spec.loader.exec_module(mod)  # type: ignore
    return mod


def run_save_reports(force: bool = False) -> dict:
    """
    Outlook에서 일일보고를 조회하여 반기별 RAG 아카이브(reports/YYYY_H?.md)에 저장합니다.

    Args:
        force: True이면 현재 반기 전체 재생성 (--force), False이면 증분 추가

    Returns:
        {"status": "ok", "mode": ..., "period": ..., "new_count": ..., "file": ...}
    """
    import importlib.util, types

    # save_all_reports.py를 모듈로 로드 (sys.argv 오염 없이)
    spec = importlib.util.spec_from_file_location(
        "save_all_reports",
        os.path.join(_ROOT, "scripts", "save_all_reports.py")
    )
    mod = types.ModuleType("save_all_reports")
    spec.loader.exec_module(mod)  # type: ignore

    # sys.argv 임시 조작 없이 직접 함수 호출
    _, namespace = connect_outlook()

    cp = mod.current_period()
    period_file = cp["fname"]
    os.makedirs(REPORTS_DIR, exist_ok=True)

    if force:
        skip_dates = set()
        mode_label = "force (전체 재생성)"
    else:
        skip_dates = mod.get_saved_dates(period_file)
        mode_label = f"증분 (기존 {len(skip_dates)}건 스킵)"

    reports = mod.search_period_from_outlook(
        namespace,
        start_date=cp["start"],
        end_date=dt.today().strftime("%Y-%m-%d"),
        skip_dates=skip_dates,
    )

    new_count = len(reports)
    if not reports:
        return {
            "status": "ok",
            "mode":   mode_label,
            "period": cp["key"],
            "new_count": 0,
            "message": "새로운 일일보고가 없습니다.",
            "file":   period_file,
        }

    if force:
        content = mod.make_period_header(cp, new_count)
        for r in reports:
            content += mod.report_to_md_block(r)
        with open(period_file, "w", encoding="utf-8") as f:
            f.write(content)
    else:
        if not os.path.exists(period_file):
            content = mod.make_period_header(cp, new_count)
            for r in reports:
                content += mod.report_to_md_block(r)
            with open(period_file, "w", encoding="utf-8") as f:
                f.write(content)
        else:
            with open(period_file, "a", encoding="utf-8") as f:
                for r in reports:
                    f.write(mod.report_to_md_block(r))

    mod.update_index()
    fsize = os.path.getsize(period_file) / 1024

    return {
        "status":    "ok",
        "mode":      mode_label,
        "period":    cp["key"],
        "new_count": new_count,
        "file":      period_file,
        "file_size_kb": round(fsize, 1),
        "added_dates": [r["sent_time"][:10] for r in reports],
    }


def run_read_report_index() -> dict:
    """
    reports/_index.md 파일을 읽어 반기별 아카이브 목록을 반환합니다.

    Returns:
        {"status": "ok", "content": "...", "file": "..."}
    """
    index_file = os.path.join(REPORTS_DIR, "_index.md")
    if not os.path.exists(index_file):
        return {
            "status": "error",
            "message": "_index.md 파일이 없습니다. save_reports를 먼저 실행하세요.",
        }
    with open(index_file, "r", encoding="utf-8") as f:
        content = f.read()
    return {
        "status":  "ok",
        "content": content,
        "file":    index_file,
    }


def run_read_daily_draft() -> dict:
    """
    output/daily_report_draft.txt (AI 작성 일일보고 초안)을 읽어 반환합니다.

    Returns:
        {"status": "ok", "content": "...", "file": "..."}
    """
    if not os.path.exists(DRAFT_FILE):
        return {
            "status": "error",
            "message": "daily_report_draft.txt 파일이 없습니다.",
        }
    with open(DRAFT_FILE, "r", encoding="utf-8") as f:
        content = f.read()
    return {
        "status":  "ok",
        "content": content,
        "file":    DRAFT_FILE,
    }


def run_read_weekly_report(week: str | None = None) -> dict:
    """
    output/weekly_report_YYYY-WNN.md 파일을 읽어 반환합니다.

    Args:
        week: 'YYYY-WNN' 형식 (예: '2026-W09'). None이면 최신 파일 자동 선택.

    Returns:
        {"status": "ok", "content": "...", "file": "..."}
    """
    import glob

    pattern = os.path.join(WEEKLY_REPORT_DIR, "weekly_report_*.md")
    files   = sorted(glob.glob(pattern), reverse=True)

    if not files:
        return {"status": "error", "message": "주간보고 파일이 없습니다."}

    if week:
        target_name = f"weekly_report_{week}.md"
        target_file = os.path.join(WEEKLY_REPORT_DIR, target_name)
        if not os.path.exists(target_file):
            return {"status": "error", "message": f"{target_name} 파일을 찾을 수 없습니다."}
    else:
        target_file = files[0]  # 최신 파일

    with open(target_file, "r", encoding="utf-8") as f:
        content = f.read()

    return {
        "status":  "ok",
        "content": content,
        "file":    target_file,
    }
