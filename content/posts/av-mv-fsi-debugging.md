---
title: "AV/MV valve FSI: debugging summary"
description: "One root cause, seven real defects, seven ruled-out hypotheses and the layered-diagnosis method behind the real aortic- and mitral-valve FSI cases, with command matrices, pressure/flow comparisons and PyVista deformation snapshots."
date: 2026-09-13
academic: true
ShowToc: true
TocOpen: false
---

## 0. Start here: the working recipes and results

These are the two recipes that actually work.  Read them first; the analysis of
why the earlier attempts failed starts in §4.  All numerical figures and the
PyVista deformation snapshots in §1–§3 were generated from the saved AV and MV
runs.

| Case | Working recipe | Result | Details |
|---|---|---|---|
| **AV** | Stokes, fibre `mny`, `--av-beta-s 5e6`, `--pk1-mask 15,16,18`, `--tether-mask 5,17` | **1.635 s / 327,000 steps**, no instability | §1, Figures 1–3 |
| **MV** | `--mv-rigid-c1 1e7`, leaflet stiffness x30, `--gpu-solid` | **0.785 s / 125,600 steps**, complete cycle | §2, Figures 4–5 |

The solid-deformation snapshots are in §3.  The failures of the simpler
configurations, the seven real defects, the ruled-out hypotheses and the layered
diagnosis method are analysed in §4–§9; the remaining work is in §10.

> **Environment and build instructions:** see
> [FDM-3D v1: environment, build and run](/posts/fdm-3d-v1-build-and-run/).
>
> **Second implementation:** §12 documents the same AV case in the
> `npuheart`/`gfem` CMake + Kokkos code base, with a conda-based build and the
> full-resolution mesh (2026-09-15 run).

## 1. AV: working recipe and results

The AV campaign splits into two command families:

- the **Stokes production run**, which is the one that reaches the full
  $T = 1.635$ s;
- the **convection runs**, used to test whether SOU advection removes the
  closing-transient wall.

<p class="tcaption">Table 1. AV: command combinations and observed reachable state.</p>

| ID | Run | Command combination | Reached | Observation |
|---|---|---|---|---|
| AV-1 | Stokes, fibre mny | `--av-iso-form mny --av-beta-s 5e6 --pk1-mask 15,16,18 --tether-mask 5,17` (exact command below) | **1.635 s / 327,000 steps** | complete, 0 instabilities |
| AV-2 | SOU convection, NH walls | `--nh --nh-mu 1e7 --nh-lambda 1e7 --pk1-mask 15,16,18 --conv --conv-upwind`; feedback off | 0.335 s | max displacement reaches 0.90, then NaN |
| AV-3 | SOU convection, elastic wall + fibre | AV-2 plus `--pk1-mask 5,15,16,17,18 --av-rigid-c1 1e7` | 0.41–0.45 s | wall elasticity extends the run; SOU alone is not the fix |

The exact AV-1 production command is:

```bash
cd fdm-3d-v1-gpu
./build-av/real_av --N 64 --pk1-mask 15,16,18 --tether-mask 5,17 \
  --beta-body 5e8 --z-clear 0.2 --radius 1.24 --feedback --feedback-kappa 1e5 \
  --open-bc --av-iso-form mny --av-beta-s 5e6 \
  --windkessel --wk-old --wk-freeze 0 --nvc 2 --helm-nvc 1 \
  --machine-error --dt 5e-6 --T 1.635 --every 1000 --out out_fiber_full/
```

For AV-2/AV-3 the essential switch
is the pk1 mask: as long as only the leaflets (15,16,18) carry elastic stiffness,
the tube and sinus (markers 5 and 17, together 88.6% of the cells) are supported
only by the body penalty.  Adding `5,17` to the pk1 mask makes the wall elastic
and pushes the convection run from about 0.35 s to about 0.42 s.

{{< figure src="/fdm/av_command_progress.png" title="Figure 1. AV command combinations and the reachable time of each. The dashed line is the full two-cycle target, T = 1.635 s." >}}

{{< figure src="/fdm/av_full_results.png" title="Figure 2. AV production run (Stokes, fibre mny, βs = 5e6, 327,000 steps). (a) inlet LV pressure and Windkessel outlet pressure; (b) flow rate integrated on the two axial faces; (c) maximum solid displacement and force; (d) L2 divergence." >}}

{{< figure src="/fdm/av_command_comparison.png" title="Figure 3. AV command comparison: Stokes fibre (blue, runs to 1.635 s) against SOU convection with NH walls and feedback off (red, 0.335 s). The prescribed inlet pressure is identical; the outlet pressure and flow already differ, and the SOU run still ends in NaN." >}}

## 2. MV: working recipe and results

The MV sequence is the clearest example of the layered diagnosis: each fix moves
the collapse to the next weakest region, so the commands must be compared as a
chain rather than one switch at a time.

<p class="tcaption">Table 2. MV: command combinations and observed reachable state.</p>

| ID | Run | Key command combination | Reached | Note |
|---|---|---|---|---|
| MV-0 | baseline, literature stiffness | `--mv-Jclip 0.2` (no `--mv-rigid-c1`) | 0.375 s (48%) | default wall |
| MV-1 | + zero-stiffness correction | add `--mv-rigid-c1 1e7` | 0.500 s (64%) | tube/disk (41% of cells) given a real modulus |
| MV-2 | + leaflet stiffness x10 | literature `C1`/`af` multiplied by 10 | 0.500 s | still fails at the same place |
| MV-3 | + leaflet stiffness x30 | `--mv-C1-ant 5.2110e6 --mv-af-ant 9.43788e6 --mv-C1-post 3.06e6 --mv-af-post 1.5e7` | **0.785 s / 125,600 steps** | complete cardiac cycle |
| MV-4 | + leaflet stiffness x100 | same with x100 values | 0.785 s | complete, but further from the literature |

The exact MV-3 command is:

```bash
cd fdm-3d-v1-gpu
DSH_CS_POIS=20 DSH_CS_HELM=8 DSH_FLAT_ASM=1 OMP_NUM_THREADS=8 \
./build-av/real_mv --variant gao_0 --N 64 --T 0.785 --dt 6.25e-6 \
  --beta 1.0 --beta-body 1e8 --pk1-mask all --tether-mask 5,6,11,12 \
  --mv-Jclip 0.2 --mv-rigid-c1 1e7 \
  --mv-C1-ant 5.2110e6 --mv-af-ant 9.43788e6 \
  --mv-C1-post 3.06e6 --mv-af-post 1.5e7 \
  --nvc 2 --helm-nvc 1 --gpu-solid --every 10000 --out out_real_mv_cycle/
```

> ⚠ MV-3 uses leaflet stiffness **30× the literature value**.  This is an
> empirical calibration, not a physical result.  The cycle can be completed, but
> `|div|` rises to 0.1–0.3 during systole, so quantitative statements about
> regurgitation and closure dynamics from this run remain unsafe.

{{< figure src="/fdm/mv_command_progress.png" title="Figure 4. MV command matrix: the reachable time moves from 0.375 s (48% of the cycle) to the complete 0.785 s cycle. The dashed line is the full-cycle target." >}}

{{< figure src="/fdm/mv_full_results.png" title="Figure 5. MV production run (gao_0, N = 64, Δt = 6.25e-6 s, rigid-c1 = 1e7, leaflet stiffness x30). (a) prescribed inlet pressure; (b) axial flow-rate estimate on the two faces, plotted on a symmetric-log axis — during systole this run has |div| = 0.1–0.3, so the curve is a numerical diagnostic rather than a physiological flow rate; (c) maximum solid displacement and force; (d) L2 divergence. The divergence peaks in systole and falls again before the end of the cycle." >}}

## 3. Solid deformation with PyVista

The deformation snapshots are rendered directly from the same binary output the
solver writes: `ref_nodes.bin` (reference coordinates), `Xc_<step>.bin` (current
coordinates), and the first four node indices of each cell in `dofmaps.bin`.
For each selected time the renderer builds a `pyvista.UnstructuredGrid`, attaches
the displacement vector and its magnitude,

```python
grid.points = Xc
grid.point_data["u"] = Xc - ref
grid.point_data["|u|"] = np.linalg.norm(grid.point_data["u"], axis=1)
surface = grid.extract_surface()
```

and renders the leaflet/chordae surface with the same camera and colour range.
The tube, disk and penalty regions are omitted so that the moving leaflets are
not hidden inside the surrounding solid.  AV snapshots are available every
$0.005$ s (`--every 1000`) and MV snapshots every $0.0625$ s
(`--every 10000`).

{{< figure src="/fdm/av_solid_deformation.png" title="Figure 6. AV leaflet solid deformation (markers 15/16/18), t = 0–1.635 s. Colour is |u| in cm; every panel uses the same camera and colour scale." >}}

{{< figure src="/fdm/mv_solid_deformation.png" title="Figure 7. MV leaflet/chordae solid deformation (markers 7/8/10/11/12), t = 0–0.785 s. Colour is |u| in cm; every panel uses the same camera and colour scale." >}}

---

## 4. Root cause: why the simple fixes fail

The instabilities of the two cases (aortic valve in a straight tube / mitral
valve in a straight tube) converge on the **same root cause**:

```text
large transvalvular pressure difference during closure/systole
+ leaflets with no load-bearing mechanism (compressive stiffness /
  coaptation contact / chordae)
      -> coaptation region crushed (J -> 0.004 ~ 0.04)
      -> local runaway -> global divergence
```

This is **not** a convection-scheme problem, **not** a time-step problem, **not**
a J-clip threshold problem, and **not** a mesh-sliver problem (in these two cases
the slivers and the collapse locations do not coincide).

## 5. Reachable state at the end of this round

| Case | Configuration | Reachable |
|---|---|---|
| **AV, Stokes** | fibre mny + `--av-beta-s 5e6` | **1.635 s completed** (327,000 steps) |
| **AV, convection ON** | NH + SOU + feedback off + vessel-wall elasticity | 0.425 s |
| **AV, convection ON** | **fibre mny + SOU + vessel-wall elasticity** | **0.41–0.45 s** |
| **MV** | `--mv-rigid-c1 1e7` + leaflet stiffness x30 | **0.785 s completed** (125,600 steps) |
| **MV** | same, x100 | 0.785 s completed |

### AV: how the convection sub-goal progressed

| Step | Instability time | Measure |
|---|---|---|
| Starting point (central difference + feedback) | 0.16 s | — |
| Switch to SOU | 0.10 s (no improvement) | the scheme is not the cause |
| Feedback off | 0.335 s | positive feedback at the orifice edge (dose–response demonstrated) |
| + elasticity in the vessel wall/sinus | 0.425 s | 88.6% of cells previously had zero elastic stiffness |
| + real fibre constitutive model | **0.41–0.45 s** | the three measures are compatible |

### MV: from "won't run" to a full cycle

| Step | Reachable | Measure |
|---|---|---|
| Starting point | 0.375 s | — |
| + stiffness in the zero-stiffness region | 0.500 s | 41% of cells had zero shear stiffness |
| + leaflet stiffness x30 | **0.785 s completed** | empirical calibration |

## 6. Real defects found and fixed (7)

