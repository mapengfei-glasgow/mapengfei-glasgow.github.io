#!/usr/bin/env python3
"""Liuyang heart (liuyang_lv) flow animations, 2 x 2 panels, from Xc_*.bin + fluid_*.vti.
  --mode 3d      four views around the LV long axis (0/90/180/270 deg): heart surfaces + speed-filtered streamlines
  --mode slices  four cuts: 3-chamber long axis (apex, MV, aorta), orthogonal long axis, LV short axis (mid
                 ventricle), atrial cut through the LA centre; |u|, tissue cut, in-plane arrows
  --mode slices --field pressure: pressure in mmHg on the same four cuts, isobars every --piso mmHg, no arrows
usage: animate_views.py <run_dir> <out_stem> --mode 3d|slices [--field speed|pressure] [--vmax 250] [--every 1] [--fps 8]
writes <out_stem>.mp4, <out_stem>.gif and frames in <out_stem>_frames/"""
import sys, os, glob, re, argparse, subprocess
import numpy as np
import pyvista as pv

pv.OFF_SCREEN = True
ap = argparse.ArgumentParser()
ap.add_argument('run'); ap.add_argument('out')
ap.add_argument('--mode', choices=['3d', 'slices'], required=True)
ap.add_argument('--vmax', type=float, default=250.0)
ap.add_argument('--field', choices=['speed', 'pressure'], default='speed', help='slices: |u| or pressure (mmHg)')
ap.add_argument('--pmin', type=float, default=-10.0); ap.add_argument('--pmax', type=float, default=140.0)
ap.add_argument('--piso', type=float, default=10.0, help='isobar spacing (mmHg), 0 = none')
ap.add_argument('--every', type=int, default=1)
ap.add_argument('--fps', type=int, default=8)
ap.add_argument('--dt', type=float, default=5e-6)
ap.add_argument('--smin', type=float, default=10.0, help='streamlines only where |u| >= max(smin, sfrac * p99.9)')
ap.add_argument('--sfrac', type=float, default=0.2)
ap.add_argument('--nseeds', type=int, default=300)
a = ap.parse_args()

D = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
L = np.array([17.0, 16.12, 16.13]); XLO = np.array([-5.0, -26.5, 133.35])
FFMPEG = os.path.join(os.path.dirname(sys.executable), 'ffmpeg')
BG, INK, MUTED = '#fcfcfb', '#0b0b0b', '#52514e'

cm = np.fromfile(D + '/cell_marker.bin', dtype=np.int64); nc = cm.size
dm = np.fromfile(D + '/dofmaps.bin', dtype=np.int64).reshape(nc, -1)[:, :4]
X0 = np.fromfile(D + '/ref_nodes.bin').reshape(-1, 3) - XLO
groups = {'LV': [21, 22, 211], 'LA': [23, 24], 'MV': [30, 40, 5], 'vessels': [100, 200, 1000, 4099]}
colors = {'LV': '#e34948', 'LA': '#2a78d6', 'MV': '#eda100', 'vessels': '#9a9890'}
opac = {'LV': 0.16, 'LA': 0.16, 'MV': 0.75, 'vessels': 0.14}
cells = {k: dm[np.isin(cm, v)] for k, v in groups.items()}

# anatomical frame from the reference configuration
apex = X0[np.unique(dm[cm == 211])].mean(0)
mv = X0[np.unique(dm[np.isin(cm, [30, 40, 5])])].mean(0)
ao = np.array([-0.81 - XLO[0], -21.32 - XLO[1], L[2] - 1.0])
la = X0[np.unique(dm[np.isin(cm, [23, 24])])].mean(0)
ax_l = (mv - apex) / np.linalg.norm(mv - apex)                       # LV long axis, apex → base
n3 = np.cross(mv - apex, ao - apex); n3 /= np.linalg.norm(n3)        # normal of the 3-chamber plane
e2 = np.cross(ax_l, n3)                                              # in the 3-chamber plane, ⟂ long axis
centre = 0.5 * (apex + la)

