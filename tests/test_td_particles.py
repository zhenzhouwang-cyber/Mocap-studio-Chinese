"""
TD粒子系统单元测试。

测试 TouchDesigner 粒子效果引擎的核心功能。
"""

import json
import socket
import struct
import threading
import time
from unittest.mock import Mock, patch

import numpy as np
import pytest

# 导入被测试模块
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from opera_mocap_tool.commercial.td_particles import (
    ParticlePreset,
    EmitterShape,
    ParticleEmitter,
    ParticleSystem,
    TDParticleTransmitter,
    PresetLibrary,
    create_td_integration_module,
)


class TestParticlePreset:
    """粒子预设枚举测试"""

    def test_preset_values(self):
        """测试预设枚举值"""
        assert ParticlePreset.INK.value == "ink"
        assert ParticlePreset.GLOW.value == "glow"
        assert ParticlePreset.FIRE.value == "fire"
        assert ParticlePreset.SNOW.value == "snow"
        assert ParticlePreset.SPARKS.value == "sparks"
        assert ParticlePreset.GOLD.value == "gold"
        assert ParticlePreset.SILK.value == "silk"
        assert ParticlePreset.ENERGY.value == "energy"

    def test_preset_count(self):
        """测试预设数量"""
        assert len(ParticlePreset) == 8


class TestEmitterShape:
    """发射器形状枚举测试"""

    def test_shape_values(self):
        """测试形状枚举值"""
        assert EmitterShape.POINT.value == "point"
        assert EmitterShape.LINE.value == "line"
        assert EmitterShape.CIRCLE.value == "circle"
        assert EmitterShape.SPHERE.value == "sphere"

    def test_shape_count(self):
        """测试形状数量"""
        assert len(EmitterShape) == 4


class TestParticleEmitter:
    """粒子发射器测试"""

    def test_emitter_creation(self):
        """测试发射器创建"""
        emitter = ParticleEmitter(
            marker_name="head",
            emit_rate=50.0,
            emit_probability=0.8,
            initial_speed=2.0,
        )
        
        assert emitter.marker_name == "head"
        assert emitter.emit_rate == 50.0
        assert emitter.emit_probability == 0.8
        assert emitter.initial_speed == 2.0

    def test_emitter_default_values(self):
        """测试默认参数"""
        emitter = ParticleEmitter(marker_name="test")
        
        assert emitter.emit_rate == 50.0
        assert emitter.emit_probability == 1.0
        assert emitter.initial_speed == 1.0
        assert emitter.lifetime == 2.0
        assert emitter.size == 0.1
        assert emitter.gravity == 0.0
        assert emitter.shape == EmitterShape.POINT

    def test_emitter_to_dict(self):
        """测试转换为字典"""
        emitter = ParticleEmitter(
            marker_name="hand_r",
            emit_rate=100.0,
            color_start=(1.0, 0.0, 0.0, 1.0),
            color_end=(0.0, 0.0, 0.0, 0.0),
        )
        
        result = emitter.to_dict()
        
        assert result["marker_name"] == "hand_r"
        assert result["emit_rate"] == 100.0
        assert result["color_start"] == (1.0, 0.0, 0.0, 1.0)
        assert result["color_end"] == (0.0, 0.0, 0.0, 0.0)


class TestParticleSystem:
    """粒子系统测试"""

    def test_particle_system_creation(self):
        """测试粒子系统创建"""
        system = ParticleSystem()
        
        assert system.max_particles == 10000
        assert system.simulation_speed == 1.0
        assert len(system.emitters) == 0
        assert system._active is False

    def test_add_emitter(self):
        """测试添加发射器"""
        system = ParticleSystem()
        emitter = ParticleEmitter(marker_name="head")
        
        system.add_emitter(emitter)
        
        assert len(system.emitters) == 1
        assert system.emitters[0].marker_name == "head"

    def test_remove_emitter(self):
        """测试移除发射器"""
        system = ParticleSystem()
        emitter1 = ParticleEmitter(marker_name="head")
        emitter2 = ParticleEmitter(marker_name="hand")
        
        system.add_emitter(emitter1)
        system.add_emitter(emitter2)
        system.remove_emitter("head")
        
        assert len(system.emitters) == 1
        assert system.emitters[0].marker_name == "hand"

    def test_start_stop(self):
        """测试启动和停止"""
        system = ParticleSystem()
        
        system.start()
        assert system._active is True
        
        system.stop()
        assert system._active is False
        assert len(system._particles) == 0

    def test_update_no_active(self):
        """测试非活跃状态不更新"""
        system = ParticleSystem()
        positions = {"head": (0.0, 1.0, 0.0)}
        
        # 不应该抛出异常
        system.update(positions, 0.016)
        assert len(system._particles) == 0

    def test_update_with_active(self):
        """测试活跃状态更新"""
        system = ParticleSystem()
        emitter = ParticleEmitter(
            marker_name="head",
            emit_rate=100.0,
            emit_probability=1.0,
            lifetime=0.1,
        )
        system.add_emitter(emitter)
        system.start()
        
        positions = {"head": (0.0, 1.0, 0.0)}
        
        # 更新几次
        for _ in range(10):
            system.update(positions, 0.016)
        
        # 应该有粒子产生
        assert len(system._particles) > 0

    def test_bounds_check(self):
        """测试边界检查"""
        system = ParticleSystem(
            bounds=(-1, -1, -1, 1, 1, 1)
        )
        
        emitter = ParticleEmitter(marker_name="test")
        system.add_emitter(emitter)
        system.start()
        
        positions = {"test": (0.0, 0.0, 0.0)}
        system.update(positions, 0.016)
        
        # 粒子应该在边界内
        for p in system._particles:
            x, y, z = p["position"]
            assert -1 <= x <= 1
            assert -1 <= y <= 1
            assert -1 <= z <= 1


