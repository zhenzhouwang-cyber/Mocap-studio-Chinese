"""
唱做关联分析：动捕与音频对齐后的节拍偏移、段落重叠、速度–能量相关。

用于学术报告/论文中的「唱做关系」量化。输入为动捕分析结果与音频分析结果（如 jingju_audio_tool 输出）。
"""

from __future__ import annotations

from typing import Any

import numpy as np


def _common_time_grid(dur_mocap: float, dur_audio: float, fps: float = 10.0) -> np.ndarray:
    """共同时间轴：取两者较短，按 fps 采样。"""
    duration = min(dur_mocap, dur_audio)
    n = max(1, int(duration * fps))
    return np.linspace(0, duration, n, endpoint=False)


def _interp_to_grid(
    times: list[float],
    values: list[float],
    grid: np.ndarray,
) -> np.ndarray:
    """将 (times, values) 插值到 grid。"""
    times = np.array(times, dtype=float)
    values = np.array(values, dtype=float)
    valid = np.isfinite(values)
    if not np.any(valid):
        return np.full_like(grid, np.nan)
    return np.interp(grid, times[valid], values[valid])


def _nearest_event_offset(beat_times: list[float], event_times: list[float]) -> list[float]:
    """每个 beat 到最近 event 的时间差（秒）。"""
    if not event_times:
        return [0.0] * len(beat_times)
    event_arr = np.array(event_times)
    offsets = []
    for t in beat_times:
        d = np.abs(event_arr - t)
        offsets.append(float(event_arr[np.argmin(d)] - t))
    return offsets


def _segment_overlap_pairs(
    segs_a: list[dict],
    segs_b: list[dict],
    key_start: str = "start_time",
    key_end: str = "end_time",
) -> list[dict]:
    """计算两组区间两两重叠长度；segs_a 用 key_start/key_end，segs_b 若为 audio 则 start/end。"""
    # 统一键名
    def _s(s: dict, start_k: str, end_k: str) -> tuple[float, float]:
        return (float(s.get(start_k, s.get("start", 0))), float(s.get(end_k, s.get("end", 0))))

    out = []
    for sa in segs_a:
        a0, a1 = _s(sa, key_start, key_end)
        for sb in segs_b:
            b0, b1 = _s(sb, "start_time", "end_time") if "start_time" in sb else _s(sb, "start", "end")
            overlap = max(0, min(a1, b1) - max(a0, b0))
            if overlap > 0:
                out.append({"segment_a": (a0, a1), "segment_b": (b0, b1), "overlap_sec": round(overlap, 4)})
    return out


