"""统一加载入口。"""

from __future__ import annotations

from pathlib import Path

from .base import MocapData
from .bvh_reader import read_bvh
from .c3d_reader import read_c3d
from .csv_reader import read_csv
from .fbx_reader import read_fbx
from .video_pose import load_video_pose


def load_mocap(path: str | Path) -> MocapData:
    """
    根据扩展名自动选择加载器，读取 C3D、CSV、FBX、BVH 或视频动捕文件。

    Args:
        path: 文件路径。

    Returns:
        MocapData 实例。

    Raises:
        ValueError: 不支持的文件格式。
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
    if suffix in (".mp4", ".avi", ".mov", ".mkv", ".webm"):
        return load_video_pose(path)

    raise ValueError(
        f"不支持的文件格式: {suffix}，"
        "请使用 .c3d、.csv、.fbx、.bvh 或视频格式 (.mp4, .avi, .mov, .mkv, .webm)"
    )
