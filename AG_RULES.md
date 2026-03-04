# 🤖 Antigravity 에이전트 시스템 (AG-AS)

이 파일은 Antigravity 에이전트가 이 프로젝트에서 작업할 때 준수해야 할 핵심 규칙과 워크플로우를 정의합니다.

## 🛠 에이전트 명령어 (Workflows)

| 명령어 | 역할 | 설명 |
|--------|------|------|
| `/setup` | 환경 구축 | 프로젝트 스택 감지 및 초기 맵 생성 |
| `/ag-design` | 설계 | 아키텍처 및 데이터 모델 설계 (Architect: Claude Opus 4.6 Thinking) |
| `/ag-plan` | 계획 | 작업 단위 분할 및 체크리스트 생성 (Planner: Claude Sonnet 4.6 Thinking) |
| `/ag-impl` | 구현 | 실제 코드 작성 및 수정 (Coder: Claude Sonnet 4.6 Thinking) |
| `/ag-review` | 리뷰 | 코드 품질 검토 및 개선 제안 (Reviewer: Gemini 3.1 Pro High) |
| `/ag-map` | 맵 갱신 | 현재 프로젝트 구조 및 기술 부채 업데이트 |

## 🧠 에이전트별 특화 모델 (LLM Designations)

메인 커맨더는 **Claude Sonnet 4.6 (Thinking)** 이며, 각 에이전트는 아래 지정된 모델의 사고 방식을 차용하여 동작합니다.

| 에이전트 | 지정 모델 | 선정 이유 |
|----------|-----------|----------|
| **Main Commander** | Claude Sonnet 4.6 (Thinking) | 지시 이해·도구 활용·사용자 소통의 안정적 균형 |
| **Architect** | Claude Opus 4.6 (Thinking) | 앤스로픽 최고 모델, 가장 깊은 추상적 설계 능력 |
| **Planner** | Claude Sonnet 4.6 (Thinking) | Thinking 모드로 논리적 의존성 완벽 계산 |
| **Coder** | Claude Sonnet 4.6 (Thinking) | 고품질 코드 생성 및 엄격한 컨벤션 준수 |
| **Reviewer** | Gemini 3.1 Pro (High) | 방대한 컨텍스트로 프로젝트 전체 무결성 검수 |

## 📏 공통 코딩 규칙

- **언어**: 한국어 주석 및 기술 문서 작성 (코드 변수명은 영어)
- **에러 처리**: 모든 주요 로직에 `try-exception` 블록 및 로깅 필수
- **품질**: 함수는 단일 책임 원칙(SRP)을 준수, 매직 넘버 사용 금지
- **문서화**: 새로운 함수/클래스 추가 시 Docstring 작성 필수

## 📂 프로젝트 구조 관리

- 모든 설계 및 계획 문서는 `.agents/context/` 디렉토리에 보관합니다.
- 진행 중인 작업은 `.agents/context/tasks/`에서 관리합니다.

---
*이 시스템은 `claude-agent-system`을 Antigravity 환경에 맞게 최적화한 버전입니다.*
