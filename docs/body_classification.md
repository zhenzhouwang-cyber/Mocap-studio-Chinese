# 身段/肢体分类依据说明

## 分类依据

**按 marker 名称中的关键词推断**，不是按 marker 点数。

实现位置：`opera_mocap_tool/analysis/opera_features.py` 中的 `classify_limb(marker_name)`。

## 分类规则表

| 肢体类型 | 中文 | 关键词（英文/中文） | 说明 |
|----------|------|---------------------|------|
| upper_extremity | 上肢末端 | wrist, hand, finger, 袖, 手 | 腕、手、手指、水袖相关 |
| upper_limb | 上肢 | elbow, shoulder, arm, 臂, 肘 | 肘、肩、上臂 |
| lower_limb | 下肢 | knee, ankle, foot, toe, 膝, 脚 | 膝、踝、脚、脚趾 |
| trunk | 躯干 | head, spine, pelvis, 头, 脊, 腰 | 头、脊柱、骨盆 |
| unknown | 其他 | 未匹配以上 | 无法从名称推断的 marker |

## 流程

1. 对每个 marker 名称调用 `classify_limb(marker_name)`，返回上述类型之一
2. 统计各类型的 **marker 数量**，即界面表格中的「Marker 数」

## 示例

- `Daphnee:WRIST` 含 "wrist" → upper_extremity
- `Daphnee:DELT` 无匹配 → unknown（可后续补充 shoulder/delt 等关键词）

## 后续

您提供 Vicon 标准 marker 模板后，可扩展 `classify_limb` 的规则或改为查表映射，使分类更贴合实际骨骼命名。
