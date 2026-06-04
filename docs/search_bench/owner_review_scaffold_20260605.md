# A1 Owner Review Scaffold (asof 20260605)

> これは gold ではない。後日 owner が監修値を入れるための**空欄台紙**。owner_* 欄は Stage1 では空のまま（本スクリプトは埋めない）。
> observed_* は観測値（canonical term は非PII）。query は report-safe（PIIリスク行は抑制済）。noise除外。

| consultation_hash | inferred_cat | query_text_report_safe | observed_terms | raw_toc | raw_rec | outcome | owner_review_status_blank | owner_comment_blank | owner_gold_later_blank |
|---|---|---|---|--:|--:|---|---|---|---|
| 6721f60977f3 | 後見 | [区切り無・表示抑制] | 後見人, 財産(stop) | 0 | 0 | non_stop_term_hit |  |  |  |
| bc3d63c1eae5 | 一般民事 | [区切り無・表示抑制] | 請求(stop) | 20 | 0 | stoplist_only_hit |  |  |  |
| ca33bb9b74c7 | 一般民事 | [区切り無・表示抑制] | 請求(stop) | 20 | 0 | stoplist_only_hit |  |  |  |
| 6501cfd92379 | 一般民事 | [区切り無・表示抑制] | 請求(stop) | 20 | 0 | stoplist_only_hit |  |  |  |
| 02994e52a7c4 | 一般民事 | [区切り無・表示抑制] | 請求(stop) | 0 | 0 | stoplist_only_hit |  |  |  |
| 26aa3469fdab | 損害賠償（交通） | 損害賠償請求事件(交通事故) | 請求(stop) | 0 | 0 | stoplist_only_hit |  |  |  |
| afbc6ba6a92a | (未分類) | [区切り無・表示抑制] | — | 3 | 2 | raw_probe_hit_but_no_term_hit |  |  |  |
| d8ee553c1dd4 | 損害賠償（交通） | [区切り無・表示抑制] | 請求(stop) | 1 | 0 | stoplist_only_hit |  |  |  |
| aa1ceab3bf99 | (未分類) | [区切り無・表示抑制] | 請求(stop) | 0 | 0 | stoplist_only_hit |  |  |  |
| 0e3b174921fb | 廃業支援（法的整理） | [区切り無・表示抑制] | — | 0 | 0 | no_term_no_raw_probe |  |  |  |
| 1404a8a6ccaa | 廃業支援（法的整理） | [区切り無・表示抑制] | — | 0 | 0 | no_term_no_raw_probe |  |  |  |
| ac6c0f541f75 | (未分類) | [区切り無・表示抑制] | 事業(stop) | 0 | 0 | stoplist_only_hit |  |  |  |
| b2bce894cd4e | 破産管財事件 | [区切り無・表示抑制] | — | 2 | 0 | raw_probe_hit_but_no_term_hit |  |  |  |
| bc477c6d5067 | (未分類) | [区切り無・表示抑制] | 事業(stop) | 0 | 0 | stoplist_only_hit |  |  |  |
| 8bf66a2adaee | 廃業支援（法的整理） | [区切り無・表示抑制] | — | 0 | 0 | no_term_no_raw_probe |  |  |  |
| f1093181b852 | 一般民事 | [区切り無・表示抑制] | 請求(stop) | 20 | 0 | stoplist_only_hit |  |  |  |
| 7ae9da2b312b | (未分類) | [区切り無・表示抑制] | — | 0 | 0 | no_term_no_raw_probe |  |  |  |
| d8ae40df84c1 | 一般民事 | 損害賠償請求事件 交通事故弁護士特約案件 | 請求(stop) | 20 | 0 | stoplist_only_hit |  |  |  |
| b6968bb3f991 | 離婚 | 離婚事件 離婚事件 | — | 13 | 22 | raw_probe_hit_but_no_term_hit |  |  |  |
| ed36c7e8eabe | (未分類) | [PIIのため表示抑制] | 会社(stop), 株式(stop) | 0 | 0 | stoplist_only_hit |  |  |  |
| b0e147d5a2cd | (未分類) | 著作権侵害事件 著作権侵害　イラスト | — | 4 | 0 | raw_probe_hit_but_no_term_hit |  |  |  |
| a9fe73396143 | 契約法務 | 法律相談 | — | 0 | 0 | stoplist_only_hit |  |  |  |
| 54aaea4c36e6 | 離婚 | 離婚予備相談 離婚相談？ | — | 0 | 0 | no_term_no_raw_probe |  |  |  |
| 7e990cb5a15b | (未分類) | 株主総会取締役会対応 | — | 0 | 0 | stoplist_only_hit |  |  |  |
| bfb7895d159e | 契約法務 | 法律相談 | — | 0 | 0 | stoplist_only_hit |  |  |  |
| d9df604fe6fb | (未分類) | [区切り無・表示抑制] 谷板金 事業承継・再生 | 事業(stop) | 0 | 0 | stoplist_only_hit |  |  |  |
| 77519de113e1 | (未分類) | [PIIのため表示抑制] | 会社(stop), 株式(stop) | 0 | 0 | stoplist_only_hit |  |  |  |
| 5170d88b9307 | 契約法務 | 企業法務 | — | 0 | 0 | no_term_no_raw_probe |  |  |  |
| 0cb5a3839290 | (未分類) | [区切り無・表示抑制] | — | 0 | 0 | no_term_no_raw_probe |  |  |  |
| d12baf1e39b8 | (未分類) | [PIIのため表示抑制] | 会社(stop) | 0 | 0 | stoplist_only_hit |  |  |  |
| 23289a8efce6 | 契約法務 | [区切り無・表示抑制] 契約書レビュー | — | 0 | 0 | no_term_no_raw_probe |  |  |  |
| 50ab3274fc9c | 損害賠償（交通） | 交通事故 [PIIのため表示抑制] | — | 149 | 185 | raw_probe_hit_but_no_term_hit |  |  |  |
| 98cee4135531 | (未分類) | [PIIのため表示抑制] | 会社(stop), 株式(stop) | 0 | 0 | stoplist_only_hit |  |  |  |
| 2bd7124ae5ac | (未分類) | [PIIのため表示抑制] | 会社(stop), 株式(stop) | 0 | 0 | stoplist_only_hit |  |  |  |
| e475331f6aa2 | 債務整理 | 債務整理 大亀さん＿債務整理 | — | 27 | 9 | raw_probe_hit_but_no_term_hit |  |  |  |
| 3c7221a66d89 | 契約法務 | ライセンス契約書レビュー [PIIのため表示抑制] | 物(stop) | 0 | 0 | stoplist_only_hit |  |  |  |
| 7f365d609626 | (未分類) | 不当利得返還請求 | 請求(stop) | 58 | 0 | stoplist_only_hit |  |  |  |
| 0e753c51b25a | 一般民事 | 損害賠償請求事件 [PIIのため表示抑制] | 請求(stop) | 20 | 0 | stoplist_only_hit |  |  |  |
| 76cdd7e86443 | 離婚 | 離婚等請求事件 | 請求(stop) | 0 | 0 | stoplist_only_hit |  |  |  |
| c253a04ea8c4 | 契約法務 | 法律相談 | — | 0 | 0 | stoplist_only_hit |  |  |  |
| c85234510574 | 不動産 | 不動産売買 | 不動産 | 53 | 5 | non_stop_term_hit |  |  |  |
| da7a1a9b6614 | 債務整理 | 債務整理 [PIIのため表示抑制] | 会社(stop), 株式(stop) | 27 | 9 | stoplist_only_hit |  |  |  |
| 3bb086f7dd38 | (未分類) | 退店金支払い請求 | 支払(stop), 請求(stop) | 0 | 0 | stoplist_only_hit |  |  |  |
| 1eaa01ed8416 | (未分類) | 事業清算・保証解除 | 事業(stop) | 0 | 0 | stoplist_only_hit |  |  |  |
| 14563fea5a80 | 契約法務 | 新事業・契約書作成 | 事業(stop) | 0 | 0 | stoplist_only_hit |  |  |  |
| eeb54bdb8285 | (未分類) | 金銭トラブル | — | 2 | 0 | raw_probe_hit_but_no_term_hit |  |  |  |
| c51996348635 | (未分類) | [PIIのため表示抑制] | 会社(stop), 株式(stop) | 0 | 0 | stoplist_only_hit |  |  |  |
| dfea64f4e260 | (未分類) | [区切り無・表示抑制] | — | 0 | 0 | no_term_no_raw_probe |  |  |  |
| 2d8d6507af1f | (未分類) | [PIIのため表示抑制] | 会社(stop), 株式(stop) | 0 | 0 | stoplist_only_hit |  |  |  |
| 5d9d3a0ff9d2 | 損害賠償（交通） | 交通事故 | — | 149 | 185 | raw_probe_hit_but_no_term_hit |  |  |  |
| 4bba64e8c5fd | M&A支援 | M&A | — | 224 | 117 | raw_probe_hit_but_no_term_hit |  |  |  |
| 5fa2c9e6b3fc | (未分類) | [PIIのため表示抑制] | 会社(stop), 株式(stop) | 0 | 0 | stoplist_only_hit |  |  |  |
| 8f5a791f0467 | 相続 | 相続 | — | 781 | 288 | raw_probe_hit_but_no_term_hit |  |  |  |
| 68413e8847f9 | (未分類) | [PIIのため表示抑制] | 会社(stop), 株式(stop) | 0 | 0 | stoplist_only_hit |  |  |  |
| 75f1f6342a7a | (未分類) | [PIIのため表示抑制] | 会社(stop), 株式(stop) | 0 | 0 | stoplist_only_hit |  |  |  |
| 7936f2948188 | (未分類) | [PIIのため表示抑制] | 会社(stop), 株式(stop) | 0 | 0 | stoplist_only_hit |  |  |  |
| bc7ec5783af5 | (未分類) | [PIIのため表示抑制] | 会社(stop), 株式(stop) | 0 | 0 | stoplist_only_hit |  |  |  |
| 873703c00421 | (未分類) | [PIIのため表示抑制] | 会社(stop), 株式(stop) | 0 | 0 | stoplist_only_hit |  |  |  |
| dd20b0bf13b3 | (未分類) | [区切り無・表示抑制] | — | 0 | 0 | no_term_no_raw_probe |  |  |  |
| 81eb42636828 | M&A支援 | 事業譲渡契約 | 事業(stop) | 18 | 0 | stoplist_only_hit |  |  |  |
| f3205e2bf808 | (未分類) | [PIIのため表示抑制] | 会社(stop) | 0 | 0 | stoplist_only_hit |  |  |  |
| 72fd256e0cf2 | 損害賠償（交通） | 道路交通法違反 | — | 15 | 0 | raw_probe_hit_but_no_term_hit |  |  |  |
| 18c63e95a62e | 契約法務 | 法律相談 | — | 0 | 0 | stoplist_only_hit |  |  |  |
| dfb98f3ad24e | 契約法務 | 法律相談 | — | 0 | 0 | stoplist_only_hit |  |  |  |
| cd64f1f3f535 | 損害賠償（交通） | 交通事故 | — | 149 | 185 | raw_probe_hit_but_no_term_hit |  |  |  |
| 60e144619eaa | (未分類) | 傷害事件 | — | 13 | 0 | raw_probe_hit_but_no_term_hit |  |  |  |
| 1885d3f47c60 | 契約法務 | 法律相談 | — | 0 | 0 | stoplist_only_hit |  |  |  |
| 4b5ee5aa752a | 契約法務 | 法律相談 | — | 0 | 0 | stoplist_only_hit |  |  |  |
| e9ca6b5d35ec | (未分類) | 少数株主売却交渉事件 | — | 0 | 0 | stoplist_only_hit |  |  |  |
| 44ec79df7172 | (未分類) | 発信者情報開示請求事件 発信者情報開示請求事件 | 請求(stop) | 1 | 0 | stoplist_only_hit |  |  |  |
| e8a79705fe08 | 損害賠償（交通） | 交通事故 | — | 149 | 185 | raw_probe_hit_but_no_term_hit |  |  |  |
| a11ad0501a13 | 契約法務 | 法律相談 | — | 0 | 0 | stoplist_only_hit |  |  |  |
| d11ee0dfc622 | 契約法務 | 少数株主対応 法律相談 | — | 0 | 0 | stoplist_only_hit |  |  |  |
| 6a9740c8e777 | 相続 | [PIIのため表示抑制] | — | 2 | 5 | raw_probe_hit_but_no_term_hit |  |  |  |
| 79309fa81bae | (未分類) | 交通事故相談 | — | 3 | 0 | raw_probe_hit_but_no_term_hit |  |  |  |
| 35a5abefc733 | (未分類) | 当番弁護 不同意性交渉（当番弁護） | — | 9 | 0 | raw_probe_hit_but_no_term_hit |  |  |  |
| f3e9c3911a4e | 相続 | 相続放棄 相続放棄相談 | — | 135 | 8 | stoplist_only_hit |  |  |  |
| d3b71a313bda | (未分類) | 事業清算 [PIIのため表示抑制] | 事業(stop), 会社(stop), 株式(stop) | 0 | 0 | stoplist_only_hit |  |  |  |
| 1f87618c762a | 廃業支援（私的整理） | 私的整理 [PIIのため表示抑制] | 会社(stop), 株式(stop) | 46 | 11 | stoplist_only_hit |  |  |  |
| d59c335bf87f | (未分類) | [PIIのため表示抑制] [PIIのため表示抑制] | 会社(stop) | 3 | 0 | stoplist_only_hit |  |  |  |
| a8a82d421358 | (未分類) | [PIIのため表示抑制] | 会社(stop), 株式(stop) | 0 | 0 | stoplist_only_hit |  |  |  |
| bfbe2f40879e | (未分類) | 欠陥住宅京都ネット相談 [PIIのため表示抑制] | — | 0 | 0 | no_term_no_raw_probe |  |  |  |
| f2c3c51737dc | 事業再生（私的整理） | 法人事業再生計画策定支援 [PIIのため表示抑制] | 事業(stop), 会社(stop), 再生計画, 株式(stop), 法人(stop) | 0 | 0 | non_stop_term_hit |  |  |  |
| 06531cb3fd02 | (未分類) | 詐欺被害事件 | — | 0 | 0 | no_term_no_raw_probe |  |  |  |
| a47f842e9e7f | (未分類) | 詐欺被害事件 | — | 0 | 0 | no_term_no_raw_probe |  |  |  |
| 6d48d6ec04a4 | 契約法務 | ECサイト契約書相談 [PIIのため表示抑制] | 会社(stop), 株式(stop) | 0 | 0 | stoplist_only_hit |  |  |  |
| 58cffb1c4fe1 | M&A支援 | 事業承継相談 [PIIのため表示抑制] | 事業(stop), 会社(stop), 株式(stop) | 0 | 4 | stoplist_only_hit |  |  |  |
| a3331bce5b85 | (未分類) | 詐欺被害事件 | — | 0 | 0 | no_term_no_raw_probe |  |  |  |
| 708b5addc849 | 一般民事 | 債権回収 | — | 68 | 18 | raw_probe_hit_but_no_term_hit |  |  |  |
| 5c77d5aaebf6 | (未分類) | 詐欺被害事件 [PIIのため表示抑制] | — | 0 | 0 | no_term_no_raw_probe |  |  |  |
| c597a9534d51 | 損害賠償（交通） | 損害賠償請求事件(交通事故) | 請求(stop) | 0 | 0 | stoplist_only_hit |  |  |  |
| 57e16e42c6d4 | (未分類) | 債権回収 [PIIのため表示抑制] | 会社(stop), 株式(stop) | 68 | 18 | stoplist_only_hit |  |  |  |
| 6b09034d1f38 | 廃業支援（法的整理） | 自己破産 [PIIのため表示抑制] | — | 25 | 0 | raw_probe_hit_but_no_term_hit |  |  |  |
| 4671eb7f2700 | (未分類) | 慰謝料請求 [PIIのため表示抑制] | 請求(stop) | 72 | 2 | stoplist_only_hit |  |  |  |
| 5f6deff3491e | 相続 | 法テラス [PIIのため表示抑制] | — | 0 | 0 | no_term_no_raw_probe |  |  |  |
| c7bb38637483 | (未分類) | M&A | — | 224 | 117 | raw_probe_hit_but_no_term_hit |  |  |  |
| bd22889fb126 | (未分類) | 詐欺被害事件 | — | 0 | 0 | no_term_no_raw_probe |  |  |  |
| d1a101e804c1 | 損害賠償（交通） | 交通事故相談 | — | 3 | 0 | raw_probe_hit_but_no_term_hit |  |  |  |
| f0e6e6a6e4be | 相続 | 相続放棄 [PIIのため表示抑制] | — | 135 | 8 | stoplist_only_hit |  |  |  |
| f4bf6baf00a7 | (未分類) | 情報商材被害相談 | — | 0 | 0 | no_term_no_raw_probe |  |  |  |
| 0ff72c63e65a | 破産管財事件 | 破産管財人事件 | 破産管財人 | 1 | 0 | non_stop_term_hit |  |  |  |
| 5eb52e23d11d | 債務整理 | 債務整理相談 [PIIのため表示抑制] | 会社(stop), 株式(stop) | 0 | 0 | stoplist_only_hit |  |  |  |
| cb3c08a379bf | (未分類) | 大麻取締法違反 [PIIのため表示抑制] | — | 1 | 0 | raw_probe_hit_but_no_term_hit |  |  |  |
| ffbec64b0885 | (未分類) | 当番弁護 [PIIのため表示抑制] | — | 9 | 0 | raw_probe_hit_but_no_term_hit |  |  |  |
| 6cc9e1491057 | (未分類) | 情報商材被害相談 | — | 0 | 0 | no_term_no_raw_probe |  |  |  |
| 6fd2955308df | 契約法務 | 継続的契約の解消 かね正グループ会社
金属製のパレットを製造しているメーカー
納入先のワコーパレットから取引契約の解除通知が届いた。
継続的供給契約の解除 | 会社(stop) | 7 | 0 | stoplist_only_hit |  |  |  |
| 0e762ab04eeb | 一般民事 | 売掛金回収 [PIIのため表示抑制] | 会社(stop), 株式(stop) | 8 | 2 | stoplist_only_hit |  |  |  |
| 54b1c50d9f79 | (未分類) | 損害賠償請求法律相談 | 請求(stop) | 0 | 0 | stoplist_only_hit |  |  |  |
| 5225ca43f33d | (未分類) | 詐欺被害事件 | — | 0 | 0 | no_term_no_raw_probe |  |  |  |
| 6c86dd73d008 | 債務整理 | 債務整理相談 | — | 0 | 0 | no_term_no_raw_probe |  |  |  |
| 6544cdc67e8b | (未分類) | 詐欺被害事件 [PIIのため表示抑制] | — | 0 | 0 | no_term_no_raw_probe |  |  |  |
| c13d4a8573e6 | (未分類) | ストーカー相談 [PIIのため表示抑制] | — | 0 | 0 | no_term_no_raw_probe |  |  |  |
| 8602e668ec49 | (未分類) | 相談 | — | 0 | 0 | no_term_no_raw_probe |  |  |  |
| b3c10b9b03b0 | (未分類) | 詐欺被害事件 [PIIのため表示抑制] | — | 0 | 0 | no_term_no_raw_probe |  |  |  |
| d75d001765c0 | 相続 | 相続相談 [PIIのため表示抑制] | — | 2 | 5 | raw_probe_hit_but_no_term_hit |  |  |  |
| 19a2536e01d6 | (未分類) | 弁護士照会対応相談 [PIIのため表示抑制] | 会社(stop), 株式(stop) | 0 | 0 | stoplist_only_hit |  |  |  |
| 8f8a3d63ea0f | 相続 | 不動産相続相談 [PIIのため表示抑制] | 不動産 | 0 | 1 | non_stop_term_hit |  |  |  |
| 97e74e21292d | 一般民事 | 損害賠償請求事件 | 請求(stop) | 20 | 0 | stoplist_only_hit |  |  |  |
| f2db574f2d15 | (未分類) | 詐欺被害 [PIIのため表示抑制] | — | 5 | 0 | raw_probe_hit_but_no_term_hit |  |  |  |
| 41527c52dc68 | 債務整理 | 債務整理 [PIIのため表示抑制] | — | 27 | 9 | raw_probe_hit_but_no_term_hit |  |  |  |
| bd1ad74b7cea | 債務整理 | 債務整理 [PIIのため表示抑制] | — | 27 | 9 | raw_probe_hit_but_no_term_hit |  |  |  |
| 19ae8b9e14a2 | 契約法務 | 法律相談 | — | 0 | 0 | stoplist_only_hit |  |  |  |
| 4b04486b45b4 | (未分類) | 京都情報商材被害対策弁護団相談案件 | — | 0 | 0 | no_term_no_raw_probe |  |  |  |
| 7c416bbc5695 | 契約法務 | 企業法務 [PIIのため表示抑制] | — | 0 | 0 | no_term_no_raw_probe |  |  |  |
| 4a71b261af25 | (未分類) | 欠陥住宅京都ネット相談 [PIIのため表示抑制] | — | 0 | 0 | no_term_no_raw_probe |  |  |  |
| 0f1e8b79e889 | (未分類) | 詐欺被害事件 [PIIのため表示抑制] | — | 0 | 0 | no_term_no_raw_probe |  |  |  |
| 01da0116489d | 相続 | 相続相談 [PIIのため表示抑制] | — | 2 | 5 | raw_probe_hit_but_no_term_hit |  |  |  |
| 3c98f5196038 | 相続 | 相続相談 [PIIのため表示抑制] | — | 2 | 5 | raw_probe_hit_but_no_term_hit |  |  |  |
| 163aa957c12c | 相続 | 相続相談 [PIIのため表示抑制] | — | 2 | 5 | raw_probe_hit_but_no_term_hit |  |  |  |
| 8d569b75c0e5 | 相続 | 相続相談 [PIIのため表示抑制] | — | 2 | 5 | raw_probe_hit_but_no_term_hit |  |  |  |
| bbf392ed053d | 刑事 | 薬機法違反 [PIIのため表示抑制] | — | 3 | 0 | raw_probe_hit_but_no_term_hit |  |  |  |
| 9b09104b7281 | (未分類) | 暴行 [PIIのため表示抑制] | — | 111 | 2 | raw_probe_hit_but_no_term_hit |  |  |  |
| 616f50c6ce35 | 債務整理 | 債務整理 [PIIのため表示抑制] | — | 27 | 9 | raw_probe_hit_but_no_term_hit |  |  |  |
| 6ca59b2b6995 | M&A支援 | M&A | — | 224 | 117 | raw_probe_hit_but_no_term_hit |  |  |  |
| 382299f481dc | 契約法務 | 法律相談 | — | 0 | 0 | stoplist_only_hit |  |  |  |
| 3883970d1b59 | (未分類) | [PIIのため表示抑制] [PIIのため表示抑制] | 会社(stop), 株式(stop) | 0 | 0 | stoplist_only_hit |  |  |  |
| ce960c7c215a | 債務整理 | 債務整理 [PIIのため表示抑制] | — | 27 | 9 | raw_probe_hit_but_no_term_hit |  |  |  |
| 0fd012240113 | 債務整理 | 債務整理 [PIIのため表示抑制] | — | 27 | 9 | raw_probe_hit_but_no_term_hit |  |  |  |
| 92f72da9f841 | (未分類) | 住宅ローン抵当権相談 [PIIのため表示抑制] | — | 0 | 0 | no_term_no_raw_probe |  |  |  |
| df71e6870e64 | 事業再生（法的整理） | 民事再生スポンサー支援 | — | 0 | 0 | no_term_no_raw_probe |  |  |  |
| fdc80a920a13 | (未分類) | 任意後見監督人 | 後見監督人 | 36 | 0 | non_stop_term_hit |  |  |  |
| 505633220b2d | 相続 | 相続放棄相談 | — | 0 | 0 | stoplist_only_hit |  |  |  |
| 068e019ee60f | (未分類) | 損害賠償等請求事件 [PIIのため表示抑制] | 請求(stop) | 0 | 0 | stoplist_only_hit |  |  |  |
| f529466b3e58 | 相続 | 相続相談 [PIIのため表示抑制] | — | 2 | 5 | raw_probe_hit_but_no_term_hit |  |  |  |
| fac39c43c35a | (未分類) | 傷害事件 [PIIのため表示抑制] | — | 13 | 0 | raw_probe_hit_but_no_term_hit |  |  |  |
| b5d113f8e042 | 損害賠償（交通） | 交通事故 | — | 149 | 185 | raw_probe_hit_but_no_term_hit |  |  |  |
| 061d50fb5679 | M&A支援 | 「ごはん日和」事業買取スキーム [PIIのため表示抑制] | 事業(stop) | 0 | 0 | stoplist_only_hit |  |  |  |
| 8f67569bbd6b | 債務整理 | 債務整理 | — | 27 | 9 | raw_probe_hit_but_no_term_hit |  |  |  |
| 67c505a559b3 | 契約法務 | 企業法務 | — | 0 | 0 | no_term_no_raw_probe |  |  |  |
| c0c37d9d96e1 | 契約法務 | 法律相談 [PIIのため表示抑制] | 会社(stop), 株式(stop) | 0 | 0 | stoplist_only_hit |  |  |  |
| 8acc9de325ad | 刑事 | 住居侵入・窃盗未遂事件 [PIIのため表示抑制] | — | 1 | 0 | raw_probe_hit_but_no_term_hit |  |  |  |
| 2a55f5ac7e4a | 債務整理 | 債務整理相談 | — | 0 | 0 | no_term_no_raw_probe |  |  |  |
| 5965c022a935 | 債務整理 | 債務整理相談 | — | 0 | 0 | no_term_no_raw_probe |  |  |  |
| 50dbb398efc9 | (未分類) | 生命・身体犯 [PIIのため表示抑制] | — | 0 | 0 | no_term_no_raw_probe |  |  |  |
| 7dc1cfade99d | M&A支援 | M&Aバイサイド支援 [PIIのため表示抑制] | — | 0 | 0 | no_term_no_raw_probe |  |  |  |
| 27e7c69dbb2c | 廃業支援（法的整理） | M&A(売り手側廃業支援) | — | 0 | 0 | no_term_no_raw_probe |  |  |  |
| c909303294e0 | (未分類) | 労務相談 | — | 0 | 0 | no_term_no_raw_probe |  |  |  |
| a23faec536c5 | 相続 | 相続相談 [PIIのため表示抑制] | — | 2 | 5 | raw_probe_hit_but_no_term_hit |  |  |  |
| ad3b6364f6f0 | (未分類) | パワハラ相談 [PIIのため表示抑制] | — | 5 | 0 | raw_probe_hit_but_no_term_hit |  |  |  |
| 1c5b207b3d42 | 債務整理 | 債務整理 [PIIのため表示抑制] | — | 27 | 9 | raw_probe_hit_but_no_term_hit |  |  |  |
| bea3909154e0 | 契約法務 | 法律相談 | — | 0 | 0 | stoplist_only_hit |  |  |  |
| dadd29eb8df5 | 契約法務 | 法律相談 | — | 0 | 0 | stoplist_only_hit |  |  |  |
| a7c6c9d55593 | (未分類) | 傷害 [PIIのため表示抑制] | — | 143 | 6 | raw_probe_hit_but_no_term_hit |  |  |  |
| 2ac3d40e367d | (未分類) | 事業整理相談 | 事業(stop) | 0 | 0 | stoplist_only_hit |  |  |  |
| 825350dc72e0 | (未分類) | 損害賠償請求事件 | 請求(stop) | 20 | 0 | stoplist_only_hit |  |  |  |
| 856e3d96abc5 | 廃業支援（私的整理） | 経営者保証ガイドライン | — | 12 | 7 | raw_probe_hit_but_no_term_hit |  |  |  |
| 793b82eae6f2 | (未分類) | 経営相談 [PIIのため表示抑制] | 会社(stop), 株式(stop) | 0 | 0 | stoplist_only_hit |  |  |  |
| 68d3aad9be57 | 契約法務 | 離縁相談 [PIIのため表示抑制] | — | 0 | 0 | no_term_no_raw_probe |  |  |  |
| 9062dcc9eb58 | 契約法務 | 金銭貸借相談 [PIIのため表示抑制] | — | 0 | 0 | no_term_no_raw_probe |  |  |  |
| b0e47dcb0cd7 | (未分類) | 任意整理 [PIIのため表示抑制] | — | 13 | 0 | raw_probe_hit_but_no_term_hit |  |  |  |
| 3c00998ce91b | (未分類) | パワハラ相談 [PIIのため表示抑制] | — | 5 | 0 | raw_probe_hit_but_no_term_hit |  |  |  |
| 19443a7fca0b | (未分類) | 建造物侵入・窃盗未遂 [PIIのため表示抑制] | 物(stop) | 0 | 0 | stoplist_only_hit |  |  |  |
| a586ede0665c | 損害賠償（交通） | 交通事故 | — | 149 | 185 | raw_probe_hit_but_no_term_hit |  |  |  |
| b059baed638c | 損害賠償（交通） | 交通事故 | — | 149 | 185 | raw_probe_hit_but_no_term_hit |  |  |  |
| f1344ce356b5 | 後見 | あっせん補助 [PIIのため表示抑制] | — | 0 | 0 | no_term_no_raw_probe |  |  |  |
| 76d32b066705 | 債務整理 | クレジット・サラ金法律相談 [PIIのため表示抑制] | — | 0 | 0 | stoplist_only_hit |  |  |  |
| f861740d573b | 債務整理 | クレジット・サラ金法律相談 [PIIのため表示抑制] | — | 0 | 0 | stoplist_only_hit |  |  |  |
| 78a66b13ee0a | 債務整理 | クレジット・サラ金法律相談 [PIIのため表示抑制] | — | 0 | 0 | stoplist_only_hit |  |  |  |
| 79b5a5262324 | 債務整理 | クレジット・サラ金法律相談 [PIIのため表示抑制] | — | 0 | 0 | stoplist_only_hit |  |  |  |
| 166e8d2e4c97 | 債務整理 | クレジット・サラ金法律相談 [PIIのため表示抑制] | — | 0 | 0 | stoplist_only_hit |  |  |  |
| f16ea36ec84e | 債務整理 | クレジット・サラ金法律相談 [PIIのため表示抑制] | — | 0 | 0 | stoplist_only_hit |  |  |  |
| e7fcff328a54 | 廃業支援（私的整理） | 事業再生(私的整理) | 事業(stop) | 0 | 0 | stoplist_only_hit |  |  |  |
| 8b712424d412 | M&A支援 | [区切り無・表示抑制] | — | 0 | 0 | no_term_no_raw_probe |  |  |  |
| 00680ed1d01d | 労働 | 団体交渉 | — | 88 | 0 | raw_probe_hit_but_no_term_hit |  |  |  |
| 16ec6ac16e44 | 離婚 | 養育費請求事件 | 請求(stop) | 1 | 0 | stoplist_only_hit |  |  |  |
| 4fc0f665b54b | 契約法務 | 法律相談 [PIIのため表示抑制] | — | 0 | 0 | stoplist_only_hit |  |  |  |
| 572ed462868f | 契約法務 | 法律相談 [PIIのため表示抑制] | — | 0 | 0 | stoplist_only_hit |  |  |  |
| 2e4ab5d3d8c5 | 損害賠償（交通） | 損害賠償請求事件(交通事故) | 請求(stop) | 0 | 0 | stoplist_only_hit |  |  |  |
| 9f8e25771825 | 一般民事 | 損害賠償請求事件 [PIIのため表示抑制] | 請求(stop) | 20 | 0 | stoplist_only_hit |  |  |  |
| 546bdc4efc17 | (未分類) | [区切り無・表示抑制] | — | 0 | 0 | no_term_no_raw_probe |  |  |  |
| fd6f5d06adaf | (未分類) | 欠陥住宅京都ネット相談 [PIIのため表示抑制] | — | 0 | 0 | no_term_no_raw_probe |  |  |  |
| 79e6dcc6e881 | (未分類) | ひまわりホットダイヤル [PIIのため表示抑制] | 会社(stop) | 0 | 0 | stoplist_only_hit |  |  |  |
| 5af244ec3233 | 債務整理 | 債務整理相談 | — | 0 | 0 | no_term_no_raw_probe |  |  |  |
| 428849494c59 | 契約法務 | 法律相談 | — | 0 | 0 | stoplist_only_hit |  |  |  |
| 52fade7c1ed5 | (未分類) | 従業員対応 [PIIのため表示抑制] | 会社(stop), 株式(stop) | 0 | 0 | stoplist_only_hit |  |  |  |
| 9db74fa0f58a | 廃業支援（法的整理） | 廃業支援 | — | 3 | 2 | raw_probe_hit_but_no_term_hit |  |  |  |
| 5820998b84c1 | 廃業支援（法的整理） | 廃業支援 | — | 3 | 2 | raw_probe_hit_but_no_term_hit |  |  |  |
| 058eee9e5b21 | (未分類) | 犯罪被害者相談 | 被害者 | 0 | 0 | non_stop_term_hit |  |  |  |
| 88ad83ed6b47 | (未分類) | 当番弁護(詐欺事件) | — | 0 | 0 | no_term_no_raw_probe |  |  |  |
| 353b42d0cf2b | (未分類) | 犯罪被害者相談 | 被害者 | 0 | 0 | non_stop_term_hit |  |  |  |
| 3874a450d7d0 | (未分類) | 宿泊施設運営相談 き＿キラエリ・モアテス＿宿泊施設運営相談 | — | 0 | 0 | stoplist_only_hit |  |  |  |
| 51f4bb088b08 | (未分類) | 退職・損害賠償対応 か＿門泰之＿退職・損害賠償対応 | — | 0 | 0 | no_term_no_raw_probe |  |  |  |
| 7f2904b8a8aa | (未分類) | 山中司法書士 事業承継案件 山中司法書士 事業承継案件 | 事業(stop) | 0 | 0 | stoplist_only_hit |  |  |  |
| 9dea5d647d0d | 契約法務 | 企業法務 | — | 0 | 0 | no_term_no_raw_probe |  |  |  |
| 60ea3a785ede | 契約法務 | 契約書レビュー | — | 9 | 2 | raw_probe_hit_but_no_term_hit |  |  |  |
| 0169e1a7943e | 一般民事 | システム開発費損害賠償請求 [PIIのため表示抑制] | 請求(stop) | 0 | 0 | stoplist_only_hit |  |  |  |
| 07617c61eff9 | 債務整理 | 債務整理相談 [PIIのため表示抑制] | — | 0 | 0 | no_term_no_raw_probe |  |  |  |
| d492433119f7 | (未分類) | 欠陥住宅京都ネット [PIIのため表示抑制] | — | 0 | 0 | no_term_no_raw_probe |  |  |  |
| 9a151b1421c4 | 一般民事 | 和解あっせん申立 [PIIのため表示抑制] | — | 0 | 0 | no_term_no_raw_probe |  |  |  |
| 843c7e488988 | (未分類) | 債務整理相談 [PIIのため表示抑制] | — | 0 | 0 | no_term_no_raw_probe |  |  |  |
| 6c8b2975c005 | (未分類) | 債務整理相談 | — | 0 | 0 | no_term_no_raw_probe |  |  |  |
| 1b66e85b6fd5 | (未分類) | 経営改善支援 | — | 0 | 1 | raw_probe_hit_but_no_term_hit |  |  |  |
| a44b0f9dea96 | (未分類) | 廃業支援 [PIIのため表示抑制] | 会社(stop), 物(stop) | 3 | 2 | stoplist_only_hit |  |  |  |
| 3e52ea46c017 | (未分類) | 相続相談 | — | 2 | 5 | raw_probe_hit_but_no_term_hit |  |  |  |
| 08ac489749da | (未分類) | 相続相談 | — | 2 | 5 | raw_probe_hit_but_no_term_hit |  |  |  |
| bebe3f72e298 | (未分類) | 法律相談 | — | 0 | 0 | stoplist_only_hit |  |  |  |
| 4fb90abd7772 | (未分類) | 労務相談 | — | 0 | 0 | no_term_no_raw_probe |  |  |  |
| 3f5382a48157 | (未分類) | [PIIのため表示抑制] [PIIのため表示抑制] | 法人(stop) | 0 | 0 | stoplist_only_hit |  |  |  |
| 752c1f58a9e2 | (未分類) | 住居侵入・不同意わいせつ未遂 [PIIのため表示抑制] | — | 0 | 0 | no_term_no_raw_probe |  |  |  |
| cb33f12e1cc0 | (未分類) | 法律相談 | — | 0 | 0 | stoplist_only_hit |  |  |  |
| 0b44bb19f79b | (未分類) | 労務相談 | — | 0 | 0 | no_term_no_raw_probe |  |  |  |
| 53be9f0607a6 | (未分類) | 法律相談 [PIIのため表示抑制] | — | 0 | 0 | stoplist_only_hit |  |  |  |
| bbb1a6facefa | (未分類) | 法律相談 [PIIのため表示抑制] | 会社(stop), 株式(stop) | 0 | 0 | stoplist_only_hit |  |  |  |
| 77b4fbf4763b | (未分類) | 和解あっせん申立事件 | — | 0 | 0 | no_term_no_raw_probe |  |  |  |
| 082fd0c77ed6 | (未分類) | 法律相談 [PIIのため表示抑制] | 会社(stop) | 0 | 0 | stoplist_only_hit |  |  |  |
| 0794b4b81930 | (未分類) | 法律相談 | — | 0 | 0 | stoplist_only_hit |  |  |  |
| 2b9a64ba5da5 | (未分類) | 支援専門家業務 [PIIのため表示抑制] | 会社(stop), 株式(stop), 業務(stop) | 0 | 0 | stoplist_only_hit |  |  |  |
