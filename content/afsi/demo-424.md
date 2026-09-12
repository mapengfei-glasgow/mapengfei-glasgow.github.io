---
title: "Pressure-driven tethered aorta: a solver-verification case with an immersed occlusion"
description: "demo_424: two 2-D planar configurations with known exact solutions — full parameter set, measured results, a mesh-refinement study, and a diagnosed open-boundary defect in the IPCS solver."
date: 2026-09-12
weight: 2
academic: true
---

## 1. Introduction

The case consists of two configurations that share one geometry, one fluid, one
tether model and one driving condition; they differ only by a membrane that
occludes the lumen. Since the exact solution is known analytically in both
configurations, every error metric reported below has a reference value, and the
case therefore serves as a pure solver-verification study.

<p class="tcaption">Table 1. The two configurations. The solid outline of the occluded case reads as the letter H.</p>

| Case | Solid | Expected physics |
|---|---|---|
| `open` | two tethered wall strips | three parallel plane-Poiseuille channels (lumen and two outer gaps) driven by the end pressure difference |
| `closed` | the same strips and a full-occlusion membrane at mid-length | lumen chambers stagnant and isobaric, a pressure jump of exactly $\Delta p$ across the membrane, bypass flow still carried by the outer gaps |

{{< figure src="/afsi/demo424-configuration.png" title="Figure 1. The two configurations. The box is half a cell longer than the aorta at each end, so the pressure Dirichlet nodes never coincide with a Lagrangian end node." >}}

## 2. Configuration

### 2.1 Geometry and mesh

The configuration is a two-dimensional planar (plane-strain) idealisation: cutting
the cylindrical aorta along a plane through its axis turns the lumen into a
parallel-plate channel and the wall into two flat strips.

<p class="tcaption">Table 2. Geometry and mesh parameters.</p>

| Quantity | Code name | Value |
|---|---|---|
| Aorta length | `L_AORTA` | $0.1\,\mathrm{m}$ |
| Lumen half-height | `A_LUMEN` | $0.015\,\mathrm{m}$ |
| Wall thickness | `T_WALL` | $0.002\,\mathrm{m}$ |
| Box length | `BOX_L` | $L_{\text{aorta}} + h$: $0.1005\,\mathrm{m}$ ($h = 1\,\mathrm{mm}$), $0.10025\,\mathrm{m}$ ($h = 0.5\,\mathrm{mm}$) |
| Box width | `BOX_W` | $1.5 \cdot 2a = 0.045\,\mathrm{m}$ |
| Outer fluid gap | `GAP` | $0.0055\,\mathrm{m}$ per side |
| Membrane thickness | `DISC_T` | $0.002\,\mathrm{m}$, spanning the lumen at mid-length |
| Fluid cells | `NX` × `NY` | $101 \times 45$, $201 \times 90$ |
| Cell size | $h$ = `BOX_W`/`NY` | $1.0\,\mathrm{mm}$, $0.5\,\mathrm{mm}$ |
| Solid cell | `SOLID_DIV` $= 2$ | $h/2$ |
| Coupling | — | `IBMesh` + `IBInterpolation`, four-point Peskin kernel |

The grid is square, which constrains the usable resolutions: with
$W_{\text{box}} = 0.045\,\mathrm{m}$ and $L_{\text{aorta}}/W_{\text{box}} = 20/9$,
$N_y$ must be a multiple of $9$, so $N_y \in \{45, 90, 180\}$ gives
$N_x \in \{101, 201, 401\}$. Because $L_{\text{box}} = L_{\text{aorta}} + h$, the
imposed gradient $\Delta p / L_{\text{box}}$ depends slightly on the resolution —
$26.4005\,\mathrm{Pa\,m^{-1}}$ at $N_y = 45$ and $26.5318\,\mathrm{Pa\,m^{-1}}$ at
$N_y = 90$. Each row of the results tables is compared against its own level's
value.

### 2.2 Fluid, solid and driving conditions

<p class="tcaption">Table 3. Material and driving parameters. The solid carries no constitutive law: it is held in place by a volumetric spring (tether) alone.</p>

