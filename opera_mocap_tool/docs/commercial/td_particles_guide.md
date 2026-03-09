# TD粒子系统使用指南

TouchDesigner 粒子效果引擎 - 基于动捕数据的实时视觉效果

## 概述

TD粒子系统模块提供基于动作捕捉数据的实时粒子效果生成，可直接传输到TouchDesigner用于舞台艺术创作。

## 安装依赖

```bash
pip install numpy
```

可选 - UDP传输需要网络支持。

## 快速开始

### 基本用法

```python
from opera_mocap_tool.commercial.td_particles import (
    ParticlePreset,
    ParticleEmitter,
    ParticleSystem,
    PresetLibrary,
)

# 1. 创建粒子发射器
emitter = PresetLibrary.create_emitter_from_preset(
    ParticlePreset.FIRE,
    marker_name="hand_r"
)

# 2. 创建粒子系统
system = ParticleSystem()
system.add_emitter(emitter)

# 3. 启动系统
system.start()

# 4. 更新粒子系统（通常在渲染循环中调用）
positions = {
    "hand_r": (0.5, 1.2, 0.3),  # 从动捕数据获取的位置
}
system.update(positions, delta_time=0.016)  # 60fps

# 5. 停止系统
system.stop()
```

## 粒子预设

| 预设 | 描述 | 适用场景 |
|------|------|----------|
| `INK` | 水墨效果 | 京剧水墨舞台 |
| `GLOW` | 发光拖尾 | 能量效果 |
| `FIRE` | 火焰效果 | 战斗场景 |
| `SNOW` | 雪花效果 | 冬日意境 |
| `SPARKS` | 火花效果 | 金属质感 |
| `GOLD` | 金粉效果 | 黄金战甲 |
| `SILK` | 丝绸效果 | 舞袖效果 |
| `ENERGY` | 能量效果 | 法术特效 |

## 发射器配置

### 基础参数

```python
emitter = ParticleEmitter(
    marker_name="head",           # 关联的动捕marker名称
    emit_rate=50.0,                # 每秒发射粒子数
    emit_probability=1.0,          # 发射概率 (0-1)
    initial_speed=1.0,             # 初始速度
    speed_variance=0.3,           # 速度随机性
    lifetime=2.0,                 # 粒子生命周期(秒)
    lifetime_variance=0.5,        # 生命周期随机性
    size=0.1,                     # 粒子大小
    size_variance=0.05,           # 大小随机性
)
```

### 颜色配置

```python
emitter = ParticleEmitter(
    marker_name="hand_l",
    color_start=(1.0, 0.0, 0.0, 1.0),  # RGBA 起始颜色
    color_end=(0.0, 0.0, 0.0, 0.0),     # RGBA 结束颜色 (透明)
)
```

### 物理效果

```python
emitter = ParticleEmitter(
    marker_name="hand_r",
    gravity=0.5,                  # 重力影响
    wind=(0.0, 0.0, 0.1),        # 风向 (x, y, z)
    turbulence=0.2,              # 湍流强度
)
```

## 预设库

### 获取预设

```python
preset = PresetLibrary.get_preset(ParticlePreset.INK)
# 返回: {"emit_rate": 50.0, "color_start": (0.0, 0.0, 0.0, 0.8), ...}
```

### 从预设创建发射器

```python
emitter = PresetLibrary.create_emitter_from_preset(
    ParticlePreset.GLOW,
    marker_name="spine_upper",
)
```

## TouchDesigner 集成

### UDP传输

```python
from opera_mocap_tool.commercial.td_particles import TDParticleTransmitter

# 创建传输器
transmitter = TDParticleTransmitter(
    host="127.0.0.1",  # TD所在主机IP
    port=7000,          # TD监听端口
)

# 传输粒子数据
particles = [
    {
        "position": (x, y, z),
        "velocity": (vx, vy, vz),
        "life": 0.5,
        "size": 0.1,
        "color": (r, g, b, a),
    }
]

transmitter.send(particles)
```

### TD端接收

在TouchDesigner中使用DAT接收：

```
1. 添加一个 DAT: Table DAT 或 Text DAT
2. 设置接收模式为 "From UDP"
3. 端口设置为 7000
4. 解析接收到的JSON数据
```

## 导出配置

```python
import json
from pathlib import Path

# 导出为JSON
config = {
    "preset": "fire",
    "emitter": emitter.to_dict(),
    "system": {
        "max_particles": 10000,
        "bounds": (-10, -10, -10, 10, 10, 10),
    }
}

output_path = Path("particles_config.json")
with open(output_path, 'w') as f:
    json.dump(config, f, indent=2)
```

## 性能优化

### 粒子数量限制

```python
system = ParticleSystem(max_particles=5000)  # 建议值
```

### 发射速率调整

```python
emitter = ParticleEmitter(
    marker_name="hand",
    emit_rate=30,  # 降低以提高性能
)
```

### 使用GPU加速

对于大量粒子场景，建议在TouchDesigner中使用GPU粒子系统，本模块仅负责数据生成和传输。

## 完整示例

```python
from opera_mocap_tool.commercial.td_particles import (
    ParticlePreset,
    ParticleSystem,
    PresetLibrary,
    TDParticleTransmitter,
)
import numpy as np

# 创建粒子效果
system = ParticleSystem()

# 为多个身体部位添加发射器
for marker in ["hand_l", "hand_r", "head"]:
    emitter = PresetLibrary.create_emitter_from_preset(
        ParticlePreset.SILK,
        marker_name=marker,
    )
    emitter.emit_rate = 30
    system.add_emitter(emitter)

# 启动系统
system.start()

# 创建UDP传输器
transmitter = TDParticleTransmitter(host="127.0.0.1", port=7000)

# 模拟动捕数据更新
positions = {
    "hand_l": (0.0, 1.0, 0.0),
    "hand_r": (0.0, 1.0, 0.0),
    "head": (0.0, 1.5, 0.0),
}

# 在渲染循环中调用
dt = 1/60
for _ in range(300):  # 5秒 @ 60fps
    system.update(positions, dt)
    
    # 获取粒子数据
    particles = []
    for p in system._particles:
        particles.append({
            "position": p["position"],
            "velocity": p["velocity"],
            "life": p.get("life", 1.0),
            "size": p.get("size", 0.1),
        })
    
    # 传输到TD
    if particles:
        transmitter.send(particles)

system.stop()
```

## 常见问题

### Q: 粒子不显示？
A: 检查 `system._active` 是否为True，以及发射器关联的marker名称是否正确。

### Q: 传输延迟高？
A: 尝试使用二进制格式传输，或降低发射粒子数量。

### Q: 粒子穿模？
A: 调整 `bounds` 参数，或禁用边界检查。

## 相关文档

- [Blender绑定指南](./blender_rig_guide.md)
- [AI动作生成指南](./ai_motion_guide.md)
