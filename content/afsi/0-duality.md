---
title: "0: Duality of the Coupling Operators — Direct Loads, IB Kernels, and RT Coupling"
description: "Discrete power consistency in AFSI: distinguishing force-density coefficients from assembled loads, correcting the IB4 transfer for a finite-element fluid, and extending the same adjoint principle to the single-process RT prototype."
date: 2026-10-01
lastmod: 2026-10-02
weight: 1
academic: true
reference: "Wells et al. (2023)"
status: "Updated; RT implementation is a validated single-process prototype"
---

Immersed coupling transfers fluid velocity to the structure and structural forces back to the fluid. In a finite-element implementation, these transfers must be defined using the correct vector representations: **a force-density coefficient vector is not an assembled load vector**.

At a fixed structural configuration, let $J$ map fluid velocity coefficients to structural nodal velocities. If $L_s$ is the assembled structural load, the power-consistent fluid load is

$$
U_s = J u_f,
\qquad
\boxed{b_f = J^T L_s.}
$$

This identity applies both to the corrected IB4 coupling and to the new RT nodal coupling. It guarantees matching discrete power across the transfer, not automatic conservation of the fully discrete system's energy or solid volume.

This page describes the supplied AFSI source and the single-process RT extension inspected and tested on 2 October 2026. Defaults are specific to each driver; they should not be inferred from the solver class alone.

## 1. Coefficients, loads, and the power identity

Write the fluid velocity as

$$
u_h(x)=\sum_j u_j\psi_j(x),
$$

and denote the fluid mass matrix by

$$
(M_f)_{ij}=\int_\Omega\psi_j\cdot\psi_i\,dx.
$$

The relevant vectors are:

| Symbol | Meaning | Power pairing |
|---|---|---|
| $u_f$ | Fluid velocity coefficients | Paired with $b_f$ |
| $f_f$ | Coefficients of a fluid force-density function | Fluid power is $u_f^T M_f f_f$ |
| $b_f$ | Assembled fluid load vector | Fluid power is $u_f^T b_f$ |
| $U_s$ | Structural nodal velocity coefficients | Paired with $L_s$ |
| $L_s$ | Assembled structural load vector | Structural power is $U_s^T L_s$ |

A structural weak form, including the selected elastic and penalty terms, produces entries such as

$$
(L_s)_a=-\int_{\Omega_s^0}P:\nabla_X\Phi_a\,dX
+\text{other structural load terms}.
$$

These entries already include the integration defining the load. They should not subsequently be multiplied by another structural mass matrix or another set of nodal quadrature weights.

For a fixed configuration $\chi$, power consistency requires

$$
u_f^T b_f=(J(\chi)u_f)^T L_s
\quad\text{for all }u_f,L_s.
$$

Consequently, the load-transfer operator is $J(\chi)^T$. If a fluid force-density function is required instead, its coefficients must satisfy

$$
M_f f_f=J(\chi)^T L_s.
$$

Equivalently, when structural force density is represented by coefficients $F_s$ with $L_s=M_sF_s$, the density-to-density spreading operator is

$$
S=M_f^{-1}J^TM_s.
$$

The different formulas describe different representations of the same transfer. Calling all of them “spreading” without identifying those representations obscures the mass matrices.

These are spatial power identities at the same configuration. With imposed velocity boundary conditions, the statement applies to the appropriate unconstrained velocity variations; boundary reactions and prescribed-boundary work must also be accounted for.

## 2. What the nodal IFED analysis contributes

The nodal IFED analysis of {{< cite "wells2023nodal" "author" >}} shows how consistent use of nodal quadrature in structural projection and coupling permits cancellation of diagonal structural mass weights. This supports efficient coupling using assembled nodal structural loads without separately recovering a force-density function through a consistent structural mass solve.

That result must not be interpreted as permission to omit the **fluid** mass matrix when a spread coefficient vector is inserted into a finite-element volume integral. The original IFED setting uses a Cartesian finite-difference fluid discretization; adapting its transfer to a finite-element fluid requires identifying the actual fluid load pairing.

Similarly, force and torque preservation require the corresponding constant and rotational reproduction or discrete moment properties. They do not follow from transpose symmetry alone.

The broader weak-coupling framework is discussed by {{< cite "griffith2017hybrid" "author" >}}. The matrix identities on this page specify how the current AFSI paths realize the power pairing.

## 3. The IB4 lattice path in AFSI

### Velocity interpolation and raw spreading

The current IB4 implementation uses an auxiliary uniform lattice aligned with the supported structured velocity DOFs. In `demo_402`, the fluid mesh is quadrilateral and the velocity-pressure spaces are **Q2/Q1**, rather than triangular P2/P1. For velocity order two, the lattice spacing is half the corresponding background cell width.

Let

$$
\Delta V=\Delta x\,\Delta y
$$

in two dimensions. Use $W_{aj}$ for the **dimensionless tensor-product kernel weight** used by the code. This avoids confusing the code weight with a dimensionally normalized regularized delta function. Component indices are suppressed below.

