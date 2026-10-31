# npuheart MV96：源码、完整输入及编译运行包

这是2026-10-31完成的MV复现包：源代码基础为`npuheart/npuheart-4`的`81f1af089af9f52ea93bc4e5e985d62c44f60fc9`（2025-07-07），保留本次输出时的P2积分点J/乳头肌位移诊断，只记告警、不主动中止。

默认：**96×96×192，Nt=200000，T=1s，dt=5e-6s，tethering beta=1e8，flow_type=Tube1**。乳头肌通过原有tethering force约束，没有速度清零或坐标复位。未裁剪J，未改材料公式。

## 包里有什么

- `source/`：与实际8383完整运行逐文件SHA256匹配的源码，排除macOS旁车、登录和编辑器文件。
- `inputs/mesh/`：mesh.xdmf/mesh.h5、材料、边界、三份纤维XML；不是只有网格文件而缺材料。
- `inputs/pressure.txt`：该次运行实际使用的压力波形。
- `config/`：相对路径配置；full=1s、driven=0.04s、smoke=0.001s，均保持dt=5e-6及96网格。
- `scripts/`：校验、环境、依赖安装、Kokkos编译、程序编译、配置生成、运行及查状态。
- `docs/records/`：实际软件版本/精确conda包版本、完整周期退出记录、输入及源码哈希。

不包含GPU驱动、第三方预编译环境、Git登录、SSH/R2密钥或十几GB的原始输出。首次依赖安装需要联网。已生成的高斯积分和FFC头文件已经包含，默认不需要重跑Basix/FFC生成器。

## 1. 解压和校验

目标环境为**Linux x86_64 + NVIDIA CUDA GPU**。不是CPU/macOS求解器。实际验证环境：Ubuntu24.04、系统GCC13.3、系统CMake3.28.3、CUDA12.6.85、原生Kokkos4.3.01、DOLFIN/FFC2019.1、RTX4090。

```bash
unzip npuheart-mv96-repro-20261031.zip
cd npuheart-mv96-repro-20261031
python3 scripts/verify_bundle.py
```

请预留至少约25GB输出空间，更多空间便于保留日志和多次测试。8383的这次1s运行实测约4小时16分；另一机器耗时取决于GPU、CPU和输出IO。

## 2. 指定依赖位置与GPU架构

```bash
export MV_CUDA_ARCH=89                 # 4090；其他型号看docs/GPU_ARCHITECTURE.md
export GFEM_ENV="$HOME/gfem-env"
export FENICS_ENV="$HOME/miniconda3/envs/fenics-legacy"
export KOKKOS_NATIVE_PREFIX="$HOME/kokkos-4.3.01-sm${MV_CUDA_ARCH}"
export CMAKE_BIN=/usr/bin/cmake        # 必须CMake3.27–3.31；实际使用3.28.3
export MV_CC=/usr/bin/gcc
export MV_CXX=/usr/bin/g++
```

这些变量要在安装、编译、运行时保持一致。已有兼容环境可直接设置为自己的前缀，跳过安装。`scripts/env.sh`不修改`~/.bashrc`。默认nvcc为`$GFEM_ENV/bin/nvcc`；如使用独立CUDA安装，可另设`MV_NVCC=/usr/local/cuda-12.6/bin/nvcc`，并保证相关依赖可被找到。

## 3. 没有环境时先安装依赖

先自行安装Miniconda/Miniforge，以及系统CMake3和C++编译器。下面使用实际8383记录的conda包版本/build重建两个独立前缀，不覆盖已有环境：

```bash
export CONDA_EXE="$HOME/miniconda3/bin/conda"  # Miniforge用户改为实际路径
bash scripts/create_conda_envs.sh
bash scripts/install_kokkos.sh
```

Kokkos按所选架构独立编译，不能只改主程序架构却复用另一个架构的Kokkos。环境精确包清单见`docs/records/conda-*-exact-specs.txt`，完整记录见JSON。该包复用了已有8383依赖进行验证；**尚未在一台空白系统上重新安装全部依赖**，精确重建依赖仍取决于conda-forge是否保留对应Linux包。若环境求解失败，保留错误，不要混用DOLFINx与DOLFIN2019。

系统CMake4不适合这套旧依赖查找逻辑。若系统没有合适CMake，可建立单独工具环境安装`cmake=3.28`，再将`CMAKE_BIN`设为那个环境的cmake绝对路径；不要让GFEM环境里的CMake4替代它。

## 4. 编译

```bash
bash scripts/preflight.sh
MV_BUILD_JOBS=8 bash scripts/build.sh
```

生成`build/gfem_main_mv`。仅构建这个经过验证的MV入口，不要直接构建所有其他历史入口。高斯积分和UFL头文件默认直接使用包内版本；只有要主动重新生成旧FFC头文件时才设置`MV_REGENERATE_UFL=ON`。

切换GPU架构时，使用独立解压目录/构建目录和对应Kokkos前缀，避免旧CMake缓存。主程序、libgpu及Kokkos子构建由同一个`MV_CUDA_ARCH`配置。

## 5. 明确选择空闲GPU并试启动

```bash
nvidia-smi
CUDA_VISIBLE_DEVICES=0 bash scripts/run.sh smoke
```

`smoke`只有0.001s（200步），压力尚未开始加载；它仅验证环境、输入、链接和启动。非零压力短测：

```bash
CUDA_VISIBLE_DEVICES=0 bash scripts/run.sh driven
```

每次创建唯一运行目录，绝不覆盖旧结果。脚本会生成绝对路径JSON，并设置包内压力文件路径。GPU必须显式设置；脚本不再强制使用8383原来的GPU编号。

## 6. 后台跑1秒完整时程

```bash
mkdir -p records
CUDA_VISIBLE_DEVICES=0 nohup bash scripts/run.sh full > records/full-launcher.log 2>&1 < /dev/null &
echo $! > records/full-supervisor.pid
```

`runs/mv96_full_*/solver.log`是求解日志；同目录保存`config.json`、`exit_code`和`finished_utc`。数据在`runs/output/<id>/solid`及`data`。可用：

```bash
bash scripts/status.sh
```

主程序使用`Nt`和`T`决定dt；不需要手工编辑源码。完整时程1s尚没有本包可直接使用的FSI断点重启功能，不能拿可视化XDMF当作完整恢复点。

## 数值结果应怎样理解

这套96网格参数在8383正常走完1s、退出0，并产生可见开闭运动；但存在局部负P2积分点J（包含支持区域），**不等于所有单元质量合格**。诊断只是记录状态，不会因负J中止。材料、压力和恢复输入与作者当年手工成功配置是否完全一致仍未得到完整证明。

`docs/records/FULL_RUN_8383.json`保存实际完成记录、软件及二进制哈希。包内程序不是仓库2026年最新MV_2病例；也不是3月673f5a4分支或直接固定乳头肌的失败试验版。

四格可视化来源说明：保存的是P2解在线性节点上的可视化几何；P2积分点J由新增诊断独立计算。VTI有半网格原点偏移。流量若从VTI重构，必须标明重构方法，不能称为原生MAC守恒量。

更多排障见`docs/TROUBLESHOOTING.md`，输入恢复过程见`docs/input_restore_method.py`及`input_verification.json`。
