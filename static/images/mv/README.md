# Mitral-valve manuscript figure delivery

Generated 2026-10-19.

**Status: exploratory figure set, not a validation certificate.** The primary G128 run completed but has severe local deformation (reported J range 0.118995–10.7343) and an inlet transient. Completion does not establish mesh convergence, correct leaflet dynamics or converged vortex topology.

Primary run for F4–F11 and movies: `runs/glamv_g128_modstress_20261017/G128_R2_cbs43_mod_dt2p5e-6_solidnu0`. G128/R2 mixed Q1+P1, modified invariants, solid-nu=0, dt=2.5e-6 s, T=1.335 s, Lz=16.09938 cm; shortened domain, CBS43 and outlet backflow treatment.

## Deliverables and captions

### F1: fig_mv_flowrate.pdf / .png

Lumen flow rate through the plane nearest z=12 cm. Seven G64 configurations, the 0.0.3 reference and three completed G128/R2 cases are shown. Actual planes are recorded per run in RUN_INVENTORY.json. The dashed IBAMR curve contains the available working-paper samples only (through 0.64 s); it is not extrapolated. G128 changes in stress/solid viscosity/domain length preclude interpretation as an isolated grid-convergence study.

### F2: fig_mv_backflow.pdf / .png

(a) Percentage of lumen points with negative axial velocity on the penultimate exported z plane. (b) Maximum speed over 3.73<r<4.3 cm and all z. Radius is measured about (4.3,4.3). G64 and G128 use their own actual outlet-adjacent planes, listed in the inventory. All 11 retained completed cases are shown.

### F3: fig_mv_jmin.pdf / .png

Minimum local J from solid_stats.csv for G64 P2/R1/R2 and the completed G128/R2 cases. The minimum includes all reported cells, including passive-rim cells, and is sampled at exported times; it is not total solid-volume error. The G64/R2 minimum near 0.89 s is annotated.

### F4: fig_mv_tipdisp.pdf / .png

Displacement components of two deterministic leaflet-node proxies in the primary G128 run. For AML and PML separately, select the leaflet node with largest absolute axial displacement between t=0 and 0.64 s, then track that same node at every frame. This is not an independently identified anatomical free-edge tip. Candidate IDs and reference positions are in TIP_NODES.json; no trajectory smoothing or favourable-node selection was applied.

### F5: fig_mv_qcriterion.pdf / .png

Q-criterion iso-surfaces at Q=3956.88 s^-2 for t=0.08,0.16,0.64,0.90 s. The fixed level is 10% of the largest positive-Q 90th percentile across these instants in r<3.5 cm, 2<z<14 cm. Surfaces are clipped to that window and coloured by speed, 0–180 cm/s (values above the limit saturate). Camera and scales are fixed. Leaflets/chordae/caps/annulus are gray; tube and housing disc are omitted. Primary G128/R2 modified-stress run; exploratory numerical fields, not validated vortex topology.

### F6: fig_mv_vorticity.pdf / .png

Signed y-vorticity on the centre plane y=4.3 cm at the same four instants, with fixed limits ±620 s^-1. The displayed window is 2<z<14 cm. Derivatives are second-order finite differences of exported point velocities; x-fastest VTK ordering is respected.

### F7: fig_mv_lambda2.pdf / .png

Alternative vortex criterion: lambda2=-3580.22 s^-2 iso-surfaces, where lambda2 is the middle eigenvalue of S^2+Omega^2. Same times, spatial window, camera and speed scale as F5. Fixed negative level based on the negative-lambda2 magnitude distribution, as recorded in FIELD_SETTINGS.json.

### F8: fig_mv_streamlines.pdf / .png

Instantaneous forward streamlines at t=0.08 and 0.64 s, seeded on a fixed disc at z=7.5 cm, radius 0.15–3.2 cm (6 radial rings, 48 angles). Fourth/fifth-order adaptive Runge–Kutta integration, maximum propagation 30 cm, 3000 steps; initial step 0.05 in VTK default cell-length units. These are instantaneous streamlines, not particle pathlines. Camera/speed scale match F5.

### F9: fig_mv_gap.pdf / .png

Exterior damping at t=0.30 s. (a) Logarithmic speed map on y=4.3 cm, showing the positive-radial half of the domain. (b) Azimuthal mean speed at z=11.990684 cm. Measured exterior max=0.00215436 cm/s; signed and absolute gap fluxes for 3.8<r<4.3 cm are 0.000131052 and 0.000216216 cm^3/s. These bounds are measured at this time, not imposed or asserted for all times.

### F10: fig_mv_energy.pdf / .png

Integrated enstrophy (one half of vorticity magnitude squared) and viscous dissipation rate (2 mu S:S), mu=0.04 P. Full Eulerian-box integrals and a lumen window (r<3.5 cm, 2<z<14 cm) are shown, using nodal trapezoidal weights. Full-box values include immersed-solid regions; they are not fluid-only integrals. Boundary transients affect full-box quantities. Exterior contributions are saved separately in energy.csv; no negligible-contribution claim is assumed.

### F11: fig_mv_spectra.pdf / .png

Exploratory summed-component velocity PSD, averaged over fixed probes on z≈8 cm with a 0.5 cm transverse grid inside r<3.5 cm. Welch estimate: 64-sample Hann windows, 50% overlap, mean removal, sampling 100 Hz, Nyquist 50 Hz; final irregular 1.335 s sample omitted. The record is a single nonstationary cycle and does not establish a turbulence spectrum or inertial range.

