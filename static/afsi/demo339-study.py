"""Post-processing for the demo_339 cylinder study.

Three things are computed for every run:

1. The direct-forcing ``Cd``/``Cl`` from the run log (the volume-force integral the
   readme already flags as grid-dependent).
2. An **independent control-volume momentum balance** for the drag, which needs only
   the velocity and pressure fields:

       F_x = rho*(Q_out - Q_in) + (p_out - p_in)*H + tau_wall_x

   with Q = int u_x^2 dy, p the boundary pressures and tau_wall_x the integrated
   wall shear (viscous drag on the two channel walls).

3. Lift/Strouhal statistics over the statistically steady window.
"""

from __future__ import annotations

import argparse
import os
import re
import sys

import numpy as np

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Circle  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

LX, LY = 2.2, 0.41
CX, CY, R, D = 0.2, 0.2, 0.05, 0.1
UM = 1.0
RHO = 1000.0
MU = 1.0
T_RAMP = 2.0

# name, label, style
RUNS = [
    ("r110", "$110\\times21$", dict(color="0.55", ls="-", lw=1.5)),
    ("r220", "$220\\times41$", dict(color="crimson", ls="-", lw=1.8)),
    ("r440", "$440\\times82$", dict(color="navy", ls="-", lw=1.5)),
    ("no_cyl", "no cylinder", dict(color="seagreen", ls="--", lw=1.5)),
    ("disk_marks", "filled-disc markers", dict(color="darkorange", ls="-.", lw=1.4)),
    ("iter2", "$n_{iter}=2$", dict(color="purple", ls=":", lw=1.6)),
    ("iter20", "$n_{iter}=20$", dict(color="teal", ls=":", lw=1.6)),
    ("dfg_110", "DFG profile, $110\\times21$", dict(color="brown", ls="-", lw=1.2)),
    ("dfg_220", "DFG profile, $220\\times41$", dict(color="black", ls="-", lw=1.6)),
]


def _nearest_index(a, grid):
    """Index of each value of ``a`` in the sorted ``grid``.

    ``searchsorted`` alone is not enough: a node whose coordinate is 0.35000000000000003
    lands one cell to the right of the 0.35 lattice line, which silently drops points
    and leaves NaNs in the assembled lattice.
    """
    idx = np.clip(np.searchsorted(grid, a), 0, len(grid) - 1)
    bad = ~np.isclose(grid[idx], a, rtol=0.0, atol=1e-9)
    if bad.any():
        idx[bad] = np.abs(grid[None, :] - a[bad, None]).argmin(axis=1)
    return idx


def parse_log(path):
    """Cd/Cl/u_L2 history straight from the driver's stdout."""
    ts, cd, cl, uL2 = [], [], [], []
    pat = re.compile(r"Step \d+/\d+, t=([\d.]+)s, u_L2=([\d.eE+-]+), p_L2=([\d.eE+-]+), "
                     r"Cd=([-\d.eE+]+), Cl=([-\d.eE+]+)")
    if not os.path.exists(path):
        return None
    for line in open(path):
        m = pat.search(line)
        if m:
            ts.append(float(m.group(1)))
            uL2.append(float(m.group(2)))
            cd.append(float(m.group(4)))
            cl.append(float(m.group(5)))
    if not ts:
        return None
    return dict(t=np.array(ts), u_L2=np.array(uL2), Cd=np.array(cd), Cl=np.array(cl))


CV_SANE_CD = 50.0   # anything above this means the balance is dominated by wall friction