| Quantity | Code name | Value |
|---|---|---|
| Fluid density (normalised) | `RHO` | $\rho = 1.0$ |
| Fluid dynamic viscosity | `MU` | $\mu = 3.5\times10^{-3}\,\mathrm{Pa\,s}$ |
| Kinematic viscosity | — | $\nu = \mu/\rho = 3.5\times10^{-3}\,\mathrm{m^2\,s^{-1}}$ |
| Tether stiffness | `BETA` | $\beta = 1.0\times10^{7}\,\mathrm{N\,m^{-3}}$ |
| Tether law | — | $\mathbf{f} = \beta\,(\mathbf{X}_{\text{ref}} - \mathbf{X})$ |
| Driving difference, `open` | `DP_MMHG` | $\Delta p = 0.02\,\mathrm{mmHg} = 2.666\,\mathrm{Pa}$ |
| Driving difference, `closed` | `DP_MMHG` | $\Delta p = 0.2\,\mathrm{mmHg} = 26.664\,\mathrm{Pa}$ |
| Ramp | `RAMP_T` | linear, $0 \to \Delta p$ over $0.05\,\mathrm{s}$, then held |
| End time | `T_END` | $T = 0.4\,\mathrm{s}$ |
| Time step | `DT` | $\Delta t = 2.0\times10^{-4}\,\mathrm{s}$, i.e. $2000$ steps |

The derived scales of the patent case are
$u_{\text{max}} = 0.848\,\mathrm{m\,s^{-1}}$,
$u_{\text{mean}} = 0.565\,\mathrm{m\,s^{-1}}$,
$\mathrm{Re} = \rho\,u_{\text{mean}} \cdot 2a/\mu \approx 4.9$ and a viscous time
$a^2/\nu = 0.064\,\mathrm{s}$. The flow is laminar and only weakly inertial, so the
fully developed profile is the exact Poiseuille parabola and the entrance region
($\approx 1.5\,\mathrm{cm}$, $15\,\%$ of the length) is excluded from the
comparisons.

The occluded case is driven at ten times the pressure difference of the patent
case for a practical reason. In the patent case the transmural pressure vanishes at
steady state — the lumen and the gap see the same axial gradient — so the wall does
not move and the case is a pure flow test. In the occluded case the flow is
essentially zero, so nothing dissipates the driving pressure: $\Delta p$ is carried
entirely by the membrane and its tether, and the only measurable response is the
membrane displacement given by the one-dimensional tether balance

$$\delta = \frac{\Delta p}{\beta\,t_{\text{wall}}} , \tag{1}$$

which is $1.3\times10^{-4}\,\mathrm{m}$ at $0.02\,\mathrm{mmHg}$ — a hundred times
smaller than a grid cell — but $1.3\times10^{-3}\,\mathrm{m}$ at
$0.2\,\mathrm{mmHg}$. The tenfold step makes the response measurable without
moving the geometry appreciably ($\delta \approx 2$ grid cells at $N_y = 90$).

### 2.3 Time integration

The explicit projection solver `ChorinSolver` is used throughout. The incremental
pressure-correction solver `IPCSSolver` is available in AFSI but is unsuitable for
this configuration as shipped; the reason, the evidence and a verified remedy are
given in Section 4.

### 2.4 Boundary conditions

* The box side walls (diameter direction) are no-slip.
* The box open ends carry a **pressure Dirichlet** condition, $p = p_{\text{in}}(t)$
  at $x = 0$ and $p = 0$ at $x = L_{\text{box}}$, and **no velocity condition**;
  the natural condition there is zero traction.

Prescribing pressure on a boundary is an essential (Dirichlet) condition on the
pressure Poisson problem rather than a traction condition in the usual sense.
Combined with the natural zero-traction condition of the momentum predictor it is
the projection-method realisation of a prescribed-normal-traction
(pressure-driven) open boundary; in this code it is exactly the `bcp` argument of
the solver. Because both ends carry Dirichlet data the pressure null space is fixed
and no gauge point is required.

## 3. Results

All figures below are for $\Delta t = 2\times10^{-4}\,\mathrm{s}$ and
$T = 0.4\,\mathrm{s}$. The wall-clock cost of a single run on the machine used here
was $26.1\,\mathrm{min}$ ($N_y = 45$) and $54.4\,\mathrm{min}$ ($N_y = 90$) per
configuration.

### 3.1 Patent configuration

