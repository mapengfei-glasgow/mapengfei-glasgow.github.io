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

{{< chart height="250" xlabel="t (s)" ylabel="flow rate" caption="Figure 13. AV: axial flow rate on the two faces of the background grid (same arbitrary units as the §1 curves). The closing transients are the negative spikes at t ≈ 0.5 s and 1.1 s." >}}
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
