#!/usr/bin/env python
"""demo_402 结果图：Chorin vs IPCS 对比（κ̂ = 1.0，T = 1 s，N = 128，MFAC = 0.5）。

用法（在 demo_402 目录下，需要 dolfinx 环境里的 pyvista）：
    conda run -n afsi-dolfinx python -B -u plot/make_site_figures.py [--out DIR]

输出（默认 plot/site/）：
    demo402-tip-history-chorin-vs-ipcs.png     ΔY(t) 与 ∫u²dA(t) 对比
    demo402-vorticity-chorin-vs-ipcs.png       t=1s 涡量场（上：Chorin，下：IPCS）
    demo402-vorticity-zoom-chorin-vs-ipcs.png  同上，放大圆柱/尾巴/近尾流
"""
import argparse
import csv
import os

import numpy as np
import h5py
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.cm import ScalarMappable
from matplotlib.colors import Normalize
import pyvista as pv

pv.OFF_SCREEN = True

HERE = os.path.dirname(os.path.abspath(__file__))
RUNS = {
    "Chorin": os.path.join(HERE, "t1s_khat1", "chorin"),
    "IPCS": os.path.join(HERE, "t1s_khat1", "ipcs"),
}
COLORS = {"Chorin": "tab:blue", "IPCS": "tab:red"}


def load_history(run):
    with open(os.path.join(run, "history.csv")) as fh:
        rows = list(csv.DictReader(fh))
    return {k: np.array([float(r[k]) for r in rows]) for k in rows[0]}


def zero_cross_freq(d):
    """t > 0.5 s 段尾尖振荡的过零频率估计 [Hz]。"""
    sel = d["t"] > 0.5
    y = d["tip_dy"][sel]
    t = d["t"][sel]
    sgn = np.sign(y - y.mean())
    n = int(np.sum(np.abs(np.diff(sgn)) > 0))
    return n / 2.0 / (t[-1] - t[0])


def fig_history(out_path):
    data = {name: load_history(run) for name, run in RUNS.items()}
    plt.rcParams.update({"font.size": 10.5, "axes.labelsize": 11})
    fig, axes = plt.subplots(2, 1, figsize=(7.6, 5.6), sharex=True,
                             constrained_layout=True)
    stats = {}
    for name, d in data.items():
        mx = float(np.abs(d["tip_dy"]).max())
        fq = zero_cross_freq(d)
        stats[name] = dict(max_abs=mx, freq=fq, uL2_final=float(d["u_L2"][-1]))
        axes[0].plot(d["t"], d["tip_dy"], color=COLORS[name], lw=1.4,
                     label=f"{name}   (max $|\\Delta Y|$ = {mx:.2f} cm)")
        axes[1].plot(d["t"], d["u_L2"] / 1e8, color=COLORS[name], lw=1.4, label=name)
    axes[0].set_ylabel("$\\Delta Y$ at point A [cm]")
    axes[1].set_ylabel("$\\int_\\Omega u^2\\,\\mathrm{d}A$  ($\\times 10^{-8}$)")
    axes[1].set_xlabel("$t$ [s]")
    axes[0].set_title("flapping frequency ≈ %.2f Hz (both)" %
                      np.mean([s["freq"] for s in stats.values()]),
                      loc="right", fontsize=9.5, color="0.35")
    for ax in axes:
        ax.grid(True, alpha=0.3)
        ax.set_xlim(0.0, float(data["Chorin"]["t"][-1]))
        ax.legend(loc="upper left", fontsize=9.5, framealpha=0.9)
    fig.savefig(out_path, dpi=170)
    plt.close(fig)

    n1, n2 = list(data)
    m = min(len(data[n1]["t"]), len(data[n2]["t"]))
    rel = np.abs(data[n1]["u_L2"][:m] - data[n2]["u_L2"][:m]) / data[n1]["u_L2"][:m]
    print(f"-> {out_path}")
    for name, s in stats.items():
        print(f"   {name:7s} max|ΔY| = {s['max_abs']:.2f} cm   f = {s['freq']:.2f} Hz"
              f"   ∫u²dA = {s['uL2_final']:.3e}")
    print(f"   u_L2 逐帧相对差: 平均 {100*rel.mean():.3f}%  中位 {100*np.median(rel):.3f}%"
          f"  最大 {100*rel.max():.3f}%")


# ---------------------------------------------------------------- vorticity

def _time_of(key):
    return float(key.replace("_", ".", 1))


def read_last(path, fname=None):
    with h5py.File(path, "r") as h:
        name = fname or list(h["Function"].keys())[0]
        keys = sorted(h[f"Function/{name}"].keys(), key=_time_of)
        key = keys[-1]
        return h[f"Function/{name}/{key}"][:], _time_of(key), name


