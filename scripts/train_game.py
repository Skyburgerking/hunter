# -*- coding: utf-8 -*-
""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import random
import sys

from benches.games import GAMES
from hunter.api import HunterEngine, load_spec

SETTINGS = {
    "2048": "specs/2048.json",
    "flappy": "specs/flappy.json",
    "pong": "specs/pong.json",
}

EVAL_SEEDS = list(range(1000, 1005))


def run_episode(env_cls, params, seeds):
    total = 0.0
    stats = []
    for s in seeds:
        state = random.getstate()
        random.seed(s)
        env = env_cls()
        obs = env.reset()
        done = False
        while not done:
            obs, reward, done, _ = env.step(env.act(params, obs))
            total += reward
        if hasattr(env, "score"):
            stats.append(env.score)
        elif hasattr(env, "passed"):
            stats.append(env.passed)
        else:
            stats.append(env.hits)
        random.setstate(state)
    return total / len(seeds), stats


def main():
    name = sys.argv[1] if len(sys.argv) > 1 else "2048"
    episodes = int(sys.argv[2]) if len(sys.argv) > 2 else 60
    env_cls = GAMES[name]
    spec = load_spec(SETTINGS[name])
    engine = HunterEngine(spec, seed=5)

    best = {"raw": -1e9, "params": None, "stats": None}
    for ep in range(episodes):
        engine.begin_episode()
        params = engine.decode_params()
        total = 0.0
        stats = []
        for s in EVAL_SEEDS:
            state = random.getstate()
            random.seed(s)
            env = env_cls()
            obs = env.reset()
            done = False
            while not done:
                out = engine.tick(obs)
                obs, reward, done, _ = env.step(env.act(out["params"], obs))
                total += reward
                engine.feedback(reward, False)
            if hasattr(env, "score"):
                stats.append(env.score)
            elif hasattr(env, "passed"):
                stats.append(env.passed)
            else:
                stats.append(env.hits)
            random.setstate(state)
        avg = total / len(EVAL_SEEDS)
        engine.end_episode(success=avg)
        if avg > best["raw"]:
            best = {"raw": avg, "params": params, "stats": stats}
        if (ep + 1) % 10 == 0:
            st = engine.state()
            print("%3d 局  本局 %.2f  最好 %.2f  %s  池 %d  地形 %.2f"
                  % (ep + 1, avg, best["raw"], params,
                     st["memory"], st["terrain"]))

    print("--- 最优 ---")
    print(json.dumps(best, ensure_ascii=False, indent=2))
    print("--- 最优参数复测 ---")
    avg, stats = run_episode(env_cls, best["params"], EVAL_SEEDS)
    print("avg %.2f  stats %s" % (avg, stats))


if __name__ == "__main__":
    main()
