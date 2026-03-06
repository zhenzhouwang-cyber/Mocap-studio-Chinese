"""
批量处理模块。

支持批量分析多个动作文件：
- 目录扫描
- 并行处理
- 进度跟踪
- 结果汇总
- 报告生成
"""

from __future__ import annotations

import json
import multiprocessing as mp
import os
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

import numpy as np


@dataclass
class BatchResult:
    """单个文件的批处理结果"""
    file_path: str
    success: bool
    error: str | None = None
    result: dict | None = None
    duration_sec: float = 0.0


@dataclass
class BatchSummary:
    """批处理汇总结果"""
    total_files: int = 0
    successful: int = 0
    failed: int = 0
    total_duration_sec: float = 0.0
    results: list[BatchResult] = field(default_factory=list)
    
    # 统计分析
    dang_distribution: dict[str, int] = field(default_factory=dict)
    avg_circularity: float = 0.0
    avg_three_section_score: float = 0.0
    avg_duration_sec: float = 0.0


def analyze_single_file(
    file_path: str,
    analyzer_func: Callable | None = None,
) -> BatchResult:
    """
    分析单个动作文件。
    
    Args:
        file_path: 文件路径
        analyzer_func: 分析函数，默认为云手分析
        
    Returns:
        单文件分析结果
    """
    import time
    start_time = time.time()
    
    try:
        # 加载数据
        from opera_mocap_tool.io.base import MocapData
        from opera_mocap_tool.analysis.yunshou_features import analyze_yunshou
        
        data = MocapData.from_file(file_path)
        
        # 执行分析
        if analyzer_func:
            result = analyzer_func(data)
        else:
            result = analyze_yunshou(data)
        
        duration = time.time() - start_time
        
        return BatchResult(
            file_path=file_path,
            success=True,
            result=result,
            duration_sec=duration,
        )
        
    except Exception as e:
        duration = time.time() - start_time
        return BatchResult(
            file_path=file_path,
            success=False,
            error=str(e),
            duration_sec=duration,
        )


def scan_mocap_files(
    directory: str | Path,
    extensions: list[str] | None = None,
    recursive: bool = True,
) -> list[str]:
    """
    扫描目录中的动作文件。
    
    Args:
        directory: 目录路径
        extensions: 文件扩展名列表
        recursive: 是否递归搜索
        
    Returns:
        文件路径列表
    """
    if extensions is None:
        extensions = [".bvh", ".c3d", ".trc", ".csv", ".json"]
    
    directory = Path(directory)
    files = []
    
    if recursive:
        for ext in extensions:
            files.extend(directory.rglob(f"*{ext}"))
    else:
        for ext in extensions:
            files.extend(directory.glob(f"*{ext}"))
    
    return [str(f) for f in files]


def process_batch(
    file_paths: list[str],
    analyzer_func: Callable | None = None,
    max_workers: int | None = None,
    progress_callback: Callable[[int, int], None] | None = None,
) -> BatchSummary:
    """
    批量处理文件。
    
    Args:
        file_paths: 文件路径列表
        analyzer_func: 分析函数
        max_workers: 最大并行数
        progress_callback: 进度回调函数
        
    Returns:
        批处理汇总结果
    """
    if max_workers is None:
        max_workers = min(mp.cpu_count(), 4)
    
    results = []
    completed = 0
    total = len(file_paths)
    
    # 使用进程池并行处理
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        future_to_file = {
            executor.submit(analyze_single_file, fp, analyzer_func): fp
            for fp in file_paths
        }
        
        for future in as_completed(future_to_file):
            result = future.result()
            results.append(result)
            completed += 1
            
            if progress_callback:
                progress_callback(completed, total)
    
    # 生成汇总
    return summarize_batch_results(results)


