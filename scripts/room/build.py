# -*- coding: utf-8 -*-
"""
Mirrai 官网 · 三维房间（docs/DESIGN-REFINEMENT.md §6）

这间房是唯一的源头：三张静帧（房间远景 / 书桌近景 / 灯灭）和进门镜头的实时三维层都从这里出，
所以镜头落点和首屏照片是同一帧。

用法（仓库根目录；先跑 node scripts/room/fetch-textures.mjs 取 CC0 贴图）：
  B=/Applications/Blender.app/Contents/MacOS/Blender
  $B -b -P scripts/room/build.py -- preview     # 三个机位小样 → .cache/room/preview-*.jpg
  $B -b -P scripts/room/build.py -- stills      # 终版静帧 → src/assets/room/*.jpg
  $B -b -P scripts/room/build.py -- bake        # 光照图集 + 网格 + scene.json（之后跑 pack-atlases.mjs）
  $B -b -P scripts/room/build.py -- json        # 只重写 scene.json（只改了 CROP 这类不影响画面的参数时）
  加 --from-blend：不重建，直接用 assets/room/room.blend（在 Blender 里手工改过场景后用）
"""
import bpy
import bmesh
import json
import math
import os
import random
import struct
import sys

import numpy as np
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Euler, Matrix, Vector

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
CACHE = os.path.join(ROOT, '.cache', 'room')
TEX = os.path.join(CACHE, 'textures')
OUT_STILLS = os.path.join(ROOT, 'src', 'assets', 'room')
OUT_3D = os.path.join(ROOT, 'src', 'assets', 'room3d')
BLEND = os.path.join(ROOT, 'assets', 'room', 'room.blend')

ARGV = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
STEPS = [a for a in ARGV if not a.startswith('--')]
FLAGS = {a for a in ARGV if a.startswith('--')}

# ---------- 房间尺寸（米；X 向右，Y 向里，Z 向上） ----------
XL, XR = -1.9, 1.9
YN, YF = 0.0, 3.4
H = 2.6
WALL_T = 0.14
WIN = dict(x0=0.84, x1=1.70, z0=0.95, z1=2.15)
DOOR = dict(x0=-0.36, x1=0.50, z1=2.05)

DESK_L, DESK_D, DESK_TOP = 1.30, 0.62, 0.75
DESK_CX = 0.67
DESK_BACK = 3.255
DESK_CY = DESK_BACK - DESK_D / 2
DESK_FRONT = DESK_BACK - DESK_D
CURTAIN_Y = 3.33


def D(x, y, z=0.0):
    """书桌桌面坐标 → 世界坐标（原点在桌面中心，x 沿桌长，y 朝墙）。"""
    return Vector((DESK_CX + x, DESK_CY + y, DESK_TOP + z))


# 台灯：底座在桌子右后方，鹅颈向前探，灯罩朝下并略朝人这一侧
LAMP_BASE = D(0.43, 0.17)
SHADE_TOP = D(0.25, 0.06, 0.40)
SHADE_AIM = Vector((-0.20, -0.36, -0.91)).normalized()
BULB = SHADE_TOP + SHADE_AIM * 0.052

LETTER = D(0.03, -0.095)
CHAIR = Vector((0.47, DESK_FRONT - 0.11, 0.0))

# 机位：位置、水平转角°（0 = 朝里，正 = 向右）、俯仰°、焦距 mm、光圈、对焦点、画幅
#   wide / close    横幅一对：门口看进来的远景（进门第一帧、第三幕）→ 书桌近景（首屏 = 镜头落点）
#   wideP / closeP  竖幅一对（手机）：同一段路，构图按竖屏重排——灯和信上下叠在画面上半
CAMS = {
    'wide': dict(loc=(0.0, -0.95, 1.50), yaw=3.7, pitch=-7.2, lens=35, fstop=4.0, focus=LETTER, res=(2560, 1440)),
    'close': dict(loc=(1.10, 1.80, 1.44), yaw=-27.5, pitch=-27.0, lens=30, fstop=2.4, focus=LETTER, res=(2560, 1440)),
    'wideP': dict(loc=(0.0, -0.95, 1.50), yaw=8.5, pitch=-7.0, lens=44, fstop=4.0, focus=LETTER, res=(1440, 1920)),
    'closeP': dict(loc=(0.98, 1.80, 1.42), yaw=-9.0, pitch=-47.0, lens=26, fstop=2.4, focus=LETTER, res=(1440, 1920)),
}
PAIRS = dict(l=('wide', 'close'), p=('wideP', 'closeP'))
RES = dict({k: v['res'] for k, v in CAMS.items()}, surface=(1600, 900))
# 每张静帧铺满视口时对准的点（站点 CSS 与 2.5D 退路的推镜拟合共用）。
# 书桌近景横向居中裁：窗口比 16:9 更方时，信纸左缘在视口里的位置基本不动，左边始终留得出文字栏
# （代价是很方的窗口里右边的钟会被裁掉）。
CROP = dict(
    wide=dict(zoom=1.0, fx=0.60, fy=0.50), close=dict(zoom=1.0, fx=0.50, fy=0.46),
    wideP=dict(zoom=1.0, fx=0.55, fy=0.50), closeP=dict(zoom=1.0, fx=0.52, fy=0.40),
)
# 进门镜头的贝塞尔控制点：先直着穿过门洞，再拐向书桌
PATH_CTRL = (-0.05, 0.85, 1.50)

LOOK = 'AgX - Medium High Contrast'
EXPOSURE = dict(on=1.0, off=2.3)
# 静帧：(文件名, 机位, 灯是否亮)。desk-top 是第二幕铺在页面底下的那张桌面（同一块木头，正上方俯拍）
SHOTS = (('room-wide', 'wide', True), ('desk-close', 'close', True), ('room-dark', 'wide', False),
         ('room-wide-p', 'wideP', True), ('desk-close-p', 'closeP', True), ('room-dark-p', 'wideP', False),
         ('desk-top', 'surface', True))
SURFACE_AT = Vector((40.0, 0.0, 0.0))     # 俯拍桌面单独摆在远处，不影响房间的光

ROOM = None  # 主集合


def lerp(a, b, t):
    return a + (b - a) * t


# =====================================================================
# 零件
# =====================================================================
def p_box(sx, sy, sz, bevel=0.0, seg=2):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co.x *= sx
        v.co.y *= sy
        v.co.z *= sz
    if bevel > 0:
        bmesh.ops.bevel(bm, geom=bm.edges[:], offset=bevel, segments=seg, profile=0.5,
                        affect='EDGES', clamp_overlap=True)
    return bm


def p_cyl(r, h, seg=24, r2=None):
    """圆柱 / 圆台，轴沿 Z，中心在原点；r 在下，r2 在上。"""
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=seg,
                          radius1=r, radius2=r if r2 is None else r2, depth=h)
    return bm


def p_sphere(r, u=24, v=12):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=u, v_segments=v, radius=r)
    return bm


def p_lathe(profile, seg=48):
    """车削：profile 为 (半径, 高度) 序列，在 (r, z) 半平面里逆时针走则法线朝外。面的 material_index 暂存段号。"""
    bm = bmesh.new()
    rings = []
    for (r, z) in profile:
        rings.append([bm.verts.new((r * math.cos(2 * math.pi * i / seg), r * math.sin(2 * math.pi * i / seg), z))
                      for i in range(seg)])
    for j in range(len(rings) - 1):
        a, b = rings[j], rings[j + 1]
        for i in range(seg):
            i2 = (i + 1) % seg
            f = bm.faces.new((a[i], a[i2], b[i2], b[i]))
            f.material_index = j
    return bm


def p_tube(points, radius, seg=10, per=8, cap=True):
    """沿 Catmull-Rom 曲线的圆管；radius 可为常数或 f(t)。"""
    P = [Vector(p) for p in points]
    ext = [P[0] * 2 - P[1]] + P + [P[-1] * 2 - P[-2]]
    path = []
    for i in range(len(P) - 1):
        p0, p1, p2, p3 = ext[i:i + 4]
        for k in range(per):
            t = k / per
            path.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t
                               + (-p0 + 3 * p1 - 3 * p2 + p3) * t * t * t))
    path.append(P[-1])
    n = len(path)
    tans = [(path[min(i + 1, n - 1)] - path[max(i - 1, 0)]).normalized() for i in range(n)]
    up = Vector((0, 0, 1)) if abs(tans[0].z) < 0.9 else Vector((1, 0, 0))
    nrm = (up - tans[0] * up.dot(tans[0])).normalized()
    bm = bmesh.new()
    rings = []
    for i in range(n):
        t = tans[i]
        nrm = (nrm - t * nrm.dot(t)).normalized()
        bn = t.cross(nrm)
        r = radius(i / (n - 1)) if callable(radius) else radius
        rings.append([bm.verts.new(path[i] + (nrm * math.cos(a) + bn * math.sin(a)) * r)
                      for a in (2 * math.pi * j / seg for j in range(seg))])
    for i in range(n - 1):
        a, b = rings[i], rings[i + 1]
        for j in range(seg):
            j2 = (j + 1) % seg
            bm.faces.new((a[j], a[j2], b[j2], b[j]))
    if cap:
        bm.faces.new(list(reversed(rings[0])))
        bm.faces.new(rings[-1])
    return bm


def p_grid(nu, nv, fn, flip=False, uv=True):
    """参数曲面：fn(u, v) → (x, y, z)，u、v ∈ [0, 1]；带一层 'tex' UV。"""
    bm = bmesh.new()
    layer = bm.loops.layers.uv.new('tex') if uv else None
    vs = [[bm.verts.new(fn(i / nu, j / nv)) for i in range(nu + 1)] for j in range(nv + 1)]
    for j in range(nv):
        for i in range(nu):
            corners = [(i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1)]
            if flip:
                corners.reverse()
            f = bm.faces.new([vs[b][a] for a, b in corners])
            if layer:
                for loop, (a, b) in zip(f.loops, corners):
                    loop[layer].uv = (a / nu, b / nv)
    return bm


def p_disc(radius, seg, z, uv_size):
    """朝 +Z 的圆片，带平面投影的 'tex' UV（uv_size 为贴图对应的边长）。"""
    bm = bmesh.new()
    layer = bm.loops.layers.uv.new('tex')
    ring = [bm.verts.new((radius * math.cos(2 * math.pi * i / seg), radius * math.sin(2 * math.pi * i / seg), z))
            for i in range(seg)]
    f = bm.faces.new(ring)
    for loop in f.loops:
        loop[layer].uv = (loop.vert.co.x / uv_size + 0.5, loop.vert.co.y / uv_size + 0.5)
    return bm


def p_rect(origin, eu, ev, normal):
    """一块矩形面，法线朝 normal 一侧（烘焙只算法线这一面，朝向必须对）。"""
    o, eu, ev = Vector(origin), Vector(eu), Vector(ev)
    pts = [o, o + eu, o + eu + ev, o + ev]
    if eu.cross(ev).dot(Vector(normal)) < 0:
        pts.reverse()
    bm = bmesh.new()
    bm.faces.new([bm.verts.new(p) for p in pts])
    return bm


