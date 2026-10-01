---
title: "339: Flow Past a Cylinder at Re = 100"
description: "Channel flow past a cylinder at Re = 100, solved four ways on the same geometry."
date: 2026-09-12
weight: 339
academic: true
demo_id: demo_339
category: Application
dimension: 2D
solid_model: "rigid cylinder (near-rigid neo-Hookean disc in case 3; rigid markers in case 4)"
coupling: "four variants: none / body-fitted / IB-FE / multi-direct forcing"
reference: "DFG benchmark 2D-3 (Schäfer & Turek)"
status: Partial
---

## 1. Introduction

The DFG 2D-3 geometry — channel flow past a cylinder at $\mathrm{Re} = 100$ — is
solved four ways on the same SI-unit geometry, so that the treatments of the body
can be compared directly:

| Case | Treatment of the cylinder |
|---|---|
| 1 | none — baseline channel |
| 2 | a hole in a body-fitted mesh with a no-slip Dirichlet condition on it |
| 3 | an immersed near-rigid neo-Hookean disc ($\mu_s = 7.7\times10^{10}$ Pa) held by a $\beta = 10^{12}$ penalty |
| 4 | multi-direct forcing with a rigid marker set and interior masking |

{{< figure src="/afsi/demo339-setup.png" title="Figure 1. The DFG 2D-3 channel and the four ways the cylinder is treated." >}}

## 2. Problem description

### 2.1 Geometry

The channel is $2.2 \times 0.41\,\mathrm{m}$. The cylinder of radius
$R = 0.05\,\mathrm{m}$ sits at $(0.2, 0.2)$ — $2.6$ diameters from the inlet — and
blocks about a quarter of the channel width.

{{< color "red" >}}TODO: figure placeholder — annotated channel geometry (dimensions $L_x$, $L_y$, cylinder position and radius).{{< /color >}}

### 2.2 Governing equations

{{< color "red" >}}TODO: governing equations — incompressible Navier–Stokes, the penalty and direct-forcing formulations of the immersed body, and the solid constitution (see the symbol table page).{{< /color >}}

### 2.3 Boundary and initial conditions

The inlet imposes the parabolic profile $u_x = 1.5\,U_m\,y(H-y)/(H/2)^2$ with a
ramp $t_{ramp} = 2\,\mathrm{s}$; in the body-fitted case the cylinder hole carries
a no-slip Dirichlet condition; in the immersed cases the solid is held against the
flow by the penalty or by the marker forces.

{{< color "red" >}}TODO: outlet and top/bottom wall conditions for cases 1, 3 and 4.{{< /color >}}

### 2.4 Physical parameters

<p class="tcaption">Table 1. Physical parameters (SI units).</p>

| Quantity | Symbol / code name | Value |
|---|---|---|
| Channel | `Lx` × `Ly` | $2.2 \times 0.41\,\mathrm{m}$ |
| Cylinder centre | `cx`, `cy` | $(0.2, 0.2)\,\mathrm{m}$ |
| Cylinder radius | `R` | $0.05\,\mathrm{m}$, i.e. $D = 0.1\,\mathrm{m}$ |
| Mean inlet velocity | `Um` | $1.0\,\mathrm{m\,s^{-1}}$ |
| Density / viscosity | `rho`, `mu` | $1000\,\mathrm{kg\,m^{-3}}$ / $1.0\,\mathrm{Pa\,s}$ |
| Reynolds number | $\mathrm{Re} = \rho U_m D/\mu$ | $100$ |

{{< color "red" >}}TODO: dimensionless numbers beyond $\mathrm{Re}$, if the case is to be reported in dimensionless form.{{< /color >}}

## 3. Numerical setup

Cases 1–3 use a Chorin projection solver with $\mathrm{P2}/\mathrm{P1}$ elements;
case 4 uses an AB2 fractional step with iterated direct forcing ($n_{iter} = 10$,
128 rim markers) and an interior mask that zeroes the velocity inside $r < R$. The
uniform grid is $220 \times 41$ ($h \approx 0.01\,\mathrm{m}$) with
$\Delta t = 0.001\,\mathrm{s}$ to $T = 10\,\mathrm{s}$; the body-fitted case uses a
Gmsh mesh ($10\,762$ nodes, $21\,524$ elements, size $\le 0.01\,\mathrm{m}$), and
the IB-FE disc mesh has size $0.002$–$0.005\,\mathrm{m}$.

## 4. Results

### 4.1 Quantities of interest

The quantities of interest are the field errors $u_{L2}$ / $p_{L2}$ of each case
against the body-fitted solution, the force coefficients $C_d$ and $C_l$ from the
immersed-boundary force integral, the lift period (as a Strouhal number), and the
recirculation length from the centreline velocity. The archived values are the
short-run summary and the recorded results:

