"""
实时Pipeline - 整合所有实时组件。

提供统一的实时动捕数据采集、处理和发送功能。
"""

from __future__ import annotations

import time
import threading
from typing import Callable, Any
from dataclasses import dataclass, field
from pathlib import Path
import sys

import numpy as np

# 添加项目根目录到路径
_root = Path(__file__).resolve().parent.parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from opera_mocap_tool.realtime.vicon_client import ViconClient, ViconConfig, ViconFrame
from opera_mocap_tool.realtime.skeleton_realtime import RealtimeSkeleton, SkeletonData, STANDARD_JOINTS
from opera_mocap_tool.realtime.filters import RealtimeFilter, FilterConfig, MotionSmoother
from opera_mocap_tool.realtime.td_sender import TDSender, TDConfig
from opera_mocap_tool.realtime.ue5_sender import UE5Sender, UE5Config


@dataclass
class PipelineConfig:
    """Pipeline配置"""
    # Vicon设置
    vicon_host: str = "localhost"
    vicon_port: int = 51001
    subject_names: list[str] = field(default_factory=lambda: ["Actor1"])
    
    # TD设置
    td_enabled: bool = True
    td_host: str = "127.0.0.1"
    td_port: int = 7000
    
    # UE5设置
    ue5_enabled: bool = False
    ue5_host: str = "127.0.0.1"
    ue5_port: int = 11111
    
    # 滤波设置
    filter_enabled: bool = True
    filter_type: str = "ema"  # "ema", "butterworth", "kalman"
    filter_alpha: float = 0.3  # EMA alpha
    filter_cutoff: float = 5.0  # Butterworth截止频率
    
    # 处理设置
    center_on_pelvis: bool = True
    scale_to_height: float = 1.7  # 目标身高
    
    # 性能设置
    target_fps: float = 60.0
    skip_frames: int = 0  # 跳帧（用于降低输出帧率）


class PipelineStats:
    """Pipeline统计信息"""
    def __init__(self):
        self.frame_count = 0
        self.start_time = 0.0
        self.current_fps = 0.0
        self.avg_latency_ms = 0.0
        self.td_packets_sent = 0
        self.ue5_packets_sent = 0
        self.errors = 0
        self.last_error: str | None = None


