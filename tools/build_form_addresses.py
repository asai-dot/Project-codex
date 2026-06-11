#!/usr/bin/env python3
"""
DD-FORMOBJ-001 S1 バルク適用ハーネス: bib_toc/toc_nodes → 書式アドレス(anchor充填)

入力: ある書籍のTOC行(JSON配列: {bib_id,ordinal,level,page,text})
出力: form_snapshot.v1 の anchorだけ充填したスタブ群(content=null/status=anchor_only)
      → 後段S2(vision OCR)が page_span を撮って content を埋める。

書式ノード検出:
  - 強マーカー: 【文例N】【書式N】【記載例N】【ひな形N】 等（記載例集の式）
  - 弱: 末端levelで form keyword（契約書/合意書/通知書/議事録/定款/規程/様式/別紙…）
頁範囲: page_start=node.page / page_end=次ノードの page-1（同頁は自身）。

DB直結は psql/Supabase 側に委譲(本ファイルはTOC配列を受ける純関数)。__main__ で自己テスト。
"""
from __future__ import annotations
import re, json, sys, argparse

FORM_MARKER = re.compile(r'^【(文例|書式|記載例|ひな形|雛形|様式|参考例|文書例)\s*\d+】')
FORM_KW = re.compile(r'(契約書|合意書|覚書|念書|誓約書|通知書|請求書|議事録|定款|規程|規則|様式|書式|別紙|別表|条項例|文例|モデル|サンプル|届出?書?|申請書)')

def build_addresses(toc_rows: list[dict]) -> list[dict]:
    rows = sorted(toc_rows, key=lambda r: r["ordinal"])
    n = len(rows)
    out = []
    for i, r in enumerate(rows):
        text = (r.get("text") or "").strip()
        is_marker = bool(FORM_MARKER.match(text))
        # 末端判定: 次ノードが自分より深くない = leaf
        is_leaf = (i+1 >= n) or (rows[i+1]["level"] <= r["level"])
        is_form = is_marker or (is_leaf and bool(FORM_KW.search(text)) and r["level"] >= 3)
        if not is_form:
            continue
        # page_span
        ps = r.get("page")
        pe = ps
        for j in range(i+1, n):
            if rows[j].get("page") is not None and rows[j]["page"] > (ps or -1):
                pe = rows[j]["page"] - 1
                break
        out.append({
            "schema": "form_snapshot.v1",
            "form_uid": None,
            "provisional_key": f'{r["bib_id"]}:toc_ord{r["ordinal"]}',
            "anchor": {
                "canonical_book_id": None,
                "book_ref": {"bencom_bib_id": r["bib_id"]},
                "toc_node_id": None,
                "toc_ref": {"source": "bencom_bib_toc", "ordinal": r["ordinal"], "level": r["level"], "text": text},
                "page_span_print": [ps, pe] if ps is not None else None,
                "page_span_pdf": None,
                "page_offset_pdf_minus_print": None,
                "span_kind": "single_node",
            },
            "form_title": text,
            "form_kind": None,           # S2/分類で確定
            "content": None,             # S2で充填
            "status": "anchor_only",
            "match": {"match_kind": "marker" if is_marker else "leaf_keyword",
                      "decision_status": "auto" if is_marker else "review"},
        })
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--toc-json", required=True, help="TOC行のJSON配列ファイル")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    rows = json.load(open(a.toc_json, encoding="utf-8"))
    addrs = build_addresses(rows)
    json.dump(addrs, open(a.out, "w"), ensure_ascii=False, indent=1)
    print(f"forms={len(addrs)}  auto={sum(1 for x in addrs if x['match']['decision_status']=='auto')}")

if __name__ == "__main__" and len(sys.argv) == 1:
    # 自己テスト(会社議事録の構造を模した小フィクスチャ)
    fx = [
        {"bib_id":"B","ordinal":91,"level":1,"page":114,"text":"第2章 株主総会議事録の作り方と記載例"},
        {"bib_id":"B","ordinal":100,"level":2,"page":118,"text":"1 全体の記載例"},
        {"bib_id":"B","ordinal":101,"level":3,"page":118,"text":"【文例1】 株主総会議事録（一括審議方式）の一般的な記載例⑴"},
        {"bib_id":"B","ordinal":102,"level":3,"page":134,"text":"【文例2】 株主総会議事録（一括審議方式）の一般的な記載例⑵"},
        {"bib_id":"B","ordinal":103,"level":3,"page":139,"text":"【文例3】 株主総会議事録（個別審議方式）の一般的な記載例"},
        {"bib_id":"B","ordinal":104,"level":2,"page":150,"text":"2 個別議題についての記載例"},  # 解説見出し=非式
        {"bib_id":"B","ordinal":455,"level":1,"page":494,"text":"索引"},
    ]
    res = build_addresses(fx)
    _s=[0,0]
    def ck(n,c):
        _s[1]+=1; print(("PASS" if c else "FAIL"),n); _s[0]+=bool(c)
    ck("文例3件を抽出(見出し/索引は除外)", len(res)==3)
    ck("文例1の頁範囲=118-133", res[0]["anchor"]["page_span_print"]==[118,133])
    ck("文例3の頁範囲=139-149", res[2]["anchor"]["page_span_print"]==[139,149])
    ck("markerはauto", all(r["match"]["decision_status"]=="auto" for r in res))
    ck("anchor_only/content=null", all(r["status"]=="anchor_only" and r["content"] is None for r in res))
    print(f"\n{_s[0]}/{_s[1]} passed")
elif __name__ == "__main__":
    main()
