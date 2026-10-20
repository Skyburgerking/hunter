# -*- coding: utf-8 -*-
""
import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from hunter import payload  # noqa: E402

FACTORIES = {
    "sokoban5": lambda: __import__("benches.thirdparty.sokoban_env", fromlist=["SokobanEnv"])
                          .SokobanEnv(level="test5", cap=24, situation_mode="side"),
    "sokoban": lambda: __import__("benches.thirdparty.sokoban_env", fromlist=["SokobanEnv"])
                          .SokobanEnv(level="test2", cap=12),
    "pacman": lambda: __import__("benches.thirdparty.pacman_env", fromlist=["PacmanEnv"])
                          .PacmanEnv(layout_name="mediumClassic", ghosts=2, cap=400),
    "pvz": lambda: __import__("benches.thirdparty.pvz_env", fromlist=["PvZEnv"])
                       .PvZEnv(level_num=1, cards=[0, 1, 3], frames_per_step=40, cap=260),
    "rts": lambda: __import__("benches.thirdparty.rts_env", fromlist=["RTSEnv"])
                       .RTSEnv(cap=80),
}


def game_of(spec):
    name = spec.get("name", "")
    for key in sorted(FACTORIES, key=len, reverse=True):   
        if name.startswith(key):
            return key
    raise SystemExit("spec 名要以游戏开头（sokoban5/sokoban/pacman/pvz/rts），收到 %r" % name)


def game_of(spec):
    name = spec.get("name", "")
    for key in sorted(FACTORIES, key=len, reverse=True):
        if name.startswith(key):
            return key
    raise SystemExit("spec 名要以游戏开头（sokoban5/sokoban/pacman/pvz/rts），收到 %r" % name)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("spec")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--rounds", type=int, default=None)
    ap.add_argument("--swarm", type=int, default=None, help="蜂群大小")
    ap.add_argument("--reps", type=int, default=None)
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    with open(args.spec, encoding="utf-8") as fh:
        spec = json.load(fh)
    game = game_of(spec)
    rounds = args.rounds or spec.get("rounds", 120)
    swarm = args.swarm or spec.get("swarm", spec.get("population", 30))
    reps = args.reps or spec.get("reps", 2)

    result = payload.evolve(spec, FACTORIES[game], rounds=rounds,
                            swarm=swarm, reps=reps,
                            seed=args.seed, verbose=not args.quiet)
    best = result["best"]      
    print("\n══════════════════════════════════════════════")
    print("任务 %-16s ｜ %d 轮 × 蜂群 %d × %d 次 ｜ 最好 %s（第 %d 代）"
          % (spec["name"], rounds, swarm, reps,
             round(best["score"], 2), best["gen"] + 1))
    print("payload:")
    print(json.dumps(best["payload"], ensure_ascii=False, indent=1)[:1600])

    out = os.path.join(ROOT, "out", "payload", spec["name"] + ".json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        json.dump({"spec": spec, "payload": best["payload"],
                   "score": best["score"], "gen": best["gen"],
                   "history": result["history"][-1]}, fh,
                  ensure_ascii=False, indent=2)
    print("存档 %s" % out)


if __name__ == "__main__":
    main()
