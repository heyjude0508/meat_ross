"""Cute shokupan-loaf hero: loaf head (ref 1) + red-suit body/limbs (ref 2).

Meters, Y-up, facing +Z, origin at ground between the boots.
"""
from __future__ import annotations

import json
import math
import os
import struct
from collections import defaultdict

OUT_GLB = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "Art", "Characters", "BreadLoaf", "SM_BreadLoaf.glb")
)

MATS = {
    "crumb":   {"color": (0.97, 0.93, 0.86, 1.0), "rough": 0.86, "metal": 0.0},
    "crust":   {"color": (0.86, 0.64, 0.38, 1.0), "rough": 0.80, "metal": 0.0},
    "blush":   {"color": (0.98, 0.62, 0.70, 1.0), "rough": 0.70, "metal": 0.0},
    "face":    {"color": (0.18, 0.10, 0.08, 1.0), "rough": 0.55, "metal": 0.0},
    "suit":    {"color": (0.88, 0.10, 0.12, 1.0), "rough": 0.62, "metal": 0.0},
    "yellow":  {"color": (1.00, 0.84, 0.10, 1.0), "rough": 0.55, "metal": 0.0},
    "buckle":  {"color": (0.96, 0.96, 0.97, 1.0), "rough": 0.40, "metal": 0.15},
    "skirt":   {"color": (0.88, 0.10, 0.12, 1.0), "rough": 0.62, "metal": 0.0},
}


def add(a, b):
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def mul(a, s):
    return (a[0] * s, a[1] * s, a[2] * s)


def dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def cross(a, b):
    return (a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0])


def length(a):
    return math.sqrt(dot(a, a))


def normalize(a):
    l = length(a)
    return mul(a, 1.0 / l) if l > 1e-12 else (0.0, 1.0, 0.0)


def lerp(a, b, t):
    return add(mul(a, 1.0 - t), mul(b, t))


def cpow(w, n):
    return math.copysign(abs(w) ** n, w)


def basis_from_y(direction):
    y = normalize(direction)
    up = (0.0, 0.0, 1.0) if abs(y[1]) > 0.92 else (0.0, 1.0, 0.0)
    x = normalize(cross(up, y))
    if length(x) < 1e-6:
        x = (1.0, 0.0, 0.0)
    z = normalize(cross(x, y))
    x = normalize(cross(y, z))
    return x, y, z


def xform(p, origin, axes, scale=(1, 1, 1)):
    x, y, z = axes
    q = (p[0] * scale[0], p[1] * scale[1], p[2] * scale[2])
    return add(origin, add(add(mul(x, q[0]), mul(y, q[1])), mul(z, q[2])))


