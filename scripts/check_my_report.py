# -*- coding: utf-8 -*-
"""
김정균 팀원 본인의 일일보고를 확인하는 스크립트
- 검색 범위: 전체 폴더 (즐겨찾기 보낸편지함 포함)
- 필터: 제목에 '김정균' 포함인 일일보고
- 날짜: 기본값 어제 (--date 인자로 지정 가능)
- 결과: UTF-8 파일로 저장

사용법:
  python check_my_report.py              → 어제 일일보고 확인
  python check_my_report.py --date 2026-02-20  → 특정 날짜 확인
"""

import sys
import os
import argparse
from datetime import datetime, timedelta

from outlook_utils import get_body, connect_outlook

# ── 설정 ─────────────────────────────────────────
MY_NAME     = "김정균"
OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "..", "output", "my_daily_report.txt")
# ────────────────────────────────────────────────


def is_my_report(item) -> bool:
    """
    본인(김정균) 일일보고인지 판단합니다.
    제목에 '김정균'이 포함되어 있으면 True를 반환합니다.
    """
    try:
        subject = item.Subject or ''
        return MY_NAME in subject
    except Exception:
        return False


def search_folder(folder, folder_path: str, results: list, log_lines: list, target_date: str):
    """
    Outlook 폴더와 하위 폴더를 재귀 탐색하여 본인 일일보고를 검색합니다.

    Args:
        folder      : Outlook MAPI 폴더 COM 객체
        folder_path : 현재 폴더 경로 (로그 표시용)
        results     : 발견된 메일을 누적할 리스트
        log_lines   : 탐색 로그를 누적할 리스트
        target_date : 조회 대상 날짜 문자열 (YYYY-MM-DD)
    """
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
                if not is_my_report(item):
                    continue

                body      = get_body(item)
                sent_time = item.SentOn.strftime("%Y-%m-%d %H:%M:%S")

                results.append({
                    "folder":    folder_path,
                    "subject":   item.Subject or "(제목없음)",
                    "sender":    getattr(item, 'SenderName', 'N/A'),
                    "sent_time": sent_time,
                    "body":      body,
                })
                log_lines.append(f"  ✔ 발견: [{sent_time}] {item.Subject} (폴더: {folder_path})")

            except Exception:
                continue

    except Exception:
        pass

    # 하위 폴더 재귀 탐색
    try:
        for subfolder in folder.Folders:
            search_folder(subfolder, f"{folder_path}/{subfolder.Name}", results, log_lines, target_date)
    except Exception:
        pass


def explore_favorites(namespace, log_lines: list) -> list:
    """
    Outlook 즐겨찾기(FavoritesFolders) 목록과 경로를 출력하고
    즐겨찾기에 등록된 MAPI 폴더 목록을 반환합니다.
    """
    fav_folders = []
    log_lines.append("\n[즐겨찾기 폴더 목록]")
    try:
        nav = namespace.Application.ActiveExplorer().NavigationPane
        for module in nav.Modules:
            try:
                module_name = module.Name
                if hasattr(module, 'NavigationGroups'):
                    for group in module.NavigationGroups:
                        try:
                            for nav_folder in group.NavigationFolders:
                                try:
                                    mapi_folder = nav_folder.Folder
                                    path = getattr(mapi_folder, 'FolderPath', nav_folder.DisplayName)
                                    log_lines.append(f"  📁 [{module_name}] {nav_folder.DisplayName} -> {path}")
                                    fav_folders.append(mapi_folder)
                                except Exception:
                                    pass
                        except Exception:
                            pass
            except Exception:
                pass
    except Exception as e:
        log_lines.append(f"  (즐겨찾기 탐색 실패: {e})")

    return fav_folders


if __name__ == "__main__":
    # ── 인자 파싱 ────────────────────────────────────
    parser = argparse.ArgumentParser(description="본인 일일보고 확인")
    parser.add_argument(
        "--date", "-d",
        type=str,
        default=None,
        help="조회 날짜 (YYYY-MM-DD 형식, 기본값: 어제)",
    )
    args = parser.parse_args()

    # 날짜 결정: 지정 없으면 자동으로 어제
    if args.date:
        TARGET_DATE = args.date
    else:
        TARGET_DATE = (datetime.today() - timedelta(days=1)).strftime("%Y-%m-%d")

    print(f"조회 대상 날짜: {TARGET_DATE}")
    print("Outlook 연결 중...")

    _, namespace = connect_outlook()

    results   = []
    log_lines = []

    # ── 1. 즐겨찾기 폴더 탐색 ─────────────────────
    log_lines.append("=" * 70)
    log_lines.append("[1] 즐겨찾기(Favorites) 폴더 탐색")
    log_lines.append("=" * 70)
    fav_folders = explore_favorites(namespace, log_lines)

    # ── 2. 즐겨찾기 폴더에서 본인 일일보고 검색 ───
    log_lines.append(f"\n[2] 즐겨찾기 폴더에서 '{MY_NAME}' 일일보고 검색 ({TARGET_DATE})")
    for mapi_folder in fav_folders:
        try:
            path = getattr(mapi_folder, 'FolderPath', '(알 수 없음)')
            search_folder(mapi_folder, path, results, log_lines, TARGET_DATE)
        except Exception:
            pass

    # ── 3. 전체 폴더에서도 본인 일일보고 검색 ─────
    log_lines.append(f"\n[3] 전체 폴더에서 '{MY_NAME}' 일일보고 검색 ({TARGET_DATE})")
    for store in namespace.Stores:
        try:
            root = store.GetRootFolder()
            search_folder(root, root.Name, results, log_lines, TARGET_DATE)
        except Exception:
            continue

    # ── 중복 제거 ──────────────────────────────────
    seen   = set()
    unique = []
    for r in results:
        key = (r["subject"], r["sent_time"])
        if key not in seen:
            seen.add(key)
            unique.append(r)
    unique.sort(key=lambda x: x["sent_time"], reverse=True)

    # ── 파일 저장 ──────────────────────────────────
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(log_lines) + "\n\n")

        f.write("=" * 70 + "\n")
        f.write(f"[결과] '{MY_NAME}' 일일보고 ({TARGET_DATE}) - 총 {len(unique)}건\n")
        f.write("=" * 70 + "\n\n")

        if not unique:
            f.write(f"({TARGET_DATE}) '{MY_NAME}' 일일보고를 찾지 못했습니다.\n")
            f.write("(Outlook이 실행 중인지, 해당 날짜에 발송한 메일이 있는지 확인하세요.)\n")
        else:
            for idx, r in enumerate(unique, 1):
                f.write("=" * 70 + "\n")
                f.write(f"[{idx}] {r['sent_time']} | {r['subject']}\n")
                f.write(f"폴더: {r['folder']}\n")
                f.write(f"보낸이: {r['sender']}\n")
                f.write("-" * 70 + "\n")
                f.write("[본문]\n")
                f.write(r["body"] + "\n\n")
        f.write("=" * 70 + "\n")

    print(f"완료! 총 {len(unique)}건 -> {OUTPUT_FILE}")
