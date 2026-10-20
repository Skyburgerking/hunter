# -*- coding: utf-8 -*-
""

import os

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(ROOT, "_gh", "finrl_data")
os.makedirs(DATA_DIR, exist_ok=True)

FEATURES = ["ret1", "mom5", "mom20", "ma_gap", "rsi",
            "macd", "vol", "boll", "vol_ratio"]


def load_prices(symbol="000001", start="20200101", end="20211231",
                adjust="qfq"):
    ""
    cache = os.path.join(DATA_DIR, "%s_%s_%s.csv" % (symbol, start, end))
    if os.path.exists(cache):
        df = pd.read_csv(cache)
        df["date"] = pd.to_datetime(df["date"])
        return df
    import akshare as ak
    code = symbol if len(symbol) > 6 else (
        ("sh" if symbol.startswith("6") else "sz") + symbol)
    df = ak.stock_zh_a_daily(symbol=code, start_date=start,
                             end_date=end, adjust=adjust)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)
    df.to_csv(cache, index=False)
    return df


def add_features(df):
    ""
    from stockstats import StockDataFrame

    d = df.copy()
    d = d.rename(columns=str.lower)
    for col in ("open", "high", "low", "close", "volume"):
        d[col] = pd.to_numeric(d[col], errors="coerce")
    sdf = StockDataFrame.retype(d.copy())

    d["ret1"] = d["close"].pct_change()
    d["mom5"] = d["close"].pct_change(5)
    d["mom20"] = d["close"].pct_change(20)
    ma20 = d["close"].rolling(20).mean()
    d["ma_gap"] = d["close"] / ma20 - 1.0
    d["rsi"] = (sdf["rsi_14"].values - 50.0) / 50.0

    ema12 = d["close"].ewm(span=12, adjust=False).mean()
    ema26 = d["close"].ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    d["macd"] = macd / d["close"]

    d["vol"] = d["ret1"].rolling(20).std()
    std20 = d["close"].rolling(20).std()
    d["boll"] = (d["close"] - ma20) / (2.0 * std20 + 1e-9)
    d["vol_ratio"] = d["volume"] / (d["volume"].rolling(20).mean() + 1e-9)

    d = d.dropna(subset=FEATURES + ["close"]).reset_index(drop=True)
    return d


class FinEnv:
    ""

    def __init__(self, symbol="000001", start="20200101",
                 end="20211231", fee=0.0012, cash=10000.0):
        raw = load_prices(symbol, start, end)
        self.df = add_features(raw)
        self.symbol = symbol
        self.fee = fee
        self.init_cash = cash
        self.feat = self.df[FEATURES].to_numpy(dtype=float)

        
        self.mu = self.feat.mean(axis=0)
        self.sd = self.feat.std(axis=0) + 1e-9
        self.feat = (self.feat - self.mu) / self.sd

    def __len__(self):
        return len(self.df)

    def run(self, weights, buy_th=0.0, sell_th=0.0, verbose=False):
        ""
        w = np.asarray(weights, dtype=float)
        scores = self.feat @ w

        close = self.df["close"].to_numpy(dtype=float)
        dates = self.df["date"].to_numpy()
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
        if daily.std() > 1e-12:
            sharpe = float(np.sqrt(252) * daily.mean() / daily.std())
        else:
            sharpe = 0.0
        if verbose:
            print("%s %s~%s  %d 天  收益 %+.2f%%  夏普 %.2f  交易 %d 次"
                  % (self.symbol, str(dates[0])[:10], str(dates[-1])[:10],
                     n, total_return * 100, sharpe, trades))
        return sharpe, float(total_return), trades

    def buy_and_hold(self):
        score, ret, trades = self.run([0.0] * len(FEATURES))
        close = self.df["close"].to_numpy(dtype=float)
        bh = close[-1] / close[0] - 1.0
        return float(bh)


if __name__ == "__main__":
    env = FinEnv()
    print("样本", len(env), "天，特征", FEATURES)
    print("买入持有 %.2f%%" % (env.buy_and_hold() * 100))
    env.run([1, 0, 0, 0, 0, 0, 0, 0, 0], verbose=True)
    env.run([0] * 9, verbose=True)
