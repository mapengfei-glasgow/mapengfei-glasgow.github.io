---
title: "demo_403 — elastic plate in cross flow (3-D)"
description: "demo_403: a 3-D beam in cross flow (Tuković et al. §4.5) with a ramped parabolic inlet, a Neo-Hookean plate clamped at its base and immersed-boundary coupling."
date: 2026-09-12
weight: 403
academic: true
---

## 1. What it is

Channel flow over a thick elastic plate clamped at its base — the 3-D beam-in-cross-flow
case of Tuković et al. (2018) §4.5, at $\mathrm{Re} = 40$. A hexahedral fluid box
is coupled to a tetrahedral plate mesh through `IBMesh3D`; the plate is a
Neo-Hookean solid fixed on its bottom face by a penalty and carries no inertia
(the solid velocity is interpolated from the fluid and the position advanced by
explicit Euler).

{{< figure src="/afsi/demo403-setup.png" title="Figure 1. The channel and the clamped plate." >}}

## 2. Configuration

<p class="tcaption">Table 1. Parameters. Lengths and material constants are in CGS, as in the source; the readme also quotes the SI equivalents.</p>

| Quantity | Code name | Value |
|---|---|---|
| Fluid box | `Lx`, `Ly`, `Lz` | $150 \times 40 \times 40\,\mathrm{cm}$ |
| Fluid cells | `Nx`, `Ny`, `Nz` | $150 \times 40 \times 40$ hexahedra |
| Plate extent | `plate_x0` … `plate_z1` | $x \in [45, 55]$, $y \in [0, 20]$, $z \in [0, 20]\,\mathrm{cm}$ |
| Plate mesh cells | `nx`, `ny`, `nz` | $5 \times 8 \times 8$ (tets) |
| Density / viscosity | `rho`, `mu` | $1.0\,\mathrm{g\,cm^{-3}}$ / $10.0\,\mathrm{dyn\,s\,cm^{-2}}$ |
| Peak inlet velocity | `Um` | $20.0\,\mathrm{cm\,s^{-1}}$ (SI: $0.2\,\mathrm{m\,s^{-1}}$) |
| Inlet ramp | `ramp_time` | $4.0\,\mathrm{s}$, $U_m(1-\cos(\pi t/t_{ramp}))/2$, then held |
| Inlet profile | literal | $u_x = s \cdot 4y(H-y)/H^2$ |
| Reynolds number | — | $40$ (based on plate height) |
| Young's modulus / Poisson | `E_s`, `nu_s` | $1.4\times10^{7}\,\mathrm{dyn\,cm^{-2}}$ / $0.4$ |
| Derived Lamé constants | `mu_s`, `lambda_s` | $5.0\times10^{6}$ / $2.0\times10^{7}$ |
| Base penalty | `beta` | $1\times10^{8}$ on facet marker $10$ |
| Boundary markers | `marker_inlet` … | $1$ inlet, $2$ outlet ($p=0$), $3$ no-slip, $4$ symmetry, $5$ no-slip, $6$ symmetry |
| Time step / end time | `dt`, `T` | $0.001\,\mathrm{s}$ / $6.0\,\mathrm{s}$ ($6000$ steps) |
| Solver | `ChorinSolver` | $\mathrm{P2}$ / $\mathrm{P1}$, force $\mathrm{P2}$ |

There are **no environment overrides** in this demo.

## 3. Files

| File | Role |
|---|---|
| `configuration.py` | All parameters for `main.py`; computes `mu_s`, `lambda_s`, step count, output path |
| `main.py` | Main 3-D driver: fluid, ramped inlet, plate, penalty fixation, IB coupling |
| `generate_mesh.py` | Plate mesh → `plate_mesh.xdmf` (required by `main.py`) |
| `NeoHookean.py`, `FRH.py` | Constitutive classes (imported only by the leftover 2-D script) |
| `fsi_paralell.py`, `generate_mesh-0.py`, `generate_mesh-1.py`, `plot/` | Leftovers from the 2-D ideal-valve work — see the notes |
| `readme.md` | Case description, CGS/SI parameter table, run commands |

## 4. Running it

```bash
cd afsic/demo/demo_403
python generate_mesh.py     # solid plate mesh first
python main.py              # or: mpirun -n 4 python main.py
```

## 5. Results and notes

{{< figure src="/afsi/demo403-results.png" title="Figure 2. A 100-step run at $40 \times 16 \times 16$ with the inlet ramp switched off: the plate picks up a displacement of up to $\approx 3$ mm over $0.05$ s (largest away from the clamped base), and the inflow has only reached $x \approx 20$ cm. The published deflection needs seconds of simulated time, which is out of reach at this resolution." >}}

**No results are archived for the beam case.** `plate_mesh.xdmf` is missing, so
the mesh has to be regenerated, and the readme quotes no outcome values — it only
lists the configuration.

The `plot/` directory does contain digitised curves and figures
(`5.17_*.csv`, `X_M2.csv`, `X_FSI.csv`, `x_dis_ALE.csv`, `Y_*.csv`,
`smoothed_x.png`, `smoothed_y.png`), but every one of them belongs to the
**2-D ideal-valve** case, not to the beam: `fsi_paralell.py` in this directory is
a stale copy of demo_340's driver (`"project_name": "demo-340"`, hard-coded path
to `340-valve/mesh-340.xdmf`), and two further images
(`Anisotropic_x_displacement.png`, `Anisotropic_y_displacement.png`) are orphan
artefacts that no script in the tree writes. AFSI's ideal-valve displacement at
the end of those series is $\approx 0.58\,\mathrm{cm}$ in $x$ and
$\approx 0.42\,\mathrm{cm}$ in $y$ — see [demo_340](/afsi/demo_340/) for the
curves that do belong to that case.

Caveats:

* The original benchmark uses a Saint Venant–Kirchhoff material; here the plate is
  Neo-Hookean, which the readme notes is only valid for small strains. The
  "modified form" the readme also mentions ($U = 0.3\,\mathrm{m\,s^{-1}}$,
  $E = 10\,\mathrm{kPa}$) is **not** what `main.py` runs.
* The symmetry planes are not enforced by Dirichlet conditions — the code simply
  does not constrain the transverse components there, and `bcu` contains only
  the inlet, the bottom and the back face.
* The inline PK1 in `main.py` uses a $J^{-2/3}$ volumetric split, a different
  formulation from `NeoHookean.py` in the same directory.
* The plate is massless and advanced by explicit Euler, with no stability
  discussion in the sources.
* `Lz` $= 40$ with a comment about $z \in [-20,20]$ conflicts with the box, which
  spans $z \in [0, 40]$ while the plate spans only $[0, 20]$ (symmetry at
  $z = 0$).
* `main.py` carries a hard-coded SwanLab key and requires an HTTPS call to build
  the experiment name, so it does not run offline unchanged.
