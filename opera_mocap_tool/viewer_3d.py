"""Three.js 3D 动捕查看器：Blender 式视窗，固定坐标轴，播放时可旋转/缩放。"""

from __future__ import annotations

import json
import math
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .io.base import MocapData

# Three.js CDN（UMD 构建，兼容 file://）
THREE_JS_URL = "https://unpkg.com/three@0.132.0/build/three.min.js"
ORBIT_CONTROLS_URL = "https://unpkg.com/three@0.132.0/examples/js/controls/OrbitControls.js"
GLTF_LOADER_URL = "https://unpkg.com/three@0.132.0/examples/js/loaders/GLTFLoader.js"


def _apply_up_axis(x: float, y: float, z: float, up_axis: str) -> tuple[float, float, float]:
    """将数据坐标转为 Three.js 约定：Y 向上。up_axis 为 'z' 时 (x,y,z) -> (x, z, -y)。"""
    if up_axis == "z":
        return (float(x), float(z), float(-y))
    return (float(x), float(y), float(z))


def mocap_to_viewer_json(
    data: MocapData,
    *,
    marker_subset: list[str] | None = None,
    max_markers: int = 200,
    frame_step: int = 1,
    segments: list[tuple[str, str]] | None = None,
    up_axis: str = "z",
) -> dict:
    """
    将 MocapData 转为 Three.js 查看器所需的 JSON 结构。
    up_axis: 数据中的向上轴，'y' 不转换，'z' 时从 Z-up 转为 Y-up（骨骼站立）。
    """
    from .skeleton import get_skeleton_segments

    markers = data.markers
    labels = list(markers.keys())
    if marker_subset:
        labels = [m for m in labels if m in marker_subset]
    else:
        labels = labels[:max_markers]

    segs = segments if segments is not None else get_skeleton_segments(list(markers.keys()))

    frame_indices = list(range(0, data.n_frames, frame_step))
    if not frame_indices:
        frame_indices = [0]

    # 按帧组织：每帧 { "name": [x,y,z], ... }，已按 up_axis 转为 Three.js Y-up
    frames_data = []
    all_x, all_y, all_z = [], [], []
    for fi in frame_indices:
        frame_pts = {}
        for name in labels:
            pts = markers.get(name, [])
            if fi < len(pts):
                x, y, z = pts[fi]
                if math.isfinite(x) and math.isfinite(y) and math.isfinite(z):
                    tx, ty, tz = _apply_up_axis(x, y, z, up_axis)
                    frame_pts[name] = [tx, ty, tz]
                    all_x.append(tx)
                    all_y.append(ty)
                    all_z.append(tz)
        frames_data.append(frame_pts)

    if all_x and all_y and all_z:
        x_min, x_max = min(all_x), max(all_x)
        y_min, y_max = min(all_y), max(all_y)
        z_min, z_max = min(all_z), max(all_z)
        pad = max((x_max - x_min), (y_max - y_min), (z_max - z_min), 0.1) * 0.2
        bounds = {
            "x": [x_min - pad, x_max + pad],
            "y": [y_min - pad, y_max + pad],
            "z": [z_min - pad, z_max + pad],
        }
    else:
        bounds = {"x": [-1, 1], "y": [-1, 1], "z": [-1, 1]}

    return {
        "frames": frames_data,
        "labels": labels,
        "segments": [[a, b] for a, b in segs],
        "frameRate": data.frame_rate,
        "frameStep": frame_step,
        "nFrames": len(frames_data),
        "durationSec": data.duration_sec,
        "bounds": bounds,
    }


