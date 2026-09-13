"""PyVista figures for three fast 2-D AFSI demos.

Covers:
  * demo_339 / 4-multi-direct-forcing — DFG 2-D-3 flow past a cylinder, Re = 100
  * demo_421 — NACA fish undulating around a closed circular tank
  * demo_423 — anisotropic fibre-reinforced ring in a driven cavity (verification)

All three write dolfinx XDMF/HDF5. Two notes on reading them here:

  * ``pv.get_reader`` (VTK's XdmfReader) cannot open this 2-D dolfinx output in
    this environment — it reports ``XDMF Error ... Can't Open Dataset`` and then
    the process dumps core — so the XDMF is parsed with ``xml.etree`` and the
    HDF5 datasets read with ``h5py``.
  * Everything after that is PyVista: the mesh is handed to
    ``pv.UnstructuredGrid``/``pv.StructuredGrid`` and all rendering (background
    scalar bars, cylinder/annulus meshes, the composite layout) goes through
    ``pv.Plotter`` off-screen.

Usage:
    python make_demo_figures.py --case 339 --out OUTDIR --figs FIGDIR [--trace LOG]
"""

from __future__ import annotations

import argparse
import os
import xml.etree.ElementTree as ET

import h5py
import numpy as np

os.environ.setdefault("PYVISTA_OFF_SCREEN", "true")
import pyvista as pv  # noqa: E402

pv.OFF_SCREEN = True

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402


# ---------------------------------------------------------------------------
# XDMF/HDF5 reading
# ---------------------------------------------------------------------------
class Series:
    """A dolfinx XDMF time series: one fixed mesh, one nodal field per step.

    Parallel dolfinx repeats each time value once per rank; entries are
    deduplicated by time.
    """

    def __init__(self, xdmf: str, field: str = "f"):
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
    xs = np.unique(np.round(points[:, 0], 10))
    ys = np.unique(np.round(points[:, 1], 10))
    return xs, ys


def _index_of(a: np.ndarray, grid: np.ndarray) -> np.ndarray:
    idx = np.clip(np.searchsorted(grid, a), 0, len(grid) - 1)
    bad = ~np.isclose(grid[idx], a, rtol=0.0, atol=1e-9)
    if bad.any():
        idx[bad] = np.abs(grid[None, :] - a[bad, None]).argmin(axis=1)
    return idx


def to_lattice(vals, points, xs, ys):
    # exact index lookup: searchsorted misplaces nodes whose coordinates differ
    # from the rounded lattice by ~1 ulp (the mesh corners do)
    ix = _index_of(points[:, 0], xs)
    iy = _index_of(points[:, 1], ys)
    if vals.ndim == 1:
        out = np.empty((len(ys), len(xs)))
        out[iy, ix] = vals
        return out
    out = np.empty((len(ys), len(xs), vals.shape[1]))
    out[iy, ix, :] = vals
    return out


def quad_grid(points: np.ndarray, cells: np.ndarray, data: dict) -> pv.UnstructuredGrid:
    """Build a PyVista grid from a dolfinx quad mesh plus nodal arrays."""
    pts3 = np.c_[points[:, :2], np.zeros(len(points))]
    g = pv.UnstructuredGrid({pv.CellType.QUAD: cells}, pts3)
    for k, v in data.items():
        g.point_data[k] = np.c_[v, np.zeros(len(v))] if v.ndim == 2 else v
    return g


def mask_disc(g: pv.UnstructuredGrid, center, radius, pad=0.0):
    """Blank the cells inside a disc so the solid reads as a hole in the field."""
    c = np.asarray(center, dtype=float)
    g = g.copy()
    inside = np.linalg.norm(g.cell_centers().points[:, :2] - c, axis=1) < radius + pad
    for name in list(g.point_data.keys()):
        arr = np.array(g.point_data[name], dtype=float)
        if arr.ndim == 1:
            arr[inside] = np.nan
        else:
            arr[inside, :] = np.nan
        g.point_data[name] = arr
    return g


