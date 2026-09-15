/* Node test for the `chart` shortcode front end (assets/js/charts.js).
 *
 *     node tools/test_charts.mjs [path/to/built/page.html]
 *
 * charts.js only needs a handful of DOM calls, so a tiny stub is enough to run
 * the real code path — including dataset/scales construction — in Node, without
 * a browser.  Chart.js itself is replaced by a recorder.
 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, '..');
const page = process.argv[2] || path.join(root, 'public/posts/av-mv-fsi-debugging/index.html');

let pass = 0;
let fail = 0;
function check(name, ok, extra = '') {
    if (ok) { pass++; console.log('  ok   ' + name + (extra ? '  (' + extra + ')' : '')); }
    else { fail++; console.log('  FAIL ' + name + (extra ? '  (' + extra + ')' : '')); }
}

/* ------------------------------------------------------------- DOM stub -- */

const CONFIGS = [];

function makeFigure(csv, attrs) {
    const dataScript = { textContent: JSON.stringify(csv) };
    const figure = { querySelector: (sel) => (sel === 'script.chart-data' ? dataScript : null) };
    return {
        dataset: attrs,
        closest: (sel) => (sel === '.chart-figure' ? figure : null),
        getContext: () => ({})
    };
}

globalThis.getComputedStyle = () => ({ getPropertyValue: () => '' });
globalThis.document = {
    documentElement: { getAttribute: () => 'light' },
    querySelectorAll: () => canvases
};
globalThis.MutationObserver = class { observe() {} };
globalThis.Chart = class {
    constructor(ctx, config) {
        CONFIGS.push(config);
        this.data = config.data;
        this.options = config.options;
    }
};

/* ------------------------------------------------------------- fixtures -- */

const rows = (s) => s.trim().split('\n').map((l) => l.split(',').map((c) => c.trim()));

const canvases = [
    makeFigure(rows(`
        t, a, b
        0, 1, 10
        1, 2,
        2, 3, 30
    `), { type: 'line', xlabel: 't', ylabel: 'y' }),

    makeFigure(rows(`
        marker, cells
        tube, 0
        disk, 121
    `), { type: 'bar', xkind: 'category', legend: 'false' }),

    makeFigure(rows(`
        t, d
        0, 1e-6
        1, 0
        2, 1e-2
    `), { type: 'line', ylog: 'true' }),

    makeFigure(rows(`
        t, p, q
        0, 1, 100
        1, 2, 200
    `), { type: 'line', ymirror: '2', y2label: 'q' })
];

/* --------------------------------------------------------------- run it -- */

await import(path.join(root, 'assets/js/charts.js'));

console.log('charts.js — ' + CONFIGS.length + ' figure(s) built in the DOM stub');
check('one config per canvas', CONFIGS.length === canvases.length, CONFIGS.length + '/' + canvases.length);

const [line, bar, log, mirror] = CONFIGS;

check('series names come from the header',
    line.data.datasets.map((d) => d.label).join(',') === 'a,b');
check('empty cell becomes a gap',
    line.data.datasets[1].data.join(',') === '10,,30');
check('numeric x axis keeps numbers',
    line.data.labels.join(',') === '0,1,2');
check('legend shown when several series', line.options.plugins.legend.display === true);
check('legend off when asked', bar.options.plugins.legend.display === false);
check('category axis', bar.options.scales.x.type === 'category');
check('log axis', log.options.scales.y.type === 'logarithmic');
check('non-positive sample dropped on log axis',
    log.data.datasets[0].data.join(',') === '0.000001,,0.01');
check('mirror axis defined and used',
    !!mirror.options.scales.y1 && mirror.data.datasets[1].yAxisID === 'y1');
check('sparse series keeps its points',
    line.data.datasets[0].pointRadius > 0, '3 points → ' + line.data.datasets[0].pointRadius);
check('title/axis labels carried over',
    line.options.scales.x.title.text === 't' && line.options.scales.y.title.text === 'y');

/* --------------------------------------------- against the real page too -- */

if (fs.existsSync(page)) {
    const html = fs.readFileSync(page, 'utf8');
    const blocks = [...html.matchAll(
        /<script type=application\/json class=chart-data>(.*?)<\/script>/gs)].map((m) => JSON.parse(m[1]));
    console.log('\n' + path.relative(root, page) + ' — ' + blocks.length + ' data block(s)');
    check('page ships chart data', blocks.length > 0);
    blocks.forEach((b, i) => {
        const parsed = globalThis.dshCharts.parseRows(b);
        check('block ' + i + ' parses', parsed !== null && parsed.x.length > 0,
            parsed ? parsed.x.length + ' points, ' + parsed.series.length + ' series' : 'unparsable');
    });
    check('chart assets referenced',
        html.includes('chart.umd.min.js') && /charts\.[0-9a-f]{20,}\.js/.test(html));

    // a dense series (the real AV curves) must drop its markers
    const canvas = makeFigure(blocks[0], { type: 'line' });
    const dense = globalThis.dshCharts.buildChart(canvas);
    check('dense series hides points', dense.data.datasets[0].pointRadius === 0,
        dense.data.labels.length + ' points → ' + dense.data.datasets[0].pointRadius);
} else {
    console.log('\n(skip) built page not found: ' + page);
}

console.log('\n' + pass + ' passed, ' + fail + ' failed');
process.exit(fail ? 1 : 0);
