# -*- coding: utf-8 -*-
""

import numpy as np
import pandas as pd

from benches.quant.single_big import BIG_FEATURES, add_big_features


FEAT_V2 = []
for _n in BIG_FEATURES:
    FEAT_V2.append(_n)
    FEAT_V2.append(_n + "_d5")


BUY_LEVELS = [-1.5, -1.0, -0.5, 0.0, 0.5, 1.0, 1.5]
SELL_LEVELS = [-1.5, -1.0, -0.5, 0.0, 0.5, 1.0, 1.5]
POS_LEVELS = [0.2, 0.4, 0.6, 0.8, 1.0]
STOP_LEVELS = [-0.02, -0.04, -0.06, -0.08, -0.10]

N_WEIGHTS = len(FEAT_V2)
N_EXTRA = 4
N_GENE = N_WEIGHTS + N_EXTRA


def build_features(df):
    ""
    d = add_big_features(df)
    for n in BIG_FEATURES:
        d[n + "_d5"] = d[n].diff(5)
    d = d.replace([np.inf, -np.inf], np.nan)
    d = d.dropna(subset=FEAT_V2 + ["close"]).reset_index(drop=True)
    return d


class QuantEnvV2:
    def __init__(self, df, mu=None, sd=None, fee=0.0012):
        self.df = df.reset_index(drop=True)
        raw = self.df[FEAT_V2].to_numpy(dtype=float)
        if mu is None:
            mu = raw.mean(axis=0)
            sd = raw.std(axis=0) + 1e-9
        self.mu, self.sd = mu, sd
        self.feat = (raw - mu) / sd
        self.close = self.df["close"].to_numpy(dtype=float)
        self.fee = fee

    def __len__(self):
        return len(self.close)

    def run(self, gene, fee=None):
        ""
        fee = self.fee if fee is None else fee
        w = np.asarray(gene[:N_WEIGHTS], dtype=float)
        buy_th, sell_th, pos, stop = gene[N_WEIGHTS:N_GENE]

        scores = self.feat @ w
        n = len(self.close)
        cash, shares, trades = 10000.0, 0.0, 0
        entry = 0.0
        wins = 0
        equity = np.empty(n)
        last_pos = 0.0

        for t in range(n):
            price = self.close[t]

            
            if shares > 0 and entry > 0 and price / entry - 1.0 <= stop:
                cash = shares * price * (1 - fee)
                shares = 0.0
                trades += 1
                equity[t] = cash
                continue

            if t > 0:
                s = scores[t - 1]
                if s > buy_th and last_pos < 1.0 and cash > 0:
                    
                    target = min(1.0, last_pos + pos)
                    buy_value = (target - last_pos) * 10000.0
                    buy_value = min(buy_value, cash)
                    if buy_value > 100.0:
                        add = buy_value * (1 - fee) / price
                        shares += add
                        cash -= buy_value
                        entry = price
                        last_pos = target
                        trades += 1
                elif s < sell_th and shares > 0:
                    if price > entry:
                        wins += 1
                    cash += shares * price * (1 - fee)
                    shares = 0.0
                    last_pos = 0.0
                    trades += 1

            equity[t] = cash + shares * price

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


def decode_gene(seg):
    ""
    from hunter.core import BASES

    out = []
    for i, ch in enumerate(seg):
        idx = BASES.index(ch)
        if i < N_WEIGHTS:
            out.append([-3.0, -2.0, -1.0, 0.0, 1.0, 2.0, 3.0][idx % 7])
        elif i == N_WEIGHTS:
            out.append(BUY_LEVELS[idx % len(BUY_LEVELS)])
        elif i == N_WEIGHTS + 1:
            out.append(SELL_LEVELS[idx % len(SELL_LEVELS)])
        elif i == N_WEIGHTS + 2:
            out.append(POS_LEVELS[idx % len(POS_LEVELS)])
        else:
            out.append(STOP_LEVELS[idx % len(STOP_LEVELS)])
    return out
