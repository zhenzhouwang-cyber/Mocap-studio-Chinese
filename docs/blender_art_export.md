# 动捕数据与 Blender / 艺术创作

除 TouchDesigner 外，本工具导出的数据可用于 **Blender** 或**直接使用动捕数据进行艺术创作**。

---

## 1. 导出格式与用途

| 导出项 | 格式 | Blender / 艺术创作用途 |
|--------|------|------------------------|
| **CSV 时间序列** | `*_mocap_timeseries.csv` | 每行一帧，列含 `time`, `frame` 及各 marker 的 `_x`, `_y`, `_z`, `_speed` 等。可在 Blender 中用脚本或插件将列映射到空物体/骨骼关键帧，驱动角色或抽象几何。 |
| **TouchDesigner 格式** | `*_mocap_td.csv` | 与上结构相同，便于在 TD 中一条时间轴驱动视觉与声音，或与 Blender 渲染结果配合。 |
| **联合 CSV（动捕+音频）** | `*_joint_timeseries.csv` | 同一时间轴含动捕通道与音频特征（pitch, rms, brightness），适合「唱做一体」的视听创作。 |
| **JSON 分析结果** | `*_mocap_analysis.json` | 含 meta、运动学、程式化指标、拉班近似、身段段落等，可供 Blender 插件或外部脚本读取，用于**参数化驱动**（如用幅度/圆顺度控制粒子、用节奏控制剪辑）。 |

---

## 2. Blender 中的使用思路

- **方式一：CSV 驱动空物体或骨骼**  
  - 将 CSV 导入为表格（Blender 无内置 CSV 导入，需用脚本）。  
  - 用 Python 脚本按帧读取各行，将 `Marker名_x/y/z` 写入空物体（Empty）的 `location`，或写入骨骼的 world location，再烘焙为关键帧。  
  - 可只选用部分 marker 对应到 Blender 骨骼，其余做辅助点或粒子发射源。

- **方式二：先转 BVH/FBX 再进 Blender**  
  - 若本工具数据来源于 C3D/CSV，可先用第三方工具（如 MotionBuilder、Blender 插件、或本工具后续若支持）将 C3D/CSV 转为 **BVH** 或 **FBX**，再在 Blender 中「文件 → 导入 → BVH/FBX」直接得到带关键帧的骨骼动画。  
  - 本工具当前支持从 **FBX** 加载（通过 Blender 子进程导出 CSV），反向「分析结果 → 导出 BVH」若需可后续扩展。

- **方式三：用分析结果做参数化艺术**  
  - 将 JSON 中的 `laban_approx`（Space/Effort/Shape）、`rhythm`（速度剖面、停顿）、`action_segments` 等读入 Blender 脚本或几何节点，驱动材质、粒子、相机路径等，实现**基于程式化指标的艺术化再创作**。

---

## 3. 直接使用动捕数据创作

- **TD**：见 [TouchDesigner 导出说明](touchdesigner_export.md)，Table DAT + CHOP 或 CSV 导入即可。  
- **Blender**：见上文 CSV/JSON 驱动。  
- **其他**：导出的 CSV/JSON 为通用表格与键值结构，可在 Max/MSP、Processing、Unity、Unreal 等中按需解析，用于实时或离线艺术创作。

---

## 4. 引用

指标定义见 [opera_metrics.md](opera_metrics.md)；TD 列命名与单位见 [touchdesigner_export.md](touchdesigner_export.md)。
