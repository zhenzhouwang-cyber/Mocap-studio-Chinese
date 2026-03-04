"""
身体重心与平衡分析。

依据文献: 运动生物力学研究
用于分析京剧站姿、转身等动作的稳定性和平衡能力。

学术价值：
- 重心轨迹分析可评估动作稳定性
- 支撑论文中"身段平稳度"相关章节
- 便于京剧步法教学的量化评估
"""

from __future__ import annotations

from typing import Any

import numpy as np

from opera_mocap_tool.io.base import MocapData


# 默认的躯干 marker（用于计算身体中心）
DEFAULT_TORSO_MARKERS = [
    "pelvis", "spine", "chest", "neck", "head",
    "Pelvis", "Spine", "Chest", "Neck", "Head",
]


def compute_center_of_mass(
    data: MocapData,
    marker_weights: dict[str, float] | None = None,
) -> dict[str, list[tuple[float, float, float]]]:
    """
    计算身体重心轨迹。
    
    使用各 marker 的位置加权平均估算身体重心。
    
    Args:
        data: MocapData。
        marker_weights: marker 权重字典，若为 None 则等权重。
    
    Returns:
        包含 center_of_mass 轨迹的字典。
    """
    if marker_weights is None:
        # 默认权重：躯干 > 四肢
        marker_weights = {
            # 躯干权重较高
            "pelvis": 0.25, "Pelvis": 0.25,
            "spine": 0.2, "Spine": 0.2,
            "chest": 0.15, "Chest": 0.15,
            "neck": 0.1, "Neck": 0.1,
            "head": 0.1, "Head": 0.1,
            # 四肢权重较低
            "shoulder": 0.05, "Shoulder": 0.05,
            "hip": 0.05, "Hip": 0.05,
        }
    
    n_frames = data.n_frames
    if n_frames == 0:
        return {}
    
    # 初始化重心
    com_x = np.zeros(n_frames)
    com_y = np.zeros(n_frames)
    com_z = np.zeros(n_frames)
    total_weight = 0.0
    
    for marker_name, coords in data.markers.items():
        weight = marker_weights.get(marker_name, 0.02)  # 默认权重
        
        arr = np.array(coords, dtype=float)
        if len(arr) < n_frames:
            # 填充不足的帧
            arr_padded = np.full((n_frames, 3), np.nan)
            arr_padded[:len(arr)] = arr
            arr = arr_padded
        
        com_x += arr[:, 0] * weight
        com_y += arr[:, 1] * weight
        com_z += arr[:, 2] * weight
        total_weight += weight
    
    # 归一化
    if total_weight > 0:
        com_x /= total_weight
        com_y /= total_weight
        com_z /= total_weight
    
    # 转换为轨迹列表
    com_trajectory = [(float(com_x[i]), float(com_y[i]), float(com_z[i])) for i in range(n_frames)]
    
    return {"center_of_mass": com_trajectory}


