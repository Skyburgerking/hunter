# -*- coding: utf-8 -*-
""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import os
import random
import sys

import numpy as np
import pandas as pd


from benches.quant.fetch import DATA_DIR, TICKERS  # noqa: E402
from hunter.core import GedaCore  # noqa: E402
from benches.quant.single_v2 import (FEAT_V2, N_GENE, N_WEIGHTS, QuantEnvV2,
                          build_features, decode_gene)  # noqa: E402

LEVELS = [-3.0, -2.0, -1.0, 0.0, 1.0, 2.0, 3.0]


def fit_of(sharpe):
    return max(0.0, min(1.0, (sharpe + 1.0) / 4.0))


def load_v2(symbol):
    cache = os.path.join(DATA_DIR, "%s_20180101_20241231.csv" % symbol)
    if not os.path.exists(cache):
        return None
    raw = pd.read_csv(cache)
    raw["date"] = pd.to_datetime(raw["date"])
    return build_features(raw)


def walk_forward(df, episodes=400, train_months=24, test_months=6, seed=7):
    df = df.reset_index(drop=True)
    start, end = df["date"].min(), df["date"].max()
    cursor = start
    rows = []

    while True:
        tr_end = cursor + pd.DateOffset(months=train_months)
        te_end = tr_end + pd.DateOffset(months=test_months)
        if te_end > end:
            break
        tr = df[(df["date"] >= cursor) & (df["date"] < tr_end)]
        te = df[(df["date"] >= tr_end) & (df["date"] < te_end)]
        if len(tr) < 200 or len(te) < 40:
            cursor += pd.DateOffset(months=test_months)
            continue

        mu = tr[FEAT_V2].to_numpy(dtype=float).mean(axis=0)
        sd = tr[FEAT_V2].to_numpy(dtype=float).std(axis=0) + 1e-9
        env_tr = QuantEnvV2(tr, mu, sd)
        env_te = QuantEnvV2(te, mu, sd)

        core = GedaCore({}, gene_len=260)
        best = {"sharpe": -99.0, "gene": None}
        for _ in range(episodes):
            seg = core.get_gene_segment(N_GENE)
            gene = decode_gene(seg)
            r = env_tr.run(gene)
            core.record(fit_of(r["sharpe"]))
            core.reward_segment(seg, fit_of(r["sharpe"]))
            if r["sharpe"] > best["sharpe"]:
                best = {"sharpe": r["sharpe"], "gene": gene}

        test_r = env_te.run(best["gene"])
        rng = random.Random(seed + int(cursor.timestamp()))
        rand_rets = [env_te.run(
            [rng.choice(LEVELS) for _ in range(N_WEIGHTS)] +
            [0.0, 0.0, 1.0, -0.10])["ret"] for _ in range(10)]

        rows.append({
            "window": str(cursor)[:7],
            "train_sharpe": best["sharpe"],
            "test_ret": test_r["ret"],
            "test_sharpe": test_r["sharpe"],
            "test_mdd": test_r["mdd"],
            "test_trades": test_r["trades"],
            "test_bh": env_te.buy_hold(),
            "rand_mean": float(np.mean(rand_rets)),
            "buy_th": best["gene"][N_WEIGHTS],
            "sell_th": best["gene"][N_WEIGHTS + 1],
            "pos": best["gene"][N_WEIGHTS + 2],
            "stop": best["gene"][N_WEIGHTS + 3],
        })
        cursor += pd.DateOffset(months=test_months)
    return rows


def main():
    episodes = int(sys.argv[1]) if len(sys.argv) > 1 else 400
    all_rows = []

    for symbol, name, _p in TICKERS:
        df = load_v2(symbol)
        if df is None or len(df) < 500:
            print("%-8s 数据不足" % symbol)
            continue
        rows = walk_forward(df, episodes=episodes)
        for r in rows:
            r["symbol"] = symbol
            r["name"] = name
        all_rows.extend(rows)
        if rows:
            print("%-8s %-6s %2d 窗口  平均 %+6.2f%%  vs 持有 %+6.2f%%  跑赢 %d/%d"
                  % (symbol, name, len(rows),
                     np.mean([r["test_ret"] for r in rows]) * 100,
                     np.mean([r["test_bh"] for r in rows]) * 100,
                     sum(1 for r in rows if r["test_ret"] > r["test_bh"]),
                     len(rows)))

    if not all_rows:
        return 1

    n = len(all_rows)
    avg_ret = np.mean([r["test_ret"] for r in all_rows])
    avg_bh = np.mean([r["test_bh"] for r in all_rows])
    avg_rand = np.mean([r["rand_mean"] for r in all_rows])
    print("\n" + "=" * 68)
    print("总窗口 %d  每窗口 %d 代  基因 %d 位（%d 权重 + 4 策略）"
          % (n, episodes, N_GENE, N_WEIGHTS))
    print("hunter 平均收益   %+.2f%%" % (avg_ret * 100))
    print("买入持有平均收益 %+.2f%%" % (avg_bh * 100))
    print("随机权重平均收益 %+.2f%%" % (avg_rand * 100))
    print("hunter 平均夏普   %.2f"
          % np.mean([r["test_sharpe"] for r in all_rows]))
    print("hunter 平均最大回撤 %.2f%%"
          % (np.mean([r["test_mdd"] for r in all_rows]) * 100))
    print("跑赢买入持有 %d/%d (%.0f%%)"
          % (sum(1 for r in all_rows if r["test_ret"] > r["test_bh"]), n,
             sum(1 for r in all_rows if r["test_ret"] > r["test_bh"]) / n * 100))
    print("跑赢随机权重 %d/%d (%.0f%%)"
          % (sum(1 for r in all_rows if r["test_ret"] > r["rand_mean"]), n,
             sum(1 for r in all_rows if r["test_ret"] > r["rand_mean"]) / n * 100))
    print("正收益窗口 %d/%d (%.0f%%)"
          % (sum(1 for r in all_rows if r["test_ret"] > 0), n,
             sum(1 for r in all_rows if r["test_ret"] > 0) / n * 100))
    print("=" * 68)

    out = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "archive", "quant_validate_v2.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump({"summary": {
            "windows": n, "episodes": episodes,
            "avg_ret": avg_ret, "avg_bh": avg_bh, "avg_rand": avg_rand,
        }, "rows": all_rows}, f, ensure_ascii=False, indent=1)
    print("记录:", out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
