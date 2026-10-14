---
title: "Mitral-valve FSI on GPUs with a nodal immersed finite element / finite difference method"
description: "Working paper. Sign in with your site sync code to read."
date: 2026-10-14
layout: protected-paper
academic: true
comments: false
searchHidden: true
build:
  list: never
---

Working document, 2026-10-14. This page records how to rerun the reference mitral-valve case **glamv-0.0.3**
with the GPU solver `gla_mv`, and the flow rate it produces, sampled every 0.01 s (135 samples).
The instructions follow `fdm-3d-v1-gpu/docs/RUN_GLAMV.md` (branch `gpu-perf-base`); every command below was run
as written on 2026-10-14. (The earlier draft of this page, with the run register and hex-mesh study, is in the
site repo history, commit `13c1fc3`.)

## 1. The case

Mitral valve FSI in a tube (Nancy GlaTube geometry, IBAMR SarahNodalMV setup):

| Item | Value |
|---|---|
| Solid | `glamv_ibamr`: P1 tetrahedra, 29,524 nodes / 80,074 cells (tube, housing disc, anterior and posterior leaflets, annulus, chordae, papillary caps) |
| Materials | SarahNodalMV: HGO leaflets with fibres, transversely isotropic chordae, neo-Hookean tube/disc; volumetric penalty $\beta_s = 5\times10^6$ |
| Fluid | $64\times64\times96$ grid on $8.6\times8.6\times16.2$ cm, $\rho = 1$, $\mu = 0.04$ P |
| Coupling | nodal IFED, composite B-spline kernel CBS43 |
| Loading | IBAMR LV–LA pressure waveform at the inlet (`lvla_pressure_closing.inlet`), $T = 1.335$ s (two cycles) |
| Outside the tube | gap mask (fluid at rest for $r \ge 3.6$ cm) and passive rim (disc cells beyond $r = 3.73$ cm force-free) |
| Time step | $\Delta t = 2\times10^{-5}$ s, 66,750 steps |

## 2. Prerequisites

| Item | Reference machine (runbook) | Also tested (this run) |
|---|---|---|
| GPU / driver | RTX 5070 Laptop, 595.99 | RTX PRO 5000 Blackwell, 595.71 |
| CUDA toolkit | 13.1 (`/usr/local/cuda-13.1`); ≥ 12.8 for RTX 50xx / Blackwell (sm_120) | 13.2 (`nvcc` from a conda env) |
| Host compiler | g++-13 | g++-15 |
| Libraries | `libhdf5-dev`, `libsqlite3-dev` | HDF5 in a local prefix |
| Python | numpy (post-processing only) | numpy 2 |
| GPU memory | 0.35 GB | 0.58 GB |

## 3. Code and data

```bash
git clone --recurse-submodules -b gpu-perf-base git@github.com:mapengfei-glasgow/fdm-3d-v1-workspace.git
cd fdm-3d-v1-workspace
# existing clone instead:  git checkout gpu-perf-base && git pull && git submodule update --init --recursive
ls fdm-3d-v1-geometry/src/ibm/data/glamv_ibamr/        # the solid data, *.bin files (~23 MB), plain git
```

If `git-lfs` is not installed, the submodule update stops on an LFS file of `fdm-3d-v1` that the run does not use;
prefix the command with `GIT_LFS_SKIP_SMUDGE=1`.

## 4. Build (once, ~30 s)

```bash
export PATH=/usr/local/cuda-13.1/bin:$PATH
cmake -S fdm-3d-v1-gpu -B fdm-3d-v1-gpu/build -DCMAKE_BUILD_TYPE=Release -DFDM3D_GPU_FMAD=ON \
  -DCMAKE_CUDA_COMPILER=/usr/local/cuda-13.1/bin/nvcc -DCMAKE_CUDA_ARCHITECTURES=120 \
  -DCMAKE_CUDA_HOST_COMPILER=/usr/bin/g++-13 -DCMAKE_CXX_COMPILER=/usr/bin/g++-13 \
  -DCMAKE_EXE_LINKER_FLAGS=-L/usr/lib/x86_64-linux-gnu/hdf5/serial
cmake --build fdm-3d-v1-gpu/build --target gla_mv -j
```

