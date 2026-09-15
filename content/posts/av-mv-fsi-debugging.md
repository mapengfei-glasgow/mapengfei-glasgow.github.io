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

<p class="tcaption">Table 12. AV in the npuheart/gfem code, snapshot at 2026-09-15 22:02 (still running).</p>

| Quantity | Value |
|---|---|
| started / elapsed | 16:54, 5 h 08 min |
| progress | **296,318 / 327,000 steps (90.6 %)**, t = 1.481 s of 1.635 s |
| rate | ≈ 16 steps/s (0.062 s per coupled step) |
| GPU | 1 × RTX 4090, 2.6 GB / 24 GB, 99 % utilisation |
| errors | **0** NaN / CUDA failures in the log |
| inlet pressure | 5,695–164,777 Pa (4.3–123.6 mmHg) over the cycle so far |
| axial flow rate | −485 to +538 (arbitrary units), last 0.38 |
| output | 297 × `fluid*.vti` (65 MB each) + growing `solid/view.h5`, ≈ 22 GB |

At roughly 0.062 s per coupled step this is the same order as the AV-1 Stokes run
in §1, on a mesh three times larger than the reduced one — the cost is dominated
by the fluid solve, not by the solid assembly.


The two curves below are drawn from the numbers written directly in this page
(no image): the CSV block under each figure is the data, parsed by a `chart`
shortcode and rendered by Chart.js.  They cover the run up to the step reached
when this section was written.