class RealtimePipeline:
    """实时Pipeline主类"""
    
    def __init__(self, config: PipelineConfig | None = None):
        self.config = config or PipelineConfig()
        
        # 组件
        self.vicon_client: ViconClient | None = None
        self.skeleton = RealtimeSkeleton()
        self.smoother = MotionSmoother()
        self.td_sender: TDSender | None = None
        self.ue5_sender: UE5Sender | None = None
        
        # 状态
        self.running = False
        self.paused = False
        
        # 回调
        self.frame_callback: Callable[[SkeletonData], None] | None = None
        
        # 统计
        self.stats = PipelineStats()
        
        # 线程
        self._process_thread: threading.Thread | None = None
        
        # 初始化组件
        self._init_components()
    
    def _init_components(self):
        """初始化所有组件"""
        # Vicon客户端
        vicon_config = ViconConfig(
            host=self.config.vicon_host,
            port=self.config.vicon_port,
        )
        self.vicon_client = ViconClient(vicon_config)
        
        # TD发送器
        if self.config.td_enabled:
            td_config = TDConfig(
                host=self.config.td_host,
                port=self.config.td_port,
            )
            self.td_sender = TDSender(td_config)
        
        # UE5发送器
        if self.config.ue5_enabled:
            ue5_config = UE5Config(
                host=self.config.ue5_host,
                port=self.config.ue5_port,
            )
            self.ue5_sender = UE5Sender(ue5_config)
        
        # 滤波器配置
        if self.config.filter_enabled:
            filter_config = FilterConfig(
                filter_type=self.config.filter_type,
                alpha=self.config.filter_alpha,
                cutoff_frequency=self.config.filter_cutoff,
            )
            self.smoother = MotionSmoother()
    
    def connect(self) -> bool:
        """连接所有组件"""
        # 连接Vicon
        if self.vicon_client:
            self.vicon_client.connect()
            self.vicon_client.subscribe_subjects(self.config.subject_names)
        
        # 连接TD
        if self.td_sender:
            self.td_sender.connect()
        
        # 连接UE5
        if self.ue5_sender:
            self.ue5_sender.connect()
        
        return True
    
    def disconnect(self):
        """断开所有组件"""
        self.stop()
        
        if self.vicon_client:
            self.vicon_client.disconnect()
        
        if self.td_sender:
            self.td_sender.disconnect()
        
        if self.ue5_sender:
            self.ue5_sender.disconnect()
    
    def start(self):
        """启动Pipeline"""
        if self.running:
            return
        
        if not self.vicon_client or not self.vicon_client.connected:
            self.connect()
        
        self.running = True
        self.stats.start_time = time.time()
        
        # 启动Vicon流式采集
        self.vicon_client.start_streaming(self._on_frame)
        
        print("Pipeline已启动")
    
    def stop(self):
        """停止Pipeline"""
        self.running = False
        
        if self.vicon_client:
            self.vicon_client.stop_streaming()
        
        print("Pipeline已停止")
    
    def pause(self):
        """暂停Pipeline"""
        self.paused = True
    
    def resume(self):
        """恢复Pipeline"""
        self.paused = False
    
    def _on_frame(self, frame: ViconFrame):
        """处理新帧"""
        if self.paused:
            return
        
        try:
            # 更新骨架
            skeleton_data = self.skeleton.update(frame)
            
            # 平滑滤波
            if self.config.filter_enabled:
                # 准备关节位置字典
                positions = {}
                velocities = {}
                for joint_name in STANDARD_JOINTS:
                    pos = skeleton_data.joints.get(joint_name)
                    if pos:
                        positions[joint_name] = pos.position
                        velocities[joint_name] = pos.velocity
                
                # 平滑
                smoothed_pos = self.smoother.smooth_positions(positions)
                smoothed_vel = self.smoother.smooth_velocities(velocities)
                
                # 应用平滑后的数据
                for joint_name in STANDARD_JOINTS:
                    if joint_name in smoothed_pos:
                        skeleton_data.joints[joint_name].position = smoothed_pos[joint_name]
                    if joint_name in smoothed_vel:
                        skeleton_data.joints[joint_name].velocity = smoothed_vel[joint_name]
            
            # 中心化
            if self.config.center_on_pelvis:
                self.skeleton.center_on_pelvis()
            
            # 缩放
            if self.config.scale_to_height > 0:
                self.skeleton.scale_to_height(self.config.scale_to_height)
            
            # 发送到TD
            if self.config.td_enabled and self.td_sender:
                data = skeleton_data.to_dict()
                if self.td_sender.send_skeleton(data):
                    self.stats.td_packets_sent += 1
            
            # 发送到UE5
            if self.config.ue5_enabled and self.ue5_sender:
                data = skeleton_data.to_dict()
                if self.ue5_sender.send_skeleton(data):
                    self.stats.ue5_packets_sent += 1
            
            # 更新统计
            self.stats.frame_count += 1
            current_time = time.time()
            if self.stats.frame_count > 1:
                self.stats.current_fps = 1.0 / (current_time - self.stats.last_frame_time) if hasattr(self.stats, 'last_frame_time') else 0
            self.stats.last_frame_time = current_time
            
            # 回调
            if self.frame_callback:
                self.frame_callback(skeleton_data)
        
        except Exception as e:
            self.stats.errors += 1
            self.stats.last_error = str(e)
            print(f"处理帧错误: {e}")
    
    def get_stats(self) -> dict:
        """获取统计信息"""
        elapsed = time.time() - self.stats.start_time if self.stats.start_time > 0 else 0
        
        return {
            "running": self.running,
            "paused": self.paused,
            "frame_count": self.stats.frame_count,
            "elapsed_seconds": elapsed,
            "avg_fps": self.stats.frame_count / elapsed if elapsed > 0 else 0,
            "current_fps": self.stats.current_fps,
            "td_packets_sent": self.stats.td_packets_sent,
            "ue5_packets_sent": self.stats.ue5_packets_sent,
            "errors": self.stats.errors,
            "last_error": self.stats.last_error,
            "vicon_connected": self.vicon_client.connected if self.vicon_client else False,
            "td_connected": self.td_sender.connected if self.td_sender else False,
            "ue5_connected": self.ue5_sender.connected if self.ue5_sender else False,
        }
    
    def get_skeleton(self) -> SkeletonData:
        """获取当前骨架数据"""
        return self.skeleton.get_skeleton_data()
    
    def update_config(self, **kwargs):
        """更新配置"""
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
        
        # 重新初始化滤波
        if 'filter_enabled' in kwargs or 'filter_type' in kwargs:
            self._init_components()


def create_pipeline(
    vicon_host: str = "localhost",
    vicon_port: int = 51001,
    td_enabled: bool = True,
    td_host: str = "127.0.0.1",
    td_port: int = 7000,
    ue5_enabled: bool = False,
    ue5_host: str = "127.0.0.1",
    ue5_port: int = 11111,
) -> RealtimePipeline:
    """创建Pipeline的便捷函数"""
    config = PipelineConfig(
        vicon_host=vicon_host,
        vicon_port=vicon_port,
        td_enabled=td_enabled,
        td_host=td_host,
        td_port=td_port,
        ue5_enabled=ue5_enabled,
        ue5_host=ue5_host,
        ue5_port=ue5_port,
    )
    return RealtimePipeline(config)


if __name__ == "__main__":
    # 测试代码
    print("测试实时Pipeline...")
    
    # 创建Pipeline（使用模拟模式）
    pipeline = create_pipeline(
        td_enabled=True,
        ue5_enabled=False,
    )
    
    # 设置回调
    def on_skeleton(skeleton_data: SkeletonData):
        print(f"帧: {skeleton_data.frame_number}, 头部: {skeleton_data.joints.get('head').position if skeleton_data.joints.get('head') else 'N/A'}")
    
    pipeline.frame_callback = on_skeleton
    
    # 启动
    pipeline.connect()
    pipeline.start()
    
    # 运行10秒
    print("运行10秒...")
    time.sleep(10)
    
    # 停止
    pipeline.stop()
    pipeline.disconnect()
    
    print(f"\n统计: {pipeline.get_stats()}")
    print("测试完成")
