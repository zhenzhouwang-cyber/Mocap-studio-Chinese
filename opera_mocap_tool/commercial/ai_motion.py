"""
AI动作生成模块。

闭源商业模块 - 基于深度学习的京剧动作生成

包含：
- 动作数据预处理管道
- 神经网络架构（编码器/解码器/Transformer）
- 训练与推理接口
- 风格迁移模块

依赖：PyTorch, NumPy, Scikit-learn
"""

from __future__ import annotations

import json
import pickle
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

import numpy as np


# ============================================================================
# 数据类型定义
# ============================================================================

class MotionDataType(Enum):
    """动作数据类型"""
    BVH = "bvh"
    C3D = "c3d"
    FBX = "fbx"
    CSV = "csv"
    JSON = "json"


@dataclass
class MotionSequence:
    """动作序列数据"""
    frames: np.ndarray                          # (T, J, 3) 位置数据
    rotations: np.ndarray | None = None         # (T, J, 4) 四元数旋转
    timestamps: np.ndarray | None = None       # (T,) 时间戳
    frame_rate: float = 30.0                    # 帧率
    skeleton: str = "opera_standard"            # 骨架类型
    
    # 元数据
    dang: str = ""                              # 行当
    action_name: str = ""                        # 动作名称
    dancer_id: str = ""                         # 舞者ID
    metadata: dict = field(default_factory=dict)
    
    def __post_init__(self):
        """验证数据"""
        if self.frames.ndim == 2:
            self.frames = self.frames[np.newaxis, :, :]
    
    @property
    def num_frames(self) -> int:
        return self.frames.shape[0]
    
    @property
    def num_joints(self) -> int:
        return self.frames.shape[1] if self.frames.ndim >= 2 else 0
    
    def to_tensor(self) -> np.ndarray:
        """转换为模型输入张量"""
        data = self.frames.copy()
        
        # 归一化
        data = (data - data.mean(axis=0, keepdims=True)) / (data.std(axis=0, keepdims=True) + 1e-8)
        
        return data.astype(np.float32)
    
    def get_velocity(self) -> np.ndarray:
        """计算速度"""
        if self.num_frames < 2:
            return np.zeros_like(self.frames)
        
        velocity = np.diff(self.frames, axis=0)
        # 最后一帧用0填充
        velocity = np.concatenate([velocity, velocity[-1:]], axis=0)
        
        return velocity
    
    def get_acceleration(self) -> np.ndarray:
        """计算加速度"""
        if self.num_frames < 3:
            return np.zeros_like(self.frames)
        
        velocity = self.get_velocity()
        acceleration = np.diff(velocity, axis=0)
        acceleration = np.concatenate([acceleration, acceleration[-1:]], axis=0)
        
        return acceleration


@dataclass
class TrainingConfig:
    """训练配置"""
    # 模型参数
    hidden_dim: int = 256
    num_layers: int = 4
    num_heads: int = 8
    dropout: float = 0.1
    
    # 训练参数
    batch_size: int = 32
    learning_rate: float = 1e-4
    num_epochs: int = 100
    validation_split: float = 0.2
    
    # 数据增强
    augment_rotation: bool = True
    augment_scale: bool = True
    augment_noise: float = 0.01
    
    # 其他
    checkpoint_dir: str = "./checkpoints"
    log_dir: str = "./logs"
    device: str = "cuda"


# ============================================================================
# 动作数据预处理
# ============================================================================

