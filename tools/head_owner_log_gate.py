#!/usr/bin/env python3
"""head_owner_log_gate.py — ORCH 検収の機械判定ゲート（DD-ORCH-CONTINUITY-001 v0.3）

ORCH 発注書 と worker RESULT の HEAD_OWNER_LOG 照合 field を読み、7 reject code で判定する。
「信用ではなく照合」: 自然言語の『読みました』は見ない。ID と commit で刺す。

使い方:
  tools/head_owner_log_gate.py --orch <ORCH.md> --result <RESULT.md> [--log <HEAD_OWNER_LOG.md>] [--repo <dir>]
  終了コード: 0=ACCEPT / 1=REJECT(1件以上) / 2=入力エラー・lint(旧alias)

正本語彙(旧alias禁止・binding note 3):
  ORCH   : required_log_commit / required_digest_id / required_standing_ids
  RESULT : read_log_commit / read_digest_id / read_standing_ids

7 reject code:
  REJECT_MISSING_DIGEST / REJECT_STALE_DIGEST / REJECT_STALE_LOG_COMMIT /
  REJECT_STANDING_UNREAD / REJECT_REQUIRED_STANDING_OMITTED /
  REJECT_STANDING_OVERFLOW / REJECT_INLINE_HISTORY
"""
import argparse
import re
import subprocess
import sys

STANDING_CAP = 20
DEPRECATED = [
    "context_log_digest_id", "read_context_log_digest_id",
    "head_owner_log_commit", "read_head_owner_log_commit",
    "standing_ids_required", "standing_ids_checked",
]


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def scalar(text, key):
    """`key: value` を1つ拾う（front-matter/body どちらでも）。list/コメントは除く。"""
    m = re.search(r"(?m)^\s*%s\s*:\s*([^\[\n#]+?)\s*(?:#.*)?$" % re.escape(key), text)
    if not m:
        return None
    v = m.group(1).strip().strip("`\"'")
    return v or None


def id_list(text, key):
    """`key: [a, b]` または YAML ブロックリストを拾う。"""
    m = re.search(r"(?m)^\s*%s\s*:\s*\[([^\]]*)\]" % re.escape(key), text)
    if m:
        return [x.strip().strip("`\"'") for x in m.group(1).split(",") if x.strip()]
    # ブロックリスト
    m = re.search(r"(?m)^\s*%s\s*:\s*$" % re.escape(key), text)
    if m:
        out, rest = [], text[m.end():]
        for line in rest.splitlines():
            mm = re.match(r"\s*-\s*(\S+)", line)
            if mm:
                out.append(mm.group(1).strip("`\"'"))
            elif line.strip() and not line.startswith(" "):
                break
        return out
    return []


def git_show(repo, commit, path):
    try:
        return subprocess.run(
            ["git", "-C", repo, "show", f"{commit}:{path}"],
            capture_output=True, text=True, check=True).stdout
    except subprocess.CalledProcessError:
        return None


def is_ancestor(repo, anc, desc):
    """anc が desc の祖先(または同一)なら True。"""
    if not anc or not desc:
        return None
    r = subprocess.run(["git", "-C", repo, "merge-base", "--is-ancestor", anc, desc],
                       capture_output=True)
    return r.returncode == 0


