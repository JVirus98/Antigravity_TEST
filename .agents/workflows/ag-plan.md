---
description: 작업을 세부 단위로 분할하고 실행 체크리스트를 생성합니다.
---

# /ag-plan - Planner 모드 (Model: Claude Sonnet 4.6 Thinking)

복잡한 요구사항을 실행 가능한 작은 단위의 작업(Sub-tasks)으로 나눕니다. Claude Sonnet 4.6 Thinking 모드의 논리적 추론으로 의존성 오류 없는 완벽한 계획을 수립합니다.

## 실행 절차

1. **요구사항 분석**
   - 사용자의 요청을 분석하고 기존 코드와의 의존성을 파악합니다.

2. **할 일 목록(Checklist) 작성**
   - `.agents/context/tasks/[task-name].md` 파일을 생성하여 다음 내용을 기록합니다:
     - 목표 (Goal)
     - 기술적 고려사항
     - 단계별 체크리스트 (Todo List)

3. **피드백 요청**
   - 계획된 내용을 사용자에게 보여주고 승인을 받습니다.