{{< figure src="/afsi/demo424-open-fields.png" title="Figure 2. Patent configuration at $N_y = 45$. Left: the pressure field is linear in $x$. Centre: the lumen jet, with the smeared wall bands. Right: the lumen profile at $x = 50\,\mathrm{mm}$ against the analytical Poiseuille parabola; the profiles coincide to the eye and the deficit appears only in the numbers." >}}

<p class="tcaption">Table 4. Patent configuration: measured quantities against their analytical values. The gradient is compared with that level's own $\Delta p / L_{\text{box}}$.</p>

| Quantity | $N_y = 45$ | $N_y = 90$ | Analytical (per level) |
|---|---|---|---|
| Fitted gradient $G = -\mathrm{d}p/\mathrm{d}x$ | $26.3856\,\mathrm{Pa\,m^{-1}}$ | $26.5147\,\mathrm{Pa\,m^{-1}}$ | $26.4005$ / $26.5318\,\mathrm{Pa\,m^{-1}}$ |
| Relative error in $G$ | $-5.6\times10^{-4}$ | $-6.5\times10^{-4}$ | — |
| Max deviation of $p(x)$ from linear | $9.83\times10^{-5}\,\mathrm{Pa}$ | $6.58\times10^{-5}\,\mathrm{Pa}$ | $0$ |
| $u_{\text{max}}$ (interior window) | $0.8106\,\mathrm{m\,s^{-1}}$ | $0.8355\,\mathrm{m\,s^{-1}}$ | $0.8481$ / $0.8523\,\mathrm{m\,s^{-1}}$ |
| Relative error in $u_{\text{max}}$ | $-4.42\,\%$ | $-1.96\,\%$ | — |
| Lumen flow rate $Q_{\text{lumen}}$ | $1.5852\times10^{-2}\,\mathrm{m^2\,s^{-1}}$ | $1.6540\times10^{-2}\,\mathrm{m^2\,s^{-1}}$ | $1.6962$ / $1.7045\times10^{-2}\,\mathrm{m^2\,s^{-1}}$ |
| Relative error in $Q_{\text{lumen}}$ | $-6.55\,\%$ | $-2.96\,\%$ | — |
| Gap flow rate $Q_{\text{gap}}$ (both sides) | $1.9850\times10^{-4}\,\mathrm{m^2\,s^{-1}}$ | $2.1793\times10^{-4}\,\mathrm{m^2\,s^{-1}}$ | $2.0916$ / $2.1020\times10^{-4}\,\mathrm{m^2\,s^{-1}}$ |
| Relative error in $Q_{\text{gap}}$ | $-5.10\,\%$ | $+3.68\,\%$ | — |
| Lumen profile, relative $L_2$ | $5.431\,\%$ | $2.625\,\%$ | — |
| Lumen profile, $\lVert e\rVert_\infty$ | $3.691\times10^{-2}\,\mathrm{m\,s^{-1}}$ | $1.722\times10^{-2}\,\mathrm{m\,s^{-1}}$ | — |

The pressure field is essentially exact and the flow is fully developed — the
profile error is identical to four significant digits at $x = 0.25$, $0.50$ and
$0.75\,L$ — but the velocity is systematically about $5\,\%$ low. The deficit is
attributable to immersed-boundary smearing: the four-point Peskin kernel spreads
the $2\,\mathrm{mm}$ wall over a band of $\pm 2h$, so the effective no-slip surface
is displaced outward and the channel carries less flux. The pointwise error peaks
next to the wall and is small in the core, which is the signature of an
interpolation error rather than a solver error.

### 3.2 Occluded configuration

{{< figure src="/afsi/demo424-closed-fields.png" title="Figure 3. Occluded configuration at $N_y = 45$. The pressure is uniform at approximately $26.6\,\mathrm{Pa}$ upstream and approximately $0$ downstream, with a jump at the membrane; the velocity magnitude shows the bypass flow in the two outer gaps and the nearly stagnant lumen chambers. Right: pressure along both channel centrelines." >}}

<p class="tcaption">Table 5. Occluded configuration: pressure holding, chamber uniformity and leakage.</p>