| # | Defect | Effect | Fix |
|---|---|---|---|
| 1 | `pk1_aortic_valve` **not stress-free in the reference state**: `P(F=I) = 2·C01·C10 = 1.9336e5 ≠ 0` | false prestress; the legacy form goes NaN within 1000 steps | `--av-iso-form mny` |
| 2 | The AV isotropic term treats `C01=12100` as an **exponential coefficient** (the same family uses 56–63) | one-sided material explosion, no restoring force in compression | same as above |
| 3 | `pk1_aortic_valve` **has no volumetric term** (CODE_AUDIT B25) | leaflet volume unconstrained | `--av-beta-s` |
| 4 | The GPU `k_assemble_pk1` supported only NH/Guccione, and `real_av.cu` hard-coded material **0** | the fibre model was unusable on the GPU path | `material==2` + per-element `fiber_dir.bin` |
| 5 | **41% of MV/tube/disk cells had zero shear stiffness** (CODE_AUDIT B24 family, caught by the T-g criterion) | the load had nowhere to go | `--mv-rigid-c1` / `--av-rigid-c1` |
| 6 | The `rigid_c1` path **was missing J clipping** -> marker 17 degenerate cell (`V_ref` 2.24e-10) NaN immediately | crashed in <500 steps | independent `rigid_Jclip` (default 0.2) |
| 7 | The instability report `std::max(a, NaN)` **swallowed NaN** | `max\|u\|` at the crash point was reported as 0 | explicit propagation (4 demos) |

## 7. Hypotheses ruled out (all measured, not guessed)

| Hypothesis | Test | Conclusion |
|---|---|---|
| Convection scheme unstable | Ported and verified SOU (linear-exact + second-order convergence 4.36) | ❌ the scheme is second-order correct; changing it does not fix the instability |
| Pressure projection under-resolved | A more accurate MG improved `\|div\|` by 3–4 orders of magnitude | ❌ still crashes at the same step |
| Mesh slivers | `--solid-vmin` removed them (MV 298 / AV 130) | ❌ no change; and the MV slivers are in the papillary muscles, not at the collapse location |
| J-clip threshold | AV scanned 0.2/0.35/0.5/0.8/1.5; MV scanned 0.05/0.2 | ❌ non-monotone, not the solution |
| Added mass / strong coupling | `--beta` scanned 0/0.5/1/2/4 | ❌ the trend is the opposite: **stronger feedback delays the crash** |
| Leaflet degrees of freedom too large | `--tether-mask all` | ❌ displacements drop by an order of magnitude but instability comes **earlier** |
| Leaflets too soft (single variable) | leaflet `C1/af` x10 | ❌ ineffective — the **disk crashed first**; the load merely moved |

## 8. Method: layered diagnosis (the most valuable lesson of this round)

**Each time a layer is fixed, the collapse moves to the weakest point in the next
layer.** So "adding one parameter at a time shows no improvement" is normal; you
must look at the collapse distribution (`diag_J.py`) **at the same time** to know
whether a switch is actually working.

The MV example (number of cells with `J<0.8` after `--mv-rigid-c1 1e7`):

| marker | default @0.3125 | after rigid @0.3125 | @0.4375 |
|---|---|---|---|
| 5 tube | 19 | **0** <- fixed | 2 |
| 6 disk | 1590 | **121** <- largely fixed | 1915 |
| 7/8 leaflets | 968 | 3756 | **15234** <- everything moved here |
| total | 2577 | 3882 | **17201** (`Jmin` 0.043) |

Final localisation (AV, step 80000):

| marker | `Jmin` | `J<0.8` |
|---|---|---|
| 5 tube | 0.940 | **0** |
| **15/16/18 leaflets** | **0.016 / 0.017 / 0.099** | **569 / 424 / 251** |
| 17 vessel wall | 0.603 | 3 |

The `Jmin` location `(4.10, 4.38, 10.11)` is the **coaptation region** near the
tube axis at z≈10.1, the same place as the crash cell `cell 623` recorded in
`aortic-valve-tube.md` §3.

## 9. CLI switches added this round

| Switch | Purpose | Default |
|---|---|---|
| `--av-iso-form legacy\|mny` | AV isotropic term formulation (mny = reference-state normalisation) | legacy |
| `--av-beta-s X` | AV volumetric term `2βs·lnJ·F^-T` | 0 (off) |
| `--av-Jclip X` | AV J clipping ⚠ **harmful for the exponential isotropic term**; prefer `--av-beta-s` | 0 |
| `--av-rigid-c1 X` | neo-Hookean modulus for non-leaflet markers (5, 17) | 0 |
| `--mv-Jclip X` | MV J clipping (**dedicated to the volumetric/exponential term**, it does not scale F) | 0 |
| `--mv-reg-c1 X` | small shear regularisation for all MV cells | 0 |
| `--mv-rigid-c1 X` | modulus for MV markers with zero deviatoric term (5 tube / 6 disk) | 0 |
| `--solid-vmin X` | skip degenerate cells with `\|J[e]\| = 6V_ref` below the threshold during PK1 assembly | 0 (off) |
| `--gpu-solid` (real_mv) | run the MV solid on the GPU kernel (18.3x speed-up, bitwise identical to CPU) | off |

## 10. Remaining work (priority order)

1. **Solve compressive collapse in the leaflet coaptation region** — the last
   obstacle shared by AV and MV.
   Known ineffective: J-clip tuning, `--solid-vmin`, simply increasing stiffness.
   Directions: (1) an **anti-compression constitutive term** (a lower-bound
   penalty on J / anisotropic compressive stiffness); (2) **coaptation contact**
   (one-sided constraints between the anterior and posterior leaflets; a real
   valve supports itself through the coaptation surface); (3) **chordae
   constraints** (`mv_gao_*` has no `tether_kind.bin`/`tether_dir.bin` at all,
   and `assemble_tether` is a silent no-op); (4) re-mesh the coaptation region.
2. The **"15x speed-up" rule in `aortic-valve-tube.md` §4 needs correcting**:
   `DSH_CS_POIS=20 / DSH_CS_HELM=8` was calibrated on the AV mesh; after changing
   the domain it must be re-calibrated, and the acceptance criterion is whether
   **`|div|` grows in time** (stable on AV, but it grows by 3–4 orders of
   magnitude on MV).
3. Run MV with **real leaflet parameters** (the current result relies on a 30x
   empirical calibration).
4. GPU still does not support `SarahMV` / `LVMV` / `RealLV` materials; `mv_ibamr`
   data is missing on this machine.

## 11. Tests and regression

`fdm-3d-v1-gpu/test/` (all PASS):

- `test_ibm_pk1_aortic_valve_gpu`: AorticValve GPU/CPU consistency + `F=I`
  invariance
- `test_ibm_pk1_mitral_valve_gpu`: MitralValve consistency + `F=I` + **shear
  stiffness scan (T-g)**
- `test_unit_convection_cuda`: SOU **linear exactness (both upwind branches) +
  second-order convergence**

## 12. The same AV case in the npuheart/gfem codebase (2026-09-15)

§1–§11 are about `fdm-3d-v1-gpu`.  A second, independent implementation of the
same aortic-valve immersed-boundary problem is `cmame-v100-2`
(`npuheart`/`gfem`): a CMake + CUDA/Kokkos code driven by a JSON deck instead of
CLI switches, with the solid on a **P2 tetrahedral finite-element mesh**, the
fluid on a **staggered Cartesian grid**, and a four-point immersed-boundary delta
function coupling the two.  The physics is comparable to §1; the code path, the
build and the numbers below are not.

### 12.1 Environment: the spack recipe replaced by conda

The published recipe for this code needs spack plus a source-built `gcc@11.4.0`
and a full FEniCS/PETSc/Kokkos concretisation (hours).  It now builds from
conda-forge packages instead, in about 20 minutes end to end:

| Dependency | spack recipe | conda recipe (used here) |
|---|---|---|
| DOLFIN 2019.1 + FFC | `spack install fenics@2019.1.0.post0` | conda-forge `fenics-dolfin=2019.1.0` (+ boost/petsc/eigen/mpich) |
| Kokkos 4.3 + CUDA | spack source build | conda-forge `kokkos=4.3.00` build `cuda12*`, then rebuilt from source for `sm_89` |
| CUDA toolchain | spack `cuda` | conda-forge `cuda-nvcc=12.6` + `cuda-cudart-dev` + `cuda-cccl` |
| spdlog / fmt / muparser / nlohmann_json | spack | conda-forge prebuilt |
| basix (Gauss rules) | `spack env activate basix` | conda-forge `fenics-basix` |
| compiler | spack `gcc@11.4.0` | system `gcc 13.3` (host) + `nvcc 12.6` |

Four commands, all scripted in the repo:

```bash
bash scripts/setup_env.sh      # two conda envs
bash scripts/build_kokkos.sh   # Kokkos 4.3.01 for ADA89 (sm_89)
bash scripts/build.sh          # cmake + make, CUDA arch = 89
bash scripts/run_av.sh config/av_smoke.json
```

The seven build defects that had to be fixed are collected in §12.5; the one that
costs real performance if missed is the Kokkos architecture — the conda-forge
package is compiled for compute capability 5.0, so on a 4090 every Kokkos kernel
is PTX-JIT-compiled at start-up with

```text
Kokkos::Cuda::initialize WARNING: running kernels compiled for compute capability 5.0
on device with compute capability 8.9, this will likely reduce potential performance.
```

Rebuilding Kokkos with `-DKokkos_ARCH_ADA89=ON` removes the warning; the source
build additionally needs `CMAKE_POSITION_INDEPENDENT_CODE=ON`, because the
project links Kokkos into the shared library `libkokkos_lib.so` (a non-PIC static
Kokkos fails with `relocation R_X86_64_TPOFF32 ... recompile with -fPIC`).

### 12.2 The real mesh, and what the JSON actually controls

The AV mesh now present at `~/mesh-cardiology/AV` is the full-resolution
`mesh_connected_scale`, i.e. three times the cell count of the reduced variant
used for the first smoke tests:

| Quantity | Value |
|---|---|
| solid tetrahedra / nodes | **683,558 / 178,457** |
| bounding box | x 2.271–6.014, y 2.064–5.940, z 0–14 |
| mean / median edge length | 0.0716 / 0.0595 |
| element | P2 Lagrange, 10 nodes per cell |
| P2 dofs | **1,174,681 scalar (3,524,043 vector)** |
| background fluid grid | 80 × 80 × 128 = **819,200 cells**, Δx = Δy = 0.1, Δz = 0.109375 (domain 8 × 8 × 14) |
| ghost layers | p 82 × 82 × 130 = 874,120; u, v 884,780 each; w 880,844 |

Two IO facts are worth recording.  The `*.xml` `MeshFunction` files are
uncompressed DOLFIN XML and dominate the input size (`boundaries_connected.xml`
alone is 164 MB against a 15 MB `mesh_connected_scale.h5`).  And `N_bg = 96` in the
JSON deck is **not used**: `dim_bg` is hard-coded to `{80,80,128}` in
`src/main_av.cpp`, so the background resolution is a rebuild-level parameter, not
a configuration one.

The solid mesh is finer than the fluid grid (edge 0.07 versus spacing 0.10), so
each fluid cell carries roughly two to three solid cells — a normal IB ratio, but
it also means the two resolutions are changed independently.

### 12.3 Commands of the 2026-09-15 production run

The original two-step recipe is unchanged (config generator, then the printed
command); only the environment wrapper is added in front of it:

```bash
cd cmame-v100-2/build
python3 ../demos/demo_3392.py                 # writes config/test10.json
taskset -c 10 nohup ./gfem_main_av config/test10.json > log/gfem-10.out &
```

with `Nt = 327,000`, `T = 1.635`, so `Δt = 5e-6`, `beta = 5e8`, `kappa = 5e6`,
`muf = 0.04`, `rhof = 1`, and the real inputs
`mesh_connected_scale.xdmf` / `boundaries_connected.xml` /
`materials_connected.xml` / `fibers_{0,1,2}_connected.xml`.

