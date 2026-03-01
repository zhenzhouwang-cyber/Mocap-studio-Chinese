"""
BVH 动捕文件解析：将 BVH 骨骼动画转为 MocapData（每关节世界坐标）。
不依赖 Blender/FBX，避免转换导致的骨骼或动画丢失。
"""
from __future__ import annotations

import math
import re
from pathlib import Path
from typing import Any

from .base import MocapData


def _euler_to_matrix_deg(rz: float, ry: float, rx: float, order: str = "ZYX") -> list[list[float]]:
    """欧拉角（度）转 4x4 旋转矩阵（行主序，齐次）。order 为应用顺序，如 ZYX 表示先 Z 再 Y 再 X。"""
    def rad(x: float) -> float:
        return math.radians(x)

    cx, sx = math.cos(rad(rx)), math.sin(rad(rx))
    cy, sy = math.cos(rad(ry)), math.sin(rad(ry))
    cz, sz = math.cos(rad(rz)), math.sin(rad(rz))

    # 3x3 旋转，列主序在内存中按列存
    if order == "ZYX":
        # R = Rz * Ry * Rx
        m = [
            [cy * cz, sx * sy * cz - cx * sz, cx * sy * cz + sx * sz],
            [cy * sz, cx * cz + sx * sy * sz, -sx * cz + cx * sy * sz],
            [-sy, sx * cy, cx * cy],
        ]
    else:
        # 默认 ZYX
        m = [
            [cy * cz, sx * sy * cz - cx * sz, cx * sy * cz + sx * sz],
            [cy * sz, cx * cz + sx * sy * sz, -sx * cz + cx * sy * sz],
            [-sy, sx * cy, cx * cy],
        ]

    return [
        [m[0][0], m[0][1], m[0][2], 0],
        [m[1][0], m[1][1], m[1][2], 0],
        [m[2][0], m[2][1], m[2][2], 0],
        [0, 0, 0, 1],
    ]


def _mat4_mul(a: list[list[float]], b: list[list[float]]) -> list[list[float]]:
    """4x4 矩阵乘法 (row-major)."""
    out = [[0.0] * 4 for _ in range(4)]
    for i in range(4):
        for j in range(4):
            for k in range(4):
                out[i][j] += a[i][k] * b[k][j]
    return out


def _mat4_translate(x: float, y: float, z: float) -> list[list[float]]:
    """平移矩阵 4x4."""
    return [
        [1, 0, 0, x],
        [0, 1, 0, y],
        [0, 0, 1, z],
        [0, 0, 0, 1],
    ]


def _mat4_get_translation(m: list[list[float]]) -> tuple[float, float, float]:
    """从 4x4 矩阵取平移 (m[0][3], m[1][3], m[2][3])."""
    return (m[0][3], m[1][3], m[2][3])


