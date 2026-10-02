#!/usr/bin/env python3
"""PyVista field figures for demo_424 — tethered aorta in a box (2-D planar).

Reads the final-state ``velocity.xdmf`` / ``pressure.xdmf`` that demo_424's
``main.py`` writes for the four canonical runs (open / closed x NY = 45 / 90)
and renders three figures, off-screen, in the style of this directory's
``demo-fields-pyvista.py``:

    demo424-open-fields-pv.png     open case:   2 x 2 — rows NY = 45 / 90,
                                   columns pressure / velocity magnitude
    demo424-closed-fields-pv.png   closed case: same montage
    demo424-closed-zoom-pv.png     closed case, membrane region (x +-10 mm):
                                   pressure and speed + streamlines for both
                                   resolutions — the wall leakage and the
                                   membrane jump seen up close

The 2-D dolfinx XDMF is parsed with ``xml.etree`` and the HDF5 datasets read
with ``h5py`` (VTK's ``XdmfReader`` crashes on these files in this
environment); everything else is PyVista, off-screen, assembled with Pillow.

Usage:
    python demo424-fields-pyvista.py [--repo /path/to/afsi] [--out DIR]
"""

from __future__ import annotations

import argparse
import os
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

import h5py
import numpy as np
from PIL import Image

os.environ.setdefault("PYVISTA_OFF_SCREEN", "true")
import pyvista as pv  # noqa: E402

pv.OFF_SCREEN = True
pv.global_theme.font.size = 16
pv.global_theme.font.title_size = 18
pv.global_theme.font.label_size = 14

DEFAULT_REPO = Path("/Users/pengfei/GitHub/afsi")
RUN_DIRS = {
    ("open", "45"): "open_NY45",
    ("open", "90"): "open_NY90",
    ("closed", "45"): "closed_NY45",
    ("closed", "90"): "closed_NY90",
}

# Geometry from demo_424/configuration.py
X_OFF = {"45": 0.0005, "90": 0.00025}        # aorta start offset (= H/2)
Y_C, A_LUMEN = 0.0225, 0.015                 # lumen centreline, half-height
Y_IN_LO, Y_IN_HI = Y_C - A_LUMEN, Y_C + A_LUMEN
X_DISC = {ny: X_OFF[ny] + 0.05 for ny in X_OFF}

CLIM = {
    ("open", "pressure"): (0.0, 2.67),
    ("open", "speed"): (0.0, 0.87),
    ("closed", "pressure"): (0.0, 26.7),
    ("closed", "speed"): (0.0, 0.45),
}


def read_xdmf(path: Path, names: tuple[str, ...]):
    """Return (points, cells, values) of the last step of a dolfinx XDMF."""
    root = ET.parse(path).getroot()
    mesh_grid = next(g for g in root.iter("Grid")
                     if g.get("GridType") == "Uniform")
    att = None
    for grid in root.iter("Grid"):
        a = grid.find("Attribute")
        if a is not None and a.get("Name") in names:
            att = a
    if att is None:
        raise SystemExit(f"no attribute {names} in {path}")
    h5ref, _, dset = att.find("DataItem").text.strip().partition(":")
    with h5py.File(path.parent / h5ref, "r") as f:
        values = np.asarray(f[dset], dtype=float)
        cells = np.asarray(f["/Mesh/mesh/topology"], dtype=np.int64)
        points = np.asarray(f["/Mesh/mesh/geometry"], dtype=float)[:, :2]
    return points, cells, values


def load_case(repo: Path, case: str, ny: str) -> pv.UnstructuredGrid:
    d = repo / "afsic/demo/demo_424/plot" / RUN_DIRS[(case, ny)]
    points, cells, vel = read_xdmf(d / "velocity.xdmf", ("f", "u_", "u"))
    _, _, pre = read_xdmf(d / "pressure.xdmf", ("p_", "p"))
    vel = np.asarray(vel)[:, :2]         # dolfinx pads the 2-D vector to 3 comps
    g = pv.UnstructuredGrid({pv.CellType.QUAD: cells},
                            np.c_[points, np.zeros(len(points))])
    g.point_data["velocity"] = np.c_[vel, np.zeros(len(vel))]
    g.point_data["speed"] = np.linalg.norm(vel, axis=1)
    g.point_data["pressure"] = np.asarray(pre).ravel()
    g.set_active_vectors("velocity")
    return g


