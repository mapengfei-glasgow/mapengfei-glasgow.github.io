---
title: "Liuyang 左心模型：128³ 流固耦合计算与压力–体积结果"
description: "2026-10-23 计算记录：1.8 s 左心模型、三维流场与压力切面、体积和流量数据，以及重启反馈稳定化的局限。"
date: 2026-10-23T12:00:00+01:00
academic: true
ShowToc: true
tags: ["FSI", "GPU", "left ventricle", "Liuyang"]
---

本页整理 2026 年 10 月 23 日 `liuyang_lv_20261023` 目录中的计算结果。主结果为 `full_N128`：128³ 网格、时间步长 5 μs，日志确认完成至 **t = 1.8 s（360,000 步）**。

**这是包含重启和稳定化处理的数值实验记录。** 运行脚本记载：未启用反馈时，主动脉出口回流在约 1.191 s 导致发散，随后从 1.153 s 检查点加入 `--feedback` 继续计算。因此，不能把整段轨迹解释为从零开始、参数完全一致的计算；也尚未建立周期稳态、网格收敛或实验验证。

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
