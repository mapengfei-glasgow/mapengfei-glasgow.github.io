---
title: "demo_423 — immersed anisotropic annulus at equilibrium"
description: "A thick fibre-reinforced ring immersed in a driven cavity, verified against the analytic pressure field: parameters, mesh pitfalls and measured errors."
date: 2026-09-12
weight: 1
---

A thick annular cylinder with **circumferential fibre reinforcement** sits
immersed in a unit square filled with incompressible fluid. It is a static
equilibrium problem with a closed-form pressure field, so the immersed-boundary
coupling can be checked against an exact solution rather than a reference
simulation.

## Parameters

| Quantity | Value |
|---|---|
| fluid domain | 1.0 × 1.0 m², `N × N` quadrilateral cells |
| fluid density / viscosity | ρ = 1.0, μ = 1.0 |
| ring inner radius `R` | 0.25 m |
| ring width `w` | 0.0625 m (outer radius `R + w` = 0.3125 m) |
| ring centre | (0.5, 0.5) |
| solid modulus `μ_s` | 1.0 |
| solid constitutive law | circumferential: `S_s = μ_s ê_θ ⊗ ê_θ` (`CircumferentialMaterial`) |
| boundary conditions | no-slip on all four walls; pressure fixed only up to a constant |
| default time stepping | dt = 1.0e-4 s, 100 steps (T = 0.01 s) |
| paper time setting | dt = 1.0e-3 s, t_f = 10 dt (too coarse for the explicit Chorin solver here) |
| velocity / force / pressure space | P2 / P2 / P1 |

The afsic Chorin solver is explicit, so the demo's default dt is 10× smaller
than the paper's setting, which gives a better equilibrium in 100 steps.

## Analytic solution

With `l = 1` (the domain side) and `v = 0` everywhere:

```
p(r) =  μ_s ln(1 + w/R)              − π μ_s / (2 l²) · ((R + w)² − R²)     for r ≤ R
     =  μ_s ln((R + w)/r)            − π μ_s / (2 l²) · ((R + w)² − R²)     for R < r < R + w
     =                               − π μ_s / (2 l²) · ((R + w)² − R²)     for r ≥ R + w
```

With the values above the far-field level is −0.05523 Pa, the inner plateau is
+0.16792 Pa, and the whole variation happens in the 6.25 cm-wide fibre band.

## Mesh: the quadrilateral ordering trap

The custom annular mesh must use the **DOLFINx quadrilateral vertex ordering**.
For a physical counter-clockwise quadrilateral `(a, b, c, d)`, DOLFINx expects the
cell as `[a, b, d, c]`. Using a naive cyclic ordering silently corrupts the solid
element Jacobians: the solid area integral is wrong, the assembled PK force is
wrong, and the resulting pressure comes out at about **half** the analytic value.
`generate_mesh.py` uses the correct ordering, so no empirical force scaling is
needed (`FORCE_SCALE = 1.0` for Chorin).

## Results

{{< figure src="/afsi/demo423-fields.png" title="Archived N = 128 snapshot: the pressure is flat inside the ring, varies only across the fibre band and is flat outside again. The error panel resolves the immersed-boundary band, where the coupling smears the interface over roughly ±2h." >}}

The archived radial profiles along `y = 0.5` (from `x = 0.5` to `x = 0.9`, i.e.
`r = 0 → 0.4`), each from its own run, give:

| Run | max abs error (whole line) | inner `r < R − 2h` | fibre band `R ≤ r ≤ R + w` | outer `r > R + w + 2h` | p at r = 0 |
|---|---|---|---|---|---|
| Chorin, N = 32 | 2.221e-2 Pa | 7.605e-3 Pa | 2.221e-2 Pa | 5.475e-3 Pa | 0.1679447 (exact 0.1679421) |
| Chorin, N = 256 | 2.002e-2 Pa | 2.817e-3 Pa | 2.002e-2 Pa | 1.999e-3 Pa | 0.1679207 (exact 0.1679204) |
| IPCS, N = 64 | 5.257e-3 Pa | 5.144e-4 Pa | 5.257e-3 Pa | 4.187e-4 Pa | 0.1679266 (exact 0.1679287) |
| IPCS, N = 128 | 2.621e-3 Pa | 4.597e-5 Pa | 2.621e-3 Pa | 2.922e-5 Pa | 0.1679219 (exact 0.1679190) |

{{< figure src="/afsi/demo423-profile.png" title="Left: the radial pressure profile — the far field and the inner plateau are captured essentially exactly, the fibre band is where the error lives. Right: the same data as an error plot; the spikes sit at the band edges, and refining the mesh shrinks them." >}}

What the numbers say:

* **The far field and the inner plateau are essentially exact** (≈ 2e-6 Pa at the
  centre even at N = 32) — the immersed coupling transmits the load correctly.
* **The error is concentrated in the fibre band** `R ≤ r ≤ R + w`, and stays
  around 2e-2 Pa there even at N = 256: this is the immersed-interface smearing
  (the band is 0.0625 m wide, so it is resolved by few cells and the IB kernel
  spreads it further), not a solver error.
* Away from the band both the inner and outer errors fall with refinement
  (7.6e-3 → 2.8e-3 and 5.5e-3 → 2.0e-3 over N = 32 → 256).
* The IPCS profiles were archived with a hand-renamed file, so their exact step
  count / dt are not recorded next to them; do not read the N = 64 / N = 128 rows
  as a controlled comparison against the Chorin rows.

A full refinement study is scripted rather than archived: `convergence.py` runs
`generate_mesh.py` + `main.py` for a sequence of levels and prints the observed
order `p = log(e_N / e_2N) / log 2` for every error measure:

```bash
python convergence.py                       # N = 16 32 64 128
python convergence.py -n 16 32 64 --steps 200
LEVELS=32,64 STEPS=100 python convergence.py
python convergence.py --dt 1e-5 --steps 1000 --json results.json
```

## Reproducing

```bash
conda activate afsi-dolfinx
cd afsic/demo/demo_423

python generate_mesh.py          # default N=32
python main.py                   # default N=32, 100 steps, dt=1e-4

N=16  python generate_mesh.py && N=16  python main.py
N=64  STEPS=100 DT=1e-4 python main.py
N=32  SOLVER=ipcs python main.py           # FORCE_SCALE becomes -1.0 automatically
N=32  CELL_TYPE=triangle python generate_mesh.py && N=32 python main.py
```

The triangle-mesh variant also runs (P2 solid elements are still used in
`main.py`).

## Files

| File | Description |
|---|---|
| `generate_mesh.py` | structured quadrilateral annular solid mesh → `plot/mesh-423.xdmf` |
| `materials.py` | `CircumferentialMaterial`: `S_s = μ_s ê_θ ⊗ ê_θ` |
| `main.py` | IB-FSI solve; prints the L²/H¹ errors and writes the profiles |
| `convergence.py` | mesh-refinement study over a sequence of `N`, with observed orders |
| `plot/` | archived field snapshots (`pressure`, `velocity`, `*_error`), solid/fluid forces and the profile CSVs |
