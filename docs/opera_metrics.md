# 京剧动捕程式化指标定义（可引用）

本文档给出本工具中京剧动作分析所用指标的形式化定义与学理依据，便于在论文或报告中引用（如：「指标定义见项目 docs/opera_metrics.md」）。

---

## 1. 学理依据（京剧程式化理论）

京剧身段遵循**程式化**表现体系，本工具据此设计可量化指标：

- **精选**：从日常动作中提炼关键形态与节奏，形成可重复的「程式」；量化上体现为动作在时间与空间上的**节段性**（停顿、段落）与**幅度分布的稳定性**。
- **装饰**：对动作进行艺术化加工，包括**粗装饰**（整体放慢、加大幅度）与**精装饰**（角色/行当差异化）；量化上体现为**整体速度水平**、**幅度（位移范围）**及**速度变异**。
- **圆柔顺美**：轨迹圆润、力度柔和、衔接顺滑；量化上体现为**圆顺度**（低曲率、速度平滑）。

水袖、身段等技法（甩、掸、拨、扬等）在上述框架下可进一步通过**肢体分类**（上肢末端/上肢/下肢/躯干）与**幅度/速度剖面**刻画。

---

## 2. 幅度（amplitude）

**定义**：各 marker 在时间上的位移量（相对前一帧的位移模长）的统计。

- **mean**：整段内位移的算术平均。
- **max**：整段内位移的最大值。
- **std**：整段内位移的标准差。

**公式**（对 marker \(m\)，帧 \(i = 1 \ldots N-1\)）：

\[
d_i^{(m)} = \| \mathbf{p}_i^{(m)} - \mathbf{p}_{i-1}^{(m)} \|, \quad
\text{mean}^{(m)} = \frac{1}{N-1}\sum_i d_i^{(m)}, \quad
\text{max}^{(m)} = \max_i d_i^{(m)}, \quad
\text{std}^{(m)} = \sqrt{\frac{1}{N-1}\sum_i (d_i^{(m)} - \text{mean}^{(m)})^2}.
\]

**学理对应**：幅度与程式化中的「装饰」相关；放大动作幅度是常见粗装饰手段。

**输出位置**：`opera_features.amplitude[marker_name]` → `{ "mean", "max", "std" }`。

---

## 3. 圆顺度（smoothness）

**定义**：轨迹的弯曲程度与速度的平滑程度。

- **mean_curvature**：近似曲率（帧间）的绝对值平均。曲率近似为 \(\kappa \approx |\mathbf{a}| / (|\mathbf{v}|^2 + \epsilon)\)，其中 \(\mathbf{v}\) 为速度、\(\mathbf{a}\) 为加速度，\(\epsilon\) 为数值稳定项。
- **speed_smoothness**：该 marker 速度序列的标准差；越小表示速度越平稳。

**学理对应**：「圆柔顺美」中轨迹圆润、衔接顺滑；曲率低、速度变化小表示更圆顺。

**输出位置**：`opera_features.smoothness[marker_name]` → `{ "mean_curvature", "speed_smoothness" }`。

---

## 4. 程式化程度（stylization）

**定义**：全体 marker 速度水平的整体刻画。

- **overall_mean_speed**：所有 marker 的「平均速度」的再平均（即跨 marker 的平均速度水平）。
- **overall_speed_std**：上述各 marker 平均速度的标准差（跨 marker 的变异）。

**公式**：设 \(\bar{s}^{(m)}\) 为 marker \(m\) 在时间上的平均速度，则  
\(\text{overall\_mean\_speed} = \frac{1}{|M|}\sum_{m\in M} \bar{s}^{(m)}\)，  
\(\text{overall\_speed\_std} = \sqrt{\frac{1}{|M|}\sum_{m\in M} (\bar{s}^{(m)} - \text{overall\_mean\_speed})^2}\)。

**学理对应**：程式化节奏的整体「标准化」程度；速度变异可与角色/段落差异（精装饰）相联系。

