// ============================================================================
// demo/tube_flow_scale.cu — GPU 泊肃叶管流验证 (对标 CPU demo/tube_flow_scale.cpp)
//
//   目标: 与 CPU 版 tube_flow_scale.cpp 在相同配置下输出 bitwise 一致
//         (sim.log 逐行 diff + 探针 CSV 逐列 diff)。
//
//   与 CPU 的对齐策略:
//     - 核心推进: GPU 求解器 (ChorinStokesSolverCUDA, 与 CPU 镜像实现)
//     - 探针输出: 在 host 端用与 CPU 完全相同的串行逻辑计算 (下载 u/v/w/p
//       与固体 u/f_solid 到 host, 相同的浮点累加顺序) → 保证 bitwise
//
//   用法 (与 CPU 相同参数):
//     ./tube_flow_scale --N 32 --T 0.5 --dt 1e-4 --beta-body 1e6 \
//         --data src/ibm/data/tube_short/ --out out_tube_scale_gpu/
// ============================================================================

#include "ns_solver_cuda.h"
#include "solid_data_gpu.h"
#include "spread_gpu.h"
#include "interp_gpu.h"
#include "common_gpu.h"
#include "args.h"
#include "config.h"
#include "fdm/mac_grid.h"
#include "ibm/io.hpp"
#include "ibm/io_vti.h"
#include "stats/demo_stats.h"

#include <cstdio>
#include <cmath>
#include <algorithm>
#include <vector>
#include <string>
#include <sstream>
#include <iomanip>
#include <fstream>
#include <sys/stat.h>

using namespace fdm3d_cuda;
using namespace fdm3d_gpu;
using namespace fdm3d::ibm::io;
using Real = double;

// ============================================================================
// Zero MMS (无制造解, 物理问题; 壁面速度 0)
// ============================================================================
struct TubeMMS {
    __host__ __device__ static Real ue(Real,Real,Real,Real){return 0;}
    __host__ __device__ static Real ve(Real,Real,Real,Real){return 0;}
    __host__ __device__ static Real we(Real,Real,Real,Real){return 0;}
    __host__ __device__ static Real pe(Real,Real,Real,Real){return 0;}
    __host__ __device__ static Real fx(Real,Real,Real,Real){return 0;}
    __host__ __device__ static Real fy(Real,Real,Real,Real){return 0;}
    __host__ __device__ static Real fz(Real,Real,Real,Real){return 0;}
};

// ============================================================================
// Config — 与 CPU tube_flow_scale 完全一致 (默认短管数据, 侧壁封闭)
// ============================================================================
struct Config : BaseConfig {
    double pmax = 1.0, ramp = 0.0;
    double r_in = 0.06;         // 管内径 (匹配 tube.geo / tube_short.geo)
    double beta_body = 0.0;
    double beta_disk = -1.0, disk_bulk = 0.0; // marker 2 only; bulk energy = k/2*(ln J)^2
    bool   sarah_wall_stress = false; // existing Sarah modified stress on tube and housing
    bool   gpu_coupling = false; // --gpu-coupling: device-resident rigid tether path
    bool   rigid_all = true;    // 全管 body penalty (PK1 跳过)
    double mu_s = 2.0, lambda_s = 3.0;
    int    poi_nvc = 8;
    int    probe_every = 10;
    std::string diag_path;      // --diag 插桩输出 (每子阶段范数, 与 CPU 同格式)

    std::vector<double> fixed_domain, reference_center; // paired overrides preserve tube placement with asymmetric housing
    double sx = 1.0, sy = 1.0, sz = 1.0;   // 缩放 (1=原始几何)
    int    nx = 0, ny = 0, nz = 0;         // 每方向格数 (0=自动)
    double pad[6] = {0.15, 0.15, 0.15, 0.15, 0.0, 0.0};  // 与 CPU 一致

    Config() {
        N = 32; nu = 0.01; T = 0.02; dt = 1e-4; beta = 1.0;
        every = 50;
#ifdef GEOMETRY_SRC_DIR
        data_dir = GEOMETRY_SRC_DIR "/src/ibm/data/tube/";
#else
        data_dir = "src/ibm/data/tube/";
#endif
        out_dir  = "out_tube_scale_gpu/";
    }
};

Config parse_args(int argc, char** argv) {
    Args a(argc, argv);
    Config c;
    c.parse_common(a);
    c.pmax       = a.get_double("--pmax", c.pmax);
    c.ramp       = a.get_double("--ramp", c.ramp);
    c.r_in       = a.get_double("--rin", c.r_in);
    c.beta_body  = a.get_double("--beta-body", c.beta_body);
    c.beta_disk = a.get_double("--beta-disk", c.beta_disk);
    c.disk_bulk = a.get_double("--disk-bulk", c.disk_bulk);
    c.rigid_all  = !a.has("--elastic");
    c.gpu_coupling = a.has("--gpu-coupling");
    c.sarah_wall_stress = a.has("--sarah-wall-stress");
    if (c.sarah_wall_stress && (!c.gpu_coupling || c.disk_bulk!=0)) {
        fprintf(stderr, "--sarah-wall-stress requires GPU coupling and excludes --disk-bulk\n");
        std::exit(1);
    }
    if (c.gpu_coupling && !c.rigid_all) {
        fprintf(stderr, "--gpu-coupling currently requires rigid tethering (no --elastic)\n");
        std::exit(1);
    }
    c.mu_s       = a.get_double("--mu", c.mu_s);
    c.lambda_s   = a.get_double("--lambda", c.lambda_s);
    c.poi_nvc    = a.get_int("--nvc", c.poi_nvc);
    c.probe_every = a.get_int("--probe-every", c.probe_every);
    c.diag_path  = a.get_str("--diag");
    c.fixed_domain = a.get_double_list("--domain");
    c.reference_center = a.get_double_list("--reference-center");
    if (!c.fixed_domain.empty() || !c.reference_center.empty()) {
        if (c.fixed_domain.size()!=3 || c.reference_center.size()!=3 ||
            !std::all_of(c.fixed_domain.begin(), c.fixed_domain.end(), [](double v){return std::isfinite(v) && v>0;}) ||
            !std::all_of(c.reference_center.begin(), c.reference_center.end(), [](double v){return std::isfinite(v);})) {
            fprintf(stderr, "--domain and --reference-center require three valid values each\n");
            std::exit(1);
        }
    }
    if ((!c.gpu_coupling && (a.has("--beta-disk") || a.has("--disk-bulk"))) ||
        !std::isfinite(c.disk_bulk) || c.disk_bulk<0 ||
        !std::isfinite(c.beta_disk) || (a.has("--beta-disk") && c.beta_disk<=0)) {
        fprintf(stderr, "Disk controls require GPU coupling, positive tether and nonnegative bulk modulus\n");
        std::exit(1);
    }
    c.sx = a.get_double("--sx", c.sx);
    c.sy = a.get_double("--sy", c.sy);
    c.sz = a.get_double("--sz", c.sz);
    c.nx = a.get_int("--nx", c.nx);
    c.ny = a.get_int("--ny", c.ny);
    c.nz = a.get_int("--nz", c.nz);
    auto pad = a.get_double_list("--pad");
    if (!pad.empty()) {
        if (pad.size() == 1)      { for (int k = 1; k < 6; ++k) pad.push_back(pad[0]); }
        else if (pad.size() != 6) { fprintf(stderr, "--pad 需要 1 或 6 个值\n"); std::exit(1); }
        for (int k = 0; k < 6; ++k) c.pad[k] = pad[k];
    }
    if (c.ramp < 0) c.ramp = c.T;
    if (c.sx <= 0 || c.sy <= 0 || c.sz <= 0) { fprintf(stderr, "--sx/--sy/--sz 必须为正\n"); std::exit(3); }
    return c;
}

// ============================================================================
// host 端: IB-4 核 (与 CPU delta_functions.h::ib4_kernel 相同)
// ============================================================================
static inline double ib4(double r) {
    r = std::fabs(r);
    if (r < 1.0) { double r2 = r * r;
        return (3.0 - 2.0 * r + std::sqrt(1.0 + 4.0 * r - 4.0 * r2)) / 8.0; }
    if (r < 2.0) { double r2 = r * r;
        return (5.0 - 2.0 * r - std::sqrt(-7.0 + 12.0 * r - 4.0 * r2)) / 8.0; }
    return 0.0;
}

