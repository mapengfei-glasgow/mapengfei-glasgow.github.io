---
title: "demo_401 — sperm-cell solid geometry (3-D)"
description: "demo_401: gmsh OpenCASCADE construction of a sperm cell (sphere head plus a three-segment flagellum) with physical surface groups, converted to a dolfinx mesh for immersed-boundary FSI."
date: 2026-09-12
weight: 401
academic: true
---

## 1. What it is

A **pre-processing only** demo: it builds the Lagrangian solid geometry of a
swimming sperm cell — a spherical head with a three-segment flagellum — classifies
its exterior surfaces into physical groups, and converts the gmsh mesh into an
XDMF file that AFSI can read. There is no fluid mesh, no coupling and no time
loop here; the readme points at [demo_400](/afsi/demo_400/) and
[demo_421](/afsi/demo_421/) for the coupled runs.

The interesting part is the construction: the sphere and the three coaxial
cylinders are combined with `occ.fragment`, so the segment interfaces stay
conformal and each lateral surface can be tagged separately.

{{< figure src="/afsi/demo401-setup.png" title="Figure 1. The solid geometry and its physical groups, drawn to scale from `a.py`." >}}

## 2. Configuration

<p class="tcaption">Table 1. Geometry and mesh parameters (`a.py`). The body is a single volume, tag $1$.</p>

| Quantity | Code name | Value |
|---|---|---|
| Head radius | `R` | $0.05$ |
| Flagellum radius | `r` | $0.01$ |
| Segment lengths | `L1`, `L2`, `L3` | $0.01$ (neck), $0.08$ (mid), $0.21$ (long tail) |
| Chain origin | `x0` $= \sqrt{R^2-r^2}$ | $0.0489898$ |
| Tip position | — | $x = 0.3489898$ |
| Head-region mesh size | `ms_h` | $0.005$ (gmsh `Box` field, $V_{in}$) |
| Flagellum mesh size | `ms_t` | $0.008$ (background, $V_{out}$) |
| Surface groups | `HEAD` / `TIP` / laterals | $15$ / $16$ / $17$, $18$, $19$ |
| Volume group | — | $1$ |

No constitutive law, fluid property, time step or boundary condition exists in
this directory, and there are **no environment overrides**.

## 3. Files

| File | Role |
|---|---|
| `a.py` | gmsh OCC construction (sphere + three cylinders, `occ.fragment`), topological classification of the exterior surfaces into groups $15$–$19$, mesh sizing, `mesh.generate(3)` → `sperm3d.msh` |
| `generate_mesh.py` | Reads `sperm3d.msh` with `read_from_msh(gdim=3)` and writes `sperm-2.xdmf`/`.h5` with cell and facet tags |
| `sperm3d.msh` | Shipped gmsh mesh: $3104$ nodes, $17\,158$ elements, tags $15/16/17/18/19$ plus volume $1$ |
| `sperm3d.geo` | Legacy CSG file describing a *different* (centimetre-scale, differently oriented) sperm; not read by any script |
| `readme.md` | Geometry table, physical tags, file list, run commands, pointer to the coupled demos |

## 4. Running it

```bash
cd afsic/demo/demo_401
python a.py                # gmsh geometry + mesh -> sperm3d.msh
python generate_mesh.py    # sperm3d.msh -> sperm-2.xdmf/.h5
```

## 5. Results and notes

{{< figure src="/afsi/demo401-mesh.png" title="Figure 2. The mesh that `a.py` writes: mid-plane nodes of the generated solid and the node distribution around the body axis." >}}

There is nothing to measure yet: no solver runs, no results, and the readme's
only figure is an external URL. The stored mesh itself reports $3104$ nodes and
$17\,158$ elements ($2986$ triangles + $14\,172$ tetrahedra).

Caveats:

* `generate_mesh.py` imports `from dolfinx.io import gmshio`, which no longer
  exists in dolfinx 0.10 — the same line's comment already records the fix
  (`from dolfinx.io import gmsh as gmshio`), so the script fails as shipped.
* The element records in the shipped `sperm3d.msh` do not follow the MSH 4.1
  layout (no element-type or tag columns, too few tokens per record), so whether
  gmsh/dolfinx can read that file is unclear; regenerating it with `a.py` is the
  safe route.
* The readme lists `sperm-1.xdmf/.h5` among the files, but no script produces it
  and it is not present.
* `sperm3d.geo` is stale and inconsistent with `a.py` (different scale, a
  different arrangement of the segments, illustrative material densities) — it
  should be treated as superseded.
* The flagellum is resolved by only about $2.5$ elements across its diameter
  ($2r = 0.02$ against `ms_t` $= 0.008$), which is marginal for an immersed
  boundary; the sources do not comment on this.
* The surface classification is heuristic: exterior facets are found by adjacency
  and bounding boxes with a tolerance of $10^{-6}$, and the tip is the surface
  with a vanishing $x$-extent.
