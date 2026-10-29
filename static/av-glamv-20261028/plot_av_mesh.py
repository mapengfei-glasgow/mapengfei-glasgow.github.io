#!/usr/bin/env python3
"""AV mesh overview (fdm-3d-v1-geometry/data/AV/AV_mesh.h5, P1 tets): 3D exterior, two longitudinal cuts through the
valve axis and three cross-sections, root/tube in blue and leaflets in gold.
Coordinates: x, y relative to the leaflet centroid (valve axis), z relative to the top of the leaflets.
usage: plot_av_mesh.py <AV_mesh.h5 | arrays.npz> <out.png>   (needs pyvista, matplotlib; h5py for .h5)"""
import sys
import numpy as np
import pyvista as pv
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection

pv.OFF_SCREEN = True
src, out = sys.argv[1], sys.argv[2]
if src.endswith('.npz'):   # arrays exported from the .h5 (when this Python has no h5py)
    d = np.load(src); X, T, tag = d['X'], d['T'].astype(np.int64), d['tag']
else:
    import h5py
    f = h5py.File(src, 'r')
    X = f['Mesh/mesh/geometry'][:]; T = f['Mesh/mesh/topology'][:].astype(np.int64)
    tag = f['MeshTags/cell_tags/Values'][:].ravel()
LEAF, ROOT = [15, 16, 18], [5, 17]
BLUE, GOLD, INK, MUTED, BG = '#5b8db8', '#c9a227', '#0b0b0b', '#52514e', '#fcfcfb'

leaf_nodes = np.unique(T[np.isin(tag, LEAF)])
c = X[leaf_nodes].mean(0)
x0, y0, z0 = c[0], c[1], X[leaf_nodes, 2].max()           # valve axis; z = 0 at the leaflet top
P = X - np.array([x0, y0, z0])

grid = pv.UnstructuredGrid(np.hstack([np.full((len(T), 1), 4), T]).ravel(), np.full(len(T), pv.CellType.TETRA, np.uint8), P)
grid.cell_data['marker'] = tag


def cut(normal, origin):
    """Exact planar section of the tets: list of (polygon in plane coords, is_leaflet)."""
    s = grid.slice(normal=normal, origin=origin, generate_triangles=True)
    if s.n_cells == 0:
        return []
    ax = np.argmax(np.abs(normal)); keep = [i for i in range(3) if i != ax]
    pts = np.asarray(s.points)[:, keep]
    tri = s.faces.reshape(-1, 4)[:, 1:]
    mk = np.asarray(s.cell_data['marker'])
    return [(pts[t], m in LEAF) for t, m in zip(tri, mk)]


def draw(ax, polys, title, xlabel, ylabel, lim=None):
    for leaf in (False, True):
        pc = [p for p, l in polys if l == leaf]
        if pc:
            ax.add_collection(PolyCollection(pc, facecolors=GOLD if leaf else BLUE, edgecolors='none', antialiased=True))
    ax.set_aspect('equal'); ax.set_title(title, fontsize=11, color=INK)
    ax.set_xlabel(xlabel, color=MUTED); ax.set_ylabel(ylabel, color=MUTED)
    if lim is not None:
        ax.set_xlim(*lim[0]); ax.set_ylim(*lim[1])
    else:
        ax.autoscale_view()
    for s in ('top', 'right'):
        ax.spines[s].set_visible(False)


# 3D exterior
pl = pv.Plotter(off_screen=True, window_size=(900, 1200)); pl.set_background(BG)
pl.add_mesh(grid.extract_surface(algorithm='dataset_surface'), color='#3b4656', smooth_shading=True, specular=0.3)
pl.camera_position = 'xz'; pl.camera.elevation = 15; pl.camera.azimuth = 30; pl.camera.zoom(1.25)
img = pl.screenshot(return_img=True); pl.close()

R = np.hypot(P[:, 0], P[:, 1]).max() * 1.05
zlo, zhi = P[:, 2].min(), P[:, 2].max()
fig = plt.figure(figsize=(14, 9.5), facecolor=BG)
gs = fig.add_gridspec(2, 3, height_ratios=[1.35, 1])
ax = fig.add_subplot(gs[0, 0]); ax.imshow(img); ax.set_axis_off(); ax.set_title('Full mesh exterior', fontsize=11, color=INK)
draw(fig.add_subplot(gs[0, 1]), cut((0, 1, 0), (0, 0, 0)), 'Longitudinal  y = 0 cm', 'x (cm)', 'z (cm)', ((-R, R), (zlo, zhi)))
draw(fig.add_subplot(gs[0, 2]), cut((1, 0, 0), (0, 0, 0)), 'Longitudinal  x = 0 cm', 'y (cm)', 'z (cm)', ((-R, R), (zlo, zhi)))
for j, zc in enumerate((-1.8, -1.0, -0.2)):
    draw(fig.add_subplot(gs[1, j]), cut((0, 0, 1), (0, 0, zc)), f'Cross-section  z = {zc:.1f} cm', 'x (cm)', 'y (cm)', ((-R, R), (-R, R)))
fig.text(0.5, 0.012, 'Blue: root / tube (markers 5, 17)    Gold: leaflets (15, 16, 18)    Original AV P1 tetrahedra '
         f'({len(T):,} cells, {len(X):,} nodes);  x, y about the valve axis, z = 0 at the leaflet top',
         ha='center', fontsize=9, color=MUTED)
fig.tight_layout(rect=(0, 0.03, 1, 1)); fig.savefig(out, dpi=150, facecolor=BG); print(out)