### M1/M2

`movie_q_iso.mp4` and `movie_vorticity.mp4`, plus GIF previews. All 135 exported frames, fixed thresholds/camera/colour scales and time stamps. 1280×720, H.264/yuv420p, 27 frames/s. The final source interval is 0.005 s; fixed movie frame rate therefore slightly stretches that interval. Both movies use the same primary run as F5/F6.

## Run mapping

| Label | Run directory | Frames | Last time (s) | Q plane / backflow plane (cm) |
|---|---|---:|---:|---|
| G64/R0/P1/BF | `runs/glamv_four_D_20261015/G64_R0_P1_BF` | 135 | 1.335 | 11.981250 / 16.031250 |
| G64/R0/P1/NBF | `runs/glamv_four_D_20261015/G64_R0_P1_NBF` | 135 | 1.335 | 11.981250 / 16.031250 |
| G64/R0/P1+Q1/BF | `runs/glamv_four_D_20261015/G64_R0_P1+Q1_BF` | 135 | 1.335 | 11.981250 / 16.031250 |
| G64/R0/Q2+P2/BF | `runs/glamv_four_D_20261015/G64_R0_Q2+P2_BF` | 135 | 1.335 | 11.981250 / 16.031250 |
| G64/R0/P2/BF | `runs/glamv_four_D_20261015/G64_R0_P2_BF` | 135 | 1.335 | 11.981250 / 16.031250 |
| G64/R1/P1+Q1/BF | `runs/glamv_four_D_20261015/G64_R1_P1+Q1_BF` | 135 | 1.335 | 11.981250 / 16.031250 |
| G64/R2/P1+Q1/BF | `runs/glamv_four_D_20261015/G64_R2_P1+Q1_BF` | 135 | 1.335 | 11.981250 / 16.031250 |
| 0.0.3 reference | `fdm-3d-v1-gpu/out_glamv003_every500` | 135 | 1.335 | 11.981250 / 16.031250 |
| G128/R2 original, nu_s=125, dt=2.5e-6 | `runs/glamv_four_D_20261015/G128_R2_P1+Q1_BF_Lz16p09938_dt2p5e-6` | 135 | 1.335 | 11.990684 / 16.015529 |
| G128/R2 modified, nu_s=0, dt=5e-6 | `runs/glamv_g128_modstress_20261017/G128_R2_cbs43_mod_dt5e-6_solidnu0` | 135 | 1.335 | 11.990684 / 16.015529 |
| G128/R2 modified, nu_s=0, dt=2.5e-6 | `runs/glamv_g128_modstress_20261017/G128_R2_cbs43_mod_dt2p5e-6_solidnu0` | 135 | 1.335 | 11.990684 / 16.015529 |

## Deviations and open questions

- No existing `arXiv-template` manuscript source was found on this machine. The requested `arXiv-template/images/mv/` was created as a staging directory; no LaTeX source or `% FIGURE` marker was edited.
- Native VTK/EGL offscreen rendering replaces PyVista, which is unavailable locally. The underlying VTK geometry, contouring and stream tracing are used directly. Matplotlib handles vector plots and slices. All 3D four-panel images are 2400 pixels wide; all time-series previews are 300 dpi. 3D PDFs embed raster renders, while time-series PDFs retain vector lines/text.
- The plan’s sample array reshaping, radius origin and y=0 slice would be wrong for these exports. Arrays are (z,y,x,component), centre is (4.3,4.3), and y-centre is 4.3 cm. Analytic rigid-rotation and pure-strain fields validate the derivative implementation.
- IBAMR: only the working-paper chart samples through 0.64 s were available, not a raw full-cycle CSV. The curve is explicitly labelled and never extrapolated. No IBAMR extension or other solver experiment was started, consistent with the instruction to avoid further experiments.
- Fibres/sheets: P1 tetrahedra and mixed R0/R1/R2 use normalized original Sarah per-parent-element directions; numerical comparison to the original map has max fibre discrepancy 2.23e-16 and zero sheet discrepancy. The original P1 mapping has 14 ambiguous parent assignments, resolved by its existing centroid rule; physical correctness of those ambiguous junctions is not newly established. See FIBRE_PROVENANCE.json.
- Failed runs deleted during requested cleanup are not reconstructed or plotted as complete simulations. The 11 retained completed cases are identified above.
- F4 uses reproducible node proxies, not interactive anatomical tip identification. F8 uses the fixed z=7.5 cm seed plane. F9 reports measured exterior quantities. F10 distinguishes full-box integrals from fluid-only quantities. F11 is sampling-limited and exploratory.
- G128 Q(0.12 s)≈602 cm³/s differs materially from G64 mixed≈489 and IBAMR≈374; this is visible in F1, not hidden by normalization. Stress, viscosity and domain differences confound a pure resolution comparison.

## Reproduction

Run `python3 scripts/mv_figures/series.py`, `python3 scripts/mv_figures/check_fibres.py`, then `python3 scripts/mv_figures/fields_figures.py` from the workspace. Set `MPLCONFIGDIR=/tmp/mv-mpl OPENBLAS_NUM_THREADS=1`. NumPy, Matplotlib, Pillow and VTK are required; ffmpeg path is recorded in the script. Raw simulation exports and original Sarah map files must be available. Derived caches and animation PNGs are under ignored `runs/mv_figures_20261019/`.
