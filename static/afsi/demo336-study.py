"""Comprehensive post-processing for the demo_336 lid-driven cavity with a disc.

Reads the per-step ``metrics.csv`` written by both drivers
(``multi-direct-frocing`` and ``multi-direct-frocing-elastic``) plus the XDMF/HDF5
fields, and produces the trajectory / history / deformation / energy / field
figures used on the demo_340-style write-up.

Every run directory must contain ``metrics.csv`` with the columns
``t,cx,cy,...``; the rigid and elastic drivers both emit that now.
"""

from __future__ import annotations

import argparse
import os
import sys

import numpy as np

os.environ.setdefault("PYVISTA_OFF_SCREEN", "true")

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Circle  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

R_DISC = 0.2
C0 = (0.6, 0.5)

# label, directory name, style
RUNS = [
    ("no solid", "no_solid", dict(color="0.55", ls="-", lw=1.6)),
    ("elastic, $\\mu_s{=}0.2$, $\\rho_s{=}1$", "elastic_base", dict(color="crimson", ls="-", lw=1.8)),
    ("elastic, $\\mu_s{=}0.05$ (softer)", "elastic_soft", dict(color="darkorange", ls="-", lw=1.6)),
    ("elastic, $\\rho_s{=}20$ (heavier)", "elastic_heavy", dict(color="navy", ls="-", lw=1.6)),
    ("rigid, free", "rigid_free", dict(color="seagreen", ls="-", lw=1.8)),
    ("rigid, fixed", "rigid_fixed", dict(color="purple", ls="--", lw=1.4)),
    ("elastic, $\\rho_s{=}20$ clamped", "elastic_heavy_clamp", dict(color="teal", ls="-.", lw=1.3)),
]

# the same case at three grid resolutions
GRID_RUNS = [
    ("$32^2$", "elastic_32", dict(color="0.6", ls="-", lw=1.5)),
    ("$64^2$", "elastic_base", dict(color="crimson", ls="-", lw=1.8)),
    ("$128^2$", "elastic_128", dict(color="navy", ls="-", lw=1.5)),
]


def load(root: str, name: str):
    path = os.path.join(root, name, "metrics.csv")
    if not os.path.exists(path):
        return None
    d = np.genfromtxt(path, delimiter=",", names=True)
    if d.size == 0:
        return None
    return d


def fig_trajectories(root, figs):
    fig, axs = plt.subplots(1, 2, figsize=(13.5, 5.6), constrained_layout=True)
    for label, name, st in RUNS:
        d = load(root, name)
        if d is None:
            continue
        ax = axs[0]
        sc = ax.scatter(d["cx"], d["cy"], c=d["t"], cmap="viridis", s=2.5)
        ax.plot(d["cx"], d["cy"], **st)
        ax.annotate(label, (d["cx"][-1], d["cy"][-1]), fontsize=8,
                    textcoords="offset points", xytext=(4, 3))
        ax = axs[1]
        ax.plot(d["t"], d["cx"], **st, label=label)
        ax.plot(d["t"], d["cy"], **dict(st, ls=":"))
    ax = axs[0]
    ax.add_patch(Circle(C0, R_DISC, fill=False, ls=":", ec="k", lw=1.0))
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.set_aspect("equal")
    ax.set_xlabel("$x$"); ax.set_ylabel("$y$")
    ax.set_title("disc-centre path (dotted circle = start, colour = $t$)")
    fig.colorbar(sc, ax=ax, fraction=0.046).set_label("$t$ [s]")
    ax = axs[1]
    ax.set_xlabel("$t$ [s]"); ax.set_ylabel("centroid coordinate")
    ax.set_title("centroid $x$ (solid) and $y$ (dotted)")
    ax.grid(alpha=0.3); ax.legend(fontsize=8, ncol=2)
    out = os.path.join(figs, "336_trajectories.png")
    fig.savefig(out, dpi=150); plt.close(fig)
    print("wrote", out)


