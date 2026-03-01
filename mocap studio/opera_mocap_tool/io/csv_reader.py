"""Vicon CSV 动捕导出解析。"""

from __future__ import annotations

import csv
import json
import time
from pathlib import Path

from .base import MocapData

# #region agent log
def _debug_log(msg: str, data: dict) -> None:
    try:
        with open(r"e:\coursor\project\.cursor\debug.log", "a", encoding="utf-8") as f:
            f.write(json.dumps({"location": "csv_reader.py", "message": msg, "data": data, "timestamp": time.time() * 1000}, ensure_ascii=False) + "\n")
    except Exception:
        pass
# #endregion


def read_csv(path: str | Path) -> MocapData:
    """
    读取 Vicon 导出的 CSV 动捕文件。

    支持常见格式：
    - 列名如 Frame, Time, Marker1_X, Marker1_Y, Marker1_Z, ...
    - 或 Marker1.X, Marker1.Y, Marker1.Z
    - 或 直接 X, Y, Z 按 marker 分组

    Args:
        path: CSV 文件路径。

    Returns:
        MocapData 实例。

    Raises:
        FileNotFoundError: 文件不存在。
        ValueError: 无法解析或数据为空。
    """
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"CSV 文件不存在: {path}")

    with open(path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        if not rows:
            raise ValueError("CSV 文件为空")

    headers = list(rows[0].keys())
    frame_col = _find_column(headers, ["Frame", "frame", "帧"])
    time_col = _find_column(headers, ["Time", "time", "时间"])

    # 按 Marker_X, Marker_Y, Marker_Z 分组
    marker_xyz: dict[str, list[str]] = {}
    for h in headers:
        if h in (frame_col, time_col) or (frame_col and h == frame_col) or (time_col and h == time_col):
            continue
        base, coord = _parse_marker_column(h)
        if base and coord:
            if base not in marker_xyz:
                marker_xyz[base] = [None, None, None]
            idx = {"x": 0, "y": 1, "z": 2}.get(coord.lower(), -1)
            if idx >= 0:
                marker_xyz[base][idx] = h

    # 过滤出完整 x,y,z 的 marker
    markers: dict[str, list[tuple[float, float, float]]] = {}
    incomplete: list[str] = []
    for name, cols in marker_xyz.items():
        if cols[0] and cols[1] and cols[2]:
            markers[name] = []
        else:
            incomplete.append(name)
    # #region agent log
    _debug_log("CSV parse: marker_xyz vs markers", {"marker_xyz_count": len(marker_xyz), "markers_count": len(markers), "incomplete_xyz": incomplete, "headers_sample": headers[:20], "hypothesisId": "H3"})
    # #endregion

    if not markers:
        raise ValueError("未找到有效的 marker 列（需 X/Y/Z 三列）")

    for row in rows:
        for name, (cx, cy, cz) in marker_xyz.items():
            if not (cx and cy and cz):
                continue
            try:
                x = float(row.get(cx, 0) or 0)
                y = float(row.get(cy, 0) or 0)
                z = float(row.get(cz, 0) or 0)
            except (ValueError, TypeError):
                x = y = z = float("nan")
            markers[name].append((x, y, z))

    # 估算帧率
    frame_rate = 100.0
    if time_col and len(rows) >= 2:
        try:
            t0 = float(rows[0].get(time_col, 0) or 0)
            t1 = float(rows[1].get(time_col, 0) or 0)
            if t1 > t0:
                frame_rate = 1.0 / (t1 - t0)
        except (ValueError, TypeError):
            pass

    # ===== 将所有标记位置移动到地面（Z=0） =====
    min_z = float('inf')
    for positions in markers.values():
        for x, y, z in positions:
            if not (x != x or y != y or z != z):  # 跳过 NaN
                min_z = min(min_z, z)
    
    if min_z != float('inf') and min_z != 0:
        offset_z = -min_z
        for name in markers:
            markers[name] = [(x, y, z + offset_z if not (x != x or y != y or z != z) else (x, y, z)) 
                              for x, y, z in markers[name]]

    return MocapData(
        markers=markers,
        frame_rate=frame_rate,
        marker_labels=list(markers.keys()),
        metadata={"source": str(path), "format": "csv"},
    )


def _find_column(headers: list[str], candidates: list[str]) -> str | None:
    """在 headers 中查找候选列名。"""
    for c in candidates:
        if c in headers:
            return c
    return None


def _parse_marker_column(header: str) -> tuple[str | None, str | None]:
    """
    解析列名，提取 marker 名与坐标轴。
    例如 Marker1_X -> (Marker1, X), LKnee.X -> (LKnee, X)
    """
    header = header.strip()
    for sep in ["_", ".", " "]:
        if sep in header:
            parts = header.rsplit(sep, 1)
            if len(parts) == 2:
                base, coord = parts[0].strip(), parts[1].strip()
                if coord.upper() in ("X", "Y", "Z"):
                    return base, coord
    return None, None
