"""
Vicon实时采集客户端。

支持连接Vicon Blade系统，实时获取动捕数据。
"""

from __future__ import annotations

import socket
import threading
import time
import json
from typing import Callable, Any
from dataclasses import dataclass, field
from pathlib import Path
import sys

# 添加项目根目录到路径
_root = Path(__file__).resolve().parent.parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))


@dataclass
class ViconFrame:
    """Vicon单帧数据"""
    frame_number: int
    timestamp: float
    subjects: dict = field(default_factory=dict)
    
    def get_subject(self, name: str) -> dict | None:
        """获取指定对象的数据"""
        return self.subjects.get(name)
    
    def get_marker_positions(self, subject_name: str) -> dict[str, tuple]:
        """获取对象的marker位置"""
        subject = self.get_subject(subject_name)
        if not subject:
            return {}
        return subject.get("markers", {})


@dataclass
class ViconConfig:
    """Vicon连接配置"""
    host: str = "localhost"
    port: int = 51001
    timeout: float = 5.0
    reconnect_delay: float = 2.0
    max_reconnect: int = 10


class ViconClient:
    """Vicon实时采集客户端"""
    
    # Vicon协议命令
    CMD_GET_FRAME = b"GetFrame"
    CMD_GET_SUBJECTS = b"GetSubjects"
    CMD_START_STREAMING = b"StartStreaming"
    CMD_STOP_STREAMING = b"StopStreaming"
    
    def __init__(self, config: ViconConfig | None = None):
        self.config = config or ViconConfig()
        self.socket: socket.socket | None = None
        self.connected = False
        self.streaming = False
        self.subscribed_subjects: set[str] = set()
        
        # 回调
        self.frame_callback: Callable[[ViconFrame], None] | None = None
        
        # 线程
        self._stream_thread: threading.Thread | None = None
        self._running = False
        
        # 性能统计
        self.fps = 0.0
        self.frame_count = 0
        self.last_frame_time = time.time()
        
        # Vicon SDK模拟模式（当SDK不可用时）
        self._simulate_mode = False
    
    def connect(self) -> bool:
        """连接到Vicon Blade"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(self.config.timeout)
            self.socket.connect((self.config.host, self.config.port))
            self.connected = True
            print(f"已连接到Vicon: {self.config.host}:{self.config.port}")
            return True
        except ConnectionRefusedError:
            print(f"无法连接到Vicon，启用模拟模式")
            self._simulate_mode = True
            self.connected = True
            return True
        except Exception as e:
            print(f"连接Vicon失败: {e}")
            self.connected = False
            return False
    
    def disconnect(self):
        """断开连接"""
        self.stop_streaming()
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None
        self.connected = False
        print("已断开Vicon连接")
    
    def subscribe_subjects(self, subject_names: list[str]):
        """订阅需要跟踪的对象"""
        self.subscribed_subjects = set(subject_names)
        if not self._simulate_mode and self.connected:
            # 发送订阅命令
            for name in subject_names:
                self._send_command(f"Subscribe:{name}".encode())
    
    def _send_command(self, cmd: bytes) -> bool:
        """发送命令到Vicon"""
        if not self.socket:
            return False
        try:
            # 发送命令长度 + 命令
            length = len(cmd)
            self.socket.send(length.to_bytes(4, byteorder='big'))
            self.socket.send(cmd)
            return True
        except Exception as e:
            print(f"发送命令失败: {e}")
            return False
    
    def _receive_data(self) -> dict | None:
        """接收Vicon数据"""
        if not self.socket:
            return None
        try:
            # 读取4字节长度
            length_bytes = self.socket.recv(4)
            if not length_bytes:
                return None
            length = int.from_bytes(length_bytes, byteorder='big')
            
            # 读取数据
            data = b""
            while len(data) < length:
                chunk = self.socket.recv(length - len(data))
                if not chunk:
                    return None
                data += chunk
            
            # 解析JSON
            return json.loads(data.decode('utf-8'))
        except Exception as e:
            return None
    
    def get_frame(self) -> ViconFrame | None:
        """获取当前帧数据"""
        if self._simulate_mode:
            return self._generate_simulated_frame()
        
        if not self.connected or not self.socket:
            return None
        
        # 发送获取帧命令
        self._send_command(self.CMD_GET_FRAME)
        
        # 接收数据
        data = self._receive_data()
        if not data:
            return None
        
        return self._parse_frame(data)
    
    def _parse_frame(self, data: dict) -> ViconFrame:
        """解析帧数据"""
        self.frame_count += 1
        current_time = time.time()
        
        # 计算FPS
        if current_time - self.last_frame_time > 0:
            self.fps = 1.0 / (current_time - self.last_frame_time)
        self.last_frame_time = current_time
        
        # 解析subjects
        subjects = {}
        for name, subject_data in data.get("Subjects", {}).items():
            if name not in self.subscribed_subjects:
                continue
                
            # 解析markers
            markers = {}
            for marker_name, marker_data in subject_data.get("Markers", {}).items():
                if marker_data.get("Occluded", False):
                    continue
                pos = marker_data.get("Position", [0, 0, 0])
                markers[marker_name] = (pos[0], pos[1], pos[2])
            
            # 解析骨骼（如果可用）
            bones = {}
            for bone_name, bone_data in subject_data.get("Bones", {}).items():
                pos = bone_data.get("Position", [0, 0, 0])
                rot = bone_data.get("Rotation", [0, 0, 0, 1])  # quaternion
                bones[bone_name] = {
                    "position": (pos[0], pos[1], pos[2]),
                    "rotation": tuple(rot),
                }
            
            subjects[name] = {
                "markers": markers,
                "bones": bones,
            }
        
        return ViconFrame(
            frame_number=data.get("FrameNumber", self.frame_count),
            timestamp=data.get("Timecode", time.time()),
            subjects=subjects,
        )
    
    def _generate_simulated_frame(self) -> ViconFrame:
        """生成模拟帧数据（用于测试）"""
        self.frame_count += 1
        current_time = time.time()
        
        # 计算FPS
        if current_time - self.last_frame_time > 0:
            self.fps = 1.0 / (current_time - self.last_frame_time)
        self.last_frame_time = current_time
        
        # 生成模拟的骨骼数据
        subjects = {}
        t = time.time()
        
        for subject_name in self.subscribed_subjects:
            # 模拟一个简单的骨骼系统
            bones = {}
            
            # 头部 - 上下移动
            head_y = 1.5 + 0.1 * (0.5 + 0.5 * (t % 2))
            bones["head"] = {
                "position": (0.0, head_y, 0.0),
                "rotation": (0, 0, 0, 1),
            }
            
            # 脊椎
            bones["spine_base"] = {
                "position": (0.0, 0.9, 0.0),
                "rotation": (0, 0, 0, 1),
            }
            bones["spine_mid"] = {
                "position": (0.0, 1.05, 0.0),
                "rotation": (0, 0, 0, 1),
            }
            bones["spine_upper"] = {
                "position": (0.0, 1.2, 0.0),
                "rotation": (0, 0, 0, 1),
            }
            
            # 左手 - 圆周运动
            angle = t * 2
            bones["hand_l"] = {
                "position": (-0.4 - 0.1 * (0.5 + 0.5 * (t % 3)), 1.1 + 0.2 * (0.5 + 0.5 * (t % 2)), 0.2 * (0.5 + 0.5 * (t % 4))),
                "rotation": (0, 0, 0, 1),
            }
            
            # 右手
            bones["hand_r"] = {
                "position": (0.4 + 0.1 * (0.5 + 0.5 * (t % 3)), 1.1 + 0.2 * (0.5 + 0.5 * (t % 2)), 0.2 * (0.5 + 0.5 * (t % 4))),
                "rotation": (0, 0, 0, 1),
            }
            
            subjects[subject_name] = {
                "markers": {},
                "bones": bones,
            }
        
        return ViconFrame(
            frame_number=self.frame_count,
            timestamp=current_time,
            subjects=subjects,
        )
    
    def start_streaming(self, callback: Callable[[ViconFrame], None] | None = None):
        """开始流式采集"""
        if self.streaming:
            return
        
        self.frame_callback = callback
        self._running = True
        
        if not self._simulate_mode:
            self._send_command(self.CMD_START_STREAMING)
        
        # 启动采集线程
        self._stream_thread = threading.Thread(target=self._streaming_loop, daemon=True)
        self._stream_thread.start()
        self.streaming = True
        print("开始Vicon流式采集")
    
    def _streaming_loop(self):
        """流式采集循环"""
        while self._running:
            frame = self.get_frame()
            if frame and self.frame_callback:
                try:
                    self.frame_callback(frame)
                except Exception as e:
                    print(f"帧回调错误: {e}")
            else:
                time.sleep(0.001)  # 避免CPU占用100%
    
    def stop_streaming(self):
        """停止流式采集"""
        self._running = False
        if not self._simulate_mode and self.socket:
            self._send_command(self.CMD_STOP_STREAMING)
        self.streaming = False
        print("停止Vicon流式采集")
    
    def get_stats(self) -> dict:
        """获取性能统计"""
        return {
            "connected": self.connected,
            "streaming": self.streaming,
            "fps": self.fps,
            "frame_count": self.frame_count,
            "subscribed_subjects": list(self.subscribed_subjects),
            "simulate_mode": self._simulate_mode,
        }


def create_vicon_client(
    host: str = "localhost",
    port: int = 51001,
    subjects: list[str] | None = None,
) -> ViconClient:
    """创建Vicon客户端的便捷函数"""
    config = ViconConfig(host=host, port=port)
    client = ViconClient(config)
    
    if client.connect():
        if subjects:
            client.subscribe_subjects(subjects)
    
    return client


if __name__ == "__main__":
    # 测试代码
    print("测试Vicon客户端...")
    
    client = create_vicon_client(subjects=["Actor1"])
    
    def on_frame(frame: ViconFrame):
        print(f"帧: {frame.frame_number}, FPS: {client.fps:.1f}")
        for subject_name, subject_data in frame.subjects.items():
            print(f"  {subject_name}: {len(subject_data.get('bones', {}))} 骨骼")
    
    client.start_streaming(on_frame)
    
    # 运行10秒
    time.sleep(10)
    
    client.stop_streaming()
    client.disconnect()
    
    print("测试完成")
    print(f"统计: {client.get_stats()}")
