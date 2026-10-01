---
title: "343: Discs Through an Ideal 2-D Valve"
description: "Two compliant discs carried through an ideal 2-D valve."
date: 2026-09-12
weight: 343
academic: true
demo_id: demo_343
category: Application
dimension: 2D
solid_model: "FRH leaflets (upper C0, lower 10·C0) + two compliant discs at 0.01·C0"
coupling: "immersed boundary (`IBMesh`), serial only"
reference: "— (CIRCLE=1 against CIRCLE=0 control run)"
status: Partial
---

## 1. Introduction

The same channel and leaflets as [demo_340](/afsi/demo-340/), with two compliant
discs of radius $0.2$ placed upstream at $x = 0.5$. The upper and lower leaflets
deliberately have different stiffness (the lower one is ten times stiffer, as a
stand-in for a hardened leaflet), and a `CIRCLE` switch produces a control run in
which the discs' restoring force is dropped. Post-processing compares centre-line
$u_x$ profiles at $y = 0.5$ and $y = 1.1$ between the two runs.

## 2. Problem description

### 2.1 Geometry

{{< figure src="/afsi/demo343-setup.png" title="Figure 1. The ideal-valve geometry with the two compliant discs that the `CIRCLE` switch controls." >}}

The channel, the two FRH leaflets and the pulsatile inlet are those of
[demo_340](/afsi/demo-340/); the discs of radius $0.2$ sit at $(0.5, 0.5)$ and
$(0.5, 1.1)$ upstream of the valve.

### 2.2 Governing equations

{{< color "red" >}}TODO: governing equations — incompressible Navier–Stokes, the FRH leaflet constitution (as in demo_340), the disc stiffness law, and the IB coupling terms (see the symbol table page).{{< /color >}}

The discs use a stiffness of $0.01 \times$ the upper leaflet's $\mathbf P$; the
leaflets are the same `FRHMaterial` as demo_340, with the lower leaflet ten times
stiffer (`C0_down` $= 10\,C0$).

### 2.3 Boundary and initial conditions

The inlet carries the pulsatile profile shared with demo_340
($5(\sin 2\pi t + 1.1)\,y\,(1.61-y)$), the channel walls are no-slip and the
outlet is at $p = 0$; the leaflets are clamped on edges $4$ and $15$.

### 2.4 Physical parameters

<p class="tcaption">Table 1. Parameters (`configuration.py`). The geometry and the inlet profile are shared with demo_340.</p>

| Quantity | Code name | Value |
|---|---|---|
| Channel | `Lx` × `Ly` | $8.0 \times 1.61$ |
| Density / viscosity | `rho`, `mu` | $1.0$ / $0.1$ |
| Inlet profile | literal | $5\,(\sin 2\pi t + 1.1)\,y\,(1.61 - y)$ |
| Leaflets | — | $0.0212 \times 0.7$ at $x \approx 1.9894$, clamped edges $4$ and $15$ |
| Discs | `Circle1`, `Circle2` | radius $0.2$ at $(0.5, 0.5)$ and $(0.5, 1.1)$ |
| Leaflet material | `FRHMaterial` | `C0` $= 2\times10^{5}$ (upper), `C0_down` $= 10\,C0$ (lower), `C1` $= 1\times10^{6}$, `kappa` $= 4\times10^{5}$ |
| Disc stiffness | literal | $0.01 \times$ the upper leaflet's $\mathbf{P}$ |
| Penalty | `beta` | $5\times10^{7}$ |

{{< color "red" >}}TODO: dimensionless numbers if the case is to be reported dimensionless.{{< /color >}}

## 3. Numerical setup

The fluid grid is $320 \times 64$ (cell $0.025 \times 0.0252$) with
`ChorinSolver` ($\mathrm{P2}$ / $\mathrm{P1}$) and $\Delta t = 1/64000\,\mathrm{s}$
to $T = 3\,\mathrm{s}$ ($192\,000$ steps). The time step was reduced to
$1/64000$ specifically for this fine grid and large inlet velocity, to prevent a
transient flip of the lower leaflet root; `kappa` was lowered from
$4\times10^{6}$ to $4\times10^{5}$ because the larger value gave excessively
large FSI forces.

Environment overrides: `STEPS` (step count and $T$) and `CIRCLE`
($1$ = disc force included, $0$ = omitted; it also selects the output directory
`plot/circle1/` or `plot/circle0/`).

## 4. Results

### 4.1 Quantities of interest

The quantities of interest are the valve opening (leaflet-tip separation and bend
from $t \approx 40$ ms), the disc transport downstream, the solid displacement
$\max\vert u_s\vert$ (discs against leaflets), the fluid energy norm $u_{L2}$ and
field maximum $\max\vert u\vert$, and the centre-line $u_x$ profiles at the two
disc heights with and without the disc force (`CIRCLE=1` vs `CIRCLE=0`).

### 4.2 Comparison with reference

{{< color "red" >}}TODO: quantify the `CIRCLE=1` vs `CIRCLE=0` centre-line
comparison — the control run is meant to isolate the discs' constitutive force, but
no numbers are archived, and what the control actually removes is itself in doubt
(see §5).{{< /color >}}

| Quantity | AFSI | Reference | rel. err. |
| --- | --- | --- | --- |
| Centreline $u_x$ (at disc heights) |  |  |  |

### 4.3 Convergence study

{{< color "red" >}}TODO: grid and time-step sensitivity — the live run used the shipped resolution only; no refinement study exists.{{< /color >}}

### 4.4 Flow and deformation fields

The case was run at its shipped resolution ($320\times64$ fluid,
$\Delta t = 1/64000$) with `CIRCLE=1`, cutting the $192000$ steps of the full
$T = 3$ s down to $12800$ (that is $t \le 0.2$ s), serially — the
$\texttt{IBMesh}$ marker map is not MPI-safe. It took $3850$ s, or
$0.30\,\mathrm{s}$ per step.

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

## 5. Discussion and limitations

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

## 6. Reproducibility

<p class="tcaption">Table 3. Files in the demo.</p>

| File | Role |
|---|---|
| `configuration.py` | All parameters, `STEPS`/`CIRCLE` handling, output paths |
| `main.py` | Driver: channel, leaflets, optional disc stiffness, IB coupling, time loop |
| `materials.py` | `FRHMaterial` (used) and `NeoHookeanMaterial` (unused here) |
| `generate_mesh.py` | Gmsh leaflets + discs ($0.01$–$0.02$ m) → `plot/mesh-343.xdmf` |
| `plot/plot_centerline.py` | Reads `velocity.h5` from each run, samples $u_x$ at $y = 0.5$ and $1.1$, writes `line_disk0.5.csv/.png`, `line_disk1.1.csv/.png` |

```bash
conda activate afsi-dolfinx
cd afsic/demo/demo_343
python generate_mesh.py                  # first run only

CIRCLE=1 STEPS=500 python main.py        # with discs
CIRCLE=0 STEPS=500 python main.py        # control run

cd plot && python plot_centerline.py
```

## References

{{< color "red" >}}TODO: references — none cited; the hardened-leaflet setup suggests a clinical motivation that should be cited.{{< /color >}}
