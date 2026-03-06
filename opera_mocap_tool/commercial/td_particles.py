"""
TouchDesigner 实时粒子系统模块。

闭源商业模块 - 动作驱动的粒子效果引擎
用于舞台艺术创作的实时视觉效果

功能特性：
- 基于身体关键点的粒子发射
- 多种粒子物理效果
- TD实时数据传输 (UDP/WebSocket)
- 预设效果库 (水墨/发光/拖尾/火焰/雪花)
"""

from __future__ import annotations

import json
import struct
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

import numpy as np


class ParticlePreset(Enum):
    """粒子效果预设"""
    INK = "ink"              # 水墨效果
    GLOW = "glow"            # 发光拖尾
    FIRE = "fire"            # 火焰效果
    SNOW = "snow"            # 雪花效果
    SPARKS = "sparks"        # 火花效果
    GOLD = "gold"            # 金粉效果
    SILK = "silk"            # 丝绸效果
    ENERGY = "energy"        # 能量效果


class EmitterShape(Enum):
    """发射器形状"""
    POINT = "point"
    LINE = "line"
    CIRCLE = "circle"
    SPHERE = "sphere"


@dataclass
class ParticleEmitter:
    """粒子发射器配置"""
    marker_name: str                    # 关联的marker名称
    emit_rate: float = 50.0             # 每秒发射粒子数
    emit_probability: float = 1.0       # 发射概率
    initial_speed: float = 1.0          # 初始速度
    speed_variance: float = 0.3         # 速度随机性
    lifetime: float = 2.0               # 粒子生命周期(秒)
    lifetime_variance: float = 0.5      # 生命周期随机性
    size: float = 0.1                   # 粒子大小
    size_variance: float = 0.05         # 大小随机性
    size_over_life: tuple = (1.0, 0.0)  # 大小随生命周期变化 (起始, 结束)
    color_start: tuple = (1.0, 1.0, 1.0, 1.0)  # RGBA 起始颜色
    color_end: tuple = (1.0, 1.0, 1.0, 0.0)    # RGBA 结束颜色
    gravity: float = 0.0                # 重力影响
    wind: tuple = (0.0, 0.0, 0.0)       # 风向
    turbulence: float = 0.0             # 湍流强度
    
    # 形状参数
    shape: EmitterShape = EmitterShape.POINT
    spread_angle: float = 180.0        # 发射角度范围(度)
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "marker_name": self.marker_name,
            "emit_rate": self.emit_rate,
            "emit_probability": self.emit_probability,
            "initial_speed": self.initial_speed,
            "speed_variance": self.speed_variance,
            "lifetime": self.lifetime,
            "lifetime_variance": self.lifetime_variance,
            "size": self.size,
            "size_variance": self.size_variance,
            "size_over_life": self.size_over_life,
            "color_start": self.color_start,
            "color_end": self.color_end,
            "gravity": self.gravity,
            "wind": self.wind,
            "turbulence": self.turbulence,
            "shape": self.shape.value,
            "spread_angle": self.spread_angle,
        }


