# 🗺 Antigravity Project Map
> **마지막 업데이트**: 2026-03-05  
> **업데이트 내용**: notebooklm_mcp 서버 구조 추가 (ON/OFF 전환, 보고서 연동, 비교 기능)

---

## 📚 기술 스택

- **Language**: Python 3.x
- **Platform**: Windows (Outlook COM Interface)
- **Key Libraries**: `pywin32` (`win32com`), `datetime`, `re`, `glob`, `os`
- **Data Format**: Markdown (YAML frontmatter + RAG 최적화 청크 구조)

---

## 📂 전체 디렉토리 구조

```
c:\TEST\dailyreport\
│
├── AG_RULES.md                  # Antigravity 에이전트 규칙 (최우선 로드)
├── requirements.txt             # 의존성 패키지 목록 (pywin32>=306)
├── daily_update.bat             # ★ 매일 퇴근 후 1회 실행 자동화 배치
│
├── scripts/                     # Python 스크립트 모음
│   ├── outlook_utils.py         # ★ 공통 유틸리티 모듈 (strip_html, get_body, connect_outlook 등)
│   ├── save_all_reports.py      # ★ 핵심 스크립트 - 반기별 보고서 관리
│   ├── check_my_report.py       # 특정 날 내 일일보고 확인 (--date 인자 지원)
│   ├── get_today_sent.py        # 오늘 보낸 메일 조회 → output/today_sent.md (--date 인자 지원)
│   └── get_sent_emails.py       # 보낸 메일 일반 조회 (argparse 지원, 터미널 출력)
│
├── outlook_mcp/                 # MCP 서버 - Outlook 메일 연동
│   ├── server.py                # ★ MCP 서버 메인 진입점 (8개 tool)
│   ├── tools/
│   │   ├── outlook.py           # Outlook 메일 조회 3개 tool
│   │   └── reports.py           # 보고서 저장/읽기 5개 tool
│   └── README.md                # 연결 설정 방법 가이드
│
├── notebooklm_mcp/              # MCP 서버 - NotebookLM ON/OFF 전환 연동
│   ├── PLAN.md                  # 개발 계획 문서
│   ├── README.md                # 연결 설정 및 사용법 가이드
│   ├── server.py                # ★ MCP 서버 메인 진입점 (5개 tool)
│   ├── mode.config.json         # ON/OFF 상태 저장 (.gitignore 제외)
│   └── tools/
│       ├── mode.py              # get_mode, set_mode tool
│       └── notebooklm.py        # upload_reports, query_notebooklm, compare_modes tool
│
├── output/                      # 생성 파일 저장 폴더 (.gitignore 제외)
│   ├── today_sent.md            # 오늘 발송 메일 조회 결과 (일일보고 작성용)
│   ├── daily_report_draft.txt   # ★ AI 작성 일일보고 초안 (단일 파일, 항상 덮어씀)
│   └── weekly_report_YYYY-WNN.md # 주간보고 출력 파일
│
├── reports/                     # 반기별 일일보고 아카이브 (RAG 학습용)
│   ├── 2025_H1.md              # 2025 상반기 (1~6월) - 완결
│   ├── 2025_H2.md              # 2025 하반기 (7~12월) - 완결
│   ├── 2026_H1.md              # 2026 상반기 (1~6월) - 진행중 ◀ 여기만 업데이트
│   └── _index.md               # 반기별 목록 인덱스
│
└── .agents/
    ├── context/
    │   ├── project-map.md           # 이 파일 - 프로젝트 전체 맵
    │   ├── daily-report-guide.md    # ★ 일일보고 가이드 (CRM 템플릿 + RAG 최적화 통합)
    │   ├── weekly-report-guide.md   # ★ 주간보고 가이드 (리포 페르소나 + 포맷 통합)
    │   └── tasks/                   # 진행 중인 작업 관리
    └── workflows/                   # 슬래시 명령어 정의
```

---

## � MCP 서버 (outlook_mcp/)

```
outlook_mcp/
├── server.py                 # ★ MCP 서버 메인 진입점 (stdio 프로토콜)
├── tools/
│   ├── outlook.py              # Outlook 메일 조회 3개 tool
│   └── reports.py              # 보고서 저장/읽기 4개 tool
└── README.md                 # 연결 설정 방법 가이드
```