- `CMAKE_CUDA_ARCHITECTURES`: 120 = RTX 50xx / RTX PRO Blackwell, 89 = RTX 40xx / Ada, 86 = RTX 30xx.
- `FDM3D_GPU_FMAD=ON` is required for performance level D (`DSH_PERF_LEVEL=3`, §5).
- The linker flag is for Ubuntu, which keeps `libhdf5_cpp` under `hdf5/serial/`. With HDF5 in another prefix, add
  `-DCMAKE_PREFIX_PATH=<prefix>` and point the linker flag at `<prefix>/lib/x86_64-linux-gnu/hdf5/serial`
  (plus `-Wl,-rpath,<same dir>` so the binary finds it at run time).
- Other toolkits / compilers: replace the `nvcc` and `g++` paths; nothing else changes.

## 5. Run (~10 min)

From `fdm-3d-v1-gpu/`. `--every 500` writes a fluid + solid frame every 0.01 s (135 frames, ≈ 4.9 GB), which gives
the flow-rate samples of §7; the runbook default `--every 2000` (0.04 s, 35 frames, ≈ 1.3 GB) gives 35.

```bash
cd fdm-3d-v1-gpu
OUT=out_glamv003_every500
DSH_PERF_LEVEL=3 ./build/gla_mv --N 64 --T 1.335 --dt 2e-5 --sarah \
  --data-dir ../fdm-3d-v1-geometry/src/ibm/data/glamv_ibamr/ --inlet lvla_pressure_closing.inlet \
  --beta-s 5e6 --nu 0.04 --nvc 8 --helm-nvc 2 --max-u 2000 --solid-nu 1e3 \
  --gap-mask 3.6 --gap-ramp 0.13 --gap-iters -1 --passive-rim 3.73 --ib-kernel cbs43 \
  --every 500 --checkpoint-every 20000 --out $OUT/ > $OUT.console.log 2>&1
```

| Option | Meaning |
|---|---|
| `DSH_PERF_LEVEL=3` | performance level D (mixed-precision multigrid, warm-started pressure), ≈ 8–9 ms/step; `0` = reference path, ≈ 19 ms/step |
| `--N 64` | fluid grid $64\times64\times96$ |
| `--T 1.335 --dt 2e-5` | end time, time step |
| `--sarah --beta-s 5e6` | SarahNodalMV materials, volumetric penalty |
| `--data-dir …/glamv_ibamr/` | solid data (must end in `/`) |
| `--inlet lvla_pressure_closing.inlet` | inlet pressure waveform |
| `--nu 0.04` | viscosity |
| `--nvc 8 --helm-nvc 2` | multigrid V-cycles per step (pressure / momentum) |
| `--max-u 2000` | abort above 2000 cm/s |
| `--solid-nu 1e3` | Kelvin–Voigt solid viscosity |
| `--gap-mask 3.6 --gap-ramp 0.13 --gap-iters -1` | keep the fluid outside the tube at rest |
| `--passive-rim 3.73` | disc cells outside the tube carry no force |
| `--ib-kernel cbs43` | composite B-spline coupling kernel |
| `--every 500` | frame interval in steps (0.01 s) |
| `--checkpoint-every 20000` | restart file `$OUT/checkpoint_latest.bin` |

- Progress: `tail -f $OUT/sim.log` (columns: step, t, $p_{in}$, max|u|, max|f|, |u|², |div u|).
- Interrupted: Ctrl+C writes the checkpoint; resume with the same command plus `--restart $OUT/checkpoint_latest.bin`.
- The run stops by itself on NaN or when max|u| exceeds `--max-u`.

This run: 66,750 steps in ≈ 9 min (8.1 ms/step), RTX PRO 5000.

## 6. Check the result

```bash
python3 tools/perf/glamv_flowrate.py $OUT
```

`sim.log` must end with `66750   1.3350 …` and contain no `nan`. This run: completed, last line
`66750 1.3350 -3394.0769 5.74e-01 …`; max|u| peaks at 1.18 at $t = 0.32$ s, as in the runbook.

