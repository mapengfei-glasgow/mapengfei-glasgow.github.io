---
title: "demo_340 — 2-D ideal valve with fibre-reinforced leaflets"
description: "demo_340: two anisotropic (FRH) leaflets in a pulsatile channel, with the fibre angle as the parameter and the archived AFSI displacement compared against Ryan et al. and Kamensky et al."
date: 2026-09-12
weight: 340
academic: true
---

## 1. What it is

Two thin leaflets sit in a straight channel driven by a pulsatile inlet profile;
they are fibre-reinforced hyperelastic (FRH) solids coupled to the fluid through
the immersed boundary. The demo has two axes: a comparison of the AFSI tip
displacement against published reference curves (Ryan et al. M2/M3, Kamensky et
al.), and a fibre-angle study at $45^\circ$, $60^\circ$ and $75^\circ$.

{{< figure src="/afsi/demo340-setup.png" title="Figure 1. The channel and the two fibre-reinforced leaflets, with the pulsatile inlet and the clamped edges." >}}

## 2. The model problem

A straight channel $\Omega_f = [0,8]\times[0,1.61]$ carries an incompressible
Newtonian fluid. Its left edge is driven by a pulsatile, parabolic inlet profile and
its right edge is held at zero pressure. Two thin fibre-reinforced hyperelastic
leaflets hang from the channel walls and move with the flow:

$$
\Omega_f = [0,8]\times[0,1.61], \qquad
\Omega_s = \Omega_1 \cup \Omega_2, \qquad
\Omega_1 = [1.9788,2.0]\times[0,0.7], \quad
\Omega_2 = [1.9788,2.0]\times[0.91,1.61].
$$

The fluid satisfies

$$
\rho\left(\frac{\partial \mathbf u}{\partial t}
+ (\mathbf u\cdot\nabla)\mathbf u\right) = -\nabla p + \mu\nabla^2\mathbf u
+ \mathbf f_{\mathrm{IB}},
\qquad \nabla\cdot\mathbf u = 0
$$

with $\rho = 1$, $\mu = 0.1$, and $\mathbf f_{\mathrm{IB}}$ the immersed-boundary
force that communicates the leaflets to the fluid. On the inlet, $x = 0$,

$$
\mathbf u(0,y,t) = \bigl(5(\sin 2\pi t + 1.1)\,y\,(1.61-y),\;0\bigr),
$$

so the pulse has period $1\,\mathrm{s}$, and the peak of the profile oscillates
between $5\times0.1 = 0.5$ and $5\times2.1 = 10.5$ over each cycle (it peaks at
$t = 1/4\,\mathrm{s}$ and troughs at $t = 3/4\,\mathrm{s}$); the walls are no-slip and
the outlet carries $p = 0$.

### The leaflet material

The leaflets are fibre-reinforced hyperelastic (FRH) solids. With
$\mathbf F = \nabla_{\!X}\mathbf X$ the deformation gradient, $J = \det\mathbf F$ and
the isochoric right Cauchy–Green tensor $\bar{\mathbf C} = J^{-2/3}\mathbf F^{\mathsf T}\mathbf F$,
the strain-energy density is

$$
\Psi = \frac{C_0}{2}\bigl(\bar I_1 - 3\bigr)
+ C_1\bigl(e^{\bar I_4 - 1} - \bar I_4\bigr)
+ \frac{\kappa}{4}\bigl(J^2 - 1\bigr) - \frac{\kappa}{2}\ln J,
$$

where $\bar I_1 = \operatorname{tr}\bar{\mathbf C}$,
$\bar I_4 = \mathbf f_1\cdot\bar{\mathbf C}\mathbf f_1$, and $\mathbf f_1$ is the unit
fibre direction. The parameters are the shear modulus $C_0 = 2\times10^5$, the fibre
stiffness $C_1 = 1\times10^6$ and the bulk modulus $\kappa = 4\times10^5$. The
exponential fibre term is what makes the leaflets nearly inextensible along
$\mathbf f_1$: a $45^\circ$ layup for each leaflet, mirrored between the two so the
pair opens symmetrically. The first Piola–Kirchhoff stress is the derivative
$\mathbf P = \partial\Psi/\partial\mathbf F$; the driver lets UFL differentiate the
energy instead of writing $\mathbf P$ out by hand.