| Quantity | $N_y = 45$ | $N_y = 90$ | Target |
|---|---|---|---|
| Held pressure jump (chamber means) | $26.2531\,\mathrm{Pa}$ | $26.5561\,\mathrm{Pa}$ | $26.6645\,\mathrm{Pa}$ ($0.2\,\mathrm{mmHg}$) |
| Fraction of $\Delta p$ held | $98.46\,\%$ | $99.59\,\%$ | $100\,\%$ |
| Upstream chamber: mean / standard deviation | $26.6147$ / $0.0259\,\mathrm{Pa}$ | $26.6432$ / $0.0110\,\mathrm{Pa}$ | isobaric |
| Downstream chamber: mean / standard deviation | $0.3616$ / $0.7811\,\mathrm{Pa}$ | $0.0871$ / $0.2903\,\mathrm{Pa}$ | isobaric |
| Leakage flux at $x_d \pm 4h$ (upstream / downstream) | $7.976$ / $6.239\times10^{-4}\,\mathrm{m^2\,s^{-1}}$ | $2.553$ / $3.606\times10^{-4}\,\mathrm{m^2\,s^{-1}}$ | $0$ |
| Gap flow rate $Q_{\text{gap}}$ | $5.250\times10^{-4}\,\mathrm{m^2\,s^{-1}}$ | $8.146\times10^{-4}\,\mathrm{m^2\,s^{-1}}$ | $2.0916$ / $2.1020\times10^{-3}\,\mathrm{m^2\,s^{-1}}$ |
| Relative error in $Q_{\text{gap}}$ | $-74.9\,\%$ | $-61.2\,\%$ | — |
| Membrane displacement $\delta$ | $2.489\times10^{-4}\,\mathrm{m}$ | $1.154\times10^{-3}\,\mathrm{m}$ | $1.333\times10^{-3}\,\mathrm{m}$ (Eq. 1) |
| $\delta$ relative to Eq. 1 | $18.7\,\%$ | $86.6\,\%$ | $100\,\%$ |
| Membrane tether force per unit depth | $0.1493\,\mathrm{N\,m^{-1}}$ | $0.6926\,\mathrm{N\,m^{-1}}$ | $\Delta p \cdot 2a = 0.800\,\mathrm{N\,m^{-1}}$ |

Two findings deserve emphasis.

1. **The membrane holds the pressure.** It sustains $98.5\,\%$ of $\Delta p$ at the
   coarse resolution and $99.6\,\%$ at the fine one, and its error converges at
   second order, so the immersed occlusion works as intended.
2. **The wall leaks.** The outer gaps see the full end-to-end gradient while the
   sealed lumen sits at approximately zero, so the downstream half of the wall
   carries a transmural pressure of a few pascals. The immersed $2\,\mathrm{mm}$
   wall — only two cells thick at $N_y = 45$ — passes fluid: the downstream chamber
   is measurably not isobaric (standard deviation $0.78\,\mathrm{Pa}$ against
   $0.026\,\mathrm{Pa}$ upstream), and only $25\,\%$ of the analytical bypass flux
   still flows in the gaps because the remainder short-circuits into the lumen
   through the wall. At $N_y = 90$, where the wall is four cells thick, the
   recovery is to $39\,\%$.

The membrane reaches only $18.7\,\%$ of the displacement predicted by Eq. (1) at
$N_y = 45$, i.e. that run is not settled: the tether force is
$0.149\,\mathrm{N\,m^{-1}}$ against a pressure force of
$0.800\,\mathrm{N\,m^{-1}}$. At $N_y = 90$ the same run reaches $86.6\,\%$
($\delta = 1.154\times10^{-3}\,\mathrm{m}$, tether force
$0.693\,\mathrm{N\,m^{-1}}$), close to the analytical tether equilibrium. The
residual gap is consistent with the occluded case never fully settling in time:
$\max \lvert \mathbf{u} \rvert$ oscillates between $0.30$ and
$0.40\,\mathrm{m\,s^{-1}}$ up to $T = 0.4\,\mathrm{s}$ at both resolutions,
whereas the patent case converges monotonically.

### 3.3 Mesh refinement

Refining $h$ from $1.0\,\mathrm{mm}$ to $0.5\,\mathrm{mm}$ gives the dollar-free
convergence orders $p = \log_2(e_{45}/e_{90})$ listed below.

