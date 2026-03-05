"""
TouchDesigner数据导出增强模块。

完善TouchDesigner数据映射功能：
- 增强数据映射
- 实时渲染支持
- 粒子系统对接
- 多种导出格式
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np


# 行当对应色彩方案
DANG_COLOR_PALETTES = {
    "laosheng": {
        "name": "老生",
        "primary": "#2C3E50",    # 深蓝
        "secondary": "#ECF0F1",   # 浅灰
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
        "primary": "#E8D5B7",     # 杏色
        "secondary": "#F5E6D3",   # 浅米
        "accent": "#F8B4B4",      # 浅红
    },
    "chou": {
        "name": "丑行",
        "primary": "#F39C12",     # 橙色
        "secondary": "#F1C40F",   # 黄色
        "accent": "#E67E22",      # 深橙
    },
    "wudan": {
        "name": "武旦",
        "primary": "#8E44AD",     # 紫色
        "secondary": "#9B59B6",   # 浅紫
        "accent": "#E74C3C",      # 红色
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
    云手分析结果映射为TouchDesigner参数。
    
    Args:
        yunshou_result: analyze_yunshou() 返回的结果
        metadata: 可选元数据，如文件名信息
        
    Returns:
        TouchDesigner可用的参数字典
    """
    # 提取各个分析模块
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
    
    # 参数映射
    params = {
        # 元信息
        "meta": {
            "dang": dang_type,
            "dang_name": color_palette["name"],
            "source_type": yunshou_result.get("meta", {}).get("source_type", "unknown"),
            "duration_sec": yunshou_result.get("meta", {}).get("duration_sec", 0),
        },
        
        # 粒子系统参数
        "particles": {
            # 发射位置：使用手腕轨迹
            "emitter_position": _extract_emitter_positions(trajectories),
            
            # 发射速度：速度越大粒子越快
            "speed_scale": _map_speed_scale(three_section),
            
            # 粒子数量：根据轨迹长度
            "particle_count": min(len(trajectories.get("wrist_left", {}).get("x", [])), 10000),
            
            # 粒子生命周期
            "lifetime": 2.0 + (circularity.get("circularity_score", 0.5) * 2.0),
            
            # 散射范围（基于space）
            "spread": laban.get("space", {}).get("span_left_right", 0.5),
            
            # 颜色
            "color": {
                "primary": color_palette["primary"],
                "secondary": color_palette["secondary"],
                "accent": color_palette["accent"],
            },
            
            # 透明度
            "opacity": _map_opacity(fancheng),
            
            # 粒子大小
            "size": _map_particle_size(three_section, circularity),
        },
        
        # 轨迹渲染参数
        "trajectory": {
            # 轨迹线条宽度
            "line_width": 2.0 + circularity.get("circularity_score", 0.5) * 3.0,
            
            # 轨迹颜色渐变
            "color_gradient": _create_color_gradient(color_palette, rhythm),
            
            # 轨迹发光
            "glow": fancheng.get("reversal_ratio", 0.1) * 10.0,
            
            # 轨迹平滑度
            "smoothing": circularity.get("circularity_score", 0.5),
        },
        
        # 节奏同步参数
        "rhythm_sync": {
            # 呼吸频率
            "breath_rate": _map_breath_rate(rhythm),
            
            # 闪烁效果
            "blink_on_lixiang": True,
            
            # 锣鼓点同步
            "luogu_sync": rhythm.get("rhythm_stats", {}).get("best_luogu_pattern"),
            
            # 停顿标记
            "pause_markers": _extract_pause_markers(rhythm),
        },
        
        # 空间参数
        "space": {
            # 运动范围
            "amplitude": _map_amplitude(circularity),
            
            # 中心位置
            "center_offset": _extract_center_offset(trajectories),
            
            # 对称性
            "symmetry": laban.get("shape", {}).get("symmetry_score", 0.5),
        },
        
        # 特效参数
        "effects": {
            # 螺旋效果（基于圆度）
            "spiral": circularity.get("circularity_score", 0.5) > 0.6,
            "spiral_tightness": circularity.get("circularity_score", 0.5),
            
            # 涟漪效果（基于反衬劲）
            "ripple": fancheng.get("reversal_ratio", 0) > 0.1,
            "ripple_intensity": fancheng.get("reversal_ratio", 0),
            
            # 拖尾效果
            "trail": True,
            "trail_length": _map_trail_length(three_section),
        },
    }
    
    return params


def _extract_emitter_positions(trajectories: dict) -> dict[str, list[float]]:
    """提取发射器位置"""
    positions = {}
    
    for side in ["left", "right"]:
        key = f"wrist_{side}"
        if key in trajectories:
            traj = trajectories[key]
            x = traj.get("x", [])
            z = traj.get("z", [])
            
            if x and z:
                # 取起始位置
                positions[key] = [
                    float(x[0]) if len(x) > 0 else 0.0,
                    0.0,  # y轴（垂直）默认0
                    float(z[0]) if len(z) > 0 else 0.0,
                ]
    
    return positions


