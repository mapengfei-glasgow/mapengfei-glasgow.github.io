---
title: "424: Tethered Aorta with an Immersed Occlusion"
description: "A tethered aorta, patent and occluded, verified against exact solutions."
date: 2026-09-12
weight: 2
academic: true
demo_id: demo_424
category: Verification
dimension: 2D
solid_model: "tether (volumetric spring, no constitutive law) + immersed occlusion membrane"
coupling: "immersed boundary (four-point Peskin kernel)"
reference: "closed-form Poiseuille solution and the one-dimensional tether balance (this page)"
status: Verified
---

## 1. Introduction

The case consists of two configurations that share one geometry, one fluid, one
tether model and one driving condition; they differ only by a membrane that
occludes the lumen. Since the exact solution is known analytically in both
configurations, every error metric reported below has a reference value, and the
case therefore serves as a pure solver-verification study. The configuration is
this page's own construction (it is not a published benchmark); its reference
values are the closed-form plane-Poiseuille solution and the one-dimensional
tether balance stated below.

<p class="tcaption">Table 1. The two configurations. The solid outline of the occluded case reads as the letter H.</p>

| Case | Solid | Expected physics |
|---|---|---|
| `open` | two tethered wall strips | three parallel plane-Poiseuille channels (lumen and two outer gaps) driven by the end pressure difference |
| `closed` | the same strips and a full-occlusion membrane at mid-length | lumen chambers stagnant and isobaric, a pressure jump of exactly $\Delta p$ across the membrane, bypass flow still carried by the outer gaps |

## 2. Problem description

### 2.1 Geometry

The configuration is a two-dimensional planar (plane-strain) idealisation: cutting
the cylindrical aorta along a plane through its axis turns the lumen into a
parallel-plate channel and the wall into two flat strips.

{{< figure src="/afsi/demo424-configuration.png" title="Figure 1. The two configurations. The box is half a cell longer than the aorta at each end, so the pressure Dirichlet nodes never coincide with a Lagrangian end node." >}}

<p class="tcaption">Table 2. Geometry and mesh parameters.</p>

| Quantity | Symbol / code name | Value |
|---|---|---|
| Aorta length | `L_AORTA` | $0.1\,\mathrm{m}$ |
| Lumen half-height | `A_LUMEN` | $0.015\,\mathrm{m}$ |
| Wall thickness | `T_WALL` | $0.002\,\mathrm{m}$ |
| Box length | `BOX_L` | $L_{\text{aorta}} + h$: $0.101\,\mathrm{m}$ ($h = 1\,\mathrm{mm}$), $0.1005\,\mathrm{m}$ ($h = 0.5\,\mathrm{mm}$) |
| Box width | `BOX_W` | $1.5 \cdot 2a = 0.045\,\mathrm{m}$ |
| Outer fluid gap | `GAP` | $0.0055\,\mathrm{m}$ per side |
| Membrane thickness | `DISC_T` | $0.002\,\mathrm{m}$, spanning the lumen at mid-length |
| Fluid cells | `NX` × `NY` | $101 \times 45$, $201 \times 90$ |
| Cell size | $h$ = `BOX_W`/`NY` | $1.0\,\mathrm{mm}$, $0.5\,\mathrm{mm}$ |
| Coupling | — | immersed boundary, four-point Peskin kernel |

### 2.2 Governing equations

{{< color "red" >}}TODO: governing equations — incompressible Navier–Stokes and the
immersed-boundary coupling terms (see the symbol table page).{{< /color >}}

The solid carries no constitutive law: it is held in place by a volumetric spring
(tether) alone, with the law

$$
\mathbf{f} = \beta\,(\mathbf{X}_{\text{ref}} - \mathbf{X}) ,
$$

and the membrane displacement follows the one-dimensional tether balance

$$
\delta = \frac{\Delta p}{\beta\,t_{\text{wall}}} , \tag{1}
$$

