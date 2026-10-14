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

> **Page history (2026-10-15).** This page combines two versions so that the author can decide what to keep:
> the working-paper draft of commit `13c1fc3` (2026-10-14 14:58; removed by `c6538e3`) as §§ Abstract–Data and code, and the
> glamv-0.0.3 rerun guide of commits `c6538e3` / `481431c` as Appendix A. Additions of 2026-10-15 (reruns on the RTX 5070
> Laptop, corrected volume window) are marked *(2026-10-15)*.
Working draft. Target journal: *Journal of Fluid Mechanics*.
Status: 2026-10-14. Empty cells are not yet measured. Run labels ({{< label "run" "G1" >}} … {{< label "run" "G11" >}}) refer to the run register in
`GLAMV_STATUS.md` (dev clone, branch `glamv-cbspline`). Code, scripts and derived data: see [Data and code](#data-and-code).

**Latest (2026-10-14):** {{< label "run" "G11" >}} — the IBAMR hybrid hex/tet mesh {{< label "mesh" "r0 @ G-64" >}} with outlet backflow
stabilisation — completed the full cycle once (1.335 s in 10.6 min), but **three reruns with the same settings fail at
$t \approx 0.86$–0.92 s**. The hex runs have two boundary instabilities, at the outlet (cured by `--outlet-backflow`) and at the
**edge of the inlet disc** (not yet treated); neither is a fluid-solver accuracy problem (§5.5).

---

## Abstract

(to be written)

## 1. Introduction

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
  in the two transverse directions. {{< label "grid" "G-64" >}} means $N_x=N_y=64$ and $N_z=96$;
  {{< label "grid" "G-128" >}} means $128 \times 128 \times 192$ cells; {{< label "grid" "G-256" >}} means
  $256 \times 256 \times 384$ cells. The number after the hyphen is not the total cell count.
- **Solid meshes:** {{< label "mesh" "r0" >}} is the original solid mesh, {{< label "mesh" "r1" >}} is one uniform refinement,
  and {{< label "mesh" "r2" >}} is two refinement levels. **{{< label "mesh" "r0 @ G-64" >}}** means the {{< label "mesh" "r0" >}} solid mesh coupled
  to the {{< label "grid" "G-64" >}} fluid grid; the “@” reads “on”.
- **Run labels:** {{< label "run" "G1" >}}–{{< label "run" "G10" >}} (without a hyphen), including variants such as {{< label "run" "G1d" >}} and {{< label "run" "G7b" >}},
  identify experiments in the run register, rather than grid sizes.
- **Mesh factor (MFAC):** $\mathrm{MFAC}=\Delta s/h$, where $\Delta s$ is the
  Lagrangian marker spacing and $h$ is the Eulerian grid spacing.
- **Methods and anatomy:** FSI = fluid–structure interaction; IFED = immersed
  finite element/finite difference; IB = immersed boundary; FE = finite element;
  MV = mitral valve; AML/PML = anterior/posterior mitral leaflet;
  LV = left ventricle; HGO = Holzapfel–Gasser–Ogden material model.
- **Element and kernel labels:** P1/P2 denote linear/quadratic tetrahedral elements;
  Q1/Q2 denote trilinear/triquadratic hexahedral elements. CBS denotes a composite
  B-spline coupling kernel; the digits distinguish the kernel orders.

### 2.1 Geometry, domain and loading

| Item | Value |
|---|---|
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

### 2.2 Background (Eulerian) grids

| Grid | $N_x \times N_y \times N_z$ | Cells | $h_x = h_y$ (cm) | $h_z$ (cm) | $\Delta t$ (s) | Steps / 1.335 s |
|---|---|---|---|---|---|---|
| {{< label "grid" "G-64" >}} | $64 \times 64 \times 96$ | 393,216 | 0.1344 | 0.1688 | $2 \times 10^{-5}$ | 66,750 |
| {{< label "grid" "G-128" >}} | $128 \times 128 \times 192$ | 3,145,728 | 0.0672 | 0.0844 | $1 \times 10^{-5}$ | 133,500 |
| {{< label "grid" "G-256" >}} | $256 \times 256 \times 384$ | 25,165,824 | 0.0336 | 0.0422 | | |
| IBAMR (reference) | $44 \times 44 \times 80$ | 154,880 | 0.195 | 0.2025 | $5 \times 10^{-6}$ | 267,000 |

Multigrid requires $N$ to be a power of two (64, 128, 256).

### 2.3 Solid (Lagrangian) meshes

Built directly from the IBAMR mesh `MV_only_hex.xda` (11,567 HEX8 + 10,686 TET4; two duplicated elements removed)
with `fdm-3d-v1-geometry/scripts/gen_glamv_hex.py`; level {{< label "mesh" "r1" >}} = one uniform refinement (hex → 8, tet → 8).
Each grid should use the solid level that keeps $\mathrm{MFAC}\approx 0.5\text{–}1$ for the leaflets ($\mathrm{MFAC}=\Delta s/h$).

| Solid mesh | Paired grid | Nodes (IB markers) | Q1 hexes | P1 tets | Volume (cm³) |
|---|---|---|---|---|---|
| {{< label "mesh" "r0" >}} (`glamv_hex`, = IBAMR mesh) | {{< label "grid" "G-64" >}} | 29,524 | 11,565 | 10,686 | |
| {{< label "mesh" "r1" >}} (`glamv_hex_r1`) | {{< label "grid" "G-128" >}} | 169,094 | 92,520 | 85,488 | |
| {{< label "mesh" "r2" >}} | {{< label "grid" "G-256" >}} | | | | |

Per component (nodes / cells / median edge length / MFAC on the paired grid):

| Component | {{< label "mesh" "r0" >}} nodes | {{< label "mesh" "r0" >}} cells | {{< label "mesh" "r0" >}} edge (cm) | MFAC {{< label "mesh" "r0 @ G-64" >}} | {{< label "mesh" "r1" >}} nodes | {{< label "mesh" "r1" >}} cells | {{< label "mesh" "r1" >}} edge (cm) | MFAC {{< label "mesh" "r1 @ G-128" >}} | {{< label "mesh" "r2" >}} … @ {{< label "grid" "G-256" >}} |
|---|---|---|---|---|---|---|---|---|---|
| Tube (marker 1) | 16,848 | 8,320 hex | 0.218 | 1.62 | 100,464 | 66,560 hex | 0.109 | 1.62 | |
| Housing disc (42) | 3,773 | 10,650 tet | 0.169 | 1.26 | 21,943 | 85,200 tet | 0.086 | 1.27 | |
| Leaflets (AML + PML) | 4,004 | 1,872 hex + 36 tet | 0.093 | 0.69 | 23,280 | 14,976 hex + 288 tet | 0.047 | 0.69 | |
| Chordae (100/200/300) | 5,217 | 1,343 hex | 0.046 | 0.34 | 24,014 | 10,744 hex | 0.024 | 0.35 | |
| Tether caps (1001–2005) | 220 | 30 hex | 0.040 | 0.30 | 790 | 240 hex | 0.020 | 0.30 | |

Known mesh issues inherited from the IBAMR model: chordae branch junctions where one hex face is shared by more
than two hexes (≈ 70 quads at {{< label "mesh" "r0" >}}), and a few poorly shaped chordae hexes (scaled Jacobian down to 0.07).
The tube wall MFAC (1.6) is above 1 on both pairs; possible leakage through the wall is checked by the flux
balance along the tube (§5.1).

**Element types: a hybrid hexahedral / tetrahedral mesh.** The {{< label "mesh" "r0" >}} and {{< label "mesh" "r1" >}} meshes keep the IBAMR element
types, so one solid mixes trilinear hexahedra (Q1, HEX8) and linear tetrahedra (P1, TET4):

| Structure | Q1 hex ({{< label "mesh" "r0" >}}) | P1 tet ({{< label "mesh" "r0" >}}) |
|---|---|---|
| Tube (1) | 8,320 | 0 |
| Housing disc (42) | 0 | 10,650 |
| Leaflets + annulus (3–7, 23–25, 4099, 5099) | 1,872 | 36 |
| Chordae (100/200/300) | 1,343 | 0 |
| Tether caps (1001–2005) | 30 | 0 |
| **Total** | **11,565** | **10,686** |

The GPU solid code handles both element types in one array: tets are padded to 8 nodes by repeating node 0, and each
cell carries its own quadrature data in 8 slots (basis values, physical gradients and $w\lvert\det J\rvert$ per point):
2×2×2 Gauss for a hex, one centroid point for a tet (slots 1–7 have weight 0). One force-assembly kernel serves both. The pure-tet runs (0.0.3, {{< label "run" "G1" >}}–{{< label "run" "G6" >}}) use the
same geometry with every hex split into tets (`glamv_ibamr`, `glamv_conf`).

### 2.4 Keeping the fluid outside the tube at rest

The tube is immersed in a box ($8.6 \times 8.6$ cm cross-section), so there is a gap of fluid between the outer
tube wall ($r \approx 3.73$ cm) and the domain boundary. Nothing in the original model stops flow in that gap: with the
inlet/outlet pressure prescribed only on the lumen disc, the gap is a bypass around the valve, and the
transvalvular pressure difference also loads the part of the housing disc that sticks out beyond the tube
(inlet pressure below it, outlet pressure above it), which tore the disc rim in early runs (glamv-0.0.1). Two measures,
both absent in IBAMR, hold the gap fluid at rest:

1. **Gap mask** (Eulerian Brinkman damping, `--gap-mask 3.6 --gap-ramp 0.13 --gap-iters -1`). A radial indicator
   $\chi(r)$ is 0 for $r \le 3.6$ cm, rises linearly to 1 at $r = 3.73$ cm (inside the tube wall) and stays 1 out to the
   domain boundary, over the full height. Every velocity face with $\chi > 0$ is damped implicitly,
   $\mathbf u \leftarrow \mathbf u / (1 + \Delta t\,\kappa\chi)$ with $\kappa\Delta t = 1000$, before the pressure projection.
   Incompressibility then forces the net flux through the wall to (almost) zero. The lumen ($r < 3.5$ cm) is untouched.
2. **Passive rim** (`--passive-rim 3.73`). The 1,658 housing-disc cells whose reference centroid lies at $r > 3.73$ cm are made
   force-free ($J_e = 0$ ⇒ no PK1, tether, viscous or volumetric force; spreading and interpolation stay dual), so they only
   follow the (static) gap fluid and no longer carry the transvalvular load.

Measured effect on the coarsest pair ({{< label "mesh" "r0 @ G-64" >}}, run {{< label "run" "G11" >}}, all 35 frames over 1.335 s): flux through the
gap $r > 3.8$ cm at most **0.013 cm³/s** (peak lumen flux 615 cm³/s, i.e. $2 \times 10^{-5}$), and $\max\lvert\mathbf u\rvert$ in the layer
just outside the wall ($3.73 < r < 4.3$ cm) at most **0.074 cm/s**; the lumen flux differs between $z = 3$, 5.5, 9 and 12 cm by
at most 0.36 % of its peak (Table in §5.1). The same holds for every passive-rim run (Figure 3).

---

## 3. Methods

### 3.1 Numerical method (summary; details in `fdm-3d-v1-gpu/docs/NUMERICAL_METHODS.md`)

The immersed finite element/finite difference formulation follows Griffith and Luo
{{< cite "griffith2017hybrid" >}}, with nodal coupling as described by Wells et al.
{{< cite "wells2023nodal" >}}. The choice of regularised kernels and relative
Lagrangian–Eulerian mesh spacing is informed by Lee and Griffith
{{< cite "lee2022coupling" >}}.

| Part | Scheme |
|---|---|
| Fluid | staggered MAC grid, incremental pressure projection; viscous term implicit (backward Euler; Crank–Nicolson available in `ifed_bench`); convection central, conservative, AB2 |
| Coupling | nodal IFED (every FE node is an IB marker), RK2 midpoint, regularised delta kernels |
| Solid | P1 / P2 tets and Q1 hexes (mixed Q1 + P1 meshes), Sarah HGO / chordae TI material, volumetric penalty |
| Boundary | pressure inlet / outlet discs, feedback forcing, gap mask outside the tube, passive rim, tethers |

### 3.2 Will the simulation benefit from these choices?

Evidence so far comes from the 3D IFED benchmarks (torsion, Cook, idealised LV; `docs/IFED_STABILITY_STUDY.md`,
`docs/NUMERICAL_METHODS.md` §9) and from the mitral-valve runs.

#### (1) Kernel: {{< label "kernel" "CBS43" >}} or higher order ({{< label "kernel" "CBS54" >}}, {{< label "kernel" "CBS65" >}})

For the local divergence-free IFED method using composite B-splines, see Li et al.
{{< cite "li2025local" >}}.

| Kernel | Implemented | Max stable $\Delta t$ (torsion, $\mathrm{MFAC}\le 0.72$) | Volume error, LV problem 2 (MFAC 0.40) | MV result |
|---|---|---|---|---|
| {{< label "kernel" "IB_4" >}} | yes | $1.6 \times 10^{-3}$ | | |
| {{< label "kernel" "BSPLINE_3" >}} (IBAMR default) | yes | | | glamv-0.0.2: backflow −23.6 cm³ (inlet) |
| {{< label "kernel" "CBS43" >}} | yes | $8 \times 10^{-4}$ | +0.05 % (wall displacement within 0.9 % of FE) | glamv-0.0.3: backflow −17.3 cm³ (inlet; IBAMR −15.6) |
| {{< label "kernel" "CBS32" >}} | yes | | | unstable at $\Delta t\ge 1 \times 10^{-5}$, stable at $5 \times 10^{-6}$ |
| {{< label "kernel" "CBS54" >}} | no | | | |
| {{< label "kernel" "CBS65" >}} | no | | | |

Finding: CBS kernels remove the leak driven by transmural pressure only at small MFAC (≤ 0.5–0.7); at $\mathrm{MFAC}>1$
they are worse than {{< label "kernel" "IB_4" >}}. Wider CBS kernels (54, 65) are expected to need smaller MFAC and cost more per marker.

#### (2) Stress form: modified invariants, deviatoric projection, or stripping the pressure part

| Form | Torsion (P1, MFAC 1.43, $\nu_s = 0.4$) | Cook | MV |
|---|---|---|---|
| modified invariants (Flory, multiplicative split) | +16.2 % | +0.89 % | |
| unmodified invariants | wrong sign, volume −17 % | −5.2 % | (IBAMR Sarah model uses unmodified + $\beta_s$) |
| deviatoric projection | +15.0 % | +0.52 % | |

#### (3) Volumetric stabilisation $\kappa_s$ ($\beta_s$)

For volumetric stabilisation and stress formulations in hyperelastic immersed
boundary methods, see Vadala-Roth et al. {{< cite "vadalaroth2020" >}}.

| Case | Without $\kappa_s$ | With $\kappa_s$ | Note |
|---|---|---|---|
| Torsion, P1, MFAC 0.43, volume error | {{< label "kernel" "IB_4" >}}: 0.138 %; {{< label "kernel" "CBS43" >}}: 0.057 % | {{< label "kernel" "IB_4" >}}, $\nu_s = 0.4$: 0.099 % | {{< label "kernel" "CBS43" >}} without $\kappa_s$ beats {{< label "kernel" "IB_4" >}} with $\kappa_s$ |
| LV problem 2, P2 + {{< label "kernel" "CBS43" >}}, MFAC 0.40 | displacement 0.9 %, volume +0.06 % (needs `--kd 0.5`) | displacement 0.9 %, volume +0.05 % | keep $\kappa_D$ fixed when dt shrinks |
| MV | | $\beta_s = 5 \times 10^6$ (all runs) | |

#### (4) Element type: P1, P2, Q1, Q2

| Element | Torsion error, $n = 6$ (MFAC) | Cook error, $n = 16$ (MFAC) | MV runs |
|---|---|---|---|
| P1 tet | +16.2 % (1.43) | +0.89 % (1.86) | 0.0.3, {{< label "run" "G5" >}}, {{< label "run" "G6" >}} (full cycle) |
| P2 tet | +1.7 % (0.72) | +0.48 % (0.93) | {{< label "run" "G3" >}} / {{< label "run" "G4" >}}: failed (old non-conforming tet split) |
| Q1 hex | +5.0 % (1.19) | +1.43 % (1.33) | {{< label "run" "G7" >}}–{{< label "run" "G10" >}}: outlet backflow instability, see §5 |
| Q2 hex | not implemented | | |

#### (5) Fluid solver and convection

| Option | Status | Effect |
|---|---|---|
| Viscous term BE vs CN | CN in `ifed_bench` (`--viscous`) | |
| Convection central + AB2 | default | |
| Convection 2nd-order upwind (SOU) | `real_av` only (`--conv-upwind`); not in `gla_mv` | |
| Outlet backflow stabilisation | `--outlet-backflow`: feedback force $\kappa(0-U_z)$ on the outlet face, only where $U_z<0$, $\kappa = 0.5/\Delta t$ | removes the outlet-backflow failure ({{< label "run" "G7b" >}} restart: passes $t = 0.835$); does **not** remove the inlet-edge failure at $t \approx 0.86$–0.92 (G11: 1 of 4 runs completes, §5.5); changes the closing transient (§5.1) |

### 3.3 Validation against IBAMR

| Quantity | IBAMR | 0.0.3 (P1 tet) | {{< label "run" "G5" >}} (conforming tet) | {{< label "run" "G7" >}} (Q1 hex, IBAMR mesh) | {{< label "run" "G11" >}} (= G7 + outlet backflow stab.) |
|---|---|---|---|---|---|
| Forward volume 0.04–0.2 s (cm³) ‡ | 35.2 | 38.5 | 37.8 | 43.2 | 46.5* |
| Backflow volume 0.2–0.56 s (cm³) | −15.6 | −16.4 | −15.5 | −18.5 | −16.4 |
| Peak forward flow rate, 1st opening (cm³/s, 0.04 s frames) | 385 | 416 | 412 | 489 | 489 |
| Closing spike $Q(0.20\,\mathrm{s})$ (cm³/s) | −488 | −473 | −460 | −575 | −406 |
| Valve opening time (s) | | | | | |
| Valve closing time (s) | | | | | |
| Completed cycle | 0–0.65 s only | yes (5 of 6 runs) § | yes | no ($t \approx 0.9$ s) in the original run; yes in the 2026-10-15 rerun § | yes (1 of 4 runs) |

\* G11 equals G7 frame by frame up to $t = 0.16$ s; the larger 0.04–0.2 s volume comes only from the weaker spike in the
$t = 0.20$ frame entering the trapezoid. Peak and spike values for IBAMR are its inlet flux sampled at the same 0.04 s frames.

(volumes from REPORT.txt, tube flux at $z = 12$ cm, 0.04 s sampling; IBAMR at the inlet. §3.2 (1) quotes inlet-flux volumes, hence −17.3 vs −16.4 for 0.0.3)

§ *(2026-10-15)* Second-cycle outcomes are not deterministic: runs are bitwise identical to $t = 0.32$ s and then differ
by the summation order of the atomic adds; the second closed phase amplifies this into completion or NaN (§5.4).

‡ *(2026-10-15)* The forward volumes of the gla_mv runs are trapezoids from $t = 0.04$ s, not from 0 (`analyse_glamv_flow.py`:
`vol(t, q, 0.04, 0.2)`), so the first segment, $\tfrac12 Q(0.04)\,\Delta t \approx 1.1$ cm³, is not included. Over 0–0.2 s the same frames
give 39.6 cm³ (0.0.3) and 44.3 cm³ (G7). The IBAMR value (35.2) is quoted from `GLAMV_STATUS.md` (inlet flux); its window was not
re-derived here. The backflow windows (0.2–0.56 s, 0.88–1.24 s) are as labelled.

---

## 4. GPU acceleration

### 4.1 What runs on the GPU

All per-step work runs on the GPU: momentum (three face Helmholtz multigrid solves), pressure Poisson multigrid,
projection, convection, IB interpolation and spreading, solid force assembly (PK1, tethers, viscosity, penalties),
feedback forcing and gap mask. The host only writes output and logs.

### 4.2 Performance levels (fluid solver, `docs/GPU_PERFORMANCE.md`)

| Level | Switch | RTX 5070 Laptop, $256^3$ (ms/step) | RTX PRO 5000, $128^3$ | RTX PRO 5000, $256^3$ | Result vs level 0 |
|---|---|---|---|---|---|
| original | — | 496 | 39.2 | 197.5 | — |
| A | default | 240 | 22.8 | 100.7 | bitwise identical |
| B | `DSH_PERF_LEVEL=1` + FMA | 179 | 17.1 | 67.8 | ~$1 \times 10^{-13}$ |
| C | `DSH_PERF_LEVEL=2` + FMA | 126 | 11.0 | 43.8 | ≤ $1 \times 10^{-8}$ |
| D | `DSH_PERF_LEVEL=3` + FMA | 111 | 9.05 | 38.0 | ~$1 \times 10^{-8}$ |

Mitral-valve case (0.0.3 configuration, {{< label "grid" "G-64" >}}, P1 tets, RTX PRO 5000): 49.4 ms/step originally, 21.7 at level A,
10.1 at level D + FMA; a full cycle takes ≈ 11 min. IBAMR: ≈ 45 ms/step on 24 MPI ranks (1 h 38 min for 0.65 s).

### 4.3 Share of the simulation time per part

Measured alone on one RTX PRO 5000 at level D (ms/step):

| Run | Grid / solid | Fluid (Helmholtz + Poisson + projection + convection) | Interpolation + spreading | Solid assembly | Other | Total |
|---|---|---|---|---|---|---|
| 0.0.3 config | {{< label "grid" "G-64" >}} / glamv_ibamr (P1) | | | | | 10.1 |
| {{< label "run" "G7" >}} | {{< label "grid" "G-64" >}} / {{< label "mesh" "r0" >}} (Q1 + P1) | | | | | |
| {{< label "run" "G11" >}} | {{< label "grid" "G-64" >}} / {{< label "mesh" "r0" >}} (Q1 + P1), alone on the GPU | 7.82 | 0.83 (RK2 midpoint half-step) | 0.29 | 0.56 | 9.51 (full cycle 10.6 min) |
| {{< label "run" "G9" >}} | {{< label "grid" "G-64" >}} / {{< label "mesh" "r1" >}} | | | | | |
| {{< label "run" "G10" >}} | {{< label "grid" "G-128" >}} / {{< label "mesh" "r1" >}} | | | | | |
| | {{< label "grid" "G-256" >}} / {{< label "mesh" "r2" >}} | | | | | |

(the existing `[perf]` lines were recorded with two runs sharing the GPU; to be re-measured with one run)

---

## 5. Results

### 5.1 Run summary

| Run | Grid | Solid mesh | Leaflets | $\Delta t$ | Outcome | Forward 0.04–0.2 (cm³) ‡ | Backflow 0.2–0.56 (cm³) | $J_{\min}$ |
|---|---|---|---|---|---|---|---|---|
| 0.0.3 | {{< label "grid" "G-64" >}} | P1 tet (glamv_ibamr) | fibre HGO | $2 \times 10^{-5}$ | full cycle | 38.5 | −16.4 | 0.31 |
| 0.0.3 rerun, level 0 | {{< label "grid" "G-64" >}} | P1 tet (glamv_ibamr) | fibre HGO | $2 \times 10^{-5}$ | full cycle (near-collapse, $J_{\min}$ 0.14 at 1.16 s) | 38.5 | −16.3 | 0.14 |
| 0.0.3 rerun, level D | {{< label "grid" "G-64" >}} | P1 tet (glamv_ibamr) | fibre HGO | $2 \times 10^{-5}$ | **NaN $t = 1.2$** (posterior leaflet, §5.4) | 38.5 | −16.4 | 0.21 |
| 0.0.3 rerun, level D *(2026-10-13, RTX 5070 Laptop)* | {{< label "grid" "G-64" >}} | P1 tet (glamv_ibamr) | fibre HGO | $2 \times 10^{-5}$ | full cycle | 38.5 | −16.3 | 0.32 |
| 0.0.3 rerun, level 0 *(2026-10-15, RTX 5070 Laptop)* | {{< label "grid" "G-64" >}} | P1 tet (glamv_ibamr) | fibre HGO | $2 \times 10^{-5}$ | full cycle | 38.5 | −16.4 | 0.36 |
| 0.0.3 rerun, level D *(2026-10-15, RTX 5070 Laptop)* | {{< label "grid" "G-64" >}} | P1 tet (glamv_ibamr) | fibre HGO | $2 \times 10^{-5}$ | full cycle | 38.5 | −16.5 | 0.35 |
| {{< label "run" "G1d" >}} | {{< label "grid" "G-64" >}} | P1 tet (glamv_ibamr) | dispersed | $2 \times 10^{-5}$ | full cycle | 40.6 | −19.9 | 0.07 |
| {{< label "run" "G5" >}} | {{< label "grid" "G-64" >}} | P1 tet, conforming | fibre HGO | $2 \times 10^{-5}$ | full cycle | 37.8 | −15.5 | 0.21 |
| {{< label "run" "G6" >}} | {{< label "grid" "G-64" >}} | P1 tet, conforming | dispersed | $2 \times 10^{-5}$ | full cycle | 40.3 | −19.2 | 0.41 |
| {{< label "run" "G7" >}} | {{< label "grid" "G-64" >}} | {{< label "mesh" "r0" >}} Q1 + P1 | fibre HGO | $2 \times 10^{-5}$ | NaN $t \approx 0.9$ (outlet backflow) | 43.2 | −18.5 | 0.37 |
| {{< label "run" "G7" >}} rerun, level D *(2026-10-15, RTX 5070 Laptop)* | {{< label "grid" "G-64" >}} | {{< label "mesh" "r0" >}} Q1 + P1 | fibre HGO | $2 \times 10^{-5}$ | full cycle (bitwise identical flow to the original up to $t = 0.32$ s) | 43.2 | −18.6 | 0.32 |
| {{< label "run" "G7b" >}} | {{< label "grid" "G-64" >}} | {{< label "mesh" "r0" >}} | fibre HGO | $1 \times 10^{-5}$ | NaN $t \approx 0.84$ (outlet backflow) | 43.1 | −19.6 | 0.47 |
| {{< label "run" "G8" >}} | {{< label "grid" "G-64" >}} | {{< label "mesh" "r0" >}} | dispersed | $2 \times 10^{-5}$ | NaN $t \approx 0.96$ | 47.5 | −21.2 | 0.45 |
| {{< label "run" "G9" >}} | {{< label "grid" "G-64" >}} | {{< label "mesh" "r1" >}} | dispersed | $2 \times 10^{-5}$ | NaN $t \approx 0.92$ | 47.6 | −12.7 | 0.16 |
| {{< label "run" "G10" >}} | {{< label "grid" "G-128" >}} | {{< label "mesh" "r1" >}} | dispersed | $1 \times 10^{-5}$ | NaN $t \approx 0.78$ (solid degraded: $J_{\min}$ 0.03, $I_{1,\max}$ 152) | 67.3† | −12.9† | 0.03 |
| **{{< label "run" "G11" >}}** | {{< label "grid" "G-64" >}} | {{< label "mesh" "r0" >}} Q1 + P1 | fibre HGO | $2 \times 10^{-5}$ | full cycle in 1 of 4 runs (`--outlet-backflow`; reruns: NaN at 0.86–0.92 s, inlet edge) | 46.5* | −16.4 | 0.36 |
| | {{< label "grid" "G-256" >}} | {{< label "mesh" "r2" >}} | | | | | | |

\* see §3.3: identical to G7 up to $t = 0.16$ s; the difference is the 0.04 s sampling of the closing spike.
† G10 writes frames every 0.02 s, so its volumes are not sampled like the others.

**Outlet backflow on the hex meshes.** On the hex meshes the valve opens wider (first-opening plateau ≈ 485 cm³/s
against ≈ 410 on the tet meshes, Figure 1) and the jet reaches the outlet with recirculation; without stabilisation
the backflow through the outlet grows until the run fails ({{< label "run" "G7" >}}–{{< label "run" "G10" >}}). With
`--outlet-backflow` the coarsest pair ({{< label "run" "G11" >}}, {{< label "mesh" "r0 @ G-64" >}}) ran through the whole 1.335 s once, with
$J_{\min} = 0.36$ and $I_{1,\max} = 6.1$ (three reruns fail at the inlet edge at $t \approx 0.91$ s, §5.5); in that run:

- Up to $t = 0.16$ s G11 and G7 agree frame by frame (the term is inactive while the outlet flows out).
- The term acts on the closing transient: the spike at $t = 0.20$ s drops from −575 (G7) to −406 cm³/s (IBAMR −488), and
  the backflow volume 0.20–0.56 s moves from −18.5 to −16.4 cm³ (IBAMR −15.6).
- Second cycle: the forward plateau stays ≈ 20 % above the tet runs (Q ≈ 400–480 vs 310–400 cm³/s), and the
  second closure is delayed — at $t = 0.92$/0.96 s G11 still has $Q = +34$/+4.5 cm³/s where 0.0.3 and G5 show the closing
  spike (−89/−100). The closed-phase leak from 1.00 s on (−48 … −10 cm³/s) matches the tet runs.
- The stabilisation does **not** remove the recirculation itself: one cell below the outlet, 61–84 % of the lumen still
  has $w<0$ in the first closed phase (0.28–0.52 s; tet runs 51–82 %) and 65–77 % in the second (1.00–1.24 s; tet runs
  57–64 %, Figure 2). It only stops reverse flow from entering through the outlet face and feeding on itself.

Leakage check (tube flux at $z = 3$, 5.5, 9, 12 cm against $z = 12$ cm, every 0.04 s frame) and the gap outside the tube
(§2.4):

| Run | $\max\lvert Q(z)-Q(12)\rvert / \max\lvert Q\rvert$ | max gap flux, $r>3.8$ (cm³/s) | max $\lvert\mathbf u\rvert$ outside the wall (cm/s) | frames |
|---|---|---|---|---|
| 0.0.3 | 0.38 % | 0.018 | 0.106 | 35 |
| {{< label "run" "G5" >}} | 0.36 % | 0.017 | 0.118 | 35 |
| {{< label "run" "G6" >}} | 0.38 % | 0.017 | 0.097 | 35 |
| {{< label "run" "G7" >}} | 0.43 % | 0.016 | 0.230 (at $t = 0.88$, before NaN) | 23 |
| {{< label "run" "G8" >}} | 0.40 % | 0.013 | 0.097 | 24 |
| {{< label "run" "G11" >}} | 0.36 % | 0.013 | 0.074 | 35 |

Flux along the tube is conserved to < 0.5 % in every run, so the tube wall does not leak at MFAC 1.6 on {{< label "grid" "G-64" >}}.

{{< chart height="340" xlabel="t (s)" ylabel="Q through the tube lumen, z = 12 cm (cm³/s)" colors="#d1495b,#edae49,#00798c,#30638e,#7a7a7a" caption="Figure 1. Flow rate through the tube lumen (r < 3.5 cm) at z = 12 cm, fluid frames every 0.04 s. G11 = r0 hex @ G-64 with outlet backflow stabilisation; G7 = same without it (NaN after 0.88 s); G5 = conforming P1 tets; 0.0.3 = glamv_ibamr P1 tets; IBAMR = inlet flux of the reference run (to 0.65 s) sampled at the same frames." >}}
t, G11 (hex + outlet stab.), G7 (hex), G5 (tet conf.), 0.0.3 (tet), IBAMR
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
t, G11 (hex + outlet stab.), G7 (hex), G5 (tet conf.), 0.0.3 (tet)
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
t, G11 (hex + outlet stab.), G7 (hex), G5 (tet conf.), 0.0.3 (tet)
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

| Analysis | {{< label "grid" "G-64" >}} | {{< label "grid" "G-128" >}} | {{< label "grid" "G-256" >}} | IBAMR |
|---|---|---|---|---|
| Flow rate vs time (inlet / tube sections) | Figure 1 ({{< label "run" "G11" >}}, G7, G5, 0.0.3) | | | Figure 1 (to 0.65 s) |
| Streamlines (opening, peak, closure) | | | | |
| Vorticity (mid-plane, transverse sections) | | | | |
| Vortex ring formation and breakdown (large → small eddies) | | | | |
| Q-criterion iso-surfaces | | | | |
| Energy dissipation rate $\varepsilon = 2\mu\,\mathbf{S}:\mathbf{S}$ (volume integral vs time) | | | | |
| Turbulent kinetic energy / spectra downstream of the valve | | | | |

### 5.3 Solid

| Analysis | {{< label "grid" "G-64" >}} / {{< label "mesh" "r0" >}} | {{< label "grid" "G-128" >}} / {{< label "mesh" "r1" >}} | {{< label "grid" "G-256" >}} / {{< label "mesh" "r2" >}} | IBAMR |
|---|---|---|---|---|
| Leaflet displacement (tip, belly) vs time | | | | |
| Orifice area vs time | | | | |
| Stress (first principal / von Mises) at peak opening and closure | | | | |
| Volume change, $J$ range (all cells / leaflets) | | | | |
| Chordae tension vs time | | | | |

### 5.4 Reproducibility of the reference run and where it fails

The reference configuration (0.0.3: `glamv_ibamr`, i.e. the IBAMR mesh with every hex split into 6 P1 tets,
80,074 tets on the same 29,524 nodes as {{< label "mesh" "r0" >}}; CBS43, passive rim, gap mask, {{< label "grid" "G-64" >}}, $\Delta t = 2\times10^{-5}$)
was rerun on 2026-10-14 with the current code and the identical command line, twice:

| Run | GPU path | Outcome | Agreement with the original | $J_{\min}$ over the cycle |
|---|---|---|---|---|
| 0.0.3 original (2026-10-10) | pre-optimisation (≈ 54 ms/step) | full cycle | — | 0.31 (at 0.52 s) |
| rerun, `DSH_PERF_LEVEL=0` | level A (19.6 ms/step) | full cycle | bitwise identical to $t = 0.32$ s, last digits differ afterwards | **0.14** (at 1.16 s) |
| rerun, `DSH_PERF_LEVEL=3` | level D + FMA (≈ 9.5 ms/step) | **NaN at $t = 1.20$ s** | log values identical to $t = 0.32$ s, differences ~$10^{-8}$ | 0.21 (at 1.16 s, then NaN) |
| rerun, level D + FMA *(2026-10-13, RTX 5070 Laptop)* | 8.9 ms/step | full cycle | flow rates identical to the original at every 0.04 s frame to $t = 0.20$ s | 0.32 (at 1.24 s) |
| rerun, `DSH_PERF_LEVEL=0` *(2026-10-15, RTX 5070 Laptop)* | level A, 19.1 ms/step | full cycle | same | 0.36 (at 0.52 s) |
| rerun, level D + FMA *(2026-10-15, RTX 5070 Laptop, merged code `a871fa0`)* | ≈ 8.9 ms/step | full cycle | same | 0.35 (at 0.40 s) |

Findings:

1. **The current code reproduces the original.** At level 0 every logged quantity is bitwise identical up to
   $t = 0.32$ s. The first differences after that come from summation order (atomic adds in spreading), not from a code
   change: the run is not bitwise deterministic from step to step on the GPU.
2. **The flow is robust to these perturbations, the leaflet is not.** All three runs give the same forward (38.5 cm³) and
   backflow volumes (−16.3 … −16.4 cm³). But in the second closed phase ($t \approx 1.04$–1.24 s) all three pass through a
   local collapse of the **posterior leaflet (marker 4) next to a chordae insertion**, at $(x, y, z) \approx (5.1$–$5.4,\ 4.6$–$5.0,\ 5.2$–$5.4)$ cm,
   where the worst chordae cell (marker 100) also sits. Its depth decides the outcome: original $J_{\min} = 0.47$ there,
   level-0 rerun 0.14 (recovers), level-D rerun 0.21 with 15 cells below $J = 0.5$ and growing → force blow-up
   (max |f| 1.5e5 → 5.5e5 from 1.04 to 1.16 s), then $\lvert\nabla\cdot\mathbf u\rvert$ jumps to $8\times10^{-4}$ and the run fails.
3. So the success of 0.0.3 is **marginal**: round-off-level differences decide between finishing and NaN. The
   performance level is not itself the cause (level 0 and level D give the same flow), it only gives a different
   perturbation.
4. **The hex runs fail differently.** {{< label "run" "G7" >}} keeps $J_{\min} = 0.37$ and fails first in the fluid: max |u| stays flat while
   $\lvert\nabla\cdot\mathbf u\rvert$ rises from $10^{-8}$ to $6\times10^{-4}$ in the last 0.02–0.04 s, driven by inflow through the outlet (§5.1). A restart
   from $t = 0.8$ s at level 0 fails as well (NaN at 0.91 s), so this is not a level-D effect either. With outlet stabilisation
   ({{< label "run" "G11" >}}) the hex mesh keeps $J_{\min} \ge 0.36$ through the second cycle and shows **no** posterior-leaflet collapse
   (Figure 4).
5. The refined meshes add a third failure mode: {{< label "run" "G10" >}} ({{< label "mesh" "r1 @ G-128" >}}) degrades in the solid ($J_{\min} = 0.03$,
   $I_{1,\max} = 152$) before failing at 0.78 s.

6. *(2026-10-15)* **Six runs of 0.0.3 so far: five complete, one fails** (level D, 1.20 s), with $J_{\min}$ between 0.14 and 0.36;
   all six give forward 38.5 cm³ and backflow −16.3 … −16.5 cm³. The same holds for the hex mesh: a rerun of {{< label "run" "G7" >}} on another
   GPU (RTX 5070 Laptop, level D, merged code) is identical to the original flow rate at every printed digit to $t = 0.32$ s
   (Q at $z = 12$ cm: 55.41, 367.93, 488.52, 482.01, −574.79 cm³/s at 0.04 … 0.20 s), gives forward 43.2 and backflow −18.6 cm³, and
   then **completes the cycle** ($J_{\min}$ 0.32 at 0.88 s; second backflow 0.88–1.24 s −2.7 cm³), where the original failed at 0.92 s.
   So the G7 failure at 0.92 s is also not deterministic, and changing the solid mesh (P1 tets → Q1 hexes + P1 tets) gives the same
   result on two machines up to the point where round-off takes over. Outcome and $J_{\min}$ of the second cycle should be reported
   as a range over several runs, not as a single value.

Where to look next: the posterior-leaflet / chordae-insertion region (element quality of the 6-tet split there,
chordae–leaflet force transfer, MFAC 0.34 of the chordae); and making the second closure deterministic enough to
compare (e.g. a fixed-order spreading for verification runs).

{{< chart height="300" xlabel="t (s)" ylabel="J_min (all active cells)" colors="#30638e,#00798c,#d1495b,#edae49" caption="Figure 4. Smallest element volume ratio over the cycle (solid_stats.csv, every 0.04 s). Three runs of the same reference configuration (original, rerun at performance level 0, rerun at level D) agree to t = 0.32 s and then split; in the second closed phase the posterior leaflet collapses locally in both reruns (0.14 and 0.21), and the level-D run fails at t = 1.20 s. G11 (hex mesh, outlet stabilisation) is shown for comparison." >}}
t, 0.0.3 original, rerun level 0, rerun level D, G11 (hex)
0.00, 1.000, 1.000, 1.000, 1.000
0.04, 0.984, 0.984, 0.984, 0.989
0.08, 0.817, 0.817, 0.817, 0.863
0.12, 0.764, 0.764, 0.764, 0.685
0.16, 0.712, 0.712, 0.712, 0.493
0.20, 0.607, 0.607, 0.607, 0.732
0.24, 0.665, 0.665, 0.665, 0.653
0.28, 0.621, 0.621, 0.621, 0.638
0.32, 0.472, 0.472, 0.472, 0.579
0.36, 0.389, 0.389, 0.385, 0.555
0.40, 0.386, 0.386, 0.364, 0.565
0.44, 0.403, 0.404, 0.355, 0.535
0.48, 0.455, 0.505, 0.411, 0.566
0.52, 0.308, 0.357, 0.466, 0.589
0.56, 0.535, 0.523, 0.494, 0.665
0.60, 0.646, 0.718, 0.611, 0.712
0.64, 0.654, 0.637, 0.676, 0.622
0.68, 0.590, 0.627, 0.553, 0.494
0.72, 0.588, 0.589, 0.593, 0.467
0.76, 0.615, 0.540, 0.543, 0.477
0.80, 0.555, 0.565, 0.555, 0.433
0.84, 0.590, 0.474, 0.533, 0.357
0.88, 0.550, 0.507, 0.540, 0.368
0.92, 0.636, 0.594, 0.624, 0.473
0.96, 0.571, 0.641, 0.381, 0.519
1.00, 0.591, 0.584, 0.421, 0.499
1.04, 0.541, 0.406, 0.404, 0.527
1.08, 0.469, 0.252, 0.361, 0.498
1.12, 0.485, 0.153, 0.289, 0.512
1.16, 0.493, 0.142, 0.210, 0.513
1.20, 0.506, 0.156, , 0.513
1.24, 0.476, 0.178, , 0.503
1.28, 0.532, 0.281, , 0.551
1.32, 0.583, 0.476, , 0.573
1.335, 0.580, 0.575, , 0.619
{{< /chart >}}

### 5.5 G11 on the hex mesh: one full cycle, two failed reruns, and where the failures come from

**Result.** {{< label "run" "G11" >}} ({{< label "mesh" "r0 @ G-64" >}}: IBAMR mesh, 11,565 Q1 hexes + 10,686 P1 tets; fibre HGO leaflets; CBS43;
$\beta_s = 5\times10^6$; passive rim + gap mask; $\Delta t = 2\times10^{-5}$; `--outlet-backflow`) ran from $t = 0$ to 1.335 s without a
NaN, at 9.5 ms/step (10.6 min), command in `fdm-3d-v1-gpu/run_hex_bf.sh`. The same configuration without
`--outlet-backflow` ({{< label "run" "G7" >}}) fails at $t \approx 0.92$ s. Flow, outlet recirculation and $J_{\min}$ of G11 are in Figures 1–4.

**The success is not reproducible.** Rerun with identical settings (only the frame interval changed, which does not
enter the numerics), G11 agrees with the first run bitwise to $t = 0.28$ s, then differs in the last digits (GPU
summation order) and fails at $t = 0.92$ s; a $\Delta t = 10^{-5}$ run fails at $t = 0.91$ s:

| Run (all: {{< label "mesh" "r0 @ G-64" >}}, CBS43, `--outlet-backflow`) | $\Delta t$ | Frames | Outcome | Fluid speed before the NaN |
|---|---|---|---|---|
| G11, first run | $2\times10^{-5}$ | 0.04 s | full cycle ($\lvert\nabla\cdot\mathbf u\rvert$ peaks $2.8\times10^{-7}$ at 0.88 s, recovers) | — |
| G11 rerun | $2\times10^{-5}$ | 0.01 s | NaN at $t = 0.92$ s | 1,300 cm/s on the **inlet face**, $r = 3.2$ cm (t = 0.91) |
| G11 rerun | $10^{-5}$ | 0.01 s | NaN at $t = 0.91$ s | 2,600 cm/s on the **inlet face**, $r = 3.3$ cm (t = 0.90) |

The first cycle is the same in all runs and independent of $\Delta t$ (Figure 5, Table below); only the second-cycle
outcome is a matter of chance, decided at the end of the second forward phase ($t \approx 0.88$–0.91 s, just before the inlet
pressure reverses for the second closure).

A third rerun with frames every 0.005 s (`EVERY=250`) fails at $t = 0.86$ s, again on the inlet rim ($r \approx 3.1$–3.3 cm).
Its 172 frames give the finely sampled flow rate of Figure 5, at the same 0.005 s spacing as IBAMR's output.
Valve metrics of the first cycle (flux through the lumen; closure/reopening = zero crossings, linearly interpolated;
reopening = last upward crossing before the second forward phase; volumes = trapezoid between them):

| First cycle | G11 rerun, 0.005 s ($\Delta t = 2\times10^{-5}$) | G11 rerun, 0.01 s ($\Delta t = 2\times10^{-5}$) | G11 rerun, 0.01 s ($\Delta t = 10^{-5}$) | IBAMR (inlet, 0.005 s) |
|---|---|---|---|---|
| Peak forward flow (cm³/s) | 490.6 at 0.13 s | 490.6 at 0.13 s | 490.5 at 0.13 s | 385.0 at 0.16 s |
| Valve closure (s) | 0.182 | 0.182 | 0.183 | 0.179 |
| Closing spike (cm³/s) | −406 at 0.20 s | −406 at 0.20 s | −294 at 0.20 s | −516 at 0.195 s |
| Reopening (s) | 0.527 | 0.525 | 0.528 | 0.513 |
| Forward volume, 0 → closure (cm³) | 52.1 | 51.9 | 51.9 | 41.0 |
| Backflow volume, closure → reopening (cm³) | −16.4 | −15.4 | −15.5 | −13.8 |
| Second-cycle peak (cm³/s) | 617 at 0.64 s | 612 at 0.64 s | 625 | — (IBAMR ends at 0.65 s) |

Valve timing matches IBAMR within 0.003 s (closure) and 0.014 s (reopening); the hex leaflets pass 27 % more forward
volume and 19 % more backflow. The closing spike depends on $\Delta t$ because the outlet term's $\kappa = 0.5/\Delta t$ doubles when
$\Delta t$ is halved.

{{< chart height="360" xlabel="t (s)" ylabel="Q through the tube lumen (cm³/s)" colors="#d1495b,#7a7a7a" caption="Figure 5. Flow rate every 0.005 s (172 samples, t = 0–0.855 s) of the G11 rerun (r0 hex mesh @ G-64, outlet backflow stabilisation, Δt = 2×10⁻⁵; lumen flux at z = 12 cm), against the IBAMR reference (inlet flux, 0.005 s output, to 0.65 s). The rerun fails at t = 0.86 s on the inlet rim; the first full run of G11 (Figure 1) is the only one that completed the cycle." >}}
t, G11 rerun (hex + outlet stab.) Q z = 12 cm, IBAMR inlet Q
0.000, 0.0, 0.0
0.005, 0.0, 1.7
0.010, 0.0, 1.6
0.015, 0.0, 0.8
0.020, 0.0, 2.1
0.025, 4.1, 5.7
0.030, 15.5, 16.9
0.035, 32.8, 34.2
0.040, 55.4, 57.0
0.045, 82.9, 82.0
0.050, 115.4, 111.8
0.055, 152.7, 144.8
0.060, 194.5, 179.3
0.065, 239.6, 215.2
0.070, 286.8, 253.1
0.075, 331.0, 283.8
0.080, 367.9, 309.3
0.085, 398.7, 328.1
0.090, 424.1, 345.0
0.095, 444.3, 358.9
0.100, 460.4, 370.0
0.105, 472.6, 378.9
0.110, 480.4, 381.6
0.115, 485.0, 379.4
0.120, 488.5, 373.9
0.125, 490.0, 368.0
0.130, 490.6, 364.3
0.135, 490.6, 362.4
0.140, 489.6, 363.7
0.145, 486.5, 366.3
0.150, 483.0, 370.9
0.155, 483.9, 379.1
0.160, 482.0, 385.0
0.165, 427.1, 333.5
0.170, 327.1, 239.1
0.175, 206.4, 122.5
0.180, 57.5, -24.7
0.185, -100.3, -196.6
0.190, -237.4, -371.8
0.195, -345.2, -515.6
0.200, -406.1, -488.2
0.205, -358.5, -174.2
0.210, -161.6, 13.8
0.215, -6.1, 10.2
0.220, 10.4, 5.3
0.225, -38.8, 2.6
0.230, -80.5, -2.5
0.235, -86.2, -8.8
0.240, -68.6, -27.3
0.245, -53.1, -65.8
0.250, -48.0, -76.2
0.255, -48.7, -50.8
0.260, -46.7, -18.3
0.265, -44.5, -12.7
0.270, -43.7, -22.4
0.275, -44.2, -46.3
0.280, -44.9, -55.5
0.285, -43.6, -38.7
0.290, -40.4, -19.1
0.295, -36.9, -14.7
0.300, -34.9, -17.4
0.305, -33.9, -26.6
0.310, -33.3, -29.1
0.315, -32.7, -24.9
0.320, -31.7, -19.9
0.325, -30.0, -16.5
0.330, -28.2, -15.1
0.335, -27.1, -17.2
0.340, -26.2, -18.5
0.345, -25.0, -19.5
0.350, -24.7, -19.2
0.355, -26.6, -18.8
0.360, -27.5, -19.2
0.365, -27.5, -18.3
0.370, -26.4, -17.8
0.375, -26.1, -17.5
0.380, -25.6, -15.6
0.385, -23.9, -16.0
0.390, -22.3, -14.9
0.395, -21.7, -14.4
0.400, -22.9, -13.7
0.405, -22.6, -13.3
0.410, -21.8, -13.7
0.415, -22.2, -12.8
0.420, -23.4, -12.3
0.425, -23.1, -12.7
0.430, -21.9, -12.2
0.435, -20.6, -11.3
0.440, -19.4, -11.2
0.445, -18.4, -10.3
0.450, -19.3, -10.2
0.455, -19.6, -9.8
0.460, -18.3, -9.8
0.465, -16.9, -8.5
0.470, -15.6, -8.6
0.475, -14.3, -7.0
0.480, -13.1, -7.0
0.485, -11.2, -5.3
0.490, -10.2, -4.2
0.495, -10.1, -3.5
0.500, -9.3, -2.6
0.505, -7.9, -1.5
0.510, -6.6, -0.8
0.515, -4.3, 0.4
0.520, -2.6, 0.8
0.525, -1.0, 1.6
0.530, 1.6, 2.8
0.535, 6.7, 4.0
0.540, 13.4, 5.8
0.545, 21.7, 7.7
0.550, 30.2, 9.9
0.555, 38.8, 12.6
0.560, 46.7, 15.0
0.565, 55.2, 17.7
0.570, 62.8, 19.7
0.575, 68.7, 21.4
0.580, 72.5, 22.5
0.585, 73.8, 23.5
0.590, 74.6, 23.8
0.595, 126.8, 352.2
0.600, 189.7, 451.8
0.605, 273.5, 514.0
0.610, 354.0, 526.1
0.615, 432.7, 510.5
0.620, 498.7, 516.5
0.625, 549.1, 538.9
0.630, 586.5, 547.4
0.635, 608.7, 545.8
0.640, 617.1, 535.5
0.645, 614.0, 505.5
0.650, 604.8, 474.9
0.655, 591.9, 
0.660, 578.0, 
0.665, 563.6, 
0.670, 549.6, 
0.675, 536.5, 
0.680, 527.0, 
0.685, 519.6, 
0.690, 514.8, 
0.695, 509.9, 
0.700, 502.7, 
0.705, 496.5, 
0.710, 488.8, 
0.715, 484.6, 
0.720, 479.1, 
0.725, 475.4, 
0.730, 471.0, 
0.735, 470.2, 
0.740, 466.9, 
0.745, 459.4, 
0.750, 456.3, 
0.755, 452.8, 
0.760, 448.5, 
0.765, 444.4, 
0.770, 440.6, 
0.775, 437.0, 
0.780, 434.7, 
0.785, 435.8, 
0.790, 435.5, 
0.795, 434.4, 
0.800, 433.8, 
0.805, 433.7, 
0.810, 431.5, 
0.815, 428.4, 
0.820, 425.2, 
0.825, 424.5, 
0.830, 424.4, 
0.835, 422.9, 
0.840, 424.5, 
0.845, 436.2, 
0.850, 442.3, 
0.855, 492.6,
{{< /chart >}}

**What `--outlet-backflow` does.** On the whole outlet face ($z = 16.2$ cm) it adds the feedback force
$f_z = \kappa\,(0 - w)$ with $\kappa = 0.5/\Delta t$, **only where $w < 0$** (fluid entering the domain). Outflow and the tangential
velocities are untouched; incoming normal velocity is halved every step ($\kappa\Delta t = 0.5$, explicit). An open outlet
lets inflowing fluid carry kinetic energy into the domain with nothing to remove it — the classical backflow
instability of open boundaries. This is what fails in G7b ($\Delta t = 10^{-5}$) at the outlet, and the term removes that energy source. It is a
model change, not only a numerical one: it also weakens the closing spike (−575 → −406 cm³/s) and delays the second
closure (§5.1).

**Is the failure a fluid-solver accuracy problem? No.** G7 was restarted from its $t = 0.8$ s checkpoint with
**4× more multigrid V-cycles** per step (32 Poisson / 6 Helmholtz instead of 8 / 2), everything else unchanged:

| G7 restart from $t = 0.8$ s | V-cycles (Poisson / Helmholtz) | $\lvert\nabla\cdot\mathbf u\rvert$ at $t = 0.805$ | $\lvert\nabla\cdot\mathbf u\rvert$ at $t = 0.895$ | Outcome |
|---|---|---|---|---|
| level D | 8 / 2 | $2.55\times10^{-8}$ | $3.93\times10^{-6}$ | NaN at $t = 0.905$ s |
| level 0 | 8 / 2 | | | NaN at $t = 0.91$ s |
| level D | **32 / 6** | $2.55\times10^{-8}$ | $3.99\times10^{-6}$ | NaN at $t = 0.915$ s |
| G7b ($\Delta t = 10^{-5}$) restart, level D, no stabilisation | 8 / 2 | | | NaN at $t = 0.835$ s |
| G7b restart, level D, **`--outlet-backflow`** | 8 / 2 | | $3\times10^{-9}$ (at 0.8275) | passes 0.835 s; test ended at 0.845 s |

The pressure solve is already converged at 8 V-cycles (identical divergence to three digits), and a more accurate
fluid solve fails at the same time. **Where** they fail (fastest fluid in the last frames before the NaN):

| Run | Location of the blow-up | Time |
|---|---|---|
| G7 restarts at $\Delta t = 2\times10^{-5}$ (8/2 and 32/6 V-cycles) | **inlet face** $z = 0$, $r \approx 2.8$–3.3 cm (inflow jets 1,250 → 3,400 cm/s) | 0.89–0.915 s |
| G7b at $\Delta t = 10^{-5}$, no stabilisation | **outlet face** $z = 16.2$ cm, $r \approx 2.2$–2.6 cm (backflow) | 0.83 s |
| G11 reruns (outlet stabilised), $\Delta t = 2\times10^{-5}$ and $10^{-5}$ | **inlet face**, $r \approx 3.2$–3.4 cm | 0.90–0.91 s |

So there are **two boundary instabilities**: the outlet one, which `--outlet-backflow` cures, and an **inlet-edge** one
that is not yet treated. The inlet failure sits in the transition band at the rim of the inlet disc: the lumen
($r < 3.5$ cm) carries the prescribed pressure, the rest of the face is held at zero velocity by feedback forcing, and the
two are blended over $\approx 2$ grid cells ($r \approx 3.2$–3.5 cm, Delta4 weight). On the hex mesh the second-cycle inflow is
≈ 20 % higher than on the tet meshes (Q ≈ 400–450 vs 310–330 cm³/s), which is why only the hex runs reach it. Candidate
remedies: a sharper or wider inlet transition, inflow stabilisation at the inlet rim, or a longer inlet tube. For the tet reference run the fluid is
likewise accurate ($\lvert\nabla\cdot\mathbf u\rvert \le 7\times10^{-8}$) while the posterior leaflet collapses (§5.4): there the fluid is the victim,
not the cause. (A tet run with 32/6 V-cycles was interrupted at $t = 0.69$ s; to be resumed from its checkpoint.)

**Which ingredients are needed for a stable run** (evidence from the run register):

| Ingredient | Varied in MV runs? | Evidence | Needed for stability? |
|---|---|---|---|
| Passive rim + gap mask | yes (0.0.1 → 0.0.2) | without passive rim: NaN at 0.84–0.88 s, housing-disc rim torn | **yes** |
| `--outlet-backflow` | yes (G7 → G11) | removes the outlet failure (G7b); hex runs still fail at the inlet edge in 3 of 4 runs; tet runs finish without | **yes on hex, not sufficient** |
| Inlet-edge treatment | **no** | hex failures at $t \approx 0.86$–0.92 s start on the inlet face at the disc rim | **likely needed on hex** (to be built) |
| Kernel {{< label "kernel" "CBS43" >}} | yes (0.0.2 → 0.0.3) | {{< label "kernel" "BSPLINE_3" >}} also completes the cycle; CBS43 raises $J_{\min}$ 0.14 → 0.31 and lowers the closed-phase leak; {{< label "kernel" "CBS32" >}} is *less* stable | no — accuracy, not stability |
| $\kappa_s$ ($\beta_s = 5\times10^6$) | **no** (all runs $5\times10^6$) | with unmodified invariants it is the only volumetric term (torsion benchmark without it: wrong sign, −17 % volume) | must be present; value untested |
| Stress form (unmodified invariants, as IBAMR) | **no** | benchmarks favour modified invariants / deviatoric projection for accuracy | unknown; not the cause of any failure so far |

Next tests for the tet weak point (posterior-leaflet collapse at $t \approx 1.1$ s): larger $\beta_s$ ($10^7$, $2\times10^7$, with a $\Delta t$
check) and modified invariants on the leaflets, each compared on $J_{\min}$ against the level-0 rerun (0.14).

---

## 6. Discussion

Key findings so far (coarsest pair {{< label "mesh" "r0 @ G-64" >}}, 2026-10-14):

1. **The hybrid hex/tet IBAMR mesh can run a full cycle on the GPU, but not reliably** ({{< label "run" "G11" >}}: 1.335 s in
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
   (the G11 vs G7 forward-volume difference is entirely this). Per-step flux output is needed before timing
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

All repositories are private (branch `glamv-cbspline`); links need a signed-in GitHub account with access.

| What | Where |
|---|---|
| Run register ({{< label "run" "G1" >}}–{{< label "run" "G11" >}}) | [`GLAMV_STATUS.md`](https://github.com/mapengfei-glasgow/fdm-3d-v1-workspace/blob/6e434b9/GLAMV_STATUS.md) |
| Derived data behind §5.1 and Figures 1–3 (per-frame flux CSVs, `summary.csv`, chart tables) | [`glamv_results/`](https://github.com/mapengfei-glasgow/fdm-3d-v1-workspace/tree/6e434b9/glamv_results) |
| G11 logs (`sim.log`, `solid_stats.csv`, console) | [`glamv_results/G11_hex_r0_N64_outlet_backflow/`](https://github.com/mapengfei-glasgow/fdm-3d-v1-workspace/tree/6e434b9/glamv_results/G11_hex_r0_N64_outlet_backflow) |
| 0.0.3 reruns (§5.4): logs, `solid_stats.csv`, worst-J diagnostics | [`rerun_0.0.3_level0/`](https://github.com/mapengfei-glasgow/fdm-3d-v1-workspace/tree/6e434b9/glamv_results/rerun_0.0.3_level0), [`rerun_0.0.3_levelD/`](https://github.com/mapengfei-glasgow/fdm-3d-v1-workspace/tree/6e434b9/glamv_results/rerun_0.0.3_levelD) |
| G11 reruns (0.005 s / 0.01 s frames, $\Delta t$ = 2e-5 / 1e-5): logs, per-frame flow CSVs (Figure 5), valve metrics (`dense.txt`) | [`G11_rerun_every250/`](https://github.com/mapengfei-glasgow/fdm-3d-v1-workspace/tree/6e434b9/glamv_results/G11_rerun_every250), [`G11_rerun_every500/`](https://github.com/mapengfei-glasgow/fdm-3d-v1-workspace/tree/6e434b9/glamv_results/G11_rerun_every500), [`G11_rerun_dt1e-5/`](https://github.com/mapengfei-glasgow/fdm-3d-v1-workspace/tree/6e434b9/glamv_results/G11_rerun_dt1e-5) |
| Failed hex runs (G7, G7b + restarts incl. the 32/6 V-cycle test, G8, G9, G10): logs, solid stats, flow CSVs | [`failed_hex/`](https://github.com/mapengfei-glasgow/fdm-3d-v1-workspace/tree/6e434b9/glamv_results/failed_hex) |
| Analysis scripts | [`glamv_flow_dense.py`](https://github.com/mapengfei-glasgow/fdm-3d-v1-workspace/blob/6e434b9/glamv_flow_dense.py), [`diag_worst_J_tet.py`](https://github.com/mapengfei-glasgow/fdm-3d-v1-workspace/blob/6e434b9/diag_worst_J_tet.py), [`analyse_glamv_flow.py`](https://github.com/mapengfei-glasgow/fdm-3d-v1-workspace/blob/6e434b9/analyse_glamv_flow.py), [`glamv_chart_tables.py`](https://github.com/mapengfei-glasgow/fdm-3d-v1-workspace/blob/6e434b9/glamv_chart_tables.py) |
| IBAMR reference flux | [`MV_flowrate_ibamr.csv`](https://github.com/mapengfei-glasgow/fdm-3d-v1-workspace/blob/6e434b9/MV_flowrate_ibamr.csv) |
| G11 run script (exact command line) | [`run_hex_bf.sh`](https://github.com/mapengfei-glasgow/fdm-3d-v1-gpu/blob/80c507f/run_hex_bf.sh) |
| Solver (`gla_mv`, incl. `--outlet-backflow`, gap mask, passive rim) | [`demo/gla_mv.cu`](https://github.com/mapengfei-glasgow/fdm-3d-v1-gpu/blob/80c507f/demo/gla_mv.cu), commit [`80c507f`](https://github.com/mapengfei-glasgow/fdm-3d-v1-gpu/commit/80c507f) |
| Base solid mesh (P1 tet, in git) | [`src/ibm/data/glamv_ibamr/`](https://github.com/mapengfei-glasgow/fdm-3d-v1-geometry/tree/glamv-cbspline/src/ibm/data/glamv_ibamr) |
| Hex mesh generator ({{< label "mesh" "r0" >}}, {{< label "mesh" "r1" >}}) | [`scripts/gen_glamv_hex.py`](https://github.com/mapengfei-glasgow/fdm-3d-v1-geometry/blob/glamv-cbspline/scripts/gen_glamv_hex.py) |
| Raw outputs (35 × `fluid_*.vti`, `Xc_*.bin`, checkpoint; ≈ 1.3 GB per run) | not uploaded — workstation `fdm-3d-v1-gpu/out_mv_hex_bf_cbs43/` (G11), `out_mv_sarah_pfull_T1335_passiverim_cbs43_rerun20261014{,_L0}/` (reruns), `out_mv_hex*` (failed hex runs); `python3 scripts/run_to_vtu.py <dir>` → ParaView |

### Rerunning G11 step by step

Tested on: Ubuntu, NVIDIA RTX PRO 5000 Blackwell (compute capability 12.0, driver 595.71), CUDA 13.2 (`nvcc` from the
`legacy-fenics` conda env), g++-15, HDF5 (C++ and HL libraries), CMake ≥ 3.20, Python 3 + NumPy ≥ 2.
Everything the run needs, including the hex mesh `glamv_hex` (55 MB), is in git — no IBAMR files are needed.

**1. Clone** (the geometry repo declares Git LFS for *other* data sets; `GIT_LFS_SKIP_SMUDGE=1` skips them if `git-lfs` is
not installed — `glamv_hex` and `glamv_ibamr` are plain git):

```bash
GIT_LFS_SKIP_SMUDGE=1 git clone --recurse-submodules -b glamv-cbspline \
    git@github.com:mapengfei-glasgow/fdm-3d-v1-workspace.git
cd fdm-3d-v1-workspace
ls fdm-3d-v1-geometry/src/ibm/data/glamv_hex/info.txt        # 29524 nodes, 22251 cells (11565 Q1 hex + 10686 P1 tet)
```

**2. Build `gla_mv`** (Release, FMA off as for G11; on the workstation also `source env.local.sh` first for g++-15/HDF5):

```bash
cmake -S fdm-3d-v1-gpu -B fdm-3d-v1-gpu/build -DCMAKE_BUILD_TYPE=Release \
      -DCMAKE_CUDA_COMPILER=$(which nvcc) -DCMAKE_CXX_COMPILER=g++-15 \
      -DFDM3D_SOURCE_DIR=$PWD/fdm-3d-v1 -DGEOMETRY_SOURCE_DIR=$PWD/fdm-3d-v1-geometry
      # add -DCMAKE_PREFIX_PATH=<hdf5 prefix> if HDF5 is not found
cmake --build fdm-3d-v1-gpu/build --target gla_mv -j
```

**3. Run** (from `fdm-3d-v1-gpu/`; ≈ 11 min of GPU time plus frame writing; ≈ 36 MB per frame: 35 frames ≈ 1.3 GB with the
default `EVERY=2000`, 268 frames ≈ 9.7 GB with `EVERY=250`):

```bash
cd fdm-3d-v1-gpu
EVERY=250 ./run_hex_bf.sh out_mv_hex_bf_cbs43_every250   # frames every 0.005 s; default EVERY=2000 (0.04 s)
#   DT=1e-5 EVERY=500 ./run_hex_bf.sh <dir>               # smaller time step, still 0.005 s frames
```

`run_hex_bf.sh` sets `DSH_PERF_LEVEL=3` and runs

```bash
./build/gla_mv --N 64 --T 1.335 --dt 2e-5 --sarah --beta-s 5e6 --nu 0.04 --inlet lvla_pressure_closing.inlet \
  --every 2000 --nvc 8 --helm-nvc 2 --max-u 2000 --solid-nu 1e3 --gap-mask 3.6 --gap-ramp 0.13 --gap-iters -1 \
  --passive-rim 3.73 --ib-kernel cbs43 --checkpoint-every 10000 --outlet-backflow \
  --data-dir ../fdm-3d-v1-geometry/src/ibm/data/glamv_hex/ --out <dir>/
```

| Option | Meaning |
|---|---|
| `--N 64` | {{< label "grid" "G-64" >}}: $64\times64\times96$ cells ($N_z$ chosen automatically) |
| `--T 1.335 --dt 2e-5` | end time and time step (66,750 steps) |
| `--sarah --beta-s 5e6` | SarahNodalMV materials (HGO leaflets, TI chordae, neo-Hookean tube/disc) + volumetric penalty $\beta_s$ |
| `--nu 0.04` | dynamic viscosity (P) |
| `--inlet lvla_pressure_closing.inlet` | IBAMR LV–LA pressure curve at the inlet disc |
| `--every N` | write `fluid_*.vti` + `Xc_*.bin` every N steps |
| `--nvc 8 --helm-nvc 2` | multigrid V-cycles per step (Poisson / Helmholtz) |
| `--max-u 2000` | abort if $\max\lvert\mathbf u\rvert$ exceeds 2000 cm/s |
| `--solid-nu 1e3` | Kelvin–Voigt solid viscosity (scale like $h^3$ on finer grids) |
| `--gap-mask 3.6 --gap-ramp 0.13 --gap-iters -1` | hold the fluid outside the tube at rest (§2.4) |
| `--passive-rim 3.73` | housing-disc cells beyond $r = 3.73$ cm force-free (§2.4) |
| `--ib-kernel cbs43` | composite B-spline coupling kernel |
| `--checkpoint-every 10000` | restart file; continue with `--restart <dir>/checkpoint_latest.bin` |
| `--outlet-backflow` | damp inflow through the outlet face (§5.5) |
| `--data-dir …/glamv_hex/` | the {{< label "mesh" "r0" >}} mixed hex/tet solid |

**4. Check the run** — `tail <dir>.console.log` ends with `Done. Output: <dir>/` (full cycle) or `失稳终止` (NaN; the step and time
are on that line). Columns of `<dir>/sim.log`: step, t, inlet pressure, max |u|, max |f|, $\sum\lvert\mathbf u\rvert^2$, |div u|.
A rising |div u| (> $10^{-6}$) around $t \approx 0.88$–0.91 s is the inlet-edge instability of §5.5.

**5. Flow rate** (from the workspace root):

```bash
python3 analyse_glamv_flow.py fdm-3d-v1-gpu <out> G11=out_mv_hex_bf_cbs43_every250   # → <out>/flow_G11.csv (Q at z = 3, 5.5, 9, 12 per frame)
python3 glamv_flow_dense.py <out>/flow_G11.csv MV_flowrate_ibamr.csv G11                # → chart table + valve metrics vs IBAMR
```

Expected (first cycle, reproducible across runs and $\Delta t$): peak ≈ 490 cm³/s at 0.13 s, closure at 0.182 s,
reopening at ≈ 0.525 s, forward volume ≈ 51.9 cm³, closed-phase backflow ≈ −15.4 cm³ (IBAMR: 385, 0.179 s, 0.513 s,
41.0, −13.8). Whether the run survives $t \approx 0.91$ s is not reproducible (§5.5).


---

## Appendix A. Rerunning glamv-0.0.3 (rerun guide, from commits `c6538e3` / `481431c`)

Working document, 2026-10-14. This appendix records how to rerun the reference mitral-valve case **glamv-0.0.3**
with the GPU solver `gla_mv`, and the flow rate it produces, sampled every 0.01 s (135 samples).
The instructions follow `fdm-3d-v1-gpu/docs/RUN_GLAMV.md` (branch `gpu-perf-base`); every command below was run
as written on 2026-10-14.
### A.1 The case

Mitral valve FSI in a tube (Nancy GlaTube geometry, IBAMR SarahNodalMV setup):

| Item | Value |
|---|---|
| Solid | `glamv_ibamr`: P1 tetrahedra, 29,524 nodes / 80,074 cells (tube, housing disc, anterior and posterior leaflets, annulus, chordae, papillary caps) |
| Materials | SarahNodalMV: HGO leaflets with fibres, transversely isotropic chordae, neo-Hookean tube/disc; volumetric penalty $\beta_s = 5\times10^6$ |
| Fluid | $64\times64\times96$ grid on $8.6\times8.6\times16.2$ cm, $\rho = 1$, $\mu = 0.04$ P |
| Coupling | nodal IFED, composite B-spline kernel CBS43 |
| Loading | IBAMR LV–LA pressure waveform at the inlet (`lvla_pressure_closing.inlet`), $T = 1.335$ s (two cycles) |
| Outside the tube | gap mask (fluid at rest for $r \ge 3.6$ cm) and passive rim (disc cells beyond $r = 3.73$ cm force-free) |
| Time step | $\Delta t = 2\times10^{-5}$ s, 66,750 steps |

### A.2 Prerequisites

| Item | Reference machine (runbook) | Also tested (this run) |
|---|---|---|
| GPU / driver | RTX 5070 Laptop, 595.99 | RTX PRO 5000 Blackwell, 595.71 |
| CUDA toolkit | 13.1 (`/usr/local/cuda-13.1`); ≥ 12.8 for RTX 50xx / Blackwell (sm_120) | 13.2 (`nvcc` from a conda env) |
| Host compiler | g++-13 | g++-15 |
| Libraries | `libhdf5-dev`, `libsqlite3-dev` | HDF5 in a local prefix |
| Python | numpy (post-processing only) | numpy 2 |
| GPU memory | 0.35 GB | 0.58 GB |

### A.3 Code and data

```bash
git clone --recurse-submodules -b gpu-perf-base git@github.com:mapengfei-glasgow/fdm-3d-v1-workspace.git
cd fdm-3d-v1-workspace
# existing clone instead:  git checkout gpu-perf-base && git pull && git submodule update --init --recursive
ls fdm-3d-v1-geometry/src/ibm/data/glamv_ibamr/        # the solid data, *.bin files (~23 MB), plain git
```

If `git-lfs` is not installed, the submodule update stops on an LFS file of `fdm-3d-v1` that the run does not use;
prefix the command with `GIT_LFS_SKIP_SMUDGE=1`.

### A.4 Build (once, ~30 s)

```bash
export PATH=/usr/local/cuda-13.1/bin:$PATH
cmake -S fdm-3d-v1-gpu -B fdm-3d-v1-gpu/build -DCMAKE_BUILD_TYPE=Release -DFDM3D_GPU_FMAD=ON \
  -DCMAKE_CUDA_COMPILER=/usr/local/cuda-13.1/bin/nvcc -DCMAKE_CUDA_ARCHITECTURES=120 \
  -DCMAKE_CUDA_HOST_COMPILER=/usr/bin/g++-13 -DCMAKE_CXX_COMPILER=/usr/bin/g++-13 \
  -DCMAKE_EXE_LINKER_FLAGS=-L/usr/lib/x86_64-linux-gnu/hdf5/serial
cmake --build fdm-3d-v1-gpu/build --target gla_mv -j
```

- `CMAKE_CUDA_ARCHITECTURES`: 120 = RTX 50xx / RTX PRO Blackwell, 89 = RTX 40xx / Ada, 86 = RTX 30xx.
- `FDM3D_GPU_FMAD=ON` is required for performance level D (`DSH_PERF_LEVEL=3`, §A.5).
- The linker flag is for Ubuntu, which keeps `libhdf5_cpp` under `hdf5/serial/`. With HDF5 in another prefix, add
  `-DCMAKE_PREFIX_PATH=<prefix>` and point the linker flag at `<prefix>/lib/x86_64-linux-gnu/hdf5/serial`
  (plus `-Wl,-rpath,<same dir>` so the binary finds it at run time).
- Other toolkits / compilers: replace the `nvcc` and `g++` paths; nothing else changes.

### A.5 Run (~10 min)

From `fdm-3d-v1-gpu/`. `--every 500` writes a fluid + solid frame every 0.01 s (135 frames, ≈ 4.9 GB), which gives
the flow-rate samples of §A.7; the runbook default `--every 2000` (0.04 s, 35 frames, ≈ 1.3 GB) gives 35.

```bash
cd fdm-3d-v1-gpu
OUT=out_glamv003_every500
DSH_PERF_LEVEL=3 ./build/gla_mv --N 64 --T 1.335 --dt 2e-5 --sarah \
  --data-dir ../fdm-3d-v1-geometry/src/ibm/data/glamv_ibamr/ --inlet lvla_pressure_closing.inlet \
  --beta-s 5e6 --nu 0.04 --nvc 8 --helm-nvc 2 --max-u 2000 --solid-nu 1e3 \
  --gap-mask 3.6 --gap-ramp 0.13 --gap-iters -1 --passive-rim 3.73 --ib-kernel cbs43 \
  --every 500 --checkpoint-every 20000 --out $OUT/ > $OUT.console.log 2>&1
```

| Option | Meaning |
|---|---|
| `DSH_PERF_LEVEL=3` | performance level D (mixed-precision multigrid, warm-started pressure), ≈ 8–9 ms/step; `0` = reference path, ≈ 19 ms/step |
| `--N 64` | fluid grid $64\times64\times96$ |
| `--T 1.335 --dt 2e-5` | end time, time step |
| `--sarah --beta-s 5e6` | SarahNodalMV materials, volumetric penalty |
| `--data-dir …/glamv_ibamr/` | solid data (must end in `/`) |
| `--inlet lvla_pressure_closing.inlet` | inlet pressure waveform |
| `--nu 0.04` | viscosity |
| `--nvc 8 --helm-nvc 2` | multigrid V-cycles per step (pressure / momentum) |
| `--max-u 2000` | abort above 2000 cm/s |
| `--solid-nu 1e3` | Kelvin–Voigt solid viscosity |
| `--gap-mask 3.6 --gap-ramp 0.13 --gap-iters -1` | keep the fluid outside the tube at rest |
| `--passive-rim 3.73` | disc cells outside the tube carry no force |
| `--ib-kernel cbs43` | composite B-spline coupling kernel |
| `--every 500` | frame interval in steps (0.01 s) |
| `--checkpoint-every 20000` | restart file `$OUT/checkpoint_latest.bin` |

- Progress: `tail -f $OUT/sim.log` (columns: step, t, $p_{in}$, max|u|, max|f|, |u|², |div u|).
- Interrupted: Ctrl+C writes the checkpoint; resume with the same command plus `--restart $OUT/checkpoint_latest.bin`.
- The run stops by itself on NaN or when max|u| exceeds `--max-u`.

This run: 66,750 steps in ≈ 9 min (8.1 ms/step), RTX PRO 5000.

### A.6 Check the result

```bash
python3 tools/perf/glamv_flowrate.py $OUT
```

`sim.log` must end with `66750   1.3350 …` and contain no `nan`. This run: completed, last line
`66750 1.3350 -3394.0769 5.74e-01 …`; max|u| peaks at 1.18 at $t = 0.32$ s, as in the runbook.

| Metric (lumen flow rate, $z = 0$ face, $r \le 3.5$ cm) | Runbook (0.04 s frames) | This run (0.04 s frames, `--every 2000`) | This run (0.01 s frames) | IBAMR |
|---|---|---|---|---|
| forward plateau, mean of frames in 0.10–0.16 s | 415.3 cm³/s | 415.3 | 412.4 | ≈ 370 |
| forward volume, 0–0.2 s (trapezoid on the frames) | 39.57 cm³ | 39.57 | 38.75 | 35.2 |
| closing spike, $Q(0.20\ \mathrm{s})$ | −471.9 cm³/s | −471.9 | −471.9 | −516 |

With `--every 2000` the run matches the runbook to every digit shown. With 0.01 s frames the plateau and volume
change slightly only because they are averages/integrals over different sample sets (7 frames instead of 2 in the
plateau window; finer trapezoid); the flow itself is the same (the spike at 0.20 s is identical).

### A.7 Flow rate, every 0.01 s

Lumen flow rate $Q(t) = \int w\,\mathrm{d}A$ over the inlet face $z = 0$, $r \le 3.5$ cm (+z = forward), from the 135 fluid
frames of the run in §A.5. The IBAMR column is the reference run's inlet flux at the same times (it was run to 0.65 s only).

{{< chart height="380" xlabel="t (s)" ylabel="Q through the tube lumen (cm³/s)" colors="#30638e,#d1495b" caption="Figure A1. Lumen flow rate of glamv-0.0.3 (gla_mv, 64×64×96, P1 solid, CBS43, Δt = 2×10⁻⁵, DSH_PERF_LEVEL=3, FMA on) every 0.01 s, against the IBAMR SarahNodalMV reference (inlet flux, to 0.65 s)." >}}
t, gla_mv glamv-0.0.3, IBAMR reference
0.000, 0.00, 0.00
0.010, 0.00, 1.58
0.020, 0.00, 2.06
0.030, 15.33, 16.91
0.040, 54.14, 57.00
0.050, 110.68, 111.79
0.060, 183.39, 179.27
0.070, 267.92, 253.13
0.080, 340.48, 309.29
0.090, 387.70, 344.96
0.100, 413.43, 369.99
0.110, 421.21, 381.61
0.120, 415.11, 373.88
0.130, 407.55, 364.28
0.140, 405.63, 363.74
0.150, 408.70, 370.89
0.160, 415.42, 385.03
0.170, 256.13, 239.10
0.180, -7.87, -24.66
0.190, -384.03, -371.83
0.200, -471.95, -488.22
0.210, 132.28, 13.80
0.220, -44.07, 5.27
0.230, -126.53, -2.47
0.240, -19.49, -27.31
0.250, -63.34, -76.21
0.260, -53.61, -18.33
0.270, -35.26, -22.45
0.280, -55.03, -55.48
0.290, -38.75, -19.11
0.300, -38.61, -17.40
0.310, -36.78, -29.10
0.320, -37.37, -19.85
0.330, -35.85, -15.14
0.340, -31.60, -18.51
0.350, -32.45, -19.16
0.360, -37.10, -19.18
0.370, -33.75, -17.82
0.380, -28.78, -15.60
0.390, -26.14, -14.92
0.400, -28.43, -13.69
0.410, -25.04, -13.70
0.420, -28.13, -12.32
0.430, -23.97, -12.15
0.440, -22.98, -11.21
0.450, -25.91, -10.24
0.460, -17.72, -9.84
0.470, -19.23, -8.61
0.480, -19.37, -7.05
0.490, -15.16, -4.16
0.500, -15.49, -2.59
0.510, -12.54, -0.83
0.520, -6.83, 0.83
0.530, -2.00, 2.80
0.540, 12.41, 5.79
0.550, 29.96, 9.94
0.560, 45.29, 14.99
0.570, 60.96, 19.70
0.580, 66.93, 22.54
0.590, 70.66, 23.76
0.600, 180.92, 451.84
0.610, 342.03, 526.13
0.620, 471.09, 516.46
0.630, 540.94, 547.38
0.640, 555.53, 535.47
0.650, 535.74, 474.88
0.660, 494.69, 
0.670, 461.00, 
0.680, 443.74, 
0.690, 431.45, 
0.700, 411.06, 
0.710, 394.59, 
0.720, 381.38, 
0.730, 371.91, 
0.740, 364.46, 
0.750, 359.48, 
0.760, 355.07, 
0.770, 349.36, 
0.780, 338.75, 
0.790, 339.55, 
0.800, 337.91, 
0.810, 336.01, 
0.820, 336.02, 
0.830, 335.21, 
0.840, 333.12, 
0.850, 327.74, 
0.860, 322.95, 
0.870, 320.46, 
0.880, 315.78, 
0.890, 308.10, 
0.900, 297.61, 
0.910, 154.32, 
0.920, -94.59, 
0.930, -454.96, 
0.940, -306.61, 
0.950, 113.94, 
0.960, -86.09, 
0.970, -106.53, 
0.980, -21.00, 
0.990, -72.16, 
1.000, -47.01, 
1.010, -42.16, 
1.020, -55.50, 
1.030, -42.41, 
1.040, -39.68, 
1.050, -35.04, 
1.060, -34.04, 
1.070, -31.20, 
1.080, -30.19, 
1.090, -30.78, 
1.100, -31.32, 
1.110, -30.19, 
1.120, -26.38, 
1.130, -27.55, 
1.140, -22.23, 
1.150, -24.12, 
1.160, -26.78, 
1.170, -24.72, 
1.180, -20.90, 
1.190, -25.29, 
1.200, -22.16, 
1.210, -15.55, 
1.220, -20.47, 
1.230, -10.66, 
1.240, -12.88, 
1.250, -11.70, 
1.260, -8.41, 
1.270, -1.77, 
1.280, 10.51, 
1.290, 29.32, 
1.300, 46.23, 
1.310, 60.11, 
1.320, 68.90, 
1.330, 72.33, 
1.335, 117.12,
{{< /chart >}}

Key values from these samples:

| Quantity | gla_mv | IBAMR (same times) |
|---|---|---|
| First peak forward flow | 421.2 cm³/s at 0.11 s | 385.0 at 0.16 s |
| Closing spike | −472.0 cm³/s at 0.20 s | −488.2 at 0.20 s |
| Second-cycle peak | 555.5 cm³/s at 0.64 s | 535.5 at 0.64 s |
| Second closing spike | −455.0 cm³/s at 0.93 s | — |
| Volume 0–0.2 s / 0.2–0.56 s | 38.75 / −10.76 cm³ | — |
| Volume 0.56–0.9 s / 0.9–1.28 s | 117.66 / −14.71 cm³ | — |

The samples are also printed by the script in §A.6 (`t:` and `Q:` lines); the full-precision values above were
computed with the same integral.

### A.8 View in ParaView

```bash
python3 scripts/solid_to_vtu_numpy.py $OUT --markers ../fdm-3d-v1-geometry/src/ibm/data/glamv_ibamr
paraview $OUT/fluid.pvd $OUT/vtu/solid.pvd
```

- `fluid.pvd`: `velocity`, `u`, `v`, `w`, `pressure`, `vorticity_mag`, `ibm_force`.
- `vtu/solid.pvd`: current geometry, `displacement`, `cell_marker` (tube 1, disc 42, anterior leaflet 3 5 7 23 25,
  posterior leaflet 4 24, annulus 4099 5099, chordae 100 200 300, papillary tips 1001–1005 2001–2005).
- Vortex rings: *Gradient* of `velocity` with *Compute QCriterion* → *Contour* at a small positive Q; or a *Slice*
  at $x = 4.3$ coloured by `vorticity_mag`.

### A.9 If something fails

| Symptom | Cause / fix |
|---|---|
| CMake: `fdm-3d-v1-geometry not found` | submodules missing: `git submodule update --init --recursive` |
| `git-lfs filter-process: git-lfs: not found` during the submodule update | install git-lfs, or `GIT_LFS_SKIP_SMUDGE=1 git submodule update --init --recursive` |
| link error `cannot find -lhdf5_cpp` | add `-DCMAKE_EXE_LINKER_FLAGS=-L<dir of libhdf5_cpp.so>` (§A.4) |
| nvcc rejects architecture 120 | CUDA < 12.8: upgrade, or set `CMAKE_CUDA_ARCHITECTURES` for your GPU |
| CUDA error at start-up | driver not loaded (`nvidia-smi` fails) |
| solid data cannot be read | `--data-dir` must point at `…/src/ibm/data/glamv_ibamr/` and end in `/` |
| ≫ 9 ms/step | built without `-DFDM3D_GPU_FMAD=ON` or run without `DSH_PERF_LEVEL=3`; `[perf]` lines in `$OUT.console.log` give the split |

{{< references >}}
