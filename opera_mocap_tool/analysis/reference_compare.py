"""
参考动作比对：DTW 时序对齐、相似度评分、按部位/肢体子集评分。

用于教学/传承类研究与艺术创作（参考–当前双轨、偏差驱动参数）。
"""

from __future__ import annotations

from typing import Any

import numpy as np

from .opera_features import classify_limb


def _timeseries_to_matrix(timeseries: list[dict], columns: list[str]) -> np.ndarray:
    """从 timeseries 中提取指定列，组成 (n_frames, n_cols) 矩阵，缺值填 nan 后按列均值填充。"""
    if not timeseries or not columns:
        return np.array([]).reshape(0, 0)
    n = len(timeseries)
    mat = np.full((n, len(columns)), np.nan)
    for i, row in enumerate(timeseries):
        for j, col in enumerate(columns):
            v = row.get(col)
            if v is not None and isinstance(v, (int, float)):
                mat[i, j] = float(v)
    # 列均值填缺
    for j in range(mat.shape[1]):
        col = mat[:, j]
        if np.any(np.isfinite(col)):
            mat[np.isnan(col), j] = np.nanmean(col)
        else:
            mat[:, j] = 0
    return mat.astype(float)


def _get_numeric_columns(timeseries: list[dict], exclude: tuple[str, ...] = ("time", "frame")) -> list[str]:
    """获取 timeseries 中所有数值列名（排除 time, frame）。"""
    if not timeseries:
        return []
    keys = [k for k in timeseries[0].keys() if k not in exclude]
    numeric = []
    for k in keys:
        v = timeseries[0].get(k)
        if v is not None and isinstance(v, (int, float)):
            numeric.append(k)
    return numeric


def _common_columns(cols_current: list[str], cols_ref: list[str]) -> list[str]:
    """取两列集的交集，保证顺序与 cols_current 一致。"""
    ref_set = set(cols_ref)
    return [c for c in cols_current if c in ref_set]


def _columns_for_markers(all_columns: list[str], marker_names: list[str]) -> list[str]:
    """选出属于给定 marker 的列（前缀匹配：Marker1_x, Marker1_y -> Marker1）。"""
    if not marker_names:
        return list(all_columns)
    out = []
    for col in all_columns:
        for m in marker_names:
            if col == f"{m}_x" or col == f"{m}_y" or col == f"{m}_z" or col.startswith(m + "_"):
                out.append(col)
                break
    return out


def _columns_for_limb(all_columns: list[str], limb: str) -> list[str]:
    """选出属于某肢体类型的 marker 的列。"""
    marker_names = []
    seen = set()
    for col in all_columns:
        if "_x" in col or "_y" in col or "_z" in col:
            parts = col.rsplit("_", 1)
            if len(parts) == 2 and parts[1] in ("x", "y", "z"):
                name = parts[0]
                if name not in seen and classify_limb(name) == limb:
                    seen.add(name)
                    marker_names.append(name)
    return _columns_for_markers(all_columns, marker_names)


def _dtw_distance(A: np.ndarray, B: np.ndarray) -> tuple[float, list[tuple[int, int]]]:
    """
    标准 DTW：欧氏距离，返回 (总距离, 对齐路径).
    A: (n, d), B: (m, d). 路径为 [(i0,j0), (i1,j1), ...].
    """
    n, m = A.shape[0], B.shape[0]
    if n == 0 or m == 0:
        return float("inf"), []
    # 成本矩阵
    C = np.sqrt(np.sum((A[:, np.newaxis, :] - B[np.newaxis, :, :]) ** 2, axis=2))
    D = np.full((n + 1, m + 1), np.inf)
    D[0, 0] = 0
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            D[i, j] = C[i - 1, j - 1] + min(D[i - 1, j], D[i - 1, j - 1], D[i, j - 1])
    total = D[n, m]
    # 回溯路径
    path = []
    i, j = n, m
    while i > 0 and j > 0:
        path.append((i - 1, j - 1))
        candidates = [(D[i - 1, j], i - 1, j), (D[i - 1, j - 1], i - 1, j - 1), (D[i, j - 1], i, j - 1)]
        _, i, j = min(candidates, key=lambda x: x[0])
    path.reverse()
    return float(total), path


def _normalize_series(X: np.ndarray) -> np.ndarray:
    """按列 z-score 标准化，避免量纲主导距离。"""
    if X.size == 0:
        return X
    mu = np.nanmean(X, axis=0)
    sigma = np.nanstd(X, axis=0)
    sigma[sigma < 1e-10] = 1.0
    return (X - mu) / sigma