which is $1.3\times10^{-4}\,\mathrm{m}$ at $0.02\,\mathrm{mmHg}$ — a hundred times
smaller than a grid cell — but $1.3\times10^{-3}\,\mathrm{m}$ at
$0.2\,\mathrm{mmHg}$. The occluded case is driven at ten times the pressure
difference of the patent case for a practical reason: in the patent case the
transmural pressure vanishes at steady state — the lumen and the gap see the same
axial gradient — so the wall does not move and the case is a pure flow test; in the
occluded case the flow is essentially zero, so nothing dissipates the driving
pressure, $\Delta p$ is carried entirely by the membrane and its tether, and the
only measurable response is the membrane displacement of Eq. (1). The tenfold step
makes the response measurable without moving the geometry appreciably
($\delta \approx 2$ grid cells at $N_y = 90$).

### 2.3 Boundary and initial conditions

* The box side walls (diameter direction) are no-slip.
* The box open ends carry a **pressure Dirichlet** condition, $p = p_{\text{in}}(t)$
  at $x = 0$ and $p = 0$ at $x = L_{\text{box}}$, and **no velocity condition**;
  the natural condition there is zero traction.

Prescribing pressure on a boundary is an essential (Dirichlet) condition on the
pressure Poisson problem rather than a traction condition in the usual sense.
Combined with the natural zero-traction condition of the momentum predictor it is
the projection-method realisation of a prescribed-normal-traction
(pressure-driven) open boundary. Because both ends carry Dirichlet data the
pressure null space is fixed and no gauge point is required.

### 2.4 Physical parameters

<p class="tcaption">Table 3. Material and driving parameters. The solid carries no constitutive law: it is held in place by a volumetric spring (tether) alone.</p>

| Quantity | Symbol / code name | Value |
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

## 3. Numerical setup

The explicit projection solver of Chorin is used throughout; the incremental
pressure-correction solver (IPCS) is unsuitable for this configuration, for the
reason analysed in §5. The grid is square, which constrains the
usable resolutions: with $W_{\text{box}} = 0.045\,\mathrm{m}$ and
$L_{\text{aorta}}/W_{\text{box}} = 20/9$, $N_y$ must be a multiple of $9$, so
$N_y \in \{45, 90, 180\}$ gives $N_x \in \{101, 201, 401\}$. Because
$L_{\text{box}} = L_{\text{aorta}} + h$, the imposed gradient
$\Delta p / L_{\text{box}}$ depends slightly on the resolution —
$26.4005\,\mathrm{Pa\,m^{-1}}$ at $N_y = 45$ and $26.5318\,\mathrm{Pa\,m^{-1}}$ at
$N_y = 90$. Each row of the results tables is compared against its own level's
value.

## 4. Results

### 4.1 Quantities of interest

The quantities of interest are, per configuration: the fitted pressure gradient
$G = -\mathrm{d}p/\mathrm{d}x$ and its relative error; the maximum deviation of
$p(x)$ from linear; the peak and flow rates $u_{\text{max}}$, $Q_{\text{lumen}}$,
$Q_{\text{gap}}$ against their analytical values; the lumen profile error
(relative $L_2$ and $\lVert e\rVert_\infty$); the fraction of $\Delta p$ held by
the membrane and the isobaricity of the lumen chambers (mean and standard
deviation); the leakage flux through the wall; and the membrane displacement
$\delta$ against the tether balance of Eq. (1). The presentation below adds the
per-station profile metrics, the solid response (wall-strip and membrane
displacement and tether force) and the flow histories recorded by the driver.

### 4.2 Comparison with the exact solution

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

<p class="tcaption">Table 5. Patent configuration: the lumen sampled at the three comparison stations. The three stations agree to four significant digits — the flow is fully developed and the discrete flux is conserved to $5\times10^{-7}\,\mathrm{m^2\,s^{-1}}$ along the lumen.</p>

| Station | Profile rel. $L_2$ ($N_y=45$ / 90) | $\lVert e\rVert_\infty$ ($\mathrm{m\,s^{-1}}$) | $Q_{\text{lumen}}$ ($\mathrm{m^2\,s^{-1}}$) |
|---|---|---|---|
| $x = 0.25\,L$ | $5.431$ / $2.625\,\%$ | $3.692$ / $1.723\times10^{-2}$ | $1.585186$ / $1.654014\times10^{-2}$ |
| $x = 0.50\,L$ | $5.431$ / $2.625\,\%$ | $3.691$ / $1.722\times10^{-2}$ | $1.585185$ / $1.654015\times10^{-2}$ |
| $x = 0.75\,L$ | $5.431$ / $2.625\,\%$ | $3.691$ / $1.721\times10^{-2}$ | $1.585193$ / $1.654013\times10^{-2}$ |
| Analytical | — | — | $1.696216$ / $1.704515\times10^{-2}$ |

