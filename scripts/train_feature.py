# -*- coding: utf-8 -*-
""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import random
import sys

from hunter.api import HunterEngine, load_spec

SETTINGS = {
    "tetris": "specs/tetris_feature.json",
    "tetris2": "specs/tetris_feature2.json",
}

ENVS = {
    "tetris": ("tetris", "TetrisEnv"),
}


def make_env(name, seed, max_pieces):
    if name.startswith("tetris"):
        from benches.tetris import TetrisEnv
        return TetrisEnv(seed=seed, max_pieces=max_pieces)
    raise KeyError(name)


def evaluate(engine, name, seeds, max_pieces):
    total = 0.0
    stats = []
    for s in seeds:
        state = random.getstate()
        random.seed(s)
        env = make_env(name, s, max_pieces)
        obs = env.reset()
        done = False
        while not done:
            action = engine.act(env)
            obs, reward, done, _ = env.step(action)
            total += reward
            engine.feedback(reward, False)
        stats.append(env.lines)
        random.setstate(state)
    return total / len(seeds), stats


def main():
    name = sys.argv[1] if len(sys.argv) > 1 else "tetris"
    episodes = int(sys.argv[2]) if len(sys.argv) > 2 else 60
    n_seeds = int(sys.argv[3]) if len(sys.argv) > 3 else 2
    max_pieces = int(sys.argv[4]) if len(sys.argv) > 4 else 150

    
    import benches.tetris  # noqa: F401
    spec = load_spec(SETTINGS[name])
    engine = HunterEngine(spec, seed=5)
    seeds = list(range(2000, 2000 + n_seeds))

    best = {"raw": -1e9, "weights": None, "stats": None}
    for ep in range(episodes):
        engine.begin_episode()
        weights = engine.policy.weights(engine.segment)
        avg, stats = evaluate(engine, name, seeds, max_pieces)
        engine.end_episode(success=avg)
        if avg > best["raw"]:
            best = {"raw": avg, "weights": weights, "stats": stats}
        if (ep + 1) % 10 == 0:
            st = engine.state()
            print("%3d 局  本局 %.2f  最好 %.2f  池 %d  地形 %.2f"
                  % (ep + 1, avg, best["raw"], st["memory"], st["terrain"]))

    print("--- 最优 ---")
    print(json.dumps(best, ensure_ascii=False, indent=2))
    print("--- 用最优权重复测（3 个新种子）---")
    from hunter.policy import FeaturePolicy
    pol = FeaturePolicy(spec)
    lines = []
    for s in range(3000, 3003):
        env = make_env(name, s, max_pieces)
        env.reset()
        done = False
        while not done:
            action = pol.choose(env, best["weights"])
            _, _, done, _ = env.step(action)
        lines.append(env.lines)
    print("lines %s  avg %.1f" % (lines, sum(lines) / len(lines)))


if __name__ == "__main__":
    main()
