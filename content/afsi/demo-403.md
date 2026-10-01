---
title: "403: Elastic Plate in Cross Flow"
description: "A 3-D elastic plate in cross flow, from the Tuković et al. beam benchmark."
date: 2026-09-12
weight: 403
academic: true
demo_id: demo_403
category: Benchmark
dimension: 3D
solid_model: "Neo-Hookean plate, massless, explicit Euler; clamped base by penalty"
coupling: "immersed boundary (`IBMesh3D`)"
reference: "Tuković et al. (2018) §4.5"
status: Partial
---

## 1. Introduction

Channel flow over a thick elastic plate clamped at its base — the 3-D
beam-in-cross-flow case of Tuković et al. (2018) §4.5, at $\mathrm{Re} = 40$. The
plate is a massless Neo-Hookean solid fixed on its bottom face by a penalty and
advanced by explicit Euler with the velocity interpolated from the fluid. The
published beam-tip time history needs several seconds of simulated time; the
results here are a first look only.

## 2. Problem description

### 2.1 Geometry

{{< figure src="/afsi/demo403-setup.png" title="Figure 1. The channel and the clamped plate." >}}

The fluid box is $150 \times 40 \times 40\,\mathrm{cm}$ with a plate spanning
$x \in [45, 55]$, $y \in [0, 20]$, $z \in [0, 20]\,\mathrm{cm}$; the plate is
clamped along its bottom face.

### 2.2 Governing equations

{{< color "red" >}}TODO: governing equations — incompressible Navier–Stokes, the
plate constitution (Neo-Hookean here; the benchmark's Saint Venant–Kirchhoff form
differs), and the IB coupling terms (see the symbol table page).{{< /color >}}

### 2.3 Boundary and initial conditions

The inlet carries a ramped parabolic profile
$U_m(1-\cos(\pi t/t_{ramp}))/2$ with $t_{ramp} = 4.0\,\mathrm{s}$, then held; the
outlet is at $p = 0$; the side and back walls are no-slip; the two symmetry planes
are enforced only by *not* constraining the transverse components (see §5). The
plate is fixed on its bottom face by the penalty $\beta$.

### 2.4 Physical parameters

<p class="tcaption">Table 1. Parameters. Lengths and material constants are in CGS; SI equivalents are noted where relevant.</p>

| Quantity | Symbol / code name | Value |
|---|---|---|
| Fluid box | `Lx`, `Ly`, `Lz` | $150 \times 40 \times 40\,\mathrm{cm}$ |
| Plate extent | — | $x \in [45, 55]$, $y \in [0, 20]$, $z \in [0, 20]\,\mathrm{cm}$ |
| Density / viscosity | `rho`, `mu` | $1.0\,\mathrm{g\,cm^{-3}}$ / $10.0\,\mathrm{dyn\,s\,cm^{-2}}$ |
| Peak inlet velocity | `Um` | $20.0\,\mathrm{cm\,s^{-1}}$ (SI: $0.2\,\mathrm{m\,s^{-1}}$) |
| Inlet ramp | `ramp_time` | $4.0\,\mathrm{s}$, $U_m(1-\cos(\pi t/t_{ramp}))/2$, then held |
| Reynolds number | — | $40$ (based on plate height) |
| Young's modulus / Poisson | `E_s`, `nu_s` | $1.4\times10^{7}\,\mathrm{dyn\,cm^{-2}}$ / $0.4$ |
| Derived Lamé constants | `mu_s`, `lambda_s` | $5.0\times10^{6}$ / $2.0\times10^{7}$ |
| Base penalty | `beta` | $1\times10^{8}$ |

{{< color "red" >}}TODO: the dimensionless groups of the benchmark (the
plate-height Reynolds number is given; check the benchmark's stiffness
parameterisation).{{< /color >}}

## 3. Numerical setup

The fluid runs on $150 \times 40 \times 40$ hexahedra with a Chorin projection
solver ($\mathrm{P2}$ / $\mathrm{P1}$, force $\mathrm{P2}$),
$\Delta t = 0.001\,\mathrm{s}$ to $T = 6.0\,\mathrm{s}$; the plate mesh is
unstructured ($5 \times 8 \times 8$ tetrahedra before any refinement).

## 4. Results

### 4.1 Quantities of interest

The quantity of interest is the **beam-tip displacement time history**, compared
against the digitised Tuković et al. curves (the benchmark target).

### 4.2 Comparison with reference

{{< color "red" >}}TODO: the beam-tip displacement time history against Tuković et
al. §4.5 — no run reaches the deflected regime yet, so the comparison is
empty.{{< /color >}}

{{< color "red" >}}TODO: figure placeholder — beam-tip displacement against the
published curve.{{< /color >}}

<p class="tcaption">Table 2. Beam-tip displacement against the published reference.</p>

| Quantity | AFSI | Reference (Tuković et al.) | rel. err. |
| --- | --- | --- | --- |
| Beam-tip displacement (steady) |  |  |  |
| Plate period / damping |  |  |  |

### 4.3 Convergence study

{{< color "red" >}}TODO: grid and time-step sensitivity — none exists.{{< /color >}}

### 4.4 Flow and deformation fields

{{< figure src="/afsi/demo403-results.png" title="Figure 2. A short run at $40 \times 16 \times 16$ with the inlet ramp switched off: the plate picks up a displacement of up to $\approx 3$ mm over $0.05$ s (largest away from the clamped base), and the inflow has only reached $x \approx 20$ cm. The published deflection needs seconds of simulated time, which is out of reach at this resolution." >}}

**No beam results exist yet**, so the comparison above has nothing to fill it.

## 5. Discussion and limitations

* The original benchmark uses a Saint Venant–Kirchhoff material; here the plate is
  Neo-Hookean, which is only valid for small strains. The "modified form"
  ($U = 0.3\,\mathrm{m\,s^{-1}}$, $E = 10\,\mathrm{kPa}$) is not the configuration
  used here.
* The symmetry planes are not enforced by Dirichlet conditions — the transverse
  components are simply left free there — which is not equivalent to symmetry.
* The plate is massless and advanced by explicit Euler, with no stability
  discussion; the long-time response is unverified.
* The box spans $z \in [0, 40]$ while the plate spans only $[0, 20]$: the region
  downstream of the plate in $z$ is a doubling of the symmetric half, not an
  independent domain. This should be stated explicitly once the geometry figure
  exists.

## References

{{< color "red" >}}TODO: references — add Tuković et al. (2018) §4.5 and the
original source of the beam case.{{< /color >}}
