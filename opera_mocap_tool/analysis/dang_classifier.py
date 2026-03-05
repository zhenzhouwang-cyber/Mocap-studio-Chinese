"""
行当判定增强模块。

融合多维度特征进行行当判定：
- 高度特征（原有）
- 幅度特征（手腕活动范围）
- 速度特征（动作刚柔）
- 风格特征（基于拉班运动分析）

增强判定：老生/武生/旦角/丑行/武旦
"""

from __future__ import annotations

from typing import Any

import numpy as np

from opera_mocap_tool.io.base import MocapData


# 增强版行当判定标准
DANG_MULTI_DIM_RULES = {
    "laosheng": {
        "name": "老生",
        "standard": "齐眉",
        "height_range": (0.70, 1.0),
        "amplitude_range": (0.3, 0.6),  # 归一化幅度
        "speed_range": (0.2, 0.5),  # 相对速度较低，表现沉稳
        "style_keywords": ["沉稳", "庄重", "儒雅"],
    },
    "wusheng": {
        "name": "武生",
        "standard": "齐口",
        "height_range": (0.55, 0.80),
        "amplitude_range": (0.5, 0.9),  # 幅度较大
        "speed_range": (0.5, 1.0),  # 速度快
        "style_keywords": ["刚健", "有力", "勇猛"],
    },
    "danjiao": {
        "name": "旦角",
        "standard": "齐胸",
        "height_range": (0.35, 0.60),
        "amplitude_range": (0.3, 0.6),
        "speed_range": (0.3, 0.6),  # 速度适中
        "style_keywords": ["柔美", "典雅", "含蓄"],
    },
    "chou": {
        "name": "丑行",
        "standard": "齐腹",
        "height_range": (0.20, 0.45),
        "amplitude_range": (0.2, 0.5),
        "speed_range": (0.4, 0.8),  # 速度变化大
        "style_keywords": ["灵活", "诙谐", "敏捷"],
    },
    "wudan": {
        "name": "武旦",
        "standard": "齐胸",
        "height_range": (0.40, 0.65),
        "amplitude_range": (0.5, 0.9),
        "speed_range": (0.6, 1.0),  # 速度快
        "style_keywords": ["敏捷", "勇猛", "泼辣"],
    },
}


def compute_amplitude_features(data: MocapData, kinematics: dict | None = None) -> dict[str, Any]:
    """
    计算幅度特征 - 手腕活动范围。
    
    Args:
        data: MocapData
        kinematics: 运动学数据
        
    Returns:
        幅度特征字典
    """
    if kinematics is None:
        from opera_mocap_tool.analysis.kinematic import compute_kinematics
        kinematics = compute_kinematics(data)
    
    # 获取手腕轨迹
    wrist_names = ["wrist_left", "wrist_right", "lwrist", "rwrist"]
    trajectories = kinematics.get("trajectories", {})
    
    amplitudes = {}
    for side in ["left", "right"]:
        for prefix in ["", "l", "r"]:
            name = f"wrist_{side}" if prefix == "" else f"{prefix}wrist"
            if name in trajectories:
                traj = trajectories[name]
                x = np.array(traj.get("x", []), dtype=float)
                y = np.array(traj.get("y", []), dtype=float)
                z = np.array(traj.get("z", []), dtype=float)
                
                if len(x) > 0 and len(y) > 0 and len(z) > 0:
                    # 计算各轴幅度
                    amp_x = np.nanmax(x) - np.nanmin(x)
                    amp_y = np.nanmax(y) - np.nanmin(y)
                    amp_z = np.nanmax(z) - np.nanmin(z)
                    
                    # 总幅度（欧氏距离范围）
                    total_range = np.sqrt(amp_x**2 + amp_y**2 + amp_z**2)
                    
                    amplitudes[name] = {
                        "range_x": float(amp_x),
                        "range_y": float(amp_y),
                        "range_z": float(amp_z),
                        "total_range": float(total_range),
                    }
    
    # 计算归一化幅度（相对于身高/躯干）
    shoulder_y = None
    hip_y = None
    
    for name in ["shoulder_left", "shoulder_right", "shoulder"]:
        if name in trajectories:
            y = np.array(trajectories[name].get("y", []), dtype=float)
            if len(y) > 0:
                shoulder_y = np.nanmean(y)
                break
    
    for name in ["hip_left", "hip_right", "hip"]:
        if name in trajectories:
            y = np.array(trajectories[name].get("y", []), dtype=float)
            if len(y) > 0:
                hip_y = np.nanmean(y)
                break
    
    norm_amplitude = None
    if shoulder_y and hip_y:
        torso_height = shoulder_y - hip_y
        if torso_height > 0 and amplitudes:
            # 取最大幅度归一化
            max_range = max(a["total_range"] for a in amplitudes.values())
            norm_amplitude = max_range / torso_height
    
    return {
        "amplitudes": amplitudes,
        "normalized_amplitude": float(norm_amplitude) if norm_amplitude else None,
        "mean_range_x": float(np.mean([a["range_x"] for a in amplitudes.values()])) if amplitudes else 0,
        "mean_range_y": float(np.mean([a["range_y"] for a in amplitudes.values()])) if amplitudes else 0,
        "mean_range_z": float(np.mean([a["range_z"] for a in amplitudes.values()])) if amplitudes else 0,
    }


