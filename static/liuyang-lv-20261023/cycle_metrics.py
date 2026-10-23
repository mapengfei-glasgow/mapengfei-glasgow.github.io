#!/usr/bin/env python3
"""Cardiac-cycle metrics for a liuyang_lv run: LV / LA cavity volumes (IBAMR LV/LA_POINTS_LIST + Facelets, orifices
closed by the orifice-centre points as BoundaryConditions.C), LV / LA cavity pressure (fluid pressure averaged over
points inside the cavity), aortic pressure / flow from flow.csv.
usage: cycle_metrics.py <run_dir> [out_stem]   → <out_stem>.csv and <out_stem>.png"""
import sys, os, glob, re
import numpy as np
import pyvista as pv

pv.OFF_SCREEN = True
run = sys.argv[1]; stem = sys.argv[2] if len(sys.argv) > 2 else os.path.join(run, 'cycle')
HERE = os.path.dirname(os.path.abspath(__file__)); D = HERE + '/data'
LG = '/home/Pengfei.Ma@glasgow.ac.uk/WholeLVHeartModelling/LiuyangLV/'
XLO = np.array([-5.0, -26.5, 133.35]); MMHG = 1333.2239; DT = 5e-6

def read_list(fn):
    v = np.loadtxt(fn, dtype=np.int64); return v[1:1 + v[0]]
# chamber: (points file, facelets file, orifice-centre pairs, 1-based indices into the points list)
CH = {'LV': ('LV_POINTS_LIST.txt', 'LV_Facelets_LIST.txt', [(7674, 6522), (2534, 2468)]),
      'LA': ('LA_POINTS_LIST.txt', 'LA_Facelets_LIST.txt', [(730, 656), (1845, 1825), (2021, 1996), (1278, 1687), (153, 560)])}
chambers = {}
for k, (pf, ff, pairs) in CH.items():
    pts = read_list(LG + pf); tri = read_list(LG + ff).reshape(-1, 3) - 1
    nreal = len(pts) - len(pairs)
    chambers[k] = (pts[:nreal] - 1, tri, pairs)   # libMesh node ids (0-based) of the real points

def surface(X, k):
    ids, tri, pairs = chambers[k]
    P = np.zeros((len(ids) + len(pairs), 3)); P[:len(ids)] = X[ids]
    for m, (a, b) in enumerate(pairs): P[len(ids) + m] = 0.5 * (P[a - 1] + P[b - 1])
    return P, tri

def volume(P, tri):
    a, b, c = P[tri[:, 0]], P[tri[:, 1]], P[tri[:, 2]]
    return abs(np.einsum('ij,ij->i', a, np.cross(b, c)).sum() / 6.0)

X0 = np.fromfile(D + '/ref_nodes.bin').reshape(-1, 3) - XLO
steps = sorted(int(re.findall(r'(\d+)', os.path.basename(f))[0]) for f in glob.glob(f'{run}/Xc_*.bin'))
flow = np.genfromtxt(f'{run}/flow.csv', delimiter=',', names=True)
rows = []
for s in steps:
    X = np.fromfile(f'{run}/Xc_{s:06d}.bin').reshape(-1, 3)
    r = {'step': s, 't': s * DT}
    vti = f'{run}/fluid_{s:06d}.vti'
    grid = pv.read(vti) if os.path.exists(vti) else None
    for k in ('LV', 'LA'):
        P, tri = surface(X, k); r[f'V_{k}'] = volume(P, tri)
        if grid is not None:   # cavity pressure: mean over grid points enclosed by the closed endocardial surface
            surf = pv.PolyData(P, np.hstack([np.full((len(tri), 1), 3), tri]).ravel())
            lo, hi = P.min(0), P.max(0)
            sel = grid.clip_box(bounds=(lo[0], hi[0], lo[1], hi[1], lo[2], hi[2]), invert=False)
            inside = sel.select_enclosed_points(surf, tolerance=1e-6, check_surface=False)
            m = inside.point_data['SelectedPoints'].view(bool)
            r[f'p_{k}'] = float(np.mean(inside.point_data['pressure'][m])) / MMHG if m.any() else np.nan
        else:
            r[f'p_{k}'] = np.nan
    i = np.argmin(np.abs(flow['step'] - s))
    r['p_Ao'] = flow['p_Aorta'][i]; r['Q_Ao'] = flow['Q_Aorta'][i]
    r['Q_veins'] = flow['Q_RIPV'][i] + flow['Q_RSPV'][i] + flow['Q_LIPV'][i] + flow['Q_LSPV'][i]
    rows.append(r)
    print(f"t={r['t']:.3f}  V_LV={r['V_LV']:.1f} ml  V_LA={r['V_LA']:.1f} ml  p_LV={r['p_LV']:.1f}  p_LA={r['p_LA']:.1f}  "
          f"p_Ao={r['p_Ao']:.1f} mmHg  Q_Ao={r['Q_Ao']:.0f}", flush=True)

keys = list(rows[0].keys())
with open(stem + '.csv', 'w') as f:
    f.write(','.join(keys) + '\n')
    for r in rows: f.write(','.join(f'{r[k]:.6g}' for k in keys) + '\n')

import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
t = np.array([r['t'] for r in rows]); g = lambda k: np.array([r[k] for r in rows])
plt.rcParams.update({'font.size': 10, 'axes.spines.top': False, 'axes.spines.right': False})
fig, ax = plt.subplots(2, 2, figsize=(11, 7.5))
a = ax[0, 0]; a.plot(t, g('V_LV'), color='#e34948', label='LV'); a.plot(t, g('V_LA'), color='#2a78d6', label='LA')
a.set_ylabel('cavity volume (ml)'); a.legend(frameon=False)
a = ax[0, 1]; a.plot(t, g('p_LV'), color='#e34948', label='LV'); a.plot(t, g('p_LA'), color='#2a78d6', label='LA')
a.plot(t, g('p_Ao'), color='#52514e', label='aorta'); a.set_ylabel('pressure (mmHg)'); a.legend(frameon=False)
a = ax[1, 0]; a.plot(flow['t'], flow['Q_Aorta'], color='#52514e', label='aorta (+ out)')
a.plot(flow['t'], flow['Q_RIPV'] + flow['Q_RSPV'] + flow['Q_LIPV'] + flow['Q_LSPV'], color='#2a78d6', label='pulmonary veins (− in)')
a.axhline(0, color='#c8c7c1', lw=0.8); a.set_ylabel('flow (ml/s)'); a.set_xlabel('t (s)'); a.legend(frameon=False)
for a in (ax[0, 0], ax[0, 1]): a.axvline(1.0, color='#c8c7c1', lw=0.8, ls='--')
a = ax[1, 1]; k = t >= 1.0 - 1e-9
if k.sum() > 1:
    a.plot(g('V_LV')[k], g('p_LV')[k], color='#e34948', marker='o', ms=3); a.set_title('LV pressure-volume loop (t ≥ 1 s)', fontsize=10)
a.set_xlabel('LV volume (ml)'); a.set_ylabel('LV pressure (mmHg)')
fig.tight_layout(); fig.savefig(stem + '.png', dpi=130); print('wrote', stem + '.csv', stem + '.png')