### The coupled weak form

The solid is advanced by a weak statement of the internal force only — there is no
solid mass term:

$$
\int_{\Omega_s}\mathbf P(\mathbf F):\nabla_{\!X}\delta\mathbf v\,\mathrm dX
\;+\;\beta\sum_{e\in\{4,15\}}\int_{\Gamma_e}
\bigl(\mathbf X - \mathbf X_0\bigr)\cdot\delta\mathbf v\,\mathrm ds
\;=\;0 ,
$$

where the second term is a penalty that pins the wall-attached leaflet edges
($\beta = 10^8$), and $e = 4$ and $e = 15$ are the facet tags of the lower and upper
leaflets respectively. $\mathbf X$ are the *current* solid node coordinates, so the
form is assembled from the Lagrangian coordinates themselves rather than from a
displacement field.

The code assembles exactly this quantity, with the opposite overall sign — the
driver's `L_hat` carries a leading minus and is used directly as the residual
vector. For a Galerkin residual that sign is a convention, but it matters for how the
resulting vector enters the fluid: the C++ spreading kernel
(`IBInterpolation::solid_to_fluid`) sets every node weight to $w_l = 1$ and sums,
$\mathbf f_{ij} = \sum_l \delta_h(\mathbf x_{ij}-\mathbf X_l)\,\mathbf F_l$, with no
further scaling. So the discrete object that drives the fluid is the assembled
leaflet stress residual, spread with unit weights.

## 3. Solving it with the immersed boundary method

The fluid and the solid live on different meshes and are coupled only through
interpolation with a regularised delta function. Let $\{\mathbf X_l\}$ be the solid
nodes and $\{\mathbf x_{ij}\}$ the fluid grid nodes. Each time step does four things.

**1. Advance the fluid one step without the solid.** `ChorinSolver` performs a
standard projection step: a tentative velocity, a pressure Poisson solve with
$p = 0$ on the outlet, then an $L^2$ projection back onto the divergence-free space
with the boundary conditions re-imposed.

**2. Interpolate the fluid velocity onto the solid nodes**,

$$
\mathbf U_l = \sum_{ij} \delta_h(\mathbf x_{ij} - \mathbf X_l)\,\mathbf u_{ij}.
$$

**3. Advect the solid nodes** with that velocity,

$$
\mathbf X^{\,n+1}_l = \mathbf X^{\,n}_l + \Delta t\,\mathbf U_l .
$$

This is the defining choice of this demo: the leaflets are **massless** and purely
kinematic. They move exactly as the fluid at their location moves, and their
elasticity enters only through the force they push back in step 4 — the same
formulation as the standard immersed-boundary method for elastic boundaries.

**4. Spread the elastic force back onto the fluid**,

$$
\mathbf f_{ij} = \sum_l \delta_h(\mathbf x_{ij} - \mathbf X_l)\,
\mathbf F_l , \qquad
\mathbf F_l = -\int_{\Omega_s}\mathbf P(\mathbf F):\nabla_{\!X}\delta\mathbf v_l\,\mathrm dX
- \beta\,(\mathbf X_l - \mathbf X_{0,l})\big|_{\Gamma_4\cup\Gamma_{15}} .
$$

Because step 1 already used $\mathbf f^n_{\mathrm{IB}}$ when it advanced the fluid,
the coupled scheme is explicit in time: fluid, then solid, then force, then next
step.

## 4. The implementation

The driver is `main.py`; the material lives in `materials.py`. We reproduce the
parts that carry the mathematics.

**Material.** The strain energy is written once and differentiated symbolically:

```python
class FRHMaterial:
    def strain_energy(self, domain, F):
        J = ufl.det(F)
        C = F.T * F
        F_bar = J ** (-1/2) * F
        C_bar = F_bar.T * F_bar
        I1_bar = ufl.tr(C_bar)
        I4_bar = ufl.dot(params["f1"], C_bar * params["f1"])
        psi = (0.5 * params["C0"] * (I1_bar - 3)
               + params["C1"] * (ufl.exp(I4_bar - 1) - I4_bar)
               + 0.5 * params["kappa_s"] * (0.5 * (J * J - 1) - ufl.ln(J)))
        return psi

    def first_piola_kirchhoff_stress_v1(self, domain, coords):
        F = ufl.variable(ufl.grad(coords))
        return ufl.diff(self.strain_energy(domain, F), F)
```