class Mesh:
    def __init__(self):
        self.parts = defaultdict(lambda: {"pos": [], "nrm": [], "uv": [], "idx": []})

    def emit(self, mat, pos, nrm, uv):
        part = self.parts[mat]
        i = len(part["pos"]) // 3
        part["pos"].extend(pos)
        part["nrm"].extend(nrm)
        part["uv"].extend(uv)
        return i

    def tri(self, mat, i0, i1, i2):
        self.parts[mat]["idx"].extend((i0, i1, i2))

    def add_tri(self, mat, p0, p1, p2, n=None, uv0=(0, 0), uv1=(1, 0), uv2=(0.5, 1)):
        n = n or normalize(cross(sub(p1, p0), sub(p2, p0)))
        i0 = self.emit(mat, p0, n, uv0)
        i1 = self.emit(mat, p1, n, uv1)
        i2 = self.emit(mat, p2, n, uv2)
        self.tri(mat, i0, i1, i2)

    def add_quad(self, mat, p0, p1, p2, p3, n=None):
        n = n or normalize(cross(sub(p1, p0), sub(p3, p0)))
        self.add_tri(mat, p0, p1, p2, n, (0, 0), (1, 0), (1, 1))
        self.add_tri(mat, p0, p2, p3, n, (0, 0), (1, 1), (0, 1))

    def stats(self):
        verts = sum(len(p["pos"]) // 3 for p in self.parts.values())
        tris = sum(len(p["idx"]) // 3 for p in self.parts.values())
        return verts, tris, list(self.parts.keys())


def add_lathe_cap(mesh, mat, center, normal, radius, segs):
    n = normalize(normal)
    x, _, z = basis_from_y(n)
    c = mesh.emit(mat, center, n, (0.5, 0.5))
    ring = []
    for i in range(segs):
        a = 2.0 * math.pi * i / segs
        p = add(center, add(mul(x, math.cos(a) * radius), mul(z, math.sin(a) * radius)))
        ring.append(mesh.emit(mat, p, n, (0.5 + 0.5 * math.cos(a), 0.5 + 0.5 * math.sin(a))))
    for i in range(segs):
        mesh.tri(mat, c, ring[i], ring[(i + 1) % segs])


def add_sphere(mesh, mat, center, radius, segs=14, stacks=10, scale=(1, 1, 1)):
    axes = ((1, 0, 0), (0, 1, 0), (0, 0, 1))
    rows = []
    for i in range(stacks + 1):
        v = i / stacks
        phi = math.pi * (v - 0.5)
        cy, sy = math.cos(phi), math.sin(phi)
        row = []
        for j in range(segs + 1):
            u = j / segs
            th = 2.0 * math.pi * u
            local = (math.cos(th) * cy, sy, math.sin(th) * cy)
            p = xform(local, center, axes, (radius * scale[0], radius * scale[1], radius * scale[2]))
            n = normalize((local[0] / max(scale[0], 1e-6),
                           local[1] / max(scale[1], 1e-6),
                           local[2] / max(scale[2], 1e-6)))
            row.append(mesh.emit(mat, p, n, (u, v)))
        rows.append(row)
    for i in range(stacks):
        for j in range(segs):
            a, b = rows[i][j], rows[i][j + 1]
            c, d = rows[i + 1][j + 1], rows[i + 1][j]
            mesh.tri(mat, a, b, c)
            mesh.tri(mat, a, c, d)


def add_cylinder(mesh, mat, p0, p1, radius, segs=12, caps=True, radius1=None):
    radius1 = radius if radius1 is None else radius1
    axis = sub(p1, p0)
    if length(axis) < 1e-8:
        return
    x, y, z = basis_from_y(axis)
    rings = []
    for t, r in ((0.0, radius), (1.0, radius1)):
        center = lerp(p0, p1, t)
        ring = []
        for i in range(segs + 1):
            a = 2.0 * math.pi * i / segs
            offset = add(mul(x, math.cos(a) * r), mul(z, math.sin(a) * r))
            ring.append(mesh.emit(mat, add(center, offset), normalize(offset), (i / segs, t)))
        rings.append(ring)
    for i in range(segs):
        a, b = rings[0][i], rings[0][i + 1]
        c, d = rings[1][i + 1], rings[1][i]
        mesh.tri(mat, a, b, c)
        mesh.tri(mat, a, c, d)
    if caps:
        add_lathe_cap(mesh, mat, p0, mul(y, -1), radius, segs)
        add_lathe_cap(mesh, mat, p1, y, radius1, segs)


def add_capsule(mesh, mat, p0, p1, radius, segs=12, stacks=6):
    add_cylinder(mesh, mat, p0, p1, radius, segs=segs, caps=False)
    add_sphere(mesh, mat, p0, radius, segs=segs, stacks=stacks)
    add_sphere(mesh, mat, p1, radius, segs=segs, stacks=stacks)


def add_torus(mesh, mat, center, normal, major, minor, segs=18, tube=10, arc=1.0):
    x, y, z = basis_from_y(normal)
    u_count = max(3, int(segs * arc))
    rows = []
    for i in range(u_count + 1):
        u = (i / u_count) * arc
        a = 2.0 * math.pi * u
        ring_c = add(center, add(mul(x, math.cos(a) * major), mul(z, math.sin(a) * major)))
        radial = normalize(sub(ring_c, center))
        row = []
        for j in range(tube + 1):
            v = j / tube
            b = 2.0 * math.pi * v
            n = add(mul(radial, math.cos(b)), mul(y, math.sin(b)))
            p = add(ring_c, mul(n, minor))
            row.append(mesh.emit(mat, p, normalize(n), (u, v)))
        rows.append(row)
    for i in range(u_count):
        for j in range(tube):
            a, b = rows[i][j], rows[i][j + 1]
            c, d = rows[i + 1][j + 1], rows[i + 1][j]
            mesh.tri(mat, a, b, c)
            mesh.tri(mat, a, c, d)


def add_box(mesh, mat, center, hx, hy, hz, axes=None):
    axes = axes or ((1, 0, 0), (0, 1, 0), (0, 0, 1))
    x, y, z = axes
    def c(ix, iy, iz):
        return add(center, add(add(mul(x, ix * hx), mul(y, iy * hy)), mul(z, iz * hz)))
    faces = (
        (c(1, -1, -1), c(1, 1, -1), c(1, 1, 1), c(1, -1, 1), x),
        (c(-1, -1, 1), c(-1, 1, 1), c(-1, 1, -1), c(-1, -1, -1), mul(x, -1)),
        (c(-1, 1, -1), c(-1, 1, 1), c(1, 1, 1), c(1, 1, -1), y),
        (c(-1, -1, 1), c(-1, -1, -1), c(1, -1, -1), c(1, -1, 1), mul(y, -1)),
        (c(-1, -1, 1), c(1, -1, 1), c(1, 1, 1), c(-1, 1, 1), z),
        (c(1, -1, -1), c(-1, -1, -1), c(-1, 1, -1), c(1, 1, -1), mul(z, -1)),
    )
    for p0, p1, p2, p3, n in faces:
        mesh.add_quad(mat, p0, p1, p2, p3, normalize(n))


def add_rounded_box(mesh, mat, center, hx, hy, hz, r, segs=6, axes=None):
    r = min(r, hx * 0.95, hy * 0.95, hz * 0.95)
    axes = axes or ((1, 0, 0), (0, 1, 0), (0, 0, 1))
    x, y, z = axes
    ihx, ihy, ihz = hx - r, hy - r, hz - r
    add_box(mesh, mat, center, ihx, ihy, hz, axes)
    add_box(mesh, mat, center, hx, ihy, ihz, axes)
    add_box(mesh, mat, center, ihx, hy, ihz, axes)
    sph = max(6, segs * 2)
    cyl = max(8, segs * 2)
    for sx in (-1, 1):
        for sy in (-1, 1):
            for sz in (-1, 1):
                c = add(center, add(add(mul(x, sx * ihx), mul(y, sy * ihy)), mul(z, sz * ihz)))
                add_sphere(mesh, mat, c, r, segs=sph, stacks=max(4, segs))
    for sy in (-1, 1):
        for sz in (-1, 1):
            a = add(center, add(mul(y, sy * ihy), mul(z, sz * ihz)))
            add_cylinder(mesh, mat, add(a, mul(x, -ihx)), add(a, mul(x, ihx)), r, segs=cyl, caps=False)
    for sx in (-1, 1):
        for sz in (-1, 1):
            a = add(center, add(mul(x, sx * ihx), mul(z, sz * ihz)))
            add_cylinder(mesh, mat, add(a, mul(y, -ihy)), add(a, mul(y, ihy)), r, segs=cyl, caps=False)
    for sx in (-1, 1):
        for sy in (-1, 1):
            a = add(center, add(mul(x, sx * ihx), mul(y, sy * ihy)))
            add_cylinder(mesh, mat, add(a, mul(z, -ihz)), add(a, mul(z, ihz)), r, segs=cyl, caps=False)


def add_superellipsoid(mesh, mat, center, rx, ry, rz, n1, n2, u_seg=36, v_seg=20, axes=None):
    axes = axes or ((1, 0, 0), (0, 1, 0), (0, 0, 1))
    rows = []
    def pt(uu, vv):
        cuu, suu = math.cos(uu), math.sin(uu)
        cvv, svv = math.cos(vv), math.sin(vv)
        return (
            rx * cpow(cvv, n1) * cpow(cuu, n2),
            ry * cpow(cvv, n1) * cpow(suu, n2),
            rz * cpow(svv, n1),
        )
    for i in range(v_seg + 1):
        v = math.pi * (i / v_seg - 0.5)
        row = []
        for j in range(u_seg + 1):
            u = 2.0 * math.pi * (j / u_seg - 0.5)
            local = pt(u, v)
            du = sub(pt(u + 1e-3, v), pt(u - 1e-3, v))
            dv = sub(pt(u, v + 1e-3), pt(u, v - 1e-3))
            nloc = normalize(cross(du, dv))
            p = xform(local, center, axes)
            n = normalize(xform(nloc, (0, 0, 0), axes))
            row.append(mesh.emit(mat, p, n, (j / u_seg, i / v_seg)))
        rows.append(row)
    for i in range(v_seg):
        for j in range(u_seg):
            a, b = rows[i][j], rows[i][j + 1]
            c, d = rows[i + 1][j + 1], rows[i + 1][j]
            mesh.tri(mat, a, b, c)
            mesh.tri(mat, a, c, d)


def add_strip(mesh, mat, pts, half_width, thickness, up_hint=(0, 1, 0)):
    n = len(pts)
    if n < 2:
        return
    tl, tr, bl, br = [], [], [], []
    for i, p in enumerate(pts):
        tang = sub(pts[1], pts[0]) if i == 0 else sub(pts[-1], pts[-2]) if i == n - 1 else sub(pts[i + 1], pts[i - 1])
        tang = normalize(tang)
        side = normalize(cross(tang, up_hint))
        nrm = normalize(cross(side, tang))
        w = half_width[i] if isinstance(half_width, (list, tuple)) else half_width
        left, right = add(p, mul(side, w)), add(p, mul(side, -w))
        tl.append(add(left, mul(nrm, thickness * 0.5)))
        tr.append(add(right, mul(nrm, thickness * 0.5)))
        bl.append(add(left, mul(nrm, -thickness * 0.5)))
        br.append(add(right, mul(nrm, -thickness * 0.5)))
    for i in range(n - 1):
        mesh.add_quad(mat, tl[i], tr[i], tr[i + 1], tl[i + 1])
        mesh.add_quad(mat, br[i], bl[i], bl[i + 1], br[i + 1])
        mesh.add_quad(mat, tl[i], tl[i + 1], bl[i + 1], bl[i])
        mesh.add_quad(mat, tr[i + 1], tr[i], br[i], br[i + 1])
    mesh.add_quad(mat, tl[0], bl[0], br[0], tr[0])
    mesh.add_quad(mat, tr[-1], br[-1], bl[-1], tl[-1])


def add_skirt(mesh, mat, y_top, y_bot, r_top, r_bot, segs=24, rings=8, folds=8, fold_amp=0.012, thickness=0.012):
    """Flared A-line skirt with gentle pleat folds. Outer surface + inner hem."""
    def radius_at(t, a):
        ease = t * t * (3.0 - 2.0 * t)
        r = r_top + (r_bot - r_top) * ease
        return r + fold_amp * abs(math.sin(a * folds * 0.5)) * t

    rows_out, rows_in = [], []
    for i in range(rings + 1):
        t = i / rings
        y = y_top + (y_bot - y_top) * t
        row_o, row_i = [], []
        for j in range(segs + 1):
            u = j / segs
            a = 2.0 * math.pi * u
            r = radius_at(t, a)
            p = (math.cos(a) * r, y, math.sin(a) * r)
            n = normalize((math.cos(a), 0.22 * (1.0 - t), math.sin(a)))
            row_o.append(mesh.emit(mat, p, n, (u, t)))
            pin = (math.cos(a) * (r - thickness), y, math.sin(a) * (r - thickness))
            row_i.append(mesh.emit(mat, pin, mul(n, -1), (u, t)))
        rows_out.append(row_o)
        rows_in.append(row_i)
    for i in range(rings):
        for j in range(segs):
            a, b = rows_out[i][j], rows_out[i][j + 1]
            c, d = rows_out[i + 1][j + 1], rows_out[i + 1][j]
            mesh.tri(mat, a, b, c)
            mesh.tri(mat, a, c, d)
            a, b = rows_in[i][j], rows_in[i][j + 1]
            c, d = rows_in[i + 1][j + 1], rows_in[i + 1][j]
            mesh.tri(mat, a, d, c)
            mesh.tri(mat, a, c, b)
    # hem ring
    for j in range(segs):
        a, b = rows_out[-1][j], rows_out[-1][j + 1]
        c, d = rows_in[-1][j + 1], rows_in[-1][j]
        mesh.tri(mat, a, b, c)
        mesh.tri(mat, a, c, d)


def build_loaf(mesh):
    """Upright shokupan: cream cut-face toward +Z, golden crust elsewhere."""
    c = (0.0, 0.78, 0.0)
    # golden crust loaf (slightly boxy pillow, a bit thicker)
    add_superellipsoid(mesh, "crust", c, 0.195, 0.225, 0.145, 0.38, 0.34, u_seg=44, v_seg=24)
    # puffy wider top crust (the loaf "hat")
    add_sphere(mesh, "crust", (0.0, 0.96, 0.0), 0.155, segs=16, stacks=10, scale=(1.28, 0.55, 1.05))
    # cream cut face covering the front
    add_rounded_box(mesh, "crumb", (0.0, 0.76, 0.132), 0.168, 0.198, 0.028, 0.055, segs=5)
    # tiny extra puff so the face reads as soft bread
    add_sphere(mesh, "crumb", (0.0, 0.74, 0.150), 0.12, segs=12, stacks=8, scale=(1.20, 1.35, 0.22))
    return c


def build_face(mesh):
    z = 0.175
    y = 0.72
    # eyes
    for sx in (-1, 1):
        add_sphere(mesh, "face", (sx * 0.042, y + 0.018, z), 0.011, segs=10, stacks=8)
    # nose
    add_sphere(mesh, "face", (0.0, y + 0.004, z + 0.004), 0.008, segs=8, stacks=6)
    # mouth — short slightly wavy line
    add_capsule(mesh, "face", (-0.018, y - 0.022, z), (0.018, y - 0.018, z), 0.0045, segs=8, stacks=4)
    # blush
    for sx in (-1, 1):
        add_sphere(mesh, "blush", (sx * 0.078, y - 0.012, z - 0.004), 0.032, segs=12, stacks=8,
                   scale=(1.15, 0.95, 0.28))


def build_body(mesh):
    # red dress bodice under the loaf
    torso_c = (0.0, 0.42, 0.0)
    add_capsule(mesh, "suit", (0.0, 0.36, 0.0), (0.0, 0.52, 0.0), 0.078, segs=14, stacks=7)
    add_sphere(mesh, "suit", (0.0, 0.50, 0.0), 0.082, segs=14, stacks=8, scale=(1.05, 0.70, 0.95))

    # yellow belt + white buckle at the waist
    add_torus(mesh, "yellow", (0.0, 0.355, 0.0), (0.0, 1.0, 0.0), 0.078, 0.016, segs=18, tube=8)
    add_rounded_box(mesh, "buckle", (0.0, 0.355, 0.090), 0.022, 0.016, 0.010, 0.004, segs=3)

    # flared red skirt from the belt, yellow hem
    add_skirt(mesh, "skirt", y_top=0.348, y_bot=0.145, r_top=0.082, r_bot=0.175,
              segs=28, rings=8, folds=8, fold_amp=0.014, thickness=0.014)
    add_torus(mesh, "yellow", (0.0, 0.148, 0.0), (0.0, 1.0, 0.0), 0.168, 0.011, segs=24, tube=8)

    return torso_c


def build_limbs(mesh):
    # arms + yellow mittens
    for sign in (-1, 1):
        shoulder = (sign * 0.095, 0.48, 0.01)
        add_sphere(mesh, "suit", shoulder, 0.032, segs=10, stacks=7)
        elbow = (sign * 0.145, 0.38, 0.03)
        wrist = (sign * 0.155, 0.285, 0.05)
        add_capsule(mesh, "suit", shoulder, elbow, 0.028, segs=10, stacks=5)
        add_capsule(mesh, "suit", elbow, wrist, 0.024, segs=10, stacks=5)
        # mitten: big puffy yellow blob, no fingers
        palm = add(wrist, (sign * 0.01, -0.01, 0.02))
        add_sphere(mesh, "yellow", palm, 0.042, segs=12, stacks=8, scale=(1.05, 0.90, 1.20))
        add_sphere(mesh, "yellow", add(palm, (sign * 0.008, -0.006, 0.028)), 0.028, segs=10, stacks=7)

    # legs peeking from under the skirt into yellow boots
    for sign in (-1, 1):
        knee = (sign * 0.048, 0.175, 0.02)
        ankle = (sign * 0.046, 0.085, 0.015)
        add_capsule(mesh, "suit", (sign * 0.045, 0.210, 0.015), knee, 0.028, segs=10, stacks=5)
        add_capsule(mesh, "suit", knee, ankle, 0.026, segs=10, stacks=5)
        # rounded boot
        boot = (sign * 0.046, 0.048, 0.028)
        add_sphere(mesh, "yellow", boot, 0.048, segs=12, stacks=8, scale=(1.05, 0.72, 1.35))
        add_sphere(mesh, "yellow", (sign * 0.046, 0.028, 0.055), 0.038, segs=10, stacks=7, scale=(1.10, 0.70, 1.20))


def pack_f32(values):
    return struct.pack("<" + "f" * len(values), *values)


def pack_u32(values):
    return struct.pack("<" + "I" * len(values), *values)


def write_glb(path, mesh: Mesh):
    bin_blob = bytearray()
    buffer_views, accessors, prims, materials = [], [], [], []

    def push_view(blob, target):
        while len(bin_blob) % 4:
            bin_blob.append(0)
        offset = len(bin_blob)
        bin_blob.extend(blob)
        buffer_views.append({"buffer": 0, "byteOffset": offset, "byteLength": len(blob), "target": target})
        return len(buffer_views) - 1

    order = [k for k in MATS if k in mesh.parts] + [k for k in mesh.parts if k not in MATS]
    for name in order:
        part = mesh.parts[name]
        if not part["idx"]:
            continue
        spec = MATS.get(name, MATS["crumb"])
        mat = {
            "name": f"MI_BreadLoaf_{name}",
            "pbrMetallicRoughness": {
                "baseColorFactor": list(spec["color"]),
                "metallicFactor": spec["metal"],
                "roughnessFactor": spec["rough"],
            },
        }
        materials.append(mat)
        pos, nrm, uv, idx = part["pos"], part["nrm"], part["uv"], part["idx"]
        xs, ys, zs = pos[0::3], pos[1::3], pos[2::3]
        pos_view = push_view(pack_f32(pos), 34962)
        nrm_view = push_view(pack_f32(nrm), 34962)
        uv_view = push_view(pack_f32(uv), 34962)
        idx_view = push_view(pack_u32(idx), 34963)
        pos_acc = len(accessors)
        accessors.append({
            "bufferView": pos_view, "componentType": 5126, "count": len(pos) // 3, "type": "VEC3",
            "min": [min(xs), min(ys), min(zs)], "max": [max(xs), max(ys), max(zs)],
        })
        nrm_acc = len(accessors)
        accessors.append({"bufferView": nrm_view, "componentType": 5126, "count": len(nrm) // 3, "type": "VEC3"})
        uv_acc = len(accessors)
        accessors.append({"bufferView": uv_view, "componentType": 5126, "count": len(uv) // 2, "type": "VEC2"})
        idx_acc = len(accessors)
        accessors.append({"bufferView": idx_view, "componentType": 5125, "count": len(idx), "type": "SCALAR"})
        prims.append({
            "attributes": {"POSITION": pos_acc, "NORMAL": nrm_acc, "TEXCOORD_0": uv_acc},
            "indices": idx_acc, "material": len(materials) - 1, "mode": 4,
        })

    gltf = {
        "asset": {"version": "2.0", "generator": "meat_ross BuildBreadLoaf"},
        "scene": 0,
        "scenes": [{"nodes": [0], "name": "BreadLoafScene"}],
        "nodes": [{"mesh": 0, "name": "SM_BreadLoaf"}],
        "meshes": [{"name": "SM_BreadLoaf", "primitives": prims}],
        "materials": materials,
        "accessors": accessors,
        "bufferViews": buffer_views,
        "buffers": [{"byteLength": len(bin_blob)}],
    }
    json_bytes = json.dumps(gltf, separators=(",", ":")).encode("utf-8")
    while len(json_bytes) % 4:
        json_bytes += b" "
    while len(bin_blob) % 4:
        bin_blob.append(0)
    total = 12 + 8 + len(json_bytes) + 8 + len(bin_blob)
    header = struct.pack("<4sII", b"glTF", 2, total)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(header)
        f.write(struct.pack("<I4s", len(json_bytes), b"JSON") + json_bytes)
        f.write(struct.pack("<I4s", len(bin_blob), b"BIN\x00") + bytes(bin_blob))


def main():
    mesh = Mesh()
    build_loaf(mesh)
    build_face(mesh)
    build_body(mesh)
    build_limbs(mesh)
    write_glb(OUT_GLB, mesh)
    verts, tris, mats = mesh.stats()
    print(f"Wrote {OUT_GLB}")
    print(f"verts={verts} tris={tris} materials={mats}")
    print(f"bytes={os.path.getsize(OUT_GLB)}")


if __name__ == "__main__":
    main()
