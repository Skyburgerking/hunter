# -*- coding: utf-8 -*-
""

import hunter.features

BASES = ["A", "G", "C", "T", "X"]


class FeaturePolicy:
    def __init__(self, spec):
        cfg = spec.get("features", {})
        self.names = list(cfg.keys())
        self.tables = {}
        for name, item in cfg.items():
            self.tables[name] = item.get("weight", [0.0, 1.0])
        missing = [n for n in self.names if not hunter.features.has(n)]
        if missing:
            raise KeyError("特征未注册: %s（可用: %s）" % (missing, hunter.features.names()))

    def weights(self, segment):
        out = {}
        for i, name in enumerate(self.names):
            idx = i % max(1, len(segment))
            base = segment[idx]
            values = self.tables[name]
            out[name] = values[BASES.index(base) % len(values)]
        return out

    def score(self, state, weights):
        total = 0.0
        for name, w in weights.items():
            if not w:
                continue
            fn = hunter.features.get(name)
            if fn is None:
                continue
            total += w * fn(state)
        return total

    def choose(self, env, weights):
        best, best_v = None, -1e18
        for action in env.candidates():
            state = env.peek(action)
            if state is None:
                continue
            value = self.score(state, weights)
            if value > best_v:
                best_v, best = value, action
        return best
