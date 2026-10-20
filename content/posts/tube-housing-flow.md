---
title: "管道与 housing disc 流动：G64/R2 数值对照"
description: "同一压差下的纯管道与管道加 disc 对照：参数、截面、流量、单元翻转及复现方法。"
date: 2026-10-20
layout: protected-paper
academic: true
comments: false
searchHidden: true
build:
  list: never
---

本文记录两组 **0.005 mmHg 恒定目标压差、计算至 5 s** 的 GPU 算例。两组仅相差原 R2 housing disc：纯管道保留管壁；tube+disc 保留管壁和 disc，均不含瓣叶、腱索及乳头肌。

**主要结果：**5 s 时，增加 disc 后出口流量由 **58.0 降至 27.9 mL/s**，最大轴向速度由 **2.07 升至 3.94 cm/s**。但 disc 已发生局部单元翻转，因此后一组只作为诊断结果，不能视为通过验证的刚性 disc 流动。

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

升压函数为 $\Delta p(t)=0.005\min(t/0.01,1)$ mmHg，出口压力为零。**本文图表来自早先的 0.01 s ramp、弱 tether 算例，不是后续的 0.2 s ramp、Sarah 应力测试。**

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

## 5. 下载与复现

[下载图表、原始探针 CSV、命令、校验记录和源码补丁（ZIP）](/data/tube-housing-20261020/tube-housing-results.zip)。也可单独查看 [纯管道输入校验清单](/data/tube-housing-20261020/tube/MESH_SHA256.json)、[tube+disc 输入校验清单](/data/tube-housing-20261020/tube-disc/MESH_SHA256.json) 和 [源码版本](/data/tube-housing-20261020/reproduction/REVISIONS.json)。

**复现前提：**保留的两组输入网格及 CUDA 构建环境。下载包不含完整网格、全部 VTI/固体快照或二进制。`glamv_hex_r2` 是生成数据，单凭仓库提交号不能恢复输入；应核对上述网格 SHA256。已有原始 R2 数据时，可使用包内两份 `prepare_glamv_*.py` 提取脚本；其路径按原工作区布局设置，移植时需调整。

将 GPU 仓库检出到下载包 `REVISIONS.json` 指定提交，再在 GPU 仓库中应用 `reproduction/gpu.patch`。与 `fdm-3d-v1`、`fdm-3d-v1-geometry` 放在同级目录，安装 CMake、兼容的 CUDA/C++ 编译器及 HDF5 等依赖后，从工作区根目录构建：

```bash
cmake -S fdm-3d-v1-gpu -B build-tube \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_CUDA_ARCHITECTURES=native \
  -DFDM3D_GPU_FMAD=ON
cmake --build build-tube --target tube_flow_scale -j2
```

下载包的 `replay.py` 读取实际运行命令，只替换可执行文件、输入网格和输出路径。先不加 `--run` 检查命令，确认后加上该参数运行：

```bash
python3 reproduction/replay.py --case tube \
  --binary /path/to/build-tube/tube_flow_scale \
  --mesh /path/to/tube_R2_Q1 --out /path/to/new-tube-run --run

python3 reproduction/replay.py --case tube-disc \
  --binary /path/to/build-tube/tube_flow_scale \
  --mesh /path/to/tube-housing-mesh --out /path/to/new-disc-run --run
```

两组命令均使用 `--gpu-coupling`，未开启后续的 `--sarah-wall-stress` 或 J 惩罚。不同 GPU、编译器及原子累加顺序可能带来舍入差异。绘图用包内 PyVista 脚本；绘图和网格审计脚本仍按原工作区路径组织，脱离该布局使用时需调整路径。

本页的用途是建立可检查的 tube/tube+disc 对照，并记录当前离散方法的限制。后续参数测试不替代这里的原始结果。
