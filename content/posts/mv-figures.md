---
title: "Mitral-valve manuscript figures: G128 flow and vortex diagnostics"
description: "Exploratory manuscript figures, numerical provenance, and full-cycle animations."
date: 2026-10-19
layout: protected-paper
academic: true
comments: false
searchHidden: true
build:
  list: never
---

Companion to [the working paper]({{< relref "mv-paper.md" >}}).

**These figures are exploratory.** The main G128/R2 modified-stress case completed, but has severe local deformation (reported J range 0.119–10.734) and inlet transients. Neither completion nor these visualisations establishes mesh convergence, validated vortex topology, or agreement with IBAMR. F1 retains the substantial G64/G128 flow-rate difference.

[Download all figures, movies, data and captions (ZIP)](/data/mv-figures-20261019.zip) · [Detailed provenance and deviations](/images/mv/README.md) · [Run inventory](/images/mv/RUN_INVENTORY.json)

The field figures and movies use `G128_R2_cbs43_mod_dt2p5e-6_solidnu0`: CBS43, modified invariants, zero added solid viscosity, dt=2.5e-6 s, Lz=16.09938 cm. Four instants: 0.08, 0.16, 0.64 and 0.90 s. The tube and housing disc are hidden in 3D views. Camera, contour levels and colour scales are held fixed. Exact settings are in [FIELD_SETTINGS.json](/images/mv/FIELD_SETTINGS.json).

## F1: Lumen flow rate

![F1: fig_mv_flowrate](/images/mv/fig_mv_flowrate.png)

Lumen flow rate through the plane nearest z=12 cm. Seven G64 configurations, the 0.0.3 reference and three completed G128/R2 cases are shown. Actual planes are recorded per run in RUN_INVENTORY.json. The dashed IBAMR curve contains the available working-paper samples only (through 0.64 s); it is not extrapolated. G128 changes in stress/solid viscosity/domain length preclude interpretation as an isolated grid-convergence study.

[PDF](/images/mv/fig_mv_flowrate.pdf) · [Full-resolution PNG](/images/mv/fig_mv_flowrate.png)

## F2: Outlet backflow and exterior speed

![F2: fig_mv_backflow](/images/mv/fig_mv_backflow.png)

(a) Percentage of lumen points with negative axial velocity on the penultimate exported z plane. (b) Maximum speed over 3.73<r<4.3 cm and all z. Radius is measured about (4.3,4.3). G64 and G128 use their own actual outlet-adjacent planes, listed in the inventory. All 11 retained completed cases are shown.

[PDF](/images/mv/fig_mv_backflow.pdf) · [Full-resolution PNG](/images/mv/fig_mv_backflow.png)

## F3: Minimum local volume ratio

![F3: fig_mv_jmin](/images/mv/fig_mv_jmin.png)

Minimum local J from solid_stats.csv for G64 P2/R1/R2 and the completed G128/R2 cases. The minimum includes all reported cells, including passive-rim cells, and is sampled at exported times; it is not total solid-volume error. The G64/R2 minimum near 0.89 s is annotated.

[PDF](/images/mv/fig_mv_jmin.pdf) · [Full-resolution PNG](/images/mv/fig_mv_jmin.png)

## F4: Leaflet displacement proxies

![F4: fig_mv_tipdisp](/images/mv/fig_mv_tipdisp.png)

Displacement components of two deterministic leaflet-node proxies in the primary G128 run. For AML and PML separately, select the leaflet node with largest absolute axial displacement between t=0 and 0.64 s, then track that same node at every frame. This is not an independently identified anatomical free-edge tip. Candidate IDs and reference positions are in TIP_NODES.json; no trajectory smoothing or favourable-node selection was applied.

[PDF](/images/mv/fig_mv_tipdisp.pdf) · [Full-resolution PNG](/images/mv/fig_mv_tipdisp.png)

## F5: Q-criterion vortex surfaces

![F5: fig_mv_qcriterion](/images/mv/fig_mv_qcriterion.png)

Q-criterion iso-surfaces at Q=3956.88 s^-2 for t=0.08,0.16,0.64,0.90 s. The fixed level is 10% of the largest positive-Q 90th percentile across these instants in r<3.5 cm, 2<z<14 cm. Surfaces are clipped to that window and coloured by speed, 0–180 cm/s (values above the limit saturate). Camera and scales are fixed. Leaflets/chordae/caps/annulus are gray; tube and housing disc are omitted. Primary G128/R2 modified-stress run; exploratory numerical fields, not validated vortex topology.

[PDF](/images/mv/fig_mv_qcriterion.pdf) · [Full-resolution PNG](/images/mv/fig_mv_qcriterion.png)

## F6: Centre-plane vorticity

![F6: fig_mv_vorticity](/images/mv/fig_mv_vorticity.png)

Signed y-vorticity on the centre plane y=4.3 cm at the same four instants, with fixed limits ±620 s^-1. The displayed window is 2<z<14 cm. Derivatives are second-order finite differences of exported point velocities; x-fastest VTK ordering is respected.

