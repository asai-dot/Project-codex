#!/usr/bin/env python3
"""alo_source_registry_seed の再構成生成 (DD-CASE-001 v0.1-recon)。

原本 alo_source_registry_seed_v0.1_20260604.jsonl (41行・confidentiality_class付与) は
ローカル散逸で回収不能。本スクリプトは典拠が明確な行のみを機械生成する:
  - 準司法機関 23件: build_forum_registry_seed.py の QUASI台帳 (Box実在) をそのまま転記
  - 公式/商用/在野の判例ソース: 31_case_layer §4 alo_source_priority + reality_check より

confidentiality は2軸に分けて持つ (DD-CASE-001 §1 の出口軸/ライセンス軸混同回避):
  confidentiality_default : matter軸 (open / matter_confirmed / lawyer_client_confidential)
  redistribution          : ライセンス軸 (public / commercial_licensed / restricted)
can_global_index = (confidentiality_default == 'open') and (redistribution == 'public')
                   かつ source != 'jufu' (RP-04: jufu は global embedding 禁止)

※ confidentiality 割当は recon 提案値。DDCASESOURCE / owner 確認まで暫定。
出力: docs/alo_source_registry_seed_v0.1-recon_20260619.jsonl
"""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "docs" / "alo_source_registry_seed_v0.1-recon_20260619.jsonl"

# build_forum_registry_seed.py QUASI台帳 (23件, Box 2264377914086 より転記)
QUASI = [
    ("kokuzei-fufuku-shinpan", "administrative_tribunal", "国税不服審判所", "租税"),
    ("churoi", "administrative_tribunal", "中央労働委員会", "労働(不当労働行為)"),
    ("jftc", "administrative_tribunal", "公正取引委員会", "独占禁止法"),
    ("gyofuku-shinsakai", "administrative_review", "行政不服審査会(総務省)", "行政横断"),
    ("roho-shinsakai", "administrative_review", "労働保険審査会", "労災・雇用保険"),
    ("shaho-shinsakai", "administrative_review", "社会保険審査会", "年金・医療保険"),
    ("kochoi", "administrative_tribunal", "公害等調整委員会", "公害・鉱業"),
    ("kainan-shinpan", "administrative_tribunal", "海難審判所", "海事"),
    ("sesc", "agency", "証券取引等監視委員会", "金商法"),
    ("finmac", "adr", "FINMAC(証券・金融商品あっせん相談センター)", "証券・金商"),
    ("zenginkyo-adr", "adr", "全国銀行協会あっせん委員会", "銀行"),
    ("nichibenren-adr", "adr", "日弁連金融ADR", "金融横断"),
    ("jsaa", "arbitration", "日本スポーツ仲裁機構", "スポーツ"),
    ("jp-drp", "adr", "JPNIC/JIPAC ドメイン名紛争処理", "ドメイン名(.jp)"),
    ("kokusen-hanrei", "agency", "国民生活センター 暮らしの判例", "消費者"),
    ("kokusen-adr", "adr", "国民生活センターADR(紛争解決委員会)", "消費者ADR"),
    ("pmda-kyufu", "agency", "PMDA 副作用救済給付決定", "薬事・無過失救済"),
    ("bpo", "other", "放送倫理・番組向上機構(BPO)", "放送倫理・人権"),
    ("retio", "agency", "不動産適正取引推進機構(RETIO)", "不動産取引"),
    ("denki-tsushin-funso", "administrative_tribunal", "電気通信紛争処理委員会", "通信・放送"),
    ("soumu-johokokai-toshin", "administrative_review", "情報公開・個人情報保護審査会(総務省)", "情報公開/個情"),
    ("zaiya-seihodb", "other", "生活保護裁決DB(学術集約)", "生活保護(行政不服)"),
    ("jufu", "court", "受任案件 手元判決(非公開・事務所保有)", "全分野"),
]

