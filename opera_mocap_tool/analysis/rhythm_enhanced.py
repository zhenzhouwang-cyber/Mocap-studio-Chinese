"""
节奏分析增强模块。

增强戏曲节奏分析功能：
- 锣鼓点时间轴对齐
- 亮相检测与分段
- 节奏可视化
- 锣鼓点模板匹配
"""

from __future__ import annotations

from typing import Any

import numpy as np

from opera_mocap_tool.io.base import MocapData


# 常见京剧锣鼓点模板
LUOGU_PATTERNS = {
    "changdian": {
        "name": "长点",
        "description": "慢速连贯的锣鼓",
        "beat_durations": [0.5, 0.5, 0.5, 0.5],  # 近似节拍时长（秒）
        "typical_speed": 0.3,  # 相对速度
    },
    "duandian": {
        "name": "短点",
        "description": "短促有力的锣鼓",
        "beat_durations": [0.2, 0.2, 0.2],
        "typical_speed": 0.7,
    },
    "kuaiban": {
        "name": "快板",
        "description": "快速连续的锣鼓",
        "beat_durations": [0.15, 0.15, 0.15, 0.15, 0.15],
        "typical_speed": 0.9,
    },
    "manban": {
        "name": "慢板",
        "description": "缓慢悠扬的锣鼓",
        "beat_durations": [0.8, 0.8, 0.8],
        "typical_speed": 0.2,
    },
    "sanban": {
        "name": "三板",
        "description": "有板无眼，节奏鲜明",
        "beat_durations": [0.3, 0.3, 0.3],
        "typical_speed": 0.6,
    },
    "yangban": {
        "name": "摇板",
        "description": "紧拉慢唱",
        "beat_durations": [0.25, 0.25],
        "typical_speed": 0.5,
    },
}


def detect_motion_boundaries(data: MocapData, kinematics: dict | None = None) -> list[dict[str, Any]]:
    """
    检测动作边界/段落分割点。
    
    基于速度变化检测动作的起始点、转折点、结束点。
    
    Args:
        data: MocapData
        kinematics: 运动学数据
        
    Returns:
        动作边界列表
    """
    if kinematics is None:
        from opera_mocap_tool.analysis.kinematic import compute_kinematics
        kinematics = compute_kinematics(data)
    
    velocities = kinematics.get("velocities", {})
    fr = data.frame_rate
    dt = 1.0 / fr if fr > 0 else 0.01
    
    # 聚合所有marker的速度
    all_speeds = []
    n_frames = data.n_frames
    
    for name, vel_data in velocities.items():
        speeds = vel_data.get("speed", [])
        if speeds:
            for i, s in enumerate(speeds):
                if i < n_frames and np.isfinite(s):
                    if i >= len(all_speeds):
                        all_speeds.append([])
                    all_speeds[i].append(s)
    
    if not all_speeds:
        return []
    
    # 计算平均速度
    mean_speeds = [np.mean(frame_speeds) if frame_speeds else 0 for frame_speeds in all_speeds]
    mean_speeds = np.array(mean_speeds)
    
    # 计算速度变化率
    speed_diff = np.diff(mean_speeds)
    
    # 找转折点（速度方向改变）
    turning_points = []
    threshold = np.std(speed_diff) * 0.5
    
    for i in range(1, len(speed_diff) - 1):
        if speed_diff[i-1] * speed_diff[i+1] < 0:  # 方向改变
            if abs(speed_diff[i]) > threshold:
                turning_points.append({
                    "frame": i + 1,
                    "time": (i + 1) * dt,
                    "type": "turning",
                    "speed_change": float(speed_diff[i]),
                })
    
    # 找静止点（速度接近0）
    pause_threshold = np.percentile(mean_speeds, 10)
    static_points = []
    
    for i in range(len(mean_speeds)):
        if mean_speeds[i] < pause_threshold:
            static_points.append({
                "frame": i,
                "time": i * dt,
                "type": "static",
                "speed": float(mean_speeds[i]),
            })
    
    return {
        "turning_points": turning_points[:20],  # 限制数量
        "static_points": static_points[:20],
    }