**제공 Tool 목록 (8개)**:
| Tool | 설명 |
|---|---|
| `get_today_sent` | 오늘 보낸 메일 조회 → today_sent.md |
| `get_sent_emails` | 보낸 메일 목록 JSON 반환 |
| `check_my_report` | 본인 일일보고 확인 → my_daily_report.txt |
| `save_reports` | 신규 일일보고 RAG 아카이브에 증분 저장 |
| `force_reports` | 현과 반기 RAG 아카이브 전체 재생성 |
| `read_report_index` | reports/_index.md 반환 |
| `read_daily_draft` | output/daily_report_draft.txt 반환 |
| `read_weekly_report` | output/weekly_report_YYYY-WNN.md 반환 |

---

## �📄 핵심 스크립트 설명

### ★ `scripts/save_all_reports.py` - 반기별 보고서 관리 (메인 워크플로우)

```powershell
# 매일 퇴근 후 실행 → 2026_H1.md에 새 날짜 자동 추가 (증분)
python scripts/save_all_reports.py

# 포맷 변경 시 현재 반기 전체 재생성
python scripts/save_all_reports.py --force

# (최초 1회만) 날짜별 MD → 반기별 MD 마이그레이션
python scripts/save_all_reports.py --init
```

**동작 원리**:
1. Outlook "나의 일일보고" 폴더에서 `김정균` 이름 포함 메일 조회
2. 현재 반기(`2026_H1`) 범위만 검색
3. 이미 저장된 날짜는 스킵 (중복 없음)
4. 신규 날짜만 `2026_H1.md` 끝에 추가

**파일 보존 정책**:
- `2025_H1.md`, `2025_H2.md` → **절대 수정하지 않음** (완결 아카이브)
- `2026_H1.md` → 매일 새 날짜 추가, 6월 말 완결 후 동결

---

### `scripts/check_my_report.py` - 특정 날 보고서 확인

Outlook 전체 폴더 + 즐겨찾기에서 본인 일일보고 검색 후 `output/my_daily_report.txt`로 저장.

```powershell
python scripts/check_my_report.py           # 기본값: 어제 날짜
python scripts/check_my_report.py --date 2026-03-04  # 날짜 지정
```

---

### `scripts/get_today_sent.py` - 오늘 보낸 메일 조회

즐겨찾기 보낸편지함 우선 탐색 → `output/today_sent.md` 저장.  
**일일보고 작성 전에 실행**하면 오늘 업무 내역 자동 정리.

```powershell
python scripts/get_today_sent.py
python scripts/get_today_sent.py --date 2026-03-04  # 날짜 지정
```

---

## 🗄 reports/ 파일 구조 (RAG 최적화)

### 반기 파일 포맷 (`YYYY_H?.md`)

```markdown
---
title: "김정균 일일보고 2026년 상반기 (1~6월)"
period: "2026_H1"
status: "진행중"
---

# 김정균 일일보고 | 2026-02-25 (수) | MSS팀

## 업무 기록 1 | [기술지원] 삼성전자 LSI - TRACE32 ramdump kernel 6.18 오류
- 날짜: 2026-02-25 (수)
- 담당자: 김정균 (MSS팀, MDS테크)
- 업무 유형: 기술지원
- 고객사/담당자: 삼성전자_시스템LSI사업부 AP SW개발팀 최정호
- 업무 상세:
  - ...
```

**설계 원칙**: 업무 1건 = `##` 섹션 1개 = RAG 청크 1개  
→ 어떤 검색어로도 날짜·담당자·고객사·내용이 한 청크에서 확인 가능

---

## 🧠 RAG 최적화 페르소나 (중요)

> **일일보고 가이드** (CRM 템플릿 + RAG 원리): `.agents/context/daily-report-guide.md` 참조  
> **주간보고 가이드** (리포 페르소나 + 포맷): `.agents/context/weekly-report-guide.md` 참조

### 핵심 페르소나: "3개월 후의 나에게 보내는 브리핑"

CRM 보고서 작성 시 이 5가지를 지킵니다:

| 규칙 | 나쁜 예 | 좋은 예 |
|------|---------|---------|
| 고유명사 풀네임 | `삼성 MX`, `T32` | `삼성전자_MX사업부`, `TRACE32` |
| 제품명 명시 | `기능 문의` | `TRACE32 ramdump kernel 6.18 오류` |
| 인과관계 | `확인함` | `문제→원인→조치→결과` 구조 |
| 상태 명시 | (생략) | `결과: 완료 / 진행중 / 보류` |
| 업무명 핵심어 | `▶ 삼성 문의` | `▶ 삼성전자 LSI - TRACE32 ramdump kernel 6.18` |

---

## 📬 Outlook 즐겨찾기 폴더 구조

