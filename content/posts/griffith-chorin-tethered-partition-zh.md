---
title: "Griffith 2009 耦合速度-压力求解器移植与 Chorin 对比"
description: "It is a draft manuscript preparing for JFM."
date: 2026-09-16
academic: true
ShowToc: true
TocOpen: false
Repository: CardioPhysX/mv-turbulance
---

## 0. 结论先写在前面

Since I've been working on the IBFE program up to now, I find myself puzzling over two things. The first is how to know whether the results I compute are correct, and the second is how to know whether my computational speed has reached the limit of the GPU device. I have prepared two test cases. In the first case, a pipe is placed in the center of a box with both ends reaching the boundary, and pressure is applied at both ends of the pipe to simulate the flow when the valve fully opens. In the second case, a baffle is placed in the middle of the pipe to simulate the flow after the valve fully closes. 

Currently, for my solver, what is certainly correct is the issue of the velocity Dirichlet boundary condition, where the pressure satisfies a homogeneous Neumann boundary condition. The internal solve is certainly correct as well. Problems can only arise in these three places: the first is the pressure boundary condition, that is, the so-called traction boundary condition; the second is the treatment of the convective term; and the third is whether the force distribution needs to be corrected when a Lagrangian marker appears on the boundary of the domain. This paper will use these two test cases to study the following test cases one by one.

There are two solvers. One is the implementation from "Griffith 2009," which couples the pressure and velocity by encapsulating the projection method within an FGMRES solver. The second is the original Chorin solver, which is simply the splitting method, known for its issues with boundary layers. There are **four** implementations of the convective term. The worst is the central difference method, which would not be used in any production environment. The second is the semi-Lagrangian method, which was used in my PhD thesis; it is very fast and stable, but not very effective at capturing the turbulence that appears during the simulation. The third is the second-order upwind scheme, and the final one is the XSPPM7 scheme implemented in "Griffith 2009."

Let me briefly summarize the results. In the `--convection off` mode, which comes closest to isolating the difference between the solvers themselves, the two solvers are in fact very close to each other: the final displacement difference of the plate is about 0.40%, the maximum distance difference in marker pairing is about 0.0053 mm, and the RMS relative difference in the velocity and pressure fields is about 0.02%–0.42%. In contrast, under their respective default convection schemes, `--convection native`, where Chorin uses second-order upwind and the Griffith method uses XSPPM7, the final displacement difference of the plate is about 2.61%, the maximum distance difference in marker pairing is about 0.406 mm, and the field differences reach 21%–67%. This larger discrepancy, however, mainly comes from the difference in convective discretization between `SecondUpwind` and `XSPPM7`, rather than from the velocity–pressure coupling approach. Using the uniformly low-order `--convection central` scheme is not a good choice: the Griffith path becomes unstable at around `t = 0.068–0.070 s` (steps 270–280), so it should simply be ignored in the future.

# 1. Problem Settings

The present study considers a series of numerical examples. The first example focuses on a zero-thickness tube model based on the immersed boundary method (IBM). This model differs from the three-dimensional solid tube mesh contained in the `geometry` repository. Both the tube wall and the internal disk are represented by a single layer of Lagrangian points, without three-dimensional solid or shell elements. Consequently, neither structure possesses a geometric thickness, bending stiffness, or in-plane elastic stiffness.

The computational domain has dimensions of 300 mm×75 mm×75 mm. The tube is aligned with the x-direction, with a length of approximately 300 mm, a radius of 15 mm, and a lumen diameter of 30 mm. The region outside the tube is also filled with fluid. A circular disk with a diameter of 30 mm is placed at x=150 mm, and its reference configuration spans the entire cross-section of the tube lumen. Since the tube wall is represented as a zero-thickness surface, no independent outer diameter is defined. If the inner and outer surfaces are regarded as coincident, both the inner and outer diameters are 30 mm, corresponding to a wall thickness of zero.

