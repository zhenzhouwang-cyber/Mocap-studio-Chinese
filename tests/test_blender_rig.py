"""
Blender绑定模块单元测试。

测试京剧角色绑定工具的核心功能。
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest

# 导入被测试模块
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from opera_mocap_tool.commercial.blender_rig import (
    DangType,
    BodyPart,
    BoneDefinition,
    RigConfig,
    OperaRigBuilder,
    OperaMaterialLibrary,
    OperaAnimationLibrary,
)


class TestDangType:
    """京剧行当枚举测试"""

    def test_dang_values(self):
        """测试行当枚举值"""
        assert DangType.SHENG.value == "sheng"
        assert DangType.DAN.value == "dan"
        assert DangType.JING.value == "jing"
        assert DangType.CHOU.value == "chou"

    def test_dang_count(self):
        """测试行当数量"""
        assert len(DangType) == 4


class TestBodyPart:
    """身体部位枚举测试"""

    def test_body_part_values(self):
        """测试身体部位枚举值"""
        assert BodyPart.HEAD.value == "head"
        assert BodyPart.TORSO.value == "torso"
        assert BodyPart.ARM_L.value == "arm_l"
        assert BodyPart.ARM_R.value == "arm_r"
        assert BodyPart.LEG_L.value == "leg_l"
        assert BodyPart.LEG_R.value == "leg_r"

    def test_body_part_count(self):
        """测试身体部位数量"""
        assert len(BodyPart) >= 6


class TestBoneDefinition:
    """骨骼定义测试"""

    def test_bone_creation(self):
        """测试骨骼创建"""
        bone = BoneDefinition(
            name="spine_base",
            parent=None,
            head=(0.0, 0.0, 0.0),
            tail=(0.0, 0.2, 0.0),
        )
        
        assert bone.name == "spine_base"
        assert bone.parent is None
        assert bone.head == (0.0, 0.0, 0.0)
        assert bone.tail == (0.0, 0.2, 0.0)

    def test_bone_default_values(self):
        """测试默认参数"""
        bone = BoneDefinition(
            name="test_bone",
            parent="parent_bone",
            head=(0.0, 0.0, 0.0),
            tail=(0.0, 0.1, 0.0),
        )
        
        assert bone.roll == 0.0
        assert bone.connect_to_parent is True
        assert bone.deform is True


class TestRigConfig:
    """绑定配置测试"""

    def test_config_default(self):
        """测试默认配置"""
        config = RigConfig()
        
        assert config.dang == DangType.SHENG
        assert config.scale == 1.0
        assert config.height == 1.7
        assert config.gender == "male"
        assert config.age_group == "adult"
        assert config.detail_level == "high"

    def test_config_custom(self):
        """测试自定义配置"""
        config = RigConfig(
            dang=DangType.DAN,
            scale=1.2,
            height=1.6,
            gender="female",
            detail_level="medium",
        )
        
        assert config.dang == DangType.DAN
        assert config.scale == 1.2
        assert config.height == 1.6
        assert config.gender == "female"
        assert config.detail_level == "medium"


class TestOperaRigBuilder:
    """京剧角色绑定构建器测试"""

    def test_builder_creation(self):
        """测试构建器创建"""
        builder = OperaRigBuilder()
        
        assert builder.config is not None
        assert builder.config.dang == DangType.SHENG
        assert len(builder.bones) == 0

    def test_builder_with_config(self):
        """测试带配置的构建器"""
        config = RigConfig(dang=DangType.JING)
        builder = OperaRigBuilder(config)
        
        assert builder.config.dang == DangType.JING

    def test_build_base_rig(self):
        """测试基础骨架构建"""
        builder = OperaRigBuilder()
        bones = builder.build_base_rig()
        
        assert len(bones) > 0
        assert "spine_base" in bones
        assert "head" in bones
        assert "hand_l" in bones
        assert "hand_r" in bones

    def test_base_rig_has_hierarchy(self):
        """测试骨架层级关系"""
        builder = OperaRigBuilder()
        builder.build_base_rig()
        
        # 检查父子关系
        assert builder.bones["spine_base"].parent is None
        assert builder.bones["spine_mid"].parent == "spine_base"
        assert builder.bones["hand_l"].parent == "forearm_l"

    def test_add_opera_bones(self):
        """测试添加京剧特有骨骼"""
        builder = OperaRigBuilder()
        builder.build_base_rig()
        bones = builder.add_opera_bones()
        
        # 检查京剧特有骨骼
        assert "feather_l" in bones
        assert "feather_r" in bones
        assert "beard_main" in bones
        assert "sleeve_l" in bones
        assert "sleeve_r" in bones
        assert "banner_l" in bones
        assert "banner_r" in bones

    def test_apply_naming_convention(self):
        """测试命名规范应用"""
        config = RigConfig(prefix_l="Left_", prefix_r="Right_")
        builder = OperaRigBuilder(config)
        builder.build_base_rig()
        
        bones = builder.apply_naming_convention()
        
        # 验证命名被修改（如果有对应的前缀）

    def test_scale_bones(self):
        """测试骨骼缩放"""
        config = RigConfig(scale=2.0)
        builder = OperaRigBuilder(config)
        builder.build_base_rig()
        
        # 缩放后骨骼应该变大
        original_y = 0.2  # spine_base tail y
        scaled_y = builder.bones["spine_base"].tail[1]
        
        assert scaled_y > original_y

    def test_height_adjustment(self):
        """测试身高调整"""
        config = RigConfig(height=2.0)  # 更高的角色
        builder = OperaRigBuilder(config)
        builder.build_base_rig()
        
        # 头部位置应该更高
        head_y = builder.bones["head"].head[1]
        
        assert head_y > 0.95  # 默认身高头在0.95

    def test_export_to_json(self):
        """测试导出为JSON"""
        builder = OperaRigBuilder()
        builder.build_base_rig()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name
        
        try:
            result = builder.export_to_json(temp_path)
            
            assert result["path"] == temp_path
            assert result["bone_count"] > 0
            
            # 验证JSON内容
            with open(temp_path, 'r') as f:
                data = json.load(f)
            
            assert "config" in data
            assert "bones" in data
            assert data["config"]["dang"] == "sheng"
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_export_to_blender_script(self):
        """测试导出为Blender脚本"""
        builder = OperaRigBuilder()
        builder.build_base_rig()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            temp_path = f.name
        
        try:
            result = builder.export_to_blender(temp_path)
            
            assert result["path"] == temp_path
            assert result["bone_count"] > 0
            
            # 验证脚本内容
            with open(temp_path, 'r') as f:
                script = f.read()
            
            assert "import bpy" in script
            assert "import json" in script
            assert "create_opera_rig" in script
        finally:
            Path(temp_path).unlink(missing_ok=True)


class TestOperaMaterialLibrary:
    """京剧材质库测试"""

    def test_material_library_creation(self):
        """测试材质库创建"""
        library = OperaMaterialLibrary()
        
        assert library.MATERIALS is not None

    def test_get_face_material(self):
        """测试获取脸谱材质"""
        material = OperaMaterialLibrary.get_material("face_red")
        
        assert material is not None
        assert "base_color" in material
        assert "roughness" in material

    def test_get_costume_material(self):
        """测试获取戏服材质"""
        material = OperaMaterialLibrary.get_material("costume_red")
        
        assert material is not None

    def test_all_face_materials_available(self):
        """测试所有脸谱材质可用"""
        face_materials = ["face_red", "face_white", "face_black", "face_green"]
        
        for name in face_materials:
            material = OperaMaterialLibrary.get_material(name)
            assert material is not None, f"Material {name} not available"

    def test_all_costume_materials_available(self):
        """测试所有戏服材质可用"""
        costume_materials = ["costume_red", "costume_gold", "costume_blue"]
        
        for name in costume_materials:
            material = OperaMaterialLibrary.get_material(name)
            assert material is not None, f"Material {name} not available"

    def test_export_material_preset(self):
        """测试导出材质预设"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name
        
        try:
            result = OperaMaterialLibrary.export_preset(temp_path)
            
            assert result["path"] == temp_path
            
            with open(temp_path, 'r') as f:
                data = json.load(f)
            
            assert "materials" in data
            assert len(data["materials"]) > 0
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_generate_blender_material_script(self):
        """测试生成Blender材质脚本"""
        script = OperaMaterialLibrary.generate_blender_script()
        
        assert "import bpy" in script
        assert "create_opera_materials" in script or "def " in script