def fig_histories(root, figs):
    fig, axs = plt.subplots(2, 2, figsize=(13.5, 8.5), constrained_layout=True)
    for label, name, st in RUNS:
        d = load(root, name)
        if d is None:
            continue
        names = d.dtype.names
        if "Fx" in names:
            axs[0][0].plot(d["t"], d["Fx"], **st, label=label)
            axs[0][1].plot(d["t"], d["Fy"], **st)
        if "u_L2" in names:
            axs[1][0].plot(d["t"], d["u_L2"], **st)
        if "disp_max" in names and name.startswith("elastic"):
            axs[1][1].plot(d["t"], d["disp_max"], **st)
    axs[0][0].set_ylabel("$F_x$ (IB force integral)")
    axs[0][1].set_ylabel("$F_y$")
    axs[1][0].set_ylabel("$u_{L2}$ (fluid energy norm)")
    axs[1][1].set_ylabel("max $|u_s|$ (solid)")
    axs[1][1].axhline(2 * R_DISC, color="k", ls=":", lw=1.0)
    axs[1][1].text(0.3, 2 * R_DISC + 0.02, "disc diameter", fontsize=8)
    for ax in axs.ravel():
        ax.set_xlabel("$t$ [s]"); ax.grid(alpha=0.3)
    axs[0][0].legend(fontsize=8, ncol=2)
    fig.suptitle("demo_336 — force balance, fluid energy and solid deformation", fontsize=12)
    out = os.path.join(figs, "336_histories.png")
    fig.savefig(out, dpi=150); plt.close(fig)
    print("wrote", out)


def fig_elastic_metrics(root, figs):
    fig, axs = plt.subplots(1, 3, figsize=(15.5, 4.4), constrained_layout=True)
    for label, name, st in RUNS:
        d = load(root, name)
        if d is None or "det_min" not in d.dtype.names or not name.startswith("elastic"):
            continue
        axs[0].plot(d["t"], d["det_min"], **st, label=label)
        axs[1].plot(d["t"], np.sqrt(np.abs(d["volume"] / (np.pi * R_DISC ** 2))), **st)
        axs[2].plot(d["t"], d["disp_rms"], **st)
    axs[0].axhline(1.0, color="k", ls=":", lw=1.0)
    axs[0].fill_between([0, 10], 0, 1.0, color="crimson", alpha=0.08)
    axs[0].text(4, 0.3, "inverted elements", fontsize=8, color="crimson")
    axs[0].set_ylabel("$\\min\\,\\det F$")
    axs[0].set_title("solid mesh health")
    axs[1].axhline(1.0, color="k", ls=":", lw=1.0)
    axs[1].set_ylabel("$(V/V_0)^{1/2}$")
    axs[1].set_title("area change")
    axs[2].set_ylabel("RMS $|u_s|$")
    axs[2].set_title("mean deformation")
    for ax in axs:
        ax.set_xlabel("$t$ [s]"); ax.grid(alpha=0.3)
    axs[0].legend(fontsize=8)
    out = os.path.join(figs, "336_elastic_metrics.png")
    fig.savefig(out, dpi=150); plt.close(fig)
    print("wrote", out)