class MB:
    """把若干零件攒进一个网格：各零件可带变换、材质槽、顶点色。"""

    def __init__(self, color=False, uv=False):
        self.bm = bmesh.new()
        self.col = self.bm.loops.layers.color.new('Col') if color else None
        if uv:
            self.bm.loops.layers.uv.new('tex')

    def add(self, part, loc=(0, 0, 0), rot=(0, 0, 0), mi=0, color=None, matrix=None):
        m = matrix if matrix is not None else Matrix.Translation(loc) @ Euler(rot, 'XYZ').to_matrix().to_4x4()
        bmesh.ops.transform(part, matrix=m, verts=part.verts[:])
        tmp = bpy.data.meshes.new('_tmp')
        part.to_mesh(tmp)
        part.free()
        n0 = len(self.bm.faces)
        self.bm.from_mesh(tmp)
        bpy.data.meshes.remove(tmp)
        self.bm.faces.ensure_lookup_table()
        for f in self.bm.faces[n0:]:
            f.material_index = mi(f.material_index) if callable(mi) else mi
            if color is not None and self.col is not None:
                for loop in f.loops:
                    loop[self.col] = (color[0], color[1], color[2], 1.0)
        return self

    def finish(self, name, mats, smooth=True, sharp=35.0, weighted=True, atlas=None, texw=1.0, loc=None, rot=None):
        bm = self.bm
        if smooth:
            lim = math.radians(sharp)
            for f in bm.faces:
                f.smooth = True
            for e in bm.edges:
                if len(e.link_faces) == 2 and e.calc_face_angle(0.0) > lim:
                    e.smooth = False
        me = bpy.data.meshes.new(name)
        bm.to_mesh(me)
        bm.free()
        for m in mats:
            me.materials.append(m)
        ob = bpy.data.objects.new(name, me)
        ROOM.objects.link(ob)
        if loc is not None:
            ob.location = loc
        if rot is not None:
            ob.rotation_euler = rot
        if smooth and weighted:
            mod = ob.modifiers.new('WeightedNormal', 'WEIGHTED_NORMAL')
            mod.keep_sharp = True
            mod.weight = 60
        if atlas is not None:
            ob['atlas'] = atlas
            ob['texw'] = texw
        return ob


def apply_modifiers(ob):
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg), preserve_all_data_layers=True, depsgraph=dg)
    old = ob.data
    ob.modifiers.clear()
    ob.data = me
    me.name = old.name
    bpy.data.meshes.remove(old)


# =====================================================================
# 程序生成的贴图
# =====================================================================
def _blur(img, sigma):
    r = max(1, int(math.ceil(sigma * 3)))
    k = np.exp(-0.5 * (np.arange(-r, r + 1) / sigma) ** 2)
    k /= k.sum()
    for axis in (0, 1):
        acc = np.zeros_like(img)
        for i, w in enumerate(k):
            acc += w * np.roll(img, i - r, axis=axis)
        img = acc
    return img


def _splat(h, w, xs, ys, weight):
    img = np.zeros((h, w), np.float32)
    x0 = np.floor(xs).astype(np.int64)
    y0 = np.floor(ys).astype(np.int64)
    fx, fy = xs - x0, ys - y0
    for dx, dy, wgt in ((0, 0, (1 - fx) * (1 - fy)), (1, 0, fx * (1 - fy)), (0, 1, (1 - fx) * fy), (1, 1, fx * fy)):
        xi, yi = x0 + dx, y0 + dy
        ok = (xi >= 0) & (xi < w) & (yi >= 0) & (yi < h)
        np.add.at(img, (yi[ok], xi[ok]), (wgt[ok] * weight).astype(np.float32))
    return img


def _to_image(name, rgb, float_buffer=False):
    """rgb: (h, w, 3)，第 0 行是图像顶部。"""
    h, w = rgb.shape[:2]
    img = bpy.data.images.new(name, w, h, alpha=False, float_buffer=float_buffer)
    px = np.ones((h, w, 4), np.float32)
    px[..., :3] = rgb[::-1]
    img.pixels.foreach_set(px.ravel())
    img.update()
    img.pack()
    return img


def tex_letter(w=768, h=1086):
    """信纸：米色纸 + 看不清内容的手写字迹（一格一字的行列，段首空两格，末尾落款）。"""
    rng = np.random.default_rng(23)
    xs, ys = [], []
    cell = 0.036 * w
    top, left, right = 0.115 * h, 0.10 * w, 0.90 * w
    line_h = cell * 1.5
    n_lines = int((0.90 * h - top) / line_h)

    def char(cx, cy, s):
        for _ in range(int(rng.integers(3, 8))):
            kind = int(rng.choice(5, p=[0.30, 0.26, 0.17, 0.17, 0.10]))
            x0 = cx + rng.uniform(-0.42, 0.25) * s
            y0 = cy + rng.uniform(-0.42, 0.25) * s
            length = rng.uniform(0.3, 0.85) * s
            if kind == 0:
                d = (1.0, rng.uniform(-0.14, 0.02))   # 横
            elif kind == 1:
                d = (rng.uniform(-0.06, 0.06), 1.0)   # 竖
            elif kind == 2:
                d = (-0.6, 0.8)                        # 撇
            elif kind == 3:
                d = (0.65, 0.76)                       # 捺
            else:
                d = (0.5, 0.5)                         # 点
                length *= 0.3
            n = max(4, int(length * 2.4))
            t = np.linspace(0, 1, n)
            bend = rng.uniform(-0.08, 0.08) * s
            xs.append(x0 + d[0] * length * t + bend * np.sin(t * np.pi) * d[1])
            ys.append(y0 + d[1] * length * t - bend * np.sin(t * np.pi) * d[0])

    for li in range(n_lines):
        y = top + li * line_h
        x, end = left, right
        if li == 0:
            end = left + 4.2 * cell                         # 称呼
        elif li in (6, 12):
            end = left + rng.uniform(5, 12) * cell          # 段末
        if li in (1, 7, 13):
            x += 2 * cell                                   # 段首空两格
        if li == n_lines - 1:
            x = right - 5.2 * cell                          # 落款
        while x + cell <= end + 1:
            if rng.random() < 0.06:
                x += cell * 0.9
                continue
            char(x + cell / 2, y, cell * 0.86)
            x += cell * rng.uniform(0.96, 1.08)

    ink = np.clip(_blur(_splat(h, w, np.concatenate(xs), np.concatenate(ys), 0.62), 0.75), 0, 1)
    fiber = _blur(rng.normal(0, 1, (h, w)).astype(np.float32), 1.2) * 0.02
    paper = np.array([0.905, 0.865, 0.765], np.float32)[None, None, :] * (1 + fiber[..., None])
    ink_col = np.array([0.085, 0.095, 0.16], np.float32)[None, None, :]
    return _to_image('LetterTex', np.clip(paper * (1 - ink[..., None]) + ink_col * ink[..., None], 0, 1))


def tex_dial(n=512):
    """钟面：米色盘 + 60 道分刻、12 道时刻。"""
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32)
    x = (xx - n / 2 + 0.5) / (n / 2)
    y = (n / 2 - yy - 0.5) / (n / 2)
    r = np.hypot(x, y)
    ang = np.arctan2(x, y)
    img = np.empty((n, n, 3), np.float32)
    img[:] = (0.90, 0.87, 0.78)
    img *= (1 - 0.12 * np.clip(r, 0, 1) ** 2)[..., None]

    def ticks(count, r0, r1, half_w):
        a = np.mod(ang, 2 * np.pi / count)
        a = np.minimum(a, 2 * np.pi / count - a)
        return (r > r0) & (r < r1) & (a * r < half_w)

    img[ticks(60, 0.86, 0.93, 0.006) | ticks(12, 0.76, 0.93, 0.017)] = (0.10, 0.09, 0.08)
    img[r < 0.04] = (0.10, 0.09, 0.08)
    return _to_image('DialTex', img)


