---
title: "402: Turek FSI2 Benchmark"
description: "An elastic flag behind a cylinder in channel flow: the classic FSI2 benchmark."
date: 2026-09-12
weight: 2
academic: true
---

## 1. Introduction

This demo appears in a lot of publications such as  {{< cite "turek2006proposal" "author" >}} and {{< cite "tukovic2018openfoam" "author" >}} , and there also some links for it: 
1. https://www.solids4foam.com/tutorials/more-tutorials/fluid-solid-interaction/HronTurekFsi3.html
2. https://kratosmultiphysics.github.io/Examples/fluid_structure_interaction/validation/fsi_turek_FSI2/
3. https://docs.feelpp.org/toolboxes/latest/fsi/TurekHron/#Sandboge
4. https://oomph-lib.github.io/oomph-lib/doc/interaction/turek_flag/html/#nested-classes
    among which I think 1 and 2 are more reliable to reimplement. what we are going to reimplement is the one appears in 
    {{< cite "li2025local" "author" >}} (**4.3.2 Modified Turek-Hron**) which is a bit different from the original one, but it is more suitable to be compared with.
    {{< references >}}



## Results

> Same as {{< cite "li2025local" "author" >}}: the Saint Venant-Kirchhoff constitutive law. Different: the IB$_4$ kernel (paper: IB$_3$/BS$_3$/CBS$_{32}$), the Chorin and IPCS schemes, a much softer tether (κ_s = κ̂Δx/Δt² with κ̂ = 1.0 vs the paper's 5.0×10⁴; the simulation already diverges at κ̂ = 2.5 in our explicit IB coupling, so the paper's stiffness cannot be computed), and no volumetric stabilization parameter.

We run the same setup (N = 128, MFAC = 0.5, κ̂ = 1.0, T = 1 s) with both schemes. The two solvers agree closely: identical flapping frequency (≈ 5.1 Hz), visually indistinguishable wake fields (Figures 2–3) and a median per-frame difference of 0.14% in the flow-energy integral (Figure 1), while the peak tip amplitude differs by 12% (3.35 cm for Chorin vs 2.94 cm for IPCS).

{{< figure src="https://githubimages.pengfeima.cn/images/202610011414836.png" title="Figure 1. Point A vertical displacement $\Delta Y(t)$ (top) and the flow-energy integral $\int_\Omega u^2\,\mathrm{d}A$ (bottom) for the two schemes (N = 128, MFAC = 0.5, κ̂ = 1.0, T = 1 s). Both schemes give the same flapping frequency ≈ 5.1 Hz; the peak amplitudes are 3.35 cm (Chorin) and 2.94 cm (IPCS)." >}}

{{< figure src="https://githubimages.pengfeima.cn/images/202610011414450.png" title="Figure 2. Vorticity $\omega_z$ at $t = 1$ s (top: Chorin, bottom: IPCS). The wake, the deflected beam and the cylinder are visually indistinguishable between the two schemes." >}}

{{< figure src="https://githubimages.pengfeima.cn/images/202610011415796.png" title="Figure 3. Figure 2 zoomed on the cylinder, the flexible beam and the near wake." >}}

{{< color "red" >}} Figures from the paper are obviously much acuter than our results. I think our results are the best we can get given the current mesh resolution. I doubted that the authors of the paper are using much denser background mesh. I also doubted that the parameter kappa in the paper is so large that we can barely use it because of stability. It should be smaller. No other questions currently.{{< /color >}}

{{< figure src="https://githubimages.pengfeima.cn/images/202609261742659.png" title="Figure 3. Figure 2 zoomed on the cylinder, the flexible beam and the near wake." >}}

{{< color "red" >}} One more question is that I doubt that they have used ramping preloading, which is not mentioned in the paper.{{< /color >}}

