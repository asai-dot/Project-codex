-- M9: 税経通信 2026年 通号 部分追補（1-4月のみ確定取得分）
-- generated: 2026-06-23 JST / target: staging_periodical
-- 重要発見: 2025-12=通号1144 → 2026-01=通号1146（1145は12月→1月の間に増刊が入った欠番）。
-- 80巻は13号まである＝毎年臨時増刊が1本入る運用と整合。Geminiが警告した「2026も飛ぶ」が現実に発生。
-- 5-6月は実通号未確認のため暦算しない（誤付与リスク確実）。canonical_ym 据置を維持。
INSERT INTO staging_periodical.tsuukan_crosswalk (journal_id, year, month, tsuukan, src) VALUES
 ('zeikei', 2026, 1, 1146, 'shinzansha+web(81巻1号)'),
 ('zeikei', 2026, 2, 1147, 'shinzansha+web(81巻2号)'),
 ('zeikei', 2026, 3, 1148, 'web(81巻3号)'),
 ('zeikei', 2026, 4, 1149, 'web/NDL(81巻4号)')
ON CONFLICT DO NOTHING;
SELECT staging_periodical.reconcile_issue_ids();
-- 結果: 1-4月8行 → ncid:AN00390536#1146..1149 canonical 化。5-6月4行は ncid:AN00390536#2026-MM 据置。