<p class="tcaption">Table 6. Patent configuration: observed convergence orders between $N_y = 45$ and $N_y = 90$.</p>

| Quantity | $N_y = 45$ | $N_y = 90$ | Order |
|---|---|---|---|
| Fitted gradient $G$, relative error | $-5.64\times10^{-4}$ | $-6.46\times10^{-4}$ | $\approx 0$ |
| Max deviation of $p(x)$ from linear | $9.83\times10^{-5}\,\mathrm{Pa}$ | $6.58\times10^{-5}\,\mathrm{Pa}$ | $0.58$ |
| Lumen profile, relative $L_2$ | $5.431\times10^{-2}$ | $2.625\times10^{-2}$ | $\mathbf{1.05}$ |
| Lumen profile, $\lVert e\rVert_\infty$ | $3.691\times10^{-2}\,\mathrm{m\,s^{-1}}$ | $1.722\times10^{-2}\,\mathrm{m\,s^{-1}}$ | $1.10$ |
| $u_{\text{max}}$, relative error | $-4.418\times10^{-2}$ | $-1.965\times10^{-2}$ | $\mathbf{1.17}$ |
| $Q_{\text{lumen}}$, relative error | $-6.55\times10^{-2}$ | $-2.96\times10^{-2}$ | $\mathbf{1.14}$ |
| $Q_{\text{gap}}$, relative error | $-5.10\times10^{-2}$ | $+3.68\times10^{-2}$ | sign change |

<p class="tcaption">Table 7. Occluded configuration: observed convergence orders between $N_y = 45$ and $N_y = 90$.</p>

| Quantity | $N_y = 45$ | $N_y = 90$ | Order |
|---|---|---|---|
| Fraction of $\Delta p$ held | $0.98457$ | $0.99593$ | — |
| Relative error of the held jump | $-1.543\times10^{-2}$ | $-4.066\times10^{-3}$ | $\mathbf{1.92}$ |
| Upstream chamber pressure standard deviation | $2.587\times10^{-2}\,\mathrm{Pa}$ | $1.095\times10^{-2}\,\mathrm{Pa}$ | $1.24$ |
| Downstream chamber pressure standard deviation | $7.811\times10^{-1}\,\mathrm{Pa}$ | $2.903\times10^{-1}\,\mathrm{Pa}$ | $1.43$ |
| Leakage flux at $x_d - 4h$ | $7.976\times10^{-4}\,\mathrm{m^2\,s^{-1}}$ | $2.553\times10^{-4}\,\mathrm{m^2\,s^{-1}}$ | $1.64$ |
| $Q_{\text{gap}}$, relative error | $-7.49\times10^{-1}$ | $-6.12\times10^{-1}$ | $-0.29$ |
| Membrane $\delta$ relative to Eq. 1 | $0.187$ | $0.866$ | — |

{{< figure src="/afsi/demo424-convergence.png" title="Figure 4. Left: the patent-case error measures fall at first order in $h$ while the pressure gradient remains flat at $0.06\,\%$. Right: occluded-case quantities, normalised so that all four are dimensionless." >}}

Tables 6 and 7 confirm the diagnosis of the velocity deficit: it is an
immersed-boundary interpolation error, not a solver error, and it converges at
**first order** in $h$. The pressure field is unaffected and remains exact to about
$0.06\,\%$ at both resolutions. The membrane's pressure holding converges at second
order and reaches $99.6\,\%$. The wall leakage is the slow quantity: even at
$N_y = 90$ the gaps carry only $39\,\%$ of the analytical bypass flux. If the
occluded configuration is to demonstrate a sealed lumen, the wall — not only the
membrane — must be better resolved or thickened.

## 4. An open-boundary defect in the IPCS solver

### 4.1 Mechanism

Multiplying the strong form
$\rho\,\mathrm{D}\mathbf{u}/\mathrm{D}t + \nabla p - \mu\nabla^2\mathbf{u} - \mathbf{f} = 0$
by a test function and integrating over the domain gives

$$\int \rho\,\frac{\mathrm{D}\mathbf{u}}{\mathrm{D}t}\cdot\mathbf{v} -
\int p\,\mathrm{div}\,\mathbf{v} +
\int \mu\,\nabla\mathbf{u} : \nabla\mathbf{v} -
\int \mathbf{f}\cdot\mathbf{v} +
\int_{\Gamma} \left[ p\,(\mathbf{v}\cdot\mathbf{n}) -
\mu\,(\nabla\mathbf{u}\cdot\mathbf{n})\cdot\mathbf{v} \right] = 0 . \tag{2}$$

