"""FBX 动画加载：将 FBX 中的骨骼/关节动画转为 MocapData，便于查看与分析。"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from .base import MocapData

# #region agent log
def _debug_log(msg: str, data: dict) -> None:
    try:
        with open(r"e:\coursor\project\.cursor\debug.log", "a", encoding="utf-8") as f:
            import json
            import time
            f.write(json.dumps({"location": "fbx_reader.py", "message": msg, "data": data, "timestamp": time.time() * 1000}, ensure_ascii=False) + "\n")
    except Exception:
        pass
# #endregion

# 由 GUI 或调用方设置后，优先使用此路径（不设则用环境变量 / PATH）
_blender_exe_override: str | None = None


def set_blender_exe(path: str | None) -> None:
    """设置 Blender 可执行文件路径（如 E:\\Software\\blender-launcher.exe），用于 FBX 加载。"""
    global _blender_exe_override
    _blender_exe_override = (path.strip() or None) if path else None


def _blender_candidates() -> list[str]:
    """返回要尝试的 Blender 可执行路径列表（优先真正支持 --background 的 blender.exe）。"""
    candidates: list[str] = []
    # 用户指定的路径：若为 launcher，同目录下的 blender.exe 优先尝试（launcher 常不支持 --background）
    if _blender_exe_override:
        p = Path(_blender_exe_override).resolve()
        if p.is_file():
            parent = p.parent
            # 若当前是 blender-launcher.exe，先试同目录的 blender.exe
            if "launcher" in p.name.lower():
                alt = parent / "blender.exe"
                if alt.is_file():
                    candidates.append(str(alt))
            candidates.append(str(p))
    for env_key in ("OPERA_BLENDER_EXE", "BLENDER_EXE"):
        path_str = os.environ.get(env_key)
        if path_str:
            p = Path(path_str).resolve()
            if p.is_file() and str(p) not in candidates:
                candidates.append(str(p))
            elif p.is_dir():
                for name in ("blender.exe", "blender-launcher.exe", "blender"):
                    child = p / name
                    if child.is_file() and str(child) not in candidates:
                        candidates.append(str(child))
    exe = shutil.which("blender")
    if exe and exe not in candidates:
        candidates.append(exe)
    if os.name == "nt":
        for base in (
            os.environ.get("ProgramFiles", "C:\\Program Files"),
            os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)"),
        ):
            for name in ("Blender Foundation\\Blender", "Blender"):
                p = Path(base) / name / "blender.exe"
                if p.is_file() and str(p) not in candidates:
                    candidates.append(str(p))
    return candidates


def read_fbx(path: str | Path) -> MocapData:
    """
    读取 FBX 文件中的骨骼动画，转换为 MocapData（每关节视为一个 marker，轨迹为世界坐标）。

    依次尝试：FBX SDK Python 绑定 -> bpy（Blender 内嵌 Python）-> Blender 子进程导出 CSV 再加载。
    若本机已安装 Blender 且 blender 在 PATH 中，通常可通过子进程方式直接加载 FBX。

    Args:
        path: FBX 文件路径。

    Returns:
        MocapData 实例。

    Raises:
        FileNotFoundError: 文件不存在。
        ValueError: 无法解析或未安装 FBX 支持。
    """
    path = Path(path).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"FBX 文件不存在: {path}")

    # 尝试使用 fbx 库（Autodesk FBX SDK Python 绑定，需单独安装 SDK）
    try:
        return _read_fbx_sdk(path)
    except ImportError:
        pass
    except Exception:
        pass

    # 尝试使用 bpy（Blender 作为库，需在 Blender 的 Python 环境运行）
    try:
        return _read_fbx_bpy(path)
    except ImportError:
        pass

    # 尝试 Blender 子进程：导出为 CSV 再加载（支持 PATH 或 Windows 常见安装路径）
    last_error: str | None = None
    try:
        return _read_fbx_via_blender_subprocess(path)
    except Exception as e:
        last_error = f"{type(e).__name__}: {e}"

    err_extra = f"\n\n最后错误: {last_error}" if last_error else ""
    raise ValueError(
        "当前环境无法读取 FBX 动画。可选方案：\n"
        "1) 安装 Blender，并设置环境变量 OPERA_BLENDER_EXE 指向可执行文件（如 E:\\Software\\blender-launcher.exe），然后重启本程序；\n"
        "2) 或将 blender 加入系统 PATH；\n"
        "3) 在 Blender 中打开该 FBX，导出骨骼动画为 CSV（每列为 关节名_X/Y/Z，每行为一帧）后在本工具中加载。"
        + err_extra
    )


def _run_blender_export(blender_exe: str, script_path: Path, path: Path, csv_path: str, script_dir: Path) -> tuple[int, str]:
    """执行一次 Blender 导出，返回 (returncode, stderr 摘要)。"""
    env = os.environ.copy()
    env["OPERA_FBX_IN"] = str(path.resolve())
    env["OPERA_FBX_OUT"] = csv_path
    proc = subprocess.run(
        [blender_exe, "--background", "--python", str(script_path)],
        capture_output=True,
        timeout=300,
        env=env,
        cwd=str(script_dir),
    )
    stderr_snippet = (proc.stderr or b"").decode(errors="replace").strip()[:600]
    return proc.returncode, stderr_snippet


def _read_fbx_via_blender_subprocess(path: Path) -> MocapData:
    """通过调用系统安装的 Blender 将 FBX 导出为 CSV，再使用 read_csv 加载。"""
    candidates = _blender_candidates()
    if not candidates:
        raise FileNotFoundError(
            "未找到 Blender。请在侧栏填写 Blender 路径（如 E:\\Software\\blender.exe），或安装 Blender 并加入 PATH。"
        )
    script_dir = Path(__file__).resolve().parent
    script_path = script_dir / "blender_export_fbx.py"
    if not script_path.is_file():
        raise FileNotFoundError(f"未找到导出脚本: {script_path}")
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
        csv_path = tmp.name
    last_code = 0
    last_stderr = ""
    try:
        for blender_exe in candidates:
            last_code, last_stderr = _run_blender_export(blender_exe, script_path, path, csv_path, script_dir)
            if last_code == 0 and Path(csv_path).is_file():
                from .csv_reader import read_csv
                data = read_csv(csv_path)
                # #region agent log
                _debug_log("After read_csv: markers loaded", {"marker_count": len(data.markers), "marker_names": list(data.markers.keys()), "hypothesisId": "H2"})
                # #endregion
                data.metadata["source"] = str(path)
                data.metadata["format"] = "fbx_blender_export"
                return data
        # 全部失败，给出明确说明
        exit_hint = {
            1: "Blender 无法加载 Python 脚本（可能用了 launcher，请改填同目录下的 blender.exe）。",
            2: "缺少环境变量（内部错误）。",
            3: "FBX 文件路径无法被 Blender 读取（请勿使用含特殊字符的路径）。",
            4: "FBX 中未识别到骨骼，请确认该 FBX 包含 Armature 动画。",
        }.get(last_code, f"Blender 退出码 {last_code}。")
        raise RuntimeError(
            f"Blender 导出失败: {exit_hint} stderr: {last_stderr or '(无)'}"
        )
    finally:
        try:
            Path(csv_path).unlink(missing_ok=True)
        except Exception:
            pass


def _read_fbx_sdk(path: Path) -> MocapData:
    """通过 Autodesk FBX SDK 的 Python 绑定读取 FBX 动画。"""
    import fbx  # type: ignore[import-untyped]

    manager = fbx.FbxManager.Create()
    scene = fbx.FbxScene.Create(manager, "")
    importer = fbx.FbxImporter.Create(manager, "")
    if not importer.Initialize(str(path)):
        raise ValueError(f"FBX 初始化失败: {path}")
    importer.Import(scene)
    importer.Destroy()

    # 取第一帧与最后一帧，估算帧数与帧率（FBX 用时间）
    anim_stack = scene.GetCurrentAnimationStack()
    if not anim_stack:
        raise ValueError("FBX 中无动画栈")
    time_span = anim_stack.GetLocalTimeSpan()
    start = time_span.GetStart().GetFrameCount()
    stop = time_span.GetStop().GetFrameCount()
    n_frames = max(1, int(stop - start) + 1)
    # 默认 30fps，可从 FBX 设置读取
    frame_rate = 30.0

    # 收集所有骨架节点及其在世界坐标系下的位置（每帧）
    root = scene.GetRootNode()
    markers: dict[str, list[tuple[float, float, float]]] = {}

    def collect_transforms(node: "fbx.FbxNode", frame_offset: int) -> None:
        name = node.GetName()
        if not name:
            return
        # 只对骨骼/关节建轨迹（可根据 GetNodeAttribute 过滤）
        attr = node.GetNodeAttribute()
        if attr and attr.GetAttributeType() == fbx.FbxNodeAttribute.eSkeleton:
            pass  # 是骨骼
        positions = []
        for fi in range(n_frames):
            # FBX SDK 中需设置当前时间再取变换
            time = fbx.FbxTime()
            time.SetFrame(frame_offset + fi)
            # 世界平移
            world_t = node.EvaluateGlobalTransform(time)
            t = world_t.GetT()
            x, y, z = t[0], t[1], t[2]
            positions.append((float(x), float(y), float(z)))
        markers[name] = positions
        for i in range(node.GetChildCount()):
            collect_transforms(node.GetChild(i), frame_offset)

    # 遍历根下节点，只处理有动画的骨架
    for i in range(root.GetChildCount()):
        collect_transforms(root.GetChild(i), int(start))

    manager.Destroy()

    if not markers:
        raise ValueError("FBX 中未找到可用的骨骼节点，请确认文件包含骨骼动画。")

    # ===== 将所有骨骼位置移动到地面（Z=0） =====
    min_z = float('inf')
    for positions in markers.values():
        for x, y, z in positions:
            min_z = min(min_z, z)
    
    if min_z != float('inf') and min_z != 0:
        offset_z = -min_z
        for name in markers:
            markers[name] = [(x, y, z + offset_z) for x, y, z in markers[name]]

    return MocapData(
        markers=markers,
        frame_rate=frame_rate,
        marker_labels=list(markers.keys()),
        metadata={"source": str(path), "format": "fbx"},
    )


def _read_fbx_bpy(path: Path) -> MocapData:
    """通过 Blender Python API (bpy) 读取 FBX 动画。仅在 Blender 内或 bpy 可用时使用。"""
    import bpy  # type: ignore[import-untyped]

    bpy.ops.wm.read_homefile(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(path))
    # 获取所有 armature 的 bone 在世界坐标下的位置
    markers: dict[str, list[tuple[float, float, float]]] = {}
    frame_start = int(bpy.context.scene.frame_start)
    frame_end = int(bpy.context.scene.frame_end)
    n_frames = max(1, frame_end - frame_start + 1)
    frame_rate = float(bpy.context.scene.render.fps)

    for obj in bpy.context.scene.objects:
        if obj.type != "ARMATURE":
            continue
        arm = obj.data
        for bone in arm.bones:
            name = bone.name
            positions = []
            for fi in range(frame_start, frame_end + 1):
                bpy.context.scene.frame_set(fi)
                bpy.context.view_layer.update()
                # 世界矩阵
                world = obj.matrix_world @ bone.matrix_local
                loc = world.translation
                positions.append((float(loc.x), float(loc.y), float(loc.z)))
            markers[name] = positions

    if not markers:
        raise ValueError("FBX 中未找到骨骼。")

    # ===== 将所有骨骼位置移动到地面（Z=0） =====
    min_z = float('inf')
    for positions in markers.values():
        for x, y, z in positions:
            min_z = min(min_z, z)
    
    if min_z != float('inf') and min_z != 0:
        offset_z = -min_z
        for name in markers:
            markers[name] = [(x, y, z + offset_z) for x, y, z in markers[name]]

    return MocapData(
        markers=markers,
        frame_rate=frame_rate,
        marker_labels=list(markers.keys()),
        metadata={"source": str(path), "format": "fbx_bpy"},
    )
