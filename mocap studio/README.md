# Mocap Studio

京剧动作捕捉数据分析工作室

基于 Vicon 光学动捕数据的**京剧**动作分析工具，用于 TouchDesigner 数字艺术创作。

> **剧种范围**：本工具仅支持京剧（京戏），不适用于昆曲、秦腔等其他剧种。分析框架依据京剧身段、水袖、程式化等特征设计。

---

## 目录

- [功能特点](#功能特点)
- [目录结构](#目录结构)
- [快速开始](#快速开始)
- [安装依赖](#安装依赖)
- [使用方式](#使用方式)
- [数据格式支持](#数据格式支持)
- [分析功能](#分析功能)
- [导出格式](#导出格式)
- [学理依据](#学理依据)
- [常见问题](#常见问题)

---

## 功能特点

- **多格式支持**：支持 C3D、CSV、BVH、FBX 等动捕数据格式
- **数据预处理**：抖动滤波（Butterworth / Savitzky-Golay）、丢点插值
- **运动学分析**：轨迹、速度、加速度、位移、空间范围
- **戏曲特征分析**：幅度、圆顺度、节奏、程式化程度
- **节奏分析**：速度剖面、停顿检测、身段段落切分
- **唱做关联**：可选关联音频，得到节拍偏移、段落重叠、速度–能量相关
- **3D 可视化**：交互式 3D 骨骼可视化
- **导出功能**：JSON、CSV、PNG 图表、TouchDesigner 格式

---

## 目录结构

```
mocap studio/
├── opera_mocap_tool/          # 核心动捕工具包
│   ├── analysis/             # 分析模块
│   │   ├── audio_sync.py     # 音频同步分析
│   │   ├── balance.py        # 平衡分析
│   │   ├── frequency.py      # 频率分析
│   │   ├── kinematic.py      # 运动学分析
│   │   ├── laban_approx.py   # 拉班近似
│   │   ├── opera_features.py # 京剧特征
│   │   ├── quality.py        # 质量评估
│   │   ├── reference_compare.py # 参考比对
│   │   ├── rhythm.py         # 节奏分析
│   │   └── segments.py       # 段落分割
│   ├── io/                   # 文件读写模块
│   │   ├── bvh_reader.py     # BVH 读取
│   │   ├── c3d_reader.py     # C3D 读取
│   │   ├── csv_reader.py     # CSV 读取
│   │   ├── fbx_reader.py     # FBX 读取
│   │   └── loaders.py        # 统一加载接口
│   ├── preprocessing/        # 预处理模块
│   │   ├── filter.py         # 滤波
│   │   ├── interpolation.py  # 插值
│   │   └── quality.py        # 质量处理
│   ├── sample_data/          # 示例数据
│   ├── docs/                 # 文档
│   ├── analyzer.py           # 分析器
│   ├── export.py             # 导出模块
│   ├── gui.py                # Streamlit 界面
│   ├── skeleton.py           # 骨骼定义
│   ├── viewer_3d.py          # 3D 查看器
│   └── plotting.py           # 绘图模块
├── sample_mocap_mocap_analysis.json   # 样本分析结果
├── sample_mocap_mocap_analysis.png    # 样本分析图表
├── sample_mocap_mocap_timeseries.csv  # 样本时间序列
├── requirements.txt          # Python 依赖
├── run_mocap_gui.pyw         # Windows GUI 启动脚本
├── 启动动捕界面.bat          # 启动动捕界面
├── 启动艺术Demo.bat          # 启动艺术Demo
└── test_bvh.py               # BVH 测试脚本
```

---

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 启动图形界面

**方式一**：双击 `run_mocap_gui.pyw`

**方式二**：双击 `启动动捕界面.bat`

**方式三**：命令行启动
```bash
streamlit run opera_mocap_tool/gui.py
```

### 3. 使用示例

启动后，在浏览器中打开界面，上传动捕文件（C3D、CSV、BVH、FBX）即可进行分析。

---

## 安装依赖

```bash
pip install -r requirements.txt
```

主要依赖：
- `streamlit` - Web 图形界面
- `scipy` - 科学计算
- `numpy` - 数值计算
- `pandas` - 数据处理
- `plotly` - 交互式图表
- `c3d` - C3D 文件读取
- `matplotlib` - 绘图
- `librosa` - 音频分析

---

## 使用方式

### Streamlit 图形界面

```bash
# 方式1：双击 run_mocap_gui.pyw
# 方式2：双击 启动动捕界面.bat
# 方式3：命令行
streamlit run opera_mocap_tool/gui.py
```

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

# 分析动捕文件
result = analyze("path/to/mocap.c3d")

# 导出结果
json_path, csv_path, plot_path, td_path = export(
    result, 
    output_dir=".", 
    write_csv=True, 
    write_plot=True
)
```

---

## 数据格式支持

| 格式 | 说明 | 依赖 |
|------|------|------|
| C3D | Vicon 标准格式 | c3d 库 |
| CSV | 自定义 CSV 格式 | - |
| BVH | Biovision 层级数据 | - |
| FBX | Autodesk FBX 动画 | Blender (可选) |

> **注意**：使用 FBX 格式需要安装 Blender，并在界面中填写 Blender 可执行文件路径。

---

## 分析功能

### 1. 运动学分析
- 轨迹追踪
- 速度/加速度计算
- 位移分析
- 空间范围估算

### 2. 京剧程式化特征
- **幅度**：动作空间范围
- **圆顺度**：动作流畅程度
- **节奏**：速度剖面、停顿检测
- **程式化程度**：动作标准化程度

### 3. 节奏分析
- 速度剖面提取
- 停顿检测
- 身段段落切分

### 4. 音频同步（可选）
- 节拍偏移分析
- 段落重叠检测
- 速度-能量相关性

### 5. 质量评估
- 数据完整性检查
- 抖动检测
- 丢点识别

---

## 导出格式

| 格式 | 文件名 | 用途 |
|------|--------|------|
| JSON 分析结果 | `*_mocap_analysis.json` | 程序化驱动、参数化创作 |
| CSV 时间序列 | `*_mocap_timeseries.csv` | Blender、Excel 分析 |
| PNG 图表 | `*_mocap_analysis.png` | 报告、展示 |
| TD 格式 | `*_mocap_td.csv` | TouchDesigner CHOP |

详细说明见：
- [TouchDesigner 导出说明](opera_mocap_tool/docs/touchdesigner_export.md)
- [Blender 艺术创作说明](docs/blender_art_export.md)

---

## 学理依据

- **京剧程式化理论**：精选、装饰、圆柔顺美
- **京剧身段与水袖技法**：甩、掸、拨、扬等
- **动捕分析**：人体运动学、时序分析、数据质量评估
- **程式化指标定义**：见 [opera_metrics.md](opera_mocap_tool/docs/opera_metrics.md)

---

## 常见问题

### Q: 上传 FBX 报错提示需要填写 Blender 路径？
**A**: 使用 FBX 格式需要安装 Blender。在界面的设置区域填写 Blender 可执行文件路径（如 `E:\Software\blender.exe`）。

### Q: 分析结果中的指标含义是什么？
**A**: 见 [opera_metrics.md](opera_mocap_tool/docs/opera_metrics.md) 中的详细定义。

### Q: 如何在 TouchDesigner 中使用导出的数据？
**A**: 见 [TouchDesigner 导出说明](opera_mocap_tool/docs/touchdesigner_export.md)。

### Q: 如何在 Blender 中使用动捕数据？
**A**: 见 [Blender 艺术创作说明](docs/blender_art_export.md)。

---

## 示例数据

文件夹中包含示例数据 `sample_mocap_*`，可用于测试：
- `sample_mocap_mocap_analysis.json` - 分析结果
- `sample_mocap_mocap_analysis.png` - 可视化图表
- `sample_mocap_mocap_timeseries.csv` - 时间序列数据

另外 `opera_mocap_tool/sample_data/` 目录中有更多示例数据。

---

## 许可与联系

本工具仅供学术研究和中国传统戏曲数字化保护使用。

如有问题，请联系项目维护者。

---

*更新时间：2026年3月*
