'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const source = fs.readFileSync(path.join(__dirname, '../pisd/web/static/js/panel_presentation_global.js'), 'utf8');

// Browser storage semantics: unchanged strings do not emit events, events are
// delivered asynchronously to other same-origin documents, never the writer.
// A distinct timestamp per write models the observed multi-context echo.
function fixture() {
  const values = new Map(), contexts = [], events = [], pending = [], timers = new Map();
  let requests = 0, writes = 0, stamp = 0, timerId = 0;
  function context() {
    const listeners = {}, docListeners = {}, body = {dataset: {}};
    const storage = {
      getItem: key => values.get(key) ?? null,
      setItem(key, value) {
        value = String(value);
        const old = values.get(key) ?? null;
        if (old === value) return;
        values.set(key, value);
        writes++;
        for (const c of contexts) if (c.storage !== storage) {
          events.push(() => c.listeners.storage?.({key, oldValue: old, newValue: value, storageArea: c.storage}));
        }
      },
    };
    const window = {addEventListener: (k, f) => listeners[k] = f, dispatchEvent() {}};
    const document = {body, documentElement: {style: {setProperty() {}}}, querySelectorAll: () => [], addEventListener: (k, f) => docListeners[k] = f};
    class Clock extends Date { constructor() { super(++stamp * 1000); } }
    vm.runInNewContext(source, {
      window, document, localStorage: storage, Date: Clock, CustomEvent: class {}, AbortController,
      setTimeout: callback => { timers.set(++timerId, callback); return timerId; },
      clearTimeout: id => timers.delete(id),
      fetch(url, options) {
        assert.equal(url, '/api/settings');
        requests++;
        return new Promise((resolve, reject) => {
          const answer = (panel, ok = true) => resolve({ok, status: ok ? 200 : 503, json: async () => ({settings: {panel_presentation: panel}})});
          pending.push(answer);
          options?.signal?.addEventListener('abort', () => {
            const index = pending.indexOf(answer);
            if (index >= 0) pending.splice(index, 1);
            reject(new Error('read aborted'));
          }, {once: true});
        });
      },
    });
    const c = {storage, listeners, body, api: window.PiSDPanelPresentation, start: docListeners.DOMContentLoaded};
    contexts.push(c);
    return c;
  }
  function deliverEvents() { while (events.length) events.shift()(); }
  async function tick() { for (let i = 0; i < 12; i++) await Promise.resolve(); }
  async function settle(panel = {theme: 'dark'}) {
    for (let i = 0; i < 80 && requests <= 250; i++) {
      deliverEvents();
      if (!pending.length) { await tick(); if (!events.length && !pending.length) return; }
      for (const answer of pending.splice(0)) answer(panel);
      await tick();
    }
    assert.fail(`storage echo did not settle: ${requests} GETs, ${writes} writes`);
  }
  function timeout() { for (const callback of [...timers.values()]) callback(); }
  return {context, values, pending, settle, deliverEvents, timeout, counts: () => ({requests, writes})};
}

async function started() {
  const f = fixture();
  const a = f.context(), b = f.context(), c = f.context();
  a.start(); b.start(); c.start();
  await f.settle();
  return {f, a, b, c, key: a.api.SETTINGS_STORAGE_KEY};
}

test('three contexts settle after one initial GET each; no settings echo', async () => {
  const {f} = await started();
  assert.deepEqual(f.counts(), {requests: 3, writes: 2});
});

test('unrelated runtime writes and equivalent values do not read, rewrite or restamp', async () => {
  const {f, a, b, c, key} = await started();
  const runtime = JSON.parse(f.values.get(key));
  runtime.manual_drive = {speed: .5};
  runtime.unknown = {preserve: true};
  runtime.saved_at = 'sentinel';
  a.storage.setItem(key, JSON.stringify(runtime));
  await f.settle();
  assert.equal(f.counts().requests, 3);
  assert.equal(JSON.parse(f.values.get(key)).saved_at, 'sentinel');
  a.api.apply(a.api.save({...a.api.read(), theme: 'light', future: {a: 1, b: 2}}));
  await f.settle();
  assert.equal(b.body.dataset.pisdTheme, 'light');
  assert.equal(c.body.dataset.pisdTheme, 'light');
  assert.deepEqual(JSON.parse(f.values.get(key)).manual_drive, {speed: .5});
  assert.deepEqual(JSON.parse(f.values.get(key)).unknown, {preserve: true});
  const before = f.counts();
  a.api.save({...a.api.read(), future: {b: 2, a: 1}});
  assert.deepEqual(f.counts(), before);
  assert.equal(before.requests, 3);
});