`IPCSSolver` retains the volume terms and **drops the entire boundary integral**.
Doing so is equivalent to imposing the natural condition

$$\mu\,\nabla\mathbf{u}\cdot\mathbf{n} = p\,\mathbf{n} ,
\qquad \text{i.e. zero total traction } \sigma\cdot\mathbf{n} = 0 \tag{3}$$

on every boundary where no velocity is prescribed. At the outlet the pressure
Dirichlet is $p = 0$, so zero traction is exactly right. At the inlet the pressure
Dirichlet is $p = \Delta p$, so zero traction is wrong by $\Delta p$: the momentum
predictor then attempts to build a viscous stress of order $\Delta p$ inside a
one-cell layer and produces a large spurious $\mathrm{div}\,\mathbf{u}^{*}$ there.

On its own this is a boundary-layer artefact. It becomes fatal because `IPCS`
**accumulates** the pressure ($p\_ \mathrel{+}= \phi$): the spurious divergence
feeds directly into $\phi$, and once the flow settles
($\mathrm{div}\,\mathbf{u}^{*} \to 0$, hence $\phi \to 0$) the corrupted pressure
is frozen in place with nothing left to correct it.

`ChorinSolver` carries no $p$ in its momentum predictor, so its natural condition
is the homogeneous $\mu\nabla\mathbf{u}\cdot\mathbf{n} = 0$ — exactly the physical
interface condition for a boundary whose exterior only supplies pressure. That is
why Chorin reproduces the exact profile and IPCS does not.

### 4.2 Evidence

A solid-free plane channel at $N_y = 9$ with a ramp $0 \to 2.666\,\mathrm{Pa}$
(`test_ipcs.py`), re-run for this page on 2026-09-13 at $2$–$3\,\mathrm{s}$ per
variant:

<p class="tcaption">Table 8. Solid-free plane channel, $N_y = 9$: fitted pressure gradient and velocity error per solver variant.</p>

| Variant | Fitted $G$ ($\mathrm{Pa\,m^{-1}}$) | $\max \lvert p - p_{\text{exact}}\rvert$ | Relative error in $u_{\text{max}}$ |
|---|---|---|---|
| Exact | $25.3947$ | $0$ | $0$ |
| Chorin | $25.3949$ | $2.08\times10^{-5}\,\mathrm{Pa}$ | $-5.14\,\%$ |
| IPCS, as shipped | $7.4107$ | $2.95\,\mathrm{Pa}$ | $-88.15\,\%$ |
| IPCS with restored traction term | $\mathbf{25.3944}$ | $\mathbf{7.43\times10^{-5}\,\mathrm{Pa}}$ | $-5.35\,\%$ |

Imposing the full $\Delta p$ in a single step instead of ramping it yields the same
broken result ($G = 7.40\,\mathrm{Pa\,m^{-1}}$, $2.95\,\mathrm{Pa}$), which rules
out the explanation that the ramp increment is too small to be resolved.

The instrumented pressure increment along the centreline shows the collapse
directly; only the fixed version propagates the boundary datum into the interior.

```text
phi (as shipped) = [1.067e-2, -1.18e-3,  2.07e-3,  1.14e-3,  7.90e-4,  4.31e-4, 0]
phi (fixed)      = [1.067e-2,  1.017e-2, 9.66e-3,  8.13e-3,  5.59e-3,  3.05e-3, 0]
```

### 4.3 Remedy

Treating the pressure on the Dirichlet-pressure facets as known data and retaining
its boundary term explicitly,

```python
F1 += dot(p_D * n, v) * ds(inlet_facets)      # n = FacetNormal(mesh)
```

leaves $\mu\nabla\mathbf{u}\cdot\mathbf{n} = 0$ as the only naturally imposed
condition — the correct interface condition for a boundary loaded by an external
pressure $p_D$. `ipcs_traction.py` implements this as `IPCSSolverTraction`, a
subclass of `IPCSSolver`, so the shared solver is left untouched:

