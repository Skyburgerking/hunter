# -*- coding: utf-8 -*-
""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import statistics
import sys

from bench import (ALGOS, ENVS, TASKS, evaluate3, run_episodes, search_ga,
                   search_grid, search_hill, search_hunter, search_random,
                   search_sa, space_of, to_params, TEST_SEEDS)
from hunter.api import load_spec

REPEATS = int(sys.argv[1]) if len(sys.argv) > 1 else 3
BUDGET = int(sys.argv[2]) if len(sys.argv) > 2 else 40


def one(spec, env_cls, keys, combos, algo, seed):
    if algo == "random":
        params, _ = search_random(keys, combos, env_cls, BUDGET, seed=seed)
    elif algo == "grid":
        params, _ = search_grid(keys, combos, env_cls, BUDGET)
    elif algo == "hill":
        params, _ = search_hill(keys, combos, env_cls, BUDGET, seed=seed)
    elif algo == "sa":
        params, _ = search_sa(keys, combos, env_cls, BUDGET, seed=seed)
    elif algo == "ga":
        params, _ = search_ga(keys, combos, env_cls, BUDGET, seed=seed)
    else:
        params, _ = search_hunter(spec, env_cls, BUDGET, seed=seed)
    return run_episodes(env_cls, params, TEST_SEEDS)


def main():
    print("=" * 100)
    print("多种子重复 %d 次，预算 %d 次评估，测试 30 回合，报均值" % (REPEATS, BUDGET))
    print("=" * 100)
    print("%-10s %-8s" % ("任务", "oracle") + "".join(" %-9s" % a for a in ALGOS) + "   满分率")
    print("-" * 100)
    totals = {a: [] for a in ALGOS}
    for key, path, label in TASKS:
        spec = load_spec(path)
        keys, combos = space_of(spec)
        env_cls = ENVS[key]
        oracle = max(run_episodes(env_cls, to_params(keys, c), TEST_SEEDS) for c in combos)
        row = "%-10s %-8.3f" % (label, oracle)
        full = {}
        for algo in ALGOS:
            vals = [one(spec, env_cls, keys, combos, algo, 100 + i * 7) for i in range(REPEATS)]
            avg = statistics.mean(vals)
            totals[algo].extend(vals)
            row += " %-9.3f" % avg
            full[algo] = sum(1 for v in vals if v >= oracle - 1e-6) / REPEATS
        best_algo = max(full, key=full.get)
        row += "   最佳 %s" % best_algo
        print(row)
    print("-" * 100)
    for a in ALGOS:
        print("%-8s 平均 %.3f  方差 %.4f" % (a, statistics.mean(totals[a]),
                                            statistics.pvariance(totals[a])))
    print("=" * 100)


if __name__ == "__main__":
    main()


import os
import sys