def make_grid(path):
    with h5py.File(path, "r") as h:
        topo = h["Mesh/mesh/topology"][:].astype(np.int64)
        geom = h["Mesh/mesh/geometry"][:]
    if geom.shape[1] == 2:
        geom = np.c_[geom, np.zeros(len(geom))]
    n, k = topo.shape
    cells = np.hstack([np.full((n, 1), k, dtype=np.int64), topo]).ravel()
    ctype = {3: pv.CellType.TRIANGLE, 4: pv.CellType.QUAD}[k]
    return pv.UnstructuredGrid(cells, np.full(n, ctype, np.uint8), geom)


def snapshot_data(run):
    fluid = make_grid(os.path.join(run, "velocity.h5"))
    u, t, _ = read_last(os.path.join(run, "velocity.h5"))
    fluid.point_data["u"] = u[:, :2]
    grad = np.asarray(fluid.compute_derivative(scalars="u").point_data["gradient"])
    w = grad[:, 3] - grad[:, 1]
    fluid.point_data["omega_z"] = w

    solid = make_grid(os.path.join(run, "solid.h5"))
    sc, _, _ = read_last(os.path.join(run, "solid.h5"), "solid_coords_io")
    solid.points = np.c_[sc[:, :2], np.zeros(len(sc))]
    return fluid, solid, t, float(np.abs(w).max())


def render(mesh, solid, clim, zoom_bounds=None, window=(1800, 430)):
    m = mesh if zoom_bounds is None else mesh.clip_box(bounds=zoom_bounds, invert=False)
    pl = pv.Plotter(off_screen=True, window_size=window)
    pl.background_color = "white"
    pl.add_mesh(m, scalars="omega_z", cmap="RdBu_r", clim=clim,
                show_scalar_bar=False, lighting=False)
    pl.add_mesh(solid, color="black", style="wireframe", line_width=2.0)
    pl.view_xy()
    if zoom_bounds is None:
        pl.camera.zoom(1.03)
    else:
        pl.reset_camera()
    img = np.asarray(pl.screenshot(return_img=True))
    pl.close()
    return img


def trim(img, pad=6):
    """裁掉渲染图四周的白边。"""
    ys, xs = np.where(img[..., :3].sum(-1) < 750)
    if not len(ys):
        return img
    y0, y1 = max(int(ys.min()) - pad, 0), min(int(ys.max()) + pad + 1, img.shape[0])
    x0, x1 = max(int(xs.min()) - pad, 0), min(int(xs.max()) + pad + 1, img.shape[1])
    return img[y0:y1, x0:x1]


def compose_pair(rows, out_path, clim, note=None):
    imgs = [(label, trim(img)) for label, img in rows]
    ar = imgs[0][1].shape[0] / imgs[0][1].shape[1]
    w = 11.0
    fig, axes = plt.subplots(len(imgs), 1, figsize=(w, len(imgs) * w * ar + 0.7))
    axs = np.atleast_1d(axes)
    for ax, (label, img) in zip(axs, imgs):
        ax.imshow(img, aspect="equal")
        ax.set_axis_off()
        ax.text(0.004, 0.985, label, transform=ax.transAxes, va="top", ha="left",
                fontsize=13, bbox=dict(facecolor="white", alpha=0.85, edgecolor="none"))
        if note:
            ax.text(0.996, 0.985, note, transform=ax.transAxes, va="top", ha="right",
                    fontsize=11, bbox=dict(facecolor="white", alpha=0.85, edgecolor="none"))
    sm = ScalarMappable(norm=Normalize(*clim), cmap="RdBu_r")
    fig.colorbar(sm, ax=list(axs), shrink=0.85, pad=0.01, label="$\\omega_z$ [1/s]")
    fig.savefig(out_path, dpi=170, bbox_inches="tight")
    plt.close(fig)


def fig_vorticity(out_path, zoom=None):
    snaps = {name: snapshot_data(run) for name, run in RUNS.items()}
    wmax = max(s[3] for s in snaps.values())
    clim = (-wmax, wmax)
    rows, t_used = [], None
    for name, (fluid, solid, t, _) in snaps.items():
        rows.append((name, render(fluid, solid, clim, zoom)))
        t_used = t
    compose_pair(rows, out_path, clim, note=f"$t$ = {t_used:.2f} s")
    print(f"-> {out_path}  (omega_z clim ±{wmax:.0f} 1/s, t = {t_used:.4f} s, "
          f"zoom={zoom})")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(HERE, "site"))
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    fig_history(os.path.join(args.out, "demo402-tip-history-chorin-vs-ipcs.png"))
    fig_vorticity(os.path.join(args.out, "demo402-vorticity-chorin-vs-ipcs.png"))
    fig_vorticity(os.path.join(args.out, "demo402-vorticity-zoom-chorin-vs-ipcs.png"),
                  zoom=(12.0, 85.0, 6.0, 35.0, -1.0, 1.0))


if __name__ == "__main__":
    main()