@dataclass
class ParticleSystem:
    """粒子系统"""
    emitters: list[ParticleEmitter] = field(default_factory=list)
    max_particles: int = 10000           # 最大粒子数
    simulation_speed: float = 1.0       # 模拟速度
    bounds: tuple = (-10, -10, -10, 10, 10, 10)  # 边界框
    
    # 内部状态
    _particles: list = field(default_factory=list, init=False)
    _active: bool = False
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False)
    
    def __post_init__(self):
        """初始化"""
        self._particles = []
    
    def add_emitter(self, emitter: ParticleEmitter):
        """添加发射器"""
        self.emitters.append(emitter)
    
    def remove_emitter(self, marker_name: str):
        """移除发射器"""
        self.emitters = [e for e in self.emitters if e.marker_name != marker_name]
    
    def start(self):
        """启动粒子系统"""
        self._active = True
    
    def stop(self):
        """停止粒子系统"""
        self._active = False
        self._particles.clear()
    
    def update(
        self, 
        positions: dict[str, tuple[float, float, float]], 
        delta_time: float
    ):
        """
        更新粒子系统
        
        Args:
            positions: marker名称到位置的映射
            delta_time: 时间步长(秒)
        """
        if not self._active:
            return
        
        dt = delta_time * self.simulation_speed
        
        with self._lock:
            # 发射新粒子
            for emitter in self.emitters:
                if emitter.marker_name not in positions:
                    continue
                
                # 检查发射概率
                if np.random.random() > emitter.emit_probability:
                    continue
                
                pos = positions[emitter.marker_name]
                
                # 计算发射数量
                emit_count = int(emitter.emit_rate * dt)
                emit_count = min(emit_count, 10)  # 每帧最多发射数量限制
                
                for _ in range(emit_count):
                    if len(self._particles) >= self.max_particles:
                        break
                    
                    # 生成粒子
                    particle = self._create_particle(emitter, pos)
                    self._particles.append(particle)
            
            # 更新现有粒子
            new_particles = []
            for p in self._particles:
                # 更新位置
                p["position"] = (
                    p["position"][0] + p["velocity"][0] * dt,
                    p["position"][1] + p["velocity"][1] * dt,
                    p["position"][2] + p["velocity"][2] * dt,
                )
                
                # 应用重力
                p["velocity"] = (
                    p["velocity"][0] + emitter.gravity * dt if emitter else p["velocity"][0],
                    p["velocity"][1] + emitter.gravity * dt if emitter else p["velocity"][1],
                    p["velocity"][2] - 9.8 * emitter.gravity * dt if emitter else p["velocity"][2],
                )
                
                # 应用风力
                if emitter:
                    p["velocity"] = (
                        p["velocity"][0] + emitter.wind[0] * dt,
                        p["velocity"][1] + emitter.wind[1] * dt,
                        p["velocity"][2] + emitter.wind[2] * dt,
                    )
                
                # 湍流
                if emitter and emitter.turbulence > 0:
                    noise = np.random.randn(3) * emitter.turbulence
                    p["velocity"] = (
                        p["velocity"][0] + noise[0],
                        p["velocity"][1] + noise[1],
                        p["velocity"][2] + noise[2],
                    )
                
                # 更新生命周期
                p["age"] += dt
                p["life_ratio"] = p["age"] / p["lifetime"]
                
                # 更新大小
                start_size, end_size = emitter.size_over_life if emitter else (1.0, 0.0)
                p["size"] = p["base_size"] * (start_size + (end_size - start_size) * p["life_ratio"])
                
                # 检查是否存活
                if p["age"] < p["lifetime"]:
                    new_particles.append(p)
            
            self._particles = new_particles
    
    def _create_particle(self, emitter: ParticleEmitter, position: tuple) -> dict:
        """创建单个粒子"""
        # 随机速度方向
        speed = emitter.initial_speed * (1 + np.random.uniform(-emitter.speed_variance, emitter.speed_variance))
        
        # 根据发射角度生成方向
        if emitter.spread_angle < 180:
            # 限制在锥形范围内
            theta = np.random.uniform(0, 2 * np.pi)
            phi = np.random.uniform(0, emitter.spread_angle * np.pi / 180)
            
            vx = speed * np.sin(phi) * np.cos(theta)
            vy = speed * np.sin(phi) * np.sin(theta)
            vz = speed * np.cos(phi)
        else:
            # 全方向
            vx = speed * (np.random.random() - 0.5) * 2
            vy = speed * (np.random.random() - 0.5) * 2
            vz = speed * (np.random.random() - 0.5) * 2
        
        # 随机生命周期
        lifetime = emitter.lifetime * (1 + np.random.uniform(-emitter.lifetime_variance, emitter.lifetime_variance))
        
        # 随机大小
        size = emitter.size * (1 + np.random.uniform(-emitter.size_variance, emitter.size_variance))
        
        return {
            "position": position,
            "velocity": (vx, vy, vz),
            "age": 0.0,
            "lifetime": lifetime,
            "life_ratio": 0.0,
            "base_size": size,
            "size": size,
            "color_start": emitter.color_start,
            "color_end": emitter.color_end,
            "emitter": emitter,
        }
    
    def get_particle_data(self) -> dict[str, Any]:
        """获取粒子数据用于渲染"""
        with self._lock:
            positions = []
            colors = []
            sizes = []
            
            for p in self._particles:
                positions.extend(p["position"])
                
                # 颜色插值
                ratio = p["life_ratio"]
                color = [
                    p["color_start"][i] + (p["color_end"][i] - p["color_start"][i]) * ratio
                    for i in range(4)
                ]
                colors.extend(color)
                
                sizes.append(p["size"])
            
            return {
                "count": len(self._particles),
                "positions": positions,
                "colors": colors,
                "sizes": sizes,
            }