The velocity operation is

$$
U_a=\sum_j W_{aj}u_j,
\qquad J=W.
$$

With `array_solid[i].w = 1.0`, the raw spreading output is

$$
f_{\mathrm{raw},j}
=\frac{1}{\Delta V}\sum_a W_{aj}(L_s)_a
=\frac{1}{\Delta V}(J^TL_s)_j.
$$

Thus the kernel operations satisfy the lattice identity

$$
\Delta V\,u_f^T f_{\mathrm{raw}}=U_s^TL_s.
$$

The factor $\Delta V$ is the background lattice measure. It is not an arbitrary structural quadrature weight and cannot be dropped when interpreting the raw output as a finite-element load.

### Three ways to use the raw output

| Path | Operation | Actual fluid load | Power-consistent with $U_s=Ju_f$? |
|---|---|---|---|
| Legacy body-force path | Store $f_{\mathrm{raw}}$ in a fluid `Function`, then assemble $\int f_h\cdot v_h\,dx$ | $M_f f_{\mathrm{raw}}=\Delta V^{-1}M_fJ^TL_s$ | Not generally |
| Mass-consistent path | Solve $M_f f_f=\Delta V f_{\mathrm{raw}}$, then assemble the body-force term | $J^TL_s$, up to solve tolerance | Yes |
| Direct-load path | Add $\Delta V f_{\mathrm{raw}}$ directly to the momentum RHS | $J^TL_s$ | Yes |

In particular, the legacy path still applies a fluid mass matrix even when that matrix is never assembled as a separate named object: it is implicit in the weak-form integration. Q2/P2 consistent mass matrices are not generally $\Delta V I$.

### Current direct-load implementation

In the supplied `demo_402/main.py`, `IB_DIRECT_LOAD` defaults to `1`. It constructs Chorin or IPCS with `ib_body_force=False`, preventing the body-force weak term from being assembled, and computes

```python
ns_solver.f.x.petsc_vec.copy(result=_b_direct)
_b_direct.scale(_Vh)
```

Here `_Vh` is the auxiliary lattice area. The solver adds the resulting load through

```python
self.b1.axpy(1.0, self.ib_load)
```

after the assembled RHS has been lifted and its shared contributions accumulated, and before velocity boundary values are imposed.

The total RHS is still assembled. Only the IB load bypasses the force-density volume integral. Enabling both `ib_body_force=True` and a nonzero `ib_load` would double-count the force.

The solver classes retain `ib_body_force=True` as their default, and other drivers have different `IB_DIRECT_LOAD` defaults. The statement “AFSI always uses direct loads” is therefore incorrect.

The active C++ kernel implementation is in `afsic/src/coupling/main.h`, with Python/MPI bindings in `afsic/src/afsic_ext.cpp`. Older files under `afsic/src/coupling/src/` are not the implementation selected by the current build. The current bindings gather data to the root process for coupling and scatter the results back.

## 4. The single-process RT nodal coupling

The RT extension uses the same assembled structural loads, but replaces the auxiliary kernel lattice with direct evaluation of the fluid finite-element field.

For a structural node at its current physical position $x_a=\chi_a$, define

$$
E_{(a,\alpha),j}=\psi_{j,\alpha}(x_a).
$$

The paired operations are

$$
\boxed{U_s=Eu_{\mathrm{RT}},\qquad b_{\mathrm{RT}}=E^TL_s.}
$$

There is no regularized delta kernel, lattice-volume scaling, fluid mass inverse, or additional global RT projection in this transfer. Fluid momentum still requires its normal global solve.

RT DOFs represent flux and internal moments, not velocities at point locations. Their geometric association with a face outside the solid does not prevent coupling: a basis function contributes whenever its value at a solid interaction point is nonzero.

The implementation uses DOLFINx point evaluation to include Piola mappings and DOF orientation transformations. A cell-conflict coloring batches independent basis evaluations when constructing the sparse matrix $E$. Force transfer uses exactly its transpose. The matrix must be updated after the structural configuration changes.

A structural point on a fluid element interface uses the trace from the smallest local cell index. Both transfer directions use that same trace. This preserves the algebraic adjoint identity but does not remove RT tangential jumps. Points outside the background mesh are rejected rather than silently ignored.

The new modules are:

- `afsic/src/afsic/euler/RTFluidSolver.py`;
- `afsic/src/afsic/coupling/RTNodalCoupling.py`;
- `afsic/demo/demo_rt_serial/main.py`.

The prototype is restricted to real-valued, single-process, two-dimensional runs. The fluid solver uses an RT/discontinuous-pressure mixed discretization, backward Euler, interior-penalty viscosity, and optional upwind convection. It is not the existing Chorin/IPCS algorithm with its space name changed.

## 5. Adjointness and divergence freedom are different properties

The identity $b_f=J^TL_s$ does **not** imply that the driving velocity field is divergence-free. Corrected IB4 coupling can be power-consistent while still producing a velocity interpolant that is not continuously divergence-free.