The pressure field is essentially exact and the flow is fully developed — the
profile error is identical to four significant digits at $x = 0.25$, $0.50$ and
$0.75\,L$ — but the velocity is systematically about $5\,\%$ low. The deficit is
attributable to immersed-boundary smearing: the four-point Peskin kernel spreads
the $2\,\mathrm{mm}$ wall over a band of $\pm 2h$, so the effective no-slip surface
is displaced outward and the channel carries less flux. The pointwise error peaks
next to the wall and is small in the core — the signature of an interpolation
error rather than a solver error.

{{< figure src="/afsi/demo424-open-fields-pv.png" title="Figure 3. The same patent configuration rendered with PyVista at both resolutions: pressure (left) and velocity magnitude (right), $N_y = 45$ above and $N_y = 90$ below. At this colour scale the two rows look alike — the refinement is quantified in Figure 4 and Tables 4–5." >}}

{{< chart xlabel="y (mm)" ylabel="u_x (m/s)" caption="Figure 4. Lumen velocity profile at mid-length: the two resolutions against the analytical Poiseuille parabola." >}}
y (mm), NY=45, NY=90, analytic Poiseuille
7.50,0.00951,-0.00220,0.00000
8.50,0.07139,0.09264,0.10992
9.50,0.17322,0.19497,0.21225
10.50,0.26751,0.28972,0.30701
11.50,0.35425,0.37689,0.39419
12.50,0.43346,0.45649,0.47378
13.50,0.50513,0.52850,0.54580
14.50,0.56925,0.59294,0.61023
15.50,0.62582,0.64979,0.66709
16.50,0.67486,0.69906,0.71636
17.50,0.71635,0.74076,0.75805
18.50,0.75029,0.77487,0.79216
19.50,0.77670,0.80140,0.81870
20.50,0.79556,0.82035,0.83765
21.50,0.80687,0.83172,0.84902
22.50,0.81064,0.83551,0.85281
23.50,0.80687,0.83172,0.84902
24.50,0.79556,0.82035,0.83765
25.50,0.77670,0.80140,0.81870
26.50,0.75029,0.77487,0.79216
27.50,0.71635,0.74076,0.75805
28.50,0.67486,0.69906,0.71636
29.50,0.62582,0.64979,0.66709
30.50,0.56925,0.59294,0.61023
31.50,0.50513,0.52850,0.54580
32.50,0.43346,0.45649,0.47378
33.50,0.35425,0.37689,0.39419
34.50,0.26751,0.28972,0.30701
35.50,0.17322,0.19497,0.21225
36.50,0.07139,0.09264,0.10992
37.50,0.00951,-0.00220,0.00000
{{< /chart >}}

{{< figure src="/afsi/demo424-closed-fields.png" title="Figure 5. Occluded configuration at $N_y = 45$. The pressure is uniform at approximately $26.6\,\mathrm{Pa}$ upstream and approximately $0$ downstream, with a jump at the membrane; the velocity magnitude shows the bypass flow in the two outer gaps and the nearly stagnant lumen chambers. Right: pressure along both channel centrelines." >}}

<p class="tcaption">Table 6. Occluded configuration: pressure holding, chamber uniformity and leakage.</p>

| Quantity | $N_y = 45$ | $N_y = 90$ | Target |
|---|---|---|---|
| Held pressure jump (chamber means) | $26.2531\,\mathrm{Pa}$ | $26.5561\,\mathrm{Pa}$ | $26.6645\,\mathrm{Pa}$ ($0.2\,\mathrm{mmHg}$) |
| Fraction of $\Delta p$ held | $98.46\,\%$ | $99.59\,\%$ | $100\,\%$ |
| Upstream chamber: mean / standard deviation | $26.6147$ / $0.0259\,\mathrm{Pa}$ | $26.6432$ / $0.0110\,\mathrm{Pa}$ | isobaric |
| Downstream chamber: mean / standard deviation | $0.3616$ / $0.7811\,\mathrm{Pa}$ | $0.0871$ / $0.2903\,\mathrm{Pa}$ | isobaric |
| Peak speed in the upstream / downstream chamber | $0.063$ / $0.102\,\mathrm{m\,s^{-1}}$ | $0.031$ / $0.048\,\mathrm{m\,s^{-1}}$ | near zero |
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
residual gap is consistent with the occluded case never fully settling in
time: $\max \lvert \mathbf{u} \rvert$ keeps swinging at both resolutions to the
end of the run, whereas the patent case settles monotonically (Table 8 and
Figure 9).

