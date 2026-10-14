---
title: "Mitral-valve FSI on GPUs"
description: "Working paper. Sign in with your site sync code to read."
date: 2026-10-14
layout: protected-paper
academic: true
comments: false
searchHidden: true
build:
  list: never
---

# Mitral-valve FSI on GPUs with a nodal immersed finite element / finite difference method

Working draft. Target journal: *Journal of Fluid Mechanics*.
Status: 2026-10-13. Empty cells are not yet measured. Run labels (G1 … G10) refer to the run register in
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

### 2.1 Geometry, domain and loading

| Item | Value |
|---|---|
| Domain | 8.6 × 8.6 × 16.2 cm (tube axis along z) |
| Tube | lumen radius 3.5 cm; housing-disc cells beyond r = 3.73 cm are force-free (passive rim) |
| Inlet / outlet | z = 0 / z = 16.2 cm, prescribed pressure on the lumen disc + feedback forcing (IBAMR FeedbackForcer) |
| Inlet pressure | `lvla_pressure_closing.inlet` (IBAMR LV–LA pressure curve) |
| Time simulated | 1.335 s |
| Fluid | ρ = 1 g/cm³, μ = 0.04 P |
| Leaflets | Sarah HGO, unmodified invariants. AML: C₁₀ = 1245, C₀₁ = 13.67, k₁ = 1.10e5, k₂ = 84.85, κ = 0.080; PML: C₁₀ = 502, C₀₁ = 15.00, k₁ = 3.02e4, k₂ = 144.5, κ = 0.053. Variant: fully dispersed (κ = 1/3) |
| Chordae | IBAMR SarahNodalMV chordae model (parameters: ) |
| Volumetric term | β_s = 5 × 10⁶ dyn/cm² (all cells) |
| Tethers | pins (tube, disc) and papillary caps, β = 100 κ_s = 5 × 10⁸, IBAMR cap schedule |

### 2.2 Background (Eulerian) grids

| Grid | N_x × N_y × N_z | Cells | h_x = h_y (cm) | h_z (cm) | dt (s) | Steps / 1.335 s |
|---|---|---|---|---|---|---|
| G-64 | 64 × 64 × 96 | 393,216 | 0.1344 | 0.1688 | 2e-5 | 66,750 |
| G-128 | 128 × 128 × 192 | 3,145,728 | 0.0672 | 0.0844 | 1e-5 | 133,500 |
| G-256 | 256 × 256 × 384 | 25,165,824 | 0.0336 | 0.0422 | | |
| IBAMR (reference) | 44 × 44 × 80 | 154,880 | 0.195 | 0.2025 | 5e-6 | 267,000 |

Multigrid requires N to be a power of two (64, 128, 256).

### 2.3 Solid (Lagrangian) meshes

Built directly from the IBAMR mesh `MV_only_hex.xda` (11,567 HEX8 + 10,686 TET4; two duplicated elements removed)
with `fdm-3d-v1-geometry/scripts/gen_glamv_hex.py`; level r1 = one uniform refinement (hex → 8, tet → 8).
Each grid should use the solid level that keeps MFAC ≈ 0.5–1 for the leaflets (MFAC = marker spacing / h).

| Solid mesh | Paired grid | Nodes (IB markers) | Q1 hexes | P1 tets | Volume (cm³) |
|---|---|---|---|---|---|
| r0 (`glamv_hex`, = IBAMR mesh) | G-64 | 29,524 | 11,565 | 10,686 | |
| r1 (`glamv_hex_r1`) | G-128 | 169,094 | 92,520 | 85,488 | |
| r2 | G-256 | | | | |

Per component (nodes / cells / median edge length / MFAC on the paired grid):

| Component | r0 nodes | r0 cells | r0 edge (cm) | MFAC r0 @ G-64 | r1 nodes | r1 cells | r1 edge (cm) | MFAC r1 @ G-128 | r2 … @ G-256 |
|---|---|---|---|---|---|---|---|---|---|
| Tube (marker 1) | 16,848 | 8,320 hex | 0.218 | 1.62 | 100,464 | 66,560 hex | 0.109 | 1.62 | |
| Housing disc (42) | 3,773 | 10,650 tet | 0.169 | 1.26 | 21,943 | 85,200 tet | 0.086 | 1.27 | |
| Leaflets (AML + PML) | 4,004 | 1,872 hex + 36 tet | 0.093 | 0.69 | 23,280 | 14,976 hex + 288 tet | 0.047 | 0.69 | |
| Chordae (100/200/300) | 5,217 | 1,343 hex | 0.046 | 0.34 | 24,014 | 10,744 hex | 0.024 | 0.35 | |
| Tether caps (1001–2005) | 220 | 30 hex | 0.040 | 0.30 | 790 | 240 hex | 0.020 | 0.30 | |

Known mesh issues inherited from the IBAMR model: chordae branch junctions where one hex face is shared by more
than two hexes (≈ 70 quads at r0), and a few poorly shaped chordae hexes (scaled Jacobian down to 0.07).
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

#### (1) Kernel: CBS43 or higher order (CBS54, CBS65)

