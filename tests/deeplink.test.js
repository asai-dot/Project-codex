/**
 * deeplink.test.js — ジャンプ解決エンジンの単体テスト（Node標準のみ。`node tests/deeplink.test.js`）
 */
'use strict';
const assert = require('assert');
const Deeplink = require('../src/deeplink.js');

const SOURCES = require('../config/library_sources.json').sources;
const byId = Object.fromEntries(SOURCES.map(s => [s.id, s]));

let pass = 0;
function t(name, fn) { fn(); pass++; console.log('  ok -', name); }

// 1) 自炊PDF: offsetあり & ページあり → ページ着地（#page= に viewer_page）
t('office_pdf: offset+page → ページ着地', () => {
  const r = Deeplink.resolveLink(byId.office_pdf, { folder: '民法', file: '債権総論.pdf', offset: 14 }, 135);
  assert.strictEqual(r.status, 'page');
  assert.strictEqual(r.viewer_page, 149);
  assert.strictEqual(r.url, '/pdf_orig/民法/債権総論.pdf#page=149');
});

// 2) リーガル: offsetあり → ページ着地
t('legal_library: offset+page → ページ着地', () => {
  const r = Deeplink.resolveLink(byId.legal_library, { book_key: '9784641138001', offset: 16 }, 135);
  assert.strictEqual(r.status, 'page');
  assert.strictEqual(r.viewer_page, 151);
  assert.ok(r.url.includes('/page/151'));
});

// 3) ベンコム: offset=null（未校正）→ トップ着地
t('bencom: offset未校正 → トップ着地', () => {
  const r = Deeplink.resolveLink(byId.bencom, { book_key: 'BLL-x', offset: null }, 135);
  assert.strictEqual(r.status, 'book_top');
  assert.strictEqual(r.reason, 'offset_not_calibrated');
  assert.strictEqual(r.url, 'https://www.businesslawyers.jp/lib/book/BLL-x');
});

// 4) print_page不明（本トップから開く）→ トップ着地
t('print_page不明 → トップ着地', () => {
  const r = Deeplink.resolveLink(byId.legal_library, { book_key: 'k', offset: 16 }, null);
  assert.strictEqual(r.status, 'book_top');
  assert.strictEqual(r.reason, 'print_page_unknown');
});

// 5) 物理本: URLなし、location と print_page を返す
t('physical_shelf: location+print_page', () => {
  const r = Deeplink.resolveLink(byId.physical_shelf, { location: '民法-A-2' }, 135);
  assert.strictEqual(r.status, 'physical');
  assert.strictEqual(r.location, '民法-A-2');
  assert.strictEqual(r.print_page, 135);
});

// 6) その本がそのライブラリに無い → unavailable
t('link無し → unavailable', () => {
  const r = Deeplink.resolveLink(byId.bencom, null, 135);
  assert.strictEqual(r.status, 'unavailable');
});

// 7) computeOffset: 1点合わせ
t('computeOffset = viewer - print', () => {
  assert.strictEqual(Deeplink.computeOffset(135, 151), 16);
  assert.strictEqual(Deeplink.computeOffset(1, 15), 14);
});

// 8) resolveAll: 全4図書館分そろう
t('resolveAll → 4系統', () => {
  const all = Deeplink.resolveAll(SOURCES, { office_pdf: { folder: 'f', file: 'a.pdf', offset: 14 }, physical_shelf: { location: 'X' } }, 100);
  assert.strictEqual(all.length, 4);
  assert.strictEqual(all.find(x => x.source_id === 'office_pdf').status, 'page');
  assert.strictEqual(all.find(x => x.source_id === 'bencom').status, 'unavailable');
});

console.log(`\n${pass} tests passed.`);
