@echo off
chcp 65001 >nul
echo 正在設定開機自動啟動...

:: 取得 Python 路徑
for /f "tokens=*" %%i in ('python -c "import sys; print(sys.executable)"') do set PYTHON=%%i

:: 取得專案路徑
set PROJECT=D:\project\個股監測

:: 建立 Windows 工作排程器任務
schtasks /create /tn "港股監測系統" /tr "\"%PYTHON%\" \"%PROJECT%\app.py\"" /sc onlogon /ru "%USERNAME%" /f /rl highest

if %errorlevel% == 0 (
    echo.
    echo [成功] 開機自動啟動已設定！
    echo        登入 Windows 後伺服器會自動在背景啟動
    echo        網址: http://localhost:5000
) else (
    echo.
    echo [失敗] 請用「系統管理員」身份執行此檔案
)
echo.
pause
