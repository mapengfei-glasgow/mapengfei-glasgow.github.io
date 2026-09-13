"""Render the demo_340 ideal-valve FSI case (2-D, fibre-reinforced leaflets).

Reads the XDMF/HDF5 written by ``afsic/demo/demo_340/main.py``:

    velocity.xdmf / .h5    nodal velocity on the channel grid   (P1, vector)
    solid_force.xdmf / .h5 the leaflet mesh + ``solid_coords_io`` (current
                           coordinates, so displacement = coords - reference)
                           and ``solid_force_io`` (IB force)

and draws, for a set of times spanning the pulse:

  * channel velocity magnitude with the deformed leaflets on top,
  * leaflet displacement magnitude on the deformed leaflet mesh,
  * the tip-displacement history against the published reference curves
    (Ryan et al. M2/M3, Kamensky et al.) archived in the demo.

Usage:
    python make_valve_figures.py OUTDIR --ref REFDIR [--figs FIGDIR]
                                       [--times 0,0.25,...,3.0]
"""

from __future__ import annotations

import argparse
import os
import xml.etree.ElementTree as ET

import h5py
import numpy as np

os.environ.setdefault("PYVISTA_OFF_SCREEN", "true")

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

# geometry of the case (main.py / generate_mesh.py)
LX, LY = 8.0, 1.61
LEAF_X, LEAF_W, LEAF_H = 2.0 - 0.0212, 0.0212, 0.7
PROBE = np.array([2.0 - 0.0106, 0.91 + 1e-4])  # tip probe used by main.py


class XdmfSeries:
    """A dolfinx XDMF series.

    Parallel dolfinx writes one Grid per rank per step, so the XML repeats each
    time value; entries are deduplicated by time.
    """

    def __init__(self, xdmf: str, field: str):
        self.dir = os.path.dirname(os.path.abspath(xdmf))
        root = ET.parse(xdmf).getroot()

        mesh_grid = root.find(".//Grid[@GridType='Uniform']")
        topo, geom = mesh_grid.find("Topology"), mesh_grid.find("Geometry")
        self.cell_type = topo.get("TopologyType")
        self.n_cells = int(topo.get("NumberOfElements"))
        self.n_points = int(geom.find("DataItem").get("Dimensions").split()[0])

        self.times, self.datasets = [], []
        seen = set()
        for grid in root.iter("Grid"):
            t, att = grid.find("Time"), grid.find("Attribute")
            if t is None or att is None or att.get("Name") != field:
                continue
            tv = float(t.get("Value"))
            if tv in seen:
                continue
            seen.add(tv)
            h5, _, dset = att.find("DataItem").text.strip().partition(":")
            self.times.append(tv)
            self.datasets.append((os.path.join(self.dir, h5), dset))
        order = np.argsort(self.times)
        self.times = np.asarray(self.times)[order]
        self.datasets = [self.datasets[i] for i in order]

        with h5py.File(self.datasets[0][0], "r") as f:
            self.cells = np.asarray(f["/Mesh/mesh/topology"], dtype=np.int64)
            self.points = np.asarray(f["/Mesh/mesh/geometry"], dtype=np.float64)

    def index(self, t: float) -> int:
        return int(np.argmin(np.abs(self.times - t)))

    def read(self, t: float):
        k = self.index(t)
        h5, dset = self.datasets[k]
        with h5py.File(h5, "r") as f:
            return float(self.times[k]), np.asarray(f[dset], dtype=np.float64)


def lattice(points: np.ndarray):
    xs = np.unique(np.round(points[:, 0], 12))
    ys = np.unique(np.round(points[:, 1], 12))
    return xs, ys


def to_lattice(vals, points, xs, ys):
    ix = np.searchsorted(xs, points[:, 0])
    iy = np.searchsorted(ys, points[:, 1])
    if vals.ndim == 1:
        out = np.empty((len(ys), len(xs)))
        out[iy, ix] = vals
        return out
    out = np.empty((len(ys), len(xs), vals.shape[1]))
    out[iy, ix, :] = vals
    return out


