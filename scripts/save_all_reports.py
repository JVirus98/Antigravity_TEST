# -*- coding: utf-8 -*-
"""
김정균 일일보고 관리 스크립트 (반기별 저장 방식)

[데이터 출처]
  - Outlook "나의 일일보고" 폴더 안의 메일만 사용
  - 초안(daily_report_draft.txt) 은 사용하지 않음

[파일 구조]
  reports/2025_H1.md  → 2025년 상반기 (1~6월) - 완결, 수정 없음
  reports/2025_H2.md  → 2025년 하반기 (7~12월) - 완결, 수정 없음
  reports/2026_H1.md  → 2026년 상반기 (1~6월) - 현재 진행 중

[실행 모드]
  python save_all_reports.py            → 현재 반기 파일에 새 날짜만 추가
  python save_all_reports.py --init     → 기존 날짜별 MD 파일로 반기 파일 최초 생성
  python save_all_reports.py --force    → 현재 반기 파일 전체 재생성 (Outlook 재조회)
"""

import re
import sys
import os
import glob
from datetime import date as dt

from outlook_utils import strip_html, get_body, get_today_body, connect_outlook, get_favorites_folder

# ── 설정 ─────────────────────────────────────────
MY_NAME    = "김정균"
MY_TEAM    = "MSS팀"
MY_COMPANY = "MDS테크"
REPORTS_DIR = os.path.join(os.path.dirname(__file__), "..", "reports")

MODE_INIT  = "--init"  in sys.argv   # 기존 daily 파일 → 반기 파일 마이그레이션
MODE_FORCE = "--force" in sys.argv   # 현재 반기 전체 재생성
# ────────────────────────────────────────────────


# ════════════════════════════════════════════════
# 반기 유틸리티
# ════════════════════════════════════════════════

def get_period_info(date_str):
    """날짜 문자열 → 반기 정보 dict 반환"""
    year  = date_str[:4]
    month = int(date_str[5:7])
    half  = "H1" if month <= 6 else "H2"
    if half == "H1":
        label, start, end = "상반기 (1~6월)", f"{year}-01-01", f"{year}-06-30"
    else:
        label, start, end = "하반기 (7~12월)", f"{year}-07-01", f"{year}-12-31"
    return {
        "key":    f"{year}_{half}",
        "year":   year,
        "half":   half,
        "label":  f"{year}년 {label}",
        "start":  start,
        "end":    end,
        "fname":  os.path.join(REPORTS_DIR, f"{year}_{half}.md"),
    }


def current_period():
    """오늘 날짜 기준 현재 반기 정보 반환"""
    today = dt.today().strftime("%Y-%m-%d")
    return get_period_info(today)


def get_saved_dates(period_fname):
    """반기 MD 파일에서 이미 저장된 날짜 목록 추출"""
    if not os.path.exists(period_fname):
        return set()
    saved = set()
    with open(period_fname, "r", encoding="utf-8") as f:
        for line in f:
            # "- 날짜: 2026-02-25 (수)" 패턴에서 날짜 추출
            m = re.search(r'- 날짜: (\d{4}-\d{2}-\d{2})', line)
            if m:
                saved.add(m.group(1))
    return saved


# ════════════════════════════════════════════════
# Outlook 데이터 수집
# ════════════════════════════════════════════════

# strip_html, get_body 함수는 outlook_utils.py에서 임포트하여 사용합니다.


def find_my_report_folder(namespace):
    """
    Outlook에서 "나의 일일보고" 폴더를 찾아 반환합니다.
    탐색 순서:
      1) 즐겨찾기(NavigationPane)에서 '나의 일일보고' 폴더 탐색
      2) 모든 스토어의 루트 폴더에서 재귀적으로 폴더명 탐색
    반환: (folder 객체, 폴더 경로 문자열) or (None, None)
    """
    TARGET = "나의 일일보고"

    # ① 즐겨찾기 탐색 (가장 빠름)
    folder, path = get_favorites_folder(namespace, TARGET)
    if folder is not None:
        print(f"  [폴더 발견 - 즐겨찾기] {path}")
        return folder, path

    # ② 전체 스토어 재귀 탐색
    def _find(folder, folder_path):
        try:
            if TARGET in folder.Name:
                return folder, folder_path
        except Exception:
            pass
        try:
            for sub in folder.Folders:
                try:
                    sub_path = f"{folder_path}/{sub.Name}"
                    result = _find(sub, sub_path)
                    if result[0] is not None:
                        return result
                except Exception:
                    continue
        except Exception:
            pass
        return None, None

    for store in namespace.Stores:
        try:
            root = store.GetRootFolder()
            result_folder, result_path = _find(root, root.Name)
            if result_folder is not None:
                print(f"  [폴더 발견] {result_path}")
                return result_folder, result_path
        except Exception:
            continue

    print(f"  [경고] '{TARGET}' 폴더를 찾을 수 없습니다.")
    return None, None


