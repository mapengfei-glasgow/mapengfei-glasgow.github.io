"""PyVista Q-criterion figure, independently recomputed from saved velocity."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent/'python-packages'))
import numpy as np
import pyvista as pv

root=Path(__file__).resolve().parent
source=root/'runs/main128/visualization/frame_3000.vti'
target=root/'runs/main128/visualization/q-criterion-pyvista.png'
mesh=pv.read(source)
# Compute Q from the actual velocity, rather than contouring a precomputed scalar.
derived=mesh.compute_derivative(scalars='velocity',gradient=False,
    vorticity='vorticity_pyvista',qcriterion='Q_pyvista',preference='point')
assert np.isfinite(derived['Q_pyvista']).all()
derived['omega_magnitude']=np.linalg.norm(derived['vorticity_pyvista'],axis=1)
surface=derived.contour([60.],scalars='Q_pyvista',compute_normals=True)
assert surface.n_points>0
# Check against the independent NumPy derivative in the interior; boundary
# stencils may differ (VTK vs NumPy one-sided derivatives).
N=128
qv=derived['Q_pyvista'].reshape(N,N,N)
qn=mesh['Q'].reshape(N,N,N)
relative=float(np.linalg.norm(qv[2:-2,2:-2,2:-2]-qn[2:-2,2:-2,2:-2])/
               np.linalg.norm(qn[2:-2,2:-2,2:-2]))
assert relative<1e-4,relative
plot=pv.Plotter(off_screen=True,window_size=[1600,1300])
plot.set_background('#101722')
plot.add_mesh(mesh.outline(),color='#99a6b8',line_width=1)
plot.add_mesh(surface,scalars='omega_magnitude',cmap='turbo',clim=[0,150],
    smooth_shading=True,scalar_bar_args={'title':'Vorticity magnitude','color':'white'})
plot.add_text('GPU 3D vortex decay | 128³ | t = 0.75\nQ = 60 isosurface, coloured by vorticity',
              font_size=18,color='white')
plot.camera_position=[(2.25,1.85,1.65),(.5,.5,.5),(0,0,1)]
plot.enable_parallel_projection();plot.camera.parallel_scale=.85
plot.show(screenshot=str(target),auto_close=True)
surface.save(str(target.with_suffix('.vtp')))
print(f'PyVista {pv.__version__}; interior relative Q difference={relative:.3e}; surface points={surface.n_points}')
print(target)