def parse_standings(log_text):
    """HEAD_OWNER_LOG の STANDING を [(id, enforcement, status), ...] に。"""
    out = []
    blocks = re.split(r"(?m)^- standing_id:\s*", log_text)
    for b in blocks[1:]:
        sid = b.splitlines()[0].strip()
        enf = re.search(r"enforcement\s*:\s*(\w+)", b)
        sta = re.search(r"status\s*:\s*(\w+)", b)
        out.append((sid, enf.group(1) if enf else "", sta.group(1) if sta else ""))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--orch", required=True)
    ap.add_argument("--result", required=True)
    ap.add_argument("--log", help="HEAD_OWNER_LOG.md。省略時は required_log_commit:docs/alo/HEAD_OWNER_LOG.md")
    ap.add_argument("--repo", default=".")
    ap.add_argument("--log-path-in-repo", default="docs/alo/HEAD_OWNER_LOG.md")
    a = ap.parse_args()

    orch, result = read(a.orch), read(a.result)
    rejects, notes = [], []

    # lint: 旧 alias 禁止 (binding note 3)
    alias_hits = [d for d in DEPRECATED if re.search(r"(?m)^\s*%s\s*:" % re.escape(d), orch + "\n" + result)]
    if alias_hits:
        print("LINT_FIELD_ALIAS: 旧field名を検出（正本語彙のみ可）:", ", ".join(sorted(set(alias_hits))), file=sys.stderr)
        return 2

    req_commit = scalar(orch, "required_log_commit")
    req_digest = scalar(orch, "required_digest_id")
    req_stand = id_list(orch, "required_standing_ids")
    read_commit = scalar(result, "read_log_commit")
    read_digest = scalar(result, "read_digest_id")
    read_stand = id_list(result, "read_standing_ids")

    # 1) MISSING_DIGEST
    if not read_digest:
        rejects.append(("REJECT_MISSING_DIGEST", "RESULT に read_digest_id が無い"))
    # 2) STALE_DIGEST (binding note 2: read は required と一致)
    elif req_digest and read_digest != req_digest:
        rejects.append(("REJECT_STALE_DIGEST", f"read_digest_id={read_digest} != required={req_digest}"))

    # 3) STALE_LOG_COMMIT: accept = required が read の祖先
    if not req_commit or not read_commit:
        rejects.append(("REJECT_STALE_LOG_COMMIT", "log_commit が欠落＝鮮度検証不能(fail-closed)"))
    else:
        anc = is_ancestor(a.repo, req_commit, read_commit)
        if anc is False:
            rejects.append(("REJECT_STALE_LOG_COMMIT",
                            f"required({req_commit[:9]}) は read({read_commit[:9]}) の祖先でない（古読み/分岐）"))
        elif anc is None:
            notes.append("merge-base 判定不能（commit 未取得の可能性）")

    # log を required_log_commit 時点で取得（binding note 1）
    log_text = None
    if a.log:
        log_text = read(a.log)
    elif req_commit:
        log_text = git_show(a.repo, req_commit, a.log_path_in_repo)
    if log_text is None:
        notes.append("HEAD_OWNER_LOG を解決できず STANDING 系チェックをスキップ")
    else:
        standings = parse_standings(log_text)
        active = [s for s in standings if s[2] == "active"]
        active_global_req = {s[0] for s in active if s[1] == "global_required"}

        # 4) STANDING_UNREAD: required ⊄ read
        missing = [s for s in req_stand if s not in read_stand]
        if missing:
            rejects.append(("REJECT_STANDING_UNREAD", f"required だが未読: {missing}"))
        # 5) REQUIRED_STANDING_OMITTED: ORCH が active global_required を網羅しない
        omitted = sorted(active_global_req - set(req_stand))
        if omitted:
            rejects.append(("REJECT_REQUIRED_STANDING_OMITTED", f"ORCH required に欠落 global_required: {omitted}"))
        # 6) STANDING_OVERFLOW
        if len(active) > STANDING_CAP:
            rejects.append(("REJECT_STANDING_OVERFLOW", f"active standing {len(active)} > {STANDING_CAP}"))

    # 7) INLINE_HISTORY (保守的 heuristic・binding note 4)
    dialog = len(re.findall(r"(?m)^\s*(owner|head|user|assistant)\s*[:：]", orch))
    big_fence = any(len(b) > 2000 for b in re.findall(r"```.*?```", orch, re.S))
    if dialog >= 6 or big_fence:
        rejects.append(("REJECT_INLINE_HISTORY",
                        f"会話履歴の長文 inline 疑い（dialog_lines={dialog}, big_fence={big_fence}）"))

    # 出力
    for n in notes:
        print(f"NOTE: {n}", file=sys.stderr)
    if rejects:
        for code, why in rejects:
            print(f"{code}: {why}")
        print(f"\nVERDICT: REJECT ({len(rejects)} 件)")
        return 1
    print("VERDICT: ACCEPT — 7 reject code すべて非該当")
    return 0


if __name__ == "__main__":
    sys.exit(main())
