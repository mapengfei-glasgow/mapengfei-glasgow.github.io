---
title: "336: Disc in a Lid-Driven Cavity"
description: "A disc carried around the primary vortex of a lid-driven cavity, solved with three immersed-boundary couplings."
date: 2026-09-12
weight: 1
academic: true
demo_id: demo_336
category: Application
dimension: 2D
solid_model: "elastic disc (IB-FE, P = μ_s(F − F⁻ᵀ)); rigid disc; inertial neo-Hookean disc with Kelvin–Voigt damping"
coupling: "immersed-boundary finite elements + two multi-direct-forcing variants"
reference: "solid-free reference cavity (this page)"
status: Partial
---

## 1. Introduction

A closed square cavity with a sliding lid carries a circular disc around its
primary vortex. The same case is implemented with three different couplings:

| Variant | Solid |
|---|---|
| Immersed-boundary finite elements | elastic disc, $\mathbf{P} = \mu_s(\mathbf{F} - \mathbf{F}^{-\mathrm{T}})$ |
| Rigid multi-direct forcing | rigid disc, iterated direct forcing, no constitutive law |
| Elastic multi-direct forcing | inertial disc, neo-Hookean + Kelvin–Voigt, added-mass term |

The pair of direct-forcing variants addresses the back-effect question: a light,
soft body carried by the flow produces almost no reaction force on the fluid, and
the case quantifies that against a solid-free reference.

## 2. Problem description

### 2.1 Geometry

The cavity is the unit square with a sliding lid; the disc of radius $r = 0.2$
($D = 0.4$) starts at $(0.6, 0.5)$.

{{< figure src="/afsi/demo336-setup.png" title="Figure 1. The case: a square cavity with a sliding lid and a disc at $(0.6, 0.5)$." >}}

### 2.2 Governing equations

{{< color "red" >}}TODO: governing equations — incompressible Navier–Stokes, the
penalty (IB-FE) and direct-forcing formulations, and the solid constitution
$\mathbf P = \mu_s(\mathbf F - \mathbf F^{-\mathrm T})$ / neo-Hookean + Kelvin–Voigt
(see the symbol table page).{{< /color >}}

### 2.3 Boundary and initial conditions

The lid slides at $U_{lid} = 1.0$ and the cavity walls are no-slip. The initial
condition is quiescent: the re-runs behind the figures below were not restarted
from an interpolated state; $t = 0$ is at rest.

### 2.4 Physical parameters

<p class="tcaption">Table 1. Common configuration.</p>

| Quantity | Symbol / code name | Value |
|---|---|---|
| Cavity | `Lx`, `Ly` | $1.0 \times 1.0$ |
| Lid velocity | `U_lid` | $1.0$ |
| Density / viscosity | `rho`, `mu` | $1.0$ / $0.01$, i.e. $\mathrm{Re} = 100$ |
| Disc centre | `cx`, `cy` | $(0.6, 0.5)$ |
| Disc radius / diameter | `r`, `D` | $0.2$ / $0.4$ |
| Solid shear modulus (IB-FE) | `mu_s` | $0.1$ ($\lambda_s = 10$ hard-coded) |

{{< color "red" >}}TODO: dimensionless numbers beyond $\mathrm{Re}$ and the solid's dimensionless groups, if the case is to be reported in dimensionless form.{{< /color >}}

## 3. Numerical setup

The direct-forcing variants use an AB2 fractional step ($1.5/0.5$ convection,
$n_{iter} = 10$ forcing iterations, a pressure Poisson solve followed by the
velocity projection) with velocity / force / pressure spaces
$\mathrm{P2}$ / $\mathrm{P2}$ / $\mathrm{P1}$. The elastic variant adds an implicit
added-mass term $\rho_f V_{node}$ to a lumped solid mass $M = \rho_s \pi r^2$ (HRZ
lumping; row-sum lumping gives near-zero or negative vertex masses). The IB-FE
variant holds the disc with a penalty $\beta = 1 \times 10^{8}$. The solver
requires the cavity to start at the origin (see §5).

