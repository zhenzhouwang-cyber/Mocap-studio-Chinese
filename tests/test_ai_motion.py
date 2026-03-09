"""
AI动作生成模块单元测试。

测试基于深度学习的京剧动作生成核心功能。
"""

import json
import tempfile
from pathlib import Path

import numpy as np
import pytest

# 导入被测试模块
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from opera_mocap_tool.commercial.ai_motion import (
    MotionDataType,
    MotionSequence,
    TrainingConfig,
    MotionPreprocessor,
)


class TestMotionDataType:
    """动作数据类型枚举测试"""

    def test_data_type_values(self):
        """测试数据类型枚举值"""
        assert MotionDataType.BVH.value == "bvh"
        assert MotionDataType.C3D.value == "c3d"
        assert MotionDataType.FBX.value == "fbx"
        assert MotionDataType.CSV.value == "csv"
        assert MotionDataType.JSON.value == "json"

    def test_data_type_count(self):
        """测试数据类型数量"""
        assert len(MotionDataType) == 5


class TestMotionSequence:
    """动作序列测试"""

    def test_sequence_creation(self):
        """测试序列创建"""
        frames = np.random.randn(100, 22, 3)  # 100帧, 22关节, 3维
        sequence = MotionSequence(
            frames=frames,
            frame_rate=30.0,
            skeleton="opera_standard",
        )
        
        assert sequence.num_frames == 100
        assert sequence.num_joints == 22
        assert sequence.frame_rate == 30.0

    def test_sequence_2d_frames(self):
        """测试2D帧自动转换为3D"""
        frames = np.random.randn(50, 22, 3)  # 已经是3D
        sequence = MotionSequence(frames=frames)
        
        assert sequence.frames.ndim == 3

    def test_sequence_properties(self):
        """测试序列属性"""
        frames = np.random.randn(60, 20, 3)
        sequence = MotionSequence(frames=frames)
        
        assert sequence.num_frames == 60
        assert sequence.num_joints == 20

    def test_sequence_to_tensor(self):
        """测试转换为张量"""
        frames = np.random.randn(30, 22, 3)
        sequence = MotionSequence(frames=frames)
        
        tensor = sequence.to_tensor()
        
        assert tensor.dtype == np.float32
        assert tensor.shape[0] == 30

    def test_sequence_velocity(self):
        """测试速度计算"""
        # 创建有速度的序列
        frames = np.zeros((10, 3, 3))
        frames[1:, :, 0] = 1.0  # x方向移动
        
        sequence = MotionSequence(frames=frames)
        velocity = sequence.get_velocity()
        
        assert velocity.shape == sequence.frames.shape

    def test_sequence_acceleration(self):
        """测试加速度计算"""
        frames = np.zeros((10, 3, 3))
        sequence = MotionSequence(frames=frames)
        
        acceleration = sequence.get_acceleration()
        
        assert acceleration.shape == sequence.frames.shape

    def test_sequence_metadata(self):
        """测试元数据"""
        frames = np.random.randn(30, 22, 3)
        sequence = MotionSequence(
            frames=frames,
            dang="sheng",
            action_name="cloud_hand",
            dancer_id="test_001",
        )
        
        assert sequence.dang == "sheng"
        assert sequence.action_name == "cloud_hand"
        assert sequence.dancer_id == "test_001"


class TestTrainingConfig:
    """训练配置测试"""

    def test_config_default(self):
        """测试默认配置"""
        config = TrainingConfig()
        
        assert config.hidden_dim == 256
        assert config.num_layers == 4
        assert config.num_heads == 8
        assert config.dropout == 0.1
        assert config.batch_size == 32
        assert config.learning_rate == 1e-4
        assert config.num_epochs == 100

    def test_config_custom(self):
        """测试自定义配置"""
        config = TrainingConfig(
            hidden_dim=512,
            num_layers=6,
            batch_size=64,
            device="cpu",
        )
        
        assert config.hidden_dim == 512
        assert config.num_layers == 6
        assert config.batch_size == 64
        assert config.device == "cpu"

    def test_config_data_augmentation(self):
        """测试数据增强配置"""
        config = TrainingConfig(
            augment_rotation=True,
            augment_scale=True,
            augment_noise=0.02,
        )
        
        assert config.augment_rotation is True
        assert config.augment_scale is True
        assert config.augment_noise == 0.02


