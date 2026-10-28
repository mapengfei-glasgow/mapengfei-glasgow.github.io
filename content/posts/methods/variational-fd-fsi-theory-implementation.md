---
title: "Variational FD–solid coupling: theory and implementation"
description: "How a P1 tetrahedral solid exchanges velocity and force with a staggered finite-difference fluid without a delta kernel: operators, adjoint force, quadrature, volume constraints, time stepping, and the CPU/CUDA code that implements them."
date: 2026-10-28T00:00:00+08:00
academic: true
ShowToc: true
TocOpen: false
tags: ["FSI", "GPU", "CUDA", "finite elements", "immersed methods"]
url: /posts/variational-fd-fsi-theory-implementation/
area: "research"
readingRoute: "gpu-solver"
areas: ["Computational Fluid Dynamics"]
noteType: "Method"
---

This page explains the **algorithms**: what is computed, why it has the
form it has, and how the code implements it. The measured results
(Cook, torsion and LV benchmarks, refinement and stability studies) are in
the companion page,
[Variational FD–solid coupling: coarse meshes, quadrature and volume conservation](/posts/variational-fd-fsi-quadrature-study/).

**In one sentence:** the solid velocity is the $L^2$ projection of the
fluid velocity onto the solid's P1 finite-element space. The force on the
fluid is the exact discrete adjoint (transpose) of that projection, so the
work done on the fluid always equals the work done by the solid, to roundoff.

