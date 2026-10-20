# -*- coding: utf-8 -*-
""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import os
import sys

import numpy as np


from benches.quant.single import FEATURES, FinEnv  # noqa: E402
from hunter.core import BASES, GedaCore  # noqa: E402

VALUES = [
    [-3.0, -2.0, -1.0, 0.0, 1.0, 2.0, 3.0],
] * len(FEATURES)


def decode(segment):
    return [VALUES[i][BASES.index(segment[i]) % 7]
            for i in range(len(FEATURES))]


def fitness_of(sharpe):
    ""
    return max(0.0, min(1.0, (sharpe + 1.0) / 4.0))


def main():
    episodes = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    env = FinEnv()

    bh = env.buy_and_hold()
    print("标的 000001  样本 %d 天  买入持有 %+.2f%%" % (len(env), bh * 100))
    print("特征: %s\n" % ", ".join(FEATURES))

    core = GedaCore({}, gene_len=80)
    best = {"sharpe": -99.0}
    hist = []

    for ep in range(1, episodes + 1):
        seg = core.get_gene_segment(len(FEATURES))
        w = decode(seg)
        sharpe, ret, trades = env.run(w)
        fit = fitness_of(sharpe)
        core.record(fit)
        core.reward_segment(seg, fit)

        if sharpe > best["sharpe"]:
            best = {"sharpe": sharpe, "return": ret,
                    "trades": trades, "weights": w, "segment": seg}
            mark = " *"
        else:
            mark = ""
        hist.append({"ep": ep, "segment": seg, "weights": w,
                     "sharpe": sharpe, "return": ret, "trades": trades})
        print("ep %3d  %s  sharpe %6.2f  收益 %+7.2f%%  交易 %3d%s"
              % (ep, seg, sharpe, ret * 100, trades, mark))

    print("\n最优：夏普 %.2f / 收益 %+.2f%% / 交易 %d 次"
          % (best["sharpe"], best["return"] * 100, best["trades"]))
    print("段 %s" % best["segment"])
    for n, v in zip(FEATURES, best["weights"]):
        print("  %-10s %+.1f" % (n, v))
    print("\n对照：买入持有 %+.2f%%" % (bh * 100))

    out = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "archive", "finrl_train.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump({"best": best, "buy_hold": bh, "history": hist}, f,
                  ensure_ascii=False, indent=1)
    print("记录:", out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
