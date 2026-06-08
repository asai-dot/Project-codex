---
description: DD/パイプライン全体の現状を1枚で出す（snapshotを描画し、HTML画面＋要約を返す）
argument-hint: "[snapshot.json のパス（省略可）]"
---

ALO の DD/パイプライン全体の現状を可視化して報告して。これは「観測ダッシュボード」
（runtime_status＝実行・運用状態の軸。artifact lifecycle とは別軸）。

## 手順

1. **地図**は `pipeline/pipeline.json`（固定）。

2. **snapshot を決める**（鮮度の源）。優先順位:
   - 引数 `$ARGUMENTS` にパスが渡っていればそれ。
   - 無ければ `build/pipeline_snapshot.json`（ローカルで直前に採取した最新）。
   - 無ければ `pipeline/pipeline_snapshot.json`（`scripts/dd_collect.command` が
     コミットする正規パス）。
   - それも無ければ、リポジトリにコミット済みの `*pipeline_snapshot*.json` を探す。
   - **どれも無ければ収集にフォールバック**（下の 3b）。

3a. **snapshot がある場合**（収集しない＝速い・どこでも可）:
   ```bash
   python scripts/pipeline_dashboard.py --manifest pipeline/pipeline.json \
     --snapshot <snapshot> \
     --out-md build/dashboard.md --out-html build/dashboard.html
   ```

3b. **snapshot が無い場合**（このリポジトリ checkout だけを一発収集）:
   ```bash
   python scripts/pipeline_dashboard.py --manifest pipeline/pipeline.json \
     --root repo=. --out-md build/dashboard.md --out-html build/dashboard.html
   ```
   この場合 `bookdx`/`alo`（Box同期・~/alo-ai）の root が無いので、それらのステージは
   `todo`/`blocked` に倒れる。**「最新の実状態は Mac で probe した snapshot が要る」**
   ことを必ず断り書きする（このコマンドの値はあくまで暫定）。

4. 生成した `build/dashboard.md` の **「サマリ」と「要注目」**（戻り待ち / 依存待ちで入れない /
   いま入れる）セクションを抜き出してチャットに表示する。`⚠ manifest エラー` バナーや
   `⚠ 重複 request_id` セクションがあれば、それも必ず併せて伝える。

5. `build/dashboard.html` を **SendUserFile で渡して**ブラウザで開けるようにする。

6. 冒頭に **「いつ時点の現状か」**を必ず明示する（snapshot の `generated_at_jst` /
   `probe_version` / roots）。snapshot が古ければ「N時間前のスナップショット」と添える。

## 注意
- read-only の観測のみ。Box/Salesforce/実DB への書き込みや、accepted/canonical 昇格は
  この合言葉では一切しない。
- snapshot を最新化したい時は Mac 側で
  `python scripts/pipeline_probe.py --manifest pipeline/pipeline.json --root bookdx=<Box> --root alo=$HOME/alo-ai --root repo=. --out build/pipeline_snapshot.json`
  を走らせて snapshot をコミットする運用（このコマンドはそれを描画するだけ）。