def read_bvh(path: str | Path) -> MocapData:
    """
    读取 BVH 文件，将每帧每个关节的世界坐标填入 MocapData。

    Args:
        path: BVH 文件路径。

    Returns:
        MocapData，markers 的 key 为关节名，value 为每帧 (x,y,z) 列表。
    """
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"BVH 文件不存在: {path}")

    text = path.read_text(encoding="utf-8", errors="replace")
    lines = [s.strip() for s in text.splitlines() if s.strip()]

    # 解析 HIERARCHY：关节名、offset、通道在帧数据中的起始下标
    joint_names: list[str] = []
    joint_offsets: list[tuple[float, float, float]] = []
    joint_channel_start: list[int] = []
    joint_channel_names: list[list[str]] = []
    joint_children: list[list[int]] = []
    global_channel_index = [0]
    stack: list[int] = []

    i = 0
    if i >= len(lines) or lines[i].upper() != "HIERARCHY":
        raise ValueError("BVH: 缺少 HIERARCHY")
    i += 1

    def parse_joint(parent_idx: int) -> int:
        nonlocal i
        if i >= len(lines):
            return -1
        line = lines[i]
        i += 1
        if line == "}":
            return -1
        joint_idx: int
        name: str
        if line.upper().startswith("ROOT "):
            name = line[5:].strip()
            joint_idx = len(joint_names)
            joint_names.append(name)
            joint_children.append([])
            if parent_idx >= 0:
                joint_children[parent_idx].append(joint_idx)
        elif line.upper().startswith("JOINT "):
            name = line[6:].strip()
            joint_idx = len(joint_names)
            joint_names.append(name)
            joint_children.append([])
            if parent_idx >= 0:
                joint_children[parent_idx].append(joint_idx)
        elif line.upper().startswith("END SITE"):
            # End Site 无通道，只占位一个“虚拟”关节便于遍历；不加入 joint_names 的通道计数
            i += 1  # {
            if i < len(lines) and "OFFSET" in lines[i]:
                parts = lines[i].split()
                if len(parts) >= 4:
                    ox, oy, oz = float(parts[1]), float(parts[2]), float(parts[3])
                i += 1
            i += 1  # }
            return -1
        else:
            return -1

        if line.upper().startswith("END SITE"):
            return -1

        # 部分 BVH 在 ROOT/JOINT 下一行是 "{"，需先跳过
        if i < len(lines) and lines[i] == "{":
            i += 1

        # OFFSET
        if i >= len(lines):
            raise ValueError("BVH: 期望 OFFSET")
        offset_line = lines[i]
        i += 1
        if "OFFSET" not in offset_line:
            raise ValueError("BVH: 期望 OFFSET")
        parts = offset_line.split()
        ox = float(parts[1])
        oy = float(parts[2])
        oz = float(parts[3])
        joint_offsets.append((ox, oy, oz))

        # CHANNELS
        if i >= len(lines):
            raise ValueError("BVH: 期望 CHANNELS")
        ch_line = lines[i]
        i += 1
        if "CHANNELS" not in ch_line:
            raise ValueError("BVH: 期望 CHANNELS")
        ch_parts = ch_line.split()
        n_ch = int(ch_parts[1])
        ch_names = ch_parts[2 : 2 + n_ch]
        joint_channel_start.append(global_channel_index[0])
        joint_channel_names.append(ch_names)
        global_channel_index[0] += n_ch

        # 子节点块：可能为 "{" 后跟 JOINT/End Site，或直接 JOINT（已在上文跳过 "{"）
        if i < len(lines) and lines[i] == "{":
            i += 1
        while i < len(lines) and lines[i] != "}":
            parse_joint(joint_idx)
        if i < len(lines):
            i += 1  # consume }

        return joint_idx

    # 从 ROOT 开始
    while i < len(lines):
        if lines[i].upper().startswith("ROOT "):
            parse_joint(-1)
            break
        i += 1

    n_channels = global_channel_index[0]

    # MOTION
    while i < len(lines) and "MOTION" not in lines[i].upper():
        i += 1
    if i >= len(lines):
        raise ValueError("BVH: 缺少 MOTION")
    i += 1
    n_frames = 0
    frame_time = 1.0 / 30.0
    if i < len(lines) and "Frames:" in lines[i]:
        n_frames = int(lines[i].split(":")[1].strip())
        i += 1
    if i < len(lines) and "Frame Time:" in lines[i]:
        frame_time = float(lines[i].split(":")[1].strip())
        i += 1

    frame_rate = 1.0 / frame_time if frame_time > 0 else 30.0
    motion_data: list[list[float]] = []
    for _ in range(n_frames):
        if i >= len(lines):
            break
        vals = [float(x) for x in lines[i].split()]
        i += 1
        if len(vals) >= n_channels:
            motion_data.append(vals[:n_channels])

    # 为每个关节计算每帧世界坐标
    markers: dict[str, list[tuple[float, float, float]]] = {name: [] for name in joint_names}

    for frame_idx, frame_vals in enumerate(motion_data):
        if len(frame_vals) < n_channels:
            for name in joint_names:
                markers[name].append((0.0, 0.0, 0.0))
            continue

        def world_matrix(j_idx: int, parent_world: list[list[float]] | None) -> list[list[float]]:
            start = joint_channel_start[j_idx]
            ch_names = joint_channel_names[j_idx]
            vals = [frame_vals[start + k] for k in range(len(ch_names))]
            ox, oy, oz = joint_offsets[j_idx]

            # 本地变换：T(offset) * R
            local_t = _mat4_translate(ox, oy, oz)
            rx = ry = rz = 0.0
            px = py = pz = 0.0
            for k, ch in enumerate(ch_names):
                v = vals[k] if k < len(vals) else 0.0
                ch_lower = ch.lower()
                if "xposition" in ch_lower:
                    px = v
                elif "yposition" in ch_lower:
                    py = v
                elif "zposition" in ch_lower:
                    pz = v
                elif "xrotation" in ch_lower:
                    rx = v
                elif "yrotation" in ch_lower:
                    ry = v
                elif "zrotation" in ch_lower:
                    rz = v

            # 根节点可能有 position 通道，先平移再旋转
            if px != 0 or py != 0 or pz != 0:
                local_t = _mat4_mul(_mat4_translate(px, py, pz), local_t)
            rot = _euler_to_matrix_deg(rz, ry, rx, "ZYX")
            local = _mat4_mul(local_t, rot)

            if parent_world is None:
                return local
            return _mat4_mul(parent_world, local)

        def traverse(j_idx: int, parent_world: list[list[float]] | None) -> None:
            w = world_matrix(j_idx, parent_world)
            tx, ty, tz = _mat4_get_translation(w)
            markers[joint_names[j_idx]].append((tx, ty, tz))
            for c in joint_children[j_idx]:
                traverse(c, w)

        traverse(0, None)

    # ===== 将所有骨骼位置移动到地面（Z=0） =====
    # 找到所有帧中所有骨骼的最小 Z 值
    min_z = float('inf')
    for positions in markers.values():
        for x, y, z in positions:
            min_z = min(min_z, z)
    
    # 如果最小 Z 不是 0，向下移动所有骨骼
    if min_z != float('inf') and min_z != 0:
        offset_z = -min_z
        for name in markers:
            markers[name] = [(x, y, z + offset_z) for x, y, z in markers[name]]

    return MocapData(
        markers=markers,
        frame_rate=frame_rate,
        marker_labels=joint_names,
        metadata={"source": str(path), "format": "bvh"},
    )
