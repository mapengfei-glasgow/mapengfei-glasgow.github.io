---
title: "Mitral-valve simulation results and limitations: G128/R2 audit"
description: "Measured timestep sensitivity, local solid deformation, MFAC and inlet-boundary failure diagnosis."
date: 2026-10-19
layout: protected-paper
academic: true
comments: false
searchHidden: true
build:
  list: never
tags: ["GPU", "FSI"]
url: /posts/mv-results-audit/
area: "research"
readingRoute: "mitral-valve"
areas: ["Cardiac Simulation"]
noteType: "Results"
projects: ["Mitral Valve"]
---

This update brings together the retained simulation results and postprocessing audits available on 19 October 2026. No new solver experiment was launched for this update. See the [working paper]({{< relref "mv-paper.md" >}}), [mesh note]({{< relref "mv-meshes.md" >}}) and [figure gallery]({{< relref "mv-figures.md" >}}).

## What completed, and what failed

| Case | Outcome | Interpretation |
|---|---|---|
| G128/R2, CBS43, modified stress, solid-nu=0, dt=2.5e-6 s | Completed to 1.335 s; source of the primary G128 figures | Completion establishes operational robustness for this run, not physical validation |
| Matched G128/R2, dt=5e-6 s | Also completed; saved fields compared at matched physical times | Bulk-flow agreement does not establish instantaneous vortex convergence |
| G128, R3 tube/disc + unchanged R2 valve, otherwise matched to dt=2.5e-6 s | Last valid output 0.88 s; NaNs detected at 0.89 s | Finer initial solid spacing alone did not prevent instability |

The completed zero-solid-viscosity case shows that added solid viscosity was not required for completion under those settings. It does not establish that viscosity has no effect on dynamics. The results support continued use of the modified-stress/CBS43 configuration as a working baseline; they do not identify a universally optimal kernel, stress projection, volumetric term or timestep. Those factors require controlled comparisons, and their individual effects should not be inferred from cases changing several settings together.

## Local deformation remains a major limitation

Reconstruction from saved G128/R2 states finds extreme volume changes in **active marginal chordae**, marker 200, original element 2096. At 1.10 s, neighboring children have J=0.118995 and 9.931819; at 1.27 s, another child reaches J=10.734314. Their reference centers are around (4.78,5.25,6.18) cm, inside the active region. These are positive Jacobians but severe departures from the intended nearly incompressible behavior; they cannot be dismissed as passive exterior tracer cells.

Consequently, the completed run is a diagnostic baseline rather than a validated final physiological solution. The effect of these errors on individual vortex structures has not been isolated. [Active-solid audit data](/data/mv-audit-20261019/mv-vortex-active-solid-extremes.json).

## Why the finer tube/disc run failed

Both cases begin with the tube end only 0.04969 cm from the inlet plane, or **0.593 axial fluid cells** at G128. In the refined case, the first saved inlet-wall crossing occurs at 0.59 s; by 0.80 s, 152 selected wall nodes lie outside the domain, with minimum z=-0.12077 cm. At 0.88 s, inlet-wall maximum I1 is 34.04, compared with 3.285 in the R2 reference.

| Time (s) | Refined tube/disc inlet peak speed (cm/s) | R2 reference (cm/s) |
|---|---:|---:|
| 0.84 | 211.64 | 93.84 |
| 0.86 | 362.27 | 127.32 |
| 0.87 | 522.82 | 153.93 |
| 0.88 | 1044.83 | 192.06 |

These observations point to inlet-end fluid/solid feedback and boundary-adjacent IB treatment as priorities. They do not identify the exact first NaN-producing step or prove a mathematical singularity. The last valid saved state has no nonpositive solid quadrature Jacobians, and its constitutive exponential arguments are far below floating-point overflow. The completed reference also has a substantial inlet transient, approximately 659 cm/s at 0.92 s, before recovery.

Shortening the background domain further is not supported as a remedy. Consistent end-ring constraints and boundary-compatible coupling are proposed next controls, not implemented or tested fixes. Increasing explicit tether stiffness can also tighten the timestep restriction. [Detailed diagnosis](/data/mv-audit-20261019/mv-inlet-outlet-instability.md).

