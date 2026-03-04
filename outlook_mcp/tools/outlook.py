# -*- coding: utf-8 -*-
"""
tools/outlook.py — Outlook 메일 조회 MCP 도구 모음

포함 tool:
  - get_today_sent    : 오늘(또는 특정 날짜) 보낸 메일 조회 → today_sent.md 저장
  - get_sent_emails   : 특정 날짜 보낸 메일 목록 반환 (JSON 친화적)
  - check_my_report   : 본인(김정균) 일일보고 확인 → my_daily_report.txt 저장
"""

import os
import sys
from datetime import datetime, timedelta

# 프로젝트 루트 및 scripts/ 경로 설정 (outlook_utils 임포트를 위해)
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
_SCRIPTS = os.path.join(_ROOT, "scripts")
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

from outlook_utils import get_body, get_recipients, connect_outlook, get_favorites_folder

# ── 설정 ─────────────────────────────────────────
MY_NAME     = "김정균"
OUTPUT_DIR  = os.path.join(_ROOT, "output")
TODAY_SENT_FILE = os.path.join(_ROOT, "today_sent.md")
MY_REPORT_FILE  = os.path.join(_ROOT, "my_daily_report.txt")
# ────────────────────────────────────────────────


# ════════════════════════════════════════════════
# get_today_sent tool
# ════════════════════════════════════════════════

def _search_sent_folder(folder, folder_path: str, results: list, seen: set, target_date: str):
    """보낸편지함 폴더에서 대상 날짜에 발송한 메일을 수집합니다."""
    try:
        items = folder.Items
        items.Sort("[SentOn]", Descending=True)
        for item in items:
            try:
                sent_date = item.SentOn.strftime("%Y-%m-%d")
                if sent_date < target_date:
                    break
                if sent_date != target_date:
                    continue
                subject   = item.Subject or "(제목없음)"
                sent_time = item.SentOn.strftime("%Y-%m-%d %H:%M:%S")
                key = (subject, sent_time)
                if key in seen:
                    continue
                seen.add(key)
                results.append({
                    "folder":    folder_path,
                    "subject":   subject,
                    "to":        ", ".join(get_recipients(item)),
                    "sent_time": sent_time,
                    "body":      get_body(item),
                })
            except Exception:
                continue
    except Exception:
        pass
    try:
        for subfolder in folder.Folders:
            _search_sent_folder(subfolder, f"{folder_path}/{subfolder.Name}", results, seen, target_date)
    except Exception:
        pass


def _save_today_sent_md(results: list, target_date: str) -> str:
    """수집한 메일을 today_sent.md로 저장하고 경로를 반환합니다."""
    with open(TODAY_SENT_FILE, "w", encoding="utf-8") as f:
        f.write(f"# 📤 {target_date} 보낸 메일 목록\n\n")
        f.write(f"> 총 **{len(results)}건** | 일일보고 작성 참고용\n\n")
        if not results:
            f.write(f"({target_date}) 보낸 메일이 없습니다.\n")
            return TODAY_SENT_FILE
        f.write("## 📑 목차\n\n")
        for idx, r in enumerate(results, 1):
            f.write(f"{idx}. [{r['sent_time'][11:16]}] {r['subject']}\n")
        f.write("\n---\n\n")
        for idx, r in enumerate(results, 1):
            f.write(f"## [{idx}] {r['sent_time'][11:16]} | {r['subject']}\n\n")
            f.write(f"- **발송 시각**: `{r['sent_time']}`\n")
            if r['to']:
                f.write(f"- **수신자**: {r['to']}\n")
            f.write(f"- **폴더**: `{r['folder']}`\n\n")
            f.write("### 📝 본문\n\n")
            for line in r["body"].splitlines():
                f.write(f"> {line}\n" if line.strip() else ">\n")
            f.write("\n---\n\n")
    return TODAY_SENT_FILE


def run_get_today_sent(date: str | None = None) -> dict:
    """
    오늘(또는 특정 날짜) 보낸 메일을 조회하여 today_sent.md로 저장합니다.

    Args:
        date: 조회 날짜 (YYYY-MM-DD 형식, None이면 오늘)

    Returns:
        {"status": "ok", "date": ..., "count": ..., "file": ...}
    """
    target_date = date if date else datetime.today().strftime("%Y-%m-%d")

    _, namespace = connect_outlook()

    results: list = []
    seen:    set  = set()

    # 1. 즐겨찾기 보낸 편지함
    fav_folder, fav_path = get_favorites_folder(namespace, "보낸")
    if fav_folder:
        _search_sent_folder(fav_folder, fav_path, results, seen, target_date)

    # 2. 기본 보낸 편지함 fallback
    try:
        sent_folder = namespace.GetDefaultFolder(5)
        _search_sent_folder(sent_folder, sent_folder.FolderPath, results, seen, target_date)
    except Exception:
        pass

    results.sort(key=lambda x: x["sent_time"])
    file_path = _save_today_sent_md(results, target_date)

    return {
        "status": "ok",
        "date":   target_date,
        "count":  len(results),
        "file":   file_path,
        "subjects": [r["subject"] for r in results],
    }


# ════════════════════════════════════════════════
# get_sent_emails tool
# ════════════════════════════════════════════════