def fig_fields(root, figs, times=(0.0, 2.0, 4.0, 6.0, 8.0, 10.0), run="rigid_free",
               coords_are_absolute=False):
    """Velocity magnitude + vorticity + pressure, with the disc outline.

    The two drivers store different things in their solid XDMF: the rigid one
    writes a *displacement* field on a fixed reference disc, the elastic one
    writes ``solid_coords_io``, which is already absolute. ``coords_are_absolute``
    selects between them.
    """
    from make_demo_figures import Series

    vel = Series(os.path.join(root, run, "velocity.xdmf"), "f")
    pre = Series(os.path.join(root, run, "pressure.xdmf"), "f")
    sol = Series(os.path.join(root, run, "disk.xdmf"), "u")
    xs, ys = np.unique(np.round(vel.points[:, 0], 10)), np.unique(np.round(vel.points[:, 1], 10))
    Y, X = np.meshgrid(ys, xs, indexing="ij")

    def lat(v, pts):
        ix = np.clip(np.searchsorted(xs, pts[:, 0]), 0, len(xs) - 1)
        iy = np.clip(np.searchsorted(ys, pts[:, 1]), 0, len(ys) - 1)
        out = np.empty((len(ys), len(xs))) if v.ndim == 1 else np.empty((len(ys), len(xs), v.shape[1]))
        if v.ndim == 1:
            out[iy, ix] = v
        else:
            out[iy, ix, :] = v
        return out

    vmax = 1.0
    times = [t for t in times if t <= float(vel.times.max()) + 1e-6]
    fig, axes = plt.subplots(3, len(times), figsize=(2.5 * len(times), 7.4),
                             constrained_layout=True, squeeze=False)
    for j, t in enumerate(times):
        _, uv = vel.read(t)
        _, pv = pre.read(t)
        _, coords = sol.read(t)
        ul = lat(uv[:, :2], vel.points)
        u_mag = np.linalg.norm(ul, axis=2)
        # vorticity by central differences on the uniform lattice
        dx = float(xs[1] - xs[0]); dy = float(ys[1] - ys[0])
        dvdx = np.gradient(ul[:, :, 1], dx, axis=1)
        dudy = np.gradient(ul[:, :, 0], dy, axis=0)
        omega = dvdx - dudy
        pl = lat(pv.ravel(), pre.points)
        cur = coords[:, :2] if coords_are_absolute else sol.points[:, :2] + coords[:, :2]

        for r, (data, cmap, vlim, name) in enumerate([
                (u_mag, "turbo", (0, vmax), "$|u|$"),
                (omega, "RdBu_r", (-np.percentile(np.abs(omega), 99), np.percentile(np.abs(omega), 99)), "$\\omega$"),
                (pl, "RdBu_r", (-np.percentile(np.abs(pl), 99), np.percentile(np.abs(pl), 99)), "$p$")]):
            ax = axes[r][j]
            pc = ax.pcolormesh(X, Y, data, cmap=cmap, vmin=vlim[0], vmax=vlim[1],
                               shading="gouraud", rasterized=True)
            ax.add_patch(Circle((cur[:, 0].mean(), cur[:, 1].mean()), R_DISC,
                                fill=False, ec="k", lw=1.2))
            ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.set_aspect("equal")
            ax.set_xticks([0, 0.5, 1.0]); ax.set_yticks([0, 0.5, 1.0])
            ax.tick_params(labelsize=7)
            if j:
                ax.set_yticklabels([])
            if j == 0:
                ax.set_ylabel(name, fontsize=10)
            if r == 0:
                ax.set_title(f"$t = {t:g}$ s", fontsize=10)
            if j == len(times) - 1 and r == 0:
                fig.colorbar(pc, ax=ax, fraction=0.05, pad=0.02).set_label("$|u|$", fontsize=8)
    fig.suptitle(f"demo_336 — flow at six instants ({run})", fontsize=12)
    out = os.path.join(figs, "336_fields.png")
    fig.savefig(out, dpi=150); plt.close(fig)
    print("wrote", out)


def fig_orbit(root, figs):
    """How far around the cavity centre each disc actually travels."""
    fig, axs = plt.subplots(1, 2, figsize=(13, 4.6), constrained_layout=True)
    for label, name, st in RUNS:
        d = load(root, name)
        if d is None or name == "no_solid":
            continue
        ang = np.unwrap(np.arctan2(d["cy"] - 0.5, d["cx"] - 0.5)) - np.arctan2(C0[1] - 0.5, C0[0] - 0.5)
        rad = np.hypot(d["cx"] - 0.5, d["cy"] - 0.5)
        axs[0].plot(d["t"], np.degrees(ang), **st, label=label)
        axs[1].plot(d["t"], rad, **st)
    axs[0].set_ylabel("swept angle about the cavity centre [deg]")
    axs[0].set_title("orbit progress: a full loop needs $\\pm 360^\\circ$")
    axs[1].set_ylabel("distance from cavity centre")
    axs[1].axhline(np.hypot(C0[0] - 0.5, C0[1] - 0.5), color="k", ls=":", lw=1.0)
    for ax in axs:
        ax.set_xlabel("$t$ [s]"); ax.grid(alpha=0.3)
    axs[0].legend(fontsize=8, ncol=2)
    out = os.path.join(figs, "336_orbit.png")
    fig.savefig(out, dpi=150); plt.close(fig)
    print("wrote", out)


