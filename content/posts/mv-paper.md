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

The configurations use **grid / mesh refinement / solid elements / outlet treatment** as their naming
convention. All configurations use {{< label "grid" "G-64" >}} ($64 \times 64 \times 96$ cells).
**BF** enables outlet backflow stabilisation (`--outlet-backflow`); **NBF** omits it.


{{< table-caption "1" "Configuration labels and solid elements" >}}

| Configuration label | Solid elements |
|:---|:---|
| {{< label "config" "G64/R0/P1/BF" >}} | Pure P1 tetrahedra |
| {{< label "config" "G64/R0/P1/NBF" >}} | Pure P1 tetrahedra |
| {{< label "config" "G64/R0/P2/BF" >}} | Pure P2 tetrahedra |
| {{< label "config" "G64/R0/P1+Q1/BF" >}} | Q1 hexahedra + P1 tetrahedra |
| {{< label "config" "G64/R0/Q2+P2/BF" >}} | Q2 hexahedra + P2 tetrahedra |
| {{< label "config" "G64/R1/P1+Q1/BF" >}} | Q1 hexahedra + P1 tetrahedra, 1 uniform refinement level(s) |
| {{< label "config" "G64/R2/P1+Q1/BF" >}} | Q1 hexahedra + P1 tetrahedra, 2 uniform refinement level(s) |

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