The physical density of the fluid is 1060 kg/m3, and the dynamic viscosity is 0.004 Pa⋅s, i.e., 4 cP, corresponding to a kinematic viscosity of approximately 3.7736×10−6 m2/s. When the dimensional momentum equation is divided by the fluid density, the coefficient of the viscous term becomes the kinematic viscosity, and the immersed-boundary body-force density is correspondingly divided by the fluid density. If a nondimensional formulation is further adopted, both the viscosity and force terms must be rescaled according to the selected characteristic scales. The current numerical viscosity parameter is 5.03145×10−5; its correspondence with the physical kinematic viscosity therefore depends on the adopted nondimensionalization scales and should be verified accordingly. The physical time step is 0.00025 s. A total of 400 time steps are performed, corresponding to a total physical simulation time of 0.1 s.

The Lagrangian points representing both the tube wall and the disk are allowed to move with the surrounding fluid and are constrained to remain close to their respective reference positions through tether penalty forces. The circular disk is discretized using concentric rings of Lagrangian points. Each point is assigned an area quadrature weight, and the sum of all area weights is equal to πR2. The same nondimensional tether penalty coefficient, κ=6400, is used for both the tube wall and the disk. Under a consistent nondimensional formulation, the restoring force associated with the i-th Lagrangian point is given by

Fi∗=−κAi∗(xi∗−xi,ref∗),

where the superscript ∗ denotes a nondimensional quantity, Ai∗ is the corresponding area quadrature weight, and xi∗ and xi,ref∗ denote the current and reference positions, respectively. The penalty coefficient controls the extent to which the Lagrangian points are allowed to deviate from their reference positions and should not be interpreted as a Young's modulus. In addition, the markers located at both ends of the tube are fixed.

When the tether penalty coefficient of the circular disk is set to zero and no other fluid-structure interaction force or constraint is applied to the disk, the disk points behave only as passive markers advected by the fluid and no longer affect the flow. From a fluid-dynamic perspective, the model then becomes equivalent to a straight-tube case without an internal disk. The point forces associated with the tube wall and the disk are spread to the face-centered velocity grid of the MAC discretization using one-sided corrected IB4 coupling weights, thereby forming the body-force density entering the fluid momentum equation. The same set of coupling weights is used for velocity interpolation and force spreading, with the appropriate quadrature weights incorporated in each operation.

The flow is driven by traction boundary conditions imposed at the two ends of the computational domain in the x-direction. Traction conditions are prescribed over the entire end surfaces. On the left boundary, a pressure load of 100 mmHg, approximately 13332.2 Pa, is applied over the circular region corresponding to the tube lumen and is gradually introduced through a temporal ramp function, ramp(t). Zero traction is imposed on the remainder of the left boundary and over the entire right boundary. The value 13332.2 Pa therefore represents the prescribed pressure loading difference at the boundaries of the computational domain. Its relation to the actual pressure difference between the physical inlet and outlet of the tube depends on the locations of the tube openings relative to the boundaries of the computational domain.

The above boundary treatment differs from the local boundary treatment used in Griffith's `CircularTractionPatch`, in which only the normal traction degree of freedom is retained within the circular opening, while velocity boundary conditions are imposed outside the opening. Following the configuration adopted in `partition_case`, no volumetric damping is applied to the fluid region outside the tube in the present example.

In the second example, the zero-thickness representation is replaced by a tube with a finite wall thickness within the framework of the nodal immersed boundary method. Both the tube wall and the internal disk are assigned a thickness of 5 mm. This configuration enables the structural components to be represented as finite-thickness immersed solids, allowing their deformation and fluid-structure interaction response to be investigated beyond the idealized zero-thickness approximation.

# 2. Some tricks

1. feedback force on the input and output.
2. Fix layers of points near the input and output.
3. appropriate boundary conditions to ensure no flows outside the tube but no drag force 
4. appropriate $\kappa$
5. appropriate discretization for the convective terms

# 3. Some results

What are the results I desire? 

1. no leakage on the wall for the tube and no leakage on the disc for the tube with a disc
2. Static fluid for the tube with a disc
3. tube flow obeys the Poiseuille law



## Which parameters will influence the leakage