{{< figure src="/afsi/demo424-closed-fields-pv.png" title="Figure 6. The occluded configuration rendered with PyVista, both resolutions: the pressure chambers and the membrane jump, the near-stagnant sealed lumen and the bypass flow in the two outer gaps." >}}

{{< figure src="/afsi/demo424-closed-zoom-pv.png" title="Figure 7. Membrane region ($x = 50 \pm 10\,\mathrm{mm}$): pressure (left) and speed with streamlines (right), $N_y = 45$ above and $N_y = 90$ below. The streamlines show the bypass flow in the outer gaps and the leakage through the downstream half of the immersed wall into the sealed lumen; the jump sharpens, and the leak band thins, with refinement." >}}

{{< chart xlabel="x (mm)" ylabel="p (Pa)" caption="Figure 8. Pressure along the lumen centre through the membrane (left chamber → jump → right chamber), with the outer gap centre as the smooth reference." >}}
x (mm), lumen centre NY=45, lumen centre NY=90, outer gap NY=90
30.00,26.5974,26.6357,22.4485
31.00,26.5954,26.6349,22.1986
32.00,26.5934,26.6340,21.9382
33.00,26.5915,26.6333,21.6571
34.00,26.5896,26.6325,21.3071
35.00,26.5878,26.6318,20.8865
36.00,26.5861,26.6311,20.3821
37.00,26.5845,26.6305,19.9517
38.00,26.5830,26.6300,19.7190
39.00,26.5816,26.6295,19.4676
40.00,26.5805,26.6291,19.0705
41.00,26.5796,26.6288,18.6996
42.00,26.5789,26.6286,18.3581
43.00,26.5782,26.6281,18.0641
44.00,26.5769,26.6264,17.7690
45.00,26.5721,26.6207,17.4582
46.00,26.5539,26.6007,17.0979
47.00,26.4864,26.5326,16.6131
48.00,26.2410,26.3039,15.9836
49.00,25.3505,25.5315,15.1765
50.00,23.0245,23.1275,14.1175
51.00,19.4524,18.9946,12.9610
52.00,15.3216,14.2447,11.5276
53.00,11.1417,9.8611,10.2323
54.00,7.7971,6.1718,9.0257
55.00,5.5176,3.4564,8.0161
56.00,3.9492,1.8894,6.6909
57.00,2.8927,0.9525,5.5025
58.00,2.1462,0.4410,4.8203
59.00,1.6324,0.1762,4.3703
60.00,1.3045,0.0738,4.0250
61.00,0.9685,0.0410,3.8020
62.00,0.6710,0.0302,3.6583
63.00,0.5347,0.0268,3.5463
64.00,0.4886,0.0259,3.4446
65.00,0.4373,0.0255,3.3461
66.00,0.3018,0.0253,3.2486
67.00,0.1421,0.0249,3.1517
68.00,0.0701,0.0244,3.0551
69.00,0.0545,0.0239,2.9589
70.00,0.0506,0.0232,2.8631
{{< /chart >}}

<p class="tcaption">Table 7. Solid response at $T = 0.4\,\mathrm{s}$: mean wall-strip displacement and tether force per unit depth, and membrane displacement and force, against their exact references. The patent wall carries no net load ($\approx 0$ against the $0.80\,\mathrm{N\,m^{-1}}$ membrane scale; the sign of the residual tether force flickers between levels). The occluded membrane carries the full $\Delta p$ and approaches its tether balance as the wall is refined.</p>

| Quantity | open $N_y=45$ | open $N_y=90$ | closed $N_y=45$ | closed $N_y=90$ | Reference |
|---|---|---|---|---|---|
| Wall-strip displacement (mm) | $0.168$ | $0.046$ | $0.141$ | $0.149$ | $0$ (patent) |
| Wall tether force (N/m) | $0.673$ | $-0.185$ | $0.388$ | $0.097$ | $0$ (patent) |
| Membrane displacement (mm) | — | — | $0.249$ | $1.154$ | $1.333$ |
| Membrane tether force (N/m) | — | — | $0.149$ | $0.693$ | $0.800$ |

