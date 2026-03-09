"""导出分析结果为 JSON、CSV、TouchDesigner 格式。"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np


class _NumpyEncoder(json.JSONEncoder):
    """将 numpy 类型转为 Python 原生类型。"""

    def default(self, obj):
        if isinstance(obj, (np.floating, np.integer)):
            return float(obj) if isinstance(obj, np.floating) else int(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return super().default(obj)


def write_json(result: dict, out_path: str | Path) -> Path:
    """将分析结果写入 JSON 文件。"""
    path = Path(out_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2, cls=_NumpyEncoder)
    return path


def write_timeseries_csv(result: dict, out_path: str | Path) -> Path:
    """将 timeseries 导出为 CSV（time + 各 marker 通道）。"""
    path = Path(out_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = result.get("timeseries", [])
    if not rows:
        with open(path, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["time"])
        return path
    fieldnames = list(rows[0].keys())
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for row in rows:
            w.writerow(row)
    return path


def write_joint_timeseries_csv(joint_timeseries: list[dict], out_path: str | Path) -> Path:
    """将动捕+音频联合时间序列导出为 CSV（一条时间轴，供 TouchDesigner 等使用）。"""
    path = Path(out_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not joint_timeseries:
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write("time,frame\n")
        return path
    fieldnames = list(joint_timeseries[0].keys())
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for row in joint_timeseries:
            w.writerow(row)
    return path


def write_touchdesigner_dat(result: dict, out_path: str | Path) -> Path:
    """
    导出为 TouchDesigner DAT 兼容格式（CSV 表格，行=帧，列=通道）。

    通道命名：marker1_x, marker1_y, marker1_z, marker1_speed, ...
    """
    path = Path(out_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = result.get("timeseries", [])
    if not rows:
        with open(path, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["frame", "time"])
        return path
    fieldnames = list(rows[0].keys())
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for row in rows:
            w.writerow(row)
    return path


def export(
    result: dict,
    output_dir: str | Path | None = None,
    *,
    base_name: str | None = None,
    write_csv: bool = True,
    write_plot: bool = True,
    write_td: bool = False,
) -> tuple[Path, Path | None, Path | None, Path | None]:
    """
    导出分析结果。

    Returns:
        (json_path, csv_path 或 None, plot_path 或 None, td_path 或 None)
    """
    meta = result.get("meta", {})
    filename = meta.get("filename", "mocap")
    base = base_name or Path(filename).stem
    out_dir = Path(output_dir) if output_dir else Path(meta.get("filepath", ".")).parent
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    json_path = out_dir / f"{base}_mocap_analysis.json"
    write_json(result, json_path)

    csv_path = None
    if write_csv:
        csv_path = out_dir / f"{base}_mocap_timeseries.csv"
        write_timeseries_csv(result, csv_path)

    plot_path = None
    if write_plot:
        from .plotting import plot_analysis
        plot_path = out_dir / f"{base}_mocap_analysis.png"
        plot_analysis(result, plot_path)

    td_path = None
    if write_td:
        td_path = out_dir / f"{base}_mocap_td.csv"
        write_touchdesigner_dat(result, td_path)

    return (json_path, csv_path, plot_path, td_path)


# ============================================================================
# 商业模块导出
# ============================================================================

def export_particle_config(
    preset: str,
    emitter_config: dict,
    output_path: str | Path,
) -> Path:
    """
    导出粒子系统配置。

    Args:
        preset: 粒子预设名称
        emitter_config: 发射器配置
        output_path: 输出文件路径

    Returns:
        输出文件路径
    """
    import json

    config = {
        "preset": preset,
        "emitter": emitter_config,
    }

    output_path = Path(output_path)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2)

    return output_path


def export_rig_config(
    rig_config: dict,
    bones: dict,
    output_path: str | Path,
) -> Path:
    """
    导出绑定配置。

    Args:
        rig_config: 绑定配置
        bones: 骨骼数据
        output_path: 输出文件路径

    Returns:
        输出文件路径
    """
    import json

    config = {
        "config": rig_config,
        "bones": bones,
    }

    output_path = Path(output_path)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2)

    return output_path