def compute_speed_features(data: MocapData, kinematics: dict | None = None) -> dict[str, Any]:
    """
    计算速度特征 - 动作的刚柔表现。
    
    Args:
        data: MocapData
        kinematics: 运动学数据
        
    Returns:
        速度特征字典
    """
    if kinematics is None:
        from opera_mocap_tool.analysis.kinematic import compute_kinematics
        kinematics = compute_kinematics(data)
    
    # 获取手腕速度
    wrist_names = ["wrist_left", "wrist_right", "lwrist", "rwrist"]
    velocities = kinematics.get("velocities", {})
    
    all_speeds = []
    for name in wrist_names:
        if name in velocities:
            speeds = velocities[name].get("speed", [])
            all_speeds.extend([s for s in speeds if np.isfinite(s)])
    
    if not all_speeds:
        return {"mean_speed": 0, "max_speed": 0, "speed_variance": 0, "relative_speed": 0}
    
    speed_arr = np.array(all_speeds)
    
    # 计算速度统计
    mean_speed = np.mean(speed_arr)
    max_speed = np.max(speed_arr)
    std_speed = np.std(speed_arr)
    
    # 计算相对速度（相对于躯干大小）
    # 假设平均人身高的速度归一化约为1.5m/s
    relative_speed = mean_speed / 1.5 if mean_speed > 0 else 0
    
    return {
        "mean_speed": float(mean_speed),
        "max_speed": float(max_speed),
        "speed_variance": float(std_speed),
        "relative_speed": float(relative_speed),
    }


def compute_style_features(data: MocapData, kinematics: dict | None = None) -> dict[str, Any]:
    """
    计算风格特征 - 基于拉班运动分析的动静刚柔。
    
    使用拉班的 Effort（力效）维度：
    - Weight（轻重）：动作力度
    - Time（缓急）：动作速度
    - Space（Direct/Indirect）：动作空间直接性
    - Flow（Free/Bound）：动作流畅度
    
    Args:
        data: MocapData
        kinematics: 运动学数据
        
    Returns:
        风格特征字典
    """
    if kinematics is None:
        from opera_mocap_tool.analysis.kinematic import compute_kinematics
        kinematics = compute_kinematics(data)
    
    # 获取所有可用的速度数据
    velocities = kinematics.get("velocities", {})
    trajectories = kinematics.get("trajectories", {})
    
    all_speeds = []
    all_accelerations = []
    
    for name, vel_data in velocities.items():
        speeds = vel_data.get("speed", [])
        all_speeds.extend([s for s in speeds if np.isfinite(s)])
        
        # 计算加速度
        if speeds and len(speeds) > 1:
            acc = np.diff([s for s in speeds if np.isfinite(s)])
            all_accelerations.extend(np.abs(acc))
    
    # Weight (轻重) - 基于加速度
    weight_score = 0.5
    if all_accelerations:
        mean_acc = np.mean(all_accelerations)
        weight_score = min(1.0, mean_acc / 50)  # 归一化
    
    # Time (缓急) - 基于速度
    time_score = 0.5
    if all_speeds:
        mean_speed = np.mean(all_speeds)
        time_score = min(1.0, mean_speed / 100)
    
    # Flow (流畅) - 基于速度变化平滑度
    flow_score = 0.5
    if len(all_speeds) > 10:
        speed_arr = np.array(all_speeds)
        # 计算变化率
        speed_changes = np.abs(np.diff(speed_arr))
        flow_score = 1.0 - min(1.0, np.mean(speed_changes) / 20)
    
    # Space - 基于轨迹的直线性
    space_score = 0.5
    wrist_names = ["wrist_left", "wrist_right"]
    for name in wrist_names:
        if name in trajectories:
            traj = trajectories[name]
            x = np.array(traj.get("x", []), dtype=float)
            z = np.array(traj.get("z", []), dtype=float)
            
            if len(x) > 10:
                # 计算总位移与路径长度的比值
                total_disp = np.sqrt((x[-1] - x[0])**2 + (z[-1] - z[0])**2)
                path_length = np.sum(np.sqrt(np.diff(x)**2 + np.diff(z)**2))
                
                if path_length > 0:
                    space_score = total_disp / path_length  # 越接近1越直接
                    break
    
    return {
        "weight": round(weight_score, 3),  # 0=轻, 1=重
        "time": round(time_score, 3),  # 0=缓, 1=急
        "flow": round(flow_score, 3),  # 0=紧, 1=畅
        "space": round(space_score, 3),  # 0=间接, 1=直接
        "style_vector": [weight_score, time_score, flow_score, space_score],
    }