{{< chart type="line" height="300" xlabel="t (s)" ylabel="pressure (mmHg)" caption="Figure 12. AV run in the npuheart/gfem code: prescribed inflow pressure and Windkessel outflow pressure, both in mmHg. Data written inline in this page and drawn by Chart.js — hover for values, drag-free zoom via the browser." >}}
t, inflow (mmHg), outflow (mmHg)
0.0000, 14.351, 85.000
0.0077, 14.898, 85.000
0.0153, 16.567, 85.000
0.0230, 20.643, 85.000
0.0307, 27.059, 85.000
0.0383, 36.129, 85.000
0.0460, 46.634, 85.000
0.0537, 57.419, 85.000
0.0613, 67.350, 85.000
0.0690, 76.059, 85.000
0.0767, 82.611, 85.000
0.0843, 87.159, 86.242
0.0920, 90.921, 86.984
0.0997, 94.730, 87.113
0.1073, 98.677, 87.741
0.1150, 102.708, 88.698
0.1226, 106.645, 89.682
0.1303, 110.270, 91.180
0.1380, 113.271, 92.956
0.1456, 115.662, 95.167
0.1533, 117.502, 97.503
0.1610, 118.983, 99.866
0.1686, 120.174, 102.354
0.1763, 121.146, 104.906
0.1840, 121.952, 107.381
0.1916, 122.610, 109.763
0.1993, 123.117, 112.073
0.2070, 123.441, 114.230
0.2146, 123.588, 116.308
0.2223, 123.523, 118.199
0.2300, 123.286, 119.942
0.2376, 122.852, 121.535
0.2453, 122.267, 122.913
0.2530, 121.515, 124.118
0.2606, 120.635, 125.076
0.2683, 119.622, 125.797
0.2759, 118.475, 126.282
0.2836, 117.173, 126.530
0.2913, 115.732, 126.537
0.2989, 114.163, 126.304
0.3066, 112.486, 125.831
0.3143, 110.729, 125.129
0.3219, 108.907, 124.216
0.3296, 106.993, 123.041
0.3373, 104.858, 121.683
0.3449, 102.437, 120.085
0.3526, 99.538, 118.268
0.3603, 96.028, 116.266
0.3679, 91.367, 115.256
0.3756, 85.412, 114.529
0.3833, 78.121, 113.786
0.3909, 69.730, 113.027
0.3986, 59.860, 112.249
0.4062, 49.314, 111.454
0.4139, 39.523, 110.657
0.4216, 31.211, 109.871
0.4292, 24.446, 109.094
0.4369, 19.329, 108.334
0.4446, 15.527, 107.586
0.4522, 12.550, 106.852
0.4599, 9.935, 106.124
0.4676, 7.864, 105.403
0.4752, 6.375, 104.693
0.4829, 5.535, 103.992
0.4906, 5.042, 102.543
0.4982, 4.720, 92.643
0.5059, 4.460, 84.979
0.5136, 4.303, 88.764
0.5212, 4.284, 99.967
0.5289, 4.397, 94.629
0.5366, 4.590, 97.035
0.5442, 4.812, 95.652
0.5519, 5.009, 94.746
0.5595, 5.171, 94.721
0.5672, 5.313, 94.161
0.5749, 5.457, 93.445
0.5825, 5.627, 93.030
0.5902, 5.833, 92.921
0.5979, 6.080, 91.485
0.6055, 6.359, 91.999
0.6132, 6.670, 90.844
0.6209, 7.006, 90.412
0.6285, 7.360, 90.395
0.6362, 7.723, 89.177
0.6439, 8.086, 89.260
0.6515, 8.440, 88.548
0.6592, 8.776, 87.949
0.6669, 9.083, 87.734
0.6745, 9.364, 87.043
0.6822, 9.620, 86.600
0.6899, 9.862, 86.202
0.6975, 10.093, 85.662
0.7052, 10.321, 85.176
0.7129, 10.553, 85.082
0.7205, 10.793, 84.961
0.7282, 11.046, 84.990
0.7358, 11.315, 85.086
0.7435, 11.606, 84.949
0.7512, 11.921, 85.040
0.7588, 12.257, 85.048
0.7665, 12.610, 84.936
0.7742, 12.975, 85.081
0.7818, 13.345, 85.001
0.7895, 13.717, 84.990
0.7972, 14.085, 85.062
0.8048, 14.445, 84.970
0.8125, 14.789, 85.018
0.8202, 14.359, 85.017
0.8278, 14.916, 84.993
0.8355, 16.636, 85.085
0.8432, 20.747, 85.088
0.8508, 27.228, 85.155
0.8585, 36.331, 85.220
0.8662, 46.852, 85.220
0.8738, 57.637, 85.220
0.8815, 67.535, 85.220
0.8891, 76.227, 85.220
0.8968, 82.714, 85.220
0.9045, 87.243, 85.220
0.9121, 90.997, 85.220
0.9198, 94.808, 85.220
0.9275, 98.757, 85.220
0.9351, 102.789, 89.115
0.9428, 106.722, 90.328
0.9505, 110.334, 91.921
0.9581, 113.326, 93.798
0.9658, 115.701, 95.923
0.9735, 117.536, 98.232
0.9811, 119.009, 100.646
0.9888, 120.196, 103.063
0.9965, 121.163, 105.439
1.0040, 121.967, 107.759
1.0120, 122.621, 110.012
1.0190, 123.126, 112.201
1.0270, 123.446, 114.302
1.0350, 123.590, 116.283
1.0420, 123.520, 118.105
1.0500, 123.279, 119.774
1.0580, 122.842, 121.270
1.0650, 122.252, 122.582
1.0730, 121.498, 123.683
1.0810, 120.616, 124.594
1.0880, 119.601, 125.293
1.0960, 118.449, 125.778
1.1040, 117.146, 126.024
1.1110, 115.701, 126.039
1.1190, 114.130, 125.814
1.1270, 112.451, 125.362
1.1340, 110.693, 124.673
1.1420, 108.869, 123.755
1.1500, 106.953, 122.613
1.1570, 104.812, 121.243
1.1650, 102.383, 119.634
1.1730, 99.475, 117.780
1.1800, 95.940, 115.643
1.1880, 91.262, 113.172
1.1960, 85.270, 110.284
1.2030, 77.966, 106.932
1.2110, 69.539, 103.182
1.2190, 59.651, 99.444
1.2260, 49.107, 95.737
1.2340, 39.333, 94.479
1.2420, 31.063, 107.472
1.2490, 24.318, 103.125
1.2570, 19.243, 100.781
1.2650, 15.457, 103.967
1.2720, 12.494, 101.081
1.2800, 9.887, 101.117
1.2880, 7.828, 101.035
1.2950, 6.355, 99.907
1.3030, 5.522, 99.553
1.3110, 5.035, 99.292
1.3180, 4.714, 98.280
1.3260, 4.456, 98.013
1.3340, 4.301, 97.691
1.3410, 4.285, 96.519
1.3490, 4.400, 96.712
1.3570, 4.595, 95.732
1.3640, 4.816, 95.214
1.3720, 5.013, 95.050
1.3800, 5.174, 94.051
1.3870, 5.315, 93.877
1.3950, 5.460, 93.277
1.4030, 5.631, 92.624
1.4100, 5.837, 92.352
1.4180, 6.085, 91.712
1.4260, 6.365, 91.189
1.4330, 6.677, 90.787
1.4410, 7.013, 90.205
1.4490, 7.368, 89.711
1.4560, 7.731, 89.331
1.4640, 8.094, 88.724
1.4720, 8.447, 88.264
1.4790, 8.782, 87.870
1.4870, 9.089, 87.234
1.4950, 9.369, 86.881
1.5020, 9.625, 86.401
1.5100, 9.866, 85.812
1.5180, 10.097, 85.488
1.5250, 10.326, 85.017
1.5330, 10.558, 84.985
1.5330, 10.568, 84.990
{{< /chart >}}

