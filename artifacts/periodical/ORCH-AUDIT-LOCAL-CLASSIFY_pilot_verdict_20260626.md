# ORCH-AUDIT: ローカル記事種別分類 パイロット受入検査 — 2026-06-26

```yaml
audit: local_article_type_pilot
input: article_type_local_pilot_v0.1.csv (Worker/QEN qwen3:30b, job-5f6705a3, 2000件)
auditor: Cloud Code Web (codex, head) / harness: tools/periodical/audit_article_type.py
verdict: PASS → 全量GO
```

## 結果
- 規格外ラベル: **0**（10種別すべて正規ラベル）。
- 分布: 判例評釈790/その他639/論説161/判例紹介129/解説99/座談会58/書評49/資料46/立法21/連載8。健全（全件その他に倒れていない）。
- 正規表現クロスチェック（公正版: 判決系は判例評釈/判例紹介/資料を相互許容）: **92.2%（928/1006）→ PASS**。
- 残不一致は「最高裁判決を契機とした論説」をQENが論説・論文と判定する等、むしろQEN妥当の境界ケース。

## 教訓（storm事故）
remote-trigger＋watcher競合で classify worktree が約26本乱立しGPUデッドロック。
原因: Mac作業ツリーのgit競合でwatcherがトリガ消費できず60s毎に再launch。
対処: watcher/wake堅牢化(競合自動解除)、storm worktree一掃、全量は単一プロセス直接実行。

## 全量実行
qwen3:30b・HTTP版ドライバ・CHUNK=40・resume(checkpoint)で302,130件を単一プロセス背景実行。
出力 article_type_local_pilot_v0.1.csv(全量)→ 完了後 article_type_local_v0.1.csv へ確定。
完了後 head 再監査（同harness）。判例評釈サブセットは次段 L5(評釈→判例リンク)へ。
