# 設計: legallib 分岐を `merge_toc_updates.py` へ統合する案

**状態**: 設計のみ（本実装は実データ・ドライラン結果の後）。
**目的**: 現行の openbd/GT 経路（`app/scripts/merge_toc_updates.py`）と本 Fork の
legallib 経路を、**1 つの統合マージエンジン**に畳み込む。既存挙動を 1 バイトも
変えずに（回帰ゼロ）、legallib を第 2 のソースチャネルとして足す。

---

## 0. なぜ統合するか / しないか

- **する理由**: ロック・atomic write・`hasToc` 反映・ログ・冪等性といった
  「書き込みの作法」は両経路で同一。二重実装は事故の元（片方だけロック忘れ等）。
- **慎重にやる理由**: 両経路は**マージ判定の思想が違う**。
  - openbd/GT = **rank ベース置換**（`replace_if_higher_source`：rank が上なら
    既存が simple でなくても置換しうる）。
  - legallib = **simple-only ゲート**（既存が simple のみ・非保護のときだけ昇格上書き）。
  この差を 1 つの分岐条件に潰すと、どちらかの安全性が崩れる。→ **per-source の
  ゲート関数**として分離し、エンジン核は共通化する。

---

## 1. 現行 `merge_toc_updates.py` の構造（実コードより）

```
load_policy() → priority/rules
books_by_isbn = {isbn: book}
for line in MERGED_JSONL:          # openbd/GT を isbn 単位で
    incoming = gt_lines_to_nodes(isbn, toc_text, src)   # toc_status="simple"
    if not exists:                 create
    elif existing_primary=="manual" keep:  skip_manual
    elif incoming_rank < existing_rank:     replace      # ← rank ベース
    elif incoming_rank==existing_rank:      merge append_missing_only
    else:                                   skip_lower
    log → toc_merge_log.jsonl
books_write_lock + atomic_write_json(BOOKS_JSON)   # hasToc 反映
```

**共通化できる核**: ロック / atomic write / hasToc 反映 / ログ / 出力パス決定。
**ソース固有**: ① 入力の取り出し方（jsonl 行 vs resolver+legallib_dl）、
② incoming ノードの作り方（`gt_lines_to_nodes` vs `convert_legallib_nodes`）、
③ **マージ判定**（rank 置換 vs simple-only ゲート）、④ 前段ガード（legallib のみ
book_id↔isbn 誤マージ0）。

---

## 2. 統合アーキテクチャ（source adapter パターン）

```
                ┌─────────────── MergeEngine（共通核） ───────────────┐
                │  - books_write_lock / atomic_write_json             │
                │  - hasToc 反映 / toc_merge_log.jsonl                 │
                │  - 出力パス決定 / --dry-run / --commit              │
                └───────────────┬───────────────────────┬────────────┘
                                │ uses                   │ uses
                   ┌────────────▼─────────┐   ┌──────────▼──────────────┐
                   │ SourceAdapter (proto) │   │  MergeGate (proto)      │
                   │  iter_incoming()      │   │  decide(existing, inc)  │
                   │   -> (isbn, nodes,    │   │   -> action             │
                   │       source, meta)   │   │                         │
                   └───────────┬───────────┘   └──────────┬──────────────┘
            ┌──────────────────┴───────┐        ┌─────────┴───────────────┐
            │ OpenbdAdapter            │        │ RankReplaceGate（現行）  │
            │  (MERGED_JSONL,          │        │  既存ロジックそのまま     │
            │   gt_lines_to_nodes)     │        └─────────────────────────┘
            ├──────────────────────────┤        ┌─────────────────────────┐
            │ LegallibAdapter          │        │ SimpleOnlyGate（本Fork） │
            │  (resolver+legallib_dl,  │        │  decide_join_action()    │
            │   convert_legallib_nodes,│        │  + mis-merge 前段ガード   │
            │   detect_mismerge 前段)  │        └─────────────────────────┘
            └──────────────────────────┘
```

### 2.1 プロトコル（インターフェース・擬似コード）

```python
class SourceAdapter(Protocol):
    name: str
    gate: "MergeGate"
    def preflight(self, ctx) -> list[str]: ...        # 前段ガード（legallib: 誤マージ）
    def iter_incoming(self, ctx) -> Iterator[Incoming]: ...
    # Incoming = (isbn, incoming_nodes, source, meta)

class MergeGate(Protocol):
    def decide(self, existing: list[dict] | None,
               incoming: Incoming, policy) -> str: ...
    # action: create | overwrite/replace | merge | skip_* | route_human_review

class MergeEngine:
    def run(self, adapters: list[SourceAdapter], *, dry_run: bool) -> Report:
        for adapter in adapters:
            blocked = adapter.preflight(self.ctx)         # legallib のみ実体
            for inc in adapter.iter_incoming(self.ctx):
                if inc.isbn in blocked: log(blocked); continue
                existing = self.load_existing(inc.isbn)
                action = adapter.gate.decide(existing, inc, self.policy)
                if action in WRITE_ACTIONS and not dry_run:
                    self.atomic_write(inc.isbn, inc.incoming_nodes)
                    self.mark_hastoc(inc.isbn)
                self.log(inc, action, dry_run)
        if not dry_run:
            self.flush_books_json()    # books_write_lock + atomic_write_json
        return self.report
```