## Appendix: Digest {{% cite "li2025local" "author" %}} 4.3.2 Modified Turek-Hron
We investigate a modified version of the Turek-Hron fluid-structure interaction (FSI) benchmark,$^{56}$ which simulates flow around a flexible elastic beam attached to a fixed circular cylinder. $^{25}$ While the original benchmark specifies domain dimensions of $L= 2. 5$ and $H=0.41$, we extend the length to $L=2.46=6.0H$ to accommodate square Cartesian grid cells. This modification has a negligible impact on the benchmark results. The computational setup uses a fine-grid Cartesian cell size of $\Delta x=L/N$ with a time step of $\Delta t=0.00164\Delta x$, where $N$ is the grid number along the $\tilde{\text{longest dimension of the fluid domain. The structure consists of a circular cylinder }}($diameter d=0.1) centered at (0.2, 0.2); (2) and an elastic beam (length $l=0.35$, height $h=0.02)$ fixed to the cylinder's rear. A control point $A$ (initial position is (0.6,0.2)) is used for monitoring displacement. Fig. 24 shows the setup schematic.

![image-20261001021029977](https://githubimages.pengfeima.cn/images/202610010210227.png)

Figure 24: Schematic of the Turek-Hron benchmark





The boundary conditions are specified as follows: at the inlet ($x = 0$), $u(0, y) = 1.5Uy(H - y)/(H/2)^2$, where $U = 2$ is the average velocity; at the outlet ($x = L$), zero normal traction and zero tangential velocity are imposed; and along the top and bottom walls ($y = 0, H$), zero velocity conditions are enforced. The flow parameters yield $Re = \rho Ud/\mu = 200$, with $\rho = 1000$ and $\mu = 1$. The structure is modeled using the Saint Venant-Kirchhoff constitutive law: $\mathbb{S} = \lambda_s \text{tr}(\mathbb{E})\mathbb{I} + 2\mu_s \mathbb{E}$ where $\mathbb{S}$ is the second Piola-Kirchhoff stress tensor, $\mathbb{E}$ is the Green-Lagrange strain tensor, $\mathbb{I}$ is the second-order identity tensor, and material parameters are $\mu_s = 1 \times 10^6$, and $\lambda = 8 \times 10^6$. The cylinder is constrained using a spring tether force with penalty parameter $\kappa_s = 5.0 \times 10^4 \Delta x / \Delta t^2$. We examine three kernels: IB$_3$, BS$_3$, and CBS$_{32}$. The fluid domain uses $N = 128$ grid points along its longest

dimension, providing sufficient resolution to isolate the effects of solid mesh refinement. We investigate MFAC values
of 0.5,0.75,1.0,1.25, and 1.5.
Figure 25 presents a representative color map of the vorticity field, highlighting the deformed beam simulated with
the CBS$_{32}$ kernel and MFAC=0.5.
Table 4 summarizes the maximum vertical displacements $(\Delta Y)$ at point A (shown in Fig. 24) for each kernel type across different MFAC values. The IB$_3$ kernel exhibits the most stable behavior concerning MFAC variations, while CBS kernels require smaller MFAC values and fail when MFAC exceeds 1, consistent with observations from other benchmarks. Figure 26 illustrates the oscillation histories of the vertical displacement for three MFAC values. The IB and BS kernels yield similar results, with smaller MFAC values generally predicting larger displacements. In contrast, the CBS kernel is less sensitive to the solid mesh resolution. The observed phase shift across different MFAC values is attributed to time step variations.



![image-20261001022506178](https://githubimages.pengfeima.cn/images/202610010225308.png)

Figure 25: Vorticity field of CBS32 with MFAC=0.5. The gray colormap shows the displacement magnitude.

Table 4: Maximum vertical displacements for different kernel types across MFAC values. Missing data points indicate timestepping instabilities encountered when using a time step size of Δt = 10−6 s.

MFAC 

0.5 0.75 1 1.25 1.5 

 0.03686 0.03215 0.02794 0.02633 0.03087



![image-20261001022652397](https://githubimages.pengfeima.cn/images/202610010226530.png)

Figure 26: Vertical displacement of point A (as shown in Fig. 24 under varying MFAC values for different kernels. Right panels show detailed oscillations during t = 6.5–7.0.