def compute_sync_report(
    mocap_result: dict,
    audio_result: dict,
    *,
    speed_peak_min_prominence: float = 0.1,
) -> dict[str, Any]:
    """
    计算唱做关联报告：节拍偏移、段落重叠、速度–能量相关。

    Args:
        mocap_result: 动捕分析结果（含 meta, rhythm, action_segments, timeseries 或 speed_profile）。
        audio_result: 音频分析结果（含 meta, beats, onsets, segments, timeseries）。
        speed_peak_min_prominence: 速度峰最小突出度（用于从速度剖面提取事件点）。

    Returns:
        sync_report: {
            "beat_offset_stats": {"mean_sec", "std_sec", "offsets_sample"},
            "segment_overlap": {"pairs", "total_overlap_sec", "summary"},
            "correlation_speed_vs_rms": {"pearson", "n_points"},
            "meta": {"duration_used", "mocap_duration", "audio_duration"}
        }
    """
    meta_m = mocap_result.get("meta", {})
    meta_a = audio_result.get("meta", {})
    dur_mocap = float(meta_m.get("duration_sec", 0))
    dur_audio = float(meta_a.get("duration_sec", 0))
    if dur_mocap <= 0 or dur_audio <= 0:
        return {
            "beat_offset_stats": {},
            "segment_overlap": {},
            "correlation_speed_vs_rms": {},
            "meta": {"duration_used": 0, "mocap_duration": dur_mocap, "audio_duration": dur_audio},
        }

    duration = min(dur_mocap, dur_audio)
    grid = _common_time_grid(dur_mocap, dur_audio)

    # ----- 1. 动捕速度序列与事件点 -----
    rhythm = mocap_result.get("rhythm", {})
    sp = rhythm.get("speed_profile", {})
    mean_speed_per_frame = sp.get("mean_speed_per_frame", [])
    fr = meta_m.get("frame_rate", 100)
    n_frames = len(mean_speed_per_frame)
    times_mocap = [i / fr for i in range(n_frames)]
    speeds = [float(x) if x is not None else np.nan for x in mean_speed_per_frame]
    if not speeds or not np.any(np.isfinite(speeds)):
        # fallback: 从 timeseries 取 mean_speed
        ts = mocap_result.get("timeseries", [])
        times_mocap = [r["time"] for r in ts]
        speeds = [r.get("mean_speed") for r in ts]
        speeds = [float(x) if x is not None else np.nan for x in speeds]
    if times_mocap and len(speeds) == len(times_mocap) and np.any(np.isfinite(speeds)):
        speed_on_grid = _interp_to_grid(times_mocap, speeds, grid)
    else:
        speed_on_grid = np.zeros_like(grid)

    # 事件点：停顿起止 + 速度局部峰
    event_times: list[float] = []
    for p in rhythm.get("pauses", []):
        event_times.append(p["start_time"])
        event_times.append(p["end_time"])
    # 局部极大点（简化：相邻比较）
    for i in range(1, len(speed_on_grid) - 1):
        if speed_on_grid[i] >= speed_on_grid[i - 1] and speed_on_grid[i] >= speed_on_grid[i + 1]:
            if speed_on_grid[i] >= (np.nanmin(speed_on_grid) + speed_peak_min_prominence):
                event_times.append(float(grid[i]))

    # ----- 2. 节拍偏移 -----
    beats = audio_result.get("beats", [])
    beat_times = [b["time"] for b in beats if isinstance(b, dict) and "time" in b]
    if not beat_times and "time" in (beats[0] if beats else {}):
        beat_times = [b["time"] for b in beats]
    beat_offsets = _nearest_event_offset(beat_times, event_times) if beat_times and event_times else []
    beat_offset_stats: dict[str, Any] = {}
    if beat_offsets:
        beat_offset_stats = {
            "mean_sec": round(float(np.mean(beat_offsets)), 4),
            "std_sec": round(float(np.std(beat_offsets)), 4),
            "n_beats": len(beat_offsets),
            "offsets_sample": [round(x, 4) for x in beat_offsets[:20]],
        }

    # ----- 3. 段落重叠 -----
    action_segments = mocap_result.get("action_segments", [])
    audio_segments = audio_result.get("segments", [])
    pairs = _segment_overlap_pairs(
        action_segments,
        audio_segments,
        key_start="start_time",
        key_end="end_time",
    )
    total_overlap = sum(p["overlap_sec"] for p in pairs)
    segment_overlap = {
        "pairs": pairs[:50],
        "total_overlap_sec": round(total_overlap, 4),
        "n_action_segments": len(action_segments),
        "n_audio_segments": len(audio_segments),
        "summary": f"动作段 {len(action_segments)} 段，音频段 {len(audio_segments)} 段，重叠合计 {round(total_overlap, 2)} 秒",
    }

    # ----- 4. 速度–RMS 相关 -----
    ts_audio = audio_result.get("timeseries", [])
    if ts_audio:
        times_audio = [r["time"] for r in ts_audio]
        rms_list = [r.get("rms") for r in ts_audio]
        rms_list = [x if x is not None else np.nan for x in rms_list]
        rms_on_grid = _interp_to_grid(times_audio, rms_list, grid)
    else:
        rms_on_grid = np.full_like(grid, np.nan)

    valid = np.isfinite(speed_on_grid) & np.isfinite(rms_on_grid)
    if np.sum(valid) >= 3:
        r = np.corrcoef(speed_on_grid[valid], rms_on_grid[valid])[0, 1]
        if np.isfinite(r):
            correlation_speed_vs_rms = {"pearson": round(float(r), 4), "n_points": int(np.sum(valid))}
        else:
            correlation_speed_vs_rms = {"pearson": None, "n_points": int(np.sum(valid))}
    else:
        correlation_speed_vs_rms = {"pearson": None, "n_points": 0}

    return {
        "beat_offset_stats": beat_offset_stats,
        "segment_overlap": segment_overlap,
        "correlation_speed_vs_rms": correlation_speed_vs_rms,
        "meta": {
            "duration_used": round(duration, 4),
            "mocap_duration": dur_mocap,
            "audio_duration": dur_audio,
        },
    }


