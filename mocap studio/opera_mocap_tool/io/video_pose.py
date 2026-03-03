"""
视频姿态估计模块 - 使用 MediaPipe 进行无标记动捕。

将视频文件或摄像头捕获转换为 MocapData 格式，
以便复用现有的分析流程（DTW 比对、运动学分析等）。

依赖：
    pip install opencv-python mediapipe

MediaPipe Pose 输出 33 个 3D 身体关键点。
"""

from __future__ import annotations

import cv2
from pathlib import Path
from typing import Generator

import numpy as np

try:
    import mediapipe as mp
except ImportError:
    raise ImportError("请安装 mediapipe: pip install mediapipe")

from .base import MocapData


# MediaPipe Pose 33个关键点的语义名称
MEDIAPIPE_LANDMARKS = [
    "nose",
    "left_eye_inner", "left_eye", "left_eye_outer",
    "right_eye_inner", "right_eye", "right_eye_outer",
    "left_ear", "right_ear",
    "mouth_left", "mouth_right",
    "left_shoulder", "right_shoulder",
    "left_elbow", "right_elbow",
    "left_wrist", "right_wrist",
    "left_pinky", "right_pinky",
    "left_index", "right_index",
    "left_thumb", "right_thumb",
    "left_hip", "right_hip",
    "left_knee", "right_knee",
    "left_ankle", "right_ankle",
    "left_heel", "right_heel",
    "left_foot_index", "right_foot_index",
]

# 简化的关键点子集（用于主要身体部位的快速分析）
SIMPLIFIED_LANDMARKS = [
    "nose",
    "left_shoulder", "right_shoulder",
    "left_elbow", "right_elbow",
    "left_wrist", "right_wrist",
    "left_hip", "right_hip",
    "left_knee", "right_knee",
    "left_ankle", "right_ankle",
]


def _get_pose_solution(
    static_image_mode: bool = False,
    model_complexity: int = 1,
    smooth_landmarks: bool = True,
    enable_segmentation: bool = False,
):
    """创建并返回 MediaPipe Pose 对象。"""
    mp_pose = mp.solutions.pose
    return mp_pose.Pose(
        static_image_mode=static_image_mode,
        model_complexity=model_complexity,
        smooth_landmarks=smooth_landmarks,
        enable_segmentation=enable_segmentation,
    )


def load_video_pose(
    video_path: str | Path,
    target_fps: float | None = None,
    use_simplified: bool = False,
) -> MocapData:
    """
    从视频文件加载姿态估计数据。

    Args:
        video_path: 视频文件路径。
        target_fps: 目标帧率。如果为 None，则使用原始视频帧率。
        use_simplified: 是否仅使用简化的关键点子集（减少计算量）。

    Returns:
        MocapData 实例，包含 33 个（或简化后的）身体关键点。

    Raises:
        FileNotFoundError: 视频文件不存在。
        ValueError: 无法读取视频或提取姿态。
    """
    video_path = Path(video_path)
    if not video_path.exists():
        raise FileNotFoundError(f"视频文件不存在: {video_path}")

    # 打开视频
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise ValueError(f"无法打开视频: {video_path}")

    # 获取原始帧率
    original_fps = cap.get(cv2.CAP_PROP_FPS)
    if original_fps <= 0:
        original_fps = 30.0  # 默认值

    # 确定目标帧率
    fps = target_fps if target_fps is not None else original_fps

    # 初始化 MediaPipe Pose
    pose = _get_pose_solution()

    # 用于存储所有关键点
    all_landmarks: list[dict] = []

    # 读取帧
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        # 转换为 RGB
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # 处理姿态
        results = pose.process(frame_rgb)

        if results.pose_landmarks:
            # 提取关键点
            frame_landmarks = {}
            landmarks_to_use = SIMPLIFIED_LANDMARKS if use_simplified else MEDIAPIPE_LANDMARKS

            for idx, landmark_name in enumerate(landmarks_to_use):
                landmark = results.pose_landmarks.landmark[idx]
                # MediaPipe 的坐标是归一化的 (0-1)
                # x, y: 图像坐标 (0-1)
                # z: 深度 (相对于髋部中心的距离)
                frame_landmarks[landmark_name] = (
                    float(landmark.x),
                    float(landmark.y),
                    float(landmark.z),
                )

            all_landmarks.append(frame_landmarks)

    cap.release()
    pose.close()

    if not all_landmarks:
        raise ValueError(f"未能从视频中提取到姿态数据: {video_path}")

    # 转换为 MocapData
    return _landmarks_to_mocapdata(all_landmarks, fps)