class TestMotionPreprocessor:
    """动作预处理器测试"""

    def test_preprocessor_creation(self):
        """测试预处理器创建"""
        preprocessor = MotionPreprocessor(target_framerate=30.0)
        
        assert preprocessor.target_framerate == 30.0
        assert len(preprocessor.joint_mapping) > 0

    def test_standard_joints(self):
        """测试标准关节定义"""
        preprocessor = MotionPreprocessor()
        
        assert "pelvis" in preprocessor.joint_mapping
        assert "head" in preprocessor.joint_mapping
        assert "hand_l" in preprocessor.joint_mapping
        assert "hand_r" in preprocessor.joint_mapping
        assert "foot_l" in preprocessor.joint_mapping
        assert "foot_r" in preprocessor.joint_mapping

    def test_resample_same_framerate(self):
        """测试相同帧率不重采样"""
        preprocessor = MotionPreprocessor(target_framerate=30.0)
        
        frames = np.random.randn(30, 22, 3)
        sequence = MotionSequence(frames=frames, frame_rate=30.0)
        
        resampled = preprocessor.resample(sequence)
        
        assert resampled.num_frames == 30

    def test_resample_upscale(self):
        """测试升采样"""
        preprocessor = MotionPreprocessor(target_framerate=60.0)
        
        frames = np.random.randn(30, 22, 3)
        sequence = MotionSequence(frames=frames, frame_rate=30.0)
        
        resampled = preprocessor.resample(sequence)
        
        # 应该增加到约60帧
        assert resampled.num_frames >= 30

    def test_resample_downscale(self):
        """测试降采样"""
        preprocessor = MotionPreprocessor(target_framerate=15.0)
        
        frames = np.random.randn(60, 22, 3)
        sequence = MotionSequence(frames=frames, frame_rate=60.0)
        
        resampled = preprocessor.resample(sequence)
        
        # 应该减少到约15帧
        assert resampled.num_frames <= 60

    def test_normalize(self):
        """测试标准化"""
        preprocessor = MotionPreprocessor()
        
        frames = np.random.randn(30, 22, 3) * 2 + 1
        sequence = MotionSequence(frames=frames)
        
        normalized = preprocessor.normalize(sequence)
        
        # 验证归一化后数据在合理范围
        assert normalized.frames.shape == sequence.frames.shape
        assert "normalization_scale" in normalized.metadata

    def test_normalize_center_on_pelvis(self):
        """测试以骨盆为中心"""
        preprocessor = MotionPreprocessor()
        
        frames = np.random.randn(30, 22, 3) + np.array([1, 1, 1])
        sequence = MotionSequence(frames=frames)
        
        normalized = preprocessor.normalize(sequence)
        
        # 骨盆位置应该接近原点
        pelvis = normalized.frames[:, 0:1, :]
        assert np.abs(pelvis.mean()) < 0.1

    def test_augment_rotation(self):
        """测试旋转增强"""
        preprocessor = MotionPreprocessor()
        
        frames = np.random.randn(30, 5, 3)
        sequence = MotionSequence(frames=frames)
        
        augmented = preprocessor.augment(sequence, rotation=True, scale=False, noise=0.0)
        
        # 应该有额外的旋转版本
        assert len(augmented) > 1
        assert any("rotation" in m.get("augmentation", "") for m in [seq.metadata for seq in augmented])

    def test_augment_scale(self):
        """测试缩放增强"""
        preprocessor = MotionPreprocessor()
        
        frames = np.random.randn(30, 5, 3)
        sequence = MotionSequence(frames=frames)
        
        augmented = preprocessor.augment(sequence, rotation=False, scale=True, noise=0.0)
        
        # 应该有额外的缩放版本
        assert len(augmented) > 1
        assert any("scale" in m.get("augmentation", "") for m in [seq.metadata for seq in augmented])

    def test_augment_noise(self):
        """测试噪声增强"""
        preprocessor = MotionPreprocessor()
        
        frames = np.random.randn(30, 5, 3)
        sequence = MotionSequence(frames=frames)
        
        augmented = preprocessor.augment(sequence, rotation=False, scale=False, noise=0.01)
        
        # 应该有额外的噪声版本
        assert len(augmented) > 1

    def test_augment_all(self):
        """测试全部增强"""
        preprocessor = MotionPreprocessor()
        
        frames = np.random.randn(30, 5, 3)
        sequence = MotionSequence(frames=frames)
        
        augmented = preprocessor.augment(sequence, rotation=True, scale=True, noise=0.01)
        
        # 应该有很多增强版本
        assert len(augmented) > 3


