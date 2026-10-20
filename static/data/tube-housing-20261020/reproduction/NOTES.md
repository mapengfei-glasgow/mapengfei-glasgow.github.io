# 复现资料范围

COMMAND.json、PROVENANCE.json 和 SHA256 对应实际计算；gpu.patch 是相对 REVISIONS.json 中 GPU 提交的当前补丁，包含默认关闭的后续 Sarah 参数。本文两组命令未开启 Sarah stress，均为纯 tethering。

下载包不包含完整网格、全部 VTI/固体快照或 CUDA 可执行文件。原始 glamv_hex_r2 是生成数据，不能仅凭 geometry 仓库提交号恢复；必须使用保留的输入文件并核对 MESH_SHA256.json，或已有原始 R2 数据配合提取脚本。提取脚本按原工作区目录布局定位路径，移植时需要调整 ROOT/SRC/OUT。replay.py 可显式指定二进制、网格和新输出目录，不依赖旧绝对路径；不加 --run 仅打印命令。

源码依赖 CUDA、CMake、HDF5 和原 fdm-3d-v1 头文件。先检出 REVISIONS.json 对应提交，再在 GPU 仓库执行 git apply /path/to/reproduction/gpu.patch；使用独立构建目录。当前源码支持显式 --domain，tube-disc 需要此选项。FMAD=ON。GPU 架构必须匹配实际设备；更换硬件允许浮点舍入差异。

图来自相同计算的 5 s 快照，压力已换算为 mmHg；tube-disc 图只能用于诊断，因为 disk 有单元翻转。
