"""
频域分析：FFT频谱、周期检测、主频提取。

依据文献 "Computational kinematics of dance: distinguishing hip hop genres" (Frontiers)
用于检测周期性动作（云手、跑圆场等）和提取运动节律特征。

学术价值：
- FFT频谱分析可识别动作的主频和周期性
- 支撑论文中"运动节律"相关章节的量化分析
- 便于与音乐节奏进行对比分析
"""

from __future__ import annotations

from typing import Any

import numpy as np

from opera_mocap_tool.io.base import MocapData


def compute_frequency_analysis(
    data: MocapData,
    kinematics: dict | None = None,
    min_period_frames: int = 10,
) -> dict[str, Any]:
    """
    计算频域特征：FFT频谱、周期检测、主频提取。

    Args:
        data: MocapData。
        kinematics: 若已计算则传入。
        min_period_frames: 最小周期帧数（用于过滤高频噪声）。

    Returns:
        包含 fft_spectrum, dominant_frequencies, periodicity 的字典。
    """
    from .kinematic import compute_kinematics

    kin = kinematics or compute_kinematics(data)
    fr = data.frame_rate
    
    result: dict[str, Any] = {
        "fft_spectrum": {},
        "dominant_frequencies": {},
        "periodicity": {},
    }

    trajectories = kin.get("trajectories", {})
    if not trajectories:
        return result

    for name, coords in trajectories.items():
        arr_x = np.array(coords.get("x", []), dtype=float)
        arr_y = np.array(coords.get("y", []), dtype=float)
        arr_z = np.array(coords.get("z", []), dtype=float)
        
        if len(arr_x) < min_period_frames * 2:
            continue

        # 对xyz分别进行FFT分析
        for axis_name, arr in [("x", arr_x), ("y", arr_y), ("z", arr_z)]:
            key = f"{name}_{axis_name}"
            
            # 去除均值以突出周期成分
            arr_centered = arr - np.nanmean(arr)
            
            # 计算FFT
            n = len(arr_centered)
            fft_result = np.fft.fft(arr_centered)
            fft_freq = np.fft.fftfreq(n, 1.0 / fr)
            
            # 只取正频率部分
            positive_mask = fft_freq > 0
            fft_magnitude = np.abs(fft_result[positive_mask])
            fft_freq_positive = fft_freq[positive_mask]
            
            # 归一化幅度
            fft_magnitude_normalized = fft_magnitude / (np.max(fft_magnitude) + 1e-8)
            
            # 存储频谱（取前50个频率分量）
            n_components = min(50, len(fft_magnitude_normalized))
            result["fft_spectrum"][key] = {
                "frequencies": [round(float(f), 4) for f in fft_freq_positive[:n_components]],
                "magnitudes": [round(float(m), 6) for m in fft_magnitude_normalized[:n_components]],
            }
            
            # 提取主频（幅度最大的频率）
            if len(fft_magnitude) > 0:
                dominant_idx = np.argmax(fft_magnitude)
                dominant_freq = fft_freq_positive[dominant_idx] if dominant_idx < len(fft_freq_positive) else 0.0
                result["dominant_frequencies"][key] = round(float(dominant_freq), 4)
            
            # 周期性检测：计算主频对应的能量占比
            if len(fft_magnitude) > 0:
                total_energy = np.sum(fft_magnitude ** 2)
                if total_energy > 0:
                    # 主频及其谐波的功率占比
                    harmonic_energy = fft_magnitude[dominant_idx] ** 2 if dominant_idx < len(fft_magnitude) else 0
                    periodicity_ratio = harmonic_energy / total_energy
                    result["periodicity"][key] = round(float(periodicity_ratio), 4)

    # 聚合所有marker的主频统计
    all_dominant_freqs = list(result["dominant_frequencies"].values())
    if all_dominant_freqs:
        result["summary"] = {
            "mean_dominant_freq": round(float(np.mean(all_dominant_freqs)), 4),
            "std_dominant_freq": round(float(np.std(all_dominant_freqs)), 4),
            "min_dominant_freq": round(float(np.min(all_dominant_freqs)), 4),
            "max_dominant_freq": round(float(np.max(all_dominant_freqs)), 4),
        }

    return result