steps = sorted(int(re.findall(r'(\d+)', os.path.basename(f))[0]) for f in glob.glob(f'{a.run}/fluid_*.vti'))
steps = [s for s in steps if os.path.exists(f'{a.run}/Xc_{s:06d}.bin')][::a.every]
fdir = a.out + '_frames'; os.makedirs(fdir, exist_ok=True)
sargs = dict(title='|u| (cm/s)', color=MUTED, title_font_size=12, label_font_size=11, n_labels=5, fmt='%.0f',
             position_x=0.25, position_y=0.02, width=0.5, height=0.06)

def label(p, text, pos, size):
    '''dark text on a light box: readable over the dark slice and over the page background'''
    act = p.add_text(text, font_size=size, color=INK, position=pos)
    tp = act.GetTextProperty(); tp.SetBackgroundColor(0.99, 0.99, 0.98); tp.SetBackgroundOpacity(0.85)
    return act

def tet_grid(t4, X):
    return pv.UnstructuredGrid(np.hstack([np.full((len(t4), 1), 4), t4]).ravel(), np.full(len(t4), pv.CellType.TETRA, np.uint8), X)

def streamtubes(flow, seed):
    spd = flow.point_data['speed']; thr = max(a.smin, a.sfrac * np.percentile(spd, 99.9))
    cand = np.flatnonzero(spd >= thr)
    if not cand.size: return None, thr
    rng = np.random.default_rng(seed)
    pick = rng.choice(cand, size=min(a.nseeds, cand.size), replace=False, p=spd[cand] / spd[cand].sum())
    st = flow.streamlines_from_source(pv.PolyData(flow.points[pick]), vectors='velocity', integration_direction='both',
                                      max_steps=1500, initial_step_length=0.2, max_length=12.0)
    if not (st.n_points and st.n_cells and 'velocity' in st.point_data): return None, thr
    st.point_data['speed'] = np.linalg.norm(st.point_data['velocity'], axis=1)
    st = st.clip_scalar(scalars='speed', value=thr, invert=False)
    if not st.n_points: return None, thr
    tb = st.extract_surface(algorithm=None).tube(radius=0.03)
    tb.point_data['speed'] = np.linalg.norm(tb.point_data['velocity'], axis=1)
    return tb, thr

# ---- panel definitions
if a.mode == '3d':
    views = []
    for k, ang in enumerate((0, 90, 180, 270)):
        th = np.radians(ang); d = np.cos(th) * n3 + np.sin(th) * e2      # view direction ⟂ long axis
        views.append((f'{ang}° around the LV long axis', d))
else:
    mid = apex + 0.5 * (mv - apex)
    slices = [('3-chamber long axis (apex, MV, aorta)', n3, centre, ax_l),
              ('orthogonal long axis', e2, centre, ax_l),
              ('LV short axis, mid ventricle', ax_l, mid, n3),
              ('atrial cut through the LA centre', ax_l, la, n3)]

MMHG = 1333.2239
try:
    flow_csv = np.genfromtxt(f'{a.run}/flow.csv', delimiter=',', names=True)
    if 'step' not in flow_csv.dtype.names: flow_csv = None
except Exception:
    flow_csv = None
