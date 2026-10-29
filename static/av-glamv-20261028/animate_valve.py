#!/usr/bin/env python3
"""av_glamv valve animation, 2 x 2 panels per output frame, from Xc_*.bin + fluid_*.vti + flow.csv:
  top-left   leaflets seen along the axis from z = Lz (inlet side), root ring for reference
  top-right  leaflets seen from z = 0 (outlet side)
  bottom-left  longitudinal cut through the axis (x-z plane): axial velocity w, leaflet and root nodes in the slab
  bottom-right inlet pressure and lumen flow rate Q(t), current time marked
usage: animate_valve.py <run_dir> <out_stem> [--every 1] [--fps 10] [--wmax 150] [--dt 1e-4]
writes <out_stem>.mp4, <out_stem>.gif and frames in <out_stem>_frames/"""
import os, glob, re, argparse, subprocess, sys
import numpy as np
import pyvista as pv
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

pv.OFF_SCREEN = True
ap = argparse.ArgumentParser()
ap.add_argument('run'); ap.add_argument('out')
ap.add_argument('--every', type=int, default=1); ap.add_argument('--fps', type=int, default=10)
ap.add_argument('--wmax', type=float, default=150.0); ap.add_argument('--dt', type=float, default=1e-4)
ap.add_argument('--data', default='/home/Pengfei.Ma@glasgow.ac.uk/fdm-3d-v1-workspace-cpu/fdm-3d-v1-workspace/fdm-3d-v1-geometry/src/ibm/data/av_p1/')
a = ap.parse_args()
FFMPEG = os.path.join(os.path.dirname(sys.executable), 'ffmpeg')
GOLD, BLUE, INK, BG = '#c9a227', '#5b8db8', '#0b0b0b', '#fcfcfb'

cm = np.fromfile(a.data + 'cell_marker.bin', dtype='<i8'); nc = len(cm)
dm = np.fromfile(a.data + 'dofmaps.bin', dtype='<i8').reshape(nc, -1)[:, :4]
LEAF = np.isin(cm, [15, 16, 18]); ROOT = np.isin(cm, [5, 17])
TL = dm[LEAF]; TR = dm[cm == 17]
leaf_n = np.unique(TL); root_n = np.unique(dm[ROOT])
X0 = np.fromfile(f'{a.run}/Xc_000000.bin').reshape(-1, 3)
cx, cy = 2.4, 2.4   # domain centre = valve axis (av_glamv centres the tube axis)
zl = X0[leaf_n, 2]; zlo, zhi = zl.min() - 1.5, zl.max() + 1.0
slab_l = leaf_n[np.abs(X0[leaf_n, 1] - cy) < 0.05]; slab_r = root_n[np.abs(X0[root_n, 1] - cy) < 0.05]
slab_r = slab_r[(X0[slab_r, 2] > zlo) & (X0[slab_r, 2] < zhi)]


def ugrid(T, X):
    return pv.UnstructuredGrid(np.hstack([np.full((len(T), 1), 4), T]).ravel(), np.full(len(T), pv.CellType.TETRA, np.uint8), X)


root_surf = ugrid(TR, X0).extract_surface(algorithm='dataset_surface')
fl = np.genfromtxt(f'{a.run}/flow.csv', delimiter=',', names=True)
steps = sorted(int(re.search(r'Xc_(\d+)', f).group(1)) for f in glob.glob(f'{a.run}/Xc_*.bin'))
steps = [s for s in steps if os.path.exists(f'{a.run}/fluid_{s:06d}.vti')][::a.every]
fdir = a.out + '_frames'; os.makedirs(fdir, exist_ok=True)