def detect_liangxiang(
    data: MocapData,
    kinematics: dict | None = None,
    min_pause_duration: float = 0.3,
    speed_threshold: float = 0.1,
) -> list[dict[str, Any]]:
    """
    亮相检测 - 戏曲中的静止/停顿动作。
    
    亮相是戏曲程式化动作的重要特征，表现为：
    - 动作突然停止
    - 身体保持特定姿态
    - 通常伴随锣鼓点
    
    Args:
        data: MocapData
        kinematics: 运动学数据
        min_pause_duration: 最小亮相持续时间（秒）
        speed_threshold: 速度阈值，低于此值认为静止
        
    Returns:
        亮相列表，每项包含开始帧、结束帧、持续时间
    """
    if kinematics is None:
        from opera_mocap_tool.analysis.kinematic import compute_kinematics
        kinematics = compute_kinematics(data)
    
    fr = data.frame_rate
    dt = 1.0 / fr if fr > 0 else 0.01
    n_frames = data.n_frames
    
    # 聚合速度
    all_speeds = []
    for name, vel_data in kinematics.get("velocities", {}).items():
        speeds = vel_data.get("speed", [])
        for i, s in enumerate(speeds):
            if i < n_frames and np.isfinite(s):
                if i >= len(all_speeds):
                    all_speeds.append([])
                all_speeds[i].append(s)
    
    if not all_speeds:
        return []
    
    mean_speeds = [np.mean(fs) if fs else 0 for fs in all_speeds]
    mean_speeds = np.array(mean_speeds)
    
    # 归一化速度
    max_speed = np.max(mean_speeds)
    if max_speed > 0:
        norm_speeds = mean_speeds / max_speed
    else:
        norm_speeds = mean_speeds
    
    # 检测低速区间（亮相候选）
    min_frames = int(min_pause_duration * fr)
    is_static = norm_speeds < speed_threshold
    
    lixiang_list = []
    i = 0
    while i < n_frames:
        if is_static[i]:
            j = i
            while j < n_frames and is_static[j]:
                j += 1
            
            duration = (j - i) * dt
            if duration >= min_pause_duration:
                # 分析亮相姿态
                lixiang_list.append({
                    "start_frame": i,
                    "end_frame": j - 1,
                    "start_time": round(i * dt, 3),
                    "end_time": round((j - 1) * dt, 3),
                    "duration_sec": round(duration, 3),
                    "duration_frames": j - i,
                    "mean_speed": round(float(np.mean(mean_speeds[i:j])), 4),
                    "max_speed": round(float(np.max(mean_speeds[i:j])), 4),
                })
            i = j
        else:
            i += 1
    
    return lixiang_list


def align_luogu(
    data: MocapData,
    lixiang_list: list[dict[str, Any]],
    kinematics: dict | None = None,
) -> list[dict[str, Any]]:
    """
    锣鼓点对齐 - 将动作与锣鼓点模板匹配。
    
    基于动作的速度特征推断可能的锣鼓点类型。
    
    Args:
        data: MocapData
        lixiang_list: 亮相列表
        kinematics: 运动学数据
        
    Returns:
        锣鼓点对齐结果
    """
    if kinematics is None:
        from opera_mocap_tool.analysis.kinematic import compute_kinematics
        kinematics = compute_kinematics(data)
    
    fr = data.frame_rate
    dt = 1.0 / fr if fr > 0 else 0.01
    
    # 计算动作整体速度特征
    velocities = kinematics.get("velocities", {})
    all_speeds = []
    for name, vel_data in velocities.items():
        speeds = vel_data.get("speed", [])
        all_speeds.extend([s for s in speeds if np.isfinite(s)])
    
    if not all_speeds:
        return []
    
    speed_arr = np.array(all_speeds)
    mean_speed = np.mean(speed_arr)
    max_speed = np.max(speed_arr)
    
    # 速度比
    speed_ratio = mean_speed / max_speed if max_speed > 0 else 0
    
    # 匹配锣鼓点类型
    matched_patterns = []
    
    for pattern_key, pattern_info in LUOGU_PATTERNS.items():
        # 计算速度相似度
        speed_diff = abs(speed_ratio - pattern_info["typical_speed"])
        confidence = 1.0 - speed_diff
        
        if confidence > 0.5:  # 置信度阈值
            matched_patterns.append({
                "pattern": pattern_key,
                "name": pattern_info["name"],
                "description": pattern_info["description"],
                "confidence": round(confidence, 3),
            })
    
    # 按置信度排序
    matched_patterns.sort(key=lambda x: x["confidence"], reverse=True)
    
    # 为每个亮相段分配锣鼓点
    lixiang_with_luogu = []
    for lixiang in lixiang_list:
        # 提取该时段的速度特征
        lixiang_speeds = speed_arr[int(lixiang["start_frame"] * fr):int(lixiang["end_frame"] * fr)]
        
        if len(lixiang_speeds) > 0:
            lx_mean = np.mean(lixiang_speeds)
            lx_max = np.max(lixiang_speeds)
            lx_ratio = lx_mean / lx_max if lx_max > 0 else 0
            
            # 匹配
            best_pattern = None
            best_conf = 0
            for pattern_key, pinfo in LUOGU_PATTERNS.items():
                diff = abs(lx_ratio - pinfo["typical_speed"])
                conf = 1.0 - diff
                if conf > best_conf:
                    best_conf = conf
                    best_pattern = {
                        "pattern": pattern_key,
                        "name": pinfo["name"],
                    }
            
            lixiang_with_luogu.append({
                **lixiang,
                "luogu": best_pattern,
                "confidence": round(best_conf, 3) if best_pattern else None,
            })
        else:
            lixiang_with_luogu.append(lixiang)
    
    return {
        "matched_patterns": matched_patterns[:3],
        "lixiang_with_luogu": lixiang_with_luogu,
    }


