# AI动作生成使用指南

基于深度学习的京剧动作生成 - VAE模型与风格迁移

## 概述

AI动作生成模块提供基于深度学习的京剧动作生成功能，包括：
- 动作数据预处理（重采样、归一化）
- 数据增强（旋转、缩放、噪声）
- VAE模型训练与推理
- 风格迁移（现代舞/芭蕾 → 京剧身段）
- 动作插值与生成

## 安装依赖

```bash
pip install numpy scipy scikit-learn
# 可选（完整功能）
pip install torch torchvision
```

## 快速开始

### 基本用法

```python
import numpy as np
from opera_mocap_tool.commercial.ai_motion import (
    MotionSequence,
    MotionPreprocessor,
    TrainingConfig,
)

# 1. 创建动作序列
frames = np.random.randn(100, 22, 3)  # 100帧, 22关节, 3维坐标
sequence = MotionSequence(
    frames=frames,
    frame_rate=30.0,
    dang="sheng",
    action_name="cloud_hand",
)

# 2. 创建预处理器
preprocessor = MotionPreprocessor(target_framerate=30.0)

# 3. 预处理
resampled = preprocessor.resample(sequence)
normalized = preprocessor.normalize(resampled)

# 4. 数据增强
augmented = preprocessor.augment(
    normalized,
    rotation=True,
    scale=True,
    noise=0.01,
)
```

## 动作序列

### 创建动作序列

```python
import numpy as np
from opera_mocap_tool.commercial.ai_motion import MotionSequence

# 从numpy数组创建
frames = np.random.randn(100, 22, 3)
sequence = MotionSequence(
    frames=frames,
    frame_rate=30.0,
    skeleton="opera_standard",
)

# 包含元数据
sequence = MotionSequence(
    frames=frames,
    frame_rate=60.0,
    dang="dan",           # 行当
    action_name="sleeve_wave",  # 动作名称
    dancer_id="performer_001",  # 舞者ID
)
```

### 动作序列属性

```python
# 帧数和关节数
print(sequence.num_frames)  # 100
print(sequence.num_joints)  # 22

# 转换为模型输入
tensor = sequence.to_tensor()
print(tensor.shape)  # (100, 22, 3)

# 计算速度
velocity = sequence.get_velocity()
print(velocity.shape)  # (100, 22, 3)

# 计算加速度
acceleration = sequence.get_acceleration()
print(acceleration.shape)  # (100, 22, 3)
```

## 预处理器

### 创建预处理器

```python
from opera_mocap_tool.commercial.ai_motion import MotionPreprocessor

# 默认参数
preprocessor = MotionPreprocessor()

# 自定义参数
preprocessor = MotionPreprocessor(target_framerate=30.0)
```

### 重采样

```python
# 升采样 (30fps -> 60fps)
preprocessor = MotionPreprocessor(target_framerate=60.0)
resampled = preprocessor.resample(sequence)

# 降采样 (60fps -> 30fps)
preprocessor = MotionPreprocessor(target_framerate=30.0)
resampled = preprocessor.resample(sequence)
```

### 标准化

```python
# 归一化（以骨盆为中心，缩放到[-1, 1]）
normalized = preprocessor.normalize(sequence)

# 获取归一化参数
scale = normalized.metadata.get("normalization_scale")
```

### 数据增强

```python
# 旋转增强
augmented = preprocessor.augment(
    sequence,
    rotation=True,
    scale=False,
    noise=0.0,
)

# 缩放增强
augmented = preprocessor.augment(
    sequence,
    rotation=False,
    scale=True,
    noise=0.0,
)

# 噪声增强
augmented = preprocessor.augment(
    sequence,
    rotation=False,
    scale=False,
    noise=0.01,
)

# 全部增强
augmented = preprocessor.augment(
    sequence,
    rotation=True,
    scale=True,
    noise=0.01,
)
```

## 训练配置

### 配置参数

```python
from opera_mocap_tool.commercial.ai_motion import TrainingConfig

# 默认配置
config = TrainingConfig()

# 自定义配置
config = TrainingConfig(
    # 模型参数
    hidden_dim=256,
    num_layers=4,
    num_heads=8,
    dropout=0.1,
    
    # 训练参数
    batch_size=32,
    learning_rate=1e-4,
    num_epochs=100,
    validation_split=0.2,
    
    # 数据增强
    augment_rotation=True,
    augment_scale=True,
    augment_noise=0.01,
    
    # 其他
    checkpoint_dir="./checkpoints",
    log_dir="./logs",
    device="cuda",
)
```

## 神经网络模型

> 注意：需要安装PyTorch才能使用神经网络功能。

### 模型架构

```python
from opera_mocap_tool.commercial.ai_motion import (
    OperaMotionVAE,
    StyleTransferModel,
    TrainingConfig,
)
import torch

config = TrainingConfig(hidden_dim=256, num_layers=4)

# 创建VAE模型
model = OperaMotionVAE(
    input_dim=3,
    hidden_dim=config.hidden_dim,
    latent_dim=128,
    num_layers=config.num_layers,
    num_heads=config.num_heads,
    dropout=config.dropout,
)

# 移动到设备
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model = model.to(device)
```

