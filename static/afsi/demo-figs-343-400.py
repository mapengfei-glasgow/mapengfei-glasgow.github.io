"""Field figures for demo_343 (discs through the ideal valve) and demo_400 (turtle)."""

from __future__ import annotations

import argparse
import os

import numpy as np

os.environ.setdefault("PYVISTA_OFF_SCREEN", "true")
import pyvista as pv  # noqa: E402

pv.OFF_SCREEN = True

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from make_demo_figures import Series, lattice, quad_grid, to_lattice  # noqa: E402


# ---------------------------------------------------------------------------
# demo_343 — two discs carried through the ideal valve
# ---------------------------------------------------------------------------
def case343(outdir, figs, times=None):
    vel = Series(os.path.join(outdir, "velocity.xdmf"), "f")
    sol = Series(os.path.join(outdir, "solid_force.xdmf"), "solid_coords_io")
    sfo = Series(os.path.join(outdir, "solid_force.xdmf"), "solid_force_io")
    print(f"343: velocity {len(vel.times)} steps t=[{vel.times.min():.4f},{vel.times.max():.4f}] "
          f"cells={vel.n_cells} nodes={vel.n_points}")
    print(f"     solid cells={sol.n_cells} nodes={sol.n_points}")

    if times is None:
        tmax = float(vel.times.max())
        n = 6
        times = [round(tmax * k / (n - 1), 6) for k in range(n)]

    xs, ys = lattice(vel.points)
    Y, X = np.meshgrid(ys, xs, indexing="ij")
    vmax = float(np.percentile(np.concatenate(
        [np.linalg.norm(vel.read(t)[1][:, :2], axis=1) for t in times]), 99.5))
    # the two discs and the two leaflets, separated by displacement magnitude
    dmax = max(float(np.linalg.norm(sol.read(t)[1][:, :2] - sol.points[:, :2], axis=1).max())
               for t in times)
    print(f"     |u| p99.5 = {vmax:.3f}, solid |u_s| max = {dmax:.4f}")

    ncol = len(times)
    fig, axes = plt.subplots(2, ncol, figsize=(2.6 * ncol, 5.2),
                             constrained_layout=True, squeeze=False)
    for j, t in enumerate(times):
        _, uv = vel.read(t)
        _, coords = sol.read(t)
        cur = coords[:, :2]
        u = cur - sol.points[:, :2]
        umag = np.linalg.norm(u, axis=1)

        ax = axes[0][j]
        ax.pcolormesh(X, Y, to_lattice(np.linalg.norm(uv[:, :2], axis=1), vel.points, xs, ys),
                      cmap="turbo", vmin=0, vmax=vmax, shading="gouraud", rasterized=True)
        ax.tricontourf(cur[:, 0], cur[:, 1], sol.cells, umag,
                       levels=np.linspace(0, max(dmax, 1e-12), 10), cmap="magma", zorder=3)
        ax.triplot(cur[:, 0], cur[:, 1], sol.cells, color="k", lw=0.1, alpha=0.3, zorder=4)
        ax.set_xlim(0, 4.0); ax.set_ylim(0, 1.61); ax.set_aspect("equal")
        ax.set_title(f"$t = {t*1e3:.2f}$ ms", fontsize=11)
        ax.set_xticks([0, 1, 2, 3, 4]); ax.set_yticks([0, 0.8, 1.6])
        ax.tick_params(labelsize=8)
        if j:
            ax.set_yticklabels([])
        if j == 0:
            ax.set_ylabel("velocity + solids", fontsize=10)

        ax = axes[1][j]
        ax.set_xlim(1.6, 2.6); ax.set_ylim(0, 1.61); ax.set_aspect("equal")
        ax.pcolormesh(X, Y, to_lattice(np.linalg.norm(uv[:, :2], axis=1), vel.points, xs, ys),
                      cmap="turbo", vmin=0, vmax=vmax, shading="gouraud", rasterized=True)
        ax.tricontourf(cur[:, 0], cur[:, 1], sol.cells, umag,
                       levels=np.linspace(0, max(dmax, 1e-12), 10), cmap="magma", zorder=3)
        ax.triplot(cur[:, 0], cur[:, 1], sol.cells, color="k", lw=0.12, alpha=0.35, zorder=4)
        ax.set_xticks([1.6, 2.0, 2.4]); ax.set_yticks([0, 0.8, 1.6])
        ax.tick_params(labelsize=8)
        if j:
            ax.set_yticklabels([])
        if j == 0:
            ax.set_ylabel("valve region (zoom)", fontsize=10)

    fig.suptitle("demo_343 — two soft discs carried through the ideal valve "
                 "(solid shading = own displacement, magma)", fontsize=12)
    out = os.path.join(figs, "343_valve_discs.png")
    fig.savefig(out, dpi=150); plt.close(fig)
    print("wrote", out)

    # --- displacement history of the discs (they are the softest material) ---
    ts = np.linspace(float(sol.times.min()), float(sol.times.max()), 60)
    hist = []
    for t in ts:
        _, coords = sol.read(t)
        cur = coords[:, :2]
        u = np.linalg.norm(cur - sol.points[:, :2], axis=1)
        hist.append([u.max(), np.median(u)])
    hist = np.array(hist)
    fig, ax = plt.subplots(figsize=(7.5, 4.2), constrained_layout=True)
    ax.plot(ts * 1e3, hist[:, 0], lw=1.5, label="max over all solids")
    ax.plot(ts * 1e3, hist[:, 1], lw=1.3, label="median")
    ax.set_xlabel("$t$ [ms]"); ax.set_ylabel("$|u_s|$ [m]")
    ax.set_title("demo_343 — solid displacement over the run")
    ax.grid(alpha=0.3); ax.legend(fontsize=9)
    out2 = os.path.join(figs, "343_displacement.png")
    fig.savefig(out2, dpi=150); plt.close(fig)
    print("wrote", out2)