<p class="tcaption">Table 2. What differs between the three runs.</p>

| Variant | Fluid grid | $\Delta t$ | $T$ | Steps | Solid parameters |
|---|---|---|---|---|---|
| IB-FE elastic disc | $64 \times 64$ | $1/200$ | $10.0$ | $2000$ | `mu_s` $= 0.1$ |
| Rigid direct forcing | $128 \times 128$ | $0.0025$ | $10.0$ | $4000$ | rigid, displacement field imposed |
| Elastic direct forcing | $128 \times 128$ | $0.0025$ | $1.0$ | $400$ | `mu_s` $= 0.05$, $\lambda_s = 0.5$, `mu_s_visc` $= 0.01$, `rho_s` $= 1.0$ |

## 4. Results

### 4.1 Quantities of interest

The quantities of interest are the disc-centre trajectory (ranges, net
displacement, path length, swept angle), the solid health measures
($\max\lvert u_s\rvert$, $\min\det\mathbf F$, volume ratio), the fluid energy norm
$u_{L2}$ — which does not depend on the force integralisation and is therefore the
cleanest cross-run comparison — and the direct-forcing force coefficients $C_x$,
$C_y$, $C_m$, which are order-of-magnitude references only (see §5).

### 4.2 Comparison with the solid-free reference

{{< figure src="/afsi/demo336-results.png" title="Figure 2. Short run at $48^2$: the centroid path (barely moved at $t = 0.5$ s) and the drag coefficient; panel (c) is the back-effect comparison." >}}

{{< figure src="/afsi/demo336-ib-vs-df.png" title="Figure 3. Archived comparison: centroid path, centroid $y(t)$ and top-edge $y(t)$ for the IB run and the direct-forcing runs at two resolutions." >}}

<p class="tcaption">Table 3. Archived comparisons.</p>

| Quantity | Value |
|---|---|
| Back-effect, no solid / soft ($\rho_s = 1$) / heavy ($\rho_s = 50$) | $u_{L2} = 0.0612$ / $0.0588$ / $0.0484$ at $t = 1.5$ s |
| 10 s run, $64\times64$, $\mu_s = 0.2$ | full clockwise orbit, period $\approx 5$ s, top edge $0.993$, $\min \det\mathbf{F} > 0.7$ |
| Solid viscosity comparison ($\rho_s = 1$, $\mu_s = 0.2$) | DF@128 without viscosity diverges at $t = 4.89$ s; with `mu_s_visc` $= 0.01$ top edge $0.993$ at $5$ s; IB@64 reaches only $0.980$ |
| Rigid disc, $128\times128$, $t = 1.25$ s | centroid $(0.6,0.5) \to (0.48,0.485)$; $C_x \approx -0.78$ fixed vs $\approx -0.03$ free |

### 4.3 Convergence and grid sensitivity

{{< figure src="/afsi/demo336-study-grid.png" title="Figure 4. The baseline elastic case at $32^2$, $64^2$ and $128^2$. The 64 and 128 curves are indistinguishable; the 32 grid agrees until about $t = 6$ s and then drifts." >}}

<p class="tcaption">Table 4. The baseline elastic case on three grids.</p>

| Grid | $x$ range | $y$ range | centroid at $t=5$ | $\max\lvert u_s\rvert$ | $\min\det\mathbf F$ | swept angle |
|---|---|---|---|---|---|---|
| $32^2$ | $[0.271,0.719]$ | $[0.489,0.871]$ | $(0.572, 0.860)$ | $0.817$ | $0.704$ | $-228^\circ$ |
| $64^2$ | $[0.269,0.723]$ | $[0.489,0.873]$ | $(0.572, 0.862)$ | $0.820$ | $0.704$ | $-587^\circ$ |
| $128^2$ | $[0.269,0.724]$ | $[0.489,0.873]$ | $(0.572, 0.862)$ | $0.821$ | $0.703$ | $-587^\circ$ |