def compute_periodicity_metrics(
    data: MocapData,
    kinematics: dict | None = None,
    window_size: int = 60,
) -> dict[str, Any]:
    """
    计算滑动窗口周期性强度的时序变化。

    用于检测动作中周期性强度的时间演变（如跑圆场的持续周期性）。

    Args:
        data: MocapData。
        kinematics: 若已计算则传入。
        window_size: 滑动窗口大小（帧数）。

    Returns:
        包含 periodicity_time_series 的字典。
    """
    from .kinematic import compute_kinematics

    kin = kinematics or compute_kinematics(data)
    fr = data.frame_rate
    n_frames = data.n_frames
    
    if n_frames < window_size * 2:
        return {"periodicity_time_series": {}}

    result: dict[str, Any] = {"periodicity_time_series": {}}

    velocities = kin.get("velocities", {})
    if not velocities:
        return result

    # 选取一个代表性marker的速度进行分析
    for name, vel_data in velocities.items():
        speed = vel_data.get("speed", [])
        if not speed or len(speed) < window_size:
            continue

        speed_arr = np.array(speed, dtype=float)
        periodicity_series = []

        for i in range(0, n_frames - window_size, window_size // 2):
            window = speed_arr[i:i + window_size]
            if len(window) < window_size // 2:
                continue

            # 计算窗口内的FFT
            window_centered = window - np.mean(window)
            fft_result = np.fft.fft(window_centered)
            fft_freq = np.fft.fftfreq(len(window_centered), 1.0 / fr)
            
            positive_mask = fft_freq > 0
            fft_magnitude = np.abs(fft_result[positive_mask])
            
            if len(fft_magnitude) > 0 and np.sum(fft_magnitude ** 2) > 0:
                dominant_idx = np.argmax(fft_magnitude)
                total_energy = np.sum(fft_magnitude ** 2)
                periodicity = (fft_magnitude[dominant_idx] ** 2) / total_energy
                periodicity_series.append(round(float(periodicity), 4))

        if periodicity_series:
            result["periodicity_time_series"][name] = {
                "time_points": [round(i * (window_size // 2) / fr, 2) for i in range(len(periodicity_series))],
                "periodicity": periodicity_series,
            }
        break  # 只分析第一个有效marker

    return result


def detect_periodic_motions(
    data: MocapData,
    kinematics: dict | None = None,
    periodicity_threshold: float = 0.3,
) -> dict[str, Any]:
    """
    检测具有明显周期性的动作段。

    识别可能为周期性动作的区域（如云手、跑圆场等）。

    Args:
        data: MocapData。
        kinematics: 若已计算则传入。
        periodicity_threshold: 周期性强度的阈值。

    Returns:
        包含 periodic_segments 的字典。
    """
    from .kinematic import compute_kinematics

    kin = kinematics or compute_kinematics(data)
    fr = data.frame_rate
    n_frames = data.n_frames
    
    result: dict[str, Any] = {"periodic_segments": []}

    velocities = kin.get("velocities", {})
    if not velocities:
        return result

    # 分析整体速度的周期性
    all_speeds = []
    for name, vel_data in velocities.items():
        speed = vel_data.get("speed", [])
        if speed:
            all_speeds.append(np.array(speed, dtype=float))
    
    if not all_speeds:
        return result

    # 计算平均速度
    max_len = max(len(s) for s in all_speeds)
    avg_speed = np.zeros(max_len)
    count = np.zeros(max_len)
    
    for s in all_speeds:
        avg_speed[:len(s)] += s
        count[:len(s)] += 1
    
    avg_speed = avg_speed / np.maximum(count, 1)

    # 使用自相关检测周期性
    def compute_autocorrelation(signal: np.ndarray, max_lag: int) -> np.ndarray:
        """计算自相关函数"""
        n = len(signal)
        signal = signal - np.mean(signal)
        autocorr = np.correlate(signal, signal, mode='full')
        autocorr = autocorr[n-1:n+max_lag]
        return autocorr / (autocorr[0] + 1e-8)

    # 计算自相关
    max_lag = min(n_frames // 2, 100)
    autocorr = compute_autocorrelation(avg_speed, max_lag)
    
    # 找到自相关的峰值（周期）
    from scipy.signal import find_peaks
    peaks, _ = find_peaks(autocorr[1:], height=periodicity_threshold)
    
    if len(peaks) > 0:
        # 第一个显著峰值即为周期
        period_frames = peaks[0] + 1
        period_sec = period_frames / fr
        
        result["periodic_segments"] = [{
            "marker": "average_body",
            "period_frames": int(period_frames),
            "period_sec": round(float(period_sec), 4),
            "dominant_freq_hz": round(float(1.0 / period_sec), 4) if period_sec > 0 else 0.0,
            "autocorrelation_strength": round(float(autocorr[peaks[0] + 1]), 4),
        }]

    return result
