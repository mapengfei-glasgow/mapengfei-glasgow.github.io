---
title: "FDM-3D v1: environment, build and run"
description: "A clean, host-independent guide to the runtime environment, CPU/GPU dependencies, geometry-data preparation, CMake builds, tests and the first AV/MV runs of the fdm-3d-v1 workspace."
date: 2026-09-14
academic: true
ShowToc: true
TocOpen: false
---

This page is the clean entry point for **what to install, how to build, and how
to run** the `fdm-3d-v1` workspace. The hostname-specific logs remain in
`fdm-3d-v1-memory/compiling_running/` and should be used only when a machine
needs special handling; the common workflow is below.

## 1. Repository graph

The workspace is a super-repo with independent sub-repositories:

| Repository | Role | Consumes |
|---|---|---|
| `fdm-3d-v1` | header-only CPU solver: `fdm`, `common`, `ibm` | spdlog, OpenMP |
| `fdm-3d-v1-tests` | 58-item CTest regression suite | `FDM3D_SOURCE_DIR`, `GEOMETRY_SOURCE_DIR` |
| `fdm-3d-v1-bench` | OpenFOAM comparison benchmarks | `FDM3D_SOURCE_DIR` |
| `fdm-3d-v1-demo` | CPU demo executables (`tube_flow`, `real_av`, `real_mv`, …) | `FDM3D_SOURCE_DIR`, `GEOMETRY_SOURCE_DIR` |
| `fdm-3d-v1-geometry` | mesh/solid-data pipeline and `src/ibm/data/<case>/` | dolfinx/gmsh Python stack |
| `fdm-3d-v1-gpu` | CUDA demos/tests (fluid GPU, solid CPU or GPU) | `FDM3D_SOURCE_DIR`, `GEOMETRY_SOURCE_DIR`, CUDA, HDF5 |
| `fdm-3d-v1-memory` | project documentation and agent memory | — |

The usual layout is all repositories side by side, so the default
`../fdm-3d-v1` and `../fdm-3d-v1-geometry` paths work without extra CMake flags.

## 2. Runtime environment

| Component | Minimum / tested | Notes |
|---|---|---|
| CMake | 3.16 CPU, 3.20 GPU | Release build is the default |
| C++ compiler | GCC 13/14/15, Clang | C++17; CPU and GPU builds must use a compiler whose C++ ABI is consistent with CUDA |
| OpenMP | compiler runtime | used by CPU solver/demos/tests |
| spdlog + fmt | matched pair | `spdlog` must link the same `fmt` ABI it was compiled against |
| CUDA toolkit | driver-compatible toolkit | `nvcc`; simplest is `-DCMAKE_CUDA_ARCHITECTURES=native` |
| HDF5 | GPU build only | development headers and libraries |
| Python | 3.12 | only for the geometry data pipeline |
| dolfinx | 0.10 (`afsi-dolfinx`) | geometry `.geo`/XDMF → solver `.bin` conversion |
| h5py, mpi4py, gmsh, numpy, scipy | geometry pipeline | versions are pinned by `fdm-3d-v1-geometry` |

> The geometry repository is the authority on the Python environment; use its
> `scripts/prepare_solver_data.sh` and do not upgrade dolfinx casually.  A
> different dolfinx/basix version changes the generated solid data.

## 3. First-time setup

Clone the workspace with submodules:

```bash
git clone --recurse-submodules \
  https://github.com/mapengfei-glasgow/fdm-3d-v1-workspace.git
cd fdm-3d-v1-workspace
# or, if already cloned:
git submodule update --init --recursive
```

Generate the solver data once.  `src/ibm/data/<case>/` contains derived binary
data and is not stored in the repository, so a fresh clone has no solid meshes:

```bash
conda create -n afsi-dolfinx -c conda-forge python=3.12 \
  "dolfinx=0.10" h5py mpi4py gmsh numpy scipy
conda activate afsi-dolfinx

cd fdm-3d-v1-geometry
scripts/prepare_solver_data.sh --only tube av mv_gao_0
python scripts/validate_mesh_rules.py
```

