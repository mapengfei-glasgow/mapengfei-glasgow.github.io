---
title: "Nodal Immersed Boundary Finite Element Method"
description: "Formulation notes for the nodal immersed boundary–finite element method."
date: 2026-10-01
weight: -1
academic: true
reference: "Wells et al. (2023)"
status: WIP
---

The method used in AFSI is basically developed from 
{{< cite "wells2023nodal" "author" >}}, some modifications are necessary for the use of background solver to be a Finite Element method, for the conservation of energy, which will be kept by using dual interpolation and spreading operators.