{{< chart type="line" height="260" xlabel="t (s)" ylabel="flow rate" caption="Figure 13. AV run: axial flow rate on the two faces of the background grid (same arbitrary units as the fdm-3d-v1 curves in §1). The sign change is the closing transient." >}}
t, flow rate
0.0000, -0.000
0.0077, -200.824
0.0153, 142.078
0.0230, 47.867
0.0307, -86.221
0.0383, -13.409
0.0460, 81.503
0.0537, 31.216
0.0613, -32.065
0.0690, -32.312
0.0767, 14.742
0.0843, 42.863
0.0920, 71.923
0.0997, 79.888
0.1073, 101.424
0.1150, 129.335
0.1226, 154.383
0.1303, 191.239
0.1380, 231.221
0.1456, 278.933
0.1533, 324.155
0.1610, 364.658
0.1686, 403.917
0.1763, 440.158
0.1840, 470.077
0.1916, 493.772
0.1993, 512.759
0.2070, 525.313
0.2146, 534.286
0.2223, 537.184
0.2300, 535.760
0.2376, 530.564
0.2453, 520.130
0.2530, 506.396
0.2606, 487.605
0.2683, 464.641
0.2759, 438.094
0.2836, 408.249
0.2913, 375.522
0.2989, 340.207
0.3066, 302.618
0.3143, 263.298
0.3219, 222.925
0.3296, 180.197
0.3373, 137.636
0.3449, 93.518
0.3526, 48.665
0.3603, 4.064
0.3679, -6.466
0.3756, -8.190
0.3833, -10.242
0.3909, -12.626
0.3986, -15.324
0.4062, -18.322
0.4139, -21.090
0.4216, -23.311
0.4292, -25.090
0.4369, -26.289
0.4446, -27.142
0.4522, -27.571
0.4599, -27.912
0.4676, -28.100
0.4752, -28.098
0.4829, -27.942
0.4906, -50.720
0.4982, -308.395
0.5059, -470.359
0.5136, -280.282
0.5212, 77.595
0.5289, -67.521
0.5366, 27.463
0.5442, -2.353
0.5519, -11.128
0.5595, 3.473
0.5672, 2.366
0.5749, -4.006
0.5825, 0.113
0.5902, 11.117
0.5979, -16.322
0.6055, 14.923
0.6132, -6.068
0.6209, -2.400
0.6285, 11.024
0.6362, -10.568
0.6439, 7.358
0.6515, -0.296
0.6592, -2.955
0.6669, 4.981
0.6745, -1.512
0.6822, -0.114
0.6899, 2.053
0.6975, 0.008
0.7052, -0.316
0.7129, 2.512
0.7205, -1.152
0.7282, -0.278
0.7358, 2.626
0.7435, -1.537
0.7512, 1.237
0.7588, 1.456
0.7665, -1.929
0.7742, 2.467
0.7818, 0.045
0.7895, -0.282
0.7972, 1.892
0.8048, -0.887
0.8125, 0.562
0.8202, 0.525
0.8278, -0.201
0.8355, 2.598
0.8432, 2.693
0.8508, 4.704
0.8585, 8.274
0.8662, 10.795
0.8738, 13.448
0.8815, 17.883
0.8891, 24.008
0.8968, 31.254
0.9045, 38.001
0.9121, 47.607
0.9198, 63.338
0.9275, 89.464
0.9351, 124.676
0.9428, 157.136
0.9505, 196.350
0.9581, 238.747
0.9658, 283.022
0.9735, 327.118
0.9811, 368.812
0.9888, 405.559
0.9965, 436.747
1.0040, 462.731
1.0120, 483.800
1.0190, 500.674
1.0270, 513.235
1.0350, 521.071
1.0420, 523.688
1.0500, 521.896
1.0580, 515.700
1.0650, 505.303
1.0730, 490.468
1.0810, 472.319
1.0880, 450.649
1.0960, 425.818
1.1040, 397.452
1.1110, 366.256
1.1190, 332.293
1.1270, 296.214
1.1340, 258.005
1.1420, 218.121
1.1500, 176.895
1.1570, 134.337
1.1650, 90.256
1.1730, 44.695
1.1800, -3.351
1.1880, -55.020
1.1960, -112.256
1.2030, -175.747
1.2110, -242.805
1.2190, -301.216
1.2260, -352.036
1.2340, -324.820
1.2420, 99.887
1.2490, -21.197
1.2570, -66.021
1.2650, 46.640
1.2720, -24.885
1.2800, -3.536
1.2880, 9.470
1.2950, -7.690
1.3030, -0.796
1.3110, 7.339
1.3180, -7.122
1.3260, 2.338
1.3340, 7.565
1.3410, -10.844
1.3490, 11.138
1.3570, -3.283
1.3640, -2.023
1.3720, 8.061
1.3800, -6.236
1.3870, 4.532
1.3950, 1.386
1.4030, -2.542
1.4100, 4.567
1.4180, 0.294
1.4260, -0.120
1.4330, 2.806
1.4410, 0.040
1.4490, 0.260
1.4560, 3.491
1.4640, -0.201
1.4720, 0.833
1.4790, 3.249
1.4870, -1.416
1.4950, 2.524
1.5020, 2.113
1.5100, -1.252
1.5180, 3.183
1.5250, 0.536
1.5330, -0.433
1.5330, -0.286
{{< /chart >}}

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
implementation.*