![fig_leak_scaling](https://githubimages.pengfeima.cn/images/202609201520722.png)



![fig5_psi_k25600](/Users/pengfei/Documents/GitHub/fdm-3d-v1-workspace/output/figs_tethered_tube_stream/fig5_psi_k25600.png)

![fig3_psi_N32](/Users/pengfei/Documents/GitHub/fdm-3d-v1-workspace/output/figs_tethered_tube_stream/fig3_psi_N32.png)

![fig4_psi_long](https://githubimages.pengfeima.cn/images/202609201520676.png)

![fig2_stream_long](/Users/pengfei/Documents/GitHub/fdm-3d-v1-workspace/output/figs_tethered_tube_stream/fig2_stream_long.png)

![fig1_stream_N32](https://githubimages.pengfeima.cn/images/202609201520683.png)

## Adding damping to the force seems improve little but adds instabilities.

$$
\mathbf{F}=-\kappa A \int \mathbf{u} \, \mathrm{d}t - \beta A \mathbf{u}
$$



![fig2_damping_flux](https://githubimages.pengfeima.cn/images/202609201516271.png)



![a](https://githubimages.pengfeima.cn/images/202609201510254.png)

















![image-20260922152404915](https://githubimages.pengfeima.cn/images/202609221524094.png)





![image-20260922152346821](https://githubimages.pengfeima.cn/images/202609221523080.png)












## 2. 同一个 demo 里同时运行两个求解器

`fdm-3d-v1-demo/demo/tethered_tube_partition.cpp` 现在包含两条路径：

- `run_chorin(...)`：`ChorinStokesSolver`
- `run_griffith(...)`：`fdm3d::griffith::NavierStokes`

两者共享：

- 同一套网格：`4N × N × N`
- 同一套 tethered 管壁和圆形隔板
- 同一个 one-sided IB4 stencil
- 同一套 x 端面 traction 和 y/z no-slip 边界
- 都不加 explicit-cell drag

运行方式：

```bash
./build/tethered_tube_partition \
  16 400 0.0033333333333333335 6400 \
  out_tethered_compare \
  12.577566273584907 1000 0 both --convection off
```

第 9 个参数选择求解器：

```text
both / chorin / griffith
```

对流开关：

```bash
--convection native   # 默认: Chorin SecondUpwind + Griffith XSPPM7
--convection off      # 两边都关闭对流
--convection central  # 两边统一二阶中心
```

输出目录：

```text
out_tethered_compare/
├── chorin/
├── griffith/
├── comparison.csv
└── summary.txt
```

---

## 3. 结果: 三种对流配置

除非特别说明，以下结果均为：

```text
N = 16
steps = 400
dt = 0.0033333333333333335
kappa = 6400
dp = 12.577566273584907  (100 mmHg)
solver = both
无 explicit-cell drag
```

相对差统一定义为：

$$
\text{rel} = \frac{|a-b|}{\frac12(|a|+|b|)} \times 100\%
$$

### 3.1 相同对流: `--convection off`

这张表最接近“两个求解器本身”的差异。

| 指标 | Chorin | Griffith | 绝对差 | 相对差 |
|---|---:|---:|---:|---:|
| plate 最终位移 (mm) | 1.26323 | 1.26826 | 0.00503159 | 0.3975% |
| 总板力 (N) | 5.30862 | 5.32596 | 0.0173449 | 0.3262% |
| marker 最大位移 (mm) | 1.26323 | 1.26826 | 配对点最大距离 0.005293 | 0.4182% |
| marker RMS 位移 (mm) | 0.16877 | 0.16957 | 配对点 RMS 距离 0.000988 | 0.5840% |
| u 场 RMS | 2.72170 | 2.72687 | 0.00806234 | 0.1896% |
| v 场 RMS | 0.072252 | 0.072551 | 0.00045972 | 0.4126% |
| w 场 RMS | 0.072262 | 0.072562 | 0.00046086 | 0.4140% |
| 压力场中心化 RMS | 3.82487 | 3.82422 | 0.00140620 | 0.0168% |

可以看到：

- plate/marker 差在 **0.4%–0.6%** 量级；
- 全场速度和压力差在 **0.02%–0.42%** 量级；
- 两个求解器的速度-压力耦合本身一致性很好。

### 3.2 各自默认对流: `--convection native`

`native` 模式保留各自稳定的对流格式：

- Chorin：`SecondUpwind`
- Griffith：`XSPPM7`

| 指标 | Chorin | Griffith | 绝对差 | 相对差 |
|---|---:|---:|---:|---:|
| plate 最终位移 (mm) | 2.01325 | 1.96136 | 0.05189 | 2.61% |
| 总板力 (N) | 19.4147 | 16.1839 | 3.23081 | 18.15% |
| marker 最大位移 (mm) | 2.01325 | 1.96136 | 配对点最大距离 0.40642 | 20.45% |
| marker RMS 位移 (mm) | 0.23668 | 0.22089 | 配对点 RMS 距离 0.07299 | 31.91% |
| u 场 RMS | 3.37654 | 2.72114 | 0.977998 | 21.50% |
| v 场 RMS | 0.103489 | 0.051490 | 0.103303 | 67.10% |
| w 场 RMS | 0.103081 | 0.052497 | 0.103208 | 65.03% |
| 压力场中心化 RMS | 7.46807 | 3.90416 | 4.04383 | 62.68% |

这张表里的差异**不能全部算到耦合方式头上**，因为对流离散本来就不同。

### 3.3 统一低阶对流: `--convection central`

`central` 模式下两边都用二阶中心对流。第 260 步（`t = 0.065 s`）时：

| 指标 | Chorin | Griffith | 绝对差 | 相对差 |
|---|---:|---:|---:|---:|
| plate 最终位移 (mm) | 0.59062 | 0.59791 | 0.0072855 | 1.226% |
| 总板力 (N) | 2.26160 | 2.34668 | 0.085083 | 3.693% |
| marker 最大位移 (mm) | 0.59062 | 0.59791 | 配对点最大距离 0.043405 | 7.304% |
| marker RMS 位移 (mm) | 0.078345 | 0.079217 | 配对点 RMS 距离 0.003518 | 4.466% |
| u 场 RMS | 1.45384 | 1.46224 | 0.030407 | 0.576% |
| v 场 RMS | 0.027788 | 0.038272 | 0.025512 | 31.74% |
| w 场 RMS | 0.027787 | 0.038262 | 0.025499 | 31.72% |
| 压力场中心化 RMS | 3.83813 | 3.85114 | 0.018151 | 0.338% |

`central` 更差的地方在于：

- 它和 `native` 一样混入了对流差异；
- 它没有限幅/迎风耗散，Griffith 路径在 step 270–280 失稳。

下图是同为第 260 步时三种模式的 plate 位移对比：

{{< chart type="bar" height="250" xlabel="convection mode" ylabel="plate disp at step 260 (mm)" xkind="category" legend="true" caption="图 1. 第 260 步 (t=0.065 s) 三种对流设置下的 plate 最大位移。" >}}
mode, chorin, griffith
native, 0.573719, 0.577121
off, 0.572894, 0.577956
central, 0.590620, 0.597905
{{< /chart >}}

### 3.4 时间曲线与采样数据

这一节的曲线直接来自两次运行的 `history.csv`；PyVista 图由 `markers.csv` 按 `N=16` 重建管壁四边形网格和隔板点云得到。

下面给出两个求解器 plate 最大位移之差 `|plate_Chorin - plate_Griffith|` 的采样值。
空白单元格在图表中会形成断点：

{{< chart height="270" xlabel="t (s)" ylabel="|plate_Chorin - plate_Griffith| (mm)" legend="true" caption="图 2. 两个求解器 plate 位移差的随时间采样；central 只跑到 t=0.065 s。" >}}
t,native_diff,off_diff,central_diff
0.000250,0.000000,0.000000,0.000000
0.005250,0.000106,0.000106,0.000106
0.010250,0.000446,0.000446,0.000446
0.015250,0.000940,0.000938,0.000938
0.020250,0.001315,0.001342,0.001342
0.025250,0.001122,0.001373,0.001373
0.030250,0.002501,0.002135,0.002133
0.035250,0.003336,0.002306,0.002308
0.040250,0.019964,0.003480,0.003382
0.045250,0.029290,0.003049,0.002804
0.050250,0.034570,0.002922,0.002483
0.055250,0.038119,0.003559,0.003077
0.060250,0.006816,0.004471,0.006596
0.065250,0.003331,0.005072,
0.070250,0.001711,0.004877,
0.075250,0.001275,0.003918,
0.080250,0.005881,0.002658,
0.085250,0.005054,0.005645,
0.090250,0.009921,0.005536,
0.095250,0.024123,0.005322,
0.100000,0.051889,0.005032,
{{< /chart >}}

完整 400 步时间曲线如下。左上/右上分别是 `native` 和 `off` 模式下两个求解器的
plate 最大位移；左下是求解器差值；右下是 plate 总力：

![time curves](/griffith-chorin/time_curves_plate.png)
<p class="tcaption">图 3. 400 步时间曲线：plate 最大位移、求解器差值和对板力。</p>

marker 最大速度和最大散度随时间的曲线：

![flow curves](/griffith-chorin/time_curves_flow.png)
<p class="tcaption">图 4. marker 最大速度和最大散度的时间曲线。</p>

原始数据下载：[native/Chorin history.csv](/griffith-chorin/native_chorin_history.csv)、[native/Griffith history.csv](/griffith-chorin/native_griffith_history.csv)、[off/Chorin history.csv](/griffith-chorin/off_chorin_history.csv)、[off/Griffith history.csv](/griffith-chorin/off_griffith_history.csv)、[差值采样 CSV](/griffith-chorin/time_diff_samples.csv)。

### 3.5 PyVista 三维视图

下面用 PyVista 查看最终时刻的 marker 构型：管壁 marker 连接成四边形网格，
隔板 marker 用球 glyph；颜色是相对参考构型的位移大小（mm）。
四个 panel 依次是 `native/Chorin`、`native/Griffith`、`off/Chorin`、`off/Griffith`：

![pyvista final](/griffith-chorin/pyvista_final_native_off.png)
<p class="tcaption">图 5. PyVista 最终 marker 构型；颜色为 |disp|。</p>

两个求解器逐 marker 的配对距离。`native` 模式的最大差约 0.41 mm，
`off` 模式约 0.005 mm，因此两个 panel 使用各自的颜色范围：

![pyvista diff](/griffith-chorin/pyvista_solver_difference.png)
<p class="tcaption">图 6. PyVista 配对 marker 距离；native（左）和 off（右）量级不同，颜色范围独立。</p>

### 3.6 最终时刻流场 VTI

demo 现在支持 `--vti`：在每次运行结束时写出最终时刻的 MAC 流场，
内部会转换为 VTI (VTK ImageData) PointData，包含 `velocity`、`pressure`、
`u`、`v`、`w`、`vorticity_mag`。可以直接在 ParaView 中打开，也可以用 PyVista 读取：

```bash
/path/to/tethered_tube_partition ... both --convection off --vti
```

本次上传的最终时刻 VTI：

- [native/Chorin final VTI](/griffith-chorin/native_chorin_final.vti)
- [native/Griffith final VTI](/griffith-chorin/native_griffith_final.vti)
- [off/Chorin final VTI](/griffith-chorin/off_chorin_final.vti)
- [off/Griffith final VTI](/griffith-chorin/off_griffith_final.vti)

下面是 PyVista 读取 VTI 后在 `z=0.5` 中截面上的速度大小和压力分布。
四个 panel 与 marker 图相同：`native/Chorin`、`native/Griffith`、`off/Chorin`、`off/Griffith`。
速度图和压力图各自使用统一颜色范围。

![flow speed slice](/griffith-chorin/pyvista_flow_speed_slice.png)
<p class="tcaption">图 7. 最终时刻 z=0.5 中截面速度大小 |u|；黑色短线为隔板参考位置。</p>

![flow pressure slice](/griffith-chorin/pyvista_flow_pressure_slice.png)
<p class="tcaption">图 8. 最终时刻 z=0.5 中截面压力 p；黑色短线为隔板参考位置。</p>

---

## 4. 怎么理解这组差异

可以把差异拆成两层：

### 4.1 求解器本身

`--convection off` 把对流项完全去掉，此时两边解的是同一个线性化问题：

- Chorin：投影分裂 + Helmholtz/Poisson 顺序求解；
- Griffith：鞍点块 `K=[A G; -D 0]` 联立。

结果：

```text
plate 差      ~ 0.40%
marker 差     ~ 0.005 mm
场量差        < 0.5%
```

所以，**耦合、分裂和压力幽灵处理本身带来的差别很小**。

### 4.2 对流离散

`native` 模式下：

- Chorin 用 `SecondUpwind`；
- Griffith 用 `XSPPM7`。

两种格式一个偏耗散、一个偏高阶重构/限幅，对无 drag、粗网格、带移动隔板的算例，
外区速度场会被不同地放大或抑制。因此：

```text
plate 差      2.61%
marker 最大差 0.406 mm
场量差        21%–67%
```

也就是说，**默认配置下的整体差异，主要来自对流离散，而不是两个求解器的压力-速度耦合。**

---

## 5. 为什么 XSPPM7 能算而 Central 会失稳

这其实是两个层面的事。

### 5.1 代码路径不同

在 `griffith_ns.h` 中：

```cpp
if (use_xsppm7_)
    return xsppm7::convection(stokes, f, reset_advection_velocity_);
```

XSPPM7 是一条独立路径，直接基于 `CoupledStokes` 的 active DOF 和
`points(a)`，自己构造 4 层 halo，自己处理 normal-traction 边界面。

而 `ConvectionAB2` fallback 只给 traction 边界补了一套**仅 Central 可用**
的扩展：

```cpp
if (stokes.has_normal_traction()) {
    if (conv_.scheme() != Central)
        throw std::invalid_argument("traction-face advection currently requires Central scheme");
}
```

所以：

- `SecondUpwind` 在 Griffith + traction 下直接不能起算；
- `Central` 能起算，但数值稳定性不足；
- `XSPPM7` 既可以起算，也能稳定跑完。

### 5.2 XSPPM7 带非线性耗散

`xsppm7.h` 的重构流程是：

```text
7 点 unlimited reconstruction
    ↓
monotonize
    ↓
WENO5 fallback
    ↓
按速度方向 upwind
```

这带来了：

- 光滑区高阶；
- 大梯度区自动退回有限体积意义下有界的分支；
- 少量但关键的迎风耗散；
- 对粗网格欠分辨剪切模态的抑制。

Central 则没有 limiter，只在 traction 面上做了一个中心差分扩展。当前算例：

- `N = 16`，网格较粗；
- 管壁和隔板是移动拉格朗日结构；
- 外区没有 explicit-cell drag；
- 压力差 100 mmHg。

这些条件叠加时，中心格式的未耗散模态逐步增长，最终让 marker 在
step 270–280 离开支持区。

---

## 6. 复现命令

关闭对流，只比较两个求解器本身：

```bash
./build/tethered_tube_partition \
  16 400 0.0033333333333333335 6400 \
  out_compare_off \
  12.577566273584907 1000 0 both --convection off
```

各自默认对流：

```bash
./build/tethered_tube_partition \
  16 400 0.0033333333333333335 6400 \
  out_compare_native \
  12.577566273584907 1000 0 both --convection native
```

统一中心格式：

```bash
./build/tethered_tube_partition \
  16 260 0.0033333333333333335 6400 \
  out_compare_central \
  12.577566273584907 1000 0 both --convection central
```

每个输出目录中都包含：

```text
out_compare_off/
├── chorin/status.txt
├── griffith/status.txt
├── comparison.csv
└── summary.txt
```

`summary.txt` 现在同时写出两个 solver 的场量 RMS，方便直接填对比表：

```text
velocity_u_chorin_rms
velocity_u_griffith_rms
velocity_v_chorin_rms
velocity_v_griffith_rms
velocity_w_chorin_rms
velocity_w_griffith_rms
pressure_chorin_centered_rms
pressure_griffith_centered_rms
```

---

## 7. 结论

| 目标 | 推荐模式 | 理由 |
|---|---|---|
| 比较两个求解器本身 | `--convection off` | 去掉对流差异后，plate/marker 差约 0.4%，场量差 < 0.5% |
| 跑参考物理算例 | `--convection native` | 保留两侧稳定对流格式，400 步完整稳定 |
| 统一低阶格式 | 不推荐 `--convection central` | 第 260 步前还能用，但 Griffith 约 t=0.068 s 失稳 |

一句话：

> **Chorin 和 Griffith 在耦合层面本身非常接近；默认输出差异主要是对流离散造成的。XSPPM7 能算，是因为它既有独立的 traction 边界实现，又有 limiter/迎风耗散来抑制粗网格不稳定模态。**
