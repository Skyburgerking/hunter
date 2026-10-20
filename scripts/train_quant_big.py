# -*- coding: utf-8 -*-
""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import os
import sys

import numpy as np


from benches.quant.single_big import BIG_FEATURES, FinBigEnv  # noqa: E402
from hunter.core import BASES, GedaCore  # noqa: E402

LEVELS = [-3.0, -2.0, -1.0, 0.0, 1.0, 2.0, 3.0]


def decode(segment):
    return [LEVELS[BASES.index(ch) % len(LEVELS)] for ch in segment]


def fit_of(sharpe):
    return max(0.0, min(1.0, (sharpe + 1.0) / 4.0))


def main():
    episodes = int(sys.argv[1]) if len(sys.argv) > 1 else 2000
    n_feat = len(BIG_FEATURES)

    train = FinBigEnv("000001", "20200101", "20211231")
    test = FinBigEnv("000001", "20220101", "20231231")
    print("训练 %d 天 / 测试 %d 天 / 特征 %d 个 / 空间 7^%d"
          % (len(train), len(test), n_feat, n_feat))
    print("买入持有  训练 %+.2f%%   测试 %+.2f%%\n"
          % (train.buy_and_hold() * 100, test.buy_and_hold() * 100))

    core = GedaCore({}, gene_len=200)
    best = {"sharpe": -99.0}
    hist = []

    for ep in range(1, episodes + 1):
        seg = core.get_gene_segment(n_feat)
        w = decode(seg)
        sharpe, ret, trades = train.run(w)
        core.record(fit_of(sharpe))
        core.reward_segment(seg, fit_of(sharpe))

        if sharpe > best["sharpe"]:
            best = {"sharpe": sharpe, "return": ret, "trades": trades,
                    "weights": w, "segment": seg}
            mark = " *"
        else:
            mark = ""
        hist.append({"ep": ep, "sharpe": sharpe, "return": ret,
                     "trades": trades, "segment": seg})
        if ep % 100 == 0 or mark:
            print("ep %5d  sharpe %6.2f  收益 %+8.2f%%  交易 %3d%s"
                  % (ep, sharpe, ret * 100, trades, mark))

    w = np.asarray(best["weights"])
    used = [(n, v) for n, v in zip(BIG_FEATURES, w) if v != 0.0]
    print("\n训练集最优：夏普 %.2f / 收益 %+.2f%% / 交易 %d 次"
          % (best["sharpe"], best["return"] * 100, best["trades"]))
    print("用到 %d/%d 个特征：" % (len(used), n_feat))
    for n, v in used:
        print("  %-14s %+.0f" % (n, v))

    s_oos, r_oos, t_oos = test.run(w)
    print("\n样本外：夏普 %.2f / 收益 %+.2f%% / 交易 %d 次"
          % (s_oos, r_oos * 100, t_oos))
    print("对照：买入持有 %+.2f%%" % (test.buy_and_hold() * 100))

    out = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "archive", "finrl_big.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump({"best": best, "oos": {"sharpe": s_oos, "return": r_oos,
                                         "trades": t_oos},
                   "train_bh": train.buy_and_hold(),
                   "test_bh": test.buy_and_hold(),
                   "history": hist}, f, ensure_ascii=False)
    print("\n记录:", out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