def _map_speed_scale(three_section: dict) -> float:
    """映射速度比例"""
    score = three_section.get("coordination_score", 50)
    # 0-100 -> 0.5-2.0
    return 0.5 + (score / 100) * 1.5


def _map_opacity(fancheng: dict) -> float:
    """映射透明度"""
    reversal = fancheng.get("reversal_ratio", 0)
    # 反衬劲越强，透明度变化越大0.7 + reversal
    return 0.7 + reversal * 0.3


def _map_particle_size(three_section: dict, circularity: dict) -> float:
    """映射粒子大小"""
    coord_score = three_section.get("coordination_score", 50) / 100
    circ_score = circularity.get("circularity_score", 0.5)
    return 2.0 + coord_score * circ_score * 4.0


def _create_color_gradient(color_palette: dict, rhythm: dict) -> list[str]:
    """创建颜色渐变"""
    primary = color_palette.get("primary", "#FFFFFF")
    secondary = color_palette.get("secondary", "#CCCCCC")
    accent = color_palette.get("accent", "#FF0000")
    
    # 基于节奏生成渐变
    n_pauses = rhythm.get("rhythm_stats", {}).get("n_pauses", 0)
    
    if n_pauses > 3:
        # 多停顿使用复杂渐变
        return [primary, secondary, accent, primary]
    else:
        # 简单渐变
        return [primary, secondary]


def _map_breath_rate(rhythm: dict) -> float:
    """映射呼吸频率"""
    n_pauses = rhythm.get("rhythm_stats", {}).get("n_pauses", 0)
    total_pause = rhythm.get("rhythm_stats", {}).get("total_pause_sec", 0)
    duration = rhythm.get("rhythm_stats", {}).get("duration_sec", 1)
    
    if duration > 0:
        pause_ratio = total_pause / duration
        # 停顿越多，呼吸越慢
        return max(0.5, 2.0 - pause_ratio * 3.0)
    
    return 1.0


def _extract_pause_markers(rhythm: dict) -> list[dict]:
    """提取停顿标记"""
    pauses = rhythm.get("pauses", [])
    markers = []
    
    for pause in pauses:
        markers.append({
            "time": pause.get("start_time", 0),
            "duration": pause.get("duration_sec", 0),
        })
    
    return markers


def _map_amplitude(circularity: dict) -> dict[str, float]:
    """映射幅度"""
    mean_r = circularity.get("mean_radius", 0.5)
    return {
        "x": mean_r * 2,
        "y": mean_r * 1.5,
        "z": mean_r * 2,
    }


def _extract_center_offset(trajectories: dict) -> dict[str, float]:
    """提取中心偏移"""
    all_x = []
    all_z = []
    
    for key in ["wrist_left", "wrist_right"]:
        if key in trajectories:
            traj = trajectories[key]
            all_x.extend(traj.get("x", []))
            all_z.extend(traj.get("z", []))
    
    if all_x and all_z:
        return {
            "x": float(np.mean(all_x)),
            "y": 0.0,
            "z": float(np.mean(all_z)),
        }
    
    return {"x": 0.0, "y": 0.0, "z": 0.0}


def _map_trail_length(three_section: dict) -> float:
    """映射拖尾长度"""
    score = three_section.get("coordination_score", 50) / 100
    return 10 + score * 40


def export_for_realtime(
    yunshou_result: dict,
    output_path: str | Path,
    format: str = "json",
) -> dict[str, Any]:
    """
    导出实时渲染所需的数据。
    
    Args:
        yunshou_result: 云手分析结果
        output_path: 输出路径
        format: 输出格式 ("json", "csv", "binary")
        
    Returns:
        导出结果信息
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # 生成TouchDesigner参数
    params = map_to_touchdesigner(yunshou_result)
    
    if format == "json":
        # 导出为JSON
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(params, f, ensure_ascii=False, indent=2)
        
        return {
            "format": "json",
            "path": str(output_path),
            "size": output_path.stat().st_size,
        }
    
    elif format == "csv":
        # 导出为CSV（简化版）
        import csv
        
        rows = []
        
        # 元信息
        for key, val in params["meta"].items():
            rows.append(["meta", key, str(val)])
        
        # 粒子参数
        for key, val in params["particles"].items():
            if isinstance(val, dict):
                for k, v in val.items():
                    rows.append([f"particles.{key}", k, str(v)])
            else:
                rows.append(["particles", key, str(val)])
        
        with open(output_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerows(rows)
        
        return {
            "format": "csv",
            "path": str(output_path),
            "rows": len(rows),
        }
    
    else:
        raise ValueError(f"Unsupported format: {format}")


def export_trajectory_points(
    yunshou_result: dict,
    output_path: str | Path,
    sample_rate: int = 1,
) -> dict[str, Any]:
    """
    导出轨迹点数据（用于粒子系统）。
    
    Args:
        yunshou_result: 云手分析结果
        output_path: 输出路径
        sample_rate: 采样率（每N帧取一个点）
        
    Returns:
        导出结果信息
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    trajectories = yunshou_result.get("trajectories", {})
    
    # 收集所有轨迹点
    all_points = []
    
    for key, traj in trajectories.items():
        x = traj.get("x", [])
        y = traj.get("y", [])
        z = traj.get("z", [])
        speeds = traj.get("speed", [])
        
        # 采样
        for i in range(0, len(x), sample_rate):
            if i < len(x) and i < len(y) and i < len(z):
                all_points.append({
                    "marker": key,
                    "index": i,
                    "x": round(x[i], 4),
                    "y": round(y[i], 4),
                    "z": round(z[i], 4),
                    "speed": round(speeds[i], 4) if i < len(speeds) else 0,
                })
    
    # 保存
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_points, f, ensure_ascii=False)
    
    return {
        "path": str(output_path),
        "n_points": len(all_points),
        "n_markers": len(trajectories),
    }


