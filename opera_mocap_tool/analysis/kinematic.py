"""运动学分析：轨迹、速度、加速度、关节角、空间范围。"""

from __future__ import annotations

from typing import Any

import numpy as np

from opera_mocap_tool.io.base import MocapData


def compute_kinematics(data: MocapData) -> dict[str, Any]:
    """
    计算运动学指标：轨迹、速度、加速度、空间范围。

    Args:
        data: 预处理后的 MocapData。

    Returns:
        包含 trajectories, velocities, accelerations, spatial_range 的字典。
    """
    fr = data.frame_rate
    dt = 1.0 / fr if fr > 0 else 0.01

    result: dict[str, Any] = {
        "trajectories": {},
        "velocities": {},
        "accelerations": {},
        "spatial_range": {},
        "displacement": {},
    }

    for name, coords in data.markers.items():
        arr = np.array(coords, dtype=float)
        if arr.size == 0 or len(arr) < 2:
            continue

        # 轨迹
        result["trajectories"][name] = {
            "x": arr[:, 0].tolist(),
            "y": arr[:, 1].tolist(),
            "z": arr[:, 2].tolist(),
        }

        # 位移幅度（相对第一帧）
        ref = np.nanmean(arr, axis=0)
        disp = np.linalg.norm(arr - ref, axis=1)
        result["displacement"][name] = [round(float(d), 4) for d in disp]

        # 速度（一阶差分）
        vel = np.gradient(arr, dt, axis=0)
        speed = np.linalg.norm(vel, axis=1)
        result["velocities"][name] = {
            "vx": [round(float(v), 4) for v in vel[:, 0]],
            "vy": [round(float(v), 4) for v in vel[:, 1]],
            "vz": [round(float(v), 4) for v in vel[:, 2]],
            "speed": [round(float(s), 4) for s in speed],
        }

        # 加速度（二阶差分）
        acc = np.gradient(vel, dt, axis=0)
        acc_mag = np.linalg.norm(acc, axis=1)
        result["accelerations"][name] = {
            "ax": [round(float(a), 4) for a in acc[:, 0]],
            "ay": [round(float(a), 4) for a in acc[:, 1]],
            "az": [round(float(a), 4) for a in acc[:, 2]],
            "magnitude": [round(float(a), 4) for a in acc_mag],
        }

        # 空间范围（AABB）
        valid = np.isfinite(arr).all(axis=1)
        if np.any(valid):
            arr_valid = arr[valid]
            result["spatial_range"][name] = {
                "x_min": float(np.min(arr_valid[:, 0])),
                "x_max": float(np.max(arr_valid[:, 0])),
                "y_min": float(np.min(arr_valid[:, 1])),
                "y_max": float(np.max(arr_valid[:, 1])),
                "z_min": float(np.min(arr_valid[:, 2])),
                "z_max": float(np.max(arr_valid[:, 2])),
                "span_x": float(np.ptp(arr_valid[:, 0])),
                "span_y": float(np.ptp(arr_valid[:, 1])),
                "span_z": float(np.ptp(arr_valid[:, 2])),
            }

    return result


def compute_joint_angles(
    data: MocapData,
    segment_pairs: dict[str, tuple[str, str, str]] | None = None,
) -> dict[str, list[float | None]]:
    """
    基于 marker 计算简化关节角（三点成角）。

    segment_pairs: 关节名 -> (近端 marker, 关节 marker, 远端 marker)
    例如 {"L_elbow": ("L_shoulder", "L_elbow_marker", "L_wrist")}

    Returns:
        关节名 -> 每帧角度（度）列表。
    """
    if not segment_pairs:
        return {}

    fr = data.frame_rate
    result: dict[str, list[float]] = {}

    for joint_name, (p1, p2, p3) in segment_pairs.items():
        if p1 not in data.markers or p2 not in data.markers or p3 not in data.markers:
            continue

        a = np.array(data.markers[p1])
        b = np.array(data.markers[p2])
        c = np.array(data.markers[p3])

        ba = a - b
        bc = c - b
        angles = []
        for i in range(len(a)):
            ba_i = ba[i]
            bc_i = bc[i]
            if np.any(np.isnan(ba_i)) or np.any(np.isnan(bc_i)):
                angles.append(float("nan"))
                continue
            cos_angle = np.dot(ba_i, bc_i) / (
                (np.linalg.norm(ba_i) * np.linalg.norm(bc_i)) + 1e-8
            )
            cos_angle = np.clip(cos_angle, -1, 1)
            angles.append(float(np.degrees(np.arccos(cos_angle))))

        result[joint_name] = [round(x, 2) if not np.isnan(x) else None for x in angles]

    return result