The prescribed inlet waveform is the original `ibamr/pressure.txt` (328 samples at
`Δt = 0.005 s`).  The code confirms it: the first computed
`pressure_atrim = 19,133.27 Pa = 14.3511 mmHg` reproduces the first file value
`14.3511332141801` exactly after the internal `×1333.22368421` conversion.

### 12.4 Status of the run

<p class="tcaption">Table 12. AV in the npuheart/gfem code, completed 2026-09-15 22:36.</p>

| Quantity | Value |
|---|---|
| started / finished | 16:54 → 22:36, **5 h 42 min** |
| progress | **327,000 / 327,000 steps completed**, t = 1.635 s (two full cycles) |
| rate | ≈ 16 steps/s (0.062 s per coupled step) |
| GPU | 1 × RTX 4090, 2.6 GB / 24 GB, 99 % utilisation |
| errors | **0** NaN / CUDA failures in the whole log |
| inlet pressure | 5,695–164,777 Pa (4.3–123.6 mmHg) over the two cycles |
| axial flow rate | −485 to +538 (arbitrary units), 0.66 at the last step |
| output | 327 × `fluid*.vti` (65 MB each) + `solid/view.h5`, ≈ 24 GB |

At roughly 0.062 s per coupled step this is the same order as the AV-1 Stokes run
in §1, on a mesh three times larger than the reduced one — the cost is dominated
by the fluid solve, not by the solid assembly.




The two curves below are drawn from the numbers written directly in this page —
there is no image to regenerate and re-upload.  The CSV block under each figure
*is* the data: the `chart` shortcode parses it and Chart.js draws it (self-hosted,
theme-aware, hover for values).

{{< chart height="300" xlabel="t (s)" ylabel="pressure (mmHg)" caption="Figure 12. AV in the npuheart/gfem code: prescribed inflow pressure and Windkessel outflow pressure over the two cardiac cycles, in mmHg." >}}
t, inflow (mmHg), outflow (mmHg)
0.0000, 14.351, 85.000
0.0082, 14.957, 85.000
0.0163, 17.021, 85.000
0.0245, 21.663, 85.000
0.0327, 29.285, 85.000
0.0409, 39.525, 85.000
0.0491, 50.939, 85.000
0.0572, 62.185, 85.000
0.0654, 72.188, 85.000
0.0736, 80.270, 85.000
0.0818, 85.782, 86.146
0.0899, 89.915, 86.810
0.0981, 93.955, 87.082
0.1063, 98.136, 87.612
0.1145, 102.431, 88.623
0.1226, 106.637, 89.680
0.1308, 110.475, 91.297
0.1390, 113.628, 93.207
0.1472, 116.050, 95.630
0.1553, 117.936, 98.126
0.1635, 119.403, 100.660
0.1717, 120.583, 103.399
0.1799, 121.542, 106.033
0.1880, 122.318, 108.653
0.1962, 122.931, 111.150
0.2044, 123.356, 113.523
0.2126, 123.562, 115.788
0.2207, 123.556, 117.825
0.2289, 123.324, 119.716
0.2371, 122.888, 121.425
0.2453, 122.269, 122.907
0.2534, 121.464, 124.184
0.2616, 120.509, 125.182
0.2698, 119.414, 125.905
0.2780, 118.145, 126.379
0.2861, 116.715, 126.551
0.2943, 115.128, 126.469
0.3025, 113.399, 126.110
0.3107, 111.568, 125.478
0.3188, 109.654, 124.629
0.3270, 107.653, 123.460
0.3352, 105.476, 122.077
0.3434, 102.952, 120.434
0.3515, 99.974, 118.531
0.3597, 96.315, 116.414
0.3679, 91.398, 115.260
0.3761, 84.988, 114.484
0.3842, 77.143, 113.690
0.3924, 67.904, 112.877
0.4006, 57.138, 112.045
0.4088, 45.969, 111.193
0.4169, 36.085, 110.346
0.4251, 27.848, 109.511
0.4333, 21.573, 108.691
0.4415, 16.948, 107.889
0.4496, 13.509, 107.101
0.4578, 10.626, 106.323
0.4660, 8.239, 105.552
0.4742, 6.554, 104.792
0.4823, 5.583, 104.043
0.4905, 5.045, 102.634
0.4987, 4.702, 92.110
0.5069, 4.435, 84.356
0.5150, 4.281, 92.601
0.5232, 4.304, 98.510
0.5314, 4.453, 94.132
0.5396, 4.676, 97.373
0.5477, 4.906, 94.602
0.5559, 5.098, 95.122
0.5641, 5.255, 94.259
0.5723, 5.406, 93.864
0.5804, 5.575, 92.931
0.5886, 5.787, 93.084
0.5968, 6.043, 91.597
0.6050, 6.336, 91.975
0.6131, 6.667, 90.862
0.6213, 7.026, 90.450
0.6295, 7.405, 90.244
0.6377, 7.792, 89.110
0.6458, 8.178, 89.235
0.6540, 8.551, 88.217
0.6622, 8.898, 87.910
0.6704, 9.215, 87.422
0.6785, 9.500, 86.773
0.6867, 9.764, 86.423
0.6949, 10.014, 85.850
0.7031, 10.258, 85.294
0.7112, 10.504, 85.055
0.7194, 10.758, 84.980
0.7276, 11.026, 84.981
0.7358, 11.312, 85.087
0.7439, 11.622, 84.942
0.7521, 11.961, 85.065
0.7603, 12.322, 85.018
0.7685, 12.702, 84.967
0.7766, 13.093, 85.082
0.7848, 13.490, 84.949
0.7930, 13.885, 85.048
0.8012, 14.274, 85.018
0.8093, 14.649, 84.989
0.8175, 14.624, 85.046
0.8257, 14.667, 84.974
0.8339, 16.132, 85.070
0.8420, 19.997, 85.086
0.8502, 26.557, 85.148
0.8584, 36.194, 85.220
0.8666, 47.422, 85.220
0.8747, 58.925, 85.220
0.8829, 69.242, 85.220
0.8911, 78.091, 85.220
0.8993, 84.343, 85.220
0.9074, 88.703, 85.220
0.9156, 92.701, 85.220
0.9238, 96.842, 85.220
0.9320, 101.111, 85.220
0.9401, 105.388, 89.854
0.9483, 109.355, 91.437
0.9565, 112.740, 93.378
0.9647, 115.394, 95.592
0.9728, 117.398, 98.035
0.9810, 118.989, 100.608
0.9892, 120.253, 103.186
0.9974, 121.263, 105.713
1.0060, 122.100, 108.179
1.0140, 122.763, 110.562
1.0220, 123.243, 112.874
1.0300, 123.531, 115.078
1.0380, 123.579, 117.123
1.0460, 123.416, 118.990
1.0550, 123.047, 120.667
1.0630, 122.473, 122.146
1.0710, 121.728, 123.395
1.0790, 120.818, 124.413
1.0870, 119.761, 125.200
1.0950, 118.555, 125.746
1.1040, 117.170, 126.021
1.1120, 115.626, 126.033
1.1200, 113.945, 125.774
1.1280, 112.136, 125.255
1.1360, 110.245, 124.464
1.1450, 108.283, 123.419
1.1530, 106.161, 122.117
1.1610, 103.768, 120.554
1.1690, 100.952, 118.709
1.1770, 97.505, 116.575
1.1850, 93.091, 114.084
1.1940, 87.110, 111.156
1.2020, 79.652, 107.705
1.2100, 70.966, 103.773
1.2180, 60.544, 99.749
1.2260, 49.308, 95.810
1.2340, 38.893, 94.717
1.2430, 30.229, 107.428
1.2510, 23.290, 102.203
1.2590, 18.191, 101.858
1.2670, 14.494, 103.114
1.2750, 11.449, 100.598
1.2830, 8.906, 101.463
1.2920, 6.997, 100.375
1.3000, 5.802, 99.608
1.3080, 5.183, 99.442
1.3160, 4.800, 98.673
1.3240, 4.504, 97.909
1.3330, 4.318, 97.887
1.3410, 4.279, 96.546
1.3490, 4.396, 96.712
1.3570, 4.604, 95.678
1.3650, 4.840, 95.243
1.3730, 5.044, 94.857
1.3820, 5.209, 93.947
1.3900, 5.359, 93.790
1.3980, 5.521, 92.971
1.4060, 5.718, 92.519
1.4140, 5.959, 92.022
1.4220, 6.244, 91.372
1.4310, 6.562, 90.937
1.4390, 6.914, 90.410
1.4470, 7.288, 89.797
1.4550, 7.674, 89.398
1.4630, 8.061, 88.781
1.4720, 8.439, 88.270
1.4800, 8.796, 87.844
1.4880, 9.121, 87.176
1.4960, 9.416, 86.823
1.5040, 9.685, 86.244
1.5120, 9.938, 85.708
1.5210, 10.183, 85.315
1.5290, 10.428, 84.959
1.5370, 10.679, 85.057
1.5450, 10.941, 85.043
1.5530, 11.222, 84.984
1.5610, 11.525, 85.083
1.5700, 11.854, 84.999
1.5780, 12.210, 85.034
1.5860, 12.584, 85.051
1.5940, 12.973, 85.001
1.6020, 13.368, 85.052
1.6100, 13.765, 85.027
1.6190, 14.156, 85.023
1.6270, 14.536, 85.040
1.6350, 14.680, 85.021
{{< /chart >}}