test('rapid genuine changes converge; runtime-only values update the public cache view', async () => {
  const {f, a, b, c, key} = await started();
  a.api.apply(a.api.save({...a.api.read(), theme: 'light'}));
  b.api.apply(b.api.save({...b.api.read(), theme: 'contrast'}));
  await f.settle();
  for (const ctx of [a, b, c]) assert.equal(ctx.body.dataset.pisdTheme, 'contrast');
  const runtime = JSON.parse(f.values.get(key));
  runtime.panel_presentation.theme = 'light';
  b.storage.setItem(key, JSON.stringify(runtime));
  await f.settle();
  assert.equal(a.body.dataset.pisdTheme, 'light');
  assert.equal(a.api.read().theme, 'light');
  assert.equal(c.api.read().theme, 'light');
  assert.equal(f.counts().requests, 3);
});

test('single-flight delayed GET cannot overwrite a newer cross-context setting', async () => {
  const {f, a, b, key} = await started();
  const pending = a.api.loadFromBackend();
  for (let i = 0; i < 8; i++) assert.equal(a.api.loadFromBackend(), pending);
  assert.equal(f.counts().requests, 4);
  b.api.apply(b.api.save({...b.api.read(), theme: 'contrast'}));
  f.deliverEvents();
  const saved = f.values.get(key);
  f.pending.shift()({theme: 'dark'});
  await pending;
  assert.equal(a.body.dataset.pisdTheme, 'contrast');
  assert.equal(f.values.get(key), saved);
  assert.equal(f.counts().requests, 4);
});

test('failed and timed-out reads retain fallback and permit a later explicit read', async () => {
  const {f, a, b, key} = await started();
  b.api.apply(b.api.save({...b.api.read(), theme: 'light'}));
  f.deliverEvents();
  const saved = f.values.get(key);
  const failed = a.api.loadFromBackend();
  f.pending.shift()({}, false);
  await failed;
  assert.equal(a.body.dataset.pisdTheme, 'light');
  const hung = a.api.loadFromBackend();
  f.timeout();
  await hung;
  assert.equal(a.body.dataset.pisdTheme, 'light');
  assert.equal(f.values.get(key), saved);
  const retry = a.api.loadFromBackend();
  f.pending.shift()({theme: 'contrast'});
  await retry;
  await f.settle();
  assert.equal(a.body.dataset.pisdTheme, 'contrast');
  assert.equal(b.body.dataset.pisdTheme, 'contrast');
  assert.equal(f.counts().requests, 6);
});

test('page-specific startup cache wins over stale dedicated events and matching GET is safe', async () => {
  const {f, a, key} = await started();
  const load = a.api.loadFromBackend();
  const runtime = JSON.parse(f.values.get(key));
  runtime.panel_presentation.theme = 'light';
  runtime.saved_at = 'page-specific';
  a.storage.setItem(key, JSON.stringify(runtime));
  assert.equal(a.api.read().theme, 'light');
  f.pending.shift()({theme: 'light'});
  await load;
  await f.settle();
  assert.equal(a.body.dataset.pisdTheme, 'light');
  assert.equal(JSON.parse(f.values.get(key)).saved_at, 'page-specific');
  assert.equal(JSON.parse(f.values.get(a.api.STORAGE_KEY)).theme, 'light');
  assert.equal(f.counts().requests, 4);
});

test('an explicit same-value cache save invalidates an earlier differing read', async () => {
  const {f, a, key} = await started();
  const load = a.api.loadFromBackend();
  const saved = f.values.get(key);
  const before = f.counts().writes;
  a.api.save(a.api.read());
  assert.equal(f.counts().writes, before);
  f.pending.shift()({theme: 'light'});
  await load;
  assert.equal(a.body.dataset.pisdTheme, 'dark');
  assert.equal(f.values.get(key), saved);
});