def build_joint_timeseries(
    mocap_result: dict,
    audio_result: dict,
    *,
    fps: float = 10.0,
) -> list[dict[str, Any]]:
    """
    构建动捕与音频的联合时间序列（一条时间轴，列=动捕通道+音频通道）。

    用于联合导出供 TouchDesigner 等一条时间轴驱动声画。

    Args:
        mocap_result: 动捕分析结果（含 meta, timeseries）。
        audio_result: 音频分析结果（含 meta, timeseries）。
        fps: 共同时间网格采样率（点/秒）。

    Returns:
        联合 timeseries：每行含 time, frame 及所有动捕列、音频列（pitch_hz, pitch_midi, rms, brightness 等）。
    """
    meta_m = mocap_result.get("meta", {})
    meta_a = audio_result.get("meta", {})
    dur_mocap = float(meta_m.get("duration_sec", 0))
    dur_audio = float(meta_a.get("duration_sec", 0))
    if dur_mocap <= 0 or dur_audio <= 0:
        return []

    duration = min(dur_mocap, dur_audio)
    grid = _common_time_grid(dur_mocap, dur_audio, fps=fps)
    fr = float(meta_m.get("frame_rate", 100))

    ts_mocap = mocap_result.get("timeseries", [])
    ts_audio = audio_result.get("timeseries", [])

    if not ts_mocap:
        return []

    # 动捕：每列插值到 grid
    times_m = [r["time"] for r in ts_mocap]
    mocap_keys = [k for k in ts_mocap[0].keys() if k != "time" and isinstance(ts_mocap[0].get(k), (int, float))]
    interp_mocap: dict[str, np.ndarray] = {}
    for key in mocap_keys:
        vals = [r.get(key) for r in ts_mocap]
        vals = [float(x) if x is not None else np.nan for x in vals]
        interp_mocap[key] = _interp_to_grid(times_m, vals, grid)

    # 音频：每列插值到 grid
    audio_keys: list[str] = []
    interp_audio: dict[str, np.ndarray] = {}
    if ts_audio:
        times_a = [r["time"] for r in ts_audio]
        audio_keys = [k for k in ts_audio[0].keys() if k != "time"]
        for key in audio_keys:
            vals = [r.get(key) for r in ts_audio]
            vals = [float(x) if x is not None else np.nan for x in vals]
            interp_audio[key] = _interp_to_grid(times_a, vals, grid)

    # 合并行
    rows: list[dict[str, Any]] = []
    for i, t in enumerate(grid):
        row: dict[str, Any] = {"time": round(float(t), 4), "frame": int(round(t * fr))}
        for key in mocap_keys:
            v = interp_mocap[key][i]
            row[key] = round(float(v), 4) if np.isfinite(v) else None
        for key in audio_keys:
            v = interp_audio[key][i]
            row[key] = round(float(v), 4) if np.isfinite(v) else None
        rows.append(row)
    return rows