The study uses G64, G128 and G256 grids in the $8.6 \times 8.6 \times 16.2$ cm domain.
Exact grid spacings, time-step choices and the IBAMR reference grid are collected in the
[mesh and refinement note]({{< relref "mv-meshes.md" >}}#2-eulerian-grids).

### 2.3 Solid (Lagrangian) meshes

The reference solid uses mixed Q1 hexes and P1 tets. R1 and R2 are successive uniform
subdivisions; P2/Q2 interpolation-order changes are separate experiments.
Mesh inventories, anatomical marker groups, refinement/data-transfer rules and known limitations
are documented in the [mesh and refinement note]({{< relref "mv-meshes.md" >}}).
Its [MFAC tables]({{< relref "mv-meshes.md" >}}#5-mfac-definition-and-sampling-convention)
give every G64/G128/G256 × R0/R1/R2 combination by anatomical group, with separate transverse
and axial grid-spacing ratios.

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

#### (2) Stress form: why modified invariants may help

**The current CBS43 comparison shows less extreme local compression with modified stress, but does not establish uniformly better volume conservation or a larger stable time step.** Here “modified” means evaluating the shear and fibre energy using the volume-preserving deformation gradient, then differentiating that energy fully. It does not mean simply deleting pressure from the original stress.

Let $F$ be the deformation gradient and $J=\det F$ the local volume ratio: $J=1$ preserves volume, while $J=0.01$ means that an element retains only 1% of its reference volume. We split the energy into

$$
\bar F=J^{-1/3}F,\qquad
W(F)=W_{\mathrm{iso}}(\bar F)+U(J),\qquad
U(J)=\beta_s(\ln J)^2.
$$

Because $\det\bar F=1$, uniform dilation is removed from the invariants used by the shear and fibre law. With $\bar P=\partial W_{\mathrm{iso}}/\partial\bar F$, the implemented first Piola–Kirchhoff stress is

$$
P_{\mathrm{iso}}=J^{-1/3}\bar P
-\frac{\bar P:\bar F}{3}F^{-T},\qquad
P_{\mathrm{vol}}=2\beta_s\ln J\,F^{-T}.
$$

The chain-rule projection gives $P_{\mathrm{iso}}:F=0$, so its Cauchy stress has zero trace. Shape and fibre deformation therefore generate a deviatoric stress, while the separate volumetric term resists changes in $J$. A pure dilation leaves $\bar F$ unchanged; it does not spuriously activate the isochoric fibre response.

**Why this matters for IB.** The Eulerian pressure enforces fluid incompressibility, but interpolation to the solid, the FE representation and time integration can still change solid-element volumes. Once $J$ drifts from one, unmodified invariants also respond to that dilation, mixing the shape response with a pressure-like elastic contribution. Separating these contributions gives the volumetric penalty a clearer role in correcting local volume drift. This mechanism and its benchmark evidence are discussed by {{< cite "vadalaroth2020" "author" >}}. Even with CBS43, the discrete FE deformation and time update do not guarantee $J=1$ in every element.

**MV evidence (2026-10-16).** The following G64/R2 mixed Q1+P1 runs use CBS43, outlet backflow stabilisation, $\Delta t=2\times10^{-5}$ s, $\beta_s=5\times10^6$, solid viscosity `--solid-nu 1000`, and the same geometry, material coefficients and boundary settings. The original-stress result reuses the completed baseline; the modified result uses `--sarah-stress mod`.

| Stress form | End time (s) | Minimum $J$ | Maximum $J$ | Signed flow volume, 0.04–0.20 s (cm³) | Signed flow volume, 0.20–0.56 s (cm³) |
|:---|---:|---:|---:|---:|---:|
| Original invariants | 1.335 | 0.009898 | 2.45364 | 47.217 | −3.258 |
| Modified invariants | 1.335 | 0.167943 | 2.65547 | 47.796 | −3.393 |

The minimum $J$ improves substantially, but 0.168 still represents severe compression, and the maximum $J$ increases. These are global extrema over saved frames and cells, including the passive rim; the worst elements need not be the same in both runs. They do not measure total solid-volume error or establish improvement in every component. The signed flow volumes are integrals of the sampled flow-rate curve, not measurements of solid volume, and their changes alone do not establish greater accuracy.

With IB4 and otherwise matching settings, modified stress fails after the last valid output at 0.66 s; original stress fails after 0.69 s. Thus this experiment does **not** support a general stability advantage for modified stress. No larger time step has yet been demonstrated for the completed CBS43 modified case. [Download the four-run comparison](/data/mv-stress-comparison.csv).

**Separate the four choices.** Modified invariants change the energy through $\bar F$; a deviatoric projection applied directly to the original stress evaluated at $F$ is a different formulation away from $J=1$, and has not been separately tested here. The volumetric term controls volume drift. Solid viscosity damps deformation rates and is held fixed in the stress-form table; its separate zero/nonzero comparison is reported below. Modified stress changes the constitutive extension away from incompressibility and cannot repair a poor mesh, boundary instability or an excessive time step by itself.

##### Completed solid-viscosity comparison and current conclusions (2026-10-17)

The zero-solid-viscosity run has now completed the full 1.335 s cycle. Both runs below use G64/R2 mixed Q1+P1, CBS43, modified invariants, outlet backflow stabilisation and $\Delta t=2\times10^{-5}$ s. Geometry, material coefficients, volumetric penalty, fluid viscosity and boundary settings are held fixed; only `--solid-nu` changes.

| Metric | `solid-nu=1000` | `solid-nu=0` |
|:---|---:|---:|
| Completed to 1.335 s | Yes | Yes |
| Minimum $J$ | 0.167943 | 0.211472 |
| Maximum $J$ | 2.65547 | 2.84226 |
| Mean flow rate, 0.10–0.16 s (cm³/s) | 482.59 | 467.37 |
| Signed flow volume, 0.04–0.20 s (cm³) | 47.796 | 46.119 |
| Signed flow volume, 0.20–0.56 s (cm³) | −3.393 | −2.501 |

Removing solid viscosity reduces the first signed flow volume by 3.51% and the magnitude of closing backflow by 26.31%. The minimum $J$ is higher, but the maximum $J$ is also higher. Thus solid viscosity is **not required for completion at this tested time step**, yet it has a measurable effect on deformation and flow. Neither completion nor reduced backflow establishes which solution is more accurate. As above, $J$ extrema include the passive rim and are taken across saved frames; flow volumes use the sampled flow-rate curve. [Download the viscosity comparison](/data/mv-viscosity-comparison.csv).

The present evidence supports the following distinctions:

- **Kernel choice has the clearest effect on robustness in these tests.** CBS43 completes with original and modified stress, whereas IB4 fails with both at the same time step and nonzero solid viscosity. This is evidence for the tested MV configuration, not a universal ranking of kernels across meshes, resolutions or time steps.
- **Modified invariants strongly affect extreme local compression.** At fixed CBS43 and solid viscosity, minimum $J$ rises from 0.009898 to 0.167943, while maximum $J$ becomes slightly worse. Both stress forms complete, so the observed benefit concerns the compression extreme rather than demonstrated completion or accuracy gains.
- **Direct deviatoric projection remains an open comparison.** Modified invariants already yield a traceless isochoric Cauchy stress through the energy derivative. Projecting the original stress evaluated at $F$ is a separate formulation and has not been independently run here.
- **Solid viscosity affects the solution but is unnecessary for completion in this case.** It should be judged against deformation, flow and reference data rather than retained or discarded solely because a run completes.

These comparisons hold the volumetric penalty fixed. They do not rank its importance, establish mesh/time-step convergence, or demonstrate that the zero-viscosity case can use a larger time step.

##### Recommended combination from the simulations so far (2026-10-17)

**For the tested G64/R2 mixed Q1+P1 case, the leading candidate is CBS43 + modified invariants + the existing volumetric stabilisation, with zero added solid viscosity.** This is a provisional choice based on full-cycle completion and the least extreme minimum $J$ among the compared cases, rather than a demonstrated accuracy optimum.

| Setting | Current recommendation |
|:---|:---|
| Fluid grid / solid mesh | G64 / R2, mixed Q1+P1 |
| Coupling kernel | `--ib-kernel cbs43` |
| Constitutive stress | `--sarah --sarah-stress mod` (modified invariants) |
| Volumetric penalty | `--beta-s 5e6` |
| Added solid viscosity | `--solid-nu 0`, provisionally |
| Time step | `--dt 2e-5` s |
| Outlet treatment | `--outlet-backflow` enabled |

Retain the other settings of the completed comparison: $L_z=16.2$ cm, fluid `--nu 0.04`, tether `--kappa-s 5e6`, `--feedback-kappa 25000`, `--gap-kappa 5e7`, `--gap-mask 3.6`, `--gap-ramp 0.13` and `--passive-rim 3.73`. The `--kappa-s` option here sets tether strength, not the volumetric penalty. GPU level D with FMA was used for these runs.

The recommended case completes to 1.335 s with $J_{\min}=0.211472$, compared with 0.167943 for modified stress with `solid-nu=1000` and 0.009898 for original stress with `solid-nu=1000`. However, its $J_{\max}=2.84226$ is worse than 2.65547 in the modified, viscous case, and $J_{\min}=0.211472$ still represents severe local compression. Keep the `solid-nu=1000` case as a reference: zero viscosity is not a uniformly better deformation result, and its lower backflow is not evidence of greater accuracy without reference data.

This recommendation applies to this tested configuration and time step. A larger stable time step, transfer of the recommendation to G128, and comparison against direct deviatoric projection remain unverified. The volumetric coefficient was held fixed rather than optimised.

#### (3) Volumetric stabilisation: parameter naming and limits

The volume penalty above supplements the Eulerian incompressibility constraint; it does not replace the pressure solve. In the convention $U=\frac12\kappa_{\mathrm{vol}}(\ln J)^2$, our $\kappa_{\mathrm{vol}}=2\beta_s$. **The solver option `--kappa-s` instead controls tether strength** (`beta_tether = 100*kappa_s`), so it must not be confused with this volumetric coefficient.

The stress comparison holds $\beta_s$ fixed and therefore is not a bulk-penalty sweep. Increasing the penalty can resist volume changes more strongly but also makes the coupled problem stiffer; it does not automatically permit a larger time step. Solid viscosity (`--solid-nu`) is another independent numerical stabilisation and is distinct from fluid viscosity (`--nu`).

#### (4) Element type: P1, P2, Q1, Q2


{{< table-caption "9" "Element types and benchmark errors" >}}

| Element | Torsion error, $n = 6$ (MFAC) | Cook error, $n = 16$ (MFAC) | MV runs |
|:---|---:|---:|:---|
| P1 tet | +16.2 % (1.43) | +0.89 % (1.86) | 0.0.3, {{< label "run" "G5" >}}, {{< label "run" "G6" >}} (full cycle) |
| P2 tet | +1.7 % (0.72) | +0.48 % (0.93) | {{< label "run" "G3" >}} / {{< label "run" "G4" >}}: failed (old non-conforming tet split); {{< label "config" "G64/R0/P2/BF" >}}: full cycle with `glamv_ibamr_p2v` and outlet backflow stabilisation |
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

The {{< label "config" "G64/R2/P1+Q1/BF" >}} run completed 66,750 steps to 1.335 s with the same time step, level-D/FMA settings and solid viscosity as R0. Its signed flow volumes use the z ≈ 12 cm curve at 0.01 s sampling. Reported local volume ratios range from $J_{\min}=0.010$ to $J_{\max}=2.454$, including passive-rim cells. Completion does not establish mesh convergence or acceptable local element deformation.

R2 construction and geometry-preservation limitations are described in the [mesh note]({{< relref "mv-meshes.md" >}}#legacy-hextet-interface-treatment). The lowest reported J occurs at t = 0.89 s in a marker-2001 papillary cap ($J \approx 0.00990$), with no nonpositive Jacobians found in that exported frame.

The {{< label "config" "G64/R1/P1+Q1/BF" >}} run completed 66,750 steps to 1.335 s with the same time step, level-D/FMA settings and solid viscosity as R0. Its signed flow volumes use the z ≈ 12 cm curve at 0.01 s sampling. Reported local volume ratios range from $J_{\min}=0.134$ to $J_{\max}=2.692$, including passive-rim cells. Completion does not establish mesh convergence or acceptable local element deformation.

The {{< label "config" "G64/R0/P2/BF" >}} run uses `glamv_ibamr_p2v`: the R0/P1 tetrahedra enriched with shared edge-midpoint nodes (169,923 markers, 80,074 ten-node tetrahedra, four-point quadrature). It retains the P1 reference geometry, cell markers, fibres, sheets and tethers. With the same GPU level-D/FMA settings, $\Delta t = 2 \times 10^{-5}$ s and outlet backflow stabilisation as the other BF runs, it completed 66,750 steps to 1.335 s without reported NaN or CUDA errors. Figures 1–3 include all 135 output frames: 0.01 s spacing through 1.33 s and the final 1.335 s frame.


{{< table-caption "12" "Run outcomes and flow metrics" >}}

| Run | Grid | Solid mesh | Leaflets | $\Delta t$ (s) | Outcome | Forward 0.04–0.2 (cm³) ‡ | Backflow 0.2–0.56 (cm³) | $J_{\min}$ |
|:---|:---|:---|:---|---:|:---|---:|---:|---:|
| 0.0.3 | {{< label "grid" "G-64" >}} | P1 tet (glamv_ibamr) | fibre HGO | $2 \times 10^{-5}$ | full cycle | 38.5 | −16.4 | 0.31 |
| {{< label "config" "G64/R0/P2/BF" >}} | {{< label "grid" "G-64" >}} | P2 tet (glamv_ibamr_p2v) | fibre HGO | $2 \times 10^{-5}$ | full cycle | 47.38 | -3.50 | 0.215 |
| {{< label "config" "G64/R1/P1+Q1/BF" >}} | {{< label "grid" "G-64" >}} | Q1+P1 (glamv_hex_r1) | fibre HGO | $2 \times 10^{-5}$ | full cycle | 47.11 | -2.88 | 0.134 |
| {{< label "config" "G64/R2/P1+Q1/BF" >}} | {{< label "grid" "G-64" >}} | Q1+P1 (glamv_hex_r2) | fibre HGO | $2 \times 10^{-5}$ | full cycle | 47.22 | -3.26 | 0.010 |

P2/BF flow volumes are signed trapezoidal integrals of the z ≈ 12 cm curve over the indicated windows, using the 0.01 s frames. Its $J_{\min}$ is the minimum reported in `solid_stats.csv` over all cells, including the passive rim. The historical 0.0.3 row retains its original sampling.


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

{{< chart height="340" xlabel="t (s)" ylabel="Q through the tube lumen, z = 12 cm (cm³/s)" colors="#8c564b,#edae49,#00798c,#7a7a7a,#9467bd,#30638e,#2ca02c,#d1495b,#111111,#e377c2,#17becf,#bcbd22,#006d2c,#54278f" caption="Figure 1. Lumen flow rate (r < 3.5 cm) at the exported plane nearest z = 12 cm (z = 11.98125 cm). Five new G64/R0 runs use GPU level D with FMA, sampled every 0.01 s through 1.335 s. Historical G11, G7, G5 and 0.0.3 curves retain their original 0.04 s samples; IBAMR is reference inlet flux through 0.65 s. BF denotes outlet backflow stabilisation; NBF omits it. G64/R1/P1+Q1/BF uses the same level-D/FMA settings and 0.01 s output sampling, completing 1.335 s. G64/R2/P1+Q1/BF uses the same level-D/FMA settings and 0.01 s output sampling, completing 1.335 s. The two G128 shortened-domain runs use Lz = 16.09938 cm, dt = 5e-6 s, solid-nu = 125, feedback-kappa = 50000 and gap-kappa = 1e8, at GPU level D with FMA. Their nearest exported z = 12 cm plane is z = 11.99068406 cm. R1 ends at its last valid frame, 0.85 s (NaNs detected at 0.86 s); R2 ends at 1.12 s (NaNs detected at 1.13 s). No values are extrapolated beyond those frames." >}}
t, G11 (historical P1+Q1 BF), G7 (hex), G5 (tet conf.), 0.0.3 (tet), IBAMR, G64/R0/P1/BF, G64/R0/P1/NBF, G64/R0/P1+Q1/BF, G64/R0/Q2+P2/BF, G64/R0/P2/BF, G64/R1/P1+Q1/BF, G64/R2/P1+Q1/BF, G128/R1/P1+Q1/BF (Lz=16.09938), G128/R2/P1+Q1/BF (Lz=16.09938)
0.000, 0.0, 0.0, 0.0, 0.0, 0.0, 0.000000, 0.000000, 0.000000, 0.000000, 0.000000, 0.000000, 0.000000, 0.000000, 0.000000
0.010, , , , , , 0.000000, 0.000000, 0.000000, 0.000000, 0.000000, 0.000000, 0.000000, 0.000000, 0.000000
0.020, , , , , , 0.000000, 0.000000, 0.000000, 0.000000, 0.000000, 0.000000, 0.000000, 0.000000, 0.000000
0.030, , , , , , 15.302135, 15.302135, 15.450807, 15.451653, 15.371845, 15.278161, 15.338720, 17.432002, 17.423934
0.040, 55.4, 55.4, 52.8, 54.2, 57.0, 54.155305, 54.155315, 55.414415, 55.674585, 55.145045, 54.590217, 55.157208, 64.597041, 64.717352
0.050, , , , , , 110.772429, 110.772468, 115.372837, 116.382713, 115.032929, 113.467493, 115.200138, 138.491619, 139.258674
0.060, , , , , , 183.594911, 183.594981, 194.506916, 195.722134, 193.322694, 190.795847, 193.855448, 235.317885, 236.744611
0.070, , , , , , 268.265779, 268.265881, 286.803983, 285.945646, 282.460227, 280.000304, 283.564479, 342.479317, 342.678392
0.080, 367.9, 367.9, 333.5, 341.0, 309.3, 340.991404, 340.991532, 367.929611, 365.066735, 360.529692, 358.541038, 361.933306, 431.438442, 428.590668
0.090, , , , , , 388.298451, 388.298589, 424.099316, 422.188564, 417.399289, 414.214445, 417.382527, 499.487048, 496.543745
0.100, , , , , , 414.059516, 414.059633, 460.401172, 458.671125, 453.345986, 449.721798, 452.285831, 550.791342, 549.478104
0.110, , , , , , 421.796818, 421.796912, 480.435499, 481.709308, 475.856788, 472.446066, 474.867835, 586.347938, 586.734686
0.120, 488.5, 488.5, 411.9, 415.6, 373.9, 415.600923, 415.601000, 488.520838, 492.126654, 484.592779, 482.747875, 483.513481, 599.948712, 600.801949
0.130, , , , , , 407.907057, 407.907137, 490.579539, 489.685029, 481.780166, 485.100257, 482.073948, 602.166824, 600.281446
0.140, , , , , , 405.843705, 405.843795, 489.589537, 491.693412, 480.575311, 484.593196, 479.520777, 612.449664, 607.860990
0.150, , , , , , 408.745073, 408.745161, 482.960849, 497.165730, 483.163658, 482.141867, 482.080638, 618.345676, 612.133638
0.160, 482.0, 482.0, 403.7, 415.3, 385.0, 415.343671, 415.343597, 482.013767, 504.100343, 487.037599, 487.098060, 488.115566, 631.042871, 619.725815
0.170, , , , , , 255.964239, 255.924809, 327.077229, 355.180055, 339.397300, 334.494143, 335.996914, 459.300604, 452.316316
0.180, , , , , , -2.486140, -8.360313, 57.528116, 92.118889, 82.229351, 72.291034, 73.023836, 150.739506, 151.353387
0.190, , , , , , -264.372186, -385.069403, -237.416951, -221.314240, -221.777026, -222.065672, -224.826777, -225.990710, -223.904457
0.200, -406.1, -574.8, -460.1, -473.2, -488.2, -380.989226, -473.228466, -406.125571, -413.214232, -409.742810, -404.366195, -408.894136, -428.021165, -420.290604
0.210, , , , , , -73.658507, 134.268087, -161.590459, -277.746556, -267.720379, -193.586638, -237.952327, -241.009080, -263.836471
0.220, , , , , , -6.533408, -43.370573, 10.350636, 44.533538, 43.453500, 37.325837, 42.960789, 61.768865, 88.926768
0.230, , , , , , -88.623403, -125.630648, -80.451999, -33.214729, -31.599589, -44.745799, -37.178110, -76.203807, -59.126989
0.240, -68.6, -34.7, -14.6, -17.7, -27.3, -60.825953, -17.669249, -68.643939, -47.558963, -49.184359, -43.854696, -45.861656, -80.096962, -60.841061
0.250, , , , , , -46.470987, -60.930110, -48.035431, -19.976620, -19.550745, -20.631233, -20.104029, -28.119695, -6.260672
0.260, , , , , , -46.997953, -50.876088, -46.741749, -19.107174, -18.467569, -19.506273, -18.978721, -49.249060, -29.124573
0.270, , , , , , -40.896543, -32.301530, -43.722058, -16.284948, -17.517869, -16.817273, -15.389031, -39.899145, -14.660810
0.280, -44.9, -46.6, -48.9, -51.8, -55.5, -44.350677, -51.783934, -44.923890, -15.742034, -16.768080, -16.906798, -16.693058, -47.612514, -16.400928
0.290, , , , , , -38.857984, -35.584764, -40.409412, -10.852489, -12.080819, -10.877139, -10.704469, -43.665035, -11.128688
0.300, , , , , , -37.533148, -35.527696, -34.941098, -6.176122, -6.799936, -6.687755, -7.045422, -37.592773, -5.319631
0.310, , , , , , -35.521565, -33.563522, -33.291404, -4.880362, -5.742563, -5.456044, -5.244132, -38.387172, -5.251060
0.320, -31.6, -29.7, -33.8, -34.2, -19.9, -33.179347, -34.096410, -31.637515, -2.705452, -2.689788, -2.403200, -2.864706, -39.379645, -2.228640
0.330, , , , , , -31.482269, -32.908213, -28.133296, -0.975697, -0.610596, -0.330911, -0.461478, -35.330218, -0.596147
0.340, , , , , , -26.559335, -29.849134, -26.123762, 0.870825, 1.186047, 1.228986, 0.778587, -30.698952, -0.328999
0.350, , , , , , -27.689878, -29.434733, -24.671120, 1.677542, 2.212195, 2.279501, 1.897057, -26.410524, 1.392732
0.360, -26.1, -27.7, -28.6, -33.2, -19.2, -30.272555, -34.749743, -26.494454, -0.287875, 0.514340, 0.214327, 0.419540, -33.461841, -1.445596
0.370, , , , , , -29.283367, -29.488760, -25.901209, 0.561211, 0.970016, 0.913575, 0.759096, -30.685150, -0.162227
0.380, , , , , , -24.601017, -27.079018, -24.648802, 2.378746, 2.346428, 2.489341, 2.244590, -25.139549, 1.377729
0.390, , , , , , -22.425538, -23.662397, -23.110125, 3.585812, 3.886286, 3.725236, 3.536665, -25.291947, 3.369836
0.400, -22.5, -23.2, -22.2, -22.9, -13.7, -23.052209, -20.791408, -21.189093, 4.247542, 4.580980, 4.414163, 4.535854, -21.315171, 3.775897
0.410, , , , , , -24.116922, -23.679238, -21.399674, 4.536793, 4.702952, 4.835858, 4.617783, -23.394418, 3.376299
0.420, , , , , , -24.162805, -19.912882, -21.793298, 4.659874, 4.820271, 4.645150, 4.597081, -24.868708, 3.712357
0.430, , , , , , -22.777272, -24.522556, -21.953644, 4.496769, 4.849711, 4.747952, 4.655571, -20.815324, 3.478809
0.440, -19.6, -21.3, -17.9, -22.6, -11.2, -22.723508, -23.116546, -20.123429, 4.930400, 5.257579, 5.200221, 4.958646, -20.063241, 4.319091
0.450, , , , , , -21.964529, -23.074289, -18.351347, 5.760475, 5.879567, 5.836836, 5.650734, -19.534332, 5.238075
0.460, , , , , , -21.147629, -21.468215, -18.536605, 6.702068, 6.910142, 6.967562, 6.789456, -17.345046, 5.266897
0.470, , , , , , -17.116364, -16.551059, -15.141175, 8.290738, 8.462197, 8.423771, 8.271040, -12.491598, 6.916202
0.480, -13.4, -13.2, -14.2, -11.1, -7.0, -13.142335, -8.310724, -11.915965, 10.716005, 10.922893, 10.764248, 10.609759, -9.036011, 9.990696
0.490, , , , , , -13.135519, -7.928642, -9.634189, 12.755644, 12.949212, 12.818167, 12.694370, -7.209688, 11.908068
0.500, , , , , , -11.680145, -15.863780, -9.246272, 13.668971, 13.599018, 13.539387, 13.275241, -5.108474, 12.155575
0.510, , , , , , -8.471614, -10.345004, -7.442904, 14.773133, 14.755080, 14.643957, 14.510252, -1.701018, 14.029961
0.520, -4.9, -3.5, 0.4, -6.3, 0.8, -5.650191, -5.875544, -4.457152, 17.518980, 17.533919, 17.432632, 17.016385, 2.569240, 16.843968
0.530, , , , , , 2.258965, 1.332347, 2.302365, 22.826917, 22.834670, 22.719061, 22.510803, 9.072728, 23.025817
0.540, , , , , , 14.671497, 13.197048, 14.361884, 32.816821, 33.066744, 32.882384, 32.508675, 21.679956, 33.828165
0.550, , , , , , 29.350113, 29.174328, 30.690658, 47.304361, 47.445701, 47.084971, 46.740827, 37.942779, 49.767388
0.560, 47.8, 47.7, 46.1, 50.8, 15.0, 45.877677, 48.590668, 49.035600, 61.931909, 61.886113, 61.888679, 61.190857, 54.096700, 64.410378
0.570, , , , , , 61.175150, 60.436199, 63.706738, 73.432212, 73.763448, 73.188532, 72.347972, 68.189311, 74.477192
0.580, , , , , , 69.249986, 68.592370, 72.691570, 78.635404, 79.098528, 78.513504, 78.124358, 77.550465, 80.464350
0.590, , , , , , 70.800251, 70.181023, 74.856226, 77.598293, 78.388575, 77.885706, 77.810888, 77.534821, 80.649884
0.600, 189.4, 186.0, 176.8, 180.6, 451.8, 183.410395, 180.308686, 190.376436, 186.740684, 189.106512, 190.353883, 189.017863, 208.069403, 214.401446
0.610, , , , , , 349.411364, 343.576520, 354.565170, 341.827967, 343.770320, 351.568695, 344.843396, 419.029916, 425.882046
0.620, , , , , , 480.587557, 471.383885, 499.103304, 485.862056, 489.129949, 487.633855, 479.665089, 607.224954, 617.172601
0.630, , , , , , 546.103234, 537.188701, 586.755510, 561.573775, 561.027385, 564.202334, 551.529605, 697.871365, 699.785991
0.640, 615.3, 616.3, 539.4, 558.3, 535.5, 562.522078, 552.374873, 616.705835, 595.595711, 593.560632, 594.963039, 581.727409, 744.425361, 747.703684
0.650, , , , , , 537.665574, 535.037858, 605.094230, 595.382024, 594.159054, 588.431035, 583.270429, 728.521036, 731.643270
0.660, , , , , , 491.560104, 495.538262, 575.778027, 573.973111, 569.978119, 563.626634, 557.887073, 681.851881, 680.142770
0.670, , , , , , 462.157907, 460.464862, 546.196757, 541.060180, 533.910112, 530.949672, 523.816937, 667.248955, 658.226681
0.680, 520.3, 531.8, 431.3, 452.6, , 444.081000, 442.606523, 520.158105, 517.830435, 511.350730, 505.698798, 502.900768, 655.103021, 638.135308
0.690, , , , , , 435.951544, 427.093004, 504.641785, 501.538481, 499.511855, 496.410255, 497.257947, 649.446088, 635.508252
0.700, , , , , , 429.718604, 413.753206, 494.764928, 486.447040, 491.758783, 489.488505, 483.356452, 646.444041, 632.707855
0.710, , , , , , 425.758966, 403.831138, 489.505626, 479.157750, 483.691815, 475.121394, 467.734560, 638.280931, 626.856264
0.720, 481.6, 475.4, 381.8, 402.7, , 413.001473, 393.929687, 482.705995, 473.459215, 473.921951, 461.513954, 456.779628, 627.459193, 623.114274
0.730, , , , , , 405.083124, 390.492940, 477.325976, 468.664483, 464.416006, 450.140266, 445.795315, 625.773855, 619.749756
0.740, , , , , , 395.223089, 389.025998, 469.337249, 458.594607, 449.817728, 440.392021, 434.616658, 624.235962, 613.655130
0.750, , , , , , 388.197378, 382.574992, 454.127990, 447.570622, 437.004794, 428.799376, 428.904093, 620.572254, 609.151271
0.760, 443.9, 428.6, 359.6, 373.7, , 382.506872, 370.149350, 447.752027, 433.419422, 429.121995, 423.267793, 420.718461, 614.142048, 604.541148
0.770, , , , , , 376.837036, 356.975500, 442.345727, 423.010625, 417.526452, 426.052501, 405.315052, 605.088248, 597.820770
0.780, , , , , , 371.032493, 350.498096, 436.082005, 422.448475, 412.072862, 423.632117, 397.674602, 597.949989, 594.039923
0.790, , , , , , 361.365330, 345.188014, 426.713328, 424.974771, 410.383027, 423.844639, 395.740491, 600.026252, 591.837255
0.800, 428.1, 408.4, 323.0, 339.7, , 353.980653, 340.312715, 417.575253, 420.167818, 413.097947, 421.606545, 393.375721, 599.481807, 591.425131
0.810, , , , , , 348.544479, 333.817357, 412.086247, 413.168497, 415.047633, 415.143666, 393.308510, 596.248104, 586.419138
0.820, , , , , , 350.262139, 335.558307, 414.130631, 406.764352, 412.758147, 407.973655, 394.235359, 597.911972, 583.702982
0.830, , , , , , 351.232518, 332.097003, 411.461746, 405.234155, 408.146523, 397.216063, 390.506957, 599.600274, 580.158612
0.840, 415.0, 403.8, 317.4, 328.1, , 346.830821, 326.574718, 413.429661, 403.062331, 402.961803, 391.903235, 383.874671, 599.069708, 574.863928
0.850, , , , , , 347.944972, 325.211824, 413.016842, 400.049023, 396.973298, 391.037376, 382.340937, 611.948353, 569.100550
0.860, , , , , , 348.175979, 321.993970, 412.665299, 397.746690, 393.395753, 389.685565, 379.895965, , 566.301389
0.870, , , , , , 340.667615, 316.496687, 409.580024, 397.308405, 386.318105, 381.756870, 375.769409, , 560.937778
0.880, 396.7, 375.2, 310.0, 322.0, , 340.497016, 313.108334, 404.481136, 391.605268, 384.205594, 376.841486, 378.358308, , 552.880931
0.890, , , , , , 340.246009, 307.015391, 400.294729, 383.540910, 380.632512, 371.596589, 384.203383, , 548.261935
0.900, , , , , , 336.130264, 300.997420, 401.596740, 377.388471, 377.330078, 367.424008, 377.734326, , 547.433021
0.910, , , , , , 202.880062, 153.550979, 262.342999, 248.877021, 249.157172, 237.969408, 245.793265, , 398.180932
0.920, 34.0, , -100.2, -88.5, , -19.036091, -99.446773, 33.929992, 38.018874, 34.307433, 27.456721, 30.723690, , 150.947385
0.930, , , , , , -267.716850, -456.972225, -242.471234, -232.650926, -231.265279, -233.386682, -237.194840, , -212.618190
0.940, , , , , , -371.996880, -288.053210, -404.881150, -410.649983, -411.467267, -404.469525, -409.690815, , -426.623096
0.950, , , , , , -66.676533, 111.792358, -161.065035, -190.413033, -208.005191, -175.818019, -157.236654, , -278.766650
0.960, 4.5, , -89.5, -80.1, , -9.354320, -84.535243, 10.810423, 38.833123, 41.588277, 37.238142, 38.433243, , 93.979795
0.970, , , , , , -87.047214, -104.131364, -81.061500, -49.455421, -44.402192, -49.815781, -52.238840, , -62.233303
0.980, , , , , , -59.531948, -18.298254, -71.665466, -40.397859, -43.455502, -40.689351, -39.107293, , -58.839219
0.990, , , , , , -46.725169, -65.351817, -46.876151, -20.286500, -19.165025, -19.954590, -19.057840, , -5.587096
1.000, -47.9, , -38.8, -40.6, , -47.865269, -43.278611, -48.157187, -21.143004, -20.122438, -20.699258, -19.302798, , -29.835298
1.010, , , , , , -41.007678, -39.420118, -43.852582, -16.061410, -16.449675, -16.787528, -14.603705, , -15.270911
1.020, , , , , , -44.016670, -49.012597, -44.727412, -18.326754, -16.496527, -17.912519, -16.247127, , -17.961674
1.030, , , , , , -39.311602, -39.961355, -40.075712, -11.181314, -11.170883, -9.604703, -9.869296, , -14.878981
1.040, -34.7, , -35.6, -35.7, , -34.939724, -38.152825, -35.608653, -6.725695, -8.073736, -7.350919, -6.647619, , -11.069145
1.050, , , , , , -34.597160, -33.582340, -34.741888, -5.703612, -5.385370, -4.765337, -5.156659, , -16.154473
1.060, , , , , , -33.175311, -27.913802, -31.104039, -2.794049, -2.708285, -2.324103, -3.077883, , -10.346751
1.070, , , , , , -31.987738, -32.507873, -30.008366, -0.936899, -0.417322, -0.292398, -1.059480, , -8.223903
1.080, -27.9, , -30.1, -30.5, , -31.599501, -23.404650, -29.122974, 1.086244, 1.241411, 0.864431, 0.986729, , -1.742091
1.090, , , , , , -26.546829, -27.355465, -26.741273, 2.038854, 2.222877, 2.021469, 1.756289, , -7.227736
1.100, , , , , , -31.045450, -28.059691, -29.188811, 0.034895, -0.064164, 0.024248, -0.272754, , -4.306029
1.110, , , , , , -28.929179, -28.044339, -27.823524, 0.927042, 1.179645, 0.987039, 0.693529, , -8.394460
1.120, -26.3, , -24.6, -25.7, , -23.488504, -23.860669, -26.018726, 2.323087, 2.565976, 2.459218, 2.467937, , -4.472143
1.130, , , , , , -26.049883, -22.847362, -23.516293, 3.499509, 3.529469, 3.516487, 3.467318, ,
1.140, , , , , , -21.861601, -23.100385, -23.660450, 4.245210, 4.559253, 4.511015, 4.079058, ,
1.150, , , , , , -21.926875, -23.307980, -22.412886, 4.568186, 4.458444, 4.369229, 4.491496, ,
1.160, -21.2, , -21.2, -23.0, , -22.054686, -23.243838, -22.578184, 4.571375, 4.662119, 4.677874, 4.540383, ,
1.170, , , , , , -24.418911, -21.389086, -21.244603, 4.629653, 4.647298, 4.674410, 4.530025, ,
1.180, , , , , , -20.571408, -20.873730, -20.727164, 4.937203, 4.880148, 4.818757, 4.755643, ,
1.190, , , , , , -18.600040, -18.599680, -20.210747, 5.553301, 5.588402, 5.537097, 5.516923, ,
1.200, -18.9, , -13.7, -18.8, , -20.755604, -20.267101, -19.868170, 6.655185, 6.664147, 6.763855, 6.537775, ,
1.210, , , , , , -17.571310, -17.511876, -16.480097, 7.972919, 8.289245, 8.068572, 8.242750, ,
1.220, , , , , , -15.364219, -12.438094, -14.378125, 10.546362, 10.416064, 10.217157, 10.214180, ,
1.230, , , , , , -11.082967, -9.664035, -11.791439, 12.667574, 12.522814, 12.388091, 12.229103, ,
1.240, -10.4, , -9.9, -10.8, , -8.866004, -7.600638, -9.009365, 13.135256, 13.030090, 13.114781, 12.518829, ,
1.250, , , , , , -6.117880, -10.478627, -8.108011, 14.330431, 14.342497, 14.271042, 13.744512, ,
1.260, , , , , , -6.636767, -2.381083, -4.958830, 17.205279, 17.034139, 17.015749, 16.454119, ,
1.270, , , , , , 1.903504, 1.775815, 0.090216, 22.381605, 22.269707, 21.975872, 21.566905, ,
1.280, 13.7, , 10.8, 13.3, , 11.552993, 13.171769, 13.820753, 32.553001, 32.099484, 31.887963, 31.275212, ,
1.290, , , , , , 27.345517, 29.447381, 29.951434, 46.977182, 46.495977, 45.829858, 45.229193, ,
1.300, , , , , , 45.934514, 45.870686, 46.576786, 61.282837, 60.579145, 60.647236, 59.789053, ,
1.310, , , , , , 59.686644, 59.494650, 60.997914, 71.884434, 72.193777, 71.366276, 69.552340, ,
1.320, 72.2, , 67.5, 69.2, , 69.020176, 68.649707, 72.195650, 77.410611, 78.167694, 76.047865, 75.588614, ,
1.330, , , , , , 72.906564, 70.491795, 73.882045, 75.946522, 76.147354, 75.660008, 75.174352, ,
1.335, 119.4, , 109.1, 115.7, , 119.432709, 114.403640, 123.345875, 122.156237, 122.427490, 123.003170, 121.990742, ,
{{< /chart >}}

The two shortened-domain G128 flow-rate series are also available as [CSV](/data/mv-g128-short-domain-flow.csv).

{{< chart height="280" xlabel="t (s)" ylabel="lumen fraction with w < 0 (%)" colors="#8c564b,#edae49,#00798c,#7a7a7a,#30638e,#2ca02c,#d1495b,#111111,#e377c2,#17becf,#bcbd22" caption="Figure 2. Fraction of lumen points with downward velocity one exported grid plane below the outlet (z = 16.03125 cm). Five new G64/R0 level-D runs are sampled every 0.01 s; historical curves retain their original samples. All five new runs reach 1.335 s. G64/R1/P1+Q1/BF uses the same level-D/FMA settings and 0.01 s output sampling, completing 1.335 s. G64/R2/P1+Q1/BF uses the same level-D/FMA settings and 0.01 s output sampling, completing 1.335 s." >}}
t, G11 (historical P1+Q1 BF), G7 (hex), G5 (tet conf.), 0.0.3 (tet), G64/R0/P1/BF, G64/R0/P1/NBF, G64/R0/P1+Q1/BF, G64/R0/Q2+P2/BF, G64/R0/P2/BF, G64/R1/P1+Q1/BF, G64/R2/P1+Q1/BF
0.000, 0.0, 0.0, 0.0, 0.0, 0.000000, 0.000000, 0.000000, 0.000000, 0.000000, 0.000000, 0.000000
0.010, , , , , 15.735087, 17.989667, 67.449507, 7.750117, 9.534993, 18.929075, 1.315171
0.020, , , , , 65.523720, 23.062471, 25.598873, 56.928135, 71.019258, 55.425082, 3.100047
0.030, , , , , 0.375763, 0.375763, 0.375763, 0.000000, 0.000000, 0.000000, 0.000000
0.040, 0.4, 0.4, 0.4, 0.4, 0.375763, 0.375763, 0.375763, 0.375763, 0.375763, 0.000000, 0.375763
0.050, , , , , 0.563645, 0.375763, 0.939408, 0.375763, 0.375763, 0.000000, 0.375763
0.060, , , , , 0.751527, 0.751527, 0.939408, 0.375763, 0.563645, 0.375763, 0.516674
0.070, , , , , 0.751527, 0.751527, 0.939408, 0.375763, 0.563645, 0.375763, 0.751527
0.080, 1.3, 1.3, 1.3, 1.3, 1.315171, 1.315171, 1.315171, 1.503053, 1.315171, 1.127290, 2.160639
0.090, , , , , 1.315171, 1.315171, 1.315171, 1.831846, 1.972757, 1.925787, 3.804603
0.100, , , , , 1.315171, 1.315171, 1.315171, 2.254580, 2.254580, 1.831846, 3.193988
0.110, , , , , 1.315171, 1.315171, 1.315171, 2.254580, 2.771254, 2.630343, 4.039455
0.120, 0.9, 0.9, 0.9, 0.9, 1.127290, 0.892438, 0.939408, 2.489432, 2.912165, 2.630343, 4.133396
0.130, , , , , 0.892438, 0.892438, 1.033349, 3.006106, 3.100047, 2.959136, 3.663692
0.140, , , , , 0.798497, 0.704556, 0.657586, 2.630343, 2.771254, 3.006106, 3.334899
0.150, , , , , 0.610615, 0.657586, 0.563645, 2.348520, 2.630343, 2.959136, 3.006106
0.160, 0.6, 0.6, 0.6, 0.7, 0.610615, 0.657586, 0.610615, 2.536402, 3.100047, 2.865195, 4.321278
0.170, , , , , 4.039455, 6.716768, 3.100047, 5.495538, 5.824331, 6.247064, 6.387976
0.180, , , , , 72.334429, 57.914514, 55.800845, 45.608267, 49.131047, 53.076562, 52.325035
0.190, , , , , 99.812118, 99.201503, 99.624237, 100.000000, 99.812118, 100.000000, 100.000000
0.200, 99.1, 98.0, 96.5, 96.8, 99.060592, 96.759042, 99.060592, 100.000000, 100.000000, 100.000000, 99.812118
0.210, , , , , 94.316581, 0.140911, 96.618131, 97.698450, 98.590888, 96.430249, 96.571160
0.220, , , , , 78.957257, 93.236261, 28.651949, 0.845467, 0.469704, 0.375763, 1.503053
0.230, , , , , 96.993894, 91.451386, 96.148426, 92.484735, 93.705965, 96.477219, 91.733208
0.240, 94.3, 75.1, 68.0, 65.0, 94.551433, 65.007046, 94.316581, 92.437764, 92.296853, 93.799906, 90.371066
0.250, , , , , 92.390794, 84.405824, 90.652889, 84.217943, 83.184594, 86.754345, 83.231564
0.260, , , , , 91.545326, 76.561766, 87.552842, 83.184594, 82.527008, 83.889150, 82.057304
0.270, , , , , 89.948333, 76.702677, 84.593706, 81.681541, 81.258807, 80.930014, 79.192109
0.280, 83.9, 78.3, 82.3, 79.1, 89.572569, 79.051198, 83.889150, 81.211837, 79.755754, 81.493659, 79.661813
0.290, , , , , 88.539220, 74.542039, 81.916393, 76.655707, 75.810240, 76.702677, 75.434476
0.300, , , , , 87.693753, 75.951151, 79.567872, 71.958666, 71.911696, 72.334429, 70.455613
0.310, , , , , 86.942226, 75.058713, 78.957257, 70.314702, 68.341945, 71.113199, 67.402536
0.320, 77.0, 63.5, 77.1, 74.1, 86.660404, 74.119305, 76.984500, 66.604039, 64.208549, 67.355566, 65.007046
0.330, , , , , 85.908877, 73.132926, 75.434476, 62.705496, 61.108502, 63.269140, 61.484265
0.340, , , , , 84.030061, 73.743542, 74.917802, 59.981212, 59.276656, 59.699389, 59.041804
0.350, , , , , 84.358854, 73.555660, 75.058713, 58.431188, 58.572100, 58.196336, 57.773603
0.360, 76.0, 62.6, 72.0, 75.1, 83.842179, 75.387506, 76.232973, 59.417567, 59.558478, 59.464537, 57.585721
0.370, , , , , 82.620949, 72.804133, 75.387506, 56.928135, 57.303899, 59.652419, 56.364490
0.380, , , , , 80.366369, 70.690465, 74.729920, 55.096289, 55.143260, 56.317520, 54.626585
0.390, , , , , 79.661813, 67.355566, 74.776891, 52.794739, 54.297792, 54.861437, 52.465946
0.400, 74.4, 59.8, 64.4, 68.5, 78.675434, 66.744951, 73.837482, 51.526538, 53.593236, 53.875059, 51.197745
0.410, , , , , 77.595115, 67.731329, 74.072334, 51.432597, 53.781118, 53.875059, 52.982621
0.420, , , , , 76.702677, 63.128229, 75.199624, 53.593236, 53.546266, 52.935651, 53.593236
0.430, , , , , 76.984500, 64.537341, 74.823861, 52.982621, 53.029591, 55.049319, 54.438704
0.440, 72.4, 59.4, 61.1, 60.7, 77.125411, 62.329732, 72.851104, 52.512917, 51.479568, 54.532644, 53.029591
0.450, , , , , 75.669328, 60.732738, 71.911696, 51.009864, 50.540160, 52.841710, 50.868953
0.460, , , , , 75.152654, 60.075153, 71.629873, 50.634101, 50.399248, 50.962893, 48.708314
0.470, , , , , 72.851104, 60.028182, 69.563175, 49.553781, 47.487083, 47.627994, 46.688586
0.480, 67.9, 57.2, 55.9, 61.0, 71.348051, 57.961484, 66.979803, 47.111320, 45.796148, 46.218882, 44.434007
0.490, , , , , 71.160169, 61.860028, 65.194927, 44.011273, 43.259746, 44.574918, 42.602161
0.500, , , , , 70.408643, 64.020667, 64.067637, 42.367309, 42.555190, 43.494598, 41.474871
0.510, , , , , 67.449507, 59.934241, 62.564584, 40.253640, 41.099108, 42.790042, 39.971818
0.520, 61.1, 53.4, 50.7, 57.4, 65.194927, 57.162987, 60.544857, 38.374824, 38.233913, 39.032410, 36.871771
0.530, , , , , 54.438704, 52.982621, 54.626585, 33.161109, 32.644434, 32.973227, 30.671677
0.540, , , , , 37.200564, 41.286989, 41.803664, 24.659465, 23.673086, 23.062471, 21.512447
0.550, , , , , 22.170033, 24.659465, 23.860968, 13.574448, 13.151714, 12.400188, 10.991076
0.560, 12.2, 15.1, 13.5, 10.3, 10.615312, 11.507750, 10.944105, 6.857680, 6.575857, 5.495538, 4.039455
0.570, , , , , 4.603100, 6.716768, 4.744011, 3.240958, 3.475810, 2.724284, 1.690935
0.580, , , , , 3.475810, 5.025834, 2.959136, 2.818225, 2.113668, 1.831846, 1.033349
0.590, , , , , 3.428840, 5.495538, 4.039455, 4.509159, 3.522781, 3.710662, 3.663692
0.600, 3.0, 3.3, 3.3, 3.1, 2.677313, 3.053077, 2.912165, 4.837952, 4.650070, 4.650070, 5.683419
0.610, , , , , 1.409112, 1.878816, 2.301550, 3.851574, 3.992485, 3.193988, 4.086426
0.620, , , , , 1.737905, 2.066698, 1.925787, 3.710662, 4.556130, 3.804603, 4.039455
0.630, , , , , 2.160639, 2.254580, 2.207609, 4.931893, 5.213715, 4.321278, 4.415218
0.640, 2.9, 2.5, 2.7, 2.6, 2.630343, 2.630343, 2.912165, 4.603100, 5.213715, 4.931893, 5.119775
0.650, , , , , 3.100047, 3.898544, 3.804603, 4.603100, 5.307656, 4.744011, 5.307656
0.660, , , , , 6.106153, 5.589479, 4.884922, 5.730390, 5.401597, 4.884922, 5.401597
0.670, , , , , 10.568342, 12.118365, 6.810709, 6.951620, 7.937999, 7.844058, 7.562236
0.680, 14.0, 14.6, 16.3, 17.8, 18.036637, 17.848755, 14.701738, 10.145608, 12.588070, 13.621419, 11.648661
0.690, , , , , 23.626116, 23.532175, 22.076092, 15.922969, 17.285110, 21.277595, 17.003288
0.700, , , , , 27.383748, 29.779239, 27.571630, 20.713950, 22.498826, 27.007985, 25.598873
0.710, , , , , 30.436825, 32.080789, 31.845937, 25.692814, 28.041334, 32.127760, 31.517144
0.720, 35.4, 31.7, 34.7, 34.5, 32.832316, 34.476280, 35.227806, 33.677783, 34.100517, 34.711132, 34.711132
0.730, , , , , 34.053546, 37.106623, 38.139972, 37.341475, 38.656646, 37.435416, 36.261155
0.740, , , , , 36.449037, 39.079380, 43.776421, 42.132457, 42.790042, 40.958196, 37.999061
0.750, , , , , 36.683889, 39.877877, 49.741663, 47.158290, 46.923438, 47.956787, 39.596054
0.760, 56.0, 38.9, 42.0, 40.5, 38.515735, 41.333960, 53.170503, 51.103805, 49.506811, 51.338657, 44.715829
0.770, , , , , 40.253640, 42.930953, 54.156881, 51.479568, 49.694692, 49.835604, 47.346172
0.780, , , , , 42.367309, 44.434007, 52.559887, 51.526538, 51.479568, 49.835604, 51.714420
0.790, , , , , 44.387036, 46.782527, 51.009864, 51.197745, 53.922029, 53.029591, 55.519023
0.800, 46.8, 50.7, 42.0, 51.2, 47.158290, 49.084077, 48.238610, 49.788633, 51.291686, 49.600752, 55.002349
0.810, , , , , 51.479568, 50.681071, 45.514326, 48.379521, 45.843119, 46.641616, 50.493189
0.820, , , , , 52.465946, 50.915923, 43.682480, 46.218882, 44.152184, 44.903711, 48.426491
0.830, , , , , 49.976515, 50.634101, 43.165806, 46.453734, 42.179427, 46.077971, 47.393142
0.840, 42.0, 48.0, 49.0, 53.6, 48.003758, 51.620479, 42.179427, 43.635510, 41.474871, 46.406764, 45.561296
0.850, , , , , 45.608267, 52.137154, 40.723344, 42.414279, 42.555190, 44.199155, 45.044622
0.860, , , , , 44.246125, 51.996242, 41.897605, 42.179427, 42.930953, 44.527947, 43.964302
0.870, , , , , 44.574918, 51.808361, 41.474871, 42.555190, 44.809770, 44.293095, 42.977924
0.880, 43.4, 46.5, 48.2, 50.4, 44.152184, 50.868953, 43.494598, 42.414279, 44.105214, 45.655237, 42.179427
0.890, , , , , 44.762799, 50.023485, 44.246125, 43.024894, 44.246125, 46.312823, 43.400658
0.900, , , , , 44.199155, 49.647722, 44.105214, 42.649131, 44.574918, 44.903711, 44.480977
0.910, , , , , 59.840301, 54.344763, 59.699389, 60.169093, 60.403946, 61.906999, 60.028182
0.920, 73.9, , 58.6, 60.4, 77.923908, 58.806952, 73.320808, 76.937529, 76.702677, 76.937529, 75.246595
0.930, , , , , 99.107562, 82.292156, 97.839361, 97.228746, 98.215124, 97.839361, 98.496947
0.940, , , , , 98.872710, 52.559887, 98.825740, 99.765148, 99.906059, 99.953030, 99.906059
0.950, , , , , 84.170972, 4.556130, 93.612024, 93.471113, 95.115078, 91.874119, 91.639267
0.960, 55.3, , 85.3, 82.7, 62.141851, 84.405824, 52.512917, 32.315641, 30.061062, 34.476280, 30.530766
0.970, , , , , 88.492250, 80.883044, 85.814937, 78.205730, 76.373884, 76.937529, 77.642085
0.980, , , , , 81.070925, 60.028182, 82.292156, 72.804133, 73.320808, 71.817755, 71.207140
0.990, , , , , 78.064819, 76.749648, 75.857210, 63.597933, 63.785815, 63.363081, 63.363081
1.000, 76.5, , 62.0, 64.2, 77.266322, 63.832785, 75.152654, 61.860028, 63.550963, 63.410052, 61.202442
1.010, , , , , 74.119305, 63.269140, 72.945045, 59.793330, 61.390324, 61.953969, 60.263034
1.020, , , , , 76.232973, 64.443401, 74.917802, 61.766087, 61.953969, 63.316111, 62.376703
1.030, , , , , 74.542039, 61.578206, 73.743542, 58.900892, 58.994833, 59.652419, 59.276656
1.040, 72.1, , 64.2, 63.2, 72.710193, 63.034288, 72.428370, 56.223579, 56.505402, 57.491780, 57.162987
1.050, , , , , 73.837482, 62.141851, 72.240488, 55.425082, 55.565993, 55.284171, 55.894786
1.060, , , , , 73.931423, 62.611555, 70.267731, 54.861437, 55.565993, 54.720526, 56.176609
1.070, , , , , 74.495068, 63.879756, 70.784406, 54.579615, 53.123532, 55.049319, 54.720526
1.080, 70.2, , 64.1, 62.0, 74.401127, 60.685768, 69.891968, 53.358384, 51.385627, 53.922029, 54.391733
1.090, , , , , 72.334429, 62.893377, 70.126820, 52.090183, 52.043213, 51.432597, 53.687177
1.100, , , , , 74.495068, 63.738845, 72.851104, 54.156881, 52.653828, 52.700798, 56.129638
1.110, , , , , 74.213246, 61.719117, 72.898074, 52.935651, 51.808361, 52.982621, 55.284171
1.120, 71.6, , 63.3, 62.8, 71.535932, 60.732738, 73.978394, 51.150775, 51.526538, 52.090183, 53.405355
1.130, , , , , 72.945045, 61.672147, 71.958666, 50.352278, 50.587130, 50.540160, 52.606858
1.140, , , , , 71.629873, 60.544857, 71.629873, 50.493189, 49.835604, 49.084077, 51.385627
1.150, , , , , 71.723814, 60.356975, 70.925317, 48.943166, 50.070456, 48.238610, 50.258337
1.160, 70.5, , 60.7, 60.9, 72.287459, 60.967590, 71.301080, 48.332550, 49.694692, 49.929544, 49.835604
1.170, , , , , 74.025364, 60.450916, 69.798027, 49.553781, 48.473462, 49.976515, 49.835604
1.180, , , , , 72.146548, 60.544857, 70.126820, 50.868953, 48.379521, 50.070456, 49.741663
1.190, , , , , 70.173791, 60.732738, 70.737435, 50.023485, 47.862846, 48.849225, 47.627994
1.200, 70.1, , 56.6, 59.3, 71.864725, 62.611555, 70.220761, 48.614373, 46.970409, 46.876468, 45.467356
1.210, , , , , 69.751057, 61.108502, 68.060122, 46.312823, 44.480977, 44.809770, 43.682480
1.220, , , , , 67.496477, 60.403946, 66.463128, 42.883983, 41.756693, 42.837013, 42.555190
1.230, , , , , 64.584312, 58.525129, 64.772194, 39.361202, 40.206670, 40.347581, 39.408173
1.240, 65.1, , 58.1, 57.9, 63.222170, 57.303899, 62.564584, 38.891498, 38.797558, 39.830907, 38.985439
1.250, , , , , 62.235791, 60.497886, 61.672147, 36.355096, 36.542978, 39.924847, 37.247534
1.260, , , , , 62.329732, 52.137154, 58.759981, 32.174730, 32.315641, 34.241428, 32.644434
1.270, , , , , 53.358384, 48.520432, 53.452325, 25.739784, 25.880695, 26.679192, 26.726163
1.280, 38.0, , 40.6, 38.6, 40.065759, 37.153593, 36.824800, 16.345702, 14.983560, 16.674495, 17.613903
1.290, , , , , 21.559418, 20.150305, 18.271489, 6.247064, 5.636449, 7.937999, 8.031940
1.300, , , , , 8.078910, 8.172851, 7.421325, 2.066698, 1.737905, 3.100047, 2.395491
1.310, , , , , 3.522781, 4.133396, 3.804603, 1.174260, 0.657586, 1.456083, 1.409112
1.320, 3.0, , 3.1, 3.7, 2.489432, 2.959136, 2.818225, 0.892438, 0.375763, 1.315171, 0.798497
1.330, , , , , 2.583372, 3.240958, 2.818225, 0.657586, 0.610615, 1.174260, 0.939408
1.335, 5.1, , 6.0, 6.2, 6.059183, 6.247064, 4.603100, 6.575857, 5.730390, 6.481916, 6.857680
{{< /chart >}}

{{< chart height="260" xlabel="t (s)" ylabel="max |u| outside the wall (cm/s)" colors="#8c564b,#edae49,#00798c,#7a7a7a,#30638e,#2ca02c,#d1495b,#111111,#e377c2,#17becf,#bcbd22" caption="Figure 3. Largest exported fluid speed outside the tube wall (3.73 < r < 4.3 cm, all z). Five new G64/R0 level-D runs are sampled every 0.01 s; historical curves retain their original samples. G64/R1/P1+Q1/BF uses the same level-D/FMA settings and 0.01 s output sampling, completing 1.335 s. G64/R2/P1+Q1/BF uses the same level-D/FMA settings and 0.01 s output sampling, completing 1.335 s." >}}
t, G11 (historical P1+Q1 BF), G7 (hex), G5 (tet conf.), 0.0.3 (tet), G64/R0/P1/BF, G64/R0/P1/NBF, G64/R0/P1+Q1/BF, G64/R0/Q2+P2/BF, G64/R0/P2/BF, G64/R1/P1+Q1/BF, G64/R2/P1+Q1/BF
0.000, 0.000, 0.000, 0.000, 0.000, 0.000000, 0.000000, 0.000000, 0.000000, 0.000000, 0.000000, 0.000000
0.010, , , , , 0.000000, 0.000000, 0.000000, 0.000000, 0.000000, 0.000000, 0.000000
0.020, , , , , 0.000000, 0.000000, 0.000000, 0.000000, 0.000000, 0.000000, 0.000000
0.030, , , , , 0.000172, 0.000172, 0.000173, 0.000114, 0.000097, 0.000111, 0.000135
0.040, 0.000, 0.000, 0.001, 0.001, 0.000587, 0.000587, 0.000495, 0.000261, 0.000272, 0.000306, 0.000276
0.050, , , , , 0.001663, 0.001663, 0.001338, 0.000484, 0.000533, 0.000621, 0.000409
0.060, , , , , 0.003131, 0.003131, 0.002429, 0.000714, 0.000757, 0.000909, 0.000521
0.070, , , , , 0.004871, 0.004871, 0.003673, 0.000879, 0.000871, 0.001069, 0.000609
0.080, 0.005, 0.005, 0.007, 0.007, 0.006863, 0.006863, 0.005148, 0.001609, 0.001862, 0.001949, 0.000615
0.090, , , , , 0.008882, 0.008882, 0.006894, 0.001825, 0.002188, 0.002359, 0.000566
0.100, , , , , 0.010294, 0.010294, 0.008275, 0.002031, 0.002300, 0.002676, 0.000829
0.110, , , , , 0.011034, 0.011034, 0.008952, 0.003689, 0.003898, 0.004680, 0.001278
0.120, 0.010, 0.010, 0.012, 0.012, 0.012249, 0.012249, 0.010082, 0.003617, 0.003502, 0.004418, 0.001542
0.130, , , , , 0.012908, 0.012908, 0.010958, 0.007495, 0.007047, 0.007309, 0.002433
0.140, , , , , 0.011138, 0.011138, 0.009219, 0.010865, 0.010404, 0.010865, 0.003562
0.150, , , , , 0.009199, 0.009199, 0.008246, 0.013511, 0.013730, 0.013293, 0.004045
0.160, 0.009, 0.009, 0.010, 0.010, 0.009836, 0.009836, 0.009308, 0.021849, 0.022182, 0.020761, 0.009357
0.170, , , , , 0.009151, 0.009151, 0.008918, 0.035164, 0.041158, 0.041986, 0.014302
0.180, , , , , 0.010993, 0.011000, 0.008136, 0.038801, 0.040539, 0.042269, 0.014751
0.190, , , , , 0.012915, 0.012805, 0.009576, 0.027207, 0.032374, 0.043524, 0.012197
0.200, 0.015, 0.022, 0.027, 0.027, 0.017806, 0.027168, 0.015079, 0.052317, 0.044721, 0.046616, 0.022073
0.210, , , , , 0.027397, 0.043433, 0.023026, 0.035296, 0.051159, 0.060702, 0.025683
0.220, , , , , 0.045103, 0.043850, 0.036452, 0.043610, 0.052333, 0.037883, 0.020230
0.230, , , , , 0.045188, 0.042187, 0.029143, 0.034702, 0.040019, 0.066661, 0.013408
0.240, 0.040, 0.043, 0.056, 0.055, 0.036486, 0.055398, 0.039948, 0.034959, 0.032859, 0.046182, 0.016649
0.250, , , , , 0.068910, 0.075381, 0.044617, 0.026189, 0.032074, 0.037397, 0.016815
0.260, , , , , 0.064234, 0.067264, 0.055791, 0.028503, 0.027446, 0.052792, 0.011347
0.270, , , , , 0.071983, 0.058019, 0.088515, 0.024775, 0.038662, 0.050288, 0.012132
0.280, 0.054, 0.071, 0.068, 0.106, 0.059076, 0.106117, 0.054127, 0.024002, 0.021321, 0.023900, 0.013039
0.290, , , , , 0.090149, 0.084290, 0.065519, 0.018499, 0.024385, 0.024572, 0.011918
0.300, , , , , 0.071941, 0.103379, 0.059555, 0.013788, 0.022866, 0.028746, 0.010828
0.310, , , , , 0.075232, 0.063167, 0.078246, 0.017481, 0.025997, 0.021858, 0.006788
0.320, 0.041, 0.059, 0.081, 0.041, 0.082365, 0.041308, 0.041053, 0.017438, 0.022269, 0.020747, 0.007389
0.330, , , , , 0.059752, 0.087379, 0.100667, 0.017019, 0.018998, 0.020610, 0.007165
0.340, , , , , 0.105928, 0.072481, 0.066412, 0.013936, 0.027431, 0.018143, 0.008654
0.350, , , , , 0.069552, 0.065467, 0.040812, 0.013648, 0.015758, 0.018168, 0.007912
0.360, 0.069, 0.057, 0.078, 0.098, 0.065578, 0.099129, 0.062609, 0.014557, 0.024961, 0.019336, 0.005613
0.370, , , , , 0.059226, 0.067942, 0.121188, 0.015561, 0.020676, 0.017322, 0.005962
0.380, , , , , 0.065152, 0.076246, 0.084287, 0.009954, 0.030948, 0.016000, 0.006749
0.390, , , , , 0.100280, 0.090703, 0.064655, 0.010550, 0.018465, 0.016254, 0.008327
0.400, 0.072, 0.094, 0.074, 0.068, 0.087002, 0.042476, 0.070263, 0.012279, 0.017351, 0.015104, 0.005107
0.410, , , , , 0.065366, 0.086976, 0.052165, 0.013552, 0.020168, 0.012504, 0.007260
0.420, , , , , 0.054565, 0.099103, 0.080714, 0.010694, 0.013840, 0.016293, 0.005758
0.430, , , , , 0.079072, 0.093177, 0.078545, 0.008860, 0.017367, 0.018466, 0.004571
0.440, 0.067, 0.076, 0.048, 0.062, 0.057986, 0.080279, 0.075869, 0.009687, 0.013554, 0.026809, 0.006000
0.450, , , , , 0.057287, 0.056603, 0.122524, 0.012788, 0.013297, 0.017827, 0.004957
0.460, , , , , 0.095974, 0.080396, 0.084962, 0.009401, 0.018030, 0.010243, 0.005165
0.470, , , , , 0.075657, 0.048606, 0.091085, 0.009421, 0.012727, 0.012917, 0.005420
0.480, 0.067, 0.124, 0.100, 0.097, 0.079209, 0.069373, 0.055901, 0.008346, 0.010259, 0.011461, 0.006358
0.490, , , , , 0.064138, 0.079833, 0.078449, 0.010611, 0.009816, 0.010405, 0.003985
0.500, , , , , 0.068693, 0.071698, 0.091704, 0.007235, 0.015712, 0.012571, 0.004868
0.510, , , , , 0.073090, 0.057111, 0.059970, 0.013586, 0.009523, 0.008403, 0.003011
0.520, 0.060, 0.068, 0.061, 0.052, 0.061026, 0.046499, 0.049206, 0.008893, 0.010573, 0.014606, 0.002900
0.530, , , , , 0.065618, 0.065989, 0.049276, 0.008512, 0.009993, 0.013439, 0.003003
0.540, , , , , 0.069084, 0.081536, 0.060271, 0.007894, 0.013132, 0.010148, 0.003251
0.550, , , , , 0.069207, 0.068714, 0.081768, 0.006886, 0.012267, 0.008505, 0.003982
0.560, 0.041, 0.049, 0.059, 0.046, 0.042405, 0.048174, 0.042152, 0.006665, 0.016437, 0.008812, 0.003305
0.570, , , , , 0.085448, 0.035049, 0.053673, 0.010106, 0.011028, 0.012796, 0.003166
0.580, , , , , 0.075317, 0.063920, 0.046904, 0.008059, 0.009870, 0.009382, 0.004120
0.590, , , , , 0.054627, 0.091007, 0.067577, 0.017125, 0.014205, 0.014209, 0.014148
0.600, 0.036, 0.044, 0.047, 0.057, 0.045024, 0.074477, 0.091945, 0.012254, 0.009631, 0.008670, 0.003958
0.610, , , , , 0.036727, 0.062948, 0.064479, 0.005569, 0.007204, 0.009387, 0.003819
0.620, , , , , 0.035362, 0.031599, 0.052212, 0.008892, 0.008078, 0.007753, 0.003490
0.630, , , , , 0.035873, 0.048270, 0.036690, 0.014395, 0.009078, 0.008790, 0.003026
0.640, 0.037, 0.039, 0.044, 0.035, 0.035717, 0.046889, 0.028281, 0.019716, 0.014950, 0.011308, 0.003577
0.650, , , , , 0.029416, 0.044681, 0.038215, 0.012226, 0.024442, 0.012403, 0.002626
0.660, , , , , 0.033743, 0.051691, 0.042203, 0.010466, 0.017033, 0.012631, 0.003735
0.670, , , , , 0.034545, 0.059381, 0.031566, 0.018022, 0.024113, 0.014535, 0.004649
0.680, 0.035, 0.029, 0.045, 0.040, 0.038759, 0.053594, 0.043142, 0.020479, 0.020809, 0.021370, 0.005559
0.690, , , , , 0.031876, 0.031835, 0.029178, 0.023340, 0.032244, 0.029336, 0.008225
0.700, , , , , 0.022452, 0.025460, 0.040126, 0.032819, 0.033290, 0.055491, 0.013539
0.710, , , , , 0.024876, 0.033668, 0.040198, 0.041820, 0.052618, 0.032736, 0.012109
0.720, 0.042, 0.032, 0.032, 0.036, 0.023356, 0.030087, 0.046440, 0.041233, 0.047776, 0.067279, 0.040410
0.730, , , , , 0.021141, 0.023030, 0.047663, 0.034434, 0.047690, 0.045117, 0.018988
0.740, , , , , 0.026871, 0.023927, 0.027113, 0.031791, 0.045444, 0.039775, 0.021386
0.750, , , , , 0.036062, 0.025578, 0.027577, 0.033810, 0.057041, 0.038934, 0.025019
0.760, 0.016, 0.019, 0.028, 0.029, 0.027852, 0.024141, 0.025382, 0.035994, 0.040581, 0.039688, 0.021394
0.770, , , , , 0.018174, 0.019186, 0.024943, 0.032147, 0.059001, 0.040761, 0.020636
0.780, , , , , 0.018812, 0.018032, 0.019908, 0.035344, 0.038081, 0.037510, 0.019233
0.790, , , , , 0.019126, 0.019237, 0.016037, 0.027530, 0.043290, 0.037429, 0.018868
0.800, 0.012, 0.016, 0.027, 0.020, 0.023373, 0.015252, 0.019874, 0.036369, 0.036254, 0.024063, 0.017533
0.810, , , , , 0.022047, 0.016315, 0.019756, 0.026371, 0.028770, 0.029133, 0.019239
0.820, , , , , 0.016866, 0.015183, 0.019915, 0.057888, 0.032522, 0.040609, 0.017090
0.830, , , , , 0.016296, 0.017269, 0.019277, 0.035583, 0.042413, 0.030493, 0.015252
0.840, 0.014, 0.022, 0.022, 0.015, 0.016632, 0.021690, 0.018348, 0.034954, 0.032833, 0.032496, 0.016003
0.850, , , , , 0.017784, 0.019058, 0.012533, 0.027798, 0.057356, 0.034034, 0.014982
0.860, , , , , 0.013114, 0.015729, 0.016843, 0.021764, 0.047581, 0.033727, 0.017599
0.870, , , , , 0.013886, 0.022110, 0.025461, 0.027959, 0.034248, 0.036065, 0.015584
0.880, 0.020, 0.230, 0.016, 0.012, 0.014061, 0.016805, 0.022922, 0.030429, 0.036056, 0.030627, 0.013798
0.890, , , , , 0.014270, 0.023764, 0.018877, 0.048610, 0.029417, 0.034488, 0.013554
0.900, , , , , 0.017403, 0.025739, 0.018181, 0.031363, 0.039186, 0.031548, 0.013087
0.910, , , , , 0.013373, 0.012399, 0.018599, 0.039636, 0.042418, 0.035992, 0.016433
0.920, 0.024, , 0.024, 0.013, 0.014090, 0.017529, 0.012716, 0.032552, 0.024733, 0.032879, 0.016935
0.930, , , , , 0.012140, 0.021576, 0.012442, 0.023614, 0.029556, 0.025143, 0.011398
0.940, , , , , 0.015913, 0.028974, 0.022948, 0.024553, 0.038052, 0.035140, 0.016458
0.950, , , , , 0.021718, 0.040090, 0.024311, 0.020663, 0.040782, 0.028215, 0.009607
0.960, 0.039, , 0.029, 0.043, 0.037087, 0.038968, 0.041784, 0.019300, 0.023846, 0.037353, 0.012472
0.970, , , , , 0.038492, 0.031779, 0.047726, 0.015753, 0.032406, 0.023267, 0.009311
0.980, , , , , 0.038447, 0.034388, 0.047180, 0.017779, 0.025790, 0.022810, 0.012359
0.990, , , , , 0.048957, 0.036405, 0.047680, 0.027311, 0.026168, 0.021118, 0.013509
1.000, 0.037, , 0.032, 0.071, 0.034067, 0.061344, 0.041533, 0.023567, 0.022402, 0.023509, 0.011278
1.010, , , , , 0.038776, 0.093757, 0.047461, 0.017698, 0.015776, 0.025379, 0.011099
1.020, , , , , 0.053125, 0.059449, 0.049681, 0.017400, 0.021038, 0.019506, 0.012954
1.030, , , , , 0.056458, 0.076046, 0.080491, 0.017595, 0.017080, 0.019116, 0.012426
1.040, 0.037, , 0.057, 0.063, 0.043675, 0.060258, 0.080756, 0.014256, 0.014551, 0.017646, 0.007666
1.050, , , , , 0.064055, 0.075998, 0.091417, 0.013012, 0.016992, 0.024131, 0.007951
1.060, , , , , 0.039887, 0.040002, 0.049050, 0.012414, 0.021374, 0.016990, 0.006146
1.070, , , , , 0.055667, 0.050657, 0.068898, 0.011588, 0.014512, 0.019737, 0.004858
1.080, 0.057, , 0.118, 0.061, 0.061671, 0.070385, 0.042968, 0.014329, 0.014508, 0.023334, 0.007135
1.090, , , , , 0.071259, 0.085449, 0.091025, 0.013476, 0.013406, 0.019130, 0.006431
1.100, , , , , 0.072951, 0.060959, 0.052634, 0.014831, 0.013134, 0.018100, 0.005295
1.110, , , , , 0.075828, 0.064068, 0.053134, 0.014138, 0.015629, 0.017935, 0.005596
1.120, 0.058, , 0.100, 0.067, 0.094555, 0.083305, 0.067162, 0.014267, 0.014039, 0.012492, 0.006589
1.130, , , , , 0.102760, 0.057839, 0.080673, 0.012571, 0.014645, 0.015353, 0.007056
1.140, , , , , 0.075746, 0.101610, 0.106141, 0.011589, 0.014438, 0.010778, 0.007011
1.150, , , , , 0.097698, 0.047244, 0.060245, 0.009482, 0.010544, 0.013721, 0.005216
1.160, 0.068, , 0.096, 0.053, 0.075601, 0.107877, 0.073474, 0.013690, 0.011583, 0.011230, 0.005129
1.170, , , , , 0.061072, 0.046787, 0.055727, 0.009972, 0.008918, 0.010138, 0.005829
1.180, , , , , 0.056120, 0.045474, 0.055820, 0.011243, 0.009696, 0.015424, 0.004285
1.190, , , , , 0.087270, 0.061793, 0.086154, 0.008708, 0.012206, 0.011672, 0.003564
1.200, 0.074, , 0.069, 0.087, 0.070622, 0.048227, 0.042345, 0.010348, 0.012797, 0.009639, 0.003851
1.210, , , , , 0.060198, 0.086586, 0.054633, 0.010042, 0.007759, 0.011912, 0.003642
1.220, , , , , 0.044312, 0.088355, 0.090802, 0.007555, 0.007903, 0.013884, 0.004206
1.230, , , , , 0.054016, 0.044359, 0.061508, 0.008903, 0.008266, 0.017356, 0.003422
1.240, 0.055, , 0.074, 0.076, 0.073708, 0.043204, 0.072087, 0.007965, 0.010426, 0.009752, 0.002987
1.250, , , , , 0.061781, 0.052583, 0.059443, 0.008497, 0.008221, 0.011630, 0.003172
1.260, , , , , 0.053114, 0.037487, 0.054597, 0.006918, 0.007112, 0.008568, 0.003805
1.270, , , , , 0.070947, 0.060892, 0.070460, 0.005674, 0.007383, 0.008709, 0.003741
1.280, 0.050, , 0.040, 0.058, 0.064116, 0.056993, 0.044348, 0.006374, 0.008727, 0.007029, 0.002650
1.290, , , , , 0.066674, 0.066889, 0.058018, 0.006327, 0.008528, 0.007386, 0.002688
1.300, , , , , 0.050445, 0.029137, 0.054844, 0.004582, 0.006464, 0.008086, 0.003469
1.310, , , , , 0.060053, 0.049609, 0.056824, 0.005864, 0.008234, 0.006803, 0.003069
1.320, 0.034, , 0.052, 0.042, 0.058366, 0.049533, 0.043337, 0.008108, 0.006623, 0.006329, 0.003379
1.330, , , , , 0.087735, 0.035594, 0.047036, 0.007073, 0.005836, 0.005881, 0.003420
1.335, 0.044, , 0.045, 0.057, 0.066570, 0.030804, 0.061783, 0.006188, 0.006826, 0.007552, 0.003687
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
