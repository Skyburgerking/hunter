# -*- coding: utf-8 -*-
""
import argparse
import json
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from hunter import payload                      # noqa: E402
from benches.arcade import registry             # noqa: E402


def run_one(name, rounds=None, swarm=None, verbose=False, workers=1):
    env = registry.make(name)
    spec = env.spec()
    if rounds:
        spec["rounds"] = rounds
    if swarm:
        spec["swarm"] = swarm
    t0 = time.time()
    
    seed = getattr(env, "SEED_PAYLOAD", None)
    if seed:
        probe = registry.make(name)
        probe.reset()
        cap = spec.get("steps") if spec.get("renderer") == "plan" else None
        score, steps = payload.PayloadSpace(spec).play(probe, seed, cap=cap)
        if abs(score - env.FULL) < 1e-6:
            return {"name": name, "score": float(score), "full": float(env.FULL),
                    "ok": True, "steps": steps, "elapsed": time.time() - t0,
                    "payload": seed, "spec": spec, "from_seed": True}
    result = payload.evolve(spec, lambda: registry.make(name),
                            rounds=spec["rounds"],
                            swarm=spec.get("swarm", 16),
                            reps=spec.get("reps", 1), seed=7, verbose=verbose,
                            workers=workers,
                            factory_ref="benches.arcade.registry:make",
                            factory_args=(name,))
    best = result["best"]
    space = result["space"]
    
    env2 = registry.make(name)
    env2.reset()
    score, steps = space.play(env2, best["payload"])
    return {
        "name": name,
        "score": float(score),
        "full": float(env.FULL),
        "ok": abs(score - env.FULL) < 1e-6,
        "steps": steps,
        "elapsed": time.time() - t0,
        "payload": best["payload"],
        "spec": spec,
        "from_seed": False,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("games", nargs="*")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--rounds", type=int, default=None)
    ap.add_argument("--swarm", type=int, default=None, help="蜂群大小")
    ap.add_argument("-v", "--verbose", action="store_true")
    ap.add_argument("--workers", type=int, default=1, help="蜂群多进程数")
    ap.add_argument("--save", action="store_true", help="把 spec 和存档写进 out/arcade")
    ap.add_argument("--controls", action="store_true", help="跑对照组（故意打不满的）")
    args = ap.parse_args()

    if args.list:
        for name in sorted(registry.GAMES):
            env = registry.make(name)
            print("%-18s 满分 %-8s %s" % (name, env.FULL, env.RENDERER))
        print("")
        print("对照组（故意打不满）：" + ", ".join(sorted(registry.CONTROLS)))
        return

    pool = registry.CONTROLS if args.controls else registry.GAMES
    names = args.games or sorted(pool)
    rows, fails = [], []
    for name in names:
        try:
            r = run_one(name, args.rounds, args.swarm, args.verbose,
                        args.workers)
        except Exception as exc:                     # noqa: BLE001
            print("%-14s ✗ %s: %s" % (name, type(exc).__name__, exc), flush=True)
            fails.append(name)
            continue
        rows.append(r)
        print("%-14s %8.2f / %-6.2f  %s  %5.1fs  %d 步"
              % (name, r["score"], r["full"], "满分" if r["ok"] else "未满",
                 r["elapsed"], r["steps"]), flush=True)
        if not r["ok"]:
            fails.append(name)
        if args.save:
            out = os.path.join(ROOT, "out", "arcade")
            os.makedirs(out, exist_ok=True)
            with open(os.path.join(out, name + ".json"), "w", encoding="utf-8") as fh:
                json.dump(r, fh, ensure_ascii=False, indent=2)

    print("\n%d 款：满分 %d，未满 %d"
          % (len(rows) + len(fails), len(rows) - len([r for r in rows if not r["ok"]]),
             len(fails)))
    if fails:
        print("未满：" + ", ".join(fails))
        sys.exit(1)


if __name__ == "__main__":
    main()