def inlet_profile(t: float) -> float:
    """Peak of the parabolic inlet 5 (sin 2 pi t + 1.1) y (Ly - y)."""
    return 5.0 * (np.sin(2.0 * np.pi * t) + 1.1)


def tip_displacement(disp, ref_points, t):
    """Displacement at the node nearest the tip probe, as main.py reports it.

    ``solid_coords_io`` holds the current coordinates, so the displacement is
    ``coords - reference``: the reference geometry is the mesh geometry, which
    dolfinx writes once and reuses for every step.
    """
    d = np.linalg.norm(ref_points - PROBE, axis=1)
    k = int(np.argmin(d))
    _, coords = disp.read(t)
    u = coords[k, :2] - ref_points[k, :2]
    return u, k, float(d[k])


# ---------------------------------------------------------------------------
def channel_figure(vel, disp, figs, times, name="340_valve", vmax=None,
                   dmax=None, xwin=(0.35, 4.35)):
    xs, ys = lattice(vel.points)
    Y, X = np.meshgrid(ys, xs, indexing="ij")
    x0, x1 = xwin

    if vmax is None:
        # the inlet sits at ~11 m/s and would wash out the channel; clip to the
        # 99.5th percentile over the plotted times so the interior is visible
        vmax = float(np.percentile(
            np.concatenate([np.linalg.norm(vel.read(t)[1][:, :2], axis=1) for t in times]), 99.5))
    if dmax is None:
        dmax = max(float(np.linalg.norm(disp.read(t)[1][:, :2] - disp.points[:, :2], axis=1).max())
                   for t in times)

    ncol = len(times)
    fig = plt.figure(figsize=(2.4 * ncol + 0.8, 7.8), constrained_layout=True)
    gs = fig.add_gridspec(3, ncol + 1, width_ratios=[1] * ncol + [0.04])
    axes = np.array([[fig.add_subplot(gs[r, c]) for c in range(ncol)] for r in range(3)])
    for j, t in enumerate(times):
        _, uv = vel.read(t)
        mag = np.linalg.norm(uv[:, :2], axis=1)
        mlat = to_lattice(mag, vel.points, xs, ys)

        ts, coords = disp.read(t)
        cur = coords[:, :2]
        u = cur - disp.points[:, :2]
        umag = np.linalg.norm(u, axis=1)
        lv = np.linspace(0, max(dmax, 1e-12), 12)

        # row 0: whole channel for context
        ax = axes[0][j]
        ax.pcolormesh(X, Y, mlat, cmap="turbo", vmin=0, vmax=vmax,
                      shading="gouraud", rasterized=True)
        ax.add_patch(plt.Rectangle((x0, 0), x1 - x0, LY, fill=False,
                                   ec="k", lw=1.0, ls="--"))
        ax.set_xlim(0, LX); ax.set_ylim(0, LY); ax.set_aspect("equal")
        ax.set_title(f"$t = {t:g}$ s", fontsize=11)
        ax.set_xticks([0, 4, 8]); ax.set_yticks([0, 0.8, 1.6])
        ax.tick_params(labelsize=8)
        if j:
            ax.set_yticklabels([])
        if j == 0:
            ax.set_ylabel("full channel", fontsize=10)

        # row 1: zoom on the valve with streamlines
        ax = axes[1][j]
        pc = ax.pcolormesh(X, Y, mlat, cmap="turbo", vmin=0, vmax=vmax,
                           shading="gouraud", rasterized=True)
        ulat = to_lattice(uv[:, :2], vel.points, xs, ys)
        m = (xs >= x0 - 0.15) & (xs <= x1 + 0.15)
        ax.streamplot(xs[m], ys, ulat[:, m, 0], ulat[:, m, 1],
                      color="k", density=1.7, linewidth=0.4, arrowsize=0.45, zorder=2)
        ax.tricontourf(cur[:, 0], cur[:, 1], disp.cells, umag, levels=lv,
                       cmap="magma", zorder=3)
        ax.triplot(cur[:, 0], cur[:, 1], disp.cells, color="k", lw=0.12,
                   alpha=0.3, zorder=4)
        ax.set_xlim(x0, x1); ax.set_ylim(0, LY); ax.set_aspect("equal")
        ax.set_xticks([]); ax.set_yticks([0, 0.8, 1.6])
        ax.tick_params(labelsize=8)
        if j:
            ax.set_yticklabels([])
        if j == 0:
            ax.set_ylabel("valve region + streamlines", fontsize=10)

        # row 2: the leaflets alone
        ax = axes[2][j]
        ax.set_xlim(LEAF_X - 1.0, LEAF_X + 1.0)
        ax.set_ylim(0, LY)
        ax.set_aspect("equal")
        ax.plot([LEAF_X] * 2, [0, LEAF_H], ":", color="0.55", lw=1.0, zorder=1)
        ax.plot([LEAF_X] * 2, [LY - LEAF_H, LY], ":", color="0.55", lw=1.0, zorder=1)
        tf = ax.tricontourf(cur[:, 0], cur[:, 1], disp.cells, umag, levels=lv,
                            cmap="magma", zorder=3)
        ax.triplot(cur[:, 0], cur[:, 1], disp.cells, color="k", lw=0.12,
                   alpha=0.35, zorder=4)
        ax.set_xticks([1, 2, 3]); ax.set_yticks([0, 0.8, 1.6])
        ax.tick_params(labelsize=8)
        if j:
            ax.set_yticklabels([])
        if j == 0:
            ax.set_ylabel("leaflet $|\\mathbf{u}_s|$ (zoom)", fontsize=10)

    cax0 = fig.add_subplot(gs[1, ncol])
    fig.colorbar(pc, cax=cax0).set_label("$|\\mathbf{u}|$  [m/s]", fontsize=9)
    cax1 = fig.add_subplot(gs[2, ncol])
    fig.colorbar(tf, cax=cax1).set_label("$|\\mathbf{u}_s|$  [m]", fontsize=9)
    fig.suptitle("demo_340 — 2-D ideal valve: channel velocity, valve-region flow and "
                 "leaflet displacement (FRH $45^\\circ$, inlet period 1 s)", fontsize=12)
    out = os.path.join(figs, name + ".png")
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print("wrote", out)
    return vmax, dmax



