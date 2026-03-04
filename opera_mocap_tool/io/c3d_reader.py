"""C3D 动捕文件解析。"""

from __future__ import annotations

from pathlib import Path

from .base import MocapData


def read_c3d(path: str | Path) -> MocapData:
    """
    读取 C3D 文件，提取 marker 坐标、帧率、标签。

    Args:
        path: C3D 文件路径。

    Returns:
        MocapData 实例。

    Raises:
        FileNotFoundError: 文件不存在。
        ValueError: 无法解析或数据为空。
    """
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"C3D 文件不存在: {path}")

    try:
        import c3d
    except ImportError:
        raise ImportError(
            "请安装 c3d 库: pip install c3d"
        ) from None

    with open(path, "rb") as f:
        reader = c3d.Reader(f)
        pl = getattr(reader, "point_labels", None)
        if pl is None or (hasattr(pl, "__len__") and len(pl) == 0):
            point_labels = _get_point_labels(reader)
        else:
            point_labels = list(pl) if hasattr(pl, "__iter__") else []

        markers: dict[str, list[tuple[float, float, float]]] = {}
        residual: dict[str, list[float]] = {}
        camera_masks: dict[str, list[int]] = {}

        def _ensure_labels(labels: list[str]) -> None:
            for label in labels:
                if label not in markers:
                    markers[label] = []
                    residual[label] = []
                    camera_masks[label] = []

        if point_labels:
            _ensure_labels(point_labels)

        frame_rate = getattr(reader, "point_rate", None) or 100.0
        if frame_rate <= 0:
            frame_rate = 100.0  # 默认

        for frame_no, points, _analog in reader.read_frames():
            if not point_labels and points.shape[0] > 0:
                point_labels = [f"Marker_{i}" for i in range(points.shape[0])]
                _ensure_labels(point_labels)
            if not point_labels:
                raise ValueError("C3D 文件中无 marker 标签")
            # points: (n_points, 4 或 5) 列 0,1,2 为 x,y,z，列 3 为 residual，列 4 为 camera_mask
            for i, label in enumerate(point_labels):
                if i < points.shape[0]:
                    x, y, z = float(points[i, 0]), float(points[i, 1]), float(points[i, 2])
                    markers[label].append((x, y, z))
                    if points.shape[1] > 3:
                        residual[label].append(float(points[i, 3]))
                    if points.shape[1] > 4:
                        camera_masks[label].append(int(points[i, 4]))

        if not markers or not next(iter(markers.values())):
            raise ValueError("C3D 文件中无有效帧数据")

    labels = point_labels or list(markers.keys())
    has_residual = any(residual.get(l) for l in labels)
    has_masks = any(camera_masks.get(l) for l in labels)

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
        marker_labels=labels,
        residual=residual if has_residual else {},
        camera_masks=camera_masks if has_masks else {},
        metadata={"source": str(path), "format": "c3d"},
    )


def _get_point_labels(reader) -> list[str]:
    """从 C3D Reader 参数中提取 POINT:LABELS。"""
    try:
        for group_name, group in reader.items():
            if group_name.upper() == "POINT":
                for param_name, param in group.items():
                    if param_name.upper() == "LABELS":
                        return list(param)
    except Exception:
        pass
    return []
