"""alo-worker — Claude Code Worker Queue の単一書き手 CLI。

``docs/worker_queue/`` の inbox / doing / done / blocked レーンを「フォルダ位置=状態」
として強制する。Claude Code ワーカーに巨大で曖昧なタスクを渡すと止まる — だから
5〜15 分単位の作業票 (worker task) に切り、台帳で進捗を縛り、止まっても 1 タスク分の
損失で済み、再開すれば続きから進む“作業機械”にする。

設計の双子は ``tools/gpt_audit`` (GPT 目付け役レーン)。あちらは検査官 (GPT) の行き帰りを
機械化する。こちらは作業者 (Claude Code) の inbox→doing→done/blocked を機械化する。
"""

from __future__ import annotations

__version__ = "0.1.0"
