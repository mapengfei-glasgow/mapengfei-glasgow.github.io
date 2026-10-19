# Local MFAC in the G128/R2 movie source

Run: G128_R2_cbs43_mod_dt2p5e-6_solidnu0. Fluid spacing: dx=dy=0.0671875 cm, dz=0.0838509375 cm. Statistics below use Euclidean cell-edge length/dx, the conservative smaller-spacing convention used in the earlier regional tables. This is not a direction-specific MFAC; axial edges should also be assessed against dz. Exact anisotropic normalized edge lengths are recorded for the worst active edges in mv-local-mfac-audit.json.

| Reference region | Median | Maximum |
|---|---:|---:|
| Tube | 0.813 | 0.857 |
| Housing disc | 0.638 | 1.577 |
| AML | 0.352 | 0.812 |
| PML | 0.335 | 0.848 |
| Annulus | 0.372 | 0.723 |
| Basal chordae | 0.171 | 0.699 |
| Marginal chordae | 0.197 | 0.596 |
| Papillary caps | 0.149 | 0.859 |

The housing disc has active cells with edge MFAC>1 (2.52% of active cell-edge occurrences). Its worst reference edge is near (5.184,1.151,4.885) cm, original element 14119, marker42; anisotropic metric1.570. This is not solely a passive-rim issue. Tube ratios are also comparatively coarse for the CBS benchmark regime; the often-discussed 0.5–0.7 range is a benchmark observation, not a universal stability/leakage threshold. Small cap/chordal medians do not exclude isolated long edges or high aspect ratios.

Dynamic MFAC matters. The actively distorted marginal-chordal parent2096 has initial median/max0.157/0.370, then0.204/1.185 at1.10s and0.206/1.183 at1.27s. This is the same parent with extreme J. Hence local deformed spacing becomes coarse even though the initial mesh is fine. This increase does not establish whether coarse coupling caused deformation or deformation caused coarse coupling.

The R3-tube/disc + R2-valve test reduced tube/disc median ratios to0.406/0.320 but failed at0.89s with the inlet-end/boundary precursor previously diagnosed. That is evidence against treating initial MFAC reduction alone as a sufficient remedy. Boundary treatment and active solid-deformation errors remain priorities; indiscriminate refinement is not a demonstrated fix.

Script: scripts/diagnostics/audit_mv_local_mfac.py. Edge statistics count occurrences per cell, not unique graph edges, consistently with the earlier tables. Active/passive classification uses distinct-node reference centroids and the r=3.73 cm cutoff. No solver experiments were launched.