{{< chart height="250" xlabel="t (s)" ylabel="flow rate" caption="Figure 13. AV: axial flow rate on the two faces of the background grid, in the case's cm-g-s units (mL/s); Figure 15 puts the same curve next to the fdm one. The closing transients are the negative spikes at t ≈ 0.51 s and 1.23 s." >}}
t, flow rate
0.0000, -0.000
0.0082, -209.328
0.0163, 170.281
0.0245, 14.631
0.0327, -102.914
0.0409, 73.976
0.0491, 62.426
0.0572, -2.891
0.0654, -41.662
0.0736, -4.220
0.0818, 36.940
0.0899, 65.281
0.0981, 78.211
0.1063, 97.385
0.1145, 127.273
0.1226, 154.333
0.1308, 194.047
0.1390, 236.649
0.1472, 288.357
0.1553, 335.345
0.1635, 377.313
0.1717, 419.812
0.1799, 453.855
0.1880, 483.239
0.1962, 505.622
0.2044, 521.814
0.2126, 533.192
0.2207, 536.940
0.2289, 536.293
0.2371, 530.965
0.2453, 520.174
0.2534, 505.341
0.2616, 484.845
0.2698, 459.557
0.2780, 430.825
0.2861, 397.581
0.2943, 361.715
0.3025, 322.960
0.3107, 281.728
0.3188, 239.909
0.3270, 194.658
0.3352, 149.399
0.3434, 102.745
0.3515, 54.859
0.3597, 7.191
0.3679, -6.457
0.3761, -8.308
0.3842, -10.552
0.3924, -13.144
0.4006, -16.046
0.4088, -19.249
0.4169, -22.027
0.4251, -24.217
0.4333, -25.806
0.4415, -26.842
0.4496, -27.436
0.4578, -27.810
0.4660, -28.077
0.4742, -28.113
0.4823, -27.963
0.4905, -48.094
0.4987, -321.067
0.5069, -479.217
0.5150, -155.230
0.5232, 35.653
0.5314, -74.044
0.5396, 41.828
0.5477, -25.764
0.5559, 8.525
0.5641, -1.139
0.5723, 3.320
0.5804, -7.340
0.5886, 13.171
0.5968, -15.464
0.6050, 13.173
0.6131, -5.677
0.6213, -0.368
0.6295, 8.151
0.6377, -9.462
0.6458, 10.124
0.6540, -5.370
0.6622, 1.662
0.6704, 2.000
0.6785, -1.910
0.6867, 2.944
0.6949, 0.756
0.7031, -0.736
0.7112, 1.702
0.7194, -0.584
0.7276, -0.554
0.7358, 2.665
0.7439, -1.730
0.7521, 1.999
0.7603, 0.552
0.7685, -0.987
0.7766, 2.507
0.7848, -1.517
0.7930, 1.483
0.8012, 0.560
0.8093, -0.320
0.8175, 1.401
0.8257, -0.778
0.8339, 2.152
0.8420, 2.629
0.8502, 4.493
0.8584, 8.231
0.8666, 10.893
0.8747, 13.931
0.8829, 18.892
0.8911, 25.864
0.8993, 33.342
0.9074, 41.123
0.9156, 53.771
0.9238, 75.703
0.9320, 109.067
0.9401, 144.758
0.9483, 184.762
0.9565, 229.599
0.9647, 276.346
0.9728, 323.490
0.9810, 368.191
0.9892, 407.306
0.9974, 440.019
1.0060, 466.960
1.0140, 488.265
1.0220, 505.038
1.0300, 516.826
1.0380, 522.852
1.0460, 523.383
1.0550, 518.762
1.0630, 509.456
1.0710, 495.169
1.0790, 476.541
1.0870, 454.094
1.0950, 428.043
1.1040, 397.974
1.1120, 364.643
1.1200, 328.232
1.1280, 289.423
1.1360, 248.181
1.1450, 205.254
1.1530, 160.812
1.1610, 114.831
1.1690, 66.939
1.1770, 17.113
1.1850, -36.323
1.1940, -95.253
1.2020, -161.369
1.2100, -232.559
1.2180, -296.971
1.2260, -351.093
1.2340, -314.752
1.2430, 98.950
1.2510, -45.177
1.2590, -27.494
1.2670, 24.622
1.2750, -31.480
1.2830, 14.132
1.2920, -2.065
1.3000, -6.405
1.3080, 6.325
1.3160, -0.108
1.3240, -4.494
1.3330, 11.191
1.3410, -11.615
1.3490, 10.847
1.3570, -4.175
1.3650, 0.668
1.3730, 4.895
1.3820, -5.310
1.3900, 6.533
1.3980, -1.966
1.4060, 1.254
1.4140, 2.215
1.4220, -1.081
1.4310, 2.021
1.4390, 1.897
1.4470, -0.496
1.4550, 3.246
1.4630, 0.168
1.4720, 0.672
1.4800, 3.073
1.4880, -1.532
1.4960, 3.267
1.5040, 0.814
1.5120, 0.085
1.5210, 3.156
1.5290, -1.217
1.5370, 1.758
1.5450, 1.320
1.5530, -0.468
1.5610, 2.544
1.5700, -0.029
1.5780, 1.039
1.5860, 1.573
1.5940, 0.057
1.6020, 1.585
1.6100, 0.835
1.6190, 0.715
1.6270, 1.228
1.6350, 0.665
{{< /chart >}}

### 12.4.1 The same quantities from the fdm run, for comparison

§1's figures are the fdm-3d-v1-gpu run, and they exist only as matplotlib PNGs
there, so the two codes could never be read against each other curve by curve.
Figures 14–18 put both runs on the same axes, from data written in this page:

- **fdm pressure and solid diagnostics** — the 328 rows of
  `out_av_fiber_mny_full/sim.log`;
- **fdm flow rate** — rebuilt from the 328 saved `fluid_*.vti` frames, because the
  fdm solver does not log one: the area integral of the axial velocity over the
  tube's two end planes, `Q = -Σ w Δx Δy`; the two planes agree with each other to
  0.003 %, and the reconstruction is the one checked against §1's Figure 2(b);
- **gfem pressure and flow rate** — the run log, sampled on the saved-frame grid
  (the same integral over the gfem frames reproduces that solver's own logged
  flow rate to 0.5 %);
- **gfem solid diagnostics** — max over the P1 nodes of every saved
  `solid/view.h5` frame (327 frames, `_displacement` and `_force`);
- **gfem divergence** — computed here from the saved frames, because the gfem
  solver never logs one.

The extraction scripts live next to the code, in
`cmame-v100-2/tools/chart_data.py` (figures 12–13) and
`cmame-v100-2/tools/{fdm_av_series,fdm_av_flow,gfem_log_series,gfem_solid_series,gfem_div_series,av_chart_blocks}.py`
(figures 14–18), so each figure can be regenerated from the run outputs alone.

{{< chart xlabel="t (s)" ylabel="pressure (mmHg)" caption="Figure 14. Inlet and outlet pressure, both codes, over the two cycles. The inlet pair is the same prescribed waveform (fdm `av_pressure.inlet`, gfem `ibamr/pressure.txt`; the two agree to 0.68 mmHg), so the outlet pair is the comparison: the same 85 mmHg baseline and the same peak time (t = 0.29 s), with fdm spanning 75.6-129.3 mmHg against gfem's 83.7-126.6 (rms difference 3.9 mmHg). The largest gap is 21.2 mmHg at t = 0.51 s: at that frame the gfem Windkessel has dropped to 83.7 mmHg while the fdm one is still at 104.8." >}}
t, fdm inlet, fdm outlet, gfem inlet, gfem outlet
0.0000, 14.351, 85.000, 14.351, 85.000
0.0100, 15.167, 75.604, 15.167, 85.000
0.0200, 18.643, 85.943, 18.641, 85.000
0.0300, 26.333, 84.810, 26.329, 85.000
0.0400, 38.305, 79.446, 38.299, 85.000
0.0500, 52.269, 80.133, 52.269, 85.000
0.0600, 65.763, 83.105, 65.763, 85.000
0.0700, 77.150, 82.663, 77.150, 85.000
0.0800, 84.840, 82.108, 84.836, 85.000
0.0900, 89.949, 82.498, 89.946, 86.817
0.1000, 94.905, 83.325, 94.903, 87.123
0.1100, 100.079, 84.484, 100.053, 88.043
0.1200, 105.323, 86.127, 105.297, 89.364
0.1300, 110.142, 88.278, 110.118, 91.094
0.1400, 113.991, 91.329, 113.973, 93.457
0.1500, 116.778, 94.955, 116.765, 96.461
0.1600, 118.823, 98.572, 118.813, 99.557
0.1700, 120.371, 102.257, 120.363, 102.804
0.1800, 121.558, 105.886, 121.552, 106.063
0.1900, 122.489, 109.580, 122.485, 109.238
0.2000, 123.159, 113.076, 123.156, 112.263
0.2100, 123.530, 116.314, 123.529, 115.058
0.2200, 123.571, 119.336, 123.571, 117.638
0.2300, 123.284, 121.999, 123.286, 119.941
0.2400, 122.694, 124.324, 122.698, 121.990
0.2500, 121.826, 126.232, 121.831, 123.666
0.2600, 120.714, 127.728, 120.720, 125.003
0.2700, 119.384, 128.655, 119.391, 125.917
0.2800, 117.810, 129.237, 117.818, 126.457
0.2900, 115.987, 129.245, 115.995, 126.550
0.3000, 113.941, 128.817, 113.950, 126.253
0.3100, 111.720, 127.813, 111.730, 125.544
0.3200, 109.377, 126.520, 109.387, 124.483
0.3300, 106.891, 125.092, 106.902, 122.982
0.3400, 104.047, 123.283, 104.061, 121.148
0.3500, 100.600, 121.430, 100.616, 118.912
0.3600, 96.175, 119.154, 96.196, 116.347
0.3700, 89.962, 116.454, 89.993, 115.066
0.3800, 81.388, 113.612, 81.429, 114.107
0.3900, 70.861, 112.002, 70.911, 113.123
0.4000, 57.945, 114.617, 58.006, 112.110
0.4100, 44.306, 112.788, 44.366, 111.068
0.4200, 32.725, 110.919, 32.775, 110.035
0.4300, 23.825, 111.819, 23.862, 109.022
0.4400, 17.610, 109.718, 17.635, 108.035
0.4500, 13.363, 109.770, 13.381, 107.070
0.4600, 9.904, 108.582, 9.919, 106.119
0.4700, 7.291, 107.883, 7.302, 105.181
0.4800, 5.781, 107.271, 5.786, 104.260
0.4900, 5.067, 106.376, 5.070, 103.355
0.5000, 4.650, 105.676, 4.652, 90.626
0.5100, 4.356, 104.806, 4.357, 83.652
0.5200, 4.271, 104.128, 4.272, 100.452
0.5300, 4.418, 103.300, 4.417, 94.273
0.5400, 4.689, 102.663, 4.688, 97.286
0.5500, 4.966, 101.851, 4.965, 94.521
0.5600, 5.180, 101.159, 5.179, 94.665
0.5700, 5.363, 100.422, 5.363, 94.095
0.5800, 5.565, 99.681, 5.564, 92.927
0.5900, 5.826, 98.994, 5.825, 92.959
0.6000, 6.153, 98.245, 6.151, 91.495
0.6100, 6.536, 97.539, 6.534, 91.602
0.6200, 6.966, 96.860, 6.964, 90.337
0.6300, 7.429, 96.167, 7.427, 90.161
0.6400, 7.904, 95.456, 7.902, 89.135
0.6500, 8.371, 94.808, 8.369, 88.793
0.6600, 8.810, 94.113, 8.808, 87.941
0.6700, 9.203, 93.413, 9.201, 87.463
0.6800, 9.550, 92.762, 9.548, 86.696
0.6900, 9.866, 92.091, 9.865, 86.194
0.7000, 10.167, 91.403, 10.165, 85.494
0.7100, 10.466, 90.787, 10.465, 85.034
0.7200, 10.776, 90.089, 10.775, 84.971
0.7300, 11.107, 89.465, 11.106, 85.026
0.7400, 11.469, 88.828, 11.467, 85.016
0.7500, 11.870, 88.184, 11.868, 85.003
0.7600, 12.309, 87.557, 12.307, 85.025
0.7700, 12.775, 86.925, 12.772, 85.001
0.7800, 13.256, 86.308, 13.254, 85.041
0.7900, 13.742, 85.682, 13.739, 84.998
0.8000, 14.220, 85.072, 14.218, 85.036
0.8100, 14.680, 84.982, 14.677, 84.995
0.8200, 14.351, 84.974, 14.357, 85.020
0.8300, 15.167, 85.014, 15.162, 85.018
0.8400, 18.643, 85.095, 18.621, 85.091
0.8500, 26.333, 85.216, 26.290, 85.145
0.8600, 38.305, 85.099, 38.240, 85.220
0.8700, 52.269, 84.730, 52.199, 85.220
0.8800, 65.763, 84.386, 65.699, 85.220
0.8900, 77.150, 84.151, 77.096, 85.220
0.9000, 84.840, 84.129, 84.806, 85.220
0.9100, 89.949, 84.308, 89.924, 85.220
0.9200, 94.905, 84.780, 94.880, 85.220
0.9300, 100.079, 85.691, 100.053, 85.220
0.9400, 105.323, 87.125, 105.297, 89.823
0.9500, 110.142, 89.064, 110.118, 91.803
0.9600, 113.991, 91.553, 113.973, 94.281
0.9700, 116.778, 94.792, 116.765, 97.153
0.9800, 118.823, 98.273, 118.813, 100.274
0.9900, 120.371, 101.873, 120.363, 103.427
1.0000, 121.558, 105.452, 121.552, 106.509
1.0100, 122.489, 108.972, 122.446, 109.352
1.0200, 123.159, 112.377, 123.129, 112.215
1.0300, 123.530, 115.606, 123.515, 114.934
1.0400, 123.571, 118.582, 123.573, 117.423
1.0500, 123.284, 121.271, 123.303, 119.647
1.0600, 122.694, 123.614, 122.728, 121.584
1.0700, 121.826, 125.519, 121.873, 123.194
1.0800, 120.714, 127.005, 120.772, 124.457
1.0900, 119.384, 128.048, 119.453, 125.374
1.1000, 117.810, 128.614, 117.892, 125.917
1.1100, 115.987, 128.702, 116.081, 126.057
1.1200, 113.941, 128.317, 114.046, 125.796
1.1300, 111.720, 127.609, 111.833, 125.143
1.1400, 109.377, 126.281, 109.495, 124.091
1.1500, 106.891, 124.851, 107.018, 122.655
1.1600, 104.047, 122.965, 104.195, 120.832
1.1700, 100.600, 121.008, 100.781, 118.595
1.1800, 96.175, 118.878, 96.413, 115.914
1.1900, 89.962, 116.128, 90.301, 112.672
1.2000, 81.388, 112.672, 81.844, 108.698
1.2100, 70.861, 108.786, 71.412, 103.977
1.2200, 57.945, 104.540, 58.622, 99.098
1.2300, 44.306, 100.171, 44.974, 94.427
1.2400, 32.725, 104.843, 33.272, 105.202
1.2500, 23.825, 111.283, 24.236, 103.054
1.2600, 17.610, 102.982, 17.888, 102.260
1.2700, 13.363, 106.129, 13.560, 102.064
1.2800, 9.904, 105.571, 10.068, 101.023
1.2900, 7.291, 102.101, 7.409, 100.706
1.3000, 5.781, 104.742, 5.843, 99.622
1.3100, 5.067, 101.514, 5.096, 99.355
1.3200, 4.650, 102.091, 4.670, 98.107
1.3300, 4.356, 101.038, 4.368, 98.130
1.3400, 4.271, 99.847, 4.272, 96.643
1.3500, 4.418, 100.093, 4.408, 96.695
1.3600, 4.689, 98.376, 4.675, 95.357
1.3700, 4.966, 98.474, 4.953, 95.284
1.3800, 5.180, 97.266, 5.170, 94.067
1.3900, 5.363, 96.730, 5.354, 93.804
1.4000, 5.565, 96.092, 5.554, 92.831
1.4100, 5.826, 95.194, 5.812, 92.404
1.4200, 6.153, 94.753, 6.136, 91.592
1.4300, 6.536, 93.882, 6.516, 90.998
1.4400, 6.966, 93.290, 6.944, 90.346
1.4500, 7.429, 92.677, 7.406, 89.672
1.4600, 7.904, 91.915, 7.880, 89.102
1.4700, 8.371, 91.384, 8.348, 88.349
1.4800, 8.810, 90.549, 8.789, 87.858
1.4900, 9.203, 89.993, 9.184, 87.082
1.5000, 9.550, 89.303, 9.533, 86.618
1.5100, 9.866, 88.666, 9.851, 85.839
1.5200, 10.167, 88.109, 10.152, 85.384
1.5300, 10.466, 87.346, 10.451, 84.956
1.5400, 10.776, 86.773, 10.761, 85.093
1.5500, 11.107, 86.120, 11.091, 84.975
1.5600, 11.469, 85.529, 11.450, 85.075
1.5700, 11.870, 85.036, 11.849, 84.999
1.5800, 12.309, 84.948, 12.287, 85.054
1.5900, 12.775, 85.032, 12.751, 85.018
1.6000, 13.256, 84.996, 13.232, 85.038
1.6100, 13.742, 84.968, 13.717, 85.033
1.6200, 14.220, 85.018, 14.196, 85.026
1.6300, 14.680, 84.989, 14.657, 85.035
{{< /chart >}}

