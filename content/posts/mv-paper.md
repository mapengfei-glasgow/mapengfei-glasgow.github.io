---
title: "Mitral-valve FSI on GPUs with a nodal immersed finite element / finite difference method"
description: "Working paper. Sign in with your site sync code to read."
date: 2026-10-14
layout: protected-paper
academic: true
comments: false
searchHidden: true
build:
  list: never
---

Target journal: Journal of Fluid Mechanics

Code, scripts and derived data: see [Data and code]({{< relref "mv-data-and-code.md" >}}).

Questions to be answered:
1. How long is the IBAMR run SarahMV model? I have to rerun it (until 1.335) to ensure it.
2. How are the fiber direcions corresponding to the cells of P1 mesh or P1+Q1 mesh? are they using the original map?

---

## Abstract

(to be written)

## 1. Introduction

Heart-valve haemodynamics depend on leaflet mechanics, valve geometry and the resulting
unsteady flow structures. In aortic-valve FSI simulations, {{< cite "chen2020pressure" "author" >}} examined leaflet pressure distributions and showed that
bending rigidity affects opening, closure and flow resistance. {{< cite "abbas2025closure" "author" >}} compared mechanical and bioprosthetic aortic valves,
linking differences in closure timing to jet structure and the pressure differences
that drive leaflet motion.

Valve design and orientation also influence downstream stresses. {{< cite "haya2016effects" "author" >}} measured changes in viscous and turbulent stresses and
coronary flow with bileaflet mechanical valve orientation. Direct numerical simulations
by {{< cite "nitti2022numerical" "author" >}} compared turbulent and fluctuating
viscous stresses across mechanical aortic-valve configurations, while {{< cite "sarkar2025direct" "author" >}} investigated how streamlined leaflet edges modify
vortical structures and reduce downstream turbulence and shear stress. These aortic-valve
studies motivate examining leaflet dynamics and downstream flow structures together;
the present work considers a mitral-valve configuration, with different anatomy and loading.

For mitral-valve flow in a ventricular setting, {{< cite "meschini2018flow" "author" >}}
used direct numerical simulations coupled to ventricular and valve dynamics, validated
against companion experiments, to compare natural, biological and mechanical mitral valves.
They found that valve type affects ventricular flow, with more pronounced differences
when pumping efficiency is reduced; bileaflet mechanical valves weakened mitral-jet
penetration and apical recirculation at pathological ejection fractions.
In a commentary on this study, {{< cite "mittal2018matters" "author" >}} discussed the
challenge of modelling coupled cardiac and valvular motion and the implications of
prosthetic-valve choice for ventricular haemodynamics. These findings provide context
for the present tube-based mitral-valve study, which does not include ventricular-wall motion.

- Motivation: transmitral flow, vortex formation and breakdown downstream of the mitral valve.
- Reference model: IBAMR SarahNodalMV (nodal IFED, libMesh HEX8 / TET4 mesh, fiber-reinforced HGO leaflets, chordae, tethers) {{< cite "ibamrSarahNodalMV" >}}.
- Contributions (draft):
  1. a GPU nodal IFED solver that reproduces the IBAMR reference flow;
  2. a resolution study (background grid and solid mesh refined together at fixed MFAC);
  3. an assessment of the numerical choices (kernel, stress form, volumetric stabilisation, element type, fluid scheme);
  4. turbulence-related flow analysis downstream of the valve.

---

## 2. Problem settings

### Notation and abbreviations

- **Background grids:** {{< label "grid" "G-64" >}}, {{< label "grid" "G-128" >}} and {{< label "grid" "G-256" >}} name the Eulerian grid resolution
  in the two transverse directions.
- **Solid meshes:** {{< label "mesh" "R0/P1+Q1" >}} is the original solid mesh, {{< label "mesh" "r1" >}} is one uniform refinement, etc. .
- **Mesh factor (MFAC):** $\mathrm{MFAC}=\Delta s/h$, where $\Delta s$ is the
  Lagrangian marker spacing and $h$ is the Eulerian grid spacing.
- **Methods and anatomy:** FSI = fluid–structure interaction; IFED = immersed
  finite element/finite difference; IB = immersed boundary; FE = finite element;
  MV = mitral valve; AML/PML = anterior/posterior mitral leaflet;
  LV = left ventricle; HGO = Holzapfel–Gasser–Ogden material model.
- **Element and kernel labels:** P1/P2 denote linear/quadratic tetrahedral elements;
  Q1/Q2 denote trilinear/triquadratic hexahedral elements. CBS denotes a composite
  B-spline coupling kernel; the digits distinguish the kernel orders.

### Configuration names

