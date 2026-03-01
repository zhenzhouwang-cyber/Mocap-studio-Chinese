"""
动作质量分析：运动平滑度(jerk)、动作起止特征。

依据文献: DTW动作比对研究、运动生物力学
用于评估动作执行的质量和流畅性。

学术价值：
- jerk（三级加速度）分析可量化动作的平滑程度
- 支撑论文中"动作质量"相关章节
- 便于京剧身段教学的量化评估
"""

from __future__ import annotations

from typing import Any

import numpy as np

from opera_mocap_tool.io.base import MocapData


def compute_jerk_analysis(
    data: MocapData,
    kinematics: dict | None = None,
) -> dict[str, Any]:
    """
    计算动作平滑度分析（三级加速度 / jerk）。
    
    Jerk是加速度的导数，反映动作的突变程度。
    平滑的动作 jerk 值较低，京剧圆柔顺美的身段应该 jerk 较小。
    
    Args:
        data: MocapData。
        kinematics: 若已计算则传入。
    
    Returns:
        包含 jerk_stats, smoothness_scores 的字典。
    """
    from .kinematic import compute_kinematics

    kin = kinematics or compute_kinematics(data)
    fr = data.frame_rate
    dt = 1.0 / fr if fr > 0 else 0.01
    
    result: dict[str, Any] = {
        "jerk_stats": {},
        "smoothness_scores": {},
    }

    velocities = kin.get("velocities", {})
    accelerations = kin.get("accelerations", {})
    
    if not velocities:
        return result

    for name in velocities.keys():
        vel_data = velocities.get(name, {})
        acc_data = accelerations.get(name, {})
        
        vx = np.array(vel_data.get("vx", []), dtype=float)
        vy = np.array(vel_data.get("vy", []), dtype=float)
        vz = np.array(vel_data.get("vz", []), dtype=float)
        
        ax = np.array(acc_data.get("ax", []), dtype=float)
        ay = np.array(acc_data.get("ay", []), dtype=float)
        az = np.array(acc_data.get("az", []), dtype=float)
        
        if len(vx) < 3:
            continue
        
        # 计算 jerk (加速度的导数)
        jerk_x = np.gradient(ax, dt)
        jerk_y = np.gradient(ay, dt)
        jerk_z = np.gradient(az, dt)
        
        # 计算 jerk 幅度
        jerk_mag = np.sqrt(jerk_x**2 + jerk_y**2 + jerk_z**2)
        
        # 统计 jerk
        valid_jerk = jerk_mag[np.isfinite(jerk_mag)]
        if len(valid_jerk) > 0:
            result["jerk_stats"][name] = {
                "mean_jerk": round(float(np.mean(valid_jerk)), 4),
                "max_jerk": round(float(np.max(valid_jerk)), 4),
                "min_jerk": round(float(np.min(valid_jerk)), 4),
                "std_jerk": round(float(np.std(valid_jerk)), 4),
            }
            
            # 平滑度评分：基于 jerk 均值的归一化评分 (0-100)
            # jerk 越小，分数越高
            mean_jerk = np.mean(valid_jerk)
            smoothness_score = max(0, min(100, 100 - mean_jerk / 10))
            result["smoothness_scores"][name] = round(float(smoothness_score), 2)

    # 整体平滑度统计
    if result["smoothness_scores"]:
        all_scores = list(result["smoothness_scores"].values())
        result["_summary"] = {
            "mean_smoothness": round(float(np.mean(all_scores)), 2),
            "min_smoothness": round(float(np.min(all_scores)), 2),
            "max_smoothness": round(float(np.max(all_scores)), 2),
        }

    return result