$64^2$ and $128^2$ agree to every digit reported; $32^2$ matches the centroid to
$0.002$ and the extreme displacements to $0.4\,\%$ but **does not reproduce the
orbit**: it covers one loop instead of two. The field quantities are therefore
grid-converged at $64^2$, while the long-time orbital phase is not resolved
there — that is the practical resolution requirement for this case.

### 4.4 Flow and deformation fields

The case was studied with a nine-run matrix — six physical configurations and
three grid resolutions, all at $T = 10\,\mathrm{s}$,
$\Delta t = 0.0025\,\mathrm{s}$ ($4000$ steps), sharing the same cavity and disc
and differing in the solid model and its parameters:

<p class="tcaption">Table 5. The run matrix. "Elastic" is the inertial neo-Hookean disc of §1 (with Kelvin–Voigt damping); "rigid" is the iterated direct-forcing disc of §1.</p>

| Run | Solid model | Parameters | Steps done |
|---|---|---|---|
| `no_solid` | none | pure cavity, reference | $4000$ |
| `elastic_base` | elastic | $\mu_s = 0.2$, $\rho_s = 1$, $\mu_s^{visc} = 0.01$ | $4000$ |
| `elastic_soft` | elastic | $\mu_s = 0.05$ (softer) | $4000$ |
| `elastic_heavy` | elastic | $\rho_s = 20$ (heavier) | $2237$ † |
| `elastic_heavy_clamp` | elastic + centroid clamp | $\rho_s = 20$ | $4000$ |
| `rigid_free` | rigid | free rigid body | $4000$ |
| `rigid_fixed` | rigid | held fixed | $4000$ |
| `elastic_32` / `elastic_128` | elastic | as `elastic_base`, at $32^2$ / $128^2$ | $4000$ |

† the heavy disc reached the wall at $t = 5.595\,\mathrm{s}$, where the run
stopped. The clamped variant exists to get a full ten seconds out of that
parameter set; its clamp is a modelling artefact, not physics.

**Snapshots at $t = 0, 2, 4, 6, 8, 10$ s.** Both direct-forcing variants were run
for the full $T = 10$ s on the $64^2$ grid, where the disc trajectory is
grid-converged (§4.3).

{{< figure src="/afsi/demo336-flow-pressure-0-10s.png" title="Figure 5. Rigid multi-direct forcing, 64x64. Top row: velocity magnitude with streamlines; bottom row: pressure with the time-averaged level removed (symlog colour scale, since the lid makes the corner values about ten times the interior signal). The disc interior is masked out; its outline is the deformed disc geometry, reconstructed as reference circle plus displacement." >}}

At $t = 0$ the fluid is at rest and the pressure is still a smooth lid-corner field. By
$t = 2$ s the primary vortex is established and the disc — which started at $(0.6, 0.5)$ —
has been carried left to $(0.395, 0.514)$. The disc then climbs the left side
($t = 4$ s: $(0.276, 0.750)$), crosses under the lid ($t = 6$ s: $(0.568, 0.760)$, the
closest approach, still $\approx 4$ cm clear of the lid), descends the right side
($t = 8$ s: $(0.541, 0.518)$) and is swept back up in the return flow
($t = 10$ s: $(0.326, 0.621)$). The full loop, together with the direct-forcing force
coefficients and the disc's translational and angular speed, is in Figure 6.

{{< figure src="/afsi/demo336-history.png" title="Figure 6. Rigid run: disc-centre trajectory (dotted circle = initial position), the direct-forcing force coefficients $C_x$, $C_y$, $C_m$, and the rigid-body speeds. The coefficients are order-of-magnitude references only — the marker volume sums to $\Delta s \cdot h \propto h$, so $\int f_{\mathrm{IB}}\,\mathrm{d}V$ does not converge under refinement (see §5)." >}}

