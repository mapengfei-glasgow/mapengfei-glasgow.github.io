"""Render case-336 (lid-driven cavity carrying a disc) snapshots with PyVista.

Input is the dolfinx XDMF/HDF5 time series written by
``afsic/demo/demo_336/multi-direct-frocing`` (or ``...-elastic``):

    velocity.xdmf / velocity.h5   nodal velocity      (P1, vector)
    pressure.xdmf / pressure.h5   nodal pressure      (P1, scalar)
    disk.xdmf     / disk.h5       solid reference mesh + nodal displacement

Output, for t = 0, 2, 4, 6, 8, 10 s: a 3 x 6 panel figure (velocity magnitude
with streamlines, pressure, warped solid displacement), per-time panels, and
trajectory / force summaries.

The HDF5 files are opened with h5py rather than VTK's XdmfReader: the reader
crashes on this 2-D dolfinx output, and the datasets are simple enough to read
directly (the same approach used for demo_424).

Usage:
    python make_figures.py RIGID_OUTDIR [--elastic ELASTIC_OUTDIR] [--figs FIGDIR]
"""

from __future__ import annotations

import argparse
import os
import shutil
import xml.etree.ElementTree as ET

import h5py
import numpy as np

os.environ.setdefault("PYVISTA_OFF_SCREEN", "true")
import pyvista as pv  # noqa: E402

pv.OFF_SCREEN = True

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Polygon as MplPolygon  # noqa: E402
from matplotlib.path import Path  # noqa: E402
from matplotlib.colors import Normalize, SymLogNorm  # noqa: E402
from scipy.interpolate import LinearNDInterpolator  # noqa: E402

TIMES = [0.0, 2.0, 4.0, 6.0, 8.0, 10.0]
R_DISC, C_DISC = 0.2, (0.6, 0.5)
WARP = 8.0


# ---------------------------------------------------------------------------
# reading
# ---------------------------------------------------------------------------
class Series:
    """A dolfinx XDMF time series: one fixed mesh, one nodal field per step."""

    def __init__(self, xdmf: str, field: str = "f"):
        self.dir = os.path.dirname(os.path.abspath(xdmf))
        root = ET.parse(xdmf).getroot()

        mesh_grid = root.find(".//Grid[@GridType='Uniform']")
        topo, geom = mesh_grid.find("Topology"), mesh_grid.find("Geometry")
        self.cell_type = topo.get("TopologyType")
        self.n_cells = int(topo.get("NumberOfElements"))
        self.n_points = int(geom.find("DataItem").get("Dimensions").split()[0])

        self.times, self.datasets = [], []
        for grid in root.iter("Grid"):
            t, att = grid.find("Time"), grid.find("Attribute")
            if t is None or att is None or att.get("Name") != field:
                continue
            h5, _, dset = att.find("DataItem").text.strip().partition(":")
            self.times.append(float(t.get("Value")))
            self.datasets.append((os.path.join(self.dir, h5), dset))
        self.times = np.asarray(self.times)

        with h5py.File(self.datasets[0][0], "r") as f:
            self.cells = np.asarray(f["/Mesh/mesh/topology"], dtype=np.int64)
            self.points = np.asarray(f["/Mesh/mesh/geometry"], dtype=np.float64)

    def index(self, t: float) -> int:
        return int(np.argmin(np.abs(self.times - t)))

    def read(self, t: float) -> tuple[float, np.ndarray]:
        k = self.index(t)
        h5, dset = self.datasets[k]
        with h5py.File(h5, "r") as f:
            vals = np.asarray(f[dset], dtype=np.float64)
        return float(self.times[k]), vals


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


def disc_outline(disp: Series, t: float, n: int = 361, shrink: float = 1.0):
    """Current disc outline = reference circle + interpolated nodal displacement."""
    _, u = disp.read(t)
    u = u[:, :2]
    interp = LinearNDInterpolator(disp.points, u, fill_value=np.nan)
    th = np.linspace(0.0, 2.0 * np.pi, n)
    ring = np.c_[C_DISC[0] + shrink * R_DISC * np.cos(th),
                 C_DISC[1] + shrink * R_DISC * np.sin(th)]
    d = interp(ring)
    bad = ~np.isfinite(d).all(axis=1)
    if bad.any():
        d[bad] = 0.0
    return ring + d, u