class TDParticleTransmitter:
    """
    TouchDesigner 粒子数据传输器
    
    支持多种传输协议:
    - UDP: 适用于本地TD实例
    - WebSocket: 适用于远程/多客户端
    - JSON: 简单数据格式
    - Binary: 高效二进制格式
    """
    
    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 7000,
        protocol: str = "udp",
    ):
        self.host = host
        self.port = port
        self.protocol = protocol
        self._socket = None
        self._connected = False
        self._thread = None
        self._running = False
        
        # 数据压缩选项
        self.use_compression = False
        self.precision = 3  # 小数位数
        
        # 回调函数
        self.on_connected: Callable | None = None
        self.on_disconnected: Callable | None = None
        self.on_error: Callable[[str], None] | None = None
    
    def connect(self) -> bool:
        """建立连接"""
        try:
            if self.protocol == "udp":
                import socket
                self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                self._connected = True
                
            elif self.protocol == "tcp":
                import socket
                self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self._socket.connect((self.host, self.port))
                self._connected = True
            
            elif self.protocol == "websocket":
                # 需要websockets库
                import asyncio
                self._async_loop = asyncio.new_event_loop()
                self._connected = True
            
            if self.on_connected:
                self.on_connected()
            
            return True
            
        except Exception as e:
            if self.on_error:
                self.on_error(str(e))
            return False
    
    def disconnect(self):
        """断开连接"""
        self._running = False
        
        if self._socket:
            try:
                self._socket.close()
            except:
                pass
        
        self._connected = False
        
        if self.on_disconnected:
            self.on_disconnected()
    
    def send_particles(self, particle_data: dict[str, Any]) -> bool:
        """发送粒子数据"""
        if not self._connected:
            return False
        
        try:
            if self.protocol in ("udp", "tcp"):
                # 二进制格式
                data = self._encode_binary(particle_data)
            else:
                # JSON格式
                data = self._encode_json(particle_data)
            
            self._socket.sendto(data, (self.host, self.port))
            return True
            
        except Exception as e:
            if self.on_error:
                self.on_error(str(e))
            return False
    
    def _encode_binary(self, particle_data: dict) -> bytes:
        """二进制编码"""
        count = particle_data["count"]
        positions = particle_data["positions"]
        colors = particle_data["colors"]
        sizes = particle_data["sizes"]
        
        # 格式: count(int) + positions(float[]) + colors(float[]) + sizes(float[])
        data = struct.pack("i", count)
        
        # 位置数据
        for i in range(0, len(positions), 3):
            data += struct.pack(
                "fff",
                round(positions[i], self.precision),
                round(positions[i+1], self.precision),
                round(positions[i+2], self.precision)
            )
        
        # 颜色数据
        for i in range(0, len(colors), 4):
            data += struct.pack(
                "ffff",
                round(colors[i], self.precision),
                round(colors[i+1], self.precision),
                round(colors[i+2], self.precision),
                round(colors[i+3], self.precision)
            )
        
        # 大小数据
        for s in sizes:
            data += struct.pack("f", round(s, self.precision))
        
        return data
    
    def _encode_json(self, particle_data: dict) -> str:
        """JSON编码"""
        # 精简数据
        simplified = {
            "c": particle_data["count"],
            "p": [round(v, self.precision) for v in particle_data["positions"]],
            "co": [round(v, self.precision) for v in particle_data["colors"]],
            "s": [round(v, self.precision) for v in particle_data["sizes"]],
        }
        
        return json.dumps(simplified)
    
    def start_realtime_stream(
        self,
        particle_system: ParticleSystem,
        positions_callback: Callable[[], dict],
        fps: float = 60.0,
    ):
        """
        启动实时流
        
        Args:
            particle_system: 粒子系统
            positions_callback: 获取当前位置的回调
            fps: 目标帧率
        """
        self._running = True
        interval = 1.0 / fps
        
        def stream_loop():
            last_time = time.time()
            
            while self._running:
                current_time = time.time()
                delta_time = current_time - last_time
                last_time = current_time
                
                # 获取最新的marker位置
                positions = positions_callback()
                
                # 更新粒子系统
                particle_system.update(positions, delta_time)
                
                # 获取粒子数据并发送
                particle_data = particle_system.get_particle_data()
                self.send_particles(particle_data)
                
                # 等待下一帧
                elapsed = time.time() - current_time
                if elapsed < interval:
                    time.sleep(interval - elapsed)
        
        self._thread = threading.Thread(target=stream_loop, daemon=True)
        self._thread.start()