The three configurations use **grid / mesh refinement / solid elements / outlet treatment** as their naming
convention. All three use {{< label "grid" "G-64" >}} ($64 \times 64 \times 96$ cells)
and outlet backflow stabilisation (`--outlet-backflow`, abbreviated **BF**).
not backflow will be labeled as **NBF**


{{< table-caption "1" "Configuration labels and solid elements" >}}

| Configuration label | Solid elements |
|:---|:---|
| {{< label "config" "G64/R0/P1/BF" >}} | Pure P1 tetrahedra |
| {{< label "config" "G64/R0/P1/NBF" >}} | Pure P1 tetrahedra |
| {{< label "config" "G64/R0/P1+Q1/BF" >}} | Q1 hexahedra + P1 tetrahedra |
| {{< label "config" "G64/R0/Q2+P2/BF" >}} | Q2 hexahedra + P2 tetrahedra |

### 2.1 Geometry, domain and loading

The original patient-specific mitral-valve geometry comes from
{{< cite "wang_finite_2013" "author" >}}, who reconstructed the valve from multi-slice
computed tomography scans, including leaflet thickness, chordal origins and insertion
points, and papillary muscle locations. The subsequent valve model and chordal structure
used here are primarily based on {{< cite "feng_chordae_2018" "author" >}}.
The present simulations use the IBAMR SarahNodalMV implementation of the reference model;
the mesh conversion is described in §2.3.


{{< table-caption "2" "Geometry, loading and material parameters" >}}

| Item | Value |
|:---|:---|
| Domain | $8.6 \times 8.6 \times 16.2$ cm (tube axis along z) |
| Tube | lumen radius 3.5 cm; housing-disc cells beyond $r = 3.73$ cm are force-free (passive rim) |
| Inlet / outlet | $z = 0$ / $z = 16.2$ cm, prescribed pressure on the lumen disc + feedback forcing (IBAMR FeedbackForcer) |
| Inlet pressure | `lvla_pressure_closing.inlet` (IBAMR LV–LA pressure curve) |
| Time simulated | 1.335 s |
| Fluid | $\rho = 1\,\mathrm{g/cm^3}$, $\mu = 0.04\,\mathrm{P}$ |
| Leaflets | Sarah HGO, unmodified invariants. AML: $C_{10} = 1245$, $C_{01} = 13.67$, $k_1 = 1.10 \times 10^{5}$, $k_2 = 84.85$, $\kappa = 0.080$; PML: $C_{10} = 502$, $C_{01} = 15.00$, $k_1 = 3.02 \times 10^{4}$, $k_2 = 144.5$, $\kappa = 0.053$. Variant: fully dispersed ($\kappa = 1/3$) |
| Chordae | IBAMR SarahNodalMV chordae model (parameters: ) |
| Volumetric term | $\beta_s = 5 \times 10^6\,\mathrm{dyn/cm^2}$ (all cells) |
| Tethers | pins (tube, disc) and papillary caps, $\beta = 100\kappa_s = 5 \times 10^8$, IBAMR cap schedule |

> TODO: there should be description about the movement of the papillary.

### 2.2 Background (Eulerian) grids


{{< table-caption "3" "Eulerian grid dimensions and time steps" >}}

| Grid | $N_x \times N_y \times N_z$ | Cells | $h_x = h_y$ (cm) | $h_z$ (cm) | $\Delta t$ (s) | Steps / 1.335 s |
|:---|---:|---:|---:|---:|---:|---:|
| {{< label "grid" "G-64" >}} | $64 \times 64 \times 96$ | 393,216 | 0.1344 | 0.1688 | $2 \times 10^{-5}$ | 66,750 |
| {{< label "grid" "G-128" >}} | $128 \times 128 \times 192$ | 3,145,728 | 0.0672 | 0.0844 | $1 \times 10^{-5}$ | 133,500 |
| {{< label "grid" "G-256" >}} | $256 \times 256 \times 384$ | 25,165,824 | 0.0336 | 0.0422 | | |
| IBAMR (reference) | $44 \times 44 \times 80$ | 154,880 | 0.195 | 0.2025 | $5 \times 10^{-6}$ | 267,000 |

Multigrid requires $N$ to be a power of two (64, 128, 256).
> TODO: this is not totally correct. 96 also can be used but the coarest grids are different.

### 2.3 Solid (Lagrangian) meshes

Built directly from the IBAMR mesh `MV_only_hex.xda` (11,567 HEX8 + 10,686 TET4; two duplicated elements removed)
with `fdm-3d-v1-geometry/scripts/gen_glamv_hex.py`;


{{< table-caption "4" "Lagrangian mesh inventory" >}}