For the AV/MV FSI cases in this site, `av` and `mv_gao_0` are sufficient.
The full data set takes roughly 30–60 minutes.

## 4. CPU build

Use a sibling layout and set the workspace root:

```bash
WS=/path/to/fdm-3d-v1-workspace
CMAKE_BASE=(-DCMAKE_BUILD_TYPE=Release)

# 1) core header-only library (configure + build for verification)
cmake -S "$WS/fdm-3d-v1" -B "$WS/fdm-3d-v1/build" "${CMAKE_BASE[@]}"
cmake --build "$WS/fdm-3d-v1/build" -j8

# 2) benchmark
cmake -S "$WS/fdm-3d-v1-bench" -B "$WS/fdm-3d-v1-bench/build" \
  "${CMAKE_BASE[@]}"
cmake --build "$WS/fdm-3d-v1-bench/build" -j8

# 3) full regression suite
cmake -S "$WS/fdm-3d-v1-tests" -B "$WS/fdm-3d-v1-tests/build" \
  -DGEOMETRY_SOURCE_DIR="$WS/fdm-3d-v1-geometry" "${CMAKE_BASE[@]}"
cmake --build "$WS/fdm-3d-v1-tests/build" -j8

# 4) CPU demos
cmake -S "$WS/fdm-3d-v1-demo" -B "$WS/fdm-3d-v1-demo/build" \
  -DGEOMETRY_SOURCE_DIR="$WS/fdm-3d-v1-geometry" "${CMAKE_BASE[@]}"
cmake --build "$WS/fdm-3d-v1-demo/build" -j8
```

If `fdm-3d-v1` and `fdm-3d-v1-geometry` are not siblings, add:

```bash
-DFDM3D_SOURCE_DIR=/path/to/fdm-3d-v1
-DGEOMETRY_SOURCE_DIR=/path/to/fdm-3d-v1-geometry
```

Run the main checks:

```bash
# core regression (58 tests, about 30–45 min for the full suite)
OMP_NUM_THREADS=4 ctest --test-dir "$WS/fdm-3d-v1-tests/build" -j4 --output-on-failure

# OpenFOAM comparison, if OpenFOAM is available
OMP_NUM_THREADS=4 ctest --test-dir "$WS/fdm-3d-v1-bench/build" \
  -R openfoam_bench --output-on-failure

# smoke app
OMP_NUM_THREADS=4 "$WS/fdm-3d-v1-demo/build/tube_flow" --T 0.01
```

`OMP_NUM_THREADS=4` is the tested setting for tests and benchmarks; the machines
in the project often have many cores and oversubscription makes timings useless.

## 5. GPU build

`fdm-3d-v1-gpu` requires `nvcc` plus HDF5.  Use the toolkit that matches the
installed NVIDIA driver, not merely the newest `/usr/local/cuda`:

```bash
WS=/path/to/fdm-3d-v1-workspace
cmake -S "$WS/fdm-3d-v1-gpu" -B "$WS/fdm-3d-v1-gpu/build" \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_CUDA_ARCHITECTURES=native \
  -DGEOMETRY_SOURCE_DIR="$WS/fdm-3d-v1-geometry"
cmake --build "$WS/fdm-3d-v1-gpu/build" -j8
ctest --test-dir "$WS/fdm-3d-v1-gpu/build"
```

On a machine with a non-standard CUDA location, add:

```bash
-DCMAKE_CUDA_COMPILER=/path/to/nvcc
```

On Ubuntu systems whose HDF5 comes from OpenMPI, the tested extra flags are:

```bash
-DCMAKE_EXE_LINKER_FLAGS="-L/usr/lib/x86_64-linux-gnu/hdf5/openmpi" \
-DCMAKE_CUDA_FLAGS="-I$WS/fdm-3d-v1/src/model -I/usr/lib/x86_64-linux-gnu/openmpi/include" \
-DCMAKE_CXX_FLAGS="-I/usr/lib/x86_64-linux-gnu/openmpi/include"
```

