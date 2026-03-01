@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo 正在启动动捕分析界面...
echo.
python -m streamlit run opera_mocap_tool/gui.py
if errorlevel 1 (
    echo.
    echo 若提示找不到 streamlit，请先安装：pip install streamlit
    pause
)
