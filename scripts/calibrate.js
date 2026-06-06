#!/usr/bin/env node
/**
 * calibrate.js — offset の1点合わせ（CLI / バッチ）
 *
 * 実ビューワーで「印刷ページ P を表示しているときのビューワーページ番号 V」を1点取れば
 * offset = V - P が確定し、以後その本はページ単位で着地できる。
 * LEGAL LIBRARY は「現在ページのURL発行」、ベンコムは画面のページ送り表示から V を読む。
 *
 * 使い方:
 *   # 実ビューワーURLを貼るだけ（book_key と viewer_page を自動抽出）＋印刷ページ
 *   node scripts/calibrate.js --book isbn_9784641138001 \
 *        --url "https://legal-library.jp/r/326510?page=39&ctg=view" --print 33
 *   # 手入力でも可
 *   node scripts/calibrate.js --book isbn_9784641138001 --source legal_library \
 *        --print 135 --viewer 151 [--book-key 326510]
 *   node scripts/calibrate.js --book isbn_9784xxxx --source physical_shelf --location 民法-A-2
 *
 * data/book_links.json を更新する。
 */
'use strict';
const fs = require('fs');
const path = require('path');
const Deeplink = require('../src/deeplink.js');

function parseArgs(argv) {
  const a = {};
  for (let i = 2; i < argv.length; i++) {
    const k = argv[i];
    if (k.startsWith('--')) { a[k.slice(2)] = (argv[i + 1] && !argv[i + 1].startsWith('--')) ? argv[++i] : true; }
  }
  return a;
}

function main() {
  const a = parseArgs(process.argv);
  // --url が来たら source/book_key/viewer を自動抽出
  if (a.url) {
    const SOURCES = require('../config/library_sources.json').sources;
    const parsed = Deeplink.parseViewerUrl(SOURCES, a.url);
    if (parsed) {
      if (!a.source) a.source = parsed.source_id;
      if (!a['book-key'] && parsed.book_key != null) a['book-key'] = parsed.book_key;
      if (a.viewer == null && parsed.viewer_page != null) a.viewer = parsed.viewer_page;
      console.log(`URL解析: source=${parsed.source_id} book_key=${parsed.book_key} viewer_page=${parsed.viewer_page}`);
    } else {
      console.error('URLからソースを判定できませんでした（config の link_parse を確認）');
    }
  }
  if (!a.book || !a.source) {
    console.error('必須: --book <book_id> --source <office_pdf|bencom|legal_library|physical_shelf>（--url 指定時 source は自動）');
    console.error('ページ着地用: --url <実URL> --print <印刷ページ>  または  --print P --viewer V [--book-key K]');
    console.error('物理本: --location <棚位置>   自炊PDF: --folder F --file NAME.pdf');
    process.exit(1);
  }
  const file = path.join(__dirname, '..', 'data', 'book_links.json');
  const doc = JSON.parse(fs.readFileSync(file, 'utf-8'));
  doc.links = doc.links || {};
  const entry = Object.assign({}, doc.links[a.book] && doc.links[a.book][a.source]);

  if (a.print != null && a.viewer != null) {
    const offset = Deeplink.computeOffset(Number(a.print), Number(a.viewer));
    entry.offset = offset;
    console.log(`offset = ${a.viewer} - ${a.print} = ${offset}`);
  }
  if (a['book-key']) entry.book_key = a['book-key'];
  if (a.folder) entry.folder = a.folder;
  if (a.file) entry.file = a.file;
  if (a.location) entry.location = a.location;

  doc.links[a.book] = Object.assign({}, doc.links[a.book], { [a.source]: entry });
  fs.writeFileSync(file, JSON.stringify(doc, null, 2) + '\n', 'utf-8');
  console.log(`保存: ${a.book} / ${a.source} →`, JSON.stringify(entry));
}

main();
