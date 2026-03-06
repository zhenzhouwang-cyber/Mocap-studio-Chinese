"""
云手动作可视化模块。

生成动作轨迹和节奏的可视化图表：
- 3D轨迹图
- 速度曲线图
- 节奏/亮相可视化
- 多格式导出
"""

from __future__ import annotations

import base64
from io import BytesIO
from pathlib import Path
from typing import Any

import numpy as np


def visualize_3d_trajectory(
    trajectories: dict[str, dict],
    markers: list[str] | None = None,
    title: str = "3D Trajectory",
    color_by: str = "marker",  # "marker" or "time"
) -> dict[str, Any]:
    """
    生成3D轨迹可视化数据。
    
    Args:
        trajectories: 轨迹数据字典
        markers: 要可视化的marker列表
        title: 图表标题
        color_by: 着色方式 ("marker"按标记, "time"按时间)
        
    Returns:
        可视化数据字典（可用于前端渲染）
    """
    if markers is None:
        markers = list(trajectories.keys())
    
    traces = []
    
    # 颜色映射
    colors = [
        "#E74C3C", "#3498DB", "#2ECC71", "#F39C12", 
        "#9B59B6", "#1ABC9C", "#E67E22", "#34495E"
    ]
    
    for idx, marker in enumerate(markers):
        if marker not in trajectories:
            continue
            
        traj = trajectories[marker]
        x = traj.get("x", [])
        y = traj.get("y", [])
        z = traj.get("z", [])
        
        if not x or not y or not z:
            continue
        
        # 根据color_by设置颜色
        if color_by == "marker":
            color = colors[idx % len(colors)]
        else:
            # 时间渐变 - 简化为单一颜色
            color = colors[0]
        
        trace = {
            "type": "scatter3d",
            "mode": "lines",
            "name": marker,
            "x": [round(v, 4) for v in x],
            "y": [round(v, 4) for v in y],
            "z": [round(v, 4) for v in z],
            "line": {
                "color": color,
                "width": 4,
            },
            "opacity": 0.8,
        }
        
        # 添加起点和终点标记
        trace["marker"] = {
            "size": 4,
            "color": [color] * len(x),
        }
        
        traces.append(trace)
    
    layout = {
        "title": title,
        "scene": {
            "xaxis": {"title": "X"},
            "yaxis": {"title": "Y"},
            "zaxis": {"title": "Z"},
            "aspectmode": "data",
        },
        "margin": {"l": 0, "r": 0, "t": 40, "b": 0},
    }
    
    return {
        "traces": traces,
        "layout": layout,
        "data_type": "plotly_3d",
    }


def visualize_speed_profile(
    speed_profile: dict[str, list],
    frame_rate: float = 30.0,
    title: str = "Speed Profile",
) -> dict[str, Any]:
    """
    生成速度曲线可视化。
    
    Args:
        speed_profile: 速度数据
        frame_rate: 帧率
        title: 图表标题
        
    Returns:
        可视化数据字典
    """
    mean_speeds = speed_profile.get("mean_speed_per_frame", [])
    threshold = speed_profile.get("threshold", 0)
    
    # 时间轴
    times = [i / frame_rate for i in range(len(mean_speeds))]
    
    # 主速度曲线
    trace_speed = {
        "type": "scatter",
        "mode": "lines",
        "name": "Speed",
        "x": [round(t, 3) for t in times],
        "y": [round(s, 4) if s is not None else None for s in mean_speeds],
        "line": {
            "color": "#3498DB",
            "width": 2,
        },
        "fill": "tozeroy",
        "fillcolor": "rgba(52, 152, 219, 0.2)",
    }
    
    # 阈值线
    trace_threshold = {
        "type": "scatter",
        "mode": "lines",
        "name": "Threshold",
        "x": [times[0], times[-1]],
        "y": [threshold, threshold],
        "line": {
            "color": "#E74C3C",
            "width": 1,
            "dash": "dash",
        },
    }
    
    layout = {
        "title": title,
        "xaxis": {"title": "Time (s)"},
        "yaxis": {"title": "Speed (m/s)"},
        "hovermode": "x unified",
        "margin": {"l": 50, "r": 20, "t": 40, "b": 40},
    }
    
    return {
        "traces": [trace_speed, trace_threshold],
        "layout": layout,
        "data_type": "plotly_2d",
    }


