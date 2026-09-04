"""安全绳的进程树去重 —— `judgment._run_upstream`。

**这条以前没有任何测试覆盖**，而它是承重件：每个 verdict runner 都靠它断言
「重跑上游，产物逐字节不变」。去重把展开从 2^(n-1) 降到每节点一次，
但**必须不削弱失败检测**——跳过是因为别人跑过了，不是因为不想跑。
"""

from __future__ import annotations

from pathlib import Path

from newlife.conform import judgment

CHEAP = "site"          # `python -m site` 打印路径即退出，够快且必定存在
MISSING = "newlife._no_such_module_for_testing"
REPO = Path(__file__).resolve().parents[4]


def test_runs_and_registers(tmp_path: Path) -> None:
    """没跑过的上游要真跑，并登记进账本。"""
    ledger = tmp_path / "ledger"
    ledger.write_text("")
    assert judgment._run_upstream(REPO, [CHEAP], ledger) is None
    assert ledger.read_text().split() == [CHEAP]


def test_skips_what_the_tree_already_ran(tmp_path: Path) -> None:
    """账本里已有的不再跑——这就是去重本身。"""
    ledger = tmp_path / "ledger"
    ledger.write_text(f"{CHEAP}\n")
    assert judgment._run_upstream(REPO, [CHEAP], ledger) is None
    # 没有被追加第二次：跳过是真跳过，不是跑完又写一遍
    assert ledger.read_text().split() == [CHEAP]


def test_failure_still_propagates(tmp_path: Path) -> None:
    """**去重不许削弱失败检测。** 上游非零退出仍要指名报出来。"""
    ledger = tmp_path / "ledger"
    ledger.write_text("")
    failed = judgment._run_upstream(REPO, [MISSING], ledger)
    assert failed is not None
    assert failed.ok is False
    assert failed.failed_runner == MISSING
    assert failed.returncode not in (None, 0)


def test_registers_before_running(tmp_path: Path) -> None:
    """先登记后执行：依赖成环时停下，而不是递归到死。

    失败的那个也留在账本里——它**跑过了**，只是没通过。
    """
    ledger = tmp_path / "ledger"
    ledger.write_text("")
    judgment._run_upstream(REPO, [MISSING], ledger)
    assert ledger.read_text().split() == [MISSING]