def tex_city(w=2048, h=1024):
    """窗外：夜空渐变 + 远近两层楼群的零星灯火（线性 HDR，灯远亮于天；灯点小而稀，交给景深去化成光斑）。"""
    rng = np.random.default_rng(5)
    v = np.linspace(1, 0, h, dtype=np.float32)[:, None, None]          # 第 0 行 = 顶
    top = np.array([0.003, 0.005, 0.014], np.float32)
    hor = np.array([0.022, 0.026, 0.040], np.float32)
    img = (top + (hor - top) * np.exp(-np.clip(v - 0.38, 0, 1) * 6.0)) * np.ones((h, w, 3), np.float32)
    lights = np.zeros((h, w, 3), np.float32)
    warm, cool = np.array([1.0, 0.68, 0.38], np.float32), np.array([0.70, 0.84, 1.0], np.float32)

    def skyline(h_lo, h_hi, bw_lo, bw_hi, body, p_lo, p_hi, cell, size, gain):
        x = 0
        while x < w:
            bw = int(rng.integers(bw_lo, bw_hi))
            x1, y0 = min(w, x + bw), h - int(rng.uniform(h_lo, h_hi) * h)
            img[y0:, x:x1] = body
            lights[y0:, x:x1] = 0
            p = rng.uniform(p_lo, p_hi)
            warm_bias = rng.uniform(0.55, 0.95)
            for yy in range(y0 + cell, h - 2, cell):
                row_p = p * rng.uniform(0.2, 1.9)                         # 有的楼层亮得多
                for xx in range(x + cell // 2, x1 - size - 1, cell):
                    if rng.random() < row_p:
                        c = warm if rng.random() < warm_bias else cool
                        jx = int(rng.integers(0, 2))
                        lights[yy:yy + size, xx + jx:xx + jx + size] = c * min(40.0, rng.lognormal(1.0, 0.8)) * gain
            x = x1 + int(rng.integers(0, 30))

    skyline(0.36, 0.50, 40, 150, (0.012, 0.014, 0.022), 0.015, 0.06, 6, 1, 0.6)     # 远
    skyline(0.16, 0.42, 90, 260, (0.004, 0.005, 0.009), 0.012, 0.07, 10, 2, 1.0)    # 近
    for c in range(3):
        img[..., c] += _blur(lights[..., c], 0.7)
    return _to_image('CityTex', img, float_buffer=True)


# =====================================================================
# 材质
# =====================================================================
def new_mat(name):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    bsdf = nt.nodes.new('ShaderNodeBsdfPrincipled')
    nt.links.new(bsdf.outputs[0], out.inputs[0])
    return m, nt, bsdf, out


def set_in(node, **kw):
    for k, v in kw.items():
        node.inputs[k.replace('_', ' ')].default_value = v


def tex_vec(nt, size, rot_z=0.0, coords='Object'):
    tc = nt.nodes.new('ShaderNodeTexCoord')
    mp = nt.nodes.new('ShaderNodeMapping')
    nt.links.new(tc.outputs[coords], mp.inputs['Vector'])
    s = 1.0 / size
    mp.inputs['Scale'].default_value = (s, s, s)
    mp.inputs['Rotation'].default_value = (0, 0, rot_z)
    return mp.outputs['Vector']


def tex_file(nt, vec, file, non_color=False):
    n = nt.nodes.new('ShaderNodeTexImage')
    n.image = bpy.data.images.load(os.path.join(TEX, file), check_existing=True)
    if non_color:
        n.image.colorspace_settings.name = 'Non-Color'
    n.projection = 'BOX'
    n.projection_blend = 0.25
    nt.links.new(vec, n.inputs['Vector'])
    return n.outputs['Color']


def mat_pbr(name, tex, size, res=('2k', '2k', '2k'), rot_z=0.0, tint=(1, 1, 1), value=1.0, sat=1.0, hue=0.5,
            rough=(1.0, 0.0), bump=0.25, bump_dist=0.002, flat=None, **principled):
    """Poly Haven 的一套贴图（diff / rough / disp），盒式投影，按真实尺寸平铺。res 里缺的项用 None。
    flat=(颜色, 比例)：把贴图颜色往一个纯色上压，留一点质感、去掉大块的色斑。"""
    m, nt, bsdf, _ = new_mat(name)
    vec = tex_vec(nt, size, rot_z)
    col = tex_file(nt, vec, f'{tex}_diff_{res[0]}.jpg')
    hsv = nt.nodes.new('ShaderNodeHueSaturation')
    hsv.inputs['Hue'].default_value = hue
    hsv.inputs['Saturation'].default_value = sat
    hsv.inputs['Value'].default_value = value
    nt.links.new(col, hsv.inputs['Color'])
    mul = nt.nodes.new('ShaderNodeVectorMath')
    mul.operation = 'MULTIPLY'
    nt.links.new(hsv.outputs['Color'], mul.inputs[0])
    mul.inputs[1].default_value = tint
    color = mul.outputs['Vector']
    if flat:
        mix = nt.nodes.new('ShaderNodeMix')
        mix.data_type = 'RGBA'
        ins = {(i.name, i.type): i for i in reversed(list(mix.inputs))}
        ins[('Factor', 'VALUE')].default_value = flat[1]
        nt.links.new(color, ins[('A', 'RGBA')])
        ins[('B', 'RGBA')].default_value = (*flat[0], 1.0)
        color = next(o for o in mix.outputs if o.type == 'RGBA')
    nt.links.new(color, bsdf.inputs['Base Color'])
    if res[1]:
        r = nt.nodes.new('ShaderNodeMath')
        r.operation = 'MULTIPLY_ADD'
        r.use_clamp = True
        nt.links.new(tex_file(nt, vec, f'{tex}_rough_{res[1]}.jpg', True), r.inputs[0])
        r.inputs[1].default_value, r.inputs[2].default_value = rough
        nt.links.new(r.outputs[0], bsdf.inputs['Roughness'])
    if res[2] and bump > 0:
        b = nt.nodes.new('ShaderNodeBump')
        b.inputs['Strength'].default_value = bump
        b.inputs['Distance'].default_value = bump_dist
        nt.links.new(tex_file(nt, vec, f'{tex}_disp_{res[2]}.jpg', True), b.inputs['Height'])
        nt.links.new(b.outputs['Normal'], bsdf.inputs['Normal'])
    set_in(bsdf, **principled)
    return m


def mat_plain(name, color, rough=0.5, noise_bump=0.0, noise_scale=300.0, **principled):
    m, nt, bsdf, _ = new_mat(name)
    set_in(bsdf, Base_Color=(*color, 1.0), Roughness=rough, **principled)
    if noise_bump > 0:
        tc = nt.nodes.new('ShaderNodeTexCoord')
        nz = nt.nodes.new('ShaderNodeTexNoise')
        nz.inputs['Scale'].default_value = noise_scale
        nz.inputs['Detail'].default_value = 3.0
        nt.links.new(tc.outputs['Object'], nz.inputs['Vector'])
        b = nt.nodes.new('ShaderNodeBump')
        b.inputs['Strength'].default_value = noise_bump
        b.inputs['Distance'].default_value = 0.0005
        nt.links.new(nz.outputs[0], b.inputs['Height'])
        nt.links.new(b.outputs['Normal'], bsdf.inputs['Normal'])
    return m


def mat_brass(name, rough=(0.20, 0.40)):
    """黄铜：整体偏暖，粗糙度和色泽有一点不均匀（手摸过、氧化过）。"""
    m, nt, bsdf, _ = new_mat(name)
    tc = nt.nodes.new('ShaderNodeTexCoord')
    n1 = nt.nodes.new('ShaderNodeTexNoise')
    n1.inputs['Scale'].default_value = 26.0
    n1.inputs['Detail'].default_value = 5.0
    nt.links.new(tc.outputs['Object'], n1.inputs['Vector'])
    mr = nt.nodes.new('ShaderNodeMapRange')
    mr.inputs[1].default_value, mr.inputs[2].default_value = 0.3, 0.7
    mr.inputs[3].default_value, mr.inputs[4].default_value = rough
    nt.links.new(n1.outputs[0], mr.inputs[0])
    nt.links.new(mr.outputs[0], bsdf.inputs['Roughness'])
    n2 = nt.nodes.new('ShaderNodeTexNoise')
    n2.inputs['Scale'].default_value = 7.0
    n2.inputs['Detail'].default_value = 3.0
    nt.links.new(tc.outputs['Object'], n2.inputs['Vector'])
    ramp = nt.nodes.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].position = 0.35
    ramp.color_ramp.elements[0].color = (0.56, 0.38, 0.16, 1)
    ramp.color_ramp.elements[1].position = 0.70
    ramp.color_ramp.elements[1].color = (0.85, 0.62, 0.28, 1)
    nt.links.new(n2.outputs[0], ramp.inputs[0])
    nt.links.new(ramp.outputs[0], bsdf.inputs['Base Color'])
    set_in(bsdf, Metallic=1.0)
    return m


def mat_curtain(name):
    """纱帘：亚麻纹理做凹凸，漫反射 + 透光各半，背后的月光能把它映蓝。"""
    m, nt, bsdf, out = new_mat(name)
    vec = tex_vec(nt, 0.27)
    b = nt.nodes.new('ShaderNodeBump')
    b.inputs['Strength'].default_value = 0.5
    b.inputs['Distance'].default_value = 0.0006
    nt.links.new(tex_file(nt, vec, 'rough_linen_disp_1k.jpg', True), b.inputs['Height'])
    nt.links.new(b.outputs['Normal'], bsdf.inputs['Normal'])
    color = (0.80, 0.78, 0.73, 1.0)
    set_in(bsdf, Base_Color=color, Roughness=0.9, Sheen_Weight=0.4)
    tr = nt.nodes.new('ShaderNodeBsdfTranslucent')
    tr.inputs['Color'].default_value = color
    nt.links.new(b.outputs['Normal'], tr.inputs['Normal'])
    mix = nt.nodes.new('ShaderNodeMixShader')
    mix.inputs[0].default_value = 0.5
    nt.links.new(bsdf.outputs[0], mix.inputs[1])
    nt.links.new(tr.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs[0])
    return m


def mat_image(name, image, uv='tex', rough=0.7, emission=0.0, **principled):
    m, nt, bsdf, out = new_mat(name)
    uvn = nt.nodes.new('ShaderNodeUVMap')
    uvn.uv_map = uv
    tex = nt.nodes.new('ShaderNodeTexImage')
    tex.image = image
    nt.links.new(uvn.outputs[0], tex.inputs['Vector'])
    if emission > 0:
        em = nt.nodes.new('ShaderNodeEmission')
        em.inputs['Strength'].default_value = emission
        nt.links.new(tex.outputs['Color'], em.inputs['Color'])
        nt.links.new(em.outputs[0], out.inputs[0])
    else:
        nt.links.new(tex.outputs['Color'], bsdf.inputs['Base Color'])
        set_in(bsdf, Roughness=rough, **principled)
    return m


def mat_emit(name, color, strength):
    m, nt, bsdf, out = new_mat(name)
    em = nt.nodes.new('ShaderNodeEmission')
    em.inputs['Color'].default_value = (*color, 1.0)
    em.inputs['Strength'].default_value = strength
    nt.links.new(em.outputs[0], out.inputs[0])
    return m


def mat_glass(name):
    """窗玻璃：相机 / 反射光线看到的是真玻璃；漫反射与阴影光线直接穿过，月光才进得来。"""
    m, nt, bsdf, out = new_mat(name)
    set_in(bsdf, Base_Color=(1, 1, 1, 1), Roughness=0.0, Transmission_Weight=1.0, IOR=1.45)
    tr = nt.nodes.new('ShaderNodeBsdfTransparent')
    lp = nt.nodes.new('ShaderNodeLightPath')
    mx = nt.nodes.new('ShaderNodeMath')
    mx.operation = 'MAXIMUM'
    nt.links.new(lp.outputs['Is Shadow Ray'], mx.inputs[0])
    nt.links.new(lp.outputs['Is Diffuse Ray'], mx.inputs[1])
    mix = nt.nodes.new('ShaderNodeMixShader')
    nt.links.new(mx.outputs[0], mix.inputs[0])
    nt.links.new(bsdf.outputs[0], mix.inputs[1])
    nt.links.new(tr.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs[0])
    return m


def mat_books(name):
    m, nt, bsdf, _ = new_mat(name)
    vc = nt.nodes.new('ShaderNodeVertexColor')
    vc.layer_name = 'Col'
    nt.links.new(vc.outputs['Color'], bsdf.inputs['Base Color'])
    set_in(bsdf, Roughness=0.7)
    return m


def make_materials():
    M = {}
    # 盒式投影在朝上的面上本来就把贴图的纵向（木纹方向）对到 X，所以桌面不用再转
    M['desk_top'] = mat_pbr('DeskTop', 'wood_table_001', 1.5, res=('4k', '2k', '2k'),
                            value=0.95, sat=0.84, hue=0.512, rough=(0.85, 0.06), bump=0.12, bump_dist=0.0015,
                            Coat_Weight=0.25, Coat_Roughness=0.22)
    M['wood'] = mat_pbr('Walnut', 'wood_table_001', 1.5, res=('4k', '2k', '2k'), value=0.8, sat=0.84, hue=0.512,
                        rough=(0.9, 0.08), bump=0.12, bump_dist=0.0015, Coat_Weight=0.15, Coat_Roughness=0.3)
    M['chair'] = mat_pbr('ChairWood', 'walnut_veneer', 1.8, tint=(0.80, 0.62, 0.46), value=0.9,
                         rough=(0.8, 0.08), bump=0.15, Coat_Weight=0.3, Coat_Roughness=0.25)
    M['wood_dark'] = mat_pbr('WalnutDark', 'walnut_veneer', 1.8, tint=(0.42, 0.30, 0.22), value=0.7,
                             rough=(0.9, 0.1), bump=0.2)
    M['floor'] = mat_pbr('Floor', 'wood_floor_worn', 2.0, tint=(0.62, 0.50, 0.42), value=0.75,
                         rough=(0.9, 0.05), bump=0.35, bump_dist=0.003)
    # 刷过漆的内墙：哑光、不做凹凸。这张高度图是 8 位的，整面墙只占了五六个灰阶，
    # 接上凹凸节点后每一级台阶都会变成一条等高线——台灯贴着墙面扫过去，就是一墙的划痕。
    M['plaster'] = mat_pbr('Plaster', 'plastered_wall_04', 3.2, tint=(1.0, 0.955, 0.89), value=1.25, sat=0.6,
                           rough=(0.25, 0.72), bump=0, flat=((0.70, 0.67, 0.61), 0.7), Specular_IOR_Level=0.2)
    M['blanket'] = mat_pbr('Blanket', 'knitted_fleece', 0.27, res=('1k', None, '1k'), tint=(0.36, 0.31, 0.28),
                           value=0.9, bump=1.0, bump_dist=0.0012, Roughness=0.95, Sheen_Weight=0.12)
    M['throw'] = mat_pbr('Throw', 'knitted_fleece', 0.27, res=('1k', None, '1k'), tint=(0.62, 0.36, 0.24),
                         value=0.8, bump=1.0, bump_dist=0.0012, Roughness=0.95, Sheen_Weight=0.12)
    M['curtain'] = mat_curtain('Curtain')
    M['paint'] = mat_plain('WhitePaint', (0.80, 0.78, 0.73), rough=0.42, noise_bump=0.08, noise_scale=120)
    M['brass'] = mat_brass('Brass')
    M['brass_fine'] = mat_brass('BrassPolished', rough=(0.12, 0.22))
    M['enamel'] = mat_plain('Enamel', (0.90, 0.86, 0.76), rough=0.4)
    M['paper'] = mat_image('LetterPaper', tex_letter(), rough=0.72, Sheen_Weight=0.15)
    M['envelope'] = mat_plain('EnvelopePaper', (0.86, 0.82, 0.72), rough=0.78, noise_bump=0.06, noise_scale=900)
    M['dial'] = mat_image('ClockDial', tex_dial(), rough=0.55)
    M['black'] = mat_plain('BlackResin', (0.012, 0.012, 0.014), rough=0.22, Coat_Weight=0.5, Coat_Roughness=0.08)
    M['rubber'] = mat_plain('Cord', (0.02, 0.02, 0.02), rough=0.6)
    M['phone'] = mat_plain('PhoneGlass', (0.018, 0.019, 0.022), rough=0.10, Coat_Weight=1.0, Coat_Roughness=0.03)
    M['books'] = mat_books('Books')
    M['bulb'] = mat_emit('Bulb', (1.0, 0.76, 0.48), 34.0)
    M['city'] = mat_image('City', tex_city(), emission=1.0)
    M['glass'] = mat_glass('WindowGlass')
    return M


