"""
拉班近似特征：从轨迹与速度派生 Space / Effort / Shape 的近似量。

用于与舞蹈学/戏曲学界对话，及艺术创作中的风格化通道导出。
"""

from __future__ import annotations

from typing import Any

import numpy as np


def compute_laban_approx(
    result: dict,
    *,
    kinematics: dict | None = None,
) -> dict[str, Any]:
    """
    从分析结果计算拉班四要素的近似指标（Space, Effort, Shape）。

    不依赖完整拉班记谱，仅输出可计算的标量，便于论文引用与通道导出。

    Args:
        result: 动捕分析结果（含 meta, kinematics 或需从 result 取 kinematics）。
        kinematics: 若已计算可传入，否则从 result 取。

    Returns:
        laban_approx: {
            "space": { "span_left_right", "span_high_low", "span_forward_back", "center_velocity" },
            "effort": { "mean_speed", "std_speed", "mean_acc", "std_acc" },
            "shape": { "expansion_mean", "expansion_std" }
        }
    """
    kin = kinematics or result.get("kinematics", {})
    meta = result.get("meta", {})
    marker_labels = meta.get("marker_labels", [])
    fr = float(meta.get("frame_rate", 100))
    dt = 1.0 / fr if fr > 0 else 0.01

    trajectories = kin.get("trajectories", {})
    velocities = kin.get("velocities", {})
    accelerations = kin.get("accelerations", {})

    if not trajectories:
        return {
            "space": {},
            "effort": {},
            "shape": {},
        }

    # 合并所有 marker 的轨迹为 (n_frames, n_markers*3) 或逐帧处理
    n_frames = 0
    for name in marker_labels:
        if name in trajectories:
            n_frames = len(trajectories[name]["x"])
            break
    if n_frames == 0:
        return {"space": {}, "effort": {}, "shape": {}}

    # 重心与空间范围（Space）
    xs, ys, zs = [], [], []
    for name in marker_labels:
        if name not in trajectories:
            continue
        t = trajectories[name]
        xs.append(np.array(t["x"], dtype=float))
        ys.append(np.array(t["y"], dtype=float))
        zs.append(np.array(t["z"], dtype=float))
    if not xs:
        return {"space": {}, "effort": {}, "shape": {}}

    X = np.stack(xs, axis=1)  # (n_frames, n_m)
    Y = np.stack(ys, axis=1)
    Z = np.stack(zs, axis=1)
    valid = np.isfinite(X) & np.isfinite(Y) & np.isfinite(Z)
    X_safe = np.where(valid, X, np.nan)
    Y_safe = np.where(valid, Y, np.nan)
    Z_safe = np.where(valid, Z, np.nan)

    center_x = np.nanmean(X_safe, axis=1)
    center_y = np.nanmean(Y_safe, axis=1)
    center_z = np.nanmean(Z_safe, axis=1)
    span_lr = float(np.nanmax(center_x) - np.nanmin(center_x)) if np.any(np.isfinite(center_x)) else 0.0
    span_hl = float(np.nanmax(center_y) - np.nanmin(center_y)) if np.any(np.isfinite(center_y)) else 0.0
    span_fb = float(np.nanmax(center_z) - np.nanmin(center_z)) if np.any(np.isfinite(center_z)) else 0.0

    center_vel = np.gradient(np.stack([center_x, center_y, center_z], axis=1), dt, axis=0)
    center_speed = np.linalg.norm(center_vel, axis=1)
    center_velocity_mean = float(np.nanmean(center_speed)) if np.any(np.isfinite(center_speed)) else 0.0

    space = {
        "span_left_right": round(span_lr, 4),
        "span_high_low": round(span_hl, 4),
        "span_forward_back": round(span_fb, 4),
        "center_velocity_mean": round(center_velocity_mean, 4),
    }

    # Effort：速度与加速度的轻重、快慢
    all_speeds: list[float] = []
    all_accs: list[float] = []
    for name in marker_labels:
        if name in velocities:
            s = velocities[name].get("speed", [])
            all_speeds.extend([x for x in s if x is not None and np.isfinite(x)])
        if name in accelerations:
            a = accelerations[name].get("magnitude", [])
            all_accs.extend([x for x in a if x is not None and np.isfinite(x)])
    effort = {
        "mean_speed": round(float(np.mean(all_speeds)), 4) if all_speeds else 0.0,
        "std_speed": round(float(np.std(all_speeds)), 4) if all_speeds else 0.0,
        "mean_acc": round(float(np.mean(all_accs)), 4) if all_accs else 0.0,
        "std_acc": round(float(np.std(all_accs)), 4) if all_accs else 0.0,
    }

    # Shape：身体扩展/收拢（各帧重心到各 marker 的平均距离）
    expansion_per_frame = []
    for i in range(n_frames):
        cx, cy, cz = center_x[i], center_y[i], center_z[i]
        if not np.isfinite(cx + cy + cz):
            continue
        dists = np.sqrt((X_safe[i, :] - cx) ** 2 + (Y_safe[i, :] - cy) ** 2 + (Z_safe[i, :] - cz) ** 2)
        valid_d = np.isfinite(dists)
        if np.any(valid_d):
            expansion_per_frame.append(float(np.nanmean(dists)))
    if expansion_per_frame:
        shape = {
            "expansion_mean": round(float(np.mean(expansion_per_frame)), 4),
            "expansion_std": round(float(np.std(expansion_per_frame)), 4),
        }
    else:
        shape = {"expansion_mean": 0.0, "expansion_std": 0.0}

    return {
        "space": space,
        "effort": effort,
        "shape": shape,
    }