<p class="tcaption">Table 2. Archived results from the short-run summary.</p>

| Quantity | Value |
|---|---|
| 300-step $u_{L2}$ / $p_{L2}$: no-cylinder, body-fitted, IB-FE, mdf | $0.002728$ / $208\,905$; $0.002792$ / $207\,765$; $0.002728$ / $208\,905$; $0.002828$ / $0.224956$ |
| Drag coefficient, $2500$ steps ($t = 2.5\,\mathrm{s}$): body-fitted / mdf disc / mdf boundary | $2.664$ / $4.091$ / $4.388$ |
| Quasi-steady wake ($t > 6\,\mathrm{s}$, mdf) | $\mathrm{Cd} \approx 2.53$, $\mathrm{St} \approx 0.52$ against the reference $\mathrm{Cd} \approx 5.57$, $\mathrm{St} \approx 0.3$ |
| Body-fitted, $10\,\mathrm{s}$ | wake spikes to $-5811\,\mathrm{m\,s^{-1}}$, Cd spikes to $10^{91}$ after $t > 6.8\,\mathrm{s}$ |

### 4.2 Comparison with the published benchmark

{{< color "red" >}}TODO: the standard DFG 2D-3 quantities of interest, compared
against Schäfer & Turek — in its current configuration it cannot reproduce them
(see §5).{{< /color >}}

| Quantity | AFSI | Reference (Schäfer–Turek) | rel. err. |
| --- | --- | --- | --- |
| $c_{D,\max}$ |  |  |  |
| $c_{L,\max}$ |  |  |  |
| $\Delta p(t = 8\,\mathrm{s})$ |  |  |  |

### 4.3 Convergence and resolution sensitivity

A study runs the multi-direct-forcing variant over a matrix of nine
configurations — three grids ($110\times21$, $220\times41$, $440\times82$), two
marker models (boundary ring / filled disc), iteration counts
($n_{iter} = 2, 10, 20$) and a cylinder-free control. Each run reaches
$t = 6\,\mathrm{s}$, i.e. $4\,\mathrm{s}$ past the end of the inlet ramp.

The volume-force integral *decreases* under refinement — $0.439 \to 0.268 \to 0.157$
at $110\times21$, $220\times41$, $440\times82$, against a reference $0.292$ — and
the refinement study recommends a control-volume momentum balance instead.

{{< figure src="/afsi/demo339-cd.png" title="Figure 2. The drag coefficient from the force integral shrinks with refinement (archived numbers)." >}}

Re-measured over the statistically steady window $t > 2.5\,\mathrm{s}$, the
decrease is there, but the fine grid never gets that far:

{{< figure src="/afsi/demo339-study-cd.png" title="Figure 3. Left: the force-integral $C_d$ at three resolutions, with the body-fitted value the tutorial reports. Middle: the apparent shedding frequency from the lift signal — but see the wake discussion in §4.4, the lift signal is not a vortex street. Right: lift histories for every variant." >}}

<p class="tcaption">Table 3. Force-integral drag and marker volume at three resolutions ($t > 2.5\,\mathrm{s}$).</p>

| Grid | $C_d$ (force integral) | marker volume $\Delta V_l$ | status |
|---|---|---|---|
| $110\times21$ | $4.3676 \pm 0.0045$ | $48.50\,\mathrm{mm^2}$ | steady |
| $220\times41$ | $2.5282 \pm 0.0029$ | $24.54\,\mathrm{mm^2}$ | steady |
| $440\times82$ | — | $12.55\,\mathrm{mm^2}$ | **diverges at $t = 2.28\,\mathrm{s}$** |

The ratio $4.3676/2.5282 = 1.73$ tracks the marker-volume ratio
$48.50/24.54 = 1.98$: halving the grid halves $\Delta V_l = \Delta s \cdot h$, and
the spread-force integral grows accordingly. The discrete drag is therefore a
property of the marker discretisation rather than of the flow — the values
should not be read as drag coefficients.

The fine grid does not merely give a different number: it **fails**.
At $440\times82$ the solution blows up at $t = 2.28\,\mathrm{s}$ ($u_{L2}$ jumps
from $\mathcal O(1)$ to $10^{180}$), after which $C_d$ wanders with a standard
deviation of $2.6$ around a mean of $2.1$ and no finite window can be used for
statistics. This is not a CFL problem: at $440\times82$ with
$\Delta t = 10^{-3}$ the advective CFL is $0.30$, half the value the coarse grid
runs stably at. The cause is the IBM forcing itself: the direct-force impulse per
step scales with the marker volume $\Delta V_l \propto h$, so halving $h$ halves
the impulse and, in an explicitly coupled scheme, eventually destabilises it.
Halving $\Delta t$ as well does run ($440\times82$ with
$\Delta t = 5\times10^{-4}$ starts cleanly), but reaching $t = 4\,\mathrm{s}$
then takes about five hours.