def compute_balance_analysis(
    data: MocapData,
    kinematics: dict | None = None,
) -> dict[str, Any]:
    """
    分析身体平衡和稳定性。
    
    计算重心的移动范围、速度、稳定性指标。
    
    Args:
        data: MocapData。
        kinematics: 若已计算则传入。
    
    Returns:
        包含 balance_metrics 的字典。
    """
    from .kinematic import compute_kinematics
    
    kin = kinematics or compute_kinematics(data)
    fr = data.frame_rate
    dt = 1.0 / fr if fr > 0 else 0.01
    
    result: dict[str, Any] = {"balance_metrics": {}}
    
    # 计算重心
    com_result = compute_center_of_mass(data)
    com_trajectory = com_result.get("center_of_mass", [])
    
    if not com_trajectory:
        return result
    
    com_arr = np.array(com_trajectory, dtype=float)
    n_frames = len(com_arr)
    
    if n_frames < 2:
        return result
    
    # 重心位移范围
    valid = np.isfinite(com_arr).all(axis=1)
    if np.any(valid):
        com_valid = com_arr[valid]
        
        result["balance_metrics"]["spatial_range"] = {
            "x_range": round(float(np.ptp(com_valid[:, 0])), 4),
            "y_range": round(float(np.ptp(com_valid[:, 1])), 4),  # 垂直方向
            "z_range": round(float(np.ptp(com_valid[:, 2])), 4),
        }
        
        # 重心速度
        com_vel = np.gradient(com_valid, dt, axis=0)
        com_speed = np.linalg.norm(com_vel, axis=1)
        
        result["balance_metrics"]["velocity"] = {
            "mean_speed": round(float(np.mean(com_speed)), 4),
            "max_speed": round(float(np.max(com_speed)), 4),
            "std_speed": round(float(np.std(com_speed)), 4),
        }
        
        # 稳定性评分：基于重心移动范围和速度
        # 移动范围小、速度低 = 稳定
        x_range = float(np.ptp(com_valid[:, 0]))
        z_range = float(np.ptp(com_valid[:, 2]))  # 水平面
        mean_speed = float(np.mean(com_speed))
        
        # 计算稳定性得分 (0-100)
        # 假设稳定状态下重心移动范围 < 0.1m, 速度 < 0.05m/s
        stability_score = 100
        if x_range > 0.1:
            stability_score -= min(30, (x_range - 0.1) * 100)
        if z_range > 0.1:
            stability_score -= min(30, (z_range - 0.1) * 100)
        if mean_speed > 0.05:
            stability_score -= min(40, (mean_speed - 0.05) * 200)
        
        stability_score = max(0, stability_score)
        
        result["balance_metrics"]["stability"] = {
            "score": round(stability_score, 2),
            "rating": _get_stability_rating(stability_score),
        }
    
    # 分析前后/左右偏移趋势
    # 前倾/后仰 (Y方向)
    y_mean = np.nanmean(com_arr[:, 1])
    y_trend = np.polyfit(range(n_frames), com_arr[:, 1], 1)[0] if n_frames > 1 else 0
    
    # 左倾/右倾 (X方向)
    x_mean = np.nanmean(com_arr[:, 0])
    x_trend = np.polyfit(range(n_frames), com_arr[:, 0], 1)[0] if n_frames > 1 else 0
    
    result["balance_metrics"]["posture_trend"] = {
        "vertical_trend": "forward" if y_trend > 0.001 else "backward" if y_trend < -0.001 else "stable",
        "lateral_trend": "left" if x_trend > 0.001 else "right" if x_trend < -0.001 else "centered",
        "vertical_offset": round(float(y_mean), 4),
        "lateral_offset": round(float(x_mean), 4),
    }
    
    return result


def compute_stability_during_motion(
    data: MocapData,
    kinematics: dict | None = None,
    window_size: int = 30,
) -> dict[str, Any]:
    """
    分析动作过程中的稳定性变化。
    
    使用滑动窗口分析稳定性随时间的变化。
    
    Args:
        data: MocapData。
        kinematics: 若已计算则传入。
        window_size: 滑动窗口大小（帧数）。
    
    Returns:
        包含 stability_time_series 的字典。
    """
    com_result = compute_center_of_mass(data)
    com_trajectory = com_result.get("center_of_mass", [])
    
    if not com_trajectory:
        return {"stability_time_series": {}}
    
    com_arr = np.array(com_trajectory, dtype=float)
    n_frames = len(com_arr)
    
    if n_frames < window_size * 2:
        return {"stability_time_series": {}}
    
    result: dict[str, Any] = {"stability_time_series": {}}
    
    stability_scores = []
    time_points = []
    
    for i in range(0, n_frames - window_size, window_size // 2):
        window = com_arr[i:i + window_size]
        
        # 计算窗口内的稳定性
        x_range = float(np.ptp(window[:, 0]))
        z_range = float(np.ptp(window[:, 2]))
        
        score = 100
        if x_range > 0.1:
            score -= min(30, (x_range - 0.1) * 100)
        if z_range > 0.1:
            score -= min(30, (z_range - 0.1) * 100)
        
        stability_scores.append(max(0, round(score, 2)))
        time_points.append(round(i / data.frame_rate, 2))
    
    if stability_scores:
        result["stability_time_series"] = {
            "time": time_points,
            "stability": stability_scores,
        }
    
    return result


def _get_stability_rating(score: float) -> str:
    """根据分数返回稳定性评级"""
    if score >= 80:
        return "excellent"
    elif score >= 60:
        return "good"
    elif score >= 40:
        return "fair"
    else:
        return "unstable"