def summarize_batch_results(results: list[BatchResult]) -> BatchSummary:
    """
    生成批处理汇总。
    
    Args:
        results: 单文件结果列表
        
    Returns:
        汇总结果
    """
    summary = BatchSummary(
        total_files=len(results),
        successful=sum(1 for r in results if r.success),
        failed=sum(1 for r in results if not r.success),
        total_duration_sec=sum(r.duration_sec for r in results),
    )
    
    # 统计分析
    successful_results = [r for r in results if r.success and r.result]
    
    if successful_results:
        # 行当分布
        dang_counts = {}
        circularities = []
        three_section_scores = []
        durations = []
        
        for r in successful_results:
            result = r.result
            
            # 行当
            dang = result.get("dang", {}).get("dang", "unknown")
            dang_counts[dang] = dang_counts.get(dang, 0) + 1
            
            # 圆度
            circ = result.get("circularity", {}).get("circularity_score", 0)
            if circ:
                circularities.append(circ)
            
            # 三节
            ts = result.get("three_section", {}).get("coordination_score", 0)
            if ts:
                three_section_scores.append(ts)
            
            # 时长
            dur = result.get("meta", {}).get("duration_sec", 0)
            if dur:
                durations.append(dur)
        
        summary.dang_distribution = dang_counts
        summary.avg_circularity = np.mean(circularities) if circularities else 0
        summary.avg_three_section_score = np.mean(three_section_scores) if three_section_scores else 0
        summary.avg_duration_sec = np.mean(durations) if durations else 0
    
    summary.results = results
    return summary


def export_batch_report(
    summary: BatchSummary,
    output_path: str | Path,
    format: str = "json",
) -> dict[str, Any]:
    """
    导出批处理报告。
    
    Args:
        summary: 批处理汇总
        output_path: 输出路径
        format: 输出格式 ("json", "html", "csv")
        
    Returns:
        导出结果
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    if format == "json":
        return _export_json(summary, output_path)
    elif format == "html":
        return _export_html(summary, output_path)
    elif format == "csv":
        return _export_csv(summary, output_path)
    else:
        raise ValueError(f"Unsupported format: {format}")


def _export_json(summary: BatchSummary, output_path: Path) -> dict:
    """导出JSON格式"""
    data = {
        "summary": {
            "total_files": summary.total_files,
            "successful": summary.successful,
            "failed": summary.failed,
            "success_rate": summary.successful / summary.total_files if summary.total_files > 0 else 0,
            "total_duration_sec": round(summary.total_duration_sec, 2),
            "avg_duration_sec": round(summary.avg_duration_sec, 2),
        },
        "statistics": {
            "dang_distribution": summary.dang_distribution,
            "avg_circularity": round(summary.avg_circularity, 3),
            "avg_three_section_score": round(summary.avg_three_section_score, 1),
        },
        "results": [
            {
                "file": r.file_path,
                "success": r.success,
                "error": r.error,
                "dang": r.result.get("dang", {}).get("dang") if r.result else None,
                "circularity": r.result.get("circularity", {}).get("circularity_score") if r.result else None,
                "duration_sec": round(r.duration_sec, 2),
            }
            for r in summary.results
        ],
    }
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    return {"path": str(output_path), "size": output_path.stat().st_size}


def _export_html(summary: BatchSummary, output_path: Path) -> dict:
    """导出HTML格式"""
    # 统计数据
    success_rate = summary.successful / summary.total_files * 100 if summary.total_files > 0 else 0
    dang_json = json.dumps(summary.dang_distribution)
    
    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Batch Analysis Report</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
        body {{
            font-family: 'Segoe UI', sans-serif;
            margin: 0;
            padding: 20px;
            background: #f5f7fa;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
            padding: 30px;
            text-align: center;
        }}
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 20px;
            padding: 30px;
            background: #f8f9fa;
        }}
        .stat-card {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        }}
        .stat-card h3 {{
            margin: 0 0 10px;
            color: #666;
            font-size: 0.85em;
            text-transform: uppercase;
        }}
        .stat-card .value {{
            font-size: 2em;
            font-weight: bold;
            color: #2C3E50;
        }}
        .section {{
            padding: 30px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #eee;
        }}
        th {{
            background: #f8f9fa;
            font-weight: 600;
        }}
        .success {{ color: #27ae60; }}
        .failed {{ color: #e74c3c; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>批量动作分析报告</h1>
            <p>共分析 {summary.total_files} 个文件</p>
        </div>
        
        <div class="stats">
            <div class="stat-card">
                <h3>总文件数</h3>
                <div class="value">{summary.total_files}</div>
            </div>
            <div class="stat-card">
                <h3>成功</h3>
                <div class="value success">{summary.successful}</div>
            </div>
            <div class="stat-card">
                <h3>失败</h3>
                <div class="value failed">{summary.failed}</div>
            </div>
            <div class="stat-card">
                <h3>成功率</h3>
                <div class="value">{success_rate:.1f}%</div>
            </div>
            <div class="stat-card">
                <h3>平均圆度</h3>
                <div class="value">{summary.avg_circularity:.2f}</div>
            </div>
            <div class="stat-card">
                <h3>平均三节分</h3>
                <div class="value">{summary.avg_three_section_score:.1f}</div>
            </div>
        </div>
        
        <div class="section">
            <h2>行当分布</h2>
            <div id="dang-chart" style="height: 300px;"></div>
        </div>
        
        <div class="section">
            <h2>详细结果</h2>
            <table>
                <thead>
                    <tr>
                        <th>文件名</th>
                        <th>状态</th>
                        <th>行当</th>
                        <th>圆度</th>
                        <th>耗时(秒)</th>
                    </tr>
                </thead>
                <tbody>
"""
    
    for r in summary.results:
        filename = Path(r.file_path).name
        status = '<span class="success">成功</span>' if r.success else '<span class="failed">失败</span>'
        
        if r.success and r.result:
            dang = r.result.get("dang", {}).get("dang_cn", "-")
            circ = r.result.get("circularity", {}).get("circularity_score", 0)
            circ_str = f"{circ:.2f}" if circ else "-"
        else:
            dang = "-"
            circ_str = "-"
        
        html += f"""
                    <tr>
                        <td>{filename}</td>
                        <td>{status}</td>
                        <td>{dang}</td>
                        <td>{circ_str}</td>
                        <td>{r.duration_sec:.2f}</td>
                    </tr>
"""
    
    html += """
                </tbody>
            </table>
        </div>
    </div>
    
    <script>
        var dangData = """ + dang_json + """;
        var labels = Object.keys(dangData);
        var values = Object.values(dangData);
        
        Plotly.newPlot('dang-chart', [{
            type: 'bar',
            x: labels,
            y: values,
            marker: {
                color: ['#3498DB', '#E74C3C', '#2ECC71', '#F39C12', '#9B59B6', '#95A5A6']
            }
        }], {
            margin: {t: 20, b: 40, l: 50, r: 20}
        });
    </script>
</body>
</html>
"""
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    
    return {"path": str(output_path), "size": output_path.stat().st_size}


