@echo off
chcp 65001 >nul
cd /d "%~dp0舞蹈动作-科目三"
if not exist "art_demo.html" (
    echo 错误：未找到 art_demo.html，请确认 舞蹈动作-科目三 目录存在
    pause
    exit /b 1
)
echo 正在启动动捕数字艺术 Demo...
echo 浏览器将自动打开 http://localhost:8000/art_demo.html
echo 按 Ctrl+C 停止
python -m http.server 8000
pause