{{< figure src="/afsi/demo336-solid-disc-0-10s.png" title="Figure 7. Rigid run: solid displacement $u_s$ on the deformed grid, true scale, initial disc dashed. The disc travels further than its own radius (max $\lvert u_s\rvert = 0.51$ against $r = 0.2$), so the field is contoured on the deformed mesh — at the reference positions only the small overlap with the current pose would show. The displacement is a rigid-body translation plus rotation about the initial centre, so the disc stays a circle and its radius is invariant (mean radius 0.1244 at every plotted time). The centroid reconstructed this way agrees with the traced disc centre to 5e-7." >}}

For contrast, the elastic variant of the same case — an inertial neo-Hookean disc with
Kelvin–Voigt damping ($\mu_s = 0.2$, $\rho_s = 1$, `mu_s_visc` $= 0.01$) — deforms
strongly instead of translating rigidly:

{{< figure src="/afsi/demo336-elastic-solid-0-10s.png" title="Figure 8. Elastic run, 64x64, 4000 steps, $T = 10$ s. Top: $\lvert u_s\rvert$ on the reference mesh. Bottom: the deformed mesh itself, which shows the stretch and shear the soft disc accumulates in the cavity vortex. The dashed circle is the initial disc. $\lvert u_s\rvert$ peaks at 0.71 in the P1 output field (0.82 on the P2 solid space), and $\min \det \mathbf{F}$ stays above 0.70, so no element inverts." >}}

Both runs completed 4000 steps at $\Delta t = 0.0025$ s with no NaN and no wall
contact; the elastic run's solid stays well clear of inverting
($\min \det \mathbf{F} \ge 0.70$ over the whole run).

**Trajectories.** The paths are all closed loops in the upper-left quadrant of the
cavity, and they all run clockwise — the direction of the primary vortex:

{{< figure src="/afsi/demo336-study-trajectories.png" title="Figure 9. Disc-centre paths for all six configurations (left, coloured by time) and the centroid coordinates against time (right; solid = $x$, dotted = $y$). Every run loops through the same upper-left region; the elastic discs reach further into the corner and start their second loop by $t = 8$ s, while the fixed disc does not move at all." >}}

<p class="tcaption">Table 6. Trajectory summary for the six configurations.</p>

| Run | $x$ range | $y$ range | net displacement | path length | swept angle |
|---|---|---|---|---|---|
| `elastic_base` | $[0.269, 0.723]$ | $[0.489, 0.873]$ | $0.393$ | $1.777$ | $-587^\circ$ |
| `elastic_soft` | $[0.284, 0.723]$ | $[0.490, 0.880]$ | $0.362$ | $1.629$ | — |
| `elastic_heavy` | $[0.173, 0.600]$ | $[0.478, 0.791]$ | $0.508$ | $0.618$ | $-262^\circ$ |
| `elastic_heavy_clamp` | $[0.231, 0.600]$ | $[0.478, 0.769]$ | $0.456$ | $0.614$ | — |
| `rigid_free` | $[0.273, 0.663]$ | $[0.484, 0.769]$ | $0.300$ | $1.399$ | $-338^\circ$ |
| `rigid_fixed` | $0.600$ | $0.500$ | $0$ | $0$ | $0^\circ$ |

{{< figure src="/afsi/demo336-study-orbit.png" title="Figure 10. Orbit progress. Left: the angle swept about the cavity centre; a full loop is $360^\circ$. The elastic disc manages **two** loops in ten seconds (a period near $5$ s), while the rigid disc covers one and the heavy disc only three quarters. Right: distance from the cavity centre, which shows that both elastic and rigid discs pass close to the centre twice per loop." >}}

