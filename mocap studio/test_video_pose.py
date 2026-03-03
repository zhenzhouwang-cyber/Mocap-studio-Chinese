"""
视频姿态估计测试脚本。

用法：
    python test_video_pose.py                    # 测试摄像头捕获
    python test_video_pose.py video.mp4          # 测试视频文件
    python test_video_pose.py video.mp4 output.csv 保存为 CSV # 测试并
"""

import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent / "opera_mocap_tool"))

from opera_mocap_tool.io import load_video_pose, convert_video_to_mocap, MEDIAPIPE_LANDMARKS


def test_video_pose(video_path: str | None = None, output_csv: str | None = None):
    """测试视频姿态估计功能。"""
    print("=" * 50)
    print("视频姿态估计测试")
    print("=" * 50)

    if video_path:
        # 测试视频文件
        video_path = Path(video_path)
        if not video_path.exists():
            print(f"错误: 视频文件不存在: {video_path}")
            return

        print(f"\n[1] 加载视频: {video_path}")
        mocap_data = load_video_pose(video_path, target_fps=30.0)

        print(f"\n[2] 视频信息:")
        print(f"    - 帧率: {mocap_data.frame_rate} Hz")
        print(f"    - 帧数: {mocap_data.n_frames}")
        print(f"    - 时长: {mocap_data.duration_sec:.2f} 秒")
        print(f"    - 关键点数量: {len(mocap_data.marker_labels)}")

        print(f"\n[3] 关键点列表:")
        for i, label in enumerate(mocap_data.marker_labels):
            print(f"    {i:2d}: {label}")

        # 显示第一帧的关键点数据
        print(f"\n[4] 第一帧关键点坐标 (归一化):")
        for label in mocap_data.marker_labels[:5]:  # 只显示前5个
            x, y, z = mocap_data.markers[label][0]
            print(f"    {label:20s}: ({x:.4f}, {y:.4f}, {z:.4f})")

        # 如果指定了输出路径，保存为 CSV
        if output_csv:
            output_path = Path(output_csv)
            print(f"\n[5] 保存为 CSV: {output_path}")
            convert_video_to_mocap(video_path, output_path)

        print("\n" + "=" * 50)
        print("测试完成!")
        print("=" * 50)

    else:
        # 测试摄像头捕获
        print("\n[提示] 未提供视频路径，将测试摄像头捕获功能")
        print("注意: 摄像头测试需要实际摄像头设备")
        print("请使用 get_camera_pose() 函数进行测试")

        # 演示代码
        print("\n--- 摄像头捕获示例代码 ---")
        print("""
from opera_mocap_tool.io import get_camera_pose

# 捕获 300 帧（约10秒）
mocap_data = get_camera_pose(
    camera_index=0,
    duration_frames=300,
    target_fps=30.0
)

print(f"捕获帧数: {mocap_data.n_frames}")
print(f"关键点数量: {len(mocap_data.marker_labels)}")
        """)


def test_load_mocap_video():
    """测试通过统一的 load_mocap 接口加载视频。"""
    print("\n" + "=" * 50)
    print("测试统一加载接口 (load_mocap)")
    print("=" * 50)

    from opera_mocap_tool.io import load_mocap

    # 测试支持的视频格式
    video_formats = [".mp4", ".avi", ".mov", ".mkv", ".webm"]
    print("\n支持的视频格式:")
    for fmt in video_formats:
        print(f"  - {fmt}")

    print("\n注意: 实际加载需要提供有效的视频文件路径")
    print("load_mocap 会自动识别视频格式并调用 load_video_pose")


if __name__ == "__main__":
    # 获取命令行参数
    args = sys.argv[1:]

    if args:
        video_path = args[0]
        output_csv = args[1] if len(args) > 1 else None
        test_video_pose(video_path, output_csv)
    else:
        test_video_pose()
        test_load_mocap_video()