# =====================================================================
# 房间
# =====================================================================
def build_shell(M):
    x0, x1, z0, z1 = WIN['x0'], WIN['x1'], WIN['z0'], WIN['z1']
    dx0, dx1, dz1 = DOOR['x0'], DOOR['x1'], DOOR['z1']

    far = MB()
    n = (0, -1, 0)
    far.add(p_rect((XL, YF, 0), (x0 - XL, 0, 0), (0, 0, H), n))
    far.add(p_rect((x1, YF, 0), (XR - x1, 0, 0), (0, 0, H), n))
    far.add(p_rect((x0, YF, 0), (x1 - x0, 0, 0), (0, 0, z0), n))
    far.add(p_rect((x0, YF, z1), (x1 - x0, 0, 0), (0, 0, H - z1), n))
    # 窗洞四壁
    far.add(p_rect((x0, YF, z0), (0, WALL_T, 0), (0, 0, z1 - z0), (1, 0, 0)))
    far.add(p_rect((x1, YF, z0), (0, WALL_T, 0), (0, 0, z1 - z0), (-1, 0, 0)))
    far.add(p_rect((x0, YF, z0), (x1 - x0, 0, 0), (0, WALL_T, 0), (0, 0, 1)))
    far.add(p_rect((x0, YF, z1), (x1 - x0, 0, 0), (0, WALL_T, 0), (0, 0, -1)))
    far.finish('WallFar', [M['plaster']], smooth=False, atlas=1, texw=1.0)

    side = MB()
    side.add(p_rect((XL, YN, 0), (0, YF - YN, 0), (0, 0, H), (1, 0, 0)))
    side.add(p_rect((XR, YN, 0), (0, YF - YN, 0), (0, 0, H), (-1, 0, 0)))
    n = (0, 1, 0)
    side.add(p_rect((XL, YN, 0), (dx0 - XL, 0, 0), (0, 0, H), n))
    side.add(p_rect((dx1, YN, 0), (XR - dx1, 0, 0), (0, 0, H), n))
    side.add(p_rect((dx0, YN, dz1), (dx1 - dx0, 0, 0), (0, 0, H - dz1), n))
    side.finish('WallSides', [M['plaster']], smooth=False, atlas=1, texw=0.45)

    hall = MB()
    n = (0, -1, 0)
    hy = YN - WALL_T
    hall.add(p_rect((-1.3, hy, 0), (dx0 + 1.3, 0, 0), (0, 0, H), n))
    hall.add(p_rect((dx1, hy, 0), (1.4 - dx1, 0, 0), (0, 0, H), n))
    hall.add(p_rect((dx0, hy, dz1), (dx1 - dx0, 0, 0), (0, 0, H - dz1), n))
    hall.finish('WallHall', [M['plaster']], smooth=False, atlas=1, texw=0.35)

    MB().add(p_rect((XL, YN, H), (XR - XL, 0, 0), (0, YF - YN, 0), (0, 0, -1))) \
        .finish('Ceiling', [M['plaster']], smooth=False, atlas=1, texw=0.25)
    MB().add(p_rect((XL, YN - WALL_T, 0), (XR - XL, 0, 0), (0, YF - YN + WALL_T, 0), (0, 0, 1))) \
        .finish('Floor', [M['floor']], smooth=False, atlas=1, texw=0.6)

    # 踢脚线
    bb = MB()
    hh, tt = 0.09, 0.014
    bb.add(p_box(XR - XL, tt, hh, 0.003), loc=((XL + XR) / 2, YF - tt / 2, hh / 2))
    bb.add(p_box(tt, YF - YN, hh, 0.003), loc=(XL + tt / 2, (YN + YF) / 2, hh / 2))
    bb.add(p_box(tt, YF - YN, hh, 0.003), loc=(XR - tt / 2, (YN + YF) / 2, hh / 2))
    bb.add(p_box(dx0 - 0.07 - XL, tt, hh, 0.003), loc=((XL + dx0 - 0.07) / 2, YN + tt / 2, hh / 2))
    bb.add(p_box(XR - dx1 - 0.07, tt, hh, 0.003), loc=((XR + dx1 + 0.07) / 2, YN + tt / 2, hh / 2))
    bb.finish('Baseboards', [M['paint']], atlas=1, texw=0.4)

    # 门框：筒子板 + 两面的门套线
    df = MB()
    lining, cw, ct = 0.028, 0.072, 0.016
    yc, yd = (YN - WALL_T) / 2 + YN / 2, WALL_T + 0.012
    df.add(p_box(lining, yd, dz1, 0.002), loc=(dx0 + lining / 2, yc, dz1 / 2))
    df.add(p_box(lining, yd, dz1, 0.002), loc=(dx1 - lining / 2, yc, dz1 / 2))
    df.add(p_box(dx1 - dx0, yd, lining, 0.002), loc=((dx0 + dx1) / 2, yc, dz1 - lining / 2))
    for y in (YN + ct / 2, YN - WALL_T - ct / 2):
        df.add(p_box(cw, ct, dz1 + cw, 0.004), loc=(dx0 - cw / 2 + 0.006, y, (dz1 + cw) / 2))
        df.add(p_box(cw, ct, dz1 + cw, 0.004), loc=(dx1 + cw / 2 - 0.006, y, (dz1 + cw) / 2))
        df.add(p_box(dx1 - dx0 + 2 * cw - 0.012, ct, cw, 0.004), loc=((dx0 + dx1) / 2, y, dz1 + cw / 2 - 0.006))
    df.finish('DoorFrame', [M['paint']], atlas=1, texw=0.5)


def build_window(M):
    x0, x1, z0, z1 = WIN['x0'], WIN['x1'], WIN['z0'], WIN['z1']
    fy, fd, bar = YF + 0.075, 0.06, 0.046
    cx, cz, w, h = (x0 + x1) / 2, (z0 + z1) / 2, x1 - x0, z1 - z0
    wf = MB()
    wf.add(p_box(bar, fd, h, 0.004), loc=(x0 + bar / 2, fy, cz))
    wf.add(p_box(bar, fd, h, 0.004), loc=(x1 - bar / 2, fy, cz))
    wf.add(p_box(w, fd, bar, 0.004), loc=(cx, fy, z0 + bar / 2))
    wf.add(p_box(w, fd, bar, 0.004), loc=(cx, fy, z1 - bar / 2))
    wf.add(p_box(0.036, fd * 0.8, h, 0.004), loc=(cx, fy, cz))
    wf.add(p_box(w, fd * 0.8, 0.03, 0.004), loc=(cx, fy, z0 + h * 0.56))
    # 窗台板
    wf.add(p_box(w + 0.08, 0.20, 0.032, 0.006), loc=(cx, YF + 0.045, z0 - 0.016))
    wf.finish('WindowFrame', [M['paint']], atlas=0, texw=1.0)

    MB().add(p_box(w, 0.004, h), loc=(cx, fy, cz)).finish('WindowGlass', [M['glass']], smooth=False)

    # 窗外的夜景幕布（只发光）
    dist = 9.0
    city = MB(uv=True)
    city.add(p_grid(1, 1, lambda u, v: (lerp(-6.5, 9.0, u), YF + dist, lerp(-2.0, 7.0, v))))
    city.finish('CityBackdrop', [M['city']], smooth=False, atlas=1, texw=0.16)['lm_grid'] = True

    def curtain(name, cx0, cx1, pleats, seed):
        rng = random.Random(seed)
        ph = rng.uniform(0, 6.28)
        z_top, z_bot = 2.30, 0.035

        def fn(u, v):
            amp = (0.012 + 0.010 * v) * (0.75 + 0.35 * math.sin(4.1 * u + ph))
            w_ = 2 * math.pi * pleats * (u + 0.035 * math.sin(5.3 * u + ph))
            x = lerp(cx0, cx1, u) + 0.016 * math.sin(v * 2.2 + ph) * v
            y = CURTAIN_Y + amp * math.sin(w_ + 0.55 * math.sin(2.6 * v + ph)) + 0.006 * math.sin(0.61 * w_ + 4 * v + ph)
            z = lerp(z_top, z_bot, v) + 0.006 * math.sin(w_ * 0.5 + ph) * v ** 3
            return (x, y, z)

        c = MB(uv=True)
        c.add(p_grid(12 * pleats, 22, fn, flip=True))
        ob = c.finish(name, [M['curtain']], weighted=False, sharp=180, atlas=0, texw=1.0)
        ob['lm_grid'] = True
        return ob

    curtain('CurtainL', 0.50, 0.93, 6, 3)
    curtain('CurtainR', 1.60, 1.87, 4, 8)
    MB().add(p_cyl(0.011, 1.55, 16), loc=(1.18, CURTAIN_Y, 2.315), rot=(0, math.pi / 2, 0)) \
        .finish('CurtainRod', [M['brass']], weighted=False)


def build_desk(M):
    top_t = 0.034
    MB().add(p_box(DESK_L, DESK_D, top_t, 0.0045, 3), loc=(DESK_CX, DESK_CY, DESK_TOP - top_t / 2)) \
        .finish('DeskTop', [M['desk_top']], atlas=0, texw=3.0)

    fr = MB()
    leg_h = DESK_TOP - top_t
    inset = 0.045
    for sx in (-1, 1):
        for sy in (-1, 1):
            leg = p_box(0.052, 0.052, leg_h, 0.004)
            for v in leg.verts:             # 腿向下收细
                k = lerp(0.68, 1.0, (v.co.z + leg_h / 2) / leg_h)
                v.co.x *= k
                v.co.y *= k
            fr.add(leg, loc=(DESK_CX + sx * (DESK_L / 2 - inset), DESK_CY + sy * (DESK_D / 2 - inset), leg_h / 2))
    ah, at = 0.085, 0.02
    az = leg_h - ah / 2
    for sy in (-1, 1):
        fr.add(p_box(DESK_L - 2 * inset - 0.05, at, ah, 0.002), loc=(DESK_CX, DESK_CY + sy * (DESK_D / 2 - inset), az))
    for sx in (-1, 1):
        fr.add(p_box(at, DESK_D - 2 * inset - 0.05, ah, 0.002), loc=(DESK_CX + sx * (DESK_L / 2 - inset), DESK_CY, az))
    fr.finish('DeskFrame', [M['wood']], atlas=0, texw=1.1)


