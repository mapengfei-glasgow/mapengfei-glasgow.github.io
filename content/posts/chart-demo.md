---
title: "chart shortcode demo"
description: "Scratch page used to check the chart shortcode; not published as a draft."
date: 2026-09-15
draft: true
academic: true
ShowToc: false
---

Line chart, two series, data written inline:

{{< chart height="260" xlabel="t (s)" ylabel="p (mmHg)" caption="Demo 1. Two series, line (default), legend on." >}}
t, inflow, outflow
0.00, 14.4, 85.0
0.05, 22.1, 85.1
0.10, 41.7, 85.0
0.15, 78.3, 84.8
0.20, 108.5, 84.6
0.25, 121.9, 84.9
0.30, 96.4, 86.0
0.35, 71.2, 88.5
0.40, 52.8, 90.1
0.45, 39.4, 89.2
0.50, 30.1, 87.4
0.55, 24.6, 86.2
0.60, 20.3, 85.5
0.65, 17.1, 85.1
0.70, 15.6, 84.9
{{< /chart >}}

Gaps (empty cells) and a single series with points:

{{< chart height="220" xlabel="step" ylabel="max |u|" caption="Demo 2. Empty cells become gaps; points are drawn when there are few samples." >}}
step, max |u|
0, 0.00
1, 0.12
2, 0.31
3,
4, 0.88
5, 1.02
6, 1.31
7, 1.44
{{< /chart >}}

Logarithmic y axis (divergence-like data), category x axis with bars:

{{< chart type="bar" height="220" xlabel="marker" ylabel="J&lt;0.8 cells" xkind="category" caption="Demo 3. Bar chart on a category axis." >}}
marker, cells
tube, 0
disk, 121
leaflets, 3756
wall, 3
{{< /chart >}}

{{< chart height="220" xlabel="t (s)" ylabel="L2 |div|" ylog="true" caption="Demo 4. Logarithmic y axis." >}}
t, |div|
0.00, 1e-6
0.10, 3.2e-5
0.20, 2.8e-4
0.30, 1.1e-2
0.40, 3.4e-2
0.50, 8.9e-3
0.60, 4.1e-4
0.70, 2.2e-5
{{< /chart >}}

{{< chart type="scatter" height="220" xlabel="Jmin" ylabel="count" caption="Demo 5. Scatter." >}}
Jmin, count
0.02, 12
0.08, 34
0.15, 91
0.22, 152
0.31, 88
0.44, 41
0.55, 9
{{< /chart >}}
