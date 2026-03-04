---
description: 프로젝트 스택 자동 감지 및 에이전트 환경 초기 설정
---

# /setup - Antigravity 초기 세팅

이 워크플로우는 프로젝트의 기술 스택을 분석하고 Antigravity가 협업하기 위한 기반을 마련합니다.

## 실행 단계

1. **🤖 AG_RULES.md 로드 (최우선 실행)**
   - 프로젝트 루트의 `AG_RULES.md` 파일을 읽어 다음 내용을 인식합니다:
     - 에이전트별 역할 및 지정 LLM 모델 (Main Commander, Architect, Planner, Coder, Reviewer)
     - 공통 코딩 규칙 (언어, 에러 처리, 품질, 문서화 기준)
     - 프로젝트 구조 관리 원칙
   - 파일이 존재하지 않으면 사용자에게 알리고 중단합니다.

2. **기술 스택 분석**
   - `requirements.txt`, `scripts/*.py` 파일 등을 스캔하여 사용 중인 라이브러리와 언어를 파악합니다.
   - 이 프로젝트의 감지된 스택:
     - **Language**: Python 3.x (Windows 전용)
     - **Platform**: Windows (Outlook COM Interface via pywin32)
     - **Key Libraries**: `pywin32` (`win32com`), `mcp`, `datetime`, `re`, `glob`, `os`, `argparse`
     - **Data Format**: Markdown (YAML frontmatter + RAG 최적화 청크 구조)
   - 의존성 설치: `pip install -r requirements.txt`

3. **Context 디렉토리 확인/생성**
   - `.agents/context/` 및 `.agents/context/tasks/` 디렉토리를 생성합니다.
   - Windows 환경: `mkdir .agents\context\tasks` (PowerShell: `New-Item -ItemType Directory -Force`)

4. **Project Map 확인/생성**
   - `.agents/context/project-map.md`를 확인하고, 없으면 현재 디렉토리 구조와 주요 파일 역할을 정의하여 생성합니다.
   - 이미 존재하는 경우 `/ag-map` 명령으로 최신 상태로 갱신합니다.

5. **핵심 파일 구조 인식**
   - 아래 파일들의 역할과 관계를 파악합니다:

   | 파일 | 역할 |
   |------|------|
   | `scripts/outlook_utils.py` | 공통 유틸리티 모듈 (strip_html, get_body, connect_outlook 등) |
   | `scripts/save_all_reports.py` | 핵심 스크립트 - Outlook "나의 일일보고" 폴더 수집 → 반기별 MD 저장 |
   | `scripts/get_today_sent.py` | 오늘 보낸 메일 조회 → `output/today_sent.md` 저장 (--date 인자 지원) |
   | `scripts/check_my_report.py` | 특정 날 본인 일일보고 확인 (--date 인자 지원, 기본값 어제) |
   | `scripts/get_sent_emails.py` | 보낸 메일 일반 조회 (argparse 지원, 터미널 출력) |
   | `daily_update.bat` | 매일 퇴근 후 1회 실행 자동화 배치 (보낸메일 조회 + 반기파일 업데이트) |
   | `output/today_sent.md` | 오늘 보낸 메일 원문 목록 (항상 덮어씀) |
   | `output/daily_report_draft.txt` | AI가 분석한 일일보고 초안 (단일 파일, 매번 덮어씀) |
   | `output/weekly_report_YYYY-WNN.md` | 주간보고 출력 파일 |
   | `reports/YYYY_H?.md` | 반기별 일일보고 아카이브 (RAG/NotebookLM 학습용) |
   | `outlook_mcp/server.py` | MCP 서버 - 8개 tool 제공 (Antigravity에서 직접 호출 가능) |
   | `.agents/context/daily-report-guide.md` | 일일보고 작성 가이드 (CRM 템플릿 + RAG 최적화 원칙) |
   | `.agents/context/weekly-report-guide.md` | 주간보고 작성 가이드 (리포 페르소나 + 포맷) |

6. **일일보고 AI 초안 기능 인식**
   - 사용자가 "오늘 일일보고 작성해줘" 또는 유사한 뉘앙스로 요청하면:
     1. `python scripts/get_today_sent.py` 실행하여 `output/today_sent.md` 최신화
     2. `output/today_sent.md` 분석 + `daily-report-guide.md` 템플릿 기준으로 초안 작성
     3. `output/daily_report_draft.txt`를 **덮어씌워** 최신 내용 갱신 (파일은 항상 1개 유지)

   > ⚠️ 핵심 분리 원칙
   > - `daily_report_draft.txt` ← **보낸편지함** 기반 (AI 초안 작성용)
   > - `reports/2026_H1.md` ← **나의 일일보고 폴더** 기반 (CRM 발송 후 아카이브)
   >
   > "일일보고 작성해줘"만으로는 `reports/` 파일이 수정되지 않음.
   > CRM 입력 → 발송 확인 → `daily_update.bat` 실행 순서로 완료됨.

7. **MCP 서버 인식**
   - `outlook_mcp/server.py`가 Antigravity MCP 설정에 등록되어 있으면 아래 tool을 직접 호출 가능:

   | Tool | 동작 |
   |------|------|
   | `get_today_sent` | 오늘 보낸 메일 조회 → `output/today_sent.md` |
   | `get_sent_emails` | 보낸 메일 목록 JSON 반환 |
   | `check_my_report` | 본인 일일보고 확인 → `output/my_daily_report.txt` |
   | `save_reports` | 신규 일일보고 RAG 아카이브에 증분 저장 |
   | `force_reports` | 현재 반기 RAG 아카이브 전체 재생성 |
   | `read_report_index` | `reports/_index.md` 반환 |
   | `read_daily_draft` | `output/daily_report_draft.txt` 반환 |
   | `read_weekly_report` | `output/weekly_report_YYYY-WNN.md` 반환 |

8. **결과 보고**
   - 감지된 스택, 확인된 파일 목록, 현재 진행 중인 반기 파일 상태를 사용자에게 요약하여 보고합니다.

// turbo
9. run_command로 디렉토리 생성 (Windows PowerShell):
   `New-Item -ItemType Directory -Force -Path ".agents\context\tasks", "output", "scripts", "reports"`
