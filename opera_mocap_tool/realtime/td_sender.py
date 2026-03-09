"""
TouchDesigner数据发送器。

通过UDP/OSC协议向TouchDesigner发送动捕数据。
"""

from __future__ import annotations

import socket
import struct
import json
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
class TDConfig:
    """TouchDesigner连接配置"""
    host: str = "127.0.0.1"
    port: int = 7000
    use_udp: bool = True
    use_osc: bool = False
    reconnect: bool = True
    reconnect_delay: float = 2.0


class TDSender:
    """TouchDesigner数据发送器"""
    
    def __init__(self, config: TDConfig | None = None):
        self.config = config or TDConfig()
        self.socket: socket.socket | None = None
        self.connected = False
        
        # OSC相关
        self._osc_socket: socket.socket | None = None
        
        # 统计
        self.packets_sent = 0
        self.bytes_sent = 0
        self.last_error: str | None = None
    
    def connect(self) -> bool:
        """建立连接"""
        try:
            if self.config.use_udp:
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                self.connected = True
                print(f"TD发送器已准备: {self.config.host}:{self.config.port}")
                return True
            else:
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.socket.settimeout(5.0)
                self.socket.connect((self.config.host, self.config.port))
                self.connected = True
                print(f"已连接到TD: {self.config.host}:{self.config.port}")
                return True
        except Exception as e:
            self.last_error = str(e)
            print(f"连接TD失败: {e}")
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
            # 转换为TD友好的格式
            td_data = self._format_for_td(skeleton_data)
            
            if self.config.use_osc:
                return self._send_osc("/mocap/skeleton", td_data)
            else:
                return self._send_udp(td_data)
        except Exception as e:
            self.last_error = str(e)
            return False
    
    def send_particles(self, particle_data: dict) -> bool:
        """发送粒子数据"""
        if not self.connected:
            self.connect()
        
        try:
            if self.config.use_osc:
                return self._send_osc("/mocap/particles", particle_data)
            else:
                return self._send_udp(particle_data)
        except Exception as e:
            self.last_error = str(e)
            return False
    
    def send_joint(self, joint_name: str, position: tuple, rotation: tuple) -> bool:
        """发送单个关节数据"""
        if not self.connected:
            self.connect()
        
        try:
            data = {
                "joint": joint_name,
                "position": list(position),
                "rotation": list(rotation),
            }
            
            if self.config.use_osc:
                address = f"/mocap/joint/{joint_name}"
                return self._send_osc(address, data)
            else:
                return self._send_udp(data)
        except Exception as e:
            self.last_error = str(e)
            return False
    
    def send_end_effectors(self, effectors: dict[str, np.ndarray]) -> bool:
        """发送末端效应器位置"""
        if not self.connected:
            self.connect()
        
        try:
            data = {
                "effectors": {
                    name: pos.tolist() if isinstance(pos, np.ndarray) else list(pos)
                    for name, pos in effectors.items()
                }
            }
            
            if self.config.use_osc:
                return self._send_osc("/mocap/effectors", data)
            else:
                return self._send_udp(data)
        except Exception as e:
            self.last_error = str(e)
            return False
    
    def _format_for_td(self, skeleton_data: dict) -> dict:
        """格式化为TD友好格式"""
        # 展平嵌套结构，便于TD解析
        result = {
            "frame": skeleton_data.get("frame_number", 0),
            "timestamp": skeleton_data.get("timestamp", 0.0),
        }
        
        # 展平关节数据
        joints = skeleton_data.get("joints", {})
        for joint_name, joint_data in joints.items():
            pos = joint_data.get("position", [0, 0, 0])
            rot = joint_data.get("rotation", [0, 0, 0, 1])
            
            result[f"{joint_name}_x"] = pos[0]
            result[f"{joint_name}_y"] = pos[1]
            result[f"{joint_name}_z"] = pos[2]
            result[f"{joint_name}_qx"] = rot[0]
            result[f"{joint_name}_qy"] = rot[1]
            result[f"{joint_name}_qz"] = rot[2]
            result[f"{joint_name}_qw"] = rot[3]
        
        return result
    
    def _send_udp(self, data: dict) -> bool:
        """通过UDP发送"""
        if not self.socket:
            return False
        
        try:
            # JSON编码
            json_data = json.dumps(data)
            encoded = json_data.encode('utf-8')
            
            # 发送
            self.socket.sendto(encoded, (self.config.host, self.config.port))
            
            self.packets_sent += 1
            self.bytes_sent += len(encoded)
            
            return True
        except Exception as e:
            self.last_error = str(e)
            # 尝试重连
            if self.config.reconnect:
                self.connect()
            return False
    
    def _send_osc(self, address: str, data: Any) -> bool:
        """通过OSC发送"""
        # OSC格式: 地址 + 类型标签 + 数据
        try:
            # 创建OSC消息
            message = self._create_osc_message(address, data)
            
            if not self._osc_socket:
                self._osc_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            
            self._osc_socket.sendto(message, (self.config.host, self.config.port))
            
            self.packets_sent += 1
            self.bytes_sent += len(message)
            
            return True
        except Exception as e:
            self.last_error = str(e)
            return False
    
    def _create_osc_message(self, address: str, data: Any) -> bytes:
        """创建OSC消息"""
        # 地址
        address_bytes = address.encode('utf-8') + b'\x00'
        # 补齐到4字节
        while len(address_bytes) % 4 != 0:
            address_bytes += b'\x00'
        
        # 类型标签
        if isinstance(data, dict):
            type_tag = b','
            values = b''
            for key, value in data.items():
                if isinstance(value, (int, np.integer)):
                    type_tag += b'i'
                    values += struct.pack('>i', int(value))
                elif isinstance(value, (float, np.floating)):
                    type_tag += b'f'
                    values += struct.pack('>f', float(value))
                elif isinstance(value, str):
                    type_tag += b's'
                    value_bytes = value.encode('utf-8') + b'\x00'
                    while len(value_bytes) % 4 != 0:
                        value_bytes += b'\x00'
                    values += value_bytes
            
            # 补齐类型标签到4字节
            while len(type_tag) % 4 != 0:
                type_tag += b'\x00'
            
            return address_bytes + type_tag + values
        elif isinstance(data, (int, np.integer)):
            return address_bytes + b',i' + b'\x00' * 2 + struct.pack('>i', int(data))
        elif isinstance(data, (float, np.floating)):
            return address_bytes + b',f' + b'\x00' + struct.pack('>f', float(data))
        else:
            return address_bytes + b',s\x00' + data.encode('utf-8') + b'\x00'
    
    def send_binary(self, data: bytes) -> bool:
        """发送二进制数据"""
        if not self.socket:
            return False
        
        try:
            self.socket.sendto(data, (self.config.host, self.config.port))
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