# 公式/商用/在野の判例ソース (31_case_layer §4 + reality_check)
CASE_SOURCES = [
    # source_system, category, confidentiality_default, redistribution, note
    ("saikousai-hp",  "official_court",   "open", "public",             "最高裁HP 公表判例"),
    ("saikousai-db",  "official_court",   "open", "restricted",         "民事判決情報DB(仮名処理・有償, 2026運用目標)"),
    ("D1-Law",        "commercial_caselaw","open","commercial_licensed", "PoC正規ソース。本文公開だが再配布はライセンス制約"),
    ("hanrei-times",  "commercial_caselaw","open","commercial_licensed", "判例タイムズ"),
    ("hanrei-hisho",  "commercial_caselaw","open","commercial_licensed", "判例秘書"),
    ("LIC",           "commercial_lit",   "open", "commercial_licensed", "解説誌4誌本文(D1-LIC crosswalk源). case_text candidate"),
    ("opac-cinii",    "academic_index",   "open", "public",             "OPAC/CiNii. 補助source(candidate/review lane)"),
    ("manual",        "manual_entry",     "matter_confirmed", "restricted", "手動入力。既定は受任由来として保守的に"),
]


def main():
    rows = []
    for source, ftype, name, juris in QUASI:
        if source == "jufu":
            conf, redist = "lawyer_client_confidential", "restricted"
        else:
            # 公表裁決・あっせん事例コーパスは原則 open / public
            conf, redist = "open", "public"
        # can_global_index は導出値 (should_fix#2: 本番は保存列でなく view 推奨)。
        can_idx = (conf == "open" and redist == "public" and source != "jufu")
        rows.append({
            "source_system": source, "forum_type": ftype, "name": name,
            "category": "quasi_judicial", "jurisdiction": juris,
            "confidentiality_default": conf, "redistribution": redist,
            "can_global_index": can_idx, "seed_source": "quasi_judicial_台帳",
            "recon_status": "reconstructed_from_residual_materials",  # must_fix#1
            "provenance": "recon_from_build_forum_registry_seed.QUASI",
        })
    for source, cat, conf, redist, note in CASE_SOURCES:
        can_idx = (conf == "open" and redist == "public" and source != "jufu")
        rows.append({
            "source_system": source, "forum_type": "", "name": note,
            "category": cat, "jurisdiction": "",
            "confidentiality_default": conf, "redistribution": redist,
            "can_global_index": can_idx, "seed_source": "31_case_layer_§4 + reality_check",
            "recon_status": "reconstructed_from_residual_materials",  # must_fix#1
            "provenance": "recon_from_alo_source_priority",
        })

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    # should_fix#1: 原本想定41行との差分10行を別queueとして開示 (推定カテゴリ)。
    missing = {
        "recon_status": "missing_recon_sources",
        "expected_original_rows": 41,
        "reconstructed_rows": len(rows),
        "gap": 41 - len(rows),
        "candidate_missing_categories": [
            "裁判所支部別の source 細分 (forum seed の支部展開に対応)",
            "分割コーパス (同一機関の公表/本文/添付PDF/匿名化前の record-level 細分)",
            "在野・学術集約の追加 source (生活保護DB 以外)",
        ],
        "note": "原本逐語不在のため正確な10行内訳は不明。owner/DDCASESOURCE 確認まで暫定 queue。",
    }
    MISS = OUT.parent / "alo_source_registry_seed_missing_recon_sources_20260619.json"
    MISS.write_text(json.dumps(missing, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    n_quasi = sum(1 for r in rows if r["category"] == "quasi_judicial")
    n_idx = sum(1 for r in rows if r["can_global_index"])
    print(f"alo_source_registry_seed_v0.1-recon: {len(rows)} 行 "
          f"(quasi={n_quasi}, case_sources={len(rows)-n_quasi})")
    print(f"  can_global_index=True: {n_idx} / global不可(非open or 非public or jufu): {len(rows)-n_idx}")
    print(f"  ※原本は41行。本reconは典拠明確分のみ={len(rows)}行 (差分は支部別・分割コーパス未展開)")
    print(f"出力: {OUT}")


if __name__ == "__main__":
    main()