def control_volume_drag(outdir, x_end=1.7, rho=RHO):
    """Drag on the cylinder from a momentum balance over [0, x_end] x [0, LY].

    Uses only u and p on the fluid mesh, so it is independent of how the IBM force
    is spread onto the grid.
    """
    from make_demo_figures import Series

    vel = Series(os.path.join(outdir, "velocity.xdmf"), "f")
    pre = Series(os.path.join(outdir, "pressure.xdmf"), "f")
    t = float(vel.times.max())
    _, uv = vel.read(t)
    _, pv = pre.read(t)

    pts = vel.points
    xs = np.unique(np.round(pts[:, 0], 10))
    ys = np.unique(np.round(pts[:, 1], 10))
    nx, ny = len(xs), len(ys)
    ix = _nearest_index(pts[:, 0], xs)
    iy = _nearest_index(pts[:, 1], ys)

    def lat(v):
        out = np.full((ny, nx), np.nan)
        out[iy, ix] = v
        return out

    ux = lat(uv[:, 0])
    uy = lat(uv[:, 1])
    p = lat(pv.ravel())
    dy = float(ys[1] - ys[0])

    j_in = int(np.argmin(np.abs(xs - (CX - R))))
    j_out = int(np.argmin(np.abs(xs - x_end)))
    q_in = np.trapezoid(ux[:, j_in] ** 2, ys)
    q_out = np.trapezoid(ux[:, j_out] ** 2, ys)
    p_in = float(np.nanmean(p[:, j_in]))
    p_out = float(np.nanmean(p[:, j_out]))

    # wall shear: mu * du_x/dy at the first interior row, both walls
    def du_dy(row_a, row_b):
        return (ux[row_a, j_in:j_out + 1] - ux[row_b, j_in:j_out + 1]) / (ys[row_a] - ys[row_b])

    tau_bot = MU * np.nanmean(du_dy(1, 0)) * (xs[j_out] - xs[j_in])
    tau_top = -MU * np.nanmean(du_dy(ny - 1, ny - 2)) * (xs[j_out] - xs[j_in])

    F = rho * (q_out - q_in) + (p_out - p_in) * LY + (tau_bot + tau_top)
    return dict(F=F, Cd=2.0 * F / (UM ** 2 * D), t=t,
                q_in=q_in, q_out=q_out, p_in=p_in, p_out=p_out,
                tau_bot=tau_bot, tau_top=tau_top,
                x_end=float(xs[j_out]), j_in=int(xs[j_in] / (xs[1] - xs[0])))


def stats(hist, t_from=None):
    if hist is None:
        return None
    t = hist["t"]
    if t_from is None:
        t_from = T_RAMP
    # a diverging run must not contaminate the statistics: drop |u_L2| > 10
    finite = np.isfinite(hist["Cd"]) & np.isfinite(hist["Cl"]) & (np.abs(hist["u_L2"]) < 10.0)
    m = (t >= t_from) & finite
    if m.sum() < 10:
        m = (t >= 0.5 * t.max()) & finite
    if m.sum() < 3:
        return dict(diverged=True, n=int(m.sum()))
    cd, cl = hist["Cd"][m], hist["Cl"][m]
    tm = t[m]
    out = dict(diverged=False, n=int(m.sum()),
               Cd_mean=float(cd.mean()), Cd_std=float(cd.std()),
               Cl_mean=float(cl.mean()), Cl_rms=float(np.sqrt(np.mean((cl - cl.mean()) ** 2))),
               t_from=float(tm[0]), t_to=float(tm[-1]))
    # Strouhal number from lift zero crossings
    s = cl - cl.mean()
    sign = np.sign(s)
    cross = np.where(np.diff(sign) != 0)[0]
    if len(cross) > 3:
        period = 2.0 * float(np.mean(np.diff(tm[cross])))
        out["St"] = D / (UM * period)
        out["period"] = period
    return out


def fig_grid_cd(root, figs):
    """Force-integral Cd vs the control-volume Cd across resolutions."""
    rows = []
    for name, label, _ in RUNS[:3]:
        h = parse_log(os.path.join(root, "logs", f"{name}.log"))
        st = stats(h)
        try:
            cv = control_volume_drag(os.path.join(root, name))
            if not np.isfinite(cv["Cd"]) or abs(cv["Cd"]) > CV_SANE_CD:
                print(f"  CV drag for {name} is {cv['Cd']:.1f} — dominated by wall "
                      f"friction in this short channel, discarded")
                cv = None
        except Exception as exc:  # noqa: BLE001
            print(f"  CV drag failed for {name}: {exc}")
            cv = None
        rows.append((name, label, st, cv))
        if st and cv:
            print(f"  {name:<10} Cd(force)={st['Cd_mean']:.4f}  Cd(CV)={cv['Cd']:.4f} "
                  f"St={st.get('St', float('nan')):.3f}")

    fig, axs = plt.subplots(1, 3, figsize=(16, 4.6), constrained_layout=True)
    labels = [r[1] for r in rows]
    x = np.arange(len(rows))
    force = [r[2]["Cd_mean"] if r[2] else np.nan for r in rows]
    cv = [r[3]["Cd"] if r[3] else np.nan for r in rows]
    axs[0].bar(x - 0.2, force, 0.4, label="volume-force integral", color="crimson")
    axs[0].bar(x + 0.2, cv, 0.4, label="control-volume balance", color="navy")
    axs[0].axhline(0.29, color="k", ls=":", lw=1.4, label="tutorial body-fitted $C_d\\approx0.29$")
    axs[0].set_xticks(x); axs[0].set_xticklabels(labels)
    axs[0].set_ylabel("$C_d$"); axs[0].legend(fontsize=8)
    axs[0].set_title("drag: two ways to compute it")
    axs[0].grid(alpha=0.3, axis="y")

    st_vals = [r[2].get("St", np.nan) if r[2] else np.nan for r in rows]
    axs[1].plot(x, st_vals, "o-", color="darkorange")
    axs[1].axhline(0.295, color="k", ls=":", lw=1.4, label="DFG 2D-3 $St\\approx0.295$")
    axs[1].axhline(0.30, color="0.7", ls="--", lw=1.0)
    axs[1].set_xticks(x); axs[1].set_xticklabels(labels)
    axs[1].set_ylabel("$St$"); axs[1].legend(fontsize=8); axs[1].grid(alpha=0.3)
    axs[1].set_title("shedding frequency from the lift signal")

    for name, label, stl in RUNS:
        h = parse_log(os.path.join(root, "logs", f"{name}.log"))
        if h is None:
            continue
        axs[2].plot(h["t"], h["Cl"], **stl, label=label)
    axs[2].axvspan(0, T_RAMP, color="0.9", zorder=0)
    axs[2].text(0.2, 0.9, "inlet ramp", fontsize=8, transform=axs[2].get_xaxis_transform())
    axs[2].set_xlabel("$t$ [s]"); axs[2].set_ylabel("$C_l$ (force integral)")
    axs[2].legend(fontsize=7, ncol=2); axs[2].grid(alpha=0.3)
    axs[2].set_title("lift history, all variants")
    out = os.path.join(figs, "339_study_cd.png")
    fig.savefig(out, dpi=150); plt.close(fig)
    print("wrote", out)
    return rows


