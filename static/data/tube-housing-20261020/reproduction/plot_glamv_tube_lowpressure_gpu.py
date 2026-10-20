"""PyVista sections and histories for completed low-pressure tube/housing runs."""
from pathlib import Path
import os,json,zipfile
os.environ.setdefault('PYVISTA_OFF_SCREEN','true')
import numpy as np
import pyvista as pv
ROOT=Path(__file__).resolve().parents[2];RUN=ROOT/'runs/glamv_tube_dp0p005mmHg_gpu_20261020/G64_R2_tube_tether_dp0p005mmHg_nu0p04_T5';OUT=ROOT/'exports/glamv_tube_dp0p005mmHg_gpu_20261020/sections'
import argparse
parser=argparse.ArgumentParser();parser.add_argument('--run',type=Path,default=RUN);parser.add_argument('--out',type=Path,default=OUT);parser.add_argument('--mesh-data',type=Path);args=parser.parse_args();RUN=args.run;OUT=args.out;OUT.mkdir(parents=True,exist_ok=True)
mesh_warning=''
audit_path=RUN.parent/'FINAL_GEOMETRY_AUDIT.json'
if args.mesh_data and audit_path.exists():
 audit=json.loads(audit_path.read_text())
 if audit['components']['42']['nonpositive_qp']>0:mesh_warning='DIAGNOSTIC ONLY: housing cells inverted'
case_label='Tube + housing' if args.mesh_data else 'Tube only'
pv.OFF_SCREEN=True;pv.global_theme.background='white';pv.global_theme.font.color='black'
g=pv.read(RUN/'fluid_010000.vti');x=np.fromfile(RUN/'Xc_010000.bin').reshape(-1,3);nn,nc,nb=np.fromfile(RUN/'meta.bin',dtype='<i8');assert nb==8
t=np.fromfile(RUN/'dofmaps.bin',dtype='<i8').reshape(int(nc),8);types=np.fromfile(args.mesh_data/'cell_type.bin',dtype='<i8') if args.mesh_data else np.full(len(t),8);solid=pv.UnstructuredGrid({pv.CellType.HEXAHEDRON:t[types==8],pv.CellType.TETRA:t[types==4,:4]},x);surface=solid.extract_surface(algorithm='dataset_surface').clean()
g['pressure']=g['pressure']/1333.22
center=np.array([4.3,4.3,g.bounds[5]/2]);Lz=g.bounds[5];wmin=float(g['w'].min());wmax=float(g['w'].max());vmax=float(np.max(np.linalg.norm(g['velocity'],axis=1)));clims={'w':(min(0,wmin),max(wmax,1e-12)),'pressure':(min(0,float(g['pressure'].min())),max(.005,float(g['pressure'].max())))};blocks=pv.MultiBlock()
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize
from matplotlib.cm import ScalarMappable

def render(normal, origin, scalar, key, eye, scale, size):
 section=g.slice(normal=normal,origin=origin)
 edge=surface.slice(normal=normal,origin=origin)
 assert np.isfinite(section[scalar]).all()
 plotter=pv.Plotter(off_screen=True,window_size=size)
 plotter.add_mesh(section,scalars=scalar,clim=clims[scalar],
                  cmap='coolwarm' if scalar=='w' else 'viridis',
                  lighting=False,show_scalar_bar=False)
 if edge.n_points:plotter.add_mesh(edge,color='black',line_width=2,lighting=False)
 plotter.enable_parallel_projection()
 plotter.camera_position=[eye,origin,(0,1,0) if normal==(0,0,1) else (0,0,1)]
 plotter.camera.parallel_scale=scale
 result=plotter.screenshot(return_img=True)
 plotter.close();blocks[key+'_'+scalar]=section
 return result

def composite(panels, titles, filename, longitudinal=False):
 cols=len(titles)
 fig=plt.figure(figsize=(6*cols,13 if longitudinal else 10))
 grid=fig.add_gridspec(4,cols,height_ratios=[1,.055,1,.055],hspace=.28,wspace=.035)
 fig.subplots_adjust(left=.04,right=.96,bottom=.085,top=.9)
 for row,scalar in enumerate(['w','pressure']):
  for col,title in enumerate(titles):
   ax=fig.add_subplot(grid[row*2,col])
   ax.imshow(panels[row][col]);ax.set_axis_off();ax.set_title(title,fontsize=11,pad=8)
  cax=fig.add_subplot(grid[row*2+1,:])
  mapper=ScalarMappable(norm=Normalize(*clims[scalar]),cmap='coolwarm' if scalar=='w' else 'viridis')
  bar=fig.colorbar(mapper,cax=cax,orientation='horizontal')
  bar.set_label('Axial velocity w (cm/s)' if scalar=='w' else 'Pressure (mmHg)',fontsize=11,labelpad=5)
  bar.ax.tick_params(labelsize=10)
 fig.suptitle(case_label+' | t = 5 s | pressure difference = 0.005 mmHg',fontsize=15,y=.975)
 fig.text(.5,.025,'Black: actual deformed wall'+('\n'+mesh_warning if mesh_warning else ''),
          ha='center',va='center',fontsize=10,color='firebrick' if mesh_warning else 'black')
 fig.savefig(OUT/filename,dpi=160);plt.close(fig)

panels=[]
for row,scalar in enumerate(['w','pressure']):
 images=[]
 for col,axis in enumerate(['XZ','YZ']):
  normal=(0,1,0) if axis=='XZ' else (1,0,0)
  eye=center+np.array([0,-30,0] if axis=='XZ' else [30,0,0])
  images.append(render(normal,center,scalar,axis+'_'+str(row),eye,Lz*.54,(700,950)))
 panels.append(images)
