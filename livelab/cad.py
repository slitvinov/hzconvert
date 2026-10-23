import subprocess
import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection

AFLO = 8.17547
HROO = 3.84
WX = 2.13
LY = 3.84
VOL = AFLO * HROO
HEAVE = (VOL / LY - WX * WX / 4) / WX
RIDGE = HEAVE + WX / 2
SLOPE = (WX / 2) * np.sqrt(2.0)

WIN_S = (1.58, 1.45)
WIN_W = (1.07, 0.885)
WIN_SKY = (1.07, 0.885)
SILL_S = 0.90
SILL_W = 1.10

WALL = "#86b6ef"
ROOF = "#2a78d6"
GLASS = "#1baf7a"
SLAB = "#eb6834"
EDGE = "#1a1a19"
INK = "#1a1a19"
def show(p):
    if sys.platform == "darwin":
        subprocess.run(["open", p], check=False)


COL = {"wall": WALL, "roof": ROOF, "glass": GLASS, "slab": SLAB}


def centered(span, size):
    c = span / 2.0
    return c - size / 2.0, c + size / 2.0


def quad(f, u0, u1, v0, v1):
    return [f(u0, v0), f(u1, v0), f(u1, v1), f(u0, v1)]


def holed(f, u0, u1, v0, v1, a0, a1, b0, b1):
    out = []
    for p, q, r, s in [(u0, u1, v0, b0), (u0, u1, b1, v1),
                       (u0, a0, b0, b1), (a1, u1, b0, b1)]:
        if q - p > 1e-9 and s - r > 1e-9:
            out.append(quad(f, p, q, r, s))
    return out


def build():
    faces = []

    def add(poly, kind, tag):
        faces.append({"p": np.array(poly, float), "kind": kind, "tag": tag})

    south = lambda x, z: (x, 0.0, z)
    north = lambda x, z: (x, LY, z)
    east = lambda y, z: (WX, y, z)
    west = lambda y, z: (0.0, y, z)

    a0, a1 = centered(WX, WIN_S[0])
    b0, b1 = SILL_S, SILL_S + WIN_S[1]
    for p in holed(south, 0, WX, 0, HEAVE, a0, a1, b0, b1):
        add(p, "wall", "S")
    add([south(0, HEAVE), south(WX, HEAVE), south(WX / 2, RIDGE)], "wall", "S")
    add(quad(south, a0, a1, b0, b1), "glass", "Swin")

    add(quad(north, 0, WX, 0, HEAVE), "wall", "N")
    add([north(0, HEAVE), north(WX, HEAVE), north(WX / 2, RIDGE)], "wall", "N")
    add(quad(east, 0, LY, 0, HEAVE), "wall", "E")

    c0, c1 = centered(LY, WIN_W[0])
    d0, d1 = SILL_W, SILL_W + WIN_W[1]
    for p in holed(west, 0, LY, 0, HEAVE, c0, c1, d0, d1):
        add(p, "wall", "W")
    add(quad(west, c0, c1, d0, d1), "glass", "Wwin")

    def rslope(sign):
        def f(s, y):
            x = WX if sign > 0 else 0.0
            return (x - sign * s / np.sqrt(2.0), y, HEAVE + s / np.sqrt(2.0))
        return f

    add(quad(rslope(+1), 0, SLOPE, 0, LY), "roof", "Eroof")

    fw = rslope(-1)
    e0, e1 = centered(SLOPE, WIN_SKY[1])
    g0, g1 = centered(LY, WIN_SKY[0])
    for p in holed(fw, 0, SLOPE, 0, LY, e0, e1, g0, g1):
        add(p, "roof", "Wroof")
    add(quad(fw, e0, e1, g0, g1), "glass", "sky")

    add([(0, 0, 0), (WX, 0, 0), (WX, LY, 0), (0, LY, 0)], "slab", "slab")

    c = np.array([WX / 2, LY / 2, RIDGE / 3])
    for f in faces:
        n = np.cross(f["p"][1] - f["p"][0], f["p"][2] - f["p"][0])
        n = n / np.linalg.norm(n)
        if np.dot(n, f["p"].mean(0) - c) < 0:
            n = -n
        f["n"] = n
    return faces


def area(p):
    n = np.zeros(3)
    for i in range(len(p)):
        n += np.cross(p[i], p[(i + 1) % len(p)])
    return float(np.linalg.norm(n) / 2.0)


def tris(p):
    return [(p[0], p[i], p[i + 1]) for i in range(1, len(p) - 1)]


def write_stl(faces, path):
    with open(path, "w") as fh:
        fh.write("solid livelab\n")
        for f in faces:
            for t in tris(f["p"]):
                fh.write("facet normal %g %g %g\n  outer loop\n" % tuple(f["n"]))
                for v in t:
                    fh.write("    vertex %g %g %g\n" % tuple(v))
                fh.write("  endloop\nendfacet\n")
        fh.write("endsolid livelab\n")


