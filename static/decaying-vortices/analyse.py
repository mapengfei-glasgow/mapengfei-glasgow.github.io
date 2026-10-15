"""Audit 3D vortex decay; export ParaView series, figures and a real-frame GIF."""
import csv
import json
import sys
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from PIL import Image
from vtkmodules.vtkCommonDataModel import vtkImageData
from vtkmodules.vtkIOXML import vtkXMLImageDataWriter
from vtkmodules.util.numpy_support import numpy_to_vtk

path=Path(sys.argv[1] if len(sys.argv)>1 else 'runs/pilot64').resolve()
meta=json.loads((path/'metadata.json').read_text());N=meta['N'];h=1/N
frames=list(csv.DictReader((path/'frames.csv').open()))
out=path/'visualization';out.mkdir(exist_ok=True)
records=[];slices=[];spectra=[];times=[]
zz,yy,xx=np.meshgrid(np.fft.fftfreq(N)*N,np.fft.fftfreq(N)*N,np.fft.rfftfreq(N)*N,indexing='ij')
shell=np.floor(np.sqrt(xx*xx+yy*yy+zz*zz)).astype(int)
weights=np.full(N//2+1,2.);weights[0]=weights[-1]=1
window=np.sin(np.pi*(np.arange(N)+.5)/N)**2
window=window[:,None,None]*window[None,:,None]*window[None,None,:]
pvd=['<?xml version="1.0"?><VTKFile type="Collection" version="0.1" byte_order="LittleEndian"><Collection>']
for index,frame in enumerate(frames):
    a=np.fromfile(path/frame['file'],dtype=np.float32).reshape(N,N,N,3)
    assert np.isfinite(a).all()
    u,v,w=[a[...,i] for i in range(3)]
    uz,uy,ux=np.gradient(u,h,h,h,edge_order=2)
    vz,vy,vx=np.gradient(v,h,h,h,edge_order=2)
    wz,wy,wx=np.gradient(w,h,h,h,edge_order=2)
    ox,oy,oz=wy-vz,uz-wx,vx-uy
    om=np.sqrt(ox*ox+oy*oy+oz*oz)
    Q=-.5*(ux*ux+vy*vy+wz*wz+2*(uy*vx+uz*wx+vz*wy))
    enstrophy=float(.5*np.mean(om.astype(float)**2))
    core=tuple(slice(N//8,7*N//8) for _ in range(3))
    stretch=ox*(ux*ox+uy*oy+uz*oz)+oy*(vx*ox+vy*oy+vz*oz)+oz*(wx*ox+wy*oy+wz*oz)
    visc=float(meta['nu']*sum(np.mean(f.astype(float)**2) for f in (ux,uy,uz,vx,vy,vz,wx,wy,wz)))
    # A tapered spectrum is a scale diagnostic for this nonperiodic box, not a HIT benchmark.
    power=np.zeros(shell.shape)
    for f in (u,v,w):power+=abs(np.fft.rfftn(f*window))**2*weights[None,None,:]
    spectrum=np.bincount(shell.ravel(),weights=power.ravel(),minlength=N)
    spectrum/=spectrum.sum()
    rec=dict(step=int(frame['step']),time=float(frame['time']),
        energy=float(.5*np.mean(np.sum(a.astype(float)**2,axis=3))),
        enstrophy=enstrophy,viscous_gradient_estimate=visc,
        interior_enstrophy=float(.5*np.mean(om[core].astype(float)**2)),
        interior_vortex_stretching=float(np.mean(stretch[core].astype(float))),
        w_rms=float(np.sqrt(np.mean(w.astype(float)**2))),
        max_vorticity=float(om.max()),positive_Q_fraction=float(np.mean(Q>0)),
        windowed_energy_fraction_k_ge_8=float(spectrum[8:].sum()),
        windowed_energy_fraction_k_ge_N_over_3=float(spectrum[N//3:].sum()))
    records.append(rec);spectra.append(spectrum);times.append(rec['time'])
    slices.append(om[N//2,:,:].copy())
    image=vtkImageData();image.SetDimensions(N,N,N);image.SetOrigin(h/2,h/2,h/2);image.SetSpacing(h,h,h)
    for name,array in [('velocity',a.reshape(-1,3)),('vorticity',np.column_stack([f.ravel() for f in (ox,oy,oz)])),('vorticity_magnitude',om.ravel()),('Q',Q.ravel())]:
        arr=numpy_to_vtk(np.ascontiguousarray(array,dtype=np.float32),deep=True);arr.SetName(name)
        image.GetPointData().AddArray(arr)
    name='frame_'+frame['step']+'.vti'
    writer=vtkXMLImageDataWriter();writer.SetFileName(str(out/name));writer.SetInputData(image)
    assert writer.Write()==1
    pvd.append(f'<DataSet timestep="{frame["time"]}" group="" part="0" file="{name}"/>')
    print(f"frame {index+1}/{len(frames)}: t={rec['time']:.4f} enstrophy={enstrophy:.3f} high-k={rec['windowed_energy_fraction_k_ge_8']:.4f}",flush=True)
pvd.append('</Collection></VTKFile>');(out/'fluid.pvd').write_text('\n'.join(pvd))
with (out/'statistics.csv').open('w') as f:
    wr=csv.DictWriter(f,fieldnames=list(records[0]));wr.writeheader();wr.writerows(records)
raw=list(csv.DictReader((path/'diagnostics.csv').open()))
summary=dict(initial=records[0],final=records[-1],
    peak_enstrophy=max(records,key=lambda r:r['enstrophy']),
    max_high_k_fraction=max(records,key=lambda r:r['windowed_energy_fraction_k_ge_8']),
    max_logged_divergence=max(float(r['div_l2']) for r in raw),
    max_logged_CFL=max(float(r['cfl']) for r in raw),
    max_logged_normal_wall_velocity=max(float(r['wall_normal_max']) for r in raw),
    energy_nonincreasing=all(float(b['kinetic_energy'])<=float(a['kinetic_energy'])+1e-10 for a,b in zip(raw,raw[1:])))
(out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
fig,axs=plt.subplots(2,2,figsize=(10,7),layout='constrained')
axs[0,0].plot(times,[r['energy'] for r in records]);axs[0,0].set(xlabel='t',ylabel='Volume-mean kinetic energy')
axs[0,1].plot(times,[r['enstrophy'] for r in records]);axs[0,1].set(xlabel='t',ylabel='Volume-mean enstrophy')
axs[1,0].plot(times,[r['windowed_energy_fraction_k_ge_8'] for r in records]);axs[1,0].set(xlabel='t',ylabel='Tapered-spectrum energy fraction, k ≥ 8')
for idx in sorted(set([0,len(frames)//4,len(frames)//2,len(frames)-1])):
    axs[1,1].loglog(np.arange(1,N//2),spectra[idx][1:N//2],label=f't={times[idx]:.2f}')
axs[1,1].set(xlabel='Wavenumber shell (cycles per box length)',ylabel='Normalized tapered spectrum');axs[1,1].legend()
fig.suptitle(f'{N}³ unforced 3D vortex decay: ν={meta["nu"]}, no-slip walls')
fig.savefig(out/'statistics.png',dpi=180);plt.close(fig)
vmax=float(np.percentile(np.stack(slices),99.5))
fig,axs=plt.subplots(1,4,figsize=(14,3.5),layout='constrained')
ids=[0,len(frames)//4,len(frames)//2,len(frames)-1]
for ax,idx in zip(axs,ids):
    im=ax.imshow(slices[idx],origin='lower',extent=[0,1,0,1],cmap='inferno',vmin=0,vmax=vmax)
    ax.set(xlabel='x',ylabel='y',title=f't={times[idx]:.3f}')
fig.colorbar(im,ax=axs,label='|vorticity|, fixed colour scale')
fig.savefig(out/'vortex-evolution.png',dpi=180);plt.close(fig)
images=[]
fig,ax=plt.subplots(figsize=(6,5),layout='constrained')
im=ax.imshow(slices[0],origin='lower',extent=[0,1,0,1],cmap='inferno',vmin=0,vmax=vmax)
fig.colorbar(im,ax=ax,label='|vorticity|, fixed colour scale')
ax.set(xlabel='x',ylabel='y');title=ax.set_title('')
for sl,t in zip(slices,times):
    im.set_data(sl);title.set_text(f'GPU 3D vortex decay, {N}³, t={t:.3f}\nz≈0.5; actual simulated frames')
    fig.canvas.draw();images.append(Image.fromarray(np.asarray(fig.canvas.buffer_rgba()).copy()).convert('RGB'))
images[0].save(out/'vortex-evolution.gif',save_all=True,append_images=images[1:],duration=110,loop=0)
plt.close(fig)
print(json.dumps(summary,indent=2),flush=True)
