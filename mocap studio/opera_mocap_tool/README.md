# 京剧动捕数据分析工具

基于 Vicon 光学动捕数据的**京剧**动作分析工具，用于 TouchDesigner 数字艺术创作。

> **剧种范围**：本工具仅支持京剧（京戏），不适用于昆曲、秦腔等其他剧种。分析框架依据京剧身段、水袖、程式化等特征设计。

## 功能

- **数据加载**：支持 C3D、CSV 格式
- **预处理**：抖动滤波（Butterworth / Savitzky-Golay）、丢点插值
- **运动学分析**：轨迹、速度、加速度、位移、空间范围
- **戏曲特征**：幅度、圆顺度、节奏、程式化程度
- **节奏分析**：速度剖面、停顿检测、身段段落切分
- **唱做关联**：可选关联音频，得到节拍偏移、段落重叠、速度–能量相关（学术报告用）
- **导出**：JSON、CSV、PNG 图表、TouchDesigner 格式；可选联合 CSV（动捕+音频，见 [TouchDesigner 导出说明](../docs/touchdesigner_export.md)）

## 安装

```bash
pip install -e .
# 或
pip install scipy c3d streamlit
```

## 使用

### 命令行

```bash
# 单文件分析
opera-mocap-analyze run path/to/file.c3d -o output_dir

# 批量分析
opera-mocap-analyze batch path/to/directory --csv --plot
```

### Python API

```python
from opera_mocap_tool import analyze, export

result = analyze("path/to/mocap.c3d")
json_path, csv_path, plot_path, td_path = export(result, output_dir=".", write_csv=True, write_plot=True)
```

### Streamlit 界面

```bash
# 在项目根目录执行
streamlit run opera_mocap_tool/gui.py
# 或
python -m opera_mocap_tool
```

或双击 `run_mocap_gui.pyw`（Windows）。

### FBX 与 Blender

- 支持通过 **FBX** 加载动画：需本机安装 **Blender**，并在界面中填写 Blender 可执行文件路径（如 `E:\Software\blender.exe`）。未填路径时上传 FBX 会提示先填写再分析。
- 导出时按 FBX 内 Armature 的动画帧范围导出，保证完整时长；若时长偏短，请在 Blender 中把时间轴设为完整范围后重新导出。

## 学理依据（京剧）

- 京剧程式化理论：精选、装饰、圆柔顺美
- 京剧身段与水袖技法（甩、掸、拨、扬等）
- 动捕分析：人体运动学、时序分析、数据质量评估
- 程式化指标定义（可引用）：见 [opera_metrics.md](../docs/opera_metrics.md)
- TouchDesigner 导出与 CHOP 使用：见 [touchdesigner_export.md](../docs/touchdesigner_export.md)
- Blender 与动捕艺术创作：见 [blender_art_export.md](../docs/blender_art_export.md)（CSV/JSON 驱动 Blender、参数化创作）

## 上传 GitHub（留档）

在项目根目录执行：

```bash
git init
git add .
git commit -m "Initial commit: 京剧动捕/音频分析工具"
git branch -M main
git remote add origin https://github.com/<你的用户名>/<仓库名>.git
git push -u origin main
```

推送前请确认已在 GitHub 创建好空仓库；若需认证，可使用 SSH 地址或 Personal Access Token。
