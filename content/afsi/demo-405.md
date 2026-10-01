---
title: "405: Vessel Wall with Merged Leaflets"
description: "A tubular vessel wall with merged leaflets under a pulsatile inlet."
date: 2026-09-12
weight: 405
academic: true
demo_id: demo_405
category: Application
dimension: 3D
solid_model: "vessel by penalty; leaflets neo-Hookean; massless, explicit Euler"
coupling: "immersed boundary (`IBMesh3D`)"
reference: "—"
status: WIP
---

## 1. Introduction

A tubular vessel wall is immersed in an $8 \times 8 \times 20$ cm fluid box driven
by a pulsatile plug inlet along the tube axis. The solid is an unstructured
tetrahedral mesh, optionally a *merged* vessel + leaflets mesh whose cell tags
separate the two parts: the vessel cells are held by a volumetric penalty spring
and the leaflet cells carry the neo-Hookean stress.

## 2. Problem description

### 2.1 Geometry

{{< figure src="/afsi/demo405-setup.png" title="Figure 1. The vessel cross-section and an axial cut, with the cell tags that separate the wall from the leaflets." >}}

The box is $8 \times 8 \times 20\,\mathrm{cm}$; the lumen of radius
$R_{inner} = 1.3\,\mathrm{cm}$ runs along the $z$ axis at $(4.0, 4.0)$. The vessel
mesh is reported as $141\,038$ nodes / $140\,612$ cells.

### 2.2 Governing equations

{{< color "red" >}}TODO: governing equations — incompressible Navier–Stokes, the
leaflet constitution (neo-Hookean,
$\psi = \frac{\mu}{2}(I_c-3) - \mu\ln J + \frac{\lambda}{2}(\ln J)^2$ as
implemented), and the IB coupling terms (see the symbol table page).{{< /color >}}

### 2.3 Boundary and initial conditions

{{< color "red" >}}TODO: boundary conditions as actually imposed — the originally
documented description does not match the configuration (see §5): the inlet is a
plug
$u_z = U_{max}\sin(2\pi f t)$ inside the lumen, the outlet is at $p = 0$, and the
box walls are no-slip, but the luminal-pressure condition does not exist in the
current setup.{{< /color >}}

### 2.4 Physical parameters

<p class="tcaption">Table 1. Parameters (CGS).</p>

| Quantity | Symbol / code name | Value |
|---|---|---|
| Fluid box | `Lx`, `Ly`, `Lz` | $8.0 \times 8.0 \times 20.0\,\mathrm{cm}$ |
| Fluid cells | `Nx`, `Ny`, `Nz` | $32 \times 32 \times 80$ hexahedra |
| Density / viscosity | `rho`, `mu` | $1.0\,\mathrm{g\,cm^{-3}}$ / $0.036\,\mathrm{dyn\,s\,cm^{-2}}$ |
| Inlet amplitude / frequency | `U_max`, `freq` | $1.0$ / $1.0\,\mathrm{Hz}$ |
| Inlet profile | — | plug, $u_z = U_{max}\sin(2\pi f t)$ inside $r < R_{inner}$ (reverses each half cycle) |
| Lumen radius / centre | `R_inner`, `cx`, `cy` | $1.3\,\mathrm{cm}$ / $(4.0, 4.0)$ |
| Solid material | `NeoHookeanMaterial` | $E = 2\times10^{6}$, $\nu = 0.4$ for the leaflets |
| Cell tags | — | vessel (penalty-fixed), leaflets (neo-Hookean) |
| Penalty | `beta` | $1\times10^{6}$ |

{{< color "red" >}}TODO: dimensionless numbers and the physiological pulse
($8/110\,\mathrm{mmHg}$ diastolic/systolic) that the demo's pressure model
describes but the current setup does not apply.{{< /color >}}

## 3. Numerical setup

Velocity / force / pressure spaces are $\mathrm{P2}$ / $\mathrm{P2}$ /
$\mathrm{P1}$, with $\Delta t = 1/10\,000\,\mathrm{s}$ to $T = 0.2\,\mathrm{s}$ —
only one fifth of the $1\,\mathrm{Hz}$ cycle, so periodicity is not established.

## 4. Results

### 4.1 Quantities of interest

The quantities of interest would be the leaflet motion and the wall deformation
over at least one full pulse cycle; neither exists yet.

### 4.2 Comparison with reference

{{< color "red" >}}TODO: comparison against a reference — none exists; the case
first needs a completed cycle and archived output.{{< /color >}}

| Quantity | AFSI | Reference | rel. err. |
| --- | --- | --- | --- |
| Leaflet tip excursion per cycle |  |  |  |
| Wall displacement per cycle |  |  |  |

### 4.3 Convergence study

{{< color "red" >}}TODO: grid and time-step sensitivity — none exists.{{< /color >}}

### 4.4 Flow and deformation fields

{{< figure src="/afsi/demo405-results.png" title="Figure 2. The applied load against the luminal-pressure model the demo describes: the run is driven by an inlet velocity, while the pressure model is used by nothing. Both curves are evaluated from the described configuration; no run data exists." >}}

No results exist for this case, and no field figures can be shown yet.

## 5. Discussion and limitations

* The documented luminal-pressure model is not used: the run is
  driven by the inlet plug velocity alone, and no pressure load is applied to the
  inner wall.
* The vessel-only configurations are penalty-only (effectively rigid) regardless
  of the material parameters.
* The solid is massless: the velocity is interpolated from the fluid and the
  position advanced by explicit Euler, with no stability discussion.
* $T = 0.2\,\mathrm{s}$ at $1\,\mathrm{Hz}$ covers only one fifth of a cycle, so
  periodicity is not established.

{{< color "red" >}}TODO: state the intended boundary-condition set (ends fixed?
luminal pressure?) and align it with §2.3.{{< /color >}}

## References

{{< color "red" >}}TODO: references — none cited; the vessel/valve geometry
source should be referenced.{{< /color >}}
