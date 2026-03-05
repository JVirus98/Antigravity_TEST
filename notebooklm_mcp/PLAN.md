# 📋 NotebookLM MCP 개발 계획

> **작성일**: 2026-03-05  
> **상태**: 개발 진행중  
> **연관 폴더**: `notebooklm_mcp/` (outlook_mcp/ 구조 동일하게 적용)

---

## 🎯 목표

Antigravity 단독 처리(MODE OFF)와 NotebookLM MCP 연동 처리(MODE ON)를
하나의 커스텀 Skill로 전환하며 결과를 비교할 수 있는 구조 구현

---

## 🏗️ 아키텍처

```
[MODE: OFF - Antigravity 단독]
Outlook → reports/2026_H1.md → Antigravity 직접 분석 → 답변

[MODE: ON - NotebookLM MCP 경유]
Outlook → reports/2026_H1.md → notebooklm_mcp → NotebookLM 업로드
                                                         ↓
                                               Gemini 2.5 처리
                                                         ↓
                                          Antigravity가 답변 수신 → 정제
```

---

## 📁 파일 구조

```
notebooklm_mcp/
├── PLAN.md                  ← 이 파일 (개발 계획)
├── README.md                ← 연결 설정 및 사용법
├── server.py                ← MCP 서버 메인 진입점
├── mode.config.json         ← ON/OFF 상태 저장
└── tools/
    ├── __init__.py
    ├── mode.py              ← ON/OFF 전환 tool
    └── notebooklm.py        ← NotebookLM 연동 tool
```

---

## 🔧 제공 Tool 목록

| Tool | MODE | 설명 |
|------|------|------|
| `get_mode` | 항상 | 현재 ON/OFF 상태 조회 |
| `set_mode` | 항상 | ON 또는 OFF로 전환 |
| `upload_reports` | ON 전용 | reports/ 마크다운을 NotebookLM에 업로드 |
| `query_notebooklm` | ON 전용 | NotebookLM에 질문하고 답변 수신 |
| `compare_modes` | 비교 | OFF(Antigravity)와 ON(NotebookLM) 결과 나란히 비교 |

---

## 📊 mode.config.json 구조

```json
{
  "notebooklm_mode": "OFF",
  "notebook_url": "",
  "last_switched": "",
  "last_upload": "",
  "description": {
    "OFF": "Antigravity가 reports/ 마크다운을 직접 분석",
    "ON":  "NotebookLM MCP를 통해 Gemini 2.5로 처리 후 Antigravity가 수신"
  }
}
```

---

## 🚀 구현 단계 체크리스트

- [x] **PLAN.md 작성** (이 파일)
- [x] **mode.config.json 생성** (기본값 OFF)
- [x] **tools/mode.py 개발** (get_mode, set_mode)
- [x] **tools/notebooklm.py 개발** (upload_reports, query_notebooklm, compare_modes)
- [x] **server.py 개발** (outlook_mcp/server.py 패턴 동일하게)
- [x] **README.md 작성** (설치 및 설정 가이드)
- [ ] **notebooklm-mcp npx 설치** (Google 인증 포함)
- [ ] **AG_RULES.md에 MCP 서버 등록**
- [ ] **Skill 파일 작성** (.agent/skills/daily-report/SKILL.md)
- [ ] **통합 테스트** (OFF vs ON 비교 실행)

---

## ⚠️ 의존성

- `notebooklm-mcp@latest` (npx로 설치)
- Google 계정 인증 (전용 계정 권장)
- Chrome 브라우저 (notebooklm-mcp가 내부적으로 사용)

---

## 🗒️ 참고 사항

- `outlook_mcp/server.py` 구조를 동일하게 따름 (가독성 유지)
- MODE OFF일 때 NotebookLM 관련 tool은 에러 없이 "mode is OFF" 반환
- `mode.config.json`은 `.gitignore`에 추가 예정 (notebook_url 등 민감 정보 포함 가능)