class MotionPreprocessor:
    """动作数据预处理器"""
    
    # 标准京剧骨架定义
    STANDARD_JOINTS = [
        "pelvis", "spine_base", "spine_mid", "spine_upper",
        "neck", "head",
        "shoulder_l", "upper_arm_l", "forearm_l", "hand_l",
        "shoulder_r", "upper_arm_r", "forearm_r", "hand_r",
        "hip_l", "thigh_l", "shin_l", "foot_l",
        "hip_r", "thigh_r", "shin_r", "foot_r",
    ]
    
    def __init__(self, target_framerate: float = 30.0):
        self.target_framerate = target_framerate
        self.joint_mapping: dict[str, int] = {}
        
        # 创建关节映射
        for i, joint in enumerate(self.STANDARD_JOINTS):
            self.joint_mapping[joint] = i
    
    def resample(self, sequence: MotionSequence) -> MotionSequence:
        """重采样到目标帧率"""
        if abs(sequence.frame_rate - self.target_framerate) < 0.01:
            return sequence
        
        # 计算缩放因子
        scale = self.target_framerate / sequence.frame_rate
        new_length = int(sequence.num_frames * scale)
        
        # 重采样
        indices = np.linspace(0, sequence.num_frames - 1, new_length)
        
        resampled_frames = self._interpolate(sequence.frames, indices)
        
        if sequence.rotations is not None:
            resampled_rotations = self._interpolate(sequence.rotations, indices)
        else:
            resampled_rotations = None
        
        if sequence.timestamps is not None:
            resampled_timestamps = np.interp(
                indices,
                np.arange(len(sequence.timestamps)),
                sequence.timestamps
            )
        else:
            resampled_timestamps = None
        
        return MotionSequence(
            frames=resampled_frames,
            rotations=resampled_rotations,
            timestamps=resampled_timestamps,
            frame_rate=self.target_framerate,
            skeleton=sequence.skeleton,
            dang=sequence.dang,
            action_name=sequence.action_name,
            dancer_id=sequence.dancer_id,
            metadata=sequence.metadata,
        )
    
    def _interpolate(self, data: np.ndarray, indices: np.ndarray) -> np.ndarray:
        """插值"""
        if data.ndim == 3:
            # (T, J, 3) 格式
            result = []
            for j in range(data.shape[1]):
                for k in range(data.shape[2]):
                    result.append(np.interp(indices, np.arange(data.shape[0]), data[:, j, k]))
            return np.stack(result, axis=1).reshape(-1, data.shape[1], data.shape[2])
        else:
            return np.interp(indices, np.arange(data.shape[0]), data)
    
    def normalize(self, sequence: MotionSequence) -> MotionSequence:
        """标准化"""
        # 中心化到骨盆
        pelvis = sequence.frames[:, 0:1, :]
        centered_frames = sequence.frames - pelvis
        
        # 归一化到[-1, 1]
        max_val = np.max(np.abs(centered_frames))
        if max_val > 1e-8:
            normalized_frames = centered_frames / max_val
        else:
            normalized_frames = centered_frames
        
        return MotionSequence(
            frames=normalized_frames,
            rotations=sequence.rotations,
            timestamps=sequence.timestamps,
            frame_rate=sequence.frame_rate,
            skeleton=sequence.skeleton,
            dang=sequence.dang,
            action_name=sequence.action_name,
            dancer_id=sequence.dancer_id,
            metadata={**sequence.metadata, "normalization_scale": max_val},
        )
    
    def augment(
        self,
        sequence: MotionSequence,
        rotation: bool = True,
        scale: bool = True,
        noise: float = 0.0,
    ) -> list[MotionSequence]:
        """数据增强"""
        augmented = [sequence]
        
        # 旋转增强
        if rotation:
            for angle in [90, 180, 270]:
                rotated = self._rotate(sequence, angle)
                rotated.metadata["augmentation"] = f"rotation_{angle}"
                augmented.append(rotated)
        
        # 缩放增强
        if scale:
            for scale_factor in [0.9, 1.1]:
                scaled = self._scale(sequence, scale_factor)
                scaled.metadata["augmentation"] = f"scale_{scale_factor}"
                augmented.append(scaled)
        
        # 噪声增强
        if noise > 0:
            noised = self._add_noise(sequence, noise)
            noised.metadata["augmentation"] = f"noise_{noise}"
            augmented.append(noised)
        
        return augmented
    
    def _rotate(self, sequence: MotionSequence, angle: float) -> MotionSequence:
        """绕Y轴旋转"""
        rad = np.radians(angle)
        cos_r, sin_r = np.cos(rad), np.sin(rad)
        rotation_matrix = np.array([
            [cos_r, 0, sin_r],
            [0, 1, 0],
            [-sin_r, 0, cos_r]
        ])
        
        # 旋转: 对每一帧的每个关节应用旋转矩阵
        # frames: (T,J,3) -> rotate each (3,) vector
        rotated_frames = np.zeros_like(sequence.frames)
        for t in range(sequence.frames.shape[0]):
            for j in range(sequence.frames.shape[1]):
                rotated_frames[t, j, :] = rotation_matrix @ sequence.frames[t, j, :]
        
        return MotionSequence(
            frames=rotated_frames,
            rotations=sequence.rotations,
            timestamps=sequence.timestamps,
            frame_rate=sequence.frame_rate,
            skeleton=sequence.skeleton,
            dang=sequence.dang,
            action_name=sequence.action_name,
            dancer_id=sequence.dancer_id,
            metadata=sequence.metadata.copy(),
        )
    
    def _scale(self, sequence: MotionSequence, scale_factor: float) -> MotionSequence:
        """缩放"""
        scaled_frames = sequence.frames * scale_factor
        
        return MotionSequence(
            frames=scaled_frames,
            rotations=sequence.rotations,
            timestamps=sequence.timestamps,
            frame_rate=sequence.frame_rate,
            skeleton=sequence.skeleton,
            dang=sequence.dang,
            action_name=sequence.action_name,
            dancer_id=sequence.dancer_id,
            metadata=sequence.metadata.copy(),
        )
    
    def _add_noise(self, sequence: MotionSequence, noise_level: float) -> MotionSequence:
        """添加噪声"""
        noise = np.random.randn(*sequence.frames.shape) * noise_level
        noised_frames = sequence.frames + noise
        
        return MotionSequence(
            frames=noised_frames,
            rotations=sequence.rotations,
            timestamps=sequence.timestamps,
            frame_rate=sequence.frame_rate,
            dang=sequence.dang,
            action_name=sequence.action_name,
            dancer_id=sequence.dancer_id,
            metadata=sequence.metadata.copy(),
        )


