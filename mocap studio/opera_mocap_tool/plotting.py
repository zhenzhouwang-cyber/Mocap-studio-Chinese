"""分析图表生成。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np


def _setup_chinese_font() -> None:
    """配置中文字体。"""
    try:
        import matplotlib.pyplot as plt
        plt.rcParams["font.sans-serif"] = [
            "Microsoft YaHei", "SimHei", "SimSun", "KaiTi"
        ] + list(plt.rcParams.get("font.sans-serif", []))
    except Exception:
        pass


def plot_analysis(result: dict[str, Any], out_path: str | Path) -> Path:
    """
    根据分析结果绘制多子图并保存为 PNG。

    包含：位移-时间、速度-时间、质量仪表盘、节奏剖面、程式化雷达图。
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    _setup_chinese_font()
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    meta = result.get("meta", {})
    title = meta.get("filename", "动捕分析结果")

    # 选择要绘制的子图
    n_plots = 0
    has_kinematics = bool(result.get("kinematics", {}).get("velocities"))
    has_quality = bool(result.get("quality_report"))
    has_rhythm = bool(result.get("rhythm", {}).get("speed_profile"))
    has_opera = bool(result.get("opera_features", {}).get("stylization"))

    if has_kinematics:
        n_plots += 1
    if has_quality:
        n_plots += 1
    if has_rhythm:
        n_plots += 1
    if has_opera:
        n_plots += 1

    if n_plots == 0:
        fig, ax = plt.subplots(1, 1, figsize=(8, 2))
        ax.text(0.5, 0.5, "无分析数据", ha="center", va="center")
        fig.savefig(out_path, dpi=150, bbox_inches="tight")
        plt.close()
        return out_path

    fig, axes = plt.subplots(n_plots, 1, figsize=(12, 3 * n_plots), sharex=False)
    if n_plots == 1:
        axes = [axes]
    idx = 0

    # 1. 位移与速度时序
    if has_kinematics:
        ax = axes[idx]
        kin = result["kinematics"]
        disp = kin.get("displacement", {})
        vels = kin.get("velocities", {})
        if disp:
            name = next(iter(disp))
            d = disp[name]
            fr = meta.get("frame_rate", 100)
            t = [i / fr for i in range(len(d))]
            ax.plot(t, d, color="darkblue", linewidth=0.6, label="位移")
        if vels:
            name = next(iter(vels))
            speeds = vels[name].get("speed", [])
            fr = meta.get("frame_rate", 100)
            t = [i / fr for i in range(len(speeds))]
            ax2 = ax.twinx()
            ax2.plot(t, speeds, color="darkgreen", linewidth=0.6, alpha=0.8, label="速度")
            ax2.set_ylabel("速度")
        ax.set_ylabel("位移")
        ax.set_title("位移/速度-时间")
        ax.grid(True, alpha=0.3)
        idx += 1

    # 2. 质量
    if has_quality and idx < n_plots:
        ax = axes[idx]
        qr = result["quality_report"]
        markers = list(qr.get("markers", {}).keys())[:10]
        missing_rates = [qr["markers"][m].get("missing_rate", 0) for m in markers]
        ax.barh(markers, missing_rates, color="steelblue", alpha=0.8)
        ax.set_xlabel("缺失率")
        ax.set_title("质量：各 Marker 缺失率")
        ax.grid(True, alpha=0.3, axis="x")
        idx += 1

    # 3. 节奏剖面
    if has_rhythm and idx < n_plots:
        ax = axes[idx]
        rhythm = result["rhythm"]
        sp = rhythm.get("speed_profile", {})
        mean_speed = sp.get("mean_speed_per_frame", [])
        if mean_speed:
            fr = meta.get("frame_rate", 100)
            t = [i / fr for i in range(len(mean_speed))]
            vals = [v if v is not None else np.nan for v in mean_speed]
            ax.fill_between(t, vals, alpha=0.3, color="orange")
            ax.plot(t, vals, color="darkorange", linewidth=0.6)
        ax.set_ylabel("平均速度")
        ax.set_xlabel("时间 (秒)")
        ax.set_title("节奏剖面")
        ax.grid(True, alpha=0.3)
        idx += 1

    # 4. 程式化指标
    if has_opera and idx < n_plots:
        ax = axes[idx]
        op = result["opera_features"].get("stylization", {})
        if op:
            labels = ["平均速度", "速度变异"]
            vals = [
                op.get("overall_mean_speed", 0) or 0,
                op.get("overall_speed_std", 0) or 0,
            ]
            ax.bar(labels, vals, color=["steelblue", "coral"], alpha=0.8)
            ax.set_ylabel("值")
            ax.set_title("京剧程式化指标")
            ax.grid(True, alpha=0.3, axis="y")
        idx += 1

    fig.suptitle(title, fontsize=11, y=1.02)
    plt.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close()
    return out_path


def plot_3d_trajectory(
    result: dict[str, Any],
    marker_name: str | None = None,
    out_path: str | Path | None = None,
):
    """
    绘制 3D 轨迹图。

    Returns:
        matplotlib Figure 或 Path（若指定 out_path）。
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d import Axes3D

    _setup_chinese_font()
    kin = result.get("kinematics", {})
    traj = kin.get("trajectories", {})
    if not traj:
        return None

    name = marker_name or next(iter(traj))
    if name not in traj:
        return None

    t = traj[name]
    x, y, z = t["x"], t["y"], t["z"]

    fig = plt.figure(figsize=(8, 6))
    ax = fig.add_subplot(111, projection="3d")
    ax.plot(x, y, z, linewidth=0.8, color="steelblue")
    ax.set_xlabel("X")
    ax.set_ylabel("Y")
    ax.set_zlabel("Z")
    ax.set_title(f"3D 轨迹: {name}")

    if out_path:
        fig.savefig(out_path, dpi=150, bbox_inches="tight")
        plt.close()
        return Path(out_path)
    return fig
