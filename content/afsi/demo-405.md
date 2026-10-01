---
title: "405: Vessel Wall with Merged Leaflets"
description: "A tubular vessel wall with merged leaflets under a pulsatile inlet."
date: 2026-09-12
weight: 405
academic: true
demo_id: demo_405
category: Application
dimension: 3D
solid_model: "vessel by penalty (tag 1); leaflets Neo-Hookean (tag 2, in the merged driver only); massless, explicit Euler"
coupling: "immersed boundary (`IBMesh3D`), serial only"
reference: "—"
status: WIP
---

## 1. Introduction

Three entry points exist — merged vessel + leaflets, vessel-only, and a copy named
for "valves". The solid is an unstructured tetrahedral mesh read from XDMF; in the
merged driver the vessel cells are held by a volumetric penalty spring and the
leaflet cells carry the neo-Hookean stress.

## 2. Problem description

### 2.1 Geometry

{{< figure src="/afsi/demo405-setup.png" title="Figure 1. The vessel cross-section and an axial cut, with the cell tags that separate the wall from the leaflets." >}}

The box is $8 \times 8 \times 20\,\mathrm{cm}$; the lumen of radius
$R_{inner} = 1.3\,\mathrm{cm}$ runs along the $z$ axis at $(4.0, 4.0)$. The
solid mesh itself is **not in the repository**; the readme quotes
$141\,038$ nodes / $140\,612$ cells for the vessel.

### 2.2 Governing equations

{{< color "red" >}}TODO: governing equations — incompressible Navier–Stokes, the
leaflet constitution (neo-Hookean),
$\psi = \frac{\mu}{2}(I_c-3) - \mu\ln J + \frac{\lambda}{2}(\ln J)^2$ as
implemented, and the IB coupling terms (see the symbol table page).{{< /color >}}

### 2.3 Boundary and initial conditions

{{< color "red" >}}TODO: boundary conditions as *imposed by the code* — the
readme's description does not match the scripts (see §5): the inlet is a plug
$u_z = U_{max}\sin(2\pi f t)$ inside $r < R_{inner}$ (markers), the outlet
(marker $6$) is at $p = 0$, and walls $1$–$4$ are no-slip as written, but the
luminal-pressure condition does not exist in any script.{{< /color >}}

### 2.4 Physical parameters

<p class="tcaption">Table 1. Parameters (`configuration.py`, CGS). The solid mesh itself is not in the repository.</p>

| Quantity | Code name | Value |
|---|---|---|
| Fluid box | `Lx`, `Ly`, `Lz` | $8.0 \times 8.0 \times 20.0\,\mathrm{cm}$ |
| Fluid cells | `Nx`, `Ny`, `Nz` | $32 \times 32 \times 80$ hexahedra |
| Density / viscosity | `rho`, `mu` | $1.0\,\mathrm{g\,cm^{-3}}$ / $0.036\,\mathrm{dyn\,s\,cm^{-2}}$ |
| Inlet amplitude / frequency | `U_max`, `freq` | $1.0$ / $1.0\,\mathrm{Hz}$ |
| Inlet profile | literal | plug, $u_z = U_{max}\sin(2\pi f t)$ inside $r < R_{inner}$ (reverses each half cycle) |
| Lumen radius / centre | `R_inner`, `cx`, `cy` | $1.3\,\mathrm{cm}$ / $(4.0, 4.0)$ |
| Solid material | `NeoHookeanMaterial` | $E = 2\times10^{6}$, $\nu = 0.4$ for the leaflets; defaults ($E = 1\times10^{4}$, $\nu = 0.3$) in the vessel-only scripts |
| Cell tags | — | $1$ = vessel (penalty-fixed), $2$ = leaflets (neo-Hookean) |
| Penalty | `beta` | $1\times10^{6}$ |
| Solid shift | literal | $x + 3.5$, $y + 4.0$, $z + 5.0$ (private geometry-array mutation) |
| Vessel mesh size (readme) | — | $141\,038$ nodes, $140\,612$ cells |

{{< color "red" >}}TODO: dimensionless numbers and the physiological pulse
($8/110\,\mathrm{mmHg}$ diastolic/systolic) that `PressureEndo.py` models but no
script applies.{{< /color >}}

## 3. Numerical setup

Velocity / force / pressure spaces are $\mathrm{P2}$ / $\mathrm{P2}$ /
$\mathrm{P1}$, with $\Delta t = 1/10\,000\,\mathrm{s}$ to $T = 0.2\,\mathrm{s}$
($2000$ steps) — only one fifth of the $1\,\mathrm{Hz}$ cycle, so periodicity is
not established. Results are written to
`~/afsi-data/demo-405/vessel-wall-3d/<timestamp>/`, and the driver calls SwanLab
plus a remote counter service. There are **no environment overrides**.

## 4. Results

### 4.1 Quantities of interest

The quantities of interest would be the leaflet motion and the wall deformation
over at least one full pulse cycle; as shipped, neither is available.

### 4.2 Comparison with reference

{{< color "red" >}}TODO: comparison against a reference — none exists; the case
first needs a mesh, a completed cycle and archived output.{{< /color >}}

| Quantity | AFSI | Reference | rel. err. |
| --- | --- | --- | --- |
| Leaflet tip excursion per cycle |  |  |  |
| Wall displacement per cycle |  |  |  |

### 4.3 Convergence study

{{< color "red" >}}TODO: grid and time-step sensitivity — none exists.{{< /color >}}

### 4.4 Flow and deformation fields

{{< figure src="/afsi/demo405-results.png" title="Figure 2. What the code applies and what it ships: the driver is driven by an inlet velocity, while `PressureEndo.py` — the only luminal-pressure model in the demo — is imported by nothing. Both curves are evaluated from the sources; no run data exists for this demo." >}}

**No results are archived**, and neither is any mesh file: the readme's
$141\,038$-node vessel mesh, `leaflets_M2_tet.xdmf` and the merged
`combined_vessel_leaflets.xdmf` are all absent, so neither the merge step nor the
driver can be reproduced from this checkout without the external meshes.

## 5. Discussion and limitations

Read the readme against the code before reusing this case:

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

## 6. Reproducibility

<p class="tcaption">Table 2. Files in the demo.</p>

| File | Role |
|---|---|
| `configuration.py` | Parameters for all three FSI scripts, output path, experiment name |
| `fsi_paralell.py` | Main driver named by the readme: reads `combined_vessel_leaflets.xdmf`, neo-Hookean on tag $2$, penalty on tag $1$ |
| `fsi_paralell_vessel.py` | Vessel-only variant; the elastic term is **commented out**, leaving only the penalty |
| `fsi_paralell_vessel_valves.py` | Byte-identical copy of the vessel-only script (same md5) |
| `merge_meshes.py` | Merges the vessel and leaflet tet meshes into `combined_vessel_leaflets.xdmf`, tagging cells $1/2$ by nearest-centroid matching |
| `NeoHookean.py` | `NeoHookeanMaterial` ($\psi = \frac{\mu}{2}(I_c-3) - \mu\ln J + \frac{\lambda}{2}(\ln J)^2$) |
| `PressureEndo.py` | Diastolic/systolic pressure ramp ($8$ / $110\,\mathrm{mmHg}$) — **imported by nothing** |

```bash
# merge the vessel and leaflet meshes (writes combined_vessel_leaflets.xdmf)
python3 merge_meshes.py

cd afsic/demo/demo_405
mpirun -np 4 python3 fsi_paralell.py
```

## References

{{< color "red" >}}TODO: references — none cited; the vessel/valve geometry
source should be referenced.{{< /color >}}