| Metric (lumen flow rate, $z = 0$ face, $r \le 3.5$ cm) | Runbook (0.04 s frames) | This run (0.04 s frames, `--every 2000`) | This run (0.01 s frames) | IBAMR |
|---|---|---|---|---|
| forward plateau, mean of frames in 0.10–0.16 s | 415.3 cm³/s | 415.3 | 412.4 | ≈ 370 |
| forward volume, 0–0.2 s (trapezoid on the frames) | 39.57 cm³ | 39.57 | 38.75 | 35.2 |
| closing spike, $Q(0.20\ \mathrm{s})$ | −471.9 cm³/s | −471.9 | −471.9 | −516 |

With `--every 2000` the run matches the runbook to every digit shown. With 0.01 s frames the plateau and volume
change slightly only because they are averages/integrals over different sample sets (7 frames instead of 2 in the
plateau window; finer trapezoid); the flow itself is the same (the spike at 0.20 s is identical).

## 7. Flow rate, every 0.01 s

Lumen flow rate $Q(t) = \int w\,\mathrm{d}A$ over the inlet face $z = 0$, $r \le 3.5$ cm (+z = forward), from the 135 fluid
frames of the run in §5. The IBAMR column is the reference run's inlet flux at the same times (it was run to 0.65 s only).

{{< chart height="380" xlabel="t (s)" ylabel="Q through the tube lumen (cm³/s)" colors="#30638e,#d1495b" caption="Figure 1. Lumen flow rate of glamv-0.0.3 (gla_mv, 64×64×96, P1 solid, CBS43, Δt = 2×10⁻⁵, DSH_PERF_LEVEL=3, FMA on) every 0.01 s, against the IBAMR SarahNodalMV reference (inlet flux, to 0.65 s)." >}}
t, gla_mv glamv-0.0.3, IBAMR reference
0.000, 0.00, 0.00
0.010, 0.00, 1.58
0.020, 0.00, 2.06
0.030, 15.33, 16.91
0.040, 54.14, 57.00
0.050, 110.68, 111.79
0.060, 183.39, 179.27
0.070, 267.92, 253.13
0.080, 340.48, 309.29
0.090, 387.70, 344.96
0.100, 413.43, 369.99
0.110, 421.21, 381.61
0.120, 415.11, 373.88
0.130, 407.55, 364.28
0.140, 405.63, 363.74
0.150, 408.70, 370.89
0.160, 415.42, 385.03
0.170, 256.13, 239.10
0.180, -7.87, -24.66
0.190, -384.03, -371.83
0.200, -471.95, -488.22
0.210, 132.28, 13.80
0.220, -44.07, 5.27
0.230, -126.53, -2.47
0.240, -19.49, -27.31
0.250, -63.34, -76.21
0.260, -53.61, -18.33
0.270, -35.26, -22.45
0.280, -55.03, -55.48
0.290, -38.75, -19.11
0.300, -38.61, -17.40
0.310, -36.78, -29.10
0.320, -37.37, -19.85
0.330, -35.85, -15.14
0.340, -31.60, -18.51
0.350, -32.45, -19.16
0.360, -37.10, -19.18
0.370, -33.75, -17.82
0.380, -28.78, -15.60
0.390, -26.14, -14.92
0.400, -28.43, -13.69
0.410, -25.04, -13.70
0.420, -28.13, -12.32
0.430, -23.97, -12.15
0.440, -22.98, -11.21
0.450, -25.91, -10.24
0.460, -17.72, -9.84
0.470, -19.23, -8.61
0.480, -19.37, -7.05
0.490, -15.16, -4.16
0.500, -15.49, -2.59
0.510, -12.54, -0.83
0.520, -6.83, 0.83
0.530, -2.00, 2.80
0.540, 12.41, 5.79
0.550, 29.96, 9.94
0.560, 45.29, 14.99
0.570, 60.96, 19.70
0.580, 66.93, 22.54
0.590, 70.66, 23.76
0.600, 180.92, 451.84
0.610, 342.03, 526.13
0.620, 471.09, 516.46
0.630, 540.94, 547.38
0.640, 555.53, 535.47
0.650, 535.74, 474.88
0.660, 494.69, 
0.670, 461.00, 
0.680, 443.74, 
0.690, 431.45, 
0.700, 411.06, 
0.710, 394.59, 
0.720, 381.38, 
0.730, 371.91, 
0.740, 364.46, 
0.750, 359.48, 
0.760, 355.07, 
0.770, 349.36, 
0.780, 338.75, 
0.790, 339.55, 
0.800, 337.91, 
0.810, 336.01, 
0.820, 336.02, 
0.830, 335.21, 
0.840, 333.12, 
0.850, 327.74, 
0.860, 322.95, 
0.870, 320.46, 
0.880, 315.78, 
0.890, 308.10, 
0.900, 297.61, 
0.910, 154.32, 
0.920, -94.59, 
0.930, -454.96, 
0.940, -306.61, 
0.950, 113.94, 
0.960, -86.09, 
0.970, -106.53, 
0.980, -21.00, 
0.990, -72.16, 
1.000, -47.01, 
1.010, -42.16, 
1.020, -55.50, 
1.030, -42.41, 
1.040, -39.68, 
1.050, -35.04, 
1.060, -34.04, 
1.070, -31.20, 
1.080, -30.19, 
1.090, -30.78, 
1.100, -31.32, 
1.110, -30.19, 
1.120, -26.38, 
1.130, -27.55, 
1.140, -22.23, 
1.150, -24.12, 
1.160, -26.78, 
1.170, -24.72, 
1.180, -20.90, 
1.190, -25.29, 
1.200, -22.16, 
1.210, -15.55, 
1.220, -20.47, 
1.230, -10.66, 
1.240, -12.88, 
1.250, -11.70, 
1.260, -8.41, 
1.270, -1.77, 
1.280, 10.51, 
1.290, 29.32, 
1.300, 46.23, 
1.310, 60.11, 
1.320, 68.90, 
1.330, 72.33, 
1.335, 117.12,
{{< /chart >}}

