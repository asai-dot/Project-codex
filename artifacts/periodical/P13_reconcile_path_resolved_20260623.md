# P13: 本流反映の経路 — 確定（reconcile関数で構造的に解決）

```yaml
artifact: P13_reconcile_path_resolved
generated_at: 2026-06-23 JST
context: 「issue_stageがaudit only/再ロードで昇格が消えるのでは」という本流反映の懸念に決着。
```

## 前提の確定
- `issues_with_id_staged.jsonl` および issue_stage への投入は **本プロジェクト自身の生成物**
  （owner管理の外部本番パイプラインは存在しない）。リポジトリ内に生成/ロードコードも無し（外部生成物）。
- よって「外部の自動再ロードが昇格を勝手に消す」リスクの主体は無い。

## 解決策：reconcile を1関数に集約
```sql
SELECT staging_periodical.reconcile_issue_ids();
```
- registry / journal_alias / tsuukan_crosswalk / issue_id_resolved（view）から
  issue_stage の issue_id・status を **冪等に再適用**。
- issue_stage が再生成・再ロードされても、**この1コールで全昇格が復元**する。
- 復元の正しさは `resolver_drift=0` で実証済（ロジック＝実体）。
- 現状で実行 → **updated_rows=0**（既に整合）。冪等性を確認。

## 永続化の構造（なぜ消えないか）
| レイヤ | 実体 | 再ロード耐性 |
|---|---|---|
| 真実の源 | journal_registry / alias / crosswalk（別テーブル） | issue_stage再ロードの影響を受けない |
| 導出ロジック | issue_id_resolved（view） | 同上（viewは定義のみ） |
| 復元手段 | reconcile_issue_ids()（関数） | 同上 |
| 適用先 | issue_stage（再生成されうる） | 再ロード後に関数1回で復元 |

→ issue_stage は「揮発してよい適用先」。真実は registry 系に永続し、関数で再投影する設計。

## 運用手順（再ロード時）
1. issue_stage を再ロード（プロジェクトの生成物を投入）。
2. `SELECT staging_periodical.reconcile_issue_ids();` を1回実行。
3. 監査view（false_merge/split/key_collision/tsuukan_monotonic/resolver_drift）が全0を確認。
   - 新誌・新変種が来た場合は `audit_unregistered` に出るので registry/alias を追補→再 reconcile。

## 残（外部一次情報依存・このセッションでは未取得）
- 法と哲学 ISSN `2188-711X` の○×確認（ISSN Portal/出版社）。
- 税経通信2026 の実通号12個（NDL書誌）。
→ いずれも値確定後 registry/crosswalk を更新し reconcile を呼ぶだけで反映。

## 現状
被覆 2,666 / 2,847 = **93.6%**、全監査クリーン、reconcile冪等性確認済。
