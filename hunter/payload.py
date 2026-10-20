# -*- coding: utf-8 -*-
""

import copy
import json
import os
import random
import time

from hunter.core import BASES, GedaCore
from hunter import search

DEFAULT_FRAGMENT = {"op": "wait"}


# ══════════════════════════════════════════════════════════
class PayloadSpace(object):
    ""

    def __init__(self, spec):
        self.slots = dict(spec.get("slots") or {})
        for b in BASES:
            self.slots.setdefault(b, [DEFAULT_FRAGMENT])
        self.renderer = spec.get("renderer", "plan")
        if self.renderer not in ("plan", "table", "stage"):
            raise ValueError("renderer 只能是 plan / table / stage，收到 %r" % self.renderer)
        self.steps = int(spec.get("steps", 20))
        self.conditions = int(spec.get("conditions", 4))
        self.stages = int(spec.get("stages", 1))
        if self.renderer == "plan":
            self.slots_per_gene = self.steps
        elif self.renderer == "stage":
            self.slots_per_gene = self.conditions * self.stages   
        else:
            self.slots_per_gene = self.conditions

    def pick(self, segment, i):
        ""
        base = segment[i % len(segment)]
        opts = self.slots[base]
        
        if not opts:
            return dict(DEFAULT_FRAGMENT)
        idx = BASES.index(segment[(i + 1) % len(segment)]) % len(opts)
        return copy.deepcopy(opts[idx])

    def payload(self, segment):
        n = self.slots_per_gene
        items = [self.pick(segment, i) for i in range(n)]
        if self.renderer == "plan":
            return {"renderer": "plan", "steps": items}
        if self.renderer == "stage":
            return {"renderer": "stage", "table": items,
                    "stages": self.stages, "conditions": self.conditions}
        return {"renderer": "table", "table": items}

    
    def play(self, env, payload, cap=None, dense=False):
        ""
        cap = int(cap or (self.steps if self.renderer == "plan" else 400))
        steps = 0
        acc = 0.0
        if self.renderer == "plan":
            for item in payload["steps"]:
                if steps >= cap:
                    break
                
                if item.get("op") == "seq":
                    done = False
                    for sub in item.get("steps", []):
                        done = env.apply(sub)
                        if done:
                            break
                else:
                    done = env.apply(item)
                steps += 1
                acc += float(getattr(env, "score", 0.0))
                if done:
                    break
        elif self.renderer == "stage":
            table = payload["table"]
            stage_n = int(payload.get("stages", self.stages) or 1)
            cond = int(payload.get("conditions", self.conditions) or 1)
            while steps < cap:
                key = env.situation()
                if key is None:
                    break
                stage = 0
                if hasattr(env, "stage"):
                    stage = int(env.stage() or 0)
                idx = (stage % stage_n) * cond + (key % cond)
                item = table[idx % len(table)]
                done = env.apply(item)
                steps += 1
                acc += float(getattr(env, "score", 0.0))
                if done:
                    break
        else:
            table = payload["table"]
            while steps < cap:
                key = env.situation()
                if key is None:
                    break
                item = table[key % len(table)]
                done = env.apply(item)
                steps += 1
                acc += float(getattr(env, "score", 0.0))
                if done:
                    break
        if dense:
            return acc, steps
        return float(getattr(env, "score", 0.0)), steps


    def _fragments(self):
        frags, seen = [], set()
        for base in BASES:
            for frag in self.slots.get(base, []):
                key = json.dumps(frag, sort_keys=True, ensure_ascii=False)
                if key not in seen:
                    seen.add(key)
                    frags.append(frag)
        return frags

    def _eval_table(self, env_factory, table, cap=None, reps=1):
        total = 0.0
        for _ in range(max(1, reps)):
            env = env_factory()
            env.reset()
            score, _ = self.play(env, {"table": list(table)}, cap=cap)
            total += score
        return total / max(1, reps)

    def refine_table(self, env_factory, sweeps=4, restarts=2, cap=None,
                     budget=None, reps=1):
        ""
        return search.table_search(self, env_factory, sweeps=sweeps,
                                   restarts=restarts, cap=cap, budget=budget,
                                   reps=reps)

    def refine_plan(self, env_factory, steps=None, beam=4, cap=None, budget=None):
        ""
        return search.plan_search(self, env_factory, steps=steps, beam=beam,
                                  cap=cap, budget=budget)


# ══════════════════════════════════════════════════════════
def _score_gene(space, gene, env_factory, reps, cap, dense=False):
    ""
    total = 0.0
    for _ in range(reps):
        env = env_factory()
        env.reset()
        score, _ = space.play(env, space.payload(gene), cap=cap, dense=dense)
        total += score
    return total / max(1, reps)


