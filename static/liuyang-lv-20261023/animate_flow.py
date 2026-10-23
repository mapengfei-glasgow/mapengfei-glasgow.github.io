#!/usr/bin/env python3
"""Liuyang heart (liuyang_lv) flow animation from Xc_*.bin + fluid_*.vti.
Left: 3D view, heart surfaces by region + streamlines seeded at the openings.
Right: long-axis cut through the LV apex, mitral valve and aorta: |u| on the plane, the tissue cut in grey,
in-plane velocity arrows.
usage: animate_flow.py <run_dir> <out_stem> [--vmax 80] [--every 1] [--fps 8]
writes <out_stem>.mp4, <out_stem>.gif and frames in <out_stem>_frames/"""
import sys, os, glob, re, argparse, subprocess
import numpy as np
import pyvista as pv

pv.OFF_SCREEN = True
ap = argparse.ArgumentParser()
ap.add_argument('run'); ap.add_argument('out')
ap.add_argument('--vmax', type=float, default=80.0)
ap.add_argument('--every', type=int, default=1)
ap.add_argument('--fps', type=int, default=8)
ap.add_argument('--dt', type=float, default=5e-6)
ap.add_argument('--smin', type=float, default=10.0, help='streamlines only where |u| >= max(smin, sfrac * p99.9)')
ap.add_argument('--sfrac', type=float, default=0.2)
ap.add_argument('--nseeds', type=int, default=250)
a = ap.parse_args()

D = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
L = np.array([17.0, 16.12, 16.13]); XLO = np.array([-5.0, -26.5, 133.35])
OPEN = [(0, -12.896 - XLO[1], 144.008 - XLO[2], 1.58), (0, -17.159 - XLO[1], 145.39 - XLO[2], 1.58),
        (3, 5.782 - XLO[0], 144.527 - XLO[2], 1.6), (5, 6.6 - XLO[0], -14.662 - XLO[1], 1.6),
        (5, -0.81 - XLO[0], -21.32 - XLO[1], 2.58)]
FFMPEG = os.path.join(os.path.dirname(sys.executable), 'ffmpeg')

cm = np.fromfile(D + '/cell_marker.bin', dtype=np.int64); nc = cm.size
dm = np.fromfile(D + '/dofmaps.bin', dtype=np.int64).reshape(nc, -1)[:, :4]
X0 = np.fromfile(D + '/ref_nodes.bin').reshape(-1, 3) - XLO
groups = {'LV': [21, 22, 211], 'LA': [23, 24], 'MV': [30, 40, 5], 'vessels': [100, 200, 1000, 4099]}
colors = {'LV': '#e34948', 'LA': '#2a78d6', 'MV': '#eda100', 'vessels': '#9a9890'}
opac = {'LV': 0.18, 'LA': 0.18, 'MV': 0.7, 'vessels': 0.18}
cells = {k: dm[np.isin(cm, v)] for k, v in groups.items()}

# long-axis plane through the apex (211), the MV centroid (30/40/5) and the aortic opening
apex = X0[np.unique(dm[cm == 211])].mean(0)
mv = X0[np.unique(dm[np.isin(cm, [30, 40, 5])])].mean(0)
ao = np.array([OPEN[4][1], OPEN[4][2], L[2] - 1.0])
nrm = np.cross(mv - apex, ao - apex); nrm /= np.linalg.norm(nrm)
ctr = (apex + mv + ao) / 3

steps = sorted(int(re.findall(r'(\d+)', os.path.basename(f))[0]) for f in glob.glob(f'{a.run}/fluid_*.vti'))
steps = [s for s in steps if os.path.exists(f'{a.run}/Xc_{s:06d}.bin')][::a.every]
fdir = a.out + '_frames'; os.makedirs(fdir, exist_ok=True)

sargs = dict(title='|u| (cm/s)', color='#52514e', title_font_size=14, label_font_size=12, n_labels=5, fmt='%.0f')

