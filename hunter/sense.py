# -*- coding: utf-8 -*-
""
import random


def collect(env_factory, episodes=12, steps=120, actions=None, seed=0,
            observe=None):
    ""
    rng = random.Random(seed)
    samples = []
    for _ in range(max(1, episodes)):
        env = env_factory()
        env.reset()
        acts = list(actions or getattr(env, "actions", lambda: [])())
        for _ in range(max(1, steps)):
            vec = (observe or (lambda e: e.observe()))(env)
            samples.append([float(v) for v in vec])
            if env.situation() is None or not acts:
                break
            env.apply(rng.choice(acts))
    return samples


def bind(bounds, bins=3):
    ""
    cuts = []
    for lo, hi in bounds:
        step = (hi - lo) / bins
        cuts.append([lo + step * k for k in range(1, bins)])
    return cuts


def fit(samples, bins=3, bounds=None):
    ""
    if bounds is not None:
        return bind(bounds, bins)
    if not samples:
        return []
    dims = len(samples[0])
    cuts = []
    for d in range(dims):
        vals = sorted(s[d] for s in samples)
        n = len(vals)
        cuts.append([vals[min(n - 1, int(n * k / bins))] for k in range(1, bins)])
    return cuts


class Binner(object):
    ""

    def __init__(self, cuts):
        self.cuts = [list(c) for c in cuts]
        self.bins = len(self.cuts[0]) + 1 if self.cuts else 1

    @classmethod
    def fit(cls, samples, bins=3, bounds=None):
        return cls(fit(samples, bins, bounds=bounds))

    def bin_of(self, v, d):
        c = self.cuts[d]
        k = 0
        for cut in c:
            if v > cut:
                k += 1
            else:
                break
        return k

    def key(self, vec):
        if not self.cuts:
            return 0
        k = 0
        for d, v in enumerate(vec):
            if d >= len(self.cuts):
                break
            k = k * self.bins + self.bin_of(float(v), d)
        return k

    @property
    def size(self):
        return self.bins ** len(self.cuts)


def consistency(env_factory, binner, actions, episodes=6, steps=80, seed=0):
    ""
    rng = random.Random(seed)
    gain = {}
    base_total = 0.0
    for _ in range(max(1, episodes)):
        env = env_factory()
        env.reset()
        for _ in range(max(1, steps)):
            if env.situation() is None:
                break
            k = binner.key(env.observe())
            a = rng.choice(actions)
            env.apply(a)
        base_total += float(getattr(env, "score", 0.0))
    baseline = base_total / max(1, episodes)
    for a in actions:
        for _ in range(max(1, episodes)):
            env = env_factory()
            env.reset()
            for _ in range(max(1, steps)):
                if env.situation() is None:
                    break
                env.apply(a)
            g = float(getattr(env, "score", 0.0)) - baseline
            tag = a if isinstance(a, (str, int, float, tuple)) else repr(sorted(a.items()))
            gain[tag] = gain.get(tag, 0.0) + g
    best = max(gain.values()) if gain else 0.0
    spread = max(gain.values()) - min(gain.values()) if gain else 0.0
    return {"gain": gain, "spread": spread,
            "useful": bool(spread > max(1e-9, abs(best) * 0.15))}
