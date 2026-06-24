# ORCH-AUDIT: L4 記事↔issue_id 接合 受入検査 — 2026-06-24

```yaml
audit: L4_article_join_acceptance
input: artifacts/periodical/article_join_dryrun_v0.1.csv (Worker Claude Code session 675a9ed1 出力)
auditor: Cloud Code Web (codex, head)
harness: tools/periodical/audit_article_join.py（独立再実行）
verdict: PASS → L4接合認定
```

## 受入検査結果（独立実行・全PASS）
| 基準 | 結果 |
|---|---|
| article_collision = 0 | **PASS**（同一article_idの異タイトル衝突なし） |
| 接合被覆 ≥ 95% | **PASS 99.28%**（joined 299,957 / 302,130） |
| 別冊ジュリスト(百選)issue_id衝突 = 0 | **PASS**（百選14,382記事は全て isbn_per_issue＝D2正しく適用） |
| orphan 理由分類済 | **PASS**（authority_unresolved 1,050 / tsuukan_unavailable 1,123） |

## 注記
- `issue_id混在 2件` = 日本国際経済法学会年報＝経済法学会年報（学会名改称・同一誌）が同ISSN同通巻を共有。
  誤接合でなく良性の継続誌。許容。
- orphan 2,173件(0.72%) の主因:
  - `authority_unresolved`(1,050): L3で取得不能だった長尾誌（月刊債権管理682等）由来。受容。
  - `tsuukan_unavailable`(1,123): 通巻算出不能（判例研究513・民事法研究367等）。L3へフィードバックして将来改善余地。

## 認定
**L4 記事↔issue_id 接合を「接合完了」と認定。** 雑誌オブジェクトは L3基盤(99.7%) の上に
L4接合(99.28%) が乗り、記事=作品が号に正しく紐づく状態に到達。
クリティカルパス次段（初出 pacsigny / OCR パイロット L2 → 本文リンク L5）へ進行可能。

## 次アクション
- orphan の `tsuukan_unavailable` 上位（判例研究/民事法研究等）の通巻規則を L3 へフィードバック（軽微・任意）。
- 初出(L4 first_pub, pacsigny) と OCRパイロット(L0-L2) の発注準備（owner GO済・ライセンス確認済）。
