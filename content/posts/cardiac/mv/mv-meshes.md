---
title: "Mitral-valve meshes, refinement and mesh factors"
description: "Solid mesh construction, refinement and anatomical MFAC tables for G64, G128 and G256."
date: 2026-10-15
layout: protected-paper
academic: true
comments: false
searchHidden: true
build:
  list: never
tags: ["GPU", "FSI"]
url: /posts/mv-meshes/
area: "research"
readingRoute: "mitral-valve"
areas: ["Cardiac Simulation"]
noteType: "Methods"
projects: ["Mitral Valve"]
---

Companion note to [the mitral-valve FSI working paper]({{< relref "mv-paper.md" >}}).
This page collects mesh construction and refinement details previously in Sections 2.2–2.3 of the paper.
The measured MFAC tables below cover the **mixed Q1-hexahedron/P1-tetrahedron** mesh sequence R0/R1/R2.
They are reference-configuration statistics, not measurements of the moving mesh.

## 1. Components, mesh levels and element order

Independent immersed solid components may overlap and couple through the same Eulerian fluid.
Geometric coincidence is not a reason to weld nodes or force matching faces between independent components.
Within an individual FE component, its intended connectivity and displacement compatibility still matter.
The current generators preserve existing node-ID sharing and never merge nodes by coordinate proximity;
the anatomical marker groups in the tables do not themselves define or certify mechanical connectivity.

- **R0:** original solid discretisation.
- **R1:** one uniform subdivision; each Q1 hex becomes eight Q1 hexes, each P1 tet becomes eight P1 tets.
- **R2:** repeat the subdivision on R1; each original R0 element has 64 descendants.
- **P1 → P2 / Q1 → Q2:** raise interpolation order and add nodes; this is separate from R0 → R1 → R2 subdivision.

Thus R0/P2 has the original tetrahedral cell count with additional edge nodes;
R1/P1 has more linear cells. The MFAC tables for Q1/P1 must not be reused unmodified for P2/Q2 marker sets.

## 2. Eulerian grids

The domain is $8.6\times8.6\times16.2$ cm. The grids are anisotropic:
$h_x=h_y=8.6/N$ and $h_z=16.2/(3N/2)$.

| Grid | Dimensions | Fluid cells | $h_x=h_y$ (cm) | $h_z$ (cm) | Time step used in these experiments |
|:---|:---|---:|---:|---:|:---|
| G64 | 64 × 64 × 96 | 393,216 | 0.134375 | 0.168750 | $2\times10^{-5}$ s |
| G128 | 128 × 128 × 192 | 3,145,728 | 0.0671875 | 0.084375 | $1\times10^{-5}$ s |
| G256 | 256 × 256 × 384 | 25,165,824 | 0.03359375 | 0.0421875 | Not established here |

These are the selected study grids; this table does not claim that the solver only supports powers of two.
The G256 MFAC entries below are calculated from grid dimensions, not evidence of completed G256 simulations.
The IBAMR reference uses 44 × 44 × 80 cells, with spacings approximately 0.195455 and 0.2025 cm.

The G128 experiments use `solid-nu=125`, following the existing runbook stability guidance;
the G64 runs use `solid-nu=1000`. Grid, time step and numerical solid viscosity therefore change together.
Their comparison does not isolate the Eulerian-grid effect.

## 3. Solid mesh inventory

The mixed R0 mesh comes from `MV_only_hex.xda`: 11,567 HEX8 + 10,686 TET4 entries,
with two duplicate hex elements removed. Hexes remain hexes.

| Mesh | Data directory | Nodes / IB markers | Q1 hexes | P1 tets | Reference volume (cm³) |
|:---|:---|---:|---:|---:|---:|
| R0/P1+Q1 | `glamv_hex` | 29,524 | 11,565 | 10,686 | 90.777886374 |
| R1/P1+Q1 | `glamv_hex_r1` | 169,094 | 92,520 | 85,488 | 90.777923873 |
| R2/P1+Q1 | `glamv_hex_r2` | 1,098,199 | 740,160 | 683,904 | 90.777933247 |

