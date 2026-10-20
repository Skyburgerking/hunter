# -*- coding: utf-8 -*-
""
import itertools
import json
import random


def _run(env_factory, seq, repeats, stop_score=None):
    ""
    env = env_factory()
    env.reset()
    for _ in range(repeats):
        for a in seq:
            if env.apply(a):
                return float(getattr(env, "score", 0.0))
        if env.situation() is None:
            break
    return float(getattr(env, "score", 0.0))


def discover(env_factory, atoms, depth=3, samples=12, top=6, seed=0,
             verbose=False, passes=2):
    ""
    atoms = list(atoms)
    if not atoms:
        return []
    rng = random.Random(seed)
    def _state_after(pre):
        env = env_factory()
        env.reset()
        for a in pre:
            if env.apply(a):
                break
        return float(getattr(env, "score", 0.0))

    
    prefixes = []
    for a in atoms:
        for k in range(1, 5):
            pre = [a] * k
            prefixes.append((pre, _state_after(pre)))
    for _ in range(max(1, int(samples))):
        env = env_factory()
        env.reset()
        pre = []
        for _ in range(rng.randrange(0, 8)):
            if env.situation() is None:
                break
            a = rng.choice(atoms)
            pre.append(a)
            env.apply(a)
        prefixes.append((pre, float(getattr(env, "score", 0.0))))

    out = []
    for _pass in range(max(1, int(passes))):
        scored = []
        for combo in itertools.product(range(len(atoms)), repeat=int(depth)):
            seq = [atoms[i] for i in combo]
            if len(seq) <= 1:
                continue
            gains = []
            for pre, base in prefixes:
                env = env_factory()
                env.reset()
                for a in pre + seq:
                    if env.apply(a):
                        break
                gains.append(float(getattr(env, "score", 0.0)) - base)
            
            top_gain = max(gains) if gains else 0.0
            mean_gain = sum(gains) / max(1, len(gains))
            scored.append((top_gain + 0.01 * mean_gain, seq))
        scored.sort(key=lambda t: -t[0])

        found = [seq for gain, seq in scored[:int(top)] if gain > 1e-6]
        for seq in found:
            if seq not in [p["steps"] for p in out]:
                out.append({"op": "seq", "steps": seq})
        if verbose:
            print(" 第 %d 轮：" % (_pass + 1))
            for gain, seq in scored[:int(top)]:
                print("   +%.3f  %s" % (gain, [a.get("dir") or a.get("op") for a in seq]))
        
        vocab = list(atoms) + [{"op": "seq", "steps": q} for q in found]
        prefixes = []
        for _ in range(max(1, int(samples))):
            env = env_factory()
            env.reset()
            pre = []
            for _ in range(rng.randrange(0, 5)):
                if env.situation() is None:
                    break
                a = rng.choice(vocab)
                if a.get("op") == "seq":
                    for sub in a["steps"]:
                        pre.append(sub)
                        if env.apply(sub):
                            break
                else:
                    pre.append(a)
                    env.apply(a)
            prefixes.append((pre, float(getattr(env, "score", 0.0))))
    return out