### 4.4 Flow and deformation fields

{{< figure src="/afsi/demo339-fields.png" title="Figure 4. All four treatments at 300 steps ($t = 0.3$ s). The inlet ramp takes 2 s, so the wake is only beginning to form." >}}

**A shorter run of the multi-direct-forcing case ($T = 5$ s).** The case was run at
the default resolution ($220\times41$, $\Delta t=0.001$, $n_{iter}=10$,
boundary-ring markers with the interior mask) for $5000$ steps, i.e.
$t \le 5\,\mathrm{s}$.

{{< figure src="/afsi/demo339-cylinder-5s.png" title="Figure 5. The re-run: velocity magnitude with streamlines (top) and pressure (bottom, symlog) at $t = 0,1,2,3,4,5$ s, with the immersed cylinder drawn in black. The wake grows to a steady recirculation and then stops changing." >}}

{{< figure src="/afsi/demo339-forces.png" title="Figure 6. Drag and lift from the re-run. $C_d$ rises to a plateau of $2.527$ by $t \approx 2$ s and stays flat to five digits; the lift is a weak but clean sinusoid." >}}

{{< figure src="/afsi/demo339-pyvista.png" title="Figure 7. The same instant rendered on the channel mesh with the immersed cylinder overlaid: velocity on the left and pressure on the right." >}}

<p class="tcaption">Table 4. The re-run's late window ($t > 2.5$ s).</p>

| Quantity | Value |
|---|---|
| $C_d$ | $2.5274$ (range $2.5270$–$2.5299$, std $6.8\times10^{-4}$) |
| $C_l$ | $-0.0528$ (std $8.0\times10^{-4}$) |
| Lift period (late window) | $0.380$ s, i.e. $\mathrm{St} = fD/U_m = 0.26$ |
| Field | $\max\lvert u\rvert = 2.09\,\mathrm{m\,s^{-1}}$ against an inlet peak of $1.5$ |

The re-run reaches $C_d = 2.53$, the same value recorded for the $10$ s
run, so the force integral is reproducible at fixed resolution.

**Wake structure.** What the re-run does **not** show is a vortex street: the lift
amplitude is $1.5\,\%$ of $\lvert C_l\rvert$ and the flow settles into a steady
wake. That is consistent with the geometry — the cylinder blocks a quarter of the
channel and sits only $2.6$ diameters from the inlet — rather than with the
unbounded DFG 2D-3 benchmark, whose reference values ($C_d \approx 3.22$,
$\mathrm{St} \approx 0.30$) this configuration does not reproduce quantitatively.

The lift signal never develops the large periodic oscillation that a von Kármán
street produces. Over $t > 2.5\,\mathrm{s}$ the lift sits at a constant offset with
a peak-to-peak ripple of

<p class="tcaption">Table 5. Late-window lift statistics.</p>

| Grid | $\overline{C_l}$ | peak-to-peak $C_l$ | recirculation length (from the centreline) |
|---|---|---|---|
| $110\times21$ | $-0.1606$ | $0.0093$ | $\approx 0.14\,\mathrm{m} = 1.4\,D$ |
| $220\times41$ | $-0.0527$ | $0.0050$ | $\approx 0.14\,\mathrm{m} = 1.4\,D$ |

A ripple three orders of magnitude below the dynamic pressure, and identical
recirculation lengths on two very different grids, is the signature of a **steady
symmetric wake**. Figure 8 shows it directly: the vorticity field behind the
cylinder is a symmetric pair of shear layers with no alternating cores, and it
barely changes between $t = 2$ and $t = 6$.

{{< figure src="/afsi/demo339-study-wake.png" title="Figure 8. Left: the centreline velocity at $t = 6$ s at both resolutions — the deficit closes monotonically and the two grids lie on top of each other. Right: the lift signal magnified by $10^3$. The residual oscillation is 0.005 in $C_l$, against a mean level of $-0.05$." >}}

{{< figure src="/afsi/demo339-study-fields.png" title="Figure 9. Vorticity (top) and pressure (bottom) at five instants for the default resolution. The pattern is symmetric about the centreline and stationary: no vortex street forms." >}}

This matters for how the case is described. Shedding frequencies computed from
that ripple are noise — the period is stable enough to divide by
($0.38\,\mathrm{s}$, i.e. $\mathrm{St} \approx 0.26$) but the amplitude carries no
signal. The honest statement is that **this implementation, at these resolutions,
produces a steady wake at $\mathrm{Re} = 100$**, where the DFG 2D-3 benchmark is
unsteady ($\mathrm{St} \approx 0.295$, $C_l$ amplitude $\approx 1$).

### 4.5 Marker model and iteration count