Other meshes used in the paper:

| Mesh | Data directory | Nodes | Cells | Reference volume (cm³) |
|:---|:---|---:|:---|---:|
| R0/P1 | `glamv_ibamr` | 29,524 | 80,074 P1 tets | 90.777675137 |
| R0/P2 | `glamv_ibamr_p2v` | 169,923 | 80,074 P2 tets | 90.777675137 |
| R0/Q2+P2 | `glamv_hex_q2p2` | 169,094 | 11,565 Q2 hexes + 10,686 P2 tets | ≈90.777953 |

`glamv_ibamr_refined` refines **only the tube and housing disc**. It is not an all-structure R1 mesh.
The older whole-solid `glamv_gmshref` has recorded degenerate chordae children and is not the mixed R1/R2 sequence tabulated here.

## 4. Refinement and data transfer

For a hex, add shared edge midpoints, face centres and a cell centre, then form a 2 × 2 × 2 set of children.
For a tet, add six edge midpoints, form four corner tets, and split the central octahedron into four more tets.
The existing mixed generator uses a fixed central-octahedron diagonal; it does not optimise child quality.
Material markers, fibre/sheet/normal frames, tether kinds and target-displacement vectors are inherited from parents.
This is piecewise inheritance of the existing material field, not a newly reconstructed anatomical fibre map.

R1 is produced by `gen_glamv_hex.py --refine`. R2 is produced by `gen_glamv_hex_r2.py` from the existing R1 binary data.
R2 records `parent_cell.bin` (R1 parent) and `parent_elem.bin` (original XDA element).
Each R1 parent has exactly eight R2 children; marker, frame and tether inheritance were checked against the parents.

### Legacy hex/tet interface treatment

The R1 generator identifies 29 original quadrilateral hex faces adjacent to two tet triangles by node IDs.
It uses the tet-diagonal midpoint as the hex face-centre node. R2 retains this rule when refining R1.
This is a legacy connectivity choice, not an IB requirement between independent overlapping components.
Sharing interface nodes alone does not establish full interpolation compatibility between hex and tet faces.

This rule can perturb geometry. R1's total volume is 90.777923873 cm³ and R2's is 90.777933247 cm³;
58 R1 parents have aggregate child-volume changes above a relative tolerance of $10^{-9}$,
with a maximum relative change of **5.3224%**. The total change is small, but the local change is not negligible.
These meshes support an exploratory refinement comparison, not a strictly geometry-preserving convergence claim.
The Q2/P2 conversion also uses this interface rule: its maximum cell-volume change relative to Q1/P1 is about 0.546%.

For Q1/P1, the solver uses 2 × 2 × 2 Gauss quadrature for hexes and one centroid point for tets.
Tets occupy the first four basis slots in the mixed eight-slot layout; unused quadrature weights are zero.
Q2/P2 uses a different basis/quadrature layout (27-node hexes and 10-node tets).

## 5. MFAC definition and sampling convention

For each anatomical marker group, define $\Delta s$ as the **median reference edge length**:
12 topological edges for every Q1 hex and six for every P1 tet. Shared edges are counted once per incident cell,
matching the earlier paper's edge-sampling convention. Hex face/body diagonals and padded tet entries are excluded.
This is a descriptive marker-spacing proxy, not a bound on every marker separation or a local element-quality measure.

Report both ratios because the fluid grid is anisotropic:

$$\mathrm{MFAC}_{xy}=\frac{\Delta s}{h_x},\qquad
\mathrm{MFAC}_{z}=\frac{\Delta s}{h_z}.$$

Both use the same Euclidean edge statistic; they are not edge projections along each coordinate axis.
Each MFAC table cell below is **MFACₓᵧ / MFAC_z**. All nine grid/refinement combinations are calculated from measured meshes,
not obtained by assuming that a group's median halves exactly at every refinement.
New internal edges and anisotropic parent elements can change the edge-length distribution.

The machine-readable files also include the **unique-topological-edge median**, using unordered node-ID pairs.
That alternative weights shared edges differently and can give substantially different results for slender chordae.
Nodes are never deduplicated by physical coordinate coincidence.