Note that `coords` are the current coordinates, so `grad(coords)` *is*
$\mathbf F$ — the form is written in the current configuration and integrated over
the reference domain, which is why no displacement field appears.

**Fibre directions.** Each leaflet gets its own mirrored unit vector:

```python
f1_u = ufl.as_vector((0.7071067811865475, -0.7071067811865475))  # upper, 45 deg
f1_d = ufl.as_vector((0.7071067811865475,  0.7071067811865475))  # lower, 45 deg

material_up = FRHMaterial(C0=config["C0"], C1=config["C1"],
                          kappa_s=config["kappa"], f1=f1_u)
material_down = FRHMaterial(C0=config["C0"], C1=config["C1"],
                            kappa_s=config["kappa"], f1=f1_d)
```

**Internal force and fixation.** One form, restricted to the two cell tags, plus the
penalty on the pinned edges:

```python
PK1_up = material_up.first_piola_kirchhoff_stress_v1(structure, solid_coords)
PK1_down = material_down.first_piola_kirchhoff_stress_v1(structure, solid_coords)

L_hat = -inner(PK1_up, grad(dVs)) * dxx(11)          # upper leaflet (cell tag 11)
L_hat -= inner(PK1_down, grad(dVs)) * dxx(1)         # lower leaflet (cell tag 1)
L_hat -= config["beta"] * ufl.inner(circum_constraint, dVs) * dss(4)   # lower edge
L_hat -= config["beta"] * ufl.inner(circum_constraint, dVs) * dss(15)  # upper edge
L_hat = form(L_hat)
```

**The time loop**, in full, is the four steps of §3:

```python
for step in range(config["num_steps"]):
    inlet_velocity.t = step * config["dt"]
    u_inlet.interpolate(inlet_velocity)          # 1. pulsatile inlet
    ns_solver.solve_one_step()                   #    fluid step (Chorin)
    ib_interpolation.fluid_to_solid(ns_solver.u_._cpp_object,
                                    solid_velocity._cpp_object)   # 2. u -> U_l
    solid_coords.x.array[:] += solid_velocity.x.array[:] * config["dt"]  # 3. advect
    solid_coords.x.scatter_forward()

    ib_interpolation.evaluate_current_points(solid_coords._cpp_object)
    assemble_vector(b1, L_hat)                   # 4. elastic force on solid nodes
    ...
    ib_interpolation.solid_to_fluid(ns_solver.f._cpp_object,
                                    solid_force._cpp_object)      #    spread to grid
    ns_solver.f.x.scatter_forward()
```

The interpolation and spreading kernels (`IBMesh`, `IBInterpolation`,
`fluid_to_solid`, `solid_to_fluid`) are compiled C++ inside the `afsic` package, so
this demo configures them rather than reimplements them; `evaluate_current_points`
is what rebuilds the node-to-cell map each step, because the leaflet nodes move.

## 5. Configuration

<p class="tcaption">Table 1. Channel, leaflets and material. The fluid grid and the leaflet mesh are fixed; the fibre angle is the only parameter that changes between runs.</p>