# ---------------------------------------------------------------------------
# demo_339 — flow past a cylinder
# ---------------------------------------------------------------------------
def case339(outdir, figs, trace=None, cylinder=(0.2, 0.2, 0.05), times=None):
    vel = Series(os.path.join(outdir, "velocity.xdmf"), "f")
    pre = Series(os.path.join(outdir, "pressure.xdmf"), "f")
    print(f"339: velocity {len(vel.times)} steps t=[{vel.times.min():.3f},{vel.times.max():.3f}] "
          f"{vel.cell_type} cells={vel.n_cells} nodes={vel.n_points}")
    xs, ys = lattice(vel.points)
    print(f"     lattice {len(xs)} x {len(ys)}")

    if times is None:
        tmax = float(vel.times.max())
        times = [round(tmax * k / 5, 4) for k in range(6)]

    vmax = float(np.percentile(np.concatenate(
        [np.linalg.norm(vel.read(t)[1][:, :2], axis=1) for t in times]), 99.5))
    pmax = float(np.percentile(np.abs(np.concatenate(
        [pre.read(t)[1].ravel() for t in times])), 99.0))
    print(f"     |u| p99.5 = {vmax:.3f}, |p| p99 = {pmax:.3f}")

    Y, X = np.meshgrid(ys, xs, indexing="ij")
    ncol = len(times)
    fig = plt.figure(figsize=(2.6 * ncol + 0.9, 6.4), constrained_layout=True)
    gs = fig.add_gridspec(2, ncol + 1, width_ratios=[1] * ncol + [0.04])
    axs = np.array([[fig.add_subplot(gs[r, c]) for c in range(ncol)] for r in range(2)])

    plots = {}
    for j, t in enumerate(times):
        _, uv = vel.read(t)
        _, pv_ = pre.read(t)
        mag = np.linalg.norm(uv[:, :2], axis=1)
        mL = to_lattice(mag, vel.points, xs, ys)
        pL = to_lattice(pv_, pre.points, xs, ys).squeeze(-1)
        uL = to_lattice(uv[:, :2], vel.points, xs, ys)

        ax = axs[0][j]
        im = ax.pcolormesh(X, Y, mL, cmap="turbo", vmin=0, vmax=vmax,
                           shading="gouraud", rasterized=True)
        plots["u"] = im
        sp = 2
        ax.streamplot(xs[::sp], ys[::sp], uL[::sp, ::sp, 0], uL[::sp, ::sp, 1],
                      color="k", density=1.3, linewidth=0.5, arrowsize=0.6, zorder=3)
        ax.add_patch(plt.Circle(cylinder[:2], cylinder[2], color="0.25", zorder=4))
        ax.set_xlim(0, 2.2); ax.set_ylim(0, 0.41); ax.set_aspect("equal")
        ax.set_title(f"$t = {t:g}$ s", fontsize=11)
        if j == 0:
            ax.set_ylabel("velocity + streamlines", fontsize=10)
        ax.set_yticks([0, 0.2, 0.4]); ax.tick_params(labelsize=8)
        if j:
            ax.set_yticklabels([])

        ax = axs[1][j]
        from matplotlib.colors import SymLogNorm
        im2 = ax.pcolormesh(X, Y, pL, cmap="RdBu_r", shading="gouraud", rasterized=True,
                            norm=SymLogNorm(linthresh=0.05 * pmax, vmin=-pmax, vmax=pmax))
        plots["p"] = im2
        ax.add_patch(plt.Circle(cylinder[:2], cylinder[2], color="0.25", zorder=4))
        ax.set_xlim(0, 2.2); ax.set_ylim(0, 0.41); ax.set_aspect("equal")
        if j == 0:
            ax.set_ylabel("pressure", fontsize=10)
        ax.set_yticks([0, 0.2, 0.4]); ax.tick_params(labelsize=8)
        if j:
            ax.set_yticklabels([])

    cax0 = fig.add_subplot(gs[0, ncol])
    fig.colorbar(plots["u"], cax=cax0).set_label("$|\\mathbf{u}|$  [m/s]", fontsize=9)
    cax1 = fig.add_subplot(gs[1, ncol])
    fig.colorbar(plots["p"], cax=cax1).set_label("$p$  [Pa]", fontsize=9)
    fig.suptitle("demo_339 — flow past a cylinder (DFG 2-D-3, Re = 100, "
                 "multi-direct forcing)", fontsize=12.5)
    out = os.path.join(figs, "339_cylinder.png")
    fig.savefig(out, dpi=150); plt.close(fig)
    print("wrote", out)

    # --- drag/lift history parsed from the run log ---
    if trace and os.path.exists(trace):
        t_, cd, cl = [], [], []
        for line in open(trace):
            if not line.startswith("Step "):
                continue
            parts = dict(p.split("=") for p in line.strip().split(", ")[1:])
            try:
                t_.append(float(parts["t"].rstrip("s")))
                cd.append(float(parts["Cd"]))
                cl.append(float(parts["Cl"]))
            except (KeyError, ValueError):
                continue
        t_ = np.asarray(t_); cd = np.asarray(cd); cl = np.asarray(cl)
        if len(t_) > 2:
            from scipy.signal import find_peaks
            fig, axs = plt.subplots(1, 2, figsize=(12, 4.0), constrained_layout=True)
            axs[0].plot(t_, cd, lw=1.3, label="$C_d$")
            axs[0].plot(t_, cl, lw=1.1, label="$C_l$", alpha=0.8)
            axs[0].set_xlabel("$t$ [s]"); axs[0].set_ylabel("force coefficient")
            axs[0].set_title("cylinder drag and lift"); axs[0].grid(alpha=0.3)
            axs[0].legend(fontsize=9)
            tail = t_ > 0.5 * t_.max()
            pk, _ = find_peaks(cl[tail])
            if len(pk) > 1:
                per = float(np.mean(np.diff(t_[tail][pk])))
                axs[1].plot(t_[tail], cl[tail], lw=1.2)
                axs[1].plot(t_[tail][pk], cl[tail][pk], "ro", ms=4)
                axs[1].set_title(f"lift, late window — shedding period $\\approx${per:.3f} s")
            else:
                axs[1].plot(t_, cl, lw=1.2)
                axs[1].set_title("lift (no clean period yet)")
            axs[1].set_xlabel("$t$ [s]"); axs[1].set_ylabel("$C_l$"); axs[1].grid(alpha=0.3)
            out2 = os.path.join(figs, "339_forces.png")
            fig.savefig(out2, dpi=150); plt.close(fig)
            print("wrote", out2, f"(Cd mean {cd[tail].mean():.3f}, Cl rms {cl[tail].std():.3f})")


