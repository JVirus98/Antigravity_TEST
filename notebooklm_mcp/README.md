# NotebookLM MCP 서버

`outlook_mcp/`와 동일한 구조로 구성된 NotebookLM MCP 서버입니다.  
Antigravity 단독 모드(OFF)와 NotebookLM 경유 모드(ON)를 전환하여 결과를 비교할 수 있습니다.

---

## 📁 구조

```
notebooklm_mcp/
├── PLAN.md              # 개발 계획 문서
├── README.md            # 이 파일
├── server.py            # MCP 서버 메인 진입점
├── mode.config.json     # ON/OFF 상태 저장 (자동 생성)
├── __init__.py
└── tools/
    ├── __init__.py
    ├── mode.py          # get_mode, set_mode tool
    └── notebooklm.py    # upload_reports, query_notebooklm, compare_modes tool
```

---

## 🔧 제공 Tool (5개)

| Tool | MODE | 설명 |
|------|------|------|
| `get_mode` | 항상 | 현재 ON/OFF 상태 조회 |
| `set_mode` | 항상 | ON/OFF 전환 + notebook_url 설정 |
| `upload_reports` | ON 전용 | reports/ 마크다운 → NotebookLM 업로드 안내 |
| `query_notebooklm` | ON 전용 | NotebookLM에 질문 전송 안내 |
| `compare_modes` | 비교 | OFF vs ON 결과 비교 구조 반환 |

---

## ⚙️ MCP 등록 설정

`.gemini/settings.json` 또는 `AG_RULES.md`에 추가:

```json
{
  "mcpServers": {
    "notebooklm": {
      "command": "python",
      "args": ["c:/TEST/dailyreport/notebooklm_mcp/server.py"]
    }
  }
}
```

---

## 🚀 사용법

### 1. 현재 모드 확인
```
"notebooklm 모드 확인해줘"  →  get_mode 호출
```

### 2. OFF 모드 (기본값 - Antigravity 단독)
```
"notebooklm 모드 꺼줘"  →  set_mode(mode="OFF")
→ Antigravity가 reports/ 마크다운을 직접 분석
```

### 3. ON 모드로 전환 (NotebookLM 경유)
```
"notebooklm 모드 켜줘, URL은 https://notebooklm.google.com/..."
→  set_mode(mode="ON", notebook_url="https://...")
→  upload_reports() 로 보고서 업로드
→  query_notebooklm(query="...") 로 질의
```

### 4. 두 모드 비교
```
"3월 업무 현황을 두 모드로 비교해줘"
→  compare_modes(query="3월 업무 현황 요약해줘")
→  output/compare_YYYYMMDD_HHMMSS.md 에 비교 리포트 저장
```

---

## 📌 ON/OFF 차이

| 항목 | MODE OFF (기본) | MODE ON |
|------|----------------|---------|
| 데이터 처리 | Antigravity 직접 | NotebookLM (Gemini 2.5) |
| 인용 출처 | 없음 | 날짜/파일명 포함 |
| 할루시네이션 | 가능성 있음 | 거의 없음 |
| 응답 속도 | 빠름 | 느림 (브라우저 자동화) |
| 데이터 경로 | Google Gemini API | Google NotebookLM |

---

## ⚠️ 주의사항

- `mode.config.json`은 `.gitignore`에 추가 권장 (notebook_url 등 민감 정보)
- MODE ON은 `notebooklm-mcp@latest` (npx) 별도 설치 필요
- Chrome 브라우저가 설치되어 있어야 함 (notebooklm-mcp 내부 사용)
- Google 계정 전용 계정 사용 권장