def view_2d(pl: pv.Plotter):
    pl.view_xy()
    pl.enable_parallel_projection()


def render(mesh, field, cmap, label, title, out: Path, size, clim=None,
           streamlines=None, lines=()):
    pl = pv.Plotter(off_screen=True, window_size=size)
    pl.set_background("white")
    kw = {} if clim is None else {"clim": clim}
    pl.add_mesh(mesh, scalars=field, cmap=cmap, show_edges=False,
                scalar_bar_args={"title": label, "n_labels": 5}, **kw)
    if streamlines is not None:
        pl.add_mesh(streamlines, color="black", line_width=1.5)
    for p1, p2, color, width in lines:
        pl.add_mesh(pv.Line(p1, p2), color=color, line_width=width)
    pl.add_text(title, position="upper_left")
    view_2d(pl)
    pl.screenshot(str(out))
    pl.close()
    print("panel", out.name)


def compose(images, cols, rows, out: Path, gap=10):
    ims = [Image.open(p) for p in images]
    w = max(i.width for i in ims)
    h = max(i.height for i in ims)
    canvas = Image.new("RGB", (cols * w + (cols - 1) * gap,
                               rows * h + (rows - 1) * gap), "white")
    for k, im in enumerate(ims):
        r, c = divmod(k, cols)
        canvas.paste(im, (c * (w + gap), r * (h + gap)))
    canvas.save(out)
    print("wrote", out)


def field_montage(repo: Path, case: str, out: Path, tmp: Path):
    panels = []
    for ny in ("45", "90"):
        mesh = load_case(repo, case, ny)
        for field, cmap, label, what in (
            ("pressure", "coolwarm", "p (Pa)", "pressure"),
            ("speed", "turbo", "|u| (m/s)", "velocity magnitude"),
        ):
            p = tmp / f"{case}-{ny}-{field}.png"
            render(mesh, field, cmap, label,
                   f"{case}  ·  NY = {ny}  ·  {what}",
                   p, (1150, 540), clim=CLIM[(case, field)])
            panels.append(p)
    compose(panels, 2, 2, out)


def zoom_figure(repo: Path, out: Path, tmp: Path):
    panels = []
    for ny in ("45", "90"):
        mesh = load_case(repo, "closed", ny)
        x_d = X_DISC[ny]
        x0, x1 = x_d - 0.010, x_d + 0.010
        clip = mesh.clip_box((x0, x1, 0.0, 0.045, -1.0, 1.0), invert=False)
        seeds_y = np.linspace(0.0004, 0.0446, 61)
        seeds = pv.PolyData(np.c_[np.full_like(seeds_y, x0 + 0.0002),
                                  seeds_y, np.zeros_like(seeds_y)])
        sl = clip.streamlines_from_source(
            seeds, vectors="velocity", integration_direction="forward",
            surface_streamlines=True, max_length=0.03)
        lines = (
            ((x_d, Y_IN_LO, 0.0), (x_d, Y_IN_HI, 0.0), "black", 4),   # membrane
            ((x0, Y_IN_LO, 0.0), (x1, Y_IN_LO, 0.0), "#333333", 2),   # wall
            ((x0, Y_IN_HI, 0.0), (x1, Y_IN_HI, 0.0), "#333333", 2),
        )
        for field, cmap, label, what in (
            ("pressure", "coolwarm", "p (Pa)", "pressure"),
            ("speed", "turbo", "|u| (m/s)", "speed + streamlines"),
        ):
            p = tmp / f"zoom-{ny}-{field}.png"
            render(clip, field, cmap, label, f"NY = {ny}  ·  {what}",
                   p, (560, 920), clim=CLIM[("closed", field)], lines=lines,
                   streamlines=(sl if field == "speed" else None))
            panels.append(p)
    compose(panels, 2, 2, out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", type=Path, default=DEFAULT_REPO)
    ap.add_argument("--out", type=Path,
                    default=Path(__file__).resolve().parent)
    args = ap.parse_args()
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        field_montage(args.repo, "open",
                      args.out / "demo424-open-fields-pv.png", tmp)
        field_montage(args.repo, "closed",
                      args.out / "demo424-closed-fields-pv.png", tmp)
        zoom_figure(args.repo, args.out / "demo424-closed-zoom-pv.png", tmp)


if __name__ == "__main__":
    main()
