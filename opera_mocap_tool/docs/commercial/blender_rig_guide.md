# Blender绑定使用指南

京剧角色智能绑定工具 - 生成专业的京剧角色骨骼和材质

## 概述

Blender绑定模块提供完整的京剧角色绑定解决方案，包括：
- 京剧专用骨骼系统（生、旦、净、丑）
- 程式化动作库（水袖、翎子、髯口、靠旗等）
- 脸谱和戏服材质库
- 一键导出到Blender

## 快速开始

### 基本用法

```python
from opera_mocap_tool.commercial.blender_rig import (
    DangType,
    RigConfig,
    OperaRigBuilder,
)

# 1. 创建配置
config = RigConfig(
    DangType.SHENG,  # 生角
    height=1.7,       # 身高(米)
    gender="male",
)

# 2. 创建绑定构建器
builder = OperaRigBuilder(config)

# 3. 构建基础骨架
bones = builder.build_base_rig()

# 4. 添加京剧特有骨骼
bones = builder.add_opera_bones()

# 5. 导出为Blender脚本
builder.export_to_blender("opera_rig.py")
```

然后在Blender中运行生成的脚本即可创建绑定。

## 京剧行当

### 支持的行当

| 行当 | 代码 | 描述 |
|------|------|------|
| 生 | `SHENG` | 男性角色 |
| 旦 | `DAN` | 女性角色 |
| 净 | `JING` | 花脸角色 |
| 丑 | `CHOU` | 丑角角色 |

### 选择行当

```python
# 生角（男性）
config = RigConfig(dang=DangType.SHENG)

# 旦角（女性）
config = RigConfig(dang=DangType.DAN)

# 净角（花脸）
config = RigConfig(dang=DangType.JING)

# 丑角
config = RigConfig(dang=DangType.CHOU)
```

## 骨骼系统

### 基础骨骼

模块包含完整的人体骨骼系统：

```
脊椎:   spine_base → spine_mid → spine_upper → neck → head
手臂:   shoulder → upper_arm → forearm → hand
腿部:   hip → thigh → shin → foot → toe
```

### 京剧特有骨骼

模块还包含京剧特有的装饰骨骼：

```python
bones = builder.add_opera_bones()
```

添加的特有骨骼包括：

| 骨骼类型 | 名称 | 描述 |
|----------|------|------|
| 翎子 | feather_l, feather_r | 头饰翎子 |
| 髯口 | beard_main, beard_l, beard_r | 胡须 |
| 水袖 | sleeve_l, sleeve_r | 舞袖 |
| 靠旗 | banner_l, banner_r | 背后靠旗 |
| 帽翅 | hat_l, hat_r | 帽翅 |

### 骨骼配置参数

```python
config = RigConfig(
    dang=DangType.DAN,
    scale=1.0,        # 缩放比例
    height=1.7,       # 身高(米)
    gender="female",  # 性别
    age_group="adult", # 年龄组
    prefix_l="L_",   # 左侧骨骼前缀
    prefix_r="R_",   # 右侧骨骼前缀
    detail_level="high",  # 详细程度: low/medium/high
)
```

## 材质库

### 脸谱材质

```python
from opera_mocap_tool.commercial.blender_rig import OperaMaterialLibrary

# 获取脸谱材质
face_red = OperaMaterialLibrary.get_material("face_red")      # 关公
face_white = OperaMaterialLibrary.get_material("face_white")  # 曹操
face_black = OperaMaterialLibrary.get_material("face_black")  # 张飞
face_green = OperaMaterialLibrary.get_material("face_green")  # 绿脸
```

### 戏服材质

```python
# 戏服材质
costume_red = OperaMaterialLibrary.get_material("costume_red")    # 红靠
costume_gold = OperaMaterialLibrary.get_material("costume_gold")  # 金靠
costume_blue = OperaMaterialLibrary.get_material("costume_blue")  # 蓝靠
```

### 材质属性

每个材质包含以下属性：

```python
material = OperaMaterialLibrary.get_material("face_red")

# 属性说明
base_color = material["base_color"]    # 基础颜色 (RGBA)
roughness = material["roughness"]       # 粗糙度
metallic = material.get("metallic", 0)  # 金属度
specular = material.get("specular", 0.5)# 高光
```

### 导出材质

