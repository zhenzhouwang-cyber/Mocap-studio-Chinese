"""京剧特征分析：节奏、幅度、圆顺度、程式化程度。

本模块仅针对京剧动作设计，依据京剧身段、水袖技法、程式化理论。
"""

from __future__ import annotations

from typing import Any

import numpy as np

from opera_mocap_tool.io.base import MocapData


def compute_opera_features(
    data: MocapData,
    kinematics: dict | None = None,
) -> dict[str, Any]:
    """
    计算京剧特征指标。

    学理依据（京剧）：程式化理论（精选、装饰）、圆柔顺美、
    水袖技法（甩、掸、拨、扬等）、身段分类。

    Args:
        data: MocapData。
        kinematics: 若已计算则传入，否则内部计算速度等。

    Returns:
        包含 amplitude, smoothness, rhythm, stylization 等指标的字典。
    """
    from .kinematic import compute_kinematics

    kin = kinematics or compute_kinematics(data)
    fr = data.frame_rate

    result: dict[str, Any] = {
        "amplitude": {},
        "smoothness": {},
        "rhythm": {},
        "stylization": {},
    }

    for name, coords in data.markers.items():
        arr = np.array(coords, dtype=float)
        if arr.size == 0 or len(arr) < 3:
            continue

        # 幅度：位移范围
        disp = kin.get("displacement", {}).get(name, [])
        if disp:
            disp_arr = np.array(disp, dtype=float)
            valid = np.isfinite(disp_arr)
            if np.any(valid):
                result["amplitude"][name] = {
                    "mean": round(float(np.nanmean(disp_arr)), 4),
                    "max": round(float(np.nanmax(disp_arr)), 4),
                    "std": round(float(np.nanstd(disp_arr)), 4),
                }

        # 圆顺度：轨迹曲率、平滑度
        vel = kin.get("velocities", {}).get(name, {})
        speed_list = vel.get("speed", [])
        if speed_list:
            speed_arr = np.array(speed_list, dtype=float)
            # 曲率近似：加速度/速度^2
            acc = kin.get("accelerations", {}).get(name, {})
            acc_mag = acc.get("magnitude", [])
            if acc_mag:
                acc_arr = np.array(acc_mag, dtype=float)
                with np.errstate(divide="ignore", invalid="ignore"):
                    curvature = np.where(
                        speed_arr > 0.01,
                        acc_arr / (speed_arr**2 + 1e-8),
                        0,
                    )
                result["smoothness"][name] = {
                    "mean_curvature": round(float(np.nanmean(np.abs(curvature))), 4),
                    "speed_smoothness": round(float(np.nanstd(speed_arr)), 4),
                }

        # 节奏：速度变化
        if speed_list:
            speed_arr = np.array(speed_list, dtype=float)
            result["rhythm"][name] = {
                "mean_speed": round(float(np.nanmean(speed_arr)), 4),
                "max_speed": round(float(np.nanmax(speed_arr)), 4),
                "speed_variation": round(float(np.nanstd(speed_arr)), 4),
            }

    # 程式化程度：整体重复性、标准化
    all_speeds: list[float] = []
    for v in result["rhythm"].values():
        all_speeds.append(v.get("mean_speed", 0))
    if all_speeds:
        result["stylization"] = {
            "overall_mean_speed": round(float(np.mean(all_speeds)), 4),
            "overall_speed_std": round(float(np.std(all_speeds)), 4),
        }

    return result


def classify_limb(marker_name: str) -> str:
    """
    根据 marker 名称推断肢体类型（上肢/下肢/躯干/末端）。

    用于京剧水袖、身段分类分析。
    """
    name_lower = marker_name.lower()
    if any(x in name_lower for x in ["wrist", "hand", "finger", "袖", "手"]):
        return "upper_extremity"
    if any(x in name_lower for x in ["elbow", "shoulder", "arm", "臂", "肘"]):
        return "upper_limb"
    if any(x in name_lower for x in ["knee", "ankle", "foot", "toe", "膝", "脚"]):
        return "lower_limb"
    if any(x in name_lower for x in ["head", "spine", "pelvis", "头", "脊", "腰"]):
        return "trunk"
    return "unknown"
