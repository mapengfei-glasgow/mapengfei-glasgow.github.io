#!/bin/bash
# av_glamv runs of 2026-10-28/29 (runs/av_glamv_20261028): aortic valve in a straight tube, two sine cycles.
#   Defaults (av_glamv.cu): 48 x 48 x 144, h = 0.1 cm, dt = 1e-4, nu = 0.04, CBS43; inlet face 5 total pressure
#   5 sin(2 pi 1.25 t) mmHg, outlet face 4 p = 0; leaflets SFRH mu = 2e5, lambda = 3e5; root/tube (5, 17) tethers +
#   Brinkman mask + end collars; FeedbackForcer on both z faces; leaflet attachment band (0.06 cm) fixed.
#   tp_fixed:       root/tube nodes also held at X_ref (published result)
#   tp_tether:      root/tube held by tethers only (--tether-pins)
#   tp_tether_up:   as tp_tether with SOU upwind convection
# Restart: add --restart <out>/checkpoint_latest.bin (same options).
source /home/Pengfei.Ma@glasgow.ac.uk/fdm-3d-v1-workspace-cpu/fdm-3d-v1-workspace/env.local.sh
R=/home/Pengfei.Ma@glasgow.ac.uk/fdm-3d-v1-workspace-cpu/fdm-3d-v1-workspace/runs/av_glamv_20261028
cd $R
run() { d=$1; shift; mkdir -p $d; nohup ./av_glamv --out $d --T 1.6 --checkpoint-every 1000 "$@" > $d/console.log 2>&1 & }
run tp_fixed
run tp_tether --tether-pins
run tp_tether_up --tether-pins --conv-upwind
wait
# animations (pyvista + matplotlib, ffmpeg next to the Python executable)
PY=/home/Pengfei.Ma@glasgow.ac.uk/miniconda3/envs/pyvista-mpm/bin/python
$PY animate_valve.py tp_fixed anim_tp_fixed --fps 10
$PY animate_streamlines.py tp_fixed anim_tp_fixed_streamlines --fps 10
