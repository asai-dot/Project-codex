# ループ振り返り 時系列ログ(メタループの蓄積)

各シルバー精度向上ループ(およびその他)の閉幕後 RETROSPECTIVE を時系列に積む。

## 命名
`<YYYYMMDD>_<domain>_<stop_kind>_RETROSPECTIVE.md`
例: `20260801_caselink_silver_SUCCESS_RETROSPECTIVE.md`

## 流れ(HEAD_OPS §10 準拠)
1. ループ閉幕 → W-NNN-510(メタ監査 packet)実行
2. RETROSPECTIVE.md 作成(本ディレクトリへ複製)
3. to_gpt/ に GPT メタ監査 REQUEST 投函
4. from_gpt/ で `LOOPMETA_<...>` 戻り
5. notes → HEAD_OPS v0.x に反映 → 次ループ

## 3回ルール
3回ループを回したら、共通改善パターンを抽出して **HEAD_OPS v1.0(汎化版)** へ。
雑誌・法令・文献など他オブジェクトでも使えるよう抽象化する。
