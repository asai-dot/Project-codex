#!/usr/bin/env bash
#
# publish_box.sh — write a per-unit reconciliation result to the Box canonical.
#
# Usage: publish_box.sh <result.json>
#
# Modes (env BOX_MODE):
#   drive       (default) copy into a Box Drive synced local folder ($BOX_CANONICAL_DIR).
#               Simplest + most robust on the Mac Studio: Box Drive handles upload.
#   mcp-bridge  upload via Box MCP by delegating to a 1-shot `claude -p` that is
#               allowed only the Box upload tool. Use when no Box Drive mount is
#               available (e.g. cloud headless). Requires $BOX_CANONICAL_FOLDER_ID
#               and that the claude install has the Box MCP server configured.
#   none        do nothing (selftest / unconfigured). Exits 0.
#
# folder_id / canonical dir are head-supplied at dispatch (see ticket §2-1.4).
# If neither is configured, this exits non-zero so the caller logs a WARN — we do
# NOT silently pretend a ghost canonical exists.
#
set -euo pipefail

src="${1:?result json path required}"
[ -f "$src" ] || { echo "publish_box: source not found: $src" >&2; exit 1; }

BOX_MODE="${BOX_MODE:-drive}"
fname="$(basename "$src")"

case "$BOX_MODE" in
  none)
    echo "publish_box: BOX_MODE=none, skipping $fname"
    exit 0
    ;;

  drive)
    if [ -z "${BOX_CANONICAL_DIR:-}" ]; then
      echo "publish_box: BOX_CANONICAL_DIR not set (head must supply canonical path)" >&2
      exit 3
    fi
    [ -d "$BOX_CANONICAL_DIR" ] || { echo "publish_box: BOX_CANONICAL_DIR not a dir: $BOX_CANONICAL_DIR" >&2; exit 4; }
    # atomic-ish: copy to temp in the same dir, then mv
    tmp="$(mktemp "$BOX_CANONICAL_DIR/.$fname.XXXXXX")"
    cp "$src" "$tmp"
    mv -f "$tmp" "$BOX_CANONICAL_DIR/$fname"
    echo "publish_box: drive -> $BOX_CANONICAL_DIR/$fname"
    ;;

  mcp-bridge)
    if [ -z "${BOX_CANONICAL_FOLDER_ID:-}" ]; then
      echo "publish_box: BOX_CANONICAL_FOLDER_ID not set (head must supply folder_id)" >&2
      exit 3
    fi
    CLAUDE_BIN="${CLAUDE_BIN:-claude}"
    BOX_UPLOAD_TOOL="${BOX_UPLOAD_TOOL:-}"   # e.g. mcp__<box-server>__upload_file
    if [ -z "$BOX_UPLOAD_TOOL" ]; then
      echo "publish_box: BOX_UPLOAD_TOOL not set (the Box MCP upload tool name)" >&2
      exit 3
    fi
    "$CLAUDE_BIN" -p "Upload the local file at '$src' to Box folder id '$BOX_CANONICAL_FOLDER_ID' \
as '$fname'. If a file with that name already exists in the folder, upload a new version \
instead of duplicating. Report only success or the error." \
      --allowedTools "$BOX_UPLOAD_TOOL" >/dev/null
    echo "publish_box: mcp-bridge -> folder $BOX_CANONICAL_FOLDER_ID/$fname"
    ;;

  *)
    echo "publish_box: unknown BOX_MODE=$BOX_MODE" >&2
    exit 2
    ;;
esac
