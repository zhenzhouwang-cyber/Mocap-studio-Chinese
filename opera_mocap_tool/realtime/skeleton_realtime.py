"""
实时骨架处理模块。

提供骨骼数据的实时处理、标准化和变换功能。
"""

from __future__ import annotations

from typing import Callable
from dataclasses import dataclass, field
from pathlib import Path
import sys

import numpy as np

# 添加项目根目录到路径
_root = Path(__file__).resolve().parent.parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from opera_mocap_tool.realtime.vicon_client import ViconFrame


# 标准京剧骨骼名称（22个关节）
STANDARD_JOINTS = [
    "pelvis",
    "spine_base", "spine_mid", "spine_upper",
    "neck", "head",
    "shoulder_l", "upper_arm_l", "forearm_l", "hand_l",
    "shoulder_r", "upper_arm_r", "forearm_r", "hand_r",
    "hip_l", "thigh_l", "shin_l", "foot_l",
    "hip_r", "thigh_r", "shin_r", "foot_r",
]

# Vicon骨骼名称映射到标准名称
VICON_TO_STANDARD = {
    "Pelvis": "pelvis",
    "Spine": "spine_base",
    "Spine1": "spine_mid",
    "Spine2": "spine_upper",
    "Neck": "neck",
    "Head": "head",
    "LeftShoulder": "shoulder_l",
    "LeftArm": "upper_arm_l",
    "LeftForeArm": "forearm_l",
    "LeftHand": "hand_l",
    "RightShoulder": "shoulder_r",
    "RightArm": "upper_arm_r",
    "RightForeArm": "forearm_r",
    "RightHand": "hand_r",
    "LeftUpLeg": "hip_l",
    "LeftLeg": "thigh_l",
    "LeftFoot": "shin_l",
    "LeftToeBase": "foot_l",
    "RightUpLeg": "hip_r",
    "RightLeg": "thigh_r",
    "RightFoot": "shin_r",
    "RightToeBase": "foot_r",
}


@dataclass
class JointData:
    """单个关节数据"""
    name: str
    position: np.ndarray  # 3D位置
    rotation: np.ndarray  # 四元数
    velocity: np.ndarray = field(default_factory=lambda: np.zeros(3))  # 速度
    acceleration: np.ndarray = field(default_factory=lambda: np.zeros(3))  # 加速度


@dataclass
class SkeletonData:
    """完整骨架数据"""
    frame_number: int
    timestamp: float
    joints: dict[str, JointData] = field(default_factory=dict)
    
    def get_joint(self, name: str) -> JointData | None:
        """获取关节数据"""
        return self.joints.get(name)
    
    def to_array(self) -> np.ndarray:
        """转换为numpy数组 (N, 7) - [x, y, z, qx, qy, qz, qw]"""
        data = []
        for joint_name in STANDARD_JOINTS:
            joint = self.joints.get(joint_name)
            if joint:
                pos = joint.position
                rot = joint.rotation
                data.append([pos[0], pos[1], pos[2], rot[0], rot[1], rot[2], rot[3]])
            else:
                data.append([0, 0, 0, 0, 0, 0, 1])
        return np.array(data)
    
    def to_dict(self) -> dict:
        """转换为字典"""
        result = {
            "frame_number": self.frame_number,
            "timestamp": self.timestamp,
            "joints": {},
        }
        for name, joint in self.joints.items():
            result["joints"][name] = {
                "position": joint.position.tolist(),
                "rotation": joint.rotation.tolist(),
                "velocity": joint.velocity.tolist(),
            }
        return result


