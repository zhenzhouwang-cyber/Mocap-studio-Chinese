"""
云手数据到生成艺术的参数映射模块。

将云手分析结果映射为TouchDesigner可用的参数：
- 轨迹 → 粒子发射位置
- 速度/加速度 → 流动强度、色彩
- 圆度 → 螺旋紧密程度
- 对称性 → 镜像效果
- 节奏停顿 → 呼吸闪烁
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


# 行当对应的色彩基调
DANG_COLOR_PALETTES = {
    "laosheng": {
        "name": "老生",
        "primary": "#2C3E50",    # 深蓝
        "secondary": "#ECF0F1",   # 浅灰白
        "accent": "#3498DB",      # 蓝色
    },
    "wusheng": {
        "name": "武生",
        "primary": "#C0392B",     # 深红
        "secondary": "#E74C3C",   # 红色
        "accent": "#F39C12",      # 橙色
    },
    "danjiao": {
        "name": "旦角",
        "primary": "#E8D5B7",     # 淡粉
        "secondary": "#F5E6D3",   # 米白
        "accent": "#F8B4B4",      # 浅红
    },
    "chou": {
        "name": "丑行",
        "primary": "#F39C12",     # 金色
        "secondary": "#F1C40F",   # 黄色
        "accent": "#E67E22",      # 橙色
    },
    "unknown": {
        "name": "未知",
        "primary": "#95A5A6",     # 灰色
        "secondary": "#BDC3C7",   # 浅灰
        "accent": "#7F8C8D",      # 深灰
    },
}


def map_to_touchdesigner(yunshou_result: dict, metadata: dict | None = None) -> dict[str, Any]:
    """
    将云手分析结果映射为TouchDesigner参数。
    
    Args:
        yunshou_result: analyze_yunshou() 返回的结果
        metadata: 可选的元数据（如文件信息）
        
    Returns:
        TouchDesigner可用的参数字典
    """
    # 提取各项特征
    dang = yunshou_result.get("dang", {})
    three_section = yunshou_result.get("three_section", {})
    fancheng = yunshou_result.get("fancheng_jin", {})
    circularity = yunshou_result.get("circularity", {})
    trajectories = yunshou_result.get("trajectories", {})
    rhythm = yunshou_result.get("rhythm", {})
    laban = yunshou_result.get("laban", {})
    
    # 获取行当
    dang_type = dang.get("dang", "unknown")
    color_palette = DANG_COLOR_PALETTES.get(dang_type, DANG_COLOR_PALETTES["unknown"])
    
    # 构建参数映射
    params = {
        # 基本信息
        "meta": {
            "dang": dang_type,
            "dang_name": color_palette["name"],
            "source_type": yunshou_result.get("meta", {}).get("source_type", "unknown"),
            "duration_sec": yunshou_result.get("meta", {}).get("duration_sec", 0),
        },
        
        # 视觉参数 - 粒子系统
        "particles": {
            # 发射位置：使用手腕轨迹
            "emitter_position": _extract_emitter_positions(trajectories),
            
            # 粒子速度：由速度决定
            "speed_scale": _map_speed_scale(three_section),
            
            # 粒子数量：由轨迹长度决定
            "particle_count": min(len(trajectories.get("wrist_left", {}).get("x", [])), 10000),
            
            # 粒子生命周期
            "lifetime": 2.0 + (circularity.get("circularity_score", 0.5) * 2.0),
            
            # 扩散范围：由拉班space决定
            "spread": laban.get("space", {}).get("span_left_right", 0.5),
            
            # 颜色
            "color": {
                "primary": color_palette["primary"],
                "secondary": color_palette["secondary"],
                "accent": color_palette["accent"],
            },
        },
        
        # 视觉参数 - 流动效果
        "flow": {
            # 流动强度：由速度决定
            "intensity": _map_flow_intensity(three_section),
            
            # 湍流程度
            "turbulence": fancheng.get("reversal_ratio", 0.1),
            
            # 流动方向一致性
            "direction_consistency": circularity.get("circularity_score", 0.5),
            
            # 螺旋紧密程度：由圆度决定
            "spiral_tightness": circularity.get("circularity_score", 0.5),
            
            # 螺旋半径
            "spiral_radius": circularity.get("mean_radius", 0.3),
        },
        
        # 视觉参数 - 运动效果
        "motion": {
            # 镜像效果：对称性
            "mirror_intensity": _map_symmetry_score(yunshou_result),
            
            # 呼吸效果：节奏停顿
            "breathing": _map_breathing(rhythm),
            
            # 发光强度
            "glow_intensity": 0.5 + (dang.get("confidence", 0.5) * 0.5),
            
            # 模糊程度
            "blur": 0.1 + (fancheng.get("reversal_ratio", 0) * 0.3),
        },
        
        # 视觉参数 - 形态
        "shape": {
            # 环形联动：三节协调
            "ring_coupling": three_section.get("coordination_score", 50) / 100.0,
            
            # 环形半径序列
            "ring_radii": _extract_ring_radii(trajectories),
            
            # 环形旋转速度
            "ring_rotation_speed": _map_rotation_speed(three_section),
            
            # 扩展/收拢
            "expansion": laban.get("shape", {}).get("expansion_mean", 0.5),
        },
        
        # 音频/节奏同步
        "rhythm": {
            # 节拍点
            "beat_points": rhythm.get("speed_profile", {}).get("peaks", []),
            
            # 停顿点
            "pause_points": rhythm.get("pauses", []),
            
            # 节奏强度
            "rhythm_intensity": _map_rhythm_intensity(rhythm),
        },
        
        # 导出格式信息
        "export_info": {
            "format": "touchdesigner_json",
            "version": "1.0",
            "description": "云手分析结果 - TouchDesigner参数映射",
        },
    }
    
    return params


def _extract_emitter_positions(trajectories: dict) -> list[dict[str, float]]:
    """提取粒子发射位置序列"""
    positions = []
    
    # 获取左手腕轨迹
    wrist_l = trajectories.get("wrist_left", {})
    wrist_r = trajectories.get("wrist_right", {})
    
    x_list = wrist_l.get("x", [])
    y_list = wrist_l.get("y", [])
    z_list = wrist_l.get("z", [])
    
    # 采样以减少数据量
    step = max(1, len(x_list) // 100)
    
    for i in range(0, len(x_list), step):
        pos = {
            "x": float(x_list[i]) if i < len(x_list) else 0.0,
            "y": float(y_list[i]) if i < len(y_list) else 0.0,
            "z": float(z_list[i]) if i < len(z_list) else 0.0,
        }
        positions.append(pos)
    
    return positions


def _map_speed_scale(three_section: dict) -> float:
    """映射速度缩放"""
    score = three_section.get("coordination_score", 50)
    return 0.5 + (score / 100.0) * 1.5  # 0.5 - 2.0


def _map_flow_intensity(three_section: dict) -> float:
    """映射流动强度"""
    score = three_section.get("coordination_score", 50)
    return score / 100.0


def _map_symmetry_score(yunshou_result: dict) -> float:
    """映射对称性得分"""
    symmetry = yunshou_result.get("symmetry", {})
    # 尝试获取summary中的对称性得分
    summary = symmetry.get("_summary", {})
    mean_score = summary.get("mean_symmetry_score", 0.5)
    return mean_score


def _map_breathing(rhythm: dict) -> dict[str, Any]:
    """映射呼吸效果"""
    pauses = rhythm.get("pauses", [])
    
    return {
        "enabled": len(pauses) > 0,
        "pause_count": len(pauses),
        "breath_rate": 1.0 / max(len(pauses), 1),  # 呼吸频率
        "hold_duration": 0.5,  # 停顿持续时间
    }


def _extract_ring_radii(trajectories: dict) -> list[float]:
    """提取环形半径序列"""
    wrist_l = trajectories.get("wrist_left", {})
    wrist_r = trajectories.get("wrist_right", {})
    
    x_l = wrist_l.get("x", [])
    x_r = wrist_r.get("x", [])
    
    if not x_r or not x_l or len(x_l) != len(x_r):
        return [0.3, 0.5, 0.7]  # 默认
    
    # 计算双手间距作为半径
    radii = []
    step = max(1, len(x_l) // 50)
    
    for i in range(0, len(x_l), step):
        if i < len(x_l) and i < len(x_r):
            dist = abs(float(x_l[i]) - float(x_r[i]))
            radii.append(dist)
    
    return radii if radii else [0.3, 0.5, 0.7]


def _map_rotation_speed(three_section: dict) -> float:
    """映射旋转速度"""
    score = three_section.get("coordination_score", 50)
    return 0.2 + (score / 100.0) * 0.8  # 0.2 - 1.0


def _map_rhythm_intensity(rhythm: dict) -> float:
    """映射节奏强度"""
    rhythm_stats = rhythm.get("rhythm_stats", {})
    mean_speed = rhythm_stats.get("mean_speed", 0.5)
    return min(mean_speed / 2.0, 1.0)


def export_to_touchdesigner(yunshou_result: dict, output_path: str | Path) -> Path:
    """
    导出为TouchDesigner可用的JSON文件。
    
    Args:
        yunshou_result: 云手分析结果
        output_path: 输出文件路径
        
    Returns:
        输出的文件路径
    """
    params = map_to_touchdesigner(yunshou_result)
    
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(params, f, ensure_ascii=False, indent=2)
    
    return output_path


def create_touchdesigner_script(yunshou_result: dict) -> str:
    """
    生成TouchDesigner脚本（DAT/SCRIPT格式）。
    
    Args:
        yunshou_result: 云手分析结果
        
    Returns:
        TouchDesigner Python脚本
    """
    params = map_to_touchdesigner(yunshou_result)
    
    script = f'''
# 云手数据驱动 TouchDesigner 脚本
# 由 opera_mocap_tool 自动生成

yunshou_params = {json.dumps(params, indent=4, ensure_ascii=False)}

# ========== 粒子系统参数 ==========
particles = yunshou_params.get("particles", {{}})

# 粒子发射位置（从轨迹采样）
emitter_positions = {json.dumps(params["particles"]["emitter_position"][:10], indent=8)}
# ... (共 {len(params['particles']['emitter_positions'])} 个点)

# 粒子速度缩放
speed_scale = {params['particles']['speed_scale']}

# 粒子数量
particle_count = {params['particles']['particle_count']}

# 颜色
color_primary = "{params['particles']['color']['primary']}"
color_secondary = "{params['particles']['color']['secondary']}"
color_accent = "{params['particles']['color']['accent']}"


# ========== 流动效果参数 ==========
flow = yunshou_params.get("flow", {{}})

# 流动强度
flow_intensity = {flow['intensity']}

# 湍流程度
turbulence = {flow['turbulence']}

# 螺旋紧密程度
spiral_tightness = {flow['spiral_tightness']}


# ========== 运动效果参数 ==========
motion = yunshou_params.get("motion", {{}})

# 镜像强度
mirror_intensity = {motion['mirror_intensity']}

# 发光强度
glow_intensity = {motion['glow_intensity']}


# ========== 环形形态参数 ==========
shape = yunshou_params.get("shape", {{}})

# 三节联动
ring_coupling = {shape['ring_coupling']}

# 环形旋转速度
ring_rotation_speed = {shape['ring_rotation_speed']}


# ========== 使用示例 ==========
def update_particles(frame):
    """每帧更新粒子参数"""
    t = frame / 100.0  # 时间因子
    
    # 使用发射位置驱动粒子
    idx = int(t * len(emitter_positions)) % len(emitter_positions)
    pos = emitter_positions[idx]
    
    return {{
        "position": pos,
        "speed": speed_scale * (1 + flow_intensity * sin(t * 2 * pi)),
        "mirror": mirror_intensity,
        "glow": glow_intensity,
    }}


def update_spiral(frame):
    """更新螺旋效果"""
    t = frame / 100.0
    
    return {{
        "tightness": spiral_tightness,
        "rotation": ring_rotation_speed * t * 2 * pi,
        "coupling": ring_coupling * sin(t * pi),
    }}
'''
    
    return script
