"""
Unreal Engine 5 数据发送器。

通过WebSocket/JSON协议向UE5发送动捕数据。
支持Live Link数据格式。
"""

from __future__ import annotations

import socket
import json
import struct
import threading
from typing import Any
from dataclasses import dataclass
from pathlib import Path
import sys

import numpy as np

# 添加项目根目录到路径
_root = Path(__file__).resolve().parent.parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))


@dataclass
class UE5Config:
    """Unreal Engine连接配置"""
    host: str = "127.0.0.1"
    port: int = 11111
    use_websocket: bool = True
    reconnect: bool = True
    reconnect_delay: float = 2.0


class UE5Sender:
    """Unreal Engine 5数据发送器"""
    
    def __init__(self, config: UE5Config | None = None):
        self.config = config or UE5Config()
        self.socket: socket.socket | None = None
        self.connected = False
        
        # 统计
        self.packets_sent = 0
        self.bytes_sent = 0
        self.last_error: str | None = None
        
        # 骨骼名称映射
        self._bone_name_mapping = {
            "pelvis": "pelvis",
            "spine_base": "spine_01",
            "spine_mid": "spine_02", 
            "spine_upper": "spine_03",
            "neck": "neck_01",
            "head": "head",
            "shoulder_l": "clavicle_l",
            "upper_arm_l": "upperarm_l",
            "forearm_l": "lowerarm_l",
            "hand_l": "hand_l",
            "shoulder_r": "clavicle_r",
            "upper_arm_r": "upperarm_r",
            "forearm_r": "lowerarm_r",
            "hand_r": "hand_r",
            "hip_l": "thigh_l",
            "thigh_l": "calf_l",
            "shin_l": "foot_l",
            "foot_l": "ball_l",
            "hip_r": "thigh_r",
            "thigh_r": "calf_r",
            "shin_r": "foot_r",
            "foot_r": "ball_r",
        }
    
    def connect(self) -> bool:
        """建立连接"""
        try:
            if self.config.use_websocket:
                # WebSocket使用TCP连接
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.socket.settimeout(5.0)
                self.socket.connect((self.config.host, self.config.port))
                self.connected = True
                print(f"已连接到UE5: {self.config.host}:{self.config.port}")
                return True
            else:
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                self.connected = True
                print(f"UE5发送器已准备: {self.config.host}:{self.config.port}")
                return True
        except Exception as e:
            self.last_error = str(e)
            print(f"连接UE5失败: {e}")
            self.connected = False
            return False
    
    def disconnect(self):
        """断开连接"""
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None
        self.connected = False
    
    def send_skeleton(self, skeleton_data: dict) -> bool:
        """发送骨架数据"""
        if not self.connected:
            self.connect()
        
        try:
            # 转换为UE5 Live Link格式
            ue5_data = self._format_for_ue5(skeleton_data)
            
            return self._send_json(ue5_data)
        except Exception as e:
            self.last_error = str(e)
            return False
    
    def send_transform(self, bone_name: str, position: tuple, rotation: tuple) -> bool:
        """发送单个骨骼变换"""
        if not self.connected:
            self.connect()
        
        try:
            # 映射骨骼名称
            ue5_bone = self._bone_name_mapping.get(bone_name, bone_name)
            
            data = {
                "type": "transform",
                "bone": ue5_bone,
                "position": {"x": position[0], "y": position[1], "z": position[2]},
                "rotation": {"x": rotation[0], "y": rotation[1], "z": rotation[2], "w": rotation[3]},
            }
            
            return self._send_json(data)
        except Exception as e:
            self.last_error = str(e)
            return False
    
    def send_full_body_transforms(self, skeleton_data: dict) -> bool:
        """发送完整身体骨骼变换"""
        if not self.connected:
            self.connect()
        
        try:
            data = {
                "type": "full_body",
                "frame": skeleton_data.get("frame_number", 0),
                "timestamp": skeleton_data.get("timestamp", 0.0),
                "bones": {},
            }
            
            joints = skeleton_data.get("joints", {})
            for joint_name, joint_data in joints.items():
                ue5_bone = self._bone_name_mapping.get(joint_name, joint_name)
                pos = joint_data.get("position", [0, 0, 0])
                rot = joint_data.get("rotation", [0, 0, 0, 1])
                
                # UE5使用左手坐标系，Z轴向上
                # 转换Y-up到Z-up
                data["bones"][ue5_bone] = {
                    "position": {"x": pos[0], "y": pos[2], "z": pos[1]},
                    "rotation": {"x": rot[0], "y": rot[2], "z": rot[1], "w": rot[3]},
                }
            
            return self._send_json(data)
        except Exception as e:
            self.last_error = str(e)
            return False
    
    def send_metadata(self, metadata: dict) -> bool:
        """发送元数据"""
        if not self.connected:
            self.connect()
        
        try:
            data = {
                "type": "metadata",
                **metadata,
            }
            return self._send_json(data)
        except Exception as e:
            self.last_error = str(e)
            return False
    
    def _format_for_ue5(self, skeleton_data: dict) -> dict:
        """格式化为UE5 Live Link格式"""
        result = {
            "type": "skeleton",
            "frame": skeleton_data.get("frame_number", 0),
            "timestamp": skeleton_data.get("timestamp", 0.0),
            "subject_name": "OperaMocap",
            "bones": {},
        }
        
        joints = skeleton_data.get("joints", {})
        for joint_name, joint_data in joints.items():
            ue5_bone = self._bone_name_mapping.get(joint_name, joint_name)
            pos = joint_data.get("position", [0, 0, 0])
            rot = joint_data.get("rotation", [0, 0, 0, 1])
            
            result["bones"][ue5_bone] = {
                "location": {"x": pos[0], "y": pos[2], "z": pos[1]},  # Y-up to Z-up
                "rotation": {"x": rot[0], "y": rot[2], "z": rot[1], "w": rot[3]},
                "scale": {"x": 1.0, "y": 1.0, "z": 1.0},
            }
        
        return result
    
    def _send_json(self, data: dict) -> bool:
        """发送JSON数据"""
        if not self.socket:
            return False
        
        try:
            # JSON编码
            json_data = json.dumps(data)
            encoded = json_data.encode('utf-8')
            
            # 添加4字节长度前缀
            message = struct.pack('>I', len(encoded)) + encoded
            
            # 发送
            self.socket.sendall(message)
            
            self.packets_sent += 1
            self.bytes_sent += len(message)
            
            return True
        except Exception as e:
            self.last_error = str(e)
            if self.config.reconnect:
                self.connect()
            return False
    
    def _send_binary(self, data: bytes) -> bool:
        """发送二进制数据"""
        if not self.socket:
            return False
        
        try:
            self.socket.sendall(data)
            self.packets_sent += 1
            self.bytes_sent += len(data)
            return True
        except Exception as e:
            self.last_error = str(e)
            return False
    
    def get_stats(self) -> dict:
        """获取统计信息"""
        return {
            "connected": self.connected,
            "packets_sent": self.packets_sent,
            "bytes_sent": self.bytes_sent,
            "last_error": self.last_error,
        }
    
    def reset_stats(self):
        """重置统计"""
        self.packets_sent = 0
        self.bytes_sent = 0
        self.last_error = None


