"""Generate Chart.js shortcode blocks for the demo_424 page.

Reads the canonical demo_424 run outputs from the afsi repository:

  plot/<case>_NY<n>/flow_history.csv   time histories (every 100 steps)
  plot/<case>_NY<n>/verify.json        final metric set
  plot/open_NY<n>/velocity.xdmf        lumen profile at mid-length
  plot/closed_NY<n>/pressure.xdmf      centreline pressure through the membrane

and prints Hugo `chart` shortcode blocks (CSV data inline) which can be pasted
into content/afsi/demo-424.md.  With ``inject:demo-424.md`` the blocks replace
``<!-- chart:424-* -->`` markers in the page.

Usage:
    python tools/make_afsi_demo424_charts.py                 # all blocks
    python tools/make_afsi_demo424_charts.py 424-maxu        # one block
    python tools/make_afsi_demo424_charts.py inject:demo-424.md
"""
import csv
import io
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import h5py
import numpy as np

AFSI = Path("/Users/pengfei/GitHub/afsi/afsic/demo/demo_424/plot")
SITE = Path(__file__).resolve().parents[1]

MU = 0.0035                                   # fluid viscosity
Y_C, A_LUMEN = 0.0225, 0.015                  # lumen centreline, half-height
X_OFF = {"45": 0.0005, "90": 0.00025}         # aorta start offset (= H/2)
DP = {"open": 0.02 * 133.322387415, "closed": 0.2 * 133.322387415}   # Pa


def capture(fn):
    buf = io.StringIO()
    old = sys.stdout
    sys.stdout = buf
    try:
        fn()
    finally:
        sys.stdout = old
    return buf.getvalue().strip()


