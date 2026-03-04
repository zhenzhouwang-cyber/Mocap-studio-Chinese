"""分析模块：运动学、戏曲特征、节奏。"""

from .kinematic import compute_kinematics, compute_joint_angles, compute_joint_range_analysis, compute_left_right_symmetry
from .opera_features import compute_opera_features
from .rhythm import compute_rhythm
from .frequency import compute_frequency_analysis, compute_periodicity_metrics, detect_periodic_motions
from .quality import compute_jerk_analysis, compute_motion_start_end_analysis, compute_motion_quality_overall
from .balance import compute_center_of_mass, compute_balance_analysis, compute_stability_during_motion
from .segments import compute_action_segments, compute_motion_phases, detect_motion_boundaries
from .yunshou_features import analyze_yunshou, classify_dang_by_height, analyze_three_section_coordination, detect_fancheng_jin, compute_yunshou_circularity, quick_analyze
from .yunshou_art_mapping import map_to_touchdesigner, export_to_touchdesigner, create_touchdesigner_script, DANG_COLOR_PALETTES

__all__ = [
    "compute_kinematics",
    "compute_joint_angles", 
    "compute_joint_range_analysis",
    "compute_left_right_symmetry",
    "compute_opera_features",
    "compute_rhythm",
    "compute_frequency_analysis",
    "compute_periodicity_metrics",
    "detect_periodic_motions",
    "compute_jerk_analysis",
    "compute_motion_start_end_analysis",
    "compute_motion_quality_overall",
    "compute_center_of_mass",
    "compute_balance_analysis",
    "compute_stability_during_motion",
    "compute_action_segments",
    "compute_motion_phases",
    "detect_motion_boundaries",
    # 云手专项分析
    "analyze_yunshou",
    "classify_dang_by_height",
    "analyze_three_section_coordination",
    "detect_fancheng_jin",
    "compute_yunshou_circularity",
    "quick_analyze",
    # 云手生成艺术映射
    "map_to_touchdesigner",
    "export_to_touchdesigner",
    "create_touchdesigner_script",
    "DANG_COLOR_PALETTES",
]