def history_figure(refdir, figs, times, probe=None, name="340_history"):
    """Tip displacement vs the published reference curves (and this run's trace)."""
    tr = np.genfromtxt(os.path.join(refdir, "data", "ani_t.csv"), skip_header=1)
    ax_ = np.genfromtxt(os.path.join(refdir, "data", "ani_x.csv"), delimiter=",", skip_header=1)
    ay_ = np.genfromtxt(os.path.join(refdir, "data", "ani_y.csv"), delimiter=",", skip_header=1)
    if probe is None:
        probe = os.path.join(refdir, "data", "ani_probe_run.csv")
    probe = os.path.expanduser(probe)

    own = None
    if probe and os.path.exists(probe):
        own = np.genfromtxt(probe, delimiter=",", names=True)

    fig, axs = plt.subplots(1, 3, figsize=(15, 4.3), constrained_layout=True)

    ax = axs[0]
    for f, lab, st in [("X_M2.csv", "Ryan et al. (M2)", "g:"),
                       ("X_FSI.csv", "Ryan et al. (M3)", "b-."),
                       ("x_dis_ALE.csv", "Kamensky et al.", "k--")]:
        d = np.genfromtxt(os.path.join(refdir, f), delimiter=",", names=True)
        ax.plot(d[d.dtype.names[0]], d[d.dtype.names[1]], st, lw=1.8, label=lab)
    ax.plot(tr, ax_[:, 0], "-", color="0.55", lw=3.0, label="AFSI (archived $45^\\circ$)")
    if own is not None:
        ax.plot(own["t"], own["x_disp"], "r-", lw=1.0, label="this run (45$^\\circ$)")
    ax.set_xlabel("$t$ [s]"); ax.set_ylabel("$x$ displacement")
    ax.set_title("tip $x$-displacement vs literature")
    ax.set_xlim(0, 3.0); ax.grid(alpha=0.3); ax.legend(fontsize=8, loc="lower right")

    ax = axs[1]
    for f, lab, st in [("y_M2.csv", "Ryan et al. (M2)", "g:"),
                       ("Y_FSI.csv", "Ryan et al. (M3)", "b-."),
                       ("Y_ALE.csv", "Kamensky et al.", "k--")]:
        d = np.genfromtxt(os.path.join(refdir, f), delimiter=",", names=True)
        ax.plot(d[d.dtype.names[0]], d[d.dtype.names[1]], st, lw=1.8, label=lab)
    ax.plot(tr, ay_[:, 0], "-", color="0.55", lw=3.0, label="AFSI (archived $45^\\circ$)")
    if own is not None:
        ax.plot(own["t"], own["y_disp"], "r-", lw=1.0, label="this run (45$^\\circ$)")
    ax.set_xlabel("$t$ [s]"); ax.set_ylabel("$y$ displacement")
    ax.set_title("tip $y$-displacement vs literature")
    ax.set_xlim(0, 3.0); ax.grid(alpha=0.3); ax.legend(fontsize=8, loc="lower right")

    ax = axs[2]
    tt = np.linspace(0, 3.0, 601)
    ax.plot(tt, inlet_profile(tt), "k-", lw=1.4)
    ax.axhline(0, color="0.7", lw=0.8)
    ax.set_xlabel("$t$ [s]"); ax.set_ylabel("inlet peak $u_x$")
    ax.set_title("inlet forcing $5(\\sin 2\\pi t + 1.1)$")
    for t in times:
        ax.axvline(t, color="crimson", lw=0.7, alpha=0.5)
    ax.set_xlim(0, 3.0); ax.grid(alpha=0.3)

    out = os.path.join(figs, name + ".png")
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print("wrote", out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("outdir", help="run output dir (velocity.xdmf, solid_force.xdmf)")
    ap.add_argument("--ref", required=True, help="demo plot dir holding the reference CSVs")
    ap.add_argument("--figs", default="figs")
    ap.add_argument("--times", default=None)
    ap.add_argument("--tend", type=float, default=None, help="last time to include")
    ap.add_argument("--probe", default=None, help="per-step probe trace csv for this run")
    args = ap.parse_args()
    os.makedirs(args.figs, exist_ok=True)

    vel = XdmfSeries(os.path.join(args.outdir, "velocity.xdmf"), "f")
    disp = XdmfSeries(os.path.join(args.outdir, "solid_force.xdmf"), "solid_coords_io")
    print(f"velocity: {len(vel.times)} steps t=[{vel.times.min():.4f},{vel.times.max():.4f}] "
          f"{vel.cell_type} cells={vel.n_cells} nodes={vel.n_points}")
    print(f"leaflets: {len(disp.times)} steps cells={disp.n_cells} nodes={disp.n_points}")

    tend = args.tend if args.tend is not None else float(vel.times.max())
    if args.times:
        times = [float(x) for x in args.times.split(",")]
    else:
        span = min(tend, 1.5)
        times = [round(span * k / 6, 4) for k in range(7)]
    times = [t for t in times if t <= vel.times.max() + 5e-3]
    print("times:", times)

    for t in times:
        u, k, dist = tip_displacement(disp, disp.points, t)
        print(f"  t={t:<6g} tip node {k} (d={dist:.2e}) disp = ({u[0]:+.5f}, {u[1]:+.5f}) m"
              f"   inlet peak = {inlet_profile(t):.3f}")

    vmax, dmax = channel_figure(vel, disp, args.figs, times)
    for t in times:
        channel_figure(vel, disp, args.figs, [t], name=f"340_snap_t{t:06.3f}",
                       vmax=vmax, dmax=dmax)
    history_figure(args.ref, args.figs, times, probe=args.probe)


if __name__ == "__main__":
    main()
