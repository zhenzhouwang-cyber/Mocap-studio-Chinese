"""
DTW多尺度比对优化模块。

增强动态时间规整（DTW）功能：
- 多尺度时序对齐
- 部位权重配置
- 相似度评分优化
- 基于京剧程式化特征的加权比对
"""

from __future__ import annotations

from typing import Any

import numpy as np

from opera_mocap_tool.io.base import MocapData


# 部位权重配置 - 不同肢体在云手比对中的重要性
LIMB_WEIGHTS = {
    # 上肢 - 最重要
    "upper_extremity": {
        "weight": 0.5,
        "markers": ["wrist", "elbow", "hand"],
        "description": "上肢是云手动作的核心",
    },
    # 躯干 - 重要
    "trunk": {
        "weight": 0.25,
        "markers": ["spine", "chest", "shoulder", "hip"],
        "description": "躯干提供支撑和协调",
    },
    # 下肢 - 辅助
    "lower_extremity": {
        "weight": 0.15,
        "markers": ["foot", "ankle", "knee", "leg"],
        "description": "下肢提供稳定",
    },
    # 头部 - 辅助
    "head": {
        "weight": 0.1,
        "markers": ["head", "neck"],
        "description": "头部姿态配合",
    },
}


# 特征权重配置
FEATURE_WEIGHTS = {
    "position": 0.4,      # 位置
    "velocity": 0.3,      # 速度
    "angle": 0.2,        # 角度
    "acceleration": 0.1,  # 加速度
}


def _normalize_sequence(seq: np.ndarray) -> np.ndarray:
    """Z-score标准化"""
    if seq.size == 0:
        return seq
    mu = np.nanmean(seq, axis=0)
    sigma = np.nanstd(seq, axis=0)
    sigma[sigma < 1e-10] = 1.0
    return (seq - mu) / sigma


def _compute_distance_matrix(A: np.ndarray, B: np.ndarray) -> np.ndarray:
    """计算两个序列之间的欧氏距离矩阵"""
    n, m = A.shape[0], B.shape[0]
    if n == 0 or m == 0:
        return np.array([[]])
    
    # 使用广播计算距离
    dist = np.sqrt(np.sum((A[:, np.newaxis, :] - B[np.newaxis, :, :]) ** 2, axis=2))
    return dist


def dtw_distance(
    A: np.ndarray,
    B: np.ndarray,
    window_ratio: float = 0.1,
) -> tuple[float, list[tuple[int, int]], np.ndarray]:
    """
    带窗口约束的DTW计算。
    
    Args:
        A: 序列A (n, d)
        B: 序列B (m, d)
        window_ratio: 窗口大小相对于序列长度的比例
        
    Returns:
        (DTW距离, 对齐路径, 累积成本矩阵)
    """
    n, m = A.shape
    if n == 0 or m == 0:
        return float("inf"), [], np.array([[]])
    
    # 窗口约束
    window = max(1, int(max(n, m) * window_ratio))
    
    # 成本矩阵
    C = _compute_distance_matrix(A, B)
    
    # 累积成本矩阵
    D = np.full((n + 1, m + 1), np.inf)
    D[0, 0] = 0
    
    for i in range(1, n + 1):
        j_start = max(1, i - window)
        j_end = min(m, i + window) + 1
        for j in range(j_start, j_end):
            D[i, j] = C[i - 1, j - 1] + min(
                D[i - 1, j],      # 插入
                D[i - 1, j - 1],  # 匹配
                D[i, j - 1]       # 删除
            )
    
    total_distance = D[n, m]
    
    # 回溯路径
    path = []
    i, j = n, m
    while i > 0 and j > 0:
        path.append((i - 1, j - 1))
        candidates = [
            (D[i - 1, j - 1], i - 1, j - 1),
            (D[i - 1, j], i - 1, j) if i > 1 else (np.inf, i - 1, j),
            (D[i, j - 1], i, j - 1) if j > 1 else (np.inf, i, j - 1),
        ]
        _, i, j = min(candidates, key=lambda x: x[0])
    
    path.reverse()
    
    return float(total_distance), path, D


