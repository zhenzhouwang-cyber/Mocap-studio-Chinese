"""统一加载入口。"""

from __future__ import annotations

from pathlib import Path

from .base import MocapData
from .bvh_reader import read_bvh
from .c3d_reader import read_c3d
from .csv_reader import read_csv
from .fbx_reader import read_fbx


def load_mocap(path: str | Path) -> MocapData:
    """
    根据扩展名自动选择加载器，读取 C3D、CSV、FBX 或 BVH 动捕/动画文件。

    Args:
        path: 文件路径。

    Returns:
        MocapData 实例。
    """
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix == ".c3d":
        return read_c3d(path)
    if suffix in (".csv", ".txt"):
        return read_csv(path)
    if suffix == ".fbx":
        return read_fbx(path)
    if suffix == ".bvh":
        return read_bvh(path)
    raise ValueError(f"不支持的文件格式: {suffix}，请使用 .c3d、.csv、.fbx 或 .bvh")
