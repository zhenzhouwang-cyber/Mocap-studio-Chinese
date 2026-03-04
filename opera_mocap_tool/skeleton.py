"""骨骼定义：marker 之间的连线，用于在 3D 查看器中显示人物形态。"""

from __future__ import annotations

# 骨骼线段：(marker_a, marker_b)，与 load_mocap 后的 marker 名称一致（如 "Daphnee:ASISr"）
# 仅当两个 marker 均存在于数据中时才会绘制该线段

# Vicon / Daphnee 风格：骨盆、脊柱、胸廓、单臂到手腕
DAPHNEE_UPPER_BODY = [
    # 骨盆
    ("Daphnee:ASISr", "Daphnee:ASISl"),
    ("Daphnee:PSISr", "Daphnee:PSISl"),
    ("Daphnee:ASISr", "Daphnee:PSISr"),
    ("Daphnee:ASISl", "Daphnee:PSISl"),
    ("Daphnee:ASISr", "Daphnee:PSISl"),
    ("Daphnee:ASISl", "Daphnee:PSISr"),
    # 脊柱 / 躯干
    ("Daphnee:STER", "Daphnee:XIPH"),
    ("Daphnee:STER", "Daphnee:T1"),
    ("Daphnee:T1", "Daphnee:T10"),
    ("Daphnee:XIPH", "Daphnee:T10"),
    ("Daphnee:STERr", "Daphnee:STER"),
    ("Daphnee:STERl", "Daphnee:STER"),
    ("Daphnee:STER", "Daphnee:CLAVm"),
    ("Daphnee:T1", "Daphnee:CLAV_ant"),
    ("Daphnee:CLAVm", "Daphnee:CLAV_ant"),
    ("Daphnee:CLAVm", "Daphnee:CLAV_SC"),
    ("Daphnee:CLAV_ant", "Daphnee:CLAV_AC"),
    # 肩胛 / 肩
    ("Daphnee:CLAV_AC", "Daphnee:SCAP_AA"),
    ("Daphnee:SCAP_AA", "Daphnee:SCAPm"),
    ("Daphnee:SCAPm", "Daphnee:SCAPl"),
    ("Daphnee:SCAP_AA", "Daphnee:DELT"),
    # 手臂链：肩 -> 肘 -> 腕
    ("Daphnee:DELT", "Daphnee:ARMm"),
    ("Daphnee:ARMm", "Daphnee:LARM_elb"),
    ("Daphnee:LARM_elb", "Daphnee:WRIST"),
    ("Daphnee:LARM_elb", "Daphnee:LARM_ant"),
    ("Daphnee:LARM_ant", "Daphnee:WRIST"),
    ("Daphnee:WRIST", "Daphnee:STYLu"),
    ("Daphnee:WRIST", "Daphnee:STYLr"),
    ("Daphnee:STYLr", "Daphnee:STYLr_up"),
    ("Daphnee:WRIST", "Daphnee:INDEX"),
]

# 通用命名（常见 Vicon/Nexus 命名）：便于其他项目使用
GENERIC_BODY = [
    ("LShoulder", "LElbow"),
    ("LElbow", "LWrist"),
    ("RShoulder", "RElbow"),
    ("RElbow", "RWrist"),
    ("Head", "Neck"),
    ("Neck", "Spine"),
    ("Spine", "Spine1"),
    ("Spine1", "Hip"),
    ("Hip", "LKnee"),
    ("LKnee", "LAnkle"),
    ("Hip", "RKnee"),
    ("RKnee", "RAnkle"),
    ("LShoulder", "Spine"),
    ("RShoulder", "Spine"),
]

