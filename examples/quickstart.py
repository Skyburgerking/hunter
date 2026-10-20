# -*- coding: utf-8 -*-
""

import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hunter import HunterEngine  # noqa: E402


class GuessGame:
    ""

    def __init__(self, seed=None):
        self.rng = random.Random(seed)
        self.reset()

    def reset(self):
        self.target = self.rng.randint(1, 100)
        self.lo, self.hi = 1, 100
        self.tries = 0
        return self.observe()

    def observe(self):
        return {"lo": self.lo, "hi": self.hi, "tries": self.tries}

    def act(self, params, obs):
        ""
        frac = params.get("frac", 0.5)
        guess = int(self.lo + frac * (self.hi - self.lo))
        return max(self.lo, min(self.hi, guess))

    def step(self, guess):
        self.tries += 1
        if guess == self.target:
            return self.observe(), 1.0, True, {}
        if guess < self.target:
            self.lo = guess + 1
        else:
            self.hi = guess - 1
        
        gap = abs(guess - self.target)
        reward = max(0.0, 1.0 - gap / 100.0) * 0.6
        done = self.lo > self.hi or self.tries >= 12
        return self.observe(), reward, done, {}


SPEC = {
    "name": "guess",
    "mode": "param",
    "max_score": 1.0,
    "params": {
        "frac": {"values": [0.0, 0.25, 0.4, 0.5, 0.6, 0.75, 1.0]},
    },
}


def main():
    engine = HunterEngine(SPEC, seed=7)
    env = GuessGame(seed=1)

    for ep in range(1, 201):
        obs = env.reset()
        engine.begin_episode()
        total = 0.0
        done = False
        while not done:
            out = engine.tick(obs)
            action = env.act(out["params"], obs)
            obs, reward, done, _info = env.step(action)
            total += reward
            engine.feedback(reward, done)
        engine.end_episode(total)

        if ep % 20 == 0:
            print("ep %3d  本局 %.3f  最优 %.3f  段 %s"
                  % (ep, total, engine.best["score"] if engine.best else 0.0,
                     engine.segment))

    print("\n最终最优：%.3f" % (engine.best["score"] if engine.best else 0.0))


if __name__ == "__main__":
    main()
