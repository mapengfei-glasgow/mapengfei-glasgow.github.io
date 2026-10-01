"""Generate Chart.js shortcode blocks for the AFSI demo pages (441/442/443).

Reads the run outputs from the afsi repository and prints Hugo `chart`
shortcode blocks (subsampled CSV) that can be pasted into content/afsi/demo-*.md.

Usage:
    python tools/make_afsi_demo_charts.py 441-time
    python tools/make_afsi_demo_charts.py 442-area
    ...
"""
import io
import re
import sys
from pathlib import Path

import numpy as np

AFSI = Path("/Users/pengfei/GitHub/afsi/afsic/demo")
SITE = Path(__file__).resolve().parents[1]


def capture(fn):
    buf = io.StringIO()
    old = sys.stdout
    sys.stdout = buf
    try:
        fn()
    finally:
        sys.stdout = old
    return buf.getvalue().strip()


def inject(page):
    path = SITE / "content/afsi" / page
    text = path.read_text()
    for key, fn in (("441-time", chart_441_time),
                    ("442-area", chart_442_area),
                    ("443-time", chart_443_time)):
        marker = f"<!-- chart:{key} -->"
        if marker in text:
            text = text.replace(marker, capture(fn))
    path.write_text(text)
    print("injected", path)


def load_csv(path, cols):
    data = np.genfromtxt(path, delimiter=",", names=True)
    return {c: data[c] for c in cols}


def subsample(n, target=28):
    if n <= target:
        return np.arange(n)
    return np.unique(np.r_[np.arange(0, n, max(1, n // (target - 1))), n - 1])


def rows_lines(xs, yss, fmt="{:.6g}"):
    k = subsample(len(xs))
    out = [",".join([""] + [fmt.format(0.0)] * len(yss)) * 0]  # placeholder
    out = [",".join([f"{x:.4g}"] + [f"{y[k]:.6g}" for y in yss]) for k, x in
           [(k, xs[k]) for k in k]]
    return out


def chart_441_time():
    d8 = load_csv(AFSI / "demo_441/plot/metrics_fx_slowM8.csv",
                  ["t", "corner_dY"])
    d16 = load_csv(AFSI / "demo_441/plot/metrics_fx_slowM16.csv",
                   ["t", "corner_dY"])
    # common time grid: sample both on their own steps, 28 rows each side
    k8 = subsample(len(d8["t"]), 24)
    k16 = subsample(len(d16["t"]), 24)
    lines = ["t, M=8 (N=13), M=16 (N=25), paper plateau (0.60-0.68, mid)"]
    tset = sorted(set(np.round(np.r_[d8["t"][k8], d16["t"][k16]], 4)))
    y8 = np.interp(tset, d8["t"], d8["corner_dY"])
    y16 = np.interp(tset, d16["t"], d16["corner_dY"])
    for t, a, b in zip(tset, y8, y16):
        lines.append(f"{t:.4g},{a:.4f},{b:.4f},0.6400")
    print("{{< chart xlabel=\"t (s)\" ylabel=\"$\\\\Delta Y$ (cm)\" "
          "caption=\"Corner displacement history, paper protocol "
          "(TL=20 s, TF=50 s).\" >}}")
    print("\n".join(lines))
    print("{{< /chart >}}")


def chart_442_area():
    d = load_csv(AFSI / "demo_442/plot/metrics_paper.csv", ["t", "dA_rel"])
    k = subsample(len(d["t"]), 30)
    print("{{< chart type=\"line\" xlabel=\"t\" ylabel=\"$\\\\Delta A/A_0$\" "
          "caption=\"Relative area change, N=128, MFAC=0.5.\" >}}")
    print("t, |A-A0|/A0")
    for i in k:
        print(f"{d['t'][i]:.5g},{d['dA_rel'][i]:.6g}")
    print("{{< /chart >}}")


def chart_443_time():
    p8 = AFSI / "demo_443/plot/metrics_kap10longm8.csv"
    if not p8.exists():
        p8 = AFSI / "demo_443/plot/metrics_tfix.csv"
    d8 = load_csv(p8, ["t", "top_dY"])
    tset = d8["t"][subsample(len(d8["t"]), 30)]
    y8 = np.interp(tset, d8["t"], d8["top_dY"])
    print("{{< chart xlabel=\"t (s)\" ylabel=\"$\\Delta Y$ (cm)\" "
          "caption=\"Top-centre displacement, M=8, N=32, calibrated bulk "
          "(KAPPA_MULT=10), against the reference plateau -4.03..-4.09 cm.\" >}}")
    print("t, M=8 (N=32, 10K), reference plateau (-4.05)")
    for t, a in zip(tset, y8):
        print(f"{t:.4g},{a:.4f},-4.0500")
    print("{{< /chart >}}")


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    if which.startswith("inject:"):
        inject(which.split(":", 1)[1])
    else:
        if which in ("all", "441-time"):
            chart_441_time()
        if which in ("all", "442-area"):
            chart_442_area()
        if which in ("all", "443-time"):
            chart_443_time()
