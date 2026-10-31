# 复现排障

|现象|处理|
|---|---|
|缺QuadratureRulesData.h/FFC头文件|包内已带生成结果；先验证MANIFEST，不要随意改UFL版本|
|Boost::timer不存在|本包先找Boost再找DOLFIN，使用同一FENICS_ENV；别混系统头文件版BoostConfig|
|PETSC::petsc/SLEPC::slepc目标不存在|本包保留已验证的旧conda接口兼容处理；不是通用PETSc配置方案|
|Kokkos找不到CUDA::cuda_driver|已在子项目中先find_package(CUDAToolkit)，核对nvcc、driver和Kokkos前缀|
|NVCC日志格式化consteval报错|源码保留FMT_CONSTEVAL兼容定义；勿因此修改数值源文件|
|OpenMP编译标志缺失|保留CUDA目标-Xcompiler=-fopenmp；勿链接未匹配的Kokkos库|
|CMake4报旧策略/FindBoost错误|使用CMake3.27–3.31，推荐已验证3.28.3|
|unsupported GPU/no kernel image|主程序和原生Kokkos都要重建为目标架构，preflight会检查Kokkos头文件|
|找不到pressure.txt|必须从scripts/run.sh启动或设置NPUHEART_MV_PRESSURE_FILE为包内绝对路径|
|CUDA_VISIBLE_DEVICES未设置|显式选择空闲GPU；脚本不会猜测并占用已有任务的GPU|
|负P2J告警|本版本按用户实验要求只记告警，不中止、不裁剪J；不等于结果已通过质量检查|
|退出0但异常变形/非有限力|退出码不等于数值有效性；保留日志、输入和输出，用独立诊断检查|

MV96和之前MV旧分支包的差别：当前目标gfem_main_mv、Nx/Ny/Nz分别96/96/192、dt5e-6、beta1e8。不要套用旧包N_bg64、dt6.25e-6的说明。当前所有三个测试模式保持同一96网格和dt，只改变时长/步数。

输入恢复保持原H5几何、拓扑、材料、纤维。原始缺失XML边界默认值并未被证明与作者文件逐位相同；实际活动MV体积装配不调用该面载荷核。详细输入来源和核对保留在input_verification与SOURCE_PROVENANCE。