### 编码与解码

```python
# 准备输入
input_tensor = torch.randn(8, 60, 22, 3).to(device)  # B, T, J, C

# 编码
mu, logvar = model.encode(input_tensor)
print(mu.shape)  # (8, 128)

# 重参数化
z = model.reparameterize(mu, logvar)
print(z.shape)  # (8, 128)

# 解码
output = model.decode(z, target_length=60)
print(output.shape)  # (8, 60, 22, 3)
```

## 动作生成器

### 创建生成器

```python
from opera_mocap_tool.commercial.ai_motion import MotionGenerator

generator = MotionGenerator(
    model=model,
    preprocessor=preprocessor,
    device="cuda",
)
```

### 从种子序列生成

```python
# 创建种子序列
seed_frames = np.random.randn(30, 22, 3)
seed_sequence = MotionSequence(
    frames=seed_frames,
    frame_rate=30.0,
)

# 生成新动作
generated = generator.generate(
    seed_sequence=seed_sequence,
    target_length=60,
    temperature=1.0,
)
```

### 动作插值

```python
# 两个动作序列之间的插值
interpolated = generator.interpolate(
    sequence1=seq1,
    sequence2=seq2,
    alpha=0.5,  # 0=seq1, 1=seq2
)
```

## 训练器

### 创建训练器

```python
from opera_mocap_tool.commercial.ai_motion import (
    MotionTrainer,
    MotionDataset,
    TrainingConfig,
)

# 创建数据集
dataset = MotionDataset(
    sequences=train_sequences,
    sequence_length=60,
)

# 创建验证集
val_dataset = MotionDataset(
    sequences=val_sequences,
    sequence_length=60,
)

# 创建训练器
trainer = MotionTrainer(
    model=model,
    config=config,
    train_dataset=dataset,
    val_dataset=val_dataset,
)
```

### 训练模型

```python
# 开始训练
history = trainer.train()

# 查看训练历史
print(history["train_loss"])
print(history["val_loss"])

# 保存检查点
trainer.save_checkpoint("final_model.pt")

# 加载检查点
trainer.load_checkpoint("final_model.pt")
```

## 完整示例

### 训练VAE模型

```python
import numpy as np
import torch
from pathlib import Path
from opera_mocap_tool.commercial.ai_motion import (
    MotionSequence,
    MotionPreprocessor,
    MotionDataset,
    OperaMotionVAE,
    MotionTrainer,
    TrainingConfig,
)

# 1. 准备数据
np.random.seed(42)
sequences = []
for _ in range(100):
    frames = np.random.randn(60, 22, 3)
    seq = MotionSequence(
        frames=frames,
        frame_rate=30.0,
        dang="sheng",
    )
    sequences.append(seq)

# 2. 预处理
preprocessor = MotionPreprocessor(target_framerate=30.0)
processed = []
for seq in sequences:
    normalized = preprocessor.normalize(seq)
    processed.append(normalized)

# 3. 划分数据集
train_data = processed[:80]
val_data = processed[20:]

train_dataset = MotionDataset(train_data, sequence_length=60)
val_dataset = MotionDataset(val_data, sequence_length=60)

# 4. 创建模型
config = TrainingConfig(
    hidden_dim=128,
    num_layers=2,
    batch_size=16,
    num_epochs=10,
    device="cuda" if torch.cuda.is_available() else "cpu",
)

model = OperaMotionVAE(
    input_dim=3,
    hidden_dim=config.hidden_dim,
    latent_dim=64,
    num_layers=config.num_layers,
)

# 5. 训练
trainer = MotionTrainer(
    model=model,
    config=config,
    train_dataset=train_dataset,
    val_dataset=val_dataset,
)

history = trainer.train()
print("训练完成！")
```

### 生成新动作

```python
import numpy as np
from opera_mocap_tool.commercial.ai_motion import (
    MotionSequence,
    MotionPreprocessor,
    OperaMotionVAE,
    MotionGenerator,
)
import torch

# 加载模型
model = OperaMotionVAE(input_dim=3, hidden_dim=128, latent_dim=64)
checkpoint = torch.load("checkpoints/best_model.pt")
model.load_state_dict(checkpoint["model_state_dict"])
model.eval()

# 创建生成器
preprocessor = MotionPreprocessor()
generator = MotionGenerator(model=model, preprocessor=preprocessor)

# 创建种子序列
seed_frames = np.random.randn(30, 22, 3)
seed = MotionSequence(frames=seed_frames)

# 生成
generated = generator.generate(seed, target_length=60)
print(f"生成动作: {generated.num_frames} 帧")
```

## 常见问题

### Q: 内存不足？
A: 减小 `batch_size` 和 `sequence_length`。

### Q: 训练不稳定？
A: 调整 `learning_rate`，或使用学习率调度器。

### Q: 生成的动作不自然？
A: 调整 `temperature` 参数，较低的值产生更保守的结果。

### Q: PyTorch未安装？
A: 模块会检测到PyTorch不可用并提供基础功能，但神经网络功能不可用。

## 相关文档

- [TD粒子系统指南](./td_particles_guide.md)
- [Blender绑定指南](./blender_rig_guide.md)