cam3d = cam2d = None
for i, s in enumerate(steps):
    png = f'{fdir}/frame_{i:04d}.png'
    t = s * a.dt
    X = np.fromfile(f'{a.run}/Xc_{s:06d}.bin').reshape(-1, 3)
    flow = pv.read(f'{a.run}/fluid_{s:06d}.vti')
    flow.point_data['speed'] = np.linalg.norm(flow.point_data['velocity'], axis=1)

    p = pv.Plotter(off_screen=True, shape=(1, 2), window_size=(1800, 860), border=False)
    p.set_background('#fcfcfb')
    # ---- left: 3D
    p.subplot(0, 0)
    for name, t4 in cells.items():
        g = pv.UnstructuredGrid(np.hstack([np.full((len(t4), 1), 4), t4]).ravel(), np.full(len(t4), pv.CellType.TETRA, np.uint8), X)
        p.add_mesh(g.extract_surface(algorithm='dataset_surface'), color=colors[name], opacity=opac[name], label=name, smooth_shading=True)
    # streamlines only in the fast flow: seeds drawn among grid points above the threshold (weighted by speed),
    # then every streamline segment below the threshold is cut away
    spd = flow.point_data['speed']; thr = max(a.smin, a.sfrac * np.percentile(spd, 99.9))
    cand = np.flatnonzero(spd >= thr)
    if cand.size:
        rng = np.random.default_rng(i)
        pick = rng.choice(cand, size=min(a.nseeds, cand.size), replace=False, p=spd[cand] / spd[cand].sum())
        st = flow.streamlines_from_source(pv.PolyData(flow.points[pick]), vectors='velocity', integration_direction='both',
                                          max_steps=1500, initial_step_length=0.2, max_length=12.0)
        if st.n_points and st.n_cells and 'velocity' in st.point_data:
            st.point_data['speed'] = np.linalg.norm(st.point_data['velocity'], axis=1)
            st = st.clip_scalar(scalars='speed', value=thr, invert=False)
            if st.n_points:
                tb = st.extract_surface(algorithm=None).tube(radius=0.03)
                tb.point_data['speed'] = np.linalg.norm(tb.point_data['velocity'], axis=1)
                p.add_mesh(tb, scalars='speed', cmap='viridis', clim=(0, a.vmax), show_scalar_bar=False)
    p.add_text(f'streamlines where |u| > {thr:.0f} cm/s', font_size=10, color='#52514e', position='lower_left')
    p.add_mesh(pv.Box(bounds=(0, L[0], 0, L[1], 0, L[2])).outline(), color='#a0a09a')
    p.add_legend(bcolor='#fcfcfb', size=(0.34, 0.2), face='r', loc='upper right')
    p.add_text(f't = {t:.3f} s', font_size=14, color='#0b0b0b', position='upper_left')
    if cam3d is None:
        p.camera_position = 'iso'; cam3d = p.camera_position
    p.camera_position = cam3d; p.camera.zoom(1.25)   # camera_position does not hold the zoom
    # ---- right: long-axis cut
    p.subplot(0, 1)
    sl = flow.slice(normal=nrm, origin=ctr)
    p.add_mesh(sl, scalars='speed', cmap='viridis', clim=(0, a.vmax), scalar_bar_args=sargs)
    allc = dm
    solid = pv.UnstructuredGrid(np.hstack([np.full((nc, 1), 4), allc]).ravel(), np.full(nc, pv.CellType.TETRA, np.uint8), X)
    cut = solid.slice(normal=nrm, origin=ctr + 0.02 * nrm)
    if cut.n_points:
        p.add_mesh(cut, color='#f2f1ec', opacity=0.85)
    gl = sl.glyph(orient='velocity', scale=False, factor=0.5, tolerance=0.03)
    if gl.n_points:
        p.add_mesh(gl, color='#ffffff', opacity=0.7)
    p.add_text('long-axis cut: LV apex, mitral valve, aorta', font_size=11, color='#52514e', position='upper_right')
    if cam2d is None:
        up = (ao - apex) - np.dot(ao - apex, nrm) * nrm
        p.view_vector(nrm, viewup=up); cam2d = p.camera_position
    p.camera_position = cam2d; p.camera.zoom(1.35)
    p.screenshot(png); p.close()
    print(f'[{i+1}/{len(steps)}] t={t:.3f} {png}', flush=True)

pat = f'{fdir}/frame_%04d.png'
subprocess.run([FFMPEG, '-y', '-loglevel', 'error', '-framerate', str(a.fps), '-i', pat, '-c:v', 'libx264', '-pix_fmt', 'yuv420p',
                '-vf', 'scale=trunc(iw/2)*2:trunc(ih/2)*2', a.out + '.mp4'], check=True)
subprocess.run([FFMPEG, '-y', '-loglevel', 'error', '-framerate', str(a.fps), '-i', pat, '-vf',
                'scale=1100:-1:flags=lanczos,split[s0][s1];[s0]palettegen=max_colors=192[p];[s1][p]paletteuse=dither=bayer',
                a.out + '.gif'], check=True)
print('wrote', a.out + '.mp4', a.out + '.gif')