def compute_joint_range_analysis(
    data: MocapData,
    segment_pairs: dict[str, tuple[str, str, str]] | None = None,
) -> dict[str, Any]:
    """
    增强的关节活动范围分析：统计角度范围、峰值、动态/静态姿势识别。
    
    依据文献: 京剧程式化动作研究
    
    Args:
        data: MocapData。
        segment_pairs: 关节名 -> (近端, 关节, 远端) marker。
    
    Returns:
        包含每个关节的角度范围、峰值统计、姿势类型。
    """
    if not segment_pairs:
        return {}
    
    angles_data = compute_joint_angles(data, segment_pairs)
    result: dict[str, Any] = {}
    
    for joint_name, angles in angles_data.items():
        angles_arr = np.array([a for a in angles if a is not None], dtype=float)
        if len(angles_arr) == 0:
            continue
        
        # 角度范围统计
        angle_min = float(np.min(angles_arr))
        angle_max = float(np.max(angles_arr))
        angle_range = angle_max - angle_min
        angle_mean = float(np.mean(angles_arr))
        angle_std = float(np.std(angles_arr))
        
        # 峰值检测
        from scipy.signal import find_peaks
        peaks, _ = find_peaks(angles_arr, distance=5)
        valleys, _ = find_peaks(-angles_arr, distance=5)
        
        # 动态/静态姿势分类
        # 如果角度变化标准差小于阈值，认为是静态姿势
        is_static = angle_std < 5.0  # 5度阈值
        
        result[joint_name] = {
            "angle_min": round(angle_min, 2),
            "angle_max": round(angle_max, 2),
            "angle_range": round(angle_range, 2),
            "angle_mean": round(angle_mean, 2),
            "angle_std": round(angle_std, 2),
            "n_peaks": len(peaks),
            "n_valleys": len(valleys),
            "posture_type": "static" if is_static else "dynamic",
        }
    
    # 整体统计
    if result:
        all_ranges = [v["angle_range"] for v in result.values()]
        result["_summary"] = {
            "total_joints": len(result),
            "n_static": sum(1 for v in result.values() if v["posture_type"] == "static"),
            "n_dynamic": sum(1 for v in result.values() if v["posture_type"] == "dynamic"),
            "mean_angle_range": round(float(np.mean(all_ranges)), 2),
            "max_angle_range": round(float(np.max(all_ranges)), 2),
        }
    
    return result


