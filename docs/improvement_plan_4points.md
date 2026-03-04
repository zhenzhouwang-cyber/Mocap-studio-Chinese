# 四项改进方案说明

## 1. 3D 动捕查看器优化（Blender 式视窗）

**现状问题**：播放时无法调整视角；坐标轴仍有跳动；Plotly 3D 在 Streamlit 内交互受限。

**方案**：将 3D 查看器改为**独立 HTML 页面**，使用 **Three.js** 实现 Blender 式交互：

- **可旋转/缩放/平移**：鼠标拖拽旋转、滚轮缩放、右键平移，播放时也可操作
- **固定世界边界**：预计算全序列 AABB，渲染固定线框或地面网格，不随动作缩放
- **突出动画**：时间轴 + 播放/暂停，帧率可调，可选显示骨骼/点/轨迹尾迹
- **集成方式**：在 GUI 中增加「在新窗口打开 3D 查看器」按钮，导出当前动捕为 JSON，打开 `viewer_standalone.html` 加载并渲染；或使用 `st.components.v1.html()` 嵌入（部分环境可能限制交互）

**实施步骤**：
1. 新增 `opera_mocap_tool/static/viewer_standalone.html`：Three.js 骨架渲染 + OrbitControls + 固定场景范围
2. 新增导出接口：将 MocapData 转为 JSON（markers 按帧、skeleton segments）
3. GUI 增加「打开独立 3D 查看器」按钮，写入临时 JSON 并打开 HTML（或提供下载链接）

---

## 2. 参考比对支持 FBX 与视频

**FBX**：✅ 已实现。参考动作上传器已支持 `c3d, csv, fbx`；FBX 需填写 Blender 路径。

**视频**：需通过**姿态估计**从视频提取骨骼数据，再转为 MocapData 参与比对。

- **可选方案**：MediaPipe Pose、OpenPose、MMPose 等
- **流程**：上传视频 → 逐帧姿态估计 → 输出关节 2D/3D 坐标 → 转为 timeseries 格式 → 与动捕做 DTW 比对
- **注意**：视频姿态多为 2D 或弱 3D，与光学动捕精度不同，比对结果需标注「来源：视频姿态估计」

**实施步骤**：
1. ~~参考比对：`type=["c3d", "csv", "fbx"]`~~ ✅ 已完成
2. 视频支持（计划中）：新增 `opera_mocap_tool/io/video_pose.py`，用 MediaPipe 提取姿态，输出 MocapData 兼容结构；GUI 参考上传增加 `mp4, avi, mov`，内部调用 video_pose 后走现有比对流程

---

## 3. 身段/肢体分类依据说明

**分类依据**：按 **marker 名称中的关键词** 推断肢体类型，**不是**按 marker 点数。

| 肢体类型 | 中文 | 关键词（英文/中文） | 说明 |
|----------|------|---------------------|------|
| upper_extremity | 上肢末端 | wrist, hand, finger, 袖, 手 | 腕、手、手指、水袖相关 |
| upper_limb | 上肢 | elbow, shoulder, arm, 臂, 肘 | 肘、肩、上臂 |
| lower_limb | 下肢 | knee, ankle, foot, toe, 膝, 脚 | 膝、踝、脚、脚趾 |
| trunk | 躯干 | head, spine, pelvis, 头, 脊, 腰 | 头、脊柱、骨盆 |
| unknown | 其他 | 未匹配以上 | 无法从名称推断的 marker |

**流程**：对每个 marker 名称调用 `classify_limb(marker_name)`，返回上述类型之一；再统计各类型的 **marker 数量**，即表格中的「Marker 数」。

**示例**：`Daphnee:WRIST` 含 "wrist" → upper_extremity；`Daphnee:DELT` 无匹配 → unknown（可后续补充 shoulder/delt 等关键词）。

**后续**：您提供 Vicon 标准 marker 模板后，可扩展 `classify_limb` 的规则或改为查表映射，使分类更贴合实际骨骼命名。

---

## 4. 基于动捕的数字艺术 Demo

**目标**：用分析数据与动捕数据做简易数字艺术 Demo，保留中国传统戏曲的程式化、美学特征。

**素材**：`E:\coursor\project\舞蹈动作-科目三\科目三.bvh`（科目三舞步，非戏曲，暂代用）。

**实施步骤**：
1. **BVH 加载**：Demo 直接使用 Three.js BVHLoader 加载 BVH，无需 Python 转换
2. **Demo 形式**：✅ 已实现。`舞蹈动作-科目三/art_demo.html`：Three.js 渲染骨架动画 + 程式化视觉（红金骨骼、粒子氛围、墨色背景、地面网格）
3. **运行**：在 `舞蹈动作-科目三` 目录执行 `python -m http.server 8000`，访问 http://localhost:8000/art_demo.html

---

*文档版本：基于当前需求整理；具体实现以代码为准。*