// ============================================================================
// host 端: 点插值 (与 CPU ib_interpolate_mac 相同的 ii→jj→kk 累加顺序, 保证 bitwise)
// ============================================================================
static void interp_point(
    const double* u, const double* v, const double* w,
    int Nxf, int Nyf, int Nzf, int Nxv, int Nyv, int Nzv, int Nxw, int Nyw, int Nzw,
    double hx, double hy, double hz, double X, double Y, double Z,
    double& uo, double& vo, double& wo)
{
    double rhx = 1.0 / hx, rhy = 1.0 / hy, rhz = 1.0 / hz;
    uo = vo = wo = 0.0;
    {   double rx = X*rhx + 1.0, ry = Y*rhy + 0.5, rz = Z*rhz + 0.5;
        int i0 = (int)std::floor(rx), j0 = (int)std::floor(ry), k0 = (int)std::floor(rz);
        for (int ii = -1; ii <= 2; ++ii) { int i = i0 + ii; if ((unsigned)i >= (unsigned)Nxf) continue;
          double wx = ib4(std::fabs(rx - i));
        for (int jj = -1; jj <= 2; ++jj) { int j = j0 + jj; if ((unsigned)j >= (unsigned)Nyf) continue;
          double wy = ib4(std::fabs(ry - j));
        for (int kk = -1; kk <= 2; ++kk) { int k = k0 + kk; if ((unsigned)k >= (unsigned)Nzf) continue;
          uo += u[i + j*Nxf + k*Nxf*Nyf] * wx * wy * ib4(std::fabs(rz - k));
        }}}
    }
    {   double rx = X*rhx + 0.5, ry = Y*rhy + 1.0, rz = Z*rhz + 0.5;
        int i0 = (int)std::floor(rx), j0 = (int)std::floor(ry), k0 = (int)std::floor(rz);
        for (int ii = -1; ii <= 2; ++ii) { int i = i0 + ii; if ((unsigned)i >= (unsigned)Nxv) continue;
          double wx = ib4(std::fabs(rx - i));
        for (int jj = -1; jj <= 2; ++jj) { int j = j0 + jj; if ((unsigned)j >= (unsigned)Nyv) continue;
          double wy = ib4(std::fabs(ry - j));
        for (int kk = -1; kk <= 2; ++kk) { int k = k0 + kk; if ((unsigned)k >= (unsigned)Nzv) continue;
          vo += v[i + j*Nxv + k*Nxv*Nyv] * wx * wy * ib4(std::fabs(rz - k));
        }}}
    }
    {   double rx = X*rhx + 0.5, ry = Y*rhy + 0.5, rz = Z*rhz + 1.0;
        int i0 = (int)std::floor(rx), j0 = (int)std::floor(ry), k0 = (int)std::floor(rz);
        for (int ii = -1; ii <= 2; ++ii) { int i = i0 + ii; if ((unsigned)i >= (unsigned)Nxw) continue;
          double wx = ib4(std::fabs(rx - i));
        for (int jj = -1; jj <= 2; ++jj) { int j = j0 + jj; if ((unsigned)j >= (unsigned)Nyw) continue;
          double wy = ib4(std::fabs(ry - j));
        for (int kk = -1; kk <= 2; ++kk) { int k = k0 + kk; if ((unsigned)k >= (unsigned)Nzw) continue;
          wo += w[i + j*Nxw + k*Nxw*Nyw] * wx * wy * ib4(std::fabs(rz - k));
        }}}
    }
}

// ============================================================================
// host 端: 压力三线性插值 (与 CPU tube_flow_scale::interp_p 相同)
// ============================================================================
static double interp_p_cc(
    const double* p, int Nxc, int Nyc, double hx, double hy, double hz,
    int nx, int ny, int nz, double X, double Y, double Z)
{
    auto idx = [Nxc, Nyc](int i, int j, int k) { return i + j * Nxc + k * Nxc * Nyc; };
    double rx = X / hx + 0.5, ry = Y / hy + 0.5, rz = Z / hz + 0.5;
    int i0 = (int)std::floor(rx), j0 = (int)std::floor(ry), k0 = (int)std::floor(rz);
    i0 = std::clamp(i0, 1, nx - 1);
    j0 = std::clamp(j0, 1, ny - 1);
    k0 = std::clamp(k0, 1, nz - 1);
    double fx = rx - i0, fy = ry - j0, fz = rz - k0;
    double c000 = p[idx(i0,   j0,   k0  )], c100 = p[idx(i0+1, j0,   k0  )];
    double c010 = p[idx(i0,   j0+1, k0  )], c110 = p[idx(i0+1, j0+1, k0  )];
    double c001 = p[idx(i0,   j0,   k0+1)], c101 = p[idx(i0+1, j0,   k0+1)];
    double c011 = p[idx(i0,   j0+1, k0+1)], c111 = p[idx(i0+1, j0+1, k0+1)];
    double c00 = c000 + (c100 - c000) * fx, c10 = c010 + (c110 - c010) * fx;
    double c01 = c001 + (c101 - c001) * fx, c11 = c011 + (c111 - c011) * fx;
    double c0 = c00 + (c10 - c00) * fy,     c1 = c01 + (c11 - c01) * fy;
    return c0 + (c1 - c0) * fz;
}

// ============================================================================
// host 端: divergence L2 (与 CPU ns_solver::divergence_l2 相同累加顺序)
// ============================================================================
static double divergence_l2_host(
    const double* u, const double* v, const double* w,
    int nx, int ny, int nz, int Nxf, int Nyf, int Nx_yf, int Ny_yf, int Nx_zf, int Ny_zf,
    int Nx_cc, int Ny_cc, double hx, double hy, double hz)
{
    double ix = 1.0 / hx, iy = 1.0 / hy, iz = 1.0 / hz;
    auto XF = [Nxf, Nyf](int i, int j, int k) { return i + j * Nxf + k * Nxf * Nyf; };
    auto YF = [Nx_yf, Ny_yf](int i, int j, int k) { return i + j * Nx_yf + k * Nx_yf * Ny_yf; };
    auto ZF = [Nx_zf, Ny_zf](int i, int j, int k) { return i + j * Nx_zf + k * Nx_zf * Ny_zf; };
    double s = 0.0, dv = hx * hy * hz;
    for (int k = 1; k <= nz; ++k)
    for (int j = 1; j <= ny; ++j)
    for (int i = 1; i <= nx; ++i) {
        double d = (u[XF(i+1,j,k)] - u[XF(i,j,k)]) * ix
                 + (v[YF(i,j+1,k)] - v[YF(i,j,k)]) * iy
                 + (w[ZF(i,j,k+1)] - w[ZF(i,j,k)]) * iz;
        s += d * d;
    }
    return std::sqrt(s * dv);
}

