"""动捕数据结构定义。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class MocapData:
    """动捕数据结构，统一 C3D 与 CSV 加载结果。"""

    markers: dict[str, list[tuple[float, float, float]]]
    """marker 名称 -> 每帧 (x, y, z) 坐标列表，长度 = n_frames"""

    frame_rate: float
    """帧率 (Hz)"""

    marker_labels: list[str]
    """marker 名称列表，保持顺序"""

    residual: dict[str, list[float]] = field(default_factory=dict)
    """marker 名称 -> 每帧残差（若 C3D 提供）"""

    camera_masks: dict[str, list[int]] = field(default_factory=dict)
    """marker 名称 -> 每帧相机掩码（若 C3D 提供）"""

    metadata: dict[str, Any] = field(default_factory=dict)
    """额外元数据"""

    @property
    def n_frames(self) -> int:
        """总帧数。"""
        if not self.markers:
            return 0
        first = next(iter(self.markers.values()))
        return len(first)

    @property
    def duration_sec(self) -> float:
        """时长（秒）。"""
        return self.n_frames / self.frame_rate if self.frame_rate > 0 else 0.0

    @property
    def time_array(self) -> list[float]:
        """时间轴（秒）。"""
        n = self.n_frames
        fr = self.frame_rate
        return [i / fr for i in range(n)]
