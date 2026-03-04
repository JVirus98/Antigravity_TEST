# -*- coding: utf-8 -*-
"""
outlook_utils.py — Outlook 공통 유틸리티 모듈

이 모듈은 프로젝트 내 여러 스크립트에서 공통으로 사용하는
Outlook 관련 헬퍼 함수를 한곳에서 관리합니다.

포함 함수:
  - strip_html(html_text)       : HTML 태그 제거 → 순수 텍스트 반환
  - get_body(item)              : Outlook 메일 아이템에서 본문 추출 (전체)
  - get_today_body(item)        : 일일보고 이메일에서 당일 컬럼만 추출
  - get_recipients(item)        : Outlook 메일 아이템에서 수신자 목록 추출
  - connect_outlook()           : Outlook COM 연결 및 MAPI 네임스페이스 반환
  - get_favorites_folder(namespace, keyword) : 즐겨찾기에서 키워드 포함 폴더 반환
"""

import re
import sys
import win32com.client


# ════════════════════════════════════════════════
# HTML / 본문 처리
# ════════════════════════════════════════════════

def strip_html(html_text: str) -> str:
    """
    HTML 태그를 제거하고 순수 텍스트만 반환합니다.
    블록 레벨 태그(br, p, div, tr, td, th, li 등)는 줄바꿈으로 변환하여
    줄 구조를 보존합니다.

    Args:
        html_text: HTML 형식의 문자열

    Returns:
        태그와 특수 엔티티가 제거된 순수 텍스트 (줄 구조 보존)
    """
    text = re.sub(r'<style[^>]*>.*?</style>', '', html_text, flags=re.DOTALL)
    text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL)
    # 블록 레벨 태그를 먼저 줄바꿈으로 치환 (줄 구조 보존)
    text = re.sub(r'<br\s*/?>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'</(p|div|tr|li|h[1-6])>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'</(td|th)>', '\n', text, flags=re.IGNORECASE)
    # 나머지 태그 제거
    text = re.sub(r'<[^>]+>', '', text)
    for entity, char in [('&nbsp;', ' '), ('&lt;', '<'), ('&gt;', '>'), ('&amp;', '&')]:
        text = text.replace(entity, char)
    text = re.sub(r'https?://\S+', '', text)          # URL 제거
    text = re.sub(r'[ \t]+', ' ', text)               # 연속 공백 정리
    text = re.sub(r'\n[ \t]+', '\n', text)            # 줄 앞 공백 정리
    text = re.sub(r'\n{3,}', '\n\n', text)            # 3중 이상 빈줄 → 2줄로
    return text.strip()


def get_body(item) -> str:
    """
    Outlook 메일 아이템에서 본문 텍스트를 추출합니다.
    텍스트 본문(Body)을 우선하며, 없을 경우 HTML 본문에서 태그를 제거하여 반환합니다.

    Args:
        item: Outlook MailItem COM 객체

    Returns:
        정제된 본문 텍스트
    """
    body = getattr(item, 'Body', '') or ''
    if not body:
        html = getattr(item, 'HTMLBody', '') or ''
        if html:
            body = strip_html(html)
    body = re.sub(r'https?://\S+', '', body)           # URL 제거
    body = re.sub(r'\n\s*\n\s*\n', '\n\n', body)       # 3중 빈줄 → 2중으로
    return body.strip()