def compare_with_reference(
    current_result: dict,
    reference_result: dict,
    *,
    marker_subset: list[str] | None = None,
    limb_subset: list[str] | None = None,
    normalize: bool = True,
) -> dict[str, Any]:
    """
    将当前分析结果与参考动作比对，基于 DTW 时序对齐。

    Args:
        current_result: 当前动捕分析结果（含 meta, timeseries）。
        reference_result: 参考动捕分析结果（含 meta, timeseries）。
        marker_subset: 仅用这些 marker 的通道比对；None 表示用全部共有通道。
        limb_subset: 仅用这些肢体类型（upper_limb, lower_limb, trunk, upper_extremity, unknown）的 marker；与 marker_subset 二选一或同时用（取交集）。
        normalize: 是否对序列做 z-score 再 DTW，避免量纲影响。

    Returns:
        reference_compare: {
            "dtw_distance", "dtw_path", "n_frames_current", "n_frames_reference",
            "by_limb": { limb: { "dtw_distance", "n_columns" } },
            "common_columns", "align_ratio" (path_len / max(n,m))
        }
    """
    ts_cur = current_result.get("timeseries", [])
    ts_ref = reference_result.get("timeseries", [])
    if not ts_cur or not ts_ref:
        return {
            "dtw_distance": None,
            "dtw_path": [],
            "n_frames_current": len(ts_cur),
            "n_frames_reference": len(ts_ref),
            "by_limb": {},
            "common_columns": [],
            "align_ratio": None,
            "error": "timeseries 为空",
        }

    cols_cur = _get_numeric_columns(ts_cur)
    cols_ref = _get_numeric_columns(ts_ref)
    common = _common_columns(cols_cur, cols_ref)
    if not common:
        return {
            "dtw_distance": None,
            "dtw_path": [],
            "n_frames_current": len(ts_cur),
            "n_frames_reference": len(ts_ref),
            "by_limb": {},
            "common_columns": [],
            "align_ratio": None,
            "error": "无共有通道",
        }

    if marker_subset:
        common = _columns_for_markers(common, marker_subset)
    if limb_subset:
        limb_cols = []
        for limb in limb_subset:
            limb_cols.extend(_columns_for_limb(common, limb))
        if limb_cols:
            common = limb_cols

    A = _timeseries_to_matrix(ts_cur, common)
    B = _timeseries_to_matrix(ts_ref, common)
    if normalize:
        # 合并后统一标准化，再拆开
        AB = np.vstack([A, B])
        ABn = _normalize_series(AB)
        A = ABn[: A.shape[0]]
        B = ABn[A.shape[0] :]

    total_dist, path = _dtw_distance(A, B)
    n_cur, n_ref = A.shape[0], B.shape[0]
    align_ratio = len(path) / max(n_cur, n_ref, 1)

    # 按肢体分块评分
    by_limb: dict[str, dict[str, Any]] = {}
    for limb in ("upper_limb", "lower_limb", "trunk", "upper_extremity", "unknown"):
        limb_cols = _columns_for_limb(common, limb)
        if not limb_cols:
            continue
        A_limb = _timeseries_to_matrix(ts_cur, limb_cols)
        B_limb = _timeseries_to_matrix(ts_ref, limb_cols)
        if A_limb.size == 0 or B_limb.size == 0:
            continue
        if normalize:
            AB_limb = np.vstack([A_limb, B_limb])
            AB_limb = _normalize_series(AB_limb)
            A_limb = AB_limb[: A_limb.shape[0]]
            B_limb = AB_limb[A_limb.shape[0] :]
        dist_limb, _ = _dtw_distance(A_limb, B_limb)
        by_limb[limb] = {"dtw_distance": round(float(dist_limb), 4), "n_columns": len(limb_cols)}

    return {
        "dtw_distance": round(float(total_dist), 4),
        "dtw_path": path[:500],
        "n_frames_current": n_cur,
        "n_frames_reference": n_ref,
        "by_limb": by_limb,
        "common_columns": common,
        "align_ratio": round(align_ratio, 4),
        "n_common_columns": len(common),
    }


