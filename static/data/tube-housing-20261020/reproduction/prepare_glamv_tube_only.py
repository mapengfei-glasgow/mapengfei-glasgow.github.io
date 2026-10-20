"""Extract native R2 Q1 tube (marker 1) without changing geometry or quadrature."""
from pathlib import Path
import numpy as np,json
ROOT=Path(__file__).resolve().parents[2];SRC=ROOT/'fdm-3d-v1-geometry/src/ibm/data/glamv_hex_r2';OUT=ROOT/'runs/glamv_tube_only_20261019/tube_R2_Q1'
def main():
 if OUT.exists():raise SystemExit(f'Refusing overwrite {OUT}')
 rd=lambda n,dt='<f8':np.fromfile(SRC/n,dtype=dt)
 markers=rd('cell_marker.bin','<i8');nc=len(markers);ids=np.flatnonzero(markers==1);ct=rd('cell_type.bin','<i8')[ids];assert (ct==8).all();t=rd('dofmaps.bin','<i8').reshape(nc,3,8)[ids,0];x=rd('ref_nodes.bin').reshape(-1,3);nodes,inv=np.unique(t,return_inverse=True);xx=x[nodes];tt=inv.reshape(-1,8);n=len(ids)
 OUT.mkdir();w=lambda name,v,dt='<f8':np.asarray(v,dtype=dt).tofile(OUT/name)
 w('ref_nodes.bin',xx);w('dofmaps.bin',np.repeat(tt[:,None,:],3,axis=1),'<i8');w('cell_marker.bin',markers[ids],'<i8');w('cell_type.bin',ct,'<i8');w('source_cell.bin',ids,'<i8');w('source_node.bin',nodes,'<i8')
 for name,tail in [('qp_grad.bin',(8,8,3)),('qp_phi.bin',(8,8)),('qp_wJ.bin',(8,))]:
  raw=np.memmap(SRC/name,dtype='<f8',mode='r',shape=(nc,*tail));w(name,raw[ids])
 for name,tail in [('J.bin',()),('inv_H.bin',(9,))]:w(name,rd(name).reshape(nc,*tail)[ids])
 for name in ['weights.bin','basis_values_ref.bin','basis_derivatives_ref.bin']:w(name,rd(name))
 for name,value in [('num_cells.bin',n),('num_dofs.bin',len(xx)),('num_basis.bin',8),('num_qp.bin',8),('num_faces.bin',0),('num_qp_face.bin',0)]:w(name,[value],'<i8')
 qphi=np.fromfile(OUT/'qp_phi.bin').reshape(n,8,8);qw=np.fromfile(OUT/'qp_wJ.bin').reshape(n,8);assert (qw>0).all() and np.isfinite(qw).all();assert np.max(abs(qphi.sum(2)-1))<1e-12
 grad=np.memmap(OUT/'qp_grad.bin',dtype='<f8',mode='r',shape=(n,8,8,3));err=0.
 for st in range(0,n,8192):
  en=min(st+8192,n);F=np.einsum('eai,eqaj->eqij',xx[tt[st:en]],grad[st:en]);err=max(err,float(abs(F-np.eye(3)).max()))
 assert err<1e-8
 extent=np.ptp(xx,axis=0);domain=np.array([8.6,8.6,16.09938]);pad=np.repeat((domain/extent-1)/2,2);center=(xx.min(0)+xx.max(0))/2;shift=domain/2-center
 report=dict(source=str(SRC.relative_to(ROOT)),selection='cell_marker == 1 only; no leaflets, chordae, caps, annulus or housing',cells=n,nodes=len(xx),element='Native Q1 hexahedra',reference_bbox=[xx.min(0).tolist(),xx.max(0).tolist()],shift_to_domain=shift.tolist(),domain_cm=domain.tolist(),padding=pad.tolist(),inlet_radius_cm=3.5,volume_cm3=float(qw.sum()),max_reference_F_identity_error=err,min_qp_weight=float(qw.min()),coordinate_change=False,quadrature_change=False,alignment='Identical fixed center/domain to current glamv G128/G256 case',end_clearance_cm=float((domain[2]-extent[2])/2))
 (OUT/'VALIDATION.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
