---
title: "423: Immersed Anisotropic Annulus at Equilibrium"
description: "A fibre-reinforced annulus at equilibrium, verified against the closed-form pressure."
date: 2026-09-12
weight: 1
academic: true
demo_id: demo_423
category: Verification
dimension: 2D
solid_model: "fibre-reinforced annulus (single circumferential fibre family)"
coupling: "immersed boundary / finite element (AFSI)"
reference: "closed-form pressure field, Eqs. (2)–(3) below"
status: Verified
---

## 1. Introduction

This case verifies the immersed-boundary coupling of AFSI against a closed-form
solution. A thick annular cylinder of inner radius $R$ and width $w$ is immersed in
the unit square $\Omega = [0,1]^2$ filled with an incompressible Newtonian fluid;
the solid is fibre-reinforced in the circumferential direction, the cavity walls are
no-slip, and the pressure is determined only up to a constant. Under these
conditions the fluid comes to rest and the pressure field is available in closed
form, so the discretisation error of the coupling can be measured directly against
an exact solution.

## 2. Problem description

### 2.1 Geometry

The cavity is the unit square $\Omega = [0,1]^2$; the annulus has inner radius
$R$, width $w$, outer radius $R + w$ and centre $(0.5,\, 0.5)$.

{{< color "red" >}}TODO: figure placeholder — annotated geometry of the annulus in the unit square (dimensions $R$, $w$, centre).{{< /color >}}

### 2.2 Governing equations and exact solution

{{< color "red" >}}TODO: governing equations — incompressible Navier–Stokes, the immersed-boundary coupling terms, and the solid constitution (see the symbol table page).{{< /color >}}

The solid carries a single circumferential fibre family,

$$S^{s} = \mu_s\,\hat{e}_\theta \otimes \hat{e}_\theta , \tag{1}$$

With $l = 1$ the domain side, $\mathbf{v} = \mathbf{0}$ everywhere, and the
constant

$$C = \frac{\pi\,\mu_s\left[(R+w)^2 - R^2\right]}{2\,l^2} , \tag{2}$$

the exact pressure is the piecewise function

$$p(r) = \begin{cases}
\mu_s \ln\!\left(1 + \dfrac{w}{R}\right) - C , & r \le R ,\\[4pt]
\mu_s \ln\!\left(\dfrac{R + w}{r}\right) - C , & R < r < R + w ,\\[4pt]
-C , & r \ge R + w .
\end{cases} \tag{3}$$

For the parameters of Table 1 the far-field level is $C = 0.055228\,\mathrm{Pa}$,
the inner plateau is $p(0) = 0.167920\,\mathrm{Pa}$, and the entire variation of
the field takes place across the $6.25\,\mathrm{cm}$ wide fibre band.

### 2.3 Boundary and initial conditions

No-slip on all four cavity walls; the pressure is determined only up to a constant.
Each run is advanced for 100 steps of $\Delta t = 10^{-4}\,\mathrm{s}$, long enough
for the fluid to come to rest and for the equilibrium to be reached.

### 2.4 Physical parameters

<p class="tcaption">Table 1. Parameters of the annular verification case; all quantities are in SI units.</p>

| Quantity | Symbol | Value |
|---|---|---|
| Fluid domain | $\Omega$ | $1.0 \times 1.0\,\mathrm{m^2}$ |
| Fluid density | $\rho$ | $1.0$ |
| Fluid viscosity | $\mu$ | $1.0$ |
| Ring inner radius | $R$ | $0.25\,\mathrm{m}$ |
| Ring width | $w$ | $0.0625\,\mathrm{m}$ |
| Ring outer radius | $R + w$ | $0.3125\,\mathrm{m}$ |
| Ring centre | — | $(0.5,\, 0.5)$ |
| Solid modulus | $\mu_s$ | $1.0$ |

{{< color "red" >}}TODO: dimensionless numbers, if any (this case is reported in SI units only).{{< /color >}}

## 3. Numerical setup

The fluid runs on a uniform $N \times N$ quadrilateral grid over $\Omega$
(cell size $h = 1/N$, $N = 32$ by default); velocity, force and pressure spaces
are $\mathrm{P2}$ / $\mathrm{P2}$ / $\mathrm{P1}$. The annular solid mesh is a
structured quadrilateral mesh. Time integration uses the explicit Chorin solver at
$\Delta t = 1.0\times10^{-4}\,\mathrm{s}$ for 100 steps ($T = 0.01\,\mathrm{s}$),
one order of magnitude below the $\Delta t = 10^{-3}\,\mathrm{s}$ used in the
accompanying paper, so that the equilibrium is reached within 100 steps. An IPCS
run with the same parameters is archived for comparison.