// ============================================================================
// host 端: 力散布 (与 CPU ib_spread_mac 相同的 ii→jj→kk 累加顺序, 保证 bitwise)
// ============================================================================
static void spread_point(
    double* fu, double* fv, double* fw,
    int Nxf, int Nyf, int Nzf, int Nxv, int Nyv, int Nzv, int Nxw, int Nyw, int Nzw,
    double hx, double hy, double hz, double X, double Y, double Z,
    double Fx, double Fy, double Fz)
{
    double rhx = 1.0 / hx, rhy = 1.0 / hy, rhz = 1.0 / hz;
    double inv_h3 = rhx * rhy * rhz;
    {   double rx = X*rhx + 1.0, ry = Y*rhy + 0.5, rz = Z*rhz + 0.5;
        int i0 = (int)std::floor(rx), j0 = (int)std::floor(ry), k0 = (int)std::floor(rz);
        double Fx_h3 = Fx * inv_h3;
        for (int ii = -1; ii <= 2; ++ii) { int i = i0 + ii; if ((unsigned)i >= (unsigned)Nxf) continue;
          double wx = ib4(std::fabs(rx - i));
        for (int jj = -1; jj <= 2; ++jj) { int j = j0 + jj; if ((unsigned)j >= (unsigned)Nyf) continue;
          double wy = ib4(std::fabs(ry - j));
        for (int kk = -1; kk <= 2; ++kk) { int k = k0 + kk; if ((unsigned)k >= (unsigned)Nzf) continue;
          fu[i + j*Nxf + k*Nxf*Nyf] += Fx_h3 * wx * wy * ib4(std::fabs(rz - k));
        }}}
    }
    {   double rx = X*rhx + 0.5, ry = Y*rhy + 1.0, rz = Z*rhz + 0.5;
        int i0 = (int)std::floor(rx), j0 = (int)std::floor(ry), k0 = (int)std::floor(rz);
        double Fy_h3 = Fy * inv_h3;
        for (int ii = -1; ii <= 2; ++ii) { int i = i0 + ii; if ((unsigned)i >= (unsigned)Nxv) continue;
          double wx = ib4(std::fabs(rx - i));
        for (int jj = -1; jj <= 2; ++jj) { int j = j0 + jj; if ((unsigned)j >= (unsigned)Nyv) continue;
          double wy = ib4(std::fabs(ry - j));
        for (int kk = -1; kk <= 2; ++kk) { int k = k0 + kk; if ((unsigned)k >= (unsigned)Nzv) continue;
          fv[i + j*Nxv + k*Nxv*Nyv] += Fy_h3 * wx * wy * ib4(std::fabs(rz - k));
        }}}
    }
    {   double rx = X*rhx + 0.5, ry = Y*rhy + 0.5, rz = Z*rhz + 1.0;
        int i0 = (int)std::floor(rx), j0 = (int)std::floor(ry), k0 = (int)std::floor(rz);
        double Fz_h3 = Fz * inv_h3;
        for (int ii = -1; ii <= 2; ++ii) { int i = i0 + ii; if ((unsigned)i >= (unsigned)Nxw) continue;
          double wx = ib4(std::fabs(rx - i));
        for (int jj = -1; jj <= 2; ++jj) { int j = j0 + jj; if ((unsigned)j >= (unsigned)Nyw) continue;
          double wy = ib4(std::fabs(ry - j));
        for (int kk = -1; kk <= 2; ++kk) { int k = k0 + kk; if ((unsigned)k >= (unsigned)Nzw) continue;
          fw[i + j*Nxw + k*Nxw*Nyw] += Fz_h3 * wx * wy * ib4(std::fabs(rz - k));
        }}}
    }
}

// ============================================================================
// host 端: 体惩罚力 (与 CPU SolidData::assemble_body_penalty 相同, 逐单元串行)
//   注意: 只累加, 不清零 (清零由 host_pk1/调用处完成, 与 CPU 一致)
// ============================================================================
static void host_body_penalty(
    const std::vector<int64_t>& dofmaps, const std::vector<int64_t>& cell_marker,
    const std::vector<double>& J, const std::vector<double>& weights,
    const std::vector<double>& bval_ref,
    const std::vector<double>& u, std::vector<double>& f_solid,
    size_t nc, size_t nq, size_t nb, double beta, uint64_t mm,
    const std::vector<double>* qp_phi = nullptr,
    const std::vector<double>* qp_wJ = nullptr)
{
    std::vector<double> td(u.size());
    for (size_t i = 0; i < u.size(); ++i) td[i] = beta * u[i];
    for (size_t e = 0; e < nc; ++e) {
        if (mm != ~uint64_t(0) && !((uint64_t(1) << (uint64_t)cell_marker[e]) & mm)) continue;
        const int64_t* d = &dofmaps[e * nb];
        double Jdet = std::fabs(J[e]);
        double f_local[30] = {0};
        for (size_t q = 0; q < nq; ++q) {
            const double* bq = &bval_ref[q * nb * 3];
            double tx = 0, ty = 0, tz = 0;
            for (size_t a = 0; a < nb; ++a) {
                double phi = qp_phi ? (*qp_phi)[(e*nq+q)*nb+a] : bq[a*3];
                size_t n = (size_t)d[a];
                tx += td[n*3+0] * phi; ty += td[n*3+1] * phi; tz += td[n*3+2] * phi;
            }
            double wJ = qp_wJ ? (*qp_wJ)[e*nq+q] : weights[q] * Jdet;
            for (size_t a = 0; a < nb; ++a) {
                double phi = qp_phi ? (*qp_phi)[(e*nq+q)*nb+a] : bq[a*3];
                f_local[a*3+0] += wJ * tx * phi;
                f_local[a*3+1] += wJ * ty * phi;
                f_local[a*3+2] += wJ * tz * phi;
            }
        }
        for (size_t a = 0; a < nb; ++a) {
            size_t n = (size_t)d[a];
            f_solid[n*3+0] += f_local[a*3+0];
            f_solid[n*3+1] += f_local[a*3+1];
            f_solid[n*3+2] += f_local[a*3+2];
        }
    }
}

// ============================================================================
// host 端: PK1 内力组装 (与 CPU SolidData::assemble_pk1 相同, 逐单元串行)
//   cell_marker 语义与 CPU 一致: 尺寸不等于 num_cells 时视为全 0 (CPU load 的守卫)
//   → 若全 0, pk1_mask=~14 时 marker-0 全部通过 (CPU rigid_all 实际行为)
// ============================================================================
static void host_pk1(
    const std::vector<int64_t>& dofmaps, const std::vector<int64_t>& cell_marker,
    const std::vector<double>& J, const std::vector<double>& inv_H,
    const std::vector<double>& weights, const std::vector<double>& bderiv_ref,
    const std::vector<double>& Xref, const std::vector<double>& u,
    std::vector<double>& f_solid,
    size_t nc, size_t nq, size_t nb, double mu, double lambda, uint64_t mm)
{
    std::fill(f_solid.begin(), f_solid.end(), 0.0);
    for (size_t e = 0; e < nc; ++e) {
        if (mm != ~uint64_t(0) && !((uint64_t(1) << (uint64_t)cell_marker[e]) & mm)) continue;
        const int64_t* d = &dofmaps[e * nb];
        const double* Hi = &inv_H[e * 9];
        double Jdet = std::fabs(J[e]);
        double x_cur[30];
        for (size_t a = 0; a < nb; ++a) {
            size_t ni = (size_t)d[a];
            x_cur[a*3+0] = Xref[ni*3+0] + u[ni*3+0];
            x_cur[a*3+1] = Xref[ni*3+1] + u[ni*3+1];
            x_cur[a*3+2] = Xref[ni*3+2] + u[ni*3+2];
        }
        double f_local[30] = {0};
        for (size_t q = 0; q < nq; ++q) {
            const double* gr = &bderiv_ref[q * nb * 3];
            double dphi[30];
            for (size_t a = 0; a < nb; ++a) {
                double r0 = gr[a*3+0], r1 = gr[a*3+1], r2 = gr[a*3+2];
                dphi[a*3+0] = r0*Hi[0] + r1*Hi[3] + r2*Hi[6];
                dphi[a*3+1] = r0*Hi[1] + r1*Hi[4] + r2*Hi[7];
                dphi[a*3+2] = r0*Hi[2] + r1*Hi[5] + r2*Hi[8];
            }
            double F[9] = {0};
            for (size_t a = 0; a < nb; ++a)
                for (int dd = 0; dd < 3; ++dd)
                    for (int k = 0; k < 3; ++k)
                        F[dd*3+k] += x_cur[a*3+dd] * dphi[a*3+k];
            double detF = F[0]*(F[4]*F[8]-F[5]*F[7]) - F[1]*(F[3]*F[8]-F[5]*F[6]) + F[2]*(F[3]*F[7]-F[4]*F[6]);
            double invDet = 1.0 / detF;
            double invF[9] = {
                (F[4]*F[8]-F[5]*F[7])*invDet, (F[2]*F[7]-F[1]*F[8])*invDet, (F[1]*F[5]-F[2]*F[4])*invDet,
                (F[5]*F[6]-F[3]*F[8])*invDet, (F[0]*F[8]-F[2]*F[6])*invDet, (F[2]*F[3]-F[0]*F[5])*invDet,
                (F[3]*F[7]-F[4]*F[6])*invDet, (F[1]*F[6]-F[0]*F[7])*invDet, (F[0]*F[4]-F[1]*F[3])*invDet};
            double invFT[9] = {invF[0],invF[3],invF[6], invF[1],invF[4],invF[7], invF[2],invF[5],invF[8]};
            double lnJ = std::log(detF);
            double P[9];
            for (int i = 0; i < 9; ++i) P[i] = mu*(F[i]-invFT[i]) + lambda*lnJ*invFT[i];
            double wJ = weights[q] * Jdet;
            for (size_t a = 0; a < nb; ++a) {
                f_local[a*3+0] += wJ*(P[0]*dphi[a*3+0]+P[1]*dphi[a*3+1]+P[2]*dphi[a*3+2]);
                f_local[a*3+1] += wJ*(P[3]*dphi[a*3+0]+P[4]*dphi[a*3+1]+P[5]*dphi[a*3+2]);
                f_local[a*3+2] += wJ*(P[6]*dphi[a*3+0]+P[7]*dphi[a*3+1]+P[8]*dphi[a*3+2]);
            }
        }
        for (size_t a = 0; a < nb; ++a) {
            size_t ni = (size_t)d[a];
            f_solid[ni*3+0] += f_local[a*3+0];
            f_solid[ni*3+1] += f_local[a*3+1];
            f_solid[ni*3+2] += f_local[a*3+2];
        }
    }
}

