// /sim0d/ — closed-loop 0D circulation simulator.
// A port of ambit's `syspul` model (src/ambit_fe/flow0d/cardiovascular0D_syspul.py)
// with four 0D time-varying elastance chambers, pressure-dependent piecewise-linear
// valves ('pwlin_pres') and the one-step-theta time integrator of flow0d_main.py.
// Defaults are those of ambit's demos/flow0d/flow0d_heart_cycle.py (kg-mm-s units).
(function () {
  "use strict";
  function init() {
  var root = document.getElementById("s0");
  if (!root || root._s0Initialized) return;
  root._s0Initialized = true;

  var KPA_TO_MMHG = 7.500615758; // 1 kg/(mm s^2) = 1 kPa
  var MM3_TO_ML = 1e-3;

  // ---- Parameters (ambit names, kg-mm-s) --------------------------------------
  function demoParams() {
    var R_ar_sys = 120.0e-6, tau_ar_sys = 1.0311433159, tau_ar_pul = 0.3;
    var C_ar_sys = tau_ar_sys / R_ar_sys;
    var R_ar_pul = R_ar_sys / 8.0;
    var C_ar_pul = tau_ar_pul / R_ar_pul;
    return {
      T_cycl: 1.0, t_ed: 0.2, t_es: 0.53,
      E_v_max_l: 30.0e-5, E_v_min_l: 12.0e-6, E_v_max_r: 20.0e-5, E_v_min_r: 10.0e-6,
      E_at_max_l: 2.9e-5, E_at_min_l: 9.0e-6, E_at_max_r: 1.8e-5, E_at_min_r: 8.0e-6,
      R_ar_sys: R_ar_sys, C_ar_sys: C_ar_sys, Z_ar_sys: R_ar_sys / 20.0, L_ar_sys: 0.667e-6,
      R_ven_sys: R_ar_sys / 5.0, C_ven_sys: 30.0 * C_ar_sys, L_ven_sys: 0.0,
      R_ar_pul: R_ar_pul, C_ar_pul: C_ar_pul, L_ar_pul: 0.0,
      R_ven_pul: R_ar_pul, C_ven_pul: 2.5 * C_ar_pul, L_ven_pul: 0.0,
      R_vin_l_min: 1.0e-6, R_vin_l_max: 1.0e1, R_vout_l_min: 1.0e-6, R_vout_l_max: 1.0e1,
      R_vin_r_min: 1.0e-6, R_vin_r_max: 1.0e1, R_vout_r_min: 1.0e-6, R_vout_r_max: 1.0e1,
      V_at_l_u: 5e3, V_at_r_u: 4e3, V_v_l_u: 10e3, V_v_r_u: 8e3,
      V_ar_sys_u: 611e3, V_ar_pul_u: 123e3, V_ven_sys_u: 2596e3, V_ven_pul_u: 120e3,
      p_at_l_0: 0.599950804034, p_v_l_0: 0.599950804034, p_ar_sys_0: 9.68378038166,
      p_ven_sys_0: 2.13315841434, p_at_r_0: 0.0933256806275, p_v_r_0: 0.0933256806275,
      p_ar_pul_0: 3.22792679389, p_ven_pul_0: 1.59986881076,
      cycles: 10, steps: 100, theta: 0.5, eps_periodic: 0.05, initial_backwardeuler: true, stop_periodic: true
    };
  }

  var GROUPS = [
    { title: "Timing", open: true, keys: [
      ["T_cycl", "Cycle period T", "s"], ["t_ed", "End-diastolic time t_ed", "s"], ["t_es", "End-systolic time t_es", "s"]] },
    { title: "Ventricular elastance", open: true, keys: [
      ["E_v_max_l", "LV E_max", "kPa/mm³"], ["E_v_min_l", "LV E_min", "kPa/mm³"],
      ["E_v_max_r", "RV E_max", "kPa/mm³"], ["E_v_min_r", "RV E_min", "kPa/mm³"]] },
    { title: "Atrial elastance", keys: [
      ["E_at_max_l", "LA E_max", "kPa/mm³"], ["E_at_min_l", "LA E_min", "kPa/mm³"],
      ["E_at_max_r", "RA E_max", "kPa/mm³"], ["E_at_min_r", "RA E_min", "kPa/mm³"]] },
    { title: "Systemic circulation", open: true, keys: [
      ["R_ar_sys", "Arterial resistance R", "kPa·s/mm³"], ["C_ar_sys", "Arterial compliance C", "mm³/kPa"],
      ["Z_ar_sys", "Char. impedance Z", "kPa·s/mm³"], ["L_ar_sys", "Arterial inertance L", "kPa·s²/mm³"],
      ["R_ven_sys", "Venous resistance R", "kPa·s/mm³"], ["C_ven_sys", "Venous compliance C", "mm³/kPa"],
      ["L_ven_sys", "Venous inertance L", "kPa·s²/mm³"]] },
    { title: "Pulmonary circulation", keys: [
      ["R_ar_pul", "Arterial resistance R", "kPa·s/mm³"], ["C_ar_pul", "Arterial compliance C", "mm³/kPa"],
      ["L_ar_pul", "Arterial inertance L", "kPa·s²/mm³"],
      ["R_ven_pul", "Venous resistance R", "kPa·s/mm³"], ["C_ven_pul", "Venous compliance C", "mm³/kPa"],
      ["L_ven_pul", "Venous inertance L", "kPa·s²/mm³"]] },
    { title: "Valves (open / closed resistance)", keys: [
      ["R_vin_l_min", "Mitral R_min"], ["R_vin_l_max", "Mitral R_max"],
      ["R_vout_l_min", "Aortic R_min"], ["R_vout_l_max", "Aortic R_max"],
      ["R_vin_r_min", "Tricuspid R_min"], ["R_vin_r_max", "Tricuspid R_max"],
      ["R_vout_r_min", "Pulmonary R_min"], ["R_vout_r_max", "Pulmonary R_max"]] },
    { title: "Unstressed volumes", keys: [
      ["V_at_l_u", "LA", "mm³"], ["V_v_l_u", "LV", "mm³"], ["V_at_r_u", "RA", "mm³"], ["V_v_r_u", "RV", "mm³"],
      ["V_ar_sys_u", "Systemic arteries", "mm³"], ["V_ven_sys_u", "Systemic veins", "mm³"],
      ["V_ar_pul_u", "Pulmonary arteries", "mm³"], ["V_ven_pul_u", "Pulmonary veins", "mm³"]] },
    { title: "Initial pressures", keys: [
      ["p_at_l_0", "LA", "kPa"], ["p_v_l_0", "LV", "kPa"], ["p_ar_sys_0", "Systemic arteries", "kPa"],
      ["p_ven_sys_0", "Systemic veins", "kPa"], ["p_at_r_0", "RA", "kPa"], ["p_v_r_0", "RV", "kPa"],
      ["p_ar_pul_0", "Pulmonary arteries", "kPa"], ["p_ven_pul_0", "Pulmonary veins", "kPa"]] },
    { title: "Time integration", open: true, keys: [
      ["cycles", "Max. number of cycles"], ["steps", "Time steps per cycle"],
      ["theta", "θ (0.5 = trapezoidal)"], ["eps_periodic", "Periodicity tolerance"]],
      checks: [["initial_backwardeuler", "Backward Euler first step"], ["stop_periodic", "Stop when periodic"]] }
  ];

  var PRESETS = [
    { name: "Baseline (ambit flow0d demo)", mod: {} },
    { name: "Systolic heart failure (LV E_max × 0.4)", mod: { E_v_max_l: 0.4 } },
    { name: "Hypertension (R_ar_sys × 1.6, C_ar_sys × 0.6)", mod: { R_ar_sys: 1.6, C_ar_sys: 0.6 } },
    { name: "Aortic stenosis (aortic R_min × 400)", mod: { R_vout_l_min: 400 } },
    { name: "Mitral regurgitation (mitral R_max × 1e-6)", mod: { R_vin_l_max: 1e-6 } },
    { name: "Tachycardia (T = 0.6 s, scaled timings)", mod: { T_cycl: 0.6, t_ed: 0.6, t_es: 0.6 } }
  ];

  // ---- Model --------------------------------------------------------------------
  // Unknowns, in ambit's varmap order (vs = vp = 1).
  var NAMES = ["q_vin_l", "p_at_l", "q_vout_l", "p_v_l", "p_ar_sys", "q_arp_sys", "p_ard_sys", "q_ar_sys",
    "p_ven_sys", "q_ven_sys", "q_vin_r", "p_at_r", "q_vout_r", "p_v_r", "p_ar_pul", "q_ar_pul", "p_ven_pul", "q_ven_pul"];
  var N = NAMES.length;

  function makeModel(P) {
    var T = P.T_cycl;
    // demo time curves: tc1 (atria) and tc2 (ventricles)
    function act(t, t0, dur) {
      var tm = t % T;
      if (tm < 0) tm += T;
      return (tm >= t0 && tm <= t0 + dur) ? 0.5 * (1.0 - Math.cos(2.0 * Math.PI * (tm - t0) / dur)) : 0.0;
    }
    function elast(t) {
      var ya = act(t, 0.0, 2.0 * P.t_ed), yv = act(t, P.t_ed, 1.8 * (P.t_es - P.t_ed));
      return {
        v_l: (P.E_v_max_l - P.E_v_min_l) * yv + P.E_v_min_l,
        v_r: (P.E_v_max_r - P.E_v_min_r) * yv + P.E_v_min_r,
        at_l: (P.E_at_max_l - P.E_at_min_l) * ya + P.E_at_min_l,
        at_r: (P.E_at_max_r - P.E_at_min_r) * ya + P.E_at_min_r
      };
    }
    // 'pwlin_pres': q = (p - popen)/R, R = Rmax if p < popen else Rmin
    function valve(p, popen, Rmin, Rmax) { return (popen - p) / (p < popen ? Rmax : Rmin); }
    function ratio(L, R) { return R > 0 ? L / R : 0; }

    // df: the terms under d/dt (volumes and inertial terms)
    function df(x, t, out) {
      var E = elast(t);
      out[0] = x[1] / E.at_l + P.V_at_l_u;
      out[1] = 0; out[3] = 0; out[4] = 0; out[5] = 0; out[11] = 0; out[13] = 0;
      out[2] = x[3] / E.v_l + P.V_v_l_u;
      out[6] = P.C_ar_sys * x[6];
      out[7] = ratio(P.L_ar_sys, P.R_ar_sys) * x[7];
      out[8] = P.C_ven_sys * x[8];
      out[9] = ratio(P.L_ven_sys, P.R_ven_sys) * x[9];
      out[10] = x[11] / E.at_r + P.V_at_r_u;
      out[12] = x[13] / E.v_r + P.V_v_r_u;
      out[14] = P.C_ar_pul * x[14];
      out[15] = ratio(P.L_ar_pul, P.R_ar_pul) * x[15];
      out[16] = P.C_ven_pul * x[16];
      out[17] = ratio(P.L_ven_pul, P.R_ven_pul) * x[17];
    }
    // f: the algebraic / resistive part
    function f(x, out) {
      out[0] = -x[17] + x[0];                                              // LA flow balance
      out[1] = valve(x[1], x[3], P.R_vin_l_min, P.R_vin_l_max) + x[0];     // mitral valve
      out[2] = -x[0] + x[2];                                               // LV flow balance
      out[3] = valve(x[3], x[4], P.R_vout_l_min, P.R_vout_l_max) + x[2];   // aortic valve
      out[4] = -x[2] + x[5];                                               // aortic root flow balance
      out[5] = (x[6] - x[4]) / P.Z_ar_sys + x[5];                          // aortic root momentum
      out[6] = -x[5] + x[7];                                               // systemic arterial flow balance
      out[7] = (x[8] - x[6]) / P.R_ar_sys + x[7];                          // systemic arterial momentum
      out[8] = -x[7] + x[9];                                               // systemic venous flow balance
      out[9] = (x[11] - x[8]) / P.R_ven_sys + x[9];                        // systemic venous momentum
      out[10] = -x[9] + x[10];                                             // RA flow balance
      out[11] = valve(x[11], x[13], P.R_vin_r_min, P.R_vin_r_max) + x[10]; // tricuspid valve
      out[12] = -x[10] + x[12];                                            // RV flow balance
      out[13] = valve(x[13], x[14], P.R_vout_r_min, P.R_vout_r_max) + x[12]; // pulmonary valve
      out[14] = -x[12] + x[15];                                            // pulmonary arterial flow balance
      out[15] = (x[16] - x[14]) / P.R_ar_pul + x[15];                      // pulmonary arterial momentum
      out[16] = -x[15] + x[17];                                            // pulmonary venous flow balance
      out[17] = (x[1] - x[16]) / P.R_ven_pul + x[17];                      // pulmonary venous momentum
    }
    function volumes(x, t) {
      var E = elast(t);
      return {
        at_l: x[1] / E.at_l + P.V_at_l_u, v_l: x[3] / E.v_l + P.V_v_l_u,
        at_r: x[11] / E.at_r + P.V_at_r_u, v_r: x[13] / E.v_r + P.V_v_r_u,
        ar_sys: P.C_ar_sys * x[6] + P.V_ar_sys_u, ven_sys: P.C_ven_sys * x[8] + P.V_ven_sys_u,
        ar_pul: P.C_ar_pul * x[14] + P.V_ar_pul_u, ven_pul: P.C_ven_pul * x[16] + P.V_ven_pul_u
      };
    }
    return { df: df, f: f, volumes: volumes };
  }

  // Dense LU solve with partial pivoting (A is overwritten).
  function solve(A, b) {
    var n = b.length, i, j, k;
    for (k = 0; k < n; k++) {
      var piv = k, mx = Math.abs(A[k][k]);
      for (i = k + 1; i < n; i++) if (Math.abs(A[i][k]) > mx) { mx = Math.abs(A[i][k]); piv = i; }
      if (mx === 0) throw new Error("singular Jacobian");
      if (piv !== k) { var tr = A[k]; A[k] = A[piv]; A[piv] = tr; var tb = b[k]; b[k] = b[piv]; b[piv] = tb; }
      for (i = k + 1; i < n; i++) {
        var m = A[i][k] / A[k][k];
        if (m === 0) continue;
        for (j = k; j < n; j++) A[i][j] -= m * A[k][j];
        b[i] -= m * b[k];
      }
    }
    var x = new Array(n);
    for (i = n - 1; i >= 0; i--) {
      var s = b[i];
      for (j = i + 1; j < n; j++) s -= A[i][j] * x[j];
      x[i] = s / A[i][i];
    }
    return x;
  }

  function simulate(P) {
    var M = makeModel(P);
    var nstep = Math.round(P.steps), dt = P.T_cycl / nstep;
    var x = new Array(N).fill(0);
    x[1] = P.p_at_l_0; x[3] = P.p_v_l_0; x[4] = P.p_ar_sys_0; x[6] = P.p_ar_sys_0; x[8] = P.p_ven_sys_0;
    x[11] = P.p_at_r_0; x[13] = P.p_v_r_0; x[14] = P.p_ar_pul_0; x[16] = P.p_ven_pul_0;

    var dfo = new Array(N), fo = new Array(N), dfn = new Array(N), fn = new Array(N);
    var r0 = new Array(N), r1 = new Array(N);
    var t = 0, out = [], cycErr = [], periodicAt = 0, newtonFails = 0, maxIt = 0;
    var xTcOld = x.slice();

    function residual(xx, tn, th, r) {
      M.df(xx, tn, dfn); M.f(xx, fn);
      for (var i = 0; i < N; i++) r[i] = (dfn[i] - dfo[i]) / dt + th * fn[i] + (1 - th) * fo[i];
    }
    function record(xx, tt) {
      out.push({ t: tt, x: xx.slice(), V: M.volumes(xx, tt) });
    }
    record(x, 0);

    for (var c = 0; c < P.cycles; c++) {
      for (var s = 0; s < nstep; s++) {
        var tn = (c * nstep + s + 1) * dt;
        var th = (P.initial_backwardeuler && c === 0 && s === 0) ? 1.0 : P.theta;
        M.df(x, t, dfo); M.f(x, fo);
        var xn = x.slice(), it, ok = false;
        for (it = 0; it < 30; it++) {
          residual(xn, tn, th, r0);
          // Jacobian by forward differences: the residual is linear for a fixed valve state
          var J = [], i, j;
          for (i = 0; i < N; i++) J.push(new Array(N));
          for (j = 0; j < N; j++) {
            var h = 1e-7 * Math.max(1, Math.abs(xn[j])), keep = xn[j];
            xn[j] = keep + h;
            residual(xn, tn, th, r1);
            xn[j] = keep;
            for (i = 0; i < N; i++) J[i][j] = (r1[i] - r0[i]) / h;
          }
          var dx = solve(J, r0.map(function (v) { return -v; }));
          var nInc = 0, nX = 0;
          for (i = 0; i < N; i++) { xn[i] += dx[i]; nInc += dx[i] * dx[i]; nX += xn[i] * xn[i]; }
          if (Math.sqrt(nInc) <= 1e-8 * (1 + Math.sqrt(nX))) { ok = true; break; }
        }
        if (!ok) newtonFails++;
        if (it + 1 > maxIt) maxIt = it + 1;
        for (var k = 0; k < N; k++) if (!isFinite(xn[k])) throw new Error("solution diverged at t = " + tn.toFixed(3) + " s");
        x = xn; t = tn;
        record(x, t);
      }
      // ambit cycle_check: max_i |x_i - x_i,old| / max(1, |x_i,old|)
      var err = 0;
      for (var m = 0; m < N; m++) err = Math.max(err, Math.abs(x[m] - xTcOld[m]) / Math.max(1, Math.abs(xTcOld[m])));
      cycErr.push(err);
      xTcOld = x.slice();
      if (err <= P.eps_periodic && !periodicAt) {
        periodicAt = c + 1;
        if (P.stop_periodic) break;
      }
    }
    return { P: P, out: out, nstep: nstep, cycErr: cycErr, periodicAt: periodicAt,
      newtonFails: newtonFails, maxIt: maxIt, ncyc: cycErr.length };
  }

  // ---- Form ---------------------------------------------------------------------
  var form = document.getElementById("s0-form");
  var base = demoParams();
  var inputs = {};

  function fmt(v) {
    if (v === 0) return "0";
    var a = Math.abs(v);
    return (a >= 1e-3 && a < 1e5) ? String(+v.toPrecision(10)) : v.toExponential(9).replace(/\.?0+e/, "e");
  }

  GROUPS.forEach(function (g) {
    var d = document.createElement("details");
    if (g.open) d.open = true;
    var sm = document.createElement("summary");
    sm.textContent = g.title;
    d.appendChild(sm);
    g.keys.forEach(function (k) {
      var row = document.createElement("div");
      row.className = "s0-row";
      var id = "s0-p-" + k[0];
      var lab = document.createElement("label");
      lab.htmlFor = id;
      lab.innerHTML = k[1] + (k[2] ? " <span>[" + k[2] + "]</span>" : "") + "<br><code>" + k[0] + "</code>";
      var inp = document.createElement("input");
      inp.type = "number"; inp.step = "any"; inp.id = id; inp.name = k[0];
      inp.addEventListener("input", function () { markChanged(k[0]); });
      inputs[k[0]] = inp;
      row.appendChild(lab); row.appendChild(inp);
      d.appendChild(row);
    });
    (g.checks || []).forEach(function (k) {
      var lab = document.createElement("label");
      lab.className = "s0-check";
      var inp = document.createElement("input");
      inp.type = "checkbox"; inp.name = k[0];
      inputs[k[0]] = inp;
      lab.appendChild(inp); lab.appendChild(document.createTextNode(k[1]));
      d.appendChild(lab);
    });
    form.appendChild(d);
  });

  function markChanged(key) {
    var inp = inputs[key];
    if (inp.type !== "number") return;
    var v = parseFloat(inp.value), b = base[key];
    // the field shows 10 significant digits, so compare relative to that
    inp.classList.toggle("s0-changed", !(Math.abs(v - b) <= 1e-9 * Math.max(Math.abs(b), 1e-300)));
  }
  function setForm(P) {
    Object.keys(inputs).forEach(function (k) {
      if (inputs[k].type === "checkbox") inputs[k].checked = !!P[k];
      else { inputs[k].value = fmt(P[k]); markChanged(k); }
    });
  }
  function readForm() {
    var P = {}, bad = [];
    Object.keys(inputs).forEach(function (k) {
      if (inputs[k].type === "checkbox") { P[k] = inputs[k].checked; return; }
      var v = parseFloat(inputs[k].value);
      if (!isFinite(v)) bad.push(k);
      P[k] = v;
    });
    if (bad.length) throw new Error("invalid value for " + bad.join(", "));
    if (!(P.T_cycl > 0)) throw new Error("T_cycl must be positive");
    if (!(P.t_es > P.t_ed && P.t_ed > 0)) throw new Error("need 0 < t_ed < t_es");
    if (!(P.steps >= 10)) throw new Error("use at least 10 steps per cycle");
    if (!(P.cycles >= 1 && P.cycles <= 200)) throw new Error("cycles must be between 1 and 200");
    if (!(P.theta > 0 && P.theta <= 1)) throw new Error("θ must be in (0, 1]");
    ["R_ar_sys", "R_ven_sys", "R_ar_pul", "R_ven_pul", "Z_ar_sys"].forEach(function (k) {
      if (!(P[k] > 0)) throw new Error(k + " must be positive");
    });
    return P;
  }

  var presetSel = document.getElementById("s0-preset");
  PRESETS.forEach(function (p, i) {
    var o = document.createElement("option");
    o.value = i; o.textContent = p.name;
    presetSel.appendChild(o);
  });
  function applyPreset(i) {
    var P = demoParams(), mod = PRESETS[i].mod;
    Object.keys(mod).forEach(function (k) { P[k] *= mod[k]; });
    setForm(P);
  }
  presetSel.addEventListener("change", function () { applyPreset(+presetSel.value); });
  document.getElementById("s0-reset").addEventListener("click", function () {
    presetSel.value = 0; applyPreset(0);
  });
  setForm(base);

  // ---- Results ------------------------------------------------------------------
  var statusEl = document.getElementById("s0-status");
  var kpiEl = document.getElementById("s0-kpis");
  var csvBtn = document.getElementById("s0-csv");
  var runBtn = document.getElementById("s0-run");
  var last = null, charts = {};

  function css(name, fb) {
    var v = getComputedStyle(document.body).getPropertyValue(name).trim();
    return v || fb;
  }
  var COL = { lv: "#e2445c", ao: "#579bfc", la: "#fdab3d", rv: "#a25ddc", pa: "#00c875", ra: "#ff8a5c", vs: "#8a8f98" };

  function slice(res, scope) {
    if (scope === "all") return res.out;
    var n = res.out.length;
    return res.out.slice(Math.max(0, n - 1 - res.nstep));
  }

  function lineChart(id, xlabel, ylabel, datasets, opts) {
    opts = opts || {};
    var fg = css("--secondary", "#888"), grid = css("--border", "#ddd");
    var cfg = {
      // loops (p-V) go through a scatter chart: a line chart assumes x is monotone
      type: opts.nearest ? "scatter" : "line",
      data: { datasets: datasets },
      options: {
        responsive: true, maintainAspectRatio: false, animation: false,
        // parsing: false makes Chart.js treat the data as sorted in x, which the
        // p-V loops are not; time series keep the fast path
        parsing: !!opts.nearest, normalized: !opts.nearest,
        interaction: { mode: opts.nearest ? "nearest" : "index", intersect: false },
        elements: { point: { radius: 0 }, line: { borderWidth: 1.6 } },
        datasets: { scatter: { showLine: true } },
        plugins: {
          legend: { labels: { color: fg, boxWidth: 12, font: { size: 11 } } },
          tooltip: { callbacks: { label: function (c) { return c.dataset.label + ": " + c.parsed.y.toPrecision(4); } } }
        },
        scales: {
          x: { type: "linear", title: { display: true, text: xlabel, color: fg }, ticks: { color: fg }, grid: { color: grid } },
          y: { type: opts.ylog ? "logarithmic" : "linear", title: { display: true, text: ylabel, color: fg },
            ticks: { color: fg }, grid: { color: grid } }
        }
      }
    };
    if (charts[id]) charts[id].destroy();
    charts[id] = new Chart(document.getElementById(id), cfg);
  }
  function ds(label, color, pts, extra) {
    var d = { label: label, data: pts, borderColor: color, backgroundColor: color };
    if (extra) Object.keys(extra).forEach(function (k) { d[k] = extra[k]; });
    return d;
  }

  function draw() {
    if (!last || typeof Chart === "undefined") return;
    var scope = root.querySelector('input[name="s0-scope"]:checked').value;
    var rows = slice(last, scope);
    var P = last.P;
    var t0 = scope === "last" ? rows[0].t : 0;
    function series(fn) { return rows.map(function (r) { return { x: r.t - t0, y: fn(r) }; }); }
    function p(i) { return function (r) { return r.x[i] * KPA_TO_MMHG; }; }
    var xl = scope === "last" ? "t in last cycle (s)" : "t (s)";

    lineChart("s0-c-pl", xl, "p (mmHg)", [
      ds("LV", COL.lv, series(p(3))), ds("Aorta", COL.ao, series(p(4))),
      ds("LA", COL.la, series(p(1))), ds("Syst. veins", COL.vs, series(p(8)), { borderDash: [4, 3] })]);
    lineChart("s0-c-pr", xl, "p (mmHg)", [
      ds("RV", COL.rv, series(p(13))), ds("Pulm. artery", COL.pa, series(p(14))),
      ds("RA", COL.ra, series(p(11))), ds("Pulm. veins", COL.vs, series(p(16)), { borderDash: [4, 3] })]);
    lineChart("s0-c-v", xl, "V (mL)", [
      ds("LV", COL.lv, series(function (r) { return r.V.v_l * MM3_TO_ML; })),
      ds("RV", COL.rv, series(function (r) { return r.V.v_r * MM3_TO_ML; })),
      ds("LA", COL.la, series(function (r) { return r.V.at_l * MM3_TO_ML; })),
      ds("RA", COL.ra, series(function (r) { return r.V.at_r * MM3_TO_ML; }))]);
    lineChart("s0-c-q", xl, "q (mL/s)", [
      ds("Mitral", COL.la, series(function (r) { return r.x[0] * MM3_TO_ML; })),
      ds("Aortic", COL.ao, series(function (r) { return r.x[2] * MM3_TO_ML; })),
      ds("Tricuspid", COL.ra, series(function (r) { return r.x[10] * MM3_TO_ML; })),
      ds("Pulmonary", COL.pa, series(function (r) { return r.x[12] * MM3_TO_ML; }))]);
    lineChart("s0-c-pv", "V (mL)", "p (mmHg)", [
      ds("LV", COL.lv, rows.map(function (r) { return { x: r.V.v_l * MM3_TO_ML, y: r.x[3] * KPA_TO_MMHG }; })),
      ds("RV", COL.rv, rows.map(function (r) { return { x: r.V.v_r * MM3_TO_ML, y: r.x[13] * KPA_TO_MMHG }; }))],
      { nearest: true });
    lineChart("s0-c-per", "cycle", "error", [
      ds("max |Δx| / max(1,|x|)", COL.ao, last.cycErr.map(function (e, i) { return { x: i + 1, y: Math.max(e, 1e-12) }; }),
        { pointRadius: 3 }),
      ds("tolerance", COL.vs, [{ x: 1, y: P.eps_periodic }, { x: Math.max(2, last.ncyc), y: P.eps_periodic }],
        { borderDash: [4, 3] })], { ylog: true, nearest: true });
  }

  function kpis(res) {
    var rows = slice(res, "last"), P = res.P;
    function ext(fn) {
      var lo = Infinity, hi = -Infinity, sum = 0;
      rows.forEach(function (r, i) { var v = fn(r); lo = Math.min(lo, v); hi = Math.max(hi, v); if (i) sum += v; });
      return { min: lo, max: hi, mean: sum / (rows.length - 1) };
    }
    var vl = ext(function (r) { return r.V.v_l * MM3_TO_ML; });
    var vr = ext(function (r) { return r.V.v_r * MM3_TO_ML; });
    var pao = ext(function (r) { return r.x[4] * KPA_TO_MMHG; });
    var plv = ext(function (r) { return r.x[3] * KPA_TO_MMHG; });
    var ppa = ext(function (r) { return r.x[14] * KPA_TO_MMHG; });
    var pla = ext(function (r) { return r.x[1] * KPA_TO_MMHG; });
    var sv = vl.max - vl.min, hr = 60 / P.T_cycl;
    function total(r) { var V = r.V, s = 0; Object.keys(V).forEach(function (k) { s += V[k]; }); return s; }
    var drift = Math.abs(total(res.out[res.out.length - 1]) - total(res.out[0])) / total(res.out[0]);
    var items = [
      ["LV EDV", vl.max.toFixed(1), "mL"], ["LV ESV", vl.min.toFixed(1), "mL"],
      ["LV SV", sv.toFixed(1), "mL"], ["LV EF", (100 * sv / vl.max).toFixed(1), "%"],
      ["Cardiac output", (sv * hr / 1000).toFixed(2), "L/min"], ["Heart rate", hr.toFixed(0), "bpm"],
      ["Aortic pressure", pao.max.toFixed(0) + "/" + pao.min.toFixed(0), "mmHg"], ["Mean aortic", pao.mean.toFixed(1), "mmHg"],
      ["LV peak p", plv.max.toFixed(1), "mmHg"], ["Mean LA p", pla.mean.toFixed(1), "mmHg"],
      ["Pulm. artery", ppa.max.toFixed(0) + "/" + ppa.min.toFixed(0), "mmHg"], ["RV SV", (vr.max - vr.min).toFixed(1), "mL"],
      ["Volume drift", drift.toExponential(1), ""]
    ];
    kpiEl.innerHTML = items.map(function (it) {
      return "<div><dt>" + it[0] + "</dt><dd>" + it[1] + (it[2] ? "<small>" + it[2] + "</small>" : "") + "</dd></div>";
    }).join("");
  }

  function run() {
    var P;
    statusEl.classList.remove("err");
    try { P = readForm(); } catch (e) { statusEl.textContent = e.message; statusEl.classList.add("err"); return; }
    runBtn.disabled = true;
    statusEl.textContent = "Running…";
    setTimeout(function () {
      try {
        var t0 = performance.now();
        var res = simulate(P);
        var ms = performance.now() - t0;
        last = res;
        kpis(res);
        draw();
        csvBtn.disabled = false;
        var msg = res.ncyc + " cycle" + (res.ncyc > 1 ? "s" : "") + ", " + (res.out.length - 1) + " steps in " + ms.toFixed(0) + " ms. ";
        msg += res.periodicAt ? "Periodic state reached after cycle " + res.periodicAt + " (error " +
          res.cycErr[res.periodicAt - 1].toExponential(2) + " ≤ " + P.eps_periodic + ")."
          : "Not periodic yet (last error " + res.cycErr[res.ncyc - 1].toExponential(2) + ").";
        if (res.newtonFails) msg += " Newton did not converge in " + res.newtonFails + " step(s).";
        statusEl.textContent = msg;
      } catch (e) {
        statusEl.textContent = "Simulation failed: " + e.message;
        statusEl.classList.add("err");
      }
      runBtn.disabled = false;
    }, 20);
  }

  function exportCsv() {
    if (!last) return;
    var head = ["t_s"].concat(NAMES, ["V_at_l", "V_v_l", "V_at_r", "V_v_r", "V_ar_sys", "V_ven_sys", "V_ar_pul", "V_ven_pul"]);
    var lines = ["# ambit syspul 0D model, kg-mm-s units (p in kPa, q in mm^3/s, V in mm^3)", head.join(",")];
    last.out.forEach(function (r) {
      var V = r.V;
      lines.push([r.t.toFixed(6)].concat(r.x.map(function (v) { return v.toPrecision(10); }),
        [V.at_l, V.v_l, V.at_r, V.v_r, V.ar_sys, V.ven_sys, V.ar_pul, V.ven_pul].map(function (v) { return v.toPrecision(10); })).join(","));
    });
    var blob = new Blob([lines.join("\n") + "\n"], { type: "text/csv" });
    var a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "flow0d_syspul_results.csv";
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(function () { URL.revokeObjectURL(a.href); }, 1000);
  }

  runBtn.addEventListener("click", run);
  csvBtn.addEventListener("click", exportCsv);
  root.querySelectorAll('input[name="s0-scope"]').forEach(function (r) { r.addEventListener("change", draw); });
  form.addEventListener("submit", function (e) { e.preventDefault(); run(); });

  // Run the baseline once Chart.js (deferred, loaded before this file) is available.
  // On a Turbo visit the head script may still be loading, so poll briefly.
  (function waitChart(n) {
    if (typeof Chart !== "undefined") run();
    else if (n > 0) setTimeout(function () { waitChart(n - 1); }, 50);
    else run();
  })(100);
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init, { once: true });
  else init();
  document.addEventListener("turbo:load", init);
})();
