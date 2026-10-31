---
title: "主动脉瓣 CMAME 与 FDM：完整时程、四格动画和全域流场对照"
description: "原版 CMAME 和新版 FDM 均完成 1.635 秒：并列展示 cardiac four-panel 视频、全域速度与压强对照动画，以及流量和压力边界差异。"
date: 2026-10-30T00:00:00+00:00
lastmod: 2026-10-31T12:00:00+00:00
academic: true
ShowToc: true
url: /posts/av-cmame-reproduction-20261030/
area: research
areas: ["Cardiac Simulation"]
projects: ["Mitral Valve"]
tags: ["FSI", "GPU", "Verification"]
noteType: "Reproduction"
readingRoute: mitral-valve
---

原版 `cmame-v100-2 2.zip` 中的 **`gfem_main_av` 已完成 327000 步，目标物理时间 1.635 s，退出码 0**。计算在 RTX A6000 上进行，UTC 开始于 2026-10-29 20:15:42，结束于 2026-10-30 03:33:06，启动至结束共 **7 小时 17 分 24 秒**。这是原版 CMAME 基线，不同于此前正弦压力驱动的 [av_glamv 直管试算](/posts/av-glamv-20261028/)。

**2026-10-31 更新：新版 FDM `real_av` 也已完成 1.635 s / 327000 步，退出码 0。** 本页现在同时展示两套 cardiac four-panel 视频和整个计算域的速度、压强同步对照动画。FDM 的关键配置修正是在固体两端与流体边界之间各留出 **2dz**；网格数量仍为 80×80×128，时间步仍为 5×10⁻⁶ s。

**正常结束证明了这套源码、输入与环境可以完成时程，并不代表数值质量已验证。** 原版输出存在负的线性可视化单元体积比，尚无原版全网格、全时程的 P2 积分点审计；FDM 在保存时刻的全网格审计中仍有支撑区积分点 J≤0。两套流量和压强场也尚未一致。以下动画及曲线是复现和诊断证据。

## 完整四格动画

### 旧实现：原版 CMAME `gfem_main_av`

<video controls playsinline preload="metadata" poster="/av-cmame-20261030/opening.png" style="width:100%;height:auto"><source src="/av-cmame-20261030/av-four-panel.mp4" type="video/mp4">请下载 MP4 查看。</video>

[下载完整 MP4](/av-cmame-20261030/av-four-panel.mp4) · [开瓣画面](/av-cmame-20261030/opening.png) · [最后保存帧](/av-cmame-20261030/final.png) · [动画输入说明](/av-cmame-20261030/video-input.json)

动画覆盖 **0.000005–1.630005 s**。计算终点是 1.635 s，但每 1000 步保存一次场，最后完整流固配对帧为 1.630005 s；没有外推或补造最后约 0.005 s。共有 327 组完整配对状态，取每四组及最后一组，共 83 组，按物理时间线性插值为 241 帧、15 fps，播放约 16.07 秒。运动保持实际尺度。

- 左上：从高 z 入口观察瓣叶；右上：从低 z 出口观察。
- 左下：y = 4 cm 纵向切片的轴向速度 w，保留 +z 符号；固定色限 ±200 cm/s，超限颜色饱和。材料轮廓随当前变形更新。
- 右下：原生日志的入口压力、Windkessel 出口压力和 MAC 平面流量，时间游标与几何同步。

流量为 **z = 12.6875 cm 处整个 MAC 平面的原生离散积分，正方向 −z**，不是仅瓣口区域的通量。压力由 dyn/cm² 换算为 mmHg。不要把这条流量曲线解释成额外的瓣口守恒证明。

### 新实现：FDM `real_av`，两端各留 2dz

<video controls playsinline preload="metadata" poster="/av-fdm-comparison-20261031/fdm-opening.png" style="width:100%;height:auto"><source src="/av-fdm-comparison-20261031/fdm-four-panel.mp4" type="video/mp4">请下载 MP4 查看。</video>

[下载 FDM 四格 MP4](/av-fdm-comparison-20261031/fdm-four-panel.mp4) · [末帧](/av-fdm-comparison-20261031/fdm-final.png) · [动画溯源](/av-fdm-comparison-20261031/fdm-video-provenance.json) · [运行记录](/av-fdm-comparison-20261031/fdm-run-summary.json)

FDM 在 RTX A6000 上从静止初态运行，UTC 2026-10-31 02:33:22–09:27:33，耗时 **6 小时 54 分 11 秒**。视频覆盖 **0–1.635 s**；328 组保存状态中选取 83 组，线性插值为 241 帧、15 fps。展示 P2 解在原线性顶点上的运动，未放大变形。