For the RT solver, the compatible pressure space contains the velocity divergence. Accurately enforcing its continuity equation gives elementwise zero divergence; RT normal continuity supplies the corresponding global flux compatibility. Direct evaluation samples this field without inserting a second kernel interpolation.

Nevertheless, RT tangential velocity may jump across fluid cells. Moreover, structural nodes are advanced numerically and connected by a finite-element geometry. Thus none of the following follows solely from background divergence freedom:

- exact preservation of every solid element's volume;
- exact conservation of fully discrete energy;
- smooth particle trajectories across cell interfaces;
- exact balance of every discretized pressure jump;
- stability for arbitrary structural stiffness or time step.

Spatial interpolation, structural resolution, force quadrature, time integration, solver tolerance, and boundary treatment must be assessed separately.

## 6. Verification available as of 2 October 2026

The existing `test_duality.py` completed **9 checks with no failures**. It tests the lattice-weighted IB interpolation/spreading identity; it does not by itself certify the legacy finite-element body-force path.

The new `test_rt_serial.py` completed **8 tests with no failures**, including parameterized cases. These cover mapped triangle/quadrilateral point evaluation, transpose power consistency, total force and torque, marker relocation, rejection of out-of-domain points, divergence and normal continuity, gradient-force response, and open-channel flux balance.

A short Turek comparison used the same solid mesh, a $32\times8$ quadrilateral background, $\Delta t=5\times10^{-5}\,\mathrm{s}$, convection enabled, and a deliberately accelerated inlet ramp of $0.02\,\mathrm{s}$. The inlet target mean speed was $200\,\mathrm{cm/s}$ and the dimensionless tether parameter was $\widehat\kappa=0.1$. The diagnostic was

$$
\|\nabla\cdot u_h\|_{L^2(\Omega)}
=\left(\int_\Omega(\nabla\cdot u_h)^2\,dx\right)^{1/2}.
$$

| Time (s) | Chorin Q2/Q1 + direct-load IB4 | RT + nodal evaluation |
|---:|---:|---:|
| 0.00005 | $3.52\times10^{-3}$ | $8.48\times10^{-15}$ |
| 0.00025 | $2.80\times10^{-1}$ | $1.61\times10^{-14}$ |
| 0.00050 | $1.92$ | $3.41\times10^{-14}$ |
| 0.00100 | $9.04$ | $8.92\times10^{-14}$ |

These are unnormalized **background fluid** divergence norms, not structural velocity divergence norms. In the two-dimensional CGS calculation their units are cm/s. The two runs use different fluid discretizations and time algorithms; the comparison is not an interpolation-only ablation, an equal-DOF benchmark, or an IPCS comparison.

Over these 20 steps, the maximum normalized power residuals were approximately $6.07\times10^{-15}$ for IB4 and $6.35\times10^{-16}$ for RT, confirming that both tested transfer paths were adjoint despite their very different divergence norms. Here the residual is

$$
\frac{|u_f^Tb_f-U_s^TL_s|}
{\max(1,|u_f^Tb_f|,|U_s^TL_s|)}.
$$

The final relative solid-volume changes were approximately $+3.02\times10^{-6}$ and $-3.25\times10^{-7}$, respectively. These are short-startup observations, not proof of long-time volume conservation.

The RT implementation is currently slower than the small-scale Chorin/IB4 comparison. No performance advantage, full-discrete energy conservation, or validated long-time Turek amplitude/frequency/drag result is claimed.

To reproduce this specific comparison from the `afsic` directory after installation and solid-mesh generation:

```bash
(cd demo/demo_402 && python generate_mesh.py)
python demo/demo_rt_serial/main.py --case turek --method ib \
  --nx 32 --ny 8 --steps 20 --dt 5e-5 --ramp-time .02 --convection \
  --out results/ib-turek-fast-start
python demo/demo_rt_serial/main.py --case turek --method rt \
  --nx 32 --ny 8 --steps 20 --dt 5e-5 --ramp-time .02 --convection \
  --out results/rt-turek-fast-start
```

Both runs write `history.csv` and `summary.json`. The RT extension's README documents the remaining implementation restrictions.

## References

{{< references >}}

- Wells et al., *A nodal immersed finite element-finite difference method*, Journal of Computational Physics 477 (2023), 111890. [DOI](https://doi.org/10.1016/j.jcp.2022.111890); [open-access text](https://pmc.ncbi.nlm.nih.gov/articles/PMC10062120/).
- FEniCS DOLFINx 0.10.0, [divergence-conforming Navier–Stokes demo](https://github.com/FEniCS/dolfinx/blob/v0.10.0/python/demo/demo_navier-stokes.py), the reference formulation for the new RT fluid prototype.
- Implementation evidence: the supplied AFSI source, `demo_402/main.py`, the Chorin/IPCS load interfaces, the new RT modules, and the single-process test and startup-run outputs. These implementation observations are distinct from the IFED literature results.
