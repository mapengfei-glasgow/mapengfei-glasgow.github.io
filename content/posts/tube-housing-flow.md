---
title: "管道与 housing disc 流动：G64/R2 数值对照"
description: "同一压差下的纯管道与管道加 disc 对照：参数、截面、流量、单元翻转及复现方法。"
date: 2026-10-20
lastmod: 2026-10-21
layout: protected-paper
academic: true
comments: false
searchHidden: true
build:
  list: never
---

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