def visualize_rhythm(
    lixiang: list[dict],
    speed_profile: dict[str, list],
    frame_rate: float = 30.0,
    title: str = "Rhythm & Liangxiang",
) -> dict[str, Any]:
    """
    生成节奏和亮相可视化。
    
    Args:
        lixiang: 亮相数据列表
        speed_profile: 速度数据
        frame_rate: 帧率
        title: 图表标题
        
    Returns:
        可视化数据字典
    """
    mean_speeds = speed_profile.get("mean_speed_per_frame", [])
    times = [i / frame_rate for i in range(len(mean_speeds))]
    
    traces = []
    
    # 速度曲线
    trace_speed = {
        "type": "scatter",
        "mode": "lines",
        "name": "Speed",
        "x": [round(t, 3) for t in times],
        "y": [round(s, 4) if s is not None else None for s in mean_speeds],
        "line": {"color": "#3498DB", "width": 2},
    }
    traces.append(trace_speed)
    
    # 亮相区域（用垂直矩形标记）
    shapes = []
    for idx, lx in enumerate(lixiang):
        start_time = lx.get("start_time", 0)
        end_time = lx.get("end_time", 0)
        
        # 背景高亮
        shapes.append({
            "type": "rect",
            "xref": "x",
            "yref": "paper",
            "x0": start_time,
            "x1": end_time,
            "y0": 0,
            "y1": 1,
            "fillcolor": "rgba(231, 76, 60, 0.2)",
            "line": {"width": 0},
        })
        
        # 亮相标记线
        traces.append({
            "type": "scatter",
            "mode": "markers+text",
            "name": f"Liangxiang {idx+1}",
            "x": [(start_time + end_time) / 2],
            "y": [max([s for s in mean_speeds if s is not None], default=0) * 1.05],
            "text": [f"LX{idx+1}"],
            "textposition": "top center",
            "marker": {
                "color": "#E74C3C",
                "size": 10,
                "symbol": "diamond",
            },
        })
    
    layout = {
        "title": title,
        "xaxis": {"title": "Time (s)"},
        "yaxis": {"title": "Speed"},
        "shapes": shapes,
        "hovermode": "x unified",
    }
    
    return {
        "traces": traces,
        "layout": layout,
        "data_type": "plotly_2d",
    }


def visualize_circularity(
    circularity: dict[str, Any],
    trajectories: dict[str, dict],
    marker_name: str = "wrist_right",
    title: str = "Circularity Analysis",
) -> dict[str, Any]:
    """
    生成圆度分析可视化。
    
    Args:
        circularity: 圆度数据
        trajectories: 轨迹数据
        marker_name: 关键marker名称
        title: 图表标题
        
    Returns:
        可视化数据字典
    """
    if marker_name not in trajectories:
        return {"error": f"Marker {marker_name} not found"}
    
    traj = trajectories[marker_name]
    x = traj.get("x", [])
    z = traj.get("z", [])  # 使用X-Z平面（水平面）
    
    if not x or not z:
        return {"error": "Insufficient trajectory data"}
    
    # 轨迹线
    trace_traj = {
        "type": "scatter",
        "mode": "lines+markers",
        "name": "Trajectory",
        "x": [round(v, 4) for v in x],
        "y": [round(v, 4) for v in z],
        "line": {"color": "#3498DB", "width": 2},
        "marker": {
            "size": 4,
            "color": list(range(len(x))),  # 颜色随时间变化
            "colorscale": "Viridis",
            "showscale": True,
            "colorbar": {"title": "Time"},
        },
    }
    
    # 拟合圆（如果有圆心数据）
    shapes = []
    center = circularity.get("center", {})
    if center:
        cx = center.get("x", 0)
        cz = center.get("z", 0)
        radius = circularity.get("mean_radius", 0)
        
        # 绘制拟合圆
        theta = np.linspace(0, 2 * np.pi, 100)
        circle_x = [cx + radius * np.cos(t) for t in theta]
        circle_z = [cz + radius * np.sin(t) for t in theta]
        
        shapes.append({
            "type": "scatter",
            "mode": "lines",
            "name": "Fitted Circle",
            "x": circle_x,
            "y": circle_z,
            "line": {"color": "#E74C3C", "width": 2, "dash": "dash"},
        })
    
    layout = {
        "title": f"{title} (Score: {circularity.get('circularity_score', 0):.2f})",
        "xaxis": {"title": "X"},
        "yaxis": {"title": "Z"},
        "shapes": shapes,
        "aspectratio": {"x": 1, "y": 1},
    }
    
    return {
        "traces": [trace_traj],
        "layout": layout,
        "data_type": "plotly_2d",
    }