The GPU solver keeps CPU/GPU bitwise alignment in mind: `-fmad=false` is set by
CMake, and the CPU side uses `-ffp-contract=off`.  Do not add `-ffast-math` or
change these if you need the cross-validation tests to pass.

## 6. Run the two production AV/MV cases

The full command matrices, pressure/flow figures and PyVista deformation
snapshots are on the [AV/MV FSI debugging summary](/posts/av-mv-fsi-debugging/).
The two commands below are the short version.

### MV complete cardiac cycle

```bash
cd "$WS/fdm-3d-v1-gpu"
DSH_CS_POIS=20 DSH_CS_HELM=8 DSH_FLAT_ASM=1 OMP_NUM_THREADS=8 \
./build/real_mv --variant gao_0 --N 64 --T 0.785 --dt 6.25e-6 \
  --beta 1.0 --beta-body 1e8 --pk1-mask all --tether-mask 5,6,11,12 \
  --mv-Jclip 0.2 --mv-rigid-c1 1e7 \
  --mv-C1-ant 5.2110e6 --mv-af-ant 9.43788e6 \
  --mv-C1-post 3.06e6 --mv-af-post 1.5e7 \
  --nvc 2 --helm-nvc 1 --gpu-solid --every 10000 --out out_real_mv_cycle/
```

### AV full cycle with the fibre model

```bash
cd "$WS/fdm-3d-v1-gpu"
./build/real_av --N 64 --pk1-mask 15,16,18 --tether-mask 5,17 \
  --beta-body 5e8 --z-clear 0.2 --radius 1.24 --feedback --feedback-kappa 1e5 \
  --open-bc --av-iso-form mny --av-beta-s 5e6 \
  --windkessel --wk-old --wk-freeze 0 --nvc 2 --helm-nvc 1 \
  --machine-error --dt 5e-6 --T 1.635 --every 1000 --out out_fiber_full/
```

If the build directory is named differently, replace `build/` with the actual
directory (this workspace has used `build-av/` for the newer CMake cache).

## 7. Common build problems

| Symptom | Cause | Fix |
|---|---|---|
| `undefined reference to spdlog::...fmt::v12...` | conda `fmt` 12 found before the system `fmt` 10 used by spdlog | `-Dfmt_DIR=/usr/lib/x86_64-linux-gnu/cmake/fmt -DCMAKE_IGNORE_PREFIX_PATH=$HOME/miniconda3` |
| `CMAKE_ROOT not found` on no-root Ubuntu | unpacked only `cmake` binary, not `cmake-data` and `librhash1` | unpack all three `.deb` files into the local prefix |
| CUDA program compiles but reports driver/runtime mismatch | toolkit newer than the driver | build with the driver-compatible toolkit, e.g. CUDA 12.x for an older 5xx driver |
| `fdm-3d-v1 not found` | no sibling layout | pass `-DFDM3D_SOURCE_DIR=...` |
| `fdm-3d-v1-geometry not found` | no sibling layout or data absent | pass `-DGEOMETRY_SOURCE_DIR=...` and run the geometry data generation step |
| HDF5 symbols or `mpi.h` missing on Ubuntu | OpenMPI-variant HDF5 | add the HDF5/OpenMPI `-L`/`-I` flags shown in §5 |
| tests crawl or timings are noisy | OpenMP oversubscription | use `OMP_NUM_THREADS=4` and `ctest -j4` |
| `src/ibm/data/<case>` missing after clone | binary solid data are not tracked | run `scripts/prepare_solver_data.sh --only <case>` |

The exact per-host package recipes, including no-root `.deb` extraction and
CUDA-version choices, are in
`fdm-3d-v1-memory/compiling_running/<hostname>.md`; the dependency overview is
`fdm-3d-v1-memory/docs/getting-started/dependencies.md`.
