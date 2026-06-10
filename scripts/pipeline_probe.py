"""パイプライン進捗の probe ランナー + 状態コレクタ (v0.2.1).

実ファイルシステム (Box 同期 / ~/alo-ai 等) を走査し、各ステージの「実状態」を
小さな snapshot.json に落とす。重い走査は Mac 側で実行し、snapshot だけを
本リポジトリへ戻せば web 側でダッシュボード描画・差分追跡ができる。

ここで言う status は **runtime_status（実行・運用状態）** であり、
DD-STATUS-REGISTRY の artifact lifecycle（draft/candidate/accepted/canonical…）
とは別軸。混同しないこと（GPT DDPROGRESS 監査 v0.1 指摘#2）。

probe 種別:
  * count     : glob 件数 vs expected (取得率)。「出せてない/未取得」を見る。
  * exists    : glob にマッチが 1 つでもあるか (成果物の有無。% は出さない)。
  * roundtrip : 送信(REQUEST)/戻り(RESULT) を **front-matter の request_id /
                result_expected_filename を優先**して突合 (v0.2)。pending(未戻り)
                / orphan(送信なしの戻り) / stale(古い未戻り=詰まり) / duplicate
                (同一 request_id の重複送信) を出す。
  * orphan    : scan glob にあって declared globs に無い「未宣言成果物」を出す
                (manifest ドリフト検知。v0.2 追加)。

snapshot は純データ (status 判定は dashboard 側)。冪等・stdlib のみ。

v0.2.1 (GPT DDPROGRESS v0.2 再監査 N1/N2 クローズ):
  * N1: manifest 検証→拒否を ``collect()`` 自体へ移し、probe/dashboard 両経路を
        単一ソースで塞ぐ。不正 manifest は既定で ``ManifestError`` を送出。
  * N2: roundtrip で同一 request_id の重複送信を silent dedupe せず ``duplicate``
        として surface する (件数は distinct request_id のまま)。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

PROBE_VERSION = "0.2.1"
_JST = timezone(timedelta(hours=9))
VALID_PROBE_TYPES = frozenset({"count", "exists", "roundtrip", "orphan", "supabase"})

# roundtrip stem fallback: 末尾の役割サフィックスを落として送信/戻りを同一キーに。
_RT_SUFFIX = re.compile(
    r"[_\-]?(request|result|response|reply|answer|req|res|out|in|送信|戻り|依頼|回答)$",
    re.IGNORECASE,
)


def _glob(root: Path, pattern: str) -> list[Path]:
    return sorted(p for p in root.glob(pattern) if p.is_file())


def _stem_key(stem: str, key_pattern: str | None) -> str:
    if key_pattern:
        m = re.search(key_pattern, stem)
        return m.group(1) if m else stem
    return _RT_SUFFIX.sub("", stem)


def _read_front_matter(path: Path) -> dict[str, str]:
    """先頭 ``---`` ブロックの ``key: value`` を素朴に取り出す (stdlib, YAML不要)。"""
    fm: dict[str, str] = {}
    try:
        with path.open(encoding="utf-8") as f:
            first = f.readline()
            if first.strip() != "---":
                return fm
            for line in f:
                if line.strip() == "---":
                    break
                if ":" in line:
                    k, _, v = line.partition(":")
                    v = v.strip()
                    if " #" in v:  # 行末コメントを落とす
                        v = v.split(" #", 1)[0].strip()
                    fm[k.strip()] = v
    except Exception:
        return {}
    return fm


def _age_epoch(fm: dict[str, str], rid: str, path: Path) -> tuple[int, str]:
    """stale 判定の基準時刻。front-matter > request_id 日付 > mtime の順で確度高。"""
    for key in ("submitted_at", "created_at", "recorded_at"):
        val = fm.get(key)
        if val:
            try:
                return int(datetime.fromisoformat(val.replace("Z", "+00:00"))
                           .timestamp()), f"front_matter:{key}"
            except ValueError:
                pass
    if len(rid) >= 8 and rid[:8].isdigit():
        try:
            d = datetime.strptime(rid[:8], "%Y%m%d").replace(tzinfo=_JST)
            return int(d.timestamp()), "request_id_date"
        except ValueError:
            pass
    return int(path.stat().st_mtime), "mtime"


def _roundtrip(root: Path, probe: dict, label: str) -> dict:
    kp = probe.get("key_pattern")
    sent = _glob(root, probe["sent"])
    returned = _glob(root, probe["returned"])

    # 戻り側のマッチトークン (request_id / 実ファイル名 / stem キー)。
    ret_request_ids: set[str] = set()
    ret_names: set[str] = set()
    ret_stem_keys: set[str] = set()
    for p in returned:
        fm = _read_front_matter(p)
        if fm.get("request_id"):
            ret_request_ids.add(fm["request_id"])
        ret_names.add(p.name)
        ret_stem_keys.add(_stem_key(p.stem, kp))

    def is_matched(rid: str, expected: str | None) -> bool:
        return (rid in ret_request_ids
                or rid in ret_stem_keys
                or bool(expected and expected in ret_names))

    sent_rids: set[str] = set()
    sent_expected: set[str] = set()
    pending: list[dict] = []
    # N2: rid -> 送信ファイル名リスト。突合は代表 (最初の) 1 件で行うが、
    # 同一 request_id の重複送信は捨てずに集約して surface する。
    seen: dict[str, list[str]] = {}
    for p in sent:
        fm = _read_front_matter(p)
        rid = fm.get("request_id") or _stem_key(p.stem, kp)
        if rid in seen:
            seen[rid].append(p.name)  # 重複送信: 件数には数えず記録のみ
            continue
        seen[rid] = [p.name]
        expected = fm.get("result_expected_filename")
        sent_rids.add(rid)
        if expected:
            sent_expected.add(expected)
        if not is_matched(rid, expected):
            epoch, basis = _age_epoch(fm, rid, p)
            pending.append({"key": rid, "sent_file": p.name, "expected_result": expected,
                            "sent_epoch": epoch, "age_basis": basis})

    # orphan: どの sent にも対応しない戻り。
    orphan = []
    for p in returned:
        fm = _read_front_matter(p)
        rid = fm.get("request_id") or _stem_key(p.stem, kp)
        if rid in sent_rids or p.name in sent_expected:
            continue
        orphan.append(p.name)

    # N2: 同一 request_id に複数の送信ファイルが紐づくものを衝突として列挙。
    duplicates = [{"key": rid, "files": sorted(files)}
                  for rid, files in seen.items() if len(files) > 1]
    duplicates.sort(key=lambda d: d["key"])

    pending.sort(key=lambda x: x["sent_epoch"])
    cap = probe.get("detail_cap", 50)
    return {
        "type": "roundtrip", "label": label,
        "sent": len(seen), "returned": len(returned),
        "pending_count": len(pending), "pending": pending[:cap],
        "orphan_count": len(orphan), "orphan": sorted(orphan)[:cap],
        "duplicate_count": len(duplicates), "duplicate": duplicates[:cap],
        "max_age_hours": probe.get("max_age_hours", 24),
        "done": len(pending) == 0 and len(seen) > 0,
    }


def run_probe(root: Path, probe: dict) -> dict:
    ptype = probe.get("type")
    label = probe.get("label", ptype)

    if ptype == "count":
        files = _glob(root, probe["path"])
        expected = probe.get("expected")
        count = len(files)
        ratio = (min(count / expected, 1.0) if expected else (1.0 if count else 0.0))
        return {
            "type": "count", "label": label, "path": probe["path"],
            "count": count, "expected": expected, "ratio": round(ratio, 4),
            "done": (count >= expected) if expected else bool(count),
        }

    if ptype == "exists":
        files = _glob(root, probe["path"])
        # % は出さない: 成果物の有無のみ (GPT 指摘#5)。
        return {
            "type": "exists", "label": label, "path": probe["path"],
            "present": bool(files), "match_count": len(files), "done": bool(files),
        }

    if ptype == "roundtrip":
        return _roundtrip(root, probe, label)

    if ptype == "orphan":
        scan = _glob(root, probe["scan"])
        declared: set[Path] = set()
        for g in probe.get("declared", []):
            declared.update(_glob(root, g))
        orphans = [p.name for p in scan if p not in declared]
        cap = probe.get("detail_cap", 50)
        return {
            "type": "orphan", "label": label,
            "scan_count": len(scan), "declared_count": len(declared),
            "orphan_count": len(orphans), "orphan": sorted(orphans)[:cap],
            "done": len(orphans) == 0,
        }

    if ptype == "supabase":
        return _supabase_probe(probe, label)

    return {"type": ptype, "label": label, "error": f"unknown probe type: {ptype}"}


def _supabase_count(probe: dict) -> tuple[int | None, str | None]:
    """Supabase(PostgREST) でテーブル行数を取得 (stdlib only)。

    接続情報は env (``SUPABASE_URL`` / ``SUPABASE_KEY`` か ``SUPABASE_ANON_KEY``)。
    manifest には資格情報を書かない。env 無し・ネット不通は **例外を投げず**
    (None, 理由) を返し、呼び出し側で skipped 扱いにする (オフライン安全)。
    """
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY") or os.environ.get("SUPABASE_ANON_KEY")
    if not url or not key:
        return None, "SUPABASE_URL/KEY 未設定"
    table = probe.get("table")
    if not table:
        return None, "table 未指定"
    q = f"{url.rstrip('/')}/rest/v1/{table}?select=*"
    if probe.get("filter"):  # PostgREST クエリ (例: claim_scope=eq.cites)
        q += "&" + probe["filter"]
    req = urllib.request.Request(q, method="GET")
    req.add_header("apikey", key)
    req.add_header("Authorization", f"Bearer {key}")
    req.add_header("Prefer", "count=exact")
    req.add_header("Range-Unit", "items")
    req.add_header("Range", "0-0")  # 本体は取らず Content-Range の総数だけ見る
    if probe.get("schema"):
        req.add_header("Accept-Profile", probe["schema"])
    try:
        with urllib.request.urlopen(req, timeout=probe.get("timeout", 8)) as resp:
            content_range = resp.headers.get("Content-Range", "")  # 例 "0-0/17259"
    except Exception as e:  # 接続/HTTP/SSL いずれも skip 扱い (collect を壊さない)
        return None, f"接続失敗: {type(e).__name__}"
    total = content_range.split("/")[-1] if "/" in content_range else ""
    if total.isdigit():
        return int(total), None
    return None, f"count 取得失敗: {content_range!r}"


def _supabase_probe(probe: dict, label: str) -> dict:
    count, err = _supabase_count(probe)
    expected = probe.get("expected")
    if count is None:
        # 未接続/未設定: error ではなく skipped (オフライン環境では — 表示)。
        return {"type": "supabase", "label": label, "table": probe.get("table"),
                "available": False, "skipped": True, "note": err,
                "expected": expected, "done": False}
    ratio = (min(count / expected, 1.0) if expected else (1.0 if count else 0.0))
    return {"type": "supabase", "label": label, "table": probe.get("table"),
            "available": True, "count": count, "expected": expected,
            "ratio": round(ratio, 4),
            "done": (count >= expected) if expected else bool(count)}


# --- manifest 検証 (GPT 指摘#4) -------------------------------------------

def validate_manifest(manifest: dict) -> list[str]:
    """duplicate id / unknown dependency / cycle / unknown root / invalid probe を検出。"""
    errors: list[str] = []
    stages = manifest.get("stages", [])
    ids = [s.get("id") for s in stages]
    valid_roots = set(manifest.get("roots", {})) | {"default"}

    seen: set[str] = set()
    for sid in ids:
        if not sid:
            errors.append("stage に id が無い")
        elif sid in seen:
            errors.append(f"duplicate stage id: {sid}")
        seen.add(sid)

    id_set = set(ids)
    graph: dict[str, list[str]] = {}
    for s in stages:
        sid = s.get("id")
        deps = s.get("depends_on", [])
        graph[sid] = deps
        for d in deps:
            if d not in id_set:
                errors.append(f"unknown dependency: {sid} -> {d}")
        for pr in s.get("probes", []):
            ptype = pr.get("type")
            if ptype not in VALID_PROBE_TYPES:
                errors.append(f"invalid probe type in {sid}: {ptype}")
            if ptype == "supabase":
                if not pr.get("table"):  # fs root は使わない。table 必須。
                    errors.append(f"supabase probe に table が無い: {sid}")
                continue
            rk = pr.get("root", "default")
            if rk not in valid_roots:
                errors.append(f"unknown root in {sid}: {rk}")

    # cycle 検出 (DFS, 3色)。
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {sid: WHITE for sid in graph}

    def visit(n: str, path: list[str]) -> None:
        color[n] = GRAY
        for m in graph.get(n, []):
            if m not in color:
                continue
            if color[m] == GRAY:
                errors.append(f"cycle: {' -> '.join(path + [n, m])}")
            elif color[m] == WHITE:
                visit(m, path + [n])
        color[n] = BLACK

    for sid in graph:
        if color.get(sid) == WHITE:
            visit(sid, [])
    return errors


def _manifest_hash(manifest: dict) -> str:
    blob = json.dumps(manifest, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return "sha256:" + hashlib.sha256(blob).hexdigest()


class ManifestError(ValueError):
    """manifest 検証に失敗 (collect 既定で拒否)。``errors`` に個別の指摘を持つ。"""

    def __init__(self, errors: list[str]):
        self.errors = list(errors)
        super().__init__("manifest validation failed:\n"
                         + "\n".join(f"  - {e}" for e in self.errors))


def collect(roots: dict[str, Path] | Path, manifest: dict, *,
            refuse_on_invalid: bool = True) -> dict:
    """manifest を probe して snapshot を返す。

    N1: 検証→拒否はここ (単一ソース)。``pipeline_probe.main`` の一括収集も、
    ``pipeline_dashboard.py --root`` の収集+描画一発実行も、どちらもこの関数を
    通るので、不正 manifest は **既定で** ``ManifestError`` を送出して止める。
    観測目的で壊れた manifest でも走らせたい場合のみ ``refuse_on_invalid=False``
    を渡す (その場合 errors は snapshot の ``manifest_errors`` に記録される)。
    """
    if isinstance(roots, Path):
        roots = {"default": roots}

    errors = validate_manifest(manifest)
    if errors and refuse_on_invalid:
        raise ManifestError(errors)

    def resolve(probe: dict) -> Path:
        rk = probe.get("root", "default")
        return roots.get(rk) or roots.get("default") or next(iter(roots.values()))

    stages_out = {}
    for stage in manifest.get("stages", []):
        results = [run_probe(resolve(pr), pr) for pr in stage.get("probes", [])]
        stages_out[stage["id"]] = {"probes": results}

    return {
        "generated_at_jst": datetime.now(_JST).strftime("%Y-%m-%dT%H:%M:%S%z"),
        "collected_epoch": int(time.time()),
        "probe_version": PROBE_VERSION,
        "manifest_hash": _manifest_hash(manifest),
        "manifest_errors": errors,
        "roots": {k: str(v) for k, v in roots.items()},
        "manifest_version": manifest.get("version"),
        "stages": stages_out,
    }


def parse_roots(values: list[str]) -> dict[str, Path]:
    """``--root name=path`` を複数、または ``--root path`` 単体を dict 化。"""
    roots: dict[str, Path] = {}
    for v in values:
        if "=" in v:
            name, _, path = v.partition("=")
            roots[name.strip()] = Path(path).expanduser()
        else:
            roots["default"] = Path(v).expanduser()
    return roots


def load_manifest(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def print_manifest_error(err: ManifestError) -> None:
    """ManifestError を stderr に整形出力 (probe/dashboard 両 CLI 共通)。"""
    for e in err.errors:
        print(f"  ❌ manifest: {e}", file=sys.stderr)
    print("manifest validation FAILED", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="パイプライン状態コレクタ")
    ap.add_argument("--root", action="append", default=[], metavar="[NAME=]PATH",
                    help="走査ルート。複数可 (例: --root bookdx=/Box/... --root alo=~/alo-ai)")
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--out", required=True, help="snapshot.json 出力先")
    args = ap.parse_args(argv)

    if not args.root:
        ap.error("--root を最低 1 つ指定 (例: --root /path または --root alo=/path)")
    roots = parse_roots(args.root)
    manifest = load_manifest(Path(args.manifest))

    # GPT 指摘#4 / N1: 検証→拒否は collect() の単一ソースに集約。
    try:
        snap = collect(roots, manifest)
    except ManifestError as e:
        print_manifest_error(e)
        return 1

    Path(args.out).write_text(json.dumps(snap, ensure_ascii=False, indent=1),
                              encoding="utf-8")
    print(f"collected {len(snap['stages'])} stages, roots={list(roots)} -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
