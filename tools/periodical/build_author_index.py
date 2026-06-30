#!/usr/bin/env python3
"""
build_author_index.py — ORCH-AUTHOR-CLUSTER executor (L4 補助メタ, read-only)

著者表記のゆれを統一する author_id を採番し、「同一論者の論考群」を引けるようにする。

Inputs
  --labeled  build/labeled_v0.2.1/article_meta_labeled.jsonl
             (Mac側 正本: /Users/yuta/ALOBookDX/事務所内本棚DX化計画/build/
              d1_bunken_article_meta_20260611/labeled_v0.2.1/article_meta_labeled.jsonl)
             NOTE: 発注書は input を article_join_dryrun_v0.1.csv (著者列込み) と想定していたが、
             実際の join CSV には著者列が無い。著者名(著者名フィールド)は labeled jsonl 側のみに
             存在するため、発注書の "(無ければ jsonl 側)" 指示に従い jsonl を入力とする。

Outputs
  --out-csv  artifacts/periodical/author_index_v0.1.csv
             (author_id, normalized_name, variant_names[], article_count,
              journals_appeared[], representative_titles[5])
  --out-json artifacts/periodical/author_index_summary_v0.1.json
             (total_unique_authors, top20_by_article_count, ambiguity_count, ...)

Read-only / dry-run。DB/Box/ネット書込なし。canonical promotion / accepted edge化 / 外部公開なし。

処理 (発注書準拠):
  1. 著者列を分割(複数著者は ・ 、 ／ 等)→ 正規化(空白/旧字/全半角統一)
  2. 編集距離 + 同誌・近年での共著ネットワークでクラスタ化(保守的: 衝突0を最優先し
     「強い共著証拠 + 編集距離<=1」のみでマージ。誤マージ回避)
  3. 著名な研究者(誌をまたいで多数執筆)が上位に来るよう記事数で序列化
  4. author_id = author:{normalized_slug}#{hash6} (normalized_name の決定関数 → 同名衝突0を保証)
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

DEFAULT_LABELED = (
    "/Users/yuta/ALOBookDX/事務所内本棚DX化計画/build/"
    "d1_bunken_article_meta_20260611/labeled_v0.2.1/article_meta_labeled.jsonl"
)
DEFAULT_OUT_CSV = "artifacts/periodical/author_index_v0.1.csv"
DEFAULT_OUT_JSON = "artifacts/periodical/author_index_summary_v0.1.json"

HEADERS = [
    "author_id", "normalized_name", "variant_names", "article_count",
    "journals_appeared", "representative_titles", "is_ambiguous",
]

# 複数著者・役割の区切り。半角/全角カンマは欧文姓名 (Surname，Given) を壊すので分割しない。
SPLIT_RE = re.compile(r"[・、；;／/]")

# 旧字・異体字 → 新字 (純粋な字形バリアントのみ。人物同定の標準的正規化)
ITAIJI_MAP = {
    "髙": "高", "﨑": "崎", "邊": "辺", "邉": "辺", "澤": "沢", "齋": "斎",
    "齊": "斎", "齌": "斎", "濵": "浜", "濱": "浜", "廣": "広", "德": "徳",
    "栁": "柳", "桒": "桑", "曻": "昇", "槗": "橋", "渕": "淵", "嶋": "島",
    "嵜": "崎", "隆": "隆", "靑": "青", "飛": "飛", "黑": "黒", "穐": "秋",
    "冨": "富", "舘": "館", "兒": "児", "convenience": "",
}
ITAIJI_MAP.pop("convenience", None)

# 役割語 (単独セグメントなら著者ではないので除去)
ROLE_WORDS = {
    "訳", "翻訳", "監修", "編", "編集", "編著", "校訂", "補訂", "共訳", "監訳",
    "述", "編纂", "解説", "聞き手", "司会", "構成", "答", "問", "訳・解説",
    "編集部", "訳注", "校注", "注", "選", "撰", "校", "監", "他",
}

# 機関・組織パターン (人名でないので除去)
ORG_RE = re.compile(
    r"(協会|事務局|事務所|研究会|委員会|審議室|審議会|学会|編集部|株式会社|"
    r"有限会社|法人|官報|省$|庁$|局$|部$|課$|室$|センター|機構|本部|支部|"
    r"大学$|大学院$|研究所|裁判所|検察庁|弁護士会|連合会|協議会|チーム|"
    r"グループ|プロジェクト|研究室|ゼミ|班|社$)"
)


def nfkc(s: str) -> str:
    return unicodedata.normalize("NFKC", s) if s else ""


def apply_itaiji(s: str) -> str:
    return "".join(ITAIJI_MAP.get(ch, ch) for ch in s)


_PAREN_RE = re.compile(r"[（(][^）)]*[）)]")
_NONNAME_EDGE = re.compile(r"^[\s\W_]+|[\s\W_]+$")


def normalize_name(token: str) -> str:
    """同定キー用の正規化名。空白除去 + 旧字統一 + 括弧内(旧姓等)除去。"""
    s = nfkc(token)
    s = _PAREN_RE.sub("", s)              # 括弧内 (旧姓/別名) を除去
    s = re.sub(r"\s+", "", s)             # 内部空白を全除去
    s = apply_itaiji(s)
    s = _NONNAME_EDGE.sub("", s)
    return s


def is_role_or_org(token: str) -> bool:
    t = nfkc(token).strip()
    if not t:
        return True
    if t in ROLE_WORDS:
        return True
    if ORG_RE.search(t):
        return True
    # 役割語が末尾に付いた単独トークン (例: "△△編集部") も ORG_RE で概ね捕捉済み
    return False


def strip_trailing_role(token: str) -> str:
    """末尾に区切り無しで付く役割語を剥がす (例: 'ｘｘ訳' → 役割なら本体長>=2で剥離)。"""
    t = token
    changed = True
    while changed:
        changed = False
        for rw in ("訳", "監修", "編著", "編集", "編", "校訂", "補訂", "解説"):
            if t.endswith(rw) and len(t) - len(rw) >= 2:
                t = t[: -len(rw)]
                changed = True
    return t


def split_authors(raw: str) -> list[str]:
    raw = nfkc(raw)
    parts = SPLIT_RE.split(raw)
    out = []
    for p in parts:
        p = p.strip()
        if not p:
            continue
        if is_role_or_org(p):
            continue
        p2 = strip_trailing_role(p)
        if not p2 or is_role_or_org(p2):
            continue
        out.append(p2)
    return out


def author_id_for(normalized_name: str) -> str:
    h = hashlib.sha1(normalized_name.encode("utf-8")).hexdigest()[:6]
    slug = re.sub(r"\s+", "", normalized_name)
    return f"author:{slug}#{h}"


def edit_distance_le1(a: str, b: str) -> bool:
    """編集距離 <= 1 (長さ差<=1 のときのみ判定)。"""
    if a == b:
        return True
    la, lb = len(a), len(b)
    if abs(la - lb) > 1:
        return False
    if la == lb:
        diff = sum(1 for x, y in zip(a, b) if x != y)
        return diff == 1
    # 長い方から1文字削れば一致するか
    if la > lb:
        a, b = b, a
        la, lb = lb, la
    i = j = 0
    skipped = False
    while i < la and j < lb:
        if a[i] == b[j]:
            i += 1
            j += 1
        else:
            if skipped:
                return False
            skipped = True
            j += 1
    return True


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--labeled", default=DEFAULT_LABELED)
    ap.add_argument("--out-csv", default=DEFAULT_OUT_CSV)
    ap.add_argument("--out-json", default=DEFAULT_OUT_JSON)
    args = ap.parse_args()

    labeled_path = Path(args.labeled)
    if not labeled_path.exists():
        print(f"ERROR labeled jsonl not found: {labeled_path}", file=sys.stderr)
        return 2

    # 集計コンテナ (キー = normalized_name)
    variants: dict[str, Counter] = defaultdict(Counter)        # normalized -> raw surface forms
    article_count: Counter = Counter()                          # normalized -> #articles
    journals: dict[str, Counter] = defaultdict(Counter)         # normalized -> journal_canonical
    titles: dict[str, list] = defaultdict(list)                 # normalized -> [titles]
    years: dict[str, Counter] = defaultdict(Counter)            # normalized -> pub_year
    coauthors: dict[str, set] = defaultdict(set)                # normalized -> {co-normalized}
    journal_year_key: dict[str, set] = defaultdict(set)         # normalized -> {(journal,year)}

    total_records = 0
    records_with_author = 0
    author_mentions = 0

    with labeled_path.open(encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            total_records += 1
            raw_author = (rec.get("著者名") or "").strip()
            if not raw_author:
                continue
            names = split_authors(raw_author)
            if not names:
                continue
            records_with_author += 1

            title = (rec.get("標題") or "").replace("\n", " ").strip()
            jc = (rec.get("journal_canonical") or "").strip()
            pub = nfkc(rec.get("発行年月日") or "")
            ym = re.search(r"(\d{4})", pub)
            year = ym.group(1) if ym else ""

            norm_list = []
            for nm in names:
                norm = normalize_name(nm)
                if not norm:
                    continue
                norm_list.append(norm)
                variants[norm][nfkc(nm)] += 1
                article_count[norm] += 1
                author_mentions += 1
                if jc:
                    journals[norm][jc] += 1
                if title and title not in titles[norm]:
                    if len(titles[norm]) < 12:
                        titles[norm].append(title)
                if year:
                    years[norm][year] += 1
                    if jc:
                        journal_year_key[norm].add((jc, year))
            # 共著ネットワーク
            uniq = set(norm_list)
            for a in uniq:
                coauthors[a] |= (uniq - {a})

    # --- クラスタ化 (保守的マージ) ---
    # 衝突0 を最優先。誤マージを避けるため「編集距離<=1 かつ 共著者を共有」のみ統合。
    # union-find
    parent: dict[str, str] = {n: n for n in article_count}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra == rb:
            return
        # 記事数の多い方を代表にする (著名研究者を代表化)
        if article_count[ra] < article_count[rb]:
            ra, rb = rb, ra
        parent[rb] = ra

    merge_pairs = 0
    names_list = list(article_count)
    # 編集距離ベースの共著マージは「評価したが無効化」している。理由(重要):
    #   日本語人名は3字前後が大半で、編集距離1の別人ペアが大量に存在する
    #   (森本滋⇔森田章, 山本和彦⇔山本龍彦, 伊藤眞⇔伊藤進 等は全て別人)。
    #   prolific な論者は座談会等で多数と共著するため「共著者共有」ゲートも弱く、
    #   別人を誤マージして article_count を汚染し「同一論者の論考群」を破壊する。
    #   → 衝突0(=同一正規化名に複数id無し)と誤マージ回避を最優先し、
    #     正規化(NFKC+旧字統一+空白/括弧除去)による厳密一致クラスタのみを採用。
    #     これだけで 渡邊→渡辺 / 全半角 / 旧姓括弧 等の真のゆれは吸収される。
    ENABLE_FUZZY_MERGE = False
    if ENABLE_FUZZY_MERGE:
        by_coauthor: dict[str, list] = defaultdict(list)
        for n in names_list:
            for ca in coauthors[n]:
                by_coauthor[ca].append(n)
        checked = set()
        for ca, members in by_coauthor.items():
            if len(members) < 2:
                continue
            for i in range(len(members)):
                for j in range(i + 1, len(members)):
                    a, b = members[i], members[j]
                    pair = (a, b) if a < b else (b, a)
                    if pair in checked:
                        continue
                    checked.add(pair)
                    if a != b and edit_distance_le1(a, b):
                        union(a, b)
                        merge_pairs += 1

    # クラスタ集約: 代表 normalized_name へ統合
    clusters: dict[str, dict] = {}
    for n in names_list:
        root = find(n)
        c = clusters.setdefault(root, {
            "members": set(),
            "article_count": 0,
            "variants": Counter(),
            "journals": Counter(),
            "titles": [],
            "title_set": set(),
        })
        c["members"].add(n)
        c["article_count"] += article_count[n]
        c["variants"].update(variants[n])
        c["journals"].update(journals[n])
        for t in titles[n]:
            if t not in c["title_set"]:
                c["title_set"].add(t)
                if len(c["titles"]) < 5:
                    c["titles"].append(t)

    # 代表 normalized_name = 最頻 variant を NFKC/旧字統一した形 (= root) を使用
    rows = []
    name_to_id = {}
    collisions = 0
    for root, c in clusters.items():
        normalized_name = root
        aid = author_id_for(normalized_name)
        # 衝突検査: 同一 normalized_name に複数 id が出ないこと
        if normalized_name in name_to_id and name_to_id[normalized_name] != aid:
            collisions += 1
        name_to_id[normalized_name] = aid
        variant_names = [v for v, _ in c["variants"].most_common()]
        journals_appeared = [j for j, _ in c["journals"].most_common()]
        rows.append({
            "author_id": aid,
            "normalized_name": normalized_name,
            "variant_names": variant_names,
            "article_count": c["article_count"],
            "journals_appeared": journals_appeared,
            "representative_titles": c["titles"][:5],
            # v0.2: 正規化名 <=2字 は同名異人の混在可能性が高い。下流が単一人物として扱わないための注意フラグ。
            "is_ambiguous": len(normalized_name) <= 2,
        })

    rows.sort(key=lambda r: (-r["article_count"], r["normalized_name"]))

    # --- 出力 CSV ---
    out_csv = Path(args.out_csv)
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_csv.open("w", encoding="utf-8", newline="") as fo:
        w = csv.writer(fo)
        w.writerow(HEADERS)
        for r in rows:
            w.writerow([
                r["author_id"],
                r["normalized_name"],
                "|".join(r["variant_names"]),
                r["article_count"],
                "|".join(r["journals_appeared"]),
                "|".join(r["representative_titles"]),
                "true" if r["is_ambiguous"] else "false",
            ])

    # --- ambiguity: 短すぎる名 (姓のみ等, 別人の可能性大) を曖昧と判定 ---
    ambiguity_count = sum(1 for r in rows if len(r["normalized_name"]) <= 2)
    authors_ge10 = sum(1 for r in rows if r["article_count"] >= 10)

    summary = {
        "schema_version": "v0.1",
        "labeled_path": str(labeled_path),
        "total_records": total_records,
        "records_with_author": records_with_author,
        "author_mentions": author_mentions,
        "total_unique_authors": len(rows),
        "authors_with_ge10_articles": authors_ge10,
        "ambiguity_count": ambiguity_count,
        "ambiguity_definition": "normalized_name length <= 2 chars (likely shared surname / multiple persons)",
        "cluster_merges": merge_pairs,
        "collision_count": collisions,
        "clustering_policy": (
            "正規化(NFKC + itaiji旧字統一 + 内部空白除去 + 括弧内除去)による厳密一致クラスタのみ採用。"
            "編集距離+共著ネットワークによる fuzzy マージは評価したが無効化 (ENABLE_FUZZY_MERGE=False)。"
            "理由: 日本語人名は3字前後が大半で編集距離1の別人ペアが多数 (森本滋⇔森田章, 山本和彦⇔山本龍彦 等)、"
            "prolific論者は座談会等で多数と共著するため共著ゲートも弱く、別人誤マージで article_count を汚染するため。"
        ),
        "author_id_scheme": "author:{normalized_slug}#{sha1(normalized_name)[:6]}",
        "top20_by_article_count": [
            {
                "author_id": r["author_id"],
                "normalized_name": r["normalized_name"],
                "article_count": r["article_count"],
                "journals_appeared": r["journals_appeared"][:8],
            }
            for r in rows[:20]
        ],
    }
    Path(args.out_json).write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(
        f"[done] records={total_records} with_author={records_with_author} "
        f"mentions={author_mentions} unique_authors={len(rows)} "
        f">=10articles={authors_ge10} merges={merge_pairs} collisions={collisions}",
        file=sys.stderr,
    )
    print(f"[out]  {args.out_csv}", file=sys.stderr)
    print(f"[out]  {args.out_json}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
