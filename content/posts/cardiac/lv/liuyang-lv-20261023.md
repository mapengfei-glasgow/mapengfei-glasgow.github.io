---
title: "Liuyang 左心模型：128³ 流固耦合计算与压力–体积结果"
description: "2026-10-23 计算记录：1.8 s 左心模型、三维流场与压力切面、体积和流量数据，以及重启反馈稳定化的局限。"
date: 2026-10-23T12:00:00+01:00
academic: true
ShowToc: true
tags: ["FSI", "GPU", "Liuyang"]
url: /posts/liuyang-lv-20261023/
area: research
readingRoute: left-ventricle
areas: ["Cardiac Simulation"]
projects: ["Left Ventricle"]
noteType: "Results"
---

本页整理 2026 年 10 月 23 日 `liuyang_lv_20261023` 目录中的计算结果。主结果为 `full_N128`：128³ 网格、时间步长 5 μs，日志确认完成至 **t = 1.8 s（360,000 步）**。

**这是包含重启和稳定化处理的数值实验记录。** 运行脚本记载：未启用反馈时，主动脉出口回流在约 1.191 s 导致发散，随后从 1.153 s 检查点加入 `--feedback` 继续计算。因此，不能把整段轨迹解释为从零开始、参数完全一致的计算；也尚未建立周期稳态、网格收敛或实验验证。

## 模型几何、材料与耦合

### 从实际参考网格绘制的几何结构

该模型包含左心室（LV）、左心房（LA）、二尖瓣（MV）与瓣周结构、四支肺静脉及主动脉/主动脉根部，并非完整四腔心脏。几何来自本次计算使用的 `FC.xda` 转换数据：**217,379 个节点、1,044,779 个线性四面体（P1/TET4）**，每个单元采用一个重心积分点。日志中的通用字符串“P2 nodes”不代表这里采用二次单元；数据转换器和运行时的 `4 basis` 确认了 P1 离散。

{{< figure src="/liuyang-lv-20261023/geometry.png" title="PyVista 直接从本次 ref_nodes.bin、dofmaps.bin 和 cell_marker.bin 提取的参考几何。左：组织外表面；右：血管、血管端段和腔壁透明化，叠加实际腱索与主动脉瓣伪纤维网络；棕色为 MV 腱索、青色为 AV 支撑纤维、紫色为 AV 瓣叶纤维。红色 LV、蓝色 LA、黄色 MV/瓣周结构、灰色血管、紫色心尖支撑区、绿色血管端段。" >}}

| 图中分组 | 本次实际单元标记 | 四面体数 | 作用 |
|---|---|---:|---|
| LV | 21 | 669,631 | 左心室心肌 |
| LA | 23 | 79,108 | 左心房心肌 |
| MV/瓣周结构 | 30、40、5 | 52,474 | 前后瓣叶及 housing；标记 5 使用前瓣叶材料 |
| 血管与主动脉根部 | 100、200、1000 | 219,948 | 肺静脉/主动脉相关血管组织与主动脉根部 |
| 心尖支撑区 | 211 | 907 | 使用 LV 被动材料并施加 tether |
| 血管端段 | 4099 | 22,711 | 端部支撑区 |

固体采用分区各向异性超弹性材料：LV/LA 为 HO-type 指数模型，二尖瓣为 Sarah HGO 型纤维增强模型，血管为指数材料；体积惩罚项控制组织压缩。每个单元读取纤维及片层方向。1 s 后启用 LV 的 NHS 主动张力和 LA 的规定主动张力，设定激活周期为 0.8 s。

腱索与主动脉瓣的伪纤维通过额外的弹簧/梁网络表示，不应把图中的主动脉根部理解为一套单独解析的实体主动脉瓣叶。日志记录网络包含 6,449 个点、10,884 根弹簧、10,275 个梁项；其中 532 个点映射至有限元单元重心。几何图右侧叠加 `Alltogether.vertex` 和 `.spring` 中的参考网络连线；按求解器的弹簧主节点编号区分 MV 腱索、AV 瓣叶纤维与其余 AV 支撑纤维。该图展示参考构型，主动脉瓣以离散伪纤维网络绘制。

