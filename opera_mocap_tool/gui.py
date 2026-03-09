"""Streamlit 可交互数据分析界面。"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

# 直接以脚本运行时，将项目根加入 path，避免相对导入失败
_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from opera_mocap_tool.analyzer import analyze
from opera_mocap_tool.config import (
    DEFAULT_BLENDER_EXE,
    DEFAULT_EXPORT_DIR,
    THEME_PRIMARY,
    THEME_PRIMARY_LIGHT,
    VIEWER_SERVER_PORT,
    VIEWER_TEMP_DIR,
)

# Plotly 图表统一配色
PLOTLY_COLORS = {"line": "#2ecc71", "area": "#9b59b6", "bar": "#3498db"}
from opera_mocap_tool.export import export
from opera_mocap_tool.io import load_mocap
from opera_mocap_tool.plotting import plot_analysis, plot_3d_trajectory
from opera_mocap_tool.viewer_3d import build_3d_viewer_html
from opera_mocap_tool.skeleton import get_skeleton_segments

# 新增的运动学分析模块
from opera_mocap_tool.analysis.frequency import (
    compute_frequency_analysis,
    compute_periodicity_metrics,
    detect_periodic_motions,
)
from opera_mocap_tool.analysis.quality import (
    compute_jerk_analysis,
    compute_motion_start_end_analysis,
    compute_motion_quality_overall,
)
from opera_mocap_tool.analysis.balance import (
    compute_center_of_mass,
    compute_balance_analysis,
    compute_stability_during_motion,
)
from opera_mocap_tool.analysis.kinematic import (
    compute_left_right_symmetry,
    compute_joint_range_analysis,
)
from opera_mocap_tool.analysis.segments import (
    compute_motion_phases,
    detect_motion_boundaries,
)

# 商业模块导入
try:
    from opera_mocap_tool.commercial import (
        ParticlePreset,
        EmitterShape,
        ParticleEmitter,
        ParticleSystem,
        TDParticleTransmitter,
        PresetLibrary,
        DangType,
        BodyPart,
        RigConfig,
        OperaRigBuilder,
        OperaMaterialLibrary,
        OperaAnimationLibrary,
    )
    COMMERCIAL_AVAILABLE = True
except ImportError:
    COMMERCIAL_AVAILABLE = False

STYLE_CSS = """
<style>
    :root {
        --bg:       #08080b;
        --surface:  #111118;
        --card:     #16161f;
        --border:   #232330;
        --text:     #e2e8f0;
        --muted:    #7b8494;
        --accent:   #22c55e;
        --accent-h: #16a34a;
        --font:     'PingFang SC', 'Noto Sans SC', 'Microsoft YaHei', '微软雅黑', system-ui, -apple-system, sans-serif;
    }

    /* ===== 全局字体 & 背景 ===== */
    /* 注意：不覆盖 span 避免 Material Icons 图标被误渲染为文字 */
    html, body, [data-testid="stAppViewContainer"], .main,
    [data-testid="stSidebar"], .stMarkdown, p, label, h1, h2, h3, h4, button, li, td, th, div {
        font-family: var(--font) !important;
    }
    /* 显式恢复 Material Icons 的字体 */
    span.material-icons, span.material-symbols-outlined {
        font-family: 'Material Icons', 'MaterialIconsOutlined', 'MaterialSymbolsOutlined', sans-serif !important;
    }
    html, body { background: var(--bg) !important; }

    /* ===== 隐藏 Streamlit 默认 header ===== */
    [data-testid="stHeader"], header[data-testid="stHeader"] {
        display: none !important; height: 0 !important; padding: 0 !important; margin: 0 !important;
    }

    /* ===== 全页面零留白 ===== */
    [data-testid="stAppViewContainer"],
    [data-testid="stAppViewContainer"] > section,
    [data-testid="stAppViewContainer"] > div,
    .main, section.main {
        background: var(--bg) !important;
        padding-top: 0 !important;
        margin-top: 0 !important;
    }
    .main .block-container,
    div[data-testid="stMainBlockContainer"],
    div[class*="block-container"] {
        padding: 0.5rem 1rem 1rem 1rem !important;
        padding-top: 0.5rem !important;
        max-width: 100% !important;
        background: transparent !important;
    }

    /* ===== Tabs 顶栏：紧贴顶部，撑满宽度 ===== */
    .stTabs { margin-top: 0 !important; padding-top: 0 !important; }
    .stTabs [data-baseweb="tab-list"] {
        display: flex !important;
        align-items: center;
        gap: 2px;
        background: var(--surface) !important;
        padding: 4px 8px;
        border-radius: 0 0 10px 10px;
        border: 1px solid var(--border);
        border-top: none;
        width: 100%;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        padding: 6px 16px;
        font-weight: 500;
        font-size: 0.83rem;
        color: var(--muted) !important;
        transition: all 0.15s;
        white-space: nowrap;
    }
    .stTabs [data-baseweb="tab"]:hover { color: var(--text) !important; background: rgba(255,255,255,0.05); }
    .stTabs [aria-selected="true"] {
        background: var(--accent) !important;
        color: #fff !important;
        box-shadow: 0 2px 8px rgba(34,197,94,0.25);
    }
    .stTabs [data-baseweb="tab-highlight"],
    .stTabs [data-baseweb="tab-border"] { display: none !important; }

    /* ===== 空状态 ===== */
    .empty-hero { text-align: center; padding: 4rem 2rem 2rem; }
    .empty-hero h2 { color: var(--text); font-size: 1.5rem; font-weight: 700; margin-bottom: 0.4rem; }
    .empty-hero p  { color: var(--muted); font-size: 0.95rem; }

    /* ===== 文字颜色 ===== */
    .main .stMarkdown, .main p, .main label, .main span { color: var(--text) !important; }
    .main h1, .main h2, .main h3, .main h4 { color: #f1f5f9 !important; }
    .main .stCaption { color: var(--muted) !important; }

    /* ===== 指标卡片 ===== */
    .stMetric {
        background: var(--card) !important;
        padding: 0.85rem 1rem;
        border-radius: 10px;
        border: 1px solid var(--border);
        transition: border-color 0.2s;
    }
    .stMetric label { color: var(--muted) !important; font-size: 0.8rem; }
    .stMetric [data-testid="stMetricValue"] { color: var(--accent) !important; font-weight: 700; }
    .stMetric:hover { border-color: var(--accent); }

    /* ===== 侧边栏 ===== */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0a0a10 0%, #111118 100%) !important;
        border-right: 1px solid var(--border);
    }
    [data-testid="stSidebar"] .stMarkdown,
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3, [data-testid="stSidebar"] h4 { color: #f1f5f9 !important; }
    [data-testid="stSidebar"] label { color: var(--muted) !important; }
    [data-testid="stFileUploader"] {
        background: var(--card) !important;
        padding: 0.85rem;
        border-radius: 10px;
        border: 2px dashed var(--border);
    }
    /* 侧边栏 expander：紧凑、图标式，默认折叠 */
    [data-testid="stSidebar"] .stExpander {
        margin-bottom: 0.35rem;
        border-radius: 8px;
        border: 1px solid var(--border);
    }
    [data-testid="stSidebar"] .stExpander summary {
        padding: 0.5rem 0.65rem !important;
        font-size: 0.9rem !important;
        font-weight: 600 !important;
        color: var(--text) !important;
        min-height: auto !important;
    }
    [data-testid="stSidebar"] .stExpander summary:hover {
        color: var(--accent) !important;
        background: rgba(34, 197, 94, 0.08);
    }
    [data-testid="stSidebar"] .stExpander [data-testid="stExpanderDetails"] {
        padding: 0.5rem 0.65rem 0.65rem !important;
        border-top: 1px solid var(--border);
    }

    /* ===== 右侧设置面板 ===== */
    .settings-card {
        background: var(--card);
        border: 1px solid var(--border);
        border-radius: 12px;
        padding: 1.1rem 1rem;
        margin-bottom: 0.75rem;
    }
    .settings-card .section-title {
        display: flex; align-items: center; gap: 6px;
        font-weight: 600; font-size: 0.88rem; color: var(--text);
        margin-bottom: 0.6rem; letter-spacing: 0.2px;
    }
    .settings-card .section-title .icon { color: var(--accent); }

    /* ===== 按钮 ===== */
    .stButton > button {
        background: var(--accent) !important; color: #fff !important;
        border: none; border-radius: 8px; font-weight: 600; font-size: 0.85rem;
        transition: all 0.15s;
    }
    .stButton > button:hover { background: var(--accent-h) !important; transform: translateY(-1px); }
    .stDownloadButton > button {
        background: var(--card) !important; color: var(--text) !important;
        border: 1px solid var(--border); border-radius: 8px; font-size: 0.85rem;
    }
    .stDownloadButton > button:hover { border-color: var(--accent); }

    /* ===== Expander / Alert / Plot ===== */
    .stSuccess, .stInfo, .stWarning {
        border-radius: 8px; border-left: 3px solid var(--accent);
        background: var(--card) !important;
    }
    .stExpander {
        background: var(--card) !important;
        border: 1px solid var(--border); border-radius: 10px;
    }
    .plotly-graph-div { border-radius: 10px; overflow: hidden; background: var(--surface) !important; }
    div[data-testid="stHorizontalBlock"] > div { align-items: stretch; }
    hr { border-color: var(--border) !important; }

    /* ===== 3D 查看器 iframe ===== */
    iframe { border-radius: 10px; border: 1px solid var(--border); }
    [data-testid="stAppViewContainer"] { background: var(--bg) !important; }

    /* ===== 上传区域样式 ===== */
    [data-testid="stFileUploaderDropzone"] {
        padding: 1rem;
    }

    /* ===== 隐藏 JS 注入 iframe 的占位高度 ===== */
    iframe[height="0"], iframe[height="0"] + div { display: none !important; height: 0 !important; }

    /* ===== 输入框美化 ===== */
    .stTextInput input, .stSelectbox select,
    [data-baseweb="input"] input, [data-baseweb="select"] {
        background: var(--surface) !important;
        border: 1px solid var(--border) !important;
        border-radius: 8px !important;
        color: var(--text) !important;
        font-size: 0.85rem !important;
    }
    .stTextInput input:focus, [data-baseweb="input"] input:focus {
        border-color: var(--accent) !important;
        box-shadow: 0 0 0 2px rgba(34,197,94,0.15) !important;
    }

    /* ===== Slider 美化 ===== */
    [data-testid="stSlider"] [data-baseweb="slider"] [role="slider"] {
        background: var(--accent) !important;
        border-color: var(--accent) !important;
    }
    [data-testid="stSlider"] [data-baseweb="slider"] div[data-testid="stSliderTrackFill"] {
        background: var(--accent) !important;
    }

    /* ===== Checkbox 美化 ===== */
    [data-testid="stCheckbox"] label span:first-child {
        border-color: var(--border) !important;
        background: var(--surface) !important;
    }
    [data-testid="stCheckbox"] input:checked + div {
        background: var(--accent) !important;
        border-color: var(--accent) !important;
    }

    /* ===== Selectbox 美化 ===== */
    [data-baseweb="select"] > div {
        background: var(--surface) !important;
        border: 1px solid var(--border) !important;
        border-radius: 8px !important;
    }
    [data-baseweb="popover"] [data-baseweb="menu"] {
        background: var(--card) !important;
        border: 1px solid var(--border) !important;
        border-radius: 8px !important;
    }
    [data-baseweb="menu"] li { color: var(--text) !important; }
    [data-baseweb="menu"] li:hover { background: rgba(34,197,94,0.1) !important; }

    /* ===== 侧边栏标题美化 ===== */
    [data-testid="stSidebar"] .stCaption {
        color: var(--accent) !important;
        font-size: 0.78rem !important;
        letter-spacing: 0.5px;
        text-transform: uppercase;
        padding: 0.3rem 0 0.5rem;
    }

    /* ===== Spinner ===== */
    [data-testid="stSpinner"] { color: var(--accent) !important; }

    /* ===== 数据表格 ===== */
    [data-testid="stDataFrame"] { border-radius: 10px; overflow: hidden; }
    [data-testid="stDataFrame"] thead th {
        background: var(--surface) !important;
        color: var(--muted) !important;
        font-size: 0.8rem;
    }

    /* ===== 隐藏特定的arrow按钮（不要隐藏标签页的箭头图标）===== */
    /* [data-testid="collapsedControl"], */
    /* button[name*="arrow"] { */
    /*     display: none !important; */
    /*     visibility: hidden !important; */
    /* } */

    /* ===== 完全隐藏侧边栏 ===== */
    [data-testid="stSidebar"] {
        display: none !important;
        width: 0 !important;
        max-width: 0 !important;
        min-width: 0 !important;
        padding: 0 !important;
        margin: 0 !important;
        border: none !important;
        overflow: hidden !important;
    }

    /* 隐藏 expander 箭头（svg 图标） */
    [data-testid="stSidebar"] .stExpander summary svg,
    [data-testid="stSidebar"] .stExpander summary span[role="img"] {
        display: none !important;
    }
</style>
"""


def _open_viewer_in_browser(html_content: str, *, copy_glb: bool = False) -> None:
    """将 3D 查看器写入临时目录，启动 HTTP 服务并打开浏览器。"""
    import shutil
    import subprocess
    import webbrowser

    viewer_dir = Path(tempfile.gettempdir()) / VIEWER_TEMP_DIR
    viewer_dir.mkdir(exist_ok=True)
    (viewer_dir / "mocap_viewer.html").write_text(html_content, encoding="utf-8")
    if copy_glb:
        glb = _find_default_mixamo_glb()
        if glb and glb.exists():
            shutil.copy2(glb, viewer_dir / glb.name)
    try:
        subprocess.Popen(
            [sys.executable, "-m", "http.server", str(VIEWER_SERVER_PORT)],
            cwd=str(viewer_dir),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        url = f"http://localhost:{VIEWER_SERVER_PORT}/mocap_viewer.html"
        webbrowser.open(url)
        st.success(f"已打开 {url}")
    except OSError as e:
        st.error(f"启动服务器失败: {e}")


def _find_default_mixamo_glb() -> Path | None:
    """在项目 resource/ 下查找可用的 Mixamo GLB 文件。"""
    candidates = [
        Path(__file__).resolve().parent.parent / "resource" / "xbot.glb",
        Path(__file__).resolve().parent.parent / "resource" / "X Bot.glb",
    ]
    for p in candidates:
        if p.exists():
            return p
    return None


def run_gui() -> None:
    """启动 Streamlit 界面。"""
    st.set_page_config(
        page_title="MoCap Studio",
        page_icon="🎭",
        layout="wide",
        initial_sidebar_state="collapsed",
    )

    st.markdown(STYLE_CSS, unsafe_allow_html=True)
    
    # 用 JavaScript 移除特定的 arrow 按钮文字（只移除 sidebar 相关的）
    st.components.v1.html("""
<script>
document.addEventListener('DOMContentLoaded', function() {
    // 只移除侧边栏展开/折叠按钮中的 arrow 文字
    // 不要移除标签页的箭头图标
});
</script>
""", height=0, scrolling=False)

    # ==================== 内容Tab：功能模块 ====================
    tab_viewer, tab_overview, tab_quality, tab_kinematics, tab_opera, tab_yunshou, tab_ref_view, tab_sync_view, tab_exp_view, tab_commercial, tab_realtime = st.tabs([
        "🎬 动捕查看器",
        "📊 概览",
        "✅ 数据质量",
        "📈 运动学",
        "🎭 京剧特征",
        "☁️ 云手分析",
        "📐 参考比对",
        "🎵 唱做关联",
        "📤 导出",
        "💎 商业模块",
        "🔴 实时Pipeline",
    ])

    # ========== 动捕查看器 Tab：上传 + 3D 查看 ==========
    with tab_viewer:
        st.markdown("### 📂 上传动捕文件")
        file_path = st.file_uploader(
            "动捕/动画文件",
            type=["c3d", "csv", "fbx", "bvh"],
            help="支持 C3D、CSV、FBX、BVH；FBX 需填 Blender 路径",
            key="viewer_file_uploader",
        )
        blender_exe = st.text_input(
            "Blender 路径（仅 FBX 需要）",
            value=DEFAULT_BLENDER_EXE,
            placeholder="如 E:\\Software\\blender.exe",
            key="viewer_blender_exe",
        )
        if blender_exe and blender_exe.strip():
            from opera_mocap_tool.io import fbx_reader
            fbx_reader.set_blender_exe(blender_exe.strip())

        # 预处理选项
        st.markdown("---")
        st.markdown("### ⚙️ 预处理设置")
        filter_cutoff = st.slider(
            "滤波截止频率 (Hz)",
            2.0, 20.0, 6.0, 0.5,
            help="去除抖动，值越小越平滑",
        )
        _interp_labels = {"线性": "linear", "样条": "spline", "三次": "cubic"}
        _interp_sel = st.selectbox(
            "插值方法",
            list(_interp_labels.keys()),
            help="填补丢失 marker",
        )
        interp_method = _interp_labels[_interp_sel]
        max_gap = st.slider("最大插值间隙（帧）", 1, 50, 10)

        # 没有上传文件时显示空状态
        if not file_path:
            st.markdown(
                '<div class="empty-hero">'
                '<h2>今天要分析什么动捕？</h2>'
                '<p>上传 C3D / CSV / FBX / BVH 文件，开始动捕分析与导出。</p>'
                '</div>',
                unsafe_allow_html=True,
            )
            st.stop()

        # FBX 需要 Blender 路径
        is_fbx = file_path.name.lower().endswith(".fbx")
        if is_fbx and (not blender_exe or not blender_exe.strip()):
            st.warning("检测到 FBX 文件。请填写 Blender 路径后重新上传。")
            st.info("例如：`E:\\Software\\blender.exe`")
            st.stop()

        # 保存上传文件
        tmp_path = Path(tempfile.gettempdir()) / file_path.name
        with open(tmp_path, "wb") as f:
            f.write(file_path.getvalue())

        # 分析（带缓存）
        cache_key = f"{file_path.name}_{filter_cutoff}_{interp_method}_{max_gap}"
        if "analysis_cache" not in st.session_state or st.session_state.get("cache_key") != cache_key:
            with st.spinner("🔄 正在分析..."):
                try:
                    result = analyze(
                        tmp_path,
                        filter_cutoff_hz=filter_cutoff,
                        interp_method=interp_method,
                        max_gap_frames=max_gap,
                    )
                    st.session_state["analysis_result"] = result
                    st.session_state["cache_key"] = cache_key
                except Exception as e:
                    st.error(f"❌ 分析失败: {e}")
                    st.stop()
        result = st.session_state.get("analysis_result")
        if not result:
            st.error("分析结果为空")
            st.stop()

        # 3D 查看器
        st.markdown("---")
        viewer_cache_key = f"viewer_mocap_{file_path.name}"
        if viewer_cache_key not in st.session_state:
            with st.spinner("加载动捕数据用于查看..."):
                try:
                    st.session_state[viewer_cache_key] = load_mocap(tmp_path)
                    # 同时保存到固定key，供其他tab使用
                    st.session_state["current_mocap_data"] = load_mocap(tmp_path)
                except Exception as e:
                    st.error(f"加载失败: {e}")
                    st.session_state[viewer_cache_key] = None
        mocap_data = st.session_state.get(viewer_cache_key)

        if mocap_data is not None:
            n_frames = mocap_data.n_frames
            fr = mocap_data.frame_rate
            labels_all = mocap_data.marker_labels

            # 右侧设置面板
            viewer_col, settings_col = st.columns([3, 1])

            with settings_col:
                st.markdown(
                    '<div class="settings-card">'
                    '<div class="section-title"><span class="icon">⚙</span> 播放设置</div>'
                    '</div>',
                    unsafe_allow_html=True,
                )
                _default_step = 1 if n_frames <= 1200 else (2 if n_frames <= 2400 else 5)
                frame_step = st.select_slider(
                    "帧步长（1=最流畅）",
                    options=[1, 2, 5, 10, 20],
                    value=_default_step,
                    key="viewer_frame_step",
                )
                trail_frames = st.select_slider(
                    "轨迹尾迹（帧数）",
                    options=[0, 15, 30, 60, 90, 120],
                    value=0,
                    key="viewer_trail",
                )

                st.markdown(
                    '<div class="settings-card">'
                    '<div class="section-title"><span class="icon">🖼</span> 显示选项</div>'
                    '</div>',
                    unsafe_allow_html=True,
                )
                _max_slider = min(200, max(50, len(labels_all)))
                max_m = st.slider(
                    "最多显示 Marker",
                    10, _max_slider,
                    min(_max_slider, len(labels_all)),
                    key="viewer_max_markers",
                )
                show_skeleton = st.checkbox("骨骼连线", value=True, key="viewer_skeleton")
                skin_bones = st.checkbox("骨骼可视化", value=True, key="viewer_skin_bones", help="显示骨骼线段或圆柱体")
                show_axes = st.checkbox("坐标轴 (XYZ)", value=False, key="viewer_axes")
                show_grid = st.checkbox("地面网格", value=True, key="viewer_grid")
                show_labels = st.checkbox("关节名称", value=False, key="viewer_labels")

                skeleton_segments_list = (
                    get_skeleton_segments(list(mocap_data.markers.keys())) if show_skeleton else []
                )
                if show_skeleton and not skeleton_segments_list:
                    st.caption("⚠️ 未匹配到骨骼线段")

                # Mixamo 蒙皮功能已暂时禁用
                # 如需启用，请在下方填写 GLB 模型 URL
                mixamo_glb_url = None  # 蒙皮功能暂时禁用

            # 左侧 3D 查看器
            with viewer_col:
                st.caption(
                    f"**{n_frames}** 帧 · **{fr:.1f}** Hz · **{len(labels_all)}** Marker · "
                    f"时长 **{mocap_data.duration_sec:.2f}** s　　　"
                    f"🖱️ 拖拽旋转 · 滚轮缩放 · 右键平移"
                )

                with st.spinner("生成 3D 查看器..."):
                    html_content = build_3d_viewer_html(
                        mocap_data,
                        max_markers=max_m,
                        frame_step=frame_step,
                        show_skeleton=show_skeleton,
                        skeleton_segments=skeleton_segments_list if skeleton_segments_list else None,
                        skin_bones=skin_bones and bool(skeleton_segments_list),
                        trail_frames=trail_frames,
                        show_axes=show_axes,
                        show_grid=show_grid,
                        show_labels=show_labels,
                        mixamo_glb_url=mixamo_glb_url,
                        height=620,
                    )
                st.components.v1.html(html_content, height=650, scrolling=False)

                btn_col1, btn_col2, _ = st.columns([1, 1, 2])
                with btn_col1:
                    st.download_button(
                        "📥 下载 HTML",
                        data=html_content,
                        file_name="mocap_viewer.html",
                        mime="text/html",
                        key="viewer_download",
                    )
                with btn_col2:
                    if st.button("🌐 在浏览器中打开", key="viewer_open_browser"):
                        _open_viewer_in_browser(html_content)
        else:
            st.warning("无法加载动捕数据，请检查文件格式。")

    # ========== 概览 ==========
    with tab_overview:
        st.markdown("### 📊 分析概览")
        
        # 获取分析结果数据
        result = st.session_state.get("analysis_result")
        if result:
            meta = result.get("meta", {})
            rhythm = result.get("rhythm", {})
            
            st.markdown(f"**文件**：{meta.get('filename', '-')}")

            c1, c2, c3, c4 = st.columns(4)
            with c1:
                st.metric("帧数", f"{meta.get('n_frames', 0):,}")
            with c2:
                st.metric("帧率", f"{meta.get('frame_rate', 0)} Hz")
            with c3:
                st.metric("时长", f"{meta.get('duration_sec', 0)} 秒")
            with c4:
                st.metric("Marker 数", len(meta.get("marker_labels", [])))

            st.markdown("**Marker 列表**")
            labels = meta.get("marker_labels", [])
            st.write(", ".join(labels) if labels else "无")

            # 节奏统计
            rhythm_stats = rhythm.get("rhythm_stats", {})
            if rhythm_stats:
                st.markdown("---")
                st.markdown("**节奏统计**")
                r1, r2, r3 = st.columns(3)
                with r1:
                    st.metric("平均速度", f"{rhythm_stats.get('mean_speed', 0):.2f}")
                with r2:
                    st.metric("峰值速度", f"{rhythm_stats.get('max_speed', 0):.2f}")
                with r3:
                    st.metric("停顿次数", rhythm_stats.get("n_pauses", 0))
        else:
            st.info("请先在「动捕查看器」上传并分析动捕文件")

    # ========== 数据质量 ==========
    with tab_quality:
        st.markdown("### ✅ 数据质量")
        
        result = st.session_state.get("analysis_result")
        if result:
            qr = result.get("quality_report", {})
            if qr:
                global_q = qr.get("global", {})
                g1, g2, g3 = st.columns(3)
                with g1:
                    st.metric("总缺失率", f"{global_q.get('overall_missing_rate', 0) * 100:.1f}%")
                with g2:
                    st.metric("有效帧", global_q.get("n_frames", 0))
                with g3:
                    res = global_q.get("overall_mean_residual")
                    st.metric("平均残差", f"{res:.2f}" if res is not None else "-")

                markers_q = qr.get("markers", {})
                if markers_q:
                    with st.expander("各 Marker 缺失率", expanded=False):
                        df_q = pd.DataFrame(markers_q).T.reset_index()
                        df_q["缺失率 (%)"] = (df_q["missing_rate"].astype(float) * 100).round(1)
                        fig_bar = px.bar(
                            df_q,
                            x="index",
                            y="缺失率 (%)",
                            labels={"index": "Marker"},
                            color_discrete_sequence=[PLOTLY_COLORS["bar"]],
                        )
                        fig_bar.update_layout(
                            showlegend=False,
                            margin=dict(t=20, b=40),
                            xaxis_tickangle=-45,
                            height=280,
                        )
                        st.plotly_chart(fig_bar, use_container_width=True)
        else:
            st.info("请先在「动捕查看器」上传并分析动捕文件")

    # ========== 运动学 ==========
    with tab_kinematics:
        st.markdown("### 📈 运动学分析")
        
        result = st.session_state.get("analysis_result")
        
        # 尝试从session_state中获取MocapData对象
        mocap_data = None
        if "analysis_result" in st.session_state:
            # 查找存储的MocapData对象
            for key in st.session_state.keys():
                if key.startswith("viewer_mocap_") and st.session_state.get(key) is not None:
                    potential_data = st.session_state[key]
                    # 检查是否有markers属性（MocapData对象的特征）
                    if hasattr(potential_data, 'markers') and hasattr(potential_data, 'frame_rate'):
                        mocap_data = potential_data
                        break
        
        if result:
            kin = result.get("kinematics", {})
            meta = result.get("meta", {})
            
            # 创建运动学分析的子选项卡
            sub_tab_kin, sub_tab_freq, sub_tab_quality, sub_tab_balance, sub_tab_symmetry = st.tabs([
                "📊 基础运动学",
                "🎵 频域分析",
                "✨ 动作质量",
                "⚖️ 平衡分析",
                "🔄 对称性分析",
            ])
            
            markers = list(kin.get("velocities", {}).keys())
            
            # ========== 基础运动学 ==========
            with sub_tab_kin:
                if markers:
                    sel = st.selectbox("选择 Marker 查看", markers, key="kin_sel")

                    if sel:
                        v = kin["velocities"][sel]
                        speeds = v.get("speed", [])
                        fr = meta.get("frame_rate", 100)
                        times = [i / fr for i in range(len(speeds))]

                        if speeds:
                            df_speed = pd.DataFrame({"时间 (秒)": times, "速度": speeds})
                            fig = px.line(
                                df_speed,
                                x="时间 (秒)",
                                y="速度",
                                title=f"{sel} 速度曲线",
                            )
                            fig.update_traces(line=dict(color=PLOTLY_COLORS["line"], width=2))
                            fig.update_layout(
                                hovermode="x unified",
                                height=350,
                                margin=dict(t=40, b=40),
                                xaxis=dict(showgrid=True, gridwidth=1, gridcolor="rgba(0,0,0,0.1)"),
                                yaxis=dict(showgrid=True, gridwidth=1, gridcolor="rgba(0,0,0,0.1)"),
                            )
                            st.plotly_chart(fig, use_container_width=True)

                        # 位移曲线
                        disp = kin.get("displacement", {}).get(sel, [])
                        if disp:
                            df_disp = pd.DataFrame({"时间 (秒)": times[: len(disp)], "位移": disp[: len(times)]})
                            fig2 = px.area(
                                df_disp,
                                x="时间 (秒)",
                                y="位移",
                                title=f"{sel} 位移曲线",
                            )
                            fig2.update_traces(fill="tozeroy", line=dict(color=PLOTLY_COLORS["area"]))
                            fig2.update_layout(height=300, margin=dict(t=40, b=40))
                            st.plotly_chart(fig2, use_container_width=True)

                # 3D 轨迹
                traj = kin.get("trajectories", {})
                if traj:
                    st.markdown("---")
                    sel_traj = st.selectbox("3D 轨迹", list(traj.keys()), key="traj_sel")
                    if sel_traj:
                        t = traj[sel_traj]
                        df_3d = pd.DataFrame({"x": t["x"], "y": t["y"], "z": t["z"]})
                        fig3d = go.Figure(data=[go.Scatter3d(
                            x=df_3d["x"],
                            y=df_3d["y"],
                            z=df_3d["z"],
                            mode="lines+markers",
                            line=dict(color="#e74c3c", width=4),
                            marker=dict(size=3, color=df_3d.index, colorscale="Viridis"),
                        )])
                        fig3d.update_layout(
                            title=f"{sel_traj} 3D 轨迹",
                            scene=dict(
                                xaxis_title="X",
                                yaxis_title="Y",
                                zaxis_title="Z",
                                aspectmode="data",
                            ),
                            height=500,
                            margin=dict(l=0, r=0, t=40, b=0),
                        )
                        st.plotly_chart(fig3d, use_container_width=True)
            
            # ========== 频域分析 ==========
            with sub_tab_freq:
                st.markdown("#### 🎵 频域与周期分析")
                st.markdown("基于FFT的运动频谱分析，用于检测周期性动作（云手、跑圆场等）")
                
                if mocap_data is None:
                    st.warning("无法获取原始动捕数据，请重新上传文件")
                elif not kin:
                    st.warning("运动学数据不可用，请先完成基础分析")
                else:
                    try:
                        freq_result = compute_frequency_analysis(mocap_data, kin)
                        if freq_result.get("summary"):
                            s = freq_result["summary"]
                            col1, col2, col3, col4 = st.columns(4)
                            with col1:
                                st.metric("主频均值 (Hz)", s.get("mean_dominant_freq", "—"))
                            with col2:
                                st.metric("主频标准差", s.get("std_dominant_freq", "—"))
                            with col3:
                                st.metric("最小主频", s.get("min_dominant_freq", "—"))
                            with col4:
                                st.metric("最大主频", s.get("max_dominant_freq", "—"))
                        
                        # 显示周期性检测结果
                        periodic_result = detect_periodic_motions(mocap_data, kin)
                        if periodic_result.get("periodic_segments"):
                            st.markdown("##### 检测到的周期性动作")
                            for seg in periodic_result["periodic_segments"]:
                                st.write(f"- 周期: {seg.get('period_sec', '—')}秒, 频率: {seg.get('dominant_freq_hz', '—')}Hz, 强度: {seg.get('autocorrelation_strength', '—')}")
                        else:
                            st.info("未检测到明显的周期性动作")
                            
                    except Exception as e:
                        st.error(f"频域分析失败: {e}")
            
            # ========== 动作质量分析 ==========
            with sub_tab_quality:
                st.markdown("#### ✨ 动作质量分析")
                st.markdown("分析动作的平滑度（Jerk）和起止特征")
                
                if mocap_data is None:
                    st.warning("无法获取原始动捕数据，请重新上传文件")
                elif not kin:
                    st.warning("运动学数据不可用，请先完成基础分析")
                else:
                    try:
                        quality_result = compute_motion_quality_overall(mocap_data, kin)
                        
                        if quality_result.get("overall_quality"):
                            oq = quality_result["overall_quality"]
                            col1, col2 = st.columns(2)
                            with col1:
                                st.metric("综合质量评分", oq.get("score", "—"), oq.get("rating", ""))
                            with col2:
                                st.metric("分析Marker数", oq.get("n_markers_analyzed", "—"))
                        
                        # 显示各marker的平滑度评分
                        smooth_scores = quality_result.get("smoothness_scores", {})
                        if smooth_scores:
                            st.markdown("##### 各Marker平滑度")
                            smooth_df = pd.DataFrame([
                                {"Marker": k, "平滑度评分": v} 
                                for k, v in smooth_scores.items()
                            ])
                            if not smooth_df.empty:
                                fig_smooth = px.bar(
                                    smooth_df, 
                                    x="Marker", 
                                    y="平滑度评分",
                                    title="各Marker平滑度评分",
                                    color="平滑度评分",
                                    color_continuous_scale="RdYlGn"
                                )
                                fig_smooth.update_layout(height=350)
                                st.plotly_chart(fig_smooth, use_container_width=True)
                        
                    except Exception as e:
                        st.error(f"动作质量分析失败: {e}")
            
            # ========== 平衡分析 ==========
            with sub_tab_balance:
                st.markdown("#### ⚖️ 身体平衡与重心分析")
                st.markdown("分析动作过程中的身体稳定性和重心移动轨迹")
                
                if mocap_data is None:
                    st.warning("无法获取原始动捕数据，请重新上传文件")
                else:
                    try:
                        balance_result = compute_balance_analysis(mocap_data)
                        bm = balance_result.get("balance_metrics", {})
                        
                        if bm.get("stability"):
                            col1, col2 = st.columns(2)
                            with col1:
                                st.metric("稳定性评分", 
                                         bm["stability"].get("score", "—"), 
                                         bm["stability"].get("rating", ""))
                            with col2:
                                if bm.get("spatial_range"):
                                    st.metric("水平移动范围", f"{bm['spatial_range'].get('x_range', 0):.4f}m")
                                    st.metric("垂直移动范围", f"{bm['spatial_range'].get('z_range', 0):.4f}m")
                        
                        if bm.get("posture_trend"):
                            st.markdown("##### 姿势趋势")
                            pt = bm["posture_trend"]
                            col1, col2 = st.columns(2)
                            with col1:
                                st.write(f"前后趋势: {pt.get('vertical_trend', '—')}")
                                st.write(f"垂直偏移: {pt.get('vertical_offset', 0):.4f}m")
                            with col2:
                                st.write(f"左右趋势: {pt.get('lateral_trend', '—')}")
                                st.write(f"横向偏移: {pt.get('lateral_offset', 0):.4f}m")
                            
                    except Exception as e:
                        st.error(f"平衡分析失败: {e}")
            
            # ========== 对称性分析 ==========
            with sub_tab_symmetry:
                st.markdown("#### 🔄 左右对称性分析")
                st.markdown("分析左右身体运动的对称性，评估动作均衡程度")
                
                if mocap_data is None:
                    st.warning("无法获取原始动捕数据，请重新上传文件")
                elif not kin:
                    st.warning("运动学数据不可用，请先完成基础分析")
                else:
                    try:
                        sym_result = compute_left_right_symmetry(mocap_data, kin)
                        
                        if sym_result.get("_summary"):
                            s = sym_result["_summary"]
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.metric("对称性评分", s.get("mean_symmetry_score", "—"))
                            with col2:
                                st.metric("最低对称性", s.get("min_symmetry_score", "—"))
                            with col3:
                                st.metric("最高对称性", s.get("max_symmetry_score", "—"))
                        
                        # 显示各配对的详细分析
                        sm = sym_result.get("symmetry_metrics", {})
                        if sm:
                            st.markdown("##### 详细对称性分析")
                            sym_data = []
                            for pair_name, metrics in sm.items():
                                if isinstance(metrics, dict) and "symmetry_score" in metrics:
                                    sym_data.append({
                                        "对比组": pair_name,
                                        "对称性得分": metrics.get("symmetry_score", 0),
                                        "位置差异(m)": metrics.get("position_symmetry", {}).get("mean_diff", 0),
                                    })
                            
                            if sym_data:
                                sym_df = pd.DataFrame(sym_data)
                                fig_sym = px.bar(
                                    sym_df,
                                    x="对比组",
                                    y="对称性得分",
                                    title="左右对称性得分",
                                    color="对称性得分",
                                    color_continuous_scale="RdYlGn"
                                )
                                fig_sym.update_layout(height=350)
                                st.plotly_chart(fig_sym, use_container_width=True)
                            else:
                                st.info("未检测到有效的左右对比Marker对")
                                
                    except Exception as e:
                        st.error(f"对称性分析失败: {e}")
                    
        else:
            st.info("请先在「概览」选项卡加载并分析动捕数据")

    # ========== 京剧特征 ==========
    with tab_opera:
        st.markdown("### 🎭 京剧特征分析")
        
        result = st.session_state.get("analysis_result")
        if result:
            op = result.get("opera_features", {})
            
            if op:
                # 程式化动作 · 学理简述
                st.markdown("#### 程式化动作分析（学理依据）")
            st.markdown("""
            京剧身段遵循**程式化**理论：**精选**（从日常动作提炼关键）、**装饰**（粗装饰如放慢、加大幅度，精装饰如角色差异化）、
            **圆柔顺美**（轨迹圆润、力度柔和、衔接顺滑）。本页从幅度、圆顺度、节奏与肢体分类四方面做学术/艺术性刻画。
            """)

            styl = op.get("stylization", {})
            amp = op.get("amplitude", {})
            smooth = op.get("smoothness", {})
            rhythm_op = op.get("rhythm", {})

            # 程式化雷达图（艺术性多维度）
            if styl or amp or smooth:
                st.markdown("---")
                st.markdown("**程式化多维指标（雷达图）**")
                try:
                    from opera_mocap_tool.analysis.opera_features import classify_limb
                    labels_all = meta.get("marker_labels", [])
                    limb_counts = {}
                    for m in labels_all:
                        limb = classify_limb(m)
                        limb_counts[limb] = limb_counts.get(limb, 0) + 1
                    limb_names = {"upper_extremity": "上肢末端", "upper_limb": "上肢", "lower_limb": "下肢", "trunk": "躯干", "unknown": "其他"}
                except Exception:
                    limb_counts = {}
                    limb_names = {}

                r_labels = []
                r_values = []
                if styl:
                    r_labels.extend(["整体平均速度", "速度变异"])
                    r_values.extend([
                        styl.get("overall_mean_speed", 0) or 0,
                        min((styl.get("overall_speed_std", 0) or 0) * 2, 10),
                    ])
                if amp:
                    max_amps = [v.get("max", 0) for v in amp.values() if isinstance(v, dict)]
                    r_labels.append("平均最大幅度")
                    r_values.append(float(np.mean(max_amps)) if max_amps else 0)
                if smooth:
                    curv = [v.get("mean_curvature", 0) for v in smooth.values() if isinstance(v, dict)]
                    r_labels.append("圆顺度(低曲率)")
                    r_values.append(10 - min(float(np.mean(curv)) * 5, 10) if curv else 5)
                if r_labels and r_values:
                    fig_radar = go.Figure(data=go.Scatterpolar(
                        r=r_values + [r_values[0]],
                        theta=r_labels + [r_labels[0]],
                        fill="toself",
                        line=dict(color="rgb(180, 100, 80)"),
                        name="程式化指标",
                    ))
                    fig_radar.update_layout(
                        polar=dict(radialaxis=dict(visible=True)),
                        title="程式化程度概览",
                        height=360,
                        showlegend=False,
                    )
                    st.plotly_chart(fig_radar, use_container_width=True)

                if limb_counts:
                    st.markdown("**身段/肢体分类（水袖·身段）**")
                    st.caption("按 marker 名称推断：上肢末端（腕/手/袖）、上肢、下肢、躯干。")
                    df_limb = pd.DataFrame({
                        "肢体类型": [limb_names.get(k, k) for k in limb_counts],
                        "Marker 数": [limb_counts[k] for k in limb_counts],
                    })
                    st.dataframe(df_limb, use_container_width=True, hide_index=True)

            if styl:
                st.markdown("---")
                st.markdown("**程式化节奏指标**")
                s1, s2 = st.columns(2)
                with s1:
                    st.metric("整体平均速度", f"{styl.get('overall_mean_speed', 0):.2f}")
                with s2:
                    st.metric("速度变异", f"{styl.get('overall_speed_std', 0):.2f}")

            if amp:
                st.markdown("**幅度（各 Marker）**")
                df_amp = pd.DataFrame(amp).T
                fig_amp = px.bar(
                    df_amp.reset_index(),
                    x="index",
                    y="max",
                    labels={"index": "Marker", "max": "最大位移"},
                    color_discrete_sequence=["#f39c12"],
                    title="最大位移幅度",
                )
                fig_amp.update_layout(height=300, margin=dict(t=40, b=60), xaxis_tickangle=-45)
                st.plotly_chart(fig_amp, use_container_width=True)

            if smooth:
                with st.expander("圆顺度详情（曲率/速度平滑）"):
                    df_smooth = pd.DataFrame(smooth).T
                    st.dataframe(df_smooth.round(4), use_container_width=True)

            # 身段段落（动作段）：与唱腔/曲牌对照用
            action_segments = result.get("action_segments", [])
            if action_segments:
                st.markdown("---")
                st.markdown("**身段段落（动作段）**")
                st.caption("基于节奏停顿切分，可与音频段落对照。指标定义见 docs/opera_metrics.md。")
                df_seg = pd.DataFrame(action_segments)
                if "dominant_limb_display" in df_seg.columns:
                    df_seg = df_seg.rename(columns={"dominant_limb_display": "主导肢体"})
                st.dataframe(df_seg, use_container_width=True, hide_index=True)

            # 拉班近似特征（学术/创作）
            laban = result.get("laban_approx", {})
            if laban:
                st.markdown("---")
                st.markdown("**拉班近似特征（Space / Effort / Shape）**")
                st.caption("指标定义见 docs/opera_metrics.md；可用于论文引用与风格化通道导出。")
                s_space = laban.get("space", {})
                s_effort = laban.get("effort", {})
                s_shape = laban.get("shape", {})
                if s_space:
                    st.markdown("*Space（空间）*")
                    c1, c2, c3, c4 = st.columns(4)
                    with c1:
                        st.metric("左右跨度", s_space.get("span_left_right", "—"))
                    with c2:
                        st.metric("高低跨度", s_space.get("span_high_low", "—"))
                    with c3:
                        st.metric("前后跨度", s_space.get("span_forward_back", "—"))
                    with c4:
                        st.metric("重心速度", s_space.get("center_velocity_mean", "—"))
                if s_effort:
                    st.markdown("*Effort（力效）*")
                    e1, e2 = st.columns(2)
                    with e1:
                        st.metric("平均速度", s_effort.get("mean_speed", "—"))
                        st.metric("速度标准差", s_effort.get("std_speed", "—"))
                    with e2:
                        st.metric("平均加速度", s_effort.get("mean_acc", "—"))
                        st.metric("加速度标准差", s_effort.get("std_acc", "—"))
                if s_shape:
                    st.markdown("*Shape（形态）*")
                    st.metric("扩展度均值", s_shape.get("expansion_mean", "—"))
                    st.metric("扩展度标准差", s_shape.get("expansion_std", "—"))

    # ========== 云手分析 ==========
    with tab_yunshou:
        st.markdown("### ☁️ 云手程式化分析")
        
        st.markdown("""
        基于京剧程式化理论和拉班运动分析，提取云手特有指标：
        - **行当幅度判定**：老生齐眉/武生齐口/旦角齐胸/丑行齐腹
        - **三节协调**：稍节(手)→中节(肘)→根节(肩)时序分析
        - **反衬劲**：欲左先右、欲右先左的方向反转检测
        - **轨迹圆度**：云手轨迹的圆形程度分析
        """)
        
        # 选项：使用已加载数据或单独上传
        yunshou_data_source = st.radio(
            "数据来源",
            ["使用已加载数据", "上传云手视频/动捕文件"],
            horizontal=True,
            key="yunshou_data_source"
        )
        
        mocap_data = None
        yunshou_result = None
        
        if yunshou_data_source == "使用已加载数据":
            mocap_data = st.session_state.get("current_mocap_data")
        else:
            # 单独上传文件
            yunshou_file = st.file_uploader(
                "上传云手文件（支持C3D/CSV/FBX/BVH）",
                type=["c3d", "csv", "fbx", "bvh"],
                key="yunshou_upload"
            )
            if yunshou_file:
                import tempfile
                from opera_mocap_tool.io import load_mocap
                yunshou_tmp = Path(tempfile.gettempdir()) / yunshou_file.name
                with open(yunshou_tmp, "wb") as f:
                    f.write(yunshou_file.getvalue())
                try:
                    with st.spinner("加载文件..."):
                        mocap_data = load_mocap(yunshou_tmp)
                except Exception as e:
                    st.error(f"加载失败: {e}")
        
        if mocap_data:
            # 执行云手分析
            from opera_mocap_tool.analysis.yunshou_features import analyze_yunshou
            
            with st.spinner("分析云手特征..."):
                yunshou_result = analyze_yunshou(mocap_data)
                
                if yunshou_result:
                    st.markdown("---")
                    st.markdown("#### 🎭 行当判定")
                    
                    dang = yunshou_result.get("dang", {})
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("行当分类", dang.get("dang_cn", "未知"))
                    with col2:
                        st.metric("置信度", f"{dang.get('confidence', 0):.1%}")
                    with col3:
                        st.metric("归一化高度", dang.get("hand_height_norm", 0))
                    st.caption(dang.get("description", ""))
                    
                    # 三节协调
                    st.markdown("---")
                    st.markdown("#### 🔄 三节协调分析")
                    three_sec = yunshou_result.get("three_section", {})
                    ts_col1, ts_col2, ts_col3 = st.columns(3)
                    with ts_col1:
                        st.metric("协调评分", f"{three_sec.get('coordination_score', 0):.1f}")
                    with ts_col2:
                        st.metric("手腕-肘部延迟", three_sec.get("delay_wrist_elbow", "—"))
                    with ts_col3:
                        st.metric("肘部-肩部延迟", three_sec.get("delay_elbow_shoulder", "—"))
                    st.caption(three_sec.get("description", ""))
                    
                    # 反衬劲
                    st.markdown("---")
                    st.markdown("#### 🔀 反衬劲检测")
                    fancheng = yunshou_result.get("fancheng_jin", {})
                    fc_col1, fc_col2 = st.columns(2)
                    with fc_col1:
                        st.metric("方向反转次数", fancheng.get("n_reversals", 0))
                    with fc_col2:
                        st.metric("反转比例", f"{fancheng.get('reversal_ratio', 0):.2%}")
                    st.caption(fancheng.get("description", ""))
                    
                    # 轨迹圆度
                    st.markdown("---")
                    st.markdown("#### ⭕ 轨迹圆度分析")
                    circ = yunshou_result.get("circularity", {})
                    cr_col1, cr_col2, cr_col3 = st.columns(3)
                    with cr_col1:
                        st.metric("圆度评分", f"{circ.get('circularity_score', 0):.2f}")
                    with cr_col2:
                        st.metric("平均半径", circ.get("mean_radius", "—"))
                    with cr_col3:
                        st.metric("半径标准差", circ.get("radius_std", "—"))
                    st.caption(circ.get("description", ""))
                    
                    # 综合指标
                    st.markdown("---")
                    st.markdown("#### 📊 综合程式化指标")
                    
                    # 创建雷达图数据
                    yunshou_metrics = {
                        "行当置信度": dang.get("confidence", 0) * 100,
                        "三节协调": three_sec.get("coordination_score", 0),
                        "反衬劲比例": min(fancheng.get("reversal_ratio", 0) * 100, 100),
                        "轨迹圆度": circ.get("circularity_score", 0) * 100,
                    }
                    
                    # 复用京剧特征的雷达图
                    if yunshou_metrics:
                        try:
                            import plotly.graph_objects as go
                            labels = list(yunshou_metrics.keys())
                            values = list(yunshou_metrics.values())
                            
                            fig_yunshou = go.Figure(data=go.Scatterpolar(
                                r=values + [values[0]],
                                theta=labels + [labels[0]],
                                fill="toself",
                                line=dict(color="rgb(100, 150, 200)"),
                                name="云手指标",
                            ))
                            fig_yunshou.update_layout(
                                polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
                                title="云手程式化程度",
                                height=350,
                                showlegend=False,
                            )
                            st.plotly_chart(fig_yunshou, use_container_width=True)
                        except Exception:
                            # 如果plotly不可用，显示柱状图
                            st.bar_chart(pd.DataFrame(yunshou_metrics, index=["值"]))
                    
                    # 参考库比对
                    st.markdown("---")
                    st.markdown("#### 📚 与参考库比对")
                    
                    try:
                        from opera_mocap_tool.io.yunshou_references import YunshouReferenceDatabase
                        ref_db = YunshouReferenceDatabase()
                        
                        # 检查是否有参考数据
                        refs = ref_db.list_all()
                        if refs:
                            compare_btn = st.button("与参考库比对", key="yunshou_compare_btn")
                            if compare_btn:
                                with st.spinner("计算相似度..."):
                                    compare_results = ref_db.compare(mocap_data, top_k=3)
                                
                                if compare_results:
                                    st.markdown("**最相似的参考动作：**")
                                    for i, cr in enumerate(compare_results):
                                        with st.expander(f"#{i+1} {cr.get('ref_name', '未知')}"):
                                            st.metric("相似度", f"{cr.get('similarity', 0):.1%}")
                                            st.caption(f"行当: {cr.get('dang', '未知')}")
                                else:
                                    st.info("未找到相似参考动作")
                        else:
                            st.info("参考库为空，请先添加参考数据")
                    except Exception as e:
                        st.warning(f"参考库功能暂时不可用: {e}")
                    
                    # 导出用于生成艺术
                    st.markdown("---")
                    st.markdown("#### 🎨 生成艺术数据导出")
                    
                    trajectories = yunshou_result.get("trajectories", {})
                    if trajectories:
                        st.markdown("**导出格式选项：**")
                        export_format = st.selectbox(
                            "选择导出格式",
                            ["JSON (特征+轨迹)", "TouchDesigner参数映射", "Python脚本"],
                            key="yunshou_export_format"
                        )
                        
                        export_btn = st.button("导出云手数据", key="export_yunshou_traj")
                        if export_btn:
                            import json
                            
                            if export_format == "JSON (特征+轨迹)":
                                # 简化轨迹数据用于导出
                                export_data = {
                                    "yunshou_features": {
                                        "dang": dang,
                                        "three_section": three_sec,
                                        "fancheng_jin": fancheng,
                                        "circularity": circ,
                                    },
                                    "trajectories": trajectories,
                                }
                                
                                # 保存为JSON
                                export_path = Path(tempfile.gettempdir()) / "yunshou_export.json"
                                with open(export_path, "w", encoding="utf-8") as f:
                                    json.dump(export_data, f, ensure_ascii=False, indent=2)
                                
                                st.success(f"已导出到: {export_path}")
                                st.download_button(
                                    label="下载JSON文件",
                                    data=export_path.read_text(encoding="utf-8"),
                                    file_name="yunshou_data.json",
                                    mime="application/json",
                                )
                                
                            elif export_format == "TouchDesigner参数映射":
                                # 使用新的映射模块
                                from opera_mocap_tool.analysis.yunshou_art_mapping import export_to_touchdesigner
                                
                                td_path = Path(tempfile.gettempdir()) / "yunshou_td_params.json"
                                export_to_touchdesigner(yunshou_result, td_path)
                                
                                st.success(f"已导出TouchDesigner参数到: {td_path}")
                                st.download_button(
                                    label="下载TouchDesigner参数",
                                    data=td_path.read_text(encoding="utf-8"),
                                    file_name="yunshou_td_params.json",
                                    mime="application/json",
                                )
                                
                            else:  # Python脚本
                                from opera_mocap_tool.analysis.yunshou_art_mapping import create_touchdesigner_script
                                
                                script = create_touchdesigner_script(yunshou_result)
                                
                                st.success("已生成TouchDesigner脚本")
                                st.download_button(
                                    label="下载Python脚本",
                                    data=script,
                                    file_name="yunshou_td_script.py",
                                    mime="text/x-python",
                                )
                    else:
                        st.caption("无可用轨迹数据")
        else:
            st.info("请上传云手文件或选择使用已加载数据")

    # ========== 参考比对 ==========
    with tab_ref_view:
        st.markdown("### 📐 参考动作比对")
        
        # 获取预处理设置
        filter_cutoff = st.slider("滤波截止频率 (Hz)", 2.0, 20.0, 6.0, 0.5, key="ref_filter_cutoff")
        _interp_labels = {"线性": "linear", "样条": "spline", "三次": "cubic"}
        _interp_sel = st.selectbox("插值方法", list(_interp_labels.keys()), key="ref_interp_sel")
        interp_method = _interp_labels[_interp_sel]
        max_gap = st.slider("最大插值间隙（帧）", 1, 50, 10, key="ref_max_gap")
        
        # 上传参考文件
        st.markdown("---")
        st.markdown("#### 📂 上传参考动作")
        reference_file = st.file_uploader(
            "参考动作（DTW 比对与评分）",
            type=["c3d", "csv", "fbx", "bvh"],
            help="上传参考动捕做时序对齐与相似度评分",
            key="reference_upload",
        )
        
        result = st.session_state.get("analysis_result")
        reference_compare_result = None
        reference_interpretation = None
        
        if result and reference_file and getattr(reference_file, "name", None):
            blender_exe = st.session_state.get("viewer_blender_exe", "")
            ref_is_fbx = reference_file.name.lower().endswith(".fbx")
            if ref_is_fbx and (not blender_exe or not blender_exe.strip()):
                st.warning("参考动作为 FBX，请先在「动捕查看器」填写 Blender 路径。")
            else:
                ref_tmp = Path(tempfile.gettempdir()) / ("ref_" + reference_file.name)
                try:
                    with open(ref_tmp, "wb") as f:
                        f.write(reference_file.getvalue())
                    ref_result = analyze(
                        ref_tmp,
                        filter_cutoff_hz=filter_cutoff,
                        interp_method=interp_method,
                        max_gap_frames=max_gap,
                    )
                    from opera_mocap_tool.analysis.reference_compare import compare_with_reference, interpret_reference_comparison
                    reference_compare_result = compare_with_reference(result, ref_result, normalize=True)
                    if reference_compare_result.get("error"):
                        reference_compare_result = None
                    else:
                        reference_interpretation = interpret_reference_comparison(result, ref_result, reference_compare_result)
                except Exception as e:
                    st.warning(f"参考比对失败: {e}")
        
        # 显示比对结果
        if reference_compare_result and reference_interpretation:
            st.markdown("---")
            st.markdown("#### DTW 比对结果")
            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric("DTW 距离", reference_compare_result.get("dtw_distance", "—"))
            with c2:
                st.metric("当前帧数", reference_compare_result.get("n_frames_current", "—"))
            with c3:
                st.metric("参考帧数", reference_compare_result.get("n_frames_reference", "—"))
            st.metric("对齐比例", reference_compare_result.get("align_ratio", "—"))
            by_limb = reference_compare_result.get("by_limb", {})
            if by_limb:
                st.markdown("**按肢体评分**")
                df_limb = pd.DataFrame([
                    {"肢体": v.get("label", k), "DTW 距离": v.get("dtw_distance"), "通道数": v.get("n_columns")}
                    for k, v in by_limb.items()
                ])
                st.dataframe(df_limb, use_container_width=True, hide_index=True)
            st.markdown("**可解释反馈**")
            for line in reference_interpretation.get("text_conclusions", []):
                st.write(f"- {line}")
            with st.expander("时间偏移与缩放"):
                st.metric("时间偏移 (秒)", reference_interpretation.get("time_shift_sec"))
                st.metric("时间缩放比", reference_interpretation.get("time_scale_ratio"))
                st.metric("节奏错位 (秒)", reference_interpretation.get("lapsing_sec"))
        elif result:
            st.info("上传参考动作文件（C3D、CSV、FBX、BVH）进行 DTW 比对分析")

    # ========== 唱做关联 ==========
    with tab_sync_view:
        st.markdown("### 🎵 唱做关联分析")
        
        # 上传音频文件
        st.markdown("#### 📂 上传关联音频")
        audio_file = st.file_uploader(
            "关联音频",
            type=["wav", "mp3", "flac", "ogg", "m4a", "mp4"],
            help="上传与动捕对应的音频文件，分析节拍偏移、段落重叠等",
            key="audio_upload",
        )
        
        result = st.session_state.get("analysis_result")
        sync_report = None
        
        if result and audio_file and getattr(audio_file, "name", None):
            audio_tmp = Path(tempfile.gettempdir()) / audio_file.name
            try:
                with open(audio_tmp, "wb") as f:
                    f.write(audio_file.getvalue())
            except Exception:
                audio_tmp = None
            if audio_tmp and audio_tmp.exists():
                try:
                    from jingju_audio_tool.analyzer import analyze as audio_analyze
                    from opera_mocap_tool.analysis.audio_sync import compute_sync_report
                    audio_result = audio_analyze(audio_tmp)
                    sync_report = compute_sync_report(result, audio_result)
                except ImportError:
                    st.error("未安装 jingju_audio_tool，无法做唱做关联分析。")
                except Exception as e:
                    st.warning(f"唱做关联分析失败: {e}")
        
        # 显示同步报告
        if sync_report:
            st.markdown("---")
            st.markdown("#### 同步分析报告")
            bos = sync_report.get("beat_offset_stats", {})
            if bos:
                st.markdown("**节拍偏移（音频节拍 → 最近动捕事件）**")
                c1, c2, c3 = st.columns(3)
                with c1:
                    st.metric("平均偏移 (秒)", f"{bos.get('mean_sec', 0):.4f}")
                with c2:
                    st.metric("标准差 (秒)", f"{bos.get('std_sec', 0):.4f}")
                with c3:
                    st.metric("节拍数", bos.get("n_beats", 0))
            so = sync_report.get("segment_overlap", {})
            if so:
                st.markdown("**段落重叠（动作段与音频段）**")
                st.write(so.get("summary", ""))
                st.metric("重叠合计 (秒)", so.get("total_overlap_sec", 0))
            corr = sync_report.get("correlation_speed_vs_rms", {})
            if corr.get("n_points", 0) > 0:
                st.markdown("**速度–能量相关**")
                r = corr.get("pearson")
                st.metric("Pearson 相关系数 (动捕速度 vs 音频 RMS)", f"{r:.4f}" if r is not None else "—")
            meta_sync = sync_report.get("meta", {})
            if meta_sync:
                with st.expander("对齐信息"):
                    st.json(meta_sync)
        elif result:
            st.info("上传音频文件（WAV/MP3/FLAC 等）进行唱做关联分析")

    # ========== 导出 ==========
    with tab_exp_view:
        st.markdown("### 📤 导出分析结果")
        
        # 导出选项
        st.markdown("#### 📋 导出内容选择")
        col1, col2, col3 = st.columns(3)
        with col1:
            write_csv = st.checkbox("CSV 时间序列", value=True, key="exp_write_csv")
        with col2:
            write_plot = st.checkbox("PNG 图表", value=True, key="exp_write_plot")
        with col3:
            write_td = st.checkbox("TouchDesigner 格式", value=False, key="exp_write_td")
        
        result = st.session_state.get("analysis_result")
        
        if result:
            out_dir = Path(DEFAULT_EXPORT_DIR)
            out_dir.mkdir(parents=True, exist_ok=True)
            json_path, csv_path, plot_path, td_path = export(
                result,
                output_dir=out_dir,
                write_csv=write_csv,
                write_plot=write_plot,
                write_td=write_td,
            )

            st.success(f"✅ 已导出至 `{out_dir}`")
            st.caption("CSV/JSON 可用于 Blender 或直接动捕艺术创作")

            if plot_path and plot_path.exists():
                st.image(str(plot_path), caption="分析图表预览")

            col_dl1, col_dl2, col_dl3 = st.columns(3)
            with col_dl1:
                with open(json_path, encoding="utf-8") as f:
                    st.download_button("📥 下载 JSON", f.read(), json_path.name, "application/json", key="dl_json")
            with col_dl2:
                if csv_path and csv_path.exists():
                    with open(csv_path, encoding="utf-8") as f:
                        st.download_button("📥 下载 CSV", f.read(), csv_path.name, "text/csv", key="dl_csv")
            with col_dl3:
                if plot_path and plot_path.exists():
                    with open(plot_path, "rb") as f:
                        st.download_button("📥 下载 PNG", f.read(), plot_path.name, "image/png", key="dl_png")

    # ========== 商业模块 ==========
    with tab_commercial:
        if not COMMERCIAL_AVAILABLE:
            st.warning("⚠️ 商业模块不可用，请检查安装")
        else:
            st.markdown("### 💎 商业模块")
            st.caption("专业的TD粒子效果、Blender绑定和AI动作生成工具")

            # 子标签页
            sub_tab_particles, sub_tab_rig, sub_tab_ai = st.tabs([
                "✨ TD粒子效果",
                "🎭 Blender绑定",
                "🤖 AI动作生成",
            ])

            # ========== TD粒子效果 ==========
            with sub_tab_particles:
                st.markdown("#### ✨ TouchDesigner 粒子效果")
                st.caption("基于动捕数据的实时粒子效果")

                col1, col2 = st.columns(2)
                with col1:
                    preset_type = st.selectbox(
                        "粒子效果预设",
                        options=[p.value for p in ParticlePreset],
                        index=0,
                    )
                with col2:
                    emitter_marker = st.selectbox(
                        "发射器关联",
                        options=["head", "hand_l", "hand_r", "spine_upper"],
                        index=0,
                    )

                # 获取预设
                preset = ParticlePreset(preset_type)
                emitter = PresetLibrary.create_emitter_from_preset(
                    preset,
                    marker_name=emitter_marker,
                )

                # 显示发射器参数
                with st.expander("⚙️ 发射器参数", expanded=False):
                    emit_rate = st.slider("发射速率", 10, 200, int(emitter.emit_rate))
                    lifetime = st.slider("生命周期(秒)", 0.5, 5.0, emitter.lifetime)
                    size = st.slider("粒子大小", 0.01, 0.5, emitter.size)

                # 创建粒子系统
                particle_system = ParticleSystem()
                particle_system.add_emitter(emitter)

                # 模拟数据预览
                st.markdown("##### 🎬 效果预览")
                if st.button("▶️ 生成粒子预览"):
                    particle_system.start()
                    positions = {
                        emitter_marker: (0.0, 1.0, 0.0),
                    }
                    for _ in range(30):
                        particle_system.update(positions, 0.016)

                    particle_count = len(particle_system._particles)
                    st.success(f"生成了 {particle_count} 个粒子")

                    particle_system.stop()

                # 导出选项
                st.markdown("##### 📤 导出设置")
                export_format = st.radio("导出格式", ["JSON", "Python脚本", "TD网络"], horizontal=True)
                if st.button("💾 导出粒子配置"):
                    import tempfile

                    if export_format == "JSON":
                        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                            temp_path = f.name
                        # 导出为JSON
                        import json
                        config = {
                            "preset": preset_type,
                            "emitter": emitter.to_dict(),
                            "system": {
                                "max_particles": particle_system.max_particles,
                            }
                        }
                        with open(temp_path, 'w') as f:
                            json.dump(config, f, indent=2)
                        st.success(f"已导出至 {temp_path}")

            # ========== Blender绑定 ==========
            with sub_tab_rig:
                st.markdown("#### 🎭 Blender 京剧角色绑定")
                st.caption("生成京剧专用骨骼系统和材质")

                col1, col2, col3 = st.columns(3)
                with col1:
                    dang_type = st.selectbox(
                        "行当",
                        options=[d.value for d in DangType],
                        index=0,
                    )
                with col2:
                    gender = st.selectbox(
                        "性别",
                        options=["male", "female"],
                        index=0,
                    )
                with col3:
                    height = st.number_input(
                        "身高(米)",
                        min_value=1.4,
                        max_value=2.0,
                        value=1.7,
                        step=0.05,
                    )

                # 创建绑定
                config = RigConfig(
                    dang=DangType(dang_type),
                    gender=gender,
                    height=height,
                )
                builder = OperaRigBuilder(config)
                bones = builder.build_base_rig()

                # 显示骨骼信息
                st.markdown("##### 🦴 骨骼信息")
                st.info(f"基础骨骼数量: {len(bones)}")

                # 添加京剧特有骨骼
                add_opera_bones = st.checkbox("添加京剧特有骨骼(翎子/髯口/水袖/靠旗)", value=True)
                if add_opera_bones:
                    bones = builder.add_opera_bones()
                    st.success(f"总骨骼数量: {len(bones)}")

                # 导出选项
                st.markdown("##### 📤 导出")
                export_format_rig = st.selectbox(
                    "导出格式",
                    options=["JSON", "Blender Python脚本"],
                    index=0,
                )

                if st.button("💾 导出绑定"):
                    import tempfile

                    if export_format_rig == "JSON":
                        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                            temp_path = f.name
                        result = builder.export_to_json(temp_path)
                        st.success(f"已导出至 {result['path']}")
                        st.caption(f"骨骼数量: {result['bone_count']}")
                    else:
                        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                            temp_path = f.name
                        result = builder.export_to_blender(temp_path)
                        st.success(f"已导出至 {result['path']}")
                        st.caption("在Blender中运行此脚本创建绑定")

                # 材质库预览
                with st.expander("🎨 材质库预览"):
                    st.markdown("##### 脸谱材质")
                    face_mats = ["face_red", "face_white", "face_black", "face_green"]
                    cols = st.columns(4)
                    for i, mat_name in enumerate(face_mats):
                        mat = OperaMaterialLibrary.get_material(mat_name)
                        if mat:
                            with cols[i]:
                                color = mat.get("base_color", (1, 1, 1, 1))
                                st.color_picker(mat_name, RGB=color[:3], disabled=True)

            # ========== AI动作生成 ==========
            with sub_tab_ai:
                st.markdown("#### 🤖 AI 动作生成")
                st.caption("基于深度学习的京剧动作生成")

                st.info("AI动作生成模块需要PyTorch支持")

                # 显示预处理器信息
                st.markdown("##### 🔧 预处理器配置")
                col1, col2 = st.columns(2)
                with col1:
                    target_framerate = st.number_input(
                        "目标帧率",
                        min_value=15,
                        max_value=120,
                        value=30,
                    )
                with col2:
                    normalize = st.checkbox("启用归一化", value=True)

                # 创建预处理器
                from opera_mocap_tool.commercial.ai_motion import MotionPreprocessor
                preprocessor = MotionPreprocessor(target_framerate=target_framerate)

                st.success(f"预处理器已配置 - 标准关节数: {len(preprocessor.joint_mapping)}")

                # 数据增强选项
                with st.expander("📊 数据增强选项"):
                    augment_rotation = st.checkbox("旋转增强", value=True)
                    augment_scale = st.checkbox("缩放增强", value=True)
                    augment_noise = st.checkbox("噪声增强", value=False)
                    noise_level = 0.0
                    if augment_noise:
                        noise_level = st.slider("噪声级别", 0.001, 0.1, 0.01)

                    if st.button("🔄 生成增强数据"):
                        # 创建示例数据
                        import numpy as np
                        from opera_mocap_tool.commercial.ai_motion import MotionSequence

                        sample_frames = np.random.randn(30, 22, 3)
                        sample_seq = MotionSequence(
                            frames=sample_frames,
                            frame_rate=target_framerate,
                        )

                        augmented = preprocessor.augment(
                            sample_seq,
                            rotation=augment_rotation,
                            scale=augment_scale,
                            noise=noise_level,
                        )

                        st.success(f"生成了 {len(augmented)} 个增强样本")

                st.caption("完整的AI训练功能需要商业授权")


    # ========== 实时Pipeline ==========
    with tab_realtime:
        st.markdown("### 🔴 实时Pipeline 控制")
        st.caption("实时动捕数据采集、处理和发送到TouchDesigner/Unreal Engine 5")

        # 导入实时模块
        try:
            from opera_mocap_tool.realtime import (
                RealtimePipeline,
                PipelineConfig,
                SkeletonData,
            )
            REALTIME_AVAILABLE = True
        except ImportError as e:
            REALTIME_AVAILABLE = False
            st.error(f"实时模块导入失败: {e}")

        if not REALTIME_AVAILABLE:
            st.warning("⚠️ 实时Pipeline不可用，请检查安装")
        else:
            # 会话状态管理
            if 'realtime_pipeline' not in st.session_state:
                st.session_state.realtime_pipeline = None

            # 配置区域
            st.markdown("#### ⚙️ 连接配置")
            col1, col2 = st.columns(2)

            with col1:
                st.markdown("**Vicon设置**")
                vicon_host = st.text_input("Vicon主机", value="localhost", key="vicon_host")
                vicon_port = st.number_input("Vicon端口", value=51001, key="vicon_port")
                subject_names = st.text_input("追踪对象(逗号分隔)", value="Actor1", key="subjects")

            with col2:
                st.markdown("**目标渲染引擎**")
                td_enabled = st.checkbox("TouchDesigner", value=True, key="td_enabled")
                td_host = st.text_input("TD主机", value="127.0.0.1", key="td_host")
                td_port = st.number_input("TD端口", value=7000, key="td_port")

                ue5_enabled = st.checkbox("Unreal Engine 5", value=False, key="ue5_enabled")
                ue5_host = st.text_input("UE5主机", value="127.0.0.1", key="ue5_host")
                ue5_port = st.number_input("UE5端口", value=11111, key="ue5_port")

            # 滤波设置
            st.markdown("#### 🔧 数据处理")
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                filter_enabled = st.checkbox("启用滤波", value=True, key="filter_enabled")
            with col_f2:
                filter_type = st.selectbox("滤波类型", ["ema", "butterworth", "kalman"], index=0, key="filter_type")

            # 控制按钮
            st.markdown("#### 🎮 控制")
            col_btn1, col_btn2, col_btn3 = st.columns(3)

            pipeline = st.session_state.realtime_pipeline

            with col_btn1:
                if st.button("▶️ 启动", use_container_width=True, key="start_pipeline"):
                    if pipeline is None or not pipeline.running:
                        # 创建Pipeline
                        config = PipelineConfig(
                            vicon_host=vicon_host,
                            vicon_port=vicon_port,
                            subject_names=[s.strip() for s in subject_names.split(",")],
                            td_enabled=td_enabled,
                            td_host=td_host,
                            td_port=td_port,
                            ue5_enabled=ue5_enabled,
                            ue5_host=ue5_host,
                            ue5_port=ue5_port,
                            filter_enabled=filter_enabled,
                            filter_type=filter_type,
                        )
                        pipeline = RealtimePipeline(config)
                        pipeline.connect()
                        pipeline.start()
                        st.session_state.realtime_pipeline = pipeline
                        st.success("Pipeline已启动!")

            with col_btn2:
                if st.button("⏹ 停止", use_container_width=True, key="stop_pipeline"):
                    if pipeline and pipeline.running:
                        pipeline.stop()
                        pipeline.disconnect()
                        st.session_state.realtime_pipeline = None
                        st.info("Pipeline已停止")

            with col_btn3:
                if st.button("🔄 刷新状态", use_container_width=True, key="refresh_stats"):
                    pass

            # 状态显示
            if pipeline:
                st.markdown("#### 📊 状态监控")
                stats = pipeline.get_stats()

                col_s1, col_s2, col_s3, col_s4 = st.columns(4)
                with col_s1:
                    status_color = "🟢" if stats["running"] else "🔴"
                    st.metric("状态", f"{status_color} {'运行中' if stats['running'] else '已停止'}")
                with col_s2:
                    st.metric("帧数", stats["frame_count"])
                with col_s3:
                    st.metric("FPS", f"{stats['current_fps']:.1f}")
                with col_s4:
                    latency = stats.get('avg_latency_ms', 0)
                    st.metric("延迟", f"{latency:.1f}ms")

                # 连接状态
                col_c1, col_c2, col_c3 = st.columns(3)
                with col_c1:
                    vicon_status = "✅" if stats.get('vicon_connected') else "❌"
                    st.write(f"Vicon: {vicon_status}")
                with col_c2:
                    td_status = "✅" if stats.get('td_connected') else "❌"
                    st.write(f"TD: {td_status}")
                with col_c3:
                    ue5_status = "✅" if stats.get('ue5_connected') else "❌"
                    st.write(f"UE5: {ue5_status}")

                # 发送统计
                if td_enabled:
                    st.metric("TD发送包数", stats.get('td_packets_sent', 0))
                if ue5_enabled:
                    st.metric("UE5发送包数", stats.get('ue5_packets_sent', 0))

                # 错误显示
                if stats.get('last_error'):
                    st.error(f"错误: {stats['last_error']}")
            else:
                st.info("点击「启动」按钮开始实时Pipeline")

            # 文档链接
            with st.expander("📖 使用说明"):
                st.markdown("""
                ### 实时Pipeline使用指南

                1. **连接Vicon**: 确保Vicon Blade正在运行，并配置正确的主机和端口
                2. **选择目标**: 勾选TouchDesigner和/或UE5，配置目标主机的IP和端口
                3. **数据处理**: 可选择启用滤波来平滑动捕数据
                4. **启动**: 点击「启动」按钮开始实时数据采集和发送
                5. **监控**: 观察状态监控区域，查看帧率、延迟和发送统计

                ### TD端配置
                - 在TD中创建一个DAT Receive或UDP DAT
                - 端口设置为7000（默认）
                - 接收格式: JSON

                ### UE5端配置
                - 使用Live Link或自定义接收器
                - 端口设置为11111（默认）
                - 数据格式: JSON with bone transforms
                """)


if __name__ == "__main__":
    run_gui()
