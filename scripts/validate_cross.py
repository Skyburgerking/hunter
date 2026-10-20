# -*- coding: utf-8 -*-
""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import os
import sys

import numpy as np
import pandas as pd


from benches.quant.cross import (CROSS_FEATURES, CrossSectionEnv, HOLD_LEVELS,
                           TOP_LEVELS, decode_cross, load_panel)
from hunter.core import GedaCore  # noqa: E402

NF = len(CROSS_FEATURES)


def fit_of(sharpe):
    return max(0.0, min(1.0, (sharpe + 1.0) / 4.0))


def main():
    episodes = int(sys.argv[1]) if len(sys.argv) > 1 else 800
    dates, close, feats, symbols = load_panel()
    env = CrossSectionEnv(dates, close, feats, symbols)
    n = len(dates)
    print("交易日 %d / 标的 %d / 每窗口 %d 代" % (n, len(symbols), episodes))

    rows = []
    start_i = 0
    train_days = 500       
    test_days = 125        
    step = 125

    while start_i + train_days + test_days <= n:
        tr_s, tr_e = start_i, start_i + train_days
        te_s, te_e = tr_e, tr_e + test_days

        
        env_tr = CrossSectionEnv(dates, close, feats, symbols)
        core = GedaCore({}, gene_len=260)
        best = {"sharpe": -99.0, "w": None, "top_n": 3, "hold": 10}

        for _ in range(episodes):
            seg = core.get_gene_segment(NF + 2)
            w, top_n, hold = decode_cross(seg, NF)
            r = env_tr.run(w, top_n, hold, start=tr_s, end=tr_e)
            core.record(fit_of(r["sharpe"]))
            core.reward_segment(seg, fit_of(r["sharpe"]))
            if r["sharpe"] > best["sharpe"]:
                best = {"sharpe": r["sharpe"], "w": w,
                        "top_n": top_n, "hold": hold}

        test_r = env.run(best["w"], best["top_n"], best["hold"],
                         start=te_s, end=te_e)
        test_bh = env.equal_weight_bh(start=te_s, end=te_e)

        rows.append({
            "train_start": str(dates[tr_s])[:10],
            "test_start": str(dates[te_s])[:10],
            "train_sharpe": best["sharpe"],
            "top_n": best["top_n"], "hold": best["hold"],
            "weights": best["w"],
            "test_ret": test_r["ret"], "test_sharpe": test_r["sharpe"],
            "test_mdd": test_r["mdd"], "test_trades": test_r["trades"],
            "test_bh": test_bh,
        })
        print("%s  选%d 持%d 日  测试 %+6.2f%%  vs 等权 %+6.2f%%  交易 %d"
              % (str(dates[te_s])[:10], best["top_n"], best["hold"],
                 test_r["ret"] * 100, test_bh * 100, test_r["trades"]))
        start_i += step

    if not rows:
        print("窗口不足")
        return 1

    m = len(rows)
    avg_ret = np.mean([r["test_ret"] for r in rows])
    avg_bh = np.mean([r["test_bh"] for r in rows])
    print("\n" + "=" * 68)
    print("窗口 %d" % m)
    print("hunter 平均 %+.2f%%   等权持有平均 %+.2f%%" % (avg_ret * 100, avg_bh * 100))
    print("hunter 平均夏普 %.2f   平均回撤 %.2f%%"
          % (np.mean([r["test_sharpe"] for r in rows]),
             np.mean([r["test_mdd"] for r in rows]) * 100))
    print("跑赢等权 %d/%d (%.0f%%)"
          % (sum(1 for r in rows if r["test_ret"] > r["test_bh"]), m,
             sum(1 for r in rows if r["test_ret"] > r["test_bh"]) / m * 100))
    print("正收益 %d/%d (%.0f%%)"
          % (sum(1 for r in rows if r["test_ret"] > 0), m,
             sum(1 for r in rows if r["test_ret"] > 0) / m * 100))
    print("=" * 68)

    out = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "archive", "quant_cross.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump({"summary": {"windows": m, "episodes": episodes,
                               "avg_ret": avg_ret, "avg_bh": avg_bh},
                   "rows": rows}, f, ensure_ascii=False, indent=1)
    print("记录:", out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