def compute_left_right_symmetry(
    data: MocapData,
    kinematics: dict | None = None,
    left_marker_prefixes: list[str] | None = None,
    right_marker_prefixes: list[str] | None = None,
) -> dict[str, Any]:
    """
    计算左右身体运动对称性分析。
    
    依据文献: 舞蹈训练中常用的对称性指标
    
    分析左右 marker 的运动轨迹、速度、加速度的对称性。
    对于京剧身段训练有重要参考价值（如云手的左右均衡）。
    
    Args:
        data: MocapData。
        kinematics: 若已计算则传入。
        left_marker_prefixes: 左侧 marker 的前缀列表。
        right_marker_prefixes: 右侧 marker 的前缀列表。
    
    Returns:
        包含 symmetry_metrics 的字典。
    """
    from .kinematic import compute_kinematics
    
    kin = kinematics or compute_kinematics(data)
    
    if left_marker_prefixes is None:
        left_marker_prefixes = ["L_", "l_", "Left_", "left_"]
    if right_marker_prefixes is None:
        right_marker_prefixes = ["R_", "r_", "Right_", "right_"]
    
    result: dict[str, Any] = {"symmetry_metrics": {}}
    
    trajectories = kin.get("trajectories", {})
    velocities = kin.get("velocities", {})
    
    # 配对左右 marker
    left_markers = {}
    right_markers = {}
    
    for name in trajectories.keys():
        for prefix in left_marker_prefixes:
            if name.startswith(prefix):
                left_markers[name] = name
                break
        for prefix in right_marker_prefixes:
            if name.startswith(prefix):
                right_markers[name] = name
                break
    
    # 配对分析
    for (left_name, left_full), (right_name, right_full) in zip(left_markers.items(), right_markers.items()):
        # 获取轨迹
        left_traj = trajectories.get(left_name, {})
        right_traj = trajectories.get(right_name, {})
        
        if not left_traj or not right_traj:
            continue
        
        # 获取速度
        left_vel = velocities.get(left_name, {})
        right_vel = velocities.get(right_name, {})
        
        # 计算对称性指标
        symmetry_results = {}
        
        # 轨迹对称性 (X坐标的差异)
        left_x = np.array(left_traj.get("x", []), dtype=float)
        right_x = np.array(right_traj.get("x", []), dtype=float)
        
        if len(left_x) > 0 and len(right_x) > 0:
            min_len = min(len(left_x), len(right_x))
            x_diff = np.abs(left_x[:min_len] - right_x[:min_len])
            symmetry_results["position_symmetry"] = {
                "mean_diff": round(float(np.mean(x_diff)), 4),
                "max_diff": round(float(np.max(x_diff)), 4),
            }
        
        # 速度对称性
        left_speed = np.array(left_vel.get("speed", []), dtype=float)
        right_speed = np.array(right_vel.get("speed", []), dtype=float)
        
        if len(left_speed) > 0 and len(right_speed) > 0:
            min_len = min(len(left_speed), len(right_speed))
            speed_diff = np.abs(left_speed[:min_len] - right_speed[:min_len])
            speed_ratio = np.mean(left_speed[:min_len]) / (np.mean(right_speed[:min_len]) + 1e-8)
            
            symmetry_results["velocity_symmetry"] = {
                "mean_diff": round(float(np.mean(speed_diff)), 4),
                "speed_ratio": round(float(speed_ratio), 4),
            }
        
        # 相关性分析
        if len(left_x) > 0 and len(right_x) > 0:
            min_len = min(len(left_x), len(right_x))
            correlation = np.corrcoef(left_x[:min_len], right_x[:min_len])[0, 1]
            symmetry_results["correlation"] = round(float(correlation), 4)
        
        # 计算对称性得分 (0-100)
        # 基于位置差异和速度差异
        pos_sym = symmetry_results.get("position_symmetry", {}).get("mean_diff", 0)
        vel_sym = symmetry_results.get("velocity_symmetry", {}).get("mean_diff", 0)
        
        # 假设好的对称性：位置差异 < 0.05m, 速度差异 < 0.1 m/s
        score = 100
        if pos_sym > 0.05:
            score -= min(50, (pos_sym - 0.05) * 500)
        if vel_sym > 0.1:
            score -= min(50, (vel_sym - 0.1) * 200)
        
        symmetry_results["symmetry_score"] = max(0, round(score, 2))
        
        result["symmetry_metrics"][f"{left_name}_vs_{right_name}"] = symmetry_results
    
    # 整体对称性统计
    if result["symmetry_metrics"]:
        scores = [v.get("symmetry_score", 0) for v in result["symmetry_metrics"].values() if "symmetry_score" in v]
        if scores:
            result["_summary"] = {
                "mean_symmetry_score": round(float(np.mean(scores)), 2),
                "min_symmetry_score": round(float(np.min(scores)), 2),
                "max_symmetry_score": round(float(np.max(scores)), 2),
            }
    
    return result