| Solid mesh | Nodes (IB markers) | Q1 hexes | P1 tets | Volume (cm³) |
|:---|---:|---:|---:|---:|
| {{< label "mesh" "R0/P1" >}}  | | | | |
| {{< label "mesh" "R0/P1+Q1" >}}  | | | | |
| {{< label "mesh" "R0/Q2+P2" >}}  | | | | |
| {{< label "mesh" "R1/P1" >}}  | | | | |
| {{< label "mesh" "R1/P1+Q1" >}}  | | | | |
| {{< label "mesh" "R1/Q2+P2" >}}  | | | | |

{{< label "mesh" "R0/P1+Q1" >}} is IBAMR mesh.
$\mathrm{MFAC}\approx 0.5\text{–}1$ should be considered for each combination of grid and mesh.


Per component (nodes / cells / median edge length / MFAC on the paired grid) (just for {{< label "mesh" "R0/P1+Q1" >}} now):

{{< table-caption "5" "Component mesh sizes and mesh factors" >}}

| Component | {{< label "mesh" "R0/P1+Q1" >}} nodes | {{< label "mesh" "R0/P1+Q1" >}} cells | {{< label "mesh" "R0/P1+Q1" >}} edge (cm) | MFAC {{< label "mesh" "R0/P1+Q1 @ G-64" >}} |
|:---|---:|---:|---:|---:|
| Tube (marker 1) | 16,848 | 8,320 hex | 0.218 | 1.62 |
| Housing disc (42) | 3,773 | 10,650 tet | 0.169 | 1.26 |
| Leaflets (AML + PML) | 4,004 | 1,872 hex + 36 tet | 0.093 | 0.69 |
| Chordae (100/200/300) | 5,217 | 1,343 hex | 0.046 | 0.34 |
| Tether caps (1001–2005) | 220 | 30 hex | 0.040 | 0.30 |

> Known mesh issues inherited from the IBAMR model: chordae branch junctions where one hex face is shared by more
> than two hexes (≈ 70 quads at {{< label "mesh" "R0/P1+Q1" >}}), and a few poorly shaped chordae hexes (scaled Jacobian down to 0.07).
> The tube wall MFAC (1.6) is above 1 on both pairs; possible leakage through the wall is checked by the flux
> balance along the tube (§5.1).

**Element types: a hybrid hexahedral / tetrahedral mesh.** The {{< label "mesh" "R0/P1+Q1" >}} and {{< label "mesh" "r1" >}} meshes keep the IBAMR element
types, so one solid mixes trilinear hexahedra (Q1, HEX8) and linear tetrahedra (P1, TET4):


{{< table-caption "6" "Element counts by anatomical structure" >}}

| Structure | Q1 hex ({{< label "mesh" "R0/P1+Q1" >}}) | P1 tet ({{< label "mesh" "R0/P1+Q1" >}}) |
|:---|---:|---:|
| Tube (1) | 8,320 | 0 |
| Housing disc (42) | 0 | 10,650 |
| Leaflets + annulus (3–7, 23–25, 4099, 5099) | 1,872 | 36 |
| Chordae (100/200/300) | 1,343 | 0 |
| Tether caps (1001–2005) | 30 | 0 |
| **Total** | **11,565** | **10,686** |

The GPU solid code handles both element types in one array: tets are padded to 8 nodes by repeating node 0, and each
cell carries its own quadrature data in 8 slots (basis values, physical gradients and $w\lvert\det J\rvert$ per point):
2×2×2 Gauss for a hex, one centroid point for a tet (slots 1–7 have weight 0). One force-assembly kernel serves both. The pure-tet runs use the
same geometry with every hex split into tets (`glamv_ibamr`, `glamv_conf`).

### 2.4 Keeping the fluid outside the tube at rest

The **[passive rim + gap mask]({{< relref "mv-passive-rim-gap-mask.md" >}})** treatment
suppresses the exterior fluid bypass and prevents the protruding housing-disc rim from
carrying the transvalvular load. The companion page gives the damping rule, passive-cell
criterion and measured effect on flux and velocity.

---

## 3. Methods

### 3.1 Numerical method


The immersed finite element/finite difference formulation follows {{< cite "griffith2017hybrid" "author" >}}, with nodal coupling as described by {{< cite "wells2023nodal" "author" >}}. The choice of regularised kernels and relative
Lagrangian–Eulerian mesh spacing is informed by {{< cite "lee2022coupling" "author" >}}.(Details in `fdm-3d-v1-gpu/docs/NUMERICAL_METHODS.md`)


{{< table-caption "7" "Numerical method summary" >}}

| Part | Scheme |
|:---|:---|
| Fluid | staggered MAC grid, incremental pressure projection; viscous term implicit (backward Euler; Crank–Nicolson available in `ifed_bench`); convection central, conservative, AB2 |
| Coupling | nodal IFED (every FE node is an IB marker), RK2 midpoint, regularised delta kernels |
| Solid | P1 / P2 tets and Q1 hexes (mixed Q1 + P1 meshes), Sarah HGO / chordae TI material, volumetric penalty |
| Boundary | pressure inlet / outlet discs, feedback forcing, gap mask outside the tube, passive rim, tethers |

### 3.2 Will the simulation benefit from these choices?

Evidence so far comes from the 3D IFED benchmarks (torsion, Cook, idealised LV; `docs/IFED_STABILITY_STUDY.md`,
`docs/NUMERICAL_METHODS.md` §9) and from the mitral-valve runs.

#### (1) Kernel: {{< label "kernel" "CBS43" >}} or higher order ({{< label "kernel" "CBS54" >}}, {{< label "kernel" "CBS65" >}})

For the local divergence-free IFED method using composite B-splines, see {{< cite "li2025local" "author" >}}.


{{< table-caption "8" "Coupling kernels and benchmark results" >}}

| Kernel | Implemented | Max stable $\Delta t$ (torsion, $\mathrm{MFAC}\le 0.72$) | Volume error, LV problem 2 (MFAC 0.40) | MV result |
|:---|:---|---:|---:|:---|
| {{< label "kernel" "IB_4" >}} | yes | $1.6 \times 10^{-3}$ | | |
| {{< label "kernel" "BSPLINE_3" >}} (IBAMR default) | yes | | | glamv-0.0.2: backflow −23.6 cm³ (inlet) |
| {{< label "kernel" "CBS43" >}} | yes | $8 \times 10^{-4}$ | +0.05 % (wall displacement within 0.9 % of FE) | glamv-0.0.3: backflow −17.3 cm³ (inlet; IBAMR −15.6) |
| {{< label "kernel" "CBS32" >}} | yes | | | unstable at $\Delta t\ge 1 \times 10^{-5}$, stable at $5 \times 10^{-6}$ |

Finding: CBS kernels remove the leak driven by transmural pressure only at small MFAC (≤ 0.5–0.7); at $\mathrm{MFAC}>1$
they are worse than {{< label "kernel" "IB_4" >}}. Wider CBS kernels (54, 65) are expected to need smaller MFAC and cost more per marker.

#### (2) Stress form: modified invariants, deviatoric projection, or stripping the pressure part

To be tested for the MV case...

#### (3) Volumetric stabilisation $\kappa_s$ ($\beta_s$)


For volumetric stabilisation and stress formulations in hyperelastic immersed
boundary methods, see {{< cite "vadalaroth2020" "author" >}}.

To be tested for the MV case...

#### (4) Element type: P1, P2, Q1, Q2


{{< table-caption "9" "Element types and benchmark errors" >}}

| Element | Torsion error, $n = 6$ (MFAC) | Cook error, $n = 16$ (MFAC) | MV runs |
|:---|---:|---:|:---|
| P1 tet | +16.2 % (1.43) | +0.89 % (1.86) | 0.0.3, {{< label "run" "G5" >}}, {{< label "run" "G6" >}} (full cycle) |
| P2 tet | +1.7 % (0.72) | +0.48 % (0.93) | {{< label "run" "G3" >}} / {{< label "run" "G4" >}}: failed (old non-conforming tet split) |
| Q1 hex | +5.0 % (1.19) | +1.43 % (1.33) | {{< label "run" "G7" >}}–{{< label "run" "G10" >}}: outlet backflow instability, see §5 |
| Q2 hex (+ P2 tets) | | | *(2026-10-15)* mixed Q2 + P2 on {{< label "mesh" "R0/P1+Q1" >}}: G12 NaN at 0.92 s (outlet backflow), ~~G12b~~ full cycle with `--outlet-backflow` (§5.6) |

#### (5) Fluid solver and convection


{{< table-caption "10" "Fluid discretisation and outlet treatment" >}}

| Option | Status | Effect |
|:---|:---|:---|
| Viscous term BE vs CN | CN in `ifed_bench` (`--viscous`) | |
| Convection central + AB2 | default | |
| Convection 2nd-order upwind (SOU) | `real_av` only (`--conv-upwind`); not in `gla_mv` | |
| Outlet backflow stabilisation | `--outlet-backflow`: feedback force $\kappa(0-U_z)$ on the outlet face, only where $U_z<0$, $\kappa = 0.5/\Delta t$ | removes the outlet-backflow failure ({{< label "run" "G7b" >}} restart: passes $t = 0.835$); does **not** remove the inlet-edge failure at $t \approx 0.86$–0.92 (~~G11~~: 1 of 4 runs completes, §5.5); changes the closing transient (§5.1) |

### 3.3 Validation against IBAMR

---

## 4. GPU acceleration

The GPU computation framework primarily builds on {{< cite "ma_fully_2025" "author" >}},
which presents a fully GPU-accelerated, matrix-free immersed boundary method for
fiber-reinforced hyperelastic cardiac models. Its nodal coupling avoids finite-element
projection operations, while a matrix-free geometric multigrid solver supports the fluid
projection method. The implementation choices and performance measurements for the present
mitral-valve solver are described below.