```python
# 导出全部材质为JSON
OperaMaterialLibrary.export_preset("materials.json")

# 生成Blender材质脚本
script = OperaMaterialLibrary.generate_blender_script()
```

## 动画库

### 程式化动作

模块提供预设的京剧程式化动作：

```python
from opera_mocap_tool.commercial.blender_rig import OperaAnimationLibrary

# 获取单个动画
sleeve_wave = OperaAnimationLibrary.get_animation("sleeve_wave")
sleeve_dust = OperaAnimationLibrary.get_animation("sleeve_dust")
hand_gesture = OperaAnimationLibrary.get_animation("hand_gesture")
fan_wave = OperaAnimationLibrary.get_animation("fan_wave")
```

### 按类别获取

```python
# 水袖动作
sleeve_animations = OperaAnimationLibrary.get_animations_by_category("sleeve")

# 手部动作
hand_animations = OperaAnimationLibrary.get_animations_by_category("hand")

# 扇子动作
fan_animations = OperaAnimationLibrary.get_animations_by_category("fan")
```

### 导出动画库

```python
# 导出为JSON
OperaAnimationLibrary.export_preset("animations.json")
```

## 导出格式

### 导出为JSON

```python
# 导出绑定配置为JSON
result = builder.export_to_json("rig_config.json")

# 返回结果
print(result)
# {'path': 'rig_config.json', 'bone_count': 42}
```

JSON格式包含：
- 绑定配置（行当、身高、性别等）
- 骨骼定义（位置、父子关系、roll角等）

### 导出为Blender脚本

```python
# 导出为Blender Python脚本
result = builder.export_to_blender("create_rig.py")

print(result)
# {'path': 'create_rig.py', 'bone_count': 42}
```

在Blender中使用：

```python
# 方法1: 文本编辑器运行
# 1. 打开Blender
# 2. 打开文本编辑器
# 3. 加载 create_rig.py
# 4. 点击运行脚本

# 方法2: 命令行运行
# blender --python create_rig.py
```

## 完整示例

### 创建完整的京剧角色

```python
from pathlib import Path
from opera_mocap_tool.commercial.blender_rig import (
    DangType,
    RigConfig,
    OperaRigBuilder,
    OperaMaterialLibrary,
    OperaAnimationLibrary,
)

# 1. 配置角色
config = RigConfig(
    dang=DangType.SHENG,
    height=1.75,
    gender="male",
    scale=1.0,
)

# 2. 创建绑定
builder = OperaRigBuilder(config)
bones = builder.build_base_rig()
bones = builder.add_opera_bones()

# 3. 导出绑定
output_dir = Path("./output")
output_dir.mkdir(exist_ok=True)

builder.export_to_json(output_dir / "rig.json")
builder.export_to_blender(output_dir / "create_rig.py")

# 4. 导出材质库
OperaMaterialLibrary.export_preset(output_dir / "materials.json")
material_script = OperaMaterialLibrary.generate_blender_script()
with open(output_dir / "create_materials.py", 'w') as f:
    f.write(material_script)

# 5. 导出动画库
OperaAnimationLibrary.export_preset(output_dir / "animations.json")

print("导出完成！")
```

### 在Blender中使用

```python
# 运行绑定脚本后，在Blender Python控制台：

# 查看骨骼
import bpy
arm = bpy.data.objects.get("OperaRig_sheng")
print(arm.name)

# 查看动画
print(arm.animation_data.nla_tracks)

# 应用材质
# 1. 运行 create_materials.py
# 2. 在材质属性中选择京剧材质
```

## 常见问题

### Q: 骨骼方向不对？
A: 检查 `roll` 参数，可在Blender中调整骨骼roll角。

### Q: 骨骼名称冲突？
A: 使用 `prefix_l` 和 `prefix_r` 参数自定义前缀。

### Q: 动画不播放？
A: 确保在Blender中选择了Armature对象，并切换到Pose模式。

### Q: 材质不显示？
A: 运行材质脚本后，需要在材质属性面板中手动分配材质。

## 最佳实践

1. **先创建基础绑定**：先导出基础骨骼，验证后再添加特有骨骼
2. **使用JSON调试**：JSON格式便于查看和修改
3. **分步导入**：先导入骨骼，再导入材质，最后导入动画
4. **备份原始数据**：导出前备份原始配置

## 相关文档

- [TD粒子系统指南](./td_particles_guide.md)
- [AI动作生成指南](./ai_motion_guide.md)