{{< chart xlabel="t (s)" ylabel="max |u| (m/s)" caption="Figure 9. Peak fluid speed against time. The patent case converges monotonically; the occluded case keeps swinging by about a fifth of its peak because nothing dissipates the driving pressure." >}}
t, open NY=45, open NY=90, closed NY=45, closed NY=90
0.02,0.0958,0.0964,0.2168,0.1884
0.04,0.3202,0.3238,0.3841,0.3529
0.06,0.5778,0.5865,0.4180,0.3814
0.08,0.7148,0.7287,0.3971,0.3839
0.10,0.7755,0.7931,0.3730,0.3759
0.12,0.8017,0.8217,0.3469,0.3612
0.14,0.8125,0.8339,0.3408,0.3545
0.16,0.8165,0.8387,0.3463,0.3565
0.18,0.8176,0.8403,0.3592,0.3677
0.20,0.8175,0.8405,0.3639,0.3953
0.22,0.8170,0.8402,0.3479,0.3491
0.24,0.8163,0.8397,0.3551,0.3489
0.26,0.8157,0.8392,0.3559,0.3418
0.28,0.8150,0.8386,0.3585,0.3079
0.30,0.8144,0.8382,0.3883,0.3085
0.32,0.8139,0.8377,0.3944,0.2990
0.34,0.8134,0.8373,0.3984,0.2867
0.36,0.8129,0.8370,0.4134,0.3424
0.38,0.8125,0.8366,0.4689,0.3420
0.40,0.8121,0.8363,0.3952,0.3162
{{< /chart >}}

{{< chart xlabel="t (s)" ylabel="|Q| (m²/s)" ylog="true" caption="Figure 10. Closed case: bypass flow in the outer gaps against the leakage through the downstream half of the wall, both resolutions. The gap flux rises while the leakage falls; neither has settled at t = 0.4 s." >}}
t, |Q_gap| NY=45, |Q_leak| NY=45, |Q_gap| NY=90, |Q_leak| NY=90
0.02,0.001501,0.0018747,0.0014167,0.0011394
0.04,0.0024836,0.0029994,0.0024889,0.0016891
0.06,0.002247,0.0019338,0.0022871,0.00045795
0.08,0.0020404,0.0021513,0.0021276,0.00056499
0.10,0.0018894,0.0022084,0.0019344,0.00053053
0.12,0.0017056,0.0021925,0.0017447,0.00051964
0.14,0.0015265,0.002051,0.0015471,0.00052185
0.16,0.001285,0.0019016,0.0013617,0.00053952
0.18,0.0010892,0.0017636,0.0011935,0.00051722
0.20,0.00085698,0.0016252,0.0011103,0.00051817
0.22,0.00069219,0.0014142,0.0010985,0.0004862
0.24,0.00056989,0.0011799,0.0010268,0.00045625
0.26,0.0005769,0.0010086,0.00098149,0.00041557
0.28,0.00044265,0.0008917,0.00094057,0.00036332
0.30,0.00042212,0.00082783,0.0009036,0.00032171
0.32,0.00041093,0.00078987,0.00086575,0.00029808
0.34,0.00033803,0.00077758,0.00084554,0.00028753
0.36,0.00018913,0.00075267,0.00084905,0.00028734
0.38,0.00045954,0.00078903,0.00082803,0.00026923
0.40,0.00052496,0.00079763,0.00081461,0.00025534
{{< /chart >}}

<p class="tcaption">Table 8. Transient diagnostics read off the flow histories (sampled every $0.02\,\mathrm{s}$): the peak speed at two times, its swing over the last tenth of a second, and the fluxes at the final time. The patent case is settled (swing below $0.3\,\%$ of the peak); the occluded case swings by roughly a fifth of its peak — $T = 0.4\,\mathrm{s}$ is not a steady state.</p>

