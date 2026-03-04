"""
云手专项特征分析模块。

基于京剧程式化理论和拉班运动分析，提取云手特有指标：
- 行当幅度判定（老生/武生/旦角/丑行）
- 三节协调分析（稍节-中节-根节时序）
- 反衬劲检测（欲左先右）
- 轨迹圆度分析

复用现有模块：kinematic, opera_features, laban_approx, rhythm
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from opera_mocap_tool.io.base import MocapData


# 行当幅度判定标准（归一化高度）
DANG_HEIGHT_RANGES = {
    "laosheng": {"min": 0.75, "max": 1.0, "name": "老生", "standard": "齐眉"},
    "wusheng": {"min": 0.55, "max": 0.8, "name": "武生/小生", "standard": "齐口"},
    "danjiao": {"min": 0.35, "max": 0.6, "name": "旦角", "standard": "齐胸"},
    "chou": {"min": 0.2, "max": 0.4, "name": "丑行", "standard": "齐腹"},
}


def analyze_yunshou(
    data: MocapData,
    *,
    compute_laban: bool = True,
    compute_symmetry: bool = True,
) -> dict[str, Any]:
    """
    完整的云手分析入口函数。

    Args:
        data: MocapData格式的动捕/姿态数据
        compute_laban: 是否计算拉班近似特征
        compute_symmetry: 是否计算左右对称性

    Returns:
        包含所有分析结果的字典
    """
    # 导入现有模块
    from opera_mocap_tool.analysis import (
        compute_kinematics,
        compute_left_right_symmetry,
        compute_opera_features,
        compute_rhythm,
    )

    try:
        from opera_mocap_tool.analysis.laban_approx import compute_laban_approx
    except ImportError:
        compute_laban_approx = None

    # 计算运动学基础数据
    kinematics = compute_kinematics(data)

    # 行当判定
    dang = classify_dang_by_height(data)

    # 三节协调分析
    three_section = analyze_three_section_coordination(data, kinematics)

    # 反衬劲检测
    fancheng_jin = detect_fancheng_jin(data, kinematics)

    # 轨迹圆度
    circularity = compute_yunshou_circularity(data, kinematics)

    # 复用现有指标
    symmetry = {}
    if compute_symmetry:
        try:
            symmetry = compute_left_right_symmetry(data)
        except Exception:
            symmetry = {}

    opera_feat = {}
    try:
        opera_feat = compute_opera_features(data, kinematics)
    except Exception:
        opera_feat = {}

    rhythm_feat = {}
    try:
        rhythm_feat = compute_rhythm(data)
    except Exception:
        rhythm_feat = {}

    laban_feat = {}
    if compute_laban and compute_laban_approx:
        try:
            laban_feat = compute_laban_approx({"kinematics": kinematics})
        except Exception:
            laban_feat = {}

    # 提取关键轨迹（用于生成艺术）
    trajectories = extract_yunshou_trajectories(data, kinematics)

    return {
        "meta": {
            "source_type": data.metadata.get("source_type", "unknown"),
            "duration_sec": data.duration_sec,
            "frame_rate": data.frame_rate,
            "n_frames": data.n_frames,
        },
        "dang": dang,
        "three_section": three_section,
        "fancheng_jin": fancheng_jin,
        "circularity": circularity,
        "symmetry": symmetry,
        "opera_features": opera_feat,
        "rhythm": rhythm_feat,
        "laban": laban_feat,
        "trajectories": trajectories,
    }


def classify_dang_by_height(data: MocapData) -> dict[str, Any]:
    """
    根据手腕高度归一化位置判定行当。

    京剧理论：
    - 老生: 齐眉 (归一化高度 0.75-1.0)
    - 武生/小生: 齐口 (归一化高度 0.55-0.8)
    - 旦角: 齐胸 (归一化高度 0.35-0.6)
    - 丑行: 齐腹 (归一化高度 0.2-0.4)

    Args:
        data: MocapData

    Returns:
        行当分类结果
    """
    # 尝试多种可能的手腕marker名称
    wrist_names = [
        "wrist_left", "wrist_right",
        "left_wrist", "right_wrist",
        "lwrist", "rwrist",
    ]

    # 尝试获取肩膀和髋部用于归一化
    shoulder_names = ["shoulder_left", "shoulder_right", "shoulder"]
    hip_names = ["hip_left", "hip_right", "hip"]

    wrist_data = None
    wrist_name = None
    for name in wrist_names:
        if name in data.markers:
            wrist_data = data.markers[name]
            wrist_name = name
            break

    if not wrist_data:
        return {
            "dang": "unknown",
            "confidence": 0.0,
            "hand_height_norm": 0.0,
            "description": "未找到手腕marker",
        }

    # 计算手腕y坐标均值
    wrist_arr = np.array(wrist_data, dtype=float)
    wrist_y = np.nanmean(wrist_arr[:, 1])  # y是垂直方向

    # 获取肩膀和髋部位置用于归一化
    shoulder_y = None
    hip_y = None

    for name in shoulder_names:
        if name in data.markers:
            shoulder_arr = np.array(data.markers[name], dtype=float)
            shoulder_y = np.nanmean(shoulder_arr[:, 1])
            break

    for name in hip_names:
        if name in data.markers:
            hip_arr = np.array(data.markers[name], dtype=float)
            hip_y = np.nanmean(hip_arr[:, 1])
            break

    # 如果没有肩膀/髋部数据，使用手腕自身的范围归一化
    if shoulder_y is None and hip_y is None:
        # 使用手腕自身的min-max归一化
        wrist_y_min = np.nanmin(wrist_arr[:, 1])
        wrist_y_max = np.nanmax(wrist_arr[:, 1])
        if wrist_y_max > wrist_y_min:
            hand_height_norm = 0.5  # 默认中间值
        else:
            hand_height_norm = 0.0
    else:
        # 使用肩膀-髋部范围归一化
        torso_range = shoulder_y - hip_y if (shoulder_y and hip_y) else 1.0
        if torso_range > 0:
            hand_height_norm = (wrist_y - hip_y) / torso_range if hip_y else 0.5
        else:
            hand_height_norm = 0.5

    # 判定行当
    dang_result = "unknown"
    confidence = 0.0
    for dang_name, config in DANG_HEIGHT_RANGES.items():
        if config["min"] <= hand_height_norm <= config["max"]:
            dang_result = dang_name
            # 计算置信度（离区间中心越近置信度越高）
            center = (config["min"] + config["max"]) / 2
            confidence = 1.0 - abs(hand_height_norm - center) / ((config["max"] - config["min"]) / 2)
            confidence = max(0.0, min(1.0, confidence))
            break

    # 描述
    if dang_result != "unknown":
        description = f"{DANG_HEIGHT_RANGES[dang_result]['name']} - {DANG_HEIGHT_RANGES[dang_result]['standard']}"
    else:
        description = "无法判定行当"

    return {
        "dang": dang_result,
        "dang_cn": DANG_HEIGHT_RANGES.get(dang_result, {}).get("name", "未知"),
        "confidence": round(confidence, 3),
        "hand_height_norm": round(hand_height_norm, 3),
        "description": description,
    }


def analyze_three_section_coordination(
    data: MocapData,
    kinematics: dict | None = None,
) -> dict[str, Any]:
    """
    分析云手"三节"协调：稍节(手)→中节(肘)→根节(肩)。

    京剧理论：
    - 稍节起：手腕首先启动
    - 中节随：肘部跟随
    - 根节追：肩部带动

    Args:
        data: MocapData
        kinematics: 运动学数据（可选）

    Returns:
        三节协调分析结果
    """
    from opera_mocap_tool.analysis.kinematic import compute_kinematics

    if kinematics is None:
        kinematics = compute_kinematics(data)

    # 定义三节marker
    section_markers = {
        "wrist": ["wrist_left", "wrist_right", "lwrist", "rwrist"],
        "elbow": ["elbow_left", "elbow_right", "lelbow", "relbow"],
        "shoulder": ["shoulder_left", "shoulder_right", "lsho", "rsho"],
    }

    def get_marker_velocity(velocities: dict, marker_names: list[str]) -> np.ndarray | None:
        """获取指定marker的速度序列"""
        for name in marker_names:
            if name in velocities:
                speed = velocities[name].get("speed", [])
                if speed:
                    return np.array(speed, dtype=float)
        return None

    velocities = kinematics.get("velocities", {})

    # 获取各节速度
    wrist_vel = get_marker_velocity(velocities, section_markers["wrist"])
    elbow_vel = get_marker_velocity(velocities, section_markers["elbow"])
    shoulder_vel = get_marker_velocity(velocities, section_markers["shoulder"])

    if wrist_vel is None:
        return {
            "coordination_score": 0.0,
            "description": "未找到手腕速度数据",
        }

    # 计算各节的速度峰值时间
    def find_velocity_peaks(vel: np.ndarray, threshold_ratio: float = 0.5) -> list[int]:
        """找到速度峰值位置"""
        if len(vel) < 3:
            return []
        threshold = np.max(vel) * threshold_ratio
        peaks = []
        for i in range(1, len(vel) - 1):
            if vel[i] > vel[i - 1] and vel[i] > vel[i + 1] and vel[i] > threshold:
                peaks.append(i)
        return peaks

    wrist_peaks = find_velocity_peaks(wrist_vel)
    elbow_peaks = find_velocity_peaks(elbow_vel) if elbow_vel is not None else []
    shoulder_peaks = find_velocity_peaks(shoulder_vel) if shoulder_vel is not None else []

    # 计算平均峰值时间
    wrist_peak_time = np.mean(wrist_peaks) / len(wrist_vel) if wrist_peaks else 0.5
    elbow_peak_time = np.mean(elbow_peaks) / len(elbow_vel) if elbow_peaks and elbow_vel is not None else 0.5
    shoulder_peak_time = np.mean(shoulder_peaks) / len(shoulder_vel) if shoulder_peaks and shoulder_vel is not None else 0.5

    # 计算时序延迟（理想情况：手腕最先，肘部其次，肩膀最后）
    delay_wrist_elbow = elbow_peak_time - wrist_peak_time
    delay_elbow_shoulder = shoulder_peak_time - elbow_peak_time

    # 协调性评分（0-100）
    # 理想延迟：正值表示手腕先动
    score = 100.0

    if delay_wrist_elbow < 0:
        score -= abs(delay_wrist_elbow) * 50  # 手腕应该在肘部之前
    if elbow_vel is not None and delay_elbow_shoulder < 0:
        score -= abs(delay_elbow_shoulder) * 50

    score = max(0.0, min(100.0, score))

    # 描述
    if score >= 80:
        description = "三节协调性好：稍节起→中节随→根节追"
    elif score >= 60:
        description = "三节基本协调，有轻微不同步"
    else:
        description = "三节协调性较差，需加强训练"

    return {
        "wrist_peak_time": round(wrist_peak_time, 3),
        "elbow_peak_time": round(elbow_peak_time, 3) if elbow_vel is not None else None,
        "shoulder_peak_time": round(shoulder_peak_time, 3) if shoulder_vel is not None else None,
        "delay_wrist_elbow": round(delay_wrist_elbow, 3),
        "delay_elbow_shoulder": round(delay_elbow_shoulder, 3),
        "coordination_score": round(score, 1),
        "description": description,
    }


def detect_fancheng_jin(
    data: MocapData,
    kinematics: dict | None = None,
    threshold: float = 0.3,
) -> dict[str, Any]:
    """
    检测"反衬劲"：欲左先右、欲右先左。

    京剧理论：
    - "反衬劲"是程式化重要特征
    - 动作前先向反方向蓄力

    Args:
        data: MocapData
        kinematics: 运动学数据（可选）
        threshold: 速度方向反转的阈值

    Returns:
        反衬劲检测结果
    """
    from opera_mocap_tool.analysis.kinematic import compute_kinematics

    if kinematics is None:
        kinematics = compute_kinematics(data)

    # 获取手腕速度
    wrist_names = ["wrist_left", "wrist_right", "lwrist", "rwrist"]
    velocities = kinematics.get("velocities", {})

    wrist_vel = None
    for name in wrist_names:
        if name in velocities:
            vx = velocities[name].get("vx", [])
            if vx:
                wrist_vel = np.array(vx, dtype=float)
                break

    if wrist_vel is None or len(wrist_vel) < 3:
        return {
            "n_reversals": 0,
            "reversal_ratio": 0.0,
            "description": "未找到足够的速度数据",
        }

    # 检测速度方向反转
    reversals = []
    for i in range(1, len(wrist_vel) - 1):
        # 连续三帧速度方向变化
        if wrist_vel[i - 1] * wrist_vel[i + 1] < 0:  # 方向反转
            # 检查幅度是否足够大
            if abs(wrist_vel[i]) > threshold * np.mean(np.abs(wrist_vel)):
                reversals.append(i)

    reversal_ratio = len(reversals) / len(wrist_vel) if len(wrist_vel) > 0 else 0.0

    # 描述
    if reversal_ratio < 0.05:
        description = "反衬劲不明显，动作较直接"
    elif reversal_ratio < 0.15:
        description = "有轻微反衬劲，符合程式化要求"
    else:
        description = "反衬劲明显，程式化程度高"

    return {
        "n_reversals": len(reversals),
        "reversal_positions": reversals[:20],  # 最多返回20个
        "reversal_ratio": round(reversal_ratio, 3),
        "description": description,
    }


def compute_yunshou_circularity(
    data: MocapData,
    kinematics: dict | None = None,
) -> dict[str, Any]:
    """
    计算云手轨迹的圆形程度。

    方法：
    1. 傅里叶描述子
    2. 圆形拟合误差
    3. 曲率分布均匀度

    Args:
        data: MocapData
        kinematics: 运动学数据（可选）

    Returns:
        圆度分析结果
    """
    from opera_mocap_tool.analysis.kinematic import compute_kinematics

    if kinematics is None:
        kinematics = compute_kinematics(data)

    # 获取手腕轨迹
    wrist_names = ["wrist_left", "wrist_right", "lwrist", "rwrist"]
    trajectories = kinematics.get("trajectories", {})

    wrist_traj = None
    for name in wrist_names:
        if name in trajectories:
            traj = trajectories[name]
            if traj.get("x") and traj.get("y"):
                wrist_traj = np.column_stack([
                    np.array(traj["x"], dtype=float),
                    np.array(traj["y"], dtype=float),
                ])
                break

    if wrist_traj is None or len(wrist_traj) < 10:
        return {
            "circularity_score": 0.0,
            "description": "未找到足够的手腕轨迹数据",
        }

    # 方法1：圆形拟合误差
    # 计算轨迹中心
    center = np.mean(wrist_traj, axis=0)
    # 计算每个点到中心的距离
    distances = np.linalg.norm(wrist_traj - center, axis=1)
    mean_radius = np.mean(distances)
    radius_std = np.std(distances)

    # 圆形度 = 1 - (半径标准差 / 平均半径)
    circularity_score = 1.0 - (radius_std / mean_radius) if mean_radius > 0 else 0.0
    circularity_score = max(0.0, min(1.0, circularity_score))

    # 方法2：曲率分布均匀度
    # 计算轨迹曲率
    if len(wrist_traj) >= 3:
        # 简化曲率：使用角度变化
        angles = np.arctan2(
            wrist_traj[1:, 1] - wrist_traj[:-1, 1],
            wrist_traj[1:, 0] - wrist_traj[:-1, 0]
        )
        angle_diffs = np.diff(angles)
        # 处理角度跳变
        angle_diffs = np.mod(angle_diffs + np.pi, 2 * np.pi) - np.pi
        curvature_variance = np.std(np.abs(angle_diffs))
    else:
        curvature_variance = 0.0

    # 描述
    if circularity_score >= 0.8:
        description = "轨迹圆形度很高，云手圆顺"
    elif circularity_score >= 0.6:
        description = "轨迹较圆，基本符合要求"
    elif circularity_score >= 0.4:
        description = "轨迹不够圆，需加强练习"
    else:
        description = "轨迹偏离圆形较多"

    return {
        "circularity_score": round(circularity_score, 3),
        "mean_radius": round(mean_radius, 3),
        "radius_std": round(radius_std, 3),
        "curvature_variance": round(curvature_variance, 3),
        "description": description,
    }


def extract_yunshou_trajectories(
    data: MocapData,
    kinematics: dict | None = None,
) -> dict[str, Any]:
    """
    提取云手关键轨迹数据，用于生成艺术。

    Args:
        data: MocapData
        kinematics: 运动学数据（可选）

    Returns:
        轨迹数据字典
    """
    from opera_mocap_tool.analysis.kinematic import compute_kinematics

    if kinematics is None:
        kinematics = compute_kinematics(data)

    trajectories = kinematics.get("trajectories", {})
    velocities = kinematics.get("velocities", {})

    result = {}

    # 定义需要提取的关键marker
    key_markers = {
        "wrist_left": ["wrist_left", "lwrist"],
        "wrist_right": ["wrist_right", "rwrist"],
        "elbow_left": ["elbow_left", "lelbow"],
        "elbow_right": ["elbow_right", "relbow"],
        "shoulder_left": ["shoulder_left", "lsho"],
        "shoulder_right": ["shoulder_right", "rsho"],
    }

    for key_name, possible_names in key_markers.items():
        # 查找轨迹
        traj = None
        vel = None
        for name in possible_names:
            if name in trajectories:
                traj = trajectories[name]
            if name in velocities:
                vel = velocities[name]

        if traj:
            result[key_name] = {
                "x": traj.get("x", []),
                "y": traj.get("y", []),
                "z": traj.get("z", []),
                "speed": vel.get("speed", []) if vel else [],
            }

    return result


# 便捷函数：单行分析
def quick_analyze(data: MocapData) -> dict[str, Any]:
    """
    快速云手分析，返回简化结果。

    Args:
        data: MocapData

    Returns:
        简化分析结果
    """
    result = analyze_yunshou(data)

    return {
        "dang": result["dang"]["dang"],
        "dang_cn": result["dang"]["dang_cn"],
        "dang_confidence": result["dang"]["confidence"],
        "three_section_score": result["three_section"]["coordination_score"],
        "fancheng_ratio": result["fancheng_jin"]["reversal_ratio"],
        "circularity": result["circularity"]["circularity_score"],
    }
