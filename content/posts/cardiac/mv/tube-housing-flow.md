---
title: "管道与 housing disc 流动：压力、网格与端部间距对照"
description: "管道与 housing 的压力对照、27 组网格和端隙试验：管腔流量、旁路交换、变形、收敛性及复现方法。"
date: 2026-10-20
lastmod: 2026-10-22
layout: protected-paper
academic: true
comments: false
searchHidden: true
build:
  list: never
tags: ["Cardiac Simulation", "MV", "GPU", "FSI"]
url: /posts/tube-housing-flow/
---

**2026-10-22 更新：**第 8 节给出已完成的高压 5 s 长测及新增五级压差扫描；第 9 节汇总全部 27 组启动试验及管腔／端隙通量分析。数值完成不等于网格收敛或刚性验证。

第 1–5 节记录早期两组 **0.005 mmHg 恒定目标压差、计算至 5 s** 的 GPU 算例。两组仅相差原 R2 housing disc：纯管道保留管壁；tube+disc 保留管壁和 disc，均不含瓣叶、腱索及乳头肌。

**早期对照结果：**5 s 时，增加 disc 后出口流量由 **58.0 降至 27.9 mL/s**，最大轴向速度由 **2.07 升至 3.94 cm/s**。但 disc 已发生局部单元翻转，因此后一组只作为诊断结果，不能视为通过验证的刚性 disc 流动。

## 1. 共同设置

采用 cm–g–s 单位制，密度为 1 g/cm³。这里的 G64 表示流体网格数，不是空间步长。

| 参数 | 两组共同取值 |
|---|---|
| 计算域 | 8.6 × 8.6 × 16.09938 cm |
| 流体网格 | 64 × 64 × 96 |
| Δx、Δy；Δz | 0.134375 cm；0.167701875 cm |
| 名义管内半径；参考管长 | 3.5 cm；16 cm |
| 管轴位置 | x = y = 4.3 cm |
| 管壁参考端面 | z = 0.04969、16.04969 cm |
| 运动黏度 ν | 0.04 cm²/s |
| 目标压差 Δp | 0.005 mmHg = 6.6661 dyn/cm² |
| 压差升压时间 | **0.01 s**，线性从 0 增至目标值，之后保持不变 |
| dt；终止时间 | 5×10⁻⁴ s；5 s，共 10,000 步 |
| IB 核；固体耦合 | IB4；显式一阶更新，GPU 插值、力组装和铺展 |
| 固体作用力 | 仅参考位置 tethering，β = 10⁵ |
| 材料弹性应力、体积稳定项、固体黏性 | 均未启用 |
| 开口与其他处理 | z 两端圆形压力孔口；无额外 feedback、gap mask 或关闭期 clamp |
| 保存间隔 | 0.1 s |

升压函数为 $\Delta p(t)=0.005\min(t/0.01,1)$ mmHg，出口压力为零。**第 1–4 节图表来自早先的 0.01 s ramp、弱 tether 算例；第 6 节另列 0.2 s ramp、Sarah 应力和 2.085Δz 间距的完整结果。**

| 输入网格 | 纯管道 | tube+disc |
|---|---:|---:|
| 管壁 Q1 六面体 | 532,480 | 532,480 |
| disc P1 四面体 | 0 | 681,600 |
| 节点数 | 667,680 | 811,754 |
| 管壁参考体积（cm³） | 83.634183 | 83.634183 |
| disc 参考体积（cm³） | 0 | 5.411126 |

网格来自保留的 `glamv_hex_r2` 数据。保留各组件的原坐标、连接和积分数据，允许组件独立重叠，不焊接节点。disc 原标记 42 在此提取数据中映射为 2，仅用于 tether 分区。disc 外形不对称，因此显式固定计算域和参考中心，避免自动居中改变管轴位置。

### 1.1 实际边界条件

初始流体速度和固体位移均为零。计算域为长方体，两个压力开口位于 z=0 和 z=Lz；开口均为以 (4.3,4.3) cm 为中心、半径 3.5 cm 的圆形离散掩码。

| 位置 | 当前程序的处理 |
|---|---|
| 入口圆形开口 | 指定 $p_\mathrm{in}(t)=6.6661\min(t/t_r,1)$ dyn/cm²；不指定轴向流速或流量 |
| 出口圆形开口 | 指定 $p_\mathrm{out}=0$；允许法向流动 |
| 两个开口的切向速度 | 保留零 Dirichlet 设置，即 u=v=0 |
| 开口的法向速度 w | 由动量—压力投影步骤求解；动量步骤在孔口使用 Neumann 补丁，不把 w 覆盖为零 |
| z 端面上圆形开口以外的区域 | 静止无滑移壁面，u=v=w=0 |
| x、y 方向四个外侧面 | 静止无滑移壁面，u=v=w=0；不是周期边界 |
| 压力在封闭壁面上的处理 | 使用求解器的壁面压力／投影 Neumann 处理，不指定沿程压力分布 |
| 浸入式管壁与 disc | 位于流体网格内部，通过 IB 插值、固体力及力铺展近似实现耦合；不是另一个直接施加速度 Dirichlet 的网格边界 |

第 1–4 节使用 $t_r=0.01$ s，第 6 节使用 $t_r=0.2$ s。求解器保留默认的旧孔口模式；**未启用 `PhysicalOpen` 的切向自由牵引模式**。也未指定入口抛物线速度、孔口径向速度平滑、入口／出口 feedback、回流稳定项或关闭期 clamp。因此，中心速度、射流和流量都是计算结果，不是入口给定值。

上述设置对应 `demo/tube_flow_scale.cu` 中的 `set_bc_u/v/w(0)`、两个 `add_pressure_hole` 调用，以及 `src/ns_solver_cuda.h` 的默认孔口处理。接口中旧模式名为 `PrescribedVelocity`，但这不表示本算例预先指定了孔口轴向速度；代码在孔口保留动量解出的法向速度。

### 1.2 gap 如何影响速度

**本页 gap 指几何间距，不是 glamv 的 `gap-mask`／`gap-feedback` 区域。** 当前这些反馈接口没有启用，gap 本身不施加速度条件，也没有“gap 越大，给定速度越大”的控制律。

两端间距定义为

$$
g_\mathrm{in}=z_\mathrm{tube,min},\qquad
 g_\mathrm{out}=L_z-z_\mathrm{tube,max}.
$$

本页对称截取管端，所以两者均为 g。流体网格、计算域和 disc 不动，只移除完整的管壁端层，从而增大 g；圆形压力孔口的半径和位置也不变。

gap 通过以下两条路径间接改变速度：