def compute_rhythm_enhanced(
    data: MocapData,
    kinematics: dict | None = None,
) -> dict[str, Any]:
    """
    增强版节奏分析。
    
    整合亮相检测、锣鼓点对齐、动作分段。
    
    Args:
        data: MocapData
        kinematics: 运动学数据
        
    Returns:
        增强版节奏分析结果
    """
    if kinematics is None:
        from opera_mocap_tool.analysis.kinematic import compute_kinematics
        kinematics = compute_kinematics(data)
    
    # 原有节奏分析
    from opera_mocap_tool.analysis.rhythm import compute_rhythm
    basic_rhythm = compute_rhythm(data, kinematics)
    
    # 检测亮相
    lixiang = detect_liangxiang(data, kinematics)
    
    # 锣鼓点对齐
    luogu = align_luogu(data, lixiang, kinematics)
    
    # 动作边界检测
    boundaries = detect_motion_boundaries(data, kinematics)
    
    # 节奏统计
    fr = data.frame_rate
    dt = 1.0 / fr if fr > 0 else 0.01
    
    rhythm_stats = {
        "total_lixiang": len(lixiang),
        "total_lixiang_duration": sum(lx["duration_sec"] for lx in lixiang),
        "lixiang_ratio": sum(lx["duration_sec"] for lx in lixiang) / data.duration_sec if data.duration_sec > 0 else 0,
        "best_luogu_pattern": luogu.get("matched_patterns", [{}])[0].get("name") if luogu.get("matched_patterns") else None,
        "n_turning_points": len(boundaries.get("turning_points", [])),
    }
    
    return {
        **basic_rhythm,
        "lixiang": lixiang,
        "luogu": luogu,
        "boundaries": boundaries,
        "rhythm_stats_enhanced": rhythm_stats,
    }


def visualize_rhythm(
    data: MocapData,
    rhythm_result: dict[str, Any],
) -> dict[str, Any]:
    """
    生成节奏可视化数据。
    
    Args:
        data: MocapData
        rhythm_result: 节奏分析结果
        
    Returns:
        可视化数据字典
    """
    fr = data.frame_rate
    dt = 1.0 / fr if fr > 0 else 0.01
    n_frames = data.n_frames
    
    # 生成时间轴
    times = [i * dt for i in range(n_frames)]
    
    # 速度曲线
    speed_profile = rhythm_result.get("speed_profile", {})
    speeds = speed_profile.get("mean_speed_per_frame", [])
    
    # 亮相区间
    lixiang = rhythm_result.get("lixiang", [])
    lixiang_regions = [(lx["start_time"], lx["end_time"]) for lx in lixiang]
    
    # 锣鼓点
    luogu = rhythm_result.get("luogu", {})
    patterns = luogu.get("matched_patterns", [])
    
    return {
        "times": times,
        "speeds": speeds,
        "lixiang_regions": lixiang_regions,
        "luogu_patterns": patterns,
        "lixiang": lixiang,
    }