## Where MFAC is large

Here MFAC is Euclidean cell-edge length divided by dx=dy=0.0671875 cm; dz=0.0838509375 cm is larger. These conservative reference ratios count edge occurrences per cell, not unique graph edges.

| Region | Median | Maximum |
|---|---:|---:|
| Tube | 0.813 | 0.857 |
| Housing disc | 0.638 | 1.577 |
| AML | 0.352 | 0.812 |
| PML | 0.335 | 0.848 |
| Annulus | 0.372 | 0.723 |
| Basal chordae | 0.171 | 0.699 |
| Marginal chordae | 0.197 | 0.596 |
| Papillary caps | 0.149 | 0.859 |

In active housing cells, 2.52% of edge occurrences exceed one. The worst reference edge is near (5.184,1.151,4.885) cm, original element 14119. Dynamic spacing also matters: parent 2096's maximum ratio increases from 0.370 initially to 1.185 at 1.10 s. Whether coarse coupling initiates the deformation or follows it remains unresolved.

The finer tube/disc test reduced median ratios to 0.406/0.320 but failed. A benchmark range such as 0.5–0.7 is not a universal stability threshold. [MFAC audit](/data/mv-audit-20261019/mv-local-mfac-audit.json).

## Interpreting Q and vorticity

The early jet-edge vorticity pattern and downstream advection are qualitatively plausible. Late fine filaments are not established resolved physiological turbulence. The two matched G128 timestep cases differ substantially in instantaneous gradient fields:

| Time (s) | Relative velocity L2 difference | Relative signed omega-y L2 difference | Q-threshold voxel intersection/union |
|---|---:|---:|---:|
| 0.08 | 0.0206% | 0.0769% | 0.9988 |
| 0.16 | 17.6987% | 63.5926% | 0.4711 |
| 0.64 | 26.7317% | 69.2381% | 0.2761 |
| 0.90 | 45.4077% | 102.4355% | 0.1846 |

L2 differences use the smaller-step field as denominator, in r<3.5 cm and 2<z<14 cm. Unsteady flows can decorrelate, so this is not proof that every structure is spurious. It does show that timestep-converged instantaneous vortex topology has not been demonstrated.

The movies use averaged MAC velocities and centered finite differences, not native staggered derivatives. Reconstructed divergence is about 10–15% of rms vorticity in the sampled central region; this is **not the pressure-solver residual**. Flat Q-surface ends at z=14 cm are plotting clips. G64/G128 movies also differ in stress, solid viscosity, dt and domain length, so they are not a controlled spatial-convergence comparison. [Full visualization audit](/data/mv-audit-20261019/mv-vortex-interpretation-20261019.md) · [Numerical data](/data/mv-audit-20261019/mv-vortex-visual-audit.json).

## Mesh quality and priorities

Reference R2 contains 10 hexahedra with VTK scaled Jacobian below 0.1; the minimum is 0.0404 in marginal chordae, marker 200. Most hexes are good by this measure (median 0.9995). The R2 tetrahedral subset has minimum sqrt(2)|det(H)|/lmax³=0.0509, with its worst cell in housing marker 42. This tetrahedral metric equals one for a regular tetrahedron and differs from the hex metric. The edge-balanced tet candidate has minimum quality 0.00157 by the same tet formula: uniform edge sizes do not guarantee good shapes.

Refinement inherits per-parent fiber/sheet fields and does not reconstruct finer anatomical directions. Independent components may overlap; coordinate coincidence must not trigger automatic welding. Uniform subdivision alone is not a quality repair. Local reconstruction or component-wise remeshing must preserve thin geometry, attachments and material fields and be checked for boundary displacement and volume change. The cap remeshing pilots have not repaired the complete R2 assembly.

Priorities supported by the present evidence are inlet/outlet coupling, active chordal volume errors, and targeted mesh-quality improvement; then native-grid derivative checks and controlled temporal/spatial convergence. These are follow-up recommendations, not newly completed simulations.

[Hex quality data](/data/mv-audit-20261019/HEX_QUALITY_AUDIT.json) · [Tet quality data](/data/mv-audit-20261019/TET_QUALITY_AUDIT.json).