def evolve(spec, env_factory, rounds=150, swarm=30, reps=2, cap=None,
           seed=None, verbose=True, callback=None, workers=1, factory_ref=None,
           factory_args=(), population=None):
    
    if population is not None:
        swarm = population
    ""
    if seed is not None:
        random.seed(seed)
    space = PayloadSpace(spec)
    max_score = float(spec.get("max_score", 1.0))
    gene_len = int(spec.get("gene_len", 60))
    seg_len = int(spec.get("segment_len", space.slots_per_gene))
    dense = bool(spec.get("dense", space.renderer == "plan"))
    score_scale = max_score * (space.steps if dense else 1.0)
    core = GedaCore({"segment_len": seg_len, "max_score": score_scale},
                    gene_len=gene_len)

    pop = ["".join(random.choice(BASES) for _ in range(gene_len))
           for _ in range(swarm)]
    best = {"score": -1e18, "gene": None, "payload": None, "gen": 0}
    history = []

    for gen in range(rounds):
        scored = []
        
        batch = None
        if workers and int(workers) > 1 and factory_ref and not dense:
            from . import parallel
            batch = [0.0] * len(pop)
            for _ in range(max(1, reps)):
                part = parallel.map_scores(factory_ref, factory_args, spec, pop,
                                           workers=int(workers))
                batch = [a + b for a, b in zip(batch, part)]
            batch = [x / max(1, reps) for x in batch]
        for i, gene in enumerate(pop):
            if batch is not None:
                raw = batch[i]
            else:
                raw = _score_gene(space, gene, env_factory, reps, cap, dense=dense)
            scored.append((raw, gene))
            utility = max(0.0, min(1.0, raw / max(1e-9, score_scale)))
            if raw > best["score"]:
                best = {"score": raw, "gene": gene, "gen": gen,
                        "payload": space.payload(gene)}
            if callback:
                callback(gen, raw, gene)
        scored.sort(key=lambda t: -t[0])

        
        top_raw, top_gene = scored[0]
        core.reward_segment(top_gene, max(0.0, min(1.0, top_raw / max(1e-9, score_scale))))
        core.record(max(0.0, min(1.0, top_raw / max(1e-9, score_scale))))

        history.append({"gen": gen, "best": top_raw,
                        "pool": len(core.memory_pool),
                        "pressure": round(core.pressure, 3),
                        "mode": core.strategy_mode})

        
        
        
        
        
        
        keep = [g for _, g in scored[:max(2, swarm // 2)]]
        
        rest = [g for _, g in scored[max(2, swarm // 2):]]
        if rest:
            keep += random.sample(rest, k=max(1, len(rest) // 4))
        new_pop = list(keep)
        stuck = core.no_improve
        while len(new_pop) < swarm:
            roll = random.random()
            if stuck >= 8 and roll < 0.35:
                child = [random.choice(BASES) for _ in range(gene_len)]      
            elif stuck >= 8 and roll < 0.70 and core.memory_pool:
                seg = core.memory_pool[0][0]                                  
                child = list(seg.ljust(gene_len, "A")[:gene_len])
                for _ in range(max(2, gene_len // 4)):
                    child[random.randrange(gene_len)] = random.choice(BASES)
            else:
                child = list(random.choice(keep))
                k = 1 if core.pressure < 0.7 else min(3, 1 + int(core.pressure * 2))
                for _ in range(k):
                    child[random.randrange(len(child))] = random.choice(BASES)
            new_pop.append("".join(child))
        pop = new_pop

        if verbose and (gen + 1) % 10 == 0:
            print("  第 %3d 代  最好 %8.2f ｜ 池 %2d ｜ 压力 %.2f %s"
                  % (gen + 1, best["score"], len(core.memory_pool),
                     core.pressure, core.strategy_mode), flush=True)

    
    if dense:
        final_gene, final_score = best["gene"], -1e18
        for gene in [scored[0][1]] + [g for _, g in scored[:5]]:
            env = env_factory()
            env.reset()
            sc, _ = space.play(env, space.payload(gene), dense=False)
            if sc > final_score:
                final_gene, final_score = gene, sc
        best = {"score": final_score, "gene": final_gene,
                "payload": space.payload(final_gene), "gen": best["gen"]}

    
    if spec.get("refine", True):
        payload, score, elapsed = core.refine(
            space, env_factory, best,
            beam=int(spec.get("beam", 12)),
            budget=float(spec.get("refine_seconds", 30)),
            reps=int(spec.get("refine_reps", 1)),
            sweeps=int(spec.get("sweeps", 4)),
            restarts=int(spec.get("restarts", 1)))
        if payload is not None and score > best["score"] + 1e-9:
            if verbose:
                print("  精修 → %.2f（%.1fs）" % (score, elapsed), flush=True)
            best = {"score": score, "gene": best["gene"],
                    "payload": payload, "gen": best["gen"]}

    return {"best": best, "history": history, "core": core, "space": space}


# ══════════════════════════════════════════════════════════
def solve(spec_path, env_factory, rounds=150, swarm=30, reps=2,
          seed=None, verbose=True, out=None):
    with open(spec_path, encoding="utf-8") as fh:
        spec = json.load(fh)
    result = evolve(spec, env_factory, rounds=rounds, swarm=swarm,
                    reps=reps, seed=seed, verbose=verbose)
    payload = result["best"]["payload"]
    
    if result["space"].renderer == "plan" and spec.get("refine", True):
        beam = int(spec.get("beam", 12))
        rplan, rscore = result["space"].refine_plan(env_factory, beam=beam)
        if rscore > result["best"]["score"] + 1e-9:
            payload = rplan
            result["best"] = {"score": rscore, "gene": result["best"]["gene"],
                              "payload": rplan, "gen": result["best"]["gen"]}
            if verbose:
                print("  精修（beam %d）→ %.2f" % (beam, rscore), flush=True)
    if out:
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(out, "w", encoding="utf-8") as fh:
            json.dump({"spec": spec, "payload": payload,
                       "score": result["best"]["score"],
                       "gen": result["best"]["gen"]}, fh,
                      ensure_ascii=False, indent=2)
    return result
