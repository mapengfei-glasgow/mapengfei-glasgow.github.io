---
title: "443: Compression Test"
description: "A rectangular elastic block under a central downward traction, following Wells et al. (2023)."
date: 2026-10-01
weight: 443
academic: true
demo_id: demo_443
category: Benchmark
dimension: 2D
solid_model: "neo-Hookean block (plane strain), G = 80.194, κ_stab = 374.239 dyn/cm²"
coupling: "immersed boundary — IB / BS / CBS kernels"
reference: "Wells et al. (2023) configuration"
status: WIP
---

## 1. Introduction

This benchmark is a plane-strain quasi-static problem: a rectangular elastic
block immersed in a fluid is loaded by a central downward traction on its top
surface. It follows the configuration of {{< cite "wells2023nodal" "author" >}}
and is used to compare the element Jacobians and the top-centre displacement of
the IB, BS and CBS kernels, as applied to this case in
{{< cite "li2025local" "author" >}}.

## 2. Problem description

### 2.1 Geometry

{{< color "red" >}}TODO: figure placeholder — the block in its fluid domain with
the loading configuration and structural dimensions, after the source
figure.{{< /color >}}

The computational domain is $40\,\mathrm{cm} \times 40\,\mathrm{cm}$, within
which a block of dimensions $20\,\mathrm{cm} \times 10\,\mathrm{cm}$ is immersed
centrally. A downward traction of magnitude $200\,\mathrm{dyn\,cm^{-1}}$ is
applied to the central $10\,\mathrm{cm}$ of the block's top surface.

### 2.2 Governing equations

{{< color "red" >}}TODO: governing equations — incompressible Navier–Stokes, the
neo-Hookean constitution and the immersed-boundary coupling terms (see the symbol
table page).{{< /color >}}

The structure follows a neo-Hookean material model, with shear modulus
$G = 80.194\,\mathrm{dyn\,cm^{-2}}$ and numerical bulk modulus
$\kappa_{\mathrm{stab}} = 374.239\,\mathrm{dyn\,cm^{-2}}$.

### 2.3 Boundary and initial conditions

The structural boundary conditions are zero vertical displacements along the
bottom boundary and zero horizontal displacements along the top boundary, with
zero traction on all other boundaries. The bottom constraint is enforced by a
penalty,
$\kappa_S = 2.5 \cdot \frac{2.5\,\Delta x}{\Delta t}\,\mathrm{dyn\,cm^{-3}}$.

The traction load increases linearly in time until reaching its full magnitude at
$T_{\mathrm{l}} = 40\,\mathrm{s}$, and the simulation runs to
$T_{\mathrm{f}} = 100\,\mathrm{s}$ so that equilibrium is achieved.

### 2.4 Physical parameters

<p class="tcaption">Table 1. Parameters. Units follow the source (CGS).</p>

| Quantity | Symbol | Value |
|---|---|---|
| Fluid box | — | $40\,\mathrm{cm} \times 40\,\mathrm{cm}$ |
| Block | — | $20\,\mathrm{cm} \times 10\,\mathrm{cm}$, centred |
| Fluid density | $\rho$ | $1.0\,\mathrm{g\,cm^{-3}}$ |
| Fluid viscosity | $\mu$ | $0.16\,\mathrm{dyn\,s\,cm^{-2}}$ |
| Shear modulus | $G$ | $80.194\,\mathrm{dyn\,cm^{-2}}$ |
| Numerical bulk modulus | $\kappa_{\mathrm{stab}}$ | $374.239\,\mathrm{dyn\,cm^{-2}}$ |
| Traction | — | $200\,\mathrm{dyn\,cm^{-1}}$, over the central $10\,\mathrm{cm}$ of the top surface |
| Fixation penalty | $\kappa_S$ | $2.5 \cdot \frac{2.5\,\Delta x}{\Delta t}\,\mathrm{dyn\,cm^{-3}}$ |
| Load time | $T_{\mathrm{l}}$ | $40.0\,\mathrm{s}$ |
| Final time | $T_{\mathrm{f}}$ | $100.0\,\mathrm{s}$ |

{{< color "red" >}}TODO: derived quantities if the case is to be reported
dimensionless.{{< /color >}}

## 3. Numerical setup

The fluid grid uses $N = \left\lceil M \cdot \mathrm{MFAC} \right\rceil$ cells per
direction, where $M = 4, 8, 16, 32, 48$ and $64$ is the number of
$\mathcal{Q}^1$ elements along the longest edge of the Lagrangian mesh, with a
time step of $\Delta t = 0.001\,\Delta x\,\mathrm{s}$. A separate study fixes
$N = 90$ and varies the mesh factor $\mathrm{MFAC}$ from $0.5$ to $1.5$ in steps
of $0.25$.

## 4. Results

### 4.1 Quantities of interest

The quantities of interest are the element Jacobians $J$, which characterise the
volumes of the deformed elements, and the vertical displacement $\Delta Y$ at the
centre of the top surface.

### 4.2 Comparison with reference

{{< color "red" >}}TODO: comparison against the published curves — no runs
yet.{{< /color >}}

<p class="tcaption">Table 2. Probe displacement and Jacobian error against the reference.</p>

| Quantity | AFSI | Reference | rel. err. |
| --- | --- | --- | --- |
| $\Delta Y$ at the top-centre |  |  |  |
| Jacobian error $\lvert J - 1\rvert_2$ |  |  |  |

### 4.3 Convergence study

{{< color "red" >}}TODO: grid convergence over $M$ and the $\mathrm{MFAC}$
study at $N = 90$ — no runs yet.{{< /color >}}

### 4.4 Flow and deformation fields

{{< color "red" >}}TODO: figure placeholders — Jacobian field and displacement
field for the kernel variants.{{< /color >}}

## 5. Discussion and limitations

* The traction acts on the central $10\,\mathrm{cm}$ of the top surface only, so
  the vertical-displacement probe sits under the loaded part; the horizontal
  constraint along the top boundary is what makes the loading a compression.

{{< color "red" >}}TODO: stabilisation effects — whether the isotropic spreads
need modified invariants or volumetric energy for volume conservation while the
CBS spreads do not; fill in from the runs.{{< /color >}}

{{< color "red" >}}TODO: kernel and $\mathrm{MFAC}$ sensitivity of the top-centre
displacement; fill in from the runs.{{< /color >}}

## References

{{< references >}}