# Mixamo 标准骨骼（FBX 常用，前缀可能为 Mixamorig / Armature 等，后缀匹配会兼容）
MIXAMO_BODY = [
    # 脊柱
    ("Mixamorig:Hips", "Mixamorig:Spine"),
    ("Mixamorig:Spine", "Mixamorig:Spine1"),
    ("Mixamorig:Spine1", "Mixamorig:Spine2"),
    ("Mixamorig:Spine2", "Mixamorig:Neck"),
    ("Mixamorig:Neck", "Mixamorig:Head"),
    # 左腿
    ("Mixamorig:Hips", "Mixamorig:LeftUpLeg"),
    ("Mixamorig:LeftUpLeg", "Mixamorig:LeftLeg"),
    ("Mixamorig:LeftLeg", "Mixamorig:LeftFoot"),
    ("Mixamorig:LeftFoot", "Mixamorig:LeftToeBase"),
    # 右腿
    ("Mixamorig:Hips", "Mixamorig:RightUpLeg"),
    ("Mixamorig:RightUpLeg", "Mixamorig:RightLeg"),
    ("Mixamorig:RightLeg", "Mixamorig:RightFoot"),
    ("Mixamorig:RightFoot", "Mixamorig:RightToeBase"),
    # 左臂
    ("Mixamorig:Spine2", "Mixamorig:LeftShoulder"),
    ("Mixamorig:LeftShoulder", "Mixamorig:LeftArm"),
    ("Mixamorig:LeftArm", "Mixamorig:LeftForeArm"),
    ("Mixamorig:LeftForeArm", "Mixamorig:LeftHand"),
    # 右臂
    ("Mixamorig:Spine2", "Mixamorig:RightShoulder"),
    ("Mixamorig:RightShoulder", "Mixamorig:RightArm"),
    ("Mixamorig:RightArm", "Mixamorig:RightForeArm"),
    ("Mixamorig:RightForeArm", "Mixamorig:RightHand"),
]
# Mixamo 部分 rig 无 LeftShoulder/RightShoulder，Spine2 直接连 LeftArm/RightArm
MIXAMO_BODY_ALT = [
    ("Mixamorig:Spine2", "Mixamorig:LeftArm"),
    ("Mixamorig:Spine2", "Mixamorig:RightArm"),
]

# Blender / Unity 常见骨骼名（无前缀或 Armature_ 等，靠后缀匹配）
BLENDER_UNITY_BODY = [
    ("Hips", "Spine"),
    ("Spine", "Spine1"),
    ("Spine1", "Spine2"),
    ("Spine2", "Neck"),
    ("Neck", "Head"),
    ("Hips", "LeftUpperLeg"),
    ("LeftUpperLeg", "LeftLowerLeg"),
    ("LeftLowerLeg", "LeftFoot"),
    ("LeftFoot", "LeftToeBase"),
    ("Hips", "RightUpperLeg"),
    ("RightUpperLeg", "RightLowerLeg"),
    ("RightLowerLeg", "RightFoot"),
    ("RightFoot", "RightToeBase"),
    ("Spine2", "LeftUpperArm"),
    ("LeftUpperArm", "LeftLowerArm"),
    ("LeftLowerArm", "LeftHand"),
    ("Spine2", "RightUpperArm"),
    ("RightUpperArm", "RightLowerArm"),
    ("RightLowerArm", "RightHand"),
]
# 与 Mixamo 命名混用（LeftArm = LeftUpperArm 等不同资源命名）
BLENDER_ALT = [
    ("Spine2", "LeftArm"),
    ("LeftArm", "LeftForeArm"),
    ("LeftForeArm", "LeftHand"),
    ("Spine2", "RightArm"),
    ("RightArm", "RightForeArm"),
    ("RightForeArm", "RightHand"),
    ("Hips", "LeftUpLeg"),
    ("LeftUpLeg", "LeftLeg"),
    ("LeftLeg", "LeftFoot"),
    ("Hips", "RightUpLeg"),
    ("RightUpLeg", "RightLeg"),
    ("RightLeg", "RightFoot"),
]