流体使用 128³ 笛卡尔网格，运动黏度为 0.04 cm²/s。组织与流体通过浸入边界（IB_4）插值/力扩散耦合，时间推进采用 RK2 中点方法。计算盒原坐标范围为 x∈[−5,12]、y∈[−26.5,−10.38]、z∈[133.35,149.48] cm；以下边界图减去左下角坐标，使范围成为 [0,17]×[0,16.12]×[0,16.13] cm。

### 边界条件及端部约束

{{< figure src="/liuyang-lv-20261023/boundary-conditions.png" title="实际参考几何与计算盒上的五个压力开口。编号 1–4 为四支肺静脉，5 为主动脉。圆盘半径取日志中经壁面识别调整后的值；文字说明压力、外部开放边界和固体端部约束。" >}}

| 开口 | 所在面（平移后坐标） | 运行时压力开口半径 | 压力条件 |
|---|---|---|---|
| RIPV：右下肺静脉 | x=0 | 1.448 cm | 输入文件的 RIPV 压力曲线 |
| RSPV：右上肺静脉 | x=0 | 1.468 cm | 输入文件的 RSPV 压力曲线 |
| LIPV：左下肺静脉 | y=16.12 cm | 1.473 cm | 输入文件的 LIPV 压力曲线 |
| LSPV：左上肺静脉 | z=16.13 cm | 1.472 cm | 输入文件的 LSPV 压力曲线 |
| Aorta：主动脉 | z=16.13 cm | 2.434 cm | 1 s 前读输入文件，1 s 后使用 Windkessel |

四支肺静脉的压力由 `HeartPressure.inlet` 按时间线性插值，超出输入时间范围时取端点值。开口采用法向压力/牵引条件、切向速度为零，法向流量由求解器决定，因此允许出现回流。

**外部盒子不是封闭的无滑移容器。** 本次默认六个盒面在压力开口和壁环之外均采用 p=0 的开放牵引条件；开口周围识别出的壁环采用无滑移。`--wall-ring 0.6` 令外壁环延伸至识别出的血管外半径再加 0.6 cm，压力开口半径取内壁半径减 0.02 cm。

固体与流体的辅助约束同时包括：距盒面 0.3 cm 内的组织节点固定于参考位置；距盒面 0.5 cm 内的单元增加 tether；原有心尖和血管端段保留 tether，并叠加 Brinkman 区域。开口附近设深度 0.5 cm、径向宽度 0.5 cm 的 Brinkman collar。1.153 s 重启后另启用边界层反馈阻尼，其法向强度随开口位置、流向及心动相位变化，不能简单等同于所有开口上的零速度条件。

### 三元 Windkessel：3D 主动脉出口与 0D 后负荷

{{< figure src="/liuyang-lv-20261023/windkessel.png" title="与代码压力方程等价的三元 RCR 电路：近端特征阻抗 Zc 与远端并联 R、C 串联。Q>0 表示流出三维主动脉，P_Ao 返回为出口压力，远端参考压力为零。" >}}

三个参数从 `liuyang_lv.cu` 读取并由 cgs 换算：

| 参数 | 数值 | 含义 |
|---|---|---|
| Zc | 0.0284 mmHg·s/ml | 近端特征阻抗 |
| R | 0.678 mmHg·s/ml | 远端阻力 |
| C | 3.4181 ml/mmHg | 储血顺应性 |

令 P_C 为等效顺应性压力，电路满足

$$
P_{Ao}=Z_cQ+P_C,\qquad C\frac{dP_C}{dt}=Q-\frac{P_C}{R}.
$$

消去 P_C，即得到代码实际推进的压力方程：

$$
C\frac{dP_{Ao}}{dt}+\frac{P_{Ao}}{R}
=\left(1+\frac{Z_c}{R}\right)Q+Z_c C\frac{dQ}{dt}.
$$