### 4.1 Performance levels

All per-step work runs on the GPU: momentum (three face Helmholtz multigrid solves), pressure Poisson multigrid, projection, convection, IB interpolation and spreading, solid force assembly (PK1, tethers, viscosity, penalties), feedback forcing and gap mask. The host only writes output and logs.
(fluid solver, `docs/GPU_PERFORMANCE.md`)


{{< table-caption "11" "GPU performance levels" >}}

| Level | Switch | RTX 5070 Laptop, $256^3$ (ms/step) | RTX PRO 5000, $128^3$ (ms/step) | RTX PRO 5000, $256^3$ (ms/step) | Result vs level 0 |
|:---|:---|---:|---:|---:|:---|
| original | — | 496 | 39.2 | 197.5 | — |
| A | default | 240 | 22.8 | 100.7 | bitwise identical |
| B | `DSH_PERF_LEVEL=1` + FMA | 179 | 17.1 | 67.8 | ~$1 \times 10^{-13}$ |
| C | `DSH_PERF_LEVEL=2` + FMA | 126 | 11.0 | 43.8 | ≤ $1 \times 10^{-8}$ |
| D | `DSH_PERF_LEVEL=3` + FMA | 111 | 9.05 | 38.0 | ~$1 \times 10^{-8}$ |

Mitral-valve case (0.0.3 configuration, {{< label "grid" "G-64" >}}, P1 tets, RTX PRO 5000): 49.4 ms/step originally, 21.7 at level A,
10.1 at level D + FMA; a full cycle takes ≈ 11 min. IBAMR: ≈ 45 ms/step on 24 MPI ranks (1 h 38 min for 0.65 s).

### 4.3 Share of the simulation time per part

---

## 5. Results

### 5.1 Run summary


{{< table-caption "12" "Run outcomes and flow metrics" >}}

| Run | Grid | Solid mesh | Leaflets | $\Delta t$ (s) | Outcome | Forward 0.04–0.2 (cm³) ‡ | Backflow 0.2–0.56 (cm³) | $J_{\min}$ |
|:---|:---|:---|:---|---:|:---|---:|---:|---:|
| 0.0.3 | {{< label "grid" "G-64" >}} | P1 tet (glamv_ibamr) | fibre HGO | $2 \times 10^{-5}$ | full cycle | 38.5 | −16.4 | 0.31 |


\* see §3.3: identical to G7 up to $t = 0.16$ s; the difference is the 0.04 s sampling of the closing spike.
† G10 writes frames every 0.02 s, so its volumes are not sampled like the others.