# ---------------------------------------------------------------------------
# demo_421 — fish in a circular tank
# ---------------------------------------------------------------------------
def read_fish_trace(path: str):
    with open(path) as fh:
        names = fh.readline().strip().split(",")
    data = np.genfromtxt(path, delimiter=",", skip_header=1)
    return names, data


def case421(outdir, figs, trace_csv=None, times=None):
    vel = Series(os.path.join(outdir, "velocity.xdmf"), "f")
    pre = Series(os.path.join(outdir, "pressure.xdmf"), "f")
    print(f"421: velocity {len(vel.times)} steps t=[{vel.times.min():.3f},{vel.times.max():.3f}] "
          f"{vel.cell_type} cells={vel.n_cells} nodes={vel.n_points}")

    names = data = None
    if trace_csv and os.path.exists(trace_csv):
        names, data = read_fish_trace(trace_csv)
        print(f"     fish trace: {data.shape[0]} steps, {len(names)//2} body markers")

    if times is None:
        tmax = float(vel.times.max())
        times = [round(tmax * k / 5, 4) for k in range(6)]

    vmax = float(np.percentile(np.concatenate(
        [np.linalg.norm(vel.read(t)[1][:, :2], axis=1) for t in times]), 99.5))
    print(f"     |u| p99.5 = {vmax:.4f} m/s")

    xs, ys = lattice(vel.points)
    Y, X = np.meshgrid(ys, xs, indexing="ij")
    ncol = len(times)
    fig = plt.figure(figsize=(2.9 * ncol, 6.0), constrained_layout=True)
    gs = fig.add_gridspec(2, ncol)
    axs = np.array([[fig.add_subplot(gs[r, c]) for c in range(ncol)] for r in range(2)])

    for j, t in enumerate(times):
        _, uv = vel.read(t)
        mag = np.linalg.norm(uv[:, :2], axis=1)
        mL = to_lattice(mag, vel.points, xs, ys)
        uL = to_lattice(uv[:, :2], vel.points, xs, ys)

        ax = axs[0][j]
        ax.pcolormesh(X, Y, mL, cmap="turbo", vmin=0, vmax=vmax,
                      shading="gouraud", rasterized=True)
        ax.streamplot(xs[::3], ys[::3], uL[::3, ::3, 0], uL[::3, ::3, 1],
                      color="w", density=1.5, linewidth=0.5, arrowsize=0.5)
        if data is not None:
            k = int(np.argmin(np.abs(data[:, 0] - t)))
            mx = data[k, 1::2]; my = data[k, 2::2]
            ax.plot(mx, my, "-", color="k", lw=1.4, zorder=5)
        ax.set_xlim(0, 1.4); ax.set_ylim(0, 1.4); ax.set_aspect("equal")
        ax.set_title(f"$t = {t:g}$ s", fontsize=11)
        ax.set_xticks([]); ax.set_yticks([])
        if j == 0:
            ax.set_ylabel("tank velocity + streamlines", fontsize=10)

        ax = axs[1][j]
        k = int(np.argmin(np.abs(data[:, 0] - t))) if data is not None else 0
        cx = data[k, 1::2].mean(); cy = data[k, 2::2].mean()
        ax.set_xlim(cx - 0.25, cx + 0.25); ax.set_ylim(cy - 0.25, cy + 0.25)
        ax.set_aspect("equal")
        ax.pcolormesh(X, Y, mL, cmap="turbo", vmin=0, vmax=vmax,
                      shading="gouraud", rasterized=True)
        ax.streamplot(xs[::2], ys[::2], uL[::2, ::2, 0], uL[::2, ::2, 1],
                      color="w", density=2.0, linewidth=0.6, arrowsize=0.6)
        if data is not None:
            ax.plot(data[k, 1::2], data[k, 2::2], "-", color="k", lw=1.6, zorder=5)
        ax.set_xticks([]); ax.set_yticks([])
        if j == 0:
            ax.set_ylabel("near-body zoom", fontsize=10)

    fig.suptitle("demo_421 — undulating fish in a closed tank "
                 "(multi-direct forcing): field and near-body zoom", fontsize=12.5)
    out = os.path.join(figs, "421_fish.png")
    fig.savefig(out, dpi=150); plt.close(fig)
    print("wrote", out)

    if data is not None:
        cx = data[:, 1::2].mean(axis=1)
        cy = data[:, 2::2].mean(axis=1)
        fig, axs = plt.subplots(1, 2, figsize=(11, 4.2), constrained_layout=True)
        ax = axs[0]
        sc = ax.scatter(cx, cy, c=data[:, 0], cmap="viridis", s=28)
        ax.plot(cx, cy, "-", color="0.7", lw=0.8, zorder=0)
        ax.set_xlim(0, 1.4); ax.set_ylim(0, 1.4); ax.set_aspect("equal")
        ax.set_title("body-centroid path (tank is 14 body lengths across)")
        fig.colorbar(sc, ax=ax).set_label("$t$ [s]")
        ax = axs[1]
        ax.plot(data[:, 0], np.hypot(cx - cx[0], cy - cy[0]), lw=1.4, label="net travel")
        ax.set_xlabel("$t$ [s]"); ax.set_ylabel("centroid displacement [m]")
        ax.set_title("net displacement over the run"); ax.grid(alpha=0.3)
        ax.legend(fontsize=9)
        out3 = os.path.join(figs, "421_path.png")
        fig.savefig(out3, dpi=150); plt.close(fig)
        travel = float(np.hypot(cx - cx[0], cy - cy[0])[-1])
        print(f"wrote {out3} (net travel {travel:.4f} m = {travel/0.1:.2f} body lengths)")