For the local divergence-free IFED method using composite B-splines, see Li et al.
{{< cite "li2025local" >}}.

| Kernel | Implemented | Max stable dt (torsion, MFAC ≤ 0.72) | Volume error, LV problem 2 (MFAC 0.40) | MV result |
|---|---|---|---|---|
| IB_4 | yes | 1.6e-3 | | |
| BSPLINE_3 (IBAMR default) | yes | | | glamv-0.0.2: backflow −23.6 cm³ (inlet) |
| CBS43 | yes | 8e-4 | +0.05 % (wall displacement within 0.9 % of FE) | glamv-0.0.3: backflow −17.3 cm³ (inlet; IBAMR −15.6) |
| CBS32 | yes | | | unstable at dt ≥ 1e-5, stable at 5e-6 |
| CBS54 | no | | | |
| CBS65 | no | | | |

Finding: CBS kernels remove the leak driven by transmural pressure only at small MFAC (≤ 0.5–0.7); at MFAC > 1
they are worse than IB_4. Wider CBS kernels (54, 65) are expected to need smaller MFAC and cost more per marker.

#### (2) Stress form: modified invariants, deviatoric projection, or stripping the pressure part

| Form | Torsion (P1, MFAC 1.43, ν_s = 0.4) | Cook | MV |
|---|---|---|---|
| modified invariants (Flory, multiplicative split) | +16.2 % | +0.89 % | |
| unmodified invariants | wrong sign, volume −17 % | −5.2 % | (IBAMR Sarah model uses unmodified + β_s) |
| deviatoric projection | +15.0 % | +0.52 % | |

#### (3) Volumetric stabilisation κ_s (β_s)

For volumetric stabilisation and stress formulations in hyperelastic immersed
boundary methods, see Vadala-Roth et al. {{< cite "vadalaroth2020" >}}.

| Case | Without κ_s | With κ_s | Note |
|---|---|---|---|
| Torsion, P1, MFAC 0.43, volume error | IB_4: 0.138 %; CBS43: 0.057 % | IB_4, ν_s = 0.4: 0.099 % | CBS43 without κ_s beats IB_4 with κ_s |
| LV problem 2, P2 + CBS43, MFAC 0.40 | displacement 0.9 %, volume +0.06 % (needs `--kd 0.5`) | displacement 0.9 %, volume +0.05 % | keep κ_D fixed when dt shrinks |
| MV | | β_s = 5e6 (all runs) | |

#### (4) Element type: P1, P2, Q1, Q2

| Element | Torsion error, n = 6 (MFAC) | Cook error, n = 16 (MFAC) | MV runs |
|---|---|---|---|
| P1 tet | +16.2 % (1.43) | +0.89 % (1.86) | 0.0.3, G5, G6 (full cycle) |
| P2 tet | +1.7 % (0.72) | +0.48 % (0.93) | G3 / G4: failed (old non-conforming tet split) |
| Q1 hex | +5.0 % (1.19) | +1.43 % (1.33) | G7–G10: outlet backflow instability, see §5 |
| Q2 hex | not implemented | | |

#### (5) Fluid solver and convection

| Option | Status | Effect |
|---|---|---|
| Viscous term BE vs CN | CN in `ifed_bench` (`--viscous`) | |
| Convection central + AB2 | default | |
| Convection 2nd-order upwind (SOU) | `real_av` only (`--conv-upwind`); not in `gla_mv` | |
| Outlet backflow stabilisation | `--outlet-backflow` (implemented, not yet tested) | |

### 3.3 Validation against IBAMR

| Quantity | IBAMR | 0.0.3 (P1 tet) | G5 (conforming tet) | G7 (Q1 hex, IBAMR mesh) |
|---|---|---|---|---|
| Forward volume 0–0.2 s (cm³) | 35.2 | 38.5 | 37.8 | 43.2 |
| Backflow volume 0.2–0.56 s (cm³) | −15.6 | −16.4 | −15.5 | −18.5 |
| Peak forward flow rate (cm³/s) | | | | |
| Valve opening time (s) | | | | |
| Valve closing time (s) | | | | |
| Completed cycle | 0–0.65 s only | yes | yes | no (t ≈ 0.9 s) |

(volumes from REPORT.txt, tube flux at z = 12 cm, 0.04 s sampling; IBAMR at the inlet. §3.2 (1) quotes inlet-flux volumes, hence −17.3 vs −16.4 for 0.0.3)

---

## 4. GPU acceleration

### 4.1 What runs on the GPU

All per-step work runs on the GPU: momentum (three face Helmholtz multigrid solves), pressure Poisson multigrid,
projection, convection, IB interpolation and spreading, solid force assembly (PK1, tethers, viscosity, penalties),
feedback forcing and gap mask. The host only writes output and logs.

### 4.2 Performance levels (fluid solver, `docs/GPU_PERFORMANCE.md`)