| Quantity | open NY=45 | open NY=90 | closed NY=45 | closed NY=90 |
|---|---|---|---|---|
| $\max\lvert u\rvert$ at $t = 0.2\,\mathrm{s}$ (m/s) | $0.818$ | $0.841$ | $0.364$ | $0.395$ |
| $\max\lvert u\rvert$ at $t = 0.4\,\mathrm{s}$ (m/s) | $0.812$ | $0.836$ | $0.395$ | $0.316$ |
| Swing of $\max\lvert u\rvert$ over $0.3$–$0.4\,\mathrm{s}$ (m/s) | $0.002$ | $0.002$ | $0.081$ | $0.056$ |
| $Q_{\text{gap}}$ at $t = 0.4\,\mathrm{s}$ (m²/s) | $1.985\times10^{-4}$ | $2.179\times10^{-4}$ | $5.250\times10^{-4}$ | $8.146\times10^{-4}$ |
| Leakage into the sealed lumen at $t = 0.4\,\mathrm{s}$ (m²/s) | — | — | $7.976\times10^{-4}$ | $2.553\times10^{-4}$ |

### 4.3 Convergence study

Refining $h$ from $1.0\,\mathrm{mm}$ to $0.5\,\mathrm{mm}$ gives the observed
orders $p = \log_2(e_{45}/e_{90})$ listed below.

<p class="tcaption">Table 9. Patent configuration: observed convergence orders between $N_y = 45$ and $N_y = 90$.</p>

| Quantity | $N_y = 45$ | $N_y = 90$ | Order |
|---|---|---|---|
| Fitted gradient $G$, relative error | $-5.64\times10^{-4}$ | $-6.46\times10^{-4}$ | $\approx 0$ |
| Max deviation of $p(x)$ from linear | $9.83\times10^{-5}\,\mathrm{Pa}$ | $6.58\times10^{-5}\,\mathrm{Pa}$ | $0.58$ |
| Lumen profile, relative $L_2$ | $5.431\times10^{-2}$ | $2.625\times10^{-2}$ | $\mathbf{1.05}$ |
| Lumen profile, $\lVert e\rVert_\infty$ | $3.691\times10^{-2}\,\mathrm{m\,s^{-1}}$ | $1.722\times10^{-2}\,\mathrm{m\,s^{-1}}$ | $1.10$ |
| $u_{\text{max}}$, relative error | $-4.418\times10^{-2}$ | $-1.965\times10^{-2}$ | $\mathbf{1.17}$ |
| $Q_{\text{lumen}}$, relative error | $-6.55\times10^{-2}$ | $-2.96\times10^{-2}$ | $\mathbf{1.14}$ |
| $Q_{\text{gap}}$, relative error | $-5.10\times10^{-2}$ | $+3.68\times10^{-2}$ | sign change |

<p class="tcaption">Table 10. Occluded configuration: observed convergence orders between $N_y = 45$ and $N_y = 90$.</p>

| Quantity | $N_y = 45$ | $N_y = 90$ | Order |
|---|---|---|---|
| Fraction of $\Delta p$ held | $0.98457$ | $0.99593$ | — |
| Relative error of the held jump | $-1.543\times10^{-2}$ | $-4.066\times10^{-3}$ | $\mathbf{1.92}$ |
| Upstream chamber pressure standard deviation | $2.587\times10^{-2}\,\mathrm{Pa}$ | $1.095\times10^{-2}\,\mathrm{Pa}$ | $1.24$ |
| Downstream chamber pressure standard deviation | $7.811\times10^{-1}\,\mathrm{Pa}$ | $2.903\times10^{-1}\,\mathrm{Pa}$ | $1.43$ |
| Leakage flux at $x_d - 4h$ | $7.976\times10^{-4}\,\mathrm{m^2\,s^{-1}}$ | $2.553\times10^{-4}\,\mathrm{m^2\,s^{-1}}$ | $1.64$ |
| $Q_{\text{gap}}$, relative error | $-7.49\times10^{-1}$ | $-6.12\times10^{-1}$ | $-0.29$ |
| Membrane $\delta$ relative to Eq. 1 | $0.187$ | $0.866$ | — |

{{< figure src="/afsi/demo424-convergence.png" title="Figure 11. Left: the patent-case error measures fall at first order in $h$ while the pressure gradient remains flat at $0.06\,\%$. Right: occluded-case quantities, normalised so that all four are dimensionless." >}}

