"""身段段落切分：基于节奏停顿与幅度，输出动作段（供唱做对照、学术引用）。"""

from __future__ import annotations

from typing import Any

import numpy as np

from opera_mocap_tool.io.base import MocapData
from .opera_features import classify_limb


def compute_action_segments(
    data: MocapData,
    kinematics: dict,
    rhythm: dict,
) -> list[dict[str, Any]]:
    """
    根据节奏停顿与幅度切分身段段落。

    学理依据：程式化节奏、段落与唱腔/曲牌对照。每段含 start_time, end_time,
    mean_amplitude, dominant_limb。

    Args:
        data: MocapData。
        kinematics: 已计算的运动学（需含 displacement）。
        rhythm: 已计算的节奏（需含 pauses，含 start_time/end_time）。

    Returns:
        动作段列表，每项为 {"start_time", "end_time", "mean_amplitude", "dominant_limb"}。
    """
    fr = data.frame_rate
    n_frames = data.n_frames
    duration_sec = (n_frames - 1) / fr if fr > 0 else 0

    pauses = rhythm.get("pauses", [])
    disp = kinematics.get("displacement", {})

    # 由停顿得到「非停顿」区间（动作段）
    bounds: list[tuple[float, float]] = []
    t_prev = 0.0
    for p in sorted(pauses, key=lambda x: x["start_time"]):
        start_t = float(p["start_time"])
        end_t = float(p["end_time"])
        if start_t > t_prev + 0.02:  # 至少 20ms 才成段
            bounds.append((t_prev, start_t))
        t_prev = max(t_prev, end_t)
    if t_prev < duration_sec - 0.02:
        bounds.append((t_prev, duration_sec))

    if not bounds:
        bounds = [(0.0, duration_sec)]

    # 每段内：帧范围
    segments_out: list[dict[str, Any]] = []
    limb_names = {"upper_extremity": "上肢末端", "upper_limb": "上肢", "lower_limb": "下肢", "trunk": "躯干", "unknown": "其他"}

    for start_t, end_t in bounds:
        start_f = max(0, int(start_t * fr))
        end_f = min(n_frames, int(np.ceil(end_t * fr)))
        if end_f <= start_f:
            end_f = start_f + 1

        # 该段内每帧的「全体 marker 位移均值」
        frame_amps: list[float] = []
        limb_sums: dict[str, list[float]] = {}

        for i in range(start_f, end_f):
            row_amp: list[float] = []
            for name in data.marker_labels:
                if name not in disp:
                    continue
                d_list = disp[name]
                if i < len(d_list) and d_list[i] is not None and np.isfinite(d_list[i]):
                    row_amp.append(float(d_list[i]))
                    limb = classify_limb(name)
                    if limb not in limb_sums:
                        limb_sums[limb] = []
                    limb_sums[limb].append(float(d_list[i]))
            if row_amp:
                frame_amps.append(np.mean(row_amp))

        mean_amplitude = round(float(np.mean(frame_amps)), 4) if frame_amps else 0.0
        dominant_limb = "unknown"
        if limb_sums:
            limb_means = {k: np.mean(v) for k, v in limb_sums.items()}
            dominant_limb = max(limb_means, key=limb_means.get)
        dominant_limb_display = limb_names.get(dominant_limb, dominant_limb)

        segments_out.append({
            "start_time": round(start_t, 4),
            "end_time": round(end_t, 4),
            "mean_amplitude": mean_amplitude,
            "dominant_limb": dominant_limb,
            "dominant_limb_display": dominant_limb_display,
        })

    return segments_out


