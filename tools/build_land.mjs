// Rebuilds the offline basemap embedded in index.html (Natural Earth 1:50m via the `world-atlas` npm package).
//   npm i world-atlas topojson-client && node tools/build_land.mjs
// Keeps only countries around Indonesia and rounds coordinates to 0.02 degrees (~2 km) to stay light.
import fs from 'fs';
import * as topojson from 'topojson-client';
const topo = JSON.parse(fs.readFileSync('node_modules/world-atlas/countries-50m.json'));
const fc = topojson.feature(topo, topo.objects.countries);
const keep = new Set(['Indonesia','Malaysia','Singapore','Brunei','Timor-Leste','Papua New Guinea','Philippines','Thailand','Vietnam','Cambodia']);
const box = [93, -13, 143, 10];
const r = (n) => Math.round(n * 50) / 50;
const ring = (c) => { const out = []; let last = null;
  for (const [x, y] of c) { const p = [r(x), r(y)]; if (!last || p[0] !== last[0] || p[1] !== last[1]) { out.push(p); last = p; } }
  return out.length >= 4 ? out : null; };
const inBox = (rg) => rg.some(([x, y]) => x >= box[0] && x <= box[2] && y >= box[1] && y <= box[3]);
const feats = [];
for (const f of fc.features) {
  const n = f.properties.name; if (!keep.has(n)) continue;
  const polys = f.geometry.type === 'Polygon' ? [f.geometry.coordinates] : f.geometry.coordinates;
  const out = [];
  for (const poly of polys) {
    const outer = ring(poly[0]); if (!outer || !inBox(outer)) continue;
    out.push([outer, ...poly.slice(1).map(ring).filter(Boolean)]);
  }
  if (out.length) feats.push({ type: 'Feature', properties: { n: n === 'Indonesia' ? 1 : 0 }, geometry: { type: 'MultiPolygon', coordinates: out } });
}
const json = JSON.stringify({ type: 'FeatureCollection', features: feats });
const html = fs.readFileSync('index.html', 'utf8');
const next = html.replace(/<!--LAND:START-->[\s\S]*?<!--LAND:END-->/,
  () => `<!--LAND:START--><script id="land-data" type="application/json">${json}</script><!--LAND:END-->`);
if (next === html && !html.includes(json)) throw new Error('LAND markers not found in index.html');
fs.writeFileSync('index.html', next);
console.log('embedded', feats.length, 'countries,', json.length, 'bytes');
