---
title: "Learning left ventricular contraction and dilation"
description: "PCA geometry, a staged graph emulator, completed mean-geometry training, and held-out evaluation with PyVista animations."
date: 2026-10-16
lastmod: 2026-10-19
academic: true
bibliography: "bib/left-ventricle-emulator.bib"
ShowToc: true
TocOpen: false
comments: false
tags: ["Cardiac mechanics", "Graph neural networks", "PCA", "Cardiac Simulation"]
url: /posts/lv-emulator/
---

This project learns an emulator of left ventricular (LV) contraction and dilation across ventricular shapes, material properties, and loading conditions. A finite-element solver provides displacement trajectories, and an augmented MeshGraphNet advances the nodal displacement in time.

**State on 19 October 2026, 13:34 BST:** mean-geometry training is complete at 120,000 iterations (final loss **0.0070**). Narrow-geometry training is at approximately **57,000 / 120,000 iterations**, with latest logged training loss **0.0077**. All 600 narrow cases are validated. All 600 wider joint-sampled meshes have passed strict checks, and **65 / 600 joint simulations are complete**. Fibre/sheet tensor inputs remain a proposed experiment; the single-geometry models and running narrow baseline are unchanged.

[Source repository](https://github.com/mapengfei-glasgow/lv-gls-bdf2-ho) · [Report data and model configuration](/data/lv-emulator/2026-10-18/report_summary.json) · [Training history CSV](/data/lv-emulator/2026-10-18/training_history.csv)

## Motivation and relation to earlier work

The objective is to predict the **three-dimensional displacement field over a prescribed cardiac cycle**, including passive filling and active contraction. A field emulator retains spatial information that cavity pressure and volume alone cannot describe. Regional strain and stress reconstruction are possible downstream uses, but they require additional checks on displacement gradients and the constitutive response; they have not been validated by the displacement errors reported here.

Graph-based cardiac emulation provides an important starting point. {{< cite "dalton2022emulation" "author" >}} developed a multiscale message-passing emulator for **passive LV mechanics**, while {{< cite "dalton2024physics" "author" >}} also investigated physics-informed soft-tissue emulation. The current repository follows a supervised, autoregressive route: its targets are finite-element trajectories, and its training objective contains no equilibrium-residual or energy-minimisation term. The encode–process–decode architecture and noise-corrected one-step training are motivated by MeshGraphNets {{< cite "pfaff2021learning" >}}.

A complementary approach is the neural reduced-order model of {{< cite "regazzoni2022machine" "author" >}}, which learns pressure–volume dynamics and couples them to circulation models. Here the output is a nodal displacement field. Endocardial pressure and active tension are prescribed inputs; this experiment does not learn electrophysiology or a closed-loop circulation model. Its current evidence concerns a fixed-topology PCA family and sampled material/load parameters.

### How the project evolved

The archived manuscript, `GNN_LV/manuscript.tex` in `GNN_LV.zip`, records an earlier exploratory implementation. It includes a 232-node, 702-element quasi-static Guccione example with four sampled parameters and 100 time steps, followed by notes on a larger Holzapfel–Ogden dataset. Those settings and figures describe historical experiments. The results on this page come from the current 11,779-node, 59,940-element implementation, eight sampled parameters, 200 time steps, and the explicitly defined splits below.

The main idea retained from that manuscript is a full-cycle, field-valued autoregressive emulator. The present study adds a reproducible PCA geometry bundle, a mean-to-variable-geometry curriculum, complete held-out parameter evaluation at the mean shape, and a separate narrow-geometry training stage. **The narrow stage is still training; the quantitative results below belong to the completed mean-geometry model.**

## Current narrow-geometry training and data generation

This is a **static snapshot at 19 October 2026, 13:34 BST**, separate from the completed mean-geometry results below. Training loss is the primary learning diagnostic.

| Narrow training progress | Value |
|---|---:|
| Latest logged iteration | 57,000 / 120,000 |
| Latest logged training-window loss | **0.0077** |
| Latest complete monitoring/checkpoint iteration | 56,000 |
| Training loss at that monitoring point | 0.0080 |
| Validation rollout component RMSE at that point | 0.56 mm |
| Active elapsed time through that monitoring point | 13.89 hours |
| Training cases / shapes | 384 / 24 |

![Narrow-geometry training loss and validation rollout error against active elapsed time.](/images/lv-emulator/results-2026-10-19/narrow_training_progress.png)

*Each plotted point is a completed 1,000-iteration monitoring window; the latest training-only log may precede its corresponding rollout evaluation. Training loss has decreased from 0.0154, but validation rollout error fluctuates rather than showing the same sustained decrease. Normalisers continue updating, so these dimensionless losses should not be interpreted as millimetres or directly equated with the fixed-geometry run. No final narrow-stage test result is available yet.*

The wider data stage samples **geometry and physical parameters jointly**: 600 distinct pairs from one 24-dimensional scrambled Sobol design. The first 16 PCA coordinates span ±0.5σ, while the other 24 PCA coefficients remain zero. The eight physical parameter ranges are unchanged. The dataset split is **456 training / 72 validation / 72 testing**. This replaces the cancelled wider crossed design that would have reused the same 20 physical vectors across new shapes; its partial outputs were preserved.

| Joint simulation status at the snapshot | Cases |
|---|---:|
| Completed | 65 |
| Solver status running | 24 |
| Failed, awaiting the campaign recovery pass | 1 |
| No solver metadata yet, including queued/preprocessing cases | 510 |

All 600 joint meshes have passed strict mesh/fibre checks. Simulation completion is different from full data validation: the campaign watcher retries solver failures after workers finish, and writes the final readiness marker only after independent validation. No training on the joint dataset has started.

[Snapshot JSON](/data/lv-emulator/2026-10-19/current_state.json) · [Narrow training history CSV](/data/lv-emulator/2026-10-19/narrow_training_history.csv)

## Completed mean-geometry training: loss is the primary measure

The training loss is the mean squared error of the **normalised, noise-corrected one-step displacement update**, averaged over all real mesh nodes and three displacement components. Virtual nodes are excluded; basal mesh nodes are included in the current implementation. It is the primary measure used to assess learning progress. The final 1,000-iteration average is **0.0070**, and the last several evaluation windows are approximately 0.0068–0.0072.

![Training loss against cumulative active training time, decreasing to 0.0070.](/images/lv-emulator/results-2026-10-18/training_loss.png)

*The logarithmic vertical axis shows normalised MSE. Time is cumulative active training/evaluation time reconstructed from the log across restarts; downtime is excluded. Running normalisers were retained and continued updating, so the loss is dimensionless and is not a displacement error in millimetres.*

| Iteration | Training loss |
|---|---:|
| 10,000 | 0.1309 |
| 20,000 | 0.0859 |
| 40,000 | 0.0450 |
| 60,000 | 0.0248 |
| 100,000 | 0.0083 |
| 120,000 | **0.0070** |

Rollout error is a secondary diagnostic of accumulated prediction error. The final monitored validation RMSE is **0.35 mm** on the same ten fixed validation cases; the best logged value is **0.34 mm** at iteration 111,000.

![Full-cycle validation rollout RMSE against cumulative active training time.](/images/lv-emulator/results-2026-10-18/rollout_history.png)

*This history uses the ten fixed validation cases used during training. There is no testing-error history: the test split is evaluated after training and is not used to select checkpoints.*

## Final validation and testing errors

The figures and results below use **`last.pt`, iteration 120,000**, with no further fitting. Both held-out splits are evaluated in full. A fixed, seeded 40-case training subset provides a diagnostic comparison; training loss above still comes from the complete training process with all 760 training cases.

| Evaluation group | Cases | Mean component RMSE | Mean vector RMSE | Mean absolute EF error |
|---|---:|---:|---:|---:|
| Training subset | 40 | 0.345 mm | 0.598 mm | 0.84 pp |
| Validation | 120 | 0.342 mm | 0.593 mm | 0.80 pp |
| Testing | 120 | 0.343 mm | 0.594 mm | 0.76 pp |

For one case, the reported component RMSE is

$$
E_{\mathrm{comp}}=
\sqrt{\frac{1}{3N(N_t+1)}
\sum_{n=0}^{N_t}\sum_{i=1}^{N}\sum_{d=1}^{3}
\left(\widehat u_{n,i,d}-u^{\mathrm{FE}}_{n,i,d}\right)^2}.
$$

Here $N=11{,}779$, $N_t=200$, and the average includes the initial frame and all real mesh nodes, including basal nodes. Displacements are stored in metres and converted to millimetres for reporting. Vector RMSE is $\sqrt{3}$ times the component value. Table entries are the mean of the per-case RMSEs. EF error is in percentage points, with end diastole at $t/T=0.5$ and end systole defined by the minimum volume over $0.5\leq t/T\leq0.8$.

![Mean training-subset, validation, and testing rollout errors over normalised cardiac time.](/images/lv-emulator/results-2026-10-18/split_errors_vs_time.png)

*Curves show mean per-case component RMSE at each cardiac phase; bands show the 10th–90th percentiles across cases. Time is normalised by the sampled cycle length, so cycles with different periods can be compared. Validation uses 120 cases and testing uses 120 cases.*

[Training-subset metrics](/data/lv-emulator/2026-10-18/train_metrics.csv) · [Validation metrics](/data/lv-emulator/2026-10-18/val_metrics.csv) · [Test metrics](/data/lv-emulator/2026-10-18/test_metrics.csv)

## A solver sample and its emulator prediction

The illustrated sample is **`mean_p0012`**, the first test case in the fixed manifest, chosen before inspecting prediction errors. It is an illustration, not a case selected for unusually good performance.

![Animated finite-element LV simulation, coloured by displacement magnitude in millimetres.](/images/lv-emulator/results-2026-10-18/simulation.gif)

*Finite-element solution through the prescribed first cycle. PyVista renders the deformed tetrahedral mesh surface; deformation is shown at true scale (1×), and the displacement colour range is fixed across frames.*

![Animated side-by-side solver, emulator, and pointwise displacement error.](/images/lv-emulator/results-2026-10-18/evaluation.gif)

[Open the full-size comparison animation](/images/lv-emulator/results-2026-10-18/evaluation.gif).

*Left: solver. Centre: final-model prediction. Right: the three-dimensional pointwise error norm, displayed on the solver geometry. Solver and prediction use the same fixed displacement colour range; the error range is also fixed. Animation colours show vector magnitudes, while the error-history plots show component RMSE. Each GIF contains 101 PyVista frames, displayed at 20 frames/s. Playback slows the cycle for inspection; the final loaded state need not equal the initially undeformed state.*

![Illustrative test-case error and cavity-volume comparison against physical time.](/images/lv-emulator/results-2026-10-18/representative_error_volume.png)

## Model structure

![Encode-process-decode graph emulator with ten residual message-passing blocks.](/images/lv-emulator/results-2026-10-18/model_architecture.svg)

| Component | Implemented configuration |
|---|---|
| Real nodes | 11,779 mesh nodes |
| Virtual nodes | 3,921 hierarchical cluster nodes |
| Graph | 15,700 nodes; 196,354 directed edges in the stored checkpoint |
| Node inputs | **18** features: displacement-derived velocity (3), endo/epi/base flags (3), virtual-node flag (1), material/load/cycle parameters (8), prescribed pressure and active tension at the next step (2), time step (1) |
| Edge inputs | **8** features: reference relative position and length (4), deformed relative position and length (4) |
| Encoders | Separate node and edge MLPs, two hidden layers, ReLU, 128 latent features, trailing LayerNorm |
| Processor | **10 independently parameterised residual blocks**; edge updates, incoming-edge sum aggregation, node updates |
| Decoder | MLP producing a three-component update; no trailing LayerNorm |
| Trainable parameters | 1,590,915 |
| Shape conditioning | Reference/deformed edge geometry; PCA coefficients are stored in the new dataset but are not appended to the base model's 18 node inputs |

The state uses displacement-derived velocity $\mathbf v_n=(\mathbf u_n-\mathbf u_{n-1})/\Delta t$. Rather than regressing the next displacement directly, the network learns the correction to linear extrapolation:

$$
\boldsymbol\Delta_n
=\mathbf u^{\mathrm{FE}}_{n+1}-2\mathbf u^{\mathrm{FE}}_n+\mathbf u^{\mathrm{FE}}_{n-1}.
$$

During an autoregressive rollout, the model receives its own predicted states:

$$
\widehat{\mathbf u}_{n+1}
=2\widehat{\mathbf u}_n-\widehat{\mathbf u}_{n-1}
+\widehat{\boldsymbol\Delta}_n,
\qquad
\widehat{\mathbf u}_{-1}=\widehat{\mathbf u}_0=\mathbf 0.
$$

This target is a second temporal difference, approximately $\Delta t^2\mathbf a_n$ for smooth motion. It is a learned discrete update, rather than a direct prediction of physical acceleration.

The target and input features are normalised using stored running statistics. Training applies position noise with standard deviation **$5\times10^{-5}$ m (0.05 mm)** and adjusts the update target accordingly, with noise parameter $\gamma=0.1$. The base loss is one-step MSE; pushforward, volume, and incompressibility penalty terms are not included.

For completeness, let $\widetilde{\mathbf u}_n=\mathbf u^{\mathrm{FE}}_n+\boldsymbol\epsilon_n$ and $\widetilde{\mathbf u}_{n-1}=\mathbf u^{\mathrm{FE}}_{n-1}+\boldsymbol\epsilon_{n-1}$ be the independently perturbed inputs. The implemented training target is

$$
\mathbf y_n=\mathbf u^{\mathrm{FE}}_{n+1}
-2\widetilde{\mathbf u}_n+\widetilde{\mathbf u}_{n-1}
+(1-\gamma)\boldsymbol\epsilon_n.
$$

With $\mathcal N_y$ the running target normaliser, the minibatch objective is

$$
\mathcal L_{\mathrm{train}}
=\frac{1}{3BN}\sum_{k=1}^{B}\sum_{i=1}^{N}\sum_{d=1}^{3}
\left[f_\theta(\mathcal G_k)_{i,d}
-\mathcal N_y(\mathbf y_k)_{i,d}\right]^2.
$$

The network output $f_\theta$ is in normalised target units. The graph $\mathcal G_k$ contains the normalised node and edge features of one sampled case/time pair. Training uses solver states with injected noise; evaluation recursively uses predictions without access to the next solver state. This distinction explains why a small one-step loss and a small full-cycle error are separate measurements.

| Training setting | Value |
|---|---|
| Optimizer | Adam |
| Batch | 4 one-step samples |
| Iterations | 120,000 |
| Learning rate | Cosine decay, $10^{-3}\rightarrow10^{-6}$ |
| Gradient clipping | Norm 1.0 |
| Latent width / message-passing steps | 128 / 10 |
| Data refresh | Every 500 iterations while simulations were completing |
| Monitoring | Every 1,000 iterations; ten fixed validation cases |
| Continuation | Weights, optimizer, scheduler, graph, normalisers, admitted case names, and RNG states retained |

The graph hierarchy is built on the mean training shape using k-means clustering, approximately four leaves per root, three nearest-neighbour connections within intermediate virtual layers, and a fully connected final virtual layer. Virtual nodes provide communication over larger spatial scales.

## Fibre directions: from cell fields to graph inputs

Dalton’s data-driven LV emulator explicitly includes three-dimensional fibre directions in the real-node features, alongside boundary indicators and the radial direction (§4.4) {{< cite "dalton2022emulation" >}}. The later physics-informed paper gives node features of the form $(d_i,\mathbf f_i)$ for the relevant anisotropic models (§2.4.5, equation 24) {{< cite "dalton2023physics" >}}. These are neural-network inputs, in addition to the fibre fields used by the constitutive law.

Our finite-element pipeline instead stores fibre and sheet directions at **tetrahedral cell centres**. Our currently trained GNN has 18 node features and **does not receive either direction explicitly**. A cell-centred field can still be supplied to a vertex-based network by defining a cell-to-node projection; matching storage locations is not required.

<div class="lv-next-steps">

### Proposed experiment: volume-weighted structural tensors

For node $i$, let $\mathcal K(i)$ be its incident tetrahedra, $V_K$ their reference volumes, and $\mathbf f_K$ the cell fibre unit vectors. A simple vector projection would average $V_K\mathbf f_K$ and normalise the result. However, $\mathbf f_K$ and $-\mathbf f_K$ describe the same material axis, so direct vector averaging can cancel physically equivalent directions. A near-zero average also makes vector normalisation unstable.

Instead, project the **fibre structural tensor**:

$$
\mathbf A_i=
\frac{\displaystyle\sum_{K\in\mathcal K(i)}
V_K\,\mathbf f_K\otimes\mathbf f_K}
{\displaystyle\sum_{K\in\mathcal K(i)}V_K}.
$$

The symmetric tensor can be encoded with six independent components:

$$
\mathbf a_i=
\left(A_{xx},A_{yy},A_{zz},A_{xy},A_{xz},A_{yz}\right)_i.
$$

This representation is unchanged by reversing any cell fibre vector. For unit cell fibres and positive weights, $\mathbf A_i$ is positive semidefinite with trace one. It represents the local mixture of fibre axes and need not be rank one; extracting a single principal direction would discard some of that information. Define the sheet tensor in exactly the same way using $\mathbf s_K\otimes\mathbf s_K$. These are averages of material directions, not predictions of strain or stress.

Appending six fibre and six sheet components would expand the real-node input from **18 to 30 features**. Virtual-node tensor features should be pooled with the same hierarchy using explicitly defined nonnegative weights. The encoder and input normaliser would need a corresponding change. This should be tested as a separate model against the unchanged baseline, using the same cases and training budget, with one-step training loss reported first and rollout/volume errors assessed separately. The running narrow-geometry model has not been modified.

Projection loses cellwise detail, particularly near sharp changes in material direction. A more expressive alternative is a bipartite graph with one node per tetrahedron connected to its four vertices: cell nodes retain the original local fibre/sheet information and exchange messages with displacement nodes. This requires more memory and a larger architectural change. The volume-weighted tensor projection is therefore the recommended first ablation, rather than an already validated improvement.

</div>

## 课程学习 / geometry curriculum

Training across a broad geometry range from the outset proved difficult in earlier experiments. The curriculum first learns material- and loading-dependent motion on one fixed geometry, then introduces small shape changes, and finally expands the target shape range. This is an application of the curriculum-learning principle of progressively increasing task difficulty {{< cite "bengio2009curriculum" >}}; its benefit here remains to be quantified against training the same geometry family from scratch.

| Stage | Geometry | Data design | State |
|---|---|---|---|
| 1. Mean-geometry base | All 40 standardised PCA coefficients zero | 1,000 parameter samples; 760 train / 120 validation / 120 test | **Training complete** |
| 2. Narrow variation | First 16 coefficients in **[−0.25, 0.25]σ**; remaining coefficients zero | 30 shapes × 20 parameters; 384 train / 102 validation / 114 test | **600 validated; training at approximately 57,000 iterations** |
| 3. Wider joint sampling | First 16 coefficients within ±0.5σ; remaining zero | 600 unique geometry/physics pairs; 456 train / 72 validation / 72 test | **Meshes checked; simulations running; no training yet** |
| 4. Full geometry family | Further PCA-range/mode expansion | To be specified | Planned |

Stage 1 began with fresh weights on the PCA mean, rather than continuing the older geom_0000 model. Completed simulations were added incrementally, while the validation set stayed fixed and optimizer/normaliser state was preserved. Stage 2 starts from the saved base checkpoint at iteration **111,000**, whose recorded training loss is **0.0069**, the lowest among the available saved base snapshots. This is a different checkpoint from the 120,000-iteration model evaluated above. Lower losses logged at unsaved iterations do not provide recoverable weights. The stage retains the network, hierarchy and normalisers, resets Adam and the cosine schedule to $10^{-4}\rightarrow10^{-6}$, and trains for a planned 120,000 further iterations with batch size 4. Outputs are stored separately in `surrogate_runs/geometry_narrow_from_mean_loss/`; `best_loss.pt` tracks minimum 1,000-iteration mean training loss. The original mean-geometry model is left intact.

The narrow stage has 24 training shapes, three validation shapes, and three test shapes. Sixteen parameter vectors come from the base training split, two from validation, and two from testing. A case is training only when both its shape and parameter are training; any test component makes it a test case; remaining combinations are validation. The mean shape is included as an anchor, and 20 identical completed mean-shape trajectories are reused. This leaves 580 new simulations.

## Sampling method and parameter ranges

**Mean campaign:** an eight-dimensional scrambled Sobol design {{< cite "sobol1967distribution" >}} (seed **42**), generated as 1,024 points and truncated to 1,000. A separate shuffled split (seed **43**) assigns 760/120/120 cases. Material constants are sampled log-uniformly; loading parameters and cycle length are sampled uniformly. Network parameter features are mapped to [−1, 1]. The truncated 1,000-point design does not retain the exact power-of-two balance of the original 1,024-point Sobol block.

| Parameter | Meaning | Nominal | Sample range | Distribution |
|---|---|---:|---:|---|
| $a$ | Isotropic stiffness (Pa) | 224.487 | 149.658–336.7305 | Log-uniform |
| $b$ | Isotropic exponential parameter | 1.6215 | 1.081–2.43225 | Log-uniform |
| $a_f$ | Fibre stiffness (Pa) | 2,426.7 | 1,617.8–3,640.05 | Log-uniform |
| $b_f$ | Fibre exponential parameter | 1.8268 | 1.2178667–2.7402 | Log-uniform |
| $T_a$ amplitude | Active tension (kPa) | 84.26 | 60–110 | Uniform |
| $p_{\mathrm{ED}}$ | Diastolic pressure (kPa) | 1.067 | 0.8–1.6 | Uniform |
| $p$ amplitude | Systolic pressure amplitude (kPa) | 13.46 | 10–16 | Uniform |
| $T$ | Cycle length (s) | 1.0 | 0.75–1.2 | Uniform |

**Narrow geometry campaign:** seed **20261017** selects the 20 parameter vectors within their original base splits, then samples 29 nonzero shape offsets uniformly in [−0.25, 0.25] on the first 16 standardised PCs. Shape 0 is the exact mean. Every shape is crossed with the same parameter vectors, allowing comparisons at matched materials and loads. The source parameter IDs, all 40 coefficients, split assignments, and asset hashes are recorded in `design.json`; `shape_coeffs.csv` stores the first 16 standardised coefficients.

**Wider joint geometry/physics campaign:** seed **20261020** generates 24-dimensional scrambled Sobol points. Coordinates 0–15 determine the 16 varied PCA coefficients; coordinates 16–23 determine the eight physical parameters through the same mappings used above. Seed **20261021** shuffles the case split. One geometry is paired with one newly sampled parameter vector, rather than crossing a small fixed parameter set over all shapes. A nonfinite/inverted tetrahedron rejects the entire pair; accepted/rejected Sobol indices, exact unit-cube samples and asset hashes are recorded. As with the mean campaign, truncation and any rejection remove exact power-of-two balance. The current wider bounds do not yet span all 40 PCA modes.

## Geometry and finite-element targets

The geometry model uses a PCA basis extracted from the Dalton LV mesh family:

$$
\mathbf X_{\mathrm{raw}}(\mathbf z)=\overline{\mathbf X}_{\mathrm{raw}}+
\sum_{i=1}^{40}z_i\sigma_i\boldsymbol\phi_i.
$$

![Mean geometry and examples of narrow and wider PCA variations.](/images/lv-emulator/pca-geometries.png)

*Reference shapes, not predicted motion. The narrow example varies 16 coefficients within ±0.25σ; the wider illustration varies 40 within ±1σ. The wider illustration is not a trained-model result.*

Connectivity is fixed at **11,779 nodes and 59,940 tetrahedra**. The bundled topology/mapping assets reconstruct corner and centroid coordinates in the solver's node ordering. The existing PCA fit uses all 2,967 source geometries, including their original train/validation/test partitions; the reported held-out model evaluation here concerns simulation parameters at a fixed mean geometry.

The solver uses Holzapfel–Ogden passive mechanics {{< cite "holzapfel2009constitutive" >}}, active fibre tension, prescribed endocardial pressure, GLS P1/P1 velocity–pressure elements, the repository’s `pdf` stabilisation variant with fibre–sheet stiffness included, and BE/BDF2 time stepping. Each cycle has **200 steps**, with $\Delta t=T/200$. Boundary tags identify base, endocardium, and epicardium. Rule-based fibres are rebuilt with a Laplace transmural coordinate and +60°/−60° endocardial/epicardial helix angles.

The repository bundles the PCA basis and geometry generator in `geometry/`, so reconstruction requires no separate geometry dataset download. Generated meshes, simulation fields, and checkpoints remain outside version control.

```bash
python geometry/generate.py --out geometry/generated/mean
python geometry/generate.py --modes 16 --scale 0.25 --seed 42 \
    --out geometry/generated/narrow
```

[Mean sampling design](/data/lv-emulator/2026-10-18/mean_design.json) · [Narrow geometry design](/data/lv-emulator/2026-10-18/narrow_design.json) · [Narrow parameter samples](/data/lv-emulator/2026-10-18/narrow_params.csv)

## Reproduction and interpretation

Report scripts are in `experiments/mean_base/report/`: batched held-out evaluation, training-history parsing, error plots, architecture drawing, and PyVista frame/GIF generation. Validation/test case coverage is checked before their distributed report parts are merged. The completed mean-geometry evaluation figures and animations use the final 120,000-iteration checkpoint; the narrow-stage progress plot uses its separate running history. The separate historical `best.pt` remains selected by monitored validation rollout RMSE; it is not the checkpoint used for these final-checkpoint figures.

The animation renderer writes PNG frames before combining them into GIFs. It uses fixed cameras, true-scale displacement, and fixed scalar limits. The report JSON records metric definitions, split counts, graph dimensions, checkpoint iteration, and sampling ranges.

Solver accuracy and emulator accuracy are assessed separately. Local incompressibility errors, mesh resolution, and stabilisation sensitivity still matter when interpreting the finite-element targets, even when the emulator matches those targets closely.


## Research directions with direct implementation value

<div class="lv-next-steps">

The papers below offer concrete experiments for this repository. Their reported results come from their own benchmarks; improvement on our LV data is a hypothesis to test. The order reflects implementation value for the present model, rather than publication date. Keep the current narrow-geometry run as the baseline and evaluate each change in a separate run.

### 1. Bi-stride pooling: the first architecture experiment

The requested paper, **Bi-Stride Multi-Scale Graph Neural Network for Mesh-Based Physical Simulation** {{< cite "cao2022bistride" >}}, constructs a hierarchy using breadth-first graph distance, selecting alternating frontiers for pooling. This is the 2022 preprint of the work published at [ICML 2023 under a revised title](https://proceedings.mlr.press/v202/cao23a.html). Our model already has multiscale communication, so the experiment is to replace its **k-means/k-nearest-neighbour hierarchy** in `surrogate/graph.py` with topology-based pooling and explicit down/up transfers. Shared tetrahedral connectivity lets us reuse the pooling indices across PCA shapes, while recomputing geometry-dependent edge features. Compare the two hierarchies at matched training budgets and similar parameter counts. This can use the existing trajectories; it requires neither new finite-element solves nor a claim that the baseline lacks a hierarchy.

### 2. Pushforward training: a smaller change to the learning objective

**Message Passing Neural PDE Solvers** {{< cite "brandstetter2022message" >}} addresses the mismatch between solver-state inputs during training and predicted-state inputs during rollout. Its pushforward method feeds predictions back into a later training step, stopping gradients through the preparatory rollout. A related two-step option already exists in this repository’s older `surrogate/train.py`, but is absent from the active curriculum trainer, `surrogate/train_base.py`. A direct experiment is to port a small, gradually introduced pushforward term into a separate curriculum run, preserving the current one-step loss and recording both losses separately. Select the weight using validation data, while keeping one-step training loss the primary learning diagnostic and testing only the final chosen recipe. The paper’s demonstrations concern other PDEs; cardiac benefit remains to be measured.

### 3. X-MeshGraphNet: reduce memory costs before increasing resolution

**X-MeshGraphNet** {{< cite "nabian2024xmeshgraphnet" >}} partitions graphs with overlapping halo regions and aggregates gradients to reproduce full-graph training under its stated setup. This is relevant to our 196,354-edge augmented graph and future finer meshes. First benchmark activation memory, time per optimiser step, and loss/gradient agreement on a small LV graph. Halos must cover the actual message-passing dependencies, halo nodes must not contribute duplicate loss, and normaliser statistics must be consistent across partitions. Our global hierarchy can make ten-hop halos very large, so simply partitioning the augmented graph may provide little saving; separating local fine-grid work from shared coarse processing is an implementation question to resolve. This is a scaling strategy, not evidence that the cardiac prediction error will fall.

### 4. ROBIN: a recent nonlinear-solid-mechanics direction

**Diffusion-Based Hierarchical Graph Neural Networks for Simulating Nonlinear Solid Mechanics** {{< cite "wurth2025diffusion" >}} combines algebraic graph coarsening with rolling diffusion inference. Its solid-mechanics benchmarks make it especially relevant to global ventricular deformation. The smallest useful experiment is to borrow the **algebraic hierarchy** while retaining our deterministic one-step decoder, and compare it with k-means and bi-stride hierarchies before attempting diffusion. A full ROBIN-style model changes the training objective and inference procedure and cannot reuse our weights unchanged. The paper also identifies limitations concerning rotational equivariance and anisotropic materials; an LV implementation must explicitly address fibre/sheet information and validate the anisotropic response. Its reported solid-mechanics gains are not established cardiac results.

### 5. RIGNO: a larger redesign for time and mesh generalisation

**RIGNO** {{< cite "mousavi2025rigno" >}} processes physical points through a regional graph and conditions predictions on time and prediction lead time. It trains on pairs of snapshots at different time separations. A useful first ablation for our data is to add cardiac phase and lead-time conditioning and sample several available time separations, retaining displacement/velocity state and the prescribed loading information. This can reuse the 201 stored snapshots per trajectory. It requires a consistent multi-step target and scaling: the present second-difference target should not simply be reused with an arbitrary lead time. Test temporal generalisation within the stored time grid first; claims about unseen mesh resolutions require additional meshes. Replacing the full model with RIGNO is a longer-term operator-learning experiment, rather than a checkpoint-compatible upgrade.

**Recommended sequence:** compare bi-stride pooling with the existing hierarchy first, then test a modest pushforward-training variant. Pursue X-MeshGraphNet when memory limits the next resolution increase; assess algebraic coarsening before full diffusion, and reserve a RIGNO redesign for explicit time/resolution-generalisation goals. For every comparison, retain the same case splits, sampling seeds and evaluation definitions; report one-step training loss first, then validation loss and rollout/volume errors, and keep the test split out of method selection. None of these proposals changes the currently running baseline.

</div>

## References

{{< references >}}
