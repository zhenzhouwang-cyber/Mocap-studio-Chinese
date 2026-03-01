"""节奏分析：速度剖面、停顿检测、节拍对齐。

针对京剧动作节奏设计，与锣鼓、唱腔配合的程式化节奏。
"""

from __future__ import annotations

from typing import Any

import numpy as np

from opera_mocap_tool.io.base import MocapData


def compute_rhythm(
    data: MocapData,
    kinematics: dict | None = None,
    speed_threshold_percentile: float = 10.0,
    min_pause_frames: int = 3,
) -> dict[str, Any]:
    """
    计算节奏相关指标：速度剖面、停顿检测。

    学理依据（京剧）：程式化节奏、锣鼓配合、动作节拍感。

    Args:
        data: MocapData。
        kinematics: 若已计算则传入。
        speed_threshold_percentile: 停顿判定为速度低于此百分位。
        min_pause_frames: 最少连续帧数才算停顿。

    Returns:
        包含 speed_profile, pauses, rhythm_stats 的字典。
    """
    from .kinematic import compute_kinematics

    kin = kinematics or compute_kinematics(data)
    fr = data.frame_rate
    dt = 1.0 / fr if fr > 0 else 0.01

    result: dict[str, Any] = {
        "speed_profile": {},
        "pauses": [],
        "rhythm_stats": {},
    }

    # 聚合所有 marker 的速度
    all_speeds: list[float] = []
    for name, vel_data in kin.get("velocities", {}).items():
        speeds = vel_data.get("speed", [])
        all_speeds.extend([s for s in speeds if np.isfinite(s)])

    if not all_speeds:
        return result

    speed_arr = np.array(all_speeds)
    threshold = np.percentile(speed_arr, speed_threshold_percentile)

    # 按时间聚合：每帧取所有 marker 的平均速度
    n_frames = data.n_frames
    frame_speeds = np.zeros(n_frames)
    counts = np.zeros(n_frames)

    for name, vel_data in kin.get("velocities", {}).items():
        speeds = vel_data.get("speed", [])
        for i, s in enumerate(speeds):
            if i < n_frames and np.isfinite(s):
                frame_speeds[i] += s
                counts[i] += 1

    with np.errstate(divide="ignore", invalid="ignore"):
        mean_speed_per_frame = np.where(counts > 0, frame_speeds / counts, np.nan)

    result["speed_profile"] = {
        "mean_speed_per_frame": [round(float(x), 4) if np.isfinite(x) else None for x in mean_speed_per_frame],
        "threshold": round(float(threshold), 4),
    }

    # 停顿检测
    is_low = mean_speed_per_frame < threshold
    is_low = np.nan_to_num(is_low, nan=False).astype(bool)

    pause_segments: list[dict] = []
    i = 0
    while i < n_frames:
        if not is_low[i]:
            i += 1
            continue
        j = i
        while j < n_frames and is_low[j]:
            j += 1
        if j - i >= min_pause_frames:
            pause_segments.append({
                "start_frame": int(i),
                "end_frame": int(j),
                "start_time": round(i * dt, 4),
                "end_time": round(j * dt, 4),
                "duration_frames": int(j - i),
                "duration_sec": round((j - i) * dt, 4),
            })
        i = j

    result["pauses"] = pause_segments

    # 节奏统计
    valid_speeds = mean_speed_per_frame[np.isfinite(mean_speed_per_frame)]
    if len(valid_speeds) > 0:
        result["rhythm_stats"] = {
            "mean_speed": round(float(np.mean(valid_speeds)), 4),
            "max_speed": round(float(np.max(valid_speeds)), 4),
            "n_pauses": len(pause_segments),
            "total_pause_sec": round(sum(p["duration_sec"] for p in pause_segments), 4),
        }

    return result
