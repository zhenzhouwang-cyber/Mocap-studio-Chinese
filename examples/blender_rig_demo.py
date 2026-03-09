#!/usr/bin/env python
"""
Blender绑定示例。

展示如何使用商业模块创建京剧角色绑定和导出到Blender。

运行方式:
    python examples/blender_rig_demo.py

注意: 此脚本仅生成配置文件，需要在Blender中运行生成的脚本。
"""

import sys
import tempfile
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from opera_mocap_tool.commercial.blender_rig import (
    DangType,
    BodyPart,
    BoneDefinition,
    RigConfig,
    OperaRigBuilder,
    OperaMaterialLibrary,
    OperaAnimationLibrary,
)


def demo_dang_types():
    """演示不同的京剧行当"""
    print("=" * 60)
    print("演示京剧行当")
    print("=" * 60)

    for dang_type in DangType:
        config = RigConfig(dang=dang_type)
        builder = OperaRigBuilder(config)
        bones = builder.build_base_rig()
        
        print(f"\n行当: {dang_type.value}")
        print(f"  基础骨骼数: {len(bones)}")


def demo_build_rig():
    """演示构建绑定"""
    print("\n" + "=" * 60)
    print("演示构建绑定")
    print("=" * 60)

    # 创建生角绑定
    config = RigConfig(
        dang=DangType.SHENG,
        height=1.75,
        gender="male",
        scale=1.0,
    )
    
    builder = OperaRigBuilder(config)
    
    # 构建基础骨架
    bones = builder.build_base_rig()
    print(f"\n基础骨骼数: {len(bones)}")
    
    # 添加京剧特有骨骼
    bones = builder.add_opera_bones()
    print(f"添加特有骨骼后: {len(bones)}")
    
    # 显示部分骨骼
    print("\n部分骨骼:")
    for name in list(bones.keys())[:10]:
        bone = bones[name]
        print(f"  - {name}: parent={bone.parent}")


def demo_export_json():
    """演示导出JSON"""
    print("\n" + "=" * 60)
    print("演示导出JSON")
    print("=" * 60)

    # 创建绑定
    config = RigConfig(dang=DangType.DAN)
    builder = OperaRigBuilder(config)
    builder.build_base_rig()
    builder.add_opera_bones()

    # 导出到临时文件
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        temp_path = f.name

    result = builder.export_to_json(temp_path)
    
    print(f"\n导出路径: {result['path']}")
    print(f"骨骼数量: {result['bone_count']}")
    
    # 读取并显示部分内容
    import json
    with open(temp_path, 'r') as f:
        data = json.load(f)
    
    print(f"\n配置信息:")
    print(f"  - 行当: {data['config']['dang']}")
    print(f"  - 身高: {data['config']['height']}m")
    print(f"  - 性别: {data['config']['gender']}")
    
    # 清理
    Path(temp_path).unlink(missing_ok=True)
    print("\n(临时文件已清理)")


def demo_export_blender():
    """演示导出Blender脚本"""
    print("\n" + "=" * 60)
    print("演示导出Blender脚本")
    print("=" * 60)

    # 创建绑定
    config = RigConfig(dang=DangType.JING)
    builder = OperaRigBuilder(config)
    builder.build_base_rig()
    builder.add_opera_bones()

    # 导出到临时文件
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        temp_path = f.name

    result = builder.export_to_blender(temp_path)
    
    print(f"\n导出路径: {result['path']}")
    print(f"骨骼数量: {result['bone_count']}")
    
    # 读取并显示部分内容
    with open(temp_path, 'r') as f:
        script = f.read()
    
    print(f"\n脚本长度: {len(script)} 字符")
    print("\n脚本预览 (前500字符):")
    print("-" * 40)
    print(script[:500])
    print("-" * 40)
    
    # 清理
    Path(temp_path).unlink(missing_ok=True)
    print("\n(临时文件已清理)")


def demo_materials():
    """演示材质库"""
    print("\n" + "=" * 60)
    print("演示材质库")
    print("=" * 60)

    # 显示脸谱材质
    print("\n脸谱材质:")
    face_materials = ["face_red", "face_white", "face_black", "face_green"]
    for name in face_materials:
        mat = OperaMaterialLibrary.get_material(name)
        if mat:
            print(f"  - {name}: {mat.get('base_color')}")

    # 显示戏服材质
    print("\n戏服材质:")
    costume_materials = ["costume_red", "costume_gold", "costume_blue"]
    for name in costume_materials:
        mat = OperaMaterialLibrary.get_material(name)
        if mat:
            print(f"  - {name}: {mat.get('base_color')}")


def demo_animations():
    """演示动画库"""
    print("\n" + "=" * 60)
    print("演示动画库")
    print("=" * 60)

    # 获取动画列表
    animations = [
        "sleeve_wave",
        "sleeve_dust", 
        "sleeve_spin",
        "hand_gesture",
        "fan_turn",
        "fan_wave",
    ]

    print("\n预设动画:")
    for name in animations:
        anim = OperaAnimationLibrary.get_animation(name)
        status = "可用" if anim else "不可用"
        print(f"  - {name}: {status}")

    # 按类别获取
    print("\n水袖动作:")
    sleeve_animations = OperaAnimationLibrary.list_by_dang("sleeve")
    print(f"  共 {len(sleeve_animations)} 个")


def demo_custom_rig():
    """演示自定义绑定配置"""
    print("\n" + "=" * 60)
    print("演示自定义绑定配置")
    print("=" * 60)

    # 自定义配置
    config = RigConfig(
        dang=DangType.CHOU,
        scale=1.2,
        height=1.65,
        gender="female",
        age_group="adult",
        prefix_l="Left_",
        prefix_r="Right_",
        detail_level="high",
    )

    builder = OperaRigBuilder(config)
    bones = builder.build_base_rig()
    bones = builder.add_opera_bones()

    print(f"\n自定义绑定:")
    print(f"  - 行当: {config.dang.value}")
    print(f"  - 缩放: {config.scale}")
    print(f"  - 身高: {config.height}m")
    print(f"  - 性别: {config.gender}")
    print(f"  - 年龄: {config.age_group}")
    print(f"  - 详细程度: {config.detail_level}")
    print(f"  - 骨骼数量: {len(bones)}")


def main():
    """主函数"""
    print("\n" + "#" * 60)
    print("# Blender绑定演示")
    print("#" * 60 + "\n")

    # 运行所有演示
    demo_dang_types()
    demo_build_rig()
    demo_export_json()
    demo_export_blender()
    demo_materials()
    demo_animations()
    demo_custom_rig()

    print("\n" + "=" * 60)
    print("演示完成！")
    print("=" * 60)
    print("""
使用说明:
1. 运行此脚本生成Blender绑定脚本
2. 在Blender中打开文本编辑器
3. 加载生成的Python脚本
4. 运行脚本创建绑定

更多信息请查看:
  docs/commercial/blender_rig_guide.md
""")


if __name__ == "__main__":
    main()