### Anatomical groups

| Group | Cell markers |
|:---|:---|
| Tube | 1 |
| Housing disc | 42 |
| AML | 3, 5, 7, 23, 25 |
| PML | 4, 24 |
| Annulus | 4099, 5099 |
| Basal chordae | 100, 300 |
| Marginal chordae | 200 |
| Papillary caps | 1001–1005, 2001–2005 |
| Cap 2001 | 2001; a subset of papillary caps |

The first eight groups partition the cells. Cap 2001 is shown separately for the compression diagnosis and must not be added to totals again.
Node counts within groups can overlap when the input uses shared node IDs.

### Measured edge-length distributions

Lengths are in cm; P10/P90 are percentiles of the same cell-edge samples used for the median.

| Mesh | Group | Nodes | Hexes | Tets | P10 edge | Median edge $\Delta s$ | P90 edge |
|:---|:---|---:|---:|---:|---:|---:|---:|
| R0 | Tube | 16,848 | 8,320 | 0 | 0.200000 | 0.218376 | 0.230263 |
| R0 | Housing disc | 3,773 | 0 | 10,650 | 0.133716 | 0.169422 | 0.210762 |
| R0 | AML | 2,054 | 963 | 14 | 0.071595 | 0.094641 | 0.117991 |
| R0 | PML | 1,728 | 780 | 18 | 0.067699 | 0.090146 | 0.112626 |
| R0 | Annulus | 526 | 129 | 4 | 0.082583 | 0.099972 | 0.113799 |
| R0 | Basal chordae | 4,817 | 1,237 | 0 | 0.039391 | 0.044204 | 0.099685 |
| R0 | Marginal chordae | 420 | 106 | 0 | 0.038465 | 0.053302 | 0.100022 |
| R0 | Papillary caps | 220 | 30 | 0 | 0.039254 | 0.040160 | 0.127636 |
| R0 | Cap 2001 (subset) | 8 | 1 | 0 | 0.040000 | 0.040011 | 0.067583 |
| R1 | Tube | 100,464 | 66,560 | 0 | 0.100000 | 0.109188 | 0.115131 |
| R1 | Housing disc | 21,943 | 0 | 85,200 | 0.067220 | 0.085598 | 0.109351 |
| R1 | AML | 11,951 | 7,704 | 112 | 0.035902 | 0.047331 | 0.058727 |
| R1 | PML | 9,879 | 6,240 | 144 | 0.034114 | 0.044999 | 0.055930 |
| R1 | Annulus | 2,358 | 1,032 | 32 | 0.041606 | 0.050012 | 0.056742 |
| R1 | Basal chordae | 22,139 | 9,896 | 0 | 0.019726 | 0.022943 | 0.049769 |
| R1 | Marginal chordae | 1,915 | 848 | 0 | 0.018974 | 0.026422 | 0.049865 |
| R1 | Papillary caps | 790 | 240 | 0 | 0.019545 | 0.020087 | 0.063816 |
| R1 | Cap 2001 (subset) | 27 | 8 | 0 | 0.020000 | 0.020005 | 0.033791 |
| R2 | Tube | 667,680 | 532,480 | 0 | 0.050000 | 0.054594 | 0.057546 |
| R2 | Housing disc | 144,074 | 0 | 681,600 | 0.033663 | 0.042898 | 0.055343 |
| R2 | AML | 78,445 | 61,632 | 896 | 0.017965 | 0.023645 | 0.029327 |
| R2 | PML | 64,245 | 49,920 | 1,152 | 0.017078 | 0.022492 | 0.027917 |
| R2 | Annulus | 13,055 | 8,256 | 256 | 0.020755 | 0.024986 | 0.028359 |
| R2 | Basal chordae | 123,761 | 79,168 | 0 | 0.009866 | 0.011505 | 0.024876 |
| R2 | Marginal chordae | 10,653 | 6,784 | 0 | 0.009478 | 0.013247 | 0.024898 |
| R2 | Papillary caps | 3,730 | 1,920 | 0 | 0.009802 | 0.010043 | 0.031799 |
| R2 | Cap 2001 (subset) | 125 | 64 | 0 | 0.010000 | 0.010003 | 0.016896 |