| 즐겨찾기 이름 | 실제 경로 |
|---|---|
| 나의 일일보고 | `받은 편지함\DT사업부 일일보고\나의 일일보고` |
| 보낸 편지함 | `\보낸 편지함` |
| MSS팀 | `받은 편지함\MSS팀` |
| DT주간보고 | `받은 편지함\DT주간보고` |
| 나 | `받은 편지함\나` |

**일일보고 발송 시스템**: CRM 입력 → `crm-noreply@hancommds.com`이 자동 발송  
→ `나의 일일보고` 폴더에 저장됨

---

## 🔄 전체 워크플로우

```
━━━ STEP 1 │ AI 초안 작성 (퇴근 전) ━━━━━━━━━━━━━━━━
Antigravity에게 "일일보고 작성해줘"
        ↓
scripts/get_today_sent.py 실행 (Outlook 보낸편지함 스캔)
        ↓
📄 output/today_sent.md       ← 오늘 보낸 메일 원문
        ↓
AI가 today_sent.md 분석 + daily-report-guide.md 템플릿 적용
        ↓
📄 output/daily_report_draft.txt  ← AI 초안

━━━ STEP 2 │ CRM 수동 입력 (사람이 직접) ━━━━━━━━━━━━
draft.txt 검토 후 CRM(Dynamics 365)에 직접 입력
        ↓
crm-noreply@hancommds.com 이 자동 발송
        ↓
Outlook "나의 일일보고" 폴더에 저장됨

━━━ STEP 3 │ RAG 아카이브 저장 (퇴근 후) ━━━━━━━━━━━━
daily_update.bat 실행
(또는 Antigravity에게 "보고서 저장해줘")
        ↓
scripts/save_all_reports.py 실행
(Outlook "나의 일일보고" 폴더 스캔 — 보낸편지함 아님!)
        ↓
📄 reports/2026_H1.md 에 추가  ← RAG 아카이브

━━━ STEP 4 │ NotebookLM 활용 ━━━━━━━━━━━━━━━━━━━━━
reports/2026_H1.md 업로드 후 질의응답
```

> ⚠️ **핵심 분리 원칙 (자주 혼동)**
> - `daily_report_draft.txt` ← **보낸편지함** 기반 (오늘 내가 보낸 메일)
> - `reports/2026_H1.md` ← **나의 일일보고 폴더** 기반 (CRM 자동 발송 메일)
>
> → "일일보고 작성해줘"만으로는 `2026_H1.md`가 수정되지 않음.
> CRM 입력 완료 후 `daily_update.bat` 실행까지 해야 아카이브에 저장됨.


---

## 🚀 작업 상태

- [x] 에이전트 시스템 초기 구축 (`/setup` - 2026-02-26)
- [x] Outlook 일일보고 수집 스크립트 개발 완료
- [x] RAG 최적화 포맷 설계 및 적용 완료
- [x] 반기별 아카이브 구조 구축 (2025_H1, 2025_H2, 2026_H1)
- [x] 불필요 스크립트 정리 완료
- [x] **outlook_utils.py 공통 모듈 생성** (strip_html, get_body, connect_outlook 통합 - 2026-02-26)
- [x] **날짜 하드코딩 제거** (check_my_report.py, get_today_sent.py → 자동 계산 + --date 인자 - 2026-02-26)
- [x] **daily_update.bat 자동화 배치 생성** (2026-02-26)
- [x] **output/daily_report_draft.txt AI 일일보고 초안 기능 추가** (오늘 보낸 메일 분석 → CRM 템플릿 초안 자동 작성 - 2026-02-26)
- [x] **requirements.txt 의존성 파일 추가** (pywin32>=306 - 2026-02-27)
- [x] **setup.md 현행화** (신규 기능 및 파일 구조 반영 - 2026-02-27)
- [x] **context 파일 4개→2개 통합** (daily-report-guide.md, weekly-report-guide.md - 2026-03-04)
- [x] **outlook_mcp MCP 서버 구축** (8개 tool - 2026-03-04)
- [x] **notebooklm_mcp MCP 서버 구조 구축** (5개 tool, ON/OFF 전환 - 2026-03-05)
- [ ] **notebooklm-mcp npx 설치 + Google 인증** (MODE ON 활성화)
- [ ] **AG_RULES.md에 notebooklm MCP 서버 등록**
- [ ] 일일보고 자동 작성 보조 기능 개발 (`/ag-design` → `/ag-impl`)
- [ ] CRM 업로드 자동화 연구
- [ ] Windows 작업 스케줄러 등록 (daily_update.bat 매일 18:00 자동 실행)

