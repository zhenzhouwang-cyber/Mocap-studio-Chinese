"""丢点插值：填补遮挡/丢失的 marker。"""

from __future__ import annotations

from typing import Literal

import numpy as np
from scipy import interpolate

from opera_mocap_tool.io.base import MocapData


def interpolate_missing(
    data: MocapData,
    method: Literal["linear", "spline", "cubic"] = "linear",
    max_gap_frames: int = 10,
) -> MocapData:
    """
    对缺失的 marker 数据进行插值填补。

    学理依据：线性插值简单稳定；样条插值更平滑；短间隙效果更好。

    Args:
        data: 原始 MocapData。
        method: "linear" / "spline" / "cubic"。
        max_gap_frames: 最大插值间隙（帧数），超过则保持 NaN。
    Returns:
        插值后的新 MocapData。
    """
    markers_out: dict[str, list[tuple[float, float, float]]] = {}

    for name, coords in data.markers.items():
        arr = np.array(coords, dtype=float)
        if arr.size == 0:
            markers_out[name] = []
            continue

        mask = np.isfinite(arr).all(axis=1)
        if np.all(mask):
            markers_out[name] = list(coords)
            continue

        out = arr.copy()
        for axis in range(3):
            col = arr[:, axis]
            valid = np.isfinite(col)
            if np.all(valid):
                continue
            if not np.any(valid):
                continue
            out[:, axis] = _fill_gaps(col, method, max_gap_frames)

        markers_out[name] = [tuple(float(x) for x in row) for row in out]

    return MocapData(
        markers=markers_out,
        frame_rate=data.frame_rate,
        marker_labels=data.marker_labels,
        residual=data.residual,
        camera_masks=data.camera_masks,
        metadata={**data.metadata, "interpolation_method": method},
    )


def _fill_gaps(
    x: np.ndarray,
    method: str,
    max_gap: int,
) -> np.ndarray:
    """对单列数据填充 NaN 间隙。"""
    out = x.copy()
    valid = np.isfinite(x)
    if not np.any(valid) or np.all(valid):
        return out

    idx_valid = np.where(valid)[0]
    vals_valid = x[idx_valid]
    idx_all = np.arange(len(x))

    # 对短间隙：用前后有效点插值；长间隙保持 NaN
    nan_mask = ~valid
    if method == "linear":
        out = np.interp(idx_all, idx_valid, vals_valid)
        out[~nan_mask] = x[~nan_mask]  # 保留原有效值
        # 仅对长度<=max_gap 的间隙插值，长间隙恢复 NaN
        _restore_long_gaps(out, x, max_gap)
    else:
        try:
            kind = "cubic" if method == "cubic" else "quadratic"
            f = interpolate.interp1d(
                idx_valid,
                vals_valid,
                kind=kind,
                fill_value=np.nan,
                bounds_error=False,
            )
            interp_vals = f(idx_all)
            short_gap_mask = _short_gap_mask(valid, max_gap)
            out = np.where(short_gap_mask & nan_mask, interp_vals, x)
            out = np.where(np.isfinite(out), out, x)
        except Exception:
            out = np.interp(idx_all, idx_valid, vals_valid)
            out[~nan_mask] = x[~nan_mask]
            _restore_long_gaps(out, x, max_gap)

    return out


def _short_gap_mask(valid: np.ndarray, max_gap: int) -> np.ndarray:
    """标记属于短间隙的 NaN 位置。"""
    n = len(valid)
    result = np.zeros(n, dtype=bool)
    i = 0
    while i < n:
        if valid[i]:
            i += 1
            continue
        j = i
        while j < n and not valid[j]:
            j += 1
        if j - i <= max_gap:
            result[i:j] = True
        i = j
    return result


def _restore_long_gaps(out: np.ndarray, orig: np.ndarray, max_gap: int) -> None:
    """将长间隙处的插值恢复为 NaN。"""
    valid = np.isfinite(orig)
    i = 0
    n = len(orig)
    while i < n:
        if valid[i]:
            i += 1
            continue
        j = i
        while j < n and not valid[j]:
            j += 1
        if j - i > max_gap:
            out[i:j] = np.nan
        i = j