def search_period_from_outlook(namespace, start_date, end_date, skip_dates=None):
    """
    Outlook "나의 일일보고" 폴더에서만 특정 기간 일일보고 수집.
    초안(draft)은 사용하지 않고, Outlook 폴더 기준으로만 가져옵니다.

    skip_dates: 이미 저장된 날짜 set (건너뜀)
    """
    if skip_dates is None:
        skip_dates = set()
    results = []
    seen    = set()

    folder, folder_path = find_my_report_folder(namespace)
    if folder is None:
        print("  [오류] '나의 일일보고' 폴더를 찾지 못해 저장을 건너뜁니다.")
        return results

    try:
        items = folder.Items
        items.Sort("[ReceivedTime]", Descending=False)
        for item in items:
            try:
                subject   = getattr(item, 'Subject', '') or ''
                # ① HTMLBody th 태그에서 '당일(YYYY-MM-DD)' 날짜 우선 추출
                #    예: <th>당일(2026-03-04)</th>
                sent_date = None
                try:
                    html = getattr(item, 'HTMLBody', '') or ''
                    if html:
                        m = re.search(
                            r'<th[^>]*>\s*당일\s*\((\d{4}-\d{2}-\d{2})\)',
                            html, re.IGNORECASE
                        )
                        if m:
                            sent_date = m.group(1)
                except Exception:
                    pass

                # ② th에서 못 찾으면 ReceivedTime 폴백
                if not sent_date:
                    try:
                        received = item.ReceivedTime
                    except Exception:
                        received = item.SentOn
                    sent_date = received.strftime("%Y-%m-%d")
                    print(f"  [경고] th 날짜 추출 실패 → ReceivedTime 사용: {sent_date} | {subject[:40]}")

                # ReceivedTime은 sent_time 기록용으로만 사용
                try:
                    received = item.ReceivedTime
                except Exception:
                    received = item.SentOn

                # 날짜 범위 필터
                if sent_date < start_date or sent_date > end_date:
                    continue
                # 이미 저장된 날짜 스킵
                if sent_date in skip_dates:
                    continue

                key = (subject, sent_date)
                if key in seen:
                    continue
                seen.add(key)

                results.append({
                    "folder":    folder_path,
                    "subject":   subject,
                    "sent_time": sent_date + " " + received.strftime("%H:%M:%S"),
                    "body":      get_today_body(item),
                })
            except Exception:
                continue
    except Exception as e:
        print(f"  [오류] 폴더 아이템 조회 실패: {e}")

    results.sort(key=lambda x: x["sent_time"])
    return results



# ════════════════════════════════════════════════
# RAG 파서
# ════════════════════════════════════════════════

WEEKDAYS = ['월', '화', '수', '목', '금', '토', '일']


def weekday_str(date_str):
    y, m, d = map(int, date_str.split("-"))
    return WEEKDAYS[dt(y, m, d).weekday()]


def parse_work_items(body):
    """본문 → 당일 업무 단위 list

    get_today_body()로 익일 컬럼이 이미 제거된 본문을 받으므로,
    단순히 섹션/업무 단위로 파싱만 수행합니다.
    """
    items = []
    lines = body.splitlines()
    cur_section = cur_title = cur_person = ""
    cur_details = []

    def flush():
        if not cur_title:
            return
        cleaned = [d.strip() for d in cur_details if d.strip() and d.strip() not in ('-', '*')]
        if cleaned or cur_person:
            items.append({
                "section": cur_section,
                "title":   cur_title.strip(),
                "person":  cur_person.strip(),
                "details": cleaned,
            })

    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        if MY_NAME in line and '일일보고' in line and '(' in line:
            continue
        if '당일' in line and '익일' in line:
            continue
        if MY_NAME in line and '팀원' in line and len(line) < 20:
            continue
        if line.startswith('※'):
            break
        if line.startswith('[') and line.endswith(']') and len(line) < 15:
            flush()
            cur_section = line[1:-1]
            cur_title = cur_person = ""
            cur_details = []
            continue
        if line.startswith('▶'):
            flush()
            cur_title   = line[1:].strip()
            cur_person  = ""
            cur_details = []
            continue
        if line.startswith('∙'):
            cur_person = line[1:].strip()
            continue
        if line.startswith('*') and not line.startswith('**'):
            sub = line[1:].strip()
            if sub:
                cur_details.append(f"[{sub}]")
            continue
        if line.startswith('-'):
            detail = line[1:].strip()
            if detail:
                cur_details.append(detail)
            continue
        if re.match(r'^\d+\.', line):
            cur_details.append(line)
            continue
        if line:
            cur_details.append(line)

    flush()
    return items


