"""Extract original R2 tube and housing; preserve mixed quadrature and component overlap."""
from pathlib import Path
import json
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
SRC=ROOT/'fdm-3d-v1-geometry/src/ibm/data/glamv_hex_r2'
OUT=ROOT/'runs/glamv_tube_housing_20261020/mesh'

def main():
 if OUT.exists():raise RuntimeError(f'Refusing overwrite {OUT}')
 rd=lambda n,dt='<f8':np.fromfile(SRC/n,dtype=dt)
 mk=rd('cell_marker.bin','<i8');nc=len(mk);ids=np.flatnonzero(np.isin(mk,[1,42]));ct=rd('cell_type.bin','<i8')[ids]
 t=rd('dofmaps.bin','<i8').reshape(nc,3,8)[ids,0];x=rd('ref_nodes.bin').reshape(-1,3)
 nodes,inv=np.unique(t,return_inverse=True);xx=x[nodes];tt=inv.reshape(-1,8);n=len(ids)
 OUT.mkdir(parents=True);w=lambda name,v,dt='<f8':np.asarray(v,dtype=dt).tofile(OUT/name)
 w('ref_nodes.bin',xx);w('dofmaps.bin',np.repeat(tt[:,None,:],3,axis=1),'<i8');w('cell_type.bin',ct,'<i8')
 # The tube demo's rigid marker mask is {1,2,3}; map housing 42 to 2, retaining source IDs.
 w('cell_marker.bin',np.where(mk[ids]==42,2,1),'<i8');w('source_marker.bin',mk[ids],'<i8');w('source_cell.bin',ids,'<i8');w('source_node.bin',nodes,'<i8')
 for name,tail in [('qp_grad.bin',(8,8,3)),('qp_phi.bin',(8,8)),('qp_wJ.bin',(8,)),('J.bin',()),('inv_H.bin',(9,))]:
  raw=np.memmap(SRC/name,dtype='<f8',mode='r',shape=(nc,*tail));w(name,raw[ids])
 for name in ['weights.bin','basis_values_ref.bin','basis_derivatives_ref.bin']:w(name,rd(name))
 for name,value in [('num_cells.bin',n),('num_dofs.bin',len(xx)),('num_basis.bin',8),('num_qp.bin',8),('num_faces.bin',0),('num_qp_face.bin',0)]:w(name,[value],'<i8')
 phi=np.memmap(OUT/'qp_phi.bin',dtype='<f8',mode='r',shape=(n,8,8));qw=np.memmap(OUT/'qp_wJ.bin',dtype='<f8',mode='r',shape=(n,8));grad=np.memmap(OUT/'qp_grad.bin',dtype='<f8',mode='r',shape=(n,8,8,3));err=0.
 assert np.isfinite(qw).all() and (qw>=0).all() and (qw.sum(1)>0).all()
 for st in range(0,n,8192):
  en=min(st+8192,n);active=qw[st:en]>0
  assert np.max(abs(phi[st:en].sum(2)[active]-1))<1e-12
  local=xx[tt[st:en]];F=np.einsum('eai,eqaj->eqij',local-local[:,:1],grad[st:en]);err=max(err,float(abs(F[active]-np.eye(3)).max()))
 assert err<1e-8
 shift=np.array([4.3,4.3,8.04969]);domain=np.array([8.6,8.6,16.09938]);assert ((xx+shift)>=0).all() and ((xx+shift)<=domain).all()
 components={str(marker):dict(cells=int((mk[ids]==marker).sum()),volume_cm3=float(qw[mk[ids]==marker].sum())) for marker in [1,42]}
 report=dict(source=str(SRC.relative_to(ROOT)),cells=n,nodes=len(xx),components=components,marker_mapping={'1':1,'42':2},hexes=int((ct==8).sum()),tets=int((ct==4).sum()),max_reference_F_error=err,domain_cm=domain.tolist(),shift=shift.tolist(),reference_bbox=[xx.min(0).tolist(),xx.max(0).tolist()],geometry_and_quadrature_unchanged=True,component_overlap_preserved=True)
 (OUT/'VALIDATION.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
