/* charts.js — draw the figures emitted by layouts/_shortcodes/chart.html.
 *
 * The shortcode ships its data as a JSON array of rows (first row = header)
 * inside <script type="application/json" class="chart-data">, so this file only
 * has to turn rows into Chart.js datasets.  It is loaded (with chart.umd.min.js
 * and css/charts.css) only on pages that use the shortcode.
 *
 * Colours follow the PaperMod theme variables and every chart is rebuilt when
 * the light/dark toggle changes html[data-theme].
 */
(function (global) {
    'use strict';

    var LIGHT = ['#2f6fdb', '#d1495b', '#2a9d8f', '#e09f3e', '#6a4c93', '#457b9d', '#bc6c25', '#8d99ae'];
    var DARK = ['#7aa7f0', '#ef7d8c', '#4fc3b5', '#f0bd63', '#a58fd6', '#7fb3d5', '#d99b5f', '#a8b2c1'];
    var charts = [];

    function currentTheme() {
        var t = document.documentElement.getAttribute('data-theme');
        if (t === 'dark' || t === 'light') { return t; }
        return global.matchMedia && global.matchMedia('(prefers-color-scheme: dark)').matches
            ? 'dark' : 'light';
    }

    function cssVar(name, fallback) {
        var v = global.getComputedStyle(document.documentElement).getPropertyValue(name);
        return (v && v.trim()) || fallback;
    }

    function truthy(v) {
        return v === '' || v === 'true' || v === '1' || v === 'yes';
    }

    /* ------------------------------------------------------------------ data */

    /** rows (JSON from the shortcode) -> { x: [...], series: [{name, values}] } */
    function parseRows(rows) {
        if (!rows || !rows.length) { return null; }
        var header = rows[0].map(function (h) { return String(h).trim(); });
        var series = header.slice(1).map(function (name) { return { name: name, values: [] }; });
        var x = [];
        for (var i = 1; i < rows.length; i++) {
            var r = rows[i];
            if (!r || !r.length) { continue; }
            x.push(String(r[0]).trim());
            for (var j = 0; j < series.length; j++) {
                var cell = r[j + 1];
                if (cell === undefined || cell === null || String(cell).trim() === '' ||
                    String(cell).trim().toLowerCase() === 'nan') {
                    series[j].values.push(null);
                } else {
                    var v = Number(String(cell).trim());
                    series[j].values.push(isFinite(v) ? v : null);
                }
            }
        }
        return { x: x, series: series };
    }

    /* ------------------------------------------------------------- rendering */

    function buildChart(canvas) {
        if (!global.Chart) { return null; }

        var figure = canvas.closest('.chart-figure') || canvas.parentNode;
        var dataEl = figure ? figure.querySelector('script.chart-data') : null;
        var parsed = dataEl ? parseRows(JSON.parse(dataEl.textContent)) : null;
        if (!parsed) { return null; }

        var dark = currentTheme() === 'dark';
        var palette = dark ? DARK : LIGHT;
        var fg = cssVar('--primary', dark ? '#dadadb' : '#1e1e1e');
        var muted = cssVar('--secondary', dark ? '#9b9c9d' : '#6c6c6c');
        var grid = cssVar('--tertiary', dark ? '#414244' : '#d6d6d6');
        var entry = cssVar('--entry', dark ? '#2e2e33' : '#ffffff');

        var type = canvas.dataset.type || 'line';
        var xkind = canvas.dataset.xkind || 'numeric';
        var xlog = truthy(canvas.dataset.xlog);
        var ylog = truthy(canvas.dataset.ylog);
        var smooth = truthy(canvas.dataset.smooth);
        var showLegend = canvas.dataset.legend === undefined
            ? parsed.series.length > 1
            : truthy(canvas.dataset.legend);
        var colors = (canvas.dataset.colors || '').split(',').map(function (c) { return c.trim(); })
            .filter(function (c) { return c; });
        var mirror = (canvas.dataset.ymirror || '').split(',')
            .map(function (s) { return parseInt(s.trim(), 10); })
            .filter(function (n) { return !isNaN(n); });

        var xs = xkind === 'category' ? parsed.x : parsed.x.map(Number);
        var many = parsed.x.length > 80;

        var datasets = parsed.series.map(function (s, i) {
            var color = colors[i] || palette[i % palette.length];
            var values = s.values.map(function (v, k) {
                if (v === null) { return null; }
                if (ylog && v <= 0) { return null; }
                if (type === 'scatter') { return { x: xs[k], y: v }; }
                return v;
            });
            var ds = {
                label: s.name,
                data: values,
                borderColor: color,
                backgroundColor: type === 'bar' ? color : color + '33',
                borderWidth: type === 'bar' ? 0 : 1.8,
                pointRadius: type === 'line' ? (many ? 0 : 2.4) : 3,
                pointHoverRadius: 4,
                tension: smooth ? 0.3 : 0,
                spanGaps: false,
                fill: false,
                yAxisID: mirror.indexOf(i + 1) >= 0 ? 'y1' : 'y'
            };
            if (type === 'bar') { ds.barPercentage = 0.9; }
            return ds;
        });

        var scales = {
            x: {
                type: xkind === 'category' ? 'category' : (xlog ? 'logarithmic' : 'linear'),
                title: { display: !!canvas.dataset.xlabel, text: canvas.dataset.xlabel, color: muted },
                ticks: { color: muted, maxTicksLimit: 8, autoSkip: true },
                grid: { color: grid, drawTicks: false }
            },
            y: {
                type: ylog ? 'logarithmic' : 'linear',
                title: { display: !!canvas.dataset.ylabel, text: canvas.dataset.ylabel, color: muted },
                ticks: { color: muted, maxTicksLimit: 7 },
                grid: { color: grid, drawTicks: false }
            }
        };
        if (mirror.length) {
            scales.y1 = {
                type: 'linear',
                position: 'right',
                title: { display: !!canvas.dataset.y2label, text: canvas.dataset.y2label, color: muted },
                ticks: { color: muted, maxTicksLimit: 7 },
                grid: { drawOnChartArea: false }
            };
        }

        return new global.Chart(canvas.getContext('2d'), {
            type: type,
            data: { labels: xkind === 'category' ? parsed.x : xs, datasets: datasets },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: { duration: 250 },
                interaction: { mode: 'nearest', axis: 'x', intersect: false },
                plugins: {
                    title: {
                        display: !!canvas.dataset.title,
                        text: canvas.dataset.title,
                        color: fg,
                        font: { size: 13, weight: '600' },
                        padding: { bottom: 10 }
                    },
                    legend: {
                        display: showLegend,
                        labels: { color: muted, boxWidth: 12, boxHeight: 2, usePointStyle: false }
                    },
                    tooltip: {
                        backgroundColor: entry,
                        titleColor: fg,
                        bodyColor: fg,
                        borderColor: grid,
                        borderWidth: 1,
                        displayColors: true,
                        callbacks: {
                            title: function (items) {
                                return (canvas.dataset.xlabel ? canvas.dataset.xlabel + ' = ' : '') +
                                    items[0].label;
                            }
                        }
                    }
                },
                scales: scales
            }
        });
    }

    function renderAll() {
        charts.forEach(function (c) { c.destroy(); });
        charts = [];
        document.querySelectorAll('canvas[data-chart]').forEach(function (canvas) {
            try {
                var c = buildChart(canvas);
                if (c) { charts.push(c); }
            } catch (e) {
                /* a broken figure must not take the rest of the page down */
                if (global.console) { console.error('chart:', e); }
            }
        });
    }

    /* ------------------------------------------------------------------ init */

    if (typeof document !== 'undefined') {
        renderAll();
        new MutationObserver(function (mutations) {
            mutations.forEach(function (m) {
                if (m.attributeName === 'data-theme') { renderAll(); }
            });
        }).observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });
    }

    /* exposed for the node test (tools/test_charts.mjs) */
    global.dshCharts = { parseRows: parseRows, buildChart: buildChart, truthy: truthy };
})(typeof window !== 'undefined' ? window : globalThis);
