# -*- coding: utf-8 -*-
""
import json
import random
import time


def apply_item(env, item):
    ""
    if isinstance(item, dict) and item.get("op") == "seq":
        done = False
        for sub in item.get("steps", []):
            done = env.apply(sub)
            if done:
                break
        return done
    return env.apply(item)


def fragments(space):
    ""
    out, seen = [], set()
    for base in ("A", "G", "C", "T", "X"):
        for frag in getattr(space, "slots", {}).get(base, []):
            key = json.dumps(frag, sort_keys=True, ensure_ascii=False)
            if key not in seen:
                seen.add(key)
                out.append(frag)
    return out


# ══════════════════════════════════════════════════════════
def plan_search(space, env_factory, steps=None, beam=12, cap=None, budget=None,
                seed_plan=None):
    ""
    frags = fragments(space)
    if not frags:
        return None, -1e18
    steps = int(steps or getattr(space, "steps", 1))

    def _score(prefix):
        env = env_factory()
        env.reset()
        for item in prefix:
            apply_item(env, item)
        return float(getattr(env, "score", 0.0))

    
    beamv = [([], 0.0)]
    if seed_plan:
        seed = list(seed_plan)[:steps]
        beamv.append((seed, _score(seed)))
    t0 = time.time()
    for _ in range(steps):
        if budget and time.time() - t0 > budget:
            break
        cand = []
        for prefix, score in beamv:
            if len(prefix) >= steps:          
                cand.append((prefix, score))
                continue
            for frag in frags:
                cand.append((prefix + [frag], _score(prefix + [frag])))
        cand.sort(key=lambda t: -t[1])
        beamv = cand[:max(1, int(beam))]
    best_plan, best_score = max(beamv, key=lambda t: t[1])
    return {"steps": best_plan}, best_score


def plan_refine(space, env_factory, base_plan=None, beam=12, cap=None,
                budget=None):
    ""
    plan, score = plan_search(space, env_factory, steps=len(base_plan or []) or None,
                              beam=beam, cap=cap, budget=budget,
                              seed_plan=base_plan)
    return plan, score


# ══════════════════════════════════════════════════════════
def _eval_table(space, env_factory, table, cap=None, reps=1):
    total = 0.0
    for _ in range(max(1, reps)):
        env = env_factory()
        env.reset()
        score, _ = space.play(env, {"table": list(table)}, cap=cap)
        total += score
    return total / max(1, reps)


def table_search(space, env_factory, sweeps=4, restarts=2, cap=None, budget=None,
                 reps=1, seed_table=None):
    ""
    frags = fragments(space)
    if not frags:
        return None, -1e18
    n = int(getattr(space, "conditions", 1))
    starts = []
    if seed_table:
        starts.append(list(seed_table))
    starts.append([frags[0]] * n)
    for frag in frags[1:3]:
        starts.append([frag] * n)
    for _ in range(max(0, int(restarts))):
        starts.append([random.choice(frags) for _ in range(n)])

    best_table, best_score = None, -1e18
    t0 = time.time()
    for table in starts:
        if budget and time.time() - t0 > budget:
            break
        table = (list(table) + [frags[0]] * n)[:n]
        score = _eval_table(space, env_factory, table, cap, reps)
        for _ in range(int(sweeps)):
            improved = False
            for i in range(n):
                if budget and time.time() - t0 > budget:
                    break
                for frag in frags:
                    trial = list(table)
                    trial[i] = frag
                    s = _eval_table(space, env_factory, trial, cap, reps)
                    if s > score + 1e-9:
                        table, score, improved = trial, s, True
            if not improved:
                break
        if score > best_score:
            best_table, best_score = table, score
    return ({"table": best_table} if best_table is not None else None), best_score


# ══════════════════════════════════════════════════════════
def refine(space, env_factory, best, beam=12, budget=30.0, reps=1,
           sweeps=4, restarts=1):
    ""
    renderer = getattr(space, "renderer", "plan")
    t0 = time.time()
    if renderer == "plan":
        base = (best or {}).get("payload", {}).get("steps")
        plan, score = plan_search(space, env_factory,
                                  steps=getattr(space, "steps", None),
                                  beam=beam, budget=budget, seed_plan=base)
    elif renderer == "stage":
        plan, score = stage_search(space, env_factory, beam=beam, budget=budget,
                                   seed_table=(best or {}).get("payload", {}).get("table"))
    else:
        table, score = table_search(space, env_factory, sweeps=sweeps,
                                    restarts=restarts, budget=budget, reps=reps,
                                    seed_table=(best or {}).get("payload", {}).get("table"))
        plan = table
    elapsed = time.time() - t0
    if plan is None:
        return None, -1e18, elapsed
    return plan, score, elapsed


# ══════════════════════════════════════════════════════════
def stage_search(space, env_factory, beam=12, budget=None, seed_table=None):
    ""
    frags = fragments(space)
    if not frags:
        return None, -1e18
    stages = int(getattr(space, "stages", 1))
    total = stages * int(getattr(space, "conditions", 1))
    return table_search(space, env_factory, sweeps=4, restarts=1,
                        budget=budget, reps=1,
                        seed_table=seed_table or [None] * total)