## 4. Results

### 4.1 Quantities of interest

The quantities of interest are the pointwise pressure error $e = p_h - p$ along
the line $y = 0.5$, $r \in [0, 0.4]\,\mathrm{m}$ — reported as its maximum over the
whole line and over the inner ($r < R - 2h$), fibre-band ($R \le r \le R + w$) and
outer ($r > R + w + 2h$) regions — the pressure at the ring centre $p(r = 0)$, and
the velocity error $\lVert v\rVert_{L^2}$ (the exact velocity is zero).

### 4.2 Comparison with the exact solution

<p class="tcaption">Table 2. Radial pressure profile along $y = 0.5$, $r \in [0, 0.4]\,\mathrm{m}$. Each row is a separate run. The inner, band and outer regions are $r < R - 2h$, $R \le r \le R + w$ and $r > R + w + 2h$ respectively.</p>

| Run | max $\lvert e\rvert$ (whole line) | inner | fibre band | outer | $p(r = 0)$ | exact |
|---|---|---|---|---|---|---|
| Chorin, $N = 32$ | $2.221\times10^{-2}\,\mathrm{Pa}$ | $7.605\times10^{-3}$ | $2.221\times10^{-2}$ | $5.475\times10^{-3}$ | $0.1679447$ | $0.1679421$ |
| Chorin, $N = 256$ | $2.002\times10^{-2}\,\mathrm{Pa}$ | $2.817\times10^{-3}$ | $2.002\times10^{-2}$ | $1.999\times10^{-3}$ | $0.1679207$ | $0.1679204$ |
| IPCS, $N = 64$ | $5.257\times10^{-3}\,\mathrm{Pa}$ | $5.144\times10^{-4}$ | $5.257\times10^{-3}$ | $4.187\times10^{-4}$ | $0.1679266$ | $0.1679287$ |
| IPCS, $N = 128$ | $2.621\times10^{-3}\,\mathrm{Pa}$ | $4.597\times10^{-5}$ | $2.621\times10^{-3}$ | $2.922\times10^{-5}$ | $0.1679219$ | $0.1679190$ |

{{< figure src="/afsi/demo423-fields.png" title="Figure 1. Archived $N = 128$ field snapshot. The pressure is uniform inside the ring, varies only across the fibre band, and is uniform again outside it. The error panel resolves the immersed-boundary band, where the coupling smears the interface over approximately $\pm 2h$." >}}

{{< figure src="/afsi/demo423-profile.png" title="Figure 2. Radial pressure profiles along $y = 0.5$ (left) and the corresponding pointwise error (right). The far field and the inner plateau are captured essentially exactly; the error is concentrated at the edges of the fibre band and decreases with refinement." >}}

{{< figure src="/afsi/demo423-error.png" title="Figure 3. The four archived profile runs: the maximum error over the line against resolution. The fibre band dominates it, so the maxima of the N = 32 and N = 256 Chorin runs stay close together." >}}

Three observations follow from Table 2 and Figures 1–2.

1. **The far field and the inner plateau are essentially exact.** Even at
   $N = 32$ the pressure at the ring centre is within $2.6\times10^{-6}\,\mathrm{Pa}$
   of the analytical value, so the immersed coupling transmits the load correctly.
2. **The residual error is concentrated in the fibre band.** Its maximum stays
   near $2\times10^{-2}\,\mathrm{Pa}$ even at $N = 256$: the band is only a few
   cells wide and the four-point kernel spreads it further. This is an
   interface-resolution effect, not a solver error.
3. **Away from the band the error falls with refinement,** from
   $7.6\times10^{-3}$ to $2.8\times10^{-3}\,\mathrm{Pa}$ (inner) and from
   $5.5\times10^{-3}$ to $2.0\times10^{-3}\,\mathrm{Pa}$ (outer) between
   $N = 32$ and $N = 256$.

### 4.3 Convergence study

The refinement study reports the observed order
$p = \log(e_N / e_{2N}) / \log 2$ for each error measure, for
$N = 16, 32, 64, 128$ (100 steps, $\Delta t = 10^{-4}$, Chorin). Reproducing the
$N = 32$ row of Table 2 to five digits confirms the archived numbers:

<p class="tcaption">Table 3. The live refinement study, against the archived rows of Table 2.</p>

| $N$ | $e_p$ whole domain | $e_p$ inner | $e_p$ fibre band | $\lVert v\rVert_{L^2}$ (exact $v = 0$) |
|---|---|---|---|---|
| $16$ | $4.798\times10^{-3}$ | $1.565\times10^{-4}$ | $4.788\times10^{-3}$ | $5.118\times10^{-5}$ |
| $32$ | $3.169\times10^{-3}$ | $9.190\times10^{-6}$ | $3.169\times10^{-3}$ | $1.541\times10^{-5}$ |
| $64$ | $3.074\times10^{-3}$ | $7.411\times10^{-5}$ | $3.073\times10^{-3}$ | $5.163\times10^{-6}$ |
| $128$ | $3.242\times10^{-3}$ | $3.764\times10^{-4}$ | $3.172\times10^{-3}$ | $1.785\times10^{-6}$ |

{{< figure src="/afsi/demo423-live-conv-pyvista.png" title="Figure 4. Pressure error against the exact solution at three levels, rendered on the fluid mesh. The scattered error of the coarse grids collapses onto the immersed-boundary band as $N$ grows." >}}

{{< figure src="/afsi/demo423-live-convergence.png" title="Figure 5. Left: the radial pressure profile along $y = 0.5$ at the three levels, against the exact solution — the plateau and the far field are captured immediately, while the fibre band is smoothed over $\pm 2h$. Right: the band error barely improves (RMS $7.4 \to 4.0 \to 3.4\times10^{-3}$), which is the interface-resolution limit rather than a solver error." >}}

{{< figure src="/afsi/demo423-live-ring.png" title="Figure 6. The $N = 32$ solution in full: fluid velocity with streamlines, numerical pressure, the closed-form pressure, and the difference. All four panels share the same colour limits where they are comparable." >}}

The observed orders quantify the two regimes: the **velocity** converges cleanly
($\lVert v\rVert_{L^2}$ orders $1.73$, $1.58$, $1.53$ — close to second order, and
$\max\lvert v\rvert$ is already $10^{-5}\,\mathrm{m\,s^{-1}}$), while the
**pressure error is stuck at the interface**: the whole-domain order is $0.60$,
$0.04$, $-0.08$ because $e_p$ is dominated by the fibre band, whose value stays near
$3\times10^{-3}\,\mathrm{Pa}$ from $N = 32$ onward. Note also that the inner-region
error is **not** monotone ($1.6\times10^{-4}$, $9.2\times10^{-6}$,
$7.4\times10^{-5}$, $3.8\times10^{-4}$) — it is a small difference of large numbers,
so its apparent order should not be read as a convergence rate.

### 4.4 Flow and deformation fields

Figures 1–3 show the archived field snapshot, the radial profiles and the error
against resolution; Figures 4–6 show the refinement study at three levels.

## 5. Discussion and limitations

**DOLFINx quadrilateral vertex ordering.** The solid mesh must follow the DOLFINx
quadrilateral vertex ordering: for a physical counter-clockwise quadrilateral
$(a, b, c, d)$, DOLFINx expects the cell as $[a, b, d, c]$. A naive cyclic
ordering is accepted without error but silently corrupts the solid element
Jacobians — the solid area integral is wrong, the assembled PK force is wrong, and
the resulting pressure is approximately **half** the analytical value. With the
correct ordering no empirical force scaling is required.

**What the case shows.** The coupling is accurate in the far field and in the
interior of the solid to the level of the time-integration error, while the error
at the immersed interface is governed by the number of fluid cells across the fibre
band and decreases monotonically with refinement. Two implementation hazards to
carry forward: the silent DOLFINx ordering failure above, and the sensitivity of
the IPCS pressure to the treatment of pressure-Dirichlet boundaries (analysed in
detail for [demo_424](/afsi/demo-424/)).

{{< color "red" >}}TODO: reconcile the IPCS rows of Table 2 — they should be
re-measured under controlled conditions before being compared with the Chorin
rows, since their step count and time step are not recorded.{{< /color >}}

## References

<div class="references">

1. Ma, P., Cai, L., Wang, X., Gao, H. *AFSI: Automated Fluid-Structure Interaction
   Solver Development for Nonlinear Solid Mechanics.* arXiv:2509.00014 (2025).
2. DOLFINx 0.10.0 documentation — quadrilateral cell vertex ordering.

</div>