def iter_video_pose(
    video_path: str | Path,
    batch_size: int = 1,
) -> Generator[dict[str, tuple[float, float, float]], None, None]:
    """
    逐帧迭代视频姿态（用于实时处理）。

    Args:
        video_path: 视频文件路径。
        batch_size: 批处理大小（暂未实现）。

    Yields:
        每帧的关键点字典 {landmark_name: (x, y, z)}。
    """
    video_path = Path(video_path)

    if not video_path.exists():
        raise FileNotFoundError(f"视频文件不存在: {video_path}")

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise ValueError(f"无法打开视频: {video_path}")

    pose = _get_pose_solution()

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = pose.process(frame_rgb)

        if results.pose_landmarks:
            frame_landmarks = {}
            for idx, landmark_name in enumerate(MEDIAPIPE_LANDMARKS):
                landmark = results.pose_landmarks.landmark[idx]
                frame_landmarks[landmark_name] = (
                    float(landmark.x),
                    float(landmark.y),
                    float(landmark.z),
                )
            yield frame_landmarks

    cap.release()
    pose.close()


def _landmarks_to_mocapdata(
    landmarks_sequence: list[dict[str, tuple[float, float, float]]],
    fps: float,
) -> MocapData:
    """
    将关键点序列转换为 MocapData 格式。

    Args:
        landmarks_sequence: 每一帧的关键点字典列表。
        fps: 帧率。

    Returns:
        MocapData 实例。
    """
    if not landmarks_sequence:
        raise ValueError("关键点序列为空")

    # 获取所有 marker 名称
    marker_labels = list(landmarks_sequence[0].keys())

    # 构建 markers 字典: {marker_name: [(x,y,z), ...]}
    markers: dict[str, list[tuple[float, float, float]]] = {
        name: [] for name in marker_labels
    }

    for frame_landmarks in landmarks_sequence:
        for name in marker_labels:
            markers[name].append(frame_landmarks.get(name, (0.0, 0.0, 0.0)))

    # 创建 MocapData
    mocap_data = MocapData(
        markers=markers,
        frame_rate=fps,
        marker_labels=marker_labels,
        metadata={
            "source": "mediapipe_pose",
            "n_landmarks": len(marker_labels),
            "coordinate_system": "normalized",
            "description": "从视频提取的 MediaPipe 姿态数据",
        },
    )

    return mocap_data


def get_camera_pose(
    camera_index: int = 0,
    duration_frames: int | None = None,
    target_fps: float = 30.0,
) -> MocapData:
    """
    从摄像头捕获姿态数据。

    Args:
        camera_index: 摄像头索引（默认 0）。
        duration_frames: 捕获的帧数。如果为 None，则持续捕获直到按 q 退出。
        target_fps: 目标帧率。

    Returns:
        MocapData 实例。

    Raises:
        ValueError: 无法打开摄像头或提取姿态。
    """
    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        raise ValueError(f"无法打开摄像头索引: {camera_index}")

    pose = _get_pose_solution()
    all_landmarks: list[dict] = []

    frame_count = 0

    print("按 'q' 键停止捕获...")

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = pose.process(frame_rgb)

        if results.pose_landmarks:
            frame_landmarks = {}
            for idx, landmark_name in enumerate(MEDIAPIPE_LANDMARKS):
                landmark = results.pose_landmarks.landmark[idx]
                frame_landmarks[landmark_name] = (
                    float(landmark.x),
                    float(landmark.y),
                    float(landmark.z),
                )
            all_landmarks.append(frame_landmarks)

        frame_count += 1

        # 显示进度
        if duration_frames and frame_count >= duration_frames:
            break

        # 按 q 退出
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    pose.close()

    if not all_landmarks:
        raise ValueError("未能从摄像头提取到姿态数据")

    return _landmarks_to_mocapdata(all_landmarks, target_fps)


def convert_video_to_mocap(
    video_path: str | Path,
    output_path: str | Path | None = None,
    target_fps: float | None = None,
) -> MocapData:
    """
    便捷函数：将视频转换为 MocapData 并可选保存为 CSV。

    Args:
        video_path: 输入视频路径。
        output_path: 输出 CSV 路径。如果为 None，则不保存。
        target_fps: 目标帧率。

    Returns:
        MocapData 实例。
    """
    mocap_data = load_video_pose(video_path, target_fps=target_fps)

    if output_path:
        output_path = Path(output_path)
        _save_as_csv(mocap_data, output_path)

    return mocap_data


def _save_as_csv(mocap_data: MocapData, output_path: Path) -> None:
    """将 MocapData 保存为 CSV 格式。"""
    import csv

    n_frames = mocap_data.n_frames

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        # 写入表头
        header = ["frame", "time"]
        for marker in mocap_data.marker_labels:
            header.extend([f"{marker}_x", f"{marker}_y", f"{marker}_z"])
        writer.writerow(header)

        # 写入数据
        for i in range(n_frames):
            row = [i, i / mocap_data.frame_rate]
            for marker in mocap_data.marker_labels:
                x, y, z = mocap_data.markers[marker][i]
                row.extend([x, y, z])
            writer.writerow(row)

    print(f"已保存到: {output_path}")


# MediaPipe landmark 索引映射（备用）
LANDMARK_NAME_TO_INDEX = {name: idx for idx, name in enumerate(MEDIAPIPE_LANDMARKS)}
