> 本说明来自已测试的私有可移植包。包的源码和网格未随本页公开；本页 A6000 完整运行已于 2026-10-30 结束，详情见 [计算记录](/posts/av-cmame-reproduction-20261030/)。4090 结果仍仅为短测。

# 原版 CMAME AV：输入、源码及可移植编译运行包

本包用于复现用户提供的 `cmame-v100-2 2.zip` 中的 **gfem_main_av**。包含当前Euclid原版AV实际使用的网格、边界/材料标记、三个纤维分量和入口压力波形，不使用8383历史测试中重新生成的替代数据。

## 包内内容

- `source/`：原版源码，附少量构建/路径适配；已包含Basix积分头文件和旧FFC生成的两个UFL头文件。
- `inputs/mesh/`：XDMF、其引用的HDF5、边界XML、材料XML、三个纤维XML。
- `inputs/pressure.txt`：原始AV入口压力波形，程序按原逻辑插值和换算单位。
- `config/smoke.template.json`：2000步、T=0.01s、dt=5e-6s。
- `config/full.template.json`：327000步、T=1.635s、dt=5e-6s。
- `scripts/`：依赖入口、可选安装、一键构建、配置展开、运行及输出检查脚本。
- `MANIFEST.json`：源文件/输入的SHA256。`docs/dependencies-8383.json`仅保存依赖包名称、版本与构建号，不含凭据。

压缩包不包含NVIDIA驱动和第三方库二进制；在全新Linux主机上仍需按下节安装依赖。在8383上优先复用现有环境，不覆盖原来的源码或计算结果。

## 8383已有依赖：直接编译并短测

```bash
unzip av-repro-20261029.zip
cd av-repro-20261029
python3 scripts/verify_bundle.py
bash scripts/build.sh > build.log 2>&1
CUDA_VISIBLE_DEVICES=1 bash scripts/run.sh smoke
```

GPU必须显式选择。此次测试计划使用物理GPU 1；运行前用`nvidia-smi`确认它空闲，不与其他任务竞争。

默认环境位置按HOME展开，可通过同名环境变量覆盖：

```bash
GFEM_ENV=$HOME/gfem-env                    # CUDA12.6、spdlog、fmt、muparser、Basix等
FENICS_ENV=$HOME/miniconda3/envs/fenics-legacy  # DOLFIN/FFC2019.1、PETSc、MPICH、Boost等
KOKKOS_NATIVE_PREFIX=$HOME/kokkos-4.3.01-ada89 # 原生sm89 Kokkos
```

构建脚本使用系统`/usr/bin/cmake`（此机3.28）和GCC13；避免conda环境中CMake4移除FindBoost造成的问题。构建强制使用Boost模块查找并先于DOLFIN定义Boost::timer，避免系统头文件版BoostConfig遮蔽conda二进制库；旧DOLFIN未定义的PETSc/SLEPc接口目标按原动态依赖补齐。顶层与Kokkos子构建都使用同一CMake和CUDA架构。Kokkos子构建先查找CUDAToolkit，避免已有Kokkos配置中的CUDA导入目标错误；OpenMP启用时给nvcc传入对应host标志，并处理旧fmt日志库的consteval兼容性。4090为89，A6000为86，V100为70；更换GPU时同时提供匹配架构的Kokkos安装，并设置`AV_CUDA_ARCH`。不可仅改顶层架构就认为Kokkos也匹配。

## 全新环境准备

需要Linux x86_64、支持CUDA12.6的NVIDIA驱动、系统GCC13、CMake3.27–3.31，以及Miniconda或Miniforge。可执行：

```bash
# 已有环境会跳过，不会删除或重置它们；首次安装需要网络。
bash scripts/install_deps.sh
bash scripts/build.sh
```

此安装脚本以4090/ADA89为目标。包中已有生成头文件，默认无需每次执行Basix/FFC。如需从UFL重新生成：

```bash
AV_REGENERATE_UFL=ON bash scripts/build.sh
# 重新生成积分规则（需对应Basix环境）：
(cd source/src/fem/include/fem && "$GFEM_ENV/bin/python" generate_quadrature_rules.py)
```

`docs/dependencies-8383.json`记录此次测试时的现有依赖版本；首次安装命令属于可执行依赖配方，不保证未来解析到逐包相同的构建。它不是离线依赖镜像。

## 完整周期与后台运行

短测试通过后，可以显式启动完整周期：

```bash
CUDA_VISIBLE_DEVICES=1 nohup bash scripts/run.sh full > full_launcher.log 2>&1 < /dev/null &
echo $!
```

每次生成新的运行ID，实际绝对路径配置在`runs/<id>/config.json`；日志、开始/结束UTC时间和退出码也在该目录。场输出位于`runs/output/<id>/`。短测有900秒保护超时，完整周期无该超时。无需修改HOME、shell登录文件或原有`mesh-cardiology`目录；脚本通过`NPUHEART_AV_PRESSURE_FILE`显式指向包内波形。

检查：

```bash
source scripts/env_8383.sh
cat runs/<id>/exit_code
python3 scripts/verify_vti.py runs/output/<id>/data > fluid_validation.json
# 此步需要numpy和h5py：
python3 scripts/verify_solid.py runs/output/<id>/solid/view.xdmf > solid_validation.json
```

退出码0仅表示程序结束。检查脚本只检查保存帧中的字段与可视化四面体，不能代替所有P2积分点、每个时间步或按材料分区的完整数值验证。

## 实际模型与复现限制

实际背景网格在`source/src/main_av.cpp`写死为 **80×80×128**、域8×8×14cm；JSON `N_bg`虽被读取，不改变该尺寸。原参数：beta=5e8、kappa=5e6、muf=0.04、rhof=1；P2四面体、原积分规则、原AV瓣叶材料与纤维、原Windkessel状态机。

保留原算法，不加入CBS43、改材料、J裁剪、重网格或替代波形。当前Euclid运行输出的部分线性可视化单元存在负体积比；包的可运行性不代表完整周期或几何质量合格。该体积比不是完整P2积分点J。

四项核对：两端z法向反馈已存在（rho/dt，含原时间窗回流处理）；modified-invariant AV应力未启用；插值/分布为原PhiIB4而非CBS43；支持区域5/17存在拉格朗日惩罚，未确认有对应的Eulerian Brinkman体掩膜。详见`docs/provenance.json`及`docs/portability.patch`。

8383采用CUDA12.6/Kokkos4.3.01，Euclid采用CUDA12.4/Kokkos4.3.0；即使输入完全相同，也不承诺逐位相同。比较须核对输入SHA256、配置、实际网格、软件与GPU架构。

## 此包的8383实测结果

2026-10-30已在物理GPU1（RTX4090）上重新构建并用本包原始输入完成2000步短测：退出码0，开始00:03:00 UTC、结束00:04:51 UTC，约111秒，末次流体时间0.009995s。两帧流体和固体检查字段均为有限值。0.005005s保存帧最大位移约0.0961365cm；可视化体积比范围0.836612–65.644480、无非正值。极大值来自此前Euclid也观察到的极小单元，不能仅凭退出码0宣称数值质量合格。完整结果见docs/VALIDATED_8383.json及两份字段检查JSON。

本次只在8383执行短测试，未自动启动8383完整周期；完整配置和启动命令已提供。Euclid原运行结果未修改。

实际遇到的问题、原因和已集成修正汇总在 [TROUBLESHOOTING.md](TROUBLESHOOTING.md)。
