#!/usr/bin/env python3
"""
DD-FORMOBJ-001 S3: canonical合成（参照実装 v0.1）

複数の form_snapshot（源別・S2出力）を1つの canonical form_object へ合成する。
方針:
  - 基底選択 = 源優先policy(D-F1) ＋ 粒度ガード(最富源比20%未満は基底になれない)
  - crosswalk = block単位対応(type+no+norm(title/text))で三点測量(agreement)
  - 品質オーバーレイ = 確定誤謬クラス(廷→延)を検出→corrected。生snapshotは不変
  - 合成で発明しない = canonicalのblockは基底のもの。他源は「裏取り/訂正/頁補完」のみ。
    基底に無いblockは discrepancies(review) として出すだけ(自動追加しない)
  - confidence = source_authority × merge × quality（係数列・finalは導出）

実装: tools/form_address_resolver.py の norm_title_v1 / ERROR_CLASSES を再利用。
__main__ で自己テスト。
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from form_address_resolver import norm_title_v1, ERROR_CLASSES

# 源優先(D-F1)。大きいほど高優先。
SOURCE_AUTHORITY = {
    "native_docx": (6, 1.00),
    "jisui_vision_ocr": (5, 0.95),
    "lionbolt": (4, 0.85),
    "bencom": (3, 0.80),
    "legallib": (2, 0.75),
    "codex_ocr": (1, 0.60),
}
GRANULARITY_MIN_RATIO = 0.20   # 最富源のblock数比

@dataclass
class Snapshot:
    source_system: str
    blocks: list                       # [{type,no?,title?,text?,blanks?}]
    provenance_group: Optional[str] = None

@dataclass
class Canonical:
    canonical_source: str
    blocks: list
    blanks_total: int
    block_count: int
    sources_used: list
    agreement: dict                    # base_block_key -> [corroborating sources]
    discrepancies: list                # 基底に無い他源block(review)
    ocr_error_classes: list
    corrections: list
    confidence: dict
    notes: str = ""

def _bkey(b: dict) -> str:
    base = (b.get("no") or "") + "|" + (b.get("title") or norm_title_v1(b.get("text","") )[:24])
    return b["type"] + ":" + base

def _detect_errors(text: str):
    found=[]
    for wrong,right in ERROR_CLASSES:
        if wrong and wrong in (text or ""):
            found.append((wrong,right))
    return found

def merge_snapshots(snaps: list[Snapshot]) -> Canonical:
    assert snaps, "no snapshots"
    # 1) 基底選択: 粒度ガード → 源優先
    richest = max(len(s.blocks) for s in snaps)
    eligible = [s for s in snaps if len(s.blocks) >= GRANULARITY_MIN_RATIO*richest and len(s.blocks)>0]
    if not eligible: eligible = snaps
    base = max(eligible, key=lambda s: SOURCE_AUTHORITY.get(s.source_system,(0,0.5))[0])
    others = [s for s in snaps if s is not base]

    # 2) crosswalk index(他源)
    other_idx = {}
    for s in others:
        for b in s.blocks:
            other_idx.setdefault(_bkey(b), []).append((s.source_system, b))

    agreement={}; ocr_errs=[]; corrections=[]; out_blocks=[]
    for b in base.blocks:
        b = dict(b)
        k=_bkey(b)
        corrob=[src for (src,_) in other_idx.get(k,[])]
        if corrob: agreement[k]=corrob
        # 品質: 基底textの確定誤謬クラス
        errs=_detect_errors(b.get("text",""))
        if errs:
            corrected=b.get("text","")
            for wrong,right in errs:
                corrected=corrected.replace(wrong,right)
                ocr_errs.append({"class":f"{wrong}→{right}","block":k})
            # 他源の対応blockが正しい綴りで裏取りできれば corrected採用
            corroborated_fix = any(right in (ob.get("text","") or "")
                                   for (_,ob) in other_idx.get(k,[]) for _,right in errs)
            b["text_corrected"]=corrected
            b["quality_verdict"]="error_confirmed"
            corrections.append({"block":k,"from":base.source_system,
                                "corroborated_by_source": corroborated_fix})
        else:
            b["quality_verdict"]="legitimate"
        out_blocks.append(b)

    # 3) discrepancies: 他源にあって基底に無いblock(自動追加しない=review)
    base_keys={_bkey(b) for b in base.blocks}
    seen=set(); discr=[]
    for s in others:
        for b in s.blocks:
            k=_bkey(b)
            if k not in base_keys and k not in seen:
                seen.add(k)
                discr.append({"source":s.source_system,"block_key":k,"type":b["type"],
                              "no":b.get("no"),"title":b.get("title"),"text":(b.get("text") or "")[:60]})

    # 4) confidence分解
    src_auth=SOURCE_AUTHORITY.get(base.source_system,(0,0.5))[1]
    if len(snaps)==1:
        merge_conf=1.0
    else:
        # 裏取り率 / discrepancy で減点
        agreed=len(agreement); merge_conf=1.0 if not discr and agreed>0 else (0.8 if agreed>0 else 0.9)
    any_uncorrected=any(bk.get("quality_verdict")=="error_confirmed" and
                        not any(c["block"]==_bkey(bk) and c["corroborated_by_source"] for c in corrections)
                        for bk in out_blocks)
    quality_adj=0.7 if any_uncorrected else 1.0
    final=round(src_auth*merge_conf*quality_adj,3)

    blanks_total=sum(len(b.get("blanks",[])) for b in out_blocks)
    return Canonical(base.source_system, out_blocks, blanks_total, len(out_blocks),
                     [s.source_system for s in snaps], agreement, discr, ocr_errs, corrections,
                     {"source_authority":src_auth,"merge":merge_conf,"quality_adjustment":quality_adj,"final":final})

# ----------------------------- 自己テスト -----------------------------
if __name__=="__main__":
    ok=0; tot=0
    def ck(name,cond):
        global ok,tot; tot+=1; print(("PASS" if cond else "FAIL"),name); ok+=bool(cond)

    # 1) 単一源(自炊vision)
    s_v=Snapshot("jisui_vision_ocr",[
        {"type":"heading","text":"製造委託基本契約書"},
        {"type":"clause","no":"第1条","title":"目的","text":"…"},
        {"type":"clause","no":"第2条","title":"個別契約","text":"…"}])
    c=merge_snapshots([s_v])
    ck("単一源=基底自炊", c.canonical_source=="jisui_vision_ocr" and c.confidence["final"]==0.95)

    # 2) 二源一致(自炊vision+lionbolt) → 基底=自炊vision・裏取りあり
    s_lb=Snapshot("lionbolt",[
        {"type":"heading","text":"製造委託基本契約書"},
        {"type":"clause","no":"第1条","title":"目的","text":"…"},
        {"type":"clause","no":"第2条","title":"個別契約","text":"…"}])
    c2=merge_snapshots([s_v,s_lb])
    ck("二源:基底=自炊vision", c2.canonical_source=="jisui_vision_ocr")
    ck("二源:裏取りagreementあり", len(c2.agreement)>=2 and not c2.discrepancies and c2.confidence["merge"]==1.0)

    # 3) 品質: bencomに廷→延誤字、lionbolt正→corrected裏取り
    s_b=Snapshot("bencom",[{"type":"clause","no":"第282条","title":"公判延","text":"第282条〔公判延〕の趣旨"}])
    s_lb2=Snapshot("lionbolt",[{"type":"clause","no":"第282条","title":"公判廷","text":"第282条〔公判廷〕の趣旨"}])
    c3=merge_snapshots([s_b,s_lb2])  # 基底はlionbolt(優先>bencom)
    ck("基底=lionbolt(優先)", c3.canonical_source=="lionbolt")
    # 誤字は基底(lionbolt=正)には無い → エラー0
    ck("正基底ならOCRエラー0", len(c3.ocr_error_classes)==0)
    # 逆: bencomだけ → 誤字検出・未裏取り→quality0.7
    c3b=merge_snapshots([s_b])
    ck("誤字基底のみ→error_confirmed", len(c3b.ocr_error_classes)==1 and c3b.confidence["quality_adjustment"]==0.7)

    # 4) 粒度ガード: native_docxが1block(スタブ) vs 自炊vision10block → 基底=自炊vision
    s_nd=Snapshot("native_docx",[{"type":"heading","text":"契約書"}])
    s_v10=Snapshot("jisui_vision_ocr",[{"type":"clause","no":f"第{i}条","text":"…"} for i in range(1,11)])
    c4=merge_snapshots([s_nd,s_v10])
    ck("粒度ガード:スタブ高優先は基底外", c4.canonical_source=="jisui_vision_ocr")

    # 5) discrepancy: 他源に基底に無い第4条 → review(自動追加しない)
    s_base=Snapshot("jisui_vision_ocr",[{"type":"clause","no":"第1条","text":"a"},{"type":"clause","no":"第2条","text":"b"}])
    s_more=Snapshot("lionbolt",[{"type":"clause","no":"第1条","text":"a"},{"type":"clause","no":"第4条","text":"d"}])
    c5=merge_snapshots([s_base,s_more])
    ck("discrepancyはreviewに出る(非追加)",
       any(d["no"]=="第4条" for d in c5.discrepancies) and all(b.get("no")!="第4条" for b in c5.blocks))
    ck("discrepancyありでmerge減点", c5.confidence["merge"]==0.8)

    print(f"\n{ok}/{tot} passed")
