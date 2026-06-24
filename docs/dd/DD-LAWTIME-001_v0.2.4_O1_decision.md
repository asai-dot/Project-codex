# DD-LAWTIME-001 v0.2.4 — O1 決定メモ（母屋 edge 削除時の FK 挙動）

> status: **DECISION REQUIRED（owner 決裁待ち / 課金ゼロ）**。本メモは判断材料のみ。DB 操作なし。
> 関連: [`..._v0.2.4_materialize_runbook.md`](./DD-LAWTIME-001_v0.2.4_materialize_runbook.md) §0/§7（O1 は PHASE D の前に確定が必要）。
> 出典: 監査 RESULT `DDLAWTIME_V024_PLACEMENT_PASS_WITH_NOTES`（Box 2306481004211）Notes O1。

---

## 1. 何が問題か

`100_lawtime_schema.sql` で、母屋 `d1law_taikei.alo_edges(edge_id)` を参照する lawtime 側の FK は **3本**あり、
**削除挙動が揃っていない**：

| 参照テーブル | 現状の FK 削除挙動 | 性質 |
|---|---|---|
| `lawtime.citation_temporal` | `ON DELETE CASCADE` | edge の時間軸評価（1 edge = 1 行） |
| `lawtime.unresolved_queue` | `ON DELETE CASCADE` | 未解決キュー（1 edge = 1 行） |
| `lawtime.temporal_eval_event` | **NO ACTION（既定）** + **append-only トリガ**（UPDATE/DELETE で `RAISE EXCEPTION`） | 解決 run/result の**追記専用監査ログ** |

### 現状の実際の挙動（`DELETE FROM d1law_taikei.alo_edges WHERE edge_id = X`）
- **X に eval 履歴がある場合**: `temporal_eval_event` の NO ACTION FK が子行を理由に**親削除をブロック**。
  → 削除自体が失敗。`citation_temporal` / `unresolved_queue` の CASCADE は**発火しない**。
- **X に eval 履歴が無い場合**: `citation_temporal` / `unresolved_queue` の行が**cascade で消える**。

→ 実質「**eval 履歴の無い edge だけ削除でき、その時だけサイドテーブルが消える**」という挙動。
**動くが暗黙的**で、設計コメント（"the temporal row must not outlive [the edge]" ＝ CASCADE 意図）と
append-only 監査ログ（"評価は消さない" 意図）が**内部で矛盾**している。これを揃えるのが O1。

---

## 2. 選択肢

### A. 統一 RESTRICT／NO ACTION（履歴保護・推奨）
3本とも「lawtime が参照している間は母屋 edge を削除できない」に揃える。

- `citation_temporal` / `unresolved_queue` の FK を `ON DELETE CASCADE` → **`ON DELETE RESTRICT`**（または NO ACTION）に変更。
- `temporal_eval_event` は現状のまま（NO ACTION + append-only）。
- 母屋 edge を消したい時は、**先に lawtime 側（citation_temporal / unresolved_queue / 必要なら eval のアーカイブ）を明示的に片付けてから**親を消す。

**長所**: 監査痕（特に eval 履歴）が**サイレントに消えない**。法令ドメインの証跡保全に最も安全。3本の挙動が一貫。削除は常に「意図的な操作」になる。
**短所**: 母屋（canonical 層）の保守が lawtime に**結合**する（誤投入 edge を消すのに lawtime 側の掃除が要る）。掃除手順を runbook 化する必要。

### B. 現状維持（混在・暗黙）
`citation_temporal`/`unresolved_queue` は CASCADE のまま、`temporal_eval_event` は NO ACTION+append-only のまま。

**長所**: コード変更ゼロ。「履歴の無い edge は気軽に消せる／履歴のある edge は守られる」は結果的に妥当な線。
**短所**: 挙動が**暗黙**で、読んだ人が「CASCADE だから全部消える」と誤解しやすい。3本の不揃いがレビュー毎に蒸し返される。監査が O1 として名指しした「揃えるべき」指摘に未対応のまま。

### C. 統一 CASCADE（母屋優先・非推奨）
3本とも CASCADE に揃え、`temporal_eval_event` の append-only-on-DELETE 保護を**外して** edge 削除時に eval 履歴も cascade 削除する。

**長所**: 母屋 edge を消せば lawtime 痕跡が**完全に消える**。canonical 層の保守が最も軽い。
**短所**: **eval 監査履歴がサイレントに失われる**。法令時間軸の証跡としては危険。append-only の設計意図を破棄することになる。**法令ドメインでは推奨しない。**

---

## 3. 推奨

**A（統一 RESTRICT／NO ACTION）** を推奨。
理由: lawtime は法令の時間軸**証跡**レイヤであり、`temporal_eval_event` を append-only にした設計意図が
すでに「評価痕は消さない」と宣言している。であれば side-table 側も同じ哲学（RESTRICT）に揃えるのが一貫し、
母屋 edge の削除を「lawtime を先に片付けた上での意図的操作」に限定できる。サイレントなデータ喪失の経路を塞ぐのが
法令用途では最優先。

**A を採る場合の差分**（PHASE D 前に 100 を修正）:
- `citation_temporal.edge_id ... ON DELETE CASCADE` → `ON DELETE RESTRICT`
- `unresolved_queue.edge_id ... ON DELETE CASCADE` → `ON DELETE RESTRICT`
- 母屋 edge 削除の**掃除手順**（lawtime 側を先に消す順序）を runbook §7 に追記。
- gate/smoke は挙動非依存（gate は行の有無を見るだけ）なので、再 smoke で 8 gate 空が維持されることだけ確認。

> どれを採っても **PHASE D（本番 apply）には進まない**。本メモは O1 を確定するだけ。
