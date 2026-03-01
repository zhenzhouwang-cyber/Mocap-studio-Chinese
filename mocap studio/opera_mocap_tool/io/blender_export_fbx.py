"""
供 Blender 以子进程方式运行：读取环境变量中的 FBX 路径与输出 CSV 路径，
导入 FBX、按帧导出骨骼世界坐标到 CSV，便于本工具用 read_csv 加载。

用法（由 fbx_reader 调用，不要直接运行）:
  set OPERA_FBX_IN=path/to/file.fbx
  set OPERA_FBX_OUT=path/to/out.csv
  blender --background --python blender_export_fbx.py
"""
from __future__ import annotations

import json
import os
import sys

# Blender 环境下才有 bpy
try:
    import bpy
except ImportError:
    sys.exit(1)

# #region agent log
def _debug_log(msg: str, data: dict) -> None:
    try:
        log_path = r"e:\coursor\project\.cursor\debug.log"
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps({"location": "blender_export_fbx.py", "message": msg, "data": data, "timestamp": __import__("time").time() * 1000}, ensure_ascii=False) + "\n")
    except Exception:
        pass
# #endregion

def main() -> None:
    fbx_in = os.environ.get("OPERA_FBX_IN")
    csv_out = os.environ.get("OPERA_FBX_OUT")
    if not fbx_in or not csv_out:
        sys.exit(2)
    if not os.path.isfile(fbx_in):
        sys.exit(3)

    bpy.ops.wm.read_homefile(use_empty=True)
    # 显式保留叶骨骼（手指、脚趾等），避免骨骼丢失
    bpy.ops.import_scene.fbx(filepath=fbx_in, ignore_leaf_bones=False)

    # ===== 将导入的骨骼移动到地面网格中心 =====
    # 1. 获取第一帧所有骨骼的世界坐标
    bpy.context.scene.frame_set(bpy.context.scene.frame_start)
    bpy.context.view_layer.update()
    
    min_z = float('inf')
    armature_obj = None
    for obj in bpy.context.scene.objects:
        if obj.type == "ARMATURE":
            armature_obj = obj
            for bone in obj.data.bones:
                pose_bone = obj.pose.bones.get(bone.name)
                if pose_bone is not None:
                    world = obj.matrix_world @ pose_bone.matrix
                else:
                    world = obj.matrix_world @ bone.matrix_local
                min_z = min(min_z, world.translation.z)
            break
    
    # 2. 如果最低点不是0，向下移动整个骨架
    if armature_obj and min_z != float('inf') and min_z != 0:
        offset_z = -min_z  # 向下移动使得最低点为0
        armature_obj.location.z += offset_z
        # 应用变换，确保动画数据也一起移动
        bpy.ops.object.transform_apply(location=True, rotation=False, scale=False)
        # #region agent log
        _debug_log("Armature moved to ground", {"min_z_before": min_z, "offset_applied": offset_z, "hypothesisId": "H3"})
        # #endregion

    # #region agent log
    armatures = [o for o in bpy.context.scene.objects if o.type == "ARMATURE"]
    arm_info = [{"name": a.name, "bone_count": len(a.data.bones), "bone_names": [b.name for b in a.data.bones]} for a in armatures]
    _debug_log("FBX import: armatures after import", {"armature_count": len(armatures), "armatures": arm_info, "hypothesisId": "H1"})
    # #endregion

    # 使用动画真实帧范围，不依赖场景的结束帧设置（保证导出完整时长）
    frame_start = int(bpy.context.scene.frame_start)
    frame_end = int(bpy.context.scene.frame_end)
    for obj in bpy.context.scene.objects:
        if obj.type != "ARMATURE":
            continue
        if obj.animation_data and obj.animation_data.action:
            act = obj.animation_data.action
            frame_start = int(act.frame_range[0])
            frame_end = int(act.frame_range[1])
            # 同步到场景，便于后续 frame_set 正确评估
            bpy.context.scene.frame_start = frame_start
            bpy.context.scene.frame_end = frame_end
        break

    fps = float(bpy.context.scene.render.fps)
    bones_order: list[str] = []
    for obj in bpy.context.scene.objects:
        if obj.type != "ARMATURE":
            continue
        for bone in obj.data.bones:
            bones_order.append(bone.name)
        break  # 只取第一个 armature

    if not bones_order:
        sys.exit(4)

    # #region agent log
    _debug_log("Export bones_order (first armature only)", {"bones_exported": len(bones_order), "bone_names": bones_order, "hypothesisId": "H1"})
    # #endregion

    rows: list[dict[str, str | float]] = []
    for fi in range(frame_start, frame_end + 1):
        bpy.context.scene.frame_set(fi)
        bpy.context.view_layer.update()
        t_sec = (fi - frame_start) / fps
        row: dict[str, str | float] = {"Frame": fi, "Time": round(t_sec, 6)}
        for obj in bpy.context.scene.objects:
            if obj.type != "ARMATURE":
                continue
            for bone in obj.data.bones:
                pose_bone = obj.pose.bones.get(bone.name)
                if pose_bone is not None:
                    world = obj.matrix_world @ pose_bone.matrix
                else:
                    world = obj.matrix_world @ bone.matrix_local
                loc = world.translation
                name = bone.name
                row[f"{name}_X"] = round(float(loc.x), 6)
                row[f"{name}_Y"] = round(float(loc.y), 6)
                row[f"{name}_Z"] = round(float(loc.z), 6)
            break
        rows.append(row)

    headers = ["Frame", "Time"] + [f"{b}_{c}" for b in bones_order for c in ("X", "Y", "Z")]
    with open(csv_out, "w", newline="", encoding="utf-8") as f:
        w = __import__("csv").DictWriter(f, fieldnames=headers, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    sys.exit(0)


if __name__ == "__main__":
    main()
