"""Check final deformation per component, without conflating finite completion with mesh validity."""
from pathlib import Path
import json
import argparse
import numpy as np
ROOT=Path(__file__).resolve().parents[2];P=ROOT/'runs/glamv_tube_housing_20261020';M=P/'mesh';RUN=P/'G64_R2_tube_housing_dp0p005mmHg_nu0p04_T5'

def evaluate(run, mesh, step, dt):
 RUN=Path(run);M=Path(mesh)
 n=int(np.fromfile(M/'num_cells.bin',dtype='<i8')[0]);t=np.fromfile(M/'dofmaps.bin',dtype='<i8').reshape(n,3,8)[:,0]
 marker=np.fromfile(M/'source_marker.bin',dtype='<i8');x=np.fromfile(RUN/f'Xc_{step:06d}.bin').reshape(-1,3);x0=np.fromfile(RUN/'ref_nodes.bin').reshape(-1,3)
 grad=np.memmap(M/'qp_grad.bin',dtype='<f8',mode='r',shape=(n,8,8,3));qw=np.memmap(M/'qp_wJ.bin',dtype='<f8',mode='r',shape=(n,8))
 source=np.fromfile(M/'source_cell.bin',dtype='<i8');types=np.fromfile(M/'cell_type.bin',dtype='<i8')
 result={str(k):dict(J_min=float('inf'),J_max=-float('inf'),nonpositive_qp=0) for k in [1,42]}
 for st in range(0,n,8192):
  en=min(st+8192,n);local=x[t[st:en]];F=np.einsum('eai,eqaj->eqij',local-local[:,:1],grad[st:en]);J=np.linalg.det(F)
  for k in [1,42]:
   active=(qw[st:en]>0)&(marker[st:en,None]==k)
   if not active.any():continue
   values=J[active];assert np.isfinite(values).all();r=result[str(k)]
   if float(values.min())<r['J_min']:
    candidates=np.where(active,J,np.inf);ei,qi=np.unravel_index(np.argmin(candidates),candidates.shape);cell=st+int(ei);centre=x0[t[cell,:int(types[cell])]].mean(0);r.update(min_J_source_cell=int(source[cell]),min_J_reference_center_cm=centre.tolist(),min_J_reference_radius_cm=float(np.linalg.norm(centre[:2]-[4.3,4.3])))
   r['J_min']=min(r['J_min'],float(values.min()));r['J_max']=max(r['J_max'],float(values.max()));r['nonpositive_qp']+=int((values<=0).sum())
 for k in [1,42]:
  nodes=np.unique(t[marker==k]);xx=x[nodes];result[str(k)].update(max_displacement_cm=float(np.linalg.norm(xx-x0[nodes],axis=1).max()),bbox=[xx.min(0).tolist(),xx.max(0).tolist()])
 report=dict(t_s=step*dt,components=result,note='Positive J and finite completion alone do not establish near-rigidity, negligible leakage or physical convergence.')
 return report

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--step',type=int,default=10000);parser.add_argument('--dt',type=float,default=.0005);args=parser.parse_args()
 report=evaluate(RUN,M,args.step,args.dt)
 (P/('FINAL_GEOMETRY_AUDIT.json' if args.step==10000 else f'GEOMETRY_AUDIT_{args.step:06d}.json')).write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
