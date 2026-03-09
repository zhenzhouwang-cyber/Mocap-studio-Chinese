"""
实时Pipeline模块。

提供京剧动捕数据的实时采集、处理和发送到TouchDesigner/Unreal Engine 5的功能。

主要功能:
- Vicon实时数据采集
- 实时骨架处理
- 动作平滑滤波
- TouchDesigner数据发送
- Unreal Engine 5数据发送

快速开始:

```python
from opera_mocap_tool.realtime import create_pipeline

# 创建Pipeline
pipeline = create_pipeline(
    vicon_host="localhost",
    td_enabled=True,
    ue5_enabled=True,
)

# 启动
pipeline.connect()
pipeline.start()

# 运行一段时间后停止
import time
time.sleep(60)
pipeline.stop()
pipeline.disconnect()

# 查看统计
print(pipeline.get_stats())
```
"""

from __future__ import annotations

from opera_mocap_tool.realtime.vicon_client import (
    ViconClient,
    ViconConfig,
    ViconFrame,
    create_vicon_client,
)

from opera_mocap_tool.realtime.skeleton_realtime import (
    RealtimeSkeleton,
    SkeletonData,
    JointData,
    STANDARD_JOINTS,
    create_standard_skeleton,
)

from opera_mocap_tool.realtime.filters import (
    RealtimeFilter,
    FilterConfig,
    MotionSmoother,
    create_filter,
    create_smoother,
)

from opera_mocap_tool.realtime.td_sender import (
    TDSender,
    TDDatSender,
    TDConfig,
    create_td_sender,
)

from opera_mocap_tool.realtime.ue5_sender import (
    UE5Sender,
    UE5Config,
    LiveLinkBridge,
    create_ue5_sender,
)

from opera_mocap_tool.realtime.pipeline import (
    RealtimePipeline,
    PipelineConfig,
    PipelineStats,
    create_pipeline,
)

__all__ = [
    # Vicon客户端
    "ViconClient",
    "ViconConfig", 
    "ViconFrame",
    "create_vicon_client",
    
    # 骨架处理
    "RealtimeSkeleton",
    "SkeletonData",
    "JointData",
    "STANDARD_JOINTS",
    "create_standard_skeleton",
    
    # 滤波
    "RealtimeFilter",
    "FilterConfig",
    "MotionSmoother",
    "create_filter",
    "create_smoother",
    
    # TD发送器
    "TDSender",
    "TDDatSender",
    "TDConfig",
    "create_td_sender",
    
    # UE5发送器
    "UE5Sender",
    "UE5Config",
    "LiveLinkBridge",
    "create_ue5_sender",
    
    # Pipeline
    "RealtimePipeline",
    "PipelineConfig",
    "PipelineStats",
    "create_pipeline",
]