composite(panels,['XZ: y = 4.3 cm','YZ: x = 4.3 cm'],'glamv_tube_longitudinal_t5.png',True)
zvalues=[.10,4.5,Lz/2,Lz-.10] if args.mesh_data else [.10,Lz/2,Lz-.10]
panels=[]
for row,scalar in enumerate(['w','pressure']):
 images=[]
 for col,z in enumerate(zvalues):
  origin=(4.3,4.3,z)
  images.append(render((0,0,1),origin,scalar,f'XY_{col}_{row}',(4.3,4.3,z+30),4.5,(700,700)))
 panels.append(images)
composite(panels,[f'z = {z:.3f} cm' for z in zvalues],'glamv_tube_cross_sections_t5.png')
blocks.save(OUT/'glamv_tube_slices_t5.vtm')
settings=dict(mesh_warning=mesh_warning,includes_housing=bool(args.mesh_data),pressure_unit='mmHg',pressure_difference_mmHg=.005,nu_cm2_s=.04,source=str((RUN/'fluid_010000.vti').relative_to(ROOT)),t_s=5,velocity_range_cm_s=[wmin,wmax],speed_max_cm_s=vmax,clims=clims,domain_cm=[8.6,8.6,Lz],cross_section_z_cm=zvalues,wall='Actual Xc_010000.bin, native mixed-element exterior surface; no coordinate shift/rescaling',warning='Nodal-averaged Eulerian fields are also defined within IB solid regions; outlines do not mask solid fields. T=5 is transient, not established steady Poiseuille flow.')
(OUT/'SETTINGS.json').write_text(json.dumps(settings,indent=2)+'\n');(OUT/'README.md').write_text('''# glamv tube/housing sections, t=5 s

PyVista rendering of the completed G64/native R2 Q1 tube, pure tethering. Longitudinal panels: columns XZ (y=4.3) and YZ (x=4.3); rows axial velocity and pressure. Axial coordinate z increases upward. Cross sections: z=0.1 cm, domain midpoint, and Lz-0.1 cm (plus z=4.5 cm through the disk when housing is present); viewed from +z with +y up. Every velocity panel uses the same full-volume axial-velocity range; pressure is converted from dyn/cm² to mmHg and uses the full field range including at least 0–0.005 mmHg. The run uses rho=1, nu=0.04 cm²/s and pressure difference 0.005 mmHg.

Black outlines are slices of the actual deformed mixed-element exterior surface. Eulerian fields within the IB solid remain shown; the plots are not fluid-only masks. Slicing/interpolation does not increase solver resolution. The last two sections lie close to the tube ends but inside their reference axial extent. End-wall motion can change this relation locally.

The run remains transient at t=5 s; neither energy stability nor Sampson flow is established by appearance. Source and scales are in SETTINGS.json. The VTM plus its accompanying directory can be opened in ParaView/PyVista for the numerical fluid slices. No new solver was launched.
''')
import csv
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
with (RUN/'probe_flow.csv').open() as f:
 rows=list(csv.DictReader(f))
times=np.array([float(r['t']) for r in rows]);qin=-np.array([float(r['Q_in']) for r in rows]);qout=np.array([float(r['Q_out']) for r in rows])
with (RUN/'probe_radial.csv').open() as f:
 radial=list(csv.DictReader(f))
fig,axes=plt.subplots(1,2,figsize=(12,4.2),layout='constrained')
axes[0].plot(times,qin,label='Inlet (into domain)',lw=2);axes[0].plot(times,qout,'--',label='Outlet (out of domain)',lw=1.8)
if args.mesh_data:
 with (ROOT/'runs/glamv_tube_dp0p005mmHg_gpu_20261020/G64_R2_tube_tether_dp0p005mmHg_nu0p04_T5/probe_flow.csv').open() as f:
  reference=list(csv.DictReader(f))
 axes[0].plot([float(r['t']) for r in reference],[float(r['Q_out']) for r in reference],':',label='Tube only: outlet',color='black',lw=2)
axes[0].set(xlabel='Time (s)',ylabel='Flow rate (mL/s)',title='Boundary-hole flow rates');axes[0].legend();axes[0].grid(alpha=.25)
axes[0].annotate(f'{qout[-1]:.1f} mL/s',xy=(times[-1],qout[-1]),xytext=(-80,-25),textcoords='offset points')
axes[1].plot([float(r['t']) for r in radial],[float(r['w_r00']) for r in radial],color='tab:orange',lw=2)
axes[1].set(xlabel='Time (s)',ylabel='Axial velocity (cm/s)',title='Centreline velocity at pipe midpoint');axes[1].grid(alpha=.25)
fig.suptitle(case_label+' | G64 / R2, GPU | pressure difference 0.005 mmHg | nu = 0.04 cm²/s')

if mesh_warning:
 fig.get_layout_engine().set(rect=(0,.08,1,.92))
 fig.text(.5,.025,mesh_warning,ha='center',color='red',fontsize=11)
fig.savefig(OUT/'glamv_tube_history_t5.png',dpi=180);plt.close(fig)
if mesh_warning:
 with (OUT/'README.md').open('a') as f:f.write('\nWARNING: '+mesh_warning+'. See FINAL_GEOMETRY_AUDIT.json in the simulation directory parent. These plots are for diagnosis, not validated rigid-housing results.\n')
archive=OUT.parent/'glamv_tube_sections_t5.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
 for f in sorted(OUT.rglob('*')):
  if f.is_file():z.write(f,str(Path('sections')/f.relative_to(OUT)))
with zipfile.ZipFile(archive) as z:assert z.testzip() is None
print(json.dumps(settings,indent=2),flush=True)