{{< chart xlabel="t (s)" ylabel="Q (mL/s)" caption="Figure 15. Axial flow rate, both codes, on one definition: the area integral of the axial velocity over a z plane, Q = -sum(w) dx dy, positive during ejection - which is what each solver's Windkessel probe uses. The fdm curve is rebuilt here from its 328 saved frames (the tube's two end planes agree to 0.003 %); applying the same integral to the gfem frames reproduces that solver's own logged flow rate to 0.5 %. Both codes put the two ejection peaks in the same frames (t = 0.220/0.225 s and 1.045 s) at 608 vs 538 and 588 vs 524 mL/s, and differ in the closing transient: fdm reaches -297 mL/s at t = 1.23 s, gfem -468 mL/s at t = 0.51 s." >}}
t, fdm (from VTI), gfem (from log)
0.0000, -0.0, -0.0
0.0050, -113.6, -139.3
0.0100, -243.7, -226.6
0.0150, -207.0, 124.1
0.0200, 113.1, 119.7
0.0250, 169.5, 5.8
0.0300, 70.9, -78.5
0.0350, -3.6, -101.9
0.0400, -72.3, 51.6
0.0450, -87.5, 86.4
0.0500, -21.2, 55.9
0.0550, 59.9, 18.6
0.0600, 78.4, -24.3
0.0650, 73.1, -42.1
0.0700, 69.7, -27.2
0.0750, 61.1, 5.0
0.0800, 59.7, 32.4
0.0850, 67.9, 44.8
0.0900, 77.3, 65.6
0.0950, 87.6, 75.6
0.1000, 104.4, 80.4
0.1050, 119.8, 92.0
0.1100, 136.3, 110.6
0.1150, 158.0, 129.2
0.1200, 176.6, 146.8
0.1250, 198.3, 163.9
0.1300, 225.0, 189.1
0.1350, 257.2, 216.3
0.1400, 290.7, 242.0
0.1450, 326.9, 274.3
0.1500, 362.1, 304.5
0.1550, 393.2, 333.2
0.1600, 422.2, 359.7
0.1650, 446.9, 384.9
0.1700, 474.9, 410.8
0.1750, 498.8, 434.6
0.1800, 518.1, 454.2
0.1850, 538.9, 473.7
0.1900, 556.6, 488.7
0.1950, 570.8, 502.5
0.2000, 583.9, 514.1
0.2050, 594.2, 522.7
0.2100, 600.2, 529.5
0.2150, 605.6, 534.4
0.2200, 608.4, 536.8
0.2250, 607.5, 537.6
0.2300, 605.9, 535.8
0.2350, 602.3, 532.5
0.2400, 594.8, 528.3
0.2450, 586.6, 520.6
0.2500, 574.4, 512.1
0.2550, 561.5, 501.7
0.2600, 546.3, 489.4
0.2650, 528.6, 475.2
0.2700, 507.3, 459.0
0.2750, 485.5, 441.6
0.2800, 465.6, 423.4
0.2850, 439.9, 402.6
0.2900, 414.7, 381.3
0.2950, 387.6, 358.7
0.3000, 360.2, 335.3
0.3050, 328.1, 310.9
0.3100, 298.6, 285.4
0.3150, 268.6, 259.9
0.3200, 238.8, 233.8
0.3250, 210.6, 206.2
0.3300, 185.0, 178.2
0.3350, 156.4, 150.7
0.3400, 129.1, 122.3
0.3450, 103.6, 93.4
0.3500, 80.9, 64.0
0.3550, 54.0, 35.0
0.3600, 28.6, 5.8
0.3650, 4.9, -5.7
0.3700, -27.4, -6.9
0.3750, -57.9, -8.0
0.3800, -78.6, -9.4
0.3850, -95.3, -10.8
0.3900, -85.9, -12.3
0.3950, -32.1, -14.0
0.4000, 23.8, -15.8
0.4050, 26.1, -17.8
0.4100, -10.3, -19.7
0.4150, -42.6, -21.4
0.4200, -35.8, -22.9
0.4250, 5.8, -24.2
0.4300, 16.2, -25.2
0.4350, -5.5, -26.0
0.4400, -22.5, -26.7
0.4450, -12.4, -27.2
0.4500, 5.2, -27.5
0.4550, 5.9, -27.7
0.4600, -7.6, -27.9
0.4650, -11.6, -28.0
0.4700, -3.4, -28.1
0.4750, 4.2, -28.1
0.4800, 1.3, -28.0
0.4850, -6.8, -27.9
0.4900, -1.6, -27.7
0.4950, 3.1, -208.2
0.5000, 0.1, -355.7
0.5050, -4.3, -458.2
0.5100, -2.6, -467.8
0.5150, 3.0, -161.9
0.5200, -0.4, 91.5
0.5250, -3.8, -4.1
0.5300, -2.5, -74.7
0.5350, 1.5, -6.6
0.5400, 0.8, 39.8
0.5450, -0.3, -9.6
0.5500, -1.4, -22.6
0.5550, -0.9, 6.8
0.5600, 0.1, 2.6
0.5650, -0.0, -0.7
0.5700, -0.3, 5.8
0.5750, -0.4, -4.3
0.5800, -0.6, -8.5
0.5850, -0.1, 7.7
0.5900, 0.3, 11.8
0.5950, -0.7, -9.0
0.6000, -0.8, -11.3
0.6050, 0.5, 13.2
0.6100, -0.7, 10.5
0.6150, -0.5, -12.8
0.6200, 0.0, -6.6
0.6250, -0.2, 11.7
0.6300, 0.1, 6.5
0.6350, 0.4, -9.5
0.6400, -0.4, -3.9
0.6450, 0.1, 9.3
0.6500, 0.8, 4.1
0.6550, -0.0, -6.2
0.6600, 0.4, -1.7
0.6650, 0.5, 4.5
0.6700, -0.3, 2.5
0.6750, -0.0, -1.7
0.6800, 0.4, -1.5
0.6850, 0.4, 2.1
0.6900, 0.3, 2.0
0.6950, -0.1, 0.7
0.7000, -0.5, -0.5
0.7050, 0.3, -0.3
0.7100, 0.8, 1.1
0.7150, 0.5, 2.6
0.7200, -0.6, -0.9
0.7250, -0.2, -1.5
0.7300, 0.2, 0.8
0.7350, 0.1, 2.9
0.7400, 0.4, 0.5
0.7450, -0.3, -2.1
0.7500, 0.3, 0.1
0.7550, 0.7, 3.1
0.7600, 0.4, 0.8
0.7650, -0.0, -2.0
0.7700, 0.4, 0.1
0.7750, 0.3, 2.6
0.7800, 0.6, 1.2
0.7850, 0.4, -1.5
0.7900, 0.4, -0.0
0.7950, 0.3, 2.0
0.8000, 0.6, 1.1
0.8050, 0.1, -0.9
0.8100, -0.5, -0.1
0.8150, -0.7, 1.2
0.8200, -0.8, 0.6
0.8250, -0.7, -0.8
0.8300, 0.4, 0.6
0.8350, 1.6, 2.5
0.8400, 2.9, 2.8
0.8450, 4.8, 3.0
0.8500, 6.6, 4.4
0.8550, 8.7, 6.7
0.8600, 11.4, 8.8
0.8650, 14.2, 10.5
0.8700, 16.3, 11.8
0.8750, 18.6, 14.1
0.8800, 21.1, 16.9
0.8850, 23.7, 20.5
0.8900, 28.1, 24.8
0.8950, 33.6, 29.6
0.9000, 39.8, 34.0
0.9050, 46.9, 38.5
0.9100, 55.2, 44.3
0.9150, 64.5, 52.5
0.9200, 76.3, 63.7
0.9250, 90.6, 79.9
0.9300, 106.2, 99.9
0.9350, 124.9, 124.0
0.9400, 146.0, 143.9
0.9450, 169.6, 167.5
0.9500, 193.5, 193.5
0.9550, 219.4, 221.1
0.9600, 249.0, 249.1
0.9650, 281.5, 278.1
0.9700, 316.7, 307.0
0.9750, 349.2, 335.5
0.9800, 380.3, 362.7
0.9850, 410.6, 387.8
0.9900, 437.5, 410.7
0.9950, 461.6, 431.1
1.0000, 485.3, 449.4
1.0050, 505.8, 463.9
1.0100, 524.2, 478.1
1.0150, 540.7, 490.1
1.0200, 554.3, 500.8
1.0250, 564.9, 509.4
1.0300, 575.1, 516.2
1.0350, 582.3, 520.9
1.0400, 586.0, 523.2
1.0450, 588.2, 523.7
1.0500, 587.8, 522.2
1.0550, 585.2, 518.8
1.0600, 580.1, 513.8
1.0650, 572.3, 506.8
1.0700, 561.9, 498.0
1.0750, 549.8, 487.4
1.0800, 535.5, 475.6
1.0850, 519.8, 462.1
1.0900, 501.4, 447.4
1.0950, 481.7, 431.3
1.1000, 459.9, 413.6
1.1050, 436.8, 394.6
1.1100, 411.9, 374.4
1.1150, 385.0, 352.9
1.1200, 358.9, 330.4
1.1250, 332.6, 307.0
1.1300, 305.7, 282.8
1.1350, 273.3, 257.6
1.1400, 243.8, 231.8
1.1450, 216.8, 205.3
1.1500, 188.8, 178.3
1.1550, 158.7, 150.7
1.1600, 130.2, 122.6
1.1650, 104.2, 93.7
1.1700, 78.7, 64.2
1.1750, 54.5, 34.0
1.1800, 30.5, 2.5
1.1850, 0.1, -30.3
1.1900, -27.6, -65.1
1.1950, -60.8, -102.5
1.2000, -96.2, -142.7
1.2050, -130.2, -185.2
1.2100, -166.1, -229.0
1.2150, -199.6, -271.4
1.2200, -235.3, -305.9
1.2250, -271.8, -339.3
1.2300, -296.7, -365.2
1.2350, -279.4, -312.6
1.2400, -87.5, 29.2
1.2450, 133.1, 74.8
1.2500, 114.0, -23.1
1.2550, -2.2, -82.6
1.2600, -113.0, -13.9
1.2650, -105.7, 47.6
1.2700, 20.1, -2.3
1.2750, 76.1, -31.5
1.2800, 16.3, -7.7
1.2850, -55.0, 15.6
1.2900, -58.2, 3.2
1.2950, 13.3, -6.7
1.3000, 43.1, -6.7
1.3050, 6.7, 2.5
1.3100, -33.0, 6.8
1.3150, -28.1, 4.5
1.3200, 10.8, -9.8
1.3250, 25.8, -3.9
1.3300, -2.0, 12.8
1.3350, -25.3, 4.5
1.3400, -12.8, -11.5
1.3450, 10.5, -1.8
1.3500, 15.0, 11.5
1.3550, -3.9, 3.1
1.3600, -14.9, -8.5
1.3650, -5.2, -1.6
1.3700, 10.7, 10.3
1.3750, 7.5, 1.9
1.3800, -5.6, -6.2
1.3850, -12.1, -0.6
1.3900, 0.7, 6.5
1.3950, 9.7, 2.2
1.4000, 1.7, -2.9
1.4050, -7.4, -0.7
1.4100, -3.9, 4.4
1.4150, 1.8, 2.1
1.4200, 3.5, -0.4
1.4250, 3.5, -0.7
1.4300, -2.3, 1.6
1.4350, -2.7, 3.1
1.4400, 0.6, 1.3
1.4450, 3.6, -1.0
1.4500, 2.1, 0.7
1.4550, -1.8, 3.1
1.4600, -0.5, 2.5
1.4650, 1.4, -0.4
1.4700, 3.3, -0.8
1.4750, -1.9, 3.1
1.4800, -2.1, 3.2
1.4850, -1.4, -0.2
1.4900, 0.9, -1.2
1.4950, 1.4, 2.4
1.5000, -0.4, 3.4
1.5050, -0.7, 0.6
1.5100, -0.1, -1.4
1.5150, 0.9, 1.6
1.5200, 2.3, 3.3
1.5250, 0.8, 1.1
1.5300, -1.6, -1.3
1.5350, -0.2, 0.4
1.5400, 0.1, 2.8
1.5450, 0.6, 1.7
1.5500, -0.9, -0.7
1.5550, -1.1, 0.0
1.5600, 0.1, 2.3
1.5650, 0.6, 1.9
1.5700, 1.1, -0.0
1.5750, -0.2, -0.1
1.5800, -1.5, 1.6
1.5850, -1.2, 1.9
1.5900, 1.0, 0.6
1.5950, 0.5, 0.1
1.6000, -0.1, 1.2
1.6050, -0.4, 1.6
1.6100, -1.0, 1.0
1.6150, -0.1, 0.4
1.6200, 0.6, 0.8
1.6250, 0.5, 1.2
1.6300, -0.3, 1.1
1.6350, -0.8, 0.7
{{< /chart >}}