// ============================================================================
// main
// ============================================================================
int main(int argc, char** argv) {
    Config cfg = parse_args(argc, argv);
    if (!is_power_of_two(cfg.N)) { fprintf(stderr, "N 必须为 2 的幂\n"); return 2; }
    mkdir(cfg.out_dir.c_str(), 0755);

    // ---- 1. 加载固体 ----
    printf("  [tube_flow_scale_gpu] loading solid...\n");
    SolidDataGPU<double> solid; solid.load(cfg.data_dir);
    solid.mu = cfg.mu_s; solid.lambda = cfg.lambda_s;
    size_t nn = solid.num_nodes;
    // host 端固体状态 (bitwise 耦合): 从 GPU solid 下载 FE 数组 + 维护 u/f/v
    std::vector<int64_t> dofmaps_h, cell_marker_h;
    std::vector<Real> J_h, weights_h, bval_ref_h, inv_H_h, bderiv_ref_h, Xref_h, u_h, f_solid_h, v_solid_h;
    std::vector<double> qp_phi_h, qp_wJ_h;
    if (solid.mixed && !cfg.rigid_all) {
        fprintf(stderr, "Mixed meshes currently require tether-only rigid-all mode in this demo\n");
        return 3;
    }

    BBox3 bb0 = compute_solid_bbox(solid);
    printf("  bbox (before): %.4f x %.4f x %.4f\n", bb0.lx(), bb0.ly(), bb0.lz());

    // ---- 2. 各向异性缩放 (与 CPU 相同) ----
    if (cfg.sx != 1.0 || cfg.sy != 1.0 || cfg.sz != 1.0) {
        std::vector<double> Xh(nn * 3);
        cudaMemcpy(Xh.data(), solid.X_ref.d, nn * 3 * sizeof(double), cudaMemcpyDeviceToHost);
        for (size_t i = 0; i < nn; ++i) {
            Xh[i*3+0] *= cfg.sx; Xh[i*3+1] *= cfg.sy; Xh[i*3+2] *= cfg.sz;
        }
        cudaMemcpy(solid.X_ref.d, Xh.data(), nn * 3 * sizeof(double), cudaMemcpyHostToDevice);
        // 同步更新 J / inv_H (CPU 缩放逻辑)
        double Sdet = cfg.sx * cfg.sy * cfg.sz;
        double si[3] = {1.0/cfg.sx, 1.0/cfg.sy, 1.0/cfg.sz};
        std::vector<double> Jv(solid.num_cells), iH(solid.num_cells * 9);
        cudaMemcpy(Jv.data(), solid.J.d, solid.num_cells * sizeof(double), cudaMemcpyDeviceToHost);
        cudaMemcpy(iH.data(), solid.inv_H.d, solid.num_cells * 9 * sizeof(double), cudaMemcpyDeviceToHost);
        for (size_t e = 0; e < solid.num_cells; ++e) {
            Jv[e] *= Sdet;
            for (int j = 0; j < 3; ++j)
                for (int k = 0; k < 3; ++k)
                    iH[e*9 + j*3 + k] *= si[k];
        }
        cudaMemcpy(solid.J.d, Jv.data(), solid.num_cells * sizeof(double), cudaMemcpyHostToDevice);
        cudaMemcpy(solid.inv_H.d, iH.data(), solid.num_cells * 9 * sizeof(double), cudaMemcpyHostToDevice);
    }

    BBox3 bb = compute_solid_bbox(solid);
    printf("  bbox (after):  %.4f x %.4f x %.4f\n", bb.lx(), bb.ly(), bb.lz());

    // ---- 3. 域设置 (与 CPU tube_flow_scale 相同: z 方向 3·2^k) ----
    double Lx = bb.lx() * (1.0 + cfg.pad[0] + cfg.pad[1]);
    double Ly = bb.ly() * (1.0 + cfg.pad[2] + cfg.pad[3]);
    double Lz = bb.lz() * (1.0 + cfg.pad[4] + cfg.pad[5]);

    if (!cfg.fixed_domain.empty()) {
        Lx=cfg.fixed_domain[0]; Ly=cfg.fixed_domain[1]; Lz=cfg.fixed_domain[2];
    }
    {   // 平移固体到域中心
        double dcx = Lx*0.5, dcy = Ly*0.5, dcz = Lz*0.5;
        double scx = (bb.xmin+bb.xmax)*0.5, scy = (bb.ymin+bb.ymax)*0.5, scz = (bb.zmin+bb.zmax)*0.5;
        if (!cfg.reference_center.empty()) {
            scx=cfg.reference_center[0]; scy=cfg.reference_center[1]; scz=cfg.reference_center[2];
        }
        std::vector<double> Xh(nn * 3);
        cudaMemcpy(Xh.data(), solid.X_ref.d, nn * 3 * sizeof(double), cudaMemcpyDeviceToHost);
        for (size_t i = 0; i < nn; ++i) {
            Xh[i*3+0] += dcx - scx; Xh[i*3+1] += dcy - scy; Xh[i*3+2] += dcz - scz;
        }
        cudaMemcpy(solid.X_ref.d, Xh.data(), nn * 3 * sizeof(double), cudaMemcpyHostToDevice);

        // ---- host 端固体 (bitwise 耦合用): 从 GPU solid 下载 (缩放+平移后) ----
        {
            size_t nc = solid.num_cells, nq = solid.num_qp, nb = solid.num_basis;
            dofmaps_h.resize(nc * nb);
            cell_marker_h.assign(nc, 0);   // 与 CPU load_solid_data 一致: 尺寸!=num_cells 时全 0
            J_h.resize(nc);
            weights_h.resize(nq);
            bval_ref_h.resize(nq * nb * 3);
            inv_H_h.resize(nc * 9);
            bderiv_ref_h.resize(nq * nb * 3);
            cudaMemcpy(dofmaps_h.data(), solid.dofmaps.d, nc*nb*sizeof(int64_t), cudaMemcpyDeviceToHost);
            if (solid.cell_marker.n == nc) {   // CPU 守卫: 尺寸匹配才使用 marker
                std::vector<int64_t> cm_tmp(nc);
                cudaMemcpy(cm_tmp.data(), solid.cell_marker.d, nc*sizeof(int64_t), cudaMemcpyDeviceToHost);
                for (size_t e = 0; e < nc; ++e) cell_marker_h[e] = (int)cm_tmp[e];
            }
            cudaMemcpy(J_h.data(), solid.J.d, nc*sizeof(Real), cudaMemcpyDeviceToHost);
            cudaMemcpy(weights_h.data(), solid.weights.d, nq*sizeof(Real), cudaMemcpyDeviceToHost);
            cudaMemcpy(bval_ref_h.data(), solid.basis_val_ref.d, nq*nb*3*sizeof(Real), cudaMemcpyDeviceToHost);
            // Native Q1/mixed meshes carry physical quadrature weights per cell.
            if (solid.mixed) {
                qp_phi_h.resize(nc*nq*nb); qp_wJ_h.resize(nc*nq);
                cudaMemcpy(qp_phi_h.data(), solid.qp_phi.d, nc*nq*nb*sizeof(double), cudaMemcpyDeviceToHost);
                cudaMemcpy(qp_wJ_h.data(), solid.qp_wJ.d, nc*nq*sizeof(double), cudaMemcpyDeviceToHost);
            }
            cudaMemcpy(inv_H_h.data(), solid.inv_H.d, nc*9*sizeof(Real), cudaMemcpyDeviceToHost);
            cudaMemcpy(bderiv_ref_h.data(), solid.bderiv_ref.d, nq*nb*3*sizeof(Real), cudaMemcpyDeviceToHost);
            Xref_h.resize(nn*3);
            cudaMemcpy(Xref_h.data(), solid.X_ref.d, nn*3*sizeof(Real), cudaMemcpyDeviceToHost);
            u_h.assign(nn*3, Real(0));
            f_solid_h.assign(nn*3, Real(0));
            v_solid_h.assign(nn*3, Real(0));
        }
    }

    auto pow2   = [](int v) { int p = 1; while (p < v) p *= 2; return p; };
    auto pow3x2 = [](int v) { int p = 3; while (p < v) p *= 2; return p; };
    auto is_pow3x2 = [](int v) { while (v > 1 && v % 2 == 0) v /= 2; return v == 3; };
    double Lmax = std::max({Lx, Ly, Lz}), href = Lmax / cfg.N;
    int Nx = cfg.nx > 0 ? cfg.nx : pow2((int)std::ceil(Lx / href));
    int Ny = cfg.ny > 0 ? cfg.ny : pow2((int)std::ceil(Ly / href));
    int Nz = cfg.nz > 0 ? cfg.nz : pow3x2((int)std::ceil(Lz / href));
    if (!is_power_of_two(Nx) || !is_power_of_two(Ny) || !is_pow3x2(Nz)) {
        fprintf(stderr, "Nx/Ny 须为 2 的幂, Nz 须为 3·2^k: %d %d %d\n", Nx, Ny, Nz); return 4;
    }
    double hx = Lx / Nx, hy = Ly / Ny, hz = Lz / Nz;
    printf("  L = (%.6f, %.6f, %.6f)  N = (%d, %d, %d)  h = (%.6f, %.6f, %.6f)\n",
           Lx, Ly, Lz, Nx, Ny, Nz, hx, hy, hz);

    // ---- 4. 求解器 + 压力孔口 (仅 z 面, 侧壁封闭) ----
    int nsteps = (int)(cfg.T / cfg.dt + 0.5);
    printf("=== GPU tube_flow_scale ===  nu=%.4g dt=%.3g T=%.3g steps=%d\n",
           cfg.nu, cfg.dt, cfg.T, nsteps);

    ChorinStokesSolverCUDA<Real, TubeMMS> solver(Nx, Ny, Nz, hx, hy, hz, cfg.dt, cfg.nu);
    solver.enable_convection(true);   // 与 CPU make_nodal_ibm_solver (enable_convection(true)) 对齐
    solver.set_mg_params(3, cfg.poi_nvc, 2);
    // 插桩: 流体子阶段逐步范数 (与 CPU 同格式, 供 bitwise diff)
    if (!cfg.diag_path.empty()) {
        FILE* f = fopen(cfg.diag_path.c_str(), "w");
        if (f) solver.set_diag(f);
        else fprintf(stderr, "无法打开 --diag %s\n", cfg.diag_path.c_str());
    }
    auto& g = solver.grid();
    g.zero_all();
    g.set_bc_u(make_dirichlet_bc<Real>(0));
    g.set_bc_v(make_dirichlet_bc<Real>(0));
    g.set_bc_w(make_dirichlet_bc<Real>(0));

    double cx = Lx * 0.5, cy = Ly * 0.5;
    double r_h = cfg.r_in * 0.5 * (cfg.sx + cfg.sy);
    auto p_inlet = [pmax = cfg.pmax, ramp = cfg.ramp](double t) {
        return pmax * std::min(1.0, t / ramp);
    };
    // 仅 z 面入口/出口 (侧壁封闭 → 管外静止, 与 CPU 一致)
    solver.add_pressure_hole(4, cx, cy, r_h, p_inlet(0.0));
    solver.add_pressure_hole(5, cx, cy, r_h, 0.0);
    solver.finalize_pressure_holes();

    // ---- 5. 刚体 (rigid_all: 全部 body penalty, PK1 跳过) ----
    int rigid_mask = make_marker_mask({1, 2, 3});
    if (cfg.gpu_coupling) {
        for (int marker : cell_marker_h) {
            if (marker < 1 || marker > 3) {
                fprintf(stderr, "GPU rigid coupling requires all cell markers in {1,2,3}\n");
                return 5;
            }
        }
    }
    if (cfg.rigid_all) {
        if (cfg.beta_body <= 0) cfg.beta_body = cfg.beta;
        printf("  rigid_all: beta_body=%.1e (marker {1,2,3}, PK1 跳过)\n", cfg.beta_body);
    }

    // ---- 6. 固体初始位移/力缓冲 (与 CPU 一致: 初始 f_solid=0, IBM 力=0, 不预散布) ----
    double *d_Xc, *d_Us;
    cudaMalloc(&d_Xc, nn * 3 * sizeof(double));
    cudaMalloc(&d_Us, nn * 3 * sizeof(double));
    cudaMemset(solid.u.d, 0, nn * 3 * sizeof(double));
    cudaMemset(solid.f_solid.d, 0, nn * 3 * sizeof(double));
    launch_add_positions(solid.X_ref.d, solid.u.d, d_Xc, nn);
    solver.zero_ibm_force();
    cudaDeviceSynchronize();

    // ---- 7. 探针点 (与 CPU 相同坐标/名称) ----
    double R = cfg.r_in * cfg.sx;
    struct ProbePt { double x, y, z; std::string name; };
    std::vector<ProbePt> cl_pts, rad_pts, rad_z03, rad_z07, p_pts;
    char nm[32];
    for (int i = 0; i < 9; ++i) { double zf = 0.1 + 0.1 * i; std::snprintf(nm, sizeof nm, "z%.2f", zf);
        cl_pts.push_back({cx, cy, zf*Lz, nm}); p_pts.push_back({cx, cy, zf*Lz, nm}); }
    const double rf[10] = {0.00, 0.17, 0.33, 0.50, 0.67, 0.75, 0.83, 0.88, 0.92, 0.95};
    for (int i = 0; i < 10; ++i) { std::snprintf(nm, sizeof nm, "r%02d", (int)std::lround(rf[i]*100.0)); rad_pts.push_back({cx + R*rf[i], cy, 0.5*Lz, nm}); }
    const double rf6[6] = {0.00, 0.33, 0.67, 0.83, 0.92, 0.95};
    for (int i = 0; i < 6; ++i) { std::snprintf(nm, sizeof nm, "r%02d", (int)std::lround(rf6[i]*100.0)); rad_z03.push_back({cx + R*rf6[i], cy, 0.3*Lz, nm}); rad_z07.push_back({cx + R*rf6[i], cy, 0.7*Lz, nm}); }

    // track_node (与 CPU 相同: r≈r_h 且 z≈0.5Lz)
    size_t track_node = 0;
    {
        std::vector<double> Xh(nn * 3);
        cudaMemcpy(Xh.data(), solid.X_ref.d, nn * 3 * sizeof(double), cudaMemcpyDeviceToHost);
        double best = 1e30;
        for (size_t i = 0; i < nn; ++i) {
            double dxr = Xh[i*3+0] - cx, dyr = Xh[i*3+1] - cy;
            double r = std::hypot(dxr, dyr);
            double dz = std::abs(Xh[i*3+2] - 0.5*Lz);
            double score = std::abs(r - r_h) + 2.0 * dz;
            if (score < best) { best = score; track_node = i; }
        }
    }

    // ---- 8. 输出文件 ----
    FILE* log_f = fopen((cfg.out_dir + "sim.log").c_str(), "w");
    std::ofstream fcl(cfg.out_dir + "probe_centerline.csv");
    std::ofstream frad(cfg.out_dir + "probe_radial.csv");
    std::ofstream frad03(cfg.out_dir + "probe_radial_z0.3.csv");
    std::ofstream frad07(cfg.out_dir + "probe_radial_z0.7.csv");
    std::ofstream fpr(cfg.out_dir + "probe_pressure.csv");
    std::ofstream fq(cfg.out_dir + "probe_flow.csv");
    // header (与 CPU 完全一致)
    fcl << "step,t";
    for (auto& p : cl_pts) fcl << ",w_" << p.name; fcl << ",u_max\n";
    frad << "step,t";
    for (auto& p : rad_pts) frad << ",w_" << p.name; frad << ",ur_wall\n";
    frad03 << "step,t";
    for (auto& p : rad_z03) frad03 << ",w_" << p.name; frad03 << "\n";
    frad07 << "step,t";
    for (auto& p : rad_z07) frad07 << ",w_" << p.name; frad07 << "\n";
    fpr << "step,t";
    for (auto& p : p_pts) fpr << ",p_" << p.name; fpr << "\n";
    fq << "step,t,p_in,Q_in,Q_out\n";

    // ---- 固体/流体快照 (与 CPU FsiWriter 输出对齐) ----
    {
        int64_t meta[3] = {(int64_t)nn, (int64_t)solid.num_cells, (int64_t)solid.num_basis};
        write_binary(cfg.out_dir + "meta.bin", meta, 3);
        write_binary(cfg.out_dir + "dofmaps.bin", dofmaps_h.data(), dofmaps_h.size());
        write_binary(cfg.out_dir + "ref_nodes.bin", Xref_h.data(), Xref_h.size());
    }
    fdm3d::FluidWriter fw;
    fw.init(cfg.out_dir, g.nx(), g.ny(), g.nz(), hx, hy, hz, cfg.dt);

    // ---- 数据统计 ----
    fdm3d::stats::DemoStats stats("experiments.db", "tube_flow_scale_gpu", {
        {"model", "tube_flow_scale"},
        {"device", "gpu"},
        {"N", cfg.N},
        {"nu", cfg.nu},
        {"dt", cfg.dt},
        {"T", cfg.T},
        {"pmax", cfg.pmax},
        {"ramp", cfg.ramp},
        {"beta_body", cfg.beta_body},
        {"mu_s", cfg.mu_s},
        {"lambda_s", cfg.lambda_s},
        {"rigid_all", cfg.rigid_all},
        {"gpu_coupling", cfg.gpu_coupling},
        {"sarah_wall_stress", cfg.sarah_wall_stress},
        {"beta_disk", cfg.beta_disk}, {"disk_bulk", cfg.disk_bulk},
        {"sx", cfg.sx},
        {"sy", cfg.sy},
        {"sz", cfg.sz},
    });

    // host 端流场缓冲
    int Nxf = g.Nx_xf(), Nyf = g.Ny_xf(), Nzf = g.Nz_xf();
    int Nxv = g.Nx_yf(), Nyv = g.Ny_yf(), Nzv = g.Nz_yf();
    int Nxw = g.Nx_zf(), Nyw = g.Ny_zf(), Nzw = g.Nz_zf();
    int Nxc = g.Nx_cc(), Nyc = g.Ny_cc(), Nzc = g.Nz_cc();
    int nx = g.nx(), ny = g.ny(), nz = g.nz();
    std::vector<double> uh(g.size_xf()), vh(g.size_yf()), wh(g.size_zf()), ph(g.size_cc());
    std::vector<double> Uh(nn * 3), Fh(nn * 3);

    const char* hdr = "  %6s %8s %8s %25s %8s %8s %8s %8s %8s\n";
    printf(hdr, "step", "t", "p_in", "center", "|u|max", "|u|²", "|f|max", "|f|²", "|div|");
    if (log_f) fprintf(log_f, hdr, "step", "t", "p_in", "center", "|u|max", "|u|²", "|f|max", "|f|²", "|div|");

    CudaArray<int64_t> sarah_markers;
    if (cfg.sarah_wall_stress) {
        std::vector<int64_t> markers(cell_marker_h.begin(),cell_marker_h.end());
        for (auto& marker : markers) {
            if (marker!=1 && marker!=2) {
                fprintf(stderr, "Sarah wall stress requires extracted tube(1)/housing(2) markers\n");
                return 6;
            }
            if (marker==2) marker=42; // restore physical source marker for constitutive dispatch
        }
        sarah_markers.upload(markers.data(),markers.size());
        solid.material=4; solid.smv.stress_form=1; solid.smv.beta_s=Real(5e6);
        solid.smv.C10_post=Real(502); solid.Jclip=Real(0); solid.smv.Jclip=Real(0);
        printf("Sarah wall stress: modified NH C10=502, beta_s=5e6, no J clipping\n");
    }
    if (cfg.gpu_coupling) {
        printf("Coupling backend: GPU (anisotropic IB4, rigid body tether)\n");
    }

    // ---- 9. 主循环 (GPU 推进 + host 端 bitwise 探针) ----
    for (int step = 0; step <= nsteps; ++step) {
        double t = step * cfg.dt;
        // 时变入口压力 (ramp 斜坡)。与 CPU 一致: 输出时使用上一时刻 patch,
        // 推进前才刷新到当前 t (CPU 在 fluid.step() 开头 refresh_hole_values(t_))。
        double p_disp = p_inlet(t);

        if (step % cfg.every == 0 || step == nsteps) {
            // 下载数据到 host
            cudaMemcpy(uh.data(), g.u_dev(), g.size_xf() * sizeof(double), cudaMemcpyDeviceToHost);
            cudaMemcpy(vh.data(), g.v_dev(), g.size_yf() * sizeof(double), cudaMemcpyDeviceToHost);
            cudaMemcpy(wh.data(), g.w_dev(), g.size_zf() * sizeof(double), cudaMemcpyDeviceToHost);
            cudaMemcpy(ph.data(), g.p_dev(), g.size_cc() * sizeof(double), cudaMemcpyDeviceToHost);
            cudaMemcpy(Uh.data(), solid.u.d, nn * 3 * sizeof(double), cudaMemcpyDeviceToHost);
            cudaMemcpy(Fh.data(), solid.f_solid.d, nn * 3 * sizeof(double), cudaMemcpyDeviceToHost);
            cudaDeviceSynchronize();

            // 固体范数 (与 CPU 相同累加)
            double u2 = 0, umax = 0, f2 = 0, fmax = 0;
            for (size_t i = 0; i < nn; ++i) {
                double ux = Uh[i*3+0], uy = Uh[i*3+1], uz = Uh[i*3+2];
                double fx = Fh[i*3+0], fy = Fh[i*3+1], fz = Fh[i*3+2];
                u2 += ux*ux + uy*uy + uz*uz;
                f2 += fx*fx + fy*fy + fz*fz;
                umax = std::max({umax, std::abs(ux), std::abs(uy), std::abs(uz)});
                fmax = std::max({fmax, std::abs(fx), std::abs(fy), std::abs(fz)});
            }
            // track_node 位置
            std::vector<double> Xh(nn * 3);
            cudaMemcpy(Xh.data(), solid.X_ref.d, nn * 3 * sizeof(double), cudaMemcpyDeviceToHost);
            double cx_t = Xh[track_node*3+0] + Uh[track_node*3+0];
            double cy_t = Xh[track_node*3+1] + Uh[track_node*3+1];
            double cz_t = Xh[track_node*3+2] + Uh[track_node*3+2];
            double div = divergence_l2_host(uh.data(), vh.data(), wh.data(),
                        nx, ny, nz, Nxf, Nyf, Nxv, Nyv, Nxw, Nyw, Nxc, Nyc, hx, hy, hz);

            // 固体 Xc + 流体 VTI (与 CPU FsiWriter::write_snapshot 对应)。
            std::vector<double> Xc(nn * 3);
            for (size_t i = 0; i < nn; ++i) {
                Xc[i*3+0] = Xh[i*3+0] + Uh[i*3+0];
                Xc[i*3+1] = Xh[i*3+1] + Uh[i*3+1];
                Xc[i*3+2] = Xh[i*3+2] + Uh[i*3+2];
            }
            {
                std::ostringstream fn;
                fn << cfg.out_dir << "Xc_" << std::setw(6) << std::setfill('0') << step << ".bin";
                write_binary(fn.str(), Xc.data(), Xc.size());
            }
            {
                fdm3d::MACGrid3D<double> tg(nx, ny, nz, hx, hy, hz);
                // 同步压力孔口 patch mask, 否则 FluidWriter 会把孔口平面法向速度写成 0。
                for (int face = 0; face < 6; ++face) {
                    std::vector<unsigned char> pm = g.download_p_patch_mask(face);
                    bool any = false;
                    for (unsigned char m : pm) if (m) { any = true; break; }
                    if (any) { std::vector<double> pv(pm.size(), 0.0); tg.set_p_patch(face, pm, pv); }
                }
                std::copy(uh.begin(), uh.end(), tg.u_data());
                std::copy(vh.begin(), vh.end(), tg.v_data());
                std::copy(wh.begin(), wh.end(), tg.w_data());
                std::copy(ph.begin(), ph.end(), tg.p_data());
                std::vector<double> fuh(g.size_xf()), fvh(g.size_yf()), fwh(g.size_zf());
                cudaMemcpy(fuh.data(), solver.ibm_fu(), g.size_xf() * sizeof(double), cudaMemcpyDeviceToHost);
                cudaMemcpy(fvh.data(), solver.ibm_fv(), g.size_yf() * sizeof(double), cudaMemcpyDeviceToHost);
                cudaMemcpy(fwh.data(), solver.ibm_fw(), g.size_zf() * sizeof(double), cudaMemcpyDeviceToHost);
                fw.write(tg, step, fuh.data(), fvh.data(), fwh.data());
            }

            char line[256];
            snprintf(line, sizeof(line),
                     "  %6d %8.4f %8.4f (%7.4f,%7.4f,%7.4f) %8.2e %8.4e %8.2e %8.4e %8.2e\n",
                     step, t, p_disp, cx_t, cy_t, cz_t, umax, u2, fmax, f2, div);
            fputs(line, stdout); fflush(stdout);
            stats.log(step, {{"t", t}, {"p_in", p_disp}, {"center_x", cx_t},
                             {"center_y", cy_t}, {"center_z", cz_t}, {"umax", umax},
                             {"u2", u2}, {"fmax", fmax}, {"f2", f2}, {"div", div}});
            if (log_f) { fputs(line, log_f); fflush(log_f); }

            // 探针 (与 CPU 相同计算, bitwise)
            if (step % cfg.probe_every == 0 || step == nsteps) {
                fcl << step << "," << std::scientific << std::setprecision(6) << t;
                double w_cen = 0;
                for (size_t pi = 0; pi < cl_pts.size(); ++pi) {
                    double u=0, v=0, w=0;
                    interp_point(uh.data(), vh.data(), wh.data(),
                        Nxf, Nyf, Nzf, Nxv, Nyv, Nzv, Nxw, Nyw, Nzw,
                        hx, hy, hz, cl_pts[pi].x, cl_pts[pi].y, cl_pts[pi].z, u, v, w);
                    if (pi == 4) w_cen = w;
                    fcl << "," << w;
                }
                fcl << "," << umax << "\n";

                frad << step << "," << std::scientific << std::setprecision(6) << t;
                double w_axis = 0;
                for (size_t pi = 0; pi < rad_pts.size(); ++pi) {
                    double u=0, v=0, w=0;
                    interp_point(uh.data(), vh.data(), wh.data(),
                        Nxf, Nyf, Nzf, Nxv, Nyv, Nzv, Nxw, Nyw, Nzw,
                        hx, hy, hz, rad_pts[pi].x, rad_pts[pi].y, rad_pts[pi].z, u, v, w);
                    if (pi == 0) w_axis = w;
                    frad << "," << w;
                }
                frad << "\n";

                frad03 << step << "," << std::scientific << std::setprecision(6) << t;
                for (auto& p : rad_z03) {
                    double u=0, v=0, w=0;
                    interp_point(uh.data(), vh.data(), wh.data(),
                        Nxf, Nyf, Nzf, Nxv, Nyv, Nzv, Nxw, Nyw, Nzw,
                        hx, hy, hz, p.x, p.y, p.z, u, v, w);
                    frad03 << "," << w;
                }
                frad03 << "\n";

                frad07 << step << "," << std::scientific << std::setprecision(6) << t;
                for (auto& p : rad_z07) {
                    double u=0, v=0, w=0;
                    interp_point(uh.data(), vh.data(), wh.data(),
                        Nxf, Nyf, Nzf, Nxv, Nyv, Nzv, Nxw, Nyw, Nzw,
                        hx, hy, hz, p.x, p.y, p.z, u, v, w);
                    frad07 << "," << w;
                }
                frad07 << "\n";

                std::vector<double> pp(p_pts.size(), 0.0);
                fpr << step << "," << std::scientific << std::setprecision(6) << t;
                for (size_t pi = 0; pi < p_pts.size(); ++pi) { pp[pi] = interp_p_cc(ph.data(), Nxc, Nyc, hx, hy, hz, nx, ny, nz, p_pts[pi].x, p_pts[pi].y, p_pts[pi].z); fpr << "," << pp[pi]; }
                fpr << "\n";

                // 流量: host 端复现 CPU z-face 孔口积分 (与 CPU 相同: 逐项 s*w*dA 累加)
                double qin = 0, qout = 0;
                {
                    auto in_hole = [&](double a, double b, double c1, double c2, double rr) {
                        double d1 = a - c1, d2 = b - c2; return d1*d1 + d2*d2 <= rr*rr; };
                    // z_low (face4): k=1, s=-1; z_high (face5): k=nz+1, s=+1
                    double dA = hx * hy;
                    double q4 = 0, q5 = 0;
                    for (int j = 1; j <= ny; ++j)
                    for (int i = 1; i <= nx; ++i) {
                        double xc = (i - 0.5) * hx, yc = (j - 0.5) * hy;
                        if (in_hole(xc, yc, cx, cy, r_h)) q4 += ((-1.0) * wh[i + j*Nxw + 1*Nxw*Nyw]) * dA;
                        if (in_hole(xc, yc, cx, cy, r_h)) q5 += (( 1.0) * wh[i + j*Nxw + (nz+1)*Nxw*Nyw]) * dA;
                    }
                    qin  = q4;
                    qout = q5;
                }
                fq << step << "," << std::scientific << std::setprecision(6) << t
                   << "," << p_disp << "," << qin << "," << qout << "\n";

                // GPU 相对泊肃叶解析解的每步误差 (w_axis = (R²/4μ)·|dp/dz|)
                double dpz = (pp[0] - pp[8]) / (0.8 * Lz);       // z=0.1Lz..0.9Lz 压力梯度
                double R_an = cfg.r_in * cfg.sx;                  // 管半径
                double w_an = (R_an * R_an) / (4.0 * cfg.nu) * std::abs(dpz);
                double w_err = (w_an > 1e-30) ? (w_cen - w_an) / w_an : 0.0;
                double Q_an = 3.14159265358979323846 * std::pow(R_an, 4) * std::abs(dpz) / (8.0 * cfg.nu);
                double Q_err = (Q_an > 1e-30) ? (qout - Q_an) / Q_an : 0.0;
                printf("  [gpu-err] step=%d t=%.4f  w_cen=%.6e w_an=%.6e w_rel=%+.3e  "
                       "Q_out=%.6e Q_an=%.6e Q_rel=%+.3e  dp/dz=%.6e\n",
                       step, t, w_cen, w_an, w_err, qout, Q_an, Q_err, dpz);

                double dp1 = (pp[0]-pp[2])/(0.2*Lz), dp2 = (pp[2]-pp[4])/(0.2*Lz), dp3 = (pp[4]-pp[6])/(0.2*Lz);
                printf("  [probe] t=%.4f w_cen(z=.5Lz)=%.4e w_axis=%.4e (match: %d)  "
                       "p(.1/.3/.5/.7/.9Lz)=(%.4e,%.4e,%.4e,%.4e,%.4e)  "
                       "dp/dz=(%.4e,%.4e,%.4e)  Q_in=%+.4e Q_out=%+.4e\n",
                       t, w_cen, w_axis, (std::abs(w_cen-w_axis) < 1e-12) ? 1 : 0,
                       pp[0], pp[2], pp[4], pp[6], pp[8], dp1, dp2, dp3, qin, qout);
                if (log_f) fprintf(log_f,
                       "  [probe] t=%.4f w_cen(z=.5Lz)=%.4e w_axis=%.4e (match: %d)  "
                       "p(.1/.3/.5/.7/.9Lz)=(%.4e,%.4e,%.4e,%.4e,%.4e)  "
                       "dp/dz=(%.4e,%.4e,%.4e)  Q_in=%+.4e Q_out=%+.4e\n",
                       t, w_cen, w_axis, (std::abs(w_cen-w_axis) < 1e-12) ? 1 : 0,
                       pp[0], pp[2], pp[4], pp[6], pp[8], dp1, dp2, dp3, qin, qout);
            }
        }

        if (step == nsteps) break;
        // 推进前刷新入口压力 (对应 CPU fluid.step() 内的 refresh_hole_values(t_))。
        {
            double p_now = p_inlet(t);
            solver.hole_val_[4].assign(solver.hole_mask_[4].size(), p_now);
            solver.refresh_hole_values();
        }
        // ---- 推进 (后): host 端固体耦合 (bitwise 对标 CPU NodalIBMSolver::step) ----
        solver.step();
        if (cfg.gpu_coupling) {
            // Match host ordering: interpolate at X^n, update u, then spread at X^{n+1}.
            launch_add_positions(solid.X_ref.d, solid.u.d, d_Xc, nn);
            interp_velocity_aniso(g, d_Xc, d_Us, nn, hx, hy, hz);
            launch_update_displacement(solid.u.d, d_Us, nn, Real(cfg.dt));
            if (cfg.sarah_wall_stress) {
                // Constitutive dispatch uses original {1,42}; tether still uses compact {1,2}.
                std::swap(solid.cell_marker,sarah_markers);
                launch_assemble_pk1(solid); // synchronous; clears and assembles both components
                std::swap(solid.cell_marker,sarah_markers);
            } else if (cfg.disk_bulk > 0) {
                // Existing mixed-element SFRH kernel with mu=0: P=k*ln(J)*F^{-T}.
                solid.mu=Real(0); solid.lambda=Real(cfg.disk_bulk);
                launch_assemble_pk1(solid, 1<<2); // clears forces, affects disk only
            } else CUDA_CHECK(cudaMemset(solid.f_solid.d, 0, nn*3*sizeof(Real)));
            if (cfg.beta_disk >= 0) {
                launch_assemble_body_penalty(solid, Real(cfg.beta_body), rigid_mask & ~(1<<2));
                launch_assemble_body_penalty(solid, Real(cfg.beta_disk), 1<<2);
            } else if (cfg.beta_body > 0)
                launch_assemble_body_penalty(solid, Real(cfg.beta_body), rigid_mask);
            launch_add_positions(solid.X_ref.d, solid.u.d, d_Xc, nn);
            solver.zero_ibm_force();
            spread_force_aniso(g, solver.ibm_fu(), solver.ibm_fv(), solver.ibm_fw(),
                d_Xc, solid.f_solid.d, nn, hx, hy, hz, Real(cfg.beta));
            CUDA_CHECK(cudaGetLastError());
        } else {
            int nx = g.nx(), ny = g.ny(), nz = g.nz();
            int Nxf = g.Nx_xf(), Nyf = g.Ny_xf(), Nzf = g.Nz_xf();
            int Nxv = g.Nx_yf(), Nyv = g.Ny_yf(), Nzv = g.Nz_yf();
            int Nxw = g.Nx_zf(), Nyw = g.Ny_zf(), Nzw = g.Nz_zf();
            std::vector<Real> uh(g.size_xf()), vh(g.size_yf()), wh(g.size_zf());
            g.download_u(uh); g.download_v(vh); g.download_w(wh);
            // interp (CPU 顺序 ii→jj→kk)
            for (size_t i = 0; i < nn; ++i) {
                Real X = Xref_h[i*3+0] + u_h[i*3+0];
                Real Y = Xref_h[i*3+1] + u_h[i*3+1];
                Real Z = Xref_h[i*3+2] + u_h[i*3+2];
                interp_point(uh.data(), vh.data(), wh.data(),
                    Nxf, Nyf, Nzf, Nxv, Nyv, Nzv, Nxw, Nyw, Nzw,
                    hx, hy, hz, X, Y, Z,
                    v_solid_h[i*3+0], v_solid_h[i*3+1], v_solid_h[i*3+2]);
            }
            // advance
            for (size_t i = 0; i < nn * 3; ++i) u_h[i] += v_solid_h[i] * cfg.dt;
            // forces (复刻 CPU NodalIBMSolver::step: PK1 mask=~body_mask, body_penalty)
            {
                std::fill(f_solid_h.begin(), f_solid_h.end(), Real(0));
                uint64_t pk1_mask = ~uint64_t(0);
                if (cfg.beta_body > 0 && rigid_mask > 0) pk1_mask = ~((uint64_t)rigid_mask);
                host_pk1(dofmaps_h, cell_marker_h, J_h, inv_H_h, weights_h, bderiv_ref_h,
                    Xref_h, u_h, f_solid_h, solid.num_cells, solid.num_qp, solid.num_basis,
                    cfg.mu_s, cfg.lambda_s, pk1_mask);
                if (cfg.beta_body > 0)
                    host_body_penalty(dofmaps_h, cell_marker_h, J_h, weights_h, bval_ref_h,
                        u_h, f_solid_h, solid.num_cells, solid.num_qp, solid.num_basis,
                        cfg.beta_body, (uint64_t)rigid_mask,
                        solid.mixed ? &qp_phi_h : nullptr, solid.mixed ? &qp_wJ_h : nullptr);
            }
            // spread (CPU 顺序 ii→jj→kk)
            std::vector<Real> fuh(g.size_xf(), Real(0)), fvh(g.size_yf(), Real(0)), fwh(g.size_zf(), Real(0));
            for (size_t i = 0; i < nn; ++i) {
                Real X = Xref_h[i*3+0] + u_h[i*3+0];
                Real Y = Xref_h[i*3+1] + u_h[i*3+1];
                Real Z = Xref_h[i*3+2] + u_h[i*3+2];
                spread_point(fuh.data(), fvh.data(), fwh.data(),
                    Nxf, Nyf, Nzf, Nxv, Nyv, Nzv, Nxw, Nyw, Nzw,
                    hx, hy, hz, X, Y, Z,
                    -f_solid_h[i*3+0] * cfg.beta,
                    -f_solid_h[i*3+1] * cfg.beta,
                    -f_solid_h[i*3+2] * cfg.beta);
            }
            // upload IBM 力 + 固体状态 (供下一步流体推进 + Xc 输出)
            CUDA_CHECK(cudaMemcpy(solver.ibm_fu(), fuh.data(), fuh.size()*sizeof(Real), cudaMemcpyHostToDevice));
            CUDA_CHECK(cudaMemcpy(solver.ibm_fv(), fvh.data(), fvh.size()*sizeof(Real), cudaMemcpyHostToDevice));
            CUDA_CHECK(cudaMemcpy(solver.ibm_fw(), fwh.data(), fwh.size()*sizeof(Real), cudaMemcpyHostToDevice));
            CUDA_CHECK(cudaMemcpy(solid.u.d, u_h.data(), nn*3*sizeof(Real), cudaMemcpyHostToDevice));
            CUDA_CHECK(cudaMemcpy(solid.f_solid.d, f_solid_h.data(), nn*3*sizeof(Real), cudaMemcpyHostToDevice));
        }
        if (!cfg.gpu_coupling || (step+1) % cfg.every == 0 || step+1 == nsteps) {   // 固体力 + spread 力插桩 (bitwise 对比, 与 CPU 同格式)
            std::vector<double> Fs(nn*3), iw(g.size_zf());
            cudaMemcpy(Fs.data(), solid.f_solid.d, nn*3*sizeof(double), cudaMemcpyDeviceToHost);
            cudaMemcpy(iw.data(), solver.ibm_fw(), g.size_zf()*sizeof(double), cudaMemcpyDeviceToHost);
            double fmx=0, fl2=0, imx=0, il2=0;
            for (auto v : Fs) { double a=std::abs(v); if(a>fmx)fmx=a; fl2+=v*v; }
            for (auto v : iw) { double a=std::abs(v); if(a>imx)imx=a; il2+=v*v; }
            printf("solid step=%d fmax=%.17e fl2=%.17e ibm_wmax=%.17e ibm_wl2=%.17e\n",
                   step, fmx, std::sqrt(fl2), imx, std::sqrt(il2));
        }
    }

    cudaFree(d_Xc); cudaFree(d_Us);
    if (log_f) fclose(log_f);
    fcl.close(); frad.close(); frad03.close(); frad07.close(); fpr.close(); fq.close();
    fw.close();
    solid.free();
    stats.done();
    printf("\n  Done. Output: %s\n", cfg.out_dir.c_str());
    return 0;
}