### 2.2 ゲートの対応（既存挙動は不変）

| ゲート | 使うソース | decide のロジック |
|---|---|---|
| `RankReplaceGate` | openbd / GT | **現行コードをそのまま**移植（create / skip_manual / rank replace / append_missing / skip_lower） |
| `SimpleOnlyGate` | legallib | `decide_join_action()`（create / overwrite_simple / skip_idempotent / route_human_review）+ 前段 `detect_mismerge` |

> **回帰ゼロの肝**: openbd は `RankReplaceGate` に**逐語移植**するだけ。判定式・
> 出力ノード・ログ文字列を変えない。legallib は独立ゲートなので互いに干渉しない。

---

## 3. ポリシーの一本化

- 単一の `data/toc_merge_policy_legallib.json`（`ndl`/`legallib` 追加済）を
  両ゲートが読む。`priority` は openbd 経路の rank 判定にもそのまま使える
  （openbd/books_or_jp/bencom/codex_ocr の相対順は不変）。
- `protected_sources`・`legallib.*` は `SimpleOnlyGate` のみ参照。`RankReplaceGate`
  は従来通り `rules.replace_if_higher_source` 等を参照。
- **`ndl` を priority に足したことの影響確認**: 既存 toc ファイルに
  `toc_source=="ndl"` が存在するかを実データで確認。存在すれば rank が上がるだけで
  既存挙動は安全側（ndl が openbd に上書きされなくなる）。要・実データ確認項目。

---

## 4. 安全性の差分（統合で**新たに足すべき**もの）

1. **`--dry-run` をエンジンに追加**: 現行 `merge_toc_updates.py` は dry-run を
   持たず、走らせると即書き込む。統合版では `--dry-run` を**既定**にし、
   `--commit` で初めて書く（legallib 経路と同じ作法に揃える）。これは openbd
   経路にとっても安全性の純増。
2. **mis-merge 前段ガードはアダプタ責務**: openbd は isbn 直キーなので不要、
   legallib は `detect_mismerge` を `preflight` で実行。
3. **不変条件アサーション**: エンジンが書き込み後に「保護対象へ書いていないか」を
   再走査（`run_dryrun` の `invariant_violations` と同型）。両経路に適用。

---

## 5. 段階移行計画（回帰を出さない順序）

| Phase | 内容 | 検証 |
|---|---|---|
| 0 | 現行 `merge_toc_updates.py` の**ゴールデン出力**を採取（既存 MERGED_JSONL で全 action と書き込みバイト列を記録） | スナップショット |
| 1 | エンジン核 + `OpenbdAdapter`/`RankReplaceGate` を実装し、openbd 経路を移植 | **Phase0 と byte 一致**（回帰ゼロ証明） |
| 2 | `LegallibAdapter`/`SimpleOnlyGate` を追加（本 Fork のコードを移設） | 既存 `tests/test_legallib_join.py` が緑のまま |
| 3 | `--dry-run` 既定化・`--commit` ゲート・不変条件アサーションを両経路へ | デモ + 実ドライラン |
| 4 | 旧 `merge_toc_updates.py` を thin wrapper（エンジン呼び出し）に置換 | 並走比較後に切替 |

> Phase 1 の「byte 一致」が回帰ゼロの機械的証明。これが取れるまで legallib を
> 同居させない。

---

## 6. 未確定（実データ後に確定する項目）

- `toc_source=="ndl"` の既存ファイル有無（§3）。
- legallib の `overwrite_simple` と openbd の `append_missing_only` が**同一 isbn に
  競合**しうるか（実行順序の規定が要るか）。原則: legallib（詳細・階層）が
  simple を置換 → その後の openbd 同 rank merge は legallib（非simple）に対しては
  `skip`（既に非simple = 保護）になり、競合しない見込み。実データで確認。
- ログ schema 統一（`source` フィールドで経路を判別できるよう既に両者付与済）。

---

## 7. 本 Fork コードとの対応

| 統合後の部品 | 本 Fork の既存実体（移設元） |
|---|---|
| `SimpleOnlyGate.decide` | `scripts/legallib_join_policy.py: decide_join_action` |
| `LegallibAdapter.iter_incoming` | `scripts/legallib_to_canonical.py: convert_legallib_nodes` + `legallib_join_dryrun.py: load_*` |
| `LegallibAdapter.preflight` | `legallib_join_dryrun.py: detect_mismerge` |
| エンジンの `--dry-run`/`--commit`/不変条件 | `legallib_join_dryrun.py` / `legallib_join_apply.py` |

→ 本 Fork のモジュールは**最初から統合を見据えた粒度**で分離してある
（変換 / ゲート / 実行 を別ファイル）。統合時は移設のみで再実装不要。
