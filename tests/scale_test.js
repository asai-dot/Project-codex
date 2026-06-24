/**
 * scale_test.js — 本番規模（既定 5,206冊 / 約124k+ノード）での取込・検索の実測（合成データ）。
 *   node tests/scale_test.js            # 5,206冊
 *   SCALE_BOOKS=1000 node tests/scale_test.js
 *
 * 1) gen_synthetic_toc.py で本番の形のTOCを生成 → 2) build_toc_search_index.py で索引化
 * → 3) server.js を合成索引で起動相当ロード → 4) 代表クエリの検索レイテンシとメモリを実測。
 * Box非依存。これが緑なら、本番データを TOC_DIR/BOOKS_JSON/INDEX_PATH に差すだけで回る。
 */
'use strict';
const assert = require('assert');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { execFileSync } = require('child_process');

const N = parseInt(process.env.SCALE_BOOKS || '5206', 10);
const REPO = path.resolve(__dirname, '..');
const WORK = fs.mkdtempSync(path.join(os.tmpdir(), 'codex-scale-'));
const TOC_DIR = path.join(WORK, 'toc');
const BOOKS_JSON = path.join(WORK, 'books.json');
const INDEX_PATH = path.join(WORK, 'toc_search_index.json');

function ms(t0) { return (Number(process.hrtime.bigint() - t0) / 1e6); }

console.log(`スケール実証: ${N.toLocaleString()} 冊 / work=${WORK}\n`);

// 1) 合成データ生成
let t0 = process.hrtime.bigint();
execFileSync('python3', [path.join(REPO, 'scripts', 'gen_synthetic_toc.py'),
  '--out-dir', TOC_DIR, '--books-json', BOOKS_JSON, '--n', String(N)],
  { stdio: 'inherit' });
console.log(`  生成 ${ms(t0).toFixed(0)}ms\n`);

// 2) 索引構築
t0 = process.hrtime.bigint();
execFileSync('python3', [path.join(REPO, 'scripts', 'build_toc_search_index.py')],
  { stdio: 'inherit', env: Object.assign({}, process.env, { TOC_DIR, BOOKS_JSON, OUT: INDEX_PATH }) });
const buildMs = ms(t0);
const idxMb = fs.statSync(INDEX_PATH).size / 1024 / 1024;
console.log(`  索引構築 ${buildMs.toFixed(0)}ms / ${idxMb.toFixed(1)}MB\n`);

// 3) server を合成索引でロード（precomputeIndex がここで走る）
process.env.INDEX_PATH = INDEX_PATH;
process.env.BOOK_LINKS_PATH = path.join(WORK, 'book_links.json'); // 不在→空リンクでOK
t0 = process.hrtime.bigint();
const { search } = require('../server/server.js');
const loadMs = ms(t0);

// 索引のノード総数を確認
const idx = JSON.parse(fs.readFileSync(INDEX_PATH, 'utf-8'));
const nNodes = Object.values(idx.books).reduce((a, b) => a + (b.nodes || []).length, 0);
console.log(`  ロード ${loadMs.toFixed(0)}ms / 索引 ${Object.keys(idx.books).length.toLocaleString()}冊 ${nNodes.toLocaleString()}ノード\n`);

// 4) 代表クエリの検索レイテンシ（全件走査）
const QUERIES = ['時効の起算点', '消滅時効', '第１章 時効', '債権 効力', 'そしょう', '安全配慮義務'];
let worst = 0, anyHit = false;
console.log('  検索レイテンシ（全件走査）:');
for (const q of QUERIES) {
  const s = process.hrtime.bigint();
  const r = search(q, 30);
  const dt = ms(s);
  worst = Math.max(worst, dt);
  if (r.length) anyHit = true;
  console.log(`    ${dt.toFixed(1)}ms  ${r.length}件  "${q}"`);
}
const rssMb = process.memoryUsage().rss / 1024 / 1024;
console.log(`\n  最遅クエリ ${worst.toFixed(1)}ms / RSS ${rssMb.toFixed(0)}MB`);

// --- アサーション（本番規模で破綻しないこと） ---
assert.ok(nNodes >= N * 5, `ノード数が規模相当（${nNodes} >= ${N * 5}）`);
assert.ok(anyHit, '代表クエリの少なくとも1つはヒット');
assert.ok(worst < 1500, `最遅クエリが1.5s未満（実測 ${worst.toFixed(0)}ms）`);
assert.ok(buildMs < 120000, `索引構築が2分未満（実測 ${buildMs.toFixed(0)}ms）`);

fs.rmSync(WORK, { recursive: true, force: true });
console.log('\nスケール実証: 合格。本番は TOC_DIR/BOOKS_JSON/INDEX_PATH を差すだけ。');