### R0: MFAC for all three Eulerian grids

Every entry is **MFACₓᵧ / MFAC_z**.

| Group | G64 | G128 | G256 |
|:---|---:|---:|---:|
| Tube | 1.6251 / 1.2941 | 3.2502 / 2.5882 | 6.5005 / 5.1763 |
| Housing disc | 1.2608 / 1.0040 | 2.5216 / 2.0080 | 5.0433 / 4.0159 |
| AML | 0.7043 / 0.5608 | 1.4086 / 1.1217 | 2.8172 / 2.2433 |
| PML | 0.6709 / 0.5342 | 1.3417 / 1.0684 | 2.6834 / 2.1368 |
| Annulus | 0.7440 / 0.5924 | 1.4879 / 1.1848 | 2.9759 / 2.3697 |
| Basal chordae | 0.3290 / 0.2619 | 0.6579 / 0.5239 | 1.3158 / 1.0478 |
| Marginal chordae | 0.3967 / 0.3159 | 0.7933 / 0.6317 | 1.5867 / 1.2635 |
| Papillary caps | 0.2989 / 0.2380 | 0.5977 / 0.4760 | 1.1955 / 0.9519 |
| Cap 2001 (subset) | 0.2978 / 0.2371 | 0.5955 / 0.4742 | 1.1910 / 0.9484 |

### R1: MFAC for all three Eulerian grids

Every entry is **MFACₓᵧ / MFAC_z**.

| Group | G64 | G128 | G256 |
|:---|---:|---:|---:|
| Tube | 0.8126 / 0.6470 | 1.6251 / 1.2941 | 3.2502 / 2.5882 |
| Housing disc | 0.6370 / 0.5072 | 1.2740 / 1.0145 | 2.5480 / 2.0290 |
| AML | 0.3522 / 0.2805 | 0.7045 / 0.5610 | 1.4089 / 1.1219 |
| PML | 0.3349 / 0.2667 | 0.6698 / 0.5333 | 1.3395 / 1.0667 |
| Annulus | 0.3722 / 0.2964 | 0.7444 / 0.5927 | 1.4887 / 1.1855 |
| Basal chordae | 0.1707 / 0.1360 | 0.3415 / 0.2719 | 0.6829 / 0.5438 |
| Marginal chordae | 0.1966 / 0.1566 | 0.3933 / 0.3131 | 0.7865 / 0.6263 |
| Papillary caps | 0.1495 / 0.1190 | 0.2990 / 0.2381 | 0.5979 / 0.4761 |
| Cap 2001 (subset) | 0.1489 / 0.1185 | 0.2977 / 0.2371 | 0.5955 / 0.4742 |

### R2: MFAC for all three Eulerian grids

Every entry is **MFACₓᵧ / MFAC_z**.

| Group | G64 | G128 | G256 |
|:---|---:|---:|---:|
| Tube | 0.4063 / 0.3235 | 0.8126 / 0.6470 | 1.6251 / 1.2941 |
| Housing disc | 0.3192 / 0.2542 | 0.6385 / 0.5084 | 1.2770 / 1.0169 |
| AML | 0.1760 / 0.1401 | 0.3519 / 0.2802 | 0.7038 / 0.5605 |
| PML | 0.1674 / 0.1333 | 0.3348 / 0.2666 | 0.6695 / 0.5332 |
| Annulus | 0.1859 / 0.1481 | 0.3719 / 0.2961 | 0.7438 / 0.5923 |
| Basal chordae | 0.0856 / 0.0682 | 0.1712 / 0.1364 | 0.3425 / 0.2727 |
| Marginal chordae | 0.0986 / 0.0785 | 0.1972 / 0.1570 | 0.3943 / 0.3140 |
| Papillary caps | 0.0747 / 0.0595 | 0.1495 / 0.1190 | 0.2990 / 0.2381 |
| Cap 2001 (subset) | 0.0744 / 0.0593 | 0.1489 / 0.1185 | 0.2978 / 0.2371 |

