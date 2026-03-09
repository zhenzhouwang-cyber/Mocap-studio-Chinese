#!/usr/bin/env python
"""
AI动作生成示例。

展示如何使用商业模块进行动作数据预处理和AI模型训练。

运行方式:
    python examples/ai_motion_demo.py
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
from opera_mocap_tool.commercial.ai_motion import (
    MotionDataType,
    MotionSequence,
    TrainingConfig,
    MotionPreprocessor,
)


def demo_motion_sequence():
    """演示动作序列创建"""
    print("=" * 60)
    print("演示动作序列创建")
    print("=" * 60)

    # 创建随机动作数据
    np.random.seed(42)
    frames = np.random.randn(100, 22, 3)

    # 创建动作序列
    sequence = MotionSequence(
        frames=frames,
        frame_rate=30.0,
        skeleton="opera_standard",
    )

    print(f"\n动作序列信息:")
    print(f"  - 帧数: {sequence.num_frames}")
    print(f"  - 关节数: {sequence.num_joints}")
    print(f"  - 帧率: {sequence.frame_rate}")
    print(f"  - 骨架: {sequence.skeleton}")

    # 创建带元数据的序列
    sequence2 = MotionSequence(
        frames=frames,
        frame_rate=30.0,
        dang="sheng",
        action_name="cloud_hand",
        dancer_id="performer_001",
    )

    print(f"\n带元数据的序列:")
    print(f"  - 行当: {sequence2.dang}")
    print(f"  - 动作: {sequence2.action_name}")
    print(f"  - 舞者: {sequence2.dancer_id}")


def demo_sequence_properties():
    """演示动作序列属性"""
    print("\n" + "=" * 60)
    print("演示动作序列属性")
    print("=" * 60)

    # 创建有规律的数据
    frames = np.zeros((50, 5, 3))
    frames[1:, :, 0] = 1.0  # x方向移动
    frames[2:, :, 1] = 0.5  # y方向移动

    sequence = MotionSequence(frames=frames)

    print(f"\n原始数据形状: {sequence.frames.shape}")

    # 转换为张量
    tensor = sequence.to_tensor()
    print(f"张量形状: {tensor.shape}")
    print(f"张量类型: {tensor.dtype}")

    # 计算速度
    velocity = sequence.get_velocity()
    print(f"速度形状: {velocity.shape}")

    # 计算加速度
    acceleration = sequence.get_acceleration()
    print(f"加速度形状: {acceleration.shape}")


def demo_preprocessor():
    """演示预处理器"""
    print("\n" + "=" * 60)
    print("演示预处理器")
    print("=" * 60)

    # 创建预处理器
    preprocessor = MotionPreprocessor(target_framerate=30.0)

    print(f"\n预处理器配置:")
    print(f"  - 目标帧率: {preprocessor.target_framerate}")
    print(f"  - 关节映射数: {len(preprocessor.joint_mapping)}")

    # 显示标准关节
    print(f"\n标准关节列表:")
    joints = list(preprocessor.joint_mapping.keys())[:10]
    for joint in joints:
        print(f"  - {joint}")


def demo_resampling():
    """演示重采样"""
    print("\n" + "=" * 60)
    print("演示重采样")
    print("=" * 60)

    # 创建30fps的序列
    frames = np.random.randn(60, 22, 3)
    sequence = MotionSequence(frames=frames, frame_rate=30.0)

    print(f"\n原始序列: {sequence.num_frames} 帧 @ {sequence.frame_rate}fps")

    # 升采样到60fps
    preprocessor_60 = MotionPreprocessor(target_framerate=60.0)
    resampled_60 = preprocessor_60.resample(sequence)
    print(f"升采样后: {resampled_60.num_frames} 帧 @ {resampled_60.frame_rate}fps")

    # 降采样到15fps
    preprocessor_15 = MotionPreprocessor(target_framerate=15.0)
    resampled_15 = preprocessor_15.resample(sequence)
    print(f"降采样后: {resampled_15.num_frames} 帧 @ {resampled_15.frame_rate}fps")


def demo_normalization():
    """演示标准化"""
    print("\n" + "=" * 60)
    print("演示标准化")
    print("=" * 60)

    # 创建数据
    frames = np.random.randn(30, 22, 3) * 2 + 5  # 偏移的数据
    sequence = MotionSequence(frames=frames)

    print(f"\n原始数据范围:")
    print(f"  - min: {frames.min():.2f}")
    print(f"  - max: {frames.max():.2f}")
    print(f"  - mean: {frames.mean():.2f}")

    # 标准化
    preprocessor = MotionPreprocessor()
    normalized = preprocessor.normalize(sequence)

    print(f"\n标准化后数据范围:")
    print(f"  - min: {normalized.frames.min():.2f}")
    print(f"  - max: {normalized.frames.max():.2f}")
    print(f"  - mean: {normalized.frames.mean():.2f}")

    print(f"\n归一化尺度: {normalized.metadata.get('normalization_scale')}")


def demo_augmentation():
    """演示数据增强"""
    print("\n" + "=" * 60)
    print("演示数据增强")
    print("=" * 60)

    # 创建样本数据
    frames = np.random.randn(30, 5, 3)
    sequence = MotionSequence(frames=frames)

    preprocessor = MotionPreprocessor()

    # 旋转增强
    augmented_rotation = preprocessor.augment(
        sequence,
        rotation=True,
        scale=False,
        noise=0.0,
    )
    print(f"\n旋转增强: {len(augmented_rotation)} 样本")

    # 缩放增强
    augmented_scale = preprocessor.augment(
        sequence,
        rotation=False,
        scale=True,
        noise=0.0,
    )
    print(f"缩放增强: {len(augmented_scale)} 样本")

    # 噪声增强
    augmented_noise = preprocessor.augment(
        sequence,
        rotation=False,
        scale=False,
        noise=0.01,
    )
    print(f"噪声增强: {len(augmented_noise)} 样本")

    # 全部增强
    augmented_all = preprocessor.augment(
        sequence,
        rotation=True,
        scale=True,
        noise=0.01,
    )
    print(f"全部增强: {len(augmented_all)} 样本")

    # 显示元数据
    print(f"\n增强元数据示例:")
    for i, seq in enumerate(augmented_all[:3]):
        aug_type = seq.metadata.get("augmentation", "original")
        print(f"  - 样本{i+1}: {aug_type}")


def demo_training_config():
    """演示训练配置"""
    print("\n" + "=" * 60)
    print("演示训练配置")
    print("=" * 60)

    # 默认配置
    config = TrainingConfig()

    print(f"\n默认训练配置:")
    print(f"  - hidden_dim: {config.hidden_dim}")
    print(f"  - num_layers: {config.num_layers}")
    print(f"  - num_heads: {config.num_heads}")
    print(f"  - dropout: {config.dropout}")
    print(f"  - batch_size: {config.batch_size}")
    print(f"  - learning_rate: {config.learning_rate}")
    print(f"  - num_epochs: {config.num_epochs}")

    # 自定义配置
    config_custom = TrainingConfig(
        hidden_dim=512,
        num_layers=6,
        num_heads=8,
        dropout=0.2,
        batch_size=64,
        learning_rate=5e-5,
        num_epochs=200,
        augment_rotation=True,
        augment_scale=True,
        augment_noise=0.02,
        device="cuda",
    )

    print(f"\n自定义训练配置:")
    print(f"  - hidden_dim: {config_custom.hidden_dim}")
    print(f"  - num_layers: {config_custom.num_layers}")
    print(f"  - batch_size: {config_custom.batch_size}")
    print(f"  - device: {config_custom.device}")


def demo_data_pipeline():
    """演示完整的数据处理流程"""
    print("\n" + "=" * 60)
    print("演示完整数据处理流程")
    print("=" * 60)

    # 1. 生成样本数据
    np.random.seed(42)
    sequences = []
    for i in range(10):
        frames = np.random.randn(60, 22, 3)
        seq = MotionSequence(
            frames=frames,
            frame_rate=30.0,
            dang=["sheng", "dan", "jing", "chou"][i % 4],
            action_name=f"action_{i}",
        )
        sequences.append(seq)

    print(f"\n1. 生成了 {len(sequences)} 个样本序列")

    # 2. 创建预处理器
    preprocessor = MotionPreprocessor(target_framerate=30.0)
    print(f"2. 创建预处理器 (目标帧率: {preprocessor.target_framerate})")

    # 3. 预处理所有序列
    processed = []
    for seq in sequences:
        # 重采样
        resampled = preprocessor.resample(seq)
        # 标准化
        normalized = preprocessor.normalize(resampled)
        processed.append(normalized)

    print(f"3. 预处理完成: {len(processed)} 序列")

    # 4. 数据增强
    augmented = []
    for seq in processed:
        aug = preprocessor.augment(
            seq,
            rotation=True,
            scale=True,
            noise=0.01,
        )
        augmented.extend(aug)

    print(f"4. 数据增强后: {len(augmented)} 序列")

    # 5. 统计
    print(f"\n最终数据集统计:")
    print(f"  - 原始样本: {len(sequences)}")
    print(f"  - 增强后: {len(augmented)}")
    print(f"  - 增强倍数: {len(augmented)/len(sequences):.1f}x")


def main():
    """主函数"""
    print("\n" + "#" * 60)
    print("# AI动作生成演示")
    print("#" * 60 + "\n")

    # 运行所有演示
    demo_motion_sequence()
    demo_sequence_properties()
    demo_preprocessor()
    demo_resampling()
    demo_normalization()
    demo_augmentation()
    demo_training_config()
    demo_data_pipeline()

    print("\n" + "=" * 60)
    print("演示完成！")
    print("=" * 60)
    print("""
使用说明:
1. 使用MotionSequence创建动作数据
2. 使用MotionPreprocessor进行预处理
3. 使用数据增强扩充训练集
4. 使用TrainingConfig配置训练参数

注意: 完整的神经网络训练需要安装PyTorch:
    pip install torch torchvision

更多信息请查看:
  docs/commercial/ai_motion_guide.md
""")


if __name__ == "__main__":
    main()