{{< chart xlabel="t (s)" ylabel="max |u| (cm)" caption="Figure 16. Maximum solid displacement, both codes (fdm: 233,216-cell AV mesh, max|u| from `sim.log`; gfem: `mesh_connected_scale`, 683,558 tetrahedra, max|u| over the 178,457 P1 nodes of every saved `solid/view.h5` frame). Both start at zero and reach the same order of deformation: during ejection fdm travels 0.25-0.94 cm against gfem's 0.86-1.03 cm, both hold a 0.27-0.29 cm plateau while the valve is shut, and each peaks at a closure - fdm 1.01 cm at t = 1.22 s, gfem 1.11 cm at t = 0.51 s." >}}
t, fdm max|u| (cm), gfem max|u| (cm)
0.0000, 0.0000, 0.0000
0.0100, 0.2640, 0.2696
0.0200, 0.4000, 0.2018
0.0300, 0.2310, 0.1862
0.0400, 0.1840, 0.2954
0.0500, 0.2820, 0.1691
0.0600, 0.2460, 0.1483
0.0700, 0.1890, 0.1944
0.0800, 0.1310, 0.1866
0.0900, 0.2040, 0.1421
0.1000, 0.3920, 0.1644
0.1100, 0.5350, 0.4250
0.1200, 0.6520, 0.6871
0.1300, 0.7020, 0.8128
0.1400, 0.7220, 0.9017
0.1500, 0.7100, 0.8622
0.1600, 0.7250, 0.8764
0.1700, 0.7320, 0.9750
0.1800, 0.7450, 0.9464
0.1900, 0.7900, 0.9627
0.2000, 0.7910, 0.9559
0.2100, 0.7400, 0.9678
0.2200, 0.7320, 0.9771
0.2300, 0.7390, 0.9785
0.2400, 0.7330, 0.9883
0.2500, 0.7100, 1.0014
0.2600, 0.7080, 0.9980
0.2700, 0.7310, 1.0142
0.2800, 0.7430, 0.9940
0.2900, 0.7500, 1.0046
0.3000, 0.7370, 1.0079
0.3100, 0.7500, 1.0061
0.3200, 0.7420, 1.0139
0.3300, 0.7770, 1.0164
0.3400, 0.8260, 1.0241
0.3500, 0.9060, 1.0288
0.3600, 0.9380, 1.0215
0.3700, 0.9220, 1.0214
0.3800, 0.8340, 0.9703
0.3900, 0.4770, 0.9539
0.4000, 0.2510, 0.9661
0.4100, 0.2280, 0.9681
0.4200, 0.2610, 0.9708
0.4300, 0.2660, 0.9623
0.4400, 0.2660, 0.9599
0.4500, 0.2850, 0.9724
0.4600, 0.2830, 0.9713
0.4700, 0.2870, 0.9955
0.4800, 0.2830, 0.9685
0.4900, 0.2920, 0.9593
0.5000, 0.2810, 1.0564
0.5100, 0.2890, 1.1066
0.5200, 0.2870, 0.3056
0.5300, 0.2870, 0.2595
0.5400, 0.2870, 0.2767
0.5500, 0.2860, 0.2856
0.5600, 0.2890, 0.2915
0.5700, 0.2870, 0.2943
0.5800, 0.2860, 0.2957
0.5900, 0.2870, 0.2959
0.6000, 0.2840, 0.2952
0.6100, 0.2870, 0.2944
0.6200, 0.2860, 0.2928
0.6300, 0.2850, 0.2918
0.6400, 0.2860, 0.2907
0.6500, 0.2850, 0.2906
0.6600, 0.2840, 0.2904
0.6700, 0.2840, 0.2914
0.6800, 0.2850, 0.2925
0.6900, 0.2840, 0.2940
0.7000, 0.2820, 0.2956
0.7100, 0.2830, 0.2970
0.7200, 0.2820, 0.2982
0.7300, 0.2820, 0.2993
0.7400, 0.2810, 0.3004
0.7500, 0.2800, 0.3013
0.7600, 0.2800, 0.3022
0.7700, 0.2800, 0.3030
0.7800, 0.2790, 0.3039
0.7900, 0.2790, 0.3047
0.8000, 0.2780, 0.3055
0.8100, 0.2770, 0.3063
0.8200, 0.2770, 0.3072
0.8300, 0.2780, 0.3080
0.8400, 0.2770, 0.3088
0.8500, 0.2720, 0.3097
0.8600, 0.2640, 0.3105
0.8700, 0.2500, 0.3113
0.8800, 0.2320, 0.3121
0.8900, 0.2040, 0.3129
0.9000, 0.1570, 0.3138
0.9100, 0.1460, 0.3148
0.9200, 0.1580, 0.3158
0.9300, 0.3190, 0.3672
0.9400, 0.5300, 0.5295
0.9500, 0.6770, 0.7381
0.9600, 0.7550, 0.9203
0.9700, 0.7270, 0.8889
0.9800, 0.7160, 0.9247
0.9900, 0.7190, 0.9431
1.0000, 0.7320, 0.9269
1.0100, 0.7450, 0.9362
1.0200, 0.7200, 0.9562
1.0300, 0.7470, 0.9638
1.0400, 0.7430, 0.9777
1.0500, 0.7630, 0.9813
1.0600, 0.7690, 0.9924
1.0700, 0.7560, 0.9907
1.0800, 0.7630, 0.9934
1.0900, 0.7850, 0.9950
1.1000, 0.7940, 1.0075
1.1100, 0.7980, 1.0081
1.1200, 0.8000, 1.0113
1.1300, 0.8090, 1.0150
1.1400, 0.7980, 1.0209
1.1500, 0.8060, 1.0209
1.1600, 0.8460, 1.0225
1.1700, 0.8950, 1.0178
1.1800, 0.9390, 1.0234
1.1900, 0.9350, 1.0281
1.2000, 0.9350, 1.0391
1.2100, 0.9920, 1.0618
1.2200, 1.0100, 1.0791
1.2300, 0.9340, 1.0144
1.2400, 0.3460, 0.4101
1.2500, 0.2340, 0.3359
1.2600, 0.2450, 0.3364
1.2700, 0.3190, 0.3368
1.2800, 0.2330, 0.3370
1.2900, 0.2690, 0.3376
1.3000, 0.2750, 0.3379
1.3100, 0.2610, 0.3385
1.3200, 0.2930, 0.3387
1.3300, 0.2600, 0.3392
1.3400, 0.2730, 0.3394
1.3500, 0.3050, 0.3398
1.3600, 0.3690, 0.3400
1.3700, 0.3230, 0.3404
1.3800, 0.2790, 0.3405
1.3900, 0.2720, 0.3409
1.4000, 0.2660, 0.3408
1.4100, 0.2630, 0.3411
1.4200, 0.2630, 0.3410
1.4300, 0.2610, 0.3412
1.4400, 0.2630, 0.3411
1.4500, 0.2610, 0.3413
1.4600, 0.2630, 0.3412
1.4700, 0.2580, 0.3414
1.4800, 0.2570, 0.3413
1.4900, 0.2600, 0.3414
1.5000, 0.2550, 0.3413
1.5100, 0.2590, 0.3413
1.5200, 0.2570, 0.3413
1.5300, 0.2550, 0.3412
1.5400, 0.2550, 0.3412
1.5500, 0.2530, 0.3411
1.5600, 0.2530, 0.3411
1.5700, 0.2530, 0.3410
1.5800, 0.2540, 0.3410
1.5900, 0.2530, 0.3409
1.6000, 0.2530, 0.3409
1.6100, 0.2520, 0.3408
1.6200, 0.2520, 0.3408
1.6300, 0.2520, 0.3408
{{< /chart >}}

