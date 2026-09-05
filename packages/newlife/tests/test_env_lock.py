"""S1「环境未变」—— 从恒真改成真检查。

2026-09-06 一次外部评审发现：模板里 `s1 = prov["env_lock_sha256"] == file_digest(env.lock)` 两边是同一
时刻对同一个文件算的哈希，永远相等；四份真实问题的 runner 全是这个写法。恒真判据正是这个项目付过账的
那一类缺陷，这次出在自己随包发出去的模板里。

新的三件套：freeze 按当下环境重写 env.lock 并钉进预注册；runner 的 S1 = 运行时安装的包清单 == env.lock；
audit 的 DATA 段证明 env.lock 冻结后没动。**每一件都先证明它会红。**
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from newlife import cli, provenance, scaffold


def _repo(tmp_path: Path) -> Path:
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    for k, v in (("user.email", "t@t"), ("user.name", "t")):
        subprocess.run(["git", "-C", str(tmp_path), "config", k, v], check=True)
    (tmp_path / "baseline.txt").write_text("base\n")
    subprocess.run(["git", "-C", str(tmp_path), "add", "baseline.txt"], check=True)
    subprocess.run(
        ["git", "-C", str(tmp_path), "commit", "-qm", "baseline"], check=True
    )
    return tmp_path


def _waive(folder: Path) -> None:
    (folder / "goal.md").write_text(
        "<!--@goal_gate: not_applicable — 测的是环境检查，不是选题-->\n",
        encoding="utf-8",
    )
    with (folder / "prereg.md").open("a", encoding="utf-8") as fh:
        fh.write("\n<!--@pilot_gate: not_applicable — 同上-->\n")


def _s1_of_latest_pilot(folder: Path) -> bool:
    runs = sorted((folder / "pilot").glob("*/summary.json"))
    return json.loads(runs[-1].read_text(encoding="utf-8"))["units"][
        "S1_env_unchanged"
    ]["passed"]


def test_s1_goes_red_when_env_lock_no_longer_matches_the_live_environment(
    tmp_path: Path,
) -> None:
    """**恒真的那条永远不会红。** 这里逼它红：env.lock 多写一行不存在的包，S1 必须变 False。"""
    repo = _repo(tmp_path)
    folder = scaffold.init("2026-09-06-s1", cwd=repo)

    assert cli._pilot(folder) == 0
    assert _s1_of_latest_pilot(folder) is True  # env.lock 由 init 按同一环境写出

    with (folder / "env.lock").open("a", encoding="utf-8") as fh:
        fh.write("not-really-installed==9.9.9\n")
    assert cli._pilot(folder) == 0  # pilot 照样记账，H0 是信息
    assert _s1_of_latest_pilot(folder) is False


def test_pilot_output_is_labelled_exploratory_not_verdict(
    tmp_path: Path, capfd
) -> None:
    repo = _repo(tmp_path)
    folder = scaffold.init("2026-09-06-label", cwd=repo)
    assert cli._pilot(folder) == 0
    out = capfd.readouterr().out
    assert "PILOT (exploratory, no evidential weight)" in out
    assert "\nverdict:" not in out


def test_freeze_rewrites_env_lock_from_the_live_environment_and_pins_it(
    tmp_path: Path,
) -> None:
    """冻结时 env.lock 被按当下环境重写、提交、钉进预注册；之后改它，audit 变红。"""
    repo = _repo(tmp_path)
    folder = scaffold.init("2026-09-06-pin", cwd=repo)
    _waive(folder)
    (folder / "env.lock").write_text(
        "stale==0.0.0\n", encoding="utf-8"
    )  # 冻结前环境变过

    assert scaffold.freeze(folder, cwd=repo) == 0

    live = "\n".join(provenance.env_lock_lines()) + "\n"
    assert (folder / "env.lock").read_text(encoding="utf-8") == live
    assert (
        subprocess.run(
            [
                "git",
                "-C",
                str(repo),
                "status",
                "--porcelain",
                "--",
                "questions/2026-09-06-pin/env.lock",
            ],
            capture_output=True,
            text=True,
        ).stdout
        == ""
    )  # 已提交，工作区干净
    prereg = (folder / "prereg.md").read_text(encoding="utf-8")
    assert "## Frozen data checksums" in prereg
    assert "questions/2026-09-06-pin/env.lock" in prereg

    (folder / "results" / "summary.json").write_text("{}\n")
    subprocess.run(
        ["git", "-C", str(repo), "add", "questions/2026-09-06-pin/results"], check=True
    )
    subprocess.run(["git", "-C", str(repo), "commit", "-qm", "result"], check=True)
    assert scaffold.audit(folder, cwd=repo) == 0

    with (folder / "env.lock").open("a", encoding="utf-8") as fh:  # 冻结后环境变了
        fh.write("sneaked-in==1.0\n")
    assert scaffold.audit(folder, cwd=repo) != 0


def test_freeze_recovery_points_to_a_new_folder_not_a_rename(tmp_path: Path) -> None:
    """旧提示让人 `git mv prereg.md prereg-v2.md`，但所有命令都读 prereg.md，照做走不通。"""
    repo = _repo(tmp_path)
    folder = scaffold.init("2026-09-06-recover", cwd=repo)
    subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-qm", "全提交了"], check=True)
    try:
        scaffold.freeze(folder, cwd=repo)
    except SystemExit as exc:
        message = str(exc)
    else:
        raise AssertionError("freeze 应当拒绝")
    assert "newlife init 2026-09-06-recover-v2" in message
    assert "git mv" not in message
