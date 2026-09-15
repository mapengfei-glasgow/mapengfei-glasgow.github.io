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

<p class="tcaption">Table 12. AV in the npuheart/gfem code, snapshot at 2026-09-15 22:32, 98.9 % of the steps done.</p>

| Quantity | Value |
|---|---|
| started / elapsed | 16:54, 5 h 38 min |
| progress | **323,533 / 327,000 steps (98.9 %)**, t = 1.618 s of 1.635 s |
| rate | ≈ 16 steps/s (0.062 s per coupled step) |
| GPU | 1 × RTX 4090, 2.6 GB / 24 GB, 99 % utilisation |
| errors | **0** NaN / CUDA failures in the log |
| inlet pressure | 5,695–164,777 Pa (4.3–123.6 mmHg) over the cycle |
| axial flow rate | −485 to +538 (arbitrary units) |
| output | 324 × `fluid*.vti` (65 MB each) + growing `solid/view.h5`, ≈ 24 GB |

At roughly 0.062 s per coupled step this is the same order as the AV-1 Stokes run
in §1, on a mesh three times larger than the reduced one — the cost is dominated
by the fluid solve, not by the solid assembly.



The two curves below are drawn from the numbers written directly in this page —
there is no image to regenerate and re-upload.  The CSV block under each figure
*is* the data: the `chart` shortcode parses it and Chart.js draws it (self-hosted,
theme-aware, hover for values).  They run to the last step logged when this page
was updated.

