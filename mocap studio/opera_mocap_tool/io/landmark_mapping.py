"""
骨架关键点映射模块。

MediaPipe 与专业动捕系统（如 Vicon、OptiTrack）之间的关键点名称映射。
支持：
1. MediaPipe → 通用名
2. 专业动捕 marker 名 → 通用名
3. 通用名 → MediaPipe / 专业动捕

这使得视频姿态估计与专业动捕数据可以进行 DTW 比对。
"""

from __future__ import annotations

from typing import Literal


# MediaPipe 33 个关键点的标准化名称（去掉 side 前缀）
MEDIAPIPE_TO_GENERIC: dict[str, str] = {
    # 头部
    "nose": "nose",
    "left_eye_inner": "eye_inner_left",
    "left_eye": "eye_left",
    "left_eye_outer": "eye_outer_left",
    "right_eye_inner": "eye_inner_right",
    "right_eye": "eye_right",
    "right_eye_outer": "eye_outer_right",
    "left_ear": "ear_left",
    "right_ear": "ear_right",
    "mouth_left": "mouth_left",
    "mouth_right": "mouth_right",
    # 上肢
    "left_shoulder": "shoulder_left",
    "right_shoulder": "shoulder_right",
    "left_elbow": "elbow_left",
    "right_elbow": "elbow_right",
    "left_wrist": "wrist_left",
    "right_wrist": "wrist_right",
    "left_pinky": "pinky_left",
    "right_pinky": "pinky_right",
    "left_index": "index_left",
    "right_index": "index_right",
    "left_thumb": "thumb_left",
    "right_thumb": "thumb_right",
    # 躯干/髋部
    "left_hip": "hip_left",
    "right_hip": "hip_right",
    # 下肢
    "left_knee": "knee_left",
    "right_knee": "knee_right",
    "left_ankle": "ankle_left",
    "right_ankle": "ankle_right",
    "left_heel": "heel_left",
    "right_heel": "heel_right",
    "left_foot_index": "foot_index_left",
    "right_foot_index": "foot_index_right",
}

# 通用名到 MediaPipe
GENERIC_TO_MEDIAPIPE: dict[str, str] = {v: k for k, v in MEDIAPIPE_TO_GENERIC.items()}

# 专业动捕常见 marker 名称到通用名的映射
# 支持多种命名约定：Vicon, OptiTrack, XSens 等
MOCAP_TO_GENERIC: dict[str, str] = {
    # 头部
    "nose": "nose",
    "head": "nose",
    " forehead": "nose",
    # 左眼
    "leye": "eye_left",
    "leyeinner": "eye_inner_left",
    "leyeouter": "eye_outer_left",
    "l_eye": "eye_left",
    "l_eye_inner": "eye_inner_left",
    # 右眼
    "reye": "eye_right",
    "reyeinner": "eye_inner_right",
    "reyeouter": "eye_outer_right",
    "r_eye": "eye_right",
    "r_eye_inner": "eye_inner_right",
    # 耳朵
    "lear": "ear_left",
    "rear": "ear_right",
    "l_ear": "ear_left",
    "r_ear": "ear_right",
    # 嘴巴
    "mouthl": "mouth_left",
    "mouthr": "mouth_right",
    "l_mouth": "mouth_left",
    "r_mouth": "mouth_right",
    # 肩膀
    "lshoulder": "shoulder_left",
    "rshoulder": "shoulder_right",
    "l_shoulder": "shoulder_left",
    "r_shoulder": "shoulder_right",
    "lsho": "shoulder_left",
    "rsho": "shoulder_right",
    "shoulder_l": "shoulder_left",
    "shoulder_r": "shoulder_right",
    # 肘部
    "lelbow": "elbow_left",
    "relbow": "elbow_right",
    "l_elbow": "elbow_left",
    "r_elbow": "elbow_right",
    "lelb": "elbow_left",
    "relb": "elbow_right",
    # 手腕
    "lwrist": "wrist_left",
    "rwrist": "wrist_right",
    "l_wrist": "wrist_left",
    "r_wrist": "wrist_right",
    "lwra": "wrist_left",
    "rwra": "wrist_right",
    # 手
    "lhand": "hand_left",
    "rhand": "hand_right",
    "l_hand": "hand_left",
    "r_hand": "hand_right",
    # 手指
    "lpinky": "pinky_left",
    "rpinky": "pinky_right",
    "l_pinky": "pinky_left",
    "r_pinky": "pinky_right",
    "lindex": "index_left",
    "rindex": "index_right",
    "l_index": "index_left",
    "r_index": "index_right",
    "lthumb": "thumb_left",
    "rthumb": "thumb_right",
    "l_thumb": "thumb_left",
    "r_thumb": "thumb_right",
    # 髋部
    "lhip": "hip_left",
    "rhip": "hip_right",
    "l_hip": "hip_left",
    "r_hip": "hip_right",
    "lhipo": "hip_left",
    "rhipo": "hip_right",
    "hip_l": "hip_left",
    "hip_r": "hip_right",
    # 膝盖
    "lknee": "knee_left",
    "rknee": "knee_right",
    "l_knee": "knee_left",
    "r_knee": "knee_right",
    "lkne": "knee_left",
    "rkne": "knee_right",
    # 脚踝
    "lankle": "ankle_left",
    "rankle": "ankle_right",
    "l_ankle": "ankle_left",
    "r_ankle": "ankle_right",
    "lank": "ankle_left",
    "rank": "ankle_right",
    # 脚
    "lfoot": "foot_left",
    "rfoot": "foot_right",
    "l_foot": "foot_left",
    "r_foot": "foot_right",
    # 脚跟
    "lheel": "heel_left",
    "rheel": "heel_right",
    "l_heel": "heel_left",
    "r_heel": "heel_right",
    # 脚尖
    "lfootindex": "foot_index_left",
    "rfootindex": "foot_index_right",
    "l_foot_index": "foot_index_left",
    "r_foot_index": "foot_index_right",
    "ltoe": "foot_index_left",
    "rtoe": "foot_index_right",
    "l_toe": "foot_index_left",
    "r_toe": "foot_index_right",
}

