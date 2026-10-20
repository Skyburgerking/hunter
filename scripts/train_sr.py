# -*- coding: utf-8 -*-
""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import os
import re
import subprocess
import sys


from hunter.core import BASES, GedaCore  # noqa: E402

EXE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "_gh", "StackRabbit-master", "sr_play.exe")

NAMES = ["lines", "bump", "holes", "landing",
         "row_trans", "col_trans", "wells", "eroded", "height"]

VALUES = [
    [0.0, 0.5, 1.0, 1.5, 2.0, 3.0],      # lines
    [0.0, -0.1, -0.25, -0.5, -1.0, -2.0],  # bump
    [0.0, -0.5, -1.0, -2.0, -3.0, -5.0],   # holes
    [0.0, -0.1, -0.25, -0.5, -1.0, -2.0],  # landing
    [0.0, -0.1, -0.3, -0.6, -1.0, -2.0],   # row transitions
    [0.0, -0.1, -0.3, -0.6, -1.0, -2.0],   # col transitions
    [0.0, -0.1, -0.3, -0.6, -1.0, -2.0],   # wells
    [0.0, 0.2, 0.5, 1.0, 1.5, 2.0],        # eroded
    [0.0, -0.2, -0.5, -1.0, -2.0, -3.0],   # height
]

SCORE_RE = re.compile(r"score=(-?\d+) lines=(\d+) pieces=(\d+)")


def decode(segment):
    return [VALUES[i][BASES.index(segment[i]) % len(VALUES[i])]
            for i in range(9)]


def play(weights, max_lines=3000, seed=1, timeout=180):
    args = [str(w) for w in weights] + [str(max_lines), "0", str(seed)]
    try:
        r = subprocess.run([EXE] + args, capture_output=True,
                           text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return 0, 0, 0
    m = SCORE_RE.search(r.stdout)
    if not m:
        return 0, 0, 0
    return int(m.group(1)), int(m.group(2)), int(m.group(3))


def evaluate(weights, seeds=(1, 2, 3), max_lines=3000):
    ""
    scores = [play(weights, max_lines, s) for s in seeds]
    best = max(scores, key=lambda x: x[1])
    avg_lines = sum(s[1] for s in scores) / len(scores)
    return avg_lines, best


def main():
    episodes = int(sys.argv[1]) if len(sys.argv) > 1 else 60
    max_lines = int(sys.argv[2]) if len(sys.argv) > 2 else 2000
    if not os.path.exists(EXE):
        print("先编译:", EXE)
        return 1

    core = GedaCore({}, gene_len=80)
    best = {"lines": -1}
    history = []

    for ep in range(1, episodes + 1):
        seg = core.get_gene_segment(9)
        w = decode(seg)
        avg_lines, (score, lines, pieces) = evaluate(w, max_lines=max_lines)
        lines = avg_lines

        
        fitness = min(1.0, lines / 2500.0)
        core.record(fitness)
        core.reward_segment(seg, fitness)

        if lines > best["lines"]:
            best = {"lines": lines, "score": score,
                    "pieces": pieces, "weights": w, "segment": seg}
            mark = " *"
        else:
            mark = ""

        history.append({"ep": ep, "segment": seg, "weights": w,
                        "score": score, "lines": lines, "pieces": pieces})
        print("ep %3d  %s  avg %5.1f 行  best %4d 行 / %d 分 / %d 块%s"
              % (ep, seg, lines, score and 0 or 0, lines, 0, 0, mark) if False else
              "ep %3d  %s  avg %5.1f 行  best %4d 行 %12d 分 %5d 块%s"
              % (ep, seg, lines, lines, score, pieces, mark))

    print("\n最优：%d 行 / %d 分 / %d 块" %
          (best["lines"], best["score"], best["pieces"]))
    print("段: %s" % best.get("segment", ""))
    for n, v in zip(NAMES, best.get("weights", [])):
        print("  %-12s %s" % (n, v))

    out = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "archive", "sr_train.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump({"best": best, "history": history}, f,
                  ensure_ascii=False, indent=1)
    print("\n记录:", out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