def interpret_reference_comparison(
    current_result: dict,
    reference_result: dict,
    compare_result: dict,
    *,
    frame_rate: float | None = None,
) -> dict[str, Any]:
    """
    基于 DTW 比对结果生成可解释反馈：轨迹偏差、时间偏移（scaling/lapsing）、文字结论。

    供学术报告与艺术创作（偏差/延迟映射为参数）。

    Args:
        current_result: 当前分析结果。
        reference_result: 参考分析结果。
        compare_result: compare_with_reference 的返回值。
        frame_rate: 帧率（用于时间偏移秒数）；若 None 则从 current_result.meta 取。

    Returns:
        interpretation: {
            "time_shift_sec", "time_scale_ratio", "lapsing_sec",
            "per_limb_deviation", "text_conclusions"
        }
    """
    fr = frame_rate or (current_result.get("meta") or {}).get("frame_rate") or 100.0
    path = compare_result.get("dtw_path", [])
    n_cur = compare_result.get("n_frames_current", 0)
    n_ref = compare_result.get("n_frames_reference", 0)
    by_limb = compare_result.get("by_limb", {})

    if not path or n_cur == 0 or n_ref == 0:
        return {
            "time_shift_sec": None,
            "time_scale_ratio": None,
            "lapsing_sec": None,
            "per_limb_deviation": {},
            "text_conclusions": ["比对数据不足，无法生成反馈。"],
        }

    # 时间尺度：参考时长/当前时长 -> 若>1 表示当前更快
    duration_cur = n_cur / fr
    duration_ref = n_ref / fr
    time_scale_ratio = round(duration_ref / duration_cur, 4) if duration_cur > 0 else None
    # 路径长度与 max 的差近似 lapsing（插入/删除）
    path_len = len(path)
    lapsing_frames = max(n_cur, n_ref) - path_len
    lapsing_sec = round(lapsing_frames / fr, 4) if lapsing_frames > 0 else 0.0
    # 简单时间偏移：路径首尾中点差（当前中帧 - 参考中帧）* dt
    if len(path) >= 2:
        i_mid = path[len(path) // 2][0]
        j_mid = path[len(path) // 2][1]
        time_shift_frames = (i_mid - j_mid) if n_cur >= n_ref else (j_mid - i_mid)
        time_shift_sec = round(time_shift_frames / fr, 4)
    else:
        time_shift_sec = 0.0

    # 各肢体偏差（已有 by_limb 的 dtw_distance，转为相对量或等级）
    limb_names_cn = {
        "upper_limb": "上肢",
        "lower_limb": "下肢",
        "trunk": "躯干",
        "upper_extremity": "上肢末端",
        "unknown": "其他",
    }
    per_limb_deviation: dict[str, dict[str, Any]] = {}
    total_dist = compare_result.get("dtw_distance") or 0
    for limb, data in by_limb.items():
        d = data.get("dtw_distance", 0)
        rel = round(d / total_dist, 4) if total_dist and total_dist > 0 else 0
        per_limb_deviation[limb] = {
            "dtw_distance": d,
            "relative_contribution": rel,
            "label": limb_names_cn.get(limb, limb),
        }

    # 文字结论
    conclusions: list[str] = []
    if time_scale_ratio is not None:
        if time_scale_ratio > 1.15:
            conclusions.append("整体节奏偏快，相较参考可适当放慢。")
        elif time_scale_ratio < 0.85:
            conclusions.append("整体节奏偏慢，相较参考可适当加快。")
    if abs(time_shift_sec) > 0.1:
        if time_shift_sec > 0:
            conclusions.append(f"整体时间略滞后约 {abs(time_shift_sec):.2f} 秒。")
        else:
            conclusions.append(f"整体时间略提前约 {abs(time_shift_sec):.2f} 秒。")
    if lapsing_sec > 0.5:
        conclusions.append(f"存在约 {lapsing_sec:.2f} 秒的节奏错位（插入或省略）。")

    if per_limb_deviation:
        worst = max(per_limb_deviation.items(), key=lambda x: x[1].get("dtw_distance", 0))
        limb_cn = worst[1].get("label", worst[0])
        conclusions.append(f"偏差最大部位：{limb_cn}，可重点校对该部分动作与节奏。")

    if not conclusions:
        conclusions.append("与参考动作在时序与整体形态上较为接近，可微调局部细节。")

    return {
        "time_shift_sec": time_shift_sec,
        "time_scale_ratio": time_scale_ratio,
        "lapsing_sec": lapsing_sec,
        "per_limb_deviation": per_limb_deviation,
        "text_conclusions": conclusions,
    }
