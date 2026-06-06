#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""判例レーンのテスト（stdlibのみ。`python3 tests/test_case_lane.py`）。

スクショの実判例（コンメンタール民訴III p.43 の引用判例 / L02010234）で検証。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.case_identity import parse_date, parse_case_number, parse_court, normalize_citation, normalize_case_ref
from src.case_deeplink import resolve_case, best_landing
from scripts.harvest_precedents import harvest_text

ok = 0


def check(name, cond):
    global ok
    assert cond, f"FAIL: {name}"
    ok += 1
    print("  ok -", name)


# --- 和暦 → 西暦 ---
check("和暦 昭和44年5月19日 → 1969-05-19", parse_date("昭和44年5月19日") == "1969-05-19")
check("和暦 令和元年5月1日 → 2019-05-01", parse_date("令和元年5月1日") == "2019-05-01")
check("和暦 昭和40年6月30日 → 1965-06-30", parse_date("昭和40年6月30日") == "1965-06-30")

# --- 事件番号 ---
cn = parse_case_number("昭和41年（ネ）第2780号")
check("事件番号 mark=ネ", cn["mark"] == "ネ")
check("事件番号 number=2780", cn["number"] == 2780)
check("事件番号 西暦=1966", cn["seireki_year"] == 1966)
check("事件番号 全角数字（２７８０）も可", parse_case_number("昭和41年（ネ）第２７８０号")["number"] == 2780)

# --- 裁判所 ---
c = parse_court("東京高等裁判所")
check("裁判所 level=high", c["level"] == "high")
check("裁判所 detail_variant=4", c["detail_variant"] == 4)
sup = parse_court("最高裁判所大法廷")
check("最高裁 detail_variant=2", sup["detail_variant"] == 2)
check("最高裁 bench=大法廷", sup["bench"] == "大法廷")

# --- 正規化（正本キー） ---
rec = normalize_citation("東京高等裁判所", "昭和44年5月19日", "昭和41年（ネ）第2780号",
                         title="建物収去、土地明渡請求控訴事件", hh_id="L02420223")
check("正本 judged_on", rec["judged_on"] == "1969-05-19")
check("正本 canonical_key 一意", rec["canonical_key"] == "tokyo-koto|1969-05-19|昭和41（ネ）2780号")
check("正本 hh_id 保持", rec["hh_id"] == "L02420223")
check("正本 case_node_id", rec["case_node_id"] == "alo:case:tokyo-koto:1969-05-19:昭和41（ネ）2780号")

# --- leala係属事件の形式（事務所自身の事件 = 内部PD判決文の供給源） ---
cn2 = parse_case_number("令和４年（ワ）第２６０号")
check("leala 事件番号 mark=ワ", cn2["mark"] == "ワ")
check("leala 事件番号 number=260（全角）", cn2["number"] == 260)
check("leala 事件番号 西暦=2022", cn2["seireki_year"] == 2022)
nara = parse_court("奈良地方裁判所　民事部３B")
check("leala 裁判所 level=district", nara["level"] == "district")
check("leala 裁判所 slug=nara-chiho（部は除外）", nara["court_slug"] == "nara-chiho")
check("leala 部=民事部3B を division に分離（NFKC正規化後）", nara["division"] == "民事部3B")
rec2 = normalize_citation("奈良地方裁判所　民事部３B", None, "令和４年（ワ）第２６０号")
check("leala 正本 court_slug 部を含まない", rec2["court_slug"] == "nara-chiho")
check("leala 正本 division 保持", rec2["division"] == "民事部3B")
check("leala 正本キー（判決日naでも事件番号で同定）",
      rec2["case_node_id"] == "alo:case:nara-chiho:na:令和4（ワ）260号")

# --- 略記の判例参照（OPAC/CiNii case_ref_text 形式）への合わせ込み ---
check("略記日付 昭44.11.26 → 1969-11-26", parse_date("昭44.11.26") == "1969-11-26")
check("略記日付 平20・3・1 → 2008-03-01", parse_date("平20・3・1") == "2008-03-01")
r_saiko = normalize_case_ref("最大判昭44.11.26民集23-11-2150")
check("case_ref 最大判→最高裁", r_saiko["court_slug"] == "saikosai")
check("case_ref 最大判→大法廷", r_saiko["bench"] == "大法廷")
check("case_ref 判決日", r_saiko["judged_on"] == "1969-11-26")
check("case_ref 判例集citation", r_saiko["reporter"].startswith("民集"))
check("case_ref 正本キー(事件番号無→citationで同定)",
      r_saiko["case_node_id"] == "alo:case:saikosai:1969-11-26:民集23-11-2150")
