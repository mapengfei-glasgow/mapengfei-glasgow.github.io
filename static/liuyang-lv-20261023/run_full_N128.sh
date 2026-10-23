#!/bin/bash
# Full model as IBAMR (stage 1+2+3) from t = 0 at G128: passive filling, pseudo-fibre chordae/AV network,
# NHS active tension and Windkessel from t = 1 s, vessel ends fixed/pinned, opening rings and collars, IBAMR FeedbackForcer
# (--feedback; added at the t = 1.153 restart after an aortic-outlet backflow blow-up at t = 1.191). To t = 1.8 s.
# Restart: add --restart $O/checkpoint_latest.bin (same options).
source /home/Pengfei.Ma@glasgow.ac.uk/fdm-3d-v1-workspace-cpu/fdm-3d-v1-workspace/env.local.sh
R=/home/Pengfei.Ma@glasgow.ac.uk/fdm-3d-v1-workspace-cpu/fdm-3d-v1-workspace/runs/liuyang_lv_20261023
L=/home/Pengfei.Ma@glasgow.ac.uk/WholeLVHeartModelling/LiuyangLV
O=$R/full_N128; mkdir -p $O; cd $O
/usr/bin/time -f "WALL %e" env OMP_NUM_THREADS=4 $R/liuyang_lv_v9 --data $R/data/ --inlet $L/HeartPressure.inlet \
  --N 128 --dt 5e-6 --T 1.8 --every 4000 --checkpoint-every 20000 --wall-ring 0.6 --seal-openings 0.5 --seal-width 0.5 \
  --pin-ends 0.5 --fix-ends 0.3 --brinkman-pins --feedback \
  --network $L/Alltogether --network-map $L/PseudoFibre_mapping.inlet --active --windkessel "$@" --out $O/ >> $O/console.log 2>&1
echo "exit $?"