每步从 z 高端主动脉中心半径 **2.5 cm** 的圆盘上积分法向速度得到 Q，利用后向差分估算 dQ/dt，并隐式处理压力衰减项。该流量积分盘与经壁面调整后的压力开口半径 2.434 cm 并不完全相同。

耦合顺序为：已有压力施加到三维出口 → 更新流体和组织 → 积分得到出口 Q → 更新 Windkessel 压力供后续步骤使用。代码直接存储并推进 P_Ao，不单独存储 P_C。1 s 前实际施加的主动脉压力仍来自输入文件；Windkessel 内部状态以 50 mmHg 为基值处理，1 s 后才接管压力边界，因此不能把整个预充盈阶段都称为恒定 50 mmHg 出口条件。

[下载绘图脚本](/liuyang-lv-20261023/plot_model.py) · [Windkessel 矢量图](/liuyang-lv-20261023/windkessel.svg)

## 主要结果

{{< figure src="/liuyang-lv-20261023/full_N128_cycle.png" title="保存快照的 LV/LA 腔体积与平均腔内压力、边界流量，以及 t ≥ 1 s 的 LV 压力–体积轨迹。体积/腔压曲线从 0.8 s 开始；流量曲线包含更早的启动过程。" >}}

以下数值直接取自 `full_N128_cycle.csv` 在 **1.0–1.8 s** 的离散快照；极值受保存间隔限制。

| 量 | 最小值（时刻） | 最大值（时刻） |
|---|---|---|
| LV 体积 | 39.54 ml（1.24 s） | 73.40 ml（1.04 s） |
| LV 腔内平均压力 | 2.00 mmHg（1.36 s） | 133.86 mmHg（1.12 s） |
| LA 体积 | 38.68 ml（1.80 s） | 58.47 ml（1.44 s） |
| LA 腔内平均压力 | 1.99 mmHg（1.80 s） | 23.17 mmHg（1.76 s） |
| 主动脉边界压力 | 50.00 mmHg（1.00 s） | 82.76 mmHg（1.18 s） |

曲线显示主动收缩阶段 LV 体积下降、腔压上升，并伴随主动脉流出。1.8 s 时 LV 体积尚未回到本段最大值；压力–体积轨迹未闭合，不应直接当作已收敛心动周期，也不据此报告正式的射血分数或每搏功。

## 三维流场与切面

视频播放速度用于展示，实际物理时间以画面标注为准。流线是各帧的瞬时速度流线，不是粒子轨迹；速度阈值筛选后的流线不能代表全部流动区域。

### 四个方向观察左心模型

围绕 LV 长轴的四个方向；展示组织表面与筛选后的瞬时速度流线。

<video controls playsinline preload="none" poster="/liuyang-lv-20261023/views3d-poster.png" style="width:100%;height:auto"><source src="/liuyang-lv-20261023/full_N128_views3d.mp4" type="video/mp4">请下载 MP4 查看。</video>

[下载视频](/liuyang-lv-20261023/full_N128_views3d.mp4)

### 速度切面

三腔长轴、正交长轴、LV 短轴和心房切面的速度大小与面内箭头。

<video controls playsinline preload="none" poster="/liuyang-lv-20261023/slices-poster.png" style="width:100%;height:auto"><source src="/liuyang-lv-20261023/full_N128_slices.mp4" type="video/mp4">请下载 MP4 查看。</video>

[下载视频](/liuyang-lv-20261023/full_N128_slices.mp4)

### 压力切面

与速度切面对应的压力分布和等压线，压力单位为 mmHg。

<video controls playsinline preload="none" poster="/liuyang-lv-20261023/pressure-poster.png" style="width:100%;height:auto"><source src="/liuyang-lv-20261023/full_N128_pressure.mp4" type="video/mp4">请下载 MP4 查看。</video>

[下载视频](/liuyang-lv-20261023/full_N128_pressure.mp4)

