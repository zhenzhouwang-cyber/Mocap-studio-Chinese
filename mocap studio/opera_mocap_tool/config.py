"""应用配置与常量。"""

from pathlib import Path

# 默认 Blender 路径（可按需修改）
DEFAULT_BLENDER_EXE = "E:\\Software\\blender.exe"

# 3D 查看器本地服务器端口
VIEWER_SERVER_PORT = 8765

# 临时查看器目录名
VIEWER_TEMP_DIR = "opera_mocap_viewer"

# 文件大小限制（MB）
MAX_UPLOAD_MB = 200

# 默认导出目录（JSON、CSV、PNG、TD 等）
DEFAULT_EXPORT_DIR = r"E:\document"

# UI 主题色（京剧红）
THEME_PRIMARY = "#8b2942"
THEME_PRIMARY_LIGHT = "#a83d5a"  # 浅色变体