| Quantity | Code name | Value |
|---|---|---|
| Channel | `Lx` × `Ly` (`main.py:39-40`) | $8.0 \times 1.61$ |
| Fluid cells | `Nx`, `Ny` | $128 \times 32$ (cell $0.0625 \times 0.0503$) |
| Density / viscosity | `rho`, `mu` | $1.0$ / $0.1$ |
| Inlet profile | literal (`main.py:123`) | $5\,(\sin 2\pi t + 1.1)\,y\,(1.61 - y)$ |
| Outlet | — | $p = 0$ on the right edge |
| Leaflets | `lx`, `ly` | $0.0212 \times 0.7$, at $x \approx 1.9894$, $y = 0$ and $y = 0.91$ |
| Clamped edges | `dss(4)`, `dss(15)` | wall-attached edges, penalty `beta` $= 1\times10^{8}$ |
| Solid mesh size | Gmsh | $0.01$ |
| Material | `FRHMaterial` | `C0` $= 2\times10^{5}$, `C1` $= 1\times10^{6}$, `kappa` $= 4\times10^{5}$ |
| Fibre vectors | `f1_d`, `f1_u` | $45^\circ$: $(0.7071, \pm0.7071)$; $60^\circ$ and $75^\circ$ are commented out in `main.py` |
| Time step / end time | `dt`, `T` | $1/16000$ / $3.0$ ($48\,000$ steps) |
| Solver | `ChorinSolver` | $\mathrm{P2}$ velocity, $\mathrm{P1}$ pressure, force $\mathrm{P2}$ |

Environment overrides: `STEPS` only (it sets both the step count and
$T = \text{STEPS}\cdot\Delta t$; `STEPS=20` is the documented smoke test).

## 6. Files

<p class="tcaption">Table 1. Channel, leaflets and material. The fluid grid and the leaflet mesh are fixed; the fibre angle is the only parameter that changes between runs.</p>

| Quantity | Code name | Value |
|---|---|---|
| Channel | `Lx` × `Ly` (`main.py:39-40`) | $8.0 \times 1.61$ |
| Fluid cells | `Nx`, `Ny` | $128 \times 32$ (cell $0.0625 \times 0.0503$) |
| Density / viscosity | `rho`, `mu` | $1.0$ / $0.1$ |
| Inlet profile | literal (`main.py:123`) | $5\,(\sin 2\pi t + 1.1)\,y\,(1.61 - y)$ |
| Outlet | — | $p = 0$ on the right edge |
| Leaflets | `lx`, `ly` | $0.0212 \times 0.7$, at $x \approx 1.9894$, $y = 0$ and $y = 0.91$ |
| Clamped edges | `dss(4)`, `dss(15)` | wall-attached edges, penalty `beta` $= 1\times10^{8}$ |
| Solid mesh size | Gmsh | $0.01$ |
| Material | `FRHMaterial` | `C0` $= 2\times10^{5}$, `C1` $= 1\times10^{6}$, `kappa` $= 4\times10^{5}$ |
| Fibre vectors | `f1_d`, `f1_u` | $45^\circ$: $(0.7071, \pm0.7071)$; $60^\circ$ and $75^\circ$ are commented out in `main.py` |
| Time step / end time | `dt`, `T` | $1/16000$ / $3.0$ ($48\,000$ steps) |
| Solver | `ChorinSolver` | $\mathrm{P2}$ velocity, $\mathrm{P1}$ pressure, force $\mathrm{P2}$ |

Environment overrides: `STEPS` only (it sets both the step count and
$T = \text{STEPS}\cdot\Delta t$; `STEPS=20` is the documented smoke test).

## 7. Running it

| File | Role |
|---|---|
| `main.py` | Driver: fluid, FRH leaflets, penalty fixation, IB coupling, time loop |
| `materials.py` | `FRHMaterial` (used) and `NeoHookeanMaterial` (fallback, unused here) |
| `generate_mesh.py` | Gmsh leaflets → `plot/mesh-340.xdmf` (tag offsets $0$ and $10$) |
| `plot/plot_1.py` | AFSI against Ryan M2/M3 and Kamensky → `smoothed_x.png`, `smoothed_y.png` |
| `plot/plot_2.py` | Fibre-angle comparison → `Anisotropic_x_displacement.png`, `Anisotropic_y_displacement.png` |
| `plot/data/ani_{t,x,y}.csv` | Archived AFSI probe series ($302$ rows) for $45^\circ/60^\circ/75^\circ$ |
| `plot/{X_M2,X_FSI,x_dis_ALE,Y_FSI,y_M2,Y_ALE}.csv` | Digitised reference curves |


```bash
conda activate afsi-dolfinx
cd afsic/demo/demo_340
python generate_mesh.py          # first run only (needs gmsh / python-gmsh)
mpirun -n 8 python main.py       # full T = 3 s; ~12 min on 8 ranks, ~7 h serial

cd plot && python plot_1.py      # comparison figure
python plot_2.py                 # fibre-angle figure
```