# ---------------------------------------------------------------------------
# demo_423 — anisotropic ring verification
# ---------------------------------------------------------------------------
def case423(outdir, figs, N=32, R=0.25, w=0.0625, mu_s=1.0, times=None):
    vel = Series(os.path.join(outdir, "velocity.xdmf"), "f")
    pre = Series(os.path.join(outdir, "pressure.xdmf"), "f")
    sol = Series(os.path.join(outdir, "solid_force.xdmf"), "solid_force_io")
    print(f"423: velocity {len(vel.times)} steps, solid cells={sol.n_cells} nodes={sol.n_points}")

    t = times[-1] if times else float(vel.times.max())
    _, uv = vel.read(t)
    _, pv_ = pre.read(t)
    _, sv = sol.read(t)

    # numerical pressure on the fluid mesh, shifted to zero mean
    p = pv_.ravel() - pv_.mean()

    def exact_pressure(x, y):
        rr = np.sqrt((x - 0.5) ** 2 + (y - 0.5) ** 2)
        const = -np.pi * mu_s / (2.0 * 1.0 * 1.0) * ((R + w) ** 2 - R ** 2)
        inside = mu_s * np.log(1.0 + w / R) + const
        ring = mu_s * np.log((R + w) / np.maximum(rr, 1e-14)) + const
        return np.where(rr <= R, inside, np.where(rr < R + w, ring, const))

    pe = exact_pressure(vel.points[:, 0], vel.points[:, 1])
    pe = pe - pe.mean()

    xs, ys = lattice(vel.points)
    Y, X = np.meshgrid(ys, xs, indexing="ij")
    pL = to_lattice(p, vel.points, xs, ys)
    peL = to_lattice(pe, vel.points, xs, ys)
    errL = pL - peL
    mL = to_lattice(np.linalg.norm(uv[:, :2], axis=1), vel.points, xs, ys)

    fig, axs = plt.subplots(2, 2, figsize=(10.5, 9.0), constrained_layout=True)

    ax = axs[0][0]
    im = ax.pcolormesh(X, Y, mL, cmap="turbo", shading="gouraud", rasterized=True)
    uL = to_lattice(uv[:, :2], vel.points, xs, ys)
    ax.streamplot(xs[::2], ys[::2], uL[::2, ::2, 0], uL[::2, ::2, 1],
                  color="k", density=1.2, linewidth=0.5, arrowsize=0.6, zorder=3)
    ax.add_patch(plt.Circle((0.5, 0.5), R, fill=False, ec="k", lw=1.4, zorder=4))
    ax.add_patch(plt.Circle((0.5, 0.5), R + w, fill=False, ec="k", lw=1.4, ls="--", zorder=4))
    ax.set_title("fluid velocity $|\\mathbf{u}|$ + streamlines (dashed = ring)", fontsize=10)
    fig.colorbar(im, ax=ax, fraction=0.046).set_label("$|\\mathbf{u}|$", fontsize=9)

    ax = axs[0][1]
    lim = float(np.abs(pL).max())
    im = ax.pcolormesh(X, Y, pL, cmap="RdBu_r", vmin=-lim, vmax=lim,
                       shading="gouraud", rasterized=True)
    ax.add_patch(plt.Circle((0.5, 0.5), R + w, fill=False, ec="k", lw=1.2))
    ax.set_title("numerical pressure, zero mean", fontsize=10)
    fig.colorbar(im, ax=ax, fraction=0.046).set_label("$p$", fontsize=9)

    ax = axs[1][0]
    im = ax.pcolormesh(X, Y, peL, cmap="RdBu_r", vmin=-lim, vmax=lim,
                       shading="gouraud", rasterized=True)
    ax.add_patch(plt.Circle((0.5, 0.5), R + w, fill=False, ec="k", lw=1.2))
    ax.set_title("analytical pressure (same gauge)", fontsize=10)
    fig.colorbar(im, ax=ax, fraction=0.046).set_label("$p$", fontsize=9)

    ax = axs[1][1]
    el = float(np.abs(errL).max())
    im = ax.pcolormesh(X, Y, errL, cmap="coolwarm", vmin=-el, vmax=el,
                       shading="gouraud", rasterized=True)
    ax.add_patch(plt.Circle((0.5, 0.5), R + w, fill=False, ec="k", lw=1.2))
    rms = float(np.sqrt(np.nanmean(errL ** 2)))
    ax.set_title(f"pressure error, RMS $= {rms:.2e}$", fontsize=10)
    fig.colorbar(im, ax=ax, fraction=0.046).set_label("$p - p_{exact}$", fontsize=9)

    for ax in axs.ravel():
        ax.set_aspect("equal"); ax.set_xticks([]); ax.set_yticks([])
    fig.suptitle(f"demo_423 — anisotropic ring in a driven cavity ($N={N}$): "
                 "immersed-boundary pressure against the closed-form solution", fontsize=12)
    out = os.path.join(figs, "423_ring.png")
    fig.savefig(out, dpi=150); plt.close(fig)
    print("wrote", out, f"(RMS error {rms:.3e})")

    # --- PyVista rendering of the solid force field on the ring mesh ---
    _CT = {"quadrilateral": pv.CellType.QUAD, "triangle": pv.CellType.TRIANGLE,
           "hexahedron": pv.CellType.HEXAHEDRON, "tetrahedron": pv.CellType.TETRA}
    ctype = _CT[sol.cell_type.lower()]
    solid = pv.UnstructuredGrid({ctype: sol.cells},
                                np.c_[sol.points, np.zeros(len(sol.points))])
    solid["f_mag"] = np.linalg.norm(sv[:, :2], axis=1)
    fluid = quad_grid(vel.points, vel.cells, {"u_mag": np.linalg.norm(uv[:, :2], axis=1)})

    sb = dict(title="", n_labels=3, label_font_size=12, width=0.5, height=0.07,
              position_x=0.25, position_y=0.05)
    pl = pv.Plotter(off_screen=True, shape=(1, 2), window_size=(1240, 620),
                    border=False)
    pl.subplot(0, 0)
    pl.add_mesh(fluid, scalars="u_mag", cmap="turbo", show_edges=False,
                scalar_bar_args=dict(sb, title="|u| [m/s]"))
    pl.add_mesh(solid.extract_surface().extract_feature_edges(),
                color="black", line_width=3)
    pl.add_text("fluid |u|, ring mesh in black", position="upper_left", font_size=11)
    pl.view_xy()
    pl.subplot(0, 1)
    pl.add_mesh(fluid, scalars="u_mag", cmap="turbo", show_edges=False, opacity=0.2,
                show_scalar_bar=False)
    pl.add_mesh(solid, scalars="f_mag", cmap="magma", show_edges=True,
                edge_color="gray", line_width=0.5,
                scalar_bar_args=dict(sb, title="|f| IB force"))
    pl.add_text("IB force on the ring mesh", position="upper_left", font_size=11)
    pl.view_xy()
    out2 = os.path.join(figs, "423_pyvista.png")
    pl.screenshot(out2, return_img=False)
    pl.close()
    print("wrote", out2)


