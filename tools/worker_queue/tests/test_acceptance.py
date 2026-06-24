"""検収テスト: Worker Queue が「止まっても 1 タスク分・再開可能」を満たすか固定する。

シナリオは §6 復旧手順そのもの:
  drain -> 中断 -> recover で状態確定 -> 続きから次の 1 件。
"""

import os

from conftest import write_result

from alo_worker.cli import main
from alo_worker.queue import scan


def run(root, *argv):
    return main(["--root", root, *argv])


def test_acceptance_drain_one_by_one(queue_root):
    # 1) P0 を claim -> 作業 -> done
    assert run(queue_root, "claim", "W-20260623-001") == 0
    write_result(queue_root, "done", "W-20260623-001", label="WORKER_PASS")
    assert run(queue_root, "complete", "W-20260623-001") == 0

    # 2) doing は空に戻り、次の 1 件 (P1) が取れる
    q = scan(queue_root)
    assert q.counts()["in_progress"] == 0
    assert q.counts()["done"] == 1

    # 3) P1 を claim -> blocker に当たって block
    assert run(queue_root, "claim", "W-20260623-002") == 0
    write_result(queue_root, "blocked", "W-20260623-002", label="WORKER_BLOCKED",
                 body="## Blocker\n対象テストが存在しない。\n")
    assert run(queue_root, "block", "W-20260623-002") == 0

    q = scan(queue_root)
    assert q.counts()["blocked"] == 1
    assert q.counts()["in_progress"] == 0


def test_acceptance_interrupt_then_recover(queue_root):
    # claim だけして「止まった」状態 (doing に中断 task が残る)
    run(queue_root, "claim", "W-20260623-001")
    q = scan(queue_root)
    assert q.counts()["in_progress"] == 1

    # 再開: recover が「RESULT 未作成 -> 状態確定せよ」を促す (exit 0, accident 無し)
    assert run(queue_root, "recover") == 0

    # 作業実体が未完だったので blocked に畳む
    write_result(queue_root, "blocked", "W-20260623-001", label="WORKER_BLOCKED")
    assert run(queue_root, "block", "W-20260623-001") == 0
    assert scan(queue_root).counts()["in_progress"] == 0


def test_acceptance_idempotent_replay(queue_root):
    # 同じ遷移を二度流しても二重移動しない
    run(queue_root, "claim", "W-20260623-001")
    write_result(queue_root, "done", "W-20260623-001", label="WORKER_PASS")
    run(queue_root, "complete", "W-20260623-001")
    # 二度目の complete は no-op (already)
    assert run(queue_root, "complete", "W-20260623-001") == 0
    assert scan(queue_root).counts()["done"] == 1
    assert not os.path.exists(os.path.join(queue_root, "doing", "W-20260623-001.md"))
