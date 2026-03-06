"""
商业模块包。

闭源商业模块 - 适用于TD/Blender艺术创作

包含：
- TD粒子系统
- Blender绑定工具
- 其他商业功能
"""

from opera_mocap_tool.commercial.td_particles import (
    ParticlePreset,
    EmitterShape,
    ParticleEmitter,
    ParticleSystem,
    TDParticleTransmitter,
    PresetLibrary,
    create_td_integration_module,
)

from opera_mocap_tool.commercial.blender_rig import (
    DangType,
    BodyPart,
    BoneDefinition,
    RigConfig,
    OperaRigBuilder,
    OperaMaterialLibrary,
    OperaAnimationLibrary,
)

from opera_mocap_tool.commercial.ai_motion import (
    MotionDataType,
    MotionSequence,
    TrainingConfig,
    MotionPreprocessor,
    MotionEncoder,
    MotionDecoder,
    OperaMotionVAE,
    StyleTransferModel,
    MotionGenerator,
    MotionTrainer,
)

__all__ = [
    # TD Particles
    "ParticlePreset",
    "EmitterShape",
    "ParticleEmitter",
    "ParticleSystem",
    "TDParticleTransmitter",
    "PresetLibrary",
    "create_td_integration_module",
    # Blender Rig
    "DangType",
    "BodyPart",
    "BoneDefinition",
    "RigConfig",
    "OperaRigBuilder",
    "OperaMaterialLibrary",
    "OperaAnimationLibrary",
    # AI Motion
    "MotionDataType",
    "MotionSequence",
    "TrainingConfig",
    "MotionPreprocessor",
    "MotionEncoder",
    "MotionDecoder",
    "OperaMotionVAE",
    "StyleTransferModel",
    "MotionGenerator",
    "MotionTrainer",
]