[PDF](/images/mv/fig_mv_vorticity.pdf) · [Full-resolution PNG](/images/mv/fig_mv_vorticity.png)

## F7: Lambda-two vortex surfaces

![F7: fig_mv_lambda2](/images/mv/fig_mv_lambda2.png)

Alternative vortex criterion: lambda2=-3580.22 s^-2 iso-surfaces, where lambda2 is the middle eigenvalue of S^2+Omega^2. Same times, spatial window, camera and speed scale as F5. Fixed negative level based on the negative-lambda2 magnitude distribution, as recorded in FIELD_SETTINGS.json.

[PDF](/images/mv/fig_mv_lambda2.pdf) · [Full-resolution PNG](/images/mv/fig_mv_lambda2.png)

## F8: Instantaneous streamlines

![F8: fig_mv_streamlines](/images/mv/fig_mv_streamlines.png)

Instantaneous forward streamlines at t=0.08 and 0.64 s, seeded on a fixed disc at z=7.5 cm, radius 0.15–3.2 cm (6 radial rings, 48 angles). Fourth/fifth-order adaptive Runge–Kutta integration, maximum propagation 30 cm, 3000 steps; initial step 0.05 in VTK default cell-length units. These are instantaneous streamlines, not particle pathlines. Camera/speed scale match F5.

[PDF](/images/mv/fig_mv_streamlines.pdf) · [Full-resolution PNG](/images/mv/fig_mv_streamlines.png)

## F9: Exterior damping

![F9: fig_mv_gap](/images/mv/fig_mv_gap.png)

Exterior damping at t=0.30 s. (a) Logarithmic speed map on y=4.3 cm, showing the positive-radial half of the domain. (b) Azimuthal mean speed at z=11.990684 cm. Measured exterior max=0.00215436 cm/s; signed and absolute gap fluxes for 3.8<r<4.3 cm are 0.000131052 and 0.000216216 cm^3/s. These bounds are measured at this time, not imposed or asserted for all times.

[PDF](/images/mv/fig_mv_gap.pdf) · [Full-resolution PNG](/images/mv/fig_mv_gap.png)

## F10: Enstrophy and dissipation

![F10: fig_mv_energy](/images/mv/fig_mv_energy.png)

Integrated enstrophy (one half of vorticity magnitude squared) and viscous dissipation rate (2 mu S:S), mu=0.04 P. Full Eulerian-box integrals and a lumen window (r<3.5 cm, 2<z<14 cm) are shown, using nodal trapezoidal weights. Full-box values include immersed-solid regions; they are not fluid-only integrals. Boundary transients affect full-box quantities. Exterior contributions are saved separately in energy.csv; no negligible-contribution claim is assumed.

[PDF](/images/mv/fig_mv_energy.pdf) · [Full-resolution PNG](/images/mv/fig_mv_energy.png)

## F11: Exploratory velocity spectrum

![F11: fig_mv_spectra](/images/mv/fig_mv_spectra.png)

Exploratory summed-component velocity PSD, averaged over fixed probes on z≈8 cm with a 0.5 cm transverse grid inside r<3.5 cm. Welch estimate: 64-sample Hann windows, 50% overlap, mean removal, sampling 100 Hz, Nyquist 50 Hz; final irregular 1.335 s sample omitted. The record is a single nonstationary cycle and does not establish a turbulence spectrum or inertial range.

[PDF](/images/mv/fig_mv_spectra.pdf) · [Full-resolution PNG](/images/mv/fig_mv_spectra.png)

## Supplementary movies

All 135 exported frames are included, with time stamps and fixed scales. MP4 files use H.264/yuv420p at 1280×720; GIFs are smaller previews. The full cycle lasts 1.335 s of simulation time; playback is slowed.

### M1: Q-criterion

![Q-criterion animation](/images/mv/movie_q_iso.gif)

[Download MP4](/images/mv/movie_q_iso.mp4) · [GIF](/images/mv/movie_q_iso.gif)

### M2: Centre-plane vorticity

![Vorticity animation](/images/mv/movie_vorticity.gif)

[Download MP4](/images/mv/movie_vorticity.mp4) · [GIF](/images/mv/movie_vorticity.gif)

## Open questions and limits

The IBAMR comparison uses the working-paper chart samples through 0.64 s only; no full-cycle reference is fabricated or extrapolated, and no additional simulation was launched for this figure set. Fibre/sheet values in the P1 and mixed meshes agree with the original Sarah map to numerical precision, with 14 ambiguous parent assignments retained from the original P1 mapping. [Fibre audit](/images/mv/FIBRE_PROVENANCE.json).

The leaflet trajectories are deterministic node proxies rather than independently identified anatomical tips. Full-box energy integrals include immersed-solid regions; the separate lumen-window integrals are shown explicitly. The single-cycle spectrum is nonstationary and limited to a 50 Hz Nyquist frequency.