def view(X, from_top):
    p = pv.Plotter(off_screen=True, window_size=(700, 700)); p.set_background(BG)
    p.add_mesh(root_surf, color=BLUE, opacity=0.12)
    p.add_mesh(ugrid(TL, X).extract_surface(algorithm='dataset_surface'), color=GOLD, smooth_shading=True, specular=0.3)
    fz = 0.5 * (zlo + zhi); d = 9.0 if from_top else -9.0
    p.camera.focal_point = (cx, cy, fz); p.camera.position = (cx, cy, fz + d); p.camera.up = (0, 1, 0)
    p.camera.view_angle = 30
    img = p.screenshot(return_img=True); p.close(); return img


for i, s in enumerate(steps):
    t = s * a.dt
    X = np.fromfile(f'{a.run}/Xc_{s:06d}.bin').reshape(-1, 3)
    m = pv.read(f'{a.run}/fluid_{s:06d}.vti'); nx, ny, nz = m.dimensions; hx = m.spacing[0]
    W = np.asarray(m['w']).reshape(nz, ny, nx)[:, int(round(cy / hx)), :]
    fig = plt.figure(figsize=(13, 11), facecolor=BG)
    gs = fig.add_gridspec(2, 2, height_ratios=[1, 1.05])
    for k, top in enumerate((True, False)):
        ax = fig.add_subplot(gs[0, k]); ax.imshow(view(X, top)); ax.set_axis_off()
        ax.set_title('leaflets from z = Lz (inlet side)' if top else 'leaflets from z = 0 (outlet side)', color=INK)
    ax = fig.add_subplot(gs[1, 0])
    im = ax.imshow(W, origin='lower', extent=[0, (nx - 1) * hx, 0, (nz - 1) * hx], cmap='RdBu_r', vmin=-a.wmax, vmax=a.wmax)
    ax.plot(X[slab_r, 0], X[slab_r, 2], '.', ms=1.2, color='#333333')
    ax.plot(X[slab_l, 0], X[slab_l, 2], '.', ms=2.0, color=GOLD)
    ax.set_xlim(cx - 2.3, cx + 2.3); ax.set_ylim(zlo, zhi); ax.set_aspect('equal')
    ax.set_xlabel('x (cm)'); ax.set_ylabel('z (cm)'); ax.set_title('axial velocity w (cm/s), cut y = axis', color=INK)
    fig.colorbar(im, ax=ax, shrink=0.8)
    ax = fig.add_subplot(gs[1, 1]); ax2 = ax.twinx()
    ax.plot(fl['t'], fl['p_in_mmHg'], color='#52514e', lw=1.4); ax.set_ylabel('inlet pressure (mmHg)')
    ax2.plot(fl['t'], -fl['Q_in'], color='#2a78d6', lw=1.6); ax2.set_ylabel('flow through the valve (ml/s, + = opening direction)', color='#2a78d6')
    ax.axvline(t, color='#e34948', lw=1.2); ax.axhline(0, color='#c8c7c1', lw=0.8)
    ax.set_xlabel('t (s)'); ax.set_xlim(0, fl['t'].max()); ax.set_title(f't = {t:.3f} s', color=INK)
    for sp in ('top',): ax.spines[sp].set_visible(False)
    fig.tight_layout(); png = f'{fdir}/frame_{i:04d}.png'; fig.savefig(png, dpi=80, facecolor=BG); plt.close(fig)
    print(f'[{i+1}/{len(steps)}] t={t:.3f}', flush=True)

pat = f'{fdir}/frame_%04d.png'
subprocess.run([FFMPEG, '-y', '-loglevel', 'error', '-framerate', str(a.fps), '-i', pat, '-c:v', 'libx264', '-pix_fmt', 'yuv420p',
                '-vf', 'scale=trunc(iw/2)*2:trunc(ih/2)*2', a.out + '.mp4'], check=True)
subprocess.run([FFMPEG, '-y', '-loglevel', 'error', '-framerate', str(a.fps), '-i', pat, '-vf',
                'scale=800:-1:flags=lanczos,split[s0][s1];[s0]palettegen=max_colors=192[p];[s1][p]paletteuse=dither=bayer',
                a.out + '.gif'], check=True)
print('wrote', a.out + '.mp4', a.out + '.gif')