def build_chair(M):
    ch = MB()
    ch.add(p_box(0.42, 0.40, 0.028, 0.008, 3), loc=(0, 0, 0.45))
    tilt = math.radians(7)
    for sx in (-1, 1):
        ch.add(p_cyl(0.0135, 0.44, 14, 0.0175), loc=(sx * 0.17, 0.155, 0.22), rot=(math.radians(-3), sx * math.radians(2), 0))
        # 后腿一直伸上去做靠背立柱，略向后仰
        ch.add(p_cyl(0.0135, 0.84, 14, 0.0125), loc=(sx * 0.17, -0.175 - 0.018, 0.42), rot=(tilt, sx * math.radians(1.5), 0))
        ch.add(p_box(0.018, 0.30, 0.02, 0.003), loc=(sx * 0.17, -0.01, 0.21))
    ch.add(p_box(0.32, 0.018, 0.02, 0.003), loc=(0, 0.15, 0.25))

    # 靠背：一条向后弯的板
    def back(u, v, off):
        a = (u - 0.5) * 0.86
        r = 0.46
        return (r * math.sin(a), -0.215 - (0.80 + 0.11 * v - 0.43) * math.tan(tilt) - r * (1 - math.cos(a)) * 0.55 + off,
                0.755 + 0.11 * v)

    front = p_grid(14, 2, lambda u, v: back(u, v, 0.0), flip=True, uv=False)
    rear = p_grid(14, 2, lambda u, v: back(u, v, -0.014), uv=False)
    ch.add(front)
    ch.add(rear)

    # 封边：上下左右四条窄面
    def strip(pa, pb):
        bm = bmesh.new()
        n = len(pa)
        va = [bm.verts.new(p) for p in pa]
        vb = [bm.verts.new(p) for p in pb]
        for i in range(n - 1):
            bm.faces.new((va[i], va[i + 1], vb[i + 1], vb[i]))
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
        return bm

    us = [i / 14 for i in range(15)]
    ch.add(strip([back(u, 1, 0) for u in us], [back(u, 1, -0.014) for u in us]))
    ch.add(strip([back(u, 0, 0) for u in us], [back(u, 0, -0.014) for u in us]))
    for u in (0, 1):
        ch.add(strip([back(u, v, 0) for v in (0, 0.5, 1)], [back(u, v, -0.014) for v in (0, 0.5, 1)]))
    # 椅子往外拉开了一点，像是人刚起身
    return ch.finish('Chair', [M['chair']], atlas=0, texw=1.0, loc=CHAIR, rot=(0, 0, math.radians(9)))


def build_lamp(M):
    lamp = MB()
    b = LAMP_BASE
    base = [(0.0005, 0.0), (0.074, 0.0), (0.0785, 0.004), (0.0785, 0.010), (0.073, 0.0155), (0.052, 0.021),
            (0.031, 0.026), (0.019, 0.033), (0.013, 0.043), (0.0105, 0.054), (0.0005, 0.055)]
    lamp.add(p_lathe(base, 64), loc=b)
    back = SHADE_TOP - SHADE_AIM * 0.07
    stem = [b + Vector((0, 0, 0.05)), b + Vector((0, 0, 0.20)), b + Vector((-0.002, -0.004, 0.335)),
            Vector((lerp(b.x, back.x, 0.45), lerp(b.y, back.y, 0.45), back.z + 0.035)), back + Vector((0.004, 0.006, 0.004)),
            SHADE_TOP + SHADE_AIM * 0.004]
    lamp.add(p_tube(stem, 0.0058, seg=14, per=10))
    # 灯罩：内壁（搪瓷）→ 沿口 → 外壁（黄铜）→ 顶上的收口
    shade = [(0.004, -0.004), (0.026, -0.0075), (0.044, -0.017), (0.0605, -0.0325), (0.0745, -0.0535),
             (0.0822, -0.0785), (0.084, -0.0825), (0.0862, -0.0835), (0.0845, -0.0795), (0.0765, -0.0535),
             (0.0625, -0.0315), (0.0455, -0.0155), (0.027, -0.0055), (0.0135, -0.001), (0.0115, 0.012),
             (0.0005, 0.013)]
    mat = Matrix.Translation(SHADE_TOP) @ SHADE_AIM.to_track_quat('-Z', 'Y').to_matrix().to_4x4()
    lamp.add(p_lathe(shade, 64), matrix=mat, mi=lambda j: 1 if j < 6 else 0)
    lamp.finish('Lamp', [M['brass'], M['enamel']], sharp=50, weighted=False, atlas=0, texw=2.6)

    bulb = MB().add(p_sphere(0.021, 24, 14), loc=BULB).finish('Bulb', [M['bulb']], weighted=False, atlas=0, texw=1.5)
    bulb.visible_shadow = False

    cord = [b + Vector((0.03, 0.074, 0.0045)), b + Vector((0.06, 0.12, 0.0045)),
            Vector((b.x + 0.085, DESK_BACK + 0.012, DESK_TOP - 0.01)), Vector((b.x + 0.09, DESK_BACK + 0.022, 0.45)),
            Vector((b.x + 0.16, DESK_BACK + 0.03, 0.10)), Vector((b.x + 0.42, DESK_BACK + 0.06, 0.05))]
    MB().add(p_tube(cord, 0.0028, seg=8, per=8)).finish('LampCord', [M['rubber']], weighted=False, atlas=0, texw=0.8)


def build_props(M):
    # ---- 信：对折成三折又摊开，两端微微翘起 ----
    lw, ll = 0.21, 0.297

    def letter(u, v):
        x, y = (u - 0.5) * lw, (v - 0.5) * ll
        over = max(0.0, abs(y) - ll / 6)
        z = 0.0007 + 0.045 * over + 0.0007 * math.exp(-((abs(y) - ll / 6) / 0.004) ** 2) + 0.13 * x * x
        return (x, y, z)

    ob = MB(uv=True).add(p_grid(8, 18, letter)).finish(
        'Letter', [M['paper']], weighted=False, sharp=180, atlas=0, texw=3.2,
        loc=LETTER, rot=(0, 0, math.radians(13)))
    ob['lm_grid'] = True

    # ---- 信封：背面朝上，封舌半开 ----
    # 信封身只有一层。背面的三片折边不单独建：同是白纸、只差零点几毫米，渲染里看不出来，
    # 烘进光照图却会把底下被盖住的那层黑从折边边缘渗出来，变成几道黑线。
    ew, eh = 0.22, 0.11
    env = MB()
    env.add(p_grid(6, 3, lambda u, v: ((u - 0.5) * ew, (v - 0.5) * eh, 0.0009 + 0.05 * ((u - 0.5) * ew) ** 2), uv=False))

    def sheet(pts):
        bm = bmesh.new()
        f = bm.faces.new([bm.verts.new((p[0], p[1], 0.0)) for p in pts])
        f.normal_update()
        if f.normal.z < 0:
            bmesh.ops.reverse_faces(bm, faces=[f])
        return bm

    hw, hh = ew / 2, eh / 2
    flap = sheet([(-hw, 0), (hw, 0), (0.02, 0.07), (-0.02, 0.07)])
    env.add(flap, matrix=Matrix.Translation((0, hh, 0.001)) @ Matrix.Rotation(math.radians(24), 4, 'X'))
    env.finish('Envelope', [M['envelope']], smooth=False, atlas=0, texw=3.0,
               loc=D(0.30, -0.15), rot=(0, 0, math.radians(21)))

    # ---- 钢笔 ----
    pen = MB()
    body = [(0.0005, 0.0), (0.003, 0.0006), (0.0048, 0.003), (0.0056, 0.009), (0.0058, 0.073),
            (0.0061, 0.0735), (0.0061, 0.0765), (0.0063, 0.077), (0.0063, 0.131), (0.0054, 0.1365),
            (0.0032, 0.1388), (0.0005, 0.1392)]
    lay = Matrix.Rotation(math.pi / 2, 4, 'Y') @ Matrix.Translation((0, 0, -0.07))
    pen.add(p_lathe(body, 24), matrix=Matrix.Translation((0, 0, 0.0063)) @ lay, mi=lambda j: 1 if j in (4, 5, 6) else 0)
    pen.add(p_box(0.036, 0.0032, 0.0012, 0.0005), loc=(0.041, 0, 0.0131), mi=1)
    pen.add(p_sphere(0.0024, 12, 8), loc=(0.024, 0, 0.0131), mi=1)
    pen.finish('Pen', [M['black'], M['brass_fine']], sharp=50, weighted=False, atlas=0, texw=3.0,
               loc=D(0.165, -0.20), rot=(0, 0, math.radians(52)))

    # ---- 座钟：停在 23:47 ----
    ck = MB(uv=True)
    r = 0.046
    case = [(0.0005, 0.0), (0.040, 0.0), (0.0455, 0.004), (0.0465, 0.026), (0.047, 0.0305), (0.0445, 0.0335),
            (0.0418, 0.0315), (0.0412, 0.029)]
    ck.add(p_lathe(case, 48))
    ck.add(p_disc(0.0413, 48, 0.0292, 0.0826), mi=1)
    for ang, ln, wd in ((353.5, 0.021, 0.0030), (282.0, 0.031, 0.0020)):
        a = math.radians(ang)
        hand = p_box(wd, ln, 0.0008)
        ck.add(hand, matrix=Matrix.Translation((0, 0, 0.0302)) @ Matrix.Rotation(-a, 4, 'Z') @ Matrix.Translation((0, ln / 2 - 0.004, 0)), mi=2)
    ck.add(p_cyl(0.003, 0.002, 12), loc=(0, 0, 0.0308), mi=2)
    for sx in (-1, 1):
        ck.add(p_sphere(0.006, 12, 8), loc=(sx * 0.026, -r - 0.001, 0.012), mi=0)
    # 立起来：盘面朝人，略向后仰
    clock = ck.finish('Clock', [M['brass_fine'], M['dial'], M['black']], sharp=50, weighted=False, atlas=0, texw=3.0)
    clock.location = D(0.535, 0.115, r + 0.0045)
    clock.rotation_euler = Euler((math.radians(90 - 9), 0, math.radians(-14)), 'XYZ')

    # ---- 手机：扣着放 ----
    ph = MB()
    ph.add(p_box(0.0715, 0.1467, 0.0078, 0.0034, 4), loc=(0, 0, 0.0039))
    ph.add(p_box(0.030, 0.030, 0.0016, 0.0007, 2), loc=(-0.016, 0.052, 0.0084))
    for dx, dy in ((-0.0225, 0.0585), (-0.0095, 0.0455)):
        ph.add(p_cyl(0.0058, 0.0012, 20), loc=(dx, dy, 0.0096))
    ph.finish('Phone', [M['phone']], atlas=0, texw=2.6, loc=D(0.39, -0.215), rot=(0, 0, math.radians(-63)))