r_koto = normalize_case_ref("東京高判昭和44年5月19日")
check("case_ref 東京高判→tokyo-koto", r_koto["court_slug"] == "tokyo-koto")
check("case_ref 東京高判 判決日", r_koto["judged_on"] == "1969-05-19")
r_chi = normalize_case_ref("大阪地判平20・3・1判時1234-56")
check("case_ref 大阪地判→osaka-chiho", r_chi["court_slug"] == "osaka-chiho")

# --- 着地解決（3層・優先順） ---
# court_id あり → 裁判所HTMLが最優先（内部PDが無い場合）
land = resolve_case(dict(rec, court_id="85887"), context={"cid": "ebaaf", "viewer_page": 83})
check("着地 候補に裁判所", any(x["source_id"] == "courts" for x in land))
courts = next(x for x in land if x["source_id"] == "courts")
check("着地 裁判所URL detail4?id=85887",
      courts["url"] == "https://www.courts.go.jp/app/hanrei_jp/detail4?id=85887")
check("着地 ベンコムオンランプ", any(x["source_id"] == "bencom_onramp" for x in land))
onramp = next(x for x in land if x["source_id"] == "bencom_onramp")
check("着地 オンランプURL", onramp["url"] == "https://library.bengo4.com/books/ebaaf/precedents#page_83")

# 内部PDがあれば最優先
land_pd = resolve_case(dict(rec, court_id="85887", has_internal_pd=True),
                       context={"cid": "ebaaf", "viewer_page": 83})
check("着地 内部PD最優先", best_landing(dict(rec, court_id="85887", has_internal_pd=True),
      context={"cid": "ebaaf", "viewer_page": 83})["source_id"] == "internal_pd")

# court_id 無し → 裁判所は除外、オンランプにフォールバック
land_noid = resolve_case(rec, context={"cid": "ebaaf", "viewer_page": 83})
check("着地 court_id無→裁判所除外", not any(x["source_id"] == "courts" for x in land_noid))
check("着地 court_id無→オンランプ最優先", best_landing(rec, context={"cid": "ebaaf", "viewer_page": 83})["source_id"] == "bencom_onramp")

# --- harvest（precedentsページ本文 → 引用レコード） ---
PAGE = """引用判例リンク
コンメンタール民事訴訟法III ［第2版］
第2編／第1章〜第3章／第133条〜第178条
この本を読む
引用判例リンク一覧
83ページ 紙面43ページ
東京高等裁判所 昭和43年8月6日
昭和43年（ラ）第557号
訴状却下命令に対する即時抗告事件
捕捉しがたい請求原因を記載した訴状の却下が許されないとした事例
東京高等裁判所 昭和44年5月19日
昭和41年（ネ）第2780号
建物収去、土地明渡請求控訴事件
賃料不払を理由とする土地賃貸借契約の解除の効果を主張することが信義に反して許されないとされた事例
福岡高等裁判所 昭和46年3月9日
昭和45年（ネ）第395号
建物収去、土地明渡請求控訴事件
民訴法224条1項に違反する不適法な訴状として、訴を却下した1審判決が違法であるとされた事例
"""
h = harvest_text(PAGE, cid="ebaaf6907d0c7eaf14a99fcd7e40c42283674fb06f5f4216fa45a02d118465b5")
check("harvest 3件抽出", len(h["cases"]) == 3)
check("harvest viewer_page=83", h["context"]["viewer_page"] == 83)
check("harvest print_page=43", h["context"]["print_page"] == 43)
check("harvest 2件目=昭44ネ2780", h["cases"][1]["case_number"]["number"] == 2780)
check("harvest 2件目 judged_on", h["cases"][1]["judged_on"] == "1969-05-19")
check("harvest 3件目=福岡高裁", h["cases"][2]["court_slug"] == "fukuoka-koto")
check("harvest citation に cid/page", h["citations"][0]["cid"].startswith("ebaaf") and h["citations"][0]["viewer_page"] == 83)
check("harvest claim_scope=cites(支持止まり)", h["citations"][0]["claim_scope"] == "cites")

print(f"\n{ok} checks passed.")