def camera(az, el):
    a, e = np.radians(az), np.radians(el)
    d = np.array([np.cos(e) * np.cos(a), np.cos(e) * np.sin(a), np.sin(e)])
    r = np.cross([0, 0, 1.0], d)
    r = r / np.linalg.norm(r)
    u = np.cross(d, r)
    return d, r, u


def render(ax, faces, az, el, title, cull=True, drop=(), labels=()):
    d, r, u = camera(az, el)
    shown = [f for f in faces if f["tag"] not in drop]
    if cull:
        shown = [f for f in shown if np.dot(f["n"], d) > 1e-6]
    shown.sort(key=lambda f: np.dot(f["p"].mean(0), d))

    polys, cols = [], []
    for f in shown:
        lit = 0.55 + 0.45 * abs(np.dot(f["n"], d))
        c = matplotlib.colors.to_rgb(COL[f["kind"]])
        cols.append(tuple(min(1.0, v * lit + (1 - lit) * 0.12) for v in c))
        off = f["p"] + f["n"] * (0.004 if f["kind"] == "glass" else 0.0)
        polys.append(np.column_stack([off @ r, off @ u]))

    ax.add_collection(PolyCollection(polys, facecolors=cols, edgecolors=EDGE,
                                     linewidths=0.6))
    allp = np.vstack(polys)
    pad = 0.35
    ax.set_xlim(allp[:, 0].min() - pad, allp[:, 0].max() + pad)
    ax.set_ylim(allp[:, 1].min() - pad, allp[:, 1].max() + pad)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title(title, color=INK, fontsize=10)
    for txt, pt, dx, dy in labels:
        p = np.array(pt, float)
        ax.annotate(txt, (p @ r, p @ u), (p @ r + dx, p @ u + dy),
                    color=INK, fontsize=8, ha="center",
                    arrowprops=dict(arrowstyle="-", lw=0.7, color=INK))


def main():
    faces = build()
    write_stl(faces, "livelab.stl")

    tot = {}
    for f in faces:
        tot[f["kind"]] = tot.get(f["kind"], 0.0) + area(f["p"])
    print("LiveLab (Z31) envelope from livelab.mo")
    print("  footprint %.3f x %.3f m = %.3f m2   (AFlo %.5f)"
          % (WX, LY, WX * LY, AFLO))
    print("  eaves %.3f  ridge %.3f  mean %.3f m  (hRoo %.2f)"
          % (HEAVE, RIDGE, VOL / (WX * LY), HROO))
    print("  volume %.2f m3" % VOL)
    for k in ("slab", "wall", "roof", "glass"):
        print("  %-5s %7.2f m2" % (k, tot[k]))

    fig, axs = plt.subplots(2, 2, figsize=(11, 9), facecolor="white")
    ys = SILL_S + WIN_S[1] / 2
    yw = SILL_W + WIN_W[1] / 2

    render(axs[0][0], faces, -125, 18, "from south-west",
           labels=[("south window\n1.58 x 1.45 m", (WX / 2, 0, ys), 1.5, -1.7),
                   ("west window\n1.07 x 0.885 m", (0, LY / 2, yw), -1.4, -1.9)])
    render(axs[0][1], faces, 35, 20, "from north-east")
    render(axs[1][0], faces, -150, 45, "from above, west",
           labels=[("skylight 1.07 x 0.885 m\nin W roof slope",
                    (WX / 4, LY / 2, HEAVE + WX / 4), -0.6, 1.4)])
    render(axs[1][1], faces, 55, 28, "cutaway: N wall and E roof removed",
           cull=False, drop=("N", "Eroof"),
           labels=[("TABS radiant slab\n8.18 m2", (WX / 2, LY / 2, 0), 1.3, -1.7)])

    h = [plt.Rectangle((0, 0), 1, 1, fc=COL[k], ec=EDGE, lw=0.5)
         for k in ("wall", "roof", "glass", "slab")]
    fig.legend(h, ["opaque wall", "roof (45 deg)", "glazing", "TABS radiant slab"],
               loc="lower center", ncol=4, frameon=False, fontsize=9, labelcolor=INK)
    fig.suptitle("LiveLab / zone Z31 envelope   %.2f x %.2f m plan, "
                 "eaves %.2f m, ridge %.2f m, %.1f m3"
                 % (WX, LY, HEAVE, RIDGE, VOL), color=INK, fontsize=12)
    fig.subplots_adjust(left=0.02, right=0.98, top=0.92, bottom=0.07,
                        wspace=0.02, hspace=0.12)
    fig.savefig("livelab_cad.png", dpi=160)
    show("livelab_cad.png")
    print("wrote livelab_cad.png and livelab.stl")


main()
