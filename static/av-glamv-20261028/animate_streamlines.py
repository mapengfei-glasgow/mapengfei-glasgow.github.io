#!/usr/bin/env python3
"""av_glamv 3D streamline animation from Xc_*.bin + fluid_*.vti + flow.csv: transparent root/tube, opaque leaflets,
speed-coloured stream tubes seeded where speed >= max(smin, sfrac * p99.9) in the valve region, oblique side view.
usage: animate_streamlines.py <run_dir> <out_stem> [--every 1] [--fps 10] [--vmax 150] [--dt 1e-4] [--zpad 3.0]
writes <out_stem>.mp4, <out_stem>.gif and frames in <out_stem>_frames/"""
import os, glob, re, argparse, subprocess, sys
import numpy as np
import pyvista as pv

pv.OFF_SCREEN = True
ap = argparse.ArgumentParser()
ap.add_argument('run'); ap.add_argument('out')
ap.add_argument('--every', type=int, default=1); ap.add_argument('--fps', type=int, default=10)
ap.add_argument('--vmax', type=float, default=100.0); ap.add_argument('--dt', type=float, default=1e-4)
ap.add_argument('--zpad', type=float, default=3.0, help='valve region: leaflet z range +- zpad (cm)')
ap.add_argument('--smin', type=float, default=10.0); ap.add_argument('--sfrac', type=float, default=0.15)
ap.add_argument('--nseeds', type=int, default=350)
ap.add_argument('--elev', type=float, default=25.0, help='camera elevation above the valve plane (deg)')
ap.add_argument('--azim', type=float, default=35.0)
ap.add_argument('--data', default='/home/Pengfei.Ma@glasgow.ac.uk/fdm-3d-v1-workspace-cpu/fdm-3d-v1-workspace/fdm-3d-v1-geometry/src/ibm/data/av_p1/')
a = ap.parse_args()
FFMPEG = os.path.join(os.path.dirname(sys.executable), 'ffmpeg')
GOLD, TUBE, INK, BG = '#c9a227', '#8fb3d1', '#0b0b0b', '#fcfcfb'
MMHG = 1333.2239

cm = np.fromfile(a.data + 'cell_marker.bin', dtype='<i8'); nc = len(cm)
dm = np.fromfile(a.data + 'dofmaps.bin', dtype='<i8').reshape(nc, -1)[:, :4]
TL = dm[np.isin(cm, [15, 16, 18])]; TR = dm[np.isin(cm, [5, 17])]
X0 = np.fromfile(f'{a.run}/Xc_000000.bin').reshape(-1, 3)
cx, cy = 2.4, 2.4
zl = X0[np.unique(TL), 2]; z0, z1 = zl.min() - a.zpad, zl.max() + a.zpad
centre = np.array([cx, cy, 0.5 * (z0 + z1)])


def surf(T, X):
    g = pv.UnstructuredGrid(np.hstack([np.full((len(T), 1), 4), T]).ravel(), np.full(len(T), pv.CellType.TETRA, np.uint8), X)
    return g.extract_surface(algorithm='dataset_surface')


box = (cx - 2.4, cx + 2.4, cy - 2.4, cy + 2.4, z0, z1)
root = surf(TR, X0).clip_box(box, invert=False).extract_surface(algorithm='dataset_surface')   # root/tube fixed in tp_fixed
fl = np.genfromtxt(f'{a.run}/flow.csv', delimiter=',', names=True)
steps = sorted(int(re.search(r'Xc_(\d+)', f).group(1)) for f in glob.glob(f'{a.run}/Xc_*.bin'))
steps = [s for s in steps if os.path.exists(f'{a.run}/fluid_{s:06d}.vti')][::a.every]
fdir = a.out + '_frames'; os.makedirs(fdir, exist_ok=True)


def streamtubes(flow, seed):
    spd = flow.point_data['speed']; thr = max(a.smin, a.sfrac * np.percentile(spd, 99.9))
    cand = np.flatnonzero(spd >= thr)
    if not cand.size: return None, thr
    rng = np.random.default_rng(seed)
    pick = rng.choice(cand, size=min(a.nseeds, cand.size), replace=False, p=spd[cand] / spd[cand].sum())
    st = flow.streamlines_from_source(pv.PolyData(flow.points[pick]), vectors='velocity', integration_direction='both',
                                      max_steps=1500, initial_step_length=0.2, max_length=10.0)
    if not (st.n_points and st.n_cells and 'velocity' in st.point_data): return None, thr
    st.point_data['speed'] = np.linalg.norm(st.point_data['velocity'], axis=1)
    st = st.clip_scalar(scalars='speed', value=thr, invert=False)
    if not st.n_points: return None, thr
    tb = st.extract_surface(algorithm=None).tube(radius=0.025)
    tb.point_data['speed'] = np.linalg.norm(tb.point_data['velocity'], axis=1)
    return tb, thr


el, az = np.radians(a.elev), np.radians(a.azim)
view = np.array([np.cos(el) * np.cos(az), np.cos(el) * np.sin(az), np.sin(el)])
sargs = dict(title='speed (cm/s)', color=INK, vertical=True, position_x=0.88, position_y=0.25, height=0.5, width=0.04,
             title_font_size=14, label_font_size=12, fmt='%.0f')
for i, s in enumerate(steps):
    t = s * a.dt
    X = np.fromfile(f'{a.run}/Xc_{s:06d}.bin').reshape(-1, 3)
    flow = pv.read(f'{a.run}/fluid_{s:06d}.vti').clip_box(box, invert=False)
    flow.point_data['speed'] = np.linalg.norm(flow.point_data['velocity'], axis=1)
    tb, thr = streamtubes(flow, i)
    p = pv.Plotter(off_screen=True, window_size=(1100, 1300)); p.set_background(BG)
    p.add_mesh(root, color=TUBE, opacity=0.15, smooth_shading=True)
    p.add_mesh(surf(TL, X), color=GOLD, smooth_shading=True, specular=0.3)
    if tb is not None:
        p.add_mesh(tb, scalars='speed', cmap='viridis', clim=(0, a.vmax), scalar_bar_args=sargs)
    j = int(np.argmin(np.abs(fl['step'] - s)))
    p.add_text(f't = {t:.3f} s    inlet {fl["p_in_mmHg"][j]:+.1f} mmHg    flow through the valve {-fl["Q_in"][j]:+.0f} ml/s\n'
               f'streamlines where speed > {thr:.0f} cm/s', font_size=11, color=INK, position='upper_left')
    p.camera.focal_point = centre; p.camera.position = centre + 25.0 * view; p.camera.up = (0, 0, 1)
    p.reset_camera(bounds=box); p.camera.zoom(1.25)
    png = f'{fdir}/frame_{i:04d}.png'; p.screenshot(png); p.close()
    print(f'[{i+1}/{len(steps)}] t={t:.3f}', flush=True)

pat = f'{fdir}/frame_%04d.png'
subprocess.run([FFMPEG, '-y', '-loglevel', 'error', '-framerate', str(a.fps), '-i', pat, '-c:v', 'libx264', '-pix_fmt', 'yuv420p',
                '-vf', 'scale=trunc(iw/2)*2:trunc(ih/2)*2', a.out + '.mp4'], check=True)
subprocess.run([FFMPEG, '-y', '-loglevel', 'error', '-framerate', str(a.fps), '-i', pat, '-vf',
                'scale=700:-1:flags=lanczos,split[s0][s1];[s0]palettegen=max_colors=192[p];[s1][p]paletteuse=dither=bayer',
                a.out + '.gif'], check=True)
print('wrote', a.out + '.mp4', a.out + '.gif')