def subsample(n, target=33):
    if n <= target:
        return np.arange(n)
    return np.unique(np.r_[np.arange(0, n, max(1, n // (target - 1))), n - 1])


def flow(run):
    with open(AFSI / run / "flow_history.csv") as fh:
        rows = list(csv.DictReader(fh))
    cols = ("t", "Q_gap", "Q_leak_up", "Q_leak_dn", "max_u")
    return {c: np.array([float(r[c]) for r in rows]) for c in cols}


def verify(run):
    return json.loads((AFSI / run / "verify.json").read_text())


# ---------------------------------------------------------------------------
# XDMF sampling (structured grid -> bilinear interpolation)
# ---------------------------------------------------------------------------
def read_field(path: Path, names):
    root = ET.parse(path).getroot()
    att = None
    for grid in root.iter("Grid"):
        a = grid.find("Attribute")
        if a is not None and a.get("Name") in names:
            att = a
    if att is None:
        raise SystemExit(f"no attribute {names} in {path}")
    h5ref, _, dset = att.find("DataItem").text.strip().partition(":")
    with h5py.File(path.parent / h5ref, "r") as f:
        vals = np.asarray(f[dset], dtype=float)
        pts = np.asarray(f["/Mesh/mesh/geometry"], dtype=float)[:, :2]
    return pts, vals


def to_lattice(pts, vals):
    xs = np.unique(np.round(pts[:, 0], 10))
    ys = np.unique(np.round(pts[:, 1], 10))
    ix = np.searchsorted(xs, np.round(pts[:, 0], 10))
    iy = np.searchsorted(ys, np.round(pts[:, 1], 10))
    out = np.full((ys.size, xs.size) + vals.shape[1:], np.nan)
    out[iy, ix] = vals
    return xs, ys, out


def bilinear(A, xs, ys, xq, yq):
    xq = np.asarray(xq, float)
    yq = np.asarray(yq, float)
    xi = np.clip(np.searchsorted(xs, xq) - 1, 0, len(xs) - 2)
    yi = np.clip(np.searchsorted(ys, yq) - 1, 0, len(ys) - 2)
    tx = (xq - xs[xi]) / (xs[xi + 1] - xs[xi])
    ty = (yq - ys[yi]) / (ys[yi + 1] - ys[yi])
    if A.ndim > 2:
        tx, ty = tx[:, None], ty[:, None]
    a, b = A[yi, xi], A[yi, xi + 1]
    c, d = A[yi + 1, xi], A[yi + 1, xi + 1]
    return (a * (1 - tx) + b * tx) * (1 - ty) + (c * (1 - tx) + d * tx) * ty


# ---------------------------------------------------------------------------
# Charts
# ---------------------------------------------------------------------------
def chart_424_profile():
    """Lumen profile at mid-length, both resolutions + analytic Poiseuille."""
    ux = {}
    yq = np.linspace(Y_C - A_LUMEN, Y_C + A_LUMEN, 121)
    for n in ("45", "90"):
        pts, vel = read_field(AFSI / f"open_NY{n}" / "velocity.xdmf",
                              ("f", "u_", "u"))
        vel = np.asarray(vel)[:, :2]     # dolfinx pads the 2-D vector to 3 comps
        xs, ys, U = to_lattice(pts, vel)
        xm = X_OFF[n] + 0.05
        ux[n] = bilinear(U, xs, ys, np.full_like(yq, xm), yq)[:, 0]
    g90 = DP["open"] / (DP["open"] / verify("open_NY90")["G_ideal"])
    uan = g90 / (2 * MU) * (A_LUMEN**2 - (yq - Y_C) ** 2)
    print('{{< chart xlabel="y (mm)" ylabel="u_x (m/s)" '
          'caption="Figure 4. Lumen velocity profile at mid-length: the two '
          'resolutions against the analytical Poiseuille parabola." >}}')
    print("y (mm), NY=45, NY=90, analytic Poiseuille")
    for k in subsample(len(yq), 31):
        print(f"{yq[k]*1000:.2f},{ux['45'][k]:.5f},{ux['90'][k]:.5f},"
              f"{uan[k]:.5f}")
    print("{{< /chart >}}")


def chart_424_jump():
    """Centreline pressure through the membrane, both resolutions."""
    p = {}
    for n in ("45", "90"):
        pts, pre = read_field(AFSI / f"closed_NY{n}" / "pressure.xdmf",
                              ("p_", "p"))
        xs, ys, P = to_lattice(pts, np.asarray(pre).ravel())
        xq = np.linspace(X_OFF[n] + 0.030, X_OFF[n] + 0.070, 81)
        p[n] = (xq - X_OFF[n],
                bilinear(P, xs, ys, xq, np.full_like(xq, Y_C)),
                bilinear(P, xs, ys, xq, np.full_like(xq, 0.00275)))
    print('{{< chart xlabel="x (mm)" ylabel="p (Pa)" '
          'caption="Figure 8. Pressure along the lumen centre through the '
          'membrane (left chamber → jump → right chamber), with the outer '
          'gap centre as the smooth reference." >}}')
    print("x (mm), lumen centre NY=45, lumen centre NY=90, outer gap NY=90")
    for k in subsample(81, 33):
        print(f"{p['45'][0][k]*1000:.2f},{p['45'][1][k]:.4f},"
              f"{p['90'][1][k]:.4f},{p['90'][2][k]:.4f}")
    print("{{< /chart >}}")


def chart_424_maxu():
    """max |u| histories, both cases and both resolutions."""
    d = {(c, n): flow(f"{c}_NY{n}")
         for c in ("open", "closed") for n in ("45", "90")}
    t = d[("open", "45")]["t"]
    print('{{< chart xlabel="t (s)" ylabel="max |u| (m/s)" '
          'caption="Figure 9. Peak fluid speed against time. The patent case '
          'converges monotonically; the occluded case keeps swinging by about '
          'a fifth of its peak because nothing dissipates the driving '
          'pressure." >}}')
    print("t, open NY=45, open NY=90, closed NY=45, closed NY=90")
    for k in range(len(t)):
        row = [f"{t[k]:.2f}"]
        for c in ("open", "closed"):
            for n in ("45", "90"):
                row.append(f"{d[(c, n)]['max_u'][k]:.4f}")
        print(",".join(row))
    print("{{< /chart >}}")


def chart_424_qhist():
    """Closed case: gap flow and wall leakage histories (log scale)."""
    d = {n: flow(f"closed_NY{n}") for n in ("45", "90")}
    t = d["45"]["t"]
    print('{{< chart xlabel="t (s)" ylabel="|Q| (m²/s)" ylog="true" '
          'caption="Figure 10. Closed case: bypass flow in the outer gaps '
          'against the leakage through the downstream half of the wall, both '
          'resolutions. The gap flux rises while the leakage falls; neither '
          'has settled at t = 0.4 s." >}}')
    print("t, |Q_gap| NY=45, |Q_leak| NY=45, |Q_gap| NY=90, |Q_leak| NY=90")
    for k in range(len(t)):
        print(f"{t[k]:.2f},{abs(d['45']['Q_gap'][k]):.5g},"
              f"{abs(d['45']['Q_leak_up'][k]):.5g},"
              f"{abs(d['90']['Q_gap'][k]):.5g},"
              f"{abs(d['90']['Q_leak_up'][k]):.5g}")
    print("{{< /chart >}}")


def chart_424_conv_open():
    """Open case: three error measures against the grid size (log-log)."""
    v = {n: verify(f"open_NY{n}") for n in ("45", "90")}
    hs = (1.0, 0.5)
    series = (
        [abs(v[n]["u_max_rel_err"]) for n in ("45", "90")],
        [abs(1 - v[n]["Q_lumen_x0.5"] / v[n]["Q_lumen_analytic"])
         for n in ("45", "90")],
        [v[n]["u_relL2_x0.5"] for n in ("45", "90")],
    )
    print('{{< chart xlog="true" ylog="true" xlabel="h (mm)" '
          'ylabel="relative error" caption="Figure 12. Patent case: the '
          'error measures fall at first order in the grid size, while the '
          'pressure gradient stays flat." >}}')
    print("h (mm), |u_max| error, |Q_lumen| error, profile rel. L2")
    for k in range(2):
        print(f"{hs[k]},{series[0][k]:.5g},{series[1][k]:.5g},"
              f"{series[2][k]:.5g}")
    print("{{< /chart >}}")


def chart_424_conv_closed():
    """Closed case: four normalised error measures against h (log-log)."""
    v = {n: verify(f"closed_NY{n}") for n in ("45", "90")}
    dp = DP["closed"]
    hs = (1.0, 0.5)
    series = (
        [abs(1 - v[n]["p_jump"] / dp) for n in ("45", "90")],
        [v[n]["p_std_upstream"] / dp for n in ("45", "90")],
        [v[n]["p_std_downstream"] / dp for n in ("45", "90")],
        [v[n]["Q_leak_4h upstream"] / v[n]["Q_gap_analytic"]
         for n in ("45", "90")],
    )
    print('{{< chart xlog="true" ylog="true" xlabel="h (mm)" '
          'ylabel="normalised error" caption="Figure 13. Occluded case: four '
          'dimensionless error measures against the grid size. The held '
          'pressure converges at second order; the wall leakage is the slow '
          'quantity." >}}')
    print("h (mm), |1 - held fraction|, p-std upstream / dp, "
          "p-std downstream / dp, leak / Q_gap analytic")
    for k in range(2):
        print(f"{hs[k]}," + ",".join(f"{s[k]:.5g}" for s in series))
    print("{{< /chart >}}")


BLOCKS = (
    ("424-profile", chart_424_profile),
    ("424-jump", chart_424_jump),
    ("424-maxu", chart_424_maxu),
    ("424-qhist", chart_424_qhist),
    ("424-conv-open", chart_424_conv_open),
    ("424-conv-closed", chart_424_conv_closed),
)


def inject(page):
    path = SITE / "content/afsi" / page
    text = path.read_text()
    for key, fn in BLOCKS:
        marker = f"<!-- chart:{key} -->"
        if marker in text:
            text = text.replace(marker, capture(fn))
    path.write_text(text)
    print("injected", path)


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    if which.startswith("inject:"):
        inject(which.split(":", 1)[1])
    else:
        for key, fn in BLOCKS:
            if which in ("all", key):
                fn()