class LiveLinkBridge:
    """Live Link桥接器 - UE5专用"""
    
    def __init__(self, port: int = 11111):
        self.port = port
        self.sender = UE5Sender(UE5Config(port=port))
    
    def start(self) -> bool:
        """启动桥接器"""
        return self.sender.connect()
    
    def stop(self):
        """停止桥接器"""
        self.sender.disconnect()
    
    def push_frame(self, skeleton_data: dict) -> bool:
        """推送一帧"""
        return self.sender.send_full_body_transforms(skeleton_data)


def create_ue5_sender(
    host: str = "127.0.0.1",
    port: int = 11111,
) -> UE5Sender:
    """创建UE5发送器的便捷函数"""
    config = UE5Config(host=host, port=port)
    sender = UE5Sender(config)
    sender.connect()
    return sender


if __name__ == "__main__":
    # 测试代码
    print("测试UE5发送器...")
    
    sender = create_ue5_sender()
    
    # 发送测试数据
    test_data = {
        "frame_number": 1,
        "timestamp": 0.0,
        "joints": {
            "head": {"position": [0, 1.6, 0], "rotation": [0, 0, 0, 1]},
            "pelvis": {"position": [0, 1.0, 0], "rotation": [0, 0, 0, 1]},
            "hand_l": {"position": [-0.3, 1.2, 0.1], "rotation": [0, 0, 0, 1]},
            "hand_r": {"position": [0.3, 1.2, 0.1], "rotation": [0, 0, 0, 1]},
        }
    }
    
    # 发送几次
    for i in range(10):
        test_data["frame_number"] = i
        sender.send_skeleton(test_data)
        print(f"已发送帧 {i}")
    
    print(f"统计: {sender.get_stats()}")
    
    sender.disconnect()
    print("测试完成")
