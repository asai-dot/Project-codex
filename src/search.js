/**
 * search.js — 日本語の目次横断検索むけテキスト正規化（サーバ/ブラウザ共有・純関数）
 *
 * 目的: 「全角/半角」「カタカナ/ひらがな」「英大小」「空白の揺れ」を吸収して、
 * 人間が雑に打った検索語でも章節タイトル・章節パスに当たるようにする。
 * deeplink.js と同じ思想で「唯一の実装」をサーバ(server.js)が読み込む。
 *
 *   normalize("ｿﾞｼｮｳ ﾎｳ")  → "そしょうほう" 相当（NFKC→小文字→カナ→かな）
 *   looseKey は空白も畳んで完全に詰めたキー（空白無視マッチ用）。
 */
'use strict';

// カタカナ(ァ-ヶ)→ひらがな。長音符・中点はそのまま。
function toHiragana(s) {
  return s.replace(/[ァ-ヶ]/g, c => String.fromCharCode(c.charCodeAt(0) - 0x60));
}

// 検索キー: Unicode正規化(NFKC, 全角英数→半角等) → 小文字 → カナ→かな
function normalize(s) {
  if (s == null) return '';
  let t = String(s).normalize('NFKC').toLowerCase();
  return toHiragana(t);
}

// 空白（半/全角・タブ）を畳んだキー。「時効 の 起算点」と「時効の起算点」を同一視。
function looseKey(s) {
  return normalize(s).replace(/[\s　]+/g, '');
}

if (typeof module !== 'undefined' && module.exports) {
  module.exports = { normalize, toHiragana, looseKey };
}