def build_bookshelf(M):
    w, d, h, t = 0.90, 0.30, 2.0, 0.02
    x0, y0 = XL + 0.06, YF - 0.02 - d
    sh = MB()
    for x in (x0 + t / 2, x0 + w - t / 2):
        sh.add(p_box(t, d, h, 0.002), loc=(x, y0 + d / 2, h / 2))
    n_shelf = 6
    zs = [0.06 + i * (h - 0.08) / (n_shelf - 1) for i in range(n_shelf)]
    for z in zs:
        sh.add(p_box(w - 2 * t, d, t, 0.002), loc=(x0 + w / 2, y0 + d / 2, z))
    sh.add(p_box(w, 0.006, h), loc=(x0 + w / 2, y0 + d - 0.003, h / 2))
    sh.finish('Bookshelf', [M['wood_dark']], atlas=1, texw=0.6)

    rng = random.Random(41)
    palette = [(0.20, 0.09, 0.07), (0.08, 0.12, 0.10), (0.07, 0.09, 0.16), (0.42, 0.36, 0.27), (0.24, 0.19, 0.15),
               (0.50, 0.45, 0.37), (0.10, 0.07, 0.07), (0.30, 0.16, 0.09), (0.16, 0.16, 0.17), (0.33, 0.29, 0.16)]
    bk = MB(color=True)
    for i in range(n_shelf - 1):
        z = zs[i] + t / 2
        room = zs[i + 1] - zs[i] - t
        x = x0 + t + 0.01
        end = x0 + w - t - 0.01
        while x < end - 0.02:
            if rng.random() < 0.07:
                x += rng.uniform(0.03, 0.12)
                continue
            th = rng.uniform(0.016, 0.048)
            hh = min(room - 0.02, rng.uniform(0.19, 0.31))
            dd = rng.uniform(0.13, 0.21)
            c = palette[rng.randrange(len(palette))]
            c = tuple(max(0.0, ch * rng.uniform(0.75, 1.2)) for ch in c)
            lean = rng.uniform(-0.03, 0.03) if rng.random() < 0.8 else rng.uniform(0.12, 0.22)
            bk.add(p_box(th, dd, hh, 0.0015, 1), loc=(x + th / 2 + abs(lean) * hh * 0.5, y0 + 0.012 + dd / 2 + rng.uniform(0, 0.03), z + hh / 2),
                   rot=(0, lean, 0), color=c)
            x += th + abs(lean) * hh + rng.uniform(0.0005, 0.002)
    bk.finish('Books', [M['books']], weighted=False, atlas=1, texw=0.6)


def build_bed(M):
    x0, x1, y0, y1 = XL + 0.02, -0.84, 0.42, 2.42
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    MB().add(p_box(x1 - x0, y1 - y0, 0.24, 0.006), loc=(cx, cy, 0.12)) \
        .finish('BedFrame', [M['wood_dark']], atlas=1, texw=0.4)

    def soften(ob, level, strength, scale, seed):
        sub = ob.modifiers.new('Subd', 'SUBSURF')
        sub.levels = sub.render_levels = level
        tex = bpy.data.textures.new(f'{ob.name}Wrinkle', 'CLOUDS')
        tex.noise_scale = scale
        tex.noise_depth = 2
        dis = ob.modifiers.new('Wrinkle', 'DISPLACE')
        dis.texture = tex
        dis.texture_coords = 'GLOBAL'
        dis.strength = strength
        dis.mid_level = 0.5
        apply_modifiers(ob)
        for p in ob.data.polygons:
            p.use_smooth = True

    duvet = MB().add(p_box(x1 - x0 + 0.03, y1 - y0 + 0.03, 0.30, 0.075, 3), loc=(cx, cy, 0.39)) \
        .finish('Duvet', [M['blanket']], weighted=False, sharp=180, atlas=1, texw=0.55)
    soften(duvet, 2, 0.035, 0.22, 1)
    throw = MB().add(p_box(0.52, 0.62, 0.085, 0.035, 3), loc=(x1 - 0.30, y0 + 0.36, 0.585), rot=(0, 0, math.radians(6))) \
        .finish('Throw', [M['throw']], weighted=False, sharp=180, atlas=1, texw=0.7)
    soften(throw, 2, 0.02, 0.12, 2)


def build_lights():
    lights = bpy.data.collections.new('Lights')
    bpy.context.scene.collection.children.link(lights)

    lamp = bpy.data.lights.new('LampLight', 'POINT')
    lamp.energy = 4.5
    lamp.color = (1.0, 0.72, 0.43)
    lamp.shadow_soft_size = 0.02
    ob = bpy.data.objects.new('LampLight', lamp)
    ob.location = BULB + SHADE_AIM * 0.004
    ob.visible_camera = False
    lights.objects.link(ob)

    moon = bpy.data.lights.new('Moon', 'AREA')
    moon.shape = 'RECTANGLE'
    moon.size, moon.size_y = 1.3, 1.7
    moon.energy = 8.0
    moon.color = (0.50, 0.66, 1.0)
    ob = bpy.data.objects.new('Moon', moon)
    ob.location = (1.75, YF + 1.25, 2.95)
    ob.rotation_euler = (D(0.1, -0.1) - Vector(ob.location)).to_track_quat('-Z', 'Y').to_euler()
    ob.visible_camera = False
    ob.visible_glossy = False
    lights.objects.link(ob)

    # 夜里的一点冷色环境光：让床、书架在暗处还读得出轮廓（不参与反射）
    fill = bpy.data.lights.new('NightFill', 'AREA')
    fill.shape = 'SQUARE'
    fill.size = 2.4
    fill.energy = 1.2
    fill.color = (0.42, 0.56, 1.0)
    ob = bpy.data.objects.new('NightFill', fill)
    ob.location = (0.0, 1.7, H - 0.04)
    ob.visible_camera = False
    ob.visible_glossy = False
    lights.objects.link(ob)

    world = bpy.data.worlds.new('Night')
    world.use_nodes = True
    bg = world.node_tree.nodes.get('Background')
    bg.inputs[0].default_value = (0.010, 0.014, 0.030, 1.0)
    bg.inputs[1].default_value = 0.3
    bpy.context.scene.world = world


def build_cameras():
    cams = bpy.data.collections.new('Cameras')
    bpy.context.scene.collection.children.link(cams)
    for name, c in CAMS.items():
        cam = bpy.data.cameras.new(f'Cam_{name}')
        cam.lens = c['lens']
        cam.sensor_width = 36
        cam.sensor_fit = 'HORIZONTAL'
        cam.clip_start, cam.clip_end = 0.05, 60
        ob = bpy.data.objects.new(f'Cam_{name}', cam)
        ob.location = c['loc']
        yaw, pitch = math.radians(c['yaw']), math.radians(c['pitch'])
        fwd = Vector((math.sin(yaw) * math.cos(pitch), math.cos(yaw) * math.cos(pitch), math.sin(pitch)))
        ob.rotation_euler = fwd.to_track_quat('-Z', 'Y').to_euler()
        cam.dof.use_dof = True
        cam.dof.aperture_fstop = c['fstop']
        cam.dof.focus_distance = (Vector(c['focus']) - Vector(c['loc'])).length
        cams.objects.link(ob)
    ctrl = bpy.data.objects.new('Path_ctrl', None)
    ctrl.empty_display_size = 0.1
    ctrl.location = PATH_CTRL
    cams.objects.link(ctrl)


def build_surface(M):
    """第二幕的桌面背景：一大块同样的木头，灯在画面右上角外，光从那里漫下来。"""
    coll = bpy.data.collections.new('Surface')
    bpy.context.scene.collection.children.link(coll)
    w, h = 2.2, 1.2375                         # 比贴图的 1.5 m 小，画面里看不到重复
    plane = MB().add(p_rect((-w / 2 - 0.2, -h / 2 - 0.2, 0), (w + 0.4, 0, 0), (0, h + 0.4, 0), (0, 0, 1))) \
        .finish('SurfaceWood', [M['desk_top']], smooth=False, loc=SURFACE_AT)
    ROOM.objects.unlink(plane)
    coll.objects.link(plane)

    light = bpy.data.lights.new('SurfaceLight', 'POINT')
    light.energy = 60.0
    light.color = (1.0, 0.72, 0.43)
    light.shadow_soft_size = 0.05
    ob = bpy.data.objects.new('SurfaceLight', light)
    ob.location = SURFACE_AT + Vector((w / 2 + 0.35, h / 2 + 0.3, 0.95))
    coll.objects.link(ob)
    # 一点很弱的顶光，让照不到的那一侧也还看得出木纹
    fill = bpy.data.lights.new('SurfaceFill', 'AREA')
    fill.shape = 'RECTANGLE'
    fill.size, fill.size_y = 4.0, 3.0
    fill.energy = 1.6
    fill.color = (1.0, 0.80, 0.62)
    ob = bpy.data.objects.new('SurfaceFill', fill)
    ob.location = SURFACE_AT + Vector((0, 0, 3.0))
    ob.visible_glossy = False
    coll.objects.link(ob)

    cam = bpy.data.cameras.new('Cam_surface')
    cam.type = 'ORTHO'
    cam.ortho_scale = w
    cam.clip_start, cam.clip_end = 0.1, 20
    ob = bpy.data.objects.new('Cam_surface', cam)
    ob.location = SURFACE_AT + Vector((0, 0, 4))
    coll.objects.link(ob)


def build_scene():
    global ROOM
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.name = 'Room'
    ROOM = bpy.data.collections.new('Room')
    scene.collection.children.link(ROOM)
    M = make_materials()
    build_shell(M)
    build_window(M)
    build_desk(M)
    build_chair(M)
    build_lamp(M)
    build_props(M)
    build_bookshelf(M)
    build_bed(M)
    build_surface(M)
    build_lights()
    build_cameras()
    bpy.context.view_layer.update()
    os.makedirs(os.path.dirname(BLEND), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=BLEND, check_existing=False)


# =====================================================================
# 渲染
# =====================================================================
SAMPLES = 800     # 成片（静帧和烘焙）的采样数，固定跑满


def setup_cycles(scene, samples, adaptive=False):
    scene.render.engine = 'CYCLES'
    prefs = bpy.context.preferences.addons['cycles'].preferences
    try:
        prefs.compute_device_type = 'METAL'
        prefs.get_devices()
        for d in prefs.devices:
            d.use = d.type == 'METAL'
        scene.cycles.device = 'GPU'
    except Exception:
        scene.cycles.device = 'CPU'
    c = scene.cycles
    c.samples = samples
    # 成片不开自适应采样：这间屋子大半是暗的，自适应会在暗处提前收手，
    # 降噪器再把剩下的噪点“脑补”成墙上一道道划痕。只有小样为了快才开。
    c.use_adaptive_sampling = adaptive
    c.adaptive_threshold = 0.012
    c.use_denoising = True
    c.denoiser = 'OPENIMAGEDENOISE'
    c.denoising_input_passes = 'RGB_ALBEDO_NORMAL'
    c.max_bounces, c.diffuse_bounces, c.glossy_bounces = 8, 5, 4
    c.transmission_bounces, c.transparent_max_bounces = 8, 8
    c.caustics_reflective = c.caustics_refractive = False
    c.sample_clamp_indirect = 8.0
    scene.view_settings.view_transform = 'AgX'
    scene.view_settings.look = LOOK
    scene.render.film_transparent = False


def set_lamp(on):
    """灯亮 / 灯灭：点光源和灯泡的自发光一起开关。"""
    bpy.data.objects['LampLight'].hide_render = not on
    em = bpy.data.materials['Bulb'].node_tree.nodes.get('Emission')
    em.inputs['Strength'].default_value = 34.0 if on else 0.0


