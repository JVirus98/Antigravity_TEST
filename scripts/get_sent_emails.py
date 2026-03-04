# -*- coding: utf-8 -*-
"""
Outlook 보낸 메일함에서 오늘 보낸 메일을 조회하는 스크립트
- win32com을 사용하여 Outlook COM 인터페이스에 접근
- 오늘 날짜 기준으로 보낸 메일을 필터링
- 제목, 수신자, 보낸 시간, 본문 요약을 출력
"""

import datetime
import re

from outlook_utils import strip_html, connect_outlook


# strip_html 함수는 outlook_utils.py에서 임포트하여 사용합니다.



def get_sent_emails(target_date=None, max_body_length=300):
    """
    Outlook 보낸 메일함에서 특정 날짜의 메일을 조회합니다.

    Args:
        target_date: 조회할 날짜 (None이면 오늘)
        max_body_length: 본문 미리보기 최대 길이
    Returns:
        list of dict: 메일 정보 목록
    """
    if target_date is None:
        target_date = datetime.date.today()

    # Outlook 연결
    _, namespace = connect_outlook()


    # 보낸 편지함 (olFolderSentMail = 5)
    sent_folder = namespace.GetDefaultFolder(5)

    # 날짜 필터 설정 (DASL 필터)
    start_date = target_date.strftime("%m/%d/%Y")
    end_date = (target_date + datetime.timedelta(days=1)).strftime("%m/%d/%Y")
    filter_str = (
        f"[SentOn] >= '{start_date}' AND [SentOn] < '{end_date}'"
    )

    items = sent_folder.Items
    items.Sort("[SentOn]", Descending=True)
    filtered_items = items.Restrict(filter_str)

    emails = []
    for item in filtered_items:
        try:
            # 수신자 목록
            recipients = []
            for i in range(1, item.Recipients.Count + 1):
                recipients.append(item.Recipients.Item(i).Name)

            # 본문 텍스트 추출
            body = item.Body if item.Body else ""
            if not body and item.HTMLBody:
                body = strip_html(item.HTMLBody)

            # 본문 미리보기 (길이 제한)
            body_preview = body[:max_body_length]
            if len(body) > max_body_length:
                body_preview += "..."

            # 첨부파일 목록
            attachments = []
            for j in range(1, item.Attachments.Count + 1):
                attachments.append(item.Attachments.Item(j).FileName)

            email_info = {
                "subject": item.Subject or "(제목 없음)",
                "to": ", ".join(recipients),
                "sent_time": item.SentOn.strftime("%Y-%m-%d %H:%M:%S"),
                "body_preview": body_preview,
                "attachments": attachments,
                "importance": ["낮음", "보통", "높음"][item.Importance],
            }
            emails.append(email_info)
        except Exception as e:
            print(f"  [경고] 메일 읽기 실패: {e}")
            continue

    return emails


def print_emails(emails, target_date=None):
    """메일 목록을 보기 좋게 출력"""
    if target_date is None:
        target_date = datetime.date.today()

    print("=" * 70)
    print(f"  [Outlook 보낸 메일 조회] {target_date.strftime('%Y년 %m월 %d일')}")
    print("=" * 70)

    if not emails:
        print("\n  해당 날짜에 보낸 메일이 없습니다.\n")
        return

    print(f"\n  총 {len(emails)}건의 메일을 발송했습니다.\n")

    for idx, email in enumerate(emails, 1):
        print(f"─── 메일 {idx} ───────────────────────────────────────")
        print(f"  [제목] {email['subject']}")
        print(f"  [수신] {email['to']}")
        print(f"  [시간] {email['sent_time']}")
        print(f"  [중요도] {email['importance']}")
        if email['attachments']:
            print(f"  [첨부] {', '.join(email['attachments'])}")
        print(f"  [내용]")
        # 본문을 들여쓰기하여 출력
        for line in email['body_preview'].split('\n'):
            stripped = line.strip()
            if stripped:
                print(f"     {stripped}")
        print()

    print("=" * 70)


def save_to_file(emails, target_date=None, filepath=None):
    """메일 목록을 텍스트 파일로 저장"""
    if target_date is None:
        target_date = datetime.date.today()
    if filepath is None:
        filepath = f"sent_emails_{target_date.strftime('%Y%m%d')}.txt"

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(f"Outlook 보낸 메일 - {target_date.strftime('%Y년 %m월 %d일')}\n")
        f.write("=" * 60 + "\n\n")

        if not emails:
            f.write("해당 날짜에 보낸 메일이 없습니다.\n")
            return filepath

        f.write(f"총 {len(emails)}건\n\n")

        for idx, email in enumerate(emails, 1):
            f.write(f"--- 메일 {idx} ---\n")
            f.write(f"제목: {email['subject']}\n")
            f.write(f"수신: {email['to']}\n")
            f.write(f"시간: {email['sent_time']}\n")
            f.write(f"중요도: {email['importance']}\n")
            if email['attachments']:
                f.write(f"첨부: {', '.join(email['attachments'])}\n")
            f.write(f"내용:\n{email['body_preview']}\n\n")

        f.write("=" * 60 + "\n")

    return filepath


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Outlook 보낸 메일 조회")
    parser.add_argument(
        "--date", "-d",
        type=str,
        default=None,
        help="조회할 날짜 (YYYY-MM-DD 형식, 기본값: 오늘)"
    )
    parser.add_argument(
        "--days", "-n",
        type=int,
        default=0,
        help="오늘 기준 며칠 전 (예: 1이면 어제)"
    )
    parser.add_argument(
        "--save", "-s",
        action="store_true",
        help="결과를 텍스트 파일로 저장"
    )
    parser.add_argument(
        "--body-length", "-b",
        type=int,
        default=300,
        help="본문 미리보기 최대 길이 (기본값: 300)"
    )

    args = parser.parse_args()

    # 날짜 결정
    if args.date:
        target = datetime.datetime.strptime(args.date, "%Y-%m-%d").date()
    elif args.days > 0:
        target = datetime.date.today() - datetime.timedelta(days=args.days)
    else:
        target = datetime.date.today()

    # 메일 조회
    print(f"\nOutlook에서 보낸 메일을 조회하는 중...")
    emails = get_sent_emails(target_date=target, max_body_length=args.body_length)

    # 출력
    print_emails(emails, target_date=target)

    # 파일 저장
    if args.save:
        output_path = save_to_file(emails, target_date=target)
        print(f"파일 저장 완료: {output_path}")
