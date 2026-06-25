#!/usr/bin/env python3
"""run_local_classify_http.py — ORCH-LOCAL-CLASSIFY-PILOT を HTTP API 経由で実行するドライバ。

背景: このMacでは `ollama run` / `ollama list` CLI が MLX/Metal 初期化で native crash する
       （libmlx mlx_random_key）。一方で ollama daemon の HTTP API (/api/generate) は正常。
       そこで run_local_classify.sh と同一仕様（同じ10種別・LIMIT・出力スキーマ/ファイル名・source=qen）
       を保ったまま、推論経路だけ CLI→HTTP に置き換える。

特徴:
  - 行番号で整列（id echo は長くモデルが復元失敗するため、内部で番号→idへ写像）。
  - チェックポイント(JSONL)に逐次追記。中断・再実行で resume。
  - タイムアウト/失敗の行は「その他」に偽装せず未分類のまま残し、resume で再挑戦。
  - 出力CSVはチェックポイントから input 順に再生成。実ラベルが付いた行のみ出力。

仕様正本: artifacts/periodical/ORCH-LOCAL-ARTICLE-TYPE_order_20260624.md
入力:   artifacts/periodical/article_join_dryrun_v0.1.csv (article_id, title)
出力:   artifacts/periodical/article_type_local_pilot_v0.1.csv (article_id,type,source)
read-only 派生生成。canonical/DB/外部公開なし。
"""
import csv, json, os, sys, urllib.request, urllib.error

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IN = os.path.join(REPO, "artifacts/periodical/article_join_dryrun_v0.1.csv")
OUT = os.path.join(REPO, "artifacts/periodical/article_type_local_pilot_v0.1.csv")
CKPT = os.path.join(REPO, "artifacts/periodical/.classify_pilot_ckpt.jsonl")
HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5")
LIMIT = int(os.environ.get("LIMIT", "2000"))
CHUNK = int(os.environ.get("CHUNK", "15"))
TIMEOUT = int(os.environ.get("TIMEOUT", "600"))

LABELS = ["判例評釈", "論説・論文", "解説", "立法・改正解説", "座談会・対談",
          "判例紹介", "書評", "資料", "連載・コラム", "その他"]
LABELSET = set(LABELS)

PROMPT_HEAD = (
    "次の各行は 番号<TAB>タイトル。各行をちょうど1つの種別に分類し、番号<TAB>種別 だけを1行ずつ返せ。"
    "種別は次のいずれかの語そのもの: " + ",".join(LABELS) + "。"
    "迷ったら その他。説明文は出力しない。\n----\n"
)


def gen(prompt):
    body = json.dumps({"model": MODEL, "prompt": prompt, "stream": False,
                       "options": {"temperature": 0}}).encode("utf-8")
    req = urllib.request.Request(HOST + "/api/generate", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return json.loads(r.read().decode("utf-8")).get("response", "")


def norm_label(s):
    s = s.strip()
    if s in LABELSET:
        return s
    for lab in LABELS:
        if lab in s:
            return lab
    if "判例" in s and "評釈" in s:
        return "判例評釈"
    if "判例" in s and "紹介" in s:
        return "判例紹介"
    return None


def classify_chunk(rows):
    """rows: list[(idx, aid, title)] -> dict idx->label（取れた分だけ）"""
    lines = [f"{i}\t{t}" for (i, _aid, t) in rows]
    resp = gen(PROMPT_HEAD + "\n".join(lines))
    out = {}
    for ln in resp.splitlines():
        ln = ln.strip()
        if not ln:
            continue
        if "\t" in ln:
            head = ln.split("\t", 1)
        elif ":" in ln or "：" in ln:
            head = ln.replace("：", ":").split(":", 1)
        else:
            head = ln.split(None, 1)
        if len(head) != 2:
            continue
        num = "".join(ch for ch in head[0] if ch.isdigit())
        if not num:
            continue
        lab = norm_label(head[1])
        if lab:
            out[int(num)] = lab
    return out


def load_ckpt():
    done = {}
    if os.path.exists(CKPT):
        with open(CKPT, encoding="utf-8") as f:
            for ln in f:
                ln = ln.strip()
                if not ln:
                    continue
                try:
                    o = json.loads(ln)
                    done[o["article_id"]] = o["type"]
                except Exception:
                    pass
    return done


def append_ckpt(recs):
    with open(CKPT, "a", encoding="utf-8") as f:
        for aid, lab in recs:
            f.write(json.dumps({"article_id": aid, "type": lab}, ensure_ascii=False) + "\n")


def write_csv(indexed, done):
    """input順に、実ラベルが付いた行のみ出力（その他偽装なし）。"""
    with open(OUT, "w", encoding="utf-8", newline="") as w:
        wr = csv.writer(w)
        wr.writerow(["article_id", "type", "source"])
        for (_i, aid, _t) in indexed:
            if aid in done:
                wr.writerow([aid, done[aid], "qen"])


def main():
    if not os.path.exists(IN):
        print(f"入力なし: {IN}", file=sys.stderr); sys.exit(2)
    rows = []
    with open(IN, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            aid = (r.get("article_id") or "").strip()
            t = (r.get("title") or "").replace("\t", " ").strip()
            if aid and t:
                rows.append((aid, t))
            if len(rows) >= LIMIT:
                break
    indexed = [(i, aid, t) for i, (aid, t) in enumerate(rows)]
    done = load_ckpt()
    todo = [(i, aid, t) for (i, aid, t) in indexed if aid not in done]
    print(f"[classify-http] model={MODEL} 全{len(indexed)} 済{len(done)} 残{len(todo)} chunk={CHUNK} timeout={TIMEOUT}", flush=True)

    for start in range(0, len(todo), CHUNK):
        chunk = todo[start:start + CHUNK]
        try:
            got = classify_chunk(chunk)
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            print(f"[classify-http] chunk@{start} 失敗(継続/未分類のまま): {e}", file=sys.stderr, flush=True)
            got = {}
        recs = []
        for (i, aid, _t) in chunk:
            if i in got:
                done[aid] = got[i]
                recs.append((aid, got[i]))
        if recs:
            append_ckpt(recs)
        write_csv(indexed, done)  # 逐次に最新CSVを反映
        print(f"[classify-http] 進捗 {len(done)}/{len(indexed)} (今回chunk {len(recs)}/{len(chunk)})", flush=True)

    cov = len(done)
    print(f"[classify-http] 完了 出力{OUT} 分類済{cov}/{len(indexed)} ({100*cov//max(1,len(indexed))}%)", flush=True)


if __name__ == "__main__":
    main()