# ---------------------------------------------------------------------------
# rendering
# ---------------------------------------------------------------------------
def paint_region(rgba: np.ndarray, xs, ys, pts, color=(0.30, 0.30, 0.34, 1.0),
                 ss: int = 4):
    """Rasterise the disc polygon into an RGBA overlay on the (ny, nx) lattice."""
    nx, ny = len(xs), len(ys)
    sx = np.linspace(xs[0], xs[-1], ss * nx)
    sy = np.linspace(ys[0], ys[-1], ss * ny)
    SX, SY = np.meshgrid(sx, sy)
    inside = Path(pts).contains_points(np.c_[SX.ravel(), SY.ravel()]).reshape(SY.shape)
    cov = inside.reshape(ny, ss, nx, ss).mean(axis=(1, 3))  # cell coverage in [0, 1]
    if not (cov > 0).any():
        return rgba
    a = np.clip(cov, 0.0, 1.0)[..., None]
    rgb = np.array(color[:3])
    rgba[..., :3] = (1.0 - a * 0.88) * rgba[..., :3] + (a * 0.88) * rgb
    rgba[..., 3] = np.maximum(rgba[..., 3], a[..., 0])
    return rgba


def _dilate(mask: np.ndarray) -> np.ndarray:
    out = mask.copy()
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            out |= np.roll(np.roll(mask, dy, axis=0), dx, axis=1)
    return out