# ============================================================================
# 神经网络架构（PyTorch）
# ============================================================================

try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    from torch.utils.data import Dataset, DataLoader
    
    TORCH_AVAILABLE = True
    
    class MotionDataset(Dataset):
        """动作数据集"""
        
        def __init__(
            self,
            sequences: list[MotionSequence],
            sequence_length: int = 60,
            transform=None,
        ):
            self.sequences = sequences
            self.sequence_length = sequence_length
            self.transform = transform
        
        def __len__(self) -> int:
            return len(self.sequences)
        
        def __getitem__(self, idx: int) -> dict[str, torch.Tensor]:
            seq = self.sequences[idx]
            
            # 截取或填充到固定长度
            if seq.num_frames < self.sequence_length:
                # 填充
                frames = np.zeros((self.sequence_length, seq.num_joints, 3), dtype=np.float32)
                frames[:seq.num_frames] = seq.frames
            else:
                # 随机截取
                start = np.random.randint(0, seq.num_frames - self.sequence_length)
                frames = seq.frames[start:start + self.sequence_length].copy()
            
            # 转换为张量
            data = torch.from_numpy(frames)
            
            return {
                "input": data,
                "dang": seq.dang,
                "action_name": seq.action_name,
            }
    
    class PositionalEncoding(nn.Module):
        """位置编码"""
        
        def __init__(self, d_model: int, max_len: int = 5000):
            super().__init__()
            pe = torch.zeros(max_len, d_model)
            position = torch.arange(0, max_len, dtype=torch.float).unsqueeze(1)
            div_term = torch.exp(torch.arange(0, d_model, 2).float() * (-np.log(10000.0) / d_model))
            pe[:, 0::2] = torch.sin(position * div_term)
            pe[:, 1::2] = torch.cos(position * div_term)
            self.register_buffer('pe', pe.unsqueeze(0))
        
        def forward(self, x: torch.Tensor) -> torch.Tensor:
            return x + self.pe[:, :x.size(1)]
    
    class MotionEncoder(nn.Module):
        """动作编码器"""
        
        def __init__(
            self,
            input_dim: int = 3,
            hidden_dim: int = 256,
            num_layers: int = 4,
            num_heads: int = 8,
            dropout: float = 0.1,
        ):
            super().__init__()
            
            self.input_projection = nn.Linear(input_dim, hidden_dim)
            self.pos_encoding = PositionalEncoding(hidden_dim)
            
            encoder_layer = nn.TransformerEncoderLayer(
                d_model=hidden_dim,
                nhead=num_heads,
                dim_feedforward=hidden_dim * 4,
                dropout=dropout,
                batch_first=True,
            )
            self.transformer = nn.TransformerEncoder(encoder_layer, num_layers)
            
            self.output_norm = nn.LayerNorm(hidden_dim)
        
        def forward(self, x: torch.Tensor) -> torch.Tensor:
            # x: (B, T, J, 3) -> (B, T*J, hidden_dim)
            B, T, J, C = x.shape
            
            # 投影
            x = x.view(B, T * J, C)
            x = self.input_projection(x)
            
            # 位置编码
            x = self.pos_encoding(x)
            
            # Transformer
            x = self.transformer(x)
            
            # 输出归一化
            x = self.output_norm(x)
            
            return x
    
    class MotionDecoder(nn.Module):
        """动作解码器"""
        
        def __init__(
            self,
            hidden_dim: int = 256,
            output_dim: int = 3,
            num_layers: int = 4,
            num_heads: int = 8,
            dropout: float = 0.1,
        ):
            super().__init__()
            
            decoder_layer = nn.TransformerEncoderLayer(
                d_model=hidden_dim,
                nhead=num_heads,
                dim_feedforward=hidden_dim * 4,
                dropout=dropout,
                batch_first=True,
            )
            self.transformer = nn.TransformerEncoder(decoder_layer, num_layers)
            
            self.output_projection = nn.Linear(hidden_dim, output_dim)
            self.output_norm = nn.LayerNorm(hidden_dim)
        
        def forward(self, x: torch.Tensor, target_length: int) -> torch.Tensor:
            # 解码生成目标长度
            B = x.shape[0]
            
            # 使用起始标记
            start_token = x[:, -1:, :]
            decoder_input = start_token.expand(B, target_length, -1)
            
            # Transformer
            x = self.transformer(decoder_input)
            x = self.output_norm(x)
            
            # 投影到输出维度
            x = self.output_projection(x)
            
            return x
    
    class OperaMotionVAE(nn.Module):
        """京剧动作变分自编码器"""
        
        def __init__(
            self,
            input_dim: int = 3,
            hidden_dim: int = 256,
            latent_dim: int = 128,
            num_layers: int = 4,
            num_heads: int = 8,
            dropout: float = 0.1,
        ):
            super().__init__()
            
            self.encoder = MotionEncoder(
                input_dim=input_dim,
                hidden_dim=hidden_dim,
                num_layers=num_layers,
                num_heads=num_heads,
                dropout=dropout,
            )
            
            # 潜在空间
            self.fc_mu = nn.Linear(hidden_dim, latent_dim)
            self.fc_logvar = nn.Linear(hidden_dim, latent_dim)
            
            self.decoder = MotionDecoder(
                hidden_dim=hidden_dim + latent_dim,
                output_dim=input_dim,
                num_layers=num_layers,
                num_heads=num_heads,
                dropout=dropout,
            )
        
        def encode(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
            h = self.encoder(x)
            h = h.mean(dim=1)  # 全局池化
            
            mu = self.fc_mu(h)
            logvar = self.fc_logvar(h)
            
            return mu, logvar
        
        def reparameterize(self, mu: torch.Tensor, logvar: torch.Tensor) -> torch.Tensor:
            std = torch.exp(0.5 * logvar)
            eps = torch.randn_like(std)
            return mu + eps * std
        
        def decode(self, z: torch.Tensor, target_length: int) -> torch.Tensor:
            # 重复潜在向量并与位置编码结合
            B = z.shape[0]
            z = z.unsqueeze(1).expand(-1, target_length, -1)
            
            return self.decoder(z, target_length)
        
        def forward(self, x: torch.Tensor, target_length: int) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
            mu, logvar = self.encode(x)
            z = self.reparameterize(mu, logvar)
            recon = self.decode(z, target_length)
            
            return recon, mu, logvar
    
    class StyleTransferModel(nn.Module):
        """风格迁移模型"""
        
        def __init__(
            self,
            content_dim: int = 128,
            style_dim: int = 64,
            hidden_dim: int = 256,
        ):
            super().__init__()
            
            # 内容编码器
            self.content_encoder = nn.Sequential(
                nn.Linear(content_dim, hidden_dim),
                nn.ReLU(),
                nn.Linear(hidden_dim, hidden_dim),
            )
            
            # 风格编码器
            self.style_encoder = nn.Sequential(
                nn.Linear(style_dim, hidden_dim),
                nn.ReLU(),
                nn.Linear(hidden_dim, hidden_dim),
            )
            
            # 融合模块
            self.fusion = nn.MultiheadAttention(hidden_dim, num_heads=4, batch_first=True)
            
            # 解码器
            self.decoder = nn.Sequential(
                nn.Linear(hidden_dim, hidden_dim),
                nn.ReLU(),
                nn.Linear(hidden_dim, content_dim),
            )
        
        def forward(
            self,
            content: torch.Tensor,
            style: torch.Tensor,
        ) -> torch.Tensor:
            # 编码
            content_h = self.content_encoder(content)
            style_h = self.style_encoder(style)
            
            # 融合
            fused, _ = self.fusion(content_h, style_h, style_h)
            
            # 解码
            output = self.decoder(fused)
            
            return output
    
    class MotionGenerator:
        """动作生成器"""
        
        def __init__(
            self,
            model: nn.Module,
            preprocessor: MotionPreprocessor,
            device: str = "cuda",
        ):
            self.model = model
            self.preprocessor = preprocessor
            self.device = device
            self.model.eval()
        
        @torch.no_grad()
        def generate(
            self,
            seed_sequence: MotionSequence,
            target_length: int = 60,
            temperature: float = 1.0,
        ) -> MotionSequence:
            """从种子序列生成新动作"""
            # 预处理
            processed = self.preprocessor.normalize(seed_sequence)
            input_tensor = torch.from_numpy(processed.to_tensor()).unsqueeze(0).to(self.device)
            
            # 编码
            mu, logvar = self.model.encode(input_tensor)
            
            # 采样
            z = mu * temperature
            
            # 解码
            output = self.model.decode(z, target_length)
            
            # 后处理
            output_np = output.squeeze(0).cpu().numpy()
            
            # 重塑为(B, T, J, 3)
            num_joints = seed_sequence.num_joints
            output_np = output_np.reshape(target_length, num_joints, 3)
            
            return MotionSequence(
                frames=output_np,
                frame_rate=seed_sequence.frame_rate,
                skeleton=seed_sequence.skeleton,
            )
        
        @torch.no_grad()
        def interpolate(
            self,
            sequence1: MotionSequence,
            sequence2: MotionSequence,
            alpha: float = 0.5,
        ) -> MotionSequence:
            """在两个动作序列之间插值"""
            p1 = self.preprocessor.normalize(sequence1).to_tensor()
            p2 = self.preprocessor.normalize(sequence2).to_tensor()
            
            t1 = torch.from_numpy(p1).unsqueeze(0).to(self.device)
            t2 = torch.from_numpy(p2).unsqueeze(0).to(self.device)
            
            mu1, _ = self.model.encode(t1)
            mu2, _ = self.model.encode(t2)
            
            # 插值
            mu = alpha * mu1 + (1 - alpha) * mu2
            
            # 解码
            target_length = max(sequence1.num_frames, sequence2.num_frames)
            output = self.model.decode(mu, target_length)
            
            output_np = output.squeeze(0).cpu().numpy()
            
            return MotionSequence(
                frames=output_np.reshape(target_length, -1, 3),
                frame_rate=sequence1.frame_rate,
            )

except ImportError:
    TORCH_AVAILABLE = False
    
    # 如果PyTorch不可用，提供基础类
    class MotionDataset:
        pass
    
    class MotionEncoder:
        pass
    
    class OperaMotionVAE:
        pass
    
    class MotionGenerator:
        pass


# ============================================================================
# 训练器
# ============================================================================

class MotionTrainer:
    """动作模型训练器"""
    
    def __init__(
        self,
        model: nn.Module,
        config: TrainingConfig,
        train_dataset: Dataset,
        val_dataset: Dataset | None = None,
    ):
        self.model = model
        self.config = config
        self.train_dataset = train_dataset
        self.val_dataset = val_dataset
        
        self.device = torch.device(config.device if torch.cuda.is_available() else "cpu")
        self.model.to(self.device)
        
        # 优化器
        self.optimizer = torch.optim.Adam(
            model.parameters(),
            lr=config.learning_rate,
        )
        
        # 学习率调度
        self.scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
            self.optimizer,
            mode='min',
            patience=10,
            factor=0.5,
        )
        
        # 检查点目录
        Path(config.checkpoint_dir).mkdir(parents=True, exist_ok=True)
        Path(config.log_dir).mkdir(parents=True, exist_ok=True)
        
        self.history: dict[str, list] = {
            "train_loss": [],
            "val_loss": [],
        }
    
    def train_epoch(self) -> float:
        """训练一个epoch"""
        self.model.train()
        total_loss = 0
        num_batches = 0
        
        loader = DataLoader(
            self.train_dataset,
            batch_size=self.config.batch_size,
            shuffle=True,
        )
        
        for batch in loader:
            input_data = batch["input"].to(self.device)
            
            self.optimizer.zero_grad()
            
            # 前向传播
            recon, mu, logvar = self.model(input_data, input_data.size(1))
            
            # 损失函数
            recon_loss = F.mse_loss(recon, input_data)
            kl_loss = -0.5 * torch.mean(1 + logvar - mu.pow(2) - logvar.exp())
            
            loss = recon_loss + 0.01 * kl_loss
            
            # 反向传播
            loss.backward()
            self.optimizer.step()
            
            total_loss += loss.item()
            num_batches += 1
        
        return total_loss / num_batches
    
    def validate(self) -> float:
        """验证"""
        if self.val_dataset is None:
            return 0.0
        
        self.model.eval()
        total_loss = 0
        num_batches = 0
        
        loader = DataLoader(self.val_dataset, batch_size=self.config.batch_size)
        
        with torch.no_grad():
            for batch in loader:
                input_data = batch["input"].to(self.device)
                recon, mu, logvar = self.model(input_data, input_data.size(1))
                
                recon_loss = F.mse_loss(recon, input_data)
                kl_loss = -0.5 * torch.mean(1 + logvar - mu.pow(2) - logvar.exp())
                
                loss = recon_loss + 0.01 * kl_loss
                total_loss += loss.item()
                num_batches += 1
        
        return total_loss / num_batches
    
    def train(self) -> dict[str, list]:
        """完整训练流程"""
        best_val_loss = float('inf')
        
        for epoch in range(self.config.num_epochs):
            # 训练
            train_loss = self.train_epoch()
            
            # 验证
            val_loss = self.validate()
            
            # 记录历史
            self.history["train_loss"].append(train_loss)
            self.history["val_loss"].append(val_loss)
            
            # 学习率调整
            self.scheduler.step(val_loss)
            
            # 保存最佳模型
            if val_loss < best_val_loss:
                best_val_loss = val_loss
                self.save_checkpoint("best_model.pt")
            
            # 定期保存
            if (epoch + 1) % 10 == 0:
                self.save_checkpoint(f"checkpoint_epoch_{epoch+1}.pt")
            
            print(f"Epoch {epoch+1}/{self.config.num_epochs} - Train Loss: {train_loss:.4f}, Val Loss: {val_loss:.4f}")
        
        return self.history
    
    def save_checkpoint(self, filename: str):
        """保存检查点"""
        path = Path(self.config.checkpoint_dir) / filename
        torch.save({
            "model_state_dict": self.model.state_dict(),
            "optimizer_state_dict": self.optimizer.state_dict(),
            "history": self.history,
            "config": self.config.__dict__,
        }, path)
    
    def load_checkpoint(self, path: str):
        """加载检查点"""
        checkpoint = torch.load(path, map_location=self.device)
        self.model.load_state_dict(checkpoint["model_state_dict"])
        self.optimizer.load_state_dict(checkpoint["optimizer_state_dict"])
        self.history = checkpoint.get("history", self.history)


# ============================================================================
# 导出接口
# ============================================================================

__all__ = [
    "MotionDataType",
    "MotionSequence",
    "TrainingConfig",
    "MotionPreprocessor",
    "MotionDataset",
    "MotionEncoder",
    "MotionDecoder",
    "OperaMotionVAE",
    "StyleTransferModel",
    "MotionGenerator",
    "MotionTrainer",
]