class PresetLibrary:
    """预设效果库"""
    
    @staticmethod
    def create_emitter(preset: ParticlePreset, marker_name: str) -> ParticleEmitter:
        """创建预设发射器"""
        presets = {
            ParticlePreset.INK: ParticleEmitter(
                marker_name=marker_name,
                emit_rate=30.0,
                lifetime=3.0,
                size=0.15,
                color_start=(0.1, 0.1, 0.15, 0.9),
                color_end=(0.05, 0.05, 0.1, 0.0),
                gravity=0.1,
                spread_angle=45,
            ),
            ParticlePreset.GLOW: ParticleEmitter(
                marker_name=marker_name,
                emit_rate=60.0,
                lifetime=1.5,
                size=0.08,
                color_start=(1.0, 0.9, 0.5, 1.0),
                color_end=(1.0, 0.5, 0.2, 0.0),
                gravity=0.0,
                turbulence=0.5,
                spread_angle=30,
            ),
            ParticlePreset.FIRE: ParticleEmitter(
                marker_name=marker_name,
                emit_rate=80.0,
                lifetime=1.0,
                size=0.12,
                color_start=(1.0, 0.8, 0.2, 1.0),
                color_end=(0.5, 0.1, 0.0, 0.0),
                gravity=-0.5,  # 向上
                turbulence=1.0,
                spread_angle=60,
            ),
            ParticlePreset.SNOW: ParticleEmitter(
                marker_name=marker_name,
                emit_rate=40.0,
                lifetime=4.0,
                size=0.05,
                color_start=(1.0, 1.0, 1.0, 0.9),
                color_end=(0.9, 0.9, 1.0, 0.0),
                gravity=0.3,
                wind=(0.2, 0.0, 0.1),
                turbulence=0.3,
                spread_angle=90,
            ),
            ParticlePreset.SPARKS: ParticleEmitter(
                marker_name=marker_name,
                emit_rate=100.0,
                lifetime=0.8,
                size=0.03,
                color_start=(1.0, 1.0, 0.8, 1.0),
                color_end=(1.0, 0.6, 0.2, 0.0),
                gravity=-0.2,
                turbulence=2.0,
                spread_angle=180,
            ),
            ParticlePreset.GOLD: ParticleEmitter(
                marker_name=marker_name,
                emit_rate=25.0,
                lifetime=2.5,
                size=0.1,
                color_start=(1.0, 0.85, 0.3, 1.0),
                color_end=(0.8, 0.6, 0.1, 0.0),
                gravity=0.05,
                turbulence=0.2,
                spread_angle=40,
            ),
            ParticlePreset.SILK: ParticleEmitter(
                marker_name=marker_name,
                emit_rate=15.0,
                lifetime=5.0,
                size=0.2,
                color_start=(0.8, 0.4, 0.5, 0.6),
                color_end=(0.6, 0.2, 0.3, 0.0),
                gravity=-0.02,
                turbulence=0.1,
                spread_angle=20,
            ),
            ParticlePreset.ENERGY: ParticleEmitter(
                marker_name=marker_name,
                emit_rate=120.0,
                lifetime=0.5,
                size=0.04,
                color_start=(0.3, 0.8, 1.0, 1.0),
                color_end=(0.5, 0.2, 1.0, 0.0),
                gravity=0.0,
                turbulence=3.0,
                spread_angle=180,
            ),
        }
        
        return presets.get(preset, presets[ParticlePreset.GLOW])
    
    @staticmethod
    def create_full_body_system(preset: ParticlePreset) -> ParticleSystem:
        """创建全身粒子系统"""
        system = ParticleSystem()
        
        # 常用markers
        markers = [
            "head", "wrist_left", "wrist_right",
            "elbow_left", "elbow_right",
            "ankle_left", "ankle_right",
        ]
        
        for marker in markers:
            emitter = PresetLibrary.create_emitter(preset, marker)
            # 根据位置调整参数
            if "ankle" in marker:
                emitter.gravity = abs(emitter.gravity) * 1.5 if emitter.gravity > 0 else 0
            if "head" in marker:
                emitter.gravity = -abs(emitter.gravity) * 0.5
            
            system.add_emitter(emitter)
        
        return system


def create_td_integration_module() -> dict[str, Any]:
    """
    创建TD集成模块配置
    
    返回可用于TD的Python模块代码
    """
    return {
        "name": "OperaParticleTD",
        "version": "1.0.0",
        "description": "京剧组子粒子系统TD集成",
        "td_version": "2022.0+",
        "dependencies": [
            "numpy",
        ],
        "parameters": [
            {
                "name": "preset",
                "type": "str",
                "default": "glow",
                "options": ["ink", "glow", "fire", "snow", "sparks", "gold", "silk", "energy"],
            },
            {
                "name": "emitRate",
                "type": "float",
                "default": 50.0,
                "range": [0, 200],
            },
            {
                "name": "particleSize",
                "type": "float",
                "default": 0.1,
                "range": [0.01, 1.0],
            },
            {
                "name": "lifetime",
                "type": "float",
                "default": 2.0,
                "range": [0.1, 10.0],
            },
            {
                "name": "gravity",
                "type": "float",
                "default": 0.0,
                "range": [-2.0, 2.0],
            },
            {
                "name": "turbulence",
                "type": "float",
                "default": 0.5,
                "range": [0, 5.0],
            },
            {
                "name": "tcpPort",
                "type": "int",
                "default": 7000,
                "range": [1024, 65535],
            },
        ],
    }


# 导出接口
__all__ = [
    "ParticlePreset",
    "EmitterShape", 
    "ParticleEmitter",
    "ParticleSystem",
    "TDParticleTransmitter",
    "PresetLibrary",
    "create_td_integration_module",
]
