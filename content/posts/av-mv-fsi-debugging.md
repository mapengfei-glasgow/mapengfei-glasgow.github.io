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