Switching the fibre angle means editing the active `f1_*` / material lines in
`main.py` (the $60^\circ$ and $75^\circ$ vectors are present but commented out).

## 8. A full $T = 3$ s run

The archived series was regenerated end to end: `generate_mesh.py` (572 nodes, 848
triangles, tag offsets 0 and 10) followed by the full $48\,000$ steps at
$\Delta t = 1/16\,000$ s, driven by the pulsatile inlet
$5(\sin 2\pi t + 1.1)\,y\,(L_y - y)$. Two practical notes from the run:

* **Run it with MPI.** The same 200 steps cost $125$ s on one rank and $7$ s on
  eight — a serial `main.py` would need roughly seven hours for $T = 3$ s, while
  eight ranks finish it in **12 minutes**. The per-step probe hook below was added
  because the archived comparison needs the trace at every step rather than at the
  `fps = 100` output rate.
* **`gmsh` is a separate install** (`python-gmsh`); without it `generate_mesh.py`
  cannot run, and `main.py` reads `plot/mesh-340.xdmf` unconditionally.
* `OUTPUT_PATH` and `PROBE_TRACE` environment overrides were added to `main.py`
  (the former so a run does not have to write into the demo tree, the latter to
  dump the probe trace to CSV per step).

{{< figure src="/afsi/demo340-valve-3s.png" title="Figure 3. The re-run at 0, 0.25, 0.5, 0.75, 1, 1.25, 1.5, 2 and 3 s. Top: the whole 8 x 1.61 channel (dashed box = the zoom below). Middle: the valve region with streamlines — the leaflets are shaded by their own displacement. Bottom: the two leaflets alone, dotted lines marking the undeformed positions. The leaflets are pushed downstream as the inlet rises and spring back as it falls." >}}

{{< figure src="/afsi/demo340-history.png" title="Figure 4. Leaflet-tip displacement against the published curves: Ryan et al. M2/M3, Kamensky et al., the archived AFSI 45-degree series (thick grey) and this run (thin red), plus the inlet waveform with the snapshot times marked. This run is indistinguishable from the archive at this scale." >}}

<p class="tcaption">Table 3. This run ($45^\circ$, $T = 3$ s) against the archived AFSI series and the reference curves.</p>

| Quantity | Value |
|---|---|
| Steps / wall time | $48\,000$ steps, $707$ s on 8 MPI ranks |
| Tip $x$-displacement | ranges $0.00015 \to 0.6015$; peak at $t \approx 1.25$ s |
| Tip $y$-displacement | ranges $0.000 \to 0.4476$; peak at $t \approx 1.25$ s |
| Whole-leaflet $\max \vert u_s \vert$ | $0.7515$ m, against a leaflet length of $0.7$ |
| Agreement with the archived AFSI $45^\circ$ series | $\max$ difference $3.7\times10^{-4}$ on a $0.6014$ signal (0.06 %) |
| Cycle-to-cycle repeat | $x$ at $t = 0.25$ s vs $t = 2.25$ s: $0.5942$ vs $0.6013$ (1.2 %), i.e. still creeping toward the periodic state |
| Versus the literature band | this run sits $\sim 8$ % above Ryan M2/M3 and Kamensky in $x$ and up to $\sim 18$ % in $y$ — the same offset the archived AFSI series shows |

Raw per-step probe trace: `static/afsi/demo340-run/probe45-tip-displacement.csv.gz`
($48\,000$ rows), figures from `static/afsi/demo340-make_valve_figures.py`.

The deflection is **quasi-steady**: the tip tracks the inlet waveform with no
visible phase lag, peaking as the inlet peaks ($t \approx 0.25$ s into each
cycle) and returning to a small residual as the inlet dips. The leaflets swing
apart rather than toward each other — the free gap between the tips widens from
$0.21$ (undeformed) up to $1.08$ at the peak, and narrows back to $0.50$ at the
trough, i.e. it stays between $31\,\%$ and $67\,\%$ of $L_y$. The highest speeds
in the field ($\sim 9.2$ m/s, against an inlet peak of $10.5$ m/s) sit at
$x \approx 2.7$, just downstream of the leaflets, rather than at the inlet.