class TDDatSender:
    """TouchDesigner DAT发送器 - 发送表格数据"""
    
    def __init__(self, host: str = "127.0.0.1", port: int = 7001):
        self.host = host
        self.port = port
        self.socket = None
    
    def connect(self) -> bool:
        """建立连接"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.connected = True
            return True
        except:
            return False
    
    def send_table(self, headers: list[str], rows: list[list]) -> bool:
        """发送表格数据"""
        if not self.socket:
            self.connect()
        
        try:
            # 格式: CSV风格
            lines = [",".join(headers)]
            for row in rows:
                lines.append(",".join(str(v) for v in row))
            
            data = "\n".join(lines).encode('utf-8')
            self.socket.sendto(data, (self.host, self.port))
            return True
        except:
            return False
    
    def send_joint_table(self, skeleton_data: dict) -> bool:
        """发送关节表格"""
        headers = ["joint", "x", "y", "z", "qx", "qy", "qz", "qw"]
        rows = []
        
        joints = skeleton_data.get("joints", {})
        for joint_name, joint_data in joints.items():
            pos = joint_data.get("position", [0, 0, 0])
            rot = joint_data.get("rotation", [0, 0, 0, 1])
            rows.append([joint_name] + pos + list(rot))
        
        return self.send_table(headers, rows)


def create_td_sender(
    host: str = "127.0.0.1",
    port: int = 7000,
    use_udp: bool = True,
) -> TDSender:
    """创建TD发送器的便捷函数"""
    config = TDConfig(host=host, port=port, use_udp=use_udp)
    sender = TDSender(config)
    sender.connect()
    return sender


if __name__ == "__main__":
    # 测试代码
    print("测试TD发送器...")
    
    sender = create_td_sender()
    
    # 发送测试数据
    test_data = {
        "frame_number": 1,
        "timestamp": 0.0,
        "joints": {
            "head": {"position": [0, 1.6, 0], "rotation": [0, 0, 0, 1]},
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