{{< chart height="280" ymirror="2" y2label="gfem (code units)" xlabel="t (s)" ylabel="max nodal force" caption="Figure 17. Maximum nodal force, each code on its own axis: fdm in dyn (left), gfem as written in `solid/view.h5` (right). The two reduce over different node sets (465,797 P2 nodes against the 178,457 P1 nodes of the P2 element), so read the timing rather than the magnitudes: both spike in the same frame (t = 1.24 s) at valve closure - 4.0e6 (fdm) and 3.7e5 (gfem) - and both are quiet while the valve is open." >}}
t, fdm max|f| (dyn), gfem max|f| (code units)
0.0000, 1.88e-08, 12.43
0.0100, 2.72e+04, 4.603e+04
0.0200, 3.73e+05, 1.479e+04
0.0300, 7.92e+04, 1.956e+04
0.0400, 8.15e+04, 9.819e+04
0.0500, 2.02e+05, 7239
0.0600, 1.1e+05, 5212
0.0700, 2.04e+05, 1.198e+04
0.0800, 4.18e+04, 8383
0.0900, 7.67e+04, 6080
0.1000, 3.9e+04, 4213
0.1100, 4.65e+04, 9033
0.1200, 8.38e+04, 9656
0.1300, 2.49e+05, 2.522e+04
0.1400, 1.25e+05, 4.984e+04
0.1500, 1.2e+05, 2.641e+04
0.1600, 1.21e+05, 1.938e+04
0.1700, 8.33e+04, 1.371e+04
0.1800, 8.73e+04, 1.794e+04
0.1900, 5.08e+04, 2.826e+04
0.2000, 4.8e+04, 3.757e+04
0.2100, 4.87e+04, 4.741e+04
0.2200, 6.78e+04, 4.224e+04
0.2300, 4.83e+04, 5.156e+04
0.2400, 1.01e+05, 4.266e+04
0.2500, 1.61e+05, 5.786e+04
0.2600, 6.84e+04, 5.651e+04
0.2700, 1.26e+05, 5.743e+04
0.2800, 1.64e+05, 6.157e+04
0.2900, 2.18e+05, 3.533e+04
0.3000, 2.81e+05, 4.705e+04
0.3100, 5.87e+05, 4.151e+04
0.3200, 2.68e+05, 3.245e+04
0.3300, 3.03e+05, 2.532e+04
0.3400, 2.31e+05, 2.567e+04
0.3500, 3.35e+05, 2.387e+04
0.3600, 2.56e+05, 3.146e+04
0.3700, 3.37e+05, 2.3e+04
0.3800, 2.43e+05, 1.851e+04
0.3900, 3.63e+05, 2.091e+04
0.4000, 7.04e+05, 1.737e+04
0.4100, 3.44e+05, 1.642e+04
0.4200, 2.29e+05, 1.761e+04
0.4300, 5.92e+05, 1.733e+04
0.4400, 9.81e+05, 1.811e+04
0.4500, 3.85e+05, 1.813e+04
0.4600, 6.1e+05, 1.855e+04
0.4700, 4.63e+05, 1.879e+04
0.4800, 7.32e+05, 1.893e+04
0.4900, 2.96e+05, 1.898e+04
0.5000, 5.21e+05, 4.347e+04
0.5100, 4.82e+05, 2.853e+05
0.5200, 6.37e+05, 1.386e+05
0.5300, 7.77e+05, 6.712e+04
0.5400, 5.16e+05, 7.066e+04
0.5500, 4.23e+05, 8.564e+04
0.5600, 5.64e+05, 8.951e+04
0.5700, 4.49e+05, 9.773e+04
0.5800, 6.65e+05, 7.99e+04
0.5900, 5.78e+05, 7.582e+04
0.6000, 5.57e+05, 8.238e+04
0.6100, 6.1e+05, 6.547e+04
0.6200, 5.67e+05, 8.557e+04
0.6300, 5.43e+05, 6.077e+04
0.6400, 5.69e+05, 7.349e+04
0.6500, 6.91e+05, 5.872e+04
0.6600, 3.72e+05, 7.119e+04
0.6700, 6.68e+05, 6.693e+04
0.6800, 6.34e+05, 7.227e+04
0.6900, 5.34e+05, 6.748e+04
0.7000, 6.13e+05, 6.773e+04
0.7100, 5.02e+05, 6.793e+04
0.7200, 5.1e+05, 6.287e+04
0.7300, 5.6e+05, 6.891e+04
0.7400, 6.51e+05, 6.481e+04
0.7500, 5.21e+05, 6.932e+04
0.7600, 5.53e+05, 6.07e+04
0.7700, 4.98e+05, 6.49e+04
0.7800, 4.99e+05, 6.298e+04
0.7900, 5.61e+05, 6.274e+04
0.8000, 4.62e+05, 6.17e+04
0.8100, 4.87e+05, 6.188e+04
0.8200, 5.53e+05, 6.184e+04
0.8300, 4.22e+05, 6.357e+04
0.8400, 4.94e+05, 5.953e+04
0.8500, 3.01e+05, 5.304e+04
0.8600, 1.87e+05, 4.377e+04
0.8700, 1.85e+05, 3.528e+04
0.8800, 1.09e+05, 2.756e+04
0.8900, 9.58e+04, 2.533e+04
0.9000, 7.32e+04, 2.453e+04
0.9100, 8.33e+04, 2.46e+04
0.9200, 7.58e+04, 2.467e+04
0.9300, 5.59e+04, 2.473e+04
0.9400, 5.66e+04, 2.481e+04
0.9500, 2.08e+05, 2.489e+04
0.9600, 1.43e+05, 2.498e+04
0.9700, 8.76e+04, 2.505e+04
0.9800, 6.99e+04, 4.145e+04
0.9900, 8.4e+04, 5.326e+04
1.0000, 7.99e+04, 6.487e+04
1.0100, 8.1e+04, 5.26e+04
1.0200, 6.25e+04, 5.12e+04
1.0300, 6.38e+04, 5.434e+04
1.0400, 9.21e+04, 8.032e+04
1.0500, 7.17e+04, 1.077e+05
1.0600, 1.4e+05, 6.113e+04
1.0700, 6.02e+04, 6.792e+04
1.0800, 1.27e+05, 8.897e+04
1.0900, 1.27e+05, 7.435e+04
1.1000, 1.69e+05, 6.663e+04
1.1100, 5.39e+05, 6.368e+04
1.1200, 4.3e+05, 6.063e+04
1.1300, 5.07e+05, 5.786e+04
1.1400, 4.38e+05, 5.508e+04
1.1500, 1.11e+06, 5.145e+04
1.1600, 3.14e+05, 4.944e+04
1.1700, 3.52e+05, 5.499e+04
1.1800, 1.75e+05, 5.529e+04
1.1900, 2.15e+05, 5.043e+04
1.2000, 2.09e+05, 5.074e+04
1.2100, 2.02e+05, 4.851e+04
1.2200, 3.1e+05, 6.803e+04
1.2300, 7.72e+05, 1.309e+05
1.2400, 4.03e+06, 3.696e+05
1.2500, 2.63e+06, 1.172e+05
1.2600, 9.17e+05, 1.724e+05
1.2700, 1.05e+06, 1.135e+05
1.2800, 4.33e+05, 1.573e+05
1.2900, 5.8e+05, 1.091e+05
1.3000, 4.2e+05, 1.26e+05
1.3100, 5.19e+05, 1.097e+05
1.3200, 5.42e+05, 1.057e+05
1.3300, 2.93e+05, 1.099e+05
1.3400, 3.49e+05, 9.577e+04
1.3500, 2.52e+05, 9.348e+04
1.3600, 4.07e+05, 9.336e+04
1.3700, 3.05e+05, 8.796e+04
1.3800, 2.57e+05, 8.506e+04
1.3900, 2.52e+05, 7.721e+04
1.4000, 2.89e+05, 7.766e+04
1.4100, 2.66e+05, 7.514e+04
1.4200, 1.88e+05, 7.194e+04
1.4300, 1.68e+05, 7.184e+04
1.4400, 1.66e+05, 6.763e+04
1.4500, 2.97e+05, 7.008e+04
1.4600, 1.83e+05, 6.138e+04
1.4700, 1.6e+05, 6.645e+04
1.4800, 1.55e+05, 6.411e+04
1.4900, 1.53e+05, 6.419e+04
1.5000, 1.98e+05, 6.318e+04
1.5100, 1.34e+05, 6.305e+04
1.5200, 1.5e+05, 6.121e+04
1.5300, 1.49e+05, 6.174e+04
1.5400, 1.68e+05, 6.227e+04
1.5500, 1.42e+05, 6.268e+04
1.5600, 1.93e+05, 6.306e+04
1.5700, 1.24e+05, 6.337e+04
1.5800, 1.34e+05, 6.362e+04
1.5900, 1.44e+05, 6.376e+04
1.6000, 1.22e+05, 6.375e+04
1.6100, 1.25e+05, 6.358e+04
1.6200, 1.25e+05, 6.323e+04
1.6300, 1.11e+05, 6.272e+04
{{< /chart >}}