## 9. What the archived series can and cannot tell us

{{< figure src="/afsi/demo340-results.png" title="Figure 2. Archived probe series for the three fibre angles, against the digitised literature curves." >}}

The archived probe series ends at $t = 2.9999\,\mathrm{s}$:

<p class="tcaption">Table 2. Leaflet-tip displacement at the end of the run, against the published reference curves (all values in mesh units, endpoint of each series).</p>

| Source | $x$ displacement | $y$ displacement |
|---|---|---|
| AFSI, $45^\circ$ fibres | $0.5141$ | $0.2624$ |
| AFSI, $60^\circ$ fibres | $0.5099$ | $0.2587$ |
| AFSI, $75^\circ$ fibres | $0.4945$ | $0.2403$ |
| Ryan et al. M2 | $0.4614$ | $0.2083$ |
| Ryan et al. M3 | $0.4759$ | $0.2229$ |
| Kamensky et al. | $0.4753$ | $0.2228$ |

The angle trend is the expected one — the stiffer $75^\circ$ layup deflects least —
but all three AFSI runs sit above the reference band ($+8\,\%$ in $x$, up to
$+18\,\%$ in $y$ for $45^\circ$), which is worth keeping in mind when reading the
comparison figures.

The tip displacement is the quantity the demo is built around, so it is also the
quantity to check against the two things we have: the archived AFSI series at the
other two fibre angles, and the published curves. Table 2 does that, and the trend is
the physically expected one — the stiffer $75^\circ$ layup deflects least — but every
AFSI run sits **above** the reference band, by $8\,\%$ in $x$ and up to $18\,\%$ in
$y$ at $45^\circ$. That offset is a property of the model as configured, not
scatter, and it is worth carrying when reading any comparison figure here.

### Which verification numbers are reproducible, and which are not

The archived probe series was written by the AFSI maintainers and re-running the
$45^\circ$ case reproduces it to $3.7\times10^{-4}$ on a $0.6014$ signal
(§9), so the archived series is trustworthy as a record of *this code*. What cannot
be reconstructed is the mapping from column to angle: the CSV headers are AFSI run
ids (`demo-340-000092/91/90`), and the claim that they are $45^\circ/60^\circ/75^\circ$
in that order lives only in a comment. Treat the angle ordering as unverified.

## 10. Practical notes

What it costs and what to know before repeating it.

| | |
|---|---|
| Steps to $T = 3$ s | $48\,000$ at $\Delta t = 1/16\,000$ |
| Cost | $707$ s on 8 MPI ranks; $\approx 7$ h serial |
| Speed-up from MPI | the fluid solve dominates, and it parallelises cleanly — unlike the 2-D immersed-boundary demos (`demo_339`, `demo_343`, `demo_421`), whose marker map is not MPI-safe, this one was written to run under `mpirun` |
| Output cadence | `fps = 100`, i.e. one frame per $160$ steps; the per-step probe trace used in §9 needs the `PROBE_TRACE` hook added to `main.py` |
| Mesh | `generate_mesh.py` needs `gmsh` (`python-gmsh`); it writes `plot/mesh-340.xdmf`, which `main.py` reads unconditionally |
| Added for this write-up | `OUTPUT_PATH` and `PROBE_TRACE` environment overrides in `main.py` |

Three properties of the shipped code are worth knowing because they silently change
results or block a run:

* **The facet-tag contract is hard-coded** — `find(15)` upper, `find(4)` lower,
  `dxx(11)` / `dxx(1)` for the two leaflet cell tags. Regenerating the mesh with a
  different tag offset misassigns the two materials without any error.
* **`main.py` calls SwanLab unconditionally** at import time, so an offline run needs
  the two entry points stubbed (or the API key/network present); the solve itself does
  not depend on it.
* **`generate_mesh.py` never calls `gmsh.finalize()`**, and several config keys
  (`Nl`, `E_s`, `nu_s`, `pressure_order`) are never read. A commented-out block at the
  end of `main.py` refers to `data/ideal_middle_wall.txt`, which is not in the repo.