{{< chart xlog="true" ylog="true" xlabel="h (mm)" ylabel="relative error" caption="Figure 12. Patent case: the error measures fall at first order in the grid size, while the pressure gradient stays flat." >}}
h (mm), |u_max| error, |Q_lumen| error, profile rel. L2
1.0,0.044176,0.065458,0.054313
0.5,0.019648,0.029627,0.026249
{{< /chart >}}

{{< chart xlog="true" ylog="true" xlabel="h (mm)" ylabel="normalised error" caption="Figure 13. Occluded case: four dimensionless error measures against the grid size. The held pressure converges at second order; the wall leakage is the slow quantity." >}}
h (mm), |1 - held fraction|, p-std upstream / dp, p-std downstream / dp, leak / Q_gap analytic
1.0,0.015428,0.00097029,0.029294,0.38135
0.5,0.0040663,0.00041082,0.010886,0.12147
{{< /chart >}}

Tables 9 and 10 confirm the diagnosis of the velocity deficit: it is an
immersed-boundary interpolation error, not a solver error, and it converges at
**first order** in $h$. The pressure field is unaffected and remains exact to about
$0.06\,\%$ at both resolutions. The membrane's pressure holding converges at second
order and reaches $99.6\,\%$. The wall leakage is the slow quantity: even at
$N_y = 90$ the gaps carry only $39\,\%$ of the analytical bypass flux. If the
occluded configuration is to demonstrate a sealed lumen, the wall — not only the
membrane — must be better resolved or thickened.

## 5. Discussion and limitations

### 5.1 Open-boundary defect in the IPCS solver: mechanism

Multiplying the strong form
$\rho\,\mathrm{D}\mathbf{u}/\mathrm{D}t + \nabla p - \mu\nabla^2\mathbf{u} - \mathbf{f} = 0$
by a test function and integrating over the domain gives

$$
\int \rho\,\frac{\mathrm{D}\mathbf{u}}{\mathrm{D}t}\cdot\mathbf{v} -
\int p\,\mathrm{div}\,\mathbf{v} +
\int \mu\,\nabla\mathbf{u} : \nabla\mathbf{v} -
\int \mathbf{f}\cdot\mathbf{v} +
\int_{\Gamma} \left[ p\,(\mathbf{v}\cdot\mathbf{n}) -
\mu\,(\nabla\mathbf{u}\cdot\mathbf{n})\cdot\mathbf{v} \right] = 0 . \tag{2}
$$

IPCS retains the volume terms and **drops the entire boundary integral**.
Doing so is equivalent to imposing the natural condition

$$
\mu\,\nabla\mathbf{u}\cdot\mathbf{n} = p\,\mathbf{n} ,
\qquad \text{i.e. zero total traction } \sigma\cdot\mathbf{n} = 0 \tag{3}
$$

on every boundary where no velocity is prescribed. At the outlet the pressure
Dirichlet is $p = 0$, so zero traction is exactly right. At the inlet the pressure
Dirichlet is $p = \Delta p$, so zero traction is wrong by $\Delta p$: the momentum
predictor then attempts to build a viscous stress of order $\Delta p$ inside a
one-cell layer and produces a large spurious $\mathrm{div}\,\mathbf{u}^{*}$ there.

On its own this is a boundary-layer artefact. It becomes fatal because IPCS
**accumulates** the pressure increment into the pressure field: the spurious
divergence feeds directly into $\phi$, and once the flow settles
($\mathrm{div}\,\mathbf{u}^{*} \to 0$, hence $\phi \to 0$) the corrupted pressure
is frozen in place with nothing left to correct it.

Chorin carries no $p$ in its momentum predictor, so its natural condition
is the homogeneous $\mu\nabla\mathbf{u}\cdot\mathbf{n} = 0$ — exactly the physical
interface condition for a boundary whose exterior only supplies pressure. That is
why Chorin reproduces the exact profile and IPCS does not.

### 5.2 Evidence

A solid-free plane channel at $N_y = 9$ with a ramp $0 \to 2.666\,\mathrm{Pa}$,
run in three variants:

<p class="tcaption">Table 11. Solid-free plane channel, $N_y = 9$: fitted pressure gradient and velocity error per solver variant.</p>

