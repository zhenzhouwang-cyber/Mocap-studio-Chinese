"""启动戏曲动捕分析 Streamlit 界面。"""
import subprocess
import sys
from pathlib import Path

if __name__ == "__main__":
    gui_path = Path(__file__).parent / "opera_mocap_tool" / "gui.py"
    subprocess.run([
        sys.executable, "-m", "streamlit", "run",
        str(gui_path),
        "--server.headless", "true",
    ])