{{< figure src="/afsi/demo339-study-variants.png" title="Figure 10. Drag and energy histories for every variant: the three grids, the two marker models, and $n_{iter} = 2$ and $20$." >}}

The remaining knobs matter much less than the grid:

<p class="tcaption">Table 6. Marker-model and iteration-count sensitivity ($t > 2.5\,\mathrm{s}$).</p>

| Run | Markers | $n_{iter}$ | $C_d$ | $\overline{C_l}$ | $u_{L2}$ at $t=6$ |
|---|---|---|---|---|---|
| default | boundary ring, 128 | $10$ | $2.5282 \pm 0.0029$ | $-0.05273$ | $1.1178$ |
| filled disc | filled disc | $10$ | $2.5282 \pm 0.0029$ | $-0.05273$ | $1.1178$ |
| $n_{iter} = 2$ | boundary ring, 128 | $2$ | $1.6891 \pm 0.0019$ | $-0.05208$ | $1.1148$ |
| $n_{iter} = 20$ | boundary ring, 128 | $20$ | $2.5962 \pm 0.0029$ | $-0.05137$ | $1.1180$ |
| no cylinder | none | — | $0.0000$ | $0.00000$ | $1.0826$ |

Two conclusions. **The marker model is irrelevant**: filling the disc with interior
markers returns bit-identical drag to the boundary ring alone, so the ring is
sufficient. And **the iteration count is a real parameter but a small one**:
dropping from $10$ to $2$ iterations costs $33\,\%$ of the drag, while going to
$20$ changes it by $+2.7\,\%$ — so $10$ is close to converged. The cylinder's
presence costs the flow about $3\,\%$ of its energy norm ($1.1178$ against
$1.0826$), a sensible magnitude for a $24\,\%$ blockage.

## 5. Discussion and limitations

**Why the published benchmark cannot be compared as configured.** Two mismatches:

1. **The inlet amplitude is 1.5× too large.** The inlet is
   $1.5\,U_m\,y\,(H-y)/(H/2)^2$ with $U_m = 1.0$, so the profile peaks at $1.5$
   with $\overline{u} = 1.0$ and stays constant. The DFG 2D-3 inlet is
   $4Uy(0.41-y)/0.41^2$ with $U = 1.5\sin(\pi t/8)$, which peaks at $1.5$ and has
   $\overline{u} = 1.0$ *only when the sine is at its maximum*. The demo therefore
   runs at a steady $\mathrm{Re} = 100$ while the benchmark sweeps
   $\mathrm{Re} = 0 \to 100$ over eight seconds and never holds a steady state.
2. **The force coefficients are normalised differently.** The coefficient is
   $C_d = 2F_x/(\bar U^2 D)$ with $\bar U = 1$, i.e. the DFG $C_d$ (which uses the
   peak) is $2.25\times$ larger for the same force. Neither the recorded
   $\approx 0.29$ (body-fitted, surface-stress integration) nor the DFG
   $\approx 3.22$ matches the value computed here.

A variant with the benchmark's inlet amplitude (peak $2.25$ in these units)
diverges at $\Delta t = 10^{-3}$ around $t = 1.7\,\mathrm{s}$: the step is simply
too large for that driving. Fixing the comparison properly needs both a smaller
$\Delta t$ and the benchmark's time-dependent amplitude, not a constant one.

**Known caveats.**

* The documented conclusion is that the **velocity field converges but the
  volume-force-integral drag does not**: marker volumes sum to
  $2\pi r h \propto h$, so $\mathrm{Cd}$ from
  $\int \mathbf{f}_{\mathrm{IB}}\,\mathrm{d}V$ is grid-dependent (§4.3), and a
  control-volume momentum balance is recommended instead. That balance **cannot be
  applied to this channel as configured**: with the cylinder only $2D$ from the
  inlet and a domain of $4.1D$, it is dominated by the channel-wall friction
  integral ($\approx 70\,\mathrm{N}$) and the inlet/outlet momentum flux
  ($\approx 37\,\mathrm{N}$), against a $0.13\,\mathrm{N}$ cylinder force. A
  circular control volume hugging the cylinder would be needed, and that cannot be
  integrated accurately on a Cartesian grid this coarse.
* The IB-FE case is stiff: the disc drifts $\approx 9\times10^{-4}\,\mathrm{m}$
  over $300$ steps and the solid force becomes `NaN` after $\approx 200$ steps.

{{< color "red" >}}TODO: check whether the archived $\mathrm{Cd}$ values are
density-normalised (the coefficient omits the density factor even though
$\rho = 1000$ is set).{{< /color >}}

## References

{{< color "red" >}}TODO: references — add the DFG 2D-3 benchmark (Schäfer & Turek)
and the geometry/reference sources for this configuration.{{< /color >}}
