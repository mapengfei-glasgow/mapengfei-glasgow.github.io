---
title: "0: Incompressibility, Divergence-Free Interpolation and the Volume Penalty"
description: "Why an immersed structure loses volume, what the reference does about it (CBS kernels or volumetric stabilisation), and what this solver learned calibrating κ_stab — a two-sided window that ends in a locked state."
date: 2026-10-01
weight: 0
academic: true
reference: "Li et al. (2025); Vadala-Roth et al. (2020)"
status: Complete
---

The three benchmark pages (demo_441, demo_442, demo_443) kept running into one
question — *who enforces the incompressibility of the immersed structure?* —
so the material is collected here once, with the reference's own statements and
with the numbers this solver measured.

## 1. The problem: interpolation and the divergence-free condition

In the immersed-boundary coupling the structure and the fluid exchange
information through a regularised delta: the fluid velocity is interpolated to
the Lagrangian markers, and the Lagrangian force is spread back. The fluid is
incompressible ($\nabla \cdot u = 0$), and a material region of an
incompressible flow must keep its volume, i.e. $J = \det F \equiv 1$. The
transfer does not preserve that property by itself: as the reference puts it,
“isotropic regularized delta functions **generally do not provide continuously
divergence-free interpolants**, even when interpolating discretely
divergence-free velocity fields” ({{< cite "li2025local" "author" >}}). The
interpolation error, combined with time-stepping and quadrature errors, lets
the structure lose volume — most visibly, in the reference's words, “for
closed, pressurized membranes” (demo_442) — and the loss grows with the
deformation (demo_443, demo_441).

## 2. What the reference says

Two remedies appear in the reference, and they act at different places.

**Composite B-spline (CBS) kernels.** A construction that “achieve[s]
continuously divergence-free interpolation by using different one-dimensional
B-spline kernels for different velocity components”: the interpolation of a
discretely divergence-free MAC velocity field is then continuously
divergence-free, and no treatment of the material is needed at all.

**Volumetric stabilisation** (the remedy for isotropic kernels such as
$\mathrm{IB}_4$): a volumetric energy $U(J)$ modulated by a *numerical*
Poisson ratio $\nu_S$,

$$
\kappa_S = \frac{2G(1+\nu_S)}{3(1-2\nu_S)},
$$

where $\nu_S = -1$ gives $\kappa_S = 0$ and “recovers the unstabilized
formulation”. The reference stresses that “both $\kappa_S$ and $\nu_S$ are
**numerical** parameters rather than physical ones, as the immersed structure
remains incompressible in all cases”. The justification is a consistency
argument: the treatment “adds consistency terms that vanish under grid
refinement, reduces spurious volume changes in the numerical solution while
**maintaining the convergence properties** of the underlying formulation”
({{< cite "vadalaroth2020" "author" >}}). Without any treatment, “unphysical
and sometimes extreme contractions of the immersed structure” can occur — the
same failure mode that appears below when the volume constraint is
under-protected.

The reference also quotes the costs of the stabilised route, and this solver
reproduces them: “the volumetric penalty terms are known to impose **more
severe time step restrictions** for explicit timestepping schemes”
({{< cite "devendran2012" "author" >}}); “these modifications … introduce
additional isotropic stresses that **alter the pressure response**”; and the
modified invariants “increase the nonlinearity of the stress response, which
can complicate implicit solvers”. One thing the reference does **not**
discuss is a locking-type limit of $\kappa_S$: the word “locking” does not
occur in it.

## 3. What it means for this solver

AFSI couples a finite-element ($\mathbb{P}_2/\mathbb{P}_1$ Chorin) fluid to
the structure with the $\mathrm{IB}_4$ kernel only: the discrete
divergence-free property of the MAC/CBS construction is not available here,
and the interpolated marker velocity is not divergence-free. In this pipeline
$\kappa_{\mathrm{stab}}$ is therefore **not** a redundant stabiliser — it is
the actual mechanism that resists volume change. It enters `materials.py` as
the Lamé $\lambda$ of the compressible neo-Hookean (`standard` form) or as
the $\kappa$ of $U(J)$ (`flory` form, which reproduces the reference's
stabilised law). Everything measured below concerns that single coefficient,
scaled by the environment variable `KAPPA_MULT`.

## 4. Measured behaviour: a two-sided window

**The soft side (volume leak).** With the raw paper constant the leak is
visible everywhere: demo_442 loses $1.3\times10^{-2}$ of its enclosed area in
one second; demo_443 settles at $-4.80\,\mathrm{cm}$ against the reference's
$-4.03$–$-4.09\,\mathrm{cm}$ with $J$ down to $0.53$; demo_441 reports
$J \in [0.821, 1.121]$ where the reference's stabilised map stays within
$[0.966, 1.010]$.