1. **端部流动几何。** 管壁没有接到压力端面时，管腔与管外区域可经端缘绕行。增大 g 会改变入口／出口的局部流动、旁路空间和等效阻力；在同一外加压差下，流量和局部速度因此可能改变。管外区域仍在封闭计算域内，不能把绕流称为流体凭空流失。
2. **IB 边界附近的离散耦合。** IB4 的轴向支撑半宽约为 2Δz。管端过近时，插值和力铺展会涉及开口边界附近的 ghost 值和边界更新。增大距离可让更多支撑落在物理域内，改变强 tether／材料力的反馈效果；这可能改善稳定性，但不能仅凭结果断言近边界算子一定存在某种不一致。

因此，gap 是当前几何与离散方式下需要检查的参数，**不是独立的流速旋钮，也没有已证实的单调关系或通用最优值**。速度还取决于压差历史、黏度、disc 开口、固体作用力和瞬态惯性。

判断合适间距时，需要同时比较 J、位移、管端穿出、管腔沿程 $Q(z)=\int_Au_z\,\mathrm dA$ 和开口间隙的径向交换。仅入口、出口总流量相等，不能排除局部绕流；仅数值稳定，也不能证明边界设置物理准确。

## 2. 纯管道：5 s 截面

![纯管道的 XZ、YZ 纵截面：上行为轴向速度，下行为压力。](/data/tube-housing-20261020/tube/glamv_tube_longitudinal_t5.png)

上行为轴向速度，下行为压力；黑线表示实际变形后的管壁。轴向 z 向上。管内中心速度分布较平坦，压强沿程近似线性下降，尚未形成稳态抛物线速度分布。

![纯管道在入口附近、中部和出口附近的横截面。](/data/tube-housing-20261020/tube/glamv_tube_cross_sections_t5.png)

三个横截面分别位于 z = 0.100、8.050、15.999 cm。同一时刻的速度分布视觉上接近；这不是沿程流量一致性的定量检验。

## 3. 加入 housing disc：5 s 截面

![tube+disc 的 XZ、YZ 纵截面：开口后形成射流，但 disc 已发生单元翻转。](/data/tube-housing-20261020/tube-disc/glamv_tube_longitudinal_t5.png)

开口后出现射流和周围回流，压强场不再接近纯管道的线性分布。由于 disc 网格已翻转，这些现象可用于定位问题，尚不能作为可信的定量预测。

![tube+disc 的横截面，z=4.500 cm 的截面穿过 disc。](/data/tube-housing-20261020/tube-disc/glamv_tube_cross_sections_t5.png)

z = 4.500 cm 的截面穿过 disc；z = 8.050 cm 展示下游非均匀射流。每组图内部使用统一色标，**两组之间的色标范围不同**，不能只按颜色比较速度。压力单位均为 mmHg。Eulerian 场也定义在 IB 固体所在区域，黑线仅标示边界，没有将固体内部数值遮掉。

## 4. 流量与网格检查

![tube+disc 的入口和出口流量、纯管道出口流量，以及 tube+disc 中部中心线速度。](/data/tube-housing-20261020/tube-disc/glamv_tube_history_t5.png)

流量按计算域两端的压力孔口积分；入口曲线取流入方向为正。两端曲线在图中重合，不足以单独证明管壁无数值渗漏。两组流量在 5 s 时都仍在增长，不能与稳态泊肃叶解直接比较。

| 5 s 指标 | 纯管道 | tube+disc |
|---|---:|---:|
| 出口流量（mL/s） | 57.9755 | 27.9114 |
| 中部轴线上轴向速度（cm/s） | 2.06775 | 3.92393 |
| 全场最大轴向速度（cm/s） | 2.06899 | 3.94473 |
| 进程是否正常结束 | 是 | 是 |

$Q=\int_A u_z\,\mathrm dA$。在相同外加压差下，局部开口可能使流量减小而射流速度增大；本例呈现这一趋势，但网格缺陷限制了其定量解释。

以 $J=\det F$ 检查局部体积变化：J=1 表示体积不变，J≤0 表示单元翻转。下表由 **5 s 保存帧的全部有效积分点**重建；最大位移是节点到参考位置的欧氏距离。

| 网格区域 | 最小 J | 最大 J | J≤0 积分点数 | 最大位移（mm） |
|---|---:|---:|---:|---:|
| 纯管道的管壁 | 0.8253 | 1.2034 | 0 | 0.1788 |
| tube+disc 的管壁 | 0.8274 | 1.1728 | 0 | 0.1252 |
| tube+disc 的 disc | −36.4776 | 38.9169 | 3,523 | 1.9083 |

disc 为 P1 四面体，每个单元只有一个有效积分点，因此 3,523 个非正积分点对应 3,523 个翻转单元。补查 2.2 s 帧时已有 139 个翻转单元，不能把 5 s 正常退出当作网格稳定的证据。纯管道的最终帧没有翻转，但也不能据此证明全过程无翻转、完全刚性或空间收敛。

## 5. Git commit 与复现命令