Two things stand out. First, the **elastic disc orbits faster than the rigid one**:
$587^\circ$ against $338^\circ$ over the same ten seconds. The elastic disc is
carried by the flow and lags it less, while the rigid disc — whose direct forcing
holds its surface at the local fluid velocity — slips against the vortex. Second,
the **clamp changes the trajectory qualitatively**: the clamped heavy disc stays in
a smaller loop near the start point, whereas the unclamped one escapes toward the
left wall. Any conclusion drawn from the clamped run is therefore about the clamp,
not about a heavy disc.

**Deformation and solid-mesh health.** The displacement magnitudes are the
headline: the disc starts with a radius of $0.2$ and its nodes move up to $0.82$ —
**four radii**. This is not a slightly wobbling disc; the baseline run is a
strongly deforming soft body being stretched around the vortex, and the RMS
displacement ($0.40$) says the deformation is distributed over the body rather
than localised.

{{< figure src="/afsi/demo336-study-deformation.png" title="Figure 11. Solid mesh health (left), area change (middle) and RMS deformation (right) for the elastic runs. The dashed line at $\det\mathbf F = 1$ is the undeformed state and the shaded band is where elements would invert; every run stays clear of it, but the heavy disc gets to $0.603$ and the baseline to $0.704$." >}}

<p class="tcaption">Table 7. Deformation summary for the elastic runs.</p>

| Run | $\max\lvert u_s\rvert$ | $\min\det\mathbf F$ | $V/V_0$ | $(\text{effective radius})/r$ |
|---|---|---|---|---|
| `elastic_base` | $0.820$ | $0.704$ | $1.107$ | $1.052$ |
| `elastic_soft` | $0.824$ | $0.776$ | $1.049$ | $1.024$ |
| `elastic_heavy` | $0.590$ (at $t=5.6$) | $0.603$ | $1.039$ | $1.019$ |
| `elastic_heavy_clamp` | $0.881$ | $0.655$ | $1.076$ | $1.037$ |

The area change deserves a note, because it is easy to misread. The configuration
sets $\lambda_s = 0.5$, i.e. a very compressible neo-Hookean solid, so $J$ may
grow. The baseline run's area increases by $10.7\,\%$ over the ten seconds — a
genuine feature of the chosen material parameters rather than a conservation
failure; a nearly incompressible solid would need a much larger $\lambda_s$, and
then P2 elements lock.

$\min\det\mathbf F$ decides whether the run survives at all: the explicit coupling
inverts an element once it crosses zero. All four elastic runs end above $0.6$,
and the baseline's minimum, $0.7038$, is reached late in the run.

**Energy and forces.** The fluid energy norm is the cleanest way to compare the
runs, because it does not depend on the force integralisation:

{{< figure src="/afsi/demo336-study-histories.png" title="Figure 12. Top row: the $x$ and $y$ components of the immersed-boundary force integral. Bottom left: the fluid energy norm $u_{L2}$. Bottom right: the maximum solid displacement, with the disc diameter marked. The force spikes are not physics — see the caveat in §5 about the marker-volume sum being $\propto h$." >}}

<p class="tcaption">Table 8. Energy budget at $t = 10$ s, relative to the solid-free run.</p>

| Run | $u_{L2}$ at $t = 10\,\mathrm{s}$ | relative to the no-solid run | $\max u_{L2}$ |
|---|---|---|---|
| `no_solid` | $0.0672$ | — | $0.0672$ |
| `elastic_base` | $0.0623$ | $-7.3\,\%$ | $0.0851$ |
| `elastic_soft` | $0.0593$ | $-11.8\,\%$ | — |
| `elastic_heavy_clamp` | $0.0518$ | $-23.0\,\%$ | $0.0548$ |
| `rigid_free` | $0.0529$ | $-21.2\,\%$ | $0.0900$ |