def visualize_comparison(
    current_result: dict[str, Any],
    reference_result: dict[str, Any],
    title: str = "Comparison",
) -> dict[str, Any]:
    """
    生成动作比对可视化。
    
    Args:
        current_result: 当前动作分析结果
        reference_result: 参考动作分析结果
        title: 图表标题
        
    Returns:
        可视化数据字典
    """
    traces = []
    
    # 当前动作轨迹
    curr_trajs = current_result.get("trajectories", {})
    for marker in ["wrist_left", "wrist_right"]:
        if marker in curr_trajs:
            traj = curr_trajs[marker]
            x = traj.get("x", [])
            z = traj.get("z", [])
            
            if x and z:
                traces.append({
                    "type": "scatter",
                    "mode": "lines",
                    "name": f"Current - {marker}",
                    "x": [round(v, 4) for v in x],
                    "y": [round(v, 4) for v in z],
                    "line": {"color": "#3498DB", "width": 2},
                })
    
    # 参考动作轨迹
    ref_trajs = reference_result.get("trajectories", {})
    for marker in ["wrist_left", "wrist_right"]:
        if marker in ref_trajs:
            traj = ref_trajs[marker]
            x = traj.get("x", [])
            z = traj.get("z", [])
            
            if x and z:
                traces.append({
                    "type": "scatter",
                    "mode": "lines",
                    "name": f"Reference - {marker}",
                    "x": [round(v, 4) for v in x],
                    "y": [round(v, 4) for v in z],
                    "line": {"color": "#E74C3C", "width": 2, "dash": "dot"},
                })
    
    layout = {
        "title": title,
        "xaxis": {"title": "X"},
        "yaxis": {"title": "Z"},
        "hovermode": "closest",
    }
    
    return {
        "traces": traces,
        "layout": layout,
        "data_type": "plotly_2d",
    }


def visualize_dang_features(
    dang_result: dict[str, Any],
    title: str = "Dang Classification Features",
) -> dict[str, Any]:
    """
    生成行当特征可视化。
    
    Args:
        dang_result: 行当判定结果
        title: 图表标题
        
    Returns:
        可视化数据字典
    """
    # 雷达图数据
    style = dang_result.get("style", {})
    speed = dang_result.get("speed", {})
    amplitude = dang_result.get("amplitude", {})
    
    # 特征值
    categories = ["Weight", "Time", "Flow", "Space", "Speed", "Amplitude"]
    values = [
        style.get("weight", 0.5),
        style.get("time", 0.5),
        style.get("flow", 0.5),
        style.get("space", 0.5),
        speed.get("relative_speed", 0.5),
        amplitude.get("normalized_amplitude", 0.5),
    ]
    
    # 雷达图
    trace_radar = {
        "type": "scatterpolar",
        "r": values + [values[0]],  # 闭合
        "theta": categories + [categories[0]],
        "fill": "toself",
        "fillcolor": "rgba(52, 152, 219, 0.3)",
        "line": {"color": "#3498DB", "width": 2},
        "name": "Features",
    }
    
    # 评分条形图
    scores = dang_result.get("all_scores", {})
    bar_trace = {
        "type": "bar",
        "x": list(scores.keys()),
        "y": list(scores.values()),
        "marker": {
            "color": ["#2ECC71", "#3498DB", "#F39C12", "#E74C3C", "#9B59B6"],
        },
        "name": "Scores",
    }
    
    layout_radar = {
        "title": f"{title} - {dang_result.get('dang_cn', 'Unknown')}",
        "polar": {
            "radialaxis": {
                "visible": True,
                "range": [0, 1],
            },
        },
        "showlegend": False,
    }
    
    layout_bar = {
        "title": "Dang Classification Scores",
        "xaxis": {"title": "Dang Type"},
        "yaxis": {"title": "Score", "range": [0, 1]},
    }
    
    return {
        "traces_radar": [trace_radar],
        "layout_radar": layout_radar,
        "traces_bar": [bar_trace],
        "layout_bar": layout_bar,
        "data_type": "plotly_radar_and_bar",
    }


