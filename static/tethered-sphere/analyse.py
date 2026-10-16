"""Visualize actual tethered-sphere fields and audit scalar diagnostics."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'decaying-vortices/python-packages'))
import csv
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from PIL import Image
import pyvista as pv

path=Path(sys.argv[1] if len(sys.argv)>1 else 'runs/main16').resolve()
meta=json.loads((path/'metadata.json').read_text());h=meta['h']
nx,ny,nz=[meta[k] for k in ['nx','ny','nz']]
frames=list(csv.DictReader((path/'frames.csv').open()))
rows=list(csv.DictReader((path/'diagnostics.csv').open()))
out=path/'visualization';out.mkdir(exist_ok=True)
times=[];slices=[];centres=[];pvd=['<?xml version="1.0"?><VTKFile type="Collection" version="0.1" byte_order="LittleEndian"><Collection>']
late_count=0;late_mean=None;late_m2=None
coords=(np.arange(nx)+.5)*h
zcoords=(np.arange(nz)+.5)*h
for index,frame in enumerate(frames):
    a=np.fromfile(path/frame['file'],dtype=np.float32).reshape(nz,ny,nx,3)
    assert np.isfinite(a).all()
    if float(frame['time'])>=max(1,meta['steps']*meta['dt']/2):
        # Fixed fluid-only wake box, away from the moving solid and downstream sponge.
        sample=a[int(4/h):int(8/h),int(2/h):int(4/h),int(2/h):int(4/h),:].astype(float)
        late_count+=1
        if late_mean is None:late_mean=np.zeros_like(sample);late_m2=np.zeros_like(sample)
        delta=sample-late_mean;late_mean+=delta/late_count;late_m2+=delta*(sample-late_mean)
    centre=np.array([float(frame[k]) for k in ['cx','cy','cz']])
    mesh=pv.ImageData(dimensions=(nx,ny,nz),spacing=(h,h,h),origin=(h/2,h/2,h/2))
    mesh['velocity']=a.reshape(-1,3)
    mesh=mesh.compute_derivative(scalars='velocity',gradient=False,vorticity='vorticity',qcriterion='Q')
    mesh['vorticity_magnitude']=np.linalg.norm(mesh['vorticity'],axis=1)
    # Mask the diffuse solid region when plotting fluid-only Q, retaining raw Q too.
    xx=coords[None,None,:]-centre[0]
    yy=(np.arange(ny)[None,:,None]+.5)*h-centre[1]
    zz=zcoords[:,None,None]-centre[2]
    fluid=(xx*xx+yy*yy+zz*zz)>(.5+h/2)**2
    mesh['fluid_Q']=np.where(fluid.ravel(),mesh['Q'],0).astype(np.float32)
    name='frame_'+frame['step']+'.vti';mesh.save(out/name)
    pvd.append(f'<DataSet timestep="{frame["time"]}" part="0" file="{name}"/>')
    om=mesh['vorticity_magnitude'].reshape(nz,ny,nx)
    j=int(round(centre[1]/h-.5));j=max(0,min(ny-1,j))
    plane=om[:,j,:].T.copy()
    d2=(coords[:,None]-centre[0])**2+(zcoords[None,:]-centre[2])**2
    plane[d2<.5**2]=np.nan
    slices.append(plane);times.append(float(frame['time']));centres.append(centre)
    print(f'Processed {index+1}/{len(frames)} t={times[-1]}',flush=True)
pvd.append('</Collection></VTKFile>');(out/'fluid.pvd').write_text('\n'.join(pvd))

def values(key):return np.array([float(r[key]) for r in rows])
t=values('time');influx=values('inlet_flux');outflux=values('outlet_flux')
active=t>=1
summary=dict(grid=[nx,ny,nz],Re_D=meta['Re_D'],cells_per_D=1/h,final_time=float(t[-1]),
    max_div_l2=float(values('div_l2').max()),max_speed=float(values('max_speed').max()),
    max_core_slip_rms=float(values('core_slip_rms').max()),
    final_core_slip_rms=float(values('core_slip_rms')[-1]),
    max_tether_displacement=float(np.sqrt((values('cx')-3)**2+(values('cy')-3)**2+(values('cz')-3)**2).max()),
    relative_flux_error_after_ramp=float(np.max(np.abs(outflux[active]-influx[active])/np.maximum(np.abs(influx[active]),1e-9))),
    final_centre=[float(values(k)[-1]) for k in ['cx','cy','cz']],
    final_wake_transverse_rms=float(values('wake_transverse_rms')[-1]),
    tail_reaction_z_std=float(np.std(values('reaction_z')[t>=max(1,t[-1]/2)])))
if late_count>1:
    summary['wake_temporal_vector_rms_after_half_time']=float(np.sqrt(np.mean(np.sum(late_m2/late_count,axis=3))))
    summary['temporal_samples']=late_count
(out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))
fig,axes=plt.subplots(2,2,figsize=(11,7),layout='constrained')
for k in ['cx','cy','cz']:axes[0,0].plot(t,values(k)-3,label=k)
axes[0,0].set(xlabel='t U∞ / D',ylabel='Centre displacement / D',title='Spring/damper-tethered sphere');axes[0,0].legend()
for k in ['reaction_x','reaction_y','reaction_z']:axes[0,1].plot(t,values(k),label=k)
axes[0,1].set(xlabel='t U∞ / D',ylabel='Penalty reaction (approximate coupling force)');axes[0,1].legend()
axes[1,0].plot(t,values('wake_transverse_rms'));axes[1,0].set(xlabel='t U∞ / D',ylabel='Wake transverse speed RMS / U∞')
axes[1,1].semilogy(t,np.maximum(values('core_slip_rms'),1e-15),label='Core slip RMS')
axes[1,1].semilogy(t,np.maximum(values('div_l2'),1e-15),label='MAC divergence L2');axes[1,1].legend();axes[1,1].set(xlabel='t U∞ / D')
fig.savefig(out/'diagnostics.png',dpi=180);plt.close(fig)

vmax=max(1,float(np.nanpercentile(np.stack(slices),99.5)))
fig,ax=plt.subplots(figsize=(10,5),layout='constrained')
im=ax.imshow(slices[0],origin='lower',extent=[0,nz*h,0,nx*h],aspect='equal',cmap='inferno',vmin=0,vmax=vmax)
fig.colorbar(im,ax=ax,label='Vorticity magnitude (fixed scale)')
ball=plt.Circle((centres[0][2],centres[0][0]),.5,color='lightgrey');ax.add_patch(ball)
ax.set(xlabel='z / D (flow direction →)',ylabel='x / D',ylim=(1,5),xlim=(0,12))
title=ax.set_title('');images=[]
for index,(sl,tm,c) in enumerate(zip(slices,times,centres)):
    im.set_data(sl);ball.center=(c[2],c[0]);title.set_text(f'Tethered sphere, Re_D={meta["Re_D"]:g}, t={tm:.2f}; actual GPU fields')
    fig.canvas.draw();images.append(Image.fromarray(np.asarray(fig.canvas.buffer_rgba()).copy()).convert('RGB'))
    if index in [len(slices)//2,len(slices)-1]:fig.savefig(out/f'wake_{index}.png',dpi=180)
images[0].save(out/'wake-evolution.gif',save_all=True,append_images=images[1:],duration=110,loop=0);plt.close(fig)

# A final-frame Q surface downstream of the body; do not interpret solid penalty shear as wake vortices.
last=frames[-1];mesh=pv.read(out/('frame_'+last['step']+'.vti'));c=centres[-1]
wake=mesh.clip_box(bounds=(1,5,1,5,c[2]+.6,9.8),invert=False)
surface=wake.contour([.5],scalars='fluid_Q')
plot=pv.Plotter(off_screen=True,window_size=(1500,900));plot.set_background('#101722')
plot.add_mesh(pv.Sphere(radius=.5,center=c,theta_resolution=48,phi_resolution=48),color='silver',smooth_shading=True)
if surface.n_points:
    plot.add_mesh(surface,scalars='vorticity_magnitude',clim=(0,12),cmap='turbo',smooth_shading=True,scalar_bar_args={'title':'Vorticity magnitude','color':'white'})
    surface.save(out/'wake-Q.vtp')
plot.add_mesh(pv.Box(bounds=(1,5,1,5,1,10)).outline(),color='grey')
plot.add_text(f'Tethered sphere | Re_D={meta["Re_D"]:g} | t={times[-1]:.2f}\nWake Q=0.5; exploratory volume-penalty coupling',font_size=15,color='white')
plot.camera_position=[(12,10,12),(3,3,6),(0,1,0)];plot.enable_parallel_projection();plot.camera.parallel_scale=5
plot.show(screenshot=str(out/'wake-Q.png'))