class RealtimeSkeleton:
    """实时骨架处理"""
    
    def __init__(self):
        self.joints: dict[str, JointData] = {}
        self.previous_positions: dict[str, np.ndarray] = {}
        self.previous_velocities: dict[str, np.ndarray] = {}
        
        # 初始化关节
        for name in STANDARD_JOINTS:
            self.joints[name] = JointData(
                name=name,
                position=np.zeros(3),
                rotation=np.array([0, 0, 0, 1]),  # 单位四元数
            )
        
        # 元数据
        self.frame_number = 0
        self.timestamp = 0.0
    
    def update(self, frame: ViconFrame) -> SkeletonData:
        """更新骨架数据"""
        self.frame_number = frame.frame_number
        self.timestamp = frame.timestamp
        
        # 解析每个subject的数据
        for subject_name, subject_data in frame.subjects.items():
            bones = subject_data.get("bones", {})
            
            for vicon_name, bone_data in bones.items():
                # 映射到标准名称
                std_name = VICON_TO_STANDARD.get(vicon_name, vicon_name.lower())
                
                if std_name not in self.joints:
                    continue
                
                # 获取位置和旋转
                pos = np.array(bone_data.get("position", (0, 0, 0)))
                rot = np.array(bone_data.get("rotation", (0, 0, 0, 1)))
                
                # 计算速度
                prev_pos = self.previous_positions.get(std_name, pos)
                velocity = pos - prev_pos
                
                # 计算加速度
                prev_vel = self.previous_velocities.get(std_name, np.zeros(3))
                acceleration = velocity - prev_vel
                
                # 更新关节数据
                self.joints[std_name].position = pos
                self.joints[std_name].rotation = rot
                self.joints[std_name].velocity = velocity
                self.joints[std_name].acceleration = acceleration
                
                # 保存上一帧数据
                self.previous_positions[std_name] = pos.copy()
                self.previous_velocities[std_name] = velocity.copy()
        
        return self.get_skeleton_data()
    
    def update_from_dict(self, data: dict) -> SkeletonData:
        """从字典更新骨架数据"""
        self.frame_number = data.get("frame_number", 0)
        self.timestamp = data.get("timestamp", 0.0)
        
        joints_data = data.get("joints", {})
        
        for joint_name, joint_info in joints_data.items():
            if joint_name not in self.joints:
                continue
            
            pos = np.array(joint_info.get("position", [0, 0, 0]))
            rot = np.array(joint_info.get("rotation", [0, 0, 0, 1]))
            vel = np.array(joint_info.get("velocity", [0, 0, 0]))
            
            # 计算加速度
            prev_vel = self.previous_velocities.get(joint_name, np.zeros(3))
            acceleration = vel - prev_vel
            
            self.joints[joint_name].position = pos
            self.joints[joint_name].rotation = rot
            self.joints[joint_name].velocity = vel
            self.joints[joint_name].acceleration = acceleration
            
            self.previous_positions[joint_name] = pos.copy()
            self.previous_velocities[joint_name] = vel.copy()
        
        return self.get_skeleton_data()
    
    def get_skeleton_data(self) -> SkeletonData:
        """获取骨架数据对象"""
        return SkeletonData(
            frame_number=self.frame_number,
            timestamp=self.timestamp,
            joints={name: joint for name, joint in self.joints.items()},
        )
    
    def get_joint_position(self, joint_name: str) -> np.ndarray:
        """获取关节位置"""
        joint = self.joints.get(joint_name)
        return joint.position if joint else np.zeros(3)
    
    def get_joint_rotation(self, joint_name: str) -> np.ndarray:
        """获取关节旋转（四元数）"""
        joint = self.joints.get(joint_name)
        return joint.rotation if joint else np.array([0, 0, 0, 1])
    
    def get_joint_velocity(self, joint_name: str) -> np.ndarray:
        """获取关节速度"""
        joint = self.joints.get(joint_name)
        return joint.velocity if joint else np.zeros(3)
    
    def get_end_effectors(self) -> dict[str, np.ndarray]:
        """获取末端效应器位置"""
        return {
            "head": self.get_joint_position("head"),
            "hand_l": self.get_joint_position("hand_l"),
            "hand_r": self.get_joint_position("hand_r"),
            "foot_l": self.get_joint_position("foot_l"),
            "foot_r": self.get_joint_position("foot_r"),
        }
    
    def get_trajectory(self, joint_name: str, num_frames: int = 60) -> np.ndarray:
        """获取关节轨迹（需要外部存储历史数据）"""
        # 简化版本，返回当前位置
        return self.get_joint_position(joint_name)
    
    def center_on_pelvis(self) -> None:
        """以骨盆为中心"""
        pelvis_pos = self.get_joint_position("pelvis")
        for joint in self.joints.values():
            joint.position = joint.position - pelvis_pos
    
    def scale_to_height(self, target_height: float = 1.7) -> None:
        """缩放到目标身高"""
        current_height = self.get_joint_position("head")[1] - self.get_joint_position("pelvis")[1]
        if current_height > 0:
            scale = target_height / current_height
            pelvis_pos = self.get_joint_position("pelvis")
            for joint in self.joints.values():
                joint.position = (joint.position - pelvis_pos) * scale + pelvis_pos


def create_standard_skeleton() -> RealtimeSkeleton:
    """创建标准骨架"""
    return RealtimeSkeleton()


if __name__ == "__main__":
    # 测试代码
    print("测试实时骨架...")
    
    skeleton = create_standard_skeleton()
    
    # 模拟帧数据
    from opera_mocap_tool.realtime.vicon_client import ViconFrame
    
    frame = ViconFrame(
        frame_number=1,
        timestamp=0.0,
        subjects={
            "Actor1": {
                "bones": {
                    "Head": {"position": (0, 1.6, 0), "rotation": (0, 0, 0, 1)},
                    "Pelvis": {"position": (0, 1.0, 0), "rotation": (0, 0, 0, 1)},
                    "LeftHand": {"position": (-0.3, 1.2, 0.1), "rotation": (0, 0, 0, 1)},
                    "RightHand": {"position": (0.3, 1.2, 0.1), "rotation": (0, 0, 0, 1)},
                },
                "markers": {},
            }
        }
    )
    
    skeleton.update(frame)
    
    print(f"头部位置: {skeleton.get_joint_position('head')}")
    print(f"左手位置: {skeleton.get_joint_position('hand_l')}")
    print(f"骨盆位置: {skeleton.get_joint_position('pelvis')}")
    
    # 导出为数组
    arr = skeleton.get_skeleton_data().to_array()
    print(f"骨架数组形状: {arr.shape}")
    
    print("测试完成")