class TestMotionPreprocessorInterpolation:
    """插值测试"""

    def test_interpolate_3d(self):
        """测试3D数据插值"""
        preprocessor = MotionPreprocessor()
        
        data = np.random.randn(10, 5, 3)
        indices = np.array([0, 2, 4, 6, 8])
        
        result = preprocessor._interpolate(data, indices)
        
        assert result.shape[0] == 5
        assert result.shape[1] == 5
        assert result.shape[2] == 3


class TestMotionSequenceResample:
    """序列重采样测试"""

    def test_resample_preserves_metadata(self):
        """测试重采样保留元数据"""
        preprocessor = MotionPreprocessor(target_framerate=30.0)
        
        frames = np.random.randn(30, 22, 3)
        sequence = MotionSequence(
            frames=frames,
            frame_rate=60.0,
            dang="dan",
            action_name="sleeve_wave",
        )
        
        resampled = preprocessor.resample(sequence)
        
        assert resampled.dang == "dan"
        assert resampled.action_name == "sleeve_wave"
        assert resampled.frame_rate == 30.0


class TestMotionSequenceNormalization:
    """序列标准化测试"""

    def test_normalize_zero_scale(self):
        """测试零尺度情况"""
        preprocessor = MotionPreprocessor()
        
        # 所有点相同
        frames = np.ones((10, 5, 3))
        sequence = MotionSequence(frames=frames)
        
        normalized = preprocessor.normalize(sequence)
        
        # 不应该崩溃，尺度为0时保持原样
        assert normalized.frames.shape == sequence.frames.shape


class TestMotionPreprocessorRoundTrip:
    """预处理器往返测试"""

    def test_normalize_denormalize(self):
        """测试标准化后再反标准化"""
        preprocessor = MotionPreprocessor()
        
        frames = np.random.randn(30, 5, 3) * 2 + 5
        sequence = MotionSequence(frames=frames)
        
        # 保存原始尺度
        original_scale = sequence.frames.copy()
        
        normalized = preprocessor.normalize(sequence)
        
        # 验证数据范围改变
        assert np.abs(normalized.frames).max() <= 1.0


class TestMotionSequencePhysics:
    """动作物理测试"""

    def test_velocity_zero_frames(self):
        """测试零帧速度"""
        frames = np.random.randn(1, 5, 3)
        sequence = MotionSequence(frames=frames)
        
        velocity = sequence.get_velocity()
        
        assert velocity.shape == sequence.frames.shape

    def test_acceleration_few_frames(self):
        """测试少帧加速度"""
        frames = np.random.randn(2, 5, 3)
        sequence = MotionSequence(frames=frames)
        
        acceleration = sequence.get_acceleration()
        
        assert acceleration.shape == sequence.frames.shape


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
