"""Render reference mesh with PyVista; draw code-derived boundary and RCR diagrams.
Run using the pyvista-mpm environment. Inputs: ../data/*.bin.
"""
from pathlib import Path
import os
os.environ.setdefault('MPLCONFIGDIR','/tmp/liuyang-model-mpl')
import numpy as np
import pyvista as pv
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle
pv.OFF_SCREEN=True
OUT=Path(__file__).resolve().parent; D=OUT.parent/'data'
X=np.fromfile(D/'ref_nodes.bin').reshape(-1,3)-[-5,-26.5,133.35]
cm=np.fromfile(D/'cell_marker.bin',dtype=np.int64)
dm=np.fromfile(D/'dofmaps.bin',dtype=np.int64).reshape(len(cm),-1)[:,:4]
COL={'LV':'#d95050','LA':'#347fc4','MV':'#e6a023','Vessels':'#9b9da3','Apex':'#9a4cac','End segments':'#477766'}
groups={'LV':[21,22],'LA':[23,24],'MV':[30,40,5],'Vessels':[100,200,1000],'Apex':[211],'End segments':[4099]}
surfs={}
for k,ids in groups.items():
 t=dm[np.isin(cm,ids)];grid=pv.UnstructuredGrid(np.c_[np.full(len(t),4),t].ravel(),np.full(len(t),10,np.uint8),X)
 surfs[k]=grid.extract_surface(algorithm='dataset_surface').clean()
 print(k,len(t),flush=True)
def meshes(p,transparent=False):
 for k,s in surfs.items():p.add_mesh(s,color=COL[k],opacity=(.15 if transparent and k in ('LV','LA','Vessels') else 1),smooth_shading=True,label=k)
def camera(p):
 p.camera_position=[(36,-35,29),(7.5,9,9),(0,0,1)];p.camera.parallel_projection=True;p.camera.parallel_scale=11
p=pv.Plotter(shape=(1,2),off_screen=True,window_size=(2000,1100));p.set_background('#fafbfC')
for i in range(2):
 p.subplot(0,i);meshes(p,i==1);camera(p)
 p.add_text('A  Reference geometry' if i==0 else 'B  Translucent chamber walls',font_size=18,color='#15263b')
 p.add_axes(viewport=(.78,.02,.98,.20));p.add_legend(size=(.23,.24),bcolor='white',face='r',loc='lower left')
p.screenshot(str(OUT/'geometry.png'));p.close()
# Opening centres in shifted simulation coordinates; numbered circles are schematic radii.
centres=np.array([[0,13.604,10.658],[0,9.341,12.040],[10.782,16.12,11.177],[11.600,11.838,16.13],[4.190,5.180,16.13]])
names=['1 RIPV','2 RSPV','3 LIPV','4 LSPV','5 Aorta']
p=pv.Plotter(off_screen=True,window_size=(1350,1250));p.set_background('white');meshes(p,True)
p.add_mesh(pv.Box(bounds=(0,17,0,16.12,0,16.13)).outline(),color='#64758b',line_width=2)
for j,c in enumerate(centres):
 normal=(1,0,0) if j<2 else ((0,1,0) if j==2 else (0,0,1))
 p.add_mesh(pv.Disc(center=c,inner=0,outer=[1.448,1.468,1.473,1.472,2.434][j],normal=normal,c_res=80),color='#d95050' if j==4 else '#347fc4',opacity=.65)
