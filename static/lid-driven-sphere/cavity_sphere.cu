// Lid-driven cavity with a translating, spring-tethered rigid sphere; volume penalty.
#include "ns_solver_cuda.h"
#include <filesystem>
#include <fstream>
#include <iostream>
#include <iomanip>
#include <array>
#include <chrono>
#include <stdexcept>
using namespace fdm3d_cuda;
struct Inflow {
    __host__ __device__ static double speed(double t){double a=fmin(1.,fmax(0.,t));return a*a*(3-2*a);}
    __host__ __device__ static double ue(double,double y,double,double t){return y>=1.-1e-10?speed(t):0.;}
    __host__ __device__ static double ve(double,double,double,double){return 0;}
    __host__ __device__ static double we(double,double,double,double){return 0;}
    __host__ __device__ static double pe(double,double,double,double){return 0;}
    __host__ __device__ static double fx(double,double,double,double){return 0;}
    __host__ __device__ static double fy(double,double,double,double){return 0;}
    __host__ __device__ static double fz(double,double,double,double){return 0;}
};
__global__ void penalize(double* force,const double* vel,int sx,int sy,int sz,int component,
    double h,double cx,double cy,double cz,double bodyv,double time,double kappa,double* sums){
    size_t n=size_t(sx)*sy*sz,c=blockIdx.x*size_t(blockDim.x)+threadIdx.x;
    if(c>=n)return;
    int i=c%sx,j=(c/sx)%sy,k=c/(size_t(sx)*sy);
    double x=(i-(component==0?1.:.5))*h,y=(j-(component==1?1.:.5))*h,z=(k-(component==2?1.:.5))*h;
    double d=sqrt((x-cx)*(x-cx)+(y-cy)*(y-cy)+(z-cz)*(z-cz));
    // Smooth half-cell-width transition: full penalty for d<=R-h/2.
    double a=fmin(1.,fmax(0.,(.18+.5*h-d)/h));
    double chi=a*a*(3-2*a),reaction=kappa*chi*(vel[c]-bodyv);
    force[c]=-reaction;
    if(chi>0){atomicAdd(sums+component,reaction*h*h*h);atomicAdd(sums+3+component,chi*h*h*h);}
}
int main(int argc,char** argv){
 try{
    int res=argc>1?std::stoi(argv[1]):64;
    double T=argc>2?std::stod(argv[2]):2,dt=argc>3?std::stod(argv[3]):.001;
    std::string out=argc>4?argv[4]:"runs/pilot64";
    int every=argc>5?std::stoi(argv[5]):100;
    double Re=argc>6?std::stod(argv[6]):1000;
    if((res!=32&&res!=64&&res!=96&&res!=128) || !(T>0&&T<=40) || !(dt>0&&dt<=.001) || every<1 || !(Re>0))throw std::runtime_error("usage: cavity_sphere N T dt output every Re_L");
    if(std::filesystem::exists(out))throw std::runtime_error("Output exists; choose a new directory.");
    std::filesystem::create_directories(out);
    const int nx=res,ny=res,nz=res,steps=int(ceil(T/dt));
    const double h=1./res,nu=1./Re,kappa=200.,spring=1.,damping=.05,rho_s=4.,volume=4*M_PI*.18*.18*.18/3;
    std::array<double,3> anchor={.5,.5,.5},position={.505,.5,.5},velocity={0,0,0},reaction={0,0,0};
    ChorinStokesSolverCUDA<double,Inflow> solver(nx,ny,nz,h,h,h,dt,nu);
    solver.enable_convection();solver.set_convection_scheme(ConvectionAB2CUDA<double>::Scheme::SecondUpwind);
    solver.set_mg_params(3,10,3);solver.set_fast_mean(true);solver.zero_ibm_force();
    auto& g=solver.grid();g.zero_all();
    DevBuf<double> sums;sums.alloc(6);
    std::vector<double> u,v,w;
    std::ofstream meta(out+"/metadata.json"),log(out+"/diagnostics.csv"),frames(out+"/frames.csv");
    meta<<std::setprecision(17)<<"{\"nx\":"<<nx<<",\"ny\":"<<ny<<",\"nz\":"<<nz<<",\"h\":"<<h<<",\"dt\":"<<dt<<",\"steps\":"<<steps<<",\"Re_L\":"<<Re<<",\"nu\":"<<nu<<",\"D\":0.36,\"U_lid\":1,\"rho_s\":4,\"spring\":1,\"damping\":0.05,\"kappa\":200,\"anchor\":[0.5,0.5,0.5],\"radius\":0.18}\n";
    log<<"step,time,cx,cy,cz,vx,vy,vz,reaction_x,reaction_y,reaction_z,max_speed,div_l2,inlet_flux,outlet_flux,core_slip_rms,fluid_transverse_rms,elapsed_seconds\n"<<std::setprecision(12);
    frames<<"step,time,file,cx,cy,cz\n"<<std::setprecision(12);
    auto start=std::chrono::steady_clock::now();
    auto record=[&](int step,bool save){
        g.download_u(u);g.download_v(v);g.download_w(w);
        double maxspeed=0,slip=0,ns=0,wake=0,nw=0,in=0,exit=0;
        std::vector<float> a;if(save)a.reserve(size_t(nx)*ny*nz*3);
        for(int k=1;k<=nz;++k)for(int j=1;j<=ny;++j)for(int i=1;i<=nx;++i){
            double ux=.5*(u[g.idx_xf(i,j,k)]+u[g.idx_xf(i+1,j,k)]),uy=.5*(v[g.idx_yf(i,j,k)]+v[g.idx_yf(i,j+1,k)]),uz=.5*(w[g.idx_zf(i,j,k)]+w[g.idx_zf(i,j,k+1)]);
            double q=ux*ux+uy*uy+uz*uz;
            if(!std::isfinite(q))throw std::runtime_error("Non-finite velocity");
            maxspeed=std::max(maxspeed,sqrt(q));
            double x=g.x_cc(i),y=g.y_cc(j),z=g.z_cc(k);
            double d2=(x-position[0])*(x-position[0])+(y-position[1])*(y-position[1])+(z-position[2])*(z-position[2]);
            if(d2<(.18-h)*(.18-h)){slip+=pow(ux-velocity[0],2)+pow(uy-velocity[1],2)+pow(uz-velocity[2],2);++ns;}
            if(d2>(.18+h)*(.18+h)){wake+=ux*ux+uy*uy;++nw;}
            if(save){a.push_back(float(ux));a.push_back(float(uy));a.push_back(float(uz));}
        }
        for(int j=1;j<=ny;++j)for(int i=1;i<=nx;++i){in+=w[g.idx_zf(i,j,1)]*h*h;exit+=w[g.idx_zf(i,j,nz+1)]*h*h;}
        double div=solver.divergence_l2(),disp=0;for(int c=0;c<3;++c)disp+=pow(position[c]-anchor[c],2);
        if(!std::isfinite(div)||div>.1||maxspeed>5||dt/h*maxspeed>.4||sqrt(disp)>.15)throw std::runtime_error("Guard failed: divergence, speed/CFL or tether excursion");
        double elapsed=std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count();
        log<<step<<","<<solver.time();for(double b:position)log<<","<<b;for(double b:velocity)log<<","<<b;for(double b:reaction)log<<","<<b;
        log<<","<<maxspeed<<","<<div<<","<<in<<","<<exit<<","<<sqrt(slip/std::max(1.,ns))<<","<<sqrt(wake/std::max(1.,nw))<<","<<elapsed<<std::endl;
        std::cout<<"step="<<step<<" t="<<solver.time()<<" centre="<<position[0]<<","<<position[1]<<","<<position[2]<<" max="<<maxspeed<<" div="<<div<<" slip="<<sqrt(slip/std::max(1.,ns))<<" elapsed="<<elapsed<<std::endl;
        if(save){std::string name="velocity_"+std::to_string(step)+".bin";std::ofstream f(out+"/"+name,std::ios::binary);f.write(reinterpret_cast<char*>(a.data()),a.size()*sizeof(float));if(!f)throw std::runtime_error("Frame write failed");
            frames<<step<<","<<solver.time()<<","<<name;for(double b:position)frames<<","<<b;frames<<std::endl;}
    };
    record(0,true);
    for(int step=1;step<=steps;++step){
        auto bc=make_dirichlet_bc<double>(0);bc.y_high.g=Inflow::speed(solver.time());g.set_bc_u(bc);
        CUDA_CHECK(cudaMemset(sums.d,0,6*sizeof(double)));
        double* force[3]={solver.ibm_fu(),solver.ibm_fv(),solver.ibm_fw()};
        const double* fluid[3]={g.u_dev(),g.v_dev(),g.w_dev()};
        const int sx[3]={g.Nx_xf(),g.Nx_yf(),g.Nx_zf()},sy[3]={g.Ny_xf(),g.Ny_yf(),g.Ny_zf()},sz[3]={g.Nz_xf(),g.Nz_yf(),g.Nz_zf()};
        for(int c=0;c<3;++c){size_t n=size_t(sx[c])*sy[c]*sz[c];
            penalize<<<int((n+255)/256),256>>>(force[c],fluid[c],sx[c],sy[c],sz[c],c,h,position[0],position[1],position[2],velocity[c],solver.time(),kappa,sums.d);check_launch();}
        double totals[6];CUDA_CHECK(cudaMemcpy(totals,sums.d,6*sizeof(double),cudaMemcpyDeviceToHost));
        solver.step();
        for(int c=0;c<3;++c){
            reaction[c]=totals[c];
            // Approximate fictitious-fluid inertia correction assumes interior fluid follows the body.
            double mass=rho_s*volume-totals[3+c];
            if(!(mass>0))throw std::runtime_error("Non-positive effective rigid-body mass");
            velocity[c]=(mass*velocity[c]+dt*(reaction[c]-spring*(position[c]-anchor[c])))/(mass+dt*damping+dt*dt*spring);
            position[c]+=dt*velocity[c];
        }
        if(step%100==0||step%every==0||step==steps)record(step,step%every==0||step==steps);
    }
    if(!meta||!log||!frames)throw std::runtime_error("Output stream failed");
    return 0;
 }catch(const std::exception& e){std::cerr<<e.what()<<std::endl;return 1;}
}
