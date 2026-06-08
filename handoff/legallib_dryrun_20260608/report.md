# legallib 接合 ドライラン diff レポート

- 判定総数: 2760
- 書き込み候補 (create + overwrite_simple): 1740

## action 内訳

- blocked_bad_isbn: 95
- create: 215
- defer_staging: 616
- overwrite_simple: 1525
- route_human_review: 309

## 検収ガード

- 誤マージ blocked: 95 件
- human_review 退避: 309 件
- defer_new staging: 616 件
- 変換 warning: 1 件
- 不変条件違反 (保護対象への書き込み): 0 件  ✅ OK

> 非simple (人手/NDL/出版社/PDF目次) は overwrite 候補に入らない = diff 0。
> 上の「不変条件違反」が 0 件であることが検収の機械的証明。