| 仓库 | 本页复现所用 commit |
|---|---|
| 工作区与辅助脚本 | [`8d62fddae5d8ceab8c34cfdc3890261c0fe52419`](https://github.com/mapengfei-glasgow/fdm-3d-v1-workspace/commit/8d62fddae5d8ceab8c34cfdc3890261c0fe52419) |
| GPU 求解器 | [`f096f922fd5ef2bbd8c6be6c3f9673d504c78b8a`](https://github.com/mapengfei-glasgow/fdm-3d-v1-gpu/commit/f096f922fd5ef2bbd8c6be6c3f9673d504c78b8a) |
| CPU 头文件依赖 | `2868a7a9463693880e7e7b6552cd6d512261a5ca` |
| geometry 仓库 | `20ac3992f7fdd198b9595486dba25da43bd1393e` |

**输入前提：**已有原始 `fdm-3d-v1-geometry/src/ibm/data/glamv_hex_r2/` 数据。该目录是生成数据，不由上述 commit 单独恢复。本页只发布图文、commit 和命令，不提供网格、探针文件或结果压缩包。

### 5.1 检出与网格提取

在独立目录中执行，避免覆盖已有计算。CUDA、兼容的 C++ 编译器、CMake、HDF5 等依赖应已安装。

```bash
git clone --branch research/pipe-end-boundaries-20261019 \
  https://github.com/mapengfei-glasgow/fdm-3d-v1-workspace.git tube-workspace
cd tube-workspace
git checkout 8d62fddae5d8ceab8c34cfdc3890261c0fe52419
git submodule update --init --recursive

# 将保留的原始 glamv_hex_r2 数据放入 geometry 仓库对应目录后：
mkdir -p runs/glamv_tube_only_20261019
OPENBLAS_NUM_THREADS=1 python3 scripts/simulations/prepare_glamv_tube_only.py
OPENBLAS_NUM_THREADS=1 python3 scripts/simulations/prepare_glamv_tube_housing.py
```

两个提取脚本拒绝覆盖已有输出。分别生成 `runs/glamv_tube_only_20261019/tube_R2_Q1/` 和 `runs/glamv_tube_housing_20261020/mesh/`。输出目录内的 `VALIDATION.json` 记录单元数、体积和参考映射检查。

### 5.2 构建与运行

```bash
cmake -S fdm-3d-v1-gpu -B build-tube \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_CUDA_ARCHITECTURES=native \
  -DFDM3D_GPU_FMAD=ON
cmake --build build-tube --target tube_flow_scale -j2

export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=2 DSH_PERF_LEVEL=0
mkdir -p runs/reproduce_20261020

# Bash 数组：两组共同参数。输出目录须为新目录。
common=(--gpu-coupling --N 64 --nx 64 --ny 64 --nz 96
  --domain 8.6,8.6,16.09938 --reference-center 0,0,0
  --rin 3.5 --nu 0.04 --pmax 6.6661 --ramp 0.01
  --T 5 --dt 0.0005 --beta-body 1e5 --mu 0 --lambda 0
  --every 200 --probe-every 200)

./build-tube/tube_flow_scale "${common[@]}" \
  --data runs/glamv_tube_only_20261019/tube_R2_Q1/ \
  --out runs/reproduce_20261020/tube/

./build-tube/tube_flow_scale "${common[@]}" \
  --data runs/glamv_tube_housing_20261020/mesh/ \
  --out runs/reproduce_20261020/tube-disc/
```

共同参数显式固定计算域与参考中心；纯管道也使用这一等价设置。该 commit 包含后续可选 Sarah 应力和 J 惩罚接口，但以上命令**均未启用**，对应本页的纯 tethering 对照。不同 GPU、编译器及原子累加顺序可能带来舍入差异。

### 5.3 绘图

先检查 disc 的最终网格，并保存绘图警示所需的审计记录：

```bash
python3 - <<'PYCODE'
from pathlib import Path
import json
from scripts.diagnostics.audit_tube_housing_final import evaluate
result = evaluate("runs/reproduce_20261020/tube-disc",
                  "runs/glamv_tube_housing_20261020/mesh", 10000, 0.0005)
Path("runs/reproduce_20261020/FINAL_GEOMETRY_AUDIT.json").write_text(
    json.dumps(result, indent=2))
print(json.dumps(result, indent=2))
PYCODE
```

安装 NumPy、PyVista、VTK 和 Matplotlib 后，在同一工作区执行：

```bash
export PYVISTA_OFF_SCREEN=true

python3 scripts/visualization/plot_glamv_tube_lowpressure_gpu.py \
  --run "$PWD/runs/reproduce_20261020/tube" \
  --out "$PWD/exports/reproduce_tube/sections"

python3 scripts/visualization/plot_glamv_tube_lowpressure_gpu.py \
  --run "$PWD/runs/reproduce_20261020/tube-disc" \
  --out "$PWD/exports/reproduce_tube_disc/sections" \
  --mesh-data "$PWD/runs/glamv_tube_housing_20261020/mesh" \
  --tube-reference "$PWD/runs/reproduce_20261020/tube"
```

绘图脚本读取 5 s 的 `fluid_010000.vti` 与 `Xc_010000.bin`；几何检查使用 `scripts/diagnostics/audit_tube_housing_final.py` 中的 `evaluate(run, mesh, step, dt)`。图片只能辅助观察，应以 J 和位移检查判断网格是否仍有效。

本页的用途是建立可检查的 tube/tube+disc 对照，并记录当前离散方法的限制。后续参数测试不替代这里的原始结果。

## 6. Sarah 应力与 2.085Δz 间距：完整 5 s 结果

**2026-10-21 更新：**这一组完整运行到 5 s，耗时 **9 小时 38 分钟**，通过保存帧的网格检查。管壁和 housing 均使用原 Sarah 的 modified Neo-Hookean 型应力、体积项及 tether。它与第 1–4 节同时改变了应力、tether、dt、ramp 和管端位置，因此不能把差异全部归因于间距。

### 6.1 管端到底离边界多少 Δz

此处的间距指**参考管端平面到相邻计算域边界的轴向距离**，不是管壁厚度。

$$
\Delta z=\frac{16.09938}{96}=0.167701875\ \mathrm{cm},\qquad
 g=0.34969\ \mathrm{cm}=3.4969\ \mathrm{mm}
 =\mathbf{2.085188\,\Delta z}.
$$

| 参数 | 此次完整算例 |
|---|---|
| 流体网格、计算域、ν、目标压差 | 与第 1 节相同：G64，ν=0.04 cm²/s，Δp=0.005 mmHg |
| 管壁参考端面 | z=0.34969、15.74969 cm |
| 两端各自的间距 | **2.085188Δz = 3.4969 mm** |
| 参考管长 | 15.4 cm，原管长 16 cm |
| 网格构造 | 两端各截去 3 mm 的完整原网格层；不缩放保留单元，不改变 disc |
| 管壁／disc 单元数 | 512,512 个 Q1 六面体／681,600 个 P1 四面体 |
| 管壁与 disc 的材料项 | modified 模式，C10=502 dyn/cm² |
| 体积应力 | $P_\mathrm{vol}=2\beta_s\ln J\,F^{-T}$，βs=5×10⁶ dyn/cm² |
| 两者的 tether 系数 | 均为 5×10⁸ |
| 时间步长、步数 | 1×10⁻⁵ s，500,000 步 |
| 压差升压时间 | **0.2 s**，之后保持目标压差 |
| IB 核、耦合、固体黏性 | IB4、一阶显式、无固体黏性；无 J 截断 |

增大间距同时缩短了管道，并改变了开口端的旁路空间。这是一组边界诊断结果，不能直接当作最佳或通用的间距设置。

### 6.2 截面和流量

![Sarah 应力、管端间距 2.085Δz 的 5 s 纵截面。](/data/tube-housing-20261020/sarah-gap2p085/glamv_tube_longitudinal_t5.png)

黑线为实际变形后的管壁和 disc。压力图使用全场范围，约 −0.183～0.399 mmHg，包含 IB 固体／界面附近的数值，**并非外加压差**；外加压差仍为 0.005 mmHg。局部压力峰值尚未完成空间收敛核查，不据此判断生理意义。

![Sarah 应力、管端间距 2.085Δz 的 5 s 横截面。](/data/tube-housing-20261020/sarah-gap2p085/glamv_tube_cross_sections_t5.png)

此图 z=0.100 和 15.999 cm 的两个截面**位于管端与计算域边界之间的间隙内**；z=4.500 cm 穿过 disc，z=8.050 cm 位于下游。

![2.085Δz 算例的入口／出口流量与中部中心线速度。](/data/tube-housing-20261020/sarah-gap2p085/glamv_tube_history_t5.png)

5 s 时出口流量为 **24.8276 mL/s**，中部中心线轴向速度为 **3.88496 cm/s**。该流动仍在发展，未建立稳态或空间收敛结论。

### 6.3 网格与间隙通量检查

| 5 s 指标 | 管壁 | disc |
|---|---:|---:|
| 最小 J | 0.999547 | 0.946104 |
| 最大 J | 1.000441 | 1.070506 |
| 非正 J 积分点 | 0 | 0 |
| 最大节点位移（μm） | 1.687 | 49.573 |
| 管壁节点穿出轴向计算域 | 0 | — |

每 0.1 s 保存帧的检查未发现翻转或管壁穿出；这不保证未保存时刻也满足相同条件，也不等于已证明严格刚性或无渗漏。

在名义半径 r=3.5 cm 上，对 5 s 的 VTI 平均速度作插值与积分，管腔五个截面流量约为 **24.809～24.814 mL/s**。两端开口间隙的径向通量估计如下；“向外”指从名义管腔进入管外区域，仍在计算域内。

| 间隙 | 向外通量（mL/s） | 向内通量绝对值（mL/s） |
|---|---:|---:|
| 入口端 | 4.88×10⁻⁵ | 4.66×10⁻⁵ |
| 出口端 | 5.38×10⁻⁵ | 4.69×10⁻⁵ |

该采样下径向交换很小，但它使用平均后的 Eulerian 场和名义圆柱，**不是原生 MAC 守恒通量，也不是穿过实际固体表面的泄漏测量**。仅约两层轴向网格的间隙仍需分辨率检查，不能据此宣称完全没有绕流。

### 6.4 Git commit 与复现命令

本节的网格截取、监控及绘图脚本提交为 [`9be5b150e146239d1c43f1e63b2d64e74d50fe7a`](https://github.com/mapengfei-glasgow/fdm-3d-v1-workspace/commit/9be5b150e146239d1c43f1e63b2d64e74d50fe7a)，GPU 源码仍为第 5 节的 `f096f92`。在已具备原始 R2 数据的独立工作区检出该提交并更新子模块，按第 5.2 节构建，然后执行：

```bash
git fetch origin research/pipe-end-boundaries-20261019
git checkout 9be5b150e146239d1c43f1e63b2d64e74d50fe7a
git submodule update --init --recursive

OPENBLAS_NUM_THREADS=1 python3 scripts/simulations/prepare_glamv_tube_housing.py \
  --tube-z-limit 7.71428625 \
  --out "$PWD/runs/reproduce_sarah_gap2p085/mesh"

export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=2 DSH_PERF_LEVEL=0
./build-tube/tube_flow_scale --gpu-coupling --sarah-wall-stress \
  --N 64 --nx 64 --ny 64 --nz 96 \
  --domain 8.6,8.6,16.09938 --reference-center 0,0,0 \
  --rin 3.5 --nu 0.04 --pmax 6.6661 --ramp 0.2 \
  --T 5 --dt 1e-5 --beta-body 5e8 --beta-disk 5e8 \
  --disk-bulk 0 --mu 0 --lambda 0 \
  --data runs/reproduce_sarah_gap2p085/mesh/ \
  --every 10000 --probe-every 10000 \
  --out runs/reproduce_sarah_gap2p085/case/
```

这里 `--mu 0 --lambda 0` 是未使用的旧 SFRH 参数；`--sarah-wall-stress` 实际启用上述 C10 和 βs，不是零材料应力。没有额外的 disk-only 体积项，以免与 Sarah 体积项重复。

```bash
PYVISTA_OFF_SCREEN=true python3 scripts/visualization/plot_glamv_tube_lowpressure_gpu.py \
  --run "$PWD/runs/reproduce_sarah_gap2p085/case" \
  --mesh-data "$PWD/runs/reproduce_sarah_gap2p085/mesh" \
  --step 500000 --label 'Tube + housing | gap = 2.085 dz' --no-reference \
  --out "$PWD/exports/reproduce_sarah_gap2p085/sections"
```

更小间距的扫描安排在这组 5 s 长测完成后顺序启动，并非与长测同时运行。扫描用于比较间距的稳定性与绕流影响；尚不能从单个 2.085Δz 结果确定经验最优值。

## 7. 间距扫描复核：为什么“最后一帧没翻转”还不够

五组短测均使用 G64、Sarah modified 管壁与 disc、两者 tether=5×10⁸、dt=10⁻⁵ s、0.2 s 升压；只改变截去的管壁端层，目标时间为 0.3 s。

![管端间距扫描：管壁位移、局部体积失真和 0.3 s 出口流量。](/data/tube-housing-20261020/clearance-sweep/clearance_audit.png)

**左图：管壁最大位移，纵轴为对数，单位 μm。** 0.893Δz 组的位移在 0.1–0.25 s 内近似每 0.05 s 增加十倍，最大位移位于入口管端；它在 0.25 s 尚有限，但 0.30 s 的速度、压力已全部非有限。其最后一个有限点不代表通过测试。0.594Δz 组的首个非零保存帧（0.05 s）已经失稳，没有可画的有限非零点，因此不出现在曲线中。

**中图：管壁最大 $|J-1|$，纵轴同样为对数。** 蓝线的体积误差持续快速增长，其他三组在这段时间内维持较小偏差。它反映局部体积变化，不是总位移，也不是全时间稳定性证明。

**右图：通过短测的三组在同一时刻 0.3 s 的出口流量。** 纵轴刻意放大到 1.923–1.931 mL/s，未从零开始；三组实际差异仅约 **0.15%**，不能按图上点的高度差理解为流量相差数倍。

| 实际间距 | 间距（mm） | 0.3 s 管壁 J | 最大管壁位移（μm） | 出口流量（mL/s） |
|---|---:|---|---:|---:|
| 1.190744Δz | 1.9969 | 0.999964–1.000036 | 0.08952 | 1.925185 |
| 1.488892Δz | 2.4969 | 0.999945–1.000055 | 0.08341 | 1.927615 |
| 1.787040Δz | 2.9969 | 0.999966–1.000034 | 0.07596 | 1.928081 |

另外两组的首次非有限时刻仅能定位于 **(0,0.05] s**（0.594Δz）和 **(0.25,0.30] s**（0.893Δz），没有保存精确的首次失稳步。

复核采用独立的当前／参考几何映射行列式比重算 J，没有使用原审计的 `qp_grad`，与原极值差小于 1.4×10⁻¹³。三组通过算例的 disc 也保持相近：J 约 0.99805–1.00146，最大位移约 1.123 μm。

### 7.1 稳定性和绕流分别判断

在已测点中，**1.191Δz 是最小短程通过间距**，尚未验证到 5 s，不能称为精确稳定阈值或最优间距。

0.3 s 时，将每端名义间隙圆柱面上的“向外通量＋向内通量绝对值”作为总交换估计，避免正负抵消；取两端较大值，分别约占出口流量的 **0.00130%、0.00310%、0.00560%**。该估计随上述间距增大，但均较小。

这些数值**不是实际泄漏率**。它们基于平均后的 VTI 速度、名义 r=3.5 cm 圆柱和插值积分；同一数据的管腔平均通量比原生孔口通量低约 **0.65%–0.77%**，说明两种离散通量还存在需要核查的差别。因此只能说“此采样未见明显的间隙交换”，不能据此证明无旁路或无穿固体渗漏。

后续应将 1.191Δz 延长到 5 s，与第 6 节已经完成的 2.085Δz 在同一时刻比较。图中三组通过结果仅覆盖升压结束后的 0.1 s。

### 7.2 图的复现

绘图脚本提交：[`06c58a4411dc78df47210b044e8eb0047a2bc4ed`](https://github.com/mapengfei-glasgow/fdm-3d-v1-workspace/commit/06c58a4411dc78df47210b044e8eb0047a2bc4ed)。已有扫描目录的 `SUMMARY.json` 和各组 `AUDIT_*.json` 时，执行：

```bash
OPENBLAS_NUM_THREADS=1 python3 scripts/visualization/plot_tube_clearance_audit.py \
  --runs "$PWD/runs/tube_clearance_sweep_20261021" \
  --out "$PWD/exports/tube_clearance_inspection_20261021/clearance_audit.png"
```

## 8. 将入口—出口压差提高十倍，保持 0.2 s ramp

本节给出十倍压差的设置；已获得的短测及进行中的长测结果见第 8.1 节。出口仍为零，只将入口目标压差由 0.005 提高到 **0.05 mmHg**：

| 参数 | 原设置 | 十倍压差 |
|---|---:|---:|
| 目标 Δp（mmHg） | 0.005 | **0.05** |
| 程序 `--pmax`（dyn/cm²） | 6.6661 | **66.661** |
| 出口压力 | 0 | 0 |
| `--ramp`（s） | 0.2 | **0.2** |

$$
p_\mathrm{in}(t)=66.661\min(t/0.2,1)\ \mathrm{dyn/cm^2},
\qquad p_\mathrm{out}=0.
$$

升压的**持续时间和归一化形状不变**；绝对升压速率必然增加十倍，从 0.025 变为 0.25 mmHg/s。这里不是将 ramp 延长到 2 s。

先沿用已通过 5 s 检查的 **2.085Δz 几何**，仅修改压差，避免同时改变间距。以下命令给出到 0.3 s 的短程检查；其余物理和耦合参数与第 6 节一致，输出使用新目录：

```bash
mkdir -p runs/reproduce_sarah_gap2p085_dp0p05
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=2 DSH_PERF_LEVEL=0
./build-tube/tube_flow_scale --gpu-coupling --sarah-wall-stress \
  --N 64 --nx 64 --ny 64 --nz 96 \
  --domain 8.6,8.6,16.09938 --reference-center 0,0,0 \
  --rin 3.5 --nu 0.04 --pmax 66.661 --ramp 0.2 \
  --T 0.3 --dt 1e-5 --beta-body 5e8 --beta-disk 5e8 \
  --disk-bulk 0 --mu 0 --lambda 0 \
  --data runs/reproduce_sarah_gap2p085/mesh/ \
  --every 1000 --probe-every 1000 \
  --out runs/reproduce_sarah_gap2p085_dp0p05/case/
```

这里给出的是求解器调用，不带自动监控。应结合第 6 节的 J、位移、管端穿出和非有限值检查判断是否通过；若要继续到 5 s，需要新输出目录并从静止重跑，不能把短测当作重启文件。

低压设置通过不保证十倍压力仍稳定。升压后也不能预期流量或射流速度严格增加十倍：本例仍是带 disc 的瞬态流动，存在惯性、局部损失和流固耦合。若不稳定，应先定位失败，再单独检查 dt 等参数；保持所要求的 0.2 s ramp。


### 8.1 高压长测最终结果（2026-10-22）

G64/R2、每端 gap=0.34969 cm（2.085Δz），dt=10⁻⁵ s，ramp=0.2 s；其余材料、IB4 和 tether 系数与第 6 节相同。0.3 s 筛查后从静止重跑，现已完成 **5 s**，耗时约 **9 小时 39 分钟**。下图覆盖全部已保存时刻。

![完成至 5 s 的高压长测：原生孔口流量、管壁和 housing 的 J 范围及最大节点位移。](/data/tube-housing-20261020/factorial/highpressure_history.png)

| 5 s 指标 | 管壁 | housing |
|---|---:|---:|
| 最小 J | 0.982157 | 0.707443 |
| 最大 J | 1.011313 | 1.447137 |
| 最大节点位移（μm） | 18.722899 | 321.699057 |
| 非正 J 积分点 | 0 | 0 |

5 s 原生出口流量为 **72.86905 mL/s**，名义管腔五截面的平均流量为 **72.70109 mL/s**。每 0.1 s 保存帧中均未检测到非正 J 或管壁穿出；这不是对每个时间步的连续证明。全保存历史中，管壁 J 包络为 **0.979960–1.012974**，housing 为 **0.702554–1.459632**；这些历史包络与上表的最终帧不同。

housing 最终最大位移为 **0.322 mm**，局部 J 对应体积减少约 **29.3%** 或增加约 **44.7%**；极值不一定在同一位置。这组算例数值上完成，但 **housing 的近刚性／局部保体积要求尚未满足**。J 极值与最大位移是分量的全局极值，不是同一材料点的轨迹。

复现这组 5 s 长测时，沿用第 8 节命令，将 `--T` 改为 `5`、`--every` 与 `--probe-every` 改为 `10000`，并指定新的空输出目录；`--dt 1e-5` 和 `--pmax 66.661` 保持不变。网格仍为第 6 节的 2.085Δz 几何。

### 8.2 十倍压差没有产生十倍的 5 s 流量

![相同几何和时间步下，两种压差的出口流量，以及高压／低压流量比。](/data/tube-housing-20261020/factorial/pressure_comparison.png)

| 指标（5 s） | 0.005 mmHg | 0.05 mmHg |
|---|---:|---:|
| 原生出口流量（mL/s） | 24.82761 | 72.86905 |
| housing J 范围 | 0.946104–1.070506 | 0.707443–1.447137 |
| housing 最大位移（μm） | 49.573 | 321.699 |

早期流量比接近 10，5 s 时已降至 **2.935**。高压流量在保存的 2.7 s 帧达到 **90.44095 mL/s**，随后回落至 72.86905；不能解释为已达到稳态。惯性、局部流动损失和固体变形均可能参与这种非线性响应；当前对照不能将变化单独归因于某一机制。

高压 5 s 的每端名义间隙圆柱总交换（向外＋向内绝对值）取两端较大值，约为管腔流量的 **0.01675%**；低压对应值为 **0.000406%**。这是插值采样诊断，不是真实固体表面的泄漏率。小间隙交换也不能抵消 housing 内部明显的局部体积失真。

### 8.3 固定 G64/R2 配置的五级压差长测（已启动）

**2026-10-22 状态快照：**用户指定压差序列 **0.05 → 0.1 → 0.2 → 0.5 → 1 mmHg**，每组目标为 **5 s**。0.05 mmHg 采用第 8.1 节已完成的对照；新增四组在四个空闲 GPU 上并行、独立从静止开始，不从前一压力组的状态续算。本小节不是实时进度页。

本轮固定为已完成两种压力 5 s 长测的 **G64/R2、每端 gap=0.34969 cm（2.085188Δz）**，不是第 9 节的三个间距，也不将 0.3 s 短测直接当成长期验证。

| 固定项目 | 设置 |
|---|---|
| 流体网格／域 | 64×64×96；8.6×8.6×16.09938 cm |
| 固体 | R2；Q1 管壁、P1 housing；保留 components 重叠 |
| 管壁端点／每端间隙 | 参考 z=±7.7 cm；gap=0.34969 cm |
| 本构 | Sarah modified NH；C10=502 dyn/cm²、βs=5×10⁶ dyn/cm² |
| 管壁／housing tether | 均为 5×10⁸ |
| 固体黏性／J 截断／额外 disk bulk | 0／不启用／0 |
| 流体运动黏度 | 0.04 cm²/s |
| IB 核／时间耦合 | IB4／Euler |
| dt／目标时长 | 10⁻⁵ s／5 s，即 500000 步 |
| 压力 ramp／出口压力 | 0.2 s 线性 ramp／0 |
| 保存与几何审计间隔 | 0.1 s，即每 10000 步 |

入口压力为

$$
p_mathrm{in}(t)=1333.22,Delta p_mathrm{target}min(t/0.2,1)quadmathrm{dyn/cm^2},
$$

其中目标压差以 mmHg 输入。每一级都保留 0.2 s 的升压时间，因此更高目标压差具有更大的绝对升压速率。

| 目标压差（mmHg） | `--pmax`（dyn/cm²） | 目标时间（s） | 本次记录状态 | 已完成的 5 s 孔口 Q（mL/s） |
|---|---:|---:|---|---:|
| 0.05 | 66.661 | 5 | 已完成对照 | 72.86905 |
| 0.1 | 133.322 | 5 | euclid-29：已启动 | — |
| 0.2 | 266.644 | 5 | euclid-30：已启动 | — |
| 0.5 | 666.610 | 5 | 8383 GPU 0：已启动 | — |
| 1 | 1333.220 | 5 | 8383 GPU 1：已启动 | — |

破折号表示结果尚未获得，不能按目标压差对 0.05 mmHg 结果作线性或平方律填表。两处远程网格的 **21 个输入二进制文件 SHA256 均与 0.05 mmHg 原始对照一致**；实际命令中，除压差、输入目录和输出目录外的选项均与对照相同。A6000 和 RTX4090 分别使用此前已做短程核对的架构对应构建，记录实际二进制哈希；不同硬件的浮点差异仍可能影响非定常细节。

**5 s 是目标，不是保证通过。** 监控遇到非有限流体／几何值、任一区域采样 J≤0.1、管壁节点穿出轴向域或磁盘不足时停止该组，保留失败原因与最后有限审计时间；不会自动改变 dt、本构或 tether 来把失败组混入同一控制试验。J>0 或位移低于监控阈值都不等于已满足刚性和保体积要求；已有 0.05 mmHg 对照的 housing 最终 J=0.707443–1.447137 已表明这一限制。

每组结束后，应分别比较原生孔口流量、名义管腔流量、每端径向交换、管壁／housing 的 J 历史包络与位移。高压下能否达到 600 mL/s 或 200 cm/s 仍是待测结果，不预先承诺。

运行、网格截取与状态收集脚本提交：[`55f35bd76ecd2a9d80f48b9b90fffa6c7dadf276`](https://github.com/mapengfei-glasgow/fdm-3d-v1-workspace/commit/55f35bd76ecd2a9d80f48b9b90fffa6c7dadf276)。原始生成网格并不随 Git 提交分发。

直接复现单个 0.1 mmHg 案例可使用下列命令；网格准备与求解器构建沿用第 6 节。更换 `--pmax` 为表中数值，并为每组使用独立的空输出目录。

```bash
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=2 DSH_PERF_LEVEL=0
./build-tube/tube_flow_scale --gpu-coupling --sarah-wall-stress \
  --N 64 --nx 64 --ny 64 --nz 96 \
  --domain 8.6,8.6,16.09938 --reference-center 0,0,0 \
  --rin 3.5 --nu 0.04 --pmax 133.322 --ramp 0.2 \
  --T 5 --dt 1e-5 --beta-body 5e8 --beta-disk 5e8 \
  --disk-bulk 0 --mu 0 --lambda 0 \
  --data runs/reproduce_sarah_gap2p085/mesh/ \
  --every 10000 --probe-every 10000 \
  --out runs/reproduce_dp0p1mmHg/case/
```

上面是直接求解器调用，不包含自动停止监控；本次实际运行由提交中的 `run_pressure_sweep_case.py` 和 `queue_housing_stability.py` 执行监控。已有本次部署记录时，可收集小型状态摘要：

```bash
python3 scripts/diagnostics/collect_pressure_sweep_status.py
```

## 9. 流体网格 × 固体网格 × 管端间距：27 组最终结果

**2026-10-22：全部队列结束。23 组完成至 0.3 s，4 组因非有限几何停止。** 本节是启动阶段的空间分辨率筛查，不是 5 s 长期验证。

### 9.1 试验设计与控制变量

流体网格为 G64=64×64×96、G128=128×128×192、G256=256×256×384，计算域均为 8.6×8.6×16.09938 cm。固体 R0/R1/R2 均保留 Q1 管壁和 P1 housing；不同 components 的重叠不合并。

三种物理间距在各网格上相同：保留参考管壁范围 z=±8、±7.8、±7.6 cm，沿各 R 层级共有的完整轴向层切除。固定物理间距可以避免比较 G 时又同时移动管端，但切端同时缩短管道，所以**管长和间距影响未被独立分离**；不同 R 层级对曲面的离散也并非完全一致。

| 每端 gap（cm） | G64：gap/Δz | G128：gap/Δz | G256：gap/Δz |
|---|---:|---:|---:|
| 0.04969 | 0.296 | 0.593 | 1.185 |
| 0.24969 | 1.489 | 2.978 | 5.956 |
| 0.44969 | 2.681 | 5.363 | 10.726 |

所有算例从静止开始：压差 0.05 mmHg，线性 ramp=0.2 s，ν=0.04 cm²/s，dt=5×10⁻⁶ s，目标 T=0.3 s；IB4、Sarah modified 应力 C10=502、βs=5×10⁶，两区域 tether=5×10⁸，无固体黏性。每 0.05 s 审计；非有限值、J≤0.1 或管壁穿出轴向域触发停止。本节与第 8 节的间距、dt 和时长不同。

![全部 27 组最终状态；绿色为完成至 0.3 s，红色为失败；数值是原生孔口流量。](/data/tube-housing-20261020/factorial/factorial_progress.png)

| 失败算例 | 每端 gap（cm） | 最后有限审计时间（s） |
|---|---:|---:|
| G64/R1 | 0.04969 | 0.00 |
| G64/R2 | 0.04969 | 0.00 |
| G128/R1 | 0.04969 | 0.20 |
| G128/R2 | 0.04969 | 0.00 |

失败均集中于最小物理间距，但这并不能证明任意较大间距都能长期稳定。“最后有限审计时间=0”只表示初始状态有限，随后非零保存帧失败，**不是 t=0 就发生失稳**。没有逐步保存首次失败时刻。固体更细而失败、R0 却能完成，说明“能完成”不能单独评价耦合精度；也仍需时间步对照才能定位失稳机制。

### 9.2 区分孔口流量、管腔流量与端隙交换

定义名义管腔流量为 r≤3.5 cm 圆盘的轴向速度积分，取五个轴向截面平均，记为 $Q_\mathrm{lumen}$。截面位置为管端内半个 Δz、域长的 1/4、1/2、3/4 和另一管端内半个 Δz。原生边界孔口流量记为 $Q_\mathrm{boundary}$。

对每端 gap 区间的名义 r=3.5 cm 圆柱面，分别积算向外和向内绝对通量。以下交换指标取两端较大值，**不相加两端，以免将同一旁路重复计数**：

$$
E_\mathrm{gap}=100\frac{\max_{\mathrm{in,out}}\left(Q_\mathrm{radial}^{+}+|Q_\mathrm{radial}^{-}|\right)}{Q_\mathrm{lumen}}\%.
$$

正方向为离开名义管腔、进入域内管外区域。该指标是总交换而不是有符号净交换，也**不是入口流量中绕流的精确百分比或穿真实固体表面的泄漏率**。

![实线为平均采样管腔流量，虚线为原生孔口流量；失败算例不连线补值。](/data/tube-housing-20261020/factorial/flow_resolution.png)

![各组端隙总交换与管腔流量之比；颜色采用对数刻度。](/data/tube-housing-20261020/factorial/gap_exchange.png)

| 流体／固体 | gap（cm） | 孔口 Q（mL/s） | 管腔 Q（mL/s） | 端隙交换／管腔 Q（%） |
|---|---:|---:|---:|---:|
| G64/R0 | 0.04969 | 21.45980 | 21.07089 | 0.40522 |
| G128/R0 | 0.04969 | 37.17516 | 28.09698 | 0.26391 |
| G256/R0 | 0.04969 | 48.08971 | 35.05218 | 1.06232 |
| G256/R1 | 0.04969 | 33.91301 | 27.12415 | 0.29515 |
| G256/R2 | 0.04969 | 23.64118 | 23.54869 | 0.01682 |
| G64/R0 | 0.24969 | 25.64667 | 21.07696 | 3.82479 |
| G64/R1 | 0.24969 | 19.58679 | 19.44431 | 0.00263 |
| G64/R2 | 0.24969 | 19.26448 | 19.11648 | 0.00315 |
| G128/R0 | 0.24969 | 39.26500 | 26.75974 | 16.92030 |
| G128/R1 | 0.24969 | 31.96740 | 22.64690 | 28.30553 |
| G128/R2 | 0.24969 | 27.45844 | 21.94122 | 11.37738 |
| G256/R0 | 0.24969 | 48.53655 | 33.02807 | 17.43822 |
| G256/R1 | 0.24969 | 38.51907 | 25.90662 | 31.98539 |
| G256/R2 | 0.24969 | 34.57343 | 23.47260 | 43.28746 |
| G64/R0 | 0.44969 | 33.06961 | 21.03731 | 32.00185 |
| G64/R1 | 0.44969 | 29.23071 | 19.44182 | 22.32377 |
| G64/R2 | 0.44969 | 28.36990 | 19.11396 | 21.37831 |
| G128/R0 | 0.44969 | 40.97819 | 25.83225 | 37.70402 |
| G128/R1 | 0.44969 | 36.78347 | 22.54486 | 53.39394 |
| G128/R2 | 0.44969 | 35.15046 | 21.83513 | 51.07575 |
| G256/R0 | 0.44969 | 48.92462 | 31.64523 | 30.99000 |
| G256/R1 | 0.44969 | 40.69515 | 25.26050 | 51.83066 |
| G256/R2 | 0.44969 | 38.41492 | 23.33815 | 61.38062 |

**最大间距出现明显的名义管腔径向交换。** 例如 G256/R2、gap=0.44969 cm：孔口 Q=38.41492，管腔 Q=23.33815 mL/s，差值约占孔口 Q 的 **39.2%**。入口 gap 的有符号径向净通量为 **+13.69924 mL/s**，出口为 **−14.32510 mL/s**；方向符合入口处向管外流出、出口处重新流入管腔的旁路特征。总交换指标为管腔流量的 **61.38%**，这个分母不同，不能称为“61.38% 的入口流量泄漏”。两种流量离散和未计入的其他面使上述差值不是严格闭合的旁路守恒预算。

**孔口流量增加不等于管腔有效流量增加。** 对 G64/R2，将 gap 从 0.24969 增至 0.44969 cm，孔口 Q 从 19.26448 升至 28.36990，但管腔 Q 几乎不变：19.11648 → 19.11396 mL/s；端隙交换指标却从 **0.00315%** 升至 **21.38%**。因此不能仅凭孔口流量选择较大 gap。

### 9.3 网格收敛与 MFAC

以中间间距 0.24969 cm 为例，R1 相对 R2 的管腔流量差，采用 $100(Q_{R1}/Q_{R2}-1)$：

| 流体网格 | R1→R2 管腔流量差 |
|---|---:|
| G64 | 1.71% |
| G128 | 3.22% |
| G256 | 10.37% |

G64 上 R1 与 R2 接近，不能外推为 G256 上固体已经足够细。固定 R2，同一间距下 G64/G128/G256 的管腔 Q 为 **19.11648 / 21.94122 / 23.47260 mL/s**；最后一级仍相差约 **7.0%**（以 G128 为分母）。因此本组**尚未达到联合空间收敛**。

下面是中间间距的参考网格边长指标：$\|\Delta\mathbf{x}/\mathbf{h}\|_2$，按单元边出现次数统计，h 分别为 dx、dy、dz；它不是相邻独立节点距离或 IB 积分作用点间距。不同单元可能重复计入共享边。

| 流体／固体 | 管壁：中位数 | housing：中位数 | housing：最大值 |
|---|---:|---:|---:|
| G64/R0 | 1.625 | 1.202 | 2.366 |
| G64/R1 | 0.813 | 0.607 | 1.570 |
| G64/R2 | 0.406 | 0.304 | 0.785 |
| G128/R0 | 3.250 | 2.404 | 4.731 |
| G128/R1 | 1.625 | 1.213 | 3.139 |
| G128/R2 | 0.813 | 0.608 | 1.570 |
| G256/R0 | 6.500 | 4.808 | 9.462 |
| G256/R1 | 3.250 | 2.426 | 6.278 |
| G256/R2 | 1.625 | 1.216 | 3.139 |

G256/R2 的管壁边指标中位数为 **1.625**，housing 最大值约 **3.139**，与 G64/R0 不是同等的精细固体分辨率。对 G256 继续比较 R3 有依据，但当前结果尚不能确定一个普遍适用的 MFAC 阈值。判断固体是否足够细，仍应比较作用点密度、速度场、管腔流量、变形和体积误差，而不是只看 J 接近 1。

### 9.4 采样误差与证据范围

通量后处理使用求解器已保存的节点平均速度，做三线性插值；NumPy 实现已与 VTK 在本机最终高压场上交叉核对。默认圆盘为 48 个径向、128 个角向中点，gap 圆柱面为 24 个轴向、128 个角向中点。它不同于原生 MAC 面通量。

将上述三个方向采样数各加倍，在三个代表组中，管腔 Q 变化均小于 **0.026%**。但很小的径向交换对采样更敏感：G256/R2、最小间距组的总交换变化约 **20.6%**，其量级仍很小；最大间距组的大交换仅变化约 **0.074%**。这检验了后处理积分敏感性，**不是流体／固体空间收敛试验**；微小交换指标不应解读到多位有效数字。

### 9.5 当前可采用的结论与下一步

- **间距同时受稳定性与旁路约束，不能越大越好。** G64/R2、gap=0.24969 cm（1.489Δz）完成短测，端隙交换较小；G256/R2、gap=0.04969 cm（1.185Δz）也完成短测，交换约 0.017%。两者都不是经过长期／时间步收敛验证的最优值。
- **G128 的这三个离散间距没有同时给出理想结果。** R2 的最小 gap（0.593Δz）失败，中间 gap（2.978Δz）虽完成，但交换指标约 11.38%。下一步适合补测 R2 的 0.09969 和 0.14969 cm，即约 1.189Δz、1.785Δz，而不是直接接受当前较大间距。
- **G256/R2 尚不能视为收敛基准。** 应在选定间距后比较更细固体及减半 dt，并延长筛选出的算例；本次没有新增这些物理算例。
- **高压长测的主要未解决项是 housing 局部变形／体积失真。** 即使所有保存帧 J>0，也不能宣称刚性 housing 流动已得到验证。

### 9.6 Git commit 与复现

最终通量分析、采样核查和绘图脚本：[`3a069cd57034d224a76c07eb8599d6f223b05aee`](https://github.com/mapengfei-glasgow/fdm-3d-v1-workspace/commit/3a069cd57034d224a76c07eb8599d6f223b05aee)；运行队列与网格提取脚本见 [`dddfdeb`](https://github.com/mapengfei-glasgow/fdm-3d-v1-workspace/commit/dddfdeb125b7059603b407604365e8e36a49ded2)。

仍需已有生成的 `glamv_hex`、`glamv_hex_r1`、`glamv_hex_r2` 输入网格；Git 提交不包含全部网格文件。求解器构建见第 5 节。以下复现 G64/R2、gap=0.24969 cm；其余组合更换源数据、截取范围和 nx/ny/nz。

```bash
OPENBLAS_NUM_THREADS=1 python3 scripts/simulations/prepare_glamv_tube_housing.py \
  --source "$PWD/fdm-3d-v1-geometry/src/ibm/data/glamv_hex_r2" \
  --tube-z-limit 7.8 --out "$PWD/runs/reproduce_factorial/mesh"

export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=2 DSH_PERF_LEVEL=0
./build-tube/tube_flow_scale --gpu-coupling --sarah-wall-stress \
  --N 64 --nx 64 --ny 64 --nz 96 \
  --domain 8.6,8.6,16.09938 --reference-center 0,0,0 \
  --rin 3.5 --nu 0.04 --pmax 66.661 --ramp 0.2 \
  --T 0.3 --dt 5e-6 --beta-body 5e8 --beta-disk 5e8 \
  --disk-bulk 0 --mu 0 --lambda 0 \
  --data runs/reproduce_factorial/mesh/ \
  --every 10000 --probe-every 10000 \
  --out runs/reproduce_factorial/case/
```

直接调用不含几何停止监控；队列脚本使用 `queue_housing_stability.py` 做保存帧审计。已有对应结果及收集文件时，重算通量和图表：

```bash
OPENBLAS_NUM_THREADS=1 python3 scripts/diagnostics/measure_tube_gap_flux_numpy.py \
  runs/reproduce_factorial/case/fluid_060000.vti --clearance 0.24969 \
  --out /tmp/reproduce-gap-flux.json

# 以下两条按原试验目录命名读取已有结果；采集脚本和采样加密脚本亦在同一提交。
OPENBLAS_NUM_THREADS=1 MPLCONFIGDIR=/tmp/mv-mpl \
  python3 scripts/diagnostics/analyze_tube_factorial_final.py
OPENBLAS_NUM_THREADS=1 MPLCONFIGDIR=/tmp/mv-mpl \
  python3 scripts/visualization/plot_tube_factorial_progress.py
```
