# Interpreting the G128 Q and vorticity movies (2026-10-19)

Primary: completed G128/R2, modified stress, solid-nu=0, dt=2.5e-6, Lz=16.09938. Assessment uses saved fields, not new simulations.

## Plausible versus suspicious appearance

The early jet-edge opposite-sign y-vorticity and a downstream advected structure persisting into the next filling pulse are qualitatively plausible. Appearance alone does not establish correct vortex dynamics. Small disconnected Q structures can depend on threshold and derivative reconstruction. Later fine filaments and mottled vorticity are not established physical turbulence.

Flat upper ends of Q surfaces are explicit clipping at z=14 cm. The plotted spatial window is r<3.5, 2<z<14 cm. These artificial cuts must not be interpreted as physical termination of a vortex. Tube and housing disc are hidden. Wall vorticity can reflect real shear; the roughly cylindrical extent is not by itself proof of a nonphysical flow. Measured Q-above-threshold voxel fractions in the outer lumen annulus 3.2<r<3.5 are not dominant: about 10% at 0.90 s, versus 16.4% of the ROI occupied by that annulus.

## Stronger quantitative concerns

The two completed modified-stress G128 cases at dt=2.5e-6 and 5e-6 match material, solid viscosity, mesh, domain, forcing and kernel; output/checkpoint cadence differs in step count but matches physical times. Compare saved fields in r<3.5, 2<z<14 cm, with the smaller-step field as the L2 normalization:

| Time (s) | Relative velocity L2 difference | Relative signed omega_y L2 difference | Q-above-threshold voxel IoU |
|---|---:|---:|---:|
| 0.08 | 0.0206% | 0.0769% | 0.9988 |
| 0.16 | 17.6987% | 63.5926% | 0.4711 |
| 0.64 | 26.7317% | 69.2381% | 0.2761 |
| 0.90 | 45.4077% | 102.4355% | 0.1846 |

Exact values are in mv-vortex-visual-audit.json. Closely matching bulk flow curves do not establish converged instantaneous velocity gradients or topology. Sensitive unsteady flows can decorrelate, so this comparison alone does not prove all structures are spurious; it does establish that a time-step-converged instantaneous vortex interpretation has not been demonstrated. Statistical/spatial convergence would need separate evidence.

Full-mesh reconstruction locates the most extreme solid volume changes in active marginal chordae, marker 200, original parent element 2096. At 1.10 s, child cells 134171 and 134163 have J=0.118995 and 9.931819, respectively; at 1.27 s, child 134170 reaches J=10.734314. Reference centres are around (4.78,5.25,6.18) cm, well inside the passive-rim cutoff. They have positive Jacobians but extreme compression/expansion incompatible with the intended incompressible-solid behaviour. They are not simply distorted passive tracer cells. These errors can affect leaflet loading and the fluid forcing; their quantitative impact on each vortex is not established.

The prior matched-mesh diagnosis also found a substantial inlet transient even in this completed R2 run: about 659 cm/s near the inlet at 0.92 s before recovery. Completing the cycle is not evidence of physical validity. Its downstream influence is possible, not yet causally isolated.

## Postprocessing checks and limits

VTK x-fastest storage, tube centre (4.3,4.3), y=4.3 slice and physical x/y/z gradient axes are correct. Analytic rigid rotation and pure strain checks pass. The movies use point velocities averaged from MAC data, followed by centred finite differences. This is not the solver's native staggered derivative operator. Reconstructed divergence is roughly 10–15% of rms vorticity in the sampled central region; this **must not** be reported as the MAC pressure-solver residual. Differentiating averaged velocities and finite resolution can alter small structures. Gradient-based Q and lambda2 deserve a native-MAC derivative cross-check before publication.

The G64/G128 movies additionally differ in stress, solid viscosity, dt and domain length, so visual differences between them are not a controlled grid-convergence result.

## Recommended interpretation

Use these as exploratory diagnostic visualisations. Do not yet describe the late filaments as resolved physiological turbulence or validated coherent vortex structures. Priority remains inlet/outlet boundary coupling and active chordal volume errors; then assess native-grid derivatives, contour-level sensitivity, temporal and spatial/statistical convergence. No new solver experiments were launched for this audit.