# ---------------------------------------------------------------------------
# demo_400 — turtle under a follower pressure
# ---------------------------------------------------------------------------
def case400(outdir, figs, times=None, log=None):
    vel = Series(os.path.join(outdir, "velocity.xdmf"), "f")
    pre = Series(os.path.join(outdir, "pressure.xdmf"), "f")
    sol = Series(os.path.join(outdir, "solid_force.xdmf"), "solid_coords_io")
    print(f"400: velocity {len(vel.times)} steps t=[{vel.times.min():.3f},{vel.times.max():.3f}] "
          f"cells={vel.n_cells} nodes={vel.n_points}")
    print(f"     solid cells={sol.n_cells} nodes={sol.n_points}")

    if times is None:
        tmax = float(vel.times.max())
        times = [round(tmax * k / 5, 4) for k in range(6)]

    xs, ys = lattice(vel.points)
    Y, X = np.meshgrid(ys, xs, indexing="ij")
    vmax = float(np.percentile(np.concatenate(
        [np.linalg.norm(vel.read(t)[1][:, :2], axis=1) for t in times]), 99.5))
    pmax = float(np.percentile(np.abs(np.concatenate(
        [pre.read(t)[1].ravel() for t in times])), 99.0))
    print(f"     |u| p99.5 = {vmax:.4g} m/s, |p| p99 = {pmax:.4g}")

    ncol = len(times)
    fig, axes = plt.subplots(2, ncol, figsize=(2.7 * ncol, 5.0),
                             constrained_layout=True, squeeze=False)
    for j, t in enumerate(times):
        _, uv = vel.read(t)
        _, pv_ = pre.read(t)
        _, coords = sol.read(t)
        cur = coords[:, :2]

        ax = axes[0][j]
        ax.pcolormesh(X, Y, to_lattice(np.linalg.norm(uv[:, :2], axis=1), vel.points, xs, ys),
                      cmap="turbo", vmin=0, vmax=vmax, shading="gouraud", rasterized=True)
        ax.triplot(cur[:, 0], cur[:, 1], sol.cells, color="k", lw=0.5, alpha=0.9, zorder=4)
        ax.set_xlim(60, 175); ax.set_ylim(0, 100)
        ax.set_aspect("equal")
        ax.set_title(f"$t = {t:g}$ s", fontsize=11)
        ax.set_xticks([]); ax.set_yticks([])
        if j == 0:
            ax.set_ylabel("velocity + body outline", fontsize=9)

        ax = axes[1][j]
        ax.pcolormesh(X, Y, to_lattice(pv_.ravel(), pre.points, xs, ys),
                      cmap="RdBu_r", vmin=-pmax, vmax=pmax, shading="gouraud", rasterized=True)
        ax.triplot(cur[:, 0], cur[:, 1], sol.cells, color="k", lw=0.4, alpha=0.7, zorder=4)
        ax.set_xlim(60, 175); ax.set_ylim(0, 100)
        ax.set_aspect("equal")
        ax.set_xticks([]); ax.set_yticks([])
        if j == 0:
            ax.set_ylabel("pressure", fontsize=9)

    fig.suptitle("demo_400 — 2-D turtle under a periodic follower pressure "
                 "(200 x 100 channel; shaded region = velocity |u|, magenta = velocity, outline = body)", fontsize=12)
    out = os.path.join(figs, "400_turtle.png")
    fig.savefig(out, dpi=150); plt.close(fig)
    print("wrote", out)

    # --- history: limb-tip displacement and pressure load ---
    ts = np.linspace(float(sol.times.min()), float(sol.times.max()), 80)
    tipA, tipB = [], []
    for t in ts:
        _, coords = sol.read(t)
        u = coords[:, :2] - sol.points[:, :2]
        # limbs are the two extremes in y; head/tail are fixed by penalty
        top = u[:, 1].argmax(); bot = u[:, 1].argmin()
        tipA.append(u[top, 1]); tipB.append(u[bot, 1])
    umax = []
    for t in ts:
        _, uv = vel.read(t)
        umax.append(float(np.linalg.norm(uv[:, :2], axis=1).max()))
    fig, axs = plt.subplots(1, 3, figsize=(15.5, 4.2), constrained_layout=True)
    axs[0].plot(ts, umax, lw=1.4, color="tab:blue")
    axs[0].set_yscale("log")
    axs[0].set_xlabel("$t$ [s]"); axs[0].set_ylabel("max $|\\mathbf{u}|$ [m/s]")
    axs[0].set_title("fluid velocity: 1.2 m/s at $t=0.35$ s, 28 m/s at $t=1$ s")
    axs[0].grid(alpha=0.3, which="both")
    axs[1].plot(ts, tipA, lw=1.4, label="largest $+y$ displacement")
    axs[1].plot(ts, tipB, lw=1.4, label="largest $-y$ displacement")
    axs[1].set_xlabel("$t$ [s]"); axs[1].set_ylabel("$y$ displacement [m]")
    axs[1].set_title("limb deflection (body height is 33.8 m)")
    axs[1].grid(alpha=0.3); axs[1].legend(fontsize=9)
    if log and os.path.exists(log):
        d = np.genfromtxt(log, delimiter=",", names=True, deletechars="")
        axs[2].plot(d["time"], d["p_ext.value"], lw=1.5, color="crimson")
        axs[2].set_xlabel("$t$ [s]"); axs[2].set_ylabel("follower pressure")
        axs[2].set_title("applied load (fast-open, period 2 s)")
        axs[2].grid(alpha=0.3)
    out2 = os.path.join(figs, "400_history.png")
    fig.savefig(out2, dpi=150); plt.close(fig)
    print("wrote", out2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--case", required=True, choices=["343", "400"])
    ap.add_argument("--out", required=True)
    ap.add_argument("--figs", required=True)
    ap.add_argument("--times", default=None)
    ap.add_argument("--log", default=None)
    args = ap.parse_args()
    os.makedirs(args.figs, exist_ok=True)
    times = [float(x) for x in args.times.split(",")] if args.times else None
    if args.case == "343":
        case343(args.out, args.figs, times)
    else:
        case400(args.out, args.figs, times, args.log)


if __name__ == "__main__":
    main()
