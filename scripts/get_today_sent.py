# -*- coding: utf-8 -*-
"""
오늘 보낸 편지함에서 발송한 메일을 조회하는 스크립트
- 검색 범위: 즐겨찾기 보낸 편지함 (+ 기본 보낸 편지함 fallback)
- 날짜: 기본값 오늘 (--date 인자로 특정 날짜 지정 가능)
- 결과: UTF-8 MD 파일(today_sent.md)로 저장 (일일보고 작성 참고용)

사용법:
  python get_today_sent.py                  → 오늘 보낸 메일 조회
  python get_today_sent.py --date 2026-02-25  → 특정 날짜 조회
"""

import os
import sys
import argparse
from datetime import datetime, timedelta

from outlook_utils import get_body, get_recipients, connect_outlook, get_favorites_folder

# ── 설정 ─────────────────────────────────────────
OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "..", "output", "today_sent.md")
# ────────────────────────────────────────────────


def search_sent_folder(folder, folder_path: str, results: list, seen: set, target_date: str):
    """
    보낸편지함 폴더에서 대상 날짜에 발송한 메일을 수집합니다.

    Args:
        folder      : Outlook MAPI 폴더 COM 객체
        folder_path : 현재 폴더 경로 (기록용)
        results     : 발견된 메일을 누적할 리스트
        seen        : 중복 방지용 (subject, sent_time) 집합
        target_date : 조회 대상 날짜 문자열 (YYYY-MM-DD)
    """
    try:
        items = folder.Items
        items.Sort("[SentOn]", Descending=True)

        for item in items:
            try:
                sent_date = item.SentOn.strftime("%Y-%m-%d")
                # 최신순 정렬이므로 대상 날짜 이전 시점에서 중단
                if sent_date < target_date:
                    break
                if sent_date != target_date:
                    continue

                subject  = item.Subject or "(제목없음)"
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

    # 하위 폴더 탐색
    try:
        for subfolder in folder.Folders:
            search_sent_folder(subfolder, f"{folder_path}/{subfolder.Name}", results, seen, target_date)
    except Exception:
        pass


def save_as_markdown(results: list, target_date: str):
    """
    수집한 메일 목록을 Markdown 형식으로 OUTPUT_FILE에 저장합니다.

    Args:
        results     : 메일 정보 dict 리스트
        target_date : 조회 날짜 문자열 (YYYY-MM-DD)
    """
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(f"# 📤 {target_date} 보낸 메일 목록\n\n")
        f.write(f"> 총 **{len(results)}건** | 일일보고 작성 참고용\n\n")

        if not results:
            f.write(f"({target_date}) 보낸 메일이 없습니다.\n")
            return

        # 목차
        f.write("## 📑 목차\n\n")
        for idx, r in enumerate(results, 1):
            f.write(f"{idx}. [{r['sent_time'][11:16]}] {r['subject']}\n")
        f.write("\n---\n\n")

        # 본문
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


if __name__ == "__main__":
    # ── 인자 파싱 ────────────────────────────────────
    parser = argparse.ArgumentParser(description="오늘(또는 특정 날짜) 보낸 메일 조회 → today_sent.md 저장")
    parser.add_argument(
        "--date", "-d",
        type=str,
        default=None,
        help="조회 날짜 (YYYY-MM-DD 형식, 기본값: 오늘)",
    )
    args = parser.parse_args()

    # 날짜 결정: 지정 없으면 오늘 자동 계산
    TARGET_DATE = args.date if args.date else datetime.today().strftime("%Y-%m-%d")

    print(f"조회 대상 날짜: {TARGET_DATE}")
    print("Outlook 연결 중...")

    _, namespace = connect_outlook()

    results: list = []
    seen:    set  = set()

    # ── 1. 즐겨찾기 보낸 편지함 탐색 ──────────────
    print(f"\n[1] 즐겨찾기 보낸편지함에서 {TARGET_DATE} 발송 메일 검색...")
    fav_folder, fav_path = get_favorites_folder(namespace, '보낸')
    if fav_folder:
        print(f"  [OK] 즐겨찾기 보낸편지함 발견: {fav_path}")
        search_sent_folder(fav_folder, fav_path, results, seen, TARGET_DATE)
        print(f"    -> {len(results)}건 수집")
    else:
        print("    즐겨찾기 보낸편지함을 찾지 못했습니다.")

    # ── 2. 기본 보낸 편지함 Fallback ──────────────
    print(f"\n[2] 기본 보낸편지함(olFolderSentMail)에서도 검색...")
    try:
        sent_folder  = namespace.GetDefaultFolder(5)   # olFolderSentMail = 5
        before_count = len(results)
        search_sent_folder(sent_folder, sent_folder.FolderPath, results, seen, TARGET_DATE)
        print(f"    → {len(results) - before_count}건 추가 수집")
    except Exception as e:
        print(f"    기본 보낸편지함 탐색 실패: {e}")

    results.sort(key=lambda x: x["sent_time"])

    # ── MD 파일로 저장 ─────────────────────────────
    save_as_markdown(results, TARGET_DATE)
    print(f"\n[완료] 총 {len(results)}건 저장 -> {OUTPUT_FILE}")
