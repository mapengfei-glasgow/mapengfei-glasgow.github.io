---
title: "Passive rim + gap mask"
description: "Keeping the fluid outside the immersed mitral-valve tube at rest."
date: 2026-10-14
layout: protected-paper
academic: true
comments: false
searchHidden: true
build:
  list: never
tags: ["Cardiac Simulation", "MV", "GPU", "FSI"]
url: /posts/mv-passive-rim-gap-mask/
---

Companion note to [the mitral-valve FSI working paper]({{< relref "mv-paper.md" >}}).
Section and figure numbers below refer to that paper.

## Why both measures are needed

The tube is immersed in a box ($8.6 \times 8.6$ cm cross-section), so there is a gap of fluid between the outer
tube wall ($r \approx 3.73$ cm) and the domain boundary. Nothing in the original model stops flow in that gap: with the
inlet/outlet pressure prescribed only on the lumen disc, the gap is a bypass around the valve, and the
transvalvular pressure difference also loads the part of the housing disc that sticks out beyond the tube
(inlet pressure below it, outlet pressure above it), which tore the disc rim in early runs (glamv-0.0.1). Two measures,
both absent in IBAMR, hold the gap fluid at rest:

## Gap mask

**Gap mask** (Eulerian Brinkman damping, `--gap-mask 3.6 --gap-ramp 0.13 --gap-iters -1`). A radial indicator
   $\chi(r)$ is 0 for $r \le 3.6$ cm, rises linearly to 1 at $r = 3.73$ cm (inside the tube wall) and stays 1 out to the
   domain boundary, over the full height. Every velocity face with $\chi > 0$ is damped implicitly,
   $\mathbf u \leftarrow \mathbf u / (1 + \Delta t\,\kappa\chi)$ with $\kappa\Delta t = 1000$, before the pressure projection.
   Incompressibility then forces the net flux through the wall to (almost) zero. The lumen ($r < 3.5$ cm) is untouched.
## Passive rim

**Passive rim** (`--passive-rim 3.73`). The 1,658 housing-disc cells whose reference centroid lies at $r > 3.73$ cm are made
   force-free ($J_e = 0$ ⇒ no PK1, tether, viscous or volumetric force; spreading and interpolation stay dual), so they only
   follow the (static) gap fluid and no longer carry the transvalvular load.

## Measured effect

Measured effect on the coarsest pair ({{< label "mesh" "R0/P1+Q1 @ G-64" >}}, run ~~{{< label "run" "G11" >}}~~, all 35 frames over 1.335 s): flux through the
gap $r > 3.8$ cm at most **0.013 cm³/s** (peak lumen flux 615 cm³/s, i.e. $2 \times 10^{-5}$), and $\max\lvert\mathbf u\rvert$ in the layer
just outside the wall ($3.73 < r < 4.3$ cm) at most **0.074 cm/s**; the lumen flux differs between $z = 3$, 5.5, 9 and 12 cm by
at most 0.36 % of its peak ([Table 13]({{< relref "mv-paper.md" >}}#table-13)). The same holds for every passive-rim run ([Figure 3]({{< relref "mv-paper.md" >}}#figure-3)).

## Reproduction instructions

See [Data and code]({{< relref "mv-data-and-code.md" >}}) for the run commands and data locations.