def case423_levels(level_dirs, figs):
    """PyVista: pressure error on the fluid mesh at three refinement levels."""
    levels = []
    for d in level_dirs:
        vel = Series(os.path.join(d, "velocity.xdmf"), "f")
        err = Series(os.path.join(d, "pressure_error.xdmf"), "pressure_error")
        t = float(vel.times.max())
        _, ev = err.read(t)
        N = len(lattice(vel.points)[0]) - 1
        levels.append(dict(N=N, vel=vel, err=ev.ravel(), dir=d))
        print(f"  N={N}: {len(vel.points)} nodes, |err|max={np.abs(ev).max():.3e}, "
              f"RMS={np.sqrt(np.mean(ev ** 2)):.3e}")

    emax = max(float(np.percentile(np.abs(l["err"]), 99.5)) for l in levels)
    sb = dict(title="", n_labels=4, label_font_size=13, width=0.55, height=0.06,
              position_x=0.22, position_y=0.04)

    pl = pv.Plotter(off_screen=True, shape=(1, len(levels)),
                    window_size=(560 * len(levels), 640), border=False)
    for i, l in enumerate(levels):
        pl.subplot(0, i)
        pts = l["vel"].points
        g = pv.UnstructuredGrid({pv.CellType.QUAD: l["vel"].cells},
                                np.c_[pts, np.zeros(len(pts))])
        g["p_err"] = l["err"]
        pl.add_mesh(g, scalars="p_err", cmap="coolwarm", clim=(-emax, emax),
                    show_edges=False, scalar_bar_args=dict(sb, title="p - p_exact"))
        pl.add_text(f"N = {l['N']} x {l['N']}", position="upper_left", font_size=13)
        pl.view_xy()
    out = os.path.join(figs, "423_conv_pyvista.png")
    pl.screenshot(out, return_img=False)
    pl.close()
    print("wrote", out)

    # --- quantitative profiles: p along y = 0.5 for every level ---
    R, w, mu_s = 0.25, 0.0625, 1.0

    def exact(x):
        rr = np.abs(x - 0.5)
        const = -np.pi * mu_s / 2.0 * ((R + w) ** 2 - R ** 2)
        ins = mu_s * np.log(1.0 + w / R) + const
        ring = mu_s * np.log((R + w) / np.maximum(rr, 1e-14)) + const
        return np.where(rr <= R, ins, np.where(rr < R + w, ring, const))

    fig, axs = plt.subplots(1, 2, figsize=(12.5, 4.4), constrained_layout=True)
    xx = np.linspace(0, 1, 801)
    axs[0].plot(xx, exact(xx) - exact(xx).mean(), "k--", lw=2.0, label="exact")
    for l in levels:
        vel = l["vel"]
        m = np.isclose(vel.points[:, 1], 0.5)
        # pressure was stored on the same nodes via pressure.xdmf
        pre = Series(os.path.join(l["dir"], "pressure.xdmf"), "f")
        _, pv_ = pre.read(float(vel.times.max()))
        p = pv_.ravel() - pv_.mean()
        o = np.argsort(vel.points[m, 0])
        axs[0].plot(vel.points[m, 0][o], p[m][o], lw=1.2, label=f"N={l['N']}")
    axs[0].set_xlabel("$x$ at $y = 0.5$"); axs[0].set_ylabel("$p - \\bar{p}$")
    axs[0].set_title("radial pressure profile"); axs[0].grid(alpha=0.3)
    axs[0].legend(fontsize=9)

    ns = np.array([l["N"] for l in levels], dtype=float)
    rms = np.array([float(np.sqrt(np.mean(l["err"] ** 2))) for l in levels])
    rmax = np.array([float(np.abs(l["err"]).max()) for l in levels])
    axs[1].loglog(ns, rms, "o-", label="RMS")
    axs[1].loglog(ns, rmax, "s-", label="max")
    ref = rms[0] * (ns / ns[0]) ** -1.0
    axs[1].loglog(ns, ref, "k:", lw=1.2, label="$h^{1}$ reference")
    axs[1].set_xlabel("$N$ (fluid elements per side)")
    axs[1].set_ylabel("pressure error vs exact")
    axs[1].set_title("interface-band error barely improves")
    axs[1].grid(alpha=0.3, which="both"); axs[1].legend(fontsize=9)
    out2 = os.path.join(figs, "423_conv_plot.png")
    fig.savefig(out2, dpi=150); plt.close(fig)
    print("wrote", out2, f"(RMS {rms.round(4)} at N={ns.astype(int)})")