p.add_point_labels(centres,names,font_size=22,point_size=10,always_visible=True,shape_color='white',shape_opacity=.9,text_color='#15263b')
camera(p);p.camera.parallel_scale=13;p.add_axes();p.screenshot(str(OUT/'boundary-render.png'));p.close()
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':12,'text.color':'#15263b','axes.labelcolor':'#15263b'})
fig=plt.figure(figsize=(16,10),facecolor='white');ax=fig.add_axes([.0,.04,.62,.86]);ax.imshow(plt.imread(OUT/'boundary-render.png'));ax.axis('off')
fig.text(.04,.96,'Boundary conditions and coupling',fontsize=24,weight='bold')
fig.text(.64,.88,'1–4  Pulmonary-vein pressure inlets',fontsize=16,color=COL['LA'],weight='bold')
fig.text(.64,.82,'RIPV, RSPV: x = 0\nLIPV: y = 16.12 cm\nLSPV: z = 16.13 cm',linespacing=1.7,va='top')
fig.text(.64,.69,'p = p_PV,i(t) from HeartPressure.inlet\nTangential velocity = 0\nFlow is solved; reversal is permitted.',linespacing=1.6,va='top')
fig.text(.64,.57,'5  Aortic pressure outlet',fontsize=16,color=COL['LV'],weight='bold')
fig.text(.64,.51,'z = 16.13 cm; positive Q points out\nt < 1 s: pressure from input file\nt ≥ 1 s: three-element Windkessel',linespacing=1.6,va='top')
fig.text(.64,.39,'Outer box and end supports',fontsize=16,weight='bold')
fig.text(.64,.32,'Outside ports and wall rings: p = 0 traction\nWall rings: no-slip\nEnd nodes ≤ 0.3 cm from box: fixed\nEnd cells ≤ 0.5 cm: tethered',fontsize=11,linespacing=1.7,va='top')
fig.text(.64,.18,'Brinkman opening collars: 0.5 cm depth\nFeedback damping added at 1.153 s restart\nTissue motion ↔ fluid through IB coupling',fontsize=11,linespacing=1.7,va='top')
fig.text(.04,.025,'Reference configuration; coordinates shifted by domain lower corner. Box: 17 × 16.12 × 16.13 cm. Port discs show runtime radii.',fontsize=11)
fig.savefig(OUT/'boundary-conditions.png',dpi=160);plt.close(fig)
# Three-element RCR network: Zc in series with parallel R and C to reference pressure.
fig,ax=plt.subplots(figsize=(14,8));fig.patch.set_facecolor('white');ax.set_xlim(0,14);ax.set_ylim(0,8);ax.axis('off')
ink='#20364d';red=COL['LV'];blue=COL['LA']
def line(x,y,**kw):ax.plot(x,y,color=ink,lw=2.2,**kw)
def resistor(x1,x2,y,label):
 line([x1,x1+.25],[y,y]);line([x2-.25,x2],[y,y]);ax.add_patch(Rectangle((x1+.25,y-.23),x2-x1-.5,.46,fill=False,ec=ink,lw=2));ax.text((x1+x2)/2,y+.46,label,ha='center',fontsize=15)
ax.text(.5,7.5,'Aortic three-element Windkessel (RCR)',fontsize=23,weight='bold')
ax.add_patch(Rectangle((.5,3.9),2.1,1.6,facecolor='#fbe9e7',ec=red,lw=2));ax.text(1.55,4.7,'3D aortic\noutlet',ha='center',va='center',fontsize=17)
line([2.6,3.5],[4.7,4.7]);resistor(3.5,5.8,4.7,r'$Z_c$');line([5.8,7],[4.7,4.7]);ax.plot(7,4.7,'o',color=ink)
ax.annotate('',xy=(3.5,5.7),xytext=(2.7,5.7),arrowprops={'arrowstyle':'->','color':red,'lw':2});ax.text(3.1,6.05,r'$Q(t)>0$',ha='center',color=red,fontsize=16)
ax.text(3,3.8,r'$P_{Ao}(t)$',fontsize=16,color=red);ax.text(6.9,5.3,r'$P_C(t)$',fontsize=16,color=blue)
line([7,7],[4.7,6.3]);resistor(7,11,6.3,'');ax.text(9,6.3,r'$R$',ha='center',va='center',fontsize=15);line([11,11],[6.3,2.6]);line([7,7],[4.7,2.6]);line([7,8.75],[2.6,2.6]);line([9.15,11],[2.6,2.6]);line([8.75,8.75],[1.95,3.25]);line([9.15,9.15],[1.95,3.25]);ax.text(8.95,1.35,r'$C$',fontsize=17,ha='center')
line([11,12.5],[4.7,4.7]);ax.text(12.6,4.7,r'$P_{ref}=0$',fontsize=16,va='center')
ax.text(.5,.55,r'$P_{Ao}=Z_c Q+P_C$'+'     '+r'$C\,dP_C/dt=Q-P_C/R$',fontsize=19)
ax.text(.5,6.8,r'$R=0.678$ mmHg·s/ml     $Z_c=0.0284$ mmHg·s/ml     $C=3.4181$ ml/mmHg',fontsize=14)
fig.savefig(OUT/'windkessel.png',dpi=160,bbox_inches='tight');fig.savefig(OUT/'windkessel.svg',bbox_inches='tight');plt.close(fig)
print('Done',flush=True)
