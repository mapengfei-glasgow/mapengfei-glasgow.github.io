---
title: "401: Sperm-Cell Solid Geometry"
description: "gmsh construction of a sperm-cell solid (head plus a three-segment flagellum) and its XDMF conversion."
date: 2026-09-12
weight: 401
academic: true
demo_id: demo_401
category: Utility
dimension: 3D
solid_model: "geometry only — no constitutive law on this page"
coupling: "none (pre-processing for the coupled runs of demo_400 / demo_421)"
reference: "—"
status: Verified
---

## 1. Introduction

This page documents the Lagrangian solid geometry of a swimming sperm cell — a
spherical head with a three-segment flagellum — whose exterior surfaces are
classified into physical groups for the coupled simulations of
[demo_400](/afsi/demo_400/) and [demo_421](/afsi/demo_421/). There is no fluid
mesh, no coupling and no time loop here; the construction is the interesting part:
the sphere and the three coaxial cylinders are combined with `occ.fragment`, so the
segment interfaces stay conformal and each lateral surface can be tagged
separately.

## 2. Problem description

### 2.1 Geometry

The body is a single volume (tag $1$) made of a spherical head of radius $R$ and a
three-segment flagellum of radius $r$, chained along the axis from the head; the
surface groups are the head face, the tip face and the three lateral surfaces,
separated by the fragment interfaces.

{{< figure src="/afsi/demo401-setup.png" title="Figure 1. The solid geometry and its physical groups, drawn to scale." >}}

### 2.2 Governing equations

Not applicable — geometry and mesh only. The constitutive law and coupling are
defined by the coupled cases ([demo_400](/afsi/demo_400/),
[demo_421](/afsi/demo_421/)).

### 2.3 Boundary and initial conditions

Not applicable — the page contains no solver.

### 2.4 Physical parameters

<p class="tcaption">Table 1. Geometry and mesh parameters. The body is a single volume, tag $1$.</p>

| Quantity | Symbol / code name | Value |
|---|---|---|
| Head radius | `R` | $0.05$ |
| Flagellum radius | `r` | $0.01$ |
| Segment lengths | `L1`, `L2`, `L3` | $0.01$ (neck), $0.08$ (mid), $0.21$ (long tail) |
| Chain origin | `x0` $= \sqrt{R^2-r^2}$ | $0.0489898$ |
| Tip position | — | $x = 0.3489898$ |
| Head-region mesh size | `ms_h` | $0.005$ |
| Flagellum mesh size | `ms_t` | $0.008$ |

## 3. Numerical setup

The mesh is generated in two sizing regions (head and flagellum), with the
exterior surfaces classified by adjacency into the head face, the tip face and the
three lateral surfaces. The mesh reports $3104$ nodes and $17\,158$ elements
($2986$ triangles + $14\,172$ tetrahedra). The flagellum is resolved by only about
$2.5$ elements across its diameter ($2r = 0.02$ against `ms_t` $= 0.008$), which
is marginal for an immersed boundary.

{{< figure src="/afsi/demo401-mesh.png" title="Figure 2. The generated mesh: mid-plane nodes of the solid and the node distribution around the body axis." >}}

## 4. Results

### 4.1 Quantities of interest

This is a pre-processing utility — the quantities of interest (swimming speed,
trajectory) live in the coupled demos.

### 4.2 Comparison with reference

{{< color "red" >}}TODO: compare the geometry against the original DFIBMFoam
sperm-cell geometry, if such a reference exists.{{< /color >}}

### 4.3 Convergence study

{{< color "red" >}}TODO: mesh refinement of the flagellum (currently ~2.5
elements across its diameter) — not studied.{{< /color >}}

### 4.4 Fields

Not applicable — geometry and mesh only.

## 5. Discussion and limitations

* The flagellum resolution is marginal for an immersed boundary; the effect of
  refining it on the coupled runs is unknown.

{{< color "red" >}}TODO: the segmentation of the flagellum (three segments of
different lengths) suggests a model with distributed stiffness or a beating
pattern — document the intended mechanics or remove the segmentation.{{< /color >}}

## References

{{< color "red" >}}TODO: references — add the DFIBMFoam sperm-cell case the
geometry is modelled on.{{< /color >}}
