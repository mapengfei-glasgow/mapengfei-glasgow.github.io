---
title: "341: Sphere in a Driven Cubic Cavity"
description: "A sphere carried through a driven cubic cavity, in Navier–Stokes and immersed-boundary FSI."
date: 2026-09-12
weight: 341
academic: true
demo_id: demo_341
category: Application
dimension: 3D
solid_model: "elastic sphere, P = μ_s(F − F⁻ᵀ), μ_s = 0.1 (no volumetric term)"
coupling: "immersed boundary (`IBMesh3D` / `IBInterpolation3D`)"
reference: "— (NS vs FSI cross-comparison on the same cavity)"
status: Partial
---

## 1. Introduction

A sphere is carried through a unit cubic cavity by the flow, first as a pure
Navier–Stokes run and then with the immersed-boundary coupling switched on. The
post-processing samples the three centre lines at $t = 1\,\mathrm{s}$ and compares
NS against FSI across background grid densities — a minimal 3-D counterpart to the
2-D lid-driven disc.

## 2. Problem description

### 2.1 Geometry

{{< figure src="/afsi/demo341-setup.png" title="Figure 1. The cubic cavity and the immersed sphere." >}}

The cavity is the unit cube; the sphere of radius $0.2$ sits at
$(0.6, 0.5, 0.5)$ and spans a quarter of the cavity. The solid mesh is an OCC
sphere with mesh size $0.01$.

### 2.2 Governing equations

{{< color "red" >}}TODO: governing equations — incompressible Navier–Stokes, the
solid law, and the immersed-boundary coupling terms (see the symbol table
page).{{< /color >}}

The solid carries the inline law
$\mathbf{P} = \mu_s(\mathbf{F} - \mathbf{F}^{-\mathrm{T}})$ with
`mu_s` $= 0.1$ and no volumetric term.

### 2.3 Boundary and initial conditions

The cavity is driven by the lid at $y = 1$ with $u_x = 1$; every other face is
no-slip, and the pressure is pinned at the corner $(0,0,0)$. The cavity starts
from rest.

### 2.4 Physical parameters

<p class="tcaption">Table 1. Physical parameters of the cubic-cavity case.</p>

| Quantity | Symbol / code name | Value |
|---|---|---|
| Cavity | `Lx`, `Ly`, `Lz` | $1.0$, $1.0$, $1.0$ |
| Density / viscosity | `rho`, `mu` | $1.0$ / $0.01$ |
| Lid velocity | `UpVelocity` | $u_x = 1.0$ on the lid face ($y = 1$) |
| Pressure pin | — | $p = 0$ at the corner $(0,0,0)$ |
| Sphere centre / radius | `center`, `radius` | $(0.6, 0.5, 0.5)$ / $0.2$ |
| Solid mesh size | `mesh_size` | $0.01$ |
| Solid law | — | $\mathbf{P} = \mu_s(\mathbf{F} - \mathbf{F}^{-\mathrm{T}})$, `mu_s` $= 0.1$ (no volumetric term) |

{{< color "red" >}}TODO: dimensionless numbers and the sphere-to-cavity mass and
stiffness ratios if the case is to be reported dimensionless.{{< /color >}}

## 3. Numerical setup

<p class="tcaption">Table 2. Numerical setup.</p>

| Quantity | Value |
|---|---|
| Fluid grid | $N^3$, default $N = 32$ ($8^3$, $16^3$, $32^3$ recommended) |
| Velocity / force / pressure spaces | $\mathrm{P2}$ / $\mathrm{P2}$ / $\mathrm{P1}$ |
| Time step | $1/200$ |

## 4. Results

### 4.1 Quantities of interest

The quantities of interest are the three centre-line profiles at $t = 1\,\mathrm{s}$
with and without the sphere (the NS vs FSI comparison), the sphere's centroid
travel and maximum nodal displacement, the fluid energy and pressure norms
$u_{L2}$ / $p_{L2}$, and the residual out-of-plane velocity on the $z$-line.

### 4.2 Comparison with reference

{{< figure src="/afsi/demo341-results.png" title="Figure 2. The archived post-processing at $N = 8$ after 20 steps: the three centrelines with and without the sphere." >}}

{{< color "red" >}}TODO: comparison against a body-fitted reference solution on the
same cavity — none exists yet, so NS/FSI agreement is the only comparison
available so far.{{< /color >}}

| Quantity | AFSI | Reference | rel. err. |
| --- | --- | --- | --- |
| Centreline $u_x$ (through sphere) |  |  |  |
| Centreline peak deficit |  |  |  |

### 4.3 Convergence study

{{< color "red" >}}TODO: grid comparison across $8^3 / 16^3 / 32^3$ — only
$N = 16$ was run; no refinement study exists.{{< /color >}}

### 4.4 Flow and deformation fields

A run was made at $N = 16$ for $200$ steps ($t = 1$ s).

{{< figure src="/afsi/demo341-3d-scene.png" title="Figure 3. The $t = 1$ s state. Top left: the cavity boundary coloured by speed — the lid at $y = 1$ carries $\lvert u\rvert = 1$, the four side walls the return flow and the floor none. Top right: the octant mesh and the immersed sphere, which spans a quarter of the cavity. Bottom left: streamlines seeded on a disc just upstream of the sphere; they wrap round its shoulder and rejoin the primary vortex. Bottom right: the tetrahedral sphere coloured by nodal displacement." >}}

{{< figure src="/afsi/demo341-trajectory.png" title="Figure 4. The sphere over the run. It starts at $(0.6, 0.5, 0.5)$ and drifts to $(0.528, 0.492, 0.500)$ — 0.073 m, or 0.37 radii — while its nodes move up to $0.107$, more than half a radius, so the sphere is being carried and deformed rather than simply translated. The drift is in $-x$, opposite the lid motion, which is the return branch of the primary vortex." >}}

{{< figure src="/afsi/demo341-centerlines.png" title="Figure 5. The three centreline profiles at $t = 1$ s. The shaded band is the sphere's span; markers inside it are the nodes the immersed boundary overwrites, which is why they must be excluded before comparing with a body-fitted reference." >}}

<p class="tcaption">Table 3. The run at $N = 16$.</p>

| Quantity | Value |
|---|---|
| $u_{L2}$ | $0 \to 0.0411$, still growing at $t = 1$ s (the cavity takes several seconds to reach its steady state) |
| $p_{L2}$ | settles at $5.6\times10^{-3}$ after $t \approx 0.4$ s |
| Boundary speeds | lid mean $0.78$ (perturbed near the sphere), floor $1.6\times10^{-18}$ |
| Sphere | centroid travel $0.073$, $\max\lvert u_s\rvert = 0.107$ against a radius of $0.2$ |
| $u_z$ on the $z$-line | $\le 2.5\times10^{-3}$ — the flow stays essentially two-component in the mid-planes |

The sphere reaches only $t = 1$ s, so the wake is still developing — Figure 5 is
the $t = 1$ s state the post-processing is written for.

## 5. Discussion and limitations

* The immersed boundary overwrites the fluid nodes it covers, so those markers
  must be excluded before any comparison with a body-fitted reference.
* The sphere carries no volumetric term, so it is effectively
  incompressibility-free; adding one would change the deformation results.

## References

{{< color "red" >}}TODO: references — none cited yet; add a 3-D lid-driven-cavity
reference if the mid-plane profiles are compared against one.{{< /color >}}