```python
solver = IPCSSolverTraction(V, Q, bcu, bcp, dt, rho, mu, ds_inlet, p_const)
solver.p_traction.value = p_inlet(t)          # update every time step
```

Two cheaper alternatives should be noted.

1. **Use Chorin** (the default of this demo). No code change is required and the
   pressure field is already exact; the only cost is Chorin's
   $O(\Delta t)$ steady-state pressure error when an immersed body force is present
   (see [demo_423](/afsi/demo-423/)).
2. **Drive with a body force** $\mathbf{f} = G\,\mathbf{e}_x$ and impose the
   pressure Dirichlet only at the outlet. This is well posed for either solver, but
   $p\_$ then holds only the incompressibility part of the pressure; the physical
   pressure is $p_{\text{phys}} = -Gx + p\_ + \text{const}$.

Finally, a separate and independent defect in `IPCSSolver` is worth fixing: its
velocity update (`A3 = assemble_matrix(a3)`) is assembled **without** `bcu`, and
`set_bc` is never called, so the corrected velocity does not re-satisfy no-slip at
the walls. `ChorinSolver` does apply `bcu` in the corresponding step.

## 5. Reproducibility

```bash
conda activate afsi-dolfinx
cd afsic/demo/demo_424

CASE=open   NY=45 python generate_mesh.py && CASE=open   NY=45 python main.py
CASE=closed NY=45 python generate_mesh.py && CASE=closed NY=45 python main.py

# solid-free control: isolates the open-boundary treatment from the IB coupling
CASE=open NY=45 T_END=0.2 python test_channel.py

# the IPCS diagnosis and its remedy
SOLVER=chorin   NY=9 T_END=0.2 python test_ipcs.py
SOLVER=ipcs     NY=9 T_END=0.2 python test_ipcs.py
SOLVER=ipcs_fix NY=9 T_END=0.2 python test_ipcs.py
```

The environment variables `CASE`, `NY`, `SOLID_DIV`, `DT`, `T_END`, `RAMP_T`,
`SOLVER`, `DP_MMHG`, `BETA` and `DIAG` override the values of Tables 2 and 3.

## 6. Summary and open items

The imposed pressure gradient is reproduced to $0.06\,\%$ at both resolutions, the
velocity field converges to the analytical Poiseuille solution at first order in
$h$ with a leading immersed-interface error of about $5\,\%$, and the immersed
membrane holds $98.5\,\% \to 99.6\,\%$ of the applied pressure difference at
second-order convergence. The remaining discrepancies all trace to a single cause —
the immersed wall is only two to four cells thick — which also limits the recovery
of the analytical bypass flow rate to $25\,\% \to 39\,\%$. The IPCS defect
documented in Section 4 makes that solver unusable for a pressure-driven inflow;
the verified remedy restores the exact gradient.

Open items:

* $N_y = 180$ (wall eight cells thick) would establish whether $Q_{\text{gap}}$
  also begins to converge; at roughly four times the cost of $N_y = 90$ this is an
  approximately four-hour run.
* The occluded case needs a longer $T$, or a steady-state solver, to settle; it
  oscillates at both resolutions.
* The solid meshes at $N_y = 45$ and $N_y = 90$ place the inner wall surfaces at
  cell centres ($7.5h$) and on grid lines ($15h$) respectively. An immersed method
  does not require alignment, but the two levels are not geometrically identical in
  this respect.
* The $N_y = 90$ field snapshots were not retained on this machine (only their
  verification summaries), so the field figures are the $N_y = 45$ runs.

<div class="references">

**References**

1. Ma, P., Cai, L., Wang, X., Gao, H. *AFSI: Automated Fluid-Structure Interaction
   Solver Development for Nonlinear Solid Mechanics.* arXiv:2509.00014 (2025).
2. Chorin, A. J. *Numerical solution of the Navier–Stokes equations.* Mathematics
   of Computation 22 (1968) 745–762.
3. Peskin, C. S. *The immersed boundary method.* Acta Numerica 11 (2002) 479–517.
4. AFSI source `afsic/demo/demo_424` (`configuration.py`, `generate_mesh.py`,
   `main.py`, `verify.py`, `test_channel.py`, `test_ipcs.py`, `ipcs_traction.py`).

</div>