cams = {}
for i, s in enumerate(steps):
    t = s * a.dt
    X = np.fromfile(f'{a.run}/Xc_{s:06d}.bin').reshape(-1, 3)
    flow = pv.read(f'{a.run}/fluid_{s:06d}.vti')
    flow.point_data['speed'] = np.linalg.norm(flow.point_data['velocity'], axis=1)
    p = pv.Plotter(off_screen=True, shape=(2, 2), window_size=(1700, 1300), border=True, border_color='#e1e0d9')
    p.set_background(BG)
    if a.mode == '3d':
        surfs = {k: tet_grid(t4, X).extract_surface(algorithm='dataset_surface') for k, t4 in cells.items()}
        tb, thr = streamtubes(flow, i)
        for k, (title, d) in enumerate(views):
            p.subplot(k // 2, k % 2)
            for name, sf in surfs.items():
                p.add_mesh(sf, color=colors[name], opacity=opac[name], smooth_shading=True, label=name if k == 0 else None)
            if tb is not None:
                p.add_mesh(tb, scalars='speed', cmap='viridis', clim=(0, a.vmax), show_scalar_bar=(k == 3),
                           scalar_bar_args=sargs if k == 3 else None)
            p.add_text(title, font_size=10, color=MUTED, position='upper_right')
            if k == 0:
                p.add_text(f't = {t:.3f} s    streamlines where |u| > {thr:.0f} cm/s', font_size=11, color=INK, position='upper_left')
                p.add_legend(bcolor=BG, size=(0.2, 0.2), face='r', loc='lower left')
            if k not in cams:
                p.camera.focal_point = centre; p.camera.position = centre + 30.0 * d; p.camera.up = ax_l
                p.reset_camera(bounds=(0, L[0], 0, L[1], 0, L[2])); cams[k] = p.camera_position
            p.camera_position = cams[k]; p.camera.zoom(1.55)
    else:
        solid = tet_grid(dm, X)
        for k, (title, nrm, org, up) in enumerate(slices):
            p.subplot(k // 2, k % 2)
            sl = flow.slice(normal=nrm, origin=org)
            if a.field == 'pressure':
                sl.point_data['p_mmHg'] = sl.point_data['pressure'] / MMHG
                p.add_mesh(sl, scalars='p_mmHg', cmap='magma', clim=(a.pmin, a.pmax), show_scalar_bar=(k == 3),
                           scalar_bar_args=dict(sargs, title='p (mmHg)') if k == 3 else None)
                if a.piso > 0:
                    iso = sl.contour(isosurfaces=list(np.arange(np.ceil(a.pmin / a.piso) * a.piso, a.pmax + 1e-9, a.piso)), scalars='p_mmHg')
                    if iso.n_points: p.add_mesh(iso, color='#ffffff', line_width=1, opacity=0.45)
            else:
                p.add_mesh(sl, scalars='speed', cmap='viridis', clim=(0, a.vmax), show_scalar_bar=(k == 3),
                           scalar_bar_args=sargs if k == 3 else None)
            cut = solid.slice(normal=nrm, origin=org + 0.02 * nrm)
            if cut.n_points: p.add_mesh(cut, color='#9fc3ee' if a.field == 'pressure' else '#f2f1ec', opacity=0.35 if a.field == 'pressure' else 0.9)
            if a.field == 'speed':
                gl = sl.glyph(orient='velocity', scale=False, factor=0.45, tolerance=0.03)
                if gl.n_points: p.add_mesh(gl, color='#ffffff', opacity=0.7)
            label(p, f' {title} ', 'upper_right', 10)
            if k == 0:
                txt = f' t = {t:.3f} s '
                if a.field == 'pressure' and flow_csv is not None:
                    j = int(np.argmin(np.abs(flow_csv['step'] - s)))
                    txt += f'   aorta {flow_csv["p_Aorta"][j]:.0f} mmHg, veins {flow_csv["p_RIPV"][j]:.0f} mmHg '
                label(p, txt, 'upper_left', 12)
            if k not in cams:
                p.camera.focal_point = org; p.camera.position = org + 30.0 * nrm; p.camera.up = up
                p.reset_camera(bounds=sl.bounds); cams[k] = p.camera_position
            p.camera_position = cams[k]; p.camera.zoom(1.6 if k < 2 else 2.2)
    png = f'{fdir}/frame_{i:04d}.png'; p.screenshot(png); p.close()
    print(f'[{i+1}/{len(steps)}] t={t:.3f} {png}', flush=True)

pat = f'{fdir}/frame_%04d.png'
subprocess.run([FFMPEG, '-y', '-loglevel', 'error', '-framerate', str(a.fps), '-i', pat, '-c:v', 'libx264', '-pix_fmt', 'yuv420p',
                '-vf', 'scale=trunc(iw/2)*2:trunc(ih/2)*2', a.out + '.mp4'], check=True)
subprocess.run([FFMPEG, '-y', '-loglevel', 'error', '-framerate', str(a.fps), '-i', pat, '-vf',
                'scale=1000:-1:flags=lanczos,split[s0][s1];[s0]palettegen=max_colors=192[p];[s1][p]paletteuse=dither=bayer',
                a.out + '.gif'], check=True)
print('wrote', a.out + '.mp4', a.out + '.gif')
