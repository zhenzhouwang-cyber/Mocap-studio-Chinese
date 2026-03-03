# Mocap Studio

京剧动作捕捉数据分析工作室

## 项目简介

基于 Vicon 光学动捕数据的**京剧**动作分析工具，用于 TouchDesigner 数字艺术创作。

> **剧种范围**：本工具仅支持京剧（京戏），不适用于昆曲、秦腔等其他剧种。

---

## 快速开始

### 1. 进入项目目录

```bash
cd mocap studio
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 启动图形界面

**方式一**：双击 `run_mocap_gui.pyw`

**方式二**：双击 `启动动捕界面.bat`

**方式三**：命令行启动
```bash
streamlit run opera_mocap_tool/gui.py
```

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

## 数据格式支持

| 格式 | 说明 | 依赖 |
|------|------|------|
| C3D | Vicon 标准格式 | c3d 库 |
| CSV | 自定义 CSV 格式 | - |
| BVH | Biovision 层级数据 | - |
| FBX | Autodesk FBX 动画 | Blender (可选) |

---

## 详细文档

详细使用说明请查看：[mocap studio/README.md](mocap%20studio/README.md)

---

## 许可与联系

本工具仅供学术研究和中国传统戏曲数字化保护使用。

如有问题，请联系项目维护者。

---

*更新时间：2026年3月*
