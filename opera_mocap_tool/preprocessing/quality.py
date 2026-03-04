"""质量评估：残差、缺失率、置信度统计。"""

from __future__ import annotations

import numpy as np

from opera_mocap_tool.io.base import MocapData


def compute_quality_report(data: MocapData) -> dict:
    """
    计算动捕数据质量报告。

    学理依据：残差反映重建精度；缺失率反映遮挡程度；置信度用于评估。

    Args:
        data: MocapData 实例。

    Returns:
        包含各 marker 及全局质量指标的字典。
    """
    report: dict = {
        "global": {
            "n_frames": data.n_frames,
            "frame_rate": data.frame_rate,
            "duration_sec": round(data.duration_sec, 4),
            "n_markers": len(data.markers),
            "overall_missing_rate": 0.0,
            "overall_mean_residual": None,
        },
        "markers": {},
    }

    total_missing = 0
    total_points = 0
    all_residuals: list[float] = []

    for name, coords in data.markers.items():
        arr = np.array(coords, dtype=float)
        valid = np.isfinite(arr).all(axis=1)
        n_valid = int(np.sum(valid))
        n_total = len(arr)
        missing_rate = 1.0 - (n_valid / n_total) if n_total > 0 else 0.0

        total_missing += n_total - n_valid
        total_points += n_total

        marker_report: dict = {
            "missing_rate": round(missing_rate, 4),
            "n_valid_frames": n_valid,
            "n_total_frames": n_total,
        }

        if data.residual and name in data.residual:
            res = np.array(data.residual[name], dtype=float)
            res_valid = res[np.isfinite(res)]
            if len(res_valid) > 0:
                marker_report["mean_residual"] = round(float(np.mean(res_valid)), 4)
                marker_report["max_residual"] = round(float(np.max(res_valid)), 4)
                marker_report["std_residual"] = round(float(np.std(res_valid)), 4)
                all_residuals.extend(res_valid.tolist())

        report["markers"][name] = marker_report

    if total_points > 0:
        report["global"]["overall_missing_rate"] = round(
            total_missing / total_points, 4
        )
    if all_residuals:
        report["global"]["overall_mean_residual"] = round(
            float(np.mean(all_residuals)), 4
        )

    return report
