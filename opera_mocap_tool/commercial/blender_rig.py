"""
Blender 京剧角色绑定模块。

闭源商业模块 - 京剧角色智能绑定与动画工具

功能特性：
- 京剧专用骨骼系统
- 智能绑定工具
- 程式化动作库
- 脸谱/戏服材质库
- 导出工具
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class DangType(Enum):
    """京剧行当"""
    SHENG = "sheng"    # 生
    DAN = "dan"        # 旦
    JING = "jing"      # 净
    CHOU = "chou"     # 丑


class BodyPart(Enum):
    """身体部位"""
    HEAD = "head"
    TORSO = "torso"
    ARM_L = "arm_l"
    ARM_R = "arm_r"
    LEG_L = "leg_l"
    LEG_R = "leg_r"
    HAND_L = "hand_l"
    HAND_R = "hand_r"
    FOOT_L = "foot_l"
    FOOT_R = "foot_r"


@dataclass
class BoneDefinition:
    """骨骼定义"""
    name: str                          # 骨骼名称
    parent: str | None                 # 父骨骼
    head: tuple[float, float, float]   # 头部位置
    tail: tuple[float, float, float]   # 尾部位置
    roll: float = 0.0                  # 滚动角度
    connect_to_parent: bool = True     # 是否连接到父骨骼
    deform: bool = True                # 是否可变形


@dataclass
class RigConfig:
    """绑定配置"""
    dang: DangType = DangType.SHENG
    scale: float = 1.0                  # 缩放
    height: float = 1.7                 # 身高(米)
    gender: str = "male"                # 性别
    age_group: str = "adult"            # 年龄组
    
    # 骨骼名称前缀
    prefix_l: str = "L_"
    prefix_r: str = "R_"
    prefix_m: str = ""
    
    # 详细程度
    detail_level: str = "high"         # "low", "medium", "high"
    
    # 自定义参数
    custom_bones: dict = field(default_factory=dict)


class OperaRigBuilder:
    """京剧角色绑定构建器"""
    
    # 默认京剧骨骼结构
    DEFAULT_BONES = {
        # 脊椎
        "spine_base": BoneDefinition("spine_base", None, (0, 0, 0), (0, 0.2, 0)),
        "spine_mid": BoneDefinition("spine_mid", "spine_base", (0, 0.2, 0), (0, 0.5, 0)),
        "spine_upper": BoneDefinition("spine_upper", "spine_mid", (0, 0.5, 0), (0, 0.8, 0)),
        
        # 颈部
        "neck": BoneDefinition("neck", "spine_upper", (0, 0.8, 0), (0, 0.95, 0)),
        "head": BoneDefinition("head", "neck", (0, 0.95, 0), (0, 1.15, 0)),
        
        # 左手臂
        "shoulder_l": BoneDefinition("shoulder_l", "spine_upper", (-0.15, 0.75, 0), (-0.25, 0.75, 0)),
        "upper_arm_l": BoneDefinition("upper_arm_l", "shoulder_l", (-0.25, 0.75, 0), (-0.45, 0.65, 0)),
        "forearm_l": BoneDefinition("forearm_l", "upper_arm_l", (-0.45, 0.65, 0), (-0.65, 0.5, 0)),
        "hand_l": BoneDefinition("hand_l", "forearm_l", (-0.65, 0.5, 0), (-0.7, 0.5, 0)),
        
        # 右手臂
        "shoulder_r": BoneDefinition("shoulder_r", "spine_upper", (0.15, 0.75, 0), (0.25, 0.75, 0)),
        "upper_arm_r": BoneDefinition("upper_arm_r", "shoulder_r", (0.25, 0.75, 0), (0.45, 0.65, 0)),
        "forearm_r": BoneDefinition("forearm_r", "upper_arm_r", (0.45, 0.65, 0), (0.65, 0.5, 0)),
        "hand_r": BoneDefinition("hand_r", "forearm_r", (0.65, 0.5, 0), (0.7, 0.5, 0)),
        
        # 左腿
        "hip_l": BoneDefinition("hip_l", "spine_base", (-0.1, 0, 0), (-0.1, -0.1, 0)),
        "thigh_l": BoneDefinition("thigh_l", "hip_l", (-0.1, -0.1, 0), (-0.1, -0.45, 0)),
        "shin_l": BoneDefinition("shin_l", "thigh_l", (-0.1, -0.45, 0), (-0.1, -0.85, 0)),
        "foot_l": BoneDefinition("foot_l", "shin_l", (-0.1, -0.85, 0), (-0.1, -0.9, 0.1)),
        "toe_l": BoneDefinition("toe_l", "foot_l", (-0.1, -0.9, 0.1), (-0.1, -0.9, 0.15)),
        
        # 右腿
        "hip_r": BoneDefinition("hip_r", "spine_base", (0.1, 0, 0), (0.1, -0.1, 0)),
        "thigh_r": BoneDefinition("thigh_r", "hip_r", (0.1, -0.1, 0), (0.1, -0.45, 0)),
        "shin_r": BoneDefinition("shin_r", "thigh_r", (0.1, -0.45, 0), (0.1, -0.85, 0)),
        "foot_r": BoneDefinition("foot_r", "shin_r", (0.1, -0.85, 0), (0.1, -0.9, 0.1)),
        "toe_r": BoneDefinition("toe_r", "foot_r", (0.1, -0.9, 0.1), (0.1, -0.9, 0.15)),
    }
    
    # 京剧特有骨骼（翎子、髯口、甩袖等）
    OPERA_SPECIFIC_BONES = {
        # 翎子
        "feather_l": BoneDefinition("feather_l", "head", (0, 1.1, -0.05), (0, 1.5, -0.15)),
        "feather_r": BoneDefinition("feather_r", "head", (0, 1.1, -0.05), (0, 1.5, -0.15)),
        
        # 髯口
        "beard_main": BoneDefinition("beard_main", "head", (0, 0.9, 0.05), (0, 0.7, 0.1)),
        "beard_l": BoneDefinition("beard_l", "beard_main", (0, 0.85, 0.08), (-0.15, 0.6, 0.12)),
        "beard_r": BoneDefinition("beard_r", "beard_main", (0, 0.85, 0.08), (0.15, 0.6, 0.12)),
        
        # 水袖
        "sleeve_l": BoneDefinition("sleeve_l", "hand_l", (-0.7, 0.5, 0), (-0.85, 0.3, 0.1)),
        "sleeve_r": BoneDefinition("sleeve_r", "hand_r", (0.7, 0.5, 0), (0.85, 0.3, 0.1)),
        
        # 靠旗
        "banner_l": BoneDefinition("banner_l", "spine_upper", (-0.2, 0.75, -0.1), (-0.4, 0.5, -0.3)),
        "banner_r": BoneDefinition("banner_r", "spine_upper", (0.2, 0.75, -0.1), (0.4, 0.5, -0.3)),
        
        # 帽翅
        "hat_l": BoneDefinition("hat_l", "head", (0, 1.15, 0), (0.15, 1.25, 0)),
        "hat_r": BoneDefinition("hat_r", "head", (0, 1.15, 0), (-0.15, 1.25, 0)),
    }
    
    def __init__(self, config: RigConfig | None = None):
        self.config = config or RigConfig()
        self.bones: dict[str, BoneDefinition] = {}
    
    def build_base_rig(self) -> dict[str, BoneDefinition]:
        """构建基础骨架"""
        scale = self.config.scale
        
        # 复制并缩放骨骼
        for name, bone in self.DEFAULT_BONES.items():
            scaled_bone = BoneDefinition(
                name=name,
                parent=bone.parent,
                head=tuple(h * scale for h in bone.head),
                tail=tuple(t * scale for t in bone.tail),
                roll=bone.roll,
                connect_to_parent=bone.connect_to_parent,
                deform=bone.deform,
            )
            self.bones[name] = scaled_bone
        
        # 根据身高调整
        if self.config.height != 1.7:
            height_ratio = self.config.height / 1.7
            for bone in self.bones.values():
                bone.head = tuple(h * height_ratio for h in bone.head)
                bone.tail = tuple(t * height_ratio for t in bone.tail)
        
        return self.bones
    
    def add_opera_bones(self) -> dict[str, BoneDefinition]:
        """添加京剧特有骨骼"""
        if not self.bones:
            self.build_base_rig()
        
        for name, bone in self.OPERA_SPECIFIC_BONES.items():
            self.bones[name] = bone
        
        return self.bones
    
    def apply_naming_convention(self) -> dict[str, BoneDefinition]:
        """应用命名规范"""
        prefix_map = {
            "L_": self.config.prefix_l,
            "R_": self.config.prefix_r,
            "": self.config.prefix_m,
        }
        
        new_bones = {}
        for name, bone in self.bones.items():
            # 应用前缀
            for old_prefix, new_prefix in prefix_map.items():
                if name.startswith(old_prefix):
                    new_name = name.replace(old_prefix, new_prefix, 1)
                    break
            else:
                new_name = name
            
            new_bones[new_name] = bone
        
        self.bones = new_bones
        return self.bones
    
    def export_to_blender(self, output_path: str | Path) -> dict[str, Any]:
        """导出为Blender可用的Python脚本"""
        output_path = Path(output_path)
        
        # 生成Blender Python脚本
        script = self._generate_blender_script()
        
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(script)
        
        return {
            "path": str(output_path),
            "bone_count": len(self.bones),
            "dang": self.config.dang.value,
        }
    
    def _generate_blender_script(self) -> str:
        """生成Blender Python脚本"""
        # 骨骼数据JSON
        bones_json = json.dumps({
            name: {
                "parent": bone.parent,
                "head": bone.head,
                "tail": bone.tail,
                "roll": bone.roll,
                "connect": bone.connect_to_parent,
                "deform": bone.deform,
            }
            for name, bone in self.bones.items()
        }, indent=2)
        
        script = f'''"""
