@echo off
chcp 65001 >nul
title 港股監測系統
echo ================================================
echo   港股監測系統啟動中...
echo   公開網址: https://overprompt-nonabsolutistically-gertrud.ngrok-free.dev
echo   關閉此視窗即停止所有服務
echo ================================================
cd /d "D:\project\個股監測"
start "港股Flask" /min python app.py
echo Flask 啟動中，等待 5 秒...
timeout /t 5 /nobreak >nul
echo 啟動 ngrok 隧道...
ngrok http --url=overprompt-nonabsolutistically-gertrud.ngrok-free.dev 5000
pause