def run_get_sent_emails(date: str | None = None, max_body_length: int = 500) -> dict:
    """
    Outlook 보낸 메일함에서 특정 날짜의 메일 목록을 반환합니다.

    Args:
        date: 조회할 날짜 (YYYY-MM-DD, None이면 오늘)
        max_body_length: 본문 미리보기 최대 길이

    Returns:
        {"status": "ok", "date": ..., "count": ..., "emails": [...]}
    """
    import datetime as dt_mod
    from outlook_utils import strip_html

    if date:
        target_date = dt_mod.datetime.strptime(date, "%Y-%m-%d").date()
    else:
        target_date = dt_mod.date.today()

    _, namespace = connect_outlook()
    sent_folder  = namespace.GetDefaultFolder(5)

    start_str = target_date.strftime("%m/%d/%Y")
    end_str   = (target_date + dt_mod.timedelta(days=1)).strftime("%m/%d/%Y")
    filter_str = f"[SentOn] >= '{start_str}' AND [SentOn] < '{end_str}'"

    items = sent_folder.Items
    items.Sort("[SentOn]", Descending=True)
    filtered = items.Restrict(filter_str)

    emails = []
    for item in filtered:
        try:
            recipients = []
            for i in range(1, item.Recipients.Count + 1):
                recipients.append(item.Recipients.Item(i).Name)

            body = item.Body if item.Body else ""
            if not body and item.HTMLBody:
                body = strip_html(item.HTMLBody)
            body_preview = body[:max_body_length] + ("..." if len(body) > max_body_length else "")

            attachments = []
            for j in range(1, item.Attachments.Count + 1):
                attachments.append(item.Attachments.Item(j).FileName)

            emails.append({
                "subject":      item.Subject or "(제목 없음)",
                "to":           ", ".join(recipients),
                "sent_time":    item.SentOn.strftime("%Y-%m-%d %H:%M:%S"),
                "body_preview": body_preview,
                "attachments":  attachments,
                "importance":   ["낮음", "보통", "높음"][item.Importance],
            })
        except Exception:
            continue

    return {
        "status": "ok",
        "date":   str(target_date),
        "count":  len(emails),
        "emails": emails,
    }


# ════════════════════════════════════════════════
# check_my_report tool
# ════════════════════════════════════════════════

def _search_report_folder(folder, folder_path: str, results: list, target_date: str):
    """일일보고 폴더를 재귀 탐색하여 본인 보고를 수집합니다."""
    try:
        items = folder.Items
        items.Sort("[SentOn]", Descending=True)
        filter_str = "@SQL=\"urn:schemas:httpmail:subject\" LIKE '%일일보고%'"
        filtered = items.Restrict(filter_str)
        for item in filtered:
            try:
                sent_date = item.SentOn.strftime("%Y-%m-%d")
                if sent_date != target_date:
                    continue
                subject = item.Subject or ""
                if MY_NAME not in subject:
                    continue
                results.append({
                    "folder":    folder_path,
                    "subject":   subject,
                    "sender":    getattr(item, "SenderName", "N/A"),
                    "sent_time": item.SentOn.strftime("%Y-%m-%d %H:%M:%S"),
                    "body":      get_body(item),
                })
            except Exception:
                continue
    except Exception:
        pass
    try:
        for subfolder in folder.Folders:
            _search_report_folder(subfolder, f"{folder_path}/{subfolder.Name}", results, target_date)
    except Exception:
        pass


def run_check_my_report(date: str | None = None) -> dict:
    """
    본인(김정균) 일일보고를 Outlook에서 찾아 my_daily_report.txt로 저장합니다.

    Args:
        date: 조회 날짜 (YYYY-MM-DD, None이면 어제)

    Returns:
        {"status": "ok", "date": ..., "count": ..., "file": ..., "reports": [...]}
    """
    if date:
        target_date = date
    else:
        target_date = (datetime.today() - timedelta(days=1)).strftime("%Y-%m-%d")

    _, namespace = connect_outlook()
    results: list = []

    # 전체 폴더 탐색
    for store in namespace.Stores:
        try:
            root = store.GetRootFolder()
            _search_report_folder(root, root.Name, results, target_date)
        except Exception:
            continue

    # 중복 제거
    seen   = set()
    unique = []
    for r in results:
        key = (r["subject"], r["sent_time"])
        if key not in seen:
            seen.add(key)
            unique.append(r)
    unique.sort(key=lambda x: x["sent_time"], reverse=True)

    # 파일 저장
    with open(MY_REPORT_FILE, "w", encoding="utf-8") as f:
        f.write(f"{'='*70}\n")
        f.write(f"[결과] '{MY_NAME}' 일일보고 ({target_date}) - 총 {len(unique)}건\n")
        f.write(f"{'='*70}\n\n")
        if not unique:
            f.write(f"({target_date}) '{MY_NAME}' 일일보고를 찾지 못했습니다.\n")
        else:
            for idx, r in enumerate(unique, 1):
                f.write(f"{'='*70}\n")
                f.write(f"[{idx}] {r['sent_time']} | {r['subject']}\n")
                f.write(f"폴더: {r['folder']}\n보낸이: {r['sender']}\n")
                f.write(f"{'-'*70}\n[본문]\n{r['body']}\n\n")
        f.write(f"{'='*70}\n")

    return {
        "status": "ok",
        "date":   target_date,
        "count":  len(unique),
        "file":   MY_REPORT_FILE,
        "reports": [
            {"subject": r["subject"], "sent_time": r["sent_time"]}
            for r in unique
        ],
    }
