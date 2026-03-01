"""抖动滤波：低通滤波去除高频噪声。"""

from __future__ import annotations

from typing import Literal

import numpy as np
from scipy import signal

from opera_mocap_tool.io.base import MocapData


def apply_filter(
    data: MocapData,
    cutoff_hz: float = 6.0,
    order: int = 4,
    method: Literal["butterworth", "savgol"] = "butterworth",
    savgol_window: int = 11,
) -> MocapData:
    """
    对动捕数据应用低通滤波，去除抖动噪声。

    学理依据：Butterworth 低通滤波常用于动捕去噪；Savitzky-Golay 可保持边缘。

    Args:
        data: 原始 MocapData。
        cutoff_hz: 截止频率 (Hz)，默认 6.0。
        order: Butterworth 阶数，默认 4。
        method: "butterworth" 或 "savgol"。
        savgol_window: Savitzky-Golay 窗口长度（奇数），默认 11。

    Returns:
        滤波后的新 MocapData（不修改原数据）。
    """
    fr = data.frame_rate
    markers_out: dict[str, list[tuple[float, float, float]]] = {}

    for name, coords in data.markers.items():
        arr = np.array(coords, dtype=float)
        if arr.size == 0:
            markers_out[name] = []
            continue

        mask = np.isfinite(arr)
        arr_filt = arr.copy()
        for axis in range(3):
            col = arr[:, axis]
            valid = np.isfinite(col)
            if not np.any(valid):
                continue
            if method == "butterworth":
                col_filt = _butterworth_lowpass(col, fr, cutoff_hz, order)
            else:
                col_filt = _savgol_filter(col, savgol_window)
            arr_filt[:, axis] = np.where(valid, col_filt, np.nan)

        markers_out[name] = [tuple(float(x) for x in row) for row in arr_filt]

    return MocapData(
        markers=markers_out,
        frame_rate=data.frame_rate,
        marker_labels=data.marker_labels,
        residual=data.residual,
        camera_masks=data.camera_masks,
        metadata={**data.metadata, "filter_cutoff_hz": cutoff_hz, "filter_method": method},
    )


def _butterworth_lowpass(
    x: np.ndarray, fs: float, cutoff: float, order: int
) -> np.ndarray:
    """Butterworth 低通滤波。"""
    min_len = 16  # filtfilt 默认 padlen 约 15
    if len(x) < min_len:
        return x.copy()
    nyq = 0.5 * fs
    normal_cutoff = min(cutoff / nyq, 0.99)
    b, a = signal.butter(order, normal_cutoff, btype="low", analog=False)
    out = np.full_like(x, np.nan)
    valid = np.isfinite(x)
    if not np.any(valid):
        return out
    x_fill = np.nan_to_num(x, nan=np.nanmean(x[valid]))
    out = signal.filtfilt(b, a, x_fill)
    out[~valid] = np.nan
    return out


def _savgol_filter(x: np.ndarray, window: int) -> np.ndarray:
    """Savitzky-Golay 滤波。"""
    if len(x) < 5:
        return x.copy()
    window = min(window, len(x) if len(x) % 2 else len(x) - 1)
    if window < 3:
        return x.copy()
    window = window if window % 2 else window - 1
    poly = min(3, window - 1)
    out = np.full_like(x, np.nan)
    valid = np.isfinite(x)
    if not np.any(valid):
        return out
    x_fill = np.nan_to_num(x, nan=np.nanmean(x[valid]))
    out = signal.savgol_filter(x_fill, window, poly, mode="nearest")
    out[~valid] = np.nan
    return out
