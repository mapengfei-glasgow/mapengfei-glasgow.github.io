---
title: "0: Duality of the Coupling Operators — Spreading and Interpolation as Discrete Adjoints"
description: "Why force spreading and velocity interpolation must be discrete adjoints of each other — the adjointness results of the nodal IFED analysis (Wells et al. 2023) and how AFSI keeps the duality by applying the assembled load vector directly as a source term."
date: 2026-10-01
weight: 1
academic: true
reference: "Wells et al. (2023)"
status: Complete
---

The immersed-boundary coupling is exactly two operators: **spreading**, which
carries the Lagrangian force to the Eulerian side, and **interpolation**,
which carries the Eulerian velocity back to the markers. Whether the coupling
conserves momentum and energy is decided by how the two relate to each other:
they must be **discrete adjoints** — *dual* — of one another. The nodal IFED
analysis of {{< cite "wells2023nodal" "author" >}} gives the precise
conditions under which this duality holds, and this solver's coupling core is
built as that paper's *fully nodal* case — with no projection matrix ever
assembled.

## 1. The requirement: discrete adjointness

Discretising both transfer integrals with the same quadrature makes the two
operators transposes of each other:

> “if we discretize the integrals … with the same quadrature formula then the
> spreading and interpolation operators are discretely adjoint”

— {{< cite "wells2023nodal" "author" >}}, who point to
{{< cite "griffith2017hybrid" "author" >}} for the full discussion. The
duality is what makes a coupling *innocent*; the paper names the two things
at stake:

* **momentum** — mixing quadratures “is not guaranteed to discretely maintain
  this equivalence”, and “this correspondence is necessary to avoid the
  spurious creation or destruction of momentum in the fluid-structure
  coupling”;
* **energy** — “although we do not have an identity for the Lagrangian
  kinetic energy, the adjointness of the coupling operators ensures that
  energy is not spuriously created or destroyed”.

In a finite-element IFED method the danger is structural: both directions
project data onto the structural finite-element space, so “evaluating either
coupling operator requires solving a matrix equation at every time step” —
the force through a mass matrix $\mathbb{M}\vec{F} = \vec{L}$, the sampled
velocity through the same kind of matrix, $\mathbb{M}\vec{U} =
\vec{L}^{\mathrm{IB}}$. If the two directions use matrices that are
inconsistent with each other (a consistent projection on one side, a lumped
one on the other), adjointness is silently lost.

## 2. What the nodal analysis proves

The paper's remedy is to use the *same* nodal quadrature for every projection
and for the coupling itself. Three results matter for us.

**The weights become arbitrary (Theorem 2).** With nodal quadrature the
velocity projection matrix cancels outright — “the projection of the
velocity … is exactly the same as interpolating $u$ at the nodes” — and the
force projection does the same:

> “If, in the IFED method, the force projection, force spreading, and velocity
> projection operators are all discretized with the same nodal quadrature rule
> $\mathbb{N}_q$, then the values of $w_q$, which correspond to the diagonal
> entries of $\mathbb{D}$, can be chosen as arbitrary nonzero values.”

“The entries of the lumped mass exactly cancel out with coupling weights”,
and the scheme “depends only on the positions of the nodes and not on the
nodal quadrature weights”. This is what removes the classical obstacle to
mass lumping for higher-order elements: for many higher-order spaces the
nodal quadrature has zero or negative weights, and the paper notes that
“since the fully nodal scheme is independent of $\mathbb{D}$, it may be used
with finite elements like $\mathbb{P}_2$ that do not normally work with mass
lumping”.

**The moments do not depend on the weights (Theorem 3).** As long as the same
rule is used on both sides:

> “the force defined on the Cartesian grid will always satisfy the *same*
> zeroth and first force moment conditions, *independent* of $\mathbb{Q}_q$.”

Total force and torque therefore reach the fluid exactly as summed on the
markers — for any admissible rule, because both sides speak the same
quadrature language.

**It is the classic IB method in disguise.** Integrating the nodal spreading
expression by parts reduces it to a weighted average of
$\nabla_X \cdot P$ at the node — in the paper's words, “the fully nodal
coupling approach described here is essentially the classic IB method”.

## 3. How AFSI adapts this to a finite-element background

AFSI replaces the finite-difference Cartesian grid by the fluid solver's own
degrees of freedom, keeping the fully nodal structure — these are the
modifications the
[nodal method page](/afsi/0-nodal-immersed-boundary-finite-element-method/)
refers to. Three design decisions carry the duality.

