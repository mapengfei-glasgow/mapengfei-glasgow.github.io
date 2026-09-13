---
title: "demo_343 — discs transported through a 2-D ideal valve"
description: "demo_343: the ideal-valve geometry with two compliant discs carried by the flow, plus a CIRCLE=0 control run that drops the discs' constitutive force."
date: 2026-09-12
weight: 343
academic: true
---

## 1. What it is

The same channel and leaflets as [demo_340](/afsi/demo-340/), with two compliant
discs of radius $0.2$ placed upstream at $x = 0.5$. The upper and lower leaflets
deliberately have different stiffness (the lower one is ten times stiffer, as a
stand-in for a hardened leaflet), and a `CIRCLE` switch produces a control run in
which the discs' restoring force is dropped. Post-processing compares centre-line
$u_x$ profiles at $y = 0.5$ and $y = 1.1$ between the two runs.

{{< figure src="/afsi/demo343-setup.png" title="Figure 1. The ideal-valve geometry with the two compliant discs that the `CIRCLE` switch controls." >}}

## 2. Configuration

<p class="tcaption">Table 1. Parameters (`configuration.py`). The geometry and the inlet profile are shared with demo_340.</p>

| Quantity | Code name | Value |
|---|---|---|
| Channel | `Lx` × `Ly` | $8.0 \times 1.61$ |
| Fluid cells | `Nx`, `Ny` | $320 \times 64$ (cell $0.025 \times 0.0252$) |
| Density / viscosity | `rho`, `mu` | $1.0$ / $0.1$ |
| Inlet profile | literal | $5\,(\sin 2\pi t + 1.1)\,y\,(1.61 - y)$ |
| Leaflets | — | $0.0212 \times 0.7$ at $x \approx 1.9894$, clamped edges $4$ and $15$ |
| Discs | `Circle1`, `Circle2` | radius $0.2$ at $(0.5, 0.5)$ and $(0.5, 1.1)$ |
| Leaflet material | `FRHMaterial` | `C0` $= 2\times10^{5}$ (upper), `C0_down` $= 10\,C0$ (lower), `C1` $= 1\times10^{6}$, `kappa` $= 4\times10^{5}$ |
| Disc stiffness | literal | $0.01 \times$ the upper leaflet's $\mathbf{P}$ |
| Penalty | `beta` | $5\times10^{7}$ |
| Time step / end time | `dt`, `T` | $1/64000$ / $3.0$ ($192\,000$ steps) |
| Solver | `ChorinSolver` | $\mathrm{P2}$ / $\mathrm{P1}$ |

The time step was reduced to $1/64000$ specifically for this fine grid and large
inlet velocity, to prevent a transient flip of the lower leaflet root; `kappa`
was lowered from $4\times10^{6}$ to $4\times10^{5}$ because the larger value gave
excessively large FSI forces.

Environment overrides: `STEPS` (step count and $T$) and `CIRCLE`
($1$ = disc force included, $0$ = omitted; it also selects the output directory
`plot/circle1/` or `plot/circle0/`).

## 3. Files

| File | Role |
|---|---|
| `configuration.py` | All parameters, `STEPS`/`CIRCLE` handling, output paths |
| `main.py` | Driver: channel, leaflets, optional disc stiffness, IB coupling, time loop |
| `materials.py` | `FRHMaterial` (used) and `NeoHookeanMaterial` (unused here) |
| `generate_mesh.py` | Gmsh leaflets + discs ($0.01$–$0.02$ m) → `plot/mesh-343.xdmf` |
| `plot/plot_centerline.py` | Reads `velocity.h5` from each run, samples $u_x$ at $y = 0.5$ and $1.1$, writes `line_disk0.5.csv/.png`, `line_disk1.1.csv/.png` |

## 4. Running it

```bash
conda activate afsi-dolfinx
cd afsic/demo/demo_343
python generate_mesh.py                  # first run only

CIRCLE=1 STEPS=500 python main.py        # with discs
CIRCLE=0 STEPS=500 python main.py        # control run

cd plot && python plot_centerline.py
```

