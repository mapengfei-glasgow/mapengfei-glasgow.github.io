#!/usr/bin/env python3
"""av_glamv tp_* runs: inlet pressure, flow through the valve (-Q_in, + = opening direction) and max root/tube
displacement against t, one axis per panel. usage: plot_runs.py <out.png> (run from the runs/av_glamv_20261028 directory)"""
import sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

RUNS = [('tp_fixed', 'root/tube fixed (published)', '#2a78d6'),
        ('tp_tether', 'root/tube tethered', '#eb6834'),
        ('tp_tether_up', 'tethered + upwind convection', '#1baf7a')]
INK, INK2, MUTED, GRID, BASE, BG = '#0b0b0b', '#52514e', '#898781', '#e1e0d9', '#c3c2b7', '#fcfcfb'
plt.rcParams.update({'font.size': 10, 'axes.edgecolor': BASE, 'axes.labelcolor': INK2, 'xtick.color': MUTED,
                     'ytick.color': MUTED, 'axes.spines.top': False, 'axes.spines.right': False})
fig, ax = plt.subplots(3, 1, figsize=(10, 9), sharex=True, gridspec_kw=dict(height_ratios=[1, 2, 1.3]), facecolor=BG)
fl = {d: np.genfromtxt(f'{d}/flow.csv', delimiter=',', names=True) for d, _, _ in RUNS}
ss = {d: np.genfromtxt(f'{d}/solid_stats.csv', delimiter=',', names=True) for d, _, _ in RUNS}
f0 = fl['tp_fixed']
ax[0].plot(f0['t'], f0['p_in_mmHg'], color=INK2, lw=2)
ax[0].set_ylabel('inlet total pressure\n(mmHg)')
for d, lab, c in RUNS:
    ax[1].plot(fl[d]['t'], -fl[d]['Q_in'], color=c, lw=2, label=lab)
    ax[2].plot(ss[d]['t'], ss[d]['max_disp_pin'], color=c, lw=2, label=lab)
ax[1].set_ylabel('flow through the valve (ml/s)\n+ = opening direction (−z)')
ax[2].set_ylabel('max root/tube\ndisplacement (cm)')
ax[2].set_xlabel('t (s)')
for a in ax:
    a.set_facecolor(BG); a.grid(True, color=GRID, lw=0.6); a.axhline(0, color=BASE, lw=0.8); a.set_xlim(0, 1.6)
ax[1].legend(frameon=False, loc='upper left', bbox_to_anchor=(0.36, 1.0), fontsize=9, labelcolor=INK2)
for d, lab, c in RUNS:   # direct labels at the right end of the displacement panel (relief for the low-contrast aqua)
    y = ss[d]['max_disp_pin'][-1]
    ax[2].annotate(d, (1.6, y), xytext=(4, 0), textcoords='offset points', va='center', fontsize=9, color=INK2, annotation_clip=False)
ax[0].set_title('av_glamv: two sine cycles (5 mmHg, 1.25 Hz), 48 × 48 × 144, dt = 1e-4 s', fontsize=11, color=INK, loc='left')
fig.tight_layout(); fig.savefig(sys.argv[1], dpi=130, facecolor=BG); print(sys.argv[1])