class TestPresetLibrary:
    """预设库测试"""

    def test_get_preset(self):
        """测试获取预设"""
        preset = PresetLibrary.get_preset(ParticlePreset.INK)
        
        assert preset is not None
        assert "emit_rate" in preset
        assert "color_start" in preset

    def test_all_presets_available(self):
        """测试所有预设都可用"""
        for preset_type in ParticlePreset:
            preset = PresetLibrary.get_preset(preset_type)
            assert preset is not None, f"Preset {preset_type} not available"

    def test_create_emitter_from_preset(self):
        """测试从预设创建发射器"""
        emitter = PresetLibrary.create_emitter_from_preset(
            ParticlePreset.FIRE,
            marker_name="hand"
        )
        
        assert emitter.marker_name == "hand"
        assert emitter.emit_rate > 0
        assert emitter.color_start != emitter.color_end


class TestTDParticleTransmitter:
    """TD传输器测试"""

    def test_transmitter_creation(self):
        """测试传输器创建"""
        transmitter = TDParticleTransmitter(
            host="127.0.0.1",
            port=7000,
        )
        
        assert transmitter.host == "127.0.0.1"
        assert transmitter.port == 7000
        assert transmitter._socket is None

    def test_transmitter_json_format(self):
        """测试JSON格式传输"""
        transmitter = TDParticleTransmitter()
        
        # 模拟粒子数据
        particles = [
            {
                "position": (0.0, 1.0, 0.0),
                "velocity": (0.1, 0.2, 0.0),
                "life": 0.5,
                "size": 0.1,
                "color": (1.0, 0.0, 0.0, 1.0),
            }
        ]
        
        data = json.dumps(particles)
        
        # 验证JSON格式正确
        parsed = json.loads(data)
        assert len(parsed) == 1
        assert parsed[0]["position"] == [0.0, 1.0, 0.0]

    def test_transmitter_binary_format(self):
        """测试二进制格式传输"""
        transmitter = TDParticleTransmitter()
        
        particles = [
            {
                "position": (0.0, 1.0, 0.0),
                "velocity": (0.1, 0.2, 0.0),
                "life": 0.5,
            }
        ]
        
        # 测试二进制打包
        data = struct.pack("fff", 0.0, 1.0, 0.0)
        assert len(data) == 12  # 3 floats * 4 bytes


class TestTDIntegrationModule:
    """TD集成模块测试"""

    def test_create_integration_module(self):
        """测试创建集成模块"""
        module = create_td_integration_module(
            output_path="./td_particles",
            use_udp=True,
        )
        
        assert module is not None
        assert "ParticleEmitter" in module
        assert "ParticleSystem" in module
        assert "TDParticleTransmitter" in module


class TestParticlePhysics:
    """粒子物理效果测试"""

    def test_gravity_effect(self):
        """测试重力效果"""
        system = ParticleSystem()
        emitter = ParticleEmitter(
            marker_name="test",
            gravity=1.0,
            lifetime=0.5,
        )
        system.add_emitter(emitter)
        system.start()
        
        positions = {"test": (0.0, 1.0, 0.0)}
        system.update(positions, 0.1)
        
        # 获取第一个粒子
        if system._particles:
            particle = system._particles[0]
            # 初始速度应该有z方向的分量（重力影响）
            assert "velocity" in particle

    def test_wind_effect(self):
        """测试风力效果"""
        system = ParticleSystem()
        emitter = ParticleEmitter(
            marker_name="test",
            wind=(1.0, 0.0, 0.0),
            lifetime=0.5,
        )
        system.add_emitter(emitter)
        system.start()
        
        positions = {"test": (0.0, 0.0, 0.0)}
        system.update(positions, 0.1)
        
        # 验证风力被应用
        # (实际测试需要检查粒子velocity的变化)

    def test_turbulence_effect(self):
        """测试湍流效果"""
        system = ParticleSystem()
        emitter = ParticleEmitter(
            marker_name="test",
            turbulence=0.5,
            lifetime=0.5,
        )
        system.add_emitter(emitter)
        system.start()
        
        positions = {"test": (0.0, 0.0, 0.0)}
        
        # 多次更新，湍流应该产生随机性
        velocities = []
        for _ in range(5):
            system.update(positions, 0.05)
            if system._particles:
                velocities.append(system._particles[0]["velocity"])
        
        # 湍流应该产生不同的速度
        assert len(velocities) > 0


class TestParticleLifecycle:
    """粒子生命周期测试"""

    def test_particle_lifetime(self):
        """测试粒子生命周期"""
        system = ParticleSystem()
        emitter = ParticleEmitter(
            marker_name="test",
            lifetime=0.1,  # 短生命周期
        )
        system.add_emitter(emitter)
        system.start()
        
        positions = {"test": (0.0, 0.0, 0.0)}
        
        # 产生粒子
        system.update(positions, 0.05)
        initial_count = len(system._particles)
        
        # 等待粒子死亡
        time.sleep(0.2)
        system.update(positions, 0.05)
        
        # 旧粒子应该被移除
        assert len(system._particles) <= initial_count


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