Opera Rig Generator for Blender
Generated by Opera Mocap Tool
"""
import bpy
import json

# Bone definitions
BONES_DATA = {bones_json}

def create_opera_rig():
    """Create opera character rig"""
    
    # Create armature
    bpy.ops.object.armature_add(enter_editmode=True, location=(0, 0, 0))
    arm = bpy.context.object
    arm.name = "OperaRig_{dang}"
    
    # Get edit bones
    ebones = arm.data.edit_bones
    
    # Create bones
    for bone_name, bone_data in BONES_DATA.items():
        if bone_name in ebones:
            continue
            
        # Create bone
        ebones.new(bone_name)
        bone = ebones[bone_name]
        
        # Set head and tail
        bone.head = bone_data["head"]
        bone.tail = bone_data["tail"]
        bone.roll = bone_data["roll"]
        
        # Set parent
        if bone_data["parent"] and bone_data["parent"] in ebones:
            bone.parent = ebones[bone_data["parent"]]
            bone.use_connect = bone_data["connect"]
        
        # Set deform
        bone.use_deform = bone_data["deform"]
    
    # Return to object mode
    bpy.ops.object.mode_set(mode='OBJECT')
    
    return arm

if __name__ == "__main__":
    create_opera_rig()
'''
        return script
    
    def export_to_json(self, output_path: str | Path) -> dict[str, Any]:
        """导出为JSON格式"""
        output_path = Path(output_path)
        
        data = {
            "config": {
                "dang": self.config.dang.value,
                "scale": self.config.scale,
                "height": self.config.height,
                "gender": self.config.gender,
                "age_group": self.config.age_group,
            },
            "bones": {
                name: {
                    "parent": bone.parent,
                    "head": bone.head,
                    "tail": bone.tail,
                    "roll": bone.roll,
                    "connect_to_parent": bone.connect_to_parent,
                    "deform": bone.deform,
                }
                for name, bone in self.bones.items()
            },
        }
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        
        return {"path": str(output_path), "bone_count": len(self.bones)}


class OperaMaterialLibrary:
    """京剧材质库"""
    
    # 预设材质
    MATERIALS = {
        # 脸谱
        "face_red": {    # 关公
            "base_color": (0.8, 0.1, 0.1, 1.0),
            "roughness": 0.3,
        },
        "face_white": {  # 曹操
            "base_color": (0.95, 0.95, 0.95, 1.0),
            "roughness": 0.2,
        },
        "face_black": {  # 张飞
            "base_color": (0.1, 0.1, 0.1, 1.0),
            "roughness": 0.4,
        },
        "face_green": {  # 绿脸
            "base_color": (0.2, 0.6, 0.2, 1.0),
            "roughness": 0.3,
        },
        
        # 戏服
        "costume_red": {
            "base_color": (0.7, 0.1, 0.1, 1.0),
            "roughness": 0.6,
        },
        "costume_gold": {
            "base_color": (0.85, 0.65, 0.2, 1.0),
            "roughness": 0.3,
            "metallic": 0.8,
        },
        "costume_blue": {
            "base_color": (0.1, 0.2, 0.6, 1.0),
            "roughness": 0.5,
        },
        
        # 头饰
        "hat_gold": {
            "base_color": (0.9, 0.75, 0.2, 1.0),
            "metallic": 0.9,
            "roughness": 0.2,
        },
        "feather": {
            "base_color": (0.1, 0.4, 0.8, 1.0),
            "roughness": 0.4,
        },
    }
    
    @classmethod
    def get_material(cls, name: str) -> dict | None:
        """获取材质预设"""
        return cls.MATERIALS.get(name)
    
    @classmethod
    def export_to_blender(cls, output_path: str | Path) -> str:
        """导出材质库为Blender脚本"""
        materials_json = json.dumps(cls.MATERIALS, indent=2)
        
        script = f'''
"""
Opera Materials for Blender
"""
import bpy

MATERIALS_DATA = {materials_json}

def create_materials():
    """Create opera materials"""
    
    for mat_name, mat_data in MATERIALS_DATA.items():
        # Create material
        mat = bpy.data.materials.new(name=mat_name)
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links
        
        # Clear default nodes
        nodes.clear()
        
        # Create nodes
        output = nodes.new('ShaderNodeOutputMaterial')
        bsdf = nodes.new('ShaderNodeBsdfPrincipled')
        
        # Set properties
        bsdf.inputs['Base Color'].default_value = mat_data.get('base_color', (0.8, 0.8, 0.8, 1.0))
        bsdf.inputs['Roughness'].default_value = mat_data.get('roughness', 0.5)
        bsdf.inputs['Metallic'].default_value = mat_data.get('metallic', 0.0)
        
        # Link nodes
        links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])
        
        # Position nodes
        output.location = (300, 0)
        bsdf.location = (0, 0)
    
    return len(MATERIALS_DATA)

if __name__ == "__main__":
    create_materials()
'''
        
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(script)
        
        return str(output_path)


class OperaAnimationLibrary:
    """京剧程式化动作库"""
    
    # 程式化动作定义
    ANIMATIONS = {
        # 云手系列
        "yunshou_basic": {
            "description": "基本云手",
            "difficulty": 1,
            "dang": ["sheng", "dan"],
            "duration_frames": 60,
            "key_poses": [
                {"frame": 0, "pose": "ready"},
                {"frame": 15, "pose": "yi1"},
                {"frame": 30, "pose": "er1"},
                {"frame": 45, "pose": "san1"},
                {"frame": 60, "pose": "complete"},
            ],
        },
        "yunshou_large": {
            "description": "大云手",
            "difficulty": 2,
            "dang": ["sheng", "dan"],
            "duration_frames": 90,
        },
        
        # 亮相系列
        "liangxiang_ding": {
            "description": "丁字步亮相",
            "difficulty": 1,
            "dang": ["sheng", "dan", "jing"],
            "duration_frames": 30,
        },
        "liangxiang_qi": {
            "description": "骑马式亮相",
            "difficulty": 2,
            "dang": ["jing"],
            "duration_frames": 30,
        },
        
        # 手眼身法步
        "shouyan": {
            "description": "手眼训练",
            "difficulty": 1,
            "dang": ["dan"],
            "duration_frames": 45,
        },
        "shenfa": {
            "description": "身法训练",
            "difficulty": 2,
            "dang": ["sheng", "dan"],
            "duration_frames": 60,
        },
        
        # 水袖
        "shuixiu_chong": {
            "description": "水袖冲",
            "difficulty": 3,
            "dang": ["dan"],
            "duration_frames": 40,
        },
        "shuixiu_feng": {
            "description": "水袖风",
            "difficulty": 3,
            "dang": ["dan"],
            "duration_frames": 50,
        },
    }
    
    @classmethod
    def get_animation(cls, name: str) -> dict | None:
        """获取动作预设"""
        return cls.ANIMATIONS.get(name)
    
    @classmethod
    def list_by_dang(cls, dang: str) -> list[dict]:
        """按行当列出动作"""
        result = []
        for name, anim in cls.ANIMATIONS.items():
            if dang in anim.get("dang", []):
                result.append({
                    "name": name,
                    "description": anim["description"],
                    "difficulty": anim["difficulty"],
                    "duration_frames": anim["duration_frames"],
                })
        return result
    
    @classmethod
    def export_library(cls, output_path: str | Path) -> dict[str, Any]:
        """导出动作库"""
        output_path = Path(output_path)
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(cls.ANIMATIONS, f, ensure_ascii=False, indent=2)
        
        return {
            "path": str(output_path),
            "animation_count": len(cls.ANIMATIONS),
        }


# 导出接口
__all__ = [
    "DangType",
    "BodyPart",
    "BoneDefinition",
    "RigConfig",
    "OperaRigBuilder",
    "OperaMaterialLibrary",
    "OperaAnimationLibrary",
]
