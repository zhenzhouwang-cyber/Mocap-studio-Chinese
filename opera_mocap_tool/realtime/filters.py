"""
实时滤波算法模块。

提供适用于实时数据的滤波算法：
- Butterworth低通滤波
- 指数移动平均
- Kalman滤波
- 噪声检测
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


@dataclass
class FilterConfig:
    """滤波配置"""
    filter_type: str = "ema"  # "butterworth", "ema", "kalman"
    cutoff_frequency: float = 5.0  # Butterworth截止频率 (Hz)
    sample_rate: float = 60.0  # 采样率 (Hz)
    alpha: float = 0.3  # EMA alpha值
    process_variance: float = 1e-5  # Kalman过程方差
    measurement_variance: float = 1e-3  # Kalman测量方差
    enabled: bool = True


class RealtimeFilter:
    """实时滤波器"""
    
    def __init__(self, config: FilterConfig | None = None):
        self.config = config or FilterConfig()
        
        # 状态变量
        self._ema_values: dict[str, np.ndarray] = {}
        self._kalman_states: dict[str, dict] = {}
        
        # Butterworth滤波器系数
        self._butter_coeffs: dict[str, tuple] = {}
    
    def filter(self, data: np.ndarray, key: str = "default") -> np.ndarray:
        """应用滤波"""
        if not self.config.enabled:
            return data
        
        filter_type = self.config.filter_type
        
        if filter_type == "ema":
            return self.exponential_moving_average(data, self.config.alpha, key)
        elif filter_type == "butterworth":
            return self.butterworth_lowpass(data, self.config.cutoff_frequency, self.config.sample_rate, key)
        elif filter_type == "kalman":
            return self.kalman_filter_array(data, key)
        else:
            return data
    
    def exponential_moving_average(
        self, 
        data: np.ndarray, 
        alpha: float = 0.3,
        key: str = "default"
    ) -> np.ndarray:
        """指数移动平均滤波"""
        if key not in self._ema_values:
            self._ema_values[key] = data.copy()
            return data
        
        # EMA: y[t] = alpha * x[t] + (1 - alpha) * y[t-1]
        self._ema_values[key] = alpha * data + (1 - alpha) * self._ema_values[key]
        return self._ema_values[key]
    
    def butterworth_lowpass(
        self, 
        data: np.ndarray, 
        cutoff: float, 
        fs: float,
        key: str = "default"
    ) -> np.ndarray:
        """Butterworth低通滤波"""
        # 归一化截止频率
        nyquist = fs / 2
        normalized_cutoff = cutoff / nyquist
        
        # 防止频率超过奈奎斯特
        if normalized_cutoff >= 1.0:
            return data
        
        # 简化实现：使用移动平均作为低通滤波的近似
        window_size = int(0.1 * fs / cutoff)  # 根据截止频率计算窗口大小
        window_size = max(3, min(window_size, 15))  # 限制窗口大小
        
        # 使用卷积实现低通滤波
        kernel = np.ones(window_size) / window_size
        
        # 对每个维度分别滤波
        result = np.zeros_like(data)
        for i in range(data.shape[-1]):
            if data.ndim == 1:
                result[i] = np.convolve(data, kernel, mode='same')
            else:
                result[..., i] = np.convolve(data[..., i], kernel, mode='same')
        
        return result
    
    def kalman_filter(
        self, 
        measurement: float, 
        process_variance: float = 1e-5,
        measurement_variance: float = 1e-3,
        key: str = "default"
    ) -> float:
        """单变量Kalman滤波"""
        if key not in self._kalman_states:
            self._kalman_states[key] = {
                "estimate": measurement,
                "error": 1.0,
            }
        
        state = self._kalman_states[key]
        
        # 预测步骤
        predicted_estimate = state["estimate"]
        predicted_error = state["error"] + process_variance
        
        # 更新步骤
        kalman_gain = predicted_error / (predicted_error + measurement_variance)
        new_estimate = predicted_estimate + kalman_gain * (measurement - predicted_estimate)
        new_error = (1 - kalman_gain) * predicted_error
        
        # 更新状态
        self._kalman_states[key] = {
            "estimate": new_estimate,
            "error": new_error,
        }
        
        return new_estimate
    
    def kalman_filter_array(self, data: np.ndarray, key: str = "default") -> np.ndarray:
        """多变量Kalman滤波（对每个元素分别滤波）"""
        result = np.zeros_like(data)
        
        # 对每个元素应用Kalman滤波
        if data.ndim == 1:
            for i in range(len(data)):
                result[i] = self.kalman_filter(
                    data[i], 
                    self.config.process_variance,
                    self.config.measurement_variance,
                    f"{key}_{i}"
                )
        else:
            # 展平处理
            flat_data = data.flatten()
            flat_result = np.zeros_like(flat_data)
            for i in range(len(flat_data)):
                flat_result[i] = self.kalman_filter(
                    flat_data[i],
                    self.config.process_variance,
                    self.config.measurement_variance,
                    f"{key}_{i}"
                )
            result = flat_result.reshape(data.shape)
        
        return result
    
    def detect_outliers(self, data: np.ndarray, threshold: float = 3.0) -> np.ndarray:
        """检测异常值（基于Z-score）"""
        if len(data) < 3:
            return np.zeros(len(data), dtype=bool)
        
        mean = np.mean(data, axis=0)
        std = np.std(data, axis=0)
        
        # 避免除以零
        std = np.where(std == 0, 1, std)
        
        z_scores = np.abs((data - mean) / std)
        
        return np.any(z_scores > threshold, axis=-1) if data.ndim > 1 else z_scores > threshold
    
    def smooth_joint_data(
        self, 
        positions: np.ndarray,
        velocities: np.ndarray,
        position_key: str = "pos",
        velocity_key: str = "vel"
    ) -> tuple[np.ndarray, np.ndarray]:
        """平滑关节位置和速度数据"""
        # 平滑位置
        smoothed_pos = self.filter(positions, position_key)
        
        # 平滑速度
        smoothed_vel = self.filter(velocities, velocity_key)
        
        return smoothed_pos, smoothed_vel
    
    def reset(self):
        """重置滤波器状态"""
        self._ema_values.clear()
        self._kalman_states.clear()
        self._butter_coeffs.clear()


class MotionSmoother:
    """动作平滑器 - 专门用于平滑动捕数据"""
    
    def __init__(self):
        self.filter = RealtimeFilter(FilterConfig(filter_type="ema", alpha=0.3))
        
        # 存储历史数据用于异常值检测
        self._position_history: dict[str, list] = {}
        self._velocity_history: dict[str, list] = {}
        self._history_size = 30
    
    def smooth_positions(
        self, 
        joint_positions: dict[str, np.ndarray]
    ) -> dict[str, np.ndarray]:
        """平滑关节位置"""
        result = {}
        
        for joint_name, position in joint_positions.items():
            key = f"pos_{joint_name}"
            
            # 检测异常值
            if joint_name in self._position_history:
                self._position_history[joint_name].append(position)
                if len(self._position_history[joint_name]) > self._history_size:
                    self._position_history[joint_name].pop(0)
                
                # 检查是否需要重置
                history = np.array(self._position_history[joint_name])
                if len(history) >= 3:
                    outliers = self.filter.detect_outliers(history, threshold=3.0)
                    if outliers[-1]:  # 当前帧是异常值
                        # 使用预测值替代
                        position = self.filter.filter(position, key)
            else:
                self._position_history[joint_name] = [position]
            
            # 应用滤波
            result[joint_name] = self.filter.filter(position, key)
        
        return result
    
    def smooth_velocities(
        self,
        joint_velocities: dict[str, np.ndarray]
    ) -> dict[str, np.ndarray]:
        """平滑关节速度"""
        result = {}
        
        for joint_name, velocity in joint_velocities.items():
            key = f"vel_{joint_name}"
            result[joint_name] = self.filter.filter(velocity, key)
        
        return result
    
    def reset(self):
        """重置平滑器"""
        self.filter.reset()
        self._position_history.clear()
        self._velocity_history.clear()


def create_filter(config: FilterConfig | None = None) -> RealtimeFilter:
    """创建滤波器的便捷函数"""
    return RealtimeFilter(config)


def create_smoother() -> MotionSmoother:
    """创建动作平滑器的便捷函数"""
    return MotionSmoother()


if __name__ == "__main__":
    # 测试代码
    print("测试实时滤波...")
    
    # 测试EMA
    filter_obj = RealtimeFilter(FilterConfig(filter_type="ema", alpha=0.3))
    
    test_data = np.array([1.0, 2.0, 3.0, 100.0, 5.0, 6.0])
    print(f"原始数据: {test_data}")
    
    filtered = filter_obj.exponential_moving_average(test_data, 0.3, "test")
    print(f"EMA滤波后: {filtered}")
    
    # 测试Kalman
    kalman_filter = RealtimeFilter(FilterConfig(filter_type="kalman"))
    for i, val in enumerate(test_data):
        result = kalman_filter.kalman_filter(val, key=f"kalman_{i}")
        if i < 3:
            print(f"Kalman {i}: {result}")
    
    # 测试动作平滑器
    smoother = create_smoother()
    positions = {
        "head": np.array([0.0, 1.5, 0.0]),
        "hand_l": np.array([-0.3, 1.2, 0.1]),
    }
    
    smoothed = smoother.smooth_positions(positions)
    print(f"平滑后: {smoothed}")
    
    print("测试完成")
