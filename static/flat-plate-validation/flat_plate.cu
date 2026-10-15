// Preliminary finite-span, laminar flat-plate smoke test; NOT a turbulent DNS.
#include "ns_solver_cuda.h"
#include <fstream>
#include <iostream>
#include <iomanip>
#include <filesystem>
#include <stdexcept>
#include <string>
using namespace fdm3d_cuda;
constexpr double LX=1., LY=.2, LZ=.2, NU=.001;
struct Plate {
    // Divergence-free erf-profile approximation, from an analytic streamfunction.
    // Virtual origin x=-.25 avoids the leading-edge singularity.
    __host__ __device__ static double ue(double x,double y,double,double) {
        return erf(y/(2*sqrt(NU*(x+.25))));
    }
    __host__ __device__ static double ve(double x,double y,double,double) {
        double s=x+.25, a=1/(2*sqrt(NU*s));
        return (1-exp(-a*a*y*y))/(2*a*sqrt(M_PI)*s);
    }
    __host__ __device__ static double we(double,double,double,double){return 0;}
    __host__ __device__ static double pe(double,double,double,double){return 0;}
    __host__ __device__ static double fx(double,double,double,double){return 0;}
    __host__ __device__ static double fy(double,double,double,double){return 0;}
    __host__ __device__ static double fz(double,double,double,double){return 0;}
};
int main(int argc,char** argv) {
    try {
        int n=argc>1?std::stoi(argv[1]):32, steps=argc>2?std::stoi(argv[2]):1000;
        const std::string out=argc>3?argv[3]:"output";
        const double DT=argc>4?std::stod(argv[4]):.001;
        if(!(DT>0 && DT<=.001))throw std::runtime_error("dt must be in (0,0.001]");
        if(n<16 || n>128 || (n&(n-1)) || steps<1 || steps>10000)
            throw std::runtime_error("usage: flat_plate [N:16,32,64,128] [steps:1..10000]");
        const int nx=n,ny=n,nz=n/2;
        std::filesystem::create_directories(out);
        ChorinStokesSolverCUDA<double,Plate> solver(nx,ny,nz,LX/nx,LY/ny,LZ/nz,DT,NU);
        solver.set_mg_params(4,20,3);
        solver.enable_convection();
        solver.set_convection_scheme(ConvectionAB2CUDA<double>::Scheme::SecondUpwind);
        auto& g=solver.grid();
        std::vector<double> u(g.size_xf()),v(g.size_yf()),w(g.size_zf()),p(g.size_cc(),0);
        // Weak divergence-free cross-plane perturbation: (v',w')=(dpsi/dz,-dpsi/dy).
        auto perturb=[](double x,double y,double z,bool for_v) {
            double sx=sin(M_PI*x/LX), sy=sin(M_PI*y/LY), sz=sin(M_PI*z/LZ);
            double amp=.001*LY/M_PI;
            return for_v ? amp*sx*sx*sy*sy*(M_PI/LZ)*sin(2*M_PI*z/LZ)
                         : -amp*sx*sx*(M_PI/LY)*sin(2*M_PI*y/LY)*sz*sz;
        };
        for(int k=0;k<g.Nz_xf();++k)for(int j=0;j<g.Ny_xf();++j)for(int i=0;i<g.Nx_xf();++i)
            u[g.idx_xf(i,j,k)]=Plate::ue(g.x_xf(i),g.y_cc(j),g.z_cc(k),0);
        for(int k=0;k<g.Nz_yf();++k)for(int j=0;j<g.Ny_yf();++j)for(int i=0;i<g.Nx_yf();++i)
            v[g.idx_yf(i,j,k)]=Plate::ve(g.x_cc(i),g.y_yf(j),g.z_cc(k),0)+perturb(g.x_cc(i),g.y_yf(j),g.z_cc(k),true);
        for(int k=0;k<g.Nz_zf();++k)for(int j=0;j<g.Ny_zf();++j)for(int i=0;i<g.Nx_zf();++i)
            w[g.idx_zf(i,j,k)]=perturb(g.x_cc(i),g.y_cc(j),g.z_zf(k),false);
        g.upload_u(u);g.upload_v(v);g.upload_w(w);g.upload_p(p);
        std::ofstream log(out+"/diagnostics.csv");
        log<<"step,time,max_speed,divergence_l2,kinetic_energy,w_rms\n"<<std::setprecision(12);
        std::cout<<"Finite-span plate smoke test: "<<nx<<"x"<<ny<<"x"<<nz<<", Re_L=1000, dt="<<DT<<", steps="<<steps<<std::endl;
        for(int s=1;s<=steps;++s) {
            solver.step();
            if(s==1 || s%50==0 || s==steps) {
                g.download_u(u);g.download_v(v);g.download_w(w);g.download_p(p);
                double maxspeed=0, energy=0, wrms=0;
                for(int k=1;k<=nz;++k)for(int j=1;j<=ny;++j)for(int i=1;i<=nx;++i){
                    double a=.5*(u[g.idx_xf(i,j,k)]+u[g.idx_xf(i+1,j,k)]);
                    double b=.5*(v[g.idx_yf(i,j,k)]+v[g.idx_yf(i,j+1,k)]);
                    double c=.5*(w[g.idx_zf(i,j,k)]+w[g.idx_zf(i,j,k+1)]);
                    double q=a*a+b*b+c*c;
                    if(!std::isfinite(q) || !std::isfinite(p[g.idx_cc(i,j,k)])) throw std::runtime_error("non-finite solution");
                    maxspeed=std::max(maxspeed,sqrt(q));energy+=.5*q;wrms+=c*c;
                }
                double div=solver.divergence_l2();
                if(!std::isfinite(div) || maxspeed>5 || div>.1) throw std::runtime_error("stability/divergence limit exceeded");
                log<<s<<","<<solver.time()<<","<<maxspeed<<","<<div<<","<<energy/(nx*ny*nz)<<","<<sqrt(wrms/(nx*ny*nz))<<std::endl;
                std::cout<<"step="<<s<<" t="<<solver.time()<<" max_speed="<<maxspeed<<" div_L2="<<div<<std::endl;
            }
        }
        // Preserve full-precision staggered fields (including ghosts) for independent checks.
        for(int f=0;f<4;++f){
            const auto& a=f==0?u:f==1?v:f==2?w:p;
            const char* name=f==0?"u":f==1?"v":f==2?"w":"p";
            std::ofstream raw(out+"/"+name+".bin",std::ios::binary);
            raw.write(reinterpret_cast<const char*>(a.data()),a.size()*sizeof(double));
            if(!raw)throw std::runtime_error("raw field write failed");
        }
        std::ofstream meta(out+"/metadata.txt");
        meta<<std::setprecision(17)<<nx<<" "<<ny<<" "<<nz<<" "<<LX<<" "<<LY<<" "<<LZ<<" "<<NU<<" "<<DT<<" "<<steps<<"\n";
        std::ofstream vtk(out+"/final.vtk");
        vtk<<"# vtk DataFile Version 3.0\nFlat plate preliminary smoke test\nASCII\nDATASET STRUCTURED_POINTS\nDIMENSIONS "<<nx<<" "<<ny<<" "<<nz<<"\nORIGIN "<<LX/nx/2<<" "<<LY/ny/2<<" "<<LZ/nz/2<<"\nSPACING "<<LX/nx<<" "<<LY/ny<<" "<<LZ/nz<<"\nPOINT_DATA "<<nx*ny*nz<<"\nVECTORS velocity double\n";
        for(int k=1;k<=nz;++k)for(int j=1;j<=ny;++j)for(int i=1;i<=nx;++i)
            vtk<<.5*(u[g.idx_xf(i,j,k)]+u[g.idx_xf(i+1,j,k)])<<" "<<.5*(v[g.idx_yf(i,j,k)]+v[g.idx_yf(i,j+1,k)])<<" "<<.5*(w[g.idx_zf(i,j,k)]+w[g.idx_zf(i,j,k+1)])<<"\n";
        vtk<<"SCALARS pressure double 1\nLOOKUP_TABLE default\n";
        for(int k=1;k<=nz;++k)for(int j=1;j<=ny;++j)for(int i=1;i<=nx;++i)vtk<<p[g.idx_cc(i,j,k)]<<"\n";
        std::ofstream profile(out+"/profile.csv");
        profile<<"y,u_at_x_mid,u_at_x_three_quarters\n";
        for(int j=1;j<=ny;++j)profile<<g.y_cc(j)<<","<<u[g.idx_xf(nx/2+1,j,nz/2)]<<","<<u[g.idx_xf(3*nx/4+1,j,nz/2)]<<"\n";
        if(!log || !vtk || !profile)throw std::runtime_error("output write failed");
        return 0;
    } catch(const std::exception& e) {std::cerr<<e.what()<<std::endl;return 1;}
}