Key values from these samples:

| Quantity | gla_mv | IBAMR (same times) |
|---|---|---|
| First peak forward flow | 421.2 cm³/s at 0.11 s | 385.0 at 0.16 s |
| Closing spike | −472.0 cm³/s at 0.20 s | −488.2 at 0.20 s |
| Second-cycle peak | 555.5 cm³/s at 0.64 s | 535.5 at 0.64 s |
| Second closing spike | −455.0 cm³/s at 0.93 s | — |
| Volume 0–0.2 s / 0.2–0.56 s | 38.75 / −10.76 cm³ | — |
| Volume 0.56–0.9 s / 0.9–1.28 s | 117.66 / −14.71 cm³ | — |

The samples are also printed by the script in §6 (`t:` and `Q:` lines); the full-precision values above were
computed with the same integral.

## 8. View in ParaView

```bash
python3 scripts/solid_to_vtu_numpy.py $OUT --markers ../fdm-3d-v1-geometry/src/ibm/data/glamv_ibamr
paraview $OUT/fluid.pvd $OUT/vtu/solid.pvd
```

- `fluid.pvd`: `velocity`, `u`, `v`, `w`, `pressure`, `vorticity_mag`, `ibm_force`.
- `vtu/solid.pvd`: current geometry, `displacement`, `cell_marker` (tube 1, disc 42, anterior leaflet 3 5 7 23 25,
  posterior leaflet 4 24, annulus 4099 5099, chordae 100 200 300, papillary tips 1001–1005 2001–2005).
- Vortex rings: *Gradient* of `velocity` with *Compute QCriterion* → *Contour* at a small positive Q; or a *Slice*
  at $x = 4.3$ coloured by `vorticity_mag`.

## 9. If something fails

| Symptom | Cause / fix |
|---|---|
| CMake: `fdm-3d-v1-geometry not found` | submodules missing: `git submodule update --init --recursive` |
| `git-lfs filter-process: git-lfs: not found` during the submodule update | install git-lfs, or `GIT_LFS_SKIP_SMUDGE=1 git submodule update --init --recursive` |
| link error `cannot find -lhdf5_cpp` | add `-DCMAKE_EXE_LINKER_FLAGS=-L<dir of libhdf5_cpp.so>` (§4) |
| nvcc rejects architecture 120 | CUDA < 12.8: upgrade, or set `CMAKE_CUDA_ARCHITECTURES` for your GPU |
| CUDA error at start-up | driver not loaded (`nvidia-smi` fails) |
| solid data cannot be read | `--data-dir` must point at `…/src/ibm/data/glamv_ibamr/` and end in `/` |
| ≫ 9 ms/step | built without `-DFDM3D_GPU_FMAD=ON` or run without `DSH_PERF_LEVEL=3`; `[perf]` lines in `$OUT.console.log` give the split |
