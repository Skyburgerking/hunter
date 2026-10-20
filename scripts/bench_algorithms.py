# -*- coding: utf-8 -*-
""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import itertools
import json
import math
import random
import statistics
import sys

from benches.basics import ENVS
from hunter.api import HunterEngine, load_spec

BUDGET = 40
TEST_SEEDS = list(range(1000, 1030))



def space_of(spec):
    keys = list(spec["params"].keys())
    axes = []
    for k in keys:
        vals = []
        for v in spec["params"][k]["values"]:
            if v not in vals:
                vals.append(v)
        axes.append(vals)
    combos = list(itertools.product(*axes))
    return keys, combos


def run_episodes(env_cls, params, seeds):
    total = 0.0
    for s in seeds:
        state = random.getstate()      
        random.seed(s)
        env = env_cls()
        obs = env.reset()
        done = False
        while not done:
            obs, reward, done, _ = env.step(env.act(params, obs))
            total += reward
        random.setstate(state)
    return total / max(1, len(seeds))


def evaluate3(env_cls, params, base=0):
    
    return run_episodes(env_cls, params, TEST_SEEDS[:10])


def single_episode(env_cls, params, seed):
    random.seed(seed)
    env = env_cls()
    obs = env.reset()
    total = 0.0
    done = False
    while not done:
        obs, reward, done, _ = env.step(env.act(params, obs))
        total += reward
    return total


def to_params(keys, combo):
    return {k: v for k, v in zip(keys, combo)}


def is_close(a, b):
    return abs(a - b) < 1e-9



def search_random(keys, combos, env_cls, budget, seed=11):
    rng = random.Random(seed)
    best, best_score = None, -1e9
    for _ in range(budget):
        combo = rng.choice(combos)
        s = evaluate3(env_cls, to_params(keys, combo), rng.randrange(10 ** 6))
        if s > best_score:
            best, best_score = combo, s
    return to_params(keys, best), best_score


def search_grid(keys, combos, env_cls, budget):
    best, best_score = None, -1e9
    for i, combo in enumerate(combos[:budget]):
        s = evaluate3(env_cls, to_params(keys, combo), 100 + i * 3)
        if s > best_score:
            best, best_score = combo, s
    return to_params(keys, best), best_score


def search_hill(keys, combos, env_cls, budget, seed=13):
    rng = random.Random(seed)
    cur = rng.choice(combos)
    cur_score = evaluate3(env_cls, to_params(keys, cur), rng.randrange(10 ** 6))
    best, best_score = cur, cur_score
    for _ in range(budget - 1):
        nxt = list(cur)
        dim = rng.randrange(len(nxt))
        
        options = [c for c in combos if sum(1 for x, y in zip(c, cur) if not is_close(x, y)) == 1]
        if options:
            nxt = rng.choice(options)
        else:
            nxt = rng.choice(combos)
        s = evaluate3(env_cls, to_params(keys, nxt), rng.randrange(10 ** 6))
        if s >= cur_score:
            cur, cur_score = nxt, s
        if s > best_score:
            best, best_score = nxt, s
    return to_params(keys, best), best_score


def search_sa(keys, combos, env_cls, budget, t0=1.0, seed=17):
    rng = random.Random(seed)
    cur = rng.choice(combos)
    cur_score = evaluate3(env_cls, to_params(keys, cur), rng.randrange(10 ** 6))
    best, best_score = cur, cur_score
    for i in range(budget - 1):
        temp = max(0.02, t0 * (1 - i / budget))
        options = [c for c in combos if sum(1 for x, y in zip(c, cur) if not is_close(x, y)) == 1]
        nxt = rng.choice(options) if options else rng.choice(combos)
        s = evaluate3(env_cls, to_params(keys, nxt), rng.randrange(10 ** 6))
        if s >= cur_score or rng.random() < math.exp((s - cur_score) / max(1e-6, temp)):
            cur, cur_score = nxt, s
        if s > best_score:
            best, best_score = nxt, s
    return to_params(keys, best), best_score


