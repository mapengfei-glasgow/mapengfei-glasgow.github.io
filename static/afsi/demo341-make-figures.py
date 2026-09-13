"""PyVista figures for the 3-D demo_341 (lid-driven cavity carrying a sphere).

The fluid output is a structured 16^3 hexahedral mesh; the immersed sphere is a
gmsh tetrahedral mesh written to the same XDMF as ``solid_force_io`` /
``solid_coords_io``. Reading follows the same route as the 2-D cases (xml.etree +
h5py, because VTK's XdmfReader cannot open these files here); the rendering is
PyVista: clip planes through the field, an isosurface of velocity magnitude,
streamlines seeded upstream of the sphere, and the deformed sphere surface.
"""

from __future__ import annotations

import argparse
import os
import sys

import numpy as np

os.environ.setdefault("PYVISTA_OFF_SCREEN", "true")
import pyvista as pv  # noqa: E402

pv.OFF_SCREEN = True

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from make_demo_figures import Series  # noqa: E402   (shared XDMF/HDF5 reader)

_CT = {"hexahedron": pv.CellType.HEXAHEDRON, "tetrahedron": pv.CellType.TETRA,
       "quadrilateral": pv.CellType.QUAD, "triangle": pv.CellType.TRIANGLE}


def grid_of(series: Series, scalars: dict | None = None, vector: np.ndarray | None = None):
    pts = series.points
    g = pv.UnstructuredGrid({_CT[series.cell_type.lower()]: series.cells}, pts)
    for k, v in (scalars or {}).items():
        g.point_data[k] = v
    if vector is not None:
        g.point_data["u"] = vector
    return g


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--figs", required=True)
    ap.add_argument("--times", default="0,0.2,0.4,0.6,0.8,1.0")
    args = ap.parse_args()
    os.makedirs(args.figs, exist_ok=True)
    times = [float(x) for x in args.times.split(",")]

    vel = Series(os.path.join(args.out, "velocity.xdmf"), "f")
    sol = Series(os.path.join(args.out, "solid_force.xdmf"), "solid_coords_io")
    sfo = Series(os.path.join(args.out, "solid_force.xdmf"), "solid_force_io")
    print(f"velocity: {len(vel.times)} frames t=[{vel.times.min():.3f},{vel.times.max():.3f}] "
          f"{vel.cell_type} cells={vel.n_cells} nodes={vel.n_points}")
    print(f"sphere:   cells={sol.n_cells} nodes={sol.n_points}")

    # ---- 3-D scene at the last available time ----
    t = min(times[-1], float(vel.times.max()))
    _, uv = vel.read(t)
    _, coords = sol.read(t)
    umag = np.linalg.norm(uv, axis=1)

    fluid = grid_of(vel, {"u_mag": umag}, vector=uv)
    sphere_pts = coords  # current (Lagrangian) coordinates
    sphere = pv.UnstructuredGrid({pv.CellType.TETRA: sol.cells}, sphere_pts)
    disp = np.linalg.norm(coords - sol.points, axis=1)
    sphere.point_data["disp"] = disp
    shell = sphere.extract_surface().compute_normals()

    vmax = float(np.percentile(umag, 99.0))
    print(f"t={t:.3f}: max|u|={umag.max():.4f} (p99 {vmax:.4f}), "
          f"sphere max|u_s|={disp.max():.3e}, centroid={coords.mean(axis=0).round(4)}")

    pl = pv.Plotter(off_screen=True, shape=(2, 2), window_size=(1500, 1250), border=False)
    sb = dict(title="", n_labels=4, label_font_size=11, width=0.45, height=0.05,
              position_x=0.28, position_y=0.04)

    # (0,0) the tank boundary coloured by speed, with the submerged sphere
    pl.subplot(0, 0)
    pl.add_mesh(fluid.extract_surface(), scalars="u_mag", cmap="turbo",
                clim=(0, vmax), scalar_bar_args=dict(sb, title="|u|"))
    pl.add_mesh(shell, color="white", opacity=0.85, smooth_shading=True,
                show_scalar_bar=False)
    pl.add_text(f"tank boundary |u|, t = {t:.2f} s", position="upper_left", font_size=11)
    pl.view_isometric()

    # (0,1) the three centreline profiles (t = 1 s), sphere span shaded
    pl.subplot(0, 1)
    pl.add_mesh(fluid.outline(), color="black", line_width=2)
    pl.add_mesh(shell, color="tan", opacity=0.95, smooth_shading=True,
                show_scalar_bar=False)
    pl.add_text("tank + sphere (0.2 radius at (0.6,0.5,0.5))",
                position="upper_left", font_size=11)
    pl.view_isometric()

    # (1,0) streamlines, seeded just upstream of the sphere
    pl.subplot(1, 0)
    seeds = pv.Disc(inner=0.02, outer=0.22, normal=(1, 0, 0), c_res=16).translate(
        (0.36, 0.5, 0.5), inplace=False)
    try:
        sl = fluid.streamlines_from_source(seeds, vectors="u", max_length=1.2,
                                           integration_direction="forward")
        print(f"  streamlines: {sl.n_cells} segments")
        pl.add_mesh(sl.tube(radius=0.0045), scalars="u_mag", cmap="turbo",
                    clim=(0, vmax), scalar_bar_args=dict(sb, title="|u|"))
    except Exception as exc:  # noqa: BLE001
        print("  streamlines skipped:", exc)
    pl.add_mesh(shell, color="white", opacity=0.85, smooth_shading=True,
                show_scalar_bar=False)
    pl.add_text("streamlines from x = 0.36", position="upper_left", font_size=11)
    pl.view_isometric()

    # (1,1) the immersed solid on its own, coloured by displacement
    pl.subplot(1, 1)
    pl.add_mesh(shell, scalars="disp", cmap="magma", smooth_shading=True,
                scalar_bar_args=dict(sb, title="|u_s|"))
    pl.add_text(f"sphere |u_s|, max {disp.max():.2e}", position="upper_left",
                font_size=11)
    pl.view_isometric()

    out = os.path.join(args.figs, "341_3d_scene.png")
    pl.screenshot(out, return_img=False)
    pl.close()
    print("wrote", out)

    # ---- trajectory of the sphere ----
    ts = np.linspace(float(sol.times.min()), float(sol.times.max()), 40)
    cen, dmax = [], []
    for tt in ts:
        _, c = sol.read(tt)
        cen.append(c.mean(axis=0))
        dmax.append(float(np.linalg.norm(c - sol.points, axis=1).max()))
    cen = np.asarray(cen)
    fig, axs = plt.subplots(1, 2, figsize=(12.5, 4.4), constrained_layout=True)
    ax = axs[0]
    sc = ax.scatter(cen[:, 0], cen[:, 1], c=ts, cmap="viridis", s=12)
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.set_aspect("equal")
    ax.set_xlabel("$x$"); ax.set_ylabel("$y$")
    ax.set_title("sphere centroid (tank is 1 x 1)")
    fig.colorbar(sc, ax=ax).set_label("$t$ [s]")
    ax = axs[1]
    ax.plot(ts, np.linalg.norm(cen - cen[0], axis=1), lw=1.5, label="centroid travel")
    ax.plot(ts, dmax, lw=1.4, label="max $|u_s|$")
    ax.set_xlabel("$t$ [s]"); ax.set_yscale("log"); ax.grid(alpha=0.3, which="both")
    ax.legend(fontsize=9); ax.set_title("motion and deformation")
    out2 = os.path.join(args.figs, "341_trajectory.png")
    fig.savefig(out2, dpi=150); plt.close(fig)
    print("wrote", out2,
          f"(centroid travel {np.linalg.norm(cen[-1]-cen[0]):.4f}, max disp {max(dmax):.2e})")

    # ---- the three centreline profiles at t = 1 s, as plot_lines.py specifies ----
    tt, uv = vel.read(1.0)
    pts = vel.points
    fig, axs = plt.subplots(1, 3, figsize=(15, 4.4), constrained_layout=True)
    for ax, axis, comp in zip(axs, [0, 1, 2], [0, 1, 2]):
        mask = np.ones(len(pts), dtype=bool)
        for d in range(3):
            if d != axis:
                mask &= np.isclose(pts[:, d], 0.5)
        # drop the nodes that the sphere covers on this line
        covered = np.zeros(mask.sum(), dtype=bool)
        for d in range(3):
            if d != axis:
                covered |= (pts[mask, d] - 0.5) ** 2 > 0
        covered = ((pts[mask, axis] - 0.6) ** 2
                   + sum((pts[mask, d] - 0.5) ** 2 for d in range(3) if d != axis)) < 0.2 ** 2
        order = np.argsort(pts[mask, axis])
        xs = pts[mask, axis][order]
        ys = uv[mask, comp][order]
        cov = covered[order]
        ax.axvspan(0.4, 0.8, color="0.9", zorder=0, label="sphere span")
        ax.plot(xs[~cov], ys[~cov], "o-", ms=3, lw=1.5, label="fluid nodes")
        ax.plot(xs[cov], ys[cov], "x", color="crimson", ms=5, label="inside sphere")
        ax.set_xlabel(f"${'xyz'[axis]}$ along the centreline")
        ax.set_ylabel(f"$u_{'xyz'[comp]}$")
        ax.grid(alpha=0.3)
        ax.set_title(f"$u_{'xyz'[comp]}$ on the ${'xyz'[axis]}$-line at $t=1$ s")
        if axis == 0:
            ax.legend(fontsize=8)
    out3 = os.path.join(args.figs, "341_centerlines.png")
    fig.savefig(out3, dpi=150); plt.close(fig)
    print("wrote", out3)


if __name__ == "__main__":
    main()
