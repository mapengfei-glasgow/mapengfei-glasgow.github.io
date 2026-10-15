"""Independent staggered-field audit and figures. Run with ParaView's pvpython."""
import csv
import json
import math
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
DEST = HERE.parents[1] / 'mapengfei-glasgow.github.io/static/flat-plate-validation'
DEST.mkdir(parents=True, exist_ok=True)


def read(name):
    path = HERE / 'runs' / name
    nx,ny,nz,lx,ly,lz,nu,dt,steps = map(float,(path/'metadata.txt').read_text().split())
    nx,ny,nz = int(nx),int(ny),int(nz)
    dx,dy,dz = lx/nx,ly/ny,lz/nz
    shapes = [(nz+2,ny+2,nx+3),(nz+2,ny+3,nx+2),(nz+3,ny+2,nx+2),(nz+2,ny+2,nx+2)]
    u,v,w,p = [np.fromfile(path/(f+'.bin'), dtype=np.float64).reshape(s) for f,s in zip('uvwp',shapes)]
    assert all(np.isfinite(a).all() for a in [u,v,w,p])
    U=u[1:nz+1,1:ny+1,1:nx+2]
    V=v[1:nz+1,1:ny+2,1:nx+1]
    W=w[1:nz+2,1:ny+1,1:nx+1]
    div=np.diff(U,axis=2)/dx+np.diff(V,axis=1)/dy+np.diff(W,axis=0)/dz
    volume=lx*ly*lz
    fluxes = [-U[:,:,0].sum()*dy*dz,U[:,:,-1].sum()*dy*dz,
              -V[:,0,:].sum()*dx*dz,V[:,-1,:].sum()*dx*dz,
              -W[0,:,:].sum()*dx*dy,W[-1,:,:].sum()*dx*dy]
    net=sum(fluxes)
    mean=float(div.mean())
    l2=float(np.sqrt(np.mean(div**2)*volume))
    fluct=float(np.sqrt(np.mean((div-mean)**2)*volume))
    yy=(np.arange(ny)+.5)*dy
    xx=(np.arange(nx)+.5)*dx
    ue=lambda x,y: np.vectorize(math.erf)(y/(2*np.sqrt(nu*(x+.25))))
    ve=lambda x,y: np.sqrt(nu/(np.pi*(x+.25)))*(1-np.exp(-y*y/(4*nu*(x+.25))))
    errors=[float(np.max(abs(U[:,:,0]-ue(0,yy)[None,:]))),
            float(np.max(abs(U[:,:,-1]-ue(lx,yy)[None,:]))),
            float(np.max(abs(V[:,0,:]))),float(np.max(abs(V[:,-1,:]-ve(xx,ly)[None,:]))),
            float(np.max(abs(W[0,:,:]))),float(np.max(abs(W[-1,:,:])))]
    rows=list(csv.DictReader((path/'diagnostics.csv').open()))
    assert abs(l2-float(rows[-1]['divergence_l2']))<1e-12
    assert abs(net-mean*volume)<1e-14
    profiles=[U[nz//2,:,nx//2],U[nz//2,:,3*nx//4]]
    # One-cell wall-gradient estimate; diagnostic only, not a converged wall shear.
    cf=[float(4*nu*q[0]/dy) for q in profiles]
    theta=[float(np.sum(q*(1-q))*dy) for q in profiles]
    metrics=dict(name=name,grid=[nx,ny,nz],dt=dt,steps=int(steps),time=dt*steps,
        max_speed=float(rows[-1]['max_speed']),div_l2=l2,div_mean=mean,div_fluct_l2=fluct,
        outward_fluxes=fluxes,net_outward_flux=net,relative_flux_imbalance=abs(net/fluxes[0]),
        normal_boundary_error_max=max(errors),normal_boundary_errors=errors,
        near_wall_cf_estimate=cf,finite_height_theta_estimate=theta,
        kinetic_energy=float(rows[-1]['kinetic_energy']),w_rms=float(rows[-1]['w_rms']),
        energy_change_last_005=float(rows[-1]['kinetic_energy'])-float(rows[-2]['kinetic_energy']))
    return dict(metrics=metrics,y=yy,x=xx,U=U,div=div,profiles=profiles,rows=rows)


cases=[read(n) for n in ['n32_dt1e-3','n64_dt1e-3','n32_dt5e-4']]
a,b,c=cases
comparison={}
for j,x in enumerate([.5,.75]):
    # Fine cell-centre profile averaged onto coarse cells in y, at a common z face-centre pair.
    Uf=b['U']; nz=Uf.shape[0]
    fp=.5*(Uf[nz//2-1,:,int(x*64)]+Uf[nz//2,:,int(x*64)])
    bp=fp.reshape(-1,2).mean(axis=1)
    ap=.5*(a['U'][7,:,int(x*32)]+a['U'][8,:,int(x*32)])
    cp=.5*(c['U'][7,:,int(x*32)]+c['U'][8,:,int(x*32)])
    comparison[str(x)]=dict(grid_profile_rms=float(np.sqrt(np.mean((ap-bp)**2))),
                            half_dt_profile_rms=float(np.sqrt(np.mean((ap-cp)**2))))
summary=dict(cases=[q['metrics'] for q in cases],comparisons=comparison,
             divergence_reduction=a['metrics']['div_l2']/b['metrics']['div_l2'])
(DEST/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary,indent=2))

plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
fig,axs=plt.subplots(1,2,figsize=(11,4),layout='constrained')
im=axs[0].pcolormesh(np.arange(32)/32,a['y'],a['U'][8,:,:-1],shading='nearest',cmap='viridis',vmin=0,vmax=1.06)
axs[0].set(xlabel='x',ylabel='y',title='32 × 32 × 16: streamwise velocity at t=1')
fig.colorbar(im,ax=axs[0],label='u / U∞')
for q,label in zip(cases,['32 grid, Δt=0.001','64 grid, Δt=0.001','32 grid, Δt=0.0005']):
    axs[1].plot(q['profiles'][0],q['y'],label=label)
axs[1].set(xlabel='u / U∞ at x=0.5',ylabel='y',title='Profile comparison (near centre span)')
axs[1].legend(fontsize=8)
fig.savefig(DEST/'velocity-profiles.png',dpi=180)
plt.close(fig)

fig,axs=plt.subplots(1,2,figsize=(11,4),layout='constrained')
for q,label in zip(cases,['32 grid','64 grid','32 grid, half Δt']):
    axs[0].plot([float(r['time']) for r in q['rows']], [float(r['kinetic_energy']) for r in q['rows']],label=label)
axs[0].set(xlabel='t',ylabel='Volume-mean kinetic energy',title='Energy still evolves at t=1')
axs[0].legend(fontsize=8)
pos=np.arange(3)
axs[1].bar(pos-.18,[q['metrics']['div_l2'] for q in cases],width=.36,label='Total divergence L2')
axs[1].bar(pos+.18,[q['metrics']['div_fluct_l2'] for q in cases],width=.36,label='Mean-subtracted divergence L2')
axs[1].set_yscale('log');axs[1].set_xticks(pos,['32 grid','64 grid','32, half Δt'])
axs[1].set(ylabel='Integrated L2 norm',title='Boundary-flux error dominates divergence')
axs[1].legend(fontsize=8)
fig.savefig(DEST/'energy-mass-balance.png',dpi=180)
plt.close(fig)

# Export numerical values and source alongside the article for independent review.
with (DEST/'metrics.csv').open('w') as f:
    keys=['name','dt','time','max_speed','div_l2','div_mean','div_fluct_l2','net_outward_flux','relative_flux_imbalance','normal_boundary_error_max','energy_change_last_005']
    writer=csv.DictWriter(f,fieldnames=keys,extrasaction='ignore');writer.writeheader()
    writer.writerows(q['metrics'] for q in cases)
for q in cases:
    import shutil
    name=q['metrics']['name']
    shutil.copyfile(HERE/'runs'/name/'diagnostics.csv',DEST/(name+'-diagnostics.csv'))
    shutil.copyfile(HERE/'runs'/name/'profile.csv',DEST/(name+'-profile.csv'))
for name in ['flat_plate.cu','analyse.py']:
    shutil.copyfile(HERE/name,DEST/name)
