# -*- coding: utf-8 -*-
""
import argparse
import glob
import io
import json
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from hunter import payload, search, sense, primitives, parallel   # noqa: E402
from benches.arcade import registry                              # noqa: E402

SLOW = {"game2048", "pvz_ext", "pacman_ext"}
HEAVY_EASY = {"tetris", "tetris_local"}      


def check_arcade(quick=False):
    from scripts.run_arcade import run_one
    rows, bad = [], []
    for name in sorted(registry.GAMES):
        if quick and name in SLOW:
            continue
        t0 = time.time()
        r = run_one(name)
        score, ok = float(r["score"]), bool(r["ok"])
        env = registry.make(name)
        rows.append((name, score, env.FULL, ok, time.time() - t0))
        if not ok:
            bad.append(name)
    for name, score, full, ok, dt in rows:
        print("  %-18s %9.2f / %-9.2f %s  %5.1fs"
              % (name, score, full, "ok" if ok else "FAIL", dt))
    return bad


def check_payload(quick=False):
    bad = []
    files = sorted(glob.glob(os.path.join(ROOT, "out", "payload", "*.json")))
    from scripts.train_payload import FACTORIES, game_of          # noqa: E402
    for path in files:
        name = os.path.basename(path)[:-5]
        if quick and name in SLOW:
            continue
        with io.open(path, encoding="utf-8") as fh:
            saved = json.load(fh)
        spec = saved["spec"]
        game = game_of(spec)
        space = payload.PayloadSpace(spec)
        env = FACTORIES[game]()
        env.reset()
        score, _ = space.play(env, saved["payload"])
        want = float(saved.get("score", 0.0))
        if game == "pacman":            
            left = len(env.state.getFood().asList())
            ok = left == 0
            print("  %-18s 剩豆 %d  %s" % (name, left, "ok" if ok else "FAIL"))
            if not ok:
                bad.append(name)
            continue
        ok = abs(score - want) < 1e-6
        print("  %-18s %9.2f / %-9.2f %s" % (name, score, want, "ok" if ok else "FAIL"))
        if not ok:
            bad.append(name)
    return bad


def check_easy(quick=False):
    ""
    from hunter import easy
    bad = []
    files = sorted(glob.glob(os.path.join(ROOT, "specs", "easy", "*.json")))
    for path in files:
        name = os.path.basename(path)[:-5]
        if quick and (name in SLOW or name in HEAVY_EASY):
            continue
        try:
            
            rep = easy.solve(path, episodes=1, verbose=False)
            best = rep.get("best") or rep.get("训练最好") or 0
            ok = True
        except Exception as exc:                          # noqa: BLE001
            best, ok = str(exc)[:40], False
        print("  %-18s %s" % (name, "ok" if ok else "FAIL: %s" % best))
        if not ok:
            bad.append(name)
    return bad


def check_core():
    bad = []

    
    from benches.arcade.registry import make
    env = make("sokoban5_ext")
    space = payload.PayloadSpace(env.spec())
    plan, score = search.plan_search(space, lambda: make("sokoban5_ext"),
                                     steps=env.spec()["steps"], beam=12)
    ok = abs(score - env.FULL) < 1e-6
    print("  search            %.2f / %.2f  %s" % (score, env.FULL, "ok" if ok else "FAIL"))
    bad += [] if ok else ["search"]

    
    b = sense.Binner.fit([], bins=5, bounds=((-1.0, 1.0), (-1.0, 1.0)))
    ok = b.size == 25
    print("  sense             %d 档  %s" % (b.size, "ok" if ok else "FAIL"))
    bad += [] if ok else ["sense"]

    
    atoms = [{"op": "go", "dir": d} for d in ("u", "d", "l", "r")]
    prims = primitives.discover(lambda: make("maze_small"), atoms, depth=3,
                                samples=8, top=4, seed=3)
    ok = len(prims) > 0 and prims[0].get("op") == "seq"
    print("  primitives        发现 %d 个  %s" % (len(prims), "ok" if ok else "FAIL"))
    bad += [] if ok else ["primitives"]

    
    env = make("corridor")
    space = payload.PayloadSpace(env.spec())
    spec = env.spec()
    result = payload.evolve(spec, lambda: make("corridor"),
                            rounds=int(spec.get("rounds", 24)),
                            swarm=int(spec.get("swarm", 16)),
                            reps=1, seed=7, verbose=False)
    e2 = make("corridor")
    e2.reset()
    score, _ = space.play(e2, result["best"]["payload"])
    ok = abs(score - env.FULL) < 1e-6
    print("  stage             %.2f / %.2f  %s" % (score, env.FULL, "ok" if ok else "FAIL"))
    bad += [] if ok else ["stage"]

    
    spec = make("snake").spec()
    genes = ["AGCTA" * 8, "TGCAT" * 8, "GGGGA" * 8]
    a = parallel.map_scores("benches.arcade.registry:make", ("snake",), spec,
                            genes, workers=1)
    b2 = parallel.map_scores("benches.arcade.registry:make", ("snake",), spec,
                             genes, workers=3)
    ok = a == b2
    print("  parallel          串行=并行  %s" % ("ok" if ok else "FAIL"))
    bad += [] if ok else ["parallel"]
    return bad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    args = ap.parse_args()

    print("① 街机库")
    bad_a = check_arcade(args.quick)
    print("\n② payload 存档")
    bad_p = check_payload(args.quick)
    print("\n③ 傻瓜层 specs/easy")
    bad_e = check_easy(args.quick)
    print("\n④ 核能力")
    bad_c = check_core()

    bad = bad_a + bad_p + bad_e + bad_c
    print("\n%s" % ("全部通过" if not bad else "失败：" + ", ".join(bad)))
    if bad:
        sys.exit(1)


if __name__ == "__main__":
    main()
