// Unforced decay of interacting 3D vortices with homogeneous no-slip walls.
// Uses the existing GPU Navier-Stokes solver without modifying library headers.
#include "ns_solver_cuda.h"
#include <filesystem>
#include <fstream>
#include <iostream>
#include <iomanip>
#include <array>
#include <chrono>
#include <stdexcept>
using namespace fdm3d_cuda;
struct Zero {
    __host__ __device__ static double ue(double,double,double,double){return 0;}
    __host__ __device__ static double ve(double,double,double,double){return 0;}
    __host__ __device__ static double we(double,double,double,double){return 0;}
    __host__ __device__ static double pe(double,double,double,double){return 0;}
    __host__ __device__ static double fx(double,double,double,double){return 0;}
    __host__ __device__ static double fy(double,double,double,double){return 0;}
    __host__ __device__ static double fz(double,double,double,double){return 0;}
};
// Fixed phases and low spatial modes; no runtime randomness or turbulent forcing.
double potential(int c,double x,double y,double z) {
    if(x<=0 || x>=1 || y<=0 || y>=1 || z<=0 || z>=1)return 0;
    const int modes[6][3]={{1,1,1},{2,1,1},{1,2,1},{1,1,2},{2,2,1},{1,2,2}};
    double e=pow(sin(M_PI*x)*sin(M_PI*y)*sin(M_PI*z),2),a=0;
    for(int m=0;m<6;++m){
        double phase=.71*(m+1)*(c+1)+.31*c;
        a+=sin(M_PI*(modes[m][0]*x+modes[m][1]*y+modes[m][2]*z)+phase)/(m+1);
    }
    return e*a;
}
int main(int argc,char** argv) {
    try {
        int N=argc>1?std::stoi(argv[1]):64;
        int steps=argc>2?std::stoi(argv[2]):2000;
        double dt=argc>3?std::stod(argv[3]):.0005;
        std::string out=argc>4?argv[4]:"runs/pilot64";
        int every=argc>5?std::stoi(argv[5]):100;
        double nu=argc>6?std::stod(argv[6]):.0005;
        if(N<16 || N>128 || (N&(N-1)) || steps<1 || steps>20000 || !(dt>0 && dt<=.001) || every<1 || !(nu>0))
            throw std::runtime_error("usage: vortex_box N steps dt output every nu");
        if(std::filesystem::exists(out))throw std::runtime_error("Output directory already exists; use a new name.");
        std::filesystem::create_directories(out);
        double h=1./N;
        ChorinStokesSolverCUDA<double,Zero> solver(N,N,N,h,h,h,dt,nu);
        solver.enable_convection();
        solver.set_convection_scheme(ConvectionAB2CUDA<double>::Scheme::SecondUpwind);
        solver.set_mg_params(3,10,3);
        solver.set_fast_mean(true);
        solver.zero_ibm_force();
        auto& g=solver.grid();g.zero_all();
        std::vector<double> u(g.size_xf(),0),v(g.size_yf(),0),w(g.size_zf(),0);
        // Discrete edge-to-face curl: div_h(curl_h A)=0 to roundoff.
        for(int k=1;k<=N;++k)for(int j=1;j<=N;++j)for(int i=1;i<=N+1;++i){
            double x=(i-1)*h,y=(j-.5)*h,z=(k-.5)*h;
            u[g.idx_xf(i,j,k)]=(potential(2,x,j*h,z)-potential(2,x,(j-1)*h,z)
                              -potential(1,x,y,k*h)+potential(1,x,y,(k-1)*h))/h;
        }
        for(int k=1;k<=N;++k)for(int j=1;j<=N+1;++j)for(int i=1;i<=N;++i){
            double x=(i-.5)*h,y=(j-1)*h,z=(k-.5)*h;
            v[g.idx_yf(i,j,k)]=(potential(0,x,y,k*h)-potential(0,x,y,(k-1)*h)
                              -potential(2,i*h,y,z)+potential(2,(i-1)*h,y,z))/h;
        }
        for(int k=1;k<=N+1;++k)for(int j=1;j<=N;++j)for(int i=1;i<=N;++i){
            double x=(i-.5)*h,y=(j-.5)*h,z=(k-1)*h;
            w[g.idx_zf(i,j,k)]=(potential(1,i*h,y,z)-potential(1,(i-1)*h,y,z)
                              -potential(0,x,j*h,z)+potential(0,x,(j-1)*h,z))/h;
        }
        double sum=0;
        for(int k=1;k<=N;++k)for(int j=1;j<=N;++j)for(int i=1;i<=N;++i){
            double a=.5*(u[g.idx_xf(i,j,k)]+u[g.idx_xf(i+1,j,k)]);
            double b=.5*(v[g.idx_yf(i,j,k)]+v[g.idx_yf(i,j+1,k)]);
            double c=.5*(w[g.idx_zf(i,j,k)]+w[g.idx_zf(i,j,k+1)]);
            sum+=a*a+b*b+c*c;
        }
        double scale=sqrt(N*double(N)*N/sum); // Initial vector RMS speed = 1.
        for(auto& a:u)a*=scale;for(auto& a:v)a*=scale;for(auto& a:w)a*=scale;
        g.upload_u(u);g.upload_v(v);g.upload_w(w);
        std::ofstream meta(out+"/metadata.json");
        meta<<std::setprecision(17)<<"{\"N\":"<<N<<",\"L\":1,\"nu\":"<<nu<<",\"dt\":"<<dt<<",\"steps\":"<<steps<<",\"every\":"<<every<<",\"initial_vector_rms\":1,\"potential_scale\":"<<scale<<"}\n";
        std::ofstream log(out+"/diagnostics.csv"),series(out+"/frames.csv");
        log<<"step,time,kinetic_energy,max_speed,div_l2,cfl,wall_normal_max,elapsed_seconds\n";
        series<<"step,time,file\n";
        log<<std::setprecision(12);series<<std::setprecision(12);
        auto start=std::chrono::steady_clock::now();
        auto record=[&](int step,bool frame){
            g.download_u(u);g.download_v(v);g.download_w(w);
            double energy=0,maxspeed=0,cfl=0,wall=0;
            std::vector<float> vel; if(frame)vel.reserve(size_t(N)*N*N*3);
            for(int k=1;k<=N;++k)for(int j=1;j<=N;++j)for(int i=1;i<=N;++i){
                double a=.5*(u[g.idx_xf(i,j,k)]+u[g.idx_xf(i+1,j,k)]);
                double b=.5*(v[g.idx_yf(i,j,k)]+v[g.idx_yf(i,j+1,k)]);
                double c=.5*(w[g.idx_zf(i,j,k)]+w[g.idx_zf(i,j,k+1)]);
                double q=a*a+b*b+c*c;
                if(!std::isfinite(q))throw std::runtime_error("Non-finite velocity");
                energy+=.5*q;maxspeed=std::max(maxspeed,sqrt(q));
                cfl=std::max(cfl,dt/h*(abs(a)+abs(b)+abs(c)));
                if(frame){vel.push_back(float(a));vel.push_back(float(b));vel.push_back(float(c));}
            }
            for(int k=1;k<=N;++k)for(int j=1;j<=N;++j){
                wall=std::max({wall,abs(u[g.idx_xf(1,j,k)]),abs(u[g.idx_xf(N+1,j,k)]),
                    abs(v[g.idx_yf(j,1,k)]),abs(v[g.idx_yf(j,N+1,k)]),
                    abs(w[g.idx_zf(j,k,1)]),abs(w[g.idx_zf(j,k,N+1)])});
            }
            double div=solver.divergence_l2(),E=energy/(double(N)*N*N);
            if(!std::isfinite(div) || div>.02 || cfl>.6 || E>1)throw std::runtime_error("Numerical guard failed (divergence, CFL or energy).");
            double elapsed=std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count();
            log<<step<<","<<solver.time()<<","<<E<<","<<maxspeed<<","<<div<<","<<cfl<<","<<wall<<","<<elapsed<<std::endl;
            std::cout<<"step="<<step<<" t="<<solver.time()<<" E="<<E<<" max="<<maxspeed<<" div="<<div<<" CFL="<<cfl<<" elapsed="<<elapsed<<std::endl;
            if(frame){
                std::string name="velocity_"+std::to_string(step)+".bin";
                std::ofstream file(out+"/"+name,std::ios::binary);
                file.write(reinterpret_cast<const char*>(vel.data()),vel.size()*sizeof(float));
                if(!file)throw std::runtime_error("Frame write failed");
                series<<step<<","<<solver.time()<<","<<name<<std::endl;
            }
        };
        record(0,true);
        for(int step=1;step<=steps;++step){
            solver.step();
            if(step%50==0 || step%every==0 || step==steps)record(step,step%every==0 || step==steps);
        }
        FILE* state=fopen((out+"/final_checkpoint.bin").c_str(),"wb");
        if(!state)throw std::runtime_error("Cannot write checkpoint");
        solver.save_state(state);fclose(state);
        if(!meta || !log || !series)throw std::runtime_error("Metadata write failed");
        return 0;
    }catch(const std::exception& e){std::cerr<<e.what()<<std::endl;return 1;}
}