The formulation follows the variational immersed finite-element framework of
[Roy, Heltai and Costanzo](https://arxiv.org/abs/1306.0936v3). Here it is
adapted to a **staggered (MAC) finite-difference fluid** on the GPU, rather
than a finite-element fluid. The adaptation, its CUDA kernels and the
experiments are this study's work. The underlying ideas are not new: dense
interaction quadrature on coarse solids
([Griffith–Luo](https://arxiv.org/abs/1612.05916),
[IFED](https://arxiv.org/abs/2105.14536)) and adjoint
interpolation/spreading
([divergence-free IB](https://arxiv.org/abs/1701.07169)) are established prior work.

## 1. The problem and the two meshes

**The fluid** fills a cube $\Omega$. It is discretised on a uniform MAC grid
with spacing $h$. The velocity component $u^c$, for $c\in\{x,y,z\}$, lives
on the faces normal to direction $c$. The pressure lives at cell centres.
The existing GPU solver takes one projection step at a time: advection,
viscous update, then a multigrid pressure Poisson solve. It accepts an extra
body-force field on the faces.

**The solid** occupies the reference domain $B$. It is meshed with linear
(P1) tetrahedra. The unknowns are the current nodal positions
$\mathbf{x}_a$ and nodal velocities $\mathbf{w}_a=\dot{\mathbf{x}}_a$. Its
deformation map is

$$
\chi_h(X,t)=\sum_a N_a(X)\,\mathbf{x}_a(t),\qquad F=\nabla_X\chi_h ,
$$

where $N_a$ is the P1 hat function of node $a$. Inside one tetrahedron,
$F$ is constant.

**The coupling must answer two questions:**

1. **Kinematics:** how fast does each solid node move, given the fluid velocity?
2. **Dynamics:** what body force does the solid's stress exert on the fluid?

Classical immersed-boundary methods answer both with a regularised delta
kernel $\delta_h$, evaluated at nodes or markers. The variational approach
instead derives both answers from one weak statement on the solid.

## 2. Kinematics: velocity as an $L^2$ projection

The continuous no-slip condition is $\partial_t\chi(X,t)=u(\chi(X,t),t)$ for
every material point $X\in B$. To impose it weakly in the P1 space, test it
against every nodal hat function $N_a$:

$$
\int_B N_a\,\mathbf{w}_h\,dX=\int_B N_a\,u_h\big(\chi_h(X)\big)\,dX
\quad\text{for all nodes } a .
$$

Here $\mathbf{w}_h=\sum_b N_b\mathbf{w}_b$, and $u_h$ is a continuous
reconstruction of the MAC velocity (section 3). Collecting the terms gives
the linear system

$$
M\,\mathbf{w}=C\,u .
$$

**The mass matrix** has entries $M_{ab}=\int_B N_aN_b\,dX$, applied
separately to each component. It is assembled exactly. For a tetrahedron of
reference volume $V$, the local matrix is $\tfrac{V}{20}(1+\delta_{ab})$.
It uses the **reference** configuration, so it never changes and is
factorised once.

**The coupling matrix** has entries

$$
C_{(a,c),\,i}=\int_B N_a(X)\,\varphi^c_i\big(\chi_h(X)\big)\,dX
\approx\sum_q w_q\,N_a(X_q)\,\varphi^c_i(\mathbf{x}_q),
\qquad \mathbf{x}_q=\sum_a N_a(X_q)\mathbf{x}_a .
$$

Here $\varphi^c_i$ is the reconstruction weight of MAC unknown $i$ of
component $c$. The integral is over the reference solid, but the fluid basis
is evaluated at the **current** quadrature-point positions. $C$ therefore
changes whenever the solid moves.

The solid velocity is then

$$
\mathbf{w}=M^{-1}C\,u .
$$

Note that this is a projection, not point sampling: every nodal velocity is a
weighted average over the support of its hat function. If the fluid velocity
is affine (for example, a rigid motion), the transfer reproduces it exactly.
Trilinear reconstruction is exact for affine fields, and the projection of a
P1 field onto P1 is the field itself.

## 3. Reconstructing a continuous fluid velocity

### Trilinear MAC reconstruction (default)

Each velocity component is interpolated trilinearly on its own staggered
grid. The solver stores fields with ghost layers. Face $u^x_{ijk}$ sits at
$((i-1)h,\,(j-\tfrac12)h,\,(k-\tfrac12)h)$, and similarly for the other
components. For a point $\mathbf{x}$, the code forms, for component $c$ and
each direction $d$,

$$
r_d=\frac{x_d}{h}+\begin{cases}1,&d=c\\ \tfrac12,&d\ne c\end{cases},\qquad
\text{base}_d=\lfloor r_d\rfloor,\quad t_d=r_d-\text{base}_d .
$$

It then uses the 8 neighbouring unknowns with tensor-product weights
$(1-t_0\text{ or }t_0)(1-t_1\text{ or }t_1)(1-t_2\text{ or }t_2)$.
Each quadrature point therefore touches $3\times8=24$ fluid unknowns.

These weights are algebraically the tensor "tent" kernel of width $h$. The
method is delta-free in its derivation, not in its arithmetic.

**Weakness:** the MAC field is discretely divergence-free, but its
componentwise trilinear reconstruction is not pointwise divergence-free.
In an audited active-LV state, MAC divergence RMS was $3\times10^{-10}\,\mathrm{s^{-1}}$.
The trilinear reconstruction at the solid quadrature points gave $4.19\,\mathrm{s^{-1}}$.

### RT0 reconstruction (option `--reconstruction rt0`)

Component $c$ is interpolated linearly in direction $c$ only, between the two
faces of the containing cell, and held constant across the cell in the other
directions. This is the lowest-order Cartesian Raviart–Thomas field. Its
divergence inside every cell equals the MAC divergence exactly. In exchange,
it no longer reproduces affine fields or rigid rotations, and it uses only
6 unknowns per point.

**Finding:** RT0 did not fix the solid volume loss. The P1 projection
$M^{-1}C$ introduces divergence on its own, even from an exactly
divergence-free input. A manufactured test that projects an analytic curl
field onto the LV mesh shows this, with no fluid solver involved.

## 4. Dynamics: the force is the adjoint of the velocity map

Let $E(\mathbf{x})$ be the solid's total potential: elastic strain energy,
plus the potentials of pressure loads, active stress and support penalties.
Let $g=\partial E/\partial\mathbf{x}$ be its nodal gradient (the negative
nodal force). The rate at which the solid's energy changes is

$$
\dot E=g^{\mathsf T}\mathbf{w}=g^{\mathsf T}M^{-1}C\,u .
$$

Let $f_i$ be the body force per unit volume on fluid unknown $i$. It does
power $h^3u^{\mathsf T}f$ on the fluid. Energy exchange requires
$h^3u^{\mathsf T}f=-\dot E$ for **every** fluid velocity $u$. Because $M$ is
symmetric, this fixes the force uniquely:

$$
\boxed{\;\lambda=M^{-1}g,\qquad f=-\frac{1}{h^3}\,C^{\mathsf T}\lambda,\qquad
\text{acceleration}=f/\rho_f\;}
$$

and the **discrete power identity**

$$
h^3u^{\mathsf T}f+g^{\mathsf T}\mathbf{w}
=-u^{\mathsf T}C^{\mathsf T}M^{-1}g+g^{\mathsf T}M^{-1}C\,u=0
$$

holds for any state, any mesh and any quadrature rule. It holds because both
maps use the same quadrature points and the same stencils. It is an
algebraic identity. It is **not** a guarantee of total energy stability,
which also depends on the time integrator.

The nodal vector $\lambda$ has a direct meaning: it is the $L^2$ representative
of the solid force density, $\lambda_h=\sum_bN_b\lambda_b$. The fluid force is
this density, spread with the same weights $w_q\varphi_i^c$ that were used to
gather velocity.

**Resultant force.** Two properties hold: trilinear weights form a partition
of unity ($\sum_i\varphi^c_i=1$), and $\sum_aN_a=1$. Together they give

$$
\sum_i h^3 f^c_i=-\int_B\lambda_{h,c}\,dX=-\sum_a g_{a,c} .
$$

For purely internal forces, translation invariance makes $\sum_a g_a=0$, so
the fluid receives zero net force. This needs the stencil to be untruncated,
which is why boundary-touching stencils are rejected (section 8).

**Elastic gradient.** The P1 constitutive force is unchanged from the host
driver: one-point integration of the first Piola–Kirchhoff stress $P$ per
tetrahedron, $g_a\mathrel{+}=V\,P\,\nabla_XN_a$. The materials are modified
Mooney–Rivlin, neo-Hookean, and Guccione with active stress, with a
volumetric stabilisation term. The original one-element prototype used
$\Psi=\tfrac{\mu}{2}(F\!:\!F-3-2\log J)$, so $P=\mu(F-F^{-\mathsf T})$.

## 5. Quadrature inside each tetrahedron

The interaction integrals are evaluated with tensor Gauss–Legendre rules
mapped onto the tetrahedron by the Duffy (collapsed-cube) transform. A
reference point $(r,s,t)\in[0,1]^3$ maps to barycentric coordinates

$$
N_1=r,\quad N_2=(1-r)s,\quad N_3=(1-r)(1-s)t,\quad N_0=1-N_1-N_2-N_3 ,
$$

with weight $6V\cdot\tfrac{w_iw_jw_k}{8}\cdot(1-r)^2(1-s)$. The factor $6V$
converts from the unit tetrahedron (volume $\tfrac16$). The $\tfrac18$ maps
$[-1,1]^3$ to $[0,1]^3$. The last factor is the Duffy Jacobian. Gauss order
3 gives 27 points per tetrahedron, and order 5 gives 125
(`--quad 3|5`).

**Why the rule matters:** inside one fluid interpolation cell, the integrand
$N_a\,\varphi_i^c(\chi_h)$ is a polynomial. But $\varphi_i^c$ has kinks on
every grid plane, and a coarse tetrahedron can span several fluid cells.
Gauss rules assume smoothness across those kinks, so their error decays
slowly. Measured on actual trilinear MAC fields (Cook n2/n4, N16/N32),
27 points give 0.04–0.26 % projection error, and 125 points give
0.015–0.08 %. Both are far above the error for smooth analytic fields.

**A separate limit:** more points cannot represent motion that the P1 space
cannot hold. For a 3 cm wavelength on the 18-node mesh, 125 points cut the
quadrature error to 0.21 %, but the best possible P1 projection is still
77 % wrong. Quadrature and structural resolution are separate errors.

Two refinements were tested as research pilots. Neither is in the
production path:

- **Uniform composite subdivision.** Eight-way splitting gives 216 to
  110,592 points per tetrahedron. It is accurate, but level 2 costs
  13.8 times the points of the 125-point rule for only 2.3–3.8 times less
  error.
- **Field-independent adaptive bisection.** Compare q3 and q5, then bisect
  the longest edge. The selector depends only on geometry, so its
  transpose is still the matching force map. It reduced local stencil
  error but had no consistent cost advantage. The planned next step is
  integration aligned with MAC grid planes.

## 6. Volume constraints with the adjoint preserved

The P1 projection does not preserve solid volume. In the active LV, the
unconstrained transfer lost 7.7 % of the wall volume by $t=0.1$ s, with only
10 % of the load applied. The fix adds constraints to the projection itself,
not to the result after the fact.

Let $B=\partial V/\partial\mathbf{x}$ hold the derivatives of the current
volume, either of the whole solid (one row) or of each fixed material region
(several rows). Choose the solid velocity closest to the unconstrained
projection, in the $M$-norm, whose instantaneous volume rate is zero:

$$
\min_{\mathbf{w}}\ \tfrac12\big\|\mathbf{w}-M^{-1}Cu\big\|_M^2
\quad\text{subject to}\quad B\mathbf{w}=0 .
$$

The Karush–Kuhn–Tucker conditions give $\mathbf{w}=A\,C\,u$ with

$$
A=M^{-1}-Z\,(BZ)^{-1}Z^{\mathsf T},\qquad Z=M^{-1}B^{\mathsf T} .
$$

Two properties make this the right operator:

- **$BA=Z^{\mathsf T}-Z^{\mathsf T}=0$.** Every transferred velocity has
  zero instantaneous volume rate.
- **$A$ is symmetric.** Replacing $M^{-1}$ by $A$ in **both** maps
  ($\mathbf{w}=ACu$ and $f=-C^{\mathsf T}Ag/h^3$) keeps the power identity
  exact. Clipping the velocity, or rescaling forces independently, would
  break it.

The volume gradient of a tetrahedron with edge vectors
$\mathbf{a},\mathbf{b},\mathbf{c}$ from node 0 is
$\partial V/\partial\mathbf{x}_1=(\mathbf{b}\times\mathbf{c})/6$,
$\partial V/\partial\mathbf{x}_2=(\mathbf{c}\times\mathbf{a})/6$ and
$\partial V/\partial\mathbf{x}_3=(\mathbf{a}\times\mathbf{b})/6$; node 0 gets
the negative sum. With one global constraint, $BZ$ is a scalar. With
regional constraints (`--volume-constraint patches --patch-bins 2|4`,
giving 8 or 52 occupied regions on the LV), $BZ$ is a small symmetric Gram
matrix. It is Cholesky-factorised at every geometry update, and the code
raises an error on a near-singular pivot instead of silently dropping a
constraint.

**What it achieved:** total volume change at $t=0.1$ s fell from
$-7.68\,\%$ to $+0.0008\,\%$. **What it did not achieve:** local
incompressibility. Individual tetrahedra still compress by up to about
19 % (global constraint) or 14 % (52 regions). At full active load,
minimum $J\approx0.39$ while the total volume stays fixed.

## 7. Time stepping

The coupling is explicit and split: one fluid step per solid update, with
no Newton iteration between them. This is the main difference from Roy,
Heltai and Costanzo, who solve the coupled system implicitly. Each step
$t_n\to t_{n+1}$ in the benchmark driver is:

1. **Predict:** $X_{1/2}=X_n+\tfrac{\Delta t}{2}W_n$, where $W_n$ is the
   transferred velocity at $X_n$.
2. **Solid loads:** assemble $g$ at $X_{1/2}$ and $t_{n+1/2}$: P1 stress,
   pressure and traction faces, active stress, and the support penalty
   $k_D$.
3. **Geometry update:** compute the volume gradient and the Gram factor if
   constrained. Build the quadrature-point stencils at $X_{1/2}$.
4. **Spread:** $f=-C^{\mathsf T}Ag/h^3$ goes into the solver's body-force
   arrays.
5. **Fluid step** $u^n\to u^{n+1}$: AB2 upwind convection, viscous update,
   pressure projection.
6. **Correct:** $W^\ast=ACu^{n+1}$ at $X_{1/2}$, then
   $X_{n+1}=X_{1/2}+\tfrac{\Delta t}{2}W^\ast$.
7. **Next velocity:** $W_{n+1}=ACu^{n+1}$, re-assembled at $X_{n+1}$.

**A defect found in step 6:** the two half steps use velocities from
different points. For steady advection $\dot X=\mathsf AX$, the update is
$(I+\tfrac{\Delta t}{2}\mathsf A)^2X_n$. Its quadratic coefficient is
$\tfrac14$ instead of $\tfrac12$, so the update is **first order** (observed
order 0.992). The option `--geometry-update midpoint` also interpolates the
old field $u^n$ at $X_{1/2}$ and sets

$$
X_{n+1}=X_n+\tfrac{\Delta t}{2}\big[\,AC u^n+AC u^{n+1}\,\big]_{X_{1/2}} ,
$$

which is explicit midpoint for a steady field (observed order 1.987). With
the global constraint, it cut the remaining active-LV volume drift about
1,400-fold at $t=0.1$ s. It does not change local $J$. The default remains
`legacy` for reproducibility.

**Stability limit.** Linearise about the reference state, ignoring
viscosity and convection. The solid displacement $d$ then obeys
$\ddot d=-HKd$. Here $K$ is the elastic tangent (including the penalty
supports), and $H=ACPC^{\mathsf T}A/h^3$ is the coupling mobility, with $P$
the exact MAC pressure projection. Explicit midpoint stepping requires
$\Delta t\,\omega_{\max}\le2$ with $\omega^2=\operatorname{eig}(HK)$. For the
eight active-LV refinement cases, this inviscid model classified every
observed outcome at $\Delta t=10^{-4}$ s correctly. For example, the coarse
solid on N64 has a limit of $9.4\times10^{-5}$ s with 27 points (it inverted)
and $1.1\times10^{-4}$ s with 125 points (it completed).

Quadrature also enters through the gain of the transfer. The mass-whitened
squared norm $\|L^{\mathsf T}AC\|^2/h^3$, with $M=LL^{\mathsf T}$, was
1.38 with 27 points and 0.94 with 125 points on that case. An under-resolved
rule can therefore amplify the coupling, while an exact one cannot.

A practical consequence: the driver sets $k_D=k_{d,\text{scale}}\,h/\Delta t^2$,
so changing $\Delta t$ silently changes the support stiffness. Every
time-step study here holds the physical $k_D$ fixed by adjusting
`--kd`.

## 8. Implementation

### Code map

All files are in `studies/variational-fd-fsi/` of the workspace repository,
branch `study/variational-fd-fsi`, commit `2f21e44`. The shared GPU fluid
solver is not modified: a script generates an isolated copy of
`fdm-3d-v1-gpu/demo/ifed_bench.cu`, adds the coupling adapter to it, and
records source hashes.

| File | Role |
| --- | --- |
| `prototype.py` | NumPy reference: one tetrahedron, dense $M$ and $C$, gradient/affine/power checks |
| `coupling.h` | Single-tetrahedron C++ operators (4-point rule, exact inverse mass) for the first GPU box test |
| `benchmark_coupling.h` | Host reference adapter: global mass, Duffy quadrature, stencils, constrained inverse, regions, RT0 |
| `cuda_transfer.cuh` | CUDA stencil construction, gather ($C u$) and spread ($-C^{\mathsf T}\lambda/h^3$) |
| `cuda_dense_inverse.cuh` | cuBLAS mass inverse (triangular or precomputed) plus the constraint correction |
| `prepare_benchmarks.py`, `build_benchmarks.sh` | Generate and build the isolated driver `ifed_comparison.cu` |
| `check_*.cpp`, `check_*.cu`, `check_*.py` | Independent operator, material, RT0, region, CUDA and quadrature checks |
| `audit_checkpoint.py` | Re-derive solid velocities and volume rates from saved checkpoints, in NumPy |

### Data layout

A quadrature point is stored once, and a stencil entry links it to one fluid
unknown:

```cpp
struct Q       { size_t nodes[4]; double basis[4]; double weight; }; // N_a(X_q), w_q
struct Stencil { size_t q; size_t index; int c; double phi; };      // phi_i^c(x_q)
```

Quadrature points are fixed: they are created once, in the reference
configuration. Stencils are rebuilt at every geometry update, with 24
entries per point (trilinear) or 6 (RT0). Matrices $C$ and $C^{\mathsf T}$
are never formed. The same stencil list is traversed in both directions, so
the two operators are transposes of each other by construction.

### Host reference

```cpp
// Gather: rhs = C u, then w = A rhs
for (auto& e : stencils) {
  const Q& q = qs[e.q];
  double v = q.weight * e.phi * u[e.c][e.index];
  for (int a = 0; a < 4; a++) rhs[3*q.nodes[a] + e.c] += q.basis[a] * v;
}
w = constrained_solve(rhs);

// Spread: lambda = A g, then f = -C^T lambda / h^3
lambda = constrained_solve(g);
for (i in points) val[i] = sum_a basis[a] * lambda[node a];   // lambda_h(x_q)
for (auto& e : stencils) f[e.c][e.index] -= qs[e.q].weight * e.phi * val[e.q][e.c] / h3;
```

`constrained_solve` applies $M^{-1}$ through a dense Cholesky factor
(reference meshes, at most 2000 nodes). It then subtracts
$Z(BZ)^{-1}Z^{\mathsf T}$ from the result.

**Interior guard:** before converting $r_d$ to an integer, the code checks
that it is finite and that $2\le r_c$ and $1\le r_{d\ne c}$, with $r<N$. A
point whose stencil would reach a boundary face or ghost cell raises an
error. The stencil is never truncated, which keeps the resultant and power
identities intact. In the benchmarks, this guard is how blow-ups and
inadequate domain clearance show up.

### CUDA kernels

Three kernels, each with one thread per item:

- **`build_stencils`** (one thread per quadrature point) computes
  $\mathbf{x}_q$ from the device nodal coordinates and writes the 24 (or 6)
  stencil entries. It sets an error flag if the guard fails, and the host
  reads back that single integer. Positions are accumulated with
  `__dmul_rn`/`__dadd_rn` (no fused multiply–add), in host order. Without
  this, a point lying exactly on a cell face could select a different cell
  on the GPU than on the CPU.
- **`gather`** (one thread per stencil entry) computes $w_q\varphi\,u$ and
  adds $N_a\times$ that value into the 4 nodal slots using double-precision
  `atomicAdd`.
- **`spread`** (one thread per stencil entry) evaluates
  $\lambda_h(\mathbf{x}_q)$ from the 4 nodal values and `atomicAdd`s
  $-w_q\varphi\lambda_h/h^3$ into the fluid face array.

Atomics make the summation order, and so the last bits, nondeterministic.
Agreement is therefore verified numerically rather than bitwise:
CPU and device trajectories differ by at most $5\times10^{-15}$ cm after
200 steps, and $8\times10^{-14}$ cm after a 0.5 s active-LV ramp.

The first CUDA version built the stencils on the host and uploaded them at
every step. It was slower than the CPU: on a 243-node Cook mesh with
125 points, the upload was 73.7 MB, 11.7 ms per transfer pair plus 14 ms of
host assembly. Building stencils on the device removed that cost. These are
warmed fixed-state timings for one geometry update plus one
interpolate/spread pair, with mass solves on the CPU:

| Nodes / points per tet | CPU (ms) | Device stencils + CUDA transfer (ms) | Ratio |
| --- | ---: | ---: | ---: |
| 50 / 27 | 0.559 | 0.117 | 4.8 |
| 50 / 125 | 2.531 | 0.345 | 7.3 |
| 243 / 27 | 5.289 | 0.612 | 8.6 |
| 243 / 125 | 24.585 | 2.721 | 9.0 |

These are component timings. They exclude the fluid solve and are not a
whole-solver or time-to-accuracy speedup.

### Mass inverse on the GPU

Nodal vectors are interleaved ($x_0,y_0,z_0,x_1,\dots$). cuBLAS reads such a
vector as a column-major $3\times n$ matrix $R$. Applying $M^{-1}$ to all
three components at once is then a right-side solve,
$R\,U^{-1}U^{-\mathsf T}$, with the host Cholesky factor uploaded once. No
transposes or copies are needed. There are two backends:

- `--mass-backend cuda-dense`: two `cublasDtrsm` calls per application.
- `--mass-backend cuda-inverse`: form $M^{-1}$ once on the GPU, symmetrise
  it, then apply it with one `cublasDgemm` $(3\times n)(n\times n)$.

The constraint correction is applied in the same routine: `dual` $=Z^{\mathsf T}r$
(GEMV), $r\leftarrow M^{-1}r$, two `trsv` calls with the Gram factor, and
$r\mathrel{-}=Z\,$`dual`. It is one fixed linear operator, identical for
velocity and force.

| Nodes | CPU solve (ms) | GPU triangular (ms) | GPU precomputed inverse (ms) |
| --- | ---: | ---: | ---: |
| 50 | 0.0043 | 0.131 | 0.019 |
| 243 | 0.097 | 0.746 | 0.063 |
| 1731 | 5.386 | 5.452 | 0.726 |

Narrow triangular solves use the GPU poorly. The precomputed inverse wins
from about 250 nodes. Its storage grows as $n^2$ and its setup as $n^3$, so
a sparse solver (for example lumped-preconditioned CG, or a sparse Cholesky)
is needed beyond a few thousand nodes. The region constraints' $Z$ and Gram
factor are still prepared on the host at each geometry update.

### Driver options

```bash
ifed_comparison --case lv_p3 --coupling variational \
  --quad 3|5 --reconstruction trilinear|rt0 \
  --volume-constraint none|global|patches --patch-bins 2|4 \
  --geometry-update legacy|midpoint \
  --transfer-backend cpu|cuda|cuda-device \
  --mass-backend cpu|cuda-dense|cuda-inverse \
  --dt 1e-4 --kd 2.5        # physical kD = kd * h / dt^2
```

`--coupling ib4` runs the original nodal IB-4 baseline on the same mesh and
grid.

## 9. How the implementation is verified

| Check | Independent of | Result |
| --- | --- | --- |
| Elastic gradient vs finite-difference energy | Analytic $P$ | $2.2\times10^{-13}$ |
| Affine velocity reproduction | — | $5.6\times10^{-16}$ |
| Power identity $h^3u^{\mathsf T}f+g^{\mathsf T}\mathbf w$ | Same stencils | $\le 2\times10^{-15}$ (operator), $<1.7\times10^{-11}$ normalised (full LV run) |
| Internal-force resultant | — | $2\times10^{-19}$ |
| Volume gradient vs finite differences | Analytic cofactors | $8.6\times10^{-13}$ |
| Constrained volume rate $B\mathbf w$ | — | $\le 1.8\times10^{-15}\,\mathrm{cm^3/s}$ |
| GPU constitutive stress vs energy differences (9 cases) | Separate code path | relative $\le 2.1\times10^{-9}$ |
| CUDA vs host operators (36 configurations) | Host reference | roundoff |
| Checkpoint audit: re-projected vs stored velocity | NumPy re-implementation | $\le 2\times10^{-14}$ cm/s |

These checks establish that the code computes the intended operators. They
do not establish that the operators give accurate FSI. That question is
answered in the companion results page.

## 10. What the method does and does not deliver

**It delivers:**

- an exact discrete work balance between fluid and solid;
- exact transfer of rigid and affine motion;
- zero net internal force on the fluid;
- an optional exact zero instantaneous total-volume rate, with the adjoint
  preserved;
- a GPU implementation that matches the CPU reference to roundoff.

**It does not (yet) deliver:**

- **Local incompressibility.** P1 projection creates divergence; the
  constraints only control volume totals.
- **Large explicit time steps.** The split coupling has an elastic-feedback
  limit, $\Delta t\,\omega\le2$.
- **Accurate penalty supports.** These are measured, not assumed.
- **Resolution of cell crossings by quadrature.** Gauss rules converge
  slowly across MAC planes.
- **Scalable sparse mass solves.**

In the Cook benchmark at the endpoint, 27 versus 125 points change the
loaded-corner displacement by less than 0.03 %. Refining the solid changes
it by 4–6 %.

The open research direction is a quadrature rule aligned with grid cells,
a divergence-compatible solid space or constraint, and a matched comparison
with an existing quadrature-based immersed method, at equal verified
accuracy. See the
[results page](/posts/variational-fd-fsi-quadrature-study/) for the evidence
behind each statement.
