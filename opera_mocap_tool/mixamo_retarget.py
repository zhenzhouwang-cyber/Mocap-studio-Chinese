"""Mixamo 蒙皮重定向：从动捕 marker/线段 构建驱动 Mixamo 骨骼的映射。

GLB 骨骼名（如 mixamorig:Hips）与动捕 marker 名（如 Hips / Mixamorig:Hips）可能大小写
或前缀不同，因此构建映射时同时输出一份 lowercase-suffix → 原名 的查找表，前端匹配时使用。
"""

from __future__ import annotations


def _suffix_lower(name: str) -> str:
    """取冒号后部分并转小写，用于模糊匹配。"""
    s = name.strip()
    if ":" in s:
        s = s.split(":")[-1]
    return s.lower()


def build_mixamo_bone_mapping(
    segments: list[tuple[str, str]],
    labels: list[str],
) -> dict:
    """
    从骨骼线段与 marker 列表构建前端驱动所需的映射结构。

    Returns:
        {
          "bones": {
            "Hips": {"start": null, "end": "Hips", "root": true},
            "Spine": {"start": "Hips", "end": "Spine"},
            ...
          },
          "suffixMap": {  // lowercase suffix → 原 marker 名
            "hips": "Hips",
            "spine": "Spine",
            ...
          }
        }
    """
    label_set = set(labels)
    ends = {b for _, b in segments}
    starts = {a for a, _ in segments}
    bones: dict[str, dict] = {}

    for a, b in segments:
        if a not in label_set or b not in label_set:
            continue
        # 不要覆盖已存在的骨骼映射，保留首次匹配的结果
        # 这避免了一些模板中的重复/错误连接覆盖正确连接的问题
        if b not in bones:
            bones[b] = {"start": a, "end": b}

    root_candidates = starts - ends
    for r in root_candidates:
        if r in label_set and r not in bones:
            bones[r] = {"start": None, "end": r, "root": True}

    suffix_map: dict[str, str] = {}
    for name in labels:
        suf = _suffix_lower(name)
        if suf not in suffix_map:
            suffix_map[suf] = name

    return {
        "bones": bones,
        "suffixMap": suffix_map,
    }