def bloom(rgb, thresh=1.0, strength=0.22):
    """高光泛光：只对超过阈值的部分做三档模糊再叠回去（在线性空间里做，之后才过显示变换）。"""
    h, w = rgb.shape[:2]
    lum = rgb.max(axis=2)
    bright = rgb * np.clip((lum - thresh) / np.maximum(lum, 1e-6), 0, 1)[..., None]
    f = 4
    small = bright[:h // f * f, :w // f * f].reshape(h // f, f, w // f, f, 3).mean(axis=(1, 3))
    s = w / 2560.0
    acc = sum(wt * _blur(small, sig * s) for sig, wt in ((2.5, 0.45), (8.0, 0.35), (24.0, 0.20)))
    up = np.repeat(np.repeat(acc, f, axis=0), f, axis=1)
    out = rgb.copy()
    out[:up.shape[0], :up.shape[1]] += strength * _blur(up, 1.5)
    return out


def render_still(scene, cam_name, out_path, exposure, w, h, samples, lamp_on=True, adaptive=False):
    setup_cycles(scene, samples, adaptive)
    set_lamp(lamp_on)
    scene.camera = bpy.data.objects[f'Cam_{cam_name}']
    scene.render.resolution_x, scene.render.resolution_y, scene.render.resolution_percentage = w, h, 100
    exr = os.path.join(CACHE, '_render.exr')
    s = scene.render.image_settings
    s.file_format, s.color_mode, s.color_depth, s.exr_codec = 'OPEN_EXR', 'RGB', '32', 'ZIP'
    scene.render.filepath = exr
    bpy.ops.render.render(write_still=True)

    src = bpy.data.images.load(exr, check_existing=False)
    px = np.empty(w * h * 4, np.float32)
    src.pixels.foreach_get(px)
    bpy.data.images.remove(src)
    px = px.reshape(h, w, 4)
    px[..., :3] = bloom(px[..., :3])
    px[..., 3] = 1.0
    post = bpy.data.images.new('_post', w, h, alpha=False, float_buffer=True)
    post.pixels.foreach_set(px.ravel())
    scene.view_settings.exposure = exposure
    s.file_format, s.color_mode, s.quality = 'JPEG', 'RGB', 95
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    post.save_render(out_path, scene=scene)
    bpy.data.images.remove(post)
    set_lamp(True)
    print(f'[room] 渲染 {os.path.relpath(out_path, ROOT)}')


def anchors():
    return {
        'bulb': BULB, 'shade': SHADE_TOP + SHADE_AIM * 0.04, 'lampBase': LAMP_BASE, 'letter': LETTER,
        'deskFL': D(-DESK_L / 2, -DESK_D / 2), 'deskFR': D(DESK_L / 2, -DESK_D / 2),
        'deskBL': D(-DESK_L / 2, DESK_D / 2), 'deskBR': D(DESK_L / 2, DESK_D / 2),
        'winBL': Vector((WIN['x0'], YF, WIN['z0'])), 'winBR': Vector((WIN['x1'], YF, WIN['z0'])),
        'clock': D(0.535, 0.115, 0.05), 'phone': D(0.39, -0.215), 'chairBack': CHAIR + Vector((0, -0.215, 0.86)),
    }


def project(scene, cam_name, p):
    """世界坐标 → 画面坐标（x 向右，y 向下，0–1）。"""
    scene.render.resolution_x, scene.render.resolution_y = CAMS[cam_name]['res']
    v = world_to_camera_view(scene, bpy.data.objects[f'Cam_{cam_name}'], Vector(p))
    return [round(v.x, 4), round(1 - v.y, 4)]


def print_anchors(scene):
    for cam in CAMS:
        print(f'[room] {cam}: ' + '  '.join(f'{k}={project(scene, cam, p)}' for k, p in anchors().items()))


# =====================================================================
# 实时三维层：光照烘进图集，网格和机位导出给网页
# =====================================================================
def rt_objects(atlas=None):
    return [o for o in bpy.data.objects
            if o.type == 'MESH' and 'atlas' in o and (atlas is None or o['atlas'] == atlas)]


def _select(objs):
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]


def _uv_array(me, name):
    layer = me.uv_layers[name]
    data = np.empty(len(me.loops) * 2, np.float64)
    layer.uv.foreach_get('vector', data)
    return layer, data.reshape(-1, 2)


def cam_fov(name):
    """(纵向视场角, 画幅宽高比)。"""
    cam = bpy.data.objects[f'Cam_{name}'].data
    w, h = CAMS[name]['res']
    return 2 * math.atan(cam.sensor_width / 2 / cam.lens * h / w), w / h


def cam_look(name):
    """机位光轴上离信最近的那一点：镜头一路盯着它走（两端的盯点都在各自光轴上，所以起止朝向不变）。"""
    ob = bpy.data.objects[f'Cam_{name}']
    pos = ob.matrix_world.translation
    fwd = ob.matrix_world.to_quaternion() @ Vector((0, 0, -1))
    return pos + fwd * (LETTER - pos).dot(fwd)


def path_cam(t, pair):
    """进门镜头在 t ∈ [0, 1] 的机位：位置走二次贝塞尔，朝向始终对着在两个盯点之间移动的点（不带滚转），
    视锥半角正切线性插值。必须与 src/components/room/room3d.ts 里的插值一致——可见性剔除靠它。"""
    start, end = PAIRS[pair]
    w, c = bpy.data.objects[f'Cam_{start}'], bpy.data.objects[f'Cam_{end}']
    p0, p1, p2 = w.matrix_world.translation, bpy.data.objects['Path_ctrl'].matrix_world.translation, c.matrix_world.translation
    pos = (1 - t) ** 2 * p0 + 2 * t * (1 - t) * p1 + t * t * p2
    quat = (cam_look(start).lerp(cam_look(end), t) - pos).to_track_quat('-Z', 'Y')
    (f0, a0), (f1, a1) = cam_fov(start), cam_fov(end)
    ty0, ty1 = math.tan(f0 / 2), math.tan(f1 / 2)
    return pos, quat, lerp(ty0, ty1, t), lerp(ty0 * a0, ty1 * a1, t)


def compute_visibility(n_cams=36, margin=1.2):
    """沿镜头轨迹逐面判可见：整段镜头里都看不到的面（桌底、书背、柜子内壁……）不占图集、也不导出。"""
    scene = bpy.context.scene
    hidden = [o for o in bpy.data.objects if o.type == 'MESH' and o.name == 'WindowGlass']
    for o in hidden:
        o.hide_viewport = True
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    cams = []
    for pair in PAIRS:
        for i in range(n_cams):
            pos, quat, ty, tx = path_cam(i / (n_cams - 1), pair)
            cams.append((pos.copy(), quat.inverted(), ty * margin, tx * margin))
    rng = random.Random(3)
    stats = {}
    for ob in rt_objects():
        me = ob.data
        mw = ob.matrix_world
        vis = [False] * len(me.polygons)
        for pi, poly in enumerate(me.polygons):
            vs = [mw @ me.vertices[v].co for v in poly.vertices]
            center = sum(vs, Vector()) / len(vs)
            pts = [center] + [v.lerp(center, 0.06) for v in vs]
            if poly.area > 0.02:
                for _ in range(14):
                    ws = [rng.random() for _ in vs]
                    pts.append(sum((v * w_ for v, w_ in zip(vs, ws)), Vector()) / sum(ws))
            seen = False
            for pos, qinv, ty, tx in cams:
                for pt in pts:
                    d = pt - pos
                    pc = qinv @ d
                    if pc.z > -0.05 or abs(pc.y) > -pc.z * ty or abs(pc.x) > -pc.z * tx:
                        continue
                    dist = d.length
                    hit, loc, _n, _i, _o, _m = scene.ray_cast(dg, pos, d / dist, distance=dist - 0.002)
                    if not hit:
                        seen = True
                        break
                if seen:
                    break
            vis[pi] = seen
        attr = me.attributes.get('rt_vis') or me.attributes.new('rt_vis', 'BOOLEAN', 'FACE')
        attr.data.foreach_set('value', vis)
        stats[ob.name] = f'{sum(vis)}/{len(vis)}'
    for o in hidden:
        o.hide_viewport = False
    bpy.context.view_layer.update()
    print(f'[room] 可见面：{stats}')


def _vis(me):
    v = np.zeros(len(me.polygons), bool)
    me.attributes['rt_vis'].data.foreach_get('value', v)
    return v


def _poly_uv_area(me, uv, mask):
    a = 0.0
    for p in me.polygons:
        if mask[p.index]:
            pts = uv[p.loop_start:p.loop_start + p.loop_total]
            a += 0.5 * abs(np.dot(pts[:, 0], np.roll(pts[:, 1], -1)) - np.dot(pts[:, 1], np.roll(pts[:, 0], -1)))
    return a


def _edit_visible(objs):
    """进编辑模式，只选中可见面（展开 / 排版都只作用于选中的面）。"""
    bpy.context.scene.tool_settings.mesh_select_mode = (False, False, True)
    for ob in objs:
        me = ob.data
        me.vertices.foreach_set('select', np.zeros(len(me.vertices), bool))
        me.edges.foreach_set('select', np.zeros(len(me.edges), bool))
        me.polygons.foreach_set('select', _vis(me))
        me.polygons.foreach_set('hide', np.zeros(len(me.polygons), bool))
    _select(objs)
    bpy.ops.object.mode_set(mode='EDIT')


def make_lightmap_uvs():
    """每个物体各自展开，按「真实面积 × 权重」统一像素密度，再按图集一起排版。"""
    bpy.context.scene.tool_settings.use_uv_select_sync = True
    for ob in [o for o in rt_objects() if not _vis(o.data).any()]:
        del ob['atlas']                                   # 整个物体都看不到
    for ob in rt_objects():
        me = ob.data
        vis = _vis(me)
        if 'lm' in me.uv_layers:
            me.uv_layers.remove(me.uv_layers['lm'])
        grid = ob.get('lm_grid') and 'tex' in me.uv_layers
        if grid:
            # 规则网格（窗帘、信纸）：沿用自带的 UV 网格，只把两个方向各自换算成真实长度，整片一个岛
            _, tex = _uv_array(me, 'tex')
            co = np.array([v.co[:] for v in me.vertices])
            lu = lv = du = dv = 0.0
            for p_ in me.polygons:
                li = list(range(p_.loop_start, p_.loop_start + p_.loop_total))
                for a_, b_ in zip(li, li[1:] + li[:1]):
                    d3 = np.linalg.norm(co[me.loops[a_].vertex_index] - co[me.loops[b_].vertex_index])
                    duv = np.abs(tex[a_] - tex[b_])
                    if duv[0] > duv[1]:
                        lu, du = lu + d3, du + duv[0]
                    else:
                        lv, dv = lv + d3, dv + duv[1]
            lm_uv = tex * np.array([lu / max(du, 1e-9), lv / max(dv, 1e-9)])
        me.uv_layers.new(name='lm', do_init=False)
        me.uv_layers.active = me.uv_layers['lm']
        layer, uv = _uv_array(me, 'lm')
        if grid:
            uv[:] = lm_uv
        else:
            uv[:] = 0.0
            layer.uv.foreach_set('vector', uv.ravel())
            _edit_visible([ob])
            bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.0, area_weight=0.0,
                                     correct_aspect=True, scale_to_bounds=False)
            bpy.ops.uv.average_islands_scale()
            bpy.ops.object.mode_set(mode='OBJECT')
            layer, uv = _uv_array(me, 'lm')
        area3d = sum(p_.area for p_ in me.polygons if vis[p_.index])
        uv *= float(ob['texw']) * math.sqrt(area3d / max(_poly_uv_area(me, uv, vis), 1e-12))
        loop_vis = np.repeat(vis, [p_.loop_total for p_ in me.polygons])
        uv[~loop_vis] = 0.0
        layer.uv.foreach_set('vector', uv.ravel())

    for atlas in (0, 1):
        objs = rt_objects(atlas)
        for ob in objs:
            ob.data.uv_layers.active = ob.data.uv_layers['lm']
        _edit_visible(objs)
        bpy.ops.uv.pack_islands(rotate=True, rotate_method='CARDINAL', scale=True, merge_overlap=False,
                                margin_method='FRACTION', margin=0.004, shape_method='AABB')
        bpy.ops.object.mode_set(mode='OBJECT')
        dens, used = {}, 0.0
        for ob in objs:
            me = ob.data
            vis = _vis(me)
            layer, uv = _uv_array(me, 'lm')
            loop_vis = np.repeat(vis, [p_.loop_total for p_ in me.polygons])
            uv[~loop_vis] = 0.0
            layer.uv.foreach_set('vector', uv.ravel())
            a = _poly_uv_area(me, uv, vis)
            used += a
            dens[ob.name] = round(2048 * math.sqrt(a / max(sum(p_.area for p_ in me.polygons if vis[p_.index]), 1e-12)))
        print(f'[room] 图集 {atlas}：占用 {used:.0%}，像素密度(px/m @2048) {dens}')


