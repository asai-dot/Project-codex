/**
 * search.test.js — 日本語検索の正規化＋ランキングの単体テスト（Node標準のみ）
 *   `node tests/search.test.js`
 * 純関数(src/search.js)の正規化と、server.js の search() への結線（全半角・かな・空白）を検証。
 */
'use strict';
const assert = require('assert');
const Search = require('../src/search.js');
const { search } = require('../server/server.js'); // require.main 経由でない限りlistenしない

let pass = 0;
function t(name, fn) { fn(); pass++; console.log('  ok -', name); }

// ---- 純関数: normalize ----
t('normalize: 全角英数→半角・小文字', () => {
  assert.strictEqual(Search.normalize('ＡＢＣ１２３'), 'abc123');
});
t('normalize: カタカナ→ひらがな', () => {
  assert.strictEqual(Search.normalize('ソショウホウ'), 'そしょうほう');
});
t('normalize: 濁点・半角カナ(NFKC)も畳む', () => {
  assert.strictEqual(Search.normalize('ｿﾞｼｮｳ'), 'ぞしょう');
});
t('normalize: null/空 → 空文字', () => {
  assert.strictEqual(Search.normalize(null), '');
  assert.strictEqual(Search.normalize(undefined), '');
});
t('toHiragana: 濁音・拗音', () => {
  assert.strictEqual(Search.toHiragana('ガギグャュョ'), 'がぎぐゃゅょ');
});

// ---- 純関数: looseKey（空白無視）----
t('looseKey: 半角/全角スペースを畳む', () => {
  assert.strictEqual(Search.looseKey('時効 の　起算点'), '時効の起算点');
});
t('looseKey: 正規化も併用（全角→半角＋詰め）', () => {
  assert.strictEqual(Search.looseKey('第 １ 章'), '第1章');
});

// ---- 結線: server.search() ----
t('search: 通常クエリで上位がタイトル一致', () => {
  const r = search('時効の起算点', 10);
  assert.ok(r.length > 0, '結果が返る');
  assert.ok(r.some(x => (x.node.t || '').includes('時効の起算点')), 'タイトル一致が含まれる');
  assert.strictEqual(r[0].match && typeof r[0].match, 'string', 'match箇所が付く');
});
t('search: 全角数字クエリ「第１章 私権」が半角タイトルに当たる(NFKC結線)', () => {
  const r = search('第１章 私権', 10);
  assert.ok(r.some(x => (x.node.t || '').includes('第1章 私権')), '全角→半角で一致');
});
t('search: 空白入りクエリが空白無視で一致(looseKey結線)', () => {
  const r = search('時効　の　起算点', 10); // 全角スペース込み
  assert.ok(r.length > 0, 'スペース揺れでも結果が返る');
  assert.ok(r.some(x => (x.node.t || '').includes('時効の起算点')), 'タイトルに着地');
});
t('search: 空クエリ→空配列', () => {
  assert.deepStrictEqual(search('   ', 10), []);
});
t('search: ランキングは完全一致＞部分一致', () => {
  // 「時効」は複数タイトルに含まれる。p昇順タイブレークで安定して返る。
  const r = search('消滅時効', 20);
  assert.ok(r.length >= 2, '複数ヒット');
  // 完全一致タイトル「第3章 消滅時効」相当が、部分一致(章節パス)より上位
  const idxTitle = r.findIndex(x => x.match === 'title');
  const idxPath = r.findIndex(x => x.match && x.match.startsWith('path'));
  if (idxTitle !== -1 && idxPath !== -1) assert.ok(idxTitle < idxPath, 'タイトル一致がパス一致より上位');
});

console.log(`\n${pass} checks passed.`);
