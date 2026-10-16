"""PyVista/Matplotlib views of actual lid-driven sphere simulation frames."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'decaying-vortices/python-packages'))
import csv,json
import numpy as np
import pyvista as pv
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from PIL import Image
path=Path(sys.argv[1] if len(sys.argv)>1 else 'runs/main96').resolve()
meta=json.loads((path/'metadata.json').read_text());N=meta['nx'];h=meta['h'];R=meta['radius']
frames=list(csv.DictReader((path/'frames.csv').open()));rows=list(csv.DictReader((path/'diagnostics.csv').open()))
out=path/'visualization';out.mkdir(exist_ok=True)
coords=(np.arange(N)+.5)*h
pvd=['<?xml version="1.0"?><VTKFile type="Collection" version="0.1" byte_order="LittleEndian"><Collection>']
slices=[];centres=[];times=[];cross=[]
for k,frame in enumerate(frames):
    a=np.fromfile(path/frame['file'],dtype=np.float32).reshape(N,N,N,3);assert np.isfinite(a).all()
    c=np.array([float(frame[key]) for key in ['cx','cy','cz']]);centres.append(c);times.append(float(frame['time']))
    mesh=pv.ImageData(dimensions=(N,N,N),spacing=(h,h,h),origin=(h/2,h/2,h/2));mesh['velocity']=a.reshape(-1,3)
    mesh['speed']=np.linalg.norm(mesh['velocity'],axis=1)
    mesh=mesh.compute_derivative(scalars='velocity',gradient=False,vorticity='vorticity',qcriterion='Q')
    mesh['vorticity_magnitude']=np.linalg.norm(mesh['vorticity'],axis=1)
    d2=(coords[:,None,None]-c[2])**2+(coords[None,:,None]-c[1])**2+(coords[None,None,:]-c[0])**2
    mesh['fluid_Q']=np.where(d2.ravel()>(R+h/2)**2,mesh['Q'],0)
    name='frame_'+frame['step']+'.vti';mesh.save(out/name)
    pvd.append(f'<DataSet timestep="{frame["time"]}" part="0" file="{name}"/>')
    mid=N//2
    speed=mesh['speed'].reshape(N,N,N)[mid,:,:].copy()
    speed[(coords[:,None]-c[1])**2+(coords[None,:]-c[0])**2<R**2]=np.nan
    slices.append(speed);cross.append(a[mid,:,:,:2].copy())
    print(f'Processed {k+1}/{len(frames)} t={times[-1]}',flush=True)
pvd.append('</Collection></VTKFile>');(out/'fluid.pvd').write_text('\n'.join(pvd))
def val(key):return np.array([float(r[key]) for r in rows])
summary=dict(grid=N,Re_L=meta['Re_L'],final_time=times[-1],max_speed=float(val('max_speed').max()),
    max_div_l2=float(val('div_l2').max()),max_core_slip_rms=float(val('core_slip_rms').max()),
    final_core_slip_rms=float(val('core_slip_rms')[-1]),
    max_tether_displacement=float(np.sqrt(sum((val(key)-.5)**2 for key in ['cx','cy','cz'])).max()),
    final_centre=centres[-1].tolist())
(out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))
fig,ax=plt.subplots(figsize=(7,6),layout='constrained')
im=ax.imshow(slices[0],origin='lower',extent=(0,1,0,1),cmap='viridis',vmin=0,vmax=1)
fig.colorbar(im,ax=ax,label='Speed / final lid speed')
ball=plt.Circle((centres[0][0],centres[0][1]),R,color='silver');ax.add_patch(ball)
ax.annotate('',xy=(.7,.99),xytext=(.3,.99),arrowprops={'arrowstyle':'->','color':'red'},annotation_clip=False)
ax.set(xlabel='x / L',ylabel='y / L');title=ax.set_title('');images=[]
for k,(sl,tm,c) in enumerate(zip(slices,times,centres)):
    im.set_data(sl);ball.center=(c[0],c[1]);title.set_text(f'Lid-driven sphere, Re_L={meta["Re_L"]:g}, t={tm:.2f}\nLid motion +x; slice near z=0.5')
    fig.canvas.draw();images.append(Image.fromarray(np.asarray(fig.canvas.buffer_rgba()).copy()).convert('RGB'))
    if k==len(slices)-1:
        vel=cross[k];ax.streamplot(coords,coords,vel[:,:,0],vel[:,:,1],color='white',linewidth=.6,density=1.3)
        # Repaint solid over streamlines passing through the diffuse penalized body.
        ax.add_patch(plt.Circle((c[0],c[1]),R,color='silver',zorder=10))
        fig.savefig(out/'cavity-flow.png',dpi=200)
images[0].save(out/'cavity-evolution.gif',save_all=True,append_images=images[1:],duration=100,loop=0);plt.close(fig)
fig,axes=plt.subplots(1,2,figsize=(10,4),layout='constrained')
for key in ['cx','cy','cz']:axes[0].plot(val('time'),val(key)-.5,label=key)
axes[0].legend();axes[0].set(xlabel='t U_lid / L',ylabel='Centre displacement / L')
axes[1].semilogy(val('time'),np.maximum(val('div_l2'),1e-16),label='MAC divergence L2')
axes[1].semilogy(val('time'),np.maximum(val('core_slip_rms'),1e-16),label='Core slip RMS');axes[1].legend();axes[1].set(xlabel='t U_lid / L')
fig.savefig(out/'diagnostics.png',dpi=180);plt.close(fig)
surface=mesh.contour([.5],scalars='fluid_Q',compute_normals=True)
plot=pv.Plotter(off_screen=True,window_size=(1300,1100));plot.set_background('#101722')
plot.add_mesh(mesh.outline(),color='grey')
plot.add_mesh(pv.Sphere(radius=R,center=centres[-1],theta_resolution=64,phi_resolution=64),color='silver',smooth_shading=True)
if surface.n_points:
    plot.add_mesh(surface,scalars='vorticity_magnitude',clim=(0,20),cmap='turbo',smooth_shading=True,scalar_bar_args={'title':'Vorticity magnitude','color':'white'})
plot.add_arrows(np.array([[.3,1.04,.5]]),np.array([[.4,0,0]]),mag=1,color='red')
plot.add_text(f'Lid-driven cavity + rigid sphere | t={times[-1]:.2f}\nRe_L={meta["Re_L"]:g}, Q=0.5; lid moves +x',font_size=16,color='white')
plot.camera_position=[(2.2,1.8,2),(.5,.5,.5),(0,1,0)];plot.enable_parallel_projection();plot.camera.parallel_scale=.9
plot.show(screenshot=str(out/'cavity-Q.png'))