def create_touchdesigner_dat(
    yunshou_result: dict,
    output_dir: str | Path,
) -> dict[str, Any]:
    """
    创建TouchDesigner DAT文件集。
    
    生成多个DAT文件用于TouchDesigner中：
    - params.dat: 参数字典
    - trajectory.dat: 轨迹数据
    - rhythm.dat: 节奏数据
    - style.dat: 风格数据
    
    Args:
        yunshou_result: 云手分析结果
        output_dir: 输出目录
        
    Returns:
        创建的文件列表
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    created_files = []
    
    # 1. params.dat
    params = map_to_touchdesigner(yunshou_result)
    params_file = output_dir / "params.dat"
    
    with open(params_file, "w", encoding="utf-8") as f:
        f.write("# TouchDesigner Parameters\n")
        f.write("# Generated by opera_mocap_tool\n\n")
        
        def write_dict(d: dict, prefix: str = "", indent: int = 0):
            for key, val in d.items():
                full_key = f"{prefix}.{key}" if prefix else key
                if isinstance(val, dict):
                    write_dict(val, full_key, indent)
                elif isinstance(val, list):
                    f.write(f"{'  '*indent}{key}\t{json.dumps(val)}\n")
                else:
                    f.write(f"{'  '*indent}{key}\t{val}\n")
        
        write_dict(params)
    
    created_files.append(str(params_file))
    
    # 2. trajectory.dat
    trajectories = yunshou_result.get("trajectories", {})
    traj_file = output_dir / "trajectory.dat"
    
    with open(traj_file, "w", encoding="utf-8") as f:
        f.write("# Trajectory Points\n")
        f.write("# marker\tx\ty\tz\tspeed\n\n")
        
        for marker, traj in trajectories.items():
            x = traj.get("x", [])
            y = traj.get("y", [])
            z = traj.get("z", [])
            speeds = traj.get("speed", [])
            
            for i in range(min(len(x), len(y), len(z))):
                speed = speeds[i] if i < len(speeds) else 0
                f.write(f"{marker}\t{x[i]:.4f}\t{y[i]:.4f}\t{z[i]:.4f}\t{speed:.4f}\n")
    
    created_files.append(str(traj_file))
    
    # 3. rhythm.dat
    rhythm = yunshou_result.get("rhythm", {})
    rhythm_file = output_dir / "rhythm.dat"
    
    with open(rhythm_file, "w", encoding="utf-8") as f:
        f.write("# Rhythm Data\n")
        f.write("# pause_index\tstart_time\tend_time\tduration\n\n")
        
        pauses = rhythm.get("pauses", [])
        for i, pause in enumerate(pauses):
            f.write(f"{i}\t{pause.get('start_time', 0):.4f}\t{pause.get('end_time', 0):.4f}\t{pause.get('duration_sec', 0):.4f}\n")
    
    created_files.append(str(rhythm_file))
    
    # 4. style.dat
    style_file = output_dir / "style.dat"
    
    dang = yunshou_result.get("dang", {})
    three_section = yunshou_result.get("three_section", {})
    circularity = yunshou_result.get("circularity", {})
    fancheng = yunshou_result.get("fancheng_jin", {})
    
    with open(style_file, "w", encoding="utf-8") as f:
        f.write("# Style Features\n")
        f.write("# parameter\tvalue\n\n")
        f.write(f"dang\t{dang.get('dang', 'unknown')}\n")
        f.write(f"dang_cn\t{dang.get('dang_cn', '未知')}\n")
        f.write(f"confidence\t{dang.get('confidence', 0):.4f}\n")
        f.write(f"three_section_score\t{three_section.get('coordination_score', 0):.4f}\n")
        f.write(f"circularity_score\t{circularity.get('circularity_score', 0):.4f}\n")
        f.write(f"fancheng_ratio\t{fancheng.get('reversal_ratio', 0):.4f}\n")
    
    created_files.append(str(style_file))
    
    return {
        "output_dir": str(output_dir),
        "created_files": created_files,
        "n_files": len(created_files),
    }