def fig_grid(root, figs):
    """The same case at 32^2, 64^2 and 128^2."""
    fig, axs = plt.subplots(1, 3, figsize=(15.5, 4.5), constrained_layout=True)
    for label, name, st in GRID_RUNS:
        d = load(root, name)
        if d is None:
            continue
        axs[0].plot(d["t"], d["cx"], **st, label=label + " $x$")
        axs[0].plot(d["t"], d["cy"], **dict(st, ls=":"))
        axs[1].plot(d["cx"], d["cy"], **st, label=label)
        names = d.dtype.names
        if "disp_max" in names:
            axs[2].plot(d["t"], d["disp_max"], **st, label=label)
    axs[0].set_xlabel("$t$ [s]"); axs[0].set_ylabel("centroid ($x$ solid, $y$ dotted)")
    axs[0].set_title("centroid history"); axs[0].legend(fontsize=8, ncol=2)
    axs[1].set_xlabel("$x$"); axs[1].set_ylabel("$y$"); axs[1].set_aspect("equal")
    axs[1].set_xlim(0, 1); axs[1].set_ylim(0, 1)
    axs[1].set_title("path"); axs[1].legend(fontsize=8)
    axs[2].set_xlabel("$t$ [s]"); axs[2].set_ylabel("max $|u_s|$")
    axs[2].set_title("deformation"); axs[2].legend(fontsize=8)
    for ax in axs:
        ax.grid(alpha=0.3)
    fig.suptitle("demo_336 — grid sensitivity of the elastic disc", fontsize=12)
    out = os.path.join(figs, "336_grid.png")
    fig.savefig(out, dpi=150); plt.close(fig)
    print("wrote", out)


def summary_table(root):
    rows = []
    for label, name, _ in RUNS:
        d = load(root, name)
        if d is None:
            continue
        t = d["t"]
        cx, cy = d["cx"], d["cy"]
        path = float(np.sum(np.hypot(np.diff(cx), np.diff(cy))))
        row = dict(run=name, t_end=float(t[-1]), n=len(t),
                   x_range=(float(cx.min()), float(cx.max())),
                   y_range=(float(cy.min()), float(cy.max())),
                   travel=float(np.hypot(cx - cx[0], cy - cy[0])[-1]),
                   path_len=path)
        names = d.dtype.names
        if "disp_max" in names:
            row["disp_max"] = float(d["disp_max"].max())
            row["det_min"] = float(d["det_min"].min())
            row["vol_rel"] = float(d["volume"].max() / d["volume"][0])
        if "u_L2" in names:
            row["u_L2_end"] = float(d["u_L2"][-1])
        if "Fx" in names:
            row["Fx_abs_max"] = float(np.abs(d["Fx"]).max())
        rows.append(row)
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("--figs", required=True)
    ap.add_argument("--fields-run", default="rigid_free")
    ap.add_argument("--coords-absolute", action="store_true",
                    help="the solid XDMF holds coordinates, not displacement")
    args = ap.parse_args()
    os.makedirs(args.figs, exist_ok=True)

    fig_trajectories(args.root, args.figs)
    fig_histories(args.root, args.figs)
    fig_elastic_metrics(args.root, args.figs)
    fig_orbit(args.root, args.figs)
    fig_grid(args.root, args.figs)
    try:
        fig_fields(args.root, args.figs, run=args.fields_run,
                   coords_are_absolute=args.coords_absolute)
    except Exception as exc:  # noqa: BLE001
        print("field figure skipped:", exc)

    print("\n=== summary ===")
    for r in summary_table(args.root):
        line = (f"{r['run']:<20} t_end={r['t_end']:5.2f} n={r['n']:5d} "
                f"x[{r['x_range'][0]:.3f},{r['x_range'][1]:.3f}] "
                f"y[{r['y_range'][0]:.3f},{r['y_range'][1]:.3f}] "
                f"travel={r['travel']:.3f} path={r['path_len']:.3f}")
        if "disp_max" in r:
            line += f" max|us|={r['disp_max']:.3f} det_min={r['det_min']:.3f} V/V0={r['vol_rel']:.3f}"
        if "Fx_abs_max" in r:
            line += f" |Fx|max={r['Fx_abs_max']:.4f}"
        print(line)


if __name__ == "__main__":
    main()
