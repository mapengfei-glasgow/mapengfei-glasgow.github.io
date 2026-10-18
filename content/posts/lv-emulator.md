---
title: "Learning left ventricular contraction and dilation"
description: "PCA geometry, a staged graph emulator, completed mean-geometry training, and held-out evaluation with PyVista animations."
date: 2026-10-16
lastmod: 2026-10-18
academic: true
bibliography: "bib/left-ventricle-emulator.bib"
ShowToc: true
TocOpen: false
comments: false
tags: ["Cardiac mechanics", "Graph neural networks", "PCA"]
---

This project learns an emulator of left ventricular (LV) contraction and dilation across ventricular shapes, material properties, and loading conditions. A finite-element solver provides displacement trajectories, and an augmented MeshGraphNet advances the nodal displacement in time.

**State on 18 October 2026:** the mean-geometry base run has completed **120,000 iterations**, with final training loss **0.0070**. All **1,000 mean-geometry simulations** are complete. All **600 narrow-geometry cases are now complete and validated**, and the narrow-geometry curriculum stage has started in a separate run. The single-geometry models are preserved.

[Source repository](https://github.com/mapengfei-glasgow/lv-gls-bdf2-ho) · [Report data and model configuration](/data/lv-emulator/2026-10-18/report_summary.json) · [Training history CSV](/data/lv-emulator/2026-10-18/training_history.csv)

## Motivation and relation to earlier work

The objective is to predict the **three-dimensional displacement field over a prescribed cardiac cycle**, including passive filling and active contraction. A field emulator retains spatial information that cavity pressure and volume alone cannot describe. Regional strain and stress reconstruction are possible downstream uses, but they require additional checks on displacement gradients and the constitutive response; they have not been validated by the displacement errors reported here.

Graph-based cardiac emulation provides an important starting point. {{< cite "dalton2022emulation" "author" >}} developed a multiscale message-passing emulator for **passive LV mechanics**, while {{< cite "dalton2024physics" "author" >}} also investigated physics-informed soft-tissue emulation. The current repository follows a supervised, autoregressive route: its targets are finite-element trajectories, and its training objective contains no equilibrium-residual or energy-minimisation term. The encode–process–decode architecture and noise-corrected one-step training are motivated by MeshGraphNets {{< cite "pfaff2021learning" >}}.

A complementary approach is the neural reduced-order model of {{< cite "regazzoni2022machine" "author" >}}, which learns pressure–volume dynamics and couples them to circulation models. Here the output is a nodal displacement field. Endocardial pressure and active tension are prescribed inputs; this experiment does not learn electrophysiology or a closed-loop circulation model. Its current evidence concerns a fixed-topology PCA family and sampled material/load parameters.

### How the project evolved

The archived manuscript, `GNN_LV/manuscript.tex` in `GNN_LV.zip`, records an earlier exploratory implementation. It includes a 232-node, 702-element quasi-static Guccione example with four sampled parameters and 100 time steps, followed by notes on a larger Holzapfel–Ogden dataset. Those settings and figures describe historical experiments. The results on this page come from the current 11,779-node, 59,940-element implementation, eight sampled parameters, 200 time steps, and the explicitly defined splits below.

The main idea retained from that manuscript is a full-cycle, field-valued autoregressive emulator. The present study adds a reproducible PCA geometry bundle, a mean-to-variable-geometry curriculum, complete held-out parameter evaluation at the mean shape, and a separate narrow-geometry training stage. **The narrow stage is still training; the quantitative results below belong to the completed mean-geometry model.**

## Training progress: loss is the primary measure

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

## 课程学习 / geometry curriculum

Training across a broad geometry range from the outset proved difficult in earlier experiments. The curriculum first learns material- and loading-dependent motion on one fixed geometry, then introduces small shape changes, and finally expands the target shape range. This is an application of the curriculum-learning principle of progressively increasing task difficulty {{< cite "bengio2009curriculum" >}}; its benefit here remains to be quantified against training the same geometry family from scratch.

| Stage | Geometry | Data design | State |
|---|---|---|---|
| 1. Mean-geometry base | All 40 standardised PCA coefficients zero | 1,000 parameter samples; 760 train / 120 validation / 120 test | **Training complete** |
| 2. Narrow variation | First 16 coefficients in **[−0.25, 0.25]σ**; remaining coefficients zero | 30 shapes × 20 parameters; 384 train / 102 validation / 114 test | **600 validated; training started** |
| 3. Wider geometry family | Broader target PCA range | To be specified | Planned |

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

Report scripts are in `experiments/mean_base/report/`: batched held-out evaluation, training-history parsing, error plots, architecture drawing, and PyVista frame/GIF generation. Validation/test case coverage is checked before their distributed report parts are merged. All figures above use the final 120,000-iteration checkpoint. The separate historical `best.pt` remains selected by monitored validation rollout RMSE; it is not the checkpoint used for these final-checkpoint figures.

The animation renderer writes PNG frames before combining them into GIFs. It uses fixed cameras, true-scale displacement, and fixed scalar limits. The report JSON records metric definitions, split counts, graph dimensions, checkpoint iteration, and sampling ranges.

Solver accuracy and emulator accuracy are assessed separately. Local incompressibility errors, mesh resolution, and stabilisation sensitivity still matter when interpreting the finite-element targets, even when the emulator matches those targets closely.


## References

{{< references >}}
