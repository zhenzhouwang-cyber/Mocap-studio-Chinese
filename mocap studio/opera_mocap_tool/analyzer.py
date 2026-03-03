"""主分析流程：加载、预处理、分析、汇总。"""

from __future__ import annotations

from pathlib import Path

from .analysis import compute_kinematics, compute_opera_features, compute_rhythm
from .analysis.segments import compute_action_segments
from .analysis.laban_approx import compute_laban_approx
from .export import export
from .io import load_mocap
from .io.base import MocapData
from .plotting import plot_analysis
from .preprocessing import apply_filter, compute_quality_report, interpolate_missing


DEFAULT_FILTER_CUTOFF_HZ = 6.0
DEFAULT_INTERP_METHOD = "linear"
DEFAULT_MAX_GAP_FRAMES = 10


def analyze(
    path: str | Path | None = None,
    *,
    mocap_data: MocapData | None = None,
    filter_cutoff_hz: float = DEFAULT_FILTER_CUTOFF_HZ,
    interp_method: str = DEFAULT_INTERP_METHOD,
    max_gap_frames: int = DEFAULT_MAX_GAP_FRAMES,
    apply_preprocessing: bool = True,
) -> dict:
    """
    对动捕文件做完整分析。

    Args:
        path: C3D 或 CSV 文件路径。
        mocap_data: 可选的 MocapData 对象（用于直接传入视频姿态数据等）。
        filter_cutoff_hz: 低通滤波截止频率。
        interp_method: 插值方法 "linear" / "spline" / "cubic"。
        max_gap_frames: 最大插值间隙帧数。
        apply_preprocessing: 是否执行滤波与插值。

    Returns:
        包含 meta, quality_report, kinematics, opera_features, rhythm, timeseries 的字典。

    Raises:
        ValueError: 当 path 和 mocap_data 都未提供时。
    """
    # 如果提供了 mocap_data，直接使用；否则从文件加载
    if mocap_data is not None:
        data = mocap_data
        filename = getattr(mocap_data, 'metadata', {}).get('source', 'video_mocap')
        filepath = 'memory'
    else:
        if path is None:
            raise ValueError("必须提供 path 或 mocap_data 参数")
        path = Path(path)
        if not path.is_file():
            raise FileNotFoundError(f"文件不存在: {path}")
        data = load_mocap(path)
        filename = path.name
        filepath = str(path.resolve())

    if apply_preprocessing:
        data = interpolate_missing(data, method=interp_method, max_gap_frames=max_gap_frames)
        data = apply_filter(data, cutoff_hz=filter_cutoff_hz)

    quality_report = compute_quality_report(data)
    kinematics = compute_kinematics(data)
    opera_features = compute_opera_features(data, kinematics=kinematics)
    rhythm = compute_rhythm(data, kinematics=kinematics)
    action_segments = compute_action_segments(data, kinematics, rhythm)
    laban_approx = compute_laban_approx(
        {"meta": {"marker_labels": list(data.marker_labels), "frame_rate": data.frame_rate}, "kinematics": kinematics},
        kinematics=kinematics,
    )

    timeseries = _build_timeseries(data, kinematics, rhythm)

    return {
        "meta": {
            "filename": filename,
            "filepath": filepath,
            "opera_type": "京剧",
            "frame_rate": float(data.frame_rate),
            "n_frames": int(data.n_frames),
            "duration_sec": round(float(data.duration_sec), 4),
            "marker_labels": list(data.marker_labels),
            "filter_cutoff_hz": filter_cutoff_hz,
            "interp_method": interp_method,
        },
        "quality_report": quality_report,
        "kinematics": kinematics,
        "opera_features": opera_features,
        "rhythm": rhythm,
        "action_segments": action_segments,
        "laban_approx": laban_approx,
        "timeseries": timeseries,
    }


def _build_timeseries(data, kinematics: dict, rhythm: dict) -> list[dict]:
    """构建对齐到时间网格的 timeseries 列表。"""
    fr = data.frame_rate
    n = data.n_frames
    times = [i / fr for i in range(n)]

    rows = []
    for i, t in enumerate(times):
        row: dict = {"time": round(t, 4), "frame": i}

        for name in data.marker_labels:
            if name not in data.markers:
                continue
            coords = data.markers[name][i] if i < len(data.markers[name]) else (None, None, None)
            if coords[0] is not None and not (coords[0] != coords[0]):  # not nan
                row[f"{name}_x"] = round(coords[0], 4)
                row[f"{name}_y"] = round(coords[1], 4)
                row[f"{name}_z"] = round(coords[2], 4)

            disp = kinematics.get("displacement", {}).get(name, [])
            if i < len(disp) and disp[i] is not None:
                row[f"{name}_displacement"] = round(disp[i], 4)

            vel = kinematics.get("velocities", {}).get(name, {})
            speed = vel.get("speed", [])
            if i < len(speed) and speed[i] is not None:
                row[f"{name}_speed"] = round(speed[i], 4)

        sp = rhythm.get("speed_profile", {}).get("mean_speed_per_frame", [])
        if i < len(sp) and sp[i] is not None:
            row["mean_speed"] = round(sp[i], 4)

        rows.append(row)

    return rows
