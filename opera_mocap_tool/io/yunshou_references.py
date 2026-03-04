"""
云手参考库管理模块。

管理云手参考数据，支持：
- 添加参考数据（FBX/视频/MocapData）
- 查询参考库
- DTW比对
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from opera_mocap_tool.io.base import MocapData


# 默认参考库路径
DEFAULT_DB_PATH = "data/yunshou_references"


class YunshouReferenceDatabase:
    """云手参考库管理器"""

    def __init__(self, db_path: str | Path | None = None):
        """
        初始化参考库。

        Args:
            db_path: 参考库根目录路径
        """
        self.db_path = Path(db_path) if db_path else Path(DEFAULT_DB_PATH)
        self.metadata_file = self.db_path / "metadata.json"
        self.references_dir = self.db_path / "references"
        self.features_dir = self.db_path / "features"

        # 确保目录存在
        self.db_path.mkdir(parents=True, exist_ok=True)
        self.references_dir.mkdir(parents=True, exist_ok=True)
        self.features_dir.mkdir(parents=True, exist_ok=True)

        # 加载元数据
        self.metadata = self._load_metadata()

    def _load_metadata(self) -> dict[str, Any]:
        """加载元数据"""
        if self.metadata_file.is_file():
            try:
                with open(self.metadata_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {"references": [], "statistics": {"total": 0, "by_dang": {}}}

    def _save_metadata(self) -> None:
        """保存元数据"""
        with open(self.metadata_file, "w", encoding="utf-8") as f:
            json.dump(self.metadata, f, ensure_ascii=False, indent=2)

    def add_reference(
        self,
        data: MocapData,
        metadata: dict[str, Any],
    ) -> str:
        """
        添加新的参考数据。

        Args:
            data: MocapData 格式的动捕数据
            metadata: 元数据，包含 name, source, dang, actor, date, frame_rate, tags 等

        Returns:
            参考数据 ID
        """
        import uuid

        # 生成唯一 ID
        ref_id = f"yunshou_{uuid.uuid4().hex[:8]}"

        # 确定子目录
        source = metadata.get("source", "unknown")
        if source == "optical":
            subdir = self.references_dir / "mocap"
        elif source == "video":
            subdir = self.references_dir / "video"
        else:
            subdir = self.references_dir / "other"

        subdir.mkdir(parents=True, exist_ok=True)

        # 保存原始数据为 JSON（简化版）
        # 实际项目中可以保存原始文件
        ref_data = {
            "id": ref_id,
            "metadata": metadata,
            "marker_labels": data.marker_labels,
            "n_frames": data.n_frames,
            "frame_rate": data.frame_rate,
            "duration_sec": data.duration_sec,
        }

        # 保存特征数据
        from opera_mocap_tool.analysis.yunshou_features import analyze_yunshou
        features = analyze_yunshou(data)

        feature_file = self.features_dir / f"{ref_id}_features.json"
        with open(feature_file, "w", encoding="utf-8") as f:
            json.dump(features, f, ensure_ascii=False, indent=2)

        # 更新元数据
        ref_entry = {
            "id": ref_id,
            "name": metadata.get("name", ref_id),
            "source": source,
            "format": metadata.get("format", "unknown"),
            "dang": metadata.get("dang", "unknown"),
            "actor": metadata.get("actor", ""),
            "date": metadata.get("date", ""),
            "duration_sec": data.duration_sec,
            "frame_rate": data.frame_rate,
            "tags": metadata.get("tags", []),
            "features_file": str(feature_file),
        }

        self.metadata["references"].append(ref_entry)

        # 更新统计
        self.metadata["statistics"]["total"] = len(self.metadata["references"])
        dang = metadata.get("dang", "unknown")
        if dang not in self.metadata["statistics"]["by_dang"]:
            self.metadata["statistics"]["by_dang"][dang] = 0
        self.metadata["statistics"]["by_dang"][dang] += 1

        self._save_metadata()

        return ref_id

    def get_reference(
        self,
        ref_id: str,
        compute_features: bool = False,
    ) -> dict[str, Any] | None:
        """
        获取参考数据及其特征。

        Args:
            ref_id: 参考数据 ID
            compute_features: 是否重新计算特征

        Returns:
            参考数据及特征字典
        """
        for ref in self.metadata["references"]:
            if ref["id"] == ref_id:
                features_file = Path(ref["features_file"])
                if features_file.is_file() and not compute_features:
                    with open(features_file, "r", encoding="utf-8") as f:
                        features = json.load(f)
                else:
                    return None  # 需要重新计算
                return {
                    "reference": ref,
                    "features": features,
                }
        return None

    def list_all(self) -> list[dict[str, Any]]:
        """列出所有参考数据"""
        return self.metadata["references"]

    def search(
        self,
        dang: str | None = None,
        source: str | None = None,
        tags: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """
        搜索参考库。

        Args:
            dang: 行当筛选
            source: 数据源筛选
            tags: 标签筛选

        Returns:
            符合条件的参考列表
        """
        results = []

        for ref in self.metadata["references"]:
            # 筛选条件
            if dang and ref.get("dang") != dang:
                continue
            if source and ref.get("source") != source:
                continue
            if tags:
                ref_tags = ref.get("tags", [])
                if not any(t in ref_tags for t in tags):
                    continue

            results.append(ref)

        return results

    def compare(
        self,
        data: MocapData,
        ref_ids: list[str] | None = None,
        top_k: int = 3,
    ) -> list[dict[str, Any]]:
        """
        与参考库比对，返回最相似的 Top-K。

        Args:
            data: 待比对的 MocapData
            ref_ids: 指定参考 ID 列表，None 表示全部
            top_k: 返回前 K 个最相似

        Returns:
            比对结果列表
        """
        from opera_mocap_tool.analysis.yunshou_features import analyze_yunshou

        # 计算待分析数据的特征
        features = analyze_yunshou(data)

        # 获取要比对的参考
        if ref_ids:
            refs_to_compare = [r for r in self.metadata["references"] if r["id"] in ref_ids]
        else:
            refs_to_compare = self.metadata["references"]

        if not refs_to_compare:
            return []

        # 简单比对：基于行当分类和特征相似度
        # 实际实现可以使用 DTW 进行更精确的时序比对
        results = []

        for ref in refs_to_compare:
            # 加载参考特征
            features_file = Path(ref["features_file"])
            if not features_file.is_file():
                continue

            with open(features_file, "r", encoding="utf-8") as f:
                ref_features = json.load(f)

            # 计算相似度（简化版）
            similarity = self._compute_similarity(features, ref_features)

            results.append({
                "ref_id": ref["id"],
                "ref_name": ref["name"],
                "dang": ref.get("dang"),
                "similarity": similarity,
                "ref_features": ref_features,
            })

        # 排序
        results.sort(key=lambda x: x["similarity"], reverse=True)

        return results[:top_k]

    def _compute_similarity(
        self,
        features1: dict[str, Any],
        features2: dict[str, Any],
    ) -> float:
        """
        计算两个特征集的相似度。

        简化实现：基于归一化特征的距离
        """
        # 行当匹配
        dang1 = features1.get("dang", {}).get("dang", "unknown")
        dang2 = features2.get("dang", {}).get("dang", "unknown")

        if dang1 == dang2 and dang1 != "unknown":
            similarity = 0.5
        else:
            similarity = 0.0

        # 圆度相似度
        circ1 = features1.get("circularity", {}).get("circularity_score", 0)
        circ2 = features2.get("circularity", {}).get("circularity_score", 0)
        similarity += 0.25 * (1 - abs(circ1 - circ2))

        # 三节协调相似度
        score1 = features1.get("three_section", {}).get("coordination_score", 0)
        score2 = features2.get("three_section", {}).get("coordination_score", 0)
        similarity += 0.25 * (1 - abs(score1 - score2) / 100)

        return min(1.0, similarity)

    def delete_reference(self, ref_id: str) -> bool:
        """
        删除参考数据。

        Args:
            ref_id: 参考数据 ID

        Returns:
            是否成功删除
        """
        refs = self.metadata["references"]
        for i, ref in enumerate(refs):
            if ref["id"] == ref_id:
                # 删除特征文件
                features_file = Path(ref.get("features_file", ""))
                if features_file.is_file():
                    features_file.unlink()

                # 从列表中移除
                refs.pop(i)

                # 更新统计
                self.metadata["statistics"]["total"] = len(refs)
                dang = ref.get("dang")
                if dang in self.metadata["statistics"]["by_dang"]:
                    self.metadata["statistics"]["by_dang"][dang] -= 1

                self._save_metadata()
                return True

        return False


# 便捷函数
def get_default_db() -> YunshouReferenceDatabase:
    """获取默认参考库实例"""
    return YunshouReferenceDatabase()
