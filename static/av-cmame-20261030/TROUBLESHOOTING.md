# 本次实际排障记录与复现要点

本页记录AV/MV在Euclid与8383实际遇到的问题，供以后换环境复用。修正已写入包内构建文件和脚本，不要求用户重复手工修改。

|现象|实际原因|包内处理|
|---|---|---|
|缺少QuadratureRulesData.h|原仓库忽略了Basix生成文件|打包验证过的生成头文件及生成器，默认直接使用|
|缺少LagrangeFirst/Second.h或并行编译次序不确定|UFL头文件未生成或依赖被注释|打包旧FFC2019.1头文件，另提供有依赖顺序的可选重新生成|
|顶层改了架构，运行仍出现架构不匹配|Kokkos子构建和Kokkos安装自身仍是旧架构|同一架构传入CUDA目标与子构建，并显式选择原生sm89 Kokkos|
|DOLFIN引用Boost::timer但目标不存在|系统头文件版BoostConfig遮蔽conda二进制Boost，且查找顺序不当|Boost模块查找先于DOLFIN，显式指向旧FEniCS前缀|
|PETSC::petsc或SLEPC::slepc导入目标缺失|旧conda DOLFIN包引用但未定义这些CMake接口目标|仅为当前网格/自由度用法补接口目标；实际库仍由libdolfin动态依赖加载。直接调用PETSc的其他程序不可照搬为空接口|
|CUDA::cuda_driver缺少库位置，或Kokkos包含目录含换行|现有原生KokkosConfig生成了不完整的CUDA导入目标|先find_package(CUDAToolkit)，让Kokkos复用正确目标，不编辑共享Kokkos安装|
|Kokkos提示启用OpenMP但编译器未启用|CUDA翻译单元没有收到host OpenMP选项|Kokkos有OPENMP时向nvcc传-Xcompiler=-fopenmp|
|nvcc编译日志格式化时出现consteval错误|旧spdlog内置fmt与nvcc C++20兼容性|在相关目标禁用FMT_CONSTEVAL日志编译优化，不修改数值算法|
|系统CUDA12.0或conda CMake4导致兼容问题|现有系统默认工具不是验证过的组合|显式使用GFEM环境CUDA12.6与系统CMake3.28/GCC13|
|程序启动后找不到pressure.txt|源码写死旧账户绝对路径|通过NPUHEART_AV_PRESSURE_FILE或NPUHEART_MV_PRESSURE_FILE指向包内波形|
|Euclid退出后出现PMIx权限警告|旧OpenMPI/PMIx临时状态目录问题|私有TMPDIR加PMIX_MCA_gds=hash通过独立诊断；8383的MPICH不等同于此环境|

## 必须保留的区别

- AV源码把背景网格写死为80×80×128，JSON的N_bg不控制它。MV当前入口使用N_bg×N_bg×2N_bg。
- 3391 JSON模板beta=1e6，批量脚本覆盖为1e8；这是不同配置，不能混称同一个测试。
- MV模板T1/Nt160000对应dt6.25e-6，并非6.75e-6。当前包的三个模式都保持dt6.25e-6。
- MV波形从0.020s之后开始线性上升，0.01s短测没有加载。必须把零压、加载短测和完整周期结果分开报告。
- 原版输出的P2解只保存了线性可视化网格上的节点值。线性四面体体积比不是全部P2积分点J；退出0、无NaN、总体积接近1也不证明每个固体区域质量合格。
- VTI点数据的原点和半网格偏移必须按文件读取，不能把所有文件都当作零原点MAC面速度。
- 原版输出间隔含浮点除法再取整，不同dt下保存帧时间可能略偏离0.005s整数倍。配对必须使用保存的物理时间。
- NaN和随后发生的CUDA非法地址不直接证明唯一根因是时间步；保留失败日志，做对照，不用J裁剪或软化掩盖故障。

## 包与凭据

压缩包只包含源码、输入、说明、脚本与检查记录，不包含R2/GitHub令牌、SSH密钥、shell登录文件或整个账号环境。包上传至私有Cloudflare R2，以限时单对象链接传输；签名链接不写入包或日志。文件SHA256和源版本写在MANIFEST及provenance中。

后续完整周期结果：MV在Euclid使用dt6.25e-6的重跑也在0.205456s异常退出134，末段报CUDA非法地址；不能把减小dt当作已完成的修复。8383的0.04s短测不覆盖该失败时段。