def report_to_md_block(report):
    """보고서 1개 → 마크다운 블록 (날짜 H1 + 업무 H2 청크들)"""
    date_str  = report["sent_time"][:10]
    sent_time = report["sent_time"]
    wd        = weekday_str(date_str)
    work_items = parse_work_items(report["body"])

    lines = []
    lines.append(f"# {MY_NAME} 일일보고 | {date_str} ({wd}) | {MY_TEAM}")
    lines.append("")

    if not work_items:
        lines.append("*(업무 내용 없음)*")
        lines.append("")
        return "\n".join(lines)

    for idx, item in enumerate(work_items, 1):
        lines.append(f"## 업무 기록 {idx} | [{item['section']}] {item['title']}")
        lines.append("")
        lines.append(f"- 날짜: {date_str} ({wd})")
        lines.append(f"- 담당자: {MY_NAME} ({MY_TEAM}, {MY_COMPANY})")
        lines.append(f"- 업무 유형: {item['section']}")
        lines.append(f"- 업무명: {item['title']}")
        if item['person']:
            lines.append(f"- 고객사/담당자: {item['person']}")
        if item['details']:
            lines.append("- 업무 상세:")
            for d in item['details']:
                if d.startswith('[') and d.endswith(']'):
                    lines.append(f"  - **{d[1:-1]}**")
                else:
                    lines.append(f"  - {d}")
        lines.append("")

    lines.append(f"<!-- end of {date_str} -->")
    lines.append("")
    lines.append("---")
    lines.append("")
    return "\n".join(lines)


def make_period_header(period_info, report_count):
    """반기 파일 헤더 생성"""
    lines = [
        "---",
        f"title: \"{MY_NAME} 일일보고 {period_info['label']}\"",
        f"period: \"{period_info['key']}\"",
        f"date_range: \"{period_info['start']} ~ {period_info['end']}\"",
        f"author: {MY_NAME}",
        f"team: {MY_TEAM}",
        f"company: {MY_COMPANY}",
        f"status: \"{'완결' if period_info['key'] != current_period()['key'] else '진행중'}\"",
        f"report_count: {report_count}",
        "note: \"RAG/NotebookLM 학습용 - 반기별 아카이브\"",
        "---",
        "",
        f"# {MY_NAME} 일일보고 | {period_info['label']} | {MY_TEAM}",
        "",
        f"> 기간: **{period_info['start']} ~ {period_info['end']}** | 총 **{report_count}건**",
        "",
        "---",
        "",
    ]
    return "\n".join(lines)


# ════════════════════════════════════════════════
# 메인 모드별 처리
# ════════════════════════════════════════════════

def mode_init():
    """
    --init: 기존 날짜별 MD 파일 → 반기 파일 마이그레이션
    Outlook 조회 없이 기존 reports/YYYY-MM-DD.md 파일들을 읽어서 반기별로 묶음
    """
    daily_files = sorted(glob.glob(os.path.join(REPORTS_DIR, "????-??-??.md")))
    if not daily_files:
        print("날짜별 MD 파일이 없습니다. 이미 마이그레이션 완료.")
        return

    print(f"날짜별 파일 {len(daily_files)}개를 반기별로 재구성합니다...")

    # 날짜 → 반기 그룹화
    period_groups = {}
    for fpath in daily_files:
        date_str = os.path.basename(fpath).replace(".md", "")
        pinfo = get_period_info(date_str)
        key = pinfo["key"]
        if key not in period_groups:
            period_groups[key] = {"info": pinfo, "files": []}
        period_groups[key]["files"].append(fpath)

    # 반기별 파일 생성
    for key in sorted(period_groups.keys()):
        group  = period_groups[key]
        pinfo  = group["info"]
        files  = sorted(group["files"])
        report_count = len(files)

        print(f"\n  [{key}] {pinfo['label']} - {report_count}건 처리 중...")

        period_file = pinfo["fname"]

        # 헤더 작성
        content_parts = [make_period_header(pinfo, report_count)]

        # 날짜별 내용 병합
        for fpath in files:
            with open(fpath, "r", encoding="utf-8") as f:
                day_content = f.read().strip()
            # YAML frontmatter 제거
            if day_content.startswith("---"):
                end_idx = day_content.find("---", 3)
                if end_idx != -1:
                    day_content = day_content[end_idx + 3:].strip()
            content_parts.append(day_content)
            content_parts.append("\n\n---\n\n")

        with open(period_file, "w", encoding="utf-8") as f:
            f.write("\n".join(content_parts))

        fsize = os.path.getsize(period_file) / 1024
        print(f"  -> {os.path.basename(period_file)} ({fsize:.1f} KB)")

    # 날짜별 파일 삭제
    print(f"\n날짜별 MD 파일 {len(daily_files)}개 삭제 중...")
    for fpath in daily_files:
        os.remove(fpath)
        print(f"  [삭제] {os.path.basename(fpath)}")

    # _all_reports.md 도 삭제 (반기별로 대체됨)
    all_file = os.path.join(REPORTS_DIR, "_all_reports.md")
    if os.path.exists(all_file):
        os.remove(all_file)
        print(f"  [삭제] _all_reports.md")

    print(f"\n마이그레이션 완료!")


