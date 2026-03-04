# TouchDesigner 导出说明（CHOP 友好）

本工具导出的动捕（及可选联合音频）CSV 可在 TouchDesigner 中作为表格或 CHOP 使用，便于一条时间轴驱动视觉与声音参数。

---

## 1. 导出格式概览

| 导出项 | 文件名示例 | 内容 |
|--------|------------|------|
| 动捕时间序列 | `*_mocap_timeseries.csv` | 行=帧，列= time, frame + 各 marker 的 x/y/z、displacement、speed + mean_speed |
| TouchDesigner 格式 | `*_mocap_td.csv` | 与上相同，仅命名习惯称 TD 用 |
| 联合（动捕+音频） | `*_joint_timeseries.csv` | 上列 + pitch_hz, pitch_midi, rms, brightness（需先上传关联音频） |

---

## 2. 列命名与单位

- **time**：时间（秒），从 0 起。
- **frame**：帧索引（整数），从 0 起。
- **Marker 相关**：每个 marker 占多列：
  - `{Marker名}_x`, `{Marker名}_y`, `{Marker名}_z`：位置（单位与原始数据一致，通常为**米**，Vicon 常见为 mm 时需自行换算）。
  - `{Marker名}_displacement`：相对前一帧的位移模长。
  - `{Marker名}_speed`：该 marker 瞬时速度模长。
- **mean_speed**：该帧全体 marker 平均速度。
- **联合 CSV 中音频列**：
  - `pitch_hz`：音高（Hz），静音可为空。
  - `pitch_midi`：音高（MIDI 音高）。
  - `rms`：能量（RMS）。
  - `brightness`：频谱亮度（Hz）。

---

## 3. 在 TouchDesigner 中加载

### 方式一：Table DAT → 按列驱动参数

1. 添加 **Table DAT**。
2. 在 **File** 中选择导出的 CSV 文件（或通过 **Select** 选 DAT 引用）。
3. 将 **Import Type** 设为 **CSV**，确保第一行为列名、逗号分隔。
4. 用 **Select** 或 **CHOP Execute** 等按行索引或 `time` 列采样：例如用 **Script CHOP** 或 **Math CHOP** 根据当前时间 `absTime.seconds` 插值得到某列的值，再驱动 TOP/CHOP 参数。

### 方式二：Table DAT → CHOP（列即通道）

1. 用 **Table DAT** 读入 CSV（同上）。
2. 使用 **Convert to CHOP**（或 **Table to CHOP** 等节点，视版本而定）：将 Table 的列转为 CHOP 的通道，行对应时间或索引。
3. 若 Table 第一列是 `time`，可设 CHOP 的 **Index** 或 **Sample Rate** 与时间轴一致，便于与 **Timeline** 或 **Timer CHOP** 对齐播放。

### 方式三：CHOP 直接读 CSV（部分版本/插件）

若使用支持 CSV 的 **File In CHOP** 或社区组件，可直接将 CSV 读成 CHOP，列名即通道名。请以当前 TD 版本文档为准。

---

## 4. 使用建议

- **时间对齐**：用 `time` 列与 `absTime.seconds` 或 Timeline 对齐，对联合 CSV 可同时驱动动捕通道与 pitch/rms/brightness。
- **缺失值**：CSV 中空单元格表示该帧该通道无有效值，在 TD 中可做插值或钳位。
- **单位**：坐标与速度单位依赖原始动捕（常见为米或毫米），在 TD 中缩放或换算后再驱动场景。

---

## 5. 引用

指标定义与动捕分析流程见本仓库 `docs/opera_metrics.md`；联合时间轴与唱做关联见分析模块 `analysis/audio_sync.py`。
