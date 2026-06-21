#!/usr/bin/env python3
"""case_symbol テーブル生成 v0.2 (DD-CASEID-002 MF-2/MF-3)。

MF-3: 1表(symbol→romaji+意味)を2表へ分離:
  case_symbol_romanization.csv : symbol_norm, romaji, romanization_scheme, scheme_version
       (identity 非使用・表示専用・多対一許容)
  case_symbol_semantics.csv    : symbol_norm, forum_level, procedure_kind, case_category,
       valid_from, valid_to, source_basis, status
       (forum・時期依存の法的意味。複合スコープで解決)

MF-2: 裁判所「符号の説明」に基づく意味訂正:
  行サ = 高裁 行政上告提起事件 (旧seed「行政抗告」は誤り。抗告提起は行ス)
  行フ = 最高裁 行政許可抗告事件 (旧seed「行政雑」は誤り)
  行ケ = 高裁 行政訴訟事件(第一審) (知財審決取消は主要例だが定義全体ではない)
  行ス = 高裁 行政抗告提起事件 (新規追加)

source_basis=court_official は裁判所公開の符号説明に着地。status=review は
意味分類・検索filter・case_type推定に *供給しない* (MF-2 閉鎖条件)。
"""
import csv
from pathlib import Path

OUTDIR = Path(__file__).resolve().parent.parent / "app" / "data" / "case_identity"
SCHEME = "alo-display-v1"

# symbol, romaji, forum_level, procedure_kind, case_category, valid_from, valid_to, source_basis, status
M = [
    # 民事
    ("ワ", "wa", "district", "first_instance_ordinary", "civil", "", "", "court_official", "confirmed"),
    ("ハ", "ha", "summary", "first_instance_ordinary", "civil", "", "", "court_official", "confirmed"),
    ("レ", "re", "district", "appeal_kosso_from_summary", "civil", "", "", "court_official", "confirmed"),
    ("ネ", "ne", "high", "appeal_kosso", "civil", "", "", "court_official", "confirmed"),
    ("オ", "o", "supreme", "jokoku", "civil", "", "", "court_official", "confirmed"),
    ("受", "ju", "supreme", "jokoku_juri_moshitate", "civil", "", "", "court_official", "confirmed"),
    ("ツ", "tsu", "high", "jokoku_from_summary", "civil", "", "", "alo_provisional", "review"),
    ("ヨ", "yo", "district", "hozen", "civil", "", "", "court_official", "confirmed"),
    ("ヲ", "wo", "district", "execution", "civil", "", "", "alo_provisional", "review"),
    ("フ", "fu", "district", "bankruptcy", "civil", "", "", "court_official", "confirmed"),
    ("再", "sai", "district", "civil_rehabilitation", "civil", "", "", "court_official", "confirmed"),
    ("ミ", "mi", "district", "corporate_reorganization", "civil", "", "", "alo_provisional", "review"),
    ("ヌ", "nu", "district", "execution_claim", "civil", "", "", "alo_provisional", "review"),
    ("ル", "ru", "district", "execution", "civil", "", "", "alo_provisional", "review"),
    ("リ", "ri", "district", "execution_secured_realty", "civil", "", "", "alo_provisional", "review"),
    # 刑事
    ("わ", "wa", "district", "first_instance", "criminal", "", "", "court_official", "confirmed"),
    ("う", "u", "high", "appeal_kosso", "criminal", "", "", "court_official", "confirmed"),
    ("あ", "a", "supreme", "jokoku", "criminal", "", "", "court_official", "confirmed"),
    ("ほ", "ho", "summary", "first_instance", "criminal", "", "", "alo_provisional", "review"),
    # 行政 (MF-2 訂正)
    ("行ウ", "gyo-u", "district", "gyosei_first_instance", "administrative", "", "", "court_official", "confirmed"),
    ("行ケ", "gyo-ke", "high", "gyosei_first_instance", "administrative", "", "",
     "court_official", "confirmed"),  # 行政訴訟第一審(知財審決取消等を含むが限定しない)
    ("行コ", "gyo-ko", "high", "gyosei_kosso_teiki", "administrative", "", "", "court_official", "confirmed"),
    ("行ス", "gyo-su", "high", "gyosei_kokoku_teiki", "administrative", "", "",
     "court_official", "confirmed"),  # 行政抗告提起(新規・行サと峻別)
    ("行サ", "gyo-sa", "high", "gyosei_jokoku_teiki", "administrative", "", "",
     "court_official", "confirmed"),  # 行政上告提起(旧「抗告」は誤り)
    ("行ツ", "gyo-tsu", "supreme", "gyosei_jokoku", "administrative", "", "", "court_official", "confirmed"),
    ("行ヒ", "gyo-hi", "supreme", "gyosei_jokoku_juri", "administrative", "", "", "court_official", "confirmed"),
    ("行フ", "gyo-fu", "supreme", "gyosei_kyoka_kokoku", "administrative", "", "",
     "court_official", "confirmed"),  # 行政許可抗告(旧「雑」は誤り)
    # 家事 / 人事
    ("家", "ka", "family", "kaji_shinpan", "family", "", "", "court_official", "confirmed"),
    ("家イ", "ka-i", "family", "kaji_chotei", "family", "", "", "court_official", "confirmed"),
    ("家ロ", "ka-ro", "family", "kaji_betsuhyo2_shinpan", "family", "", "", "alo_provisional", "review"),
    ("タ", "ta", "district", "jinji_sosho", "family", "", "", "alo_provisional", "review"),
    # 労働 / 少年
    ("労", "ro", "district", "rodo_shinpan", "labor", "", "", "court_official", "confirmed"),
    ("少", "sho", "family", "shonen_hogo", "juvenile", "", "",
     "court_official", "confirmed"),  # 非公開性は出口ACL側で強制(MF SHOULD-FIX#4)
    # 旧法
    ("ヰ", "i", "daishin_in", "old_civil", "civil", "", "1947-05-02", "alo_provisional", "review"),
]


def main():
    OUTDIR.mkdir(parents=True, exist_ok=True)
    rom = OUTDIR / "case_symbol_romanization.csv"
    sem = OUTDIR / "case_symbol_semantics.csv"

    with rom.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["symbol_norm", "romaji", "romanization_scheme", "scheme_version"])
        for row in M:
            w.writerow([row[0], row[1], SCHEME, "1"])

    with sem.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["symbol_norm", "forum_level", "procedure_kind", "case_category",
                    "valid_from", "valid_to", "source_basis", "status"])
        for s, r, fl, pk, cc, vf, vt, sb, st in M:
            w.writerow([s, fl, pk, cc, vf, vt, sb, st])

    conf = sum(1 for x in M if x[8] == "confirmed")
    print(f"romanization: {len(M)} 行 / semantics: {len(M)} 行 "
          f"(confirmed={conf}, review={len(M)-conf})")
    print(f"  romaji衝突(display許容): wa = 民事ワ + 刑事わ")
    print(f"  MF-2訂正: 行サ=上告提起 / 行フ=許可抗告 / 行ケ=行政訴訟第一審 / 行ス=抗告提起(新規)")
    print(f"出力: {rom.name}, {sem.name}")


if __name__ == "__main__":
    main()
