# -*- coding: utf-8 -*-
"""快速测试 BVH 加载（可指定路径）。"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from opera_mocap_tool.io.loaders import load_mocap

# 优先项目内，其次用户数据路径
p = Path(__file__).resolve().parent / "舞蹈动作-科目三" / "科目三.bvh"
if not p.exists():
    p = Path(r"E:\resource\动捕数据\舞蹈动作-科目三\科目三.bvh")
if not p.exists():
    print("未找到 BVH 文件，请将 科目三.bvh 放在 舞蹈动作-科目三/ 或 E:\\resource\\动捕数据\\舞蹈动作-科目三\\")
    sys.exit(1)
d = load_mocap(p)
print("OK: markers", len(d.markers), "frames", d.n_frames, "rate", d.frame_rate)
print("joints sample:", list(d.markers.keys())[:10])
