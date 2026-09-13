---
title: "demo_405 — vessel-wall FSI with a valve (3-D)"
description: "demo_405: a tubular vessel wall (optionally merged with leaflets) in a hexahedral fluid box under a pulsatile plug inlet, with 3-D immersed-boundary coupling."
date: 2026-09-12
weight: 405
academic: true
---

## 1. What it is

A tubular vessel wall immersed in a $\mathrm{8 \times 8 \times 20}$ cm fluid box,
driven by a pulsatile plug inlet along the tube axis. The solid is an
unstructured tetrahedral mesh read from XDMF, optionally a *merged* vessel +
leaflets mesh whose cell tags separate the two parts: the vessel cells are held by
a volumetric penalty spring and the leaflet cells carry the neo-Hookean stress.
Three entry points exist — merged vessel + leaflets, vessel-only, and a copy named
for "valves".

{{< figure src="/afsi/demo405-setup.png" title="Figure 1. The vessel cross-section and an axial cut, with the cell tags that separate the wall from the leaflets." >}}

## 2. Configuration

<p class="tcaption">Table 1. Parameters (`configuration.py`, CGS). The solid mesh itself is not in the repository.</p>

| Quantity | Code name | Value |
|---|---|---|
| Fluid box | `Lx`, `Ly`, `Lz` | $8.0 \times 8.0 \times 20.0\,\mathrm{cm}$ |
| Fluid cells | `Nx`, `Ny`, `Nz` | $32 \times 32 \times 80$ hexahedra |
| Density / viscosity | `rho`, `mu` | $1.0\,\mathrm{g\,cm^{-3}}$ / $0.036\,\mathrm{dyn\,s\,cm^{-2}}$ |
| Inlet amplitude / frequency | `U_max`, `freq` | $1.0$ / $1.0\,\mathrm{Hz}$ |
| Inlet profile | literal | plug, $u_z = U_{max}\sin(2\pi f t)$ inside $r < R_{inner}$ (reverses each half cycle) |
| Lumen radius / centre | `R_inner`, `cx`, `cy` | $1.3\,\mathrm{cm}$ / $(4.0, 4.0)$ |
| Outlet | marker $6$ | $p = 0$ |
| Walls | markers $1$–$4$ | no-slip |
| Solid material | `NeoHookeanMaterial` | $E = 2\times10^{6}$, $\nu = 0.4$ for the leaflets; defaults ($E = 1\times10^{4}$, $\nu = 0.3$) in the vessel-only scripts |
| Cell tags | — | $1$ = vessel (penalty-fixed), $2$ = leaflets (neo-Hookean) |
| Penalty | `beta` | $1\times10^{6}$ |
| Solid shift | literal | $x + 3.5$, $y + 4.0$, $z + 5.0$ (private geometry-array mutation) |
| Velocity / force / pressure order | — | $\mathrm{P2}$ / $\mathrm{P2}$ / $\mathrm{P1}$ |
| Time step / end time | `dt`, `T` | $1/10\,000\,\mathrm{s}$ / $0.2\,\mathrm{s}$ ($2000$ steps) |
| Vessel mesh size (readme) | — | $141\,038$ nodes, $140\,612$ cells |

There are **no environment overrides**. Results are written to
`~/afsi-data/demo-405/vessel-wall-3d/<timestamp>/`, and the driver calls SwanLab
plus a remote counter service.

## 3. Files

| File | Role |
|---|---|
| `configuration.py` | Parameters for all three FSI scripts, output path, experiment name |
| `fsi_paralell.py` | Main driver named by the readme: reads `combined_vessel_leaflets.xdmf`, neo-Hookean on tag $2$, penalty on tag $1$ |
| `fsi_paralell_vessel.py` | Vessel-only variant; the elastic term is **commented out**, leaving only the penalty |
| `fsi_paralell_vessel_valves.py` | Byte-identical copy of the vessel-only script (same md5) |
| `merge_meshes.py` | Merges the vessel and leaflet tet meshes into `combined_vessel_leaflets.xdmf`, tagging cells $1/2$ by nearest-centroid matching |
| `NeoHookean.py` | `NeoHookeanMaterial` ($\psi = \frac{\mu}{2}(I_c-3) - \mu\ln J + \frac{\lambda}{2}(\ln J)^2$) |
| `PressureEndo.py` | Diastolic/systolic pressure ramp ($8$ / $110\,\mathrm{mmHg}$) — **imported by nothing** |

## 4. Running it

```bash
# merge the vessel and leaflet meshes (writes combined_vessel_leaflets.xdmf)
python3 merge_meshes.py

cd afsic/demo/demo_405
mpirun -np 4 python3 fsi_paralell.py
```

## 5. Results and notes

{{< figure src="/afsi/demo405-results.png" title="Figure 2. What the code applies and what it ships: the driver is driven by an inlet velocity, while `PressureEndo.py` — the only luminal-pressure model in the demo — is imported by nothing. Both curves are evaluated from the sources; no run data exists for this demo." >}}

**No results are archived**, and neither is any mesh file: the readme's
$141\,038$-node vessel mesh, `leaflets_M2_tet.xdmf` and the merged
`combined_vessel_leaflets.xdmf` are all absent, so neither the merge step nor the
driver can be reproduced from this checkout without the external meshes.

Caveats — read the readme against the code before reusing this case:

* `fsi_paralell_vessel_valves.py` is **byte-identical** to
  `fsi_paralell_vessel.py`, so the "vessel + valve" version the readme describes
  does not exist as a distinct implementation.
* `PressureEndo.py`, the only luminal-pressure implementation in the demo, is
  never imported; the readme's boundary conditions ("ends fixed, luminal pressure
  on the inner wall, outer wall free") are not what any script imposes — the
  penalty covers the whole vessel cell set and no pressure load is applied.
* In the vessel-only scripts the neo-Hookean term is commented out, so those runs
  are penalty-only (effectively rigid) regardless of the material parameters.
* The readme describes a wedge/prism vessel mesh while the merge script builds
  degree-1 tetrahedra, and the mesh *names* are inconsistent between the merge
  script (`name="Grid"`) and the drivers (`name="mesh"`, tags `"mesh_tags"`).
* The solid is massless: the velocity is interpolated from the fluid and the
  position advanced by explicit Euler, with no stability discussion.
* The mesh is repositioned by mutating the private geometry array
  (`structure._geometry._cpp_object.x[...]`), which is undocumented and breaks
  across dolfinx versions.
* $T = 0.2\,\mathrm{s}$ at $1\,\mathrm{Hz}$ covers only one fifth of a cycle, so
  periodicity is not established.