# BVH 常见命名（含 RootNode(0)->Hips、LeftShoulder/RightShoulder）
BVH_BODY = [
    ("RootNode(0)", "Hips"),
    ("Hips", "Spine"),
    ("Spine", "Spine1"),
    ("Spine1", "Spine2"),
    ("Spine2", "Neck"),
    ("Neck", "Neck1"),
    ("Neck1", "Head"),
    ("Spine2", "LeftShoulder"),
    ("LeftShoulder", "LeftArm"),
    ("LeftArm", "LeftForeArm"),
    ("LeftForeArm", "LeftHand"),
    ("Spine2", "RightShoulder"),
    ("RightShoulder", "RightArm"),
    ("RightArm", "RightForeArm"),
    ("RightForeArm", "RightHand"),
    ("Hips", "LeftUpLeg"),
    ("LeftUpLeg", "LeftLeg"),
    ("LeftLeg", "LeftFoot"),
    ("LeftFoot", "LeftToeBase"),
    ("Hips", "RightUpLeg"),
    ("RightUpLeg", "RightLeg"),
    ("RightLeg", "RightFoot"),
    ("RightFoot", "RightToeBase"),
]

# 默认使用的模板（按顺序尝试，后缀匹配后合并去重）
DEFAULT_TEMPLATES = [
    BVH_BODY,
    DAPHNEE_UPPER_BODY,
    GENERIC_BODY,
    MIXAMO_BODY,
    MIXAMO_BODY_ALT,
    BLENDER_UNITY_BODY,
    BLENDER_ALT,
]


def _suffix(name: str) -> str:
    """模板或 marker 名的“关节名”部分，用于模糊匹配（如 Daphnee:ASISr -> ASISr）。"""
    s = name.strip()
    if ":" in s:
        return s.split(":")[-1].strip()
    return s


def _find_marker_for_template(template_name: str, label_set: set[str], suffix_to_labels: dict[str, list[str]]) -> str | None:
    """为模板中的名称在真实 marker 列表中找一个匹配：先精确匹配，再按后缀匹配。"""
    if template_name in label_set:
        return template_name
    suf = _suffix(template_name)
    if suf in suffix_to_labels:
        # 同一后缀可能有多个（如左右），取第一个；调用方会成对使用
        return suffix_to_labels[suf][0]
    return None


def get_skeleton_segments(
    marker_labels: list[str],
    *,
    templates: list[list[tuple[str, str]]] | None = None,
    use_suffix_match: bool = True,
) -> list[tuple[str, str]]:
    """
    根据当前数据中的 marker 名称，返回可绘制的骨骼线段。

    只保留两端 marker 都存在于 marker_labels 中的线段。若 use_suffix_match 为 True，
    会先用精确名匹配，再用“后缀”匹配（如模板 Daphnee:ASISr 可匹配数据中的 XXX:ASISr），
    以便不同被试名或导出格式下也能显示骨骼。

    Args:
        marker_labels: 当前动捕数据中的 marker 名称列表。
        templates: 骨骼模板列表，每项为 (marker_a, marker_b) 的列表；默认用 DEFAULT_TEMPLATES。
        use_suffix_match: 是否启用按后缀匹配（推荐 True）。

    Returns:
        可绘制的线段列表 [(name_a, name_b), ...]，名称为 marker_labels 中的真实名称。
    """
    if templates is None:
        templates = DEFAULT_TEMPLATES
    label_set = set(marker_labels)
    # 按后缀建立索引，便于后缀匹配（每个后缀对应数据中该关节的 marker 名列表）
    suffix_to_labels: dict[str, list[str]] = {}
    for m in marker_labels:
        suf = _suffix(m)
        if suf not in suffix_to_labels:
            suffix_to_labels[suf] = []
        suffix_to_labels[suf].append(m)

    out: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for template in templates:
        for ta, tb in template:
            if use_suffix_match:
                ma = _find_marker_for_template(ta, label_set, suffix_to_labels)
                mb = _find_marker_for_template(tb, label_set, suffix_to_labels)
            else:
                ma = ta if ta in label_set else None
                mb = tb if tb in label_set else None
            if ma and mb and ma != mb:
                key = (ma, mb) if ma <= mb else (mb, ma)
                if key not in seen:
                    seen.add(key)
                    out.append((ma, mb))
    return out
