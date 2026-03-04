@echo off
chcp 65001 > nul
:: ============================================================
:: daily_update.bat  -  일일보고 자동 업데이트 배치 파일
::
:: [역할]
::   퇴근 전 또는 퇴근 후 1회 실행하면:
::   1. 오늘 보낸 메일 목록을 today_sent.md로 정리 (보고서 작성 참고)
::   2. Outlook "나의 일일보고" 폴더를 스캔하여
::      2026_H1.md에 오늘 보고서를 자동 추가
::
:: [실행 방법]
::   더블클릭 또는 PowerShell에서:
::     .\daily_update.bat
::
:: [스케줄러 자동 실행 등록]
::   아래 PowerShell 명령을 1회 실행하면 매일 오후 6시 자동 실행:
::     $action  = New-ScheduledTaskAction -Execute "C:\TEST\dailyreport\daily_update.bat"
::     $trigger = New-ScheduledTaskTrigger -Daily -At "18:00"
::     Register-ScheduledTask -Action $action -Trigger $trigger -TaskName "DailyReportUpdate" -RunLevel Highest
:: ============================================================

setlocal
set "SCRIPT_DIR=%~dp0"
set "PYTHON=python"
set "LOG_FILE=%SCRIPT_DIR%daily_update.log"

echo.
echo ====================================================
echo   일일보고 자동 업데이트 시작
echo   실행 시각: %date% %time%
echo ====================================================
echo.

:: ── STEP 1: 오늘 보낸 메일 조회 → today_sent.md ───────────
echo [1/2] 오늘 보낸 메일 조회 중...
echo ----------------------------------------
%PYTHON% "%SCRIPT_DIR%scripts\get_today_sent.py"
if %errorlevel% neq 0 (
    echo [경고] get_today_sent.py 실행 중 오류 발생 (계속 진행)
) else (
    echo       → today_sent.md 저장 완료
)

echo.

:: ── STEP 2: 일일보고 반기 파일 업데이트 ──────────────────
echo [2/2] 일일보고 반기 파일 업데이트 중...
echo ----------------------------------------
%PYTHON% "%SCRIPT_DIR%scripts\save_all_reports.py"
if %errorlevel% neq 0 (
    echo [오류] save_all_reports.py 실행 실패!
    echo        Outlook이 실행 중인지 확인하세요.
    goto :END
)

echo.
echo ====================================================
echo   완료! reports\2026_H1.md 업데이트됨
echo   실행 종료: %date% %time%
echo ====================================================

:END
echo.
pause
