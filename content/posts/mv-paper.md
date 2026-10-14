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

Working draft. Target journal: *Journal of Fluid Mechanics*.
Status: 2026-10-13. Empty cells are not yet measured. Run labels ({{< label "run" "G1" >}} … {{< label "run" "G10" >}}) refer to the run register in
`GLAMV_STATUS.md` (dev clone, branch `glamv-cbspline`).

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
| Outlet backflow stabilisation | `--outlet-backflow` (implemented, not yet tested) | |

### 3.3 Validation against IBAMR

| Quantity | IBAMR | 0.0.3 (P1 tet) | {{< label "run" "G5" >}} (conforming tet) | {{< label "run" "G7" >}} (Q1 hex, IBAMR mesh) |
|---|---|---|---|---|
| Forward volume 0–0.2 s (cm³) | 35.2 | 38.5 | 37.8 | 43.2 |
| Backflow volume 0.2–0.56 s (cm³) | −15.6 | −16.4 | −15.5 | −18.5 |
| Peak forward flow rate (cm³/s) | | | | |
| Valve opening time (s) | | | | |
| Valve closing time (s) | | | | |
| Completed cycle | 0–0.65 s only | yes | yes | no ($t \approx 0.9$ s) |

(volumes from REPORT.txt, tube flux at $z = 12$ cm, 0.04 s sampling; IBAMR at the inlet. §3.2 (1) quotes inlet-flux volumes, hence −17.3 vs −16.4 for 0.0.3)

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
| {{< label "run" "G9" >}} | {{< label "grid" "G-64" >}} / {{< label "mesh" "r1" >}} | | | | | |
| {{< label "run" "G10" >}} | {{< label "grid" "G-128" >}} / {{< label "mesh" "r1" >}} | | | | | |
| | {{< label "grid" "G-256" >}} / {{< label "mesh" "r2" >}} | | | | | |

(the existing `[perf]` lines were recorded with two runs sharing the GPU; to be re-measured with one run)

---

## 5. Results

### 5.1 Run summary

| Run | Grid | Solid mesh | Leaflets | $\Delta t$ | Outcome | Forward 0–0.2 (cm³) | Backflow 0.2–0.56 (cm³) | $J_{\min}$ |
|---|---|---|---|---|---|---|---|---|
| 0.0.3 | {{< label "grid" "G-64" >}} | P1 tet (glamv_ibamr) | fibre HGO | $2 \times 10^{-5}$ | full cycle | 38.5 | −16.4 | 0.31 |
| {{< label "run" "G1d" >}} | {{< label "grid" "G-64" >}} | P1 tet (glamv_ibamr) | dispersed | $2 \times 10^{-5}$ | full cycle | 40.6 | −19.9 | 0.07 |
| {{< label "run" "G5" >}} | {{< label "grid" "G-64" >}} | P1 tet, conforming | fibre HGO | $2 \times 10^{-5}$ | full cycle | 37.8 | −15.5 | 0.21 |
| {{< label "run" "G6" >}} | {{< label "grid" "G-64" >}} | P1 tet, conforming | dispersed | $2 \times 10^{-5}$ | full cycle | 40.3 | −19.2 | 0.41 |
| {{< label "run" "G7" >}} | {{< label "grid" "G-64" >}} | {{< label "mesh" "r0" >}} Q1 + P1 | fibre HGO | $2 \times 10^{-5}$ | NaN $t \approx 0.9$ (outlet backflow) | 43.2 | −18.5 | 0.37 |
| {{< label "run" "G7b" >}} | {{< label "grid" "G-64" >}} | {{< label "mesh" "r0" >}} | fibre HGO | $1 \times 10^{-5}$ | NaN $t \approx 0.83$ (outlet backflow) | | | |
| {{< label "run" "G8" >}} | {{< label "grid" "G-64" >}} | {{< label "mesh" "r0" >}} | dispersed | $2 \times 10^{-5}$ | NaN $t \approx 0.9$ | 47.5 | −21.2 | |
| {{< label "run" "G9" >}} | {{< label "grid" "G-64" >}} | {{< label "mesh" "r1" >}} | dispersed | $2 \times 10^{-5}$ | NaN $t \approx 0.9$ | | | |
| {{< label "run" "G10" >}} | {{< label "grid" "G-128" >}} | {{< label "mesh" "r1" >}} | dispersed | $1 \times 10^{-5}$ | NaN $t \approx 0.78$ (outlet backflow) | | | |
| | {{< label "grid" "G-256" >}} | {{< label "mesh" "r2" >}} | | | | | | |

Open issue: on the hex meshes the valve opens wider and the jet reaches the outlet with recirculation; about 40 %
of the outlet lumen flows back in and the backflow grows exponentially. Remedy under test: `--outlet-backflow`.

Leakage check (tube flux at $z = 3$, 5.5, 9, 12 cm; difference between sections):

| Run | $\max\lvert Q(z_1)-Q(z_2)\rvert / \max Q$ |
|---|---|
| | |

### 5.2 Fluid

| Analysis | {{< label "grid" "G-64" >}} | {{< label "grid" "G-128" >}} | {{< label "grid" "G-256" >}} | IBAMR |
|---|---|---|---|---|
| Flow rate vs time (inlet / tube sections) | | | | |
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

---

## 6. Discussion

- Resolution: does the flow converge between {{< label "grid" "G-64" >}}, {{< label "grid" "G-128" >}}, {{< label "grid" "G-256" >}} at fixed MFAC?
- Which numerical choice matters most for the valve dynamics (kernel, element, stabilisation)?
- Limits: outlet boundary treatment, chordae mesh of the IBAMR model, tube-wall $\mathrm{MFAC}>1$, comparison with IBAMR
  only up to 0.65 s.

## 7. Conclusions

(to be written)

{{< references >}}
