# -*- coding: utf-8 -*-
""

import os

import numpy as np
import pandas as pd

from benches.quant.fetch import DATA_DIR, TICKERS
from benches.quant.single_big import BIG_FEATURES, add_big_features


CROSS_FEATURES = list(BIG_FEATURES)

TOP_LEVELS = [1, 2, 3, 4, 5]
HOLD_LEVELS = [5, 10, 20, 40]
FEE = 0.0012


def load_panel():
    ""
    frames = {}
    for symbol, _name, _p in TICKERS:
        path = os.path.join(DATA_DIR, "%s_20180101_20241231.csv" % symbol)
        if not os.path.exists(path):
            continue
        raw = pd.read_csv(path)
        raw["date"] = pd.to_datetime(raw["date"])
        df = add_big_features(raw)
        frames[symbol] = df.set_index("date")

    common = None
    for df in frames.values():
        idx = df.index
        common = idx if common is None else common.intersection(idx)
    common = common.sort_values()

    close, feats = {}, {}
    for symbol, df in frames.items():
        d = df.loc[common]
        close[symbol] = d["close"].to_numpy(dtype=float)
        feats[symbol] = d[CROSS_FEATURES].to_numpy(dtype=float)
    return common, close, feats, list(frames.keys())


class CrossSectionEnv:
    def __init__(self, dates, close, feats, symbols):
        self.dates = dates
        self.close = close
        self.feats = feats
        self.symbols = symbols
        self.n = len(dates)
        self.k = len(symbols)

        
        self.mu = {}
        self.sd = {}
        for s in symbols:
            self.mu[s] = feats[s].mean(axis=0)
            self.sd[s] = feats[s].std(axis=0) + 1e-9

    def _scores(self, t, weights):
        ""
        w = np.asarray(weights, dtype=float)
        sc = np.empty(self.k)
        for i, s in enumerate(self.symbols):
            f = (self.feats[s][t] - self.mu[s]) / self.sd[s]
            sc[i] = f @ w
        return sc

    def run(self, weights, top_n=3, hold=10, start=0, end=None):
        end = self.n if end is None else end
        cash = 10000.0
        holding = {}          # symbol -> shares
        equity = np.empty(end - start)
        trades = 0
        next_rebalance = start

        for t in range(start, end):
            if t >= next_rebalance and t < end - 1:
                sc = self._scores(t, weights)
                order = np.argsort(-sc)
                picks = {self.symbols[i] for i in order[:top_n]}

                
                for s in list(holding):
                    if s not in picks:
                        cash += holding[s] * self.close[s][t] * (1 - FEE)
                        del holding[s]
                        trades += 1
                
                target = cash / max(1, len(picks))
                for s in picks:
                    if s in holding:
                        continue
                    px = self.close[s][t]
                    if px <= 0:
                        continue
                    sh = target / px
                    cash -= sh * px * (1 + FEE)
                    holding[s] = sh
                    trades += 1
                next_rebalance = t + hold

            equity[t - start] = cash + sum(
                holding[s] * self.close[s][t] for s in holding)

        ret = equity[-1] / equity[0] - 1.0
        daily = np.diff(equity) / (equity[:-1] + 1e-9)
        sharpe = (float(np.sqrt(252) * daily.mean() / daily.std())
                  if daily.std() > 1e-12 else 0.0)
        peak = np.maximum.accumulate(equity)
        mdd = float((equity / peak - 1.0).min())
        return {"ret": float(ret), "sharpe": sharpe, "mdd": mdd,
                "trades": trades}

    def equal_weight_bh(self, start=0, end=None):
        end = self.n if end is None else end
        rets = [self.close[s][end - 1] / self.close[s][start] - 1.0
                for s in self.symbols]
        return float(np.mean(rets))


def decode_cross(seg, n_feat):
    from hunter.core import BASES
    LEVELS = [-3.0, -2.0, -1.0, 0.0, 1.0, 2.0, 3.0]
    w = [LEVELS[BASES.index(seg[i]) % 7] for i in range(n_feat)]
    top_n = TOP_LEVELS[BASES.index(seg[n_feat]) % len(TOP_LEVELS)]
    hold = HOLD_LEVELS[BASES.index(seg[n_feat + 1]) % len(HOLD_LEVELS)]
    return w, top_n, hold


if __name__ == "__main__":
    dates, close, feats, symbols = load_panel()
    print("交易日 %d / 标的 %d" % (len(dates), len(symbols)))
    env = CrossSectionEnv(dates, close, feats, symbols)
    print("等权持有 %.2f%%" % (env.equal_weight_bh() * 100))
    w = [0.0] * len(CROSS_FEATURES)
    w[CROSS_FEATURES.index("mom20")] = 1.0
    print("20 日动量选 3", env.run(w, top_n=3, hold=10))
