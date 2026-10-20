# -*- coding: utf-8 -*-
""

import os
import time

import akshare as ak
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(ROOT, "_gh", "finrl_data")
os.makedirs(DATA_DIR, exist_ok=True)

TICKERS = [
    ("000001", "平安银行", "sz"),
    ("600519", "贵州茅台", "sh"),
    ("000858", "五粮液", "sz"),
    ("601318", "中国平安", "sh"),
    ("000333", "美的集团", "sz"),
    ("600036", "招商银行", "sh"),
    ("002415", "海康威视", "sz"),
    ("600276", "恒瑞医药", "sh"),
    ("601888", "中国中免", "sh"),
    ("000651", "格力电器", "sz"),
]

START = "20180101"
END = "20241231"


def fetch(symbol, prefix, retries=3):
    cache = os.path.join(DATA_DIR, "%s_%s_%s.csv" % (symbol, START, END))
    if os.path.exists(cache):
        df = pd.read_csv(cache)
        return df, "cached"
    code = prefix + symbol
    for attempt in range(retries):
        try:
            df = ak.stock_zh_a_daily(symbol=code, start_date=START,
                                     end_date=END, adjust="qfq")
            if len(df) < 500:
                return None, "short(%d)" % len(df)
            df["date"] = pd.to_datetime(df["date"])
            df = df.sort_values("date").reset_index(drop=True)
            df.to_csv(cache, index=False)
            return df, "ok(%d)" % len(df)
        except Exception as e:
            if attempt == retries - 1:
                return None, "err:%s" % type(e).__name__
            time.sleep(3)
    return None, "fail"


def main():
    ok = 0
    for symbol, name, prefix in TICKERS:
        df, status = fetch(symbol, prefix)
        print("%-8s %-8s %s" % (symbol, name, status))
        if df is not None:
            ok += 1
        time.sleep(1.5)
    print("\n可用 %d/%d" % (ok, len(TICKERS)))


if __name__ == "__main__":
    main()