**The coupling lattice is the velocity-dof lattice.** `IBMesh(order)` builds
a uniform lattice whose spacing matches the dofs of the structured fluid
mesh (`order = 2` for the $\mathbb{P}_2$ velocity space, so the lattice
sizing is $h/2$); `build_map` hashes the actual dof coordinates onto it, and
`extract_dofs` / `assign_dofs` move values between the lattice and the dof
vector. Both operators evaluate the same four-point kernel
($\mathrm{IB}_4$) on that same lattice, at the same marker positions — the
interaction points are the solid mesh's degrees of freedom, the paper's
“nodal interaction”.

**The force is applied directly as a source term, not projected.** Each step
the solid's unified weak form is assembled by FEniCSx into a load vector $L$
— the same weak form that defines the Lagrangian force density $F$ on the
demo pages, plus the penalty and traction terms — and the marker weights are
fixed to the constant

$$
w_k = 1,
$$

an arbitrary value in the sense of Theorem 2 (literally the
`array_solid[i].w = 1.0` of `solid_to_fluid`). Spreading then distributes the
loads onto the velocity dofs,

$$
f_j = \frac{1}{\Delta x\,\Delta y}\sum_k w_k\,\delta_h(x_j - X_k)\,L_k,
$$

and writes the result straight into the fluid force field. No Lagrangian mass
matrix is formed anywhere; algebraically this is the nodal IFED route
$F = \mathbb{D}^{-1}L$ followed by spreading with $\mathbb{D}_{qq}$ — the
mass-matrix entries cancel, so writing them down would change nothing.

**The velocity is read back by the same machinery.** `fluid_to_solid`
evaluates

$$
U_k = \sum_j \delta_h(x_j - X_k)\,u_j
$$

on the same lattice and writes the result into the solid's dof vector — the
nodal identity $\vec{U} = \vec{U}^{\mathrm{IB}}$ again, with no projection
solve. The whole per-step coupling is five lines of the driver (demo_441):

```text
u ← fluid step          # the momentum equation sees f as a source term
U = fluid_to_solid(u)   # velocity → markers (four-point-kernel sums)
X += U Δt               # advect the structure
L = assemble(solid weak form)   # the load vector — no projection
f = solid_to_fluid(L)   # w = 1, same kernel, same lattice → velocity dofs
```

**The duality is then exact up to one constant.** For a given marker
configuration both operators evaluate identical kernel values on identical
lattice points, so

$$
\sum_j f_j\,u_j \;=\; \frac{1}{\Delta x\,\Delta y}\sum_k L_k\,U_k
\qquad \text{for every } L \text{ and } u,
$$

i.e. $J = \Delta x\,\Delta y\,S^{\top}$ — exact transposes, with a single
global constant (the lattice cell measure) standing between them, playing the
role of the arbitrary admissible weight. Summing over the lattice, the zeroth
and first moments of the spread force reproduce the marker sums
$\sum_k L_k$ and $\sum_k X_k L_k$ (away from the domain boundaries, where
the four-point kernel carries precisely the discrete moment conditions of
Theorem 3).

**And the fluid only ever sees a source term.** The Eulerian force enters the
momentum equation through one weak-form term only,
$-\int f \cdot v \,\mathrm{d}x$ in the Chorin solver, so it never appears in
a matrix operator of the fluid solve either. The practical consequence: in
this solver *there is no coupling mass matrix that could be inconsistent with
the interpolation operator* — the failure mode of §1 cannot arise, because
the matrix is never assembled in the first place. The coupling lives in the
compiled core (`afsic/src/coupling`, exposed as `from afsic import IBMesh,
IBInterpolation`, with the 3-D twin `IBInterpolation3D`); every demo on this
site drives it through the same four calls.

| scheme | force to the fluid | velocity to the markers |
|---|---|---|
| elemental IFED | solve $\mathbb{M}\vec{F} = \vec{L}$; spread with adaptive quadrature | solve $\mathbb{M}\vec{U} = \vec{L}^{\mathrm{IB}}$ |
| nodal IFED (Wells et al.) | weights arbitrary (Theorem 2); lumped-mass entries cancel | $\vec{U} = \vec{U}^{\mathrm{IB}}$: projection = interpolation |
| AFSI (this solver) | spread the assembled load with $w_k = 1$; no matrix | four-point-kernel sums at the markers; no matrix |

## 4. What the duality does not buy

Adjointness is a consistency property, not an accuracy one. The nodal
coupling still needs the markers dense enough for the spread force density to
leave no gaps on the lattice — otherwise, in the paper's words, “there will
be gaps in the Cartesian grid representation of the force density and,
therefore, the potential for catastrophic leaks through the structure”. That
requirement is what the marker-spacing scans of
[demo_442](/afsi/demo-442/) (the $\mathrm{MFAC}$ sweep and the $1\,\%$
pressure-plateau) and the volume checks across these pages measure; the
duality guarantees that whatever accuracy the discretisation has is not
spoiled by a momentum or energy leak in the transfer itself.

## References

{{< references >}}
