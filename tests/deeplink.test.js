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

// 2) リーガル: offsetあり → ページ着地（実URL形式 /r/{key}?page=...&ctg=view）
t('legal_library: offset+page → ページ着地', () => {
  const r = Deeplink.resolveLink(byId.legal_library, { book_key: '326510', offset: 16 }, 135);
  assert.strictEqual(r.status, 'page');
  assert.strictEqual(r.viewer_page, 151);
  assert.strictEqual(r.url, 'https://legal-library.jp/r/326510?page=151&ctg=view');
});

// 2b) parseViewerUrl: 実URLから source/book_key/viewer_page を抽出
t('parseViewerUrl: 実リーガルURLを分解', () => {
  const p = Deeplink.parseViewerUrl(SOURCES, 'https://legal-library.jp/r/326510?page=39&ctg=view');
  assert.strictEqual(p.source_id, 'legal_library');
  assert.strictEqual(p.book_key, '326510');
  assert.strictEqual(p.viewer_page, 39);
});

// 2c) parse → computeOffset の連携（印刷33ページがビューワー39 → offset 6）
t('paste-URL校正: offset = viewer - print', () => {
  const p = Deeplink.parseViewerUrl(SOURCES, 'https://legal-library.jp/r/326510?page=39&ctg=view');
  assert.strictEqual(Deeplink.computeOffset(33, p.viewer_page), 6);
});

// 3) ベンコム: offset+page → ページ着地（共有URLの &adr={viewer_page} 形式）
//    引用判例リンク画面の「83ページ 紙面43ページ」が offset=40 の根拠
t('bencom: offset+page → ページ着地（adr）', () => {
  const cid = 'ebaaf6907d0c7eaf14a99fcd7e40c42283674fb06f5f4216fa45a02d118465b5';
  const r = Deeplink.resolveLink(byId.bencom, { book_key: cid, offset: 40 }, 43);
  assert.strictEqual(r.status, 'page');
  assert.strictEqual(r.viewer_page, 83);
  assert.strictEqual(r.url, 'https://library.bengo4.com/reader/?cid=' + cid + '&adr=83');
});

// 3a) ベンコム: offset未設定 → トップ着地（fallback）
t('bencom: offset未設定 → トップ着地', () => {
  const cid = 'ebaaf6907d0c7eaf14a99fcd7e40c42283674fb06f5f4216fa45a02d118465b5';
  const r = Deeplink.resolveLink(byId.bencom, { book_key: cid }, 43);
  assert.strictEqual(r.status, 'book_top');
  assert.strictEqual(r.url, 'https://library.bengo4.com/reader/?cid=' + cid);
});

// 3b) parseViewerUrl: ベンコム共有URL（&adr=81）から cid と viewer_page を抽出
t('parseViewerUrl: ベンコム共有URL（adr）を分解', () => {
  const cid = 'ebaaf6907d0c7eaf14a99fcd7e40c42283674fb06f5f4216fa45a02d118465b5';
  const p = Deeplink.parseViewerUrl(SOURCES, 'https://library.bengo4.com/reader/?cid=' + cid + '&adr=81');
  assert.strictEqual(p.source_id, 'bencom');
  assert.strictEqual(p.book_key, cid);
  assert.strictEqual(p.viewer_page, 81);
});

// 3c) 共有URL貼付け校正: adr=81 を印刷41で取れば offset=40
t('paste-URL校正(bencom): offset = adr - print', () => {
  const p = Deeplink.parseViewerUrl(SOURCES, 'https://library.bengo4.com/reader/?cid=x0123456789abcdef&adr=81');
  assert.strictEqual(Deeplink.computeOffset(41, p.viewer_page), 40);
});

// 3d) book_only 戦略（合成ソースで分岐を担保）: 常にトップ着地
t('book_only 戦略 → 常にトップ着地', () => {
  const fake = { id: 'x', page_strategy: 'book_only', book_url_template: 'https://ex/{book_key}' };
  const r = Deeplink.resolveLink(fake, { book_key: 'k' }, 99);
  assert.strictEqual(r.status, 'book_top');
  assert.strictEqual(r.reason, 'book_only');
  assert.strictEqual(r.url, 'https://ex/k');
});

// 3b) parseViewerUrl: ベンコム reader URL から cid を book_key として抽出（page無し→viewer_page null）
t('parseViewerUrl: 実ベンコムreader URL → cid捕捉', () => {
  const p = Deeplink.parseViewerUrl(SOURCES, 'https://library.bengo4.com/reader/?cid=ebaaf6907d0c7eaf14a99fcd7e40c42283674fb06f5f4216fa45a02d118465b5');
  assert.strictEqual(p.source_id, 'bencom');
  assert.strictEqual(p.book_key, 'ebaaf6907d0c7eaf14a99fcd7e40c42283674fb06f5f4216fa45a02d118465b5');
  assert.strictEqual(p.viewer_page, null);
});

// 3c) parseViewerUrl: ベンコム books ランディング形式でも cid を捕捉
t('parseViewerUrl: ベンコム /books/ 形式も捕捉', () => {
  const p = Deeplink.parseViewerUrl(SOURCES, 'https://library.bengo4.com/books/09fbb75af2ad93c5daf60babe8d2c1192329d7a8ed03936a7ea4b602e25b4b46');
  assert.strictEqual(p.source_id, 'bencom');
  assert.strictEqual(p.book_key, '09fbb75af2ad93c5daf60babe8d2c1192329d7a8ed03936a7ea4b602e25b4b46');
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