The elastic discs take only a few per cent of energy out of the cavity at the
baseline parameters, and the softer one takes more than the baseline — the
back-effect conclusion, now with numbers: a light, soft body carried by the flow
pushes back very little, and making it softer still does not make it a better
obstacle. What does change the budget is mass: the clamped heavy disc removes
$23\,\%$, as much as the rigid one removes through its no-slip constraint. Note
also that the *peak* $u_{L2}$ is high early in every solid run ($0.085$–$0.090$
against a monotone $0.067$ for the empty cavity) — the disc perturbs the flow
strongly while it is being accelerated, even when the late-time energy is lower.

**Instantaneous fields.** {{< figure src="/afsi/demo336-study-fields.png" title="Figure 13. The rigid-disc run at $t = 0, 2, 4, 6, 8, 10$ s: velocity magnitude (top), vorticity (middle) and pressure (bottom), with the disc outline drawn from its own displacement field. The cavity vortex forms by $t=2$ s, the disc is squeezed through the top-left corner between $t = 4$ and $6$ s where the velocity and pressure gradients are largest, and the flow is close to periodic afterwards." >}}

The instantaneous fields show why the trajectory is what it is. At $t = 4$ s the
disc sits in the upper-left corner where the return flow meets the lid-driven one;
that is exactly where the deformation peaks and where $\det\mathbf F$ falls
fastest. After $t = 6$ s the disc rides the vortex core and the field returns to a
state close to its $t = 2$ s shape, consistent with the nearly periodic orbit.

The re-runs behind Figures 5–8 add:

<p class="tcaption">Table 9. Re-run numbers.</p>

| Quantity | Value |
|---|---|
| Rigid disc, $T = 10$ s | centroid path $(0.600,0.500) \to (0.395,0.514) \to (0.276,0.750) \to (0.568,0.760) \to (0.541,0.518) \to (0.326,0.621)$; $\lvert\mathbf{V}_c\rvert_{\max} = 0.251$, $\lvert\omega\rvert_{\max} = 0.295$ rad/s, total rotation $1.055$ rad |
| Rigid disc, $T = 10$ s | $\max\lvert u_s\rvert = 0.509$ over the run; trajectories stay inside $x \in [0.273, 0.663]$, $y \in [0.484, 0.769]$; no wall contact |
| Rigid run fluid | $u_{L2}$ grows $0 \to 0.0529$; $\lvert C_x\rvert \le 1.07$, $\lvert C_y\rvert \le 2.04$ |
| Elastic disc, $T = 10$ s | $\max\lvert u_s\rvert = 0.820$ on the P2 solid space ($0.71$ in the P1 output field at the plotted times); peak at $t \approx 4$ s then partial rebound ($0.71 \to 0.61 \to 0.31 \to 0.44$); $\min \det \mathbf{F} = 0.7038 \ge 0.70$; volume $0.12566 \to 0.1274$; final centroid $(0.282, 0.732)$ |
| Elastic run fluid | $u_{L2} \to 0.0623$, i.e. above the rigid run's $0.0529$ and above the 1.5 s no-solid reference $0.0612$ |

## 5. Discussion and limitations

* Both direct-forcing variants are single-process only, and their drag/lift
  integrals are order-of-magnitude references only: the marker volumes sum to
  $\Delta s \cdot h \propto h$, so $\int \mathbf{f}_{\mathrm{IB}}\,\mathrm{d}V$
  does not converge under refinement.
* The solver requires the cavity to start at the origin: the IBM kernel computes
  its base node as $X/h$ without subtracting a domain offset.
* The clamped heavy-disc run is a modelling artefact (§4.4): conclusions from it
  are about the clamp, not about a heavy disc.

{{< color "red" >}}TODO: what the case shows, in one paragraph — the open
question of why the elastic disc orbits faster, and any comparison against a
published reference, if one exists.{{< /color >}}

## References

{{< color "red" >}}TODO: references — none cited yet; add a lid-driven-cavity
reference (e.g. Ghia et al.) if the flow field is compared against one.{{< /color >}}
