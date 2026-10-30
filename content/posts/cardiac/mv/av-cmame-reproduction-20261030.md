---
title: "原版 CMAME 主动脉瓣：1.635 秒完整运行、四格动画与 FDM 迁移基线"
description: "复现原版 gfem_main_av：RTX A6000 上完成 327000 步，记录真实网格、环境修正、构建运行过程、完整动画和几何质量限制，并建立新版 FDM 的逐项对照基线。"
date: 2026-10-30T00:00:00+00:00
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

原版 `cmame-v100-2 2.zip` 中的 **`gfem_main_av` 已完成 327000 步，目标物理时间 1.635 s，退出码 0**。计算在 RTX A6000 上进行，UTC 开始于 2026-10-29 20:15:42，结束于 2026-10-30 03:33:06，启动至结束共 **7 小时 17 分 24 秒**。这里记录的是原版 CMAME 求解器，不是新版 FDM，也不是此前正弦压力驱动的 [av_glamv 直管试算](/posts/av-glamv-20261028/)。

**正常结束证明了这套源码、输入与环境可以完成时程，并不代表数值质量已验证。** 输出存在负的线性可视化单元体积比；完整 P2 积分点的 Jacobian 尚未核查。以下动画及曲线应作为复现和诊断证据。

## 完整四格动画

<video controls playsinline preload="metadata" poster="/av-cmame-20261030/opening.png" style="width:100%;height:auto"><source src="/av-cmame-20261030/av-four-panel.mp4" type="video/mp4">请下载 MP4 查看。</video>

[下载完整 MP4](/av-cmame-20261030/av-four-panel.mp4) · [开瓣画面](/av-cmame-20261030/opening.png) · [最后保存帧](/av-cmame-20261030/final.png) · [动画输入说明](/av-cmame-20261030/video-input.json)

动画覆盖 **0.000005–1.630005 s**。计算终点是 1.635 s，但每 1000 步保存一次场，最后完整流固配对帧为 1.630005 s；没有外推或补造最后约 0.005 s。共有 327 组完整配对状态，取每四组及最后一组，共 83 组，按物理时间线性插值为 241 帧、15 fps，播放约 16.07 秒。运动保持实际尺度。

- 左上：从高 z 入口观察瓣叶；右上：从低 z 出口观察。
- 左下：y = 4 cm 纵向切片的轴向速度 w，保留 +z 符号；固定色限 ±200 cm/s，超限颜色饱和。材料轮廓随当前变形更新。
- 右下：原生日志的入口压力、Windkessel 出口压力和 MAC 平面流量，时间游标与几何同步。

流量为 **z = 12.6875 cm 处整个 MAC 平面的原生离散积分，正方向 −z**，不是仅瓣口区域的通量。压力由 dyn/cm² 换算为 mmHg。不要把这条流量曲线解释成额外的瓣口守恒证明。

## 实际计算设置

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

当前还缺少按材料区域的完整 P2 积分点 J、主伸长、支持运动、旁路流和空间/时间收敛检查。本页不宣称实验验证、体积保持或生理准确性。

[原生日志抽样压力/流量 CSV](/av-cmame-20261030/pressure-flow.csv) · [83 组可视化体积比 CSV](/av-cmame-20261030/visualization-quality.csv) · [公开资源 SHA256](/av-cmame-20261030/SHA256.json)

## 新版 FDM 从这里开始迁移

这次结果提供了**可完成时程、输入明确、有原始压力/流量和运动输出的工程对照基线**。它支持开始迁移，不等于迁移后的数值方法已经得到验证。

已有 FDM `real_av` 和过去的复现记录，但那些记录涉及其他运行、配置与网格。应以本次校验清单重新核对，而不是将旧记录中的“细网格/粗网格差异”直接当成本次已确认事实。迁移按以下顺序推进：

1. 固定本次源码、网格/标记/纤维/压力哈希、实际 80×80×128 网格和流量平面，导入同一输入并验证参考坐标和拓扑。
2. 单独核对原入口压力、Windkessel 状态机、两端反馈、对流路径及符号，再比较相同物理时刻的压力和流量。
3. 审计本构力符号、参考应力修正、纤维张压分支、P2 积分与耦合；以零载和短窗测试确认，不能仅靠相似的参数名判断等价。
4. 先复现原配置，再把 modified-invariant 材料、CBS43、Brinkman 加 tether 等新方案作为独立分支逐项加入，明确哪些物理或数值设置变了。
5. 通过有限值、分区 J/伸长、支持运动和通量检查后，再延长到开启、关闭与完整时程。

本页发布时已建立此次运行的 FDM 对照记录；**尚未宣称新版 FDM 已复现这段 1.635 s 结果**。