| Level | Switch | RTX 5070 Laptop, 256³ (ms/step) | RTX PRO 5000, 128³ | RTX PRO 5000, 256³ | Result vs level 0 |
|---|---|---|---|---|---|
| original | — | 496 | 39.2 | 197.5 | — |
| A | default | 240 | 22.8 | 100.7 | bitwise identical |
| B | `DSH_PERF_LEVEL=1` + FMA | 179 | 17.1 | 67.8 | ~1e-13 |
| C | `DSH_PERF_LEVEL=2` + FMA | 126 | 11.0 | 43.8 | ≤ 1e-8 |
| D | `DSH_PERF_LEVEL=3` + FMA | 111 | 9.05 | 38.0 | ~1e-8 |

Mitral-valve case (0.0.3 configuration, G-64, P1 tets, RTX PRO 5000): 49.4 ms/step originally, 21.7 at level A,
10.1 at level D + FMA; a full cycle takes ≈ 11 min. IBAMR: ≈ 45 ms/step on 24 MPI ranks (1 h 38 min for 0.65 s).

### 4.3 Share of the simulation time per part

Measured alone on one RTX PRO 5000 at level D (ms/step):

| Run | Grid / solid | Fluid (Helmholtz + Poisson + projection + convection) | Interpolation + spreading | Solid assembly | Other | Total |
|---|---|---|---|---|---|---|
| 0.0.3 config | G-64 / glamv_ibamr (P1) | | | | | 10.1 |
| G7 | G-64 / r0 (Q1 + P1) | | | | | |
| G9 | G-64 / r1 | | | | | |
| G10 | G-128 / r1 | | | | | |
| | G-256 / r2 | | | | | |

(the existing `[perf]` lines were recorded with two runs sharing the GPU; to be re-measured with one run)

---

## 5. Results

### 5.1 Run summary

| Run | Grid | Solid mesh | Leaflets | dt | Outcome | Forward 0–0.2 (cm³) | Backflow 0.2–0.56 (cm³) | J min |
|---|---|---|---|---|---|---|---|---|
| 0.0.3 | G-64 | P1 tet (glamv_ibamr) | fibre HGO | 2e-5 | full cycle | 38.5 | −16.4 | 0.31 |
| G1d | G-64 | P1 tet (glamv_ibamr) | dispersed | 2e-5 | full cycle | 40.6 | −19.9 | 0.07 |
| G5 | G-64 | P1 tet, conforming | fibre HGO | 2e-5 | full cycle | 37.8 | −15.5 | 0.21 |
| G6 | G-64 | P1 tet, conforming | dispersed | 2e-5 | full cycle | 40.3 | −19.2 | 0.41 |
| G7 | G-64 | r0 Q1 + P1 | fibre HGO | 2e-5 | NaN t ≈ 0.9 (outlet backflow) | 43.2 | −18.5 | 0.37 |
| G7b | G-64 | r0 | fibre HGO | 1e-5 | NaN t ≈ 0.83 (outlet backflow) | | | |
| G8 | G-64 | r0 | dispersed | 2e-5 | NaN t ≈ 0.9 | 47.5 | −21.2 | |
| G9 | G-64 | r1 | dispersed | 2e-5 | NaN t ≈ 0.9 | | | |
| G10 | G-128 | r1 | dispersed | 1e-5 | NaN t ≈ 0.78 (outlet backflow) | | | |
| | G-256 | r2 | | | | | | |

Open issue: on the hex meshes the valve opens wider and the jet reaches the outlet with recirculation; about 40 %
of the outlet lumen flows back in and the backflow grows exponentially. Remedy under test: `--outlet-backflow`.

Leakage check (tube flux at z = 3, 5.5, 9, 12 cm; difference between sections):

| Run | max |Q(z₁) − Q(z₂)| / max Q |
|---|---|
| | |

### 5.2 Fluid

| Analysis | G-64 | G-128 | G-256 | IBAMR |
|---|---|---|---|---|
| Flow rate vs time (inlet / tube sections) | | | | |
| Streamlines (opening, peak, closure) | | | | |
| Vorticity (mid-plane, transverse sections) | | | | |
| Vortex ring formation and breakdown (large → small eddies) | | | | |
| Q-criterion iso-surfaces | | | | |
| Energy dissipation rate ε = 2μ S:S (volume integral vs time) | | | | |
| Turbulent kinetic energy / spectra downstream of the valve | | | | |

### 5.3 Solid

| Analysis | G-64 / r0 | G-128 / r1 | G-256 / r2 | IBAMR |
|---|---|---|---|---|
| Leaflet displacement (tip, belly) vs time | | | | |
| Orifice area vs time | | | | |
| Stress (first principal / von Mises) at peak opening and closure | | | | |
| Volume change, J range (all cells / leaflets) | | | | |
| Chordae tension vs time | | | | |

---

## 6. Discussion

- Resolution: does the flow converge between G-64, G-128, G-256 at fixed MFAC?
- Which numerical choice matters most for the valve dynamics (kernel, element, stabilisation)?
- Limits: outlet boundary treatment, chordae mesh of the IBAMR model, tube-wall MFAC > 1, comparison with IBAMR
  only up to 0.65 s.

## 7. Conclusions

(to be written)

{{< references >}}