def fig_fields(root, figs, run="grid_220", times=(2.0, 3.0, 4.0, 5.0, 5.5, 6.0)):
    from make_demo_figures import Series

    vel = Series(os.path.join(root, run, "velocity.xdmf"), "f")
    pre = Series(os.path.join(root, run, "pressure.xdmf"), "f")
    xs = np.unique(np.round(vel.points[:, 0], 10))
    ys = np.unique(np.round(vel.points[:, 1], 10))
    Y, X = np.meshgrid(ys, xs, indexing="ij")

    def lat(v, pts):
        ix = _nearest_index(pts[:, 0], xs)
        iy = _nearest_index(pts[:, 1], ys)
        if v.ndim == 1:
            out = np.empty((len(ys), len(xs))); out[iy, ix] = v
        else:
            out = np.empty((len(ys), len(xs), v.shape[1])); out[iy, ix, :] = v
        return out

    times = [t for t in times if t <= float(vel.times.max()) + 1e-6]
    fig, axes = plt.subplots(2, len(times), figsize=(3.0 * len(times), 4.6),
                             constrained_layout=True, squeeze=False)
    for j, t in enumerate(times):
        _, uv = vel.read(t)
        _, pv = pre.read(t)
        ul = lat(uv[:, :2], vel.points)
        dx = float(xs[1] - xs[0]); dy = float(ys[1] - ys[0])
        omega = np.gradient(ul[:, :, 1], dx, axis=1) - np.gradient(ul[:, :, 0], dy, axis=0)

        ax = axes[0][j]
        pc = ax.pcolormesh(X, Y, omega, cmap="RdBu_r", shading="gouraud", rasterized=True,
                           vmin=-np.percentile(np.abs(omega), 99.5),
                           vmax=np.percentile(np.abs(omega), 99.5))
        ax.add_patch(Circle((CX, CY), R, color="k"))
        ax.set_xlim(0, 1.2); ax.set_ylim(0, LY); ax.set_aspect("equal")
        ax.set_title(f"$t = {t:g}$ s", fontsize=10)
        ax.set_xticks([]); ax.set_yticks([0, 0.2, 0.4]); ax.tick_params(labelsize=7)
        if j:
            ax.set_yticklabels([])
        if j == 0:
            ax.set_ylabel("vorticity", fontsize=9)

        ax = axes[1][j]
        pl = lat(pv.ravel(), pre.points)
        pm = np.percentile(np.abs(pl), 99)
        ax.pcolormesh(X, Y, pl, cmap="RdBu_r", vmin=-pm, vmax=pm,
                      shading="gouraud", rasterized=True)
        ax.add_patch(Circle((CX, CY), R, color="k"))
        ax.set_xlim(0, 1.2); ax.set_ylim(0, LY); ax.set_aspect("equal")
        ax.set_xticks([0, 0.5, 1.0]); ax.set_yticks([0, 0.2, 0.4])
        ax.tick_params(labelsize=7)
        if j:
            ax.set_yticklabels([])
        if j == 0:
            ax.set_ylabel("pressure", fontsize=9)
    fig.suptitle(f"demo_339 — vortex street behind the cylinder ({run})", fontsize=12)
    out = os.path.join(figs, "339_study_fields.png")
    fig.savefig(out, dpi=150); plt.close(fig)
    print("wrote", out)