def export_html_report(
    yunshou_result: dict[str, Any],
    output_path: str | Path,
    title: str = "Yunshou Analysis Report",
) -> dict[str, Any]:
    """
    生成HTML可视化报告。
    
    Args:
        yunshou_result: 云手分析结果
        output_path: 输出路径
        title: 报告标题
        
    Returns:
        导出结果
    """
    import json
    
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # 收集所有可视化数据
    visualizations = {}
    
    # 1. 3D轨迹
    trajs = yunshou_result.get("trajectories", {})
    if trajs:
        visualizations["trajectory_3d"] = visualize_3d_trajectory(
            trajs, 
            title="3D Trajectory"
        )
    
    # 2. 速度曲线
    rhythm = yunshou_result.get("rhythm", {})
    if rhythm:
        speed_profile = rhythm.get("speed_profile", {})
        if speed_profile:
            visualizations["speed_profile"] = visualize_speed_profile(
                speed_profile,
                title="Speed Profile"
            )
        
        # 3. 亮相可视化
        lixiang = rhythm.get("lixiang", [])
        if lixiang:
            visualizations["rhythm"] = visualize_rhythm(
                lixiang,
                speed_profile,
                title="Rhythm & Liangxiang"
            )
    
    # 4. 圆度分析
    circularity = yunshou_result.get("circularity", {})
    if circularity and trajs:
        visualizations["circularity"] = visualize_circularity(
            circularity,
            trajs,
            title="Circularity Analysis"
        )
    
    # 5. 行当特征
    dang = yunshou_result.get("dang", {})
    if dang:
        visualizations["dang_features"] = visualize_dang_features(
            dang,
            title="Dang Features"
        )
    
    # 生成HTML
    html_content = _generate_html_report(
        title=title,
        visualizations=visualizations,
        result=yunshou_result,
    )
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    
    return {
        "path": str(output_path),
        "size": output_path.stat().st_size,
        "visualizations": list(visualizations.keys()),
    }


