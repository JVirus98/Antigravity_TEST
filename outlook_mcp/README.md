# dailyreport MCP Server

Outlook 메일 조회 + 일일/주간보고 관리 기능을 **Model Context Protocol(MCP)** 서버로 제공합니다.  
Antigravity(이 에이전트), Claude Desktop 등 MCP 호환 클라이언트에서 직접 호출할 수 있습니다.

---

## 📁 파일 구조

```
outlook_mcp/
├── server.py           ← MCP 서버 메인 진입점 (여기를 실행)
├── tools/
│   ├── outlook.py      ← Outlook 메일 조회 tool 함수들
│   └── reports.py      ← 보고서 저장/읽기 tool 함수들
└── README.md           ← 이 파일
```

---

## 🔧 사전 요구사항

```powershell
pip install mcp pywin32
```

- **mcp** ≥ 1.0.0 (공식 MCP Python SDK)
- **pywin32** ≥ 306 (Outlook COM 연결)
- Outlook이 Windows에서 실행 중이어야 함

---

## ▶ 실행 방법

```powershell
cd c:\TEST\dailyreport
python outlook_mcp/server.py
```

서버는 **stdio** 방식으로 동작하므로, MCP 클라이언트가 프로세스를 직접 실행합니다.

---

## ⚙ Antigravity / Claude Desktop 연결 설정

### Claude Desktop (`claude_desktop_config.json`)

```json
{
  "mcpServers": {
    "dailyreport": {
      "command": "python",
      "args": ["c:/TEST/dailyreport/outlook_mcp/server.py"]
    }
  }
}
```

파일 위치: `%APPDATA%\Claude\claude_desktop_config.json`

---

## 🛠 제공 Tools (8개)

### Outlook 메일 조회

| Tool | 설명 | 인자 |
|------|------|------|
| `get_today_sent` | 오늘(또는 특정 날짜) 보낸 메일 조회 → `today_sent.md` 저장 | `date?` |
| `get_sent_emails` | 보낸 메일 목록 JSON 반환 (제목/수신자/본문 미리보기) | `date?`, `max_body_length?` |
| `check_my_report` | 본인 일일보고 Outlook 검색 → `my_daily_report.txt` 저장 | `date?` |

### 보고서 관리

| Tool | 설명 | 인자 |
|------|------|------|
| `save_reports` | 신규 일일보고 RAG 아카이브에 증분 저장 | 없음 |
| `force_reports` | 현재 반기 RAG 아카이브 전체 재생성 | 없음 |
| `read_report_index` | `reports/_index.md` 반환 | 없음 |
| `read_daily_draft` | `output/daily_report_draft.txt` 반환 | 없음 |
| `read_weekly_report` | `output/weekly_report_YYYY-WNN.md` 반환 | `week?` |

---

## 🔄 일반적인 사용 흐름

```
① [퇴근 전] get_today_sent       → 오늘 보낸 메일 정리 (today_sent.md)
② [AI 초안] read_daily_draft     → AI 작성 일일보고 초안 확인
③ [CRM 입력] (수동으로 CRM에 입력)
④ [퇴근 후] save_reports         → Outlook에서 오늘 일일보고 → 반기 아카이브 추가
⑤ [주 1회]  read_weekly_report   → 주간보고 확인
```

---

## 💡 참고

- `scripts/outlook_utils.py`는 `scripts/` 폴더에 위치합니다 (MCP 서버에서 sys.path로 자동 로드)
- `scripts/save_all_reports.py`는 `save_reports` / `force_reports` tool이 내부적으로 활용합니다
- Outlook COM은 **메인 스레드**에서만 안정적으로 동작하므로, async/await 내에서 동기 호출합니다