def bake_atlases(scene, size, samples):
    setup_cycles(scene, samples)
    set_lamp(True)
    scene.camera = bpy.data.objects['Cam_close']        # 高光按首屏机位算：镜头落定时反光是对的
    scene.render.resolution_x, scene.render.resolution_y = CAMS['close']['res']
    bk = scene.render.bake
    scene.cycles.bake_type = 'COMBINED'
    bk.target = 'IMAGE_TEXTURES'
    bk.view_from = 'ACTIVE_CAMERA'
    bk.use_clear = False
    bk.margin = max(4, size // 256)
    bk.margin_type = 'EXTEND'
    for flag in ('use_pass_direct', 'use_pass_indirect', 'use_pass_diffuse', 'use_pass_glossy',
                 'use_pass_transmission', 'use_pass_emit'):
        setattr(bk, flag, True)
    scene.view_settings.exposure = EXPOSURE['on']
    s = scene.render.image_settings
    s.file_format, s.color_mode, s.color_depth, s.compression = 'PNG', 'RGB', '8', 60

    for atlas in (0, 1):
        img = bpy.data.images.new(f'_atlas{atlas}', size, size, alpha=False, float_buffer=True)
        objs = rt_objects(atlas)
        for ob in objs:
            ob.data.uv_layers.active = ob.data.uv_layers['lm']
            for slot in ob.material_slots:
                nt = slot.material.node_tree
                node = nt.nodes.get('BakeTarget') or nt.nodes.new('ShaderNodeTexImage')
                node.name = 'BakeTarget'
                node.image = img
                for n in nt.nodes:
                    n.select = False
                node.select = True
                nt.nodes.active = node
        _select(objs)
        bpy.ops.object.bake(type='COMBINED', uv_layer='lm', use_clear=False, margin=bk.margin, margin_type='EXTEND')
        out = os.path.join(CACHE, f'atlas-{atlas}.png')
        img.save_render(out, scene=scene)
        bpy.data.images.remove(img)
        print(f'[room] 烘焙 {os.path.relpath(out, ROOT)}（{len(objs)} 个物体）')
    for m in bpy.data.materials:
        node = m.node_tree.nodes.get('BakeTarget') if m.node_tree else None
        if node:
            m.node_tree.nodes.remove(node)


def export_mesh():
    """网格 → src/assets/room3d/room.bin：位置 / UV 量化成 uint16，按图集分组；无光照，所以不带法线。"""
    dg = bpy.context.evaluated_depsgraph_get()
    raw = {0: [], 1: []}
    for ob in rt_objects():
        ev = ob.evaluated_get(dg)
        me = ev.to_mesh()
        me.calc_loop_triangles()
        n = len(me.loop_triangles)
        tl = np.empty(n * 3, np.int32)
        tv = np.empty(n * 3, np.int32)
        tp = np.empty(n, np.int32)
        me.loop_triangles.foreach_get('loops', tl)
        me.loop_triangles.foreach_get('vertices', tv)
        me.loop_triangles.foreach_get('polygon_index', tp)
        keep = np.repeat(_vis(ob.data)[tp], 3)
        tl, tv = tl[keep], tv[keep]
        co = np.empty(len(me.vertices) * 3, np.float64)
        me.vertices.foreach_get('co', co)
        mw = np.array(ob.matrix_world)
        world = co.reshape(-1, 3) @ mw[:3, :3].T + mw[:3, 3]
        _, uv = _uv_array(me, 'lm')
        raw[int(ob['atlas'])].append((world[tv], uv[tl]))
        ev.to_mesh_clear()

    allpos = np.concatenate([p for g in raw.values() for p, _ in g])
    lo = allpos.min(axis=0)
    size = np.maximum(allpos.max(axis=0) - lo, 1e-6)
    groups, blobs, offset = [], [], 0

    def push(arr):
        nonlocal offset
        b = arr.tobytes()
        b += b'\0' * (-len(b) % 4)
        blobs.append(b)
        start = offset
        offset += len(b)
        return start

    for atlas in (0, 1):
        pos = np.concatenate([p for p, _ in raw[atlas]])
        uv = np.concatenate([u for _, u in raw[atlas]])
        qp = np.round((pos - lo) / size * 65535).astype(np.uint16)
        quv = np.round(np.clip(np.stack([uv[:, 0], 1 - uv[:, 1]], axis=1), 0, 1) * 65535).astype(np.uint16)
        verts, index = np.unique(np.concatenate([qp, quv], axis=1), axis=0, return_inverse=True)
        index = index.reshape(-1)
        idx32 = len(verts) > 65535
        groups.append(dict(atlas=atlas, verts=int(len(verts)), indices=int(len(index)), idx32=bool(idx32),
                           pos=push(np.ascontiguousarray(verts[:, :3])), uv=push(np.ascontiguousarray(verts[:, 3:])),
                           idx=push(index.astype(np.uint32 if idx32 else np.uint16))))
    head = json.dumps(dict(min=[round(float(v), 5) for v in lo], size=[round(float(v), 5) for v in size],
                           groups=groups), separators=(',', ':')).encode()
    head += b' ' * (-len(head) % 4)
    os.makedirs(OUT_3D, exist_ok=True)
    path = os.path.join(OUT_3D, 'room.bin')
    with open(path, 'wb') as f:
        f.write(b'MRR1' + struct.pack('<I', len(head)) + head + b''.join(blobs))
    tris = sum(g['indices'] for g in groups) // 3
    print(f'[room] 网格 {os.path.relpath(path, ROOT)}：{tris} 个三角形，{sum(g["verts"] for g in groups)} 个顶点，'
          f'{os.path.getsize(path) // 1024} KB')


def cover_box(vw, vh, ar, zoom, fx, fy):
    """与 desk.css 里 .scene-cover 相同的铺满算法：返回图片盒子在视口里的 (left, top, width, height)。"""
    bw = max(vw, vh * ar * zoom)
    bh = bw / ar
    return min(0.0, max(vw - bw, vw / 2 - fx * bw)), min(0.0, max(vh - bh, vh / 2 - fy * bh)), bw, bh


def fit_push(a, b):
    """最小二乘求相似变换 b ≈ s·a + t，返回 (s, 不动点)。"""
    am, bm_ = a.mean(axis=0), b.mean(axis=0)
    s_fit = float(((a - am) * (b - bm_)).sum() / ((a - am) ** 2).sum())
    return s_fit, (bm_ - s_fit * am) / (1 - s_fit)


def export_scene_json(scene):
    """机位、灯的位置、裁切和 2.5D 退路的推镜参数 → src/assets/room/scene.json（站点组件直接读）。"""
    cams = {}
    for name in CAMS:
        ob = bpy.data.objects[f'Cam_{name}']
        fov, aspect = cam_fov(name)
        cams[name] = dict(pos=[round(v, 5) for v in ob.matrix_world.translation],
                          look=[round(v, 5) for v in cam_look(name)], fovY=round(fov, 6), aspect=round(aspect, 6))
    pts = anchors()
    proj = {cam: {k: project(scene, cam, p) for k, p in pts.items()} for cam in CAMS}
    # 信纸在每幅画面里占的范围 [x0, y0, x1, y1]：首屏的文字栏据此让开它
    sheet = bpy.data.objects['Letter']
    sheet_pts = [sheet.matrix_world @ v.co for v in sheet.data.vertices]

    def letter_box(cam):
        xy = [project(scene, cam, p) for p in sheet_pts]
        return [min(p[0] for p in xy), min(p[1] for p in xy), max(p[0] for p in xy), max(p[1] for p in xy)]
    keys = ['bulb', 'letter', 'lampBase', 'clock', 'phone']
    # 2.5D 推镜：远景绕 (ox, oy) 放大 s 倍，尽量把灯、信、钟对到近景里的位置。
    # 两张图铺满视口的方式可能不同，所以放到一块参考屏上按像素拟合，再换回远景盒子的归一化坐标。
    push = {}
    for pair, (vw, vh) in (('l', (1600.0, 900.0)), ('p', (390.0, 800.0))):
        a_name, b_name = PAIRS[pair]
        al, at, abw, abh = cover_box(vw, vh, cams[a_name]['aspect'], **CROP[a_name])
        bl, bt, bbw, bbh = cover_box(vw, vh, cams[b_name]['aspect'], **CROP[b_name])
        a_px = np.array([[al + proj[a_name][k][0] * abw, at + proj[a_name][k][1] * abh] for k in keys])
        b_px = np.array([[bl + proj[b_name][k][0] * bbw, bt + proj[b_name][k][1] * bbh] for k in keys])
        s_fit, o_px = fit_push(a_px, b_px)
        push[pair] = dict(scale=round(s_fit, 4), ox=round(float((o_px[0] - al) / abw), 4), oy=round(float((o_px[1] - at) / abh), 4))
    data = dict(
        near=0.05, far=40.0,
        cams=cams,
        ctrl=[round(v, 5) for v in bpy.data.objects['Path_ctrl'].matrix_world.translation],
        bulb=[round(v, 5) for v in pts['bulb']],
        stills={cam: dict(lamp=proj[cam]['bulb'], letter=proj[cam]['letter'], letterBox=letter_box(cam))
                for cam in CAMS},
        pairs={k: list(v) for k, v in PAIRS.items()},
        crop=CROP,
        push=push,
    )
    path = os.path.join(OUT_STILLS, 'scene.json')
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)
        f.write('\n')
    print(f'[room] {os.path.relpath(path, ROOT)}：push={data["push"]}')


# =====================================================================
# 入口
# =====================================================================
def main():
    os.makedirs(CACHE, exist_ok=True)
    if '--from-blend' in FLAGS:
        bpy.ops.wm.open_mainfile(filepath=BLEND)
    else:
        build_scene()
    scene = bpy.context.scene
    print_anchors(scene)

    if 'preview' in STEPS:
        opt = dict(a[2:].split('=') for a in FLAGS if '=' in a)
        pw = int(opt.get('width', 960))
        for name, cam, on in SHOTS:
            if 'only' in opt and name not in opt['only'].split(','):
                continue
            rw, rh = RES[cam]
            k = pw / 2560
            render_still(scene, cam, os.path.join(CACHE, f'preview-{name}.jpg'), EXPOSURE['on' if on else 'off'],
                         int(rw * k) // 4 * 4, int(rh * k) // 4 * 4, int(opt.get('samples', 96)), on, adaptive=True)

    if 'bake' in STEPS:
        opt = dict(a[2:].split('=') for a in FLAGS if '=' in a)
        compute_visibility()
        make_lightmap_uvs()
        bake_atlases(scene, int(opt.get('atlas', 2048)), int(opt.get('samples', SAMPLES)))
        export_mesh()
        export_scene_json(scene)
        bpy.ops.wm.save_as_mainfile(filepath=BLEND, check_existing=False)
    elif 'json' in STEPS:
        export_scene_json(scene)

    if 'stills' in STEPS:
        opt = dict(a[2:].split('=') for a in FLAGS if '=' in a)
        for name, cam, on in SHOTS:
            if 'only' in opt and name not in opt['only'].split(','):
                continue
            render_still(scene, cam, os.path.join(OUT_STILLS, f'{name}.jpg'), EXPOSURE['on' if on else 'off'],
                         *RES[cam], int(opt.get('samples', SAMPLES)), on)


main()
