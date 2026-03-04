# 云手生成艺术 - TouchDesigner 使用指南

本文档说明如何使用 `opera_mocap_tool` 导出的云手数据在 TouchDesigner 中创作生成艺术。

---

## 快速开始

### 1. 导出云手数据

在 `☁️ 云手分析` Tab 中：

1. 上传云手动捕/视频文件
2. 分析完成后，在「生成艺术数据导出」部分
2. 选择导出格式：`TouchDesigner参数映射`
3. 点击「导出云手数据」
4. 下载生成的 JSON 文件

### 2. 在 TouchDesigner 中使用

#### 方式 A：读取 JSON 参数

```python
# 在 TouchDesigner 的 Script DAT 中
import json

# 读取导出的参数文件
with open('yunshou_td_params.json', 'r') as f:
    params = json.load(f)

# 访问参数
particles = params['particles']
flow = params['flow']
motion = params['motion']
```

#### 方式 B：使用 Python 脚本模板

导出的 Python 脚本可以直接复制到 TouchDesigner 的 Script DAT 中使用。

---

## 参数说明

### 粒子系统参数 (`particles`)

| 参数 | 说明 | 取值范围 |
|------|------|----------|
| `emitter_position` | 粒子发射位置序列 | XYZ 坐标数组 |
| `speed_scale` | 粒子速度缩放 | 0.5 - 2.0 |
| `particle_count` | 粒子数量 | 0 - 10000 |
| `lifetime` | 粒子生命周期(秒) | 2.0 - 4.0 |
| `spread` | 粒子扩散范围 | 0.0 - 2.0 |
| `color.primary` | 主色调 | Hex 颜色 |
| `color.secondary` | 副色调 | Hex 颜色 |
| `color.accent` | 强调色 | Hex 颜色 |

### 流动效果参数 (`flow`)

| 参数 | 说明 | 取值范围 |
|------|------|----------|
| `intensity` | 流动强度 | 0.0 - 1.0 |
| `turbulence` | 湍流程度 | 0.0 - 1.0 |
| `direction_consistency` | 方向一致性 | 0.0 - 1.0 |
| `spiral_tightness` | 螺旋紧密程度 | 0.0 - 1.0 |
| `spiral_radius` | 螺旋半径 | 0.0 - 1.0 |

### 运动效果参数 (`motion`)

| 参数 | 说明 | 取值范围 |
|------|------|----------|
| `mirror_intensity` | 镜像效果强度 | 0.0 - 1.0 |
| `breathing.enabled` | 是否启用呼吸效果 | bool |
| `breathing.pause_count` | 停顿次数 | 整数 |
| `glow_intensity` | 发光强度 | 0.0 - 1.0 |
| `blur` | 模糊程度 | 0.0 - 1.0 |

### 形态参数 (`shape`)

| 参数 | 说明 | 取值范围 |
|------|------|----------|
| `ring_coupling` | 多层环形联动程度 | 0.0 - 1.0 |
| `ring_radii` | 环形半径序列 | 浮点数数组 |
| `ring_rotation_speed` | 环形旋转速度 | 0.0 - 1.0 |
| `expansion` | 扩展/收拢程度 | 0.0 - 1.0 |

---

## 行当色彩映射

| 行当 | 主色 | 副色 | 强调色 |
|------|------|------|--------|
| 老生 | #2C3E50 (深蓝) | #ECF0F1 (浅灰白) | #3498DB (蓝色) |
| 武生 | #C0392B (深红) | #E74C3C (红色) | #F39C12 (橙色) |
| 旦角 | #E8D5B7 (淡粉) | #F5E6D3 (米白) | #F8B4B4 (浅红) |
| 丑行 | #F39C12 (金色) | #F1C40F (黄色) | #E67E22 (橙色) |

---

## 创作示例

### 示例 1：粒子流动场

```
1. 创建 Particle System COMP
2. 在 Script DAT 中读取 yunshou_td_params.json
3. 使用 emitter_position 设置发射位置
4. 使用 flow.intensity 控制流动强度
5. 使用 color.primary/secondary 设置粒子颜色
```

### 示例 2：螺旋粒子

```
1. 创建 Spiral SOP 或 Particle System
2. 使用 flow.spiral_tightness 控制螺旋紧密程度
3. 使用 flow.spiral_radius 控制螺旋半径
4. 使用 shape.ring_rotation_speed 控制旋转
```

### 示例 3：呼吸闪烁效果

```
1. 创建 Rectangle SOP 或 Circle SOP
2. 在 Script DAT 中检测 motion.breathing.pause_points
3. 使用 pause_points 触发透明度变化
4. 使用 motion.glow_intensity 控制发光
```

### 示例 4：对称镜像

```
1. 创建两个相同的粒子系统
2. 使用 motion.mirror_intensity 控制镜像程度
3. 一组使用原始位置，另一组使用 X 轴镜像位置
```

---

## 高级用法

### 实时轨迹驱动

```python
# Script DAT 示例
def updateFrame(frame):
    params = yunshou_params
    
    # 获取当前帧的轨迹位置
    emitter_pos = params['particles']['emitter_position']
    idx = frame % len(emitter_pos)
    pos = emitter_pos[idx]
    
    # 更新粒子发射位置
    particleSystem.par.tx = pos['x']
    particleSystem.par.ty = pos['y']
    particleSystem.par.tz = pos['z']
```

### 音频同步

```python
# 与京剧锣鼓同步
rhythm = params['rhythm']
beat_points = rhythm['beat_points']  # 节拍点帧号
pause_points = rhythm['pause_points']  # 停顿点

# 在节拍点触发效果
if frame in beat_points:
    triggerEffect()
```

---

## 常见问题

### Q: 粒子数量太大怎么办？
A: 可以使用 `particle_count` 参数限制，或在导出时采样轨迹数据。

### Q: 如何调整颜色？
A: 直接编辑导出的 JSON 文件中的 `color` 参数，或使用 `DANG_COLOR_PALETTES` 在代码中重新映射。

### Q: 如何实现实时录制？
A: 结合 `video_pose.py` 实现实时姿态估计，实时输出到 TouchDesigner。

---

## 相关文件

- `opera_mocap_tool/analysis/yunshou_features.py` - 云手特征提取
- `opera_mocap_tool/analysis/yunshou_art_mapping.py` - 生成艺术参数映射
- `opera_mocap_tool/io/yunshou_references.py` - 云手参考库

---

*文档版本：1.0*