原几何轴向长度 14 cm，固定 Nz=128 时令 `c=2dz`、`dz=(14+2c)/128`，得到每端留白 **c=0.2258064516 cm**、新域长 **14.4516129032 cm**、dz=0.1129032258 cm。固体整体沿 +z 平移 c，未重网格；由于域长增加，dz 相对旧版略有变化。

四格视频右下角的 FDM 流量是从 VTI 节点速度重建的全平面积分，实际测量面 z=12.8709677419 cm，正方向 −z。**它与上方原版视频的原生 MAC 通量不是完全相同的测量方法**；下面另给统一重建方法的比较。

全部 328 个保存时刻中，三片瓣叶（15/16/18）的 64 积分点 J 均未出现非正值；各瓣叶跨保存时刻的最小 J 约为 0.14073、0.02483、0.08874。**5/17 号管壁与瓣根支撑区仍有反转和明显畸变**，末帧分别有 3246、2436 个单元含非正积分点 J。允许有限负 J 继续计算，NaN/Inf 仍会终止。该审计不覆盖输出间隔内每一步。

[分区积分点 J 记录 CSV](/av-fdm-comparison-20261031/fdm-quadrature-j.csv) · [Workspace 分支与复现说明](https://github.com/mapengfei-glasgow/fdm-3d-v1-workspace/tree/av/cmame-clearance-2dz-20261031) · [GPU 代码分支](https://github.com/mapengfei-glasgow/fdm-3d-v1-gpu/tree/av/cmame-clearance-2dz-20261031)

## 整个计算域：速度和压强同步对照动画

<video controls playsinline preload="metadata" poster="/av-fdm-comparison-20261031/full-domain-poster.png" style="width:100%;height:auto"><source src="/av-fdm-comparison-20261031/full-domain-comparison.mp4" type="video/mp4">请下载 MP4 查看。</video>

[下载全域对照 MP4](/av-fdm-comparison-20261031/full-domain-comparison.mp4) · [动画溯源](/av-fdm-comparison-20261031/full-domain-provenance.json) · [末帧](/av-fdm-comparison-20261031/full-domain-final.png) · [保存场来源](/av-fdm-comparison-20261031/full-domain-input.json) · [新增资源校验清单](/av-fdm-comparison-20261031/SHA256.json)

**上排：旧版 CMAME；下排：FDM。三列依次为速度大小 |v|、有符号轴向速度 w、压强。** 截面是 y=4 cm，保留 x=0–8 cm 及全部轴向流体区域，包括管外流体和两端边界；没有裁到瓣叶局部。原版域长 14 cm，新版 14.4516129032 cm。两排使用相同物理坐标轴，旧版上方灰条表示超出旧域的区域。

动画按同一物理时间同步播放，覆盖两套数据的公共区间 **0.000005–1.630005 s**。每套取 83 组保存场，分别在各自实际保存时间上插值；不外推至原版未保存的 1.635 s。速度、压强色标在新旧及整个动画中固定共享，压强按原保存值换算为 mmHg，**未平移压力零点**。共享色标为速度大小 0–600 cm/s、轴向速度 ±600 cm/s、压强 −125–550 mmHg，保留保存场的局部压力尖峰；见动画溯源。箭头为截面内 (u,w) 速度，金色为当前瓣叶轮廓，黑色为当前管壁/瓣根轮廓。原版 VTI 的单元中心采样与 FDM 的节点采样不同，不能把边界像素看作完全相同的离散位置。

关键静帧：[0.22 s 主流峰](/av-fdm-comparison-20261031/section-022.png) · [0.50 s 回流](/av-fdm-comparison-20261031/section-050.png) · [1.24 s 流量差异最大附近](/av-fdm-comparison-20261031/section-124.png) · [1.63 s 末期](/av-fdm-comparison-20261031/section-163.png)

**一个明显线索是管外压强不同。** 在约 0.22 s 的 y=4 cm 截面上，取 z∈(1,7) cm：管内 x∈(3.5,4.5) cm 的压力中位数，旧版约 118.10、新版约 115.74 mmHg；管外 x∈(0.3,2) cm 则分别约 −0.03 和 118.19 mmHg。这不是单纯的全场常数偏移，提示应优先核对管外区域和进出口的压力边界处理。**这仍是排查线索，不是已经确定的唯一误差来源。**

[静帧字段与来源](/av-fdm-comparison-20261031/section-input.json) · [压力区域统计](/av-fdm-comparison-20261031/section-diagnostic.json)

## 统一重建方法后的流量差异

![同一方法重建的新旧全平面流量](/av-fdm-comparison-20261031/same-method-flow.png)

为排除视频中两种测量方法的差别，这里将原版与 FDM 都从 VTI 速度重建：取相对原几何 z=12.6875 cm 的截面，FDM 加上固体平移 c；在共同的物理 x/y∈[0,8] cm 网格上插值后做同一梯形积分，正方向 −z。

| 保存状态下的指标 | 原版 CMAME | FDM |
|---|---:|---:|
| 正向峰值（mL/s） | 535.4 | 492.9 |
| 峰值时刻（s） | 0.220005 | 0.220000 |
| 最大反向流量（mL/s） | −340.2 | −475.0 |
| 公共时段净通过体积（mL） | 166.9 | 120.7 |

新版正向峰值低约 7.9%，回流峰值幅度比旧版约高 40%。这些结果来自约 0.02 s 保存间隔，使用线性时间插值；尖峰和净体积仍受采样精度影响，不是每一步的极值或精确离散守恒测量。原版最后公共时刻为 1.630005 s。

[统一重建 CSV](/av-fdm-comparison-20261031/same-method-flow.csv) · [比较方法和统计 JSON](/av-fdm-comparison-20261031/flow-comparison.json)

## 原版实际计算设置

| 项目 | 本次原版运行 |
|---|---|
| 可执行入口 | `gfem_main_av` / `src/main_av.cpp` |
| GPU / 架构 | NVIDIA RTX A6000 / sm86 |
| 依赖 | CUDA 12.4、Kokkos 4.3.0、GCC 11.4、旧 DOLFIN/FFC；Basix 用于生成积分头 |
| 流体网格 | **80 × 80 × 128** |
| 计算域 | 8 × 8 × 14 cm |
| 时间步 / 总步数 | 5×10⁻⁶ s / 327000 |
| 流体密度 / 动力黏度 | 1 g/cm³ / 0.04 g/(cm·s) |
| 固体 | 233216 个参考四面体、77530 个参考线性顶点；求解使用 P2，输出落在原线性可视化网格上 |
| 瓣叶标记 / 支持标记 | 15、16、18 / 5、17 |
| 约束参数 beta | 5×10⁸ |
| 体积材料参数 beta_s | 活跃材料代码内为 5×10⁶ |
| 入口 / 出口 | 高 z 原压力驱动 / 低 z 原 Windkessel |
| 耦合 | 原 PhiIB4 路径 |

**JSON 的 `N_bg=64` 不控制本例实际背景网格**：尺寸在 `main_av.cpp` 中写死为 80×80×128。JSON 的 `kappa=5e6` 虽传入组装接口，不能据此推断它控制了所有材料分支；必须检查活跃源码。本次没有引入 CBS43、modified-invariant 材料、Brinkman 体掩膜、J 裁剪或重网格。

[机器可读运行记录](/av-cmame-20261030/run-record.json) · [可移植配置模板](/av-cmame-20261030/full-config.template.json) · [输入与源码校验清单](/av-cmame-20261030/bundle-manifest.json)

## 从源码到可执行程序

原先操作依赖多次 Spack 激活、手工生成积分规则、逐文件修改 CUDA 架构，以及让 FFC 先生成 UFL 头。此次把输入、生成头、环境入口、构建脚本、配置展开和输出检查集中进可移植包。压缩包保留在私有存储；这里公开计算记录和说明，不公开私有存储凭据或临时签名链接。

### 1. 核对源码与完整输入

原始压缩包 SHA256：

```text
2200fab8549c79c0921486b4ee6e16e5b185000cef2126c7c4d6378cee6655f0
```

输入包含 XDMF 及其 HDF5、边界与材料 XML、三个纤维分量 XML，以及原始压力波形。只复制 XDMF 或只复制源码都不够。本次使用原 AV 实际输入，没有替换为另一个重新生成的网格。

### 2. 构建环境与兼容修正

Euclid 原版构建复用既有 Spack/DOLFIN 与 sm86 Kokkos。主要处理的是环境兼容：Ubuntu 上 CUDA driver 的导入库路径、系统头和库路径、所有 CUDA 目标及 Kokkos 子构建的一致架构，以及 FFC 生成顺序。这些修正没有改变本构、积分或时间推进公式。

在 RTX 4090 主机还做了独立移植：CUDA 12.6、Kokkos 4.3.01、sm89；使用系统 CMake 3.28，处理 Boost 查找顺序、旧 DOLFIN 的导入目标、Kokkos/CUDAToolkit 初始化顺序、nvcc 的 OpenMP 标志和旧 fmt 的 consteval 兼容问题。**V100 为 sm70、A6000 为 sm86、4090 为 sm89**；要连同 Kokkos 安装一起匹配，不能仅把所有文件中的某个数字替换掉。

### 3. 包内构建与短测

以下命令针对已经取得的 `av-repro-20261029` 包，环境目录由脚本按 HOME 展开；其他机器需提供对应依赖路径。

```bash
unzip av-repro-20261029.zip
cd av-repro-20261029
python3 scripts/verify_bundle.py
bash scripts/build.sh > build.log 2>&1
# 先用 nvidia-smi 确认目标 GPU 空闲；此处 1 是当时的测试卡。
CUDA_VISIBLE_DEVICES=1 bash scripts/run.sh smoke
```

4090 上仅完成 **0.01 s / 2000 步**短测，退出 0，约 111 秒；不能把该卡的短测写成本页 A6000 的完整时程结果，也不能据此推算严格加速比。

### 4. 后台完整运行与收尾

```bash
CUDA_VISIBLE_DEVICES=1 nohup bash scripts/run.sh full \
  > full_launcher.log 2>&1 < /dev/null &
```

每次运行使用独立 ID，生成展开后的配置、日志、UTC 起止时间和 `exit_code`。完整运行不受短测的 900 秒超时限制。完成后检查退出码、保存场的有限性、位移和单元体积比，再制作动画。原版 A6000 直接构建得到的二进制 SHA256 为：

```text
400d78d8184d4e1b9b130e0590e10eee1023d04afe316561e37ca3493fbdb8e9
```

[详细编译运行说明](/av-cmame-20261030/REPRODUCTION.md) · [实际遇到的问题和处理](/av-cmame-20261030/TROUBLESHOOTING.md)

## 输出质量与使用边界

83 组动画选取状态中，81 组出现非正线性可视化四面体体积比；最后保存帧的范围约为 **−65.4961–5.95195**。这是 P2 解在输出顶点上形成的 `J_vis`，不是完整 P2 积分点 J，不能仅凭这个数字确定全部有限元积分点的翻转情况，也不能将它忽略为无害的渲染现象。

对于原版，当前仍缺少全网格按材料区域的 P2 积分点 J 审计；两套结果也都还需要主伸长、支持运动、旁路流和空间/时间收敛检查。本页不宣称实验验证、体积保持或生理准确性。

[原生日志抽样压力/流量 CSV](/av-cmame-20261030/pressure-flow.csv) · [83 组可视化体积比 CSV](/av-cmame-20261030/visualization-quality.csv) · [公开资源 SHA256](/av-cmame-20261030/SHA256.json)

## 新版 FDM 迁移记录与后续核对

这次结果提供了**可完成时程、输入明确、有原始压力/流量和运动输出的工程对照基线**。它支持开始迁移，不等于迁移后的数值方法已经得到验证。

已有 FDM `real_av` 和过去的复现记录，但那些记录涉及其他运行、配置与网格。应以本次校验清单重新核对，而不是将旧记录中的“细网格/粗网格差异”直接当成本次已确认事实。后续仍按以下顺序逐项核对，不能用一次退出 0 代替数值等价性验证：

1. 固定本次源码、网格/标记/纤维/压力哈希、实际 80×80×128 网格和流量平面，导入同一输入并验证参考坐标和拓扑。
2. 单独核对原入口压力、Windkessel 状态机、两端反馈、对流路径及符号，再比较相同物理时刻的压力和流量。
3. 审计本构力符号、参考应力修正、纤维张压分支、P2 积分与耦合；以零载和短窗测试确认，不能仅靠相似的参数名判断等价。
4. 先复现原配置，再把 modified-invariant 材料、CBS43、Brinkman 加 tether 等新方案作为独立分支逐项加入，明确哪些物理或数值设置变了。
5. 通过有限值、分区 J/伸长、支持运动和通量检查后，再延长到开启、关闭与完整时程。

最初的参考坐标、233216 个四面体的拓扑、材料标记和纤维分量已逐项导入并与原版可视化参考数据校验，未重网格、平滑或归一化纤维，见 [初始输入导入审计](/av-cmame-20261030/fdm-input-import-audit.json)。随后导出完整的 465797 个 P2 自由度和每单元 64 积分点数据，核对材料力符号、旧对流和反馈路径，并修正两端留白。当前 FDM 已完成 1.635 s，但全域压力、回流及支撑畸变尚未与原版对齐，**仍不能称为数值复现成功**。