def search_ga(keys, combos, env_cls, budget, pop=8, seed=19):
    rng = random.Random(seed)
    population = [list(rng.choice(combos)) for _ in range(pop)]
    scored = []
    used = 0
    while used < budget:
        for g in population:
            if used >= budget:
                break
            s = evaluate3(env_cls, to_params(keys, g), rng.randrange(10 ** 6))
            scored.append((s, g))
            used += 1
        scored.sort(reverse=True, key=lambda x: x[0])
        elites = [list(g) for _s, g in scored[:2]]
        population = [list(e) for e in elites]
        while len(population) < pop:
            a = list(rng.choice(scored[:max(2, len(scored) // 2)])[1])
            b = list(rng.choice(scored[:max(2, len(scored) // 2)])[1])
            cut = rng.randrange(len(a))
            child = a[:cut] + b[cut:]
            for i in range(len(child)):
                if rng.random() < 0.2:
                    child[i] = rng.choice([c[i] for c in combos])
            population.append(child)
    best = max(scored, key=lambda x: x[0])
    return to_params(keys, best[1]), best[0]


def search_hunter(spec, env_cls, budget, reps=10, seed=23):
    engine = HunterEngine(spec, seed=seed)
    best_params, best_score = None, -1e9
    for i in range(budget):
        engine.begin_episode()
        total = 0.0
        last = None
        for k in range(reps):
            state = random.getstate()
            random.seed(TEST_SEEDS[k])
            env = env_cls()
            obs = env.reset()
            done = False
            while not done:
                out = engine.tick(obs)
                last = out["params"]
                obs, reward, done, _ = env.step(env.act(out["params"], obs))
                total += reward
                engine.feedback(reward, False)
            random.setstate(state)
        engine.end_episode(success=total / reps)
        avg = total / reps
        if avg > best_score:
            best_params, best_score = last, avg
    return best_params, best_score



TASKS = [
    ("drone", "specs/drone.json", "空中拦截"),
    ("snake", "specs/snake.json", "贪吃蛇"),
    ("grid", "specs/grid.json", "网格寻宝"),
    ("guess", "specs/guess.json", "猜数"),
    ("queue", "specs/queue.json", "任务调度"),
]

ALGOS = ["random", "grid", "hill", "sa", "ga", "hunter"]


def main():
    budget = int(sys.argv[1]) if len(sys.argv) > 1 else BUDGET
    print("=" * 96)
    print("六种算法 / 五个任务 / 每任务 %d 次评估 / 测试 30 回合" % budget)
    print("=" * 96)
    header = "%-8s %-10s" % ("任务", "oracle")
    for a in ALGOS:
        header += " %-8s" % a
    print(header + "   最优参数")
    print("-" * 96)

    for key, path, label in TASKS:
        spec = load_spec(path)
        keys, combos = space_of(spec)
        env_cls = ENVS[key]
        # oracle
        oracle_score, oracle_combo = -1e9, None
        for combo in combos:
            s = run_episodes(env_cls, to_params(keys, combo), TEST_SEEDS)
            if s > oracle_score:
                oracle_score, oracle_combo = s, combo
        row = "%-8s %-10.3f" % (label, oracle_score)
        results = {}
        for algo in ALGOS:
            if algo == "random":
                params, _ = search_random(keys, combos, env_cls, budget)
            elif algo == "grid":
                params, _ = search_grid(keys, combos, env_cls, budget)
            elif algo == "hill":
                params, _ = search_hill(keys, combos, env_cls, budget)
            elif algo == "sa":
                params, _ = search_sa(keys, combos, env_cls, budget)
            elif algo == "ga":
                params, _ = search_ga(keys, combos, env_cls, budget)
            else:
                params, _ = search_hunter(spec, env_cls, budget)
            final = run_episodes(env_cls, params, TEST_SEEDS)
            results[algo] = final
            row += " %-8.3f" % final
        print(row)
        best_algo = max(results, key=results.get)
        print("         oracle 参数 %s   最佳算法 %s   差距 %.1f%%" %
              (dict(zip(keys, oracle_combo)), best_algo,
               100.0 * (oracle_score - results[best_algo]) / max(1e-9, abs(oracle_score))))
    print("=" * 96)


if __name__ == "__main__":
    main()
