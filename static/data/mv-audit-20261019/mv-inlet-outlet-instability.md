# Valve-scale G128 instability diagnosis — 2026-10-18

The strongest observed precursor is loss of control of the tube's inlet end, followed by a rapidly growing inlet-plane normal velocity. This is a spatial/temporal diagnosis from saved states, not proof of the precise floating-point operation that first generated NaN.

The failed case uses R3 tube/disc + R2 valve, G128, CBS43, modified invariants, solid-nu=0, dt=2.5e-6. The completed comparison uses R2 everywhere with the same numerical/material/boundary settings. Both start with the tube end at z=0.04969 cm; dz=0.0838509375 cm, so the end clearance is only 0.593 fluid cells. Tube median edge changes 0.05459 -> 0.02730 cm. The valve's mesh is unchanged.

## Observed sequence

- At t=0.01 s, inlet-wall deformation is identity (I1=3, J=1).
- At t=0.40 s, inlet-wall max I1 has grown to 5.43; at 0.60 s it is 9.75; at 0.80 s it is 33.44. Here I1=tr(F^T F), with reference value 3.
- The first *saved* inlet-wall boundary crossing is t=0.59 s (previous examined frame 0.58 s has none). 32 selected inlet-wall nodes have z<0, including 16 original R2 nodes and 16 newly introduced nodes. The worst node moves from z=0.04969 to -0.00250 cm.
- At 0.60 s there are 48 outside nodes; at 0.80 s, 152, with minimum z=-0.12077 cm. Node selection: reference z<0.3 cm and radius 3.45–3.76 cm about (4.3,4.3), isolating the inlet tube wall. The R2 comparison has no outside nodes in the same selection at the sampled times through 0.88 s.
- Inlet peak speed then grows sharply. These are the first four exported z planes (0–0.25155 cm):

| Time (s) | Refined tube/disc (cm/s) | R2 reference (cm/s) |
|---|---:|---:|
| 0.84 | 211.64 | 93.84 |
| 0.86 | 362.27 | 127.32 |
| 0.87 | 522.82 | 153.93 |
| 0.88 | 1044.83 | 192.06 |

The failed-case peaks lie on z=0, near (4.37–4.43,1.01,0), and are entirely normal velocity w; exported tangential components there are zero. The successful reference also shows an inlet transient (658.79 cm/s at 0.92 s), then recovers (61.27 cm/s at 0.95 s). Thus inlet amplification is not unique to refinement, but its timing/severity and wall response differ substantially.

At 0.88 s, the refined inlet wall has max I1=34.04 and J range 0.664–2.285; the reference inlet wall has I1=3.285 and J range 0.954–1.091. The refined max-I1 cell is tube marker 1, original element 3322, reference centre (1.76948,6.73674,0.06219) cm. Its reference radius is about 3.51 cm, so it is an active tube cell, not passive-rim tissue.

The last valid output is 0.88 s; NaNs are detected at the scheduled 0.89 s log/output. The first NaN-producing step within this interval is not recorded. Node 0 is only the first index found by the diagnostic scan, not an established source location.

## What this does and does not establish

At 0.88 s, a full solid scan finds no nonpositive quadrature-point Jacobians. The valve-only minimum J is 0.236 (marginal chordae, original element 2096), and its maximum I1 is 9.49. The largest active constitutive exponential argument is about 10.22, far below double-precision exponential overflow. The completed reference's argument is similar (10.85). Therefore the saved frames do not support a valve-material exponential overflow or a valve inversion as the observed precursor. Either could still occur later during the unsaved interval after the inlet disturbance grows.

The full-mesh minimum J=0.148 occurs in housing-disc marker 42, original element 11678, near z=4.779 cm, not at the inlet. The maximum J=3.205 in the last frame is in cap marker 1002. These deformation defects exist but are not evidence that either location initiated the final inlet blow-up.

The initial mesh passes positive reference Jacobian and geometry-preservation checks; added tube/disc refinement preserves each R2 parent volume to 8.9e-14 relative error. This rules out the earlier hex-to-tet conversion-volume issue for this run, but does not prove that the refined coupled operator has a sufficiently large stability margin.

## Mechanistic interpretation and next discriminating test

The likely mechanism is an inlet-end fluid/solid feedback instability: the tube end is held by a finite penalty tether rather than an exact displacement constraint; local deformation accumulates, some nodes cross the inlet plane, and the boundary-adjacent interpolation/spreading/pressure-feedback system develops a growing normal-velocity disturbance. The code zeroes coupling weights outside allocated grid bounds (`interp_gpu.h::stag_weights`), so markers crossing an open boundary do not retain an interior coupling stencil. This is a concrete boundary-treatment concern, not proof that truncation alone causes the failure: the exact roles of tether stiffness, solid/fluid coupling, pressure-hole treatment and boundary extension require an isolated test.

The short clearance (0.593 dz) is relevant; shortening the background domain further is not supported as a remedy here. Refining the valve itself is also not the first targeted remedy, since its mesh did not change.

The next useful controlled test is to keep the mesh/material/dt fixed and enforce a consistent inlet/outlet tube-end constraint (e.g. exact reference end-ring displacement) together with a boundary-compatible IB treatment. Compare minimum end-node z, local I1 and inlet speed. Increasing explicit tether strength indiscriminately can change the time-step restriction and should not be presented as a guaranteed fix. Reintroducing solid damping is a separate control, not a proven solution. A diagnostic restart from the 0.8 s checkpoint with checks every step would locate the first nonfinite field and tighten the causal diagnosis.

## Reproducibility

`audit_instability.py` reconstructs F from exported Xc and original mixed quadrature gradients; uses the **translated run reference coordinates** for boundary/radius classification; excludes zero-weight tet quadrature slots. Full result files:

- `INSTABILITY_AUDIT.json`: valve comparisons and full refined-mesh scan at 0.88 s.
- `INLET_WALL_AUDIT.json`: inlet tube-wall comparison, reference z<0.3 cm.
- `INLET_EARLY_AUDIT.json`: early inlet-wall development.
- `INLET_NODE_MOTION.json`, `FIRST_BOUNDARY_CROSSING.json`: node excursions.
- `REFERENCE_AFTER_FAILURE.json`: reference's recovering inlet transient.

Existing simulation data are unchanged. No additional simulation was launched for this diagnosis.

## Follow-up decision (2026-10-19)

The user agrees that inlet/outlet boundary treatment deserves priority and requests recording the diagnosis without further experiments. Boundary-condition transitions and boundary-adjacent IB stencils are suspected; a mathematical singularity has not been demonstrated. No end-constraint implementation or new test was retained. Proposed constraints and diagnostic restarts above are unexecuted suggestions.

Tracked audit entry point: `scripts/diagnostics/audit_mv_inlet.py` (requires the retained raw run snapshots). Compact observation tables are stored beside this note; large raw files remain ignored under `runs/`.