**The calibrated middle.** Scaling the bulk on demo_443 ($M = 8$, $N = 32$,
$t = 25\,\mathrm{s}$):

<p class="tcaption">Table 1. The bulk-modulus window (demo_443; reference plateau $-4.03$…$-4.09\,\mathrm{cm}$, $J$ range $[0.892, 1.021]$).</p>

| bulk | $\Delta Y$ (cm) | $J$ range | outcome |
| --- | --- | --- | --- |
| $K$ (raw, 374.2) | $-4.80$ | $[0.68, 1.09]$ | soft; volume looser than the reference |
| $10K$ | $-4.09$ | $[0.88, 1.03]$ | matches the reference in both metrics |
| $100K$ | $-3.87$ | $[0.96, 1.01]$ | last stable rung; volume tighter than the reference |
| $1000K$ | — | inverted | locks (see below) |

The same calibration applied to demo_441 gives $0.745/0.750\,\mathrm{cm}$
($M = 8/16$, mesh-converged) with $J$ pinned to the reference's range
$[0.99, 1.02]$ — but that is $\approx 0.09\,\mathrm{cm}$ *above* the
reference band $0.59$–$0.68\,\mathrm{cm}$, which the raw constant had sat
inside. The calibration therefore reconciles the compression benchmark
completely but not the bending one; the residual is documented in demo_441
§4.3 and attributed to the different Lagrangian discretisations
($\mathbb{Q}^2$ mesh with a penalty clamp here, $\mathbb{Q}^1$ mesh with a
combined elastic + viscous tether there).

**The stiff side (the lock).** At $\kappa \times 1000$ on the same mesh an
element inverts at the punch corner ($J_{\min} = -0.42$) within the first
two-and-a-half seconds, and the coupled run then **freezes completely**: from
that moment every diagnostic is constant and the fluid velocity is
*identically zero*. The run neither converges nor diverges — it locks.
$\kappa \times 100$ is the last stable rung. The identical locked state
appears at $\kappa \times 10$ as soon as the marker spacing drops to $h$ or
below, and at $M = 16$ at any grid ratio tried; halving $\Delta t$ does not
recover it. The cliff is thus crossed either by raising $\kappa$ or by
refining the markers relative to $h$ — the two directions meet at the
explicit-stability ratio of the stiffest, most compressed solid element in
the feedback loop. This is the practical form of the reference's cited
time-step restriction.

**The failure is silent in displacement-only diagnostics.** In the locked
runs the probe displacement looks perfectly plausible; only $J$ (element
inversion) and $u$ (identically zero) reveal it. Every number on the demo
pages is therefore quoted together with its Jacobian range.

## 5. Is it a unit problem?

No — on four counts. (i) The reference's numbers cross-check in CGS: the
traction gives $\sigma \approx 200\,\mathrm{dyn\,cm^{-2}}$, which with
$G = 80.194$ gives $\Delta Y \approx -4.2\,\mathrm{cm}$; the viscosity
$0.16\,\mathrm{dyn\,s\,cm^{-2}}$ matches the settling times. (ii) A global
unit factor (Pa $\leftrightarrow$ dyn/cm² is exactly $10$) would shift every
benchmark the same way, yet the compression case wants the bulk about ten
times harder while the same adjustment pushes Cook's membrane *above* its
band — opposite requirements cannot come from a single slip. (iii) In the
reference's own words $\kappa_S$ and $\nu_S$ are numerical parameters, so the
stated value cannot be unit-tested against their results (their $J$ is pinned
by the coupling, not by $\kappa_S$). (iv) What this solver matches is an
*effective incompressibility*, verified directly through the $J$ range — not
a converted constant.

## 6. Practical guidance for this solver

* Keep the marker spacing at $\gtrsim 2h$ when the bulk is raised
  ($\kappa \times 10$ is stable to $t = 100\,\mathrm{s}$ at $M = 8$, $N = 32$;
  markers at $h$ or below lock).
* Use `KAPPA_MULT=10` when the goal is to match the reference's effective
  incompressibility; the raw constant is the soft end, $\times100$ the last
  stable hard end.
* Always report the Jacobian range **and** the fluid velocity norm next to
  the displacement — the lock is silent otherwise.
* Expect the window to be case-dependent: the compression benchmark matches
  at $\times 10$; the Cook's membrane keeps a residual at matched volume
  behaviour.

## References

{{< references >}}