def mode_update(namespace):
    """
    (기본): 현재 반기 파일에 새 날짜만 추가
    --force: 현재 반기 전체 재생성
    """
    cp = current_period()
    period_file = cp["fname"]

    if MODE_FORCE:
        skip_dates = set()
        print(f"[--force] {cp['label']} 전체 재생성 모드")
    else:
        skip_dates = get_saved_dates(period_file)
        print(f"[증분] {cp['label']} - 이미 저장된 날짜: {len(skip_dates)}건")

    print(f"Outlook에서 {cp['start']} ~ 오늘 범위 검색 중...")
    reports = search_period_from_outlook(
        namespace,
        start_date=cp["start"],
        end_date=dt.today().strftime("%Y-%m-%d"),
        skip_dates=skip_dates,
    )

    if not reports:
        print("새로운 일일보고가 없습니다.")
        return

    print(f"신규 {len(reports)}건 발견.")

    if MODE_FORCE:
        # 전체 재생성: 헤더 + 모든 보고서
        content = make_period_header(cp, len(reports))
        for r in reports:
            content += report_to_md_block(r)
        with open(period_file, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"[재생성] {os.path.basename(period_file)}")
    else:
        # 증분: 헤더 없이 기존 파일 끝에 추가
        if not os.path.exists(period_file):
            # 최초 생성
            content = make_period_header(cp, len(reports))
            for r in reports:
                content += report_to_md_block(r)
            with open(period_file, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"[최초 생성] {os.path.basename(period_file)}")
        else:
            # 기존 파일에 추가
            with open(period_file, "a", encoding="utf-8") as f:
                for r in reports:
                    f.write(report_to_md_block(r))
            print(f"[추가] {os.path.basename(period_file)}")
            for r in reports:
                print(f"  + {r['sent_time'][:10]} ({weekday_str(r['sent_time'][:10])})")

    # 인덱스 업데이트
    update_index()
    fsize = os.path.getsize(period_file) / 1024
    print(f"\n완료! {os.path.basename(period_file)} ({fsize:.1f} KB)")


def update_index():
    """_index.md 갱신"""
    period_files = sorted(glob.glob(os.path.join(REPORTS_DIR, "????_H?.md")))
    cp = current_period()
    lines = [
        f"# {MY_NAME} 일일보고 반기별 아카이브",
        "",
        "> RAG/NotebookLM 학습용 | 반기별 분리 저장",
        "",
        "| 파일 | 기간 | 상태 |",
        "|------|------|------|",
    ]
    for fpath in period_files:
        fname = os.path.basename(fpath)
        key = fname.replace(".md", "")
        year, half = key.split("_")
        label = f"{year}년 {'상반기 (1~6월)' if half == 'H1' else '하반기 (7~12월)'}"
        status = "진행중" if key == cp["key"] else "완결"
        fsize = os.path.getsize(fpath) / 1024
        lines.append(f"| [{fname}]({fname}) | {label} | {status} ({fsize:.0f} KB) |")

    with open(os.path.join(REPORTS_DIR, "_index.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


# ════════════════════════════════════════════════
# 메인 진입점
# ════════════════════════════════════════════════

if __name__ == "__main__":
    os.makedirs(REPORTS_DIR, exist_ok=True)

    if MODE_INIT:
        print("[모드] --init: 날짜별 MD -> 반기별 MD 마이그레이션")
        mode_init()
        update_index()
    else:
        print("[모드] Outlook 조회 후 현재 반기 파일 업데이트")
        _, namespace = connect_outlook()
        mode_update(namespace)
