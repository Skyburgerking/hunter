# -*- coding: utf-8 -*-
""

import os

import numpy as np
import pandas as pd

from benches.quant.single import load_prices

BIG_FEATURES = [
    
    "ret1", "ret5", "ret10", "ret20", "ret60",
    "mom5", "mom10", "mom20", "mom60",
    
    "ma_gap_5", "ma_gap_10", "ma_gap_20", "ma_gap_60",
    "ma_cross_5_20", "ma_cross_10_60",
    
    "vol_5", "vol_10", "vol_20", "vol_60", "hl_range", "atr",
    
    "rsi_6", "rsi_12", "rsi_24",
    "kdjk", "kdjd", "kdjj",
    "wr_6", "wr_10", "wr_20",
    "cci", "mfi",
    
    "macd", "macds", "macdh",
    "trix", "dma", "cr", "vr",
    "pdi", "dx", "adx", "adxr",
    
    "boll", "boll_ub", "boll_lb",
    
    "vol_ratio_5", "vol_ratio_20", "amount_ratio",
    
    "close_pos_20", "close_pos_60",
]


def add_big_features(df):
    from stockstats import StockDataFrame

    d = df.copy()
    d = d.rename(columns=str.lower)
    for col in ("open", "high", "low", "close", "volume", "amount"):
        if col in d.columns:
            d[col] = pd.to_numeric(d[col], errors="coerce")
    sdf = StockDataFrame.retype(d.copy())
    close = d["close"]

    
    for n in (1, 5, 10, 20, 60):
        d["ret%d" % n] = close.pct_change(n)
    for n in (5, 10, 20, 60):
        d["mom%d" % n] = close.pct_change(n)

    
    for n in (5, 10, 20, 60):
        ma = close.rolling(n).mean()
        d["ma_gap_%d" % n] = close / ma - 1.0
    ma5 = close.rolling(5).mean()
    ma10 = close.rolling(10).mean()
    ma20 = close.rolling(20).mean()
    ma60 = close.rolling(60).mean()
    d["ma_cross_5_20"] = ma5 / ma20 - 1.0
    d["ma_cross_10_60"] = ma10 / ma60 - 1.0

    
    r1 = close.pct_change()
    for n in (5, 10, 20, 60):
        d["vol_%d" % n] = r1.rolling(n).std()
    d["hl_range"] = (d["high"] - d["low"]) / close
    d["atr"] = sdf["atr"].values / close

    
    for name in ("rsi_6", "rsi_12", "rsi_24", "kdjk", "kdjd", "kdjj",
                 "wr_6", "wr_10", "wr_20", "cci", "mfi",
                 "macd", "macds", "macdh", "trix", "dma", "cr", "vr",
                 "pdi", "dx", "adx", "adxr", "boll"):
        d[name] = sdf[name].values

    
    d["boll_ub"] = sdf["boll_ub"].values
    d["boll_lb"] = sdf["boll_lb"].values

    
    v = d["volume"]
    d["vol_ratio_5"] = v / (v.rolling(5).mean() + 1e-9)
    d["vol_ratio_20"] = v / (v.rolling(20).mean() + 1e-9)
    if "amount" in d.columns:
        a = d["amount"]
        d["amount_ratio"] = a / (a.rolling(20).mean() + 1e-9)
    else:
        d["amount_ratio"] = 1.0

    
    for n in (20, 60):
        lo = close.rolling(n).min()
        hi = close.rolling(n).max()
        d["close_pos_%d" % n] = (close - lo) / (hi - lo + 1e-9)

    d = d.replace([np.inf, -np.inf], np.nan)
    d = d.dropna(subset=BIG_FEATURES + ["close"]).reset_index(drop=True)
    return d


class FinBigEnv:
    def __init__(self, symbol="000001", start="20200101",
                 end="20211231", fee=0.0012, cash=10000.0):
        raw = load_prices(symbol, start, end)
        self.df = add_big_features(raw)
        self.symbol = symbol
        self.fee = fee
        self.init_cash = cash
        self.feat = self.df[BIG_FEATURES].to_numpy(dtype=float)
        self.mu = self.feat.mean(axis=0)
        self.sd = self.feat.std(axis=0) + 1e-9
        self.feat = (self.feat - self.mu) / self.sd

    def __len__(self):
        return len(self.df)

    def run(self, weights, buy_th=0.0, sell_th=0.0):
        w = np.asarray(weights, dtype=float)
        scores = self.feat @ w
        close = self.df["close"].to_numpy(dtype=float)
        n = len(self.df)

        cash = self.init_cash
        shares = 0.0
        trades = 0
        equity = []

        for t in range(n):
            if t > 0:
                s = scores[t - 1]
                price = close[t]
                if s > buy_th and shares == 0.0 and cash > 0:
                    shares = cash * (1 - self.fee) / price
                    cash = 0.0
                    trades += 1
                elif s < sell_th and shares > 0.0:
                    cash = shares * price * (1 - self.fee)
                    shares = 0.0
                    trades += 1
            equity.append(cash + shares * close[t])

        equity = np.asarray(equity)
        total_return = equity[-1] / equity[0] - 1.0
        daily = np.diff(equity) / (equity[:-1] + 1e-9)
        sharpe = (float(np.sqrt(252) * daily.mean() / daily.std())
                  if daily.std() > 1e-12 else 0.0)
        return sharpe, float(total_return), trades

    def buy_and_hold(self):
        close = self.df["close"].to_numpy(dtype=float)
        return float(close[-1] / close[0] - 1.0)


if __name__ == "__main__":
    env = FinBigEnv()
    print("样本 %d 天 / 特征 %d 个" % (len(env), len(BIG_FEATURES)))
    print("买入持有 %+.2f%%" % (env.buy_and_hold() * 100))
    print("零权重", env.run([0.0] * len(BIG_FEATURES)))
    print("单特征 ret1", env.run([1.0] + [0.0] * (len(BIG_FEATURES) - 1)))
