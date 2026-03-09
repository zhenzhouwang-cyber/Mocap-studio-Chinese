#!/usr/bin/env python
"""
TD粒子效果示例。

展示如何使用商业模块创建基于动捕数据的TouchDesigner粒子效果。

运行方式:
    python examples/td_particles_demo.py
"""

import sys
import time
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
from opera_mocap_tool.commercial.td_particles import (
    ParticlePreset,
    ParticleEmitter,
    ParticleSystem,
    PresetLibrary,
    TDParticleTransmitter,
    EmitterShape,
)


def demo_particle_presets():
    """演示不同的粒子预设效果"""
    print("=" * 60)
    print("演示粒子预设效果")
    print("=" * 60)

    # 测试所有预设
    presets = [
        ParticlePreset.INK,
        ParticlePreset.GLOW,
        ParticlePreset.FIRE,
        ParticlePreset.SNOW,
        ParticlePreset.SPARKS,
        ParticlePreset.GOLD,
        ParticlePreset.SILK,
        ParticlePreset.ENERGY,
    ]

    for preset in presets:
        emitter = PresetLibrary.create_emitter(
            preset,
            marker_name="hand",
        )
        print(f"\n预设: {preset.value}")
        print(f"  - 发射速率: {emitter.emit_rate}")
        print(f"  - 生命周期: {emitter.lifetime}s")
        print(f"  - 起始颜色: {emitter.color_start}")
        print(f"  - 结束颜色: {emitter.color_end}")


def demo_particle_system():
    """演示粒子系统"""
    print("\n" + "=" * 60)
    print("演示粒子系统")
    print("=" * 60)

    # 创建粒子系统
    system = ParticleSystem(max_particles=5000)

    # 添加多个发射器
    markers = ["head", "hand_l", "hand_r", "spine_upper"]
    for i, marker in enumerate(markers):
        emitter = PresetLibrary.create_emitter(
            ParticlePreset.SILK,
            marker_name=marker,
        )
        emitter.emit_rate = 20 + i * 10
        system.add_emitter(emitter)

    print(f"\n添加了 {len(system.emitters)} 个发射器")

    # 模拟位置数据
    positions = {
        "head": (0.0, 1.6, 0.0),
        "hand_l": (-0.3, 1.2, 0.1),
        "hand_r": (0.3, 1.2, 0.1),
        "spine_upper": (0.0, 1.3, 0.0),
    }

    # 启动系统并更新几帧
    system.start()
    print("粒子系统已启动")

    # 模拟30帧
    for frame in range(30):
        system.update(positions, 0.016)
        if frame % 10 == 0:
            print(f"  帧 {frame}: {len(system._particles)} 粒子")

    print(f"\n最终粒子数: {len(system._particles)}")
    system.stop()
    print("粒子系统已停止")


def demo_udp_transmission():
    """演示UDP传输（仅演示，不实际发送）"""
    print("\n" + "=" * 60)
    print("演示UDP传输")
    print("=" * 60)

    # 创建传输器
    transmitter = TDParticleTransmitter(
        host="127.0.0.1",
        port=7000,
    )

    print(f"\n传输器配置:")
    print(f"  - 主机: {transmitter.host}")
    print(f"  - 端口: {transmitter.port}")

    # 模拟粒子数据
    particles = [
        {
            "position": (0.0, 1.5, 0.0),
            "velocity": (0.1, 0.2, 0.0),
            "life": 0.8,
            "size": 0.1,
            "color": (1.0, 0.5, 0.0, 1.0),
        }
    ]

    # 序列化为JSON
    import json
    data = json.dumps(particles)
    print(f"\n模拟传输数据 ({len(data)} bytes):")
    print(f"  {data[:100]}...")


def demo_custom_emitter():
    """演示自定义发射器"""
    print("\n" + "=" * 60)
    print("演示自定义发射器")
    print("=" * 60)

    # 创建自定义发射器
    emitter = ParticleEmitter(
        marker_name="test",
        emit_rate=100.0,
        emit_probability=0.8,
        initial_speed=2.0,
        speed_variance=0.5,
        lifetime=1.5,
        lifetime_variance=0.3,
        size=0.15,
        size_variance=0.05,
        size_over_life=(1.0, 0.0),
        color_start=(1.0, 0.0, 0.0, 1.0),
        color_end=(1.0, 0.0, 0.0, 0.0),
        gravity=0.2,
        wind=(0.0, 0.0, 0.1),
        turbulence=0.3,
        shape=EmitterShape.SPHERE,
        spread_angle=45.0,
    )

    print("\n自定义发射器配置:")
    for key, value in emitter.to_dict().items():
        print(f"  - {key}: {value}")


def demo_physics():
    """演示物理效果"""
    print("\n" + "=" * 60)
    print("演示物理效果")
    print("=" * 60)

    # 测试不同物理参数
    test_cases = [
        {"name": "无重力", "gravity": 0.0},
        {"name": "轻度重力", "gravity": 0.5},
        {"name": "重度重力", "gravity": 1.0},
    ]

    for test in test_cases:
        system = ParticleSystem()
        emitter = ParticleEmitter(
            marker_name="test",
            gravity=test["gravity"],
            lifetime=1.0,
        )
        system.add_emitter(emitter)
        system.start()

        positions = {"test": (0.0, 1.0, 0.0)}
        system.update(positions, 0.1)

        particle_count = len(system._particles)
        print(f"  {test['name']}: {particle_count} 粒子")


def main():
    """主函数"""
    print("\n" + "#" * 60)
    print("# TD粒子系统演示")
    print("#" * 60 + "\n")

    # 运行所有演示
    demo_particle_presets()
    demo_particle_system()
    demo_udp_transmission()
    demo_custom_emitter()
    demo_physics()

    print("\n" + "=" * 60)
    print("演示完成！")
    print("=" * 60)
    print("""
使用说明:
1. 创建ParticleEmitter并配置参数
2. 创建ParticleSystem并添加发射器
3. 启动系统，在渲染循环中调用update()
4. 使用TDParticleTransmitter发送到TouchDesigner

更多信息请查看:
  docs/commercial/td_particles_guide.md
""")


if __name__ == "__main__":
    main()