def compute_motion_phases(
    data: MocapData,
    kinematics: dict | None = None,
) -> dict[str, Any]:
    """
    增强的动作分段：基于速度曲线的动作阶段检测。
    
    依据文献: 京剧程式化动作分析
    
    将动作分为"起、承、转、合"四个阶段：
    - 起：动作开始，加速阶段
    - 承：动作持续，速度稳定
    - 转：动作变化，速度波动
    - 合：动作结束，减速阶段
    
    Args:
        data: MocapData。
        kinematics: 若已计算则传入。
    
    Returns:
        包含 motion_phases 的字典。
    """
    from .kinematic import compute_kinematics
    
    kin = kinematics or compute_kinematics(data)
    fr = data.frame_rate
    n_frames = data.n_frames
    
    result: dict[str, Any] = {"motion_phases": []}
    
    velocities = kin.get("velocities", {})
    if not velocities:
        return result
    
    # 使用第一个有效 marker 的速度进行分析
    for name, vel_data in velocities.items():
        speed = np.array(vel_data.get("speed", []), dtype=float)
        if len(speed) < 10:
            continue
        
        # 计算速度变化率（加速度）
        speed_diff = np.diff(speed)
        
        # 识别四个阶段
        phases = []
        n = len(speed)
        
        # 简单分段策略
        # 起：前 20% 帧
        # 承：20%-50% 帧
        # 转：50%-80% 帧  
        # 合：后 20% 帧
        
        quarter = n // 4
        
        if quarter > 0:
            # 起阶段
            start_phase = speed[:quarter]
            phases.append({
                "phase": "起 (Initiation)",
                "start_frame": 0,
                "end_frame": quarter,
                "start_time": 0.0,
                "end_time": round(quarter / fr, 3),
                "mean_speed": round(float(np.mean(start_phase)), 4),
                "speed_trend": "accelerating" if np.mean(speed_diff[:quarter]) > 0 else "decelerating",
            })
            
            # 承阶段
            sustain_phase = speed[quarter:quarter*2]
            phases.append({
                "phase": "承 (Sustain)",
                "start_frame": quarter,
                "end_frame": quarter * 2,
                "start_time": round(quarter / fr, 3),
                "end_time": round(quarter * 2 / fr, 3),
                "mean_speed": round(float(np.mean(sustain_phase)), 4),
                "speed_trend": "stable",
            })
            
            # 转阶段
            transition_phase = speed[quarter*2:quarter*3]
            phases.append({
                "phase": "转 (Transition)",
                "start_frame": quarter * 2,
                "end_frame": quarter * 3,
                "start_time": round(quarter * 2 / fr, 3),
                "end_time": round(quarter * 3 / fr, 3),
                "mean_speed": round(float(np.mean(transition_phase)), 4),
                "speed_trend": "varying",
            })
            
            # 合阶段
            end_phase = speed[quarter*3:]
            phases.append({
                "phase": "合 (Conclusion)",
                "start_frame": quarter * 3,
                "end_frame": n,
                "start_time": round(quarter * 3 / fr, 3),
                "end_time": round(n / fr, 3),
                "mean_speed": round(float(np.mean(end_phase)), 4),
                "speed_trend": "decelerating" if np.mean(speed_diff[quarter*3:]) < 0 else "accelerating",
            })
        
        result["motion_phases"] = phases
        break
    
    return result


def detect_motion_boundaries(
    data: MocapData,
    kinematics: dict | None = None,
    velocity_threshold_percentile: float = 25.0,
    min_segment_frames: int = 10,
) -> dict[str, Any]:
    """
    基于速度曲线的动作边界检测。
    
    自动识别动作的开始和结束位置，用于动作分段。
    
    Args:
        data: MocapData。
        kinematics: 若已计算则传入。
        velocity_threshold_percentile: 速度百分位阈值。
        min_segment_frames: 最小动作段帧数。
    
    Returns:
        包含 motion_boundaries 的字典。
    """
    from .kinematic import compute_kinematics
    
    kin = kinematics or compute_kinematics(data)
    fr = data.frame_rate
    n_frames = data.n_frames
    
    result: dict[str, Any] = {"motion_boundaries": []}
    
    velocities = kin.get("velocities", {})
    if not velocities:
        return result
    
    # 聚合所有 marker 的速度
    all_speeds = []
    for name, vel_data in velocities.items():
        speed = vel_data.get("speed", [])
        if speed:
            all_speeds.append(np.array(speed, dtype=float))
    
    if not all_speeds:
        return result
    
    # 计算平均速度
    max_len = max(len(s) for s in all_speeds)
    avg_speed = np.zeros(max_len)
    count = np.zeros(max_len)
    
    for s in all_speeds:
        avg_speed[:len(s)] += s
        count[:len(s)] += 1
    
    avg_speed = avg_speed / np.maximum(count, 1)
    
    # 计算阈值
    threshold = np.percentile(avg_speed[avg_speed > 0], velocity_threshold_percentile)
    
    # 识别动作边界
    is_active = avg_speed > threshold
    
    boundaries = []
    in_motion = False
    motion_start = 0
    
    for i, active in enumerate(is_active):
        if active and not in_motion:
            motion_start = i
            in_motion = True
        elif not active and in_motion:
            if i - motion_start >= min_segment_frames:
                boundaries.append({
                    "start_frame": motion_start,
                    "end_frame": i,
                    "start_time": round(motion_start / fr, 3),
                    "end_time": round(i / fr, 3),
                    "duration_frames": i - motion_start,
                    "duration_sec": round((i - motion_start) / fr, 3),
                })
            in_motion = False
    
    # 处理最后一段
    if in_motion and n_frames - motion_start >= min_segment_frames:
        boundaries.append({
            "start_frame": motion_start,
            "end_frame": n_frames,
            "start_time": round(motion_start / fr, 3),
            "end_time": round(n_frames / fr, 3),
            "duration_frames": n_frames - motion_start,
            "duration_sec": round((n_frames - motion_start) / fr, 3),
        })
    
    result["motion_boundaries"] = boundaries
    result["n_segments"] = len(boundaries)
    
    return result