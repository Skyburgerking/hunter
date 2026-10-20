# -*- coding: utf-8 -*-
""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import random
import sys
import time

from hunter.api import HunterEngine, load_spec
from benches.official import OfficialTetris

TARGET = 20_000_000
SPEC = "specs/tetris_official.json"


def main():
    episodes = int(sys.argv[1]) if len(sys.argv) > 1 else 200
    spec = load_spec(SPEC)
    
    
    spec["max_score"] = 1.0
    engine = HunterEngine(spec, seed=7)

    t_start = time.time()
    best = {"score": 0, "lines": 0, "weights": None, "seed": None}

    for ep in range(episodes):
        engine.begin_episode()
        weights = engine.policy.weights(engine.segment)
        seed = 1000 + ep

        state = random.getstate()
        env = OfficialTetris(seed=seed)
        random.setstate(state)

        done = False
        while not done:
            idx = engine.act(env)
            done = env.step(idx)

        norm = min(1.0, env.score / TARGET)
        engine.end_episode(success=norm)

        if env.score > best["score"]:
            best = {"score": env.score, "lines": env.lines,
                    "weights": dict(weights), "seed": seed}

        elapsed = time.time() - t_start
        print("%3d 局  种子 %d  %5d 行  %9d 分  %5d 块  最好 %9d  %.0fs"
              % (ep + 1, seed, env.lines, env.score, env.pieces,
                 best["score"], elapsed), flush=True)

        if env.score >= TARGET:
            print("达标：%d 分 / %d 行 / %d 块" % (env.score, env.lines, env.pieces), flush=True)
            break

    print("--- 最好一局 ---", flush=True)
    print(json.dumps(best, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