def classify_dang_enhanced(
    data: MocapData,
    kinematics: dict | None = None,
) -> dict[str, Any]:
    """
    增强版行当判定 - 融合多维度特征。
    
    Args:
        data: MocapData
        kinematics: 运动学数据
        
    Returns:
        增强版行当判定结果
    """
    # 计算各维度特征
    amplitude_feat = compute_amplitude_features(data, kinematics)
    speed_feat = compute_speed_features(data, kinematics)
    style_feat = compute_style_features(data, kinematics)
    
    # 获取原有高度判定
    from opera_mocap_tool.analysis.yunshou_features import classify_dang_by_height
    height_result = classify_dang_by_height(data)
    
    # 多维度融合判定
    scores = {}
    
    for dang_key, rules in DANG_MULTI_DIM_RULES.items():
        score = 0.0
        weights = {"height": 0.4, "amplitude": 0.3, "speed": 0.3}
        
        # 高度评分
        height_norm = height_result.get("hand_height_norm", 0.5)
        h_min, h_max = rules["height_range"]
        if h_min <= height_norm <= h_max:
            height_score = 1.0 - abs(height_norm - (h_min + h_max) / 2) / ((h_max - h_min) / 2)
            height_score = max(0, min(1, height_score))
        else:
            height_score = max(0, 1 - abs(height_norm - (h_min + h_max) / 2))
        score += weights["height"] * height_score
        
        # 幅度评分
        norm_amp = amplitude_feat.get("normalized_amplitude", 0.5)
        if norm_amp:
            a_min, a_max = rules["amplitude_range"]
            if a_min <= norm_amp <= a_max:
                amp_score = 1.0 - abs(norm_amp - (a_min + a_max) / 2) / ((a_max - a_min) / 2)
                amp_score = max(0, min(1, amp_score))
            else:
                amp_score = max(0, 1 - abs(norm_amp - (a_min + a_max) / 2))
        else:
            amp_score = 0.5
        score += weights["amplitude"] * amp_score
        
        # 速度评分
        rel_speed = speed_feat.get("relative_speed", 0.5)
        s_min, s_max = rules["speed_range"]
        if s_min <= rel_speed <= s_max:
            speed_score = 1.0 - abs(rel_speed - (s_min + s_max) / 2) / ((s_max - s_min) / 2)
            speed_score = max(0, min(1, speed_score))
        else:
            speed_score = max(0, 1 - abs(rel_speed - (s_min + s_max) / 2))
        score += weights["speed"] * speed_score
        
        scores[dang_key] = round(score, 3)
    
    # 选择最高分
    best_dang = max(scores, key=scores.get)
    best_score = scores[best_dang]
    
    # 获取风格描述
    style_keywords = DANG_MULTI_DIM_RULES[best_dang]["style_keywords"]
    
    # 综合判断
    return {
        "dang": best_dang,
        "dang_cn": DANG_MULTI_DIM_RULES[best_dang]["name"],
        "confidence": best_score,
        "all_scores": scores,
        "height_result": height_result,
        "amplitude": amplitude_feat,
        "speed": speed_feat,
        "style": style_feat,
        "style_keywords": style_keywords,
        "description": f"{DANG_MULTI_DIM_RULES[best_dang]['name']} - {DANG_MULTI_DIM_RULES[best_dang]['standard']}，风格特征：{', '.join(style_keywords)}",
    }


def quick_classify_dang(data: MocapData) -> dict[str, Any]:
    """
    快速行当判定（简化版）。
    
    Args:
        data: MocapData
        
    Returns:
        简化判定结果
    """
    return classify_dang_enhanced(data)