{{< chart height="300" xlabel="t (s)" ylabel="pressure (mmHg)" caption="Figure 12. AV in the npuheart/gfem code: prescribed inflow pressure and Windkessel outflow pressure, in mmHg." >}}
t, inflow (mmHg), outflow (mmHg)
0.0000, 14.351, 85.000
0.0081, 14.948, 85.000
0.0162, 16.950, 85.000
0.0243, 21.503, 85.000
0.0324, 28.936, 85.000
0.0405, 38.971, 85.000
0.0486, 50.264, 85.000
0.0567, 61.462, 85.000
0.0648, 71.469, 85.000
0.0729, 79.643, 85.000
0.0810, 85.352, 86.117
0.0891, 89.488, 86.718
0.0972, 93.473, 87.069
0.1052, 97.593, 87.479
0.1133, 101.840, 88.466
0.1214, 106.038, 89.527
0.1295, 109.921, 90.998
0.1376, 113.145, 92.871
0.1457, 115.681, 95.190
0.1538, 117.612, 97.658
0.1619, 119.138, 100.152
0.1700, 120.371, 102.821
0.1781, 121.346, 105.477
0.1862, 122.158, 108.093
0.1943, 122.806, 110.570
0.2024, 123.266, 112.954
0.2105, 123.536, 115.210
0.2186, 123.577, 117.293
0.2267, 123.406, 119.231
0.2348, 123.038, 120.951
0.2429, 122.465, 122.493
0.2510, 121.726, 123.822
0.2590, 120.825, 124.901
0.2671, 119.780, 125.707
0.2752, 118.591, 126.245
0.2833, 117.223, 126.526
0.2914, 115.702, 126.534
0.2995, 114.041, 126.276
0.3076, 112.258, 125.748
0.3157, 110.392, 124.984
0.3238, 108.453, 123.950
0.3319, 106.373, 122.657
0.3400, 104.049, 121.140
0.3481, 101.293, 119.355
0.3562, 97.990, 117.354
0.3643, 93.755, 115.605
0.3724, 88.056, 114.834
0.3805, 80.916, 114.057
0.3886, 72.442, 113.260
0.3967, 62.466, 112.447
0.4048, 51.325, 111.610
0.4128, 40.824, 110.768
0.4209, 31.820, 109.935
0.4290, 24.614, 109.115
0.4371, 19.204, 108.312
0.4452, 15.243, 107.522
0.4533, 12.157, 106.749
0.4614, 9.497, 105.981
0.4695, 7.405, 105.222
0.4776, 6.079, 104.475
0.4857, 5.316, 103.737
0.4938, 4.899, 98.157
0.5019, 4.587, 88.545
0.5100, 4.356, 83.663
0.5181, 4.275, 99.705
0.5262, 4.345, 96.160
0.5343, 4.527, 95.495
0.5424, 4.758, 96.458
0.5505, 4.977, 94.562
0.5586, 5.151, 94.864
0.5667, 5.302, 94.168
0.5747, 5.454, 93.469
0.5828, 5.634, 93.044
0.5909, 5.855, 92.808
0.5990, 6.120, 91.454
0.6071, 6.422, 91.978
0.6152, 6.756, 90.456
0.6233, 7.118, 90.590
0.6314, 7.496, 89.879
0.6395, 7.881, 89.123
0.6476, 8.260, 89.115
0.6557, 8.625, 88.067
0.6638, 8.964, 87.874
0.6719, 9.270, 87.267
0.6800, 9.549, 86.695
0.6881, 9.807, 86.339
0.6962, 10.053, 85.759
0.7043, 10.294, 85.225
0.7124, 10.539, 85.074
0.7205, 10.791, 84.962
0.7286, 11.059, 84.998
0.7367, 11.345, 85.076
0.7447, 11.654, 84.933
0.7528, 11.992, 85.082
0.7609, 12.352, 85.003
0.7690, 12.729, 84.980
0.7771, 13.117, 85.079
0.7852, 13.510, 84.946
0.7933, 13.901, 85.052
0.8014, 14.286, 85.014
0.8095, 14.657, 84.990
0.8176, 14.614, 85.045
0.8257, 14.669, 84.974
0.8338, 16.116, 85.070
0.8419, 19.900, 85.086
0.8500, 26.316, 85.145
0.8581, 35.797, 85.220
0.8662, 46.880, 85.220
0.8743, 58.270, 85.220
0.8824, 68.589, 85.220
0.8905, 77.547, 85.220
0.8986, 83.873, 85.220
0.9066, 88.322, 85.220
0.9147, 92.270, 85.220
0.9228, 96.358, 85.220
0.9309, 100.570, 85.220
0.9390, 104.815, 89.671
0.9471, 108.805, 91.185
0.9552, 112.291, 93.062
0.9633, 114.988, 95.207
0.9714, 117.086, 97.594
0.9795, 118.728, 100.132
0.9876, 120.024, 102.689
0.9957, 121.078, 105.205
1.0040, 121.934, 107.660
1.0120, 122.628, 110.040
1.0200, 123.157, 112.347
1.0280, 123.474, 114.556
1.0360, 123.588, 116.626
1.0440, 123.482, 118.516
1.0520, 123.162, 120.229
1.0600, 122.658, 121.752
1.0690, 121.962, 123.056
1.0770, 121.106, 124.126
1.0850, 120.110, 124.980
1.0930, 118.957, 125.600
1.1010, 117.647, 125.960
1.1090, 116.171, 126.060
1.1170, 114.546, 125.893
1.1250, 112.801, 125.472
1.1330, 110.953, 124.789
1.1410, 109.037, 123.847
1.1490, 107.019, 122.655
1.1580, 104.762, 121.210
1.1660, 102.166, 119.497
1.1740, 99.053, 117.511
1.1820, 95.115, 115.201
1.1900, 89.982, 112.504
1.1980, 83.154, 109.316
1.2060, 75.092, 105.625
1.2140, 65.629, 101.581
1.2220, 54.673, 97.740
1.2300, 43.762, 94.179
1.2390, 34.323, 102.803
1.2470, 26.591, 105.126
1.2550, 20.577, 100.505
1.2630, 16.324, 104.010
1.2710, 13.029, 101.535
1.2790, 10.228, 100.941
1.2870, 7.973, 101.144
1.2950, 6.378, 99.927
1.3030, 5.501, 99.556
1.3110, 5.005, 99.253
1.3190, 4.670, 98.109
1.3280, 4.417, 98.093
1.3360, 4.280, 97.291
1.3440, 4.309, 96.558
1.3520, 4.466, 96.507
1.3600, 4.688, 95.313
1.3680, 4.915, 95.312
1.3760, 5.103, 94.442
1.3840, 5.258, 93.902
1.3920, 5.408, 93.577
1.4000, 5.576, 92.756
1.4090, 5.785, 92.450
1.4170, 6.037, 91.827
1.4250, 6.328, 91.238
1.4330, 6.654, 90.816
1.4410, 7.008, 90.215
1.4490, 7.383, 89.695
1.4570, 7.766, 89.284
1.4650, 8.149, 88.629
1.4730, 8.519, 88.209
1.4810, 8.866, 87.699
1.4890, 9.183, 87.083
1.4980, 9.468, 86.743
1.5060, 9.732, 86.115
1.5140, 9.980, 85.656
1.5220, 10.222, 85.223
1.5300, 10.465, 84.956
1.5380, 10.715, 85.077
1.5460, 10.978, 85.022
1.5540, 11.257, 84.996
1.5620, 11.560, 85.081
1.5700, 11.889, 84.992
1.5790, 12.243, 85.043
1.5870, 12.616, 85.045
1.5950, 13.001, 85.004
1.6030, 13.393, 85.053
1.6110, 13.786, 85.024
1.6190, 14.173, 85.024
1.6190, 14.182, 85.025
{{< /chart >}}