def build_3d_viewer_html(
    data: MocapData,
    *,
    marker_subset: list[str] | None = None,
    max_markers: int = 200,
    frame_step: int = 1,
    show_skeleton: bool = True,
    skeleton_segments: list[tuple[str, str]] | None = None,
    skin_bones: bool = True,
    trail_frames: int = 0,
    show_axes: bool = False,
    show_grid: bool = True,
    show_labels: bool = False,
    mixamo_glb_url: str | None = None,
    height: int = 600,
) -> str:
    """
    生成 Three.js 3D 查看器的完整 HTML 字符串，可嵌入 Streamlit 或单独打开。

    特性：固定坐标轴、OrbitControls、骨骼/蒙皮、视图预设与快捷键。
    mixamo_glb_url: 可选，Mixamo 导出的 GLB 地址；提供时启用蒙皮人形，用动捕驱动骨骼。
    """
    segs = skeleton_segments if show_skeleton and skeleton_segments else []
    payload = mocap_to_viewer_json(
        data,
        marker_subset=marker_subset,
        max_markers=max_markers,
        frame_step=frame_step,
        segments=segs if segs else None,
    )
    payload["skinBones"] = skin_bones
    payload["trailFrames"] = max(0, min(120, trail_frames))
    payload["showAxes"] = show_axes
    payload["showGrid"] = show_grid
    payload["showLabels"] = show_labels
    if mixamo_glb_url and mixamo_glb_url.strip():
        from .mixamo_retarget import build_mixamo_bone_mapping
        payload["mixamoGlbUrl"] = mixamo_glb_url.strip()
        payload["mixamoBoneMapping"] = build_mixamo_bone_mapping(segs, payload["labels"])
    else:
        payload["mixamoGlbUrl"] = None
        payload["mixamoBoneMapping"] = None
    json_str = json.dumps(payload, ensure_ascii=False)
    # 转义供嵌入 HTML script
    json_escaped = json_str.replace("</", "<\\/").replace("<!--", "<\\!--")

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>动捕 3D 查看器</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
html,body{{height:100%;background:#0c0c0f;color:#e2e8f0;font-family:'Segoe UI',system-ui,sans-serif;overflow:hidden}}
body{{display:flex;flex-direction:column}}
#viewport{{
  position:relative;flex:1;min-height:200px;
  background:#0c0c0f;
  display:flex;align-items:center;justify-content:center;
}}
#viewport.fullscreen{{position:fixed;inset:0;width:100%;height:100%;z-index:9999}}
#viewbox{{position:relative;flex-shrink:0;aspect-ratio:16/9;max-width:100%;max-height:100%}}
#canvas{{display:block;width:100%;height:100%}}
#ui{{
  position:fixed;bottom:0;left:0;right:0;
  padding:12px 20px 20px;
  background:linear-gradient(transparent,rgba(12,12,15,0.95));
  display:flex;align-items:center;gap:20px;flex-wrap:wrap
}}
.ui-group{{display:flex;align-items:center;gap:8px}}
.ui-group label{{font-size:12px;color:#94a3b8;min-width:28px}}
button{{
  background:#22c55e;border:none;color:#fff;padding:8px 16px;cursor:pointer;
  font-size:13px;border-radius:8px;transition:opacity 0.2s
}}
button:hover{{opacity:0.9}}
button.secondary{{background:#334155;color:#e2e8f0}}
#time{{min-width:100px;font-size:13px;font-variant-numeric:tabular-nums}}
input[type="range"]{{width:100px;accent-color:#22c55e;cursor:pointer}}
#timelineBar{{width:180px;height:10px;background:#334155;border-radius:5px;cursor:pointer;overflow:hidden}}
#timelineFill{{height:100%;background:#22c55e;border-radius:5px;transition:width 0.05s}}
#frameInput{{width:52px;padding:4px 6px;font-size:12px;background:#1e293b;border:1px solid #334155;border-radius:6px;color:#e2e8f0;text-align:center}}
#shortcuts{{font-size:11px;color:#64748b}}
</style>
</head>
<body>
<div id="viewport">
  <div id="viewbox">
    <canvas id="canvas"></canvas>
    <div id="jointTooltip" style="display:none;position:absolute;background:rgba(0,0,0,0.85);color:#e2e8f0;padding:4px 8px;border-radius:6px;font-size:12px;pointer-events:none;z-index:10"></div>
  </div>
</div>
<div id="ui">
  <div class="ui-group">
    <button id="btnPlay">▶ 播放</button>
    <button id="btnPause" class="secondary">⏸ 暂停</button>
  </div>
  <div class="ui-group">
    <span id="time">0.00 / 0.00 s</span>
  </div>
  <div class="ui-group">
    <label>时间轴</label>
    <div id="timelineBar" title="点击跳转"><div id="timelineFill"></div></div>
  </div>
  <div class="ui-group">
    <label>帧</label>
    <input type="range" id="frameSlider" min="0" max="1" value="0" style="width:120px">
  </div>
  <div class="ui-group">
    <label>帧号</label>
    <input type="number" id="frameInput" min="0" value="0" style="width:52px" title="输入后回车跳转">
  </div>
  <div class="ui-group">
    <label><input type="checkbox" id="loopCheck" checked> 循环</label>
  </div>
  <div class="ui-group">
    <label>速度</label>
    <input type="range" id="speed" min="0.25" max="2" step="0.25" value="1">
  </div>
  <div class="ui-group">
    <button type="button" id="btnFullscreen" class="secondary" title="全屏 (F11)">⛶ 全屏</button>
  </div>
  <div class="ui-group" id="shortcuts">空格 播放/暂停 · 1-4 视图 · F 聚焦 · R 重置</div>
</div>
<script src="{THREE_JS_URL}"></script>
<script src="{ORBIT_CONTROLS_URL}"></script>
<script src="{GLTF_LOADER_URL}"></script>
<script>
(function() {{
if (typeof THREE === 'undefined') {{
  document.body.innerHTML = '<div style="padding:2rem;color:#e74c3c">无法加载 Three.js。请通过 HTTP 访问。</div>';
  return;
}}
try {{
var PAYLOAD = {json_escaped};

var canvas = document.getElementById('canvas');
var viewportEl = document.getElementById('viewport');
var viewboxEl = document.getElementById('viewbox');
var btnPlay = document.getElementById('btnPlay');
var btnPause = document.getElementById('btnPause');
var timeEl = document.getElementById('time');
var speedInput = document.getElementById('speed');
var frameSlider = document.getElementById('frameSlider');
var timelineBar = document.getElementById('timelineBar');
var timelineFill = document.getElementById('timelineFill');
var frameInput = document.getElementById('frameInput');
var loopCheck = document.getElementById('loopCheck');
var btnFullscreen = document.getElementById('btnFullscreen');

var frames = PAYLOAD.frames, labels = PAYLOAD.labels, segments = PAYLOAD.segments;
var frameRate = PAYLOAD.frameRate, frameStep = PAYLOAD.frameStep, nFrames = PAYLOAD.nFrames;
var durationSec = PAYLOAD.durationSec, bounds = PAYLOAD.bounds;
var skinBones = PAYLOAD.skinBones !== false;
var trailFrames = Math.max(0, parseInt(PAYLOAD.trailFrames, 10) || 0);
var showAxes = PAYLOAD.showAxes === true;
var showGrid = PAYLOAD.showGrid !== false;
var showLabels = PAYLOAD.showLabels === true;
var mixamoGlbUrl = PAYLOAD.mixamoGlbUrl || null;
var mixamoMapping = PAYLOAD.mixamoBoneMapping || null;
var mixamoBones = mixamoMapping ? mixamoMapping.bones : null;
var mixamoSuffixMap = mixamoMapping ? mixamoMapping.suffixMap : {{}};
var useMixamo = !!(mixamoGlbUrl && mixamoBones && typeof THREE !== 'undefined');

var scene = new THREE.Scene();
scene.background = new THREE.Color(0x0c0c0f);

function getViewboxSize() {{
  var vp = viewportEl;
  var vpW = Math.max(vp ? vp.clientWidth : 0, 1);
  var vpH = Math.max(vp ? vp.clientHeight : 0, 1);
  var vbW = Math.min(vpW, Math.floor(vpH * 16 / 9));
  var vbH = Math.min(vpH, Math.floor(vpW * 9 / 16));
  return {{ w: vbW, h: vbH }};
}}
var _vb = getViewboxSize();
var camW = Math.max(_vb.w || 640, 1);
var camH = Math.max(_vb.h || 360, 1);
if (viewboxEl) {{ viewboxEl.style.width = camW + 'px'; viewboxEl.style.height = camH + 'px'; }}
var camera = new THREE.PerspectiveCamera(50, camW / camH, 0.1, 10000);
var cx = (bounds.x[0] + bounds.x[1]) / 2;
var cy = (bounds.y[0] + bounds.y[1]) / 2;
var cz = (bounds.z[0] + bounds.z[1]) / 2;
var r = Math.max(
  bounds.x[1]-bounds.x[0],
  bounds.y[1]-bounds.y[0],
  bounds.z[1]-bounds.z[0],
  1
) * 0.6;
camera.position.set(cx + r*1.2, cy + r*1.0, cz + r*1.2);
camera.lookAt(cx, cy, cz);

var renderer = new THREE.WebGLRenderer({{ canvas: canvas, antialias: true, alpha: false }});
renderer.setSize(camW, camH);
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.setClearColor(0x0c0c0f);
var gl = renderer.domElement;

var controls = new THREE.OrbitControls(camera, gl);
controls.target.set(cx, cy, cz);
controls.enableDamping = true;
controls.dampingFactor = 0.05;

// 视图预设（1前 2侧 3顶 4透视）与聚焦
var viewCenter = new THREE.Vector3(cx, cy, cz);
var viewRadius = r;
var initialPos = new THREE.Vector3(cx + r*1.2, cy + r*1.0, cz + r*1.2);
function setView(preset) {{
  controls.target.copy(viewCenter);
  if (preset === 1) {{ camera.position.set(cx + viewRadius, cy, cz); }}
  else if (preset === 2) {{ camera.position.set(cx, cy, cz + viewRadius); }}
  else if (preset === 3) {{ camera.position.set(cx, cy + viewRadius, cz); }}
  else {{ camera.position.copy(initialPos); }}
}}
function focusView() {{ setView(4); }}
function resetView() {{ camera.position.copy(initialPos); controls.target.copy(viewCenter); }}

// 光照（Meshy 风格：柔和环境光 + 主光源）
scene.add(new THREE.AmbientLight(0x404060, 0.6));
var dirLight = new THREE.DirectionalLight(0xffffff, 0.8);
dirLight.position.set(cx + r, cy + r*2, cz + r);
dirLight.castShadow = false;
scene.add(dirLight);

// 地面网格（可关）
var gridSize = Math.max(r * 2.5, 10);
var grid = new THREE.GridHelper(gridSize, 16, 0x1e293b, 0x0f172a);
grid.position.set(cx, bounds.y[0], cz);
grid.visible = showGrid;
scene.add(grid);

// 世界坐标轴（可选）
if (showAxes) {{
  var axesLen = r * 0.4;
  var axes = new THREE.AxesHelper(axesLen);
  axes.position.set(cx, cy, cz);
  scene.add(axes);
}}

// 骨骼：蒙皮模式用圆柱体，否则用线段
// 骨骼连线使用亮绿色，便于在深色背景下看清
var lineMat = new THREE.LineBasicMaterial({{ color: 0x4ade80, linewidth: 1 }});
let lineObj = null;
var boneCylinders = [];
var boneRadius = Math.min(Math.max(r * 0.004, 0.008), 0.05);
if (skinBones && segments.length > 0) {{
  var boneMat = new THREE.MeshLambertMaterial({{ color: 0x22c55e, flatShading: false }});
  var boneGeo = new THREE.CylinderGeometry(boneRadius, boneRadius, 1, 8);
  for (var s = 0; s < segments.length; s++) {{
    var cyl = new THREE.Mesh(boneGeo, boneMat);
    boneCylinders.push(cyl);
    scene.add(cyl);
  }}
}}

// 关节球体：按场景尺度比例，避免过大绿块（上限 0.08，下限 0.012）
var jointRadius = Math.min(Math.max(r * 0.006, 0.012), 0.08);
var sphereGeo = new THREE.SphereGeometry(jointRadius, 8, 6);
var sphereMat = new THREE.MeshBasicMaterial({{ color: 0x4ade80 }});
var jointMeshes = [];
for (var j = 0; j < labels.length; j++) {{
  var m = new THREE.Mesh(sphereGeo, sphereMat);
  jointMeshes.push(m);
  scene.add(m);
}}
var _v0 = new THREE.Vector3();
var _v1 = new THREE.Vector3();
var _mid = new THREE.Vector3();

// 轨迹尾迹（每关节一条线，最近 N 帧）
var trailPoints = [];
var trailLines = [];
if (trailFrames > 0 && labels.length > 0) {{
  var trailMat = new THREE.LineBasicMaterial({{ color: 0x22c55e, opacity: 0.5, transparent: true }});
  for (var ti = 0; ti < labels.length; ti++) {{
    trailPoints.push([]);
    var trailGeo = new THREE.BufferGeometry().setFromPoints([]);
    trailLines.push(new THREE.Line(trailGeo, trailMat));
    scene.add(trailLines[ti]);
  }}
}}

// 关节标签：悬停时 tooltip
var jointTooltip = document.getElementById('jointTooltip');
var raycaster = new THREE.Raycaster();
var mouse = new THREE.Vector2();
function onCanvasMouseMove(ev) {{
  if (!showLabels || !jointTooltip) return;
  var rect = canvas.getBoundingClientRect();
  mouse.x = ((ev.clientX - rect.left) / rect.width) * 2 - 1;
  mouse.y = -((ev.clientY - rect.top) / rect.height) * 2 + 1;
  raycaster.setFromCamera(mouse, camera);
  var hits = raycaster.intersectObjects(jointMeshes);
  if (hits.length > 0) {{
    var idx = jointMeshes.indexOf(hits[0].object);
    if (idx >= 0 && idx < labels.length) {{
      jointTooltip.textContent = labels[idx];
      jointTooltip.style.display = 'block';
      jointTooltip.style.left = (ev.clientX - rect.left + 12) + 'px';
      jointTooltip.style.top = (ev.clientY - rect.top) + 'px';
      return;
    }}
  }}
  jointTooltip.style.display = 'none';
}}
if (showLabels) {{ canvas.addEventListener('mousemove', onCanvasMouseMove); }}

// Mixamo 蒙皮：加载 GLB 与骨骼驱动
var mixamoModel = null;
var mixamoSkel = null;
var mixamoReady = false;
var _mxDir = new THREE.Vector3();
var _mxUp = new THREE.Vector3(0, 1, 0);
var _mxQuat = new THREE.Quaternion();
var _mxParentInv = new THREE.Quaternion();
var _mxPos = new THREE.Vector3();
var _mxLocalPos = new THREE.Vector3();

function _resolveMarkerName(glbBoneName) {{
  var suf = glbBoneName.replace(/^[^:]+:/, '').toLowerCase();
  var markerName = mixamoSuffixMap[suf];
  return markerName || null;
}}

function _findBoneMap(glbBoneName) {{
  var markerName = _resolveMarkerName(glbBoneName);
  if (markerName && mixamoBones[markerName]) return mixamoBones[markerName];
  if (mixamoBones[glbBoneName]) return mixamoBones[glbBoneName];
  var stripped = glbBoneName.replace(/^[^:]+:/, '');
  if (mixamoBones[stripped]) return mixamoBones[stripped];
  // Debug: log unmatched bones
  // console.log('Unmatched bone:', glbBoneName, 'markerName:', markerName, 'stripped:', stripped);
  return null;
}}

if (useMixamo && typeof THREE.GLTFLoader !== 'undefined') {{
  var loader = new THREE.GLTFLoader();
  loader.load(mixamoGlbUrl, function(gltf) {{
    mixamoModel = gltf.scene;
    mixamoModel.traverse(function(o) {{
      if (o.isSkinnedMesh && !mixamoSkel) {{
        mixamoSkel = o.skeleton;
        console.log('Found SkinnedMesh, skeleton bones:', mixamoSkel ? mixamoSkel.bones.length : 0);
      }}
    }});
    if (mixamoSkel) {{
      scene.add(mixamoModel);
      mixamoReady = true;
      console.log('Mixamo ready, bone mapping keys:', mixamoBones ? Object.keys(mixamoBones).length : 0);
      if (nFrames > 0) updateFrame(0);
    }} else {{
      console.warn('GLB 中未找到 SkinnedMesh/Skeleton');
    }}
  }}, undefined, function(err) {{ console.warn('Mixamo GLB 加载失败', err); }});
}}

function driveMixamoBones(frame) {{
  if (!mixamoSkel || !mixamoBones) return;
  var bones = mixamoSkel.bones;
  var driven = 0;
  for (var bi = 0; bi < bones.length; bi++) {{
    var bone = bones[bi];
    var map = _findBoneMap(bone.name);
    if (!map) continue;
    driven++;
    if (map.root) {{
      var pe = frame[map.end];
      if (!pe || pe.length < 3) continue;
      bone.position.set(pe[0], pe[1], pe[2]);
    }} else {{
      var ps = frame[map.start], pe = frame[map.end];
      if (!ps || !pe || ps.length < 3 || pe.length < 3) continue;
      _mxDir.set(pe[0]-ps[0], pe[1]-ps[1], pe[2]-ps[2]);
      var len = _mxDir.length();
      if (len < 1e-5) continue;
      _mxDir.divideScalar(len);
      _mxQuat.setFromUnitVectors(_mxUp, _mxDir);
      _mxPos.set(ps[0], ps[1], ps[2]);
      var parent = bone.parent;
      if (parent && parent.isBone) {{
        _mxLocalPos.copy(_mxPos);
        parent.worldToLocal(_mxLocalPos);
        bone.position.copy(_mxLocalPos);
        parent.getWorldQuaternion(_mxParentInv);
        _mxParentInv.invert();
        bone.quaternion.copy(_mxQuat).premultiply(_mxParentInv);
      }} else {{
        bone.position.copy(_mxPos);
        bone.quaternion.copy(_mxQuat);
      }}
    }}
  }}
  if (driven === 0) {{
    console.warn('No bones driven! mixamoBones keys:', Object.keys(mixamoBones), 'GLB bone names:', bones.map(function(b) {{ return b.name; }}));
  }}
}}

function updateFrame(idx) {{
  idx = Math.max(0, Math.min(idx, nFrames - 1));
  const frame = frames[idx];

  if (mixamoReady) {{
    for (var i = 0; i < jointMeshes.length; i++) jointMeshes[i].visible = false;
    for (var c = 0; c < boneCylinders.length; c++) if (boneCylinders[c]) boneCylinders[c].visible = false;
    if (lineObj) {{ scene.remove(lineObj); lineObj = null; }}
    for (var t = 0; t < trailLines.length; t++) if (trailLines[t]) trailLines[t].visible = false;
    driveMixamoBones(frame);
    return idx;
  }}

  for (var i = 0; i < labels.length; i++) {{
    var p = frame[labels[i]];
    var m = jointMeshes[i];
    if (p && p.length >= 3) {{
      m.position.set(p[0], p[1], p[2]);
      m.visible = true;
      if (trailFrames > 0 && trailPoints[i]) {{
        trailPoints[i].unshift(new THREE.Vector3(p[0], p[1], p[2]));
        if (trailPoints[i].length > trailFrames) trailPoints[i].pop();
        trailLines[i].geometry.setFromPoints(trailPoints[i]);
        trailLines[i].geometry.attributes.position.needsUpdate = true;
        trailLines[i].visible = trailPoints[i].length > 1;
      }}
    }} else {{
      m.visible = false;
      if (trailFrames > 0 && trailLines[i]) {{ trailLines[i].visible = false; }}
    }}
  }}

  // 骨骼：蒙皮用圆柱体，否则用线段
  if (skinBones && boneCylinders.length > 0) {{
    for (var s = 0; s < segments.length; s++) {{
      var pa = frame[segments[s][0]], pb = frame[segments[s][1]];
      var cyl = boneCylinders[s];
      if (pa && pb && cyl) {{
        _v0.set(pa[0], pa[1], pa[2]);
        _v1.set(pb[0], pb[1], pb[2]);
        var len = _v0.distanceTo(_v1);
        if (len < 1e-4) {{ cyl.visible = false; continue; }}
        _mid.copy(_v0).add(_v1).multiplyScalar(0.5);
        cyl.position.copy(_mid);
        cyl.scale.set(1, len, 1);
        _v1.sub(_v0).normalize();
        cyl.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), _v1);
        cyl.visible = true;
      }} else if (cyl) {{ cyl.visible = false; }}
    }}
  }} else {{
    if (lineObj) scene.remove(lineObj);
    lineObj = null;
    var linePts = [];
    for (var s = 0; s < segments.length; s++) {{
      var pa = frame[segments[s][0]], pb = frame[segments[s][1]];
      if (pa && pb) {{
        linePts.push(new THREE.Vector3(pa[0], pa[1], pa[2]), new THREE.Vector3(pb[0], pb[1], pb[2]));
      }}
    }}
    if (linePts.length >= 2) {{
      var lineGeo = new THREE.BufferGeometry().setFromPoints(linePts);
      lineObj = new THREE.LineSegments(lineGeo, lineMat);
      scene.add(lineObj);
    }}
  }}
  return idx;
}}

frameSlider.max = Math.max(0, nFrames - 1);
if (nFrames > 0) {{ frameInput.max = nFrames - 1; frameInput.placeholder = '0-' + (nFrames-1); }}
if (nFrames === 0) {{
  timeEl.textContent = '无数据';
}} else {{
let currentIdx = 0;
let playing = false;
let lastTime = performance.now();
let acc = 0;

function syncUIFromFrame() {{
  frameSlider.value = currentIdx;
  frameInput.value = currentIdx;
  var pct = nFrames > 1 ? (currentIdx / (nFrames - 1)) * 100 : 0;
  timelineFill.style.width = pct + '%';
}}

function animate(now) {{
  requestAnimationFrame(animate);
  const dt = (now - lastTime) / 1000;
  lastTime = now;
  if (playing) {{
    const speed = parseFloat(speedInput.value);
    acc += dt * frameRate * speed / frameStep;
    if (acc >= 1) {{
      const step = Math.floor(acc);
      acc -= step;
      if (loopCheck.checked) {{
        currentIdx = (currentIdx + step) % nFrames;
      }} else {{
        currentIdx = Math.min(currentIdx + step, nFrames - 1);
        if (currentIdx >= nFrames - 1) {{ playing = false; }}
      }}
      updateFrame(currentIdx);
      syncUIFromFrame();
    }}
  }}
  const t = (currentIdx * frameStep) / frameRate;
  timeEl.textContent = t.toFixed(2) + ' / ' + durationSec.toFixed(2) + ' s';
  controls.update();
  renderer.render(scene, camera);
}}

btnPlay.onclick = () => {{ playing = true; }};
btnPause.onclick = () => {{ playing = false; }};
frameSlider.oninput = () => {{
  currentIdx = parseInt(frameSlider.value);
  updateFrame(currentIdx);
  syncUIFromFrame();
}};
timelineBar.onclick = function(e) {{
  var w = timelineBar.offsetWidth;
  if (w <= 0) return;
  var x = e.offsetX;
  currentIdx = Math.min(Math.floor((x / w) * nFrames), nFrames - 1);
  currentIdx = Math.max(0, currentIdx);
  updateFrame(currentIdx);
  syncUIFromFrame();
}};
frameInput.onchange = function() {{
  var v = parseInt(frameInput.value, 10);
  if (!isNaN(v)) {{
    currentIdx = Math.max(0, Math.min(v, nFrames - 1));
    updateFrame(currentIdx);
    syncUIFromFrame();
  }}
}};

function toggleFullscreen() {{
  if (!document.fullscreenElement && !document.webkitFullscreenElement) {{
    (viewportEl.requestFullscreen || viewportEl.webkitRequestFullscreen).call(viewportEl);
    viewportEl.classList.add('fullscreen');
    if (btnFullscreen) {{ btnFullscreen.textContent = '⛶ 退出全屏'; }}
  }} else {{
    (document.exitFullscreen || document.webkitExitFullscreen).call(document);
    viewportEl.classList.remove('fullscreen');
    if (btnFullscreen) {{ btnFullscreen.textContent = '⛶ 全屏'; }}
  }}
}}
if (btnFullscreen) {{ btnFullscreen.onclick = toggleFullscreen; }}
document.addEventListener('keydown', function(e) {{
  if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
  if (e.key === ' ') {{ e.preventDefault(); playing = !playing; return; }}
  if (e.key === 'F11') {{ e.preventDefault(); toggleFullscreen(); return; }}
  if (e.key === 'f' || e.key === 'F') {{ focusView(); return; }}
  if (e.key === 'r' || e.key === 'R') {{ resetView(); return; }}
  var num = parseInt(e.key, 10);
  if (num >= 1 && num <= 4) {{ setView(num); }}
}});

currentIdx = updateFrame(0);
syncUIFromFrame();
animate(performance.now());
}}

function onResize() {{
  requestAnimationFrame(function() {{
    var vb = getViewboxSize();
    var w = Math.max(vb.w, 1);
    var h = Math.max(vb.h, 1);
    if (viewboxEl) {{ viewboxEl.style.width = w + 'px'; viewboxEl.style.height = h + 'px'; }}
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
    renderer.setSize(w, h);
  }});
}}
window.addEventListener('resize', onResize);
document.addEventListener('fullscreenchange', onResize);
document.addEventListener('webkitfullscreenchange', onResize);
setTimeout(onResize, 0);
}} catch (e) {{
  document.body.innerHTML = '<div style="padding:2rem;color:#e74c3c;font-family:system-ui">3D 查看器加载失败: ' + (e.message || e) + '<br><br>若为直接打开HTML文件，请通过本地服务器访问（如 python -m http.server 8000）。</div>';
  console.error(e);
}}
}})();
</script>
</body>
</html>"""
