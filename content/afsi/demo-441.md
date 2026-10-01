---
title: "441: Cook's Membrane"
description: "Cook's membrane — the classical plane-strain benchmark, in a modified 13 cm square domain."
date: 2026-10-01
weight: 441
academic: true
demo_id: demo_441
category: Benchmark
dimension: 2D
solid_model: "neo-Hookean block (plane strain), G = 83.333, κ_stab = 388.889 dyn/cm²"
coupling: "immersed boundary — IB / BS / CBS kernels"
reference: "Wells et al. (2023) configuration"
status: WIP
---

## 1. Introduction

Cook's membrane is a classical plane-strain benchmark for incompressible
elasticity: a block held on one side and loaded by a traction on the other, whose
corner displacement and element volumes probe an elasticity solver's robustness.
The configuration follows {{< cite "wells2023nodal" "author" >}}, with the
computational domain enlarged from the original
$10\,\mathrm{cm} \times 10\,\mathrm{cm}$ to
$13\,\mathrm{cm} \times 13\,\mathrm{cm}$ so that the grid resolution stays
integral during mesh-convergence studies. The kernels compared are the
isotropic IB and BS spreads and the divergence-free composite B-spline (CBS)
spreads of {{< cite "gruninger2024local" "author" >}}, as applied to this case in
{{< cite "li2025local" "author" >}}.

## 2. Problem description

### 2.1 Geometry

The computational domain is a $13\,\mathrm{cm} \times 13\,\mathrm{cm}$ square
filled with fluid, with the block immersed in it. The block's left side is held
fixed and its right side carries the load; the vertical displacement
$\Delta Y$ is monitored at the upper-right corner of the membrane, at
$(8.05\,\mathrm{cm},\, 9.5\,\mathrm{cm})$.

{{< color "red" >}}TODO: figure placeholder — annotated geometry (structural
dimensions, the fixed left edge and the loaded right side), after the source
figure.{{< /color >}}

### 2.2 Governing equations

{{< color "red" >}}TODO: governing equations — incompressible Navier–Stokes, the
neo-Hookean constitution, the immersed-boundary coupling and the composite
B-spline interpolation (see the symbol table page).{{< /color >}}

The solid is neo-Hookean, with shear modulus
$G = 83.333\,\mathrm{dyn\,cm^{-2}}$ and numerical bulk modulus
$\kappa_{\mathrm{stab}} = 388.889\,\mathrm{dyn\,cm^{-2}}$.

### 2.3 Boundary and initial conditions

The left side of the block is fixed by a penalty,
$\kappa_S = 0.125\,\frac{\Delta x}{\Delta t}\,\mathrm{dyn\,cm^{-3}}$; an upward
traction of density $6.25\,\mathrm{dyn\,cm^{-1}}$ is applied to the right side;
all other structural boundaries are stress free, and the fluid is at rest with
zero velocity enforced on $\partial\Omega$. The traction ramps linearly in time,
reaching its full magnitude at $T_{\mathrm{l}} = 20\,\mathrm{s}$, and the
simulation runs to $T_{\mathrm{f}} = 50\,\mathrm{s}$ so that the configuration
settles.

### 2.4 Physical parameters

<p class="tcaption">Table 1. Parameters. Units follow the source (CGS).</p>

| Quantity | Symbol | Value |
|---|---|---|
| Fluid density | $\rho$ | $1.0\,\mathrm{g\,cm^{-3}}$ |
| Fluid viscosity | $\mu$ | $0.16\,\mathrm{dyn\,s\,cm^{-2}}$ |
| Material model | — | neo-Hookean |
| Shear modulus | $G$ | $83.333\,\mathrm{dyn\,cm^{-2}}$ |
| Numerical bulk modulus | $\kappa_{\mathrm{stab}}$ | $388.889\,\mathrm{dyn\,cm^{-2}}$ |
| Traction density | — | $6.25\,\mathrm{dyn\,cm^{-1}}$, on the right side |
| Fixation penalty | $\kappa_S$ | $0.125\,\frac{\Delta x}{\Delta t}\,\mathrm{dyn\,cm^{-3}}$ |
| Load time | $T_{\mathrm{l}}$ | $20.0\,\mathrm{s}$ |
| Final time | $T_{\mathrm{f}}$ | $50.0\,\mathrm{s}$ |

{{< color "red" >}}TODO: derived quantities if the case is to be reported
dimensionless.{{< /color >}}

## 3. Numerical setup

The solid mesh carries $M = 4, 8, 16, 32, 48$ and $64$ $\mathcal{Q}^1$ elements
per edge; the fluid grid uses
$N = \left\lceil M \cdot \mathrm{MFAC} \cdot \frac{10}{6.5} \right\rceil$ cells in
each coordinate direction, where the factor $\frac{10}{6.5}$ accounts for the
ratio between the computational domain length and the structure's longest side.
Mesh factors $\mathrm{MFAC} = 0.5, 0.75, 1.0, 1.25$ and $1.5$ are used, with a
time step of $\Delta t = 0.001\,\Delta x\,\mathrm{s}$.

## 4. Results

### 4.1 Quantities of interest

The quantities of interest are the element Jacobians $J$, which characterise the
volumes of the deformed elements, and the vertical displacement $\Delta Y$ at the
membrane's upper-right corner.

### 4.2 Comparison with reference

{{< color "red" >}}TODO: comparison against the published curves — no runs
yet.{{< /color >}}

<p class="tcaption">Table 2. Probe displacement and Jacobian range against the reference.</p>

| Quantity | AFSI | Reference | rel. err. |
| --- | --- | --- | --- |
| $\Delta Y$ at $(8.05, 9.5)\,\mathrm{cm}$ |  |  |  |
| $\min J$ / $\max J$ |  |  |  |

### 4.3 Convergence study

{{< color "red" >}}TODO: grid convergence over $M$ and $\mathrm{MFAC}$ — no runs
yet.{{< /color >}}

### 4.4 Flow and deformation fields

{{< color "red" >}}TODO: figure placeholders — Jacobian field and displacement
field for the kernel variants.{{< /color >}}

## 5. Discussion and limitations

* The $13\,\mathrm{cm}$ domain differs from the original $10\,\mathrm{cm}$
  benchmark, so published tip-displacement values are not directly comparable.
* The case is plane strain: the constraints that make it so should be stated once
  the configuration is finalised.

{{< color "red" >}}TODO: kernel sensitivity — whether the isotropic spreads need
volumetric energy or modified invariants for volume conservation while the CBS
spreads do not; quantify once the runs exist.{{< /color >}}

{{< color "red" >}}TODO: complete the geometry and load description once the
figure exists (structural dimensions, traction extent).{{< /color >}}

## References

{{< references >}}
