---
title: "Learning left ventricular contraction and dilation"
description: "A geometry-aware graph emulator trained on finite-element simulations, with a curriculum from the PCA mean ventricle to a wider shape space."
date: 2026-10-16
lastmod: 2026-10-17
academic: true
ShowToc: true
TocOpen: false
comments: false
tags: ["Cardiac mechanics", "Graph neural networks", "PCA"]
---

The aim of this project is to emulate the contraction and dilation of the left ventricle (LV) across different ventricular shapes, material properties, and loading conditions. Finite-element simulations provide displacement trajectories; an augmented MeshGraphNet learns to advance the nodal displacement in time.

**Current phase — 17 October 2026:** all **1,000 mean-geometry simulations are complete**. The base model is training with all **760 training cases**, with its latest evaluation recorded at **49,000 of 120,000 iterations**. Expansion to a broader geometry space is the next stage.

[Source repository: lv-gls-bdf2-ho](https://github.com/mapengfei-glasgow/lv-gls-bdf2-ho)

## Current training state

*Snapshot recorded on 17 October 2026. This is a manual update from the training log, not a live dashboard.*

**Training loss is the primary measure of progress.** It is the mean squared error of the normalised, noise-corrected one-step displacement update. The latest evaluation-window average is **0.0351**. The overall trend is downward, with occasional increases between evaluations.

| Iteration | Training loss |
|---|---:|
| 10,000 | 0.1309 |
| 20,000 | 0.0859 |
| 30,000 | 0.0575 |
| 40,000 | 0.0450 |
| 49,000 | **0.0351** |

| Campaign item | State |
|---|---|
| Mean-geometry solver simulations | **1,000 / 1,000 complete** |
| Training cases admitted | **760 / 760** |
| Planned optimisation iterations | 120,000 |
| Latest recorded evaluation | **49,000 iterations** |
| Validation / test split | 120 / 120 cases |
| Fixed validation cases used during training | 10 |

Rollout error is a **secondary diagnostic**. The latest full-cycle displacement RMSE is **2.10 mm**, averaged over the ten fixed validation cases. The best recorded rollout RMSE is **1.24 mm at iteration 45,000**. Rollout error fluctuates more than training loss: recent evaluations range from 1.24 to 6.42 mm, so these are interim results rather than final accuracy estimates.

The loss uses running normalisation statistics and is dimensionless; it is not a displacement error in millimetres. The current `best.pt` checkpoint is selected by validation rollout RMSE, while training loss remains the primary indicator used to discuss learning progress.

## Geometry from PCA

The geometry model is extracted from the Dalton LV mesh family. It represents the raw corner coordinates as

$$
\mathbf X_{\mathrm{raw}}(\mathbf z)
= \overline{\mathbf X}_{\mathrm{raw}}
+ \sum_{i=1}^{40} z_i\,\sigma_i\,\boldsymbol\phi_i,
$$

where $\boldsymbol\phi_i$ are PCA modes, $\sigma_i$ are score standard deviations, and $z_i$ are standardised coefficients. Setting all coefficients to zero gives the mean ventricle used for the base model.

![PCA mean LV geometry and two examples with progressively wider coefficient variation.](/images/lv-emulator/pca-geometries.png)

*Reference geometries, not predicted deformations. The narrow example varies the first 16 coefficients within ±0.25 standard deviations; the wider example varies all 40 within ±1. Each has positive tetrahedral volumes.*

The mesh connectivity is fixed: **11,779 nodes and 59,940 tetrahedra**. Only coordinates change. A stored mapping recovers the tetrahedral node ordering and interpolates the additional centroid nodes. Boundary tags identify the base, endocardium, and epicardium. Rule-based fibres are regenerated for each shape using a Laplace transmural coordinate, with helix angles of +60° at the endocardium and −60° at the epicardium.

The repository bundles the PCA basis, topology, mappings, and generator in `geometry/`. Regeneration needs no separate geometry dataset download; generated meshes are kept outside version control.

```bash
# Mean geometry
python geometry/generate.py --out geometry/generated/mean

# Small variation about the mean
python geometry/generate.py --modes 16 --scale 0.25 --seed 42 \
    --out geometry/generated/narrow
```

## Why use a geometry curriculum?

Training over the full geometry range from the outset has been difficult. Earlier experiments converged more readily when the model first learned parameter-dependent motion on one fixed shape, then encountered progressively wider geometry variation.

The revised curriculum starts at the population mean:

| Stage | Geometry variation | Purpose |
|---|---|---|
| 1. Mean-geometry base | All PCA coefficients zero; many parameter samples | Learn the dependence of ventricular motion on materials and loads |
| 2. Narrow shape variation | Small coefficient offsets around the mean | Adapt the base model to nearby geometries |
| 3. Wider shape space | Expand coefficients to the target range | Learn motion across the intended geometry family |

The current base model starts from fresh weights. It does not inherit weights from the earlier geom_0000 experiment.

## Simulation data

The training targets come from the GLS P1/P1 velocity–pressure solver, using Holzapfel–Ogden passive mechanics, active fibre tension, prescribed endocardial pressure, and BE/BDF2 time stepping. Each cardiac cycle contains 200 time steps, with $\Delta t=T/200$.

Eight parameters vary: the material constants $a$, $b$, $a_f$, and $b_f$; active-tension amplitude; diastolic pressure; systolic pressure amplitude; and cycle length.

The mean-geometry campaign contains **1,000 completed parameter samples**, drawn from a scrambled Sobol design. The fixed split is **760 training, 120 validation, and 120 test cases**. Because geometry is fixed at this stage, these held-out cases assess generalisation across parameters.

## Incremental training

Training began with the completed simulations while data generation continued. Every 500 iterations, the trainer checks for new completed training cases; all 760 training cases have now been admitted. Before admission, each simulation is checked against the intended geometry, topology, material and loading parameters, time-step count, and finite displacement fields.

The model predicts a displacement update at each real mesh node:

$$
\Delta_n = \mathbf u_{n+1}-2\mathbf u_n+\mathbf u_{n-1}.
$$

An augmented graph adds virtual nodes and connections at multiple spatial scales. Inputs describe geometry, displacement-derived velocity, boundary tags, material parameters, and loads. The base recipe uses 128 latent features, ten message-passing steps, and position noise with corrected training targets.

Adding samples preserves model weights, optimizer state, running normalization statistics, and the learning-rate schedule. A fixed set of ten completed validation cases is used for checkpoint selection, keeping scores comparable as the training pool grows. Test cases remain outside training and checkpoint selection. Checkpoints retain the admitted case names and the state needed to resume.

## Evaluation and next steps

Evaluation uses full autoregressive rollouts. The quantities of interest are displacement error, cavity-volume curves, pressure–volume loops, and ejection fraction. Simulation generation is complete. Full validation and test evaluation will follow the current training run; final accuracy results are not available yet.

Solver accuracy is assessed separately from emulator accuracy. In particular, local incompressibility errors and sensitivity to mesh resolution and stabilisation need to be considered alongside displacement and cavity-volume errors.

The next experiment will expand PCA coefficients around the mean while carrying forward the trained base model. The reproducible campaign design and scripts are maintained in `experiments/mean_base/` in the source repository.
