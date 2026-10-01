---
title: "337: Idealised Left Ventricle"
description: "A passively loaded left ventricle, compared against pulse-fenicsx and IBAMR."
date: 2026-09-12
weight: 337
academic: true
demo_id: demo_337
category: Application
dimension: 3D
solid_model: "neo-Hookean wall (E = 10⁴, ν = 0.3)"
coupling: "immersed boundary (`IBMesh3D` / `IBInterpolation3D`) + base-ring penalty"
reference: "pulse-fenicsx and IBAMR displacements"
status: Partial
---

## 1. Introduction

A passive left-ventricle ellipsoid is immersed in a $5 \times 5 \times 5$ fluid
box and loaded by a physiological endocardial pressure waveform. The wall is a
neo-Hookean solid whose internal force is spread back onto the fluid through
`IBMesh3D`/`IBInterpolation3D`, and a penalty on the base ring restrains the valve
plane. The case is set up to compare AFSI's mid-wall displacement against
`pulse-fenicsx` and IBAMR.

## 2. Problem description

### 2.1 Geometry

{{< figure src="/afsi/demo337-setup.png" title="Figure 1. The idealised ventricle: endocardial and epicardial ellipsoids, the penalty-held base ring, and the endocardial pressure load." >}}

The ventricle is an ellipsoid pair (endocardium and epicardium) standing in the
box, with semi-axes $r_{\text{short}} = 7.0$ / $10.0$ and
$r_{\text{long}} = 17.0$ / $20.0$; the base ring is held by a penalty.

### 2.2 Governing equations

{{< color "red" >}}TODO: governing equations — incompressible Navier–Stokes, the neo-Hookean wall constitution, the endocardial pressure traction and the IB coupling terms (see the symbol table page).{{< /color >}}

### 2.3 Boundary and initial conditions

The endocardium carries the physiological pressure waveform
($8\,\mathrm{mmHg}$ diastolic, $110\,\mathrm{mmHg}$ systolic); the base ring is
restrained by the penalty.

### 2.4 Physical parameters

<p class="tcaption">Table 1. Main parameters.</p>

| Quantity | Symbol / code name | Value |
|---|---|---|
| Fluid box | `Lx`, `Ly`, `Lz` | $5.0$, $5.0$, $5.0$ |
| Fluid density / viscosity | `rho`, `mu` | $1.0$ / $0.01$ |
| Solid model | `NeoHookeanMaterial` | $E = 1.0\times10^{4}$, $\nu = 0.3$ (the config's `mu_s` $= 0.1$ is **not** used) |
| Base-ring penalty | `beta` | $5\times10^{6}$ |
| Endocardial pressure | `diastole_pressure`, `systole_pressure` | $8\,\mathrm{mmHg}$ / $110\,\mathrm{mmHg}$ |
| LV mesh radii | `r_short_endo` … | $7.0$ / $10.0$ short, $17.0$ / $20.0$ long |

{{< color "red" >}}TODO: dimensionless numbers and the physiological scaling (cycle time, Reynolds number) if the case is to be reported as a model problem.{{< /color >}}

## 3. Numerical setup

{{< color "red" >}}TODO: numerical setup — mesh, time step and solver details (the run matrix this page should report).{{< /color >}}

## 4. Results

### 4.1 Quantities of interest

The quantities of interest are the mid-wall displacement at end-diastole and
end-systole, compared against the `pulse-fenicsx` and IBAMR reference series
($58$ rows each), and the parallel scaling of the solver at fixed problem size on
the $32^3$ and $64^3$ grids.

### 4.2 Comparison with the reference solvers

{{< figure src="/afsi/demo337-results.png" title="Figure 2. Archived data: strong scaling on the $32^3$ and $64^3$ grids, and the end-diastolic mid-wall line against the `pulse-fenicsx` reference." >}}

The archived reference series are the four $58$-row displacement files and the
end-diastolic mid-wall location. The intended comparison figures (diastole and
systole) do not exist yet, and neither does the $58$-row AFSI displacement for
the systole case — the quantitative comparison is therefore incomplete.

{{< color "red" >}}TODO: the comparison table against Land et al. (2015) Problem 2 and against pulse-fenicsx / IBAMR — apex displacement and end-face positions, mean and amplitude per cycle.{{< /color >}}

| Quantity | AFSI | Reference | rel. err. |
| --- | --- | --- | --- |
| Apex displacement (diastole) |  |  |  |
| Apex displacement (systole) |  |  |  |
| End-face position (diastole) |  |  |  |
| End-face position (systole) |  |  |  |

### 4.3 Convergence study

{{< color "red" >}}TODO: grid and time-step sensitivity — only strong scaling at fixed problem size was recorded; no refinement study exists.{{< /color >}}

### 4.4 Parallel scaling

| Grid | Processes | Speed-up |
|---|---|---|
| $32^3$ | $1 \to 160$ | $21.1$ |
| $64^3$ | $1 \to 160$ | $50.1$ |

No field figures are archived for this demo.

{{< color "red" >}}TODO: field figures — end-diastolic and end-systolic displacement fields.{{< /color >}}

## 5. Discussion and limitations

* The solid uses $E = 10^{4}$, $\nu = 0.3$ with no fibre families or active
  contraction; fibre-reinforced and active variants exist but are not covered by
  this page.
* The applied pressure is the systolic ramp only for
  $t < t_{cycle} = 0.8\,\mathrm{s}$, so within the simulated window
  ($T = 0.1\,\mathrm{s}$) the $8\,\mathrm{mmHg}$ diastolic load does not enter the
  value applied.

{{< color "red" >}}TODO: whether the loaded period reproduces the physiological
cycle (and what the comparable literature setup is) is unclear — fill in once the
comparison data exists.{{< /color >}}

## References

{{< color "red" >}}TODO: references — add Land et al. (2015) Problem 2 and the pulse-fenicsx source.{{< /color >}}
