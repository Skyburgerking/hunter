# -*- coding: utf-8 -*-
""
from .base import ArcadeEnv, frags

PRICES = [100, 98, 95, 92, 96, 101, 107, 112, 108, 103,
          99, 104, 110, 116, 111, 105, 100, 106, 113, 120]


def _best_profit(prices):
    ""
    cash, hold = 100.0, 0.0
    shares = 0
    for i, p in enumerate(prices):
        nxt = prices[i + 1] if i + 1 < len(prices) else None
        if shares == 0 and nxt is not None and nxt > p:
            shares = cash / p
            cash = 0.0
        elif shares > 0 and (nxt is None or nxt < p):
            cash = shares * p
            shares = 0
    return cash - 100.0        


class FinrlTrade(ArcadeEnv):
    ""

    NAME = "finrl_trade"
    RENDERER = "table"
    CONDITIONS = 4

    def __init__(self):
        ArcadeEnv.__init__(self)
        self.FULL = _best_profit(PRICES)
        self.SLOTS = frags({"op": "buy"}, {"op": "sell"}, {"op": "hold"})

    def reset(self):
        self.t = 0
        self.cash = 100.0
        self.shares = 0.0
        self.bought_at = 0.0
        self.score = 0.0
        self.done = False
        self.steps = 0
        return self

    def _equity(self):
        return self.cash + self.shares * PRICES[min(self.t, len(PRICES) - 1)]

    def apply(self, step_json):
        if self.done:
            return True
        op = step_json.get("op")
        p = PRICES[self.t]
        if op == "buy":
            if self.shares == 0 and self.cash > 0:
                self.shares = self.cash / p
                self.cash = 0.0
                self.bought_at = p
        elif op == "sell":
            if self.shares > 0:
                self.cash = self.shares * p
                self.shares = 0.0
        elif op != "hold":
            return False
        self.steps += 1
        self.t += 1
        self.score = self._equity() - 100.0
        if self.t >= len(PRICES) - 1:
            self.cash = self._equity()
            self.shares = 0.0
            self.score = self.cash - 100.0
            self.done = True
        return self.done

    def situation(self):
        if self.done:
            return None
        
        up = (self.t + 1 < len(PRICES)
              and PRICES[self.t + 1] >= PRICES[self.t])
        return (2 if self.shares > 0 else 0) + (0 if up else 1)