def dtw_multiscale(
    A: np.ndarray,
    B: np.ndarray,
    scales: list[int] = None,
) -> dict[str, Any]:
    """
    多尺度DTW比对。
    
    在不同时间分辨率上进行DTW，然后融合结果。
    
    Args:
        A: 序列A (n, d)
        B: 序列B (m, d)
        scales: 下采样比例列表
        
    Returns:
        多尺度比对结果
    """
    if scales is None:
        scales = [1, 2, 4]  # 原始、2倍、4倍下采样
    
    results = []
    
    for scale in scales:
        # 下采样
        if scale == 1:
            A_scale = A
            B_scale = B
        else:
            # 每scale个点取一个
            A_scale = A[::scale] if len(A) > scale else A
            B_scale = B[::scale] if len(B) > scale else B
        
        # 计算DTW
        dist, path, _ = dtw_distance(
            _normalize_sequence(A_scale),
            _normalize_sequence(B_scale),
        )
        
        # 归一化距离
        norm_dist = dist / (len(A_scale) + len(B_scale)) if (len(A_scale) + len(B_scale)) > 0 else np.inf
        
        results.append({
            "scale": scale,
            "distance": dist,
            "normalized_distance": norm_dist,
            "path_length": len(path),
            "A_len": len(A_scale),
            "B_len": len(B_scale),
        })
    
    # 融合多尺度结果（加权平均）
    # 细尺度权重更高
    weights = [1.0 / (s ** 0.5) for s in scales]
    total_weight = sum(weights)
    weights = [w / total_weight for w in weights]
    
    fused_distance = sum(r["normalized_distance"] * w for r, w in zip(results, weights))
    
    return {
        "scales": scales,
        "scale_results": results,
        "fused_distance": fused_distance,
        "best_scale": min(results, key=lambda x: x["normalized_distance"]),
    }


def dtw_weighted_limb(
    current_data: np.ndarray,
    ref_data: np.ndarray,
    limb_weights: dict[str, float] = None,
) -> dict[str, Any]:
    """
    带部位权重的DTW比对。
    
    Args:
        current_data: 当前数据 (n_frames, n_markers, 3)
        ref_data: 参考数据 (m_frames, n_markers, 3)
        limb_weights: 部位权重字典
        
    Returns:
        加权比对结果
    """
    if limb_weights is None:
        limb_weights = {k: v["weight"] for k, v in LIMB_WEIGHTS.items()}
    
    n_frames_curr, n_markers, _ = current_data.shape
    n_frames_ref, _, _ = ref_data.shape
    
    # 提取各部位的marker
    # 这里简化处理，实际需要根据marker名称分组
    limb_distances = {}
    
    # 整体DTW
    curr_flat = current_data.reshape(n_frames_curr, -1)
    ref_flat = ref_data.reshape(n_frames_ref, -1)
    
    overall_dist, overall_path, _ = dtw_distance(
        _normalize_sequence(curr_flat),
        _normalize_sequence(ref_flat),
    )
    
    # 按部位计算DTW
    # 简化：假设marker按顺序排列
    n_per_limb = n_markers // 4  # 简化为4组
    
    limb_names = list(limb_weights.keys())
    
    for idx, limb_name in enumerate(limb_names):
        start = idx * n_per_limb
        end = start + n_per_limb if idx < 3 else n_markers
        
        if end <= n_markers and start < n_markers:
            curr_limb = current_data[:, start:end, :].reshape(n_frames_curr, -1)
            ref_limb = ref_data[:, start:end, :].reshape(n_frames_ref, -1)
            
            if curr_limb.size > 0 and ref_limb.size > 0:
                dist, path, _ = dtw_distance(
                    _normalize_sequence(curr_limb),
                    _normalize_sequence(ref_limb),
                )
                
                limb_distances[limb_name] = {
                    "distance": dist,
                    "normalized_distance": dist / (curr_limb.shape[1] + ref_limb.shape[1]) if curr_limb.shape[1] > 0 else 0,
                    "path_length": len(path),
                }
    
    # 计算加权总分
    total_weighted_dist = 0
    total_weight_used = 0
    
    for limb_name, limd in limb_distances.items():
        weight = limb_weights.get(limb_name, 0)
        total_weighted_dist += limd["normalized_distance"] * weight
        total_weight_used += weight
    
    if total_weight_used > 0:
        weighted_score = total_weighted_dist / total_weight_used
    else:
        weighted_score = overall_dist
    
    # 转换为相似度 (0-1, 1为完全相似)
    similarity = 1.0 / (1.0 + weighted_score)
    
    return {
        "overall_distance": overall_dist,
        "overall_similarity": similarity,
        "limb_distances": limb_distances,
        "weighted_score": weighted_score,
        "path_length": len(overall_path),
    }