def get_today_body(item) -> str:
    """
    일일보고 이메일에서 '당일' 컬럼 본문만 추출합니다.

    일일보고 이메일 HTML 표 구조:
      <tr>
        <th>당일(YYYY-MM-DD)</th>  ← 헤더
        <th>익일(YYYY-MM-DD)</th>
      </tr>
      <tr>
        <td>...당일 업무 내용 전체...</td>  ← 첫 번째 td = 당일
        <td>...익일 업무 내용 전체...</td>  ← 두 번째 td = 익일
      </tr>

    HTMLBody에서 <th>로 일일보고 형식을 확인하고,
    첫 번째 <td> 내용만 추출하여 텍스트로 변환합니다.
    HTML 파싱에 실패하면 일반 get_body() 결과를 반환합니다.

    Args:
        item: Outlook MailItem COM 객체

    Returns:
        당일 컬럼 텍스트 (익일 내용 제외)
    """
    html = getattr(item, 'HTMLBody', '') or ''
    if not html:
        return get_body(item)

    try:
        # <th> 태그에서 '당일'/'익일' 헤더 확인 → 일일보고 형식 검증
        th_pattern = re.compile(r'<th\b[^>]*>(.*?)</th>', re.DOTALL | re.IGNORECASE)
        ths = th_pattern.findall(html)
        th_texts = [strip_html(t).strip() for t in ths]

        is_daily_report = any('당일' in t for t in th_texts) and any('익일' in t for t in th_texts)
        if not is_daily_report:
            # 일일보고 표 구조가 아님 → 일반 방식 사용
            return get_body(item)

        # 상단 헤더(제목, 팀원명) 추출 — 표 바깥 영역
        header_match = re.search(
            r'<body[^>]*>(.*?)<table',
            html, re.DOTALL | re.IGNORECASE
        )
        header_text = ''
        if header_match:
            header_text = strip_html(header_match.group(1)).strip()

        # 첫 번째 <td> = 당일 컬럼 전체
        td_pattern = re.compile(r'<td\b[^>]*>(.*?)</td>', re.DOTALL | re.IGNORECASE)
        tds = td_pattern.findall(html)

        if not tds:
            return get_body(item)

        today_text = strip_html(tds[0]).strip()

        # 헤더 + 당일 본문 조합
        full_text = (header_text + '\n\n' + today_text).strip() if header_text else today_text

        # URL 제거, 연속 빈줄 정리
        full_text = re.sub(r'https?://\S+', '', full_text)
        full_text = re.sub(r'\n\s*\n\s*\n', '\n\n', full_text)
        return full_text.strip()

    except Exception:
        # 파싱 실패 시 일반 방식으로 폴백
        return get_body(item)



def get_recipients(item) -> list[str]:
    """
    Outlook 메일 아이템에서 수신자 이름 목록을 추출합니다.

    Args:
        item: Outlook MailItem COM 객체

    Returns:
        수신자 이름 문자열 리스트 (실패 시 빈 리스트)
    """
    recipients = []
    try:
        for i in range(1, item.Recipients.Count + 1):
            rec = item.Recipients.Item(i)
            name = rec.Name or rec.Address or ''
            if name:
                recipients.append(name)
    except Exception:
        pass
    return recipients


# ════════════════════════════════════════════════
# Outlook 연결
# ════════════════════════════════════════════════

def connect_outlook():
    """
    Outlook COM 인터페이스에 연결하고 MAPI 네임스페이스를 반환합니다.
    연결 실패 시 에러 메시지를 출력하고 프로세스를 종료합니다.

    Returns:
        (outlook, namespace) 튜플
          - outlook  : Outlook.Application COM 객체
          - namespace: MAPI 네임스페이스 COM 객체
    """
    try:
        outlook   = win32com.client.Dispatch("Outlook.Application")
        namespace = outlook.GetNamespace("MAPI")
        return outlook, namespace
    except Exception as e:
        print(f"[오류] Outlook 연결 실패: {e}")
        print("  → Outlook이 실행 중인지, COM 인터페이스가 활성화되어 있는지 확인하세요.")
        sys.exit(1)


# ════════════════════════════════════════════════
# 즐겨찾기 폴더 탐색
# ════════════════════════════════════════════════

def get_favorites_folder(namespace, keyword: str):
    """
    Outlook 즐겨찾기(NavigationPane)에서 DisplayName에 keyword가 포함된
    첫 번째 MAPI 폴더를 반환합니다.

    Args:
        namespace : MAPI 네임스페이스 COM 객체
        keyword   : 즐겨찾기 폴더명에서 검색할 키워드 (예: '보낸', '일일보고')

    Returns:
        (mapi_folder, folder_path) 튜플.
        찾지 못한 경우 (None, None)
    """
    try:
        nav = namespace.Application.ActiveExplorer().NavigationPane
        for module in nav.Modules:
            try:
                if not hasattr(module, 'NavigationGroups'):
                    continue
                for group in module.NavigationGroups:
                    try:
                        for nav_folder in group.NavigationFolders:
                            try:
                                if keyword in nav_folder.DisplayName:
                                    mapi_folder = nav_folder.Folder
                                    path = getattr(mapi_folder, 'FolderPath', nav_folder.DisplayName)
                                    return mapi_folder, path
                            except Exception:
                                pass
                    except Exception:
                        pass
            except Exception:
                pass
    except Exception as e:
        print(f"  (즐겨찾기 탐색 실패: {e})")
    return None, None