def draw_solid(ax, disp: Series, t: float, dmax: float, title: str | None = None):
    """Deformed solid: filled contours of |u| over the reference triangulation."""
    _, u = disp.read(t)
    u = u[:, :2]
    mag = np.linalg.norm(u, axis=1)
    ref = disp.points
    levels = np.linspace(0.0, max(dmax, 1e-12), 15)
    tf = ax.tricontourf(ref[:, 0], ref[:, 1], disp.cells, mag, levels=levels, cmap="turbo")
    ax.triplot(ref[:, 0], ref[:, 1], disp.cells, color="k", lw=0.2, alpha=0.35)
    th = np.linspace(0, 2 * np.pi, 361)
    ax.plot(C_DISC[0] + R_DISC * np.cos(th), C_DISC[1] + R_DISC * np.sin(th),
            "--", color="0.35", lw=1.0, zorder=1)
    step = max(1, len(ref) // 28)
    ax.quiver(ref[::step, 0], ref[::step, 1], 2.0 * u[::step, 0], 2.0 * u[::step, 1],
              angles="xy", scale_units="xy", scale=1.0, width=0.006, color="k", zorder=4)
    ax.set_aspect("equal")
    ax.set_xlim(C_DISC[0] - 0.34, C_DISC[0] + 0.34)
    ax.set_ylim(C_DISC[1] - 0.34, C_DISC[1] + 0.34)
    ax.set_xticks([])
    ax.set_yticks([])
    if title:
        ax.set_title(title, fontsize=11)
    return tf


def plot_scalar_with_disc(ax, X, Y, data, poly, *, cmap, vmin, vmax, label="",
                          fontsize=9, linthresh=None):
    if linthresh:
        norm = SymLogNorm(linthresh=linthresh, vmin=vmin, vmax=vmax)
    else:
        norm = Normalize(vmin=vmin, vmax=vmax)
    ax.pcolormesh(X, Y, data, cmap=cmap, norm=norm, shading="gouraud")
    ax.collections[-1].set_rasterized(True)
    overlay = np.zeros((*data.shape, 4))
    paint_region(overlay, X[0], Y[:, 0], poly)
    ax.imshow(overlay, origin="lower", zorder=4, aspect="auto",
              extent=(X.min(), X.max(), Y.min(), Y.max()), interpolation="bilinear")
    ax.set_xlim(X.min(), X.max())
    ax.set_ylim(Y.min(), Y.max())
    ax.set_aspect("equal")
    return ax.collections[0]


def panel_mosaic(vel, pre, disp, elastic, figs, times=TIMES):
    vmax = 0.0
    psamples = []
    dmax = 0.0
    for t in times:
        _, uv = vel.read(t)
        vmax = max(vmax, float(np.linalg.norm(uv[:, :2], axis=1).max()))
        _, pv_ = pre.read(t)
        psamples.append(pv_ - pv_.mean())
        _, uu = disp.read(t)
        dmax = max(dmax, float(np.linalg.norm(uu[:, :2], axis=1).max()))
    ps = np.concatenate(psamples)
    pmax = float(np.percentile(np.abs(ps), 99.9))
    print(f"colour limits: |u|max={vmax:.3f}  |p-pmean| p99={pmax:.3f} "
          f"(full range {ps.min():.2f}..{ps.max():.2f})  |d|max={dmax:.4f}")

    xs, ys = lattice(vel.points)
    Y, X = np.meshgrid(ys, xs, indexing="ij")

    nrow, ncol = 2, len(times)
    fig, axes = plt.subplots(nrow, ncol, figsize=(2.5 * ncol, 5.6),
                             constrained_layout=True, squeeze=False)
    for j, t in enumerate(times):
        _, uv = vel.read(t)
        _, pv_ = pre.read(t)
        poly, _ = disc_outline(disp, t)
        u_lat = to_lattice(uv[:, :2], vel.points, xs, ys)
        mag_lat = np.linalg.norm(u_lat, axis=2)
        p_lat = to_lattice(pv_ - pv_.mean(), pre.points, xs, ys).squeeze(-1)

        ax = axes[0][j]
        plot_scalar_with_disc(ax, X, Y, mag_lat, poly, cmap="turbo",
                              vmin=0, vmax=vmax)
        sp = 2
        ax.streamplot(xs[::sp], ys[::sp], u_lat[::sp, ::sp, 0], u_lat[::sp, ::sp, 1],
                      color="k", density=1.1, linewidth=0.5, arrowsize=0.6, zorder=5)
        cb = fig.colorbar(ax.collections[0], ax=ax, fraction=0.046, pad=0.02)
        cb.set_label("$|\\mathbf{u}|$", fontsize=9)
        ax.set_title(f"$t = {t:g}$ s", fontsize=12)

        ax = axes[1][j]
        plot_scalar_with_disc(ax, X, Y, p_lat, poly, cmap="RdBu_r",
                              vmin=-pmax, vmax=pmax, linthresh=0.05)
        cb = fig.colorbar(ax.collections[0], ax=ax, fraction=0.046, pad=0.02,
                          ticks=[-10, -1, -0.1, 0, 0.1, 1, 10])
        cb.ax.set_yticklabels(["-10", "-1", "-0.1", "0", "0.1", "1", "10"], fontsize=7)
        cb.set_label("$p-\\bar p$", fontsize=9)

        for r in (0, 1):
            axes[r][j].set_xticks([0, 0.5, 1.0])
            axes[r][j].set_yticks([0, 0.5, 1.0])
            if j:
                axes[r][j].set_yticklabels([])

    axes[0][0].set_ylabel("velocity + streamlines", fontsize=11)
    axes[1][0].set_ylabel("pressure  ($p-\\bar p$)", fontsize=11)

    fig.suptitle("demo_336 — lid-driven cavity carrying a disc "
                 "(rigid multi-direct forcing, $64^2$, $t = 0\\ldots10$ s)", fontsize=14)
    out = os.path.join(figs, "336_overview_0-10s.png")
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print("wrote", out)
    return vmax, pmax, dmax


def solid_figure(disp, figs, dmax, times=TIMES):
    """The disc itself, true scale, drawn at its deformed position.

    The disc travels further than its own radius (|u_s| up to 0.51 against
    r = 0.2), so the field is contoured on the deformed mesh; drawing it at the
    reference positions would show only the small overlap with the current pose.
    The dashed circle marks the initial position.
    """
    ref = disp.points
    th = np.linspace(0, 2 * np.pi, 361)
    ring = np.c_[C_DISC[0] + R_DISC * np.cos(th), C_DISC[1] + R_DISC * np.sin(th)]

    fig, axes = plt.subplots(1, len(times), figsize=(2.35 * len(times), 3.3),
                             constrained_layout=True, squeeze=False)
    axes = axes[0]
    for j, t in enumerate(times):
        tt, u = disp.read(t)
        u = u[:, :2]
        mag = np.linalg.norm(u, axis=1)
        cur = ref + u
        cx, cy = cur[:, 0].mean(), cur[:, 1].mean()
        levels = np.linspace(0.0, max(dmax, 1e-12), 15)

        ax = axes[j]
        # set the viewport BEFORE drawing: the contours are rasterized, so they
        # would otherwise be clipped against the default (reference-position) limits
        ax.set_xlim(cx - 0.24, cx + 0.24)
        ax.set_ylim(cy - 0.24, cy + 0.24)
        ax.set_aspect("equal")
        tf = ax.tricontourf(cur[:, 0], cur[:, 1], disp.cells, mag, levels=levels, cmap="turbo")
        ax.triplot(cur[:, 0], cur[:, 1], disp.cells, color="k", lw=0.15, alpha=0.3)
        ax.plot(ring[:, 0], ring[:, 1], "--", color="0.45", lw=1.0)
        ax.set_xticks([]); ax.set_yticks([])
        ax.set_title(f"$t = {t:g}$ s", fontsize=12)
        if j == 0:
            ax.set_ylabel("disc, true scale", fontsize=11)

    cb = fig.colorbar(tf, ax=list(axes), fraction=0.016, pad=0.008)
    cb.set_label("$|\\mathbf{u}_s|$", fontsize=9)
    fig.suptitle("demo_336 — rigid disc: displacement $\\mathbf{u}_s$ on the deformed grid, "
                 "dashed outline = initial position", fontsize=12.5)
    out = os.path.join(figs, "336_solid_disc_0-10s.png")
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print("wrote", out)


def panel_individual(vel, pre, disp, figs, vmax, pmax, dmax, times=TIMES):
    xs, ys = lattice(vel.points)
    Y, X = np.meshgrid(ys, xs, indexing="ij")
    for j, t in enumerate(times):
        _, uv = vel.read(t)
        _, pv_ = pre.read(t)
        poly, _ = disc_outline(disp, t)
        u_lat = to_lattice(uv[:, :2], vel.points, xs, ys)
        p_lat = to_lattice(pv_ - pv_.mean(), pre.points, xs, ys).squeeze(-1)

        fig, axs = plt.subplots(1, 3, figsize=(15, 4.8), constrained_layout=True)
        ax = axs[0]
        plot_scalar_with_disc(ax, X, Y, np.linalg.norm(u_lat, axis=2), poly, cmap="turbo",
                              vmin=0, vmax=vmax)
        sp = 2
        ax.streamplot(xs[::sp], ys[::sp], u_lat[::sp, ::sp, 0], u_lat[::sp, ::sp, 1],
                      color="k", density=1.3, linewidth=0.6, arrowsize=0.7, zorder=5)
        ax.set_title(f"velocity + streamlines, $t = {t:g}$ s")
        fig.colorbar(ax.collections[0], ax=ax).set_label("$|\\mathbf{u}|$")

        ax = axs[1]
        plot_scalar_with_disc(ax, X, Y, p_lat, poly, cmap="RdBu_r",
                              vmin=-pmax, vmax=pmax, linthresh=0.05)
        ax.set_title("pressure")
        fig.colorbar(ax.collections[0], ax=ax).set_label("$p-\\bar p$")

        ax = axs[2]
        tf = draw_solid(ax, disp, t, dmax, "solid: $|\\mathbf{u}_s|$ + vectors")
        fig.colorbar(tf, ax=ax).set_label("$|\\mathbf{u}_s|$")

        out = os.path.join(figs, f"336_t{t:04.1f}s.png")
        fig.savefig(out, dpi=150)
        plt.close(fig)
        print("wrote", out)


def plot_history(outdir, figs):
    """Disc trajectory + force history from the CSV logs."""
    tr = os.path.join(outdir, "disk_trace.csv")
    fo = os.path.join(outdir, "forces.csv")
    if not (os.path.exists(tr) and os.path.exists(fo)):
        return
    tra = np.genfromtxt(tr, delimiter=",", names=True)
    frc = np.genfromtxt(fo, delimiter=",", names=True)

    fig, axs = plt.subplots(1, 3, figsize=(15, 4.2), constrained_layout=True)

    ax = axs[0]
    ax.plot(tra["cx"], tra["cy"], "-", color="0.6", lw=1.0)
    sc = ax.scatter(tra["cx"], tra["cy"], c=tra["t"], cmap="viridis", s=3)
    for t in TIMES:
        k = int(np.argmin(np.abs(tra["t"] - t)))
        ax.plot(tra["cx"][k], tra["cy"][k], "o", ms=7, mfc="none", mec="crimson", mew=1.6)
        ax.annotate(f"{t:g}s", (tra["cx"][k], tra["cy"][k]), textcoords="offset points",
                    xytext=(6, 5), fontsize=9, color="crimson")
    ax.add_patch(plt.Circle(C_DISC, R_DISC, fill=False, ls=":", ec="k"))
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.set_aspect("equal")
    ax.set_xlabel("$x$"); ax.set_ylabel("$y$")
    ax.set_title("disc-centre trajectory")
    fig.colorbar(sc, ax=ax).set_label("$t$ [s]")

    ax = axs[1]
    ax.plot(frc["t"], frc["Cx"], label="$C_x$")
    ax.plot(frc["t"], frc["Cy"], label="$C_y$")
    ax.plot(frc["t"], frc["Cm"], label="$C_m$", alpha=0.7)
    for t in TIMES[1:]:
        ax.axvline(t, color="0.85", lw=0.8, zorder=0)
    ax.axhline(0, color="0.7", lw=0.8)
    ax.set_xlabel("$t$ [s]"); ax.set_title("direct-forcing force coefficients")
    ax.legend(fontsize=9)

    ax = axs[2]
    ax.plot(tra["t"], np.hypot(tra["Vc_x"], tra["Vc_y"]), label="$|\\mathbf{V}_c|$")
    ax.plot(tra["t"], -tra["omega"], label="$-\\omega$")
    for t in TIMES[1:]:
        ax.axvline(t, color="0.85", lw=0.8, zorder=0)
    ax.set_xlabel("$t$ [s]"); ax.set_title("disc translational / angular speed")
    ax.legend(fontsize=9)

    out = os.path.join(figs, "336_history.png")
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print("wrote", out)


def elastic_figure(outdir, figs, times=TIMES):
    """Elastic-disc variant: the solid mesh genuinely deforms, so show the material.

    Top row  : |u_s| on the reference mesh.
    Bottom row: the deformed mesh (warped by u_s) shaded by |u_s|, showing the
                large stretch/shear the soft disc undergoes in the cavity vortex.
    """
    disp = Series(os.path.join(outdir, "solid.xdmf"), "f")  # dolfinx names the field "f"
    print(f"elastic solid: {len(disp.times)} steps, cells={disp.n_cells}, nodes={disp.n_points}")
    dmax = max(float(np.linalg.norm(disp.read(t)[1][:, :2], axis=1).max()) for t in times)
    print(f"elastic |u_s|max over plotted times = {dmax:.4f}")

    ref = disp.points
    levels = np.linspace(0.0, max(dmax, 1e-12), 15)
    th = np.linspace(0, 2 * np.pi, 361)
    ring = np.c_[C_DISC[0] + R_DISC * np.cos(th), C_DISC[1] + R_DISC * np.sin(th)]

    fig, axes = plt.subplots(2, len(times), figsize=(2.6 * len(times), 6.2),
                             constrained_layout=True)
    cax = fig.add_axes([0.965, 0.12, 0.007, 0.76])
    for j, t in enumerate(times):
        tt, u = disp.read(t)
        u = u[:, :2]
        mag = np.linalg.norm(u, axis=1)
        warped = ref + u
        cx, cy = warped[:, 0].mean(), warped[:, 1].mean()

        ax = axes[0][j]
        # viewport first: rasterised contours are otherwise clipped to default limits
        ax.set_aspect("equal")
        ax.set_xlim(C_DISC[0] - 0.22, C_DISC[0] + 0.22)
        ax.set_ylim(C_DISC[1] - 0.22, C_DISC[1] + 0.22)
        tf = ax.tricontourf(ref[:, 0], ref[:, 1], disp.cells, mag, levels=levels, cmap="turbo")
        ax.triplot(ref[:, 0], ref[:, 1], disp.cells, color="k", lw=0.15, alpha=0.3)
        ax.plot(ring[:, 0], ring[:, 1], "--", color="0.35", lw=1.0)
        ax.set_title(f"$t = {t:g}$ s", fontsize=12)

        ax = axes[1][j]
        ax.set_aspect("equal")
        ax.set_xlim(cx - 0.22, cx + 0.22)
        ax.set_ylim(cy - 0.22, cy + 0.22)
        ax.tricontourf(warped[:, 0], warped[:, 1], disp.cells, mag, levels=levels, cmap="turbo")
        ax.triplot(warped[:, 0], warped[:, 1], disp.cells, color="k", lw=0.2, alpha=0.45)
        ax.plot(ring[:, 0], ring[:, 1], "--", color="0.5", lw=1.0, zorder=0)

        for r in (0, 1):
            axes[r][j].set_xticks([])
            axes[r][j].set_yticks([])
        axes[1][j].plot([], [], " ", label=f"$|\\mathbf{{u}}_s|_{{max}}={mag.max():.2f}$")
        axes[1][j].legend(fontsize=8, loc="lower left", framealpha=0.85)

    axes[0][0].set_ylabel("reference mesh", fontsize=11)
    axes[1][0].set_ylabel("deformed mesh", fontsize=11)
    cb = fig.colorbar(tf, cax=cax)
    cb.set_label("$|\\mathbf{u}_s|$")
    fig.suptitle("demo_336 — elastic disc ($\\mu_s=0.2$, $\\rho_s=1$, Kelvin–Voigt $\\mu_s^{visc}=0.01$): "
                 "the soft solid stretches and shears inside the vortex", fontsize=12.5)
    out = os.path.join(figs, "336_elastic_solid_0-10s.png")
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print("wrote", out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("rigid", help="output dir of multi-direct-frocing (velocity/pressure/disk xdmf)")
    ap.add_argument("--elastic", default=None, help="output dir of multi-direct-frocing-elastic")
    ap.add_argument("--figs", default="figs")
    ap.add_argument("--snapshot", action="store_true",
                    help="copy the HDF5 inputs to a snapshot dir first (use while a run is live)")
    ap.add_argument("--times", default=None,
                    help="comma-separated times to plot instead of 0,2,4,6,8,10")
    args = ap.parse_args()
    global TIMES
    if args.times:
        TIMES = [float(x) for x in args.times.split(",")]

    src = args.rigid
    if args.snapshot:
        src = os.path.join(args.figs, "_snapshot")
        os.makedirs(src, exist_ok=True)
        for name in ("velocity", "pressure", "disk"):
            for ext in (".xdmf", ".h5"):
                s = os.path.join(args.rigid, name + ext)
                if os.path.exists(s):
                    shutil.copy2(s, src)
    os.makedirs(args.figs, exist_ok=True)

    vel = Series(os.path.join(src, "velocity.xdmf"), "f")
    pre = Series(os.path.join(src, "pressure.xdmf"), "f")
    disp = Series(os.path.join(src, "disk.xdmf"), "u")
    print(f"velocity: {len(vel.times)} steps  t=[{vel.times.min():.3f}, {vel.times.max():.3f}]  "
          f"{vel.cell_type} cells={vel.n_cells} nodes={vel.n_points}")
    print(f"pressure: {len(pre.times)} steps")
    print(f"disk:     {len(disp.times)} steps  cells={disp.n_cells} nodes={disp.n_points}")

    vmax, pmax, dmax = panel_mosaic(vel, pre, disp, args.elastic, args.figs)
    solid_figure(disp, args.figs, dmax)
    panel_individual(vel, pre, disp, args.figs, vmax, pmax, dmax)
    plot_history(args.rigid, args.figs)
    if args.elastic:
        elastic_figure(args.elastic, args.figs)


if __name__ == "__main__":
    main()