def pv_field_panel(case, outdir, figs, t=None, ncol=2, window=(1300, 640)):
    """One PyVista figure per case: the fields, rendered off-screen with PyVista.

    Kept separate from the matplotlib summaries: PyVista draws the meshes
    (including the immersed solids) and the background scalar bars.
    """
    vel = Series(os.path.join(outdir, "velocity.xdmf"), "f")
    pre = Series(os.path.join(outdir, "pressure.xdmf"), "f")
    t = float(vel.times.max()) if t is None else t
    _, uv = vel.read(t)
    _, pv_ = pre.read(t)
    pts = vel.points
    pts3 = np.c_[pts, np.zeros(len(pts))]
    sb = dict(title="", n_labels=4, label_font_size=12, width=0.5, height=0.055,
              position_x=0.25, position_y=0.05)

    if case == "339":
        cx, cy, r = 0.2, 0.2, 0.05
        g = quad_grid(pts, vel.cells, {"u_mag": np.linalg.norm(uv[:, :2], axis=1),
                                       "p": pv_.ravel()})
        pl = pv.Plotter(off_screen=True, shape=(1, 2), window_size=window, border=False)
        pl.subplot(0, 0)
        pl.add_mesh(g, scalars="u_mag", cmap="turbo", show_edges=False,
                    scalar_bar_args=dict(sb, title="|u| [m/s]"))
        pl.add_mesh(pv.Circle(radius=r, resolution=128).translate((cx, cy, 0.0), inplace=False), color="black")
        pl.add_text(f"t = {t:.3f} s", position="upper_left", font_size=12)
        pl.view_xy()
        pl.subplot(0, 1)
        pclip = float(np.percentile(np.abs(g["p"]), 98))
        pl.add_mesh(g, scalars="p", cmap="RdBu_r", show_edges=False,
                    clim=(-pclip, pclip), scalar_bar_args=dict(sb, title="p [Pa]"))
        pl.add_mesh(pv.Circle(radius=r, resolution=128).translate((cx, cy, 0.0), inplace=False), color="black")
        pl.view_xy()
        out = os.path.join(figs, "339_pyvista_fields.png")
    elif case == "421":
        g = quad_grid(pts, vel.cells, {"u_mag": np.linalg.norm(uv[:, :2], axis=1),
                                       "p": pv_.ravel()})
        pl = pv.Plotter(off_screen=True, shape=(1, 2), window_size=window, border=False)
        pl.subplot(0, 0)
        pl.add_mesh(g, scalars="u_mag", cmap="turbo", show_edges=False,
                    scalar_bar_args=dict(sb, title="|u| [m/s]"))
        pl.add_text(f"t = {t:.3f} s", position="upper_left", font_size=12)
        pl.view_xy()
        pl.subplot(0, 1)
        pl.add_mesh(g, scalars="u_mag", cmap="turbo", show_edges=False,
                    show_scalar_bar=False)
        cx, cy = pts[:, 0].mean(), pts[:, 1].mean()
        pl.camera_position = "xy"
        pl.camera.focal_point = (cx, cy, 0.0)
        pl.camera.position = (cx, cy, 2.0)
        pl.camera.parallel_scale = 0.16
        pl.add_text("near-body zoom", position="upper_left", font_size=12)
        out = os.path.join(figs, "421_pyvista_fields.png")
    else:
        raise SystemExit("pv_field_panel: unsupported case")

    pl.screenshot(out, return_img=False)
    pl.close()
    print("wrote", out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--case", required=True, choices=["339", "421", "423", "423levels", "pv339", "pv421"])
    ap.add_argument("--out", required=True)
    ap.add_argument("--figs", required=True)
    ap.add_argument("--trace", default=None, help="run log (339) or fish_trace.csv (421)")
    ap.add_argument("--times", default=None)
    ap.add_argument("--N", type=int, default=32, help="fluid elements per side (423)")
    args = ap.parse_args()
    os.makedirs(args.figs, exist_ok=True)
    times = [float(x) for x in args.times.split(",")] if args.times else None

    if args.case in ("pv339", "pv421"):
        pv_field_panel(args.case[2:], args.out, args.figs, ncol=2)
        return
    if args.case == "423levels":
        case423_levels([x for x in args.out.split(",")], args.figs)
        return
    if args.case == "339":
        case339(args.out, args.figs, trace=args.trace, times=times)
    elif args.case == "421":
        case421(args.out, args.figs, trace_csv=args.trace, times=times)
    else:
        case423(args.out, args.figs, N=args.N, times=times)


if __name__ == "__main__":
    main()