def compute_motion_start_end_analysis(
    data: MocapData,
    kinematics: dict | None = None,
    velocity_threshold: float = 0.05,
) -> dict[str, Any]:
    """
    分析动作的开始和结束特征。
    
    检测动作的起止帧、起止速度、加速度等特征。
    对于京剧程式化动作的"起、承、转、合"分析有参考价值。
    
    Args:
        data: MocapData。
        kinematics: 若已计算则传入。
        velocity_threshold: 速度阈值，用于判断动作开始/结束。
    
    Returns:
        包含 start_end_features 的字典。
    """
    from .kinematic import compute_kinematics

    kin = kinematics or compute_kinematics(data)
    fr = data.frame_rate
    
    result: dict[str, Any] = {"start_end_features": {}}

    velocities = kin.get("velocities", {})
    if not velocities:
        return result

    # 使用第一个有效 marker 进行分析
    for name, vel_data in velocities.items():
        speed = np.array(vel_data.get("speed", []), dtype=float)
        if len(speed) < 10:
            continue
        
        # 找到动作开始和结束的帧
        is_moving = speed > velocity_threshold
        
        # 找到第一段和最后一段连续动作
        motion_starts = []
        motion_ends = []
        
        in_motion = False
        for i, moving in enumerate(is_moving):
            if moving and not in_motion:
                motion_starts.append(i)
                in_motion = True
            elif not moving and in_motion:
                motion_ends.append(i)
                in_motion = False
        
        # 如果动作持续到最后一帧
        if in_motion:
            motion_ends.append(len(speed) - 1)
        
        if motion_starts and motion_ends:
            # 分析第一个动作段
            first_start = motion_starts[0]
            first_end = motion_ends[0]
            
            # 最后一个动作段
            last_start = motion_starts[-1]
            last_end = motion_ends[-1]
            
            result["start_end_features"][name] = {
                "first_motion_start_frame": int(first_start),
                "first_motion_end_frame": int(first_end),
                "first_motion_start_time": round(first_start / fr, 3),
                "first_motion_end_time": round(first_end / fr, 3),
                "first_motion_duration_frames": int(first_end - first_start),
                "first_motion_duration_sec": round((first_end - first_start) / fr, 3),
                "last_motion_start_frame": int(last_start),
                "last_motion_end_frame": int(last_end),
                "last_motion_start_time": round(last_start / fr, 3),
                "last_motion_end_time": round(last_end / fr, 3),
                "last_motion_duration_frames": int(last_end - last_start),
                "last_motion_duration_sec": round((last_end - last_start) / fr, 3),
                "n_motion_segments": len(motion_starts),
            }
        break  # 只分析第一个有效 marker

    return result


def compute_motion_quality_overall(
    data: MocapData,
    kinematics: dict | None = None,
) -> dict[str, Any]:
    """
    综合动作质量评估。
    
    结合 jerk 分析、速度变化、轨迹平滑度等给出综合评分。
    
    Args:
        data: MocapData。
        kinematics: 若已计算则传入。
    
    Returns:
        包含 overall_quality 的字典。
    """
    jerk_result = compute_jerk_analysis(data, kinematics)
    start_end_result = compute_motion_start_end_analysis(data, kinematics)
    
    result: dict[str, Any] = {
        "jerk_analysis": jerk_result.get("jerk_stats", {}),
        "smoothness_scores": jerk_result.get("smoothness_scores", {}),
        "start_end": start_end_result.get("start_end_features", {}),
    }
    
    # 计算综合质量评分
    smoothness_scores = jerk_result.get("smoothness_scores", {})
    if smoothness_scores:
        overall_score = float(np.mean(list(smoothness_scores.values())))
        result["overall_quality"] = {
            "score": round(overall_score, 2),
            "rating": _get_quality_rating(overall_score),
            "n_markers_analyzed": len(smoothness_scores),
        }
    
    return result


def _get_quality_rating(score: float) -> str:
    """根据分数返回质量评级"""
    if score >= 80:
        return "excellent"
    elif score >= 60:
        return "good"
    elif score >= 40:
        return "fair"
    else:
        return "needs_improvement"