### Interpreting the combinations

At fixed solid mesh, doubling N doubles both MFAC values. At fixed fluid grid, subdivision generally reduces MFAC.
The diagonal sequence **G64/R0 → G128/R1 → G256/R2** approximately maintains marker/fluid spacing ratios;
**G64/R0 → G64/R1 → G64/R2** instead tests solid refinement at fixed Eulerian resolution.
Similar ratios alone do not establish accuracy, volume conservation or stability.
Small MFAC does not mean the fluid resolves each tiny solid element, and scalar medians hide directional and local extremes.
Do not apply a universal 0.5–1 acceptance threshold to all structures, kernels and element orders.

## 6. Quality checks and the papillary-cap limitation

The [G128/R2 results and limitations, updated 19 October 2026]({{< relref "mv-results-audit.md" >}}) adds measured R2 quality and moving-mesh MFAC. R2 has 10 hexes with VTK scaled Jacobian below 0.1 (minimum 0.0404, marker 200); its tetrahedral minimum sqrt(2)|det(H)|/lmax³ is 0.0509 (marker 42). These distinct metrics must not be compared as identical quantities. The edge-balanced tetrahedral candidate reaches 0.00157 by the tet metric. More uniform edge lengths and positive Jacobians do not guarantee good shapes.

The R3-tube/disc + R2-valve test reduced tube/disc median G128 MFAC to 0.406/0.320 but failed at 0.89 s after inlet-wall excursions. This is evidence against refinement alone as a sufficient remedy. The cap remeshing pilots remain local candidates, not a repaired production assembly.

The R2 generator found positive reference hex Jacobians at all integration points and nonzero tet volumes.
Its minimum cell volume is $4.5351\times10^{-8}$ cm³; the maximum reference $|F-I|$ check is $1.37\times10^{-12}$.
These checks establish neither good element aspect ratios nor good quality under deformation.
The original mesh also has branch-junction face incidences that need interpretation in light of the intended independent components;
coincident or overlapping components are not automatically mesh defects.

In the G64/R2 run, the minimum reported $J\approx0.009898$ occurs at t=0.89 s in a marker-2001 papillary cap,
original XDA element 2033. This particular parent's volume is preserved by refinement to roundoff,
so the legacy interface-volume change does not explain its compression.
The cell is deformable basal-chordae material with a tether penalty, not a rigid prescribed-motion body.
The cap target returns to zero over 0.59–0.60 s. Underresolved fluid-mediated motion, penalty coupling and that rapid return
are hypotheses to test separately; the completed run does not isolate their causal contributions.

## 7. Reproduction and derived data

From the workspace root:

```bash
# R0 and R1: require the original IBAMR input files at the generator's configured path.
python3 fdm-3d-v1-geometry/scripts/gen_glamv_hex.py
python3 fdm-3d-v1-geometry/scripts/gen_glamv_hex.py --refine

# R2: reads the existing R1 binaries; refuses to overwrite an existing R2 directory.
python3 fdm-3d-v1-geometry/scripts/gen_glamv_hex_r2.py

# All measured edge statistics and the nine G/R combinations.
python3 runs/glamv_four_D_20261015/mesh_mfac.py

# Separate interpolation-order changes.
python3 fdm-3d-v1-geometry/scripts/gen_glamv_p2_from_p1.py
python3 fdm-3d-v1-geometry/scripts/gen_glamv_q2p2_from_hex.py
```

Derived statistics: [CSV](/data/mv-mesh-mfac.csv), [JSON](/data/mv-mesh-mfac.json).
The JSON includes inventory and marker groups; both files preserve more precision than the displayed tables.
Mesh binaries are under `fdm-3d-v1-geometry/src/ibm/data/`.
Run settings and result curves remain in [the paper]({{< relref "mv-paper.md" >}})
and [the data/code note]({{< relref "mv-data-and-code.md" >}}).
