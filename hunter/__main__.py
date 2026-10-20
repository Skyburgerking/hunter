# -*- coding: utf-8 -*-
""

import os
import sys

from .easy import ALIASES, solve, watch

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EASY_DIR = os.path.join(HERE, "specs", "easy")

USAGE = """用法：
  python -m hunter list               内置任务清单
  python -m hunter tetris             直接跑 specs/easy/tetris.json
  python -m hunter run <json>         跑任意傻瓜 JSON
  python -m hunter watch <json>       回放最优权重

选项：
  --episodes N   回合数（默认 JSON 里的 episodes，或 60）
  --seed S       随机种子（默认 7）
  --cap N        单局步数上限
  --no-sign      跳过符号核对
  --quiet        少打印
"""


def _options(argv):
    opts = {"episodes": None, "seed": None, "cap": None,
            "sign": None, "verbose": True}
    rest = []
    i = 0
    while i < len(argv):
        item = argv[i]
        if item == "--episodes":
            opts["episodes"] = int(argv[i + 1]); i += 2
        elif item == "--seed":
            opts["seed"] = int(argv[i + 1]); i += 2
        elif item == "--cap":
            opts["cap"] = int(argv[i + 1]); i += 2
        elif item == "--no-sign":
            opts["sign"] = False; i += 1
        elif item == "--quiet":
            opts["verbose"] = False; i += 1
        else:
            rest.append(item); i += 1
    return opts, rest


def _resolve(name):
    ""
    if os.path.exists(name):
        return name
    candidate = os.path.join(EASY_DIR, name + ".json")
    if os.path.exists(candidate):
        return candidate
    return name


def _list():
    print("内置任务（specs/easy/ 里也有对应 JSON，可以直接改）")
    seen = {}
    for alias, target in ALIASES.items():
        seen.setdefault(target, []).append(alias)
    for target, names in sorted(seen.items()):
        mark = "●" if os.path.exists(
            os.path.join(EASY_DIR, names[0] + ".json")) else "○"
        print("  %s %-16s %s" % (mark, " / ".join(names), target))
    print("\n● = 已经有傻瓜 JSON；○ = 还没写，可自己建一份")


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        print(USAGE)
        _list()
        return 0
    cmd = argv.pop(0)
    if cmd in ("-h", "--help", "help"):
        print(USAGE)
        return 0
    if cmd in ("list", "ls"):
        _list()
        return 0

    opts, rest = _options(argv)
    if cmd in ("run", "watch"):
        if not rest:
            print(USAGE)
            return 2
        source = _resolve(rest[0])
    else:
        source = _resolve(cmd)

    if cmd == "watch":
        watch(source, seed=opts["seed"] or 9001, verbose=opts["verbose"],
              cap=opts["cap"])
        return 0

    solve(source, episodes=opts["episodes"], seed=opts["seed"],
          verbose=opts["verbose"], sign_check=opts["sign"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