# 通用名到肢体类型的映射
GENERIC_TO_LIMB_TYPE: dict[str, str] = {
    # 上肢末端
    "wrist_left": "upper_extremity",
    "wrist_right": "upper_extremity",
    "hand_left": "upper_extremity",
    "hand_right": "upper_extremity",
    "pinky_left": "upper_extremity",
    "pinky_right": "upper_extremity",
    "index_left": "upper_extremity",
    "index_right": "upper_extremity",
    "thumb_left": "upper_extremity",
    "thumb_right": "upper_extremity",
    # 上肢
    "elbow_left": "upper_limb",
    "elbow_right": "upper_limb",
    "shoulder_left": "upper_limb",
    "shoulder_right": "upper_limb",
    # 下肢
    "knee_left": "lower_limb",
    "knee_right": "lower_limb",
    "ankle_left": "lower_limb",
    "ankle_right": "lower_limb",
    "heel_left": "lower_limb",
    "heel_right": "lower_limb",
    "foot_index_left": "lower_limb",
    "foot_index_right": "lower_limb",
    "foot_left": "lower_limb",
    "foot_right": "lower_limb",
    # 躯干
    "nose": "trunk",
    "eye_left": "trunk",
    "eye_right": "trunk",
    "eye_inner_left": "trunk",
    "eye_inner_right": "trunk",
    "eye_outer_left": "trunk",
    "eye_outer_right": "trunk",
    "ear_left": "trunk",
    "ear_right": "trunk",
    "mouth_left": "trunk",
    "mouth_right": "trunk",
    "hip_left": "trunk",
    "hip_right": "trunk",
}


def get_generic_name(
    marker_name: str,
    source: Literal["mediapipe", "mocap"] = "mediapipe",
) -> str | None:
    """
    将 marker 名称转换为通用名。

    Args:
        marker_name: marker 原始名称。
        source: 来源类型，"mediapipe" 或 "mocap"。

    Returns:
        通用名称，如果无法识别则返回 None。
    """
    name_lower = marker_name.lower()

    if source == "mediapipe":
        # 直接从 MediaPipe 映射表查找
        return MEDIAPIPE_TO_GENERIC.get(name_lower)

    # 对于动捕 marker，尝试多种匹配方式
    # 1. 精确匹配
    if name_lower in MOCAP_TO_GENERIC:
        return MOCAP_TO_GENERIC[name_lower]

    # 2. 包含匹配（处理如 "L_Wrist_X" 这种带后缀的）
    for mocap_name, generic_name in MOCAP_TO_GENERIC.items():
        if mocap_name in name_lower or name_lower in mocap_name:
            return generic_name

    return None


def get_limb_type(generic_name: str) -> str | None:
    """
    根据通用名获取肢体类型。

    Args:
        generic_name: 通用名称。

    Returns:
        肢体类型："upper_extremity", "upper_limb", "lower_limb", "trunk", 或 None。
    """
    return GENERIC_TO_LIMB_TYPE.get(generic_name.lower())


def get_mediapipe_name(generic_name: str) -> str | None:
    """
    根据通用名获取 MediaPipe 名称。

    Args:
        generic_name: 通用名称。

    Returns:
        MediaPipe 关键点名称，或 None。
    """
    return GENERIC_TO_MEDIAPIPE.get(generic_name.lower())


def get_available_generic_names() -> list[str]:
    """获取所有可用的通用名称列表。"""
    return list(set(MEDIAPIPE_TO_GENERIC.values()))


def get_limb_markers(limb_type: str) -> list[str]:
    """
    获取指定肢体类型的所有通用 marker 名称。

    Args:
        limb_type: 肢体类型 ("upper_extremity", "upper_limb", "lower_limb", "trunk")

    Returns:
        该肢体类型的 marker 名称列表。
    """
    return [
        name for name, limb in GENERIC_TO_LIMB_TYPE.items()
        if limb == limb_type
    ]


# 肢体类型中文映射
LIMB_TYPE_CN = {
    "upper_extremity": "上肢末端",
    "upper_limb": "上肢",
    "lower_limb": "下肢",
    "trunk": "躯干",
    "unknown": "其他",
}
