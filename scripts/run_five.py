# -*- coding: utf-8 -*-
""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import random
import shutil
import statistics
import sys

from benches.basics import ENVS
from hunter.api import HunterEngine, load_spec

TASKS = [
    ("drone", "specs/drone.json", "空中拦截"),
    ("snake", "specs/snake.json", "贪吃蛇"),
    ("grid", "specs/grid.json", "网格寻宝"),
    ("guess", "specs/guess.json", "猜数"),
    ("queue", "specs/queue.json", "任务调度"),
]

BASES = "AGCTX"


def run_hunter(spec, env_cls, episodes, seed=7, reps=5):
    ""
    engine = HunterEngine(spec, seed=seed)
    param_mode = spec.get("mode") == "param"
    scores = []
    for _ in range(episodes):
        engine.begin_episode()
        total = 0.0
        for k in range(reps):
            state = random.getstate()
            random.seed(1000 + k)
            env = env_cls()
            obs = env.reset()
            done = False
            while not done:
                out = engine.tick(obs)
                action = env.act(out["params"], obs) if param_mode else out["action"]
                obs, reward, done, _info = env.step(action)
                total += reward
                engine.feedback(reward, False)
            random.setstate(state)
        engine.end_episode(success=total / reps)
        scores.append(total / reps)
    return engine, scores


def run_random(spec, env_cls, episodes, seed=7):
    ""
    rng = random.Random(seed)
    env = env_cls()
    scores = []
    param_mode = spec.get("mode") == "param"
    keys = list(spec.get("params", {}).keys())
    actions = []
    if not param_mode:
        actions = [a["name"] for b in BASES
                   for a in spec.get("actions", {}).get(b, [])]
    for _ in range(episodes):
        params = {k: rng.choice(spec["params"][k]["values"]) for k in keys}
        total = 0.0
        for k in range(5):
            state = random.getstate()
            random.seed(1000 + k)
            env = env_cls()
            obs = env.reset()
            done = False
            while not done:
                action = env.act(params, obs) if param_mode else rng.choice(actions)
                obs, reward, done, _info = env.step(action)
                total += reward
            random.setstate(state)
        scores.append(total / 5.0)
    return scores


def summarize(scores, head=50):
    early = statistics.mean(scores[:head])
    late = statistics.mean(scores[-head:])
    best = max(scores)
    return early, late, best


def main():
    episodes = int(sys.argv[1]) if len(sys.argv) > 1 else 200
    if os.path.isdir(".memory"):
        shutil.rmtree(".memory")
    print("=" * 78)
    print("通用 hunter：五份 spec，五件事，每件 %d 回合" % episodes)
    print("=" * 78)
    print("%-8s %-10s %-14s %-8s %-8s %-8s" %
          ("setting", "任务", "动作数", "前50", "后50", "随机基线"))
    print("-" * 78)
    rows = []
    for key, path, label in TASKS:
        spec = load_spec(path)
        env_cls = ENVS[key]
        engine, scores = run_hunter(spec, env_cls, episodes)
        rand_scores = run_random(spec, env_cls, episodes)
        e1, e2, best = summarize(scores)
        r1, r2, _ = summarize(rand_scores)
        rows.append((key, label, e1, e2, best, r2, engine))
        n_actions = (len(spec["params"]) if spec.get("params")
                     else sum(len(v) for v in spec.get("actions", {}).values()))
        print("%-8s %-10s %-14d %-8.3f %-8.3f %-8.3f" %
              (key, label, n_actions, e1, e2, r2))
    print("-" * 78)
    for key, label, e1, e2, best, r2, engine in rows:
        gain = (e2 - r2) * 100
        print("%-8s 学习增益 %+6.1f 百分点   记忆池 %2d   最优段 %s" %
              (key, gain, len(engine.core.memory_pool),
               engine.best["segment"] if engine.best else "-"))
    print("=" * 78)


if __name__ == "__main__":
    main()
