"""Vicon 动捕数据 3D 查看器：按帧显示 marker 位置与骨骼形态，支持时间轴播放。"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from .skeleton import get_skeleton_segments

if TYPE_CHECKING:
    from .io.base import MocapData


def _skeleton_line_traces(
    markers: dict[str, list[tuple[float, float, float]]],
    segments: list[tuple[str, str]],
    fi: int,
    *,
    line_color: str = "rgb(220, 50, 50)",
    line_width: float = 6.0,
):
    """某一帧的骨骼线段 Plotly 轨迹列表（每条线段一个 Scatter3d）。"""
    import plotly.graph_objects as go

    traces = []
    for a, b in segments:
        if a not in markers or b not in markers:
            continue
        pa, pb = markers[a], markers[b]
        if fi >= len(pa) or fi >= len(pb):
            continue
        (xa, ya, za), (xb, yb, zb) = pa[fi], pb[fi]
        if not all(math.isfinite(x) for x in (xa, ya, za, xb, yb, zb)):
            continue
        traces.append(
            go.Scatter3d(
                x=[xa, xb],
                y=[ya, yb],
                z=[za, zb],
                mode="lines",
                line=dict(color=line_color, width=line_width),
                name="骨骼",
                showlegend=False,
                hoverinfo="skip",
            )
        )
    return traces


def build_3d_viewer(
    data: MocapData,
    *,
    marker_subset: list[str] | None = None,
    max_markers: int = 80,
    frame_step: int = 1,
    point_size: float = 4.0,
    show_trail: bool = False,
    trail_frames: int = 30,
    show_skeleton: bool = True,
    skeleton_segments: list[tuple[str, str]] | None = None,
) -> "dict":
    """
    构建带时间轴动画的 3D 动捕查看器（Plotly 图数据，供 Streamlit 等使用）。

    每一帧显示当前时刻所有 marker 的 3D 位置，支持播放/暂停、拖动时间轴。

    Args:
        data: 已加载的 MocapData（来自 load_mocap）。
        marker_subset: 仅显示这些 marker；None 表示全部（受 max_markers 限制）。
        max_markers: 若未指定 marker_subset，最多显示的 marker 数量（避免卡顿）。
        frame_step: 动画帧步长（1=每帧都显示，2=隔一帧，用于长序列加速）。
        point_size: 3D 点大小。
        show_trail: 是否显示轨迹尾迹（最近 trail_frames 帧的轨迹）。
        trail_frames: 尾迹长度（帧数）。

    Returns:
        包含 "fig" (Plotly Figure)、"n_frames"、"frame_rate" 的字典，便于界面显示信息。
    """
    import plotly.graph_objects as go

    markers = data.markers
    labels = list(markers.keys())
    if marker_subset:
        labels = [m for m in labels if m in marker_subset]
    else:
        labels = labels[: max_markers]

    if not labels:
        return {"fig": go.Figure(), "n_frames": 0, "frame_rate": data.frame_rate}

    segments: list[tuple[str, str]] = []
    if show_skeleton:
        segments = skeleton_segments if skeleton_segments is not None else get_skeleton_segments(list(data.markers.keys()))

    n_frames = data.n_frames
    fr = data.frame_rate
    # 按 frame_step 下采样帧，用于动画
    frame_indices = list(range(0, n_frames, frame_step))
    if not frame_indices:
        frame_indices = [0]

    # 预计算全序列空间范围，用于固定坐标轴，避免播放时线框/边界随动作跳动
    all_x, all_y, all_z = [], [], []
    for fi in range(n_frames):
        for name in labels:
            pts = markers[name]
            if fi < len(pts):
                x, y, z = pts[fi]
                if math.isfinite(x) and math.isfinite(y) and math.isfinite(z):
                    all_x.append(x)
                    all_y.append(y)
                    all_z.append(z)
    if segments:
        for a, b in segments:
            if a in markers and b in markers:
                for fi in range(n_frames):
                    pa, pb = markers[a], markers[b]
                    if fi < len(pa) and fi < len(pb):
                        for pt in (pa[fi], pb[fi]):
                            if all(math.isfinite(v) for v in pt):
                                all_x.append(pt[0])
                                all_y.append(pt[1])
                                all_z.append(pt[2])
    if all_x and all_y and all_z:
        x_min, x_max = min(all_x), max(all_x)
        y_min, y_max = min(all_y), max(all_y)
        z_min, z_max = min(all_z), max(all_z)
        pad = max((x_max - x_min), (y_max - y_min), (z_max - z_min), 0.1) * 0.15
        fixed_ranges = dict(
            xaxis=dict(range=[x_min - pad, x_max + pad], autorange=False),
            yaxis=dict(range=[y_min - pad, y_max + pad], autorange=False),
            zaxis=dict(range=[z_min - pad, z_max + pad], autorange=False),
        )
    else:
        fixed_ranges = {}

    def positions_at_frame(fi: int) -> tuple[list[float], list[float], list[float], list[str]]:
        xs, ys, zs, names = [], [], [], []
        for name in labels:
            pts = markers[name]
            if fi < len(pts):
                x, y, z = pts[fi]
                if math.isfinite(x) and math.isfinite(y) and math.isfinite(z):
                    xs.append(x)
                    ys.append(y)
                    zs.append(z)
                    names.append(name)
        return xs, ys, zs, names

    # 第一帧：先画骨骼（在底层），再画点
    x0, y0, z0, n0 = positions_at_frame(0)
    initial_data: list = []
    if segments:
        initial_data.extend(_skeleton_line_traces(markers, segments, 0))
    initial_data.append(
        go.Scatter3d(
            x=x0,
            y=y0,
            z=z0,
            mode="markers+text" if n0 else "markers",
            text=n0 if n0 else None,
            textposition="top center",
            marker=dict(size=point_size, color="rgb(31, 119, 180)", line=dict(width=0.5, color="white")),
            name="Markers",
            hovertemplate="%{text}<br>x: %{x:.1f}<br>y: %{y:.1f}<br>z: %{z:.1f}<extra></extra>",
        )
    )
    fig = go.Figure(data=initial_data)

    # 可选：尾迹（仅第一帧先不画尾迹，动画时由 frames 更新）
    if show_trail and trail_frames > 0:
        trail_x, trail_y, trail_z = [], [], []
        for fi in range(max(0, 0 - trail_frames), 1):
            for name in labels:
                pts = markers[name]
                if fi >= 0 and fi < len(pts):
                    x, y, z = pts[fi]
                    if math.isfinite(x) and math.isfinite(y) and math.isfinite(z):
                        trail_x.append(x)
                        trail_y.append(y)
                        trail_z.append(z)
        if trail_x:
            fig.add_trace(
                go.Scatter3d(
                    x=trail_x,
                    y=trail_y,
                    z=trail_z,
                    mode="lines",
                    line=dict(color="rgba(128,128,128,0.4)", width=1),
                    name="轨迹尾迹",
                )
            )

    frames_list = []
    for k, fi in enumerate(frame_indices):
        frame_data: list = []
        if segments:
            frame_data.extend(_skeleton_line_traces(markers, segments, fi))
        xs, ys, zs, names = positions_at_frame(fi)
        frame_data.append(
            go.Scatter3d(
                x=xs,
                y=ys,
                z=zs,
                mode="markers+text" if names else "markers",
                text=names if names else None,
                textposition="top center",
                marker=dict(size=point_size, color="rgb(31, 119, 180)", line=dict(width=0.5, color="white")),
                name="Markers",
                hovertemplate="%{text}<br>x: %{x:.1f}<br>y: %{y:.1f}<br>z: %{z:.1f}<extra></extra>",
            )
        )
        if show_trail and trail_frames > 0:
            start = max(0, fi - trail_frames)
            tx, ty, tz = [], [], []
            for t in range(start, fi + 1):
                for name in labels:
                    pts = markers[name]
                    if t < len(pts):
                        x, y, z = pts[t]
                        if math.isfinite(x) and math.isfinite(y) and math.isfinite(z):
                            tx.append(x)
                            ty.append(y)
                            tz.append(z)
            if tx:
                frame_data.append(
                    go.Scatter3d(
                        x=tx, y=ty, z=tz,
                        mode="lines",
                        line=dict(color="rgba(128,128,128,0.4)", width=1),
                        name="轨迹尾迹",
                    )
                )
        frames_list.append(go.Frame(data=frame_data, name=str(fi), layout=dict()))

    fig.frames = frames_list

    # 播放速度：每帧显示 (frame_step/帧率) 秒，实现近似 1x 实时播放
    frame_duration_ms = max(30, 1000.0 * frame_step / fr)
    slider_steps = [
        dict(
            args=[[str(fi)], dict(frame=dict(duration=0, redraw=True), mode="immediate")],
            label=f"{fi / fr:.2f}s",
            method="animate",
        )
        for fi in frame_indices
    ]
    # 暗色背景便于看清亮色连线与点；固定坐标轴范围，避免播放时线框/边界随动作跳动
    scene_layout = dict(
        xaxis_title="X",
        yaxis_title="Y",
        zaxis_title="Z",
        aspectmode="data",
        camera=dict(eye=dict(x=1.6, y=1.6, z=1.2)),
        bgcolor="rgb(22, 22, 28)",
        xaxis=dict(gridcolor="rgba(80, 80, 100, 0.4)", **fixed_ranges.get("xaxis", {})),
        yaxis=dict(gridcolor="rgba(80, 80, 100, 0.4)", **fixed_ranges.get("yaxis", {})),
        zaxis=dict(gridcolor="rgba(80, 80, 100, 0.4)", **fixed_ranges.get("zaxis", {})),
    )
    fig.update_layout(
        title=dict(text="动捕 3D 查看器 · 可播放/拖动时间轴", font=dict(size=16)),
        scene=scene_layout,
        paper_bgcolor="rgb(22, 22, 28)",
        plot_bgcolor="rgb(22, 22, 28)",
        font=dict(color="rgb(200, 200, 210)"),
        height=600,
        margin=dict(l=0, r=0, t=50, b=0),
        updatemenus=[
            dict(
                type="buttons",
                showactive=False,
                x=0.05,
                y=0,
                buttons=[
                    dict(label="▶ 播放", method="animate", args=[None, dict(frame=dict(duration=frame_duration_ms, redraw=True), fromcurrent=True, mode="immediate")]),
                    dict(label="⏸ 暂停", method="animate", args=[[None], dict(mode="immediate")]),
                ],
            )
        ],
        sliders=[
            dict(
                active=0,
                xanchor="left",
                x=0.05,
                len=0.9,
                y=0,
                pad=dict(t=40, b=10),
                currentvalue=dict(visible=True, prefix="时间: ", suffix=" s", xanchor="center"),
                steps=slider_steps,
            )
        ],
    )

    return {
        "fig": fig,
        "n_frames": len(frame_indices),
        "frame_rate": fr,
        "duration_sec": data.duration_sec,
        "marker_count": len(labels),
    }


def build_3d_single_frame(
    data: MocapData,
    frame_index: int,
    *,
    marker_subset: list[str] | None = None,
    max_markers: int = 80,
    point_size: float = 4.0,
    show_skeleton: bool = True,
    skeleton_segments: list[tuple[str, str]] | None = None,
):
    """
    绘制某一帧的 3D marker 位置与骨骼形态（无动画，适合配合滑块逐帧查看）。

    Returns:
        Plotly Figure。
    """
    import plotly.graph_objects as go

    markers = data.markers
    labels = list(markers.keys())
    if marker_subset:
        labels = [m for m in labels if m in marker_subset]
    else:
        labels = labels[:max_markers]

    if not labels:
        return go.Figure()

    segments: list[tuple[str, str]] = []
    if show_skeleton:
        segments = skeleton_segments if skeleton_segments is not None else get_skeleton_segments(list(markers.keys()))

    fi = max(0, min(frame_index, data.n_frames - 1))
    fig_data: list = []
    if segments:
        fig_data.extend(_skeleton_line_traces(markers, segments, fi))
    xs, ys, zs, names = [], [], [], []
    for name in labels:
        pts = markers[name]
        if fi < len(pts):
            x, y, z = pts[fi]
            if math.isfinite(x) and math.isfinite(y) and math.isfinite(z):
                xs.append(x)
                ys.append(y)
                zs.append(z)
                names.append(name)
    fig_data.append(
        go.Scatter3d(
            x=xs,
            y=ys,
            z=zs,
            mode="markers+text" if names else "markers",
            text=names if names else None,
            textposition="top center",
            marker=dict(size=point_size, color="rgb(31, 119, 180)", line=dict(width=0.5, color="white")),
            hovertemplate="%{text}<br>x: %{x:.1f}<br>y: %{y:.1f}<br>z: %{z:.1f}<extra></extra>",
        )
    )
    fig = go.Figure(data=fig_data)
    t_sec = fi / data.frame_rate
    fig.update_layout(
        title=dict(text=f"第 {fi} 帧 · 时间 {t_sec:.2f} s", font=dict(size=16)),
        scene=dict(
            xaxis_title="X",
            yaxis_title="Y",
            zaxis_title="Z",
            aspectmode="data",
            camera=dict(eye=dict(x=1.6, y=1.6, z=1.2)),
            bgcolor="rgb(22, 22, 28)",
            xaxis=dict(gridcolor="rgba(80, 80, 100, 0.4)"),
            yaxis=dict(gridcolor="rgba(80, 80, 100, 0.4)"),
            zaxis=dict(gridcolor="rgba(80, 80, 100, 0.4)"),
        ),
        paper_bgcolor="rgb(22, 22, 28)",
        plot_bgcolor="rgb(22, 22, 28)",
        font=dict(color="rgb(200, 200, 210)"),
        height=550,
        margin=dict(l=0, r=0, t=50, b=0),
    )
    return fig