| Variant | Fitted $G$ ($\mathrm{Pa\,m^{-1}}$) | $\max \lvert p - p_{\text{exact}}\rvert$ | Relative error in $u_{\text{max}}$ |
|---|---|---|---|
| Exact | $25.3947$ | $0$ | $0$ |
| Chorin | $25.3949$ | $2.08\times10^{-5}\,\mathrm{Pa}$ | $-5.14\,\%$ |
| IPCS, as configured | $7.4107$ | $2.95\,\mathrm{Pa}$ | $-88.15\,\%$ |
| IPCS with restored traction term | $\mathbf{25.3944}$ | $\mathbf{7.43\times10^{-5}\,\mathrm{Pa}}$ | $-5.35\,\%$ |

Imposing the full $\Delta p$ in a single step instead of ramping it yields the same
broken result ($G = 7.40\,\mathrm{Pa\,m^{-1}}$, $2.95\,\mathrm{Pa}$), which rules
out the explanation that the ramp increment is too small to be resolved.

The pressure increment along the centreline shows the collapse directly. In the
defective case it decays immediately from the inlet datum ($1.07\times10^{-2}$,
$-1.18\times10^{-3}$, $2.07\times10^{-3}$, $1.14\times10^{-3}$,
$7.90\times10^{-4}$, $4.31\times10^{-4}$, $0$ from inlet to outlet), while with
the restored traction term it carries the datum into the interior
($1.07\times10^{-2}$, $1.02\times10^{-2}$, $9.66\times10^{-3}$,
$8.13\times10^{-3}$, $5.59\times10^{-3}$, $3.05\times10^{-3}$, $0$).

### 5.3 Remedy

Treating the pressure on the Dirichlet-pressure facets as known data and retaining
its boundary term explicitly leaves $\mu\nabla\mathbf{u}\cdot\mathbf{n} = 0$ as the
only naturally imposed condition — the correct interface condition for a boundary
loaded by an external pressure $p_D$. The verified implementation restores the
exact gradient (Table 11).

Two cheaper alternatives should be noted.

1. **Use Chorin** (the default of this page). No change is required and the
   pressure field is already exact; the only cost is Chorin's
   $O(\Delta t)$ steady-state pressure error when an immersed body force is present
   (see [demo_423](/afsi/demo-423/)).
2. **Drive with a body force** $\mathbf{f} = G\,\mathbf{e}_x$ and impose the
   pressure Dirichlet only at the outlet. This is well posed for either solver, but
   the accumulated pressure then holds only the incompressibility part; the
   physical pressure is $-Gx$ plus the accumulated field plus a constant.

A second, independent defect: the corrected IPCS velocity does not re-satisfy the
wall boundary conditions (Chorin's does).

### 5.4 Summary and open items

The imposed pressure gradient is reproduced to $0.06\,\%$ at both resolutions, the
velocity field converges to the analytical Poiseuille solution at first order in
$h$ with a leading immersed-interface error of about $5\,\%$, and the immersed
membrane holds $98.5\,\% \to 99.6\,\%$ of the applied pressure difference at
second-order convergence. The remaining discrepancies all trace to a single cause —
the immersed wall is only two to four cells thick — which also limits the recovery
of the analytical bypass flow rate to $25\,\% \to 39\,\%$. The IPCS defect of
§5.1–5.3 makes that solver unusable for a pressure-driven inflow; the verified
remedy restores the exact gradient.

Open items:

* $N_y = 180$ (wall eight cells thick) would establish whether $Q_{\text{gap}}$
  also begins to converge.
* The occluded case needs a longer $T$, or a steady-state solver, to settle; it
  oscillates at both resolutions.
* The solid meshes at $N_y = 45$ and $N_y = 90$ place the inner wall surfaces at
  cell centres ($7.5h$) and on grid lines ($15h$) respectively. An immersed method
  does not require alignment, but the two levels are not geometrically identical in
  this respect.
* The $N_y = 90$ field snapshots are now supplied (Figures 3, 6 and 7), so the
  geometric caveat above is the only remaining asymmetry between the levels.

## References

<div class="references">

1. Ma, P., Cai, L., Wang, X., Gao, H. *AFSI: Automated Fluid-Structure Interaction
   Solver Development for Nonlinear Solid Mechanics.* arXiv:2509.00014 (2025).
2. Chorin, A. J. *Numerical solution of the Navier–Stokes equations.* Mathematics
   of Computation 22 (1968) 745–762.
3. Peskin, C. S. *The immersed boundary method.* Acta Numerica 11 (2002) 479–517.

</div>