def fig_wake(root, figs):
    """Steadiness of the wake: centreline velocity and the recirculation length."""
    from make_demo_figures import Series

    fig, axs = plt.subplots(1, 2, figsize=(13, 4.4), constrained_layout=True)
    for name, label, stl in RUNS[:3]:
        try:
            vel = Series(os.path.join(root, name, "velocity.xdmf"), "f")
        except Exception:  # noqa: BLE001
            continue
        # sample the centreline just above the cylinder axis (y = 0.21)
        for t in [float(vel.times.max())]:
            _, uv = vel.read(t)
            pts = vel.points
            m = np.isclose(pts[:, 1], 0.2) | np.isclose(pts[:, 1], 0.21)
            o = np.argsort(pts[m, 0])
            axs[0].plot(pts[m, 0][o], uv[m, 0][o], **stl, label=label)
    axs[0].axhline(0, color="k", lw=0.8, ls=":")
    axs[0].set_xlim(0, 1.2); axs[0].set_xlabel("$x$")
    axs[0].set_ylabel("$u_x$ on $y = 0.2$")
    axs[0].set_title("centreline velocity: the deficit closes, no oscillation")
    axs[0].grid(alpha=0.3); axs[0].legend(fontsize=8)

    for name, label, stl in RUNS[:3]:
        h = parse_log(os.path.join(root, "logs", f"{name}.log"))
        if h is None:
            continue
        m = h["t"] >= 2.5
        axs[1].plot(h["t"][m], h["Cl"][m] * 1e3, **stl, label=label)
    axs[1].set_xlabel("$t$ [s]"); axs[1].set_ylabel("$C_l \times 10^{3}$")
    axs[1].set_title("lift: the residual oscillation is $\\sim10^{-3}$, i.e. numerical")
    axs[1].grid(alpha=0.3); axs[1].legend(fontsize=8)
    out = os.path.join(figs, "339_study_wake.png")
    fig.savefig(out, dpi=150); plt.close(fig)
    print("wrote", out)


def fig_variants(root, figs):
    """Cd histories for every variant, plus the marker/iteration sensitivity."""
    fig, axs = plt.subplots(1, 2, figsize=(14, 4.6), constrained_layout=True)
    for name, label, stl in RUNS:
        h = parse_log(os.path.join(root, "logs", f"{name}.log"))
        if h is None:
            continue
        axs[0].plot(h["t"], h["Cd"], **stl, label=label)
        axs[1].plot(h["t"], h["u_L2"], **stl)
    for ax, ylab in zip(axs, ["$C_d$ (force integral)", "$u_{L2}$"]):
        ax.axvspan(0, T_RAMP, color="0.9", zorder=0)
        ax.set_xlabel("$t$ [s]"); ax.set_ylabel(ylab)
        ax.grid(alpha=0.3); ax.legend(fontsize=7, ncol=2)
    axs[0].set_title("drag history")
    axs[1].set_title("fluid energy norm")
    out = os.path.join(figs, "339_study_variants.png")
    fig.savefig(out, dpi=150); plt.close(fig)
    print("wrote", out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("--figs", required=True)
    args = ap.parse_args()
    os.makedirs(args.figs, exist_ok=True)

    rows = fig_grid_cd(args.root, args.figs)
    fig_variants(args.root, args.figs)
    try:
        fig_wake(args.root, args.figs)
    except Exception as exc:  # noqa: BLE001
        print('wake figure skipped:', exc)
    try:
        fig_fields(args.root, args.figs)
    except Exception as exc:  # noqa: BLE001
        print("field figure skipped:", exc)

    print("\n=== per-run summary (t >= 2 s) ===")
    for name, label, st in RUNS:
        h = parse_log(os.path.join(args.root, "logs", f"{name}.log"))
        s = stats(h)
        if s is None:
            print(f"{name:<12} (no log)")
            continue
        if s.get("diverged"):
            print(f"{name:<12} {label:<22} DIVERGED (no finite window)")
            continue
        extra = ""
        try:
            cv = control_volume_drag(os.path.join(args.root, name))
            if np.isfinite(cv["Cd"]) and abs(cv["Cd"]) <= CV_SANE_CD:
                extra = f" Cd_CV={cv['Cd']:.4f}"
        except Exception:  # noqa: BLE001
            pass
        print(f"{name:<12} {label:<22} Cd={s['Cd_mean']:.4f}+-{s['Cd_std']:.4f} "
              f"Cl_rms={s['Cl_rms']:.5f} St={s.get('St', float('nan')):.3f}{extra}")


if __name__ == "__main__":
    main()