**Outlet backflow on the hex meshes.** On the hex meshes the valve opens wider (first-opening plateau ≈ 485 cm³/s
against ≈ 410 on the tet meshes, [Figure 1]({{< relref "mv-paper.md" >}}#figure-1)) and the jet reaches the outlet with recirculation; without stabilisation
the backflow through the outlet grows until the run fails ({{< label "run" "G7" >}}–{{< label "run" "G10" >}}). With
`--outlet-backflow` the coarsest pair (~~{{< label "run" "G11" >}}~~, {{< label "mesh" "R0/P1+Q1 @ G-64" >}}) ran through the whole 1.335 s once, with
$J_{\min} = 0.36$ and $I_{1,\max} = 6.1$ (three reruns fail at the inlet edge at $t \approx 0.91$ s, §5.5); in that run:

- Up to $t = 0.16$ s ~~G11~~ and G7 agree frame by frame (the term is inactive while the outlet flows out).
- The term acts on the closing transient: the spike at $t = 0.20$ s drops from −575 (G7) to −406 cm³/s (IBAMR −488), and
  the backflow volume 0.20–0.56 s moves from −18.5 to −16.4 cm³ (IBAMR −15.6).
- Second cycle: the forward plateau stays ≈ 20 % above the tet runs (Q ≈ 400–480 vs 310–400 cm³/s), and the
  second closure is delayed — at $t = 0.92$/0.96 s ~~G11~~ still has $Q = +34$/+4.5 cm³/s where 0.0.3 and G5 show the closing
  spike (−89/−100). The closed-phase leak from 1.00 s on (−48 … −10 cm³/s) matches the tet runs.
- The stabilisation does **not** remove the recirculation itself: one cell below the outlet, 61–84 % of the lumen still
  has $w<0$ in the first closed phase (0.28–0.52 s; tet runs 51–82 %) and 65–77 % in the second (1.00–1.24 s; tet runs
  57–64 %, [Figure 2]({{< relref "mv-paper.md" >}}#figure-2)). It only stops reverse flow from entering through the outlet face and feeding on itself.

Leakage check (tube flux at $z = 3$, 5.5, 9, 12 cm against $z = 12$ cm, every 0.04 s frame) and the gap outside the tube
(§2.4):


{{< table-caption "13" "Tube-flux conservation and exterior-flow checks" >}}

| Run | $\max\lvert Q(z)-Q(12)\rvert / \max\lvert Q\rvert$ | max gap flux, $r>3.8$ (cm³/s) | max $\lvert\mathbf u\rvert$ outside the wall (cm/s) | frames |
|:---|---:|---:|---:|---:|
| 0.0.3 | 0.38 % | 0.018 | 0.106 | 35 |

Flux along the tube is conserved to < 0.5 % in every run, so the tube wall does not leak at MFAC 1.6 on {{< label "grid" "G-64" >}}.

{{< chart height="340" xlabel="t (s)" ylabel="Q through the tube lumen, z = 12 cm (cm³/s)" colors="#d1495b,#edae49,#00798c,#30638e,#7a7a7a" caption="Figure 1. Flow rate through the tube lumen (r < 3.5 cm) at z = 12 cm, fluid frames every 0.04 s. ~~G11~~ = R0/P1+Q1 hex @ G-64 with outlet backflow stabilisation; G7 = same without it (NaN after 0.88 s); G5 = conforming P1 tets; 0.0.3 = glamv_ibamr P1 tets; IBAMR = inlet flux of the reference run (to 0.65 s) sampled at the same frames." >}}
t, G64/R0/P1+Q1/BF, G7 (hex), G5 (tet conf.), 0.0.3 (tet), IBAMR
0.00, 0.0, 0.0, 0.0, 0.0, 0.0
0.04, 55.4, 55.4, 52.8, 54.2, 57.0
0.08, 367.9, 367.9, 333.5, 341.0, 309.3
0.12, 488.5, 488.5, 411.9, 415.6, 373.9
0.16, 482.0, 482.0, 403.7, 415.3, 385.0
0.20, -406.1, -574.8, -460.1, -473.2, -488.2
0.24, -68.6, -34.7, -14.6, -17.7, -27.3
0.28, -44.9, -46.6, -48.9, -51.8, -55.5
0.32, -31.6, -29.7, -33.8, -34.2, -19.9
0.36, -26.1, -27.7, -28.6, -33.2, -19.2
0.40, -22.5, -23.2, -22.2, -22.9, -13.7
0.44, -19.6, -21.3, -17.9, -22.6, -11.2
0.48, -13.4, -13.2, -14.2, -11.1, -7.0
0.52, -4.9, -3.5, 0.4, -6.3, 0.8
0.56, 47.8, 47.7, 46.1, 50.8, 15.0
0.60, 189.4, 186.0, 176.8, 180.6, 451.8
0.64, 615.3, 616.3, 539.4, 558.3, 535.5
0.68, 520.3, 531.8, 431.3, 452.6,
0.72, 481.6, 475.4, 381.8, 402.7,
0.76, 443.9, 428.6, 359.6, 373.7,
0.80, 428.1, 408.4, 323.0, 339.7,
0.84, 415.0, 403.8, 317.4, 328.1,
0.88, 396.7, 375.2, 310.0, 322.0,
0.92, 34.0, , -100.2, -88.5,
0.96, 4.5, , -89.5, -80.1,
1.00, -47.9, , -38.8, -40.6,
1.04, -34.7, , -35.6, -35.7,
1.08, -27.9, , -30.1, -30.5,
1.12, -26.3, , -24.6, -25.7,
1.16, -21.2, , -21.2, -23.0,
1.20, -18.9, , -13.7, -18.8,
1.24, -10.4, , -9.9, -10.8,
1.28, 13.7, , 10.8, 13.3,
1.32, 72.2, , 67.5, 69.2,
1.335, 119.4, , 109.1, 115.7,
{{< /chart >}}

{{< chart height="280" xlabel="t (s)" ylabel="lumen fraction with w < 0 (%)" colors="#d1495b,#edae49,#00798c,#30638e" caption="Figure 2. Outlet recirculation: fraction of the tube lumen with downward velocity one cell below the outlet face (z ≈ 16.0 cm). The near-100 % values at t = 0.20 s are the closing spike (the whole column moves back)." >}}
t, G64/R0/P1+Q1/BF, G7 (hex), G5 (tet conf.), 0.0.3 (tet)
0.00, 0.0, 0.0, 0.0, 0.0
0.04, 0.4, 0.4, 0.4, 0.4
0.08, 1.3, 1.3, 1.3, 1.3
0.12, 0.9, 0.9, 0.9, 0.9
0.16, 0.6, 0.6, 0.6, 0.7
0.20, 99.1, 98.0, 96.5, 96.8
0.24, 94.3, 75.1, 68.0, 65.0
0.28, 83.9, 78.3, 82.3, 79.1
0.32, 77.0, 63.5, 77.1, 74.1
0.36, 76.0, 62.6, 72.0, 75.1
0.40, 74.4, 59.8, 64.4, 68.5
0.44, 72.4, 59.4, 61.1, 60.7
0.48, 67.9, 57.2, 55.9, 61.0
0.52, 61.1, 53.4, 50.7, 57.4
0.56, 12.2, 15.1, 13.5, 10.3
0.60, 3.0, 3.3, 3.3, 3.1
0.64, 2.9, 2.5, 2.7, 2.6
0.68, 14.0, 14.6, 16.3, 17.8
0.72, 35.4, 31.7, 34.7, 34.5
0.76, 56.0, 38.9, 42.0, 40.5
0.80, 46.8, 50.7, 42.0, 51.2
0.84, 42.0, 48.0, 49.0, 53.6
0.88, 43.4, 46.5, 48.2, 50.4
0.92, 73.9, , 58.6, 60.4
0.96, 55.3, , 85.3, 82.7
1.00, 76.5, , 62.0, 64.2
1.04, 72.1, , 64.2, 63.2
1.08, 70.2, , 64.1, 62.0
1.12, 71.6, , 63.3, 62.8
1.16, 70.5, , 60.7, 60.9
1.20, 70.1, , 56.6, 59.3
1.24, 65.1, , 58.1, 57.9
1.28, 38.0, , 40.6, 38.6
1.32, 3.0, , 3.1, 3.7
1.335, 5.1, , 6.0, 6.2
{{< /chart >}}

{{< chart height="260" xlabel="t (s)" ylabel="max |u| outside the wall (cm/s)" colors="#d1495b,#edae49,#00798c,#30638e" caption="Figure 3. Largest fluid speed in the layer just outside the tube wall (3.73 < r < 4.3 cm, all z): the gap mask and passive rim hold it below 0.12 cm/s (G7: 0.23 cm/s in its last frame before NaN), against lumen speeds of order 100 cm/s." >}}
t, G64/R0/P1+Q1/BF, G7 (hex), G5 (tet conf.), 0.0.3 (tet)
0.00, 0.000, 0.000, 0.000, 0.000
0.04, 0.000, 0.000, 0.001, 0.001
0.08, 0.005, 0.005, 0.007, 0.007
0.12, 0.010, 0.010, 0.012, 0.012
0.16, 0.009, 0.009, 0.010, 0.010
0.20, 0.015, 0.022, 0.027, 0.027
0.24, 0.040, 0.043, 0.056, 0.055
0.28, 0.054, 0.071, 0.068, 0.106
0.32, 0.041, 0.059, 0.081, 0.041
0.36, 0.069, 0.057, 0.078, 0.098
0.40, 0.072, 0.094, 0.074, 0.068
0.44, 0.067, 0.076, 0.048, 0.062
0.48, 0.067, 0.124, 0.100, 0.097
0.52, 0.060, 0.068, 0.061, 0.052
0.56, 0.041, 0.049, 0.059, 0.046
0.60, 0.036, 0.044, 0.047, 0.057
0.64, 0.037, 0.039, 0.044, 0.035
0.68, 0.035, 0.029, 0.045, 0.040
0.72, 0.042, 0.032, 0.032, 0.036
0.76, 0.016, 0.019, 0.028, 0.029
0.80, 0.012, 0.016, 0.027, 0.020
0.84, 0.014, 0.022, 0.022, 0.015
0.88, 0.020, 0.230, 0.016, 0.012
0.92, 0.024, , 0.024, 0.013
0.96, 0.039, , 0.029, 0.043
1.00, 0.037, , 0.032, 0.071
1.04, 0.037, , 0.057, 0.063
1.08, 0.057, , 0.118, 0.061
1.12, 0.058, , 0.100, 0.067
1.16, 0.068, , 0.096, 0.053
1.20, 0.074, , 0.069, 0.087
1.24, 0.055, , 0.074, 0.076
1.28, 0.050, , 0.040, 0.058
1.32, 0.034, , 0.052, 0.042
1.335, 0.044, , 0.045, 0.057
{{< /chart >}}

### 5.2 Fluid


{{< table-caption "14" "Planned fluid analysis by grid" >}}

| Analysis | {{< label "grid" "G-64" >}} | {{< label "grid" "G-128" >}} | {{< label "grid" "G-256" >}} | IBAMR |
|:---|:---|:---|:---|:---|
| Flow rate vs time (inlet / tube sections) | [Figure 1]({{< relref "mv-paper.md" >}}#figure-1) (~~{{< label "run" "G11" >}}~~, G7, G5, 0.0.3) | | | [Figure 1]({{< relref "mv-paper.md" >}}#figure-1) (to 0.65 s) |
| Streamlines (opening, peak, closure) | | | | |
| Vorticity (mid-plane, transverse sections) | | | | |
| Vortex ring formation and breakdown (large → small eddies) | | | | |
| Q-criterion iso-surfaces | | | | |
| Energy dissipation rate $\varepsilon = 2\mu\,\mathbf{S}:\mathbf{S}$ (volume integral vs time) | | | | |
| Turbulent kinetic energy / spectra downstream of the valve | | | | |

### 5.3 Solid


{{< table-caption "15" "Planned solid analysis by grid and mesh" >}}

| Analysis | {{< label "grid" "G-64" >}} / {{< label "mesh" "R0/P1+Q1" >}} | {{< label "grid" "G-128" >}} / {{< label "mesh" "r1" >}} | {{< label "grid" "G-256" >}} / {{< label "mesh" "r2" >}} | IBAMR |
|:---|:---|:---|:---|:---|
| Leaflet displacement (tip, belly) vs time | | | | |
| Orifice area vs time | | | | |
| Stress (first principal / von Mises) at peak opening and closure | | | | |
| Volume change, $J$ range (all cells / leaflets) | | | | |
| Chordae tension vs time | | | | |

## 6. Discussion

Key findings so far (coarsest pair {{< label "mesh" "R0/P1+Q1 @ G-64" >}}, 2026-10-14):

1. **The hybrid hex/tet IBAMR mesh can run a full cycle on the GPU, but not reliably** (~~{{< label "run" "G11" >}}~~: 1.335 s in
   10.6 min, 9.5 ms/step, 82 % of it in the fluid solver, $J_{\min} = 0.36$, once; three reruns fail at $t \approx 0.86$–0.92 s at the inlet
   edge). The first cycle is reproducible and $\Delta t$-independent.
2. **The fluid outside the tube stays at rest** (gap mask + passive rim): gap flux ≤ 0.013 cm³/s and speeds ≤ 0.074 cm/s
   outside the wall over the whole cycle, and the lumen flux is conserved along the tube to 0.36 %, despite tube-wall
   MFAC 1.6.
3. **Hex leaflets open wider than tet leaflets**: peak forward flow 489 vs 412–416 cm³/s (IBAMR 385, same sampling).
   With the same geometry and material, the element type alone raises the forward flow by ≈ 18 %, and moves it away
   from IBAMR, which uses the same HEX8 mesh. Candidates: quadrature rule (ours 2×2×2 Gauss per hex), stress
   evaluation, or resolution — to be checked against IBAMR's settings and at {{< label "mesh" "r1 @ G-128" >}}.
4. **Outlet stabilisation changes the closure, not only the stability**: it lowers the closing spike (−406 vs −575 cm³/s;
   IBAMR −488) and delays the second closure. Regurgitant volumes on hex meshes therefore depend on the outlet
   treatment; a longer outlet tube (or a pressure–flow outlet) would separate the two effects.
5. The closing spike lies between two 0.04 s frames, so volumes and peak values from frames are sampling-limited
   (the ~~G11~~ vs G7 forward-volume difference is entirely this). Per-step flux output is needed before timing
   (opening/closing) and regurgitant volumes go into the paper.
6. **The reference run (0.0.3) is reproducible but only marginally stable** (§5.4): the current code reproduces it
   bitwise to 0.32 s and finishes at level 0, but a level-D rerun fails at 1.20 s. All reruns show a local collapse of the
   posterior leaflet at a chordae insertion in the second closed phase; this, not the flow, is the weak point of the
   tet model. The hex failures are boundary instabilities instead: at the outlet (cured by `--outlet-backflow`) and at the
   rim of the inlet disc (not yet treated). In neither case is the fluid solver's accuracy the cause.

Open questions:

- Resolution: does the flow converge between {{< label "grid" "G-64" >}}, {{< label "grid" "G-128" >}}, {{< label "grid" "G-256" >}} at fixed MFAC?
- Which numerical choice matters most for the valve dynamics (kernel, element, stabilisation)?
- Limits: outlet boundary treatment, chordae mesh of the IBAMR model, tube-wall $\mathrm{MFAC}>1$, comparison with IBAMR
  only up to 0.65 s.

## 7. Conclusions

(to be written)

## Data and code

Repository links, simulation outputs, analysis scripts and the ~~G11~~ reproduction instructions
are available on the separate [Data and code page]({{< relref "mv-data-and-code.md" >}}).
The [Appendix A rerun guide for glamv-0.0.3]({{< relref "mv-data-and-code.md" >}}#appendix-a-rerunning-glamv-003-rerun-guide-from-commits-c6538e3--481431c)
is also on that page.

---

{{< references >}}