def _export_csv(summary: BatchSummary, output_path: Path) -> dict:
    """导出CSV格式"""
    import csv
    
    with open(output_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Filename", "Status", "Error", "Dang", "Dang_CN", "Circularity", "Three_Section", "Duration_Sec"])
        
        for r in summary.results:
            filename = Path(r.file_path).name
            status = "success" if r.success else "failed"
            
            if r.success and r.result:
                dang = r.result.get("dang", {}).get("dang", "")
                dang_cn = r.result.get("dang", {}).get("dang_cn", "")
                circ = r.result.get("circularity", {}).get("circularity_score", 0)
                ts = r.result.get("three_section", {}).get("coordination_score", 0)
            else:
                dang = ""
                dang_cn = ""
                circ = ""
                ts = ""
            
            writer.writerow([
                filename,
                status,
                r.error or "",
                dang,
                dang_cn,
                circ,
                ts,
                round(r.duration_sec, 2),
            ])
    
    return {"path": str(output_path), "size": output_path.stat().st_size}


def quick_batch_analyze(
    input_dir: str | Path,
    output_dir: str | Path | None = None,
    format: str = "html",
    recursive: bool = True,
) -> BatchSummary:
    """
    快速批量分析。
    
    Args:
        input_dir: 输入目录
        output_dir: 输出目录
        format: 报告格式
        recursive: 是否递归
        
    Returns:
        批处理汇总
    """
    # 扫描文件
    files = scan_mocap_files(input_dir, recursive=recursive)
    
    if not files:
        print(f"No mocap files found in {input_dir}")
        return BatchSummary()
    
    print(f"Found {len(files)} files, processing...")
    
    # 处理
    def progress(current, total):
        print(f"Progress: {current}/{total} ({current*100//total}%)")
    
    summary = process_batch(
        files,
        progress_callback=progress,
    )
    
    # 导出报告
    if output_dir:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        if format == "html":
            report_path = output_dir / "batch_report.html"
        elif format == "json":
            report_path = output_dir / "batch_report.json"
        else:
            report_path = output_dir / "batch_report.csv"
        
        export_batch_report(summary, report_path, format)
        print(f"Report saved to {report_path}")
    
    return summary