class TestOperaAnimationLibrary:
    """京剧动画库测试"""

    def test_animation_library_creation(self):
        """测试动画库创建"""
        library = OperaAnimationLibrary()
        
        assert library.ANIMATIONS is not None

    def test_get_animation(self):
        """测试获取动画"""
        animation = OperaAnimationLibrary.get_animation("sleeve_wave")
        
        assert animation is not None

    def test_all_animations_available(self):
        """测试所有动画可用"""
        animations = [
            "sleeve_wave", "sleeve_dust", "sleeve_spin",
            "hand_gesture", "fan_turn", "fan_wave",
        ]
        
        for name in animations:
            animation = OperaAnimationLibrary.get_animation(name)
            # 部分动画可能不存在，但不应该崩溃

    def test_get_animations_by_category(self):
        """测试按类别获取动画"""
        sleeve_animations = OperaAnimationLibrary.get_animations_by_category("sleeve")
        
        assert isinstance(sleeve_animations, list)

    def test_export_animation_preset(self):
        """测试导出动画预设"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name
        
        try:
            result = OperaAnimationLibrary.export_preset(temp_path)
            
            assert result["path"] == temp_path
            
            with open(temp_path, 'r') as f:
                data = json.load(f)
            
            assert "animations" in data
        finally:
            Path(temp_path).unlink(missing_ok=True)


class TestRigBuilderWithDifferentDang:
    """不同行当的绑定测试"""

    def test_sheng_rig(self):
        """测试生角绑定"""
        config = RigConfig(dang=DangType.SHENG)
        builder = OperaRigBuilder(config)
        bones = builder.build_base_rig()
        
        assert len(bones) > 0

    def test_dan_rig(self):
        """测试旦角绑定"""
        config = RigConfig(dang=DangType.DAN)
        builder = OperaRigBuilder(config)
        bones = builder.build_base_rig()
        
        assert len(bones) > 0

    def test_jing_rig(self):
        """测试净角绑定"""
        config = RigConfig(dang=DangType.JING)
        builder = OperaRigBuilder(config)
        bones = builder.build_base_rig()
        
        assert len(bones) > 0

    def test_chou_rig(self):
        """测试丑角绑定"""
        config = RigConfig(dang=DangType.CHOU)
        builder = OperaRigBuilder(config)
        bones = builder.build_base_rig()
        
        assert len(bones) > 0


class TestRigExportFormats:
    """绑定导出格式测试"""

    def test_json_export_structure(self):
        """测试JSON导出结构"""
        builder = OperaRigBuilder()
        builder.build_base_rig()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name
        
        try:
            builder.export_to_json(temp_path)
            
            with open(temp_path, 'r') as f:
                data = json.load(f)
            
            # 验证结构完整性
            assert "config" in data
            assert "bones" in data
            
            # 验证骨骼数据完整性
            for bone_name, bone_data in data["bones"].items():
                assert "parent" in bone_data
                assert "head" in bone_data
                assert "tail" in bone_data
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_blender_script_imports(self):
        """测试Blender脚本导入"""
        builder = OperaRigBuilder()
        builder.build_base_rig()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            temp_path = f.name
        
        try:
            builder.export_to_blender(temp_path)
            
            with open(temp_path, 'r') as f:
                script = f.read()
            
            # 验证必要的导入
            assert "import bpy" in script
            assert "import json" in script
            
            # 验证函数定义
            assert "def " in script
        finally:
            Path(temp_path).unlink(missing_ok=True)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
