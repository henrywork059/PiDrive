'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const root = path.join(__dirname, '../pisd/web');
const design = fs.readFileSync(path.join(root,'static/css/pisd_design_system.css'),'utf8');
const layout = fs.readFileSync(path.join(root,'static/css/pisd_layout_system.css'),'utf8');
const required = ['bg','surface','surface-soft','line','text','muted','primary','ok','warning','danger','recording','capture'];
for (const name of required) assert.match(design, new RegExp('--pisd-palette-'+name+':\\s*#[0-9a-f]{6}\\s*;', 'i'));
for (const name of ['ring','shadow','width']) {
  assert.match(design,new RegExp('--pisd-focus-'+name+':'));
  assert.ok(design.includes('var(--pisd-focus-'+name+')'));
}
assert.ok(layout.includes('var(--pisd-ui-gap, 10px)'));
assert.ok(layout.includes('var(--pisd-ui-density-pad, 0.86)'));
assert.ok(layout.includes('var(--pisd-ui-radius, 14px)'));
assert.ok(design.includes('prefers-reduced-motion: reduce'));
assert.ok(design.includes('forced-colors: active'));
assert.equal((design.match(/:where\([^\n]*\bsummary\b[^\n]*\):focus-visible/g) || []).length, 2,
  'native disclosure controls must receive normal and forced-colors focus rings');
const front = fs.readFileSync(path.join(root,'static/css/front_page.css'),'utf8');
assert.match(front, /@media\s*\(prefers-reduced-motion:\s*reduce\)\s*\{\s*\.fp-mode-card:hover,\s*\.fp-mode-card:focus-visible\s*\{\s*transform:\s*none;/);
for (const name of ['manual_drive','ai_mode','settings_tab','front_page']) {
  const html = fs.readFileSync(path.join(root,'templates',name+'.html'),'utf8');
  assert.ok(html.includes('css/pisd_design_system.css'), name+' lost design system');
}
console.log('PiSD R45 semantic palette, focus, density and page contract passed');