{{< chart height="250" xlabel="t (s)" ylabel="flow rate" caption="Figure 13. AV: axial flow rate on the two faces of the background grid (same arbitrary units as the §1 curves). The sign change is the closing transient." >}}
t, flow rate
0.0000, -0.000
0.0081, -207.927
0.0162, 168.164
0.0243, 19.486
0.0324, -100.964
0.0405, 65.079
0.0486, 65.927
0.0567, 2.277
0.0648, -42.250
0.0729, -9.415
0.0810, 35.089
0.0891, 61.851
0.0972, 77.329
0.1052, 93.145
0.1133, 122.862
0.1214, 150.639
0.1295, 186.847
0.1376, 229.403
0.1457, 279.412
0.1538, 326.973
0.1619, 369.180
0.1700, 411.104
0.1781, 447.217
0.1862, 477.865
0.1943, 500.831
0.2024, 518.388
0.2105, 530.380
0.2186, 536.165
0.2267, 537.428
0.2348, 532.682
0.2429, 523.766
0.2510, 510.331
0.2590, 491.860
0.2671, 468.377
0.2752, 440.631
0.2833, 409.441
0.2914, 374.858
0.2995, 337.419
0.3076, 297.417
0.3157, 256.111
0.3238, 212.604
0.3319, 167.544
0.3400, 122.029
0.3481, 74.882
0.3562, 27.755
0.3643, -5.528
0.3724, -7.470
0.3805, -9.499
0.3886, -11.901
0.3967, -14.604
0.4048, -17.717
0.4128, -20.717
0.4209, -23.156
0.4290, -25.053
0.4371, -26.317
0.4452, -27.201
0.4533, -27.621
0.4614, -27.957
0.4695, -28.117
0.4776, -28.042
0.4857, -27.841
0.4938, -169.879
0.5019, -401.674
0.5100, -467.119
0.5181, 67.891
0.5262, -29.303
0.5343, -23.831
0.5424, 18.438
0.5505, -20.073
0.5586, 5.861
0.5667, 1.434
0.5747, -3.546
0.5828, 1.150
0.5909, 9.049
0.5990, -14.576
0.6071, 17.011
0.6152, -13.423
0.6233, 7.712
0.6314, 0.762
0.6395, -5.203
0.6476, 9.604
0.6557, -6.459
0.6638, 3.586
0.6719, 0.212
0.6800, -1.478
0.6881, 2.936
0.6962, 0.425
0.7043, -0.525
0.7124, 2.270
0.7205, -1.130
0.7286, -0.024
0.7367, 2.324
0.7447, -2.027
0.7528, 2.491
0.7609, 0.092
0.7690, -0.591
0.7771, 2.398
0.7852, -1.607
0.7933, 1.586
0.8014, 0.435
0.8095, -0.268
0.8176, 1.388
0.8257, -0.776
0.8338, 2.129
0.8419, 2.625
0.8500, 4.414
0.8581, 8.101
0.8662, 10.800
0.8743, 13.679
0.8824, 18.491
0.8905, 25.255
0.8986, 32.735
0.9066, 40.253
0.9147, 52.116
0.9228, 72.496
0.9309, 104.285
0.9390, 139.871
0.9471, 178.622
0.9552, 222.602
0.9633, 268.484
0.9714, 315.258
0.9795, 360.332
0.9876, 400.196
0.9957, 433.903
1.0040, 461.719
1.0120, 484.035
1.0200, 501.646
1.0280, 514.459
1.0360, 521.971
1.0440, 523.703
1.0520, 520.483
1.0600, 512.635
1.0690, 499.861
1.0770, 482.475
1.0850, 461.480
1.0930, 436.850
1.1010, 408.315
1.1090, 376.380
1.1170, 341.258
1.1250, 303.677
1.1330, 263.721
1.1410, 221.774
1.1490, 178.313
1.1580, 133.382
1.1660, 86.721
1.1740, 38.407
1.1820, -12.829
1.1900, -68.490
1.1980, -130.932
1.2060, -199.644
1.2140, -269.458
1.2220, -324.676
1.2300, -364.477
1.2390, -45.681
1.2470, 33.387
1.2550, -82.875
1.2630, 45.316
1.2710, -14.953
1.2790, -11.307
1.2870, 11.543
1.2950, -7.508
1.3030, -0.165
1.3110, 7.560
1.3190, -9.753
1.3280, 7.909
1.3360, -0.482
1.3440, -4.258
1.3520, 10.314
1.3600, -8.763
1.3680, 8.412
1.3760, -2.034
1.3840, -1.018
1.3920, 5.118
1.4000, -3.240
1.4090, 3.968
1.4170, 0.976
1.4250, -0.571
1.4330, 2.618
1.4410, 0.114
1.4490, 0.417
1.4570, 3.487
1.4650, -0.776
1.4730, 2.217
1.4810, 1.896
1.4890, -1.213
1.4980, 3.679
1.5060, -0.318
1.5140, 1.107
1.5220, 2.733
1.5300, -1.319
1.5380, 2.349
1.5460, 0.672
1.5540, -0.111
1.5620, 2.468
1.5700, -0.217
1.5790, 1.319
1.5870, 1.384
1.5950, 0.130
1.6030, 1.619
1.6110, 0.756
1.6190, 0.750
1.6190, 0.771
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