### 流场动画

用于补充观察流场与组织运动，色标和时间见画面。

<video controls playsinline preload="none" poster="/liuyang-lv-20261023/flow-poster.png" style="width:100%;height:auto"><source src="/liuyang-lv-20261023/full_N128_flow.mp4" type="video/mp4">请下载 MP4 查看。</video>

[下载视频](/liuyang-lv-20261023/full_N128_flow.mp4)

## 模型与运行条件

运行脚本描述了被动充盈、伪纤维腱索/AV 网络、NHS 主动张力及 Windkessel 边界；主动张力与 Windkessel 从 1 s 开始。以下列出脚本中的关键选项，完整命令见下载区。

| 项目 | 设置 |
|---|---|
| 网格 / 时间步 / 终止时间 | `--N 128 --dt 5e-6 --T 1.8` |
| 保存间隔 | `--every 4000`（0.02 s） |
| 检查点间隔 | `--checkpoint-every 20000`（0.10 s） |
| 开口 / 环带 | `--wall-ring 0.6 --seal-openings 0.5 --seal-width 0.5` |
| 血管端部 | `--pin-ends 0.5 --fix-ends 0.3 --brinkman-pins` |
| 主动与出口模型 | `--active --windkessel` |
| 续算稳定化 | 在 1.153 s 重启时加入 `--feedback`，依据运行脚本注释 |

当前脚本包含 `--feedback`，不是所有早期分段运行的原始命令。日志末段记录的 `WALL 11929.82` 是该次进程耗时，不能当作整个含重启实验的总用时。

### 指标如何计算

`cycle_metrics.py` 使用 LV/LA 内膜节点与面片构造闭合表面，并用开口中心点封口。体积通过三角面片的有向体积求和取绝对值得到；腔内压力是闭合表面内流体网格采样点压力的算术平均，以 1333.2239 换算为 mmHg。它不是壁面压力，也不是严格的单元体积加权积分。主动脉压力/流量来自 `flow.csv`；肺静脉流量为四支静脉之和。

脚本和图例采用主动脉正向为流出、肺静脉负向为流入的符号约定。启动期存在明显反向流量，读图时应保留符号。

## 反馈关闭时的失稳记录

运行脚本记载未启用反馈的分支约在 1.191 s 因主动脉出口回流失稳。下面单独保留对应动画，作为诊断材料；它不属于完成至 1.8 s 的结果。

<video controls playsinline preload="none" style="width:100%;height:auto"><source src="/liuyang-lv-20261023/blowup_nofb_pressure.mp4" type="video/mp4">请下载 MP4 查看。</video>

[下载失稳诊断视频](/liuyang-lv-20261023/blowup_nofb_pressure.mp4)

单次失败分支与含反馈的续算不足以证明稳定化的普适有效性；后续需要相同初态的受控对照、质量/体积守恒检查、网格和时间步收敛，以及多个心动周期的重复性检查。

## 数据与复现材料

- [体积与压力指标 CSV](/liuyang-lv-20261023/full_N128_cycle.csv)
- [边界压力与流量 CSV](/liuyang-lv-20261023/flow.csv)
- [运行脚本](/liuyang-lv-20261023/run_full_N128.sh)
- [指标计算脚本](/liuyang-lv-20261023/cycle_metrics.py)
- [多视角与切面绘图脚本](/liuyang-lv-20261023/animate_views.py)
- [流场动画脚本](/liuyang-lv-20261023/animate_flow.py)
- [发布文件校验清单（SHA-256）](/liuyang-lv-20261023/manifest.json)

上述脚本保留了本次运行环境的原始路径，依赖本地几何、网格、边界输入及二进制程序，下载脚本本身不足以独立复现。本页仅发布汇总数据、脚本、图和 MP4；原始检查点、三维场数据、编译产物和逐帧图片仍保存在计算目录中。早期 `passive_*`、`seal_*`、`diag_*` 等目录属于诊断或参数试验，未混入主结果。