def _generate_html_report(
    title: str,
    visualizations: dict[str, Any],
    result: dict[str, Any],
) -> str:
    """生成HTML报告内容"""
    import json
    
    # 提取关键数据
    meta = result.get("meta", {})
    dang = result.get("dang", {})
    rhythm_stats = result.get("rhythm", {}).get("rhythm_stats_enhanced", {})
    circularity = result.get("circularity", {})
    
    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 16px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(90deg, #2C3E50, #3498DB);
            color: white;
            padding: 30px;
            text-align: center;
        }}
        .header h1 {{
            margin: 0;
            font-size: 2em;
        }}
        .summary {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            padding: 30px;
            background: #f8f9fa;
        }}
        .summary-card {{
            background: white;
            padding: 20px;
            border-radius: 12px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            text-align: center;
        }}
        .summary-card h3 {{
            margin: 0 0 10px 0;
            color: #666;
            font-size: 0.9em;
            text-transform: uppercase;
        }}
        .summary-card .value {{
            font-size: 1.8em;
            font-weight: bold;
            color: #2C3E50;
        }}
        .section {{
            padding: 30px;
            border-bottom: 1px solid #eee;
        }}
        .section h2 {{
            color: #2C3E50;
            margin-top: 0;
        }}
        .chart {{
            width: 100%;
            height: 500px;
            margin: 20px 0;
        }}
        .chart-small {{
            height: 350px;
        }}
        .grid-2 {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
        }}
        @media (max-width: 768px) {{
            .grid-2 {{
                grid-template-columns: 1fr;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{title}</h1>
            <p>云手程式化动作分析报告</p>
        </div>
        
        <div class="summary">
            <div class="summary-card">
                <h3>行当</h3>
                <div class="value">{dang.get('dang_cn', '未知')}</div>
            </div>
            <div class="summary-card">
                <h3>置信度</h3>
                <div class="value">{dang.get('confidence', 0):.1%}</div>
            </div>
            <div class="summary-card">
                <h3>圆度</h3>
                <div class="value">{circularity.get('circularity_score', 0):.2f}</div>
            </div>
            <div class="summary-card">
                <h3>亮相次数</h3>
                <div class="value">{rhythm_stats.get('total_lixiang', 0)}</div>
            </div>
            <div class="summary-card">
                <h3>时长</h3>
                <div class="value">{meta.get('duration_sec', 0):.1f}s</div>
            </div>
        </div>
"""
    
    # 添加各可视化部分
    if "trajectory_3d" in visualizations:
        viz = visualizations["trajectory_3d"]
        html += f"""
        <div class="section">
            <h2>3D 轨迹</h2>
            <div id="chart-trajectory" class="chart"></div>
            <script>
                Plotly.newPlot('chart-trajectory', {json.dumps(viz['traces'])}, {json.dumps(viz['layout'])});
            </script>
        </div>
"""
    
    if "speed_profile" in visualizations:
        viz = visualizations["speed_profile"]
        html += f"""
        <div class="section">
            <h2>速度曲线</h2>
            <div id="chart-speed" class="chart chart-small"></div>
            <script>
                Plotly.newPlot('chart-speed', {json.dumps(viz['traces'])}, {json.dumps(viz['layout'])});
            </script>
        </div>
"""
    
    if "rhythm" in visualizations:
        viz = visualizations["rhythm"]
        html += f"""
        <div class="section">
            <h2>节奏与亮相</h2>
            <div id="chart-rhythm" class="chart"></div>
            <script>
                Plotly.newPlot('chart-rhythm', {json.dumps(viz['traces'])}, {json.dumps(viz['layout'])});
            </script>
        </div>
"""
    
    if "circularity" in visualizations:
        viz = visualizations["circularity"]
        html += f"""
        <div class="section">
            <h2>圆度分析</h2>
            <div id="chart-circularity" class="chart chart-small"></div>
            <script>
                Plotly.newPlot('chart-circularity', {json.dumps(viz['traces'])}, {json.dumps(viz['layout'])});
            </script>
        </div>
"""
    
    if "dang_features" in visualizations:
        viz = visualizations["dang_features"]
        html += f"""
        <div class="section">
            <h2>行当特征</h2>
            <div class="grid-2">
                <div id="chart-radar" class="chart chart-small"></div>
                <div id="chart-bar" class="chart chart-small"></div>
            </div>
            <script>
                Plotly.newPlot('chart-radar', {json.dumps(viz['traces_radar'])}, {json.dumps(viz['layout_radar'])});
                Plotly.newPlot('chart-bar', {json.dumps(viz['traces_bar'])}, {json.dumps(viz['layout_bar'])});
            </script>
        </div>
"""
    
    html += """
        <div class="section" style="text-align: center; color: #666; font-size: 0.9em;">
            <p>Generated by Opera Mocap Tool</p>
        </div>
    </div>
</body>
</html>
"""
    
    return html