def compare_yunshou_enhanced(
    current_result: dict[str, Any],
    reference_result: dict[str, Any],
    use_multiscale: bool = True,
    use_weighted_limb: bool = True,
) -> dict[str, Any]:
    """
    增强版云手比对。
    
    整合多尺度DTW和部位权重。
    
    Args:
        current_result: 当前动作分析结果
        reference_result: 参考动作分析结果
        use_multiscale: 是否使用多尺度
        use_weighted_limb: 是否使用部位权重
        
    Returns:
        增强比对结果
    """
    # 提取轨迹数据
    curr_trajs = current_result.get("trajectories", {})
    ref_trajs = reference_result.get("trajectories", {})
    
    # 合并所有marker的轨迹
    def extract_combined_trajectory(trajs: dict) -> np.ndarray:
        all_points = []
        for marker_name, traj_data in trajs.items():
            x = traj_data.get("x", [])
            y = traj_data.get("y", [])
            z = traj_data.get("z", [])
            
            if x and y and z:
                # 取最短长度
                n = min(len(x), len(y), len(z))
                points = np.array([[x[i], y[i], z[i]] for i in range(n)])
                all_points.append(points)
        
        if not all_points:
            return np.array([]).reshape(0, 3)
        
        # 拼接所有marker
        return np.concatenate(all_points, axis=1)
    
    curr_traj = extract_combined_trajectory(curr_trajs)
    ref_traj = extract_combined_trajectory(ref_trajs)
    
    if curr_traj.size == 0 or ref_traj.size == 0:
        return {
            "error": "Insufficient trajectory data",
            "similarity": 0,
        }
    
    result = {}
    
    # 多尺度DTW
    if use_multiscale:
        multiscale_result = dtw_multiscale(curr_traj, ref_traj)
        result["multiscale"] = multiscale_result
        result["similarity"] = 1.0 / (1.0 + multiscale_result["fused_distance"])
    else:
        dist, path, _ = dtw_distance(
            _normalize_sequence(curr_traj),
            _normalize_sequence(ref_traj),
        )
        result["similarity"] = 1.0 / (1.0 + dist / (curr_traj.shape[1] + ref_traj.shape[1]))
    
    # 部位权重
    if use_weighted_limb:
        # 需要3D数据
        curr_3d = curr_traj.reshape(-1, curr_traj.shape[1] // 3, 3)
        ref_3d = ref_traj.reshape(-1, ref_traj.shape[1] // 3, 3)
        
        if curr_3d.shape[1] > 0 and ref_3d.shape[1] > 0:
            limb_result = dtw_weighted_limb(curr_3d, ref_3d)
            result["limb_weighted"] = limb_result
            # 综合相似度
            result["final_similarity"] = (
                result["similarity"] * 0.6 +
                limb_result["overall_similarity"] * 0.4
            )
        else:
            result["final_similarity"] = result["similarity"]
    else:
        result["final_similarity"] = result["similarity"]
    
    # 行当匹配
    curr_dang = current_result.get("dang", {}).get("dang", "unknown")
    ref_dang = reference_result.get("dang", {}).get("dang", "unknown")
    result["dang_match"] = curr_dang == ref_dang
    
    # 三节协调匹配
    curr_three = current_result.get("three_section", {}).get("coordination_score", 0)
    ref_three = reference_result.get("three_section", {}).get("coordination_score", 0)
    result["three_section_similarity"] = 1.0 - abs(curr_three - ref_three) / 100
    
    # 圆度匹配
    curr_circ = current_result.get("circularity", {}).get("circularity_score", 0)
    ref_circ = reference_result.get("circularity", {}).get("circularity_score", 0)
    result["circularity_similarity"] = 1.0 - abs(curr_circ - ref_circ)
    
    # 综合评分
    result["composite_score"] = (
        result["final_similarity"] * 0.5 +
        (1.0 if result["dang_match"] else 0.0) * 0.1 +
        result["three_section_similarity"] * 0.2 +
        result["circularity_similarity"] * 0.2
    )
    
    return result


def find_best_references(
    current_result: dict[str, Any],
    reference_results: list[dict[str, Any]],
    top_k: int = 5,
) -> list[dict[str, Any]]:
    """
    查找最相似的参考动作。
    
    Args:
        current_result: 当前动作分析结果
        reference_results: 参考动作分析结果列表
        top_k: 返回前K个
        
    Returns:
        排序后的相似参考列表
    """
    similarities = []
    
    for ref_result in reference_results:
        comp = compare_yunshou_enhanced(current_result, ref_result)
        similarities.append({
            "reference": ref_result.get("meta", {}).get("name", "unknown"),
            "similarity": comp.get("composite_score", 0),
            "details": comp,
        })
    
    # 排序
    similarities.sort(key=lambda x: x["similarity"], reverse=True)
    
    return similarities[:top_k]
