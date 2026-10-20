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
from benches.quant.single_big import BIG_FEATURES, add_big_features  # noqa: E402
from hunter.core import BASES, GedaCore  # noqa: E402

LEVELS = [-3.0, -2.0, -1.0, 0.0, 1.0, 2.0, 3.0]
NF = len(BIG_FEATURES)


def decode(seg):
    return [LEVELS[BASES.index(ch) % len(LEVELS)] for ch in seg]


def fit_of(sharpe):
    return max(0.0, min(1.0, (sharpe + 1.0) / 4.0))


class SliceEnv:
    ""

    def __init__(self, df, mu, sd):
        self.df = df.reset_index(drop=True)
        self.feat = (self.df[BIG_FEATURES].to_numpy(dtype=float) - mu) / sd
        self.close = self.df["close"].to_numpy(dtype=float)

    def __len__(self):
        return len(self.df)

    def run(self, weights, fee=0.0012):
        w = np.asarray(weights, dtype=float)
        scores = self.feat @ w
        n = len(self.close)
        cash, shares, trades = 10000.0, 0.0, 0
        equity = np.empty(n)
        wins = 0
        entry = 0.0

        for t in range(n):
            if t > 0:
                s = scores[t - 1]
                price = self.close[t]
                if s > 0 and shares == 0.0 and cash > 0:
                    shares = cash * (1 - fee) / price
                    entry = price
                    cash = 0.0
                    trades += 1
                elif s < 0 and shares > 0.0:
                    if price > entry:
                        wins += 1
                    cash = shares * price * (1 - fee)
                    shares = 0.0
                    trades += 1
            equity[t] = cash + shares * self.close[t]

        ret = equity[-1] / equity[0] - 1.0
        daily = np.diff(equity) / (equity[:-1] + 1e-9)
        sharpe = (float(np.sqrt(252) * daily.mean() / daily.std())
                  if daily.std() > 1e-12 else 0.0)
        peak = np.maximum.accumulate(equity)
        mdd = float((equity / peak - 1.0).min())
        closed = max(1, trades // 2)
        return {"ret": float(ret), "sharpe": sharpe, "mdd": mdd,
                "trades": trades, "winrate": wins / closed}

    def buy_hold(self):
        return float(self.close[-1] / self.close[0] - 1.0)


def load_big(symbol):
    cache = os.path.join(DATA_DIR, "%s_20180101_20241231.csv" % symbol)
    if not os.path.exists(cache):
        return None
    raw = pd.read_csv(cache)
    raw["date"] = pd.to_datetime(raw["date"])
    return add_big_features(raw)


def walk_forward(df, episodes=400, train_months=24, test_months=6,
                 seed=7):
    ""
    df = df.reset_index(drop=True)
    start = df["date"].min()
    end = df["date"].max()
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
            cursor = cursor + pd.DateOffset(months=test_months)
            continue

        mu = tr[BIG_FEATURES].to_numpy(dtype=float).mean(axis=0)
        sd = tr[BIG_FEATURES].to_numpy(dtype=float).std(axis=0) + 1e-9
        env_tr = SliceEnv(tr, mu, sd)
        env_te = SliceEnv(te, mu, sd)

        core = GedaCore({}, gene_len=200)
        best = {"sharpe": -99.0, "w": None}
        for _ in range(episodes):
            seg = core.get_gene_segment(NF)
            w = decode(seg)
            r = env_tr.run(w)
            core.record(fit_of(r["sharpe"]))
            core.reward_segment(seg, fit_of(r["sharpe"]))
            if r["sharpe"] > best["sharpe"]:
                best = {"sharpe": r["sharpe"], "w": w}

        w = best["w"]
        test_r = env_te.run(w)
        test_bh = env_te.buy_hold()

        rng = random.Random(seed + int(cursor.timestamp()))
        rand_rets = []
        for _ in range(10):
            rw = [rng.choice(LEVELS) for _ in range(NF)]
            rand_rets.append(env_te.run(rw)["ret"])

        rows.append({
            "window": str(cursor)[:7],
            "train_days": len(tr),
            "test_days": len(te),
            "train_sharpe": best["sharpe"],
            "test_ret": test_r["ret"],
            "test_sharpe": test_r["sharpe"],
            "test_mdd": test_r["mdd"],
            "test_trades": test_r["trades"],
            "test_winrate": test_r["winrate"],
            "test_bh": test_bh,
            "rand_mean": float(np.mean(rand_rets)),
        })
        cursor = cursor + pd.DateOffset(months=test_months)
    return rows


def main():
    episodes = int(sys.argv[1]) if len(sys.argv) > 1 else 400
    all_rows = []
    per_ticker = {}

    for symbol, name, _prefix in TICKERS:
        df = load_big(symbol)
        if df is None or len(df) < 500:
            print("%-8s 数据不足，跳过" % symbol)
            continue
        rows = walk_forward(df, episodes=episodes)
        per_ticker[symbol] = {"name": name, "rows": rows}
        for r in rows:
            r["symbol"] = symbol
            r["name"] = name
        all_rows.extend(rows)
        if rows:
            avg_ret = np.mean([r["test_ret"] for r in rows])
            avg_bh = np.mean([r["test_bh"] for r in rows])
            beat = sum(1 for r in rows if r["test_ret"] > r["test_bh"])
            print("%-8s %-6s %2d 窗口  平均 %+6.2f%%  vs 持有 %+6.2f%%  跑赢 %d/%d"
                  % (symbol, name, len(rows), avg_ret * 100, avg_bh * 100,
                     beat, len(rows)))

    if not all_rows:
        print("没有可用数据")
        return 1

    n = len(all_rows)
    avg_ret = np.mean([r["test_ret"] for r in all_rows])
    avg_bh = np.mean([r["test_bh"] for r in all_rows])
    avg_rand = np.mean([r["rand_mean"] for r in all_rows])
    avg_sharpe = np.mean([r["test_sharpe"] for r in all_rows])
    avg_mdd = np.mean([r["test_mdd"] for r in all_rows])
    beat_bh = sum(1 for r in all_rows if r["test_ret"] > r["test_bh"])
    beat_rand = sum(1 for r in all_rows if r["test_ret"] > r["rand_mean"])
    pos = sum(1 for r in all_rows if r["test_ret"] > 0)

    print("\n" + "=" * 68)
    print("总窗口 %d  标的 %d  每窗口训练 %d 代" % (n, len(per_ticker), episodes))
    print("hunter 平均收益   %+.2f%%" % (avg_ret * 100))
    print("买入持有平均收益 %+.2f%%" % (avg_bh * 100))
    print("随机权重平均收益 %+.2f%%" % (avg_rand * 100))
    print("hunter 平均夏普   %.2f" % avg_sharpe)
    print("hunter 平均最大回撤 %.2f%%" % (avg_mdd * 100))
    print("跑赢买入持有 %d/%d (%.0f%%)" % (beat_bh, n, beat_bh / n * 100))
    print("跑赢随机权重 %d/%d (%.0f%%)" % (beat_rand, n, beat_rand / n * 100))
    print("正收益窗口 %d/%d (%.0f%%)" % (pos, n, pos / n * 100))
    print("=" * 68)

    out = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "archive", "quant_validate.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump({"summary": {
            "windows": n, "episodes": episodes,
            "avg_ret": avg_ret, "avg_bh": avg_bh, "avg_rand": avg_rand,
            "avg_sharpe": avg_sharpe, "avg_mdd": avg_mdd,
            "beat_bh": beat_bh, "beat_rand": beat_rand, "pos": pos,
        }, "rows": all_rows}, f, ensure_ascii=False, indent=1)
    print("记录:", out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