{{< chart height="300" ymirror="3" y2label="fdm |div| (solver log)" xlabel="t (s)" ylabel="|div u| (1/s)" caption="Figure 18. Divergence. The two left series are computed here from the gfem frames: central differences of the collocated point velocities, on the physical cells minus the layer that touches the ghost ring, as rms (0.11-27.9 1/s) and max (9.7-1520 1/s). The gfem solver never logs a divergence, so that is a post-processing estimator, not its projection residual. The right-hand series is fdm's own solver diagnostic from `sim.log` (0-0.083), a different estimator on a different grid. Both are largest at the closure frames (t = 0.51 s and 1.24 s). Read the shapes, not the magnitudes." >}}
t, gfem rms, gfem max, fdm |div| (right)
0.0000, 0.1076, 9.703, 0
0.0100, 7.344, 280.6, 0.000559
0.0200, 16.4, 565.2, 0.00621
0.0300, 14.46, 347, 0.00188
0.0400, 15.88, 574.1, 0.00188
0.0500, 13.81, 346.1, 0.00266
0.0600, 12.67, 289.1, 0.00197
0.0700, 11.92, 268.6, 0.00182
0.0800, 10.85, 251.5, 0.00164
0.0900, 9.795, 278.1, 0.00163
0.1000, 9.369, 279.4, 0.00147
0.1100, 8.997, 256.3, 0.00141
0.1200, 9.252, 346.9, 0.00132
0.1300, 9.929, 370, 0.00135
0.1400, 10.18, 410.3, 0.00129
0.1500, 10.37, 399, 0.00125
0.1600, 10.86, 425.7, 0.00112
0.1700, 11.26, 422.8, 0.00114
0.1800, 12.18, 463, 0.00106
0.1900, 13.55, 510.9, 0.000998
0.2000, 14.6, 516.7, 0.000956
0.2100, 15.26, 437.8, 0.000887
0.2200, 15.84, 469.9, 0.000821
0.2300, 16.06, 508.3, 0.000784
0.2400, 15.87, 516, 0.000907
0.2500, 15.74, 486.8, 0.00081
0.2600, 15.62, 472, 0.000766
0.2700, 15.38, 434.6, 0.00097
0.2800, 14.93, 474.8, 0.00115
0.2900, 14.17, 410.5, 0.00173
0.3000, 13.33, 382.3, 0.00221
0.3100, 12.61, 359.7, 0.00405
0.3200, 11.73, 304.8, 0.0038
0.3300, 10.93, 264.4, 0.00341
0.3400, 10.23, 282.2, 0.003
0.3500, 9.582, 273.2, 0.00262
0.3600, 9.109, 261.2, 0.00257
0.3700, 8.817, 266.9, 0.00237
0.3800, 8.663, 288, 0.00245
0.3900, 8.648, 312.5, 0.00372
0.4000, 8.543, 356, 0.00434
0.4100, 8.272, 307.6, 0.00362
0.4200, 8.065, 314.1, 0.00421
0.4300, 7.773, 253.5, 0.00354
0.4400, 7.534, 264.3, 0.00324
0.4500, 7.329, 264, 0.00362
0.4600, 7.235, 270.3, 0.00304
0.4700, 7.257, 322.8, 0.00327
0.4800, 7.392, 310.3, 0.00263
0.4900, 7.439, 287.2, 0.00252
0.5000, 9.819, 296.4, 0.0024
0.5100, 23.04, 1028, 0.00234
0.5200, 27.57, 967.7, 0.00239
0.5300, 21.96, 528.1, 0.00226
0.5400, 20.27, 617.2, 0.00202
0.5500, 17.88, 368.9, 0.00195
0.5600, 16.22, 394.5, 0.00165
0.5700, 14.75, 323, 0.00172
0.5800, 13.53, 303.8, 0.00176
0.5900, 12.41, 285.8, 0.00154
0.6000, 11.45, 247.2, 0.00153
0.6100, 10.47, 282.3, 0.00132
0.6200, 9.733, 240.7, 0.00133
0.6300, 8.976, 213.5, 0.00128
0.6400, 8.274, 186, 0.00122
0.6500, 7.579, 189.4, 0.0012
0.6600, 7.052, 175.5, 0.00109
0.6700, 6.511, 173.8, 0.00109
0.6800, 6.019, 169.5, 0.000969
0.6900, 5.634, 128, 0.000929
0.7000, 5.191, 116.4, 0.000893
0.7100, 4.846, 98.83, 0.000881
0.7200, 4.503, 100, 0.000804
0.7300, 4.278, 87.85, 0.000763
0.7400, 4.016, 82.3, 0.000819
0.7500, 3.824, 99.65, 0.0007
0.7600, 3.619, 82.37, 0.00067
0.7700, 3.489, 81.61, 0.000649
0.7800, 3.331, 76.32, 0.000638
0.7900, 3.216, 89.12, 0.000551
0.8000, 3.105, 77.2, 0.000563
0.8100, 2.996, 103, 0.000576
0.8200, 2.915, 77.43, 0.000477
0.8300, 2.843, 94.89, 0.000595
0.8400, 2.791, 79.36, 0.00047
0.8500, 2.828, 94.42, 0.000447
0.8600, 3.093, 94.06, 0.000406
0.8700, 3.714, 156.9, 0.000418
0.8800, 4.474, 167.5, 0.000367
0.8900, 5.531, 325.6, 0.000344
0.9000, 6.389, 336.9, 0.000335
0.9100, 6.917, 289.3, 0.000299
0.9200, 7.436, 273.5, 0.000306
0.9300, 7.86, 279.4, 0.000297
0.9400, 8.447, 300.6, 0.000329
0.9500, 8.782, 311.8, 0.000546
0.9600, 9.649, 359.2, 0.000824
0.9700, 10.16, 377.6, 0.000687
0.9800, 10.67, 383.4, 0.000736
0.9900, 11.62, 484.5, 0.000633
1.0000, 12.82, 535.5, 0.000641
1.0100, 13.87, 476.2, 0.000617
1.0200, 14.64, 533.3, 0.000607
1.0300, 15.3, 514.7, 0.000536
1.0400, 15.83, 574.7, 0.00054
1.0500, 16.05, 538.8, 0.000511
1.0600, 16.13, 467.4, 0.00046
1.0700, 16.13, 492.7, 0.000479
1.0800, 16, 515.2, 0.000541
1.0900, 15.7, 497.5, 0.000655
1.1000, 15.34, 468.1, 0.000726
1.1100, 14.79, 377.5, 0.00258
1.1200, 14.23, 409, 0.0025
1.1300, 13.5, 365.2, 0.00279
1.1400, 12.72, 397.4, 0.00375
1.1500, 12.13, 460.9, 0.00285
1.1600, 11.53, 397.9, 0.00323
1.1700, 11.01, 345.3, 0.00266
1.1800, 10.6, 373.6, 0.00233
1.1900, 10.33, 308.5, 0.00236
1.2000, 10.48, 288.4, 0.00228
1.2100, 11.55, 372.1, 0.00228
1.2200, 14.66, 535.6, 0.00241
1.2300, 18.03, 613, 0.00652
1.2400, 27.88, 1518, 0.0826
1.2500, 20.98, 586.5, 0.0209
1.2600, 21.02, 684.1, 0.0239
1.2700, 18.45, 456, 0.0305
1.2800, 17.09, 409.2, 0.0117
1.2900, 15.81, 374.3, 0.0132
1.3000, 14.78, 338.8, 0.0123
1.3100, 13.97, 372.9, 0.00989
1.3200, 13.15, 275.5, 0.00967
1.3300, 12.47, 293.7, 0.00747
1.3400, 11.75, 257.3, 0.008
1.3500, 11.14, 308.7, 0.00707
1.3600, 10.57, 263.4, 0.00685
1.3700, 10.2, 334.8, 0.00676
1.3800, 9.792, 262.1, 0.00589
1.3900, 9.417, 306.7, 0.00587
1.4000, 9.056, 259.4, 0.00505
1.4100, 8.8, 286.6, 0.00493
1.4200, 8.528, 252.6, 0.00454
1.4300, 8.393, 273.1, 0.00443
1.4400, 8.228, 245.3, 0.00415
1.4500, 8.101, 250.2, 0.00383
1.4600, 7.937, 257, 0.00414
1.4700, 7.876, 247.9, 0.00371
1.4800, 7.77, 262.6, 0.00346
1.4900, 7.735, 230.1, 0.00335
1.5000, 7.662, 225.1, 0.00305
1.5100, 7.607, 237.7, 0.003
1.5200, 7.552, 203.9, 0.0027
1.5300, 7.514, 230.3, 0.00256
1.5400, 7.5, 220.8, 0.00247
1.5500, 7.482, 226, 0.00233
1.5600, 7.483, 228.1, 0.00241
1.5700, 7.471, 236.7, 0.00219
1.5800, 7.481, 241.1, 0.00218
1.5900, 7.482, 245.2, 0.00209
1.6000, 7.508, 252.8, 0.00189
1.6100, 7.52, 258.2, 0.00188
1.6200, 7.545, 263.3, 0.00154
1.6300, 7.571, 264.7, 0.00166
{{< /chart >}}

The comparison is informative in both directions.  The two codes agree on the
driving waveform (0.68 mmHg apart), on the frame in which each ejection peak
occurs, and on the size of the solid response (1.01 cm against 1.11 cm).  They
disagree at the closure transients, where the two Windkessel state machines
behave differently — at `t = 0.51 s` the fdm Windkessel is still at 104.8 mmHg
while the gfem one has dropped to 83.7 with a −468 mL/s backflow — and in the
reported nodal force, which differs by an order of magnitude.  None of that is a
statement about accuracy: the two decks do not use the same leaflet
constitutive parameters, the meshes differ by a factor of three in cell count,
and the force and divergence series are, as their captions say, different
estimators rather than the same quantity computed twice.

### 12.5 Build and run pitfalls worth recording

| # | Symptom | Fix |
|---|---|---|
| 1 | `nvcc` 12.6 rejects gcc 13.3 (`gcc versions later than 13 are not supported`, the check stops at 13.2) | `-allow-unsupported-compiler` |
| 2 | `KOKKOS_LAMBDA` in `.cpp` files (it expands to `__host__ __device__`) cannot be parsed by g++ | mark those translation units `LANGUAGE CUDA`; no `nvcc_wrapper` needed |
| 3 | nvcc does not implement C++20 `consteval` fully, spdlog's bundled fmt 8 fails with `call to consteval function did not produce a valid constant expression` | compile CUDA with `-DFMT_CONSTEVAL=` |
| 4 | Kokkos is built with the OpenMP backend while the project compiles CUDA | `-Xcompiler=-fopenmp` on CUDA compilations |
| 5 | conda Kokkos config asks for `CUDA::cudart` / `CUDA::cuda_driver` | `find_package(CUDAToolkit REQUIRED)` **before** `find_package(Kokkos)` |
| 6 | DOLFIN's imported target references `PETSC::petsc` and `SLEPC::slepc`, which its config never defines | add placeholder imported targets, and disable Boost's CONFIG mode (`Boost_NO_BOOST_CMAKE`), since the conda Boost ships no `BoostConfig.cmake` |
| 7 | CMake 4.x removed the `FindBoost` module entirely | configure with the system CMake 3.28 |

One numerical pitfall matters more than all of these.  **`Δt` must stay at
`5e-6`.**  Running the same deck at `Nt = 100` (`Δt = 1.6e-2`) diverges to NaN
within about three steps, and the NaN then propagates into a CUDA illegal-address
fault inside the flow-rate reduction — an environment-looking crash with a
time-step cause.  The reference deck's `Nt = 327,000` is not merely a resolution
choice.

Finally, `$HOME/mesh-cardiology/AV/ibamr/pressure.txt` is **hard-coded** in
`src/libkokkos/StokesFlow3D/TubeFlow.h:157`, in the original
`dataSize / timeInterval / values` format.  Any other case must either create
that exact path or patch the source.

---

*This page is the English edition of the project note
`av-mv-fsi-summary.md` (2026-09-13). The command matrices, pressure/flow
figures and PyVista deformation snapshots were generated from the saved AV and
MV runs on 2026-09-14.  §12 was added on 2026-09-15 for the npuheart/gfem
implementation; Figures 14–18 compare the two codes and were built the same day
from the saved run outputs (§12.4.1).*
