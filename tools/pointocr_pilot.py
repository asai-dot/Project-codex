#!/usr/bin/env python3
"""
ポイントOCR パイロット runner（Mac/ワーカー側で実行）
tmplstruct v0.4 — 自炊600dpi画像を基準に、書式ページだけを Claude vision でOCRし式構造JSONを得る。

前提環境変数:
  BOX_TOKEN        : Box API アクセストークン（Developer/JWT/OAuth いずれか）
  ANTHROPIC_API_KEY: Claude API キー
  SUPABASE_URL, SUPABASE_KEY : (任意) bib_toc を直接引く場合

なぜMac側か:
  リモート実行環境では Box get_preview_page が空(0byte)を返し、600dpi画像を取得できない。
  本スクリプトは Box の PNG representation を直接取得して vision に渡す。

使い方:
  python pointocr_pilot.py --box-file-id 2150796103179 \
      --pages 158-167,61-70 --out out/keiyakukaisho
"""
import os, sys, json, time, argparse, urllib.request, urllib.error

BOX="https://api.box.com/2.0"
ANTHROPIC="https://api.anthropic.com/v1/messages"
MODEL="claude-opus-4-8"   # 最新の高精度モデル。コスト優先なら claude-sonnet-4-6

# === ポイントOCR 固定プロンプト（式の体裁を保って構造化／解説本文は拾わない） ===
SYS = (
 "あなたは法律書の『書式（契約書・合意書・通知書・議事録・申請書等）』ページを構造化する専門OCRです。"
 "渡された600dpiページ画像から、書式部分のみを、体裁を保ったまま構造化してください。"
 "解説・地の文・脚注の本文は本文として混ぜず notes に要点だけ残します。"
 "空欄は ___ 、選択肢は □ で表記し、当事者名・日付・金額等のプレースホルダは blanks に列挙します。"
)
USER_TMPL = (
 "この画像は『{title}』のスキャン {page} ページ目です。"
 "書式が含まれる場合のみ、次のJSONスキーマで返してください（書式が無ければ {{\"forms\":[]}}）。\n"
 "{schema}"
)
SCHEMA = {
  "forms": [{
    "form_title": "string（例: 共同研究開発契約書／解除通知書）",
    "form_kind": "contract|agreement|notice|minutes|application|bylaw|other",
    "page_from": "int", "page_to": "int",
    "blocks": [
      {"type":"heading|party|recital|clause|item|signature|date|attachment|note",
       "no":"string(任意: 第1条 等)", "text":"string",
       "blanks":["string(空欄ラベル)"]}
    ],
    "blanks_total":"int", "clause_count":"int",
    "notes":"string(記載上の注意・別紙参照など)"
  }]
}

def box_png(file_id, page, dim=2048):
    """Box の PNG representation で 1ページ取得（[png?dimensions=...] 表現）。"""
    url=f"{BOX}/files/{file_id}?fields=representations"
    req=urllib.request.Request(url, headers={
        "Authorization":f"Bearer {os.environ['BOX_TOKEN']}",
        "X-Rep-Hints":f"[png?dimensions={dim}x{dim}]"})
    info=json.load(urllib.request.urlopen(req))
    reps=info["representations"]["entries"]
    png=next(r for r in reps if r["representation"]=="png")
    tmpl=png["content"]["url_template"]
    # ページは asset_path で指定（1.png, 2.png ...）
    asset=tmpl.replace("{+asset_path}", f"{page}.png")
    # 表現生成を待つ
    for _ in range(30):
        s=png["status"]["state"]
        if s=="success": break
        time.sleep(2)
        info=json.load(urllib.request.urlopen(req)); png=next(r for r in info["representations"]["entries"] if r["representation"]=="png")
    r2=urllib.request.Request(asset, headers={"Authorization":f"Bearer {os.environ['BOX_TOKEN']}"})
    return urllib.request.urlopen(r2).read()  # PNG bytes

def ocr(img_bytes, title, page):
    import base64
    body={
      "model":MODEL,"max_tokens":4096,"system":SYS,
      "messages":[{"role":"user","content":[
        {"type":"image","source":{"type":"base64","media_type":"image/png",
           "data":base64.b64encode(img_bytes).decode()}},
        {"type":"text","text":USER_TMPL.format(title=title,page=page,
           schema=json.dumps(SCHEMA,ensure_ascii=False))}
      ]}]}
    req=urllib.request.Request(ANTHROPIC, data=json.dumps(body).encode(),
        headers={"x-api-key":os.environ["ANTHROPIC_API_KEY"],
                 "anthropic-version":"2023-06-01","content-type":"application/json"})
    resp=json.load(urllib.request.urlopen(req))
    txt="".join(b["text"] for b in resp["content"] if b["type"]=="text")
    try: return json.loads(txt[txt.find("{"):txt.rfind("}")+1])
    except Exception: return {"_raw":txt}

def parse_pages(spec):
    out=[]
    for part in spec.split(","):
        if "-" in part: a,b=part.split("-"); out+=list(range(int(a),int(b)+1))
        else: out.append(int(part))
    return out

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--box-file-id", required=True)
    ap.add_argument("--pages", required=True, help="例 158-167,61-70")
    ap.add_argument("--title", default="契約解消の法律実務")
    ap.add_argument("--out", default="out")
    a=ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    for p in parse_pages(a.pages):
        try:
            png=box_png(a.box_file_id, p)
            res=ocr(png, a.title, p)
            json.dump(res, open(f"{a.out}/p{p:03d}.json","w"), ensure_ascii=False, indent=2)
            nf=len(res.get("forms",[])) if isinstance(res,dict) else 0
            print(f"p{p}: forms={nf}")
        except urllib.error.HTTPError as e:
            print(f"p{p}: HTTP {e.code} {e.reason}", file=sys.stderr)
        time.sleep(1)

if __name__=="__main__":
    main()
