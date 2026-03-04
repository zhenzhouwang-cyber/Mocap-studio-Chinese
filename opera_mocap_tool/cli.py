"""命令行入口。"""

from __future__ import annotations

from pathlib import Path

import click

from .analyzer import analyze
from .export import export


@click.group()
def main() -> None:
    """京剧动捕数据分析工具 - 基于 Vicon 光学动捕数据（仅限京剧）。"""


@main.command()
@click.argument("path", type=click.Path(exists=True, path_type=Path))
@click.option("-o", "--output-dir", type=click.Path(path_type=Path), default=None, help="输出目录")
@click.option("--csv/--no-csv", default=True, help="导出 CSV 时间序列")
@click.option("--plot/--no-plot", default=True, help="导出分析图表 PNG")
@click.option("--td/--no-td", default=False, help="导出 TouchDesigner 格式 CSV")
@click.option("--filter-cutoff", type=float, default=6.0, help="低通滤波截止频率 (Hz)")
@click.option("--interp", type=click.Choice(["linear", "spline", "cubic"]), default="linear", help="插值方法")
@click.option("--max-gap", type=int, default=10, help="最大插值间隙帧数")
def run(
    path: Path,
    output_dir: Path | None,
    csv: bool,
    plot: bool,
    td: bool,
    filter_cutoff: float,
    interp: str,
    max_gap: int,
) -> None:
    """对单个动捕文件进行分析并导出。"""
    result = analyze(
        path,
        filter_cutoff_hz=filter_cutoff,
        interp_method=interp,
        max_gap_frames=max_gap,
    )
    out_dir = output_dir or path.parent
    json_path, csv_path, plot_path, td_path = export(
        result,
        output_dir=out_dir,
        write_csv=csv,
        write_plot=plot,
        write_td=td,
    )
    parts = [str(json_path.name)]
    if csv_path:
        parts.append(csv_path.name)
    if plot_path:
        parts.append(plot_path.name)
    if td_path:
        parts.append(td_path.name)
    click.echo(f"完成：已生成 {', '.join(parts)}")


@main.command("batch")
@click.argument("directory", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("-o", "--output-dir", type=click.Path(path_type=Path), default=None, help="输出目录（默认与输入同目录）")
@click.option("-j", "--jobs", type=int, default=1, help="并行任务数")
@click.option("--csv/--no-csv", default=True, help="导出 CSV")
@click.option("--plot/--no-plot", default=True, help="导出图表")
@click.option("--td/--no-td", default=False, help="导出 TouchDesigner 格式")
def batch(
    directory: Path,
    output_dir: Path | None,
    jobs: int,
    csv: bool,
    plot: bool,
    td: bool,
) -> None:
    """批量分析目录下的 C3D/CSV 文件。"""
    exts = {".c3d", ".csv"}
    files = [f for f in directory.iterdir() if f.is_file() and f.suffix.lower() in exts]
    if not files:
        click.echo("未找到 C3D 或 CSV 文件")
        return

    out_dir = output_dir or directory
    ok = 0
    for f in files:
        try:
            result = analyze(f)
            export(result, output_dir=out_dir, write_csv=csv, write_plot=plot, write_td=td)
            click.echo(f"OK: {f.name}")
            ok += 1
        except Exception as e:
            click.echo(f"FAIL: {f.name} - {e}", err=True)
    click.echo(f"完成：{ok}/{len(files)}")