## 5. Results and notes

### 5.1 A live run of the `CIRCLE=1` case ($t \le 0.2$ s)

The case was run at its shipped resolution ($320\times64$ fluid, $\Delta t = 1/64000$)
with `CIRCLE=1`, cutting the $192000$ steps of the full $T = 3$ s down to $12800$
(that is $t \le 0.2$ s), serially — the $\texttt{IBMesh}$ marker map is not MPI-safe.
It took $3850$ s, or $0.30\,\mathrm{s}$ per step.

{{< figure src="/afsi/demo343-valve-discs.png" title="Figure 3. The re-run: velocity magnitude with the solids shaded by their own displacement (top: whole channel, bottom: the valve region). The leaflets swing open as the inlet rises, forming an asymmetric nozzle, while the two discs are carried downstream." >}}

{{< figure src="/afsi/demo343-displacement.png" title="Figure 4. Solid displacement over the run. The maximum grows steadily with the pressure load; the discs are 100x softer than the leaflets, so they dominate it." >}}

<p class="tcaption">Table 2. The live run.</p>

| Quantity | Value |
|---|---|
| Steps / wall time | $12800$ steps, $3850$ s serial ($0.30\,\mathrm{s}$/step) |
| $u_{L2}$ | grows monotonically $73 \to 297$ (the inlet forcing is still ramping up to its $t = 0.25$ s peak) |
| Field | $\max\lvert u\rvert = 8.05\,\mathrm{m\,s^{-1}}$ |
| Solid $\max\lvert u_s\rvert$ | $0.824\,\mathrm{m}$ — carried by the soft discs, not the leaflets |
| Leaflet opening | the two tips separate and bend downstream from $t \approx 40$ ms, reaching a nozzle-like shape by $t = 200$ ms |

Note on the output cadence: `TimeManager` derives its write interval from
$T/(\mathrm{fps}\,T)$, so with `STEPS` overriding `num_steps` but not `T` it writes
**every step**. `main.py` now builds the `TimeManager` from
$\texttt{num\_steps}\cdot\Delta t$. Running the full $T = 3$ s at this resolution needs
$192000$ steps, about 16 h serial.

{{< figure src="/afsi/demo343-results.png" title="Figure 2. The demo's own post-processing after 500 steps (both `CIRCLE` settings): the centreline at the two disc heights. The two runs differ only near the discs, which is what the `CIRCLE=0` control was meant to expose — it removes the constitutive force but leaves the markers coupled." >}}

**No results are archived** for this demo — neither the fields, nor the
centre-line CSVs, nor the comparison figures are in the repository, so the run
has to be repeated to reproduce them. The only quantitative statement in the
sources is the cost note: about $0.2\,\mathrm{s}$ per step on the
$320 \times 64$ grid, which makes the full $192\,000$-step run a long one.

Caveats:

* The readme and the `main.py` docstring describe a neo-Hookean solid with
  $\mu_s = 5.6\times10^{5}$ (upper) and $\mu_{s,\text{down}} = 5.6\times10^{6}$
  (lower); the code actually uses `FRHMaterial`, so the lower leaflet stiffness
  is `C0_down` $= 2\times10^{6}$, and the `mu_s`/`nv_s` config entries are dead.
* `CIRCLE=0` does not remove the discs: it only omits their constitutive force.
  The disc markers stay in the coupled system, still receive the interpolated
  fluid velocity and are still spread back into the fluid, so what the control
  run actually measures is unclear.
* The docstring tells the user to run `fsi_paralell.py`, which no longer exists
  (renamed to `main.py`); `plot_centerline.py` prints the same stale message.
* `plot_centerline.py` bypasses the XDMF reader and parses `velocity.h5` with raw
  `h5py`, sorting keys by `float(key.replace("_", "."))` and taking the last
  stored step, so it is sensitive to any change in the output layout.
* As in demo_340 the facet/cell tag numbering is a hard-coded contract with
  `generate_mesh.py`.