**输出位置**：`opera_features.stylization` → `{ "overall_mean_speed", "overall_speed_std" }`。

---

## 5. 肢体分类（limb classification）

**定义**：根据 marker 名称关键词将 marker 归为：上肢末端、上肢、下肢、躯干、其他。

| 类别（英文）   | 中文     | 关键词（英文/中文） |
|----------------|----------|----------------------|
| upper_extremity | 上肢末端 | wrist, hand, finger, 袖, 手 |
| upper_limb      | 上肢     | elbow, shoulder, arm, 臂, 肘 |
| lower_limb      | 下肢     | knee, ankle, foot, toe, 膝, 脚 |
| trunk           | 躯干     | head, spine, pelvis, 头, 脊, 腰 |
| unknown         | 其他     | 未匹配以上关键词     |

**学理对应**：水袖、身段分析常关注上肢末端（腕、手、袖）与躯干；分类便于分肢体统计幅度/圆顺度。

**实现**：`opera_features.classify_limb(marker_name)`；GUI 中展示各肢体类型的 marker 数量。

---

## 6. 节奏与停顿（rhythm, pauses）

**定义**：

- **speed_profile**：每帧所有 marker 速度的均值序列 `mean_speed_per_frame`；阈值 `threshold` 取全体速度的某百分位（默认 10%），用于判定低速度。
- **pauses**：连续若干帧（默认 ≥ 3 帧）速度低于 `threshold` 的区间，记为停顿；每项含 `start_frame`, `end_frame`, `start_time`, `end_time`, `duration_frames`, `duration_sec`。

**学理对应**：程式化节奏与锣鼓、唱腔配合；停顿常对应「亮相」或段落的起止。

**输出位置**：`rhythm.speed_profile`，`rhythm.pauses`，`rhythm.rhythm_stats`（含 `n_pauses`, `total_pause_sec` 等）。

---

## 7. 身段段落（action_segments）

**定义**：在时间轴上根据**停顿**与**幅度变化**切分出的动作段。每段包含：

- **start_time**, **end_time**：秒。
- **mean_amplitude**：该段时间内全体 marker 位移均值的平均。
- **dominant_limb**：该段内平均位移最大的肢体类型（依 `classify_limb`）。

**学理对应**：与唱腔段落、曲牌/板式对照；可用于「唱做」段落一致性分析。

**输出位置**：`action_segments`（列表，每项为上述字段）。

---

## 8. 拉班近似特征（laban_approx）

**定义**：从轨迹与速度派生的、与拉班四要素（Body, Space, Effort, Shape）对应的近似标量，便于与舞蹈学/戏曲学界对话及风格化通道导出。本工具不实现完整拉班记谱，仅输出可计算指标。

- **Space（空间）**：重心在左右（span_left_right）、高低（span_high_low）、前后（span_forward_back）的跨度；重心移动平均速度（center_velocity_mean）。坐标轴依动捕约定（通常 X 左右、Y 高低、Z 前后）。
- **Effort（力效）**：全体 marker 速度的均值与标准差（mean_speed, std_speed）对应快/慢；加速度的均值与标准差（mean_acc, std_acc）对应轻/重。
- **Shape（形态）**：每帧重心到各 marker 的平均距离的均值与标准差（expansion_mean, expansion_std），表示身体扩展/收拢的程度与变化。

**学理对应**：拉班运动分析（LMA）中的 Space、Effort、Shape 要素；用于动作风格描述与跨剧目比较。

**输出位置**：`laban_approx` → `{ "space", "effort", "shape" }`，每子项为上述键值。

---

## 9. 参考文献与引用建议

- 京剧程式化、身段与水袖的学理表述可参见戏曲学与表演理论相关文献；本工具的实现与公式以本文档为准。
- 论文/报告中可写：「动捕程式化指标（幅度、圆顺度、程式化程度、肢体分类、节奏与身段段落、拉班近似特征）定义见开源项目 opera_mocap_tool 文档 `docs/opera_metrics.md`。」
