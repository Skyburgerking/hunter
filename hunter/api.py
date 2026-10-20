# -*- coding: utf-8 -*-
""

import json
import random

from hunter.core import BASES, GedaCore
from hunter.policy import FeaturePolicy


class HunterEngine:
    def __init__(self, spec, seed=None, memory_path=None):
        if seed is not None:
            random.seed(seed)
        self.spec = dict(spec)
        self.name = spec.get("name", "task")
        self.max_score = float(spec.get("max_score", 1.0))
        self.core = GedaCore(spec, gene_len=int(spec.get("gene_len", 80)))

        self.param = {}
        for base in BASES:
            for item in spec.get("actions", {}).get(base, []):
                self.param[item["name"]] = dict(item)

        self.mode = spec.get("mode", "action")
        self.param_spec = spec.get("params", {})
        self.policy = FeaturePolicy(spec) if self.mode == "feature" else None
        self.memory_path = memory_path or spec.get("memory_path")
        self.segment = ""
        self.step_index = 0
        self.episode_reward = 0.0
        self.episode_count = 0
        self.history = []
        self.best = None
        if self.memory_path:
            self.core.load(self.memory_path)

    
    def begin_episode(self):
        self.segment = self.core.get_gene_segment()
        self.step_index = 0
        self.episode_reward = 0.0
        return self.segment

    def tick(self, obs=None):
        if not self.segment:
            self.begin_episode()
        self.step_index += 1
        if self.mode == "param":
            return {
                "task": self.name,
                "params": self.decode_params(),
                "segment": self.segment,
                "step": self.step_index,
                "pressure": round(self.core.pressure, 3),
                "mode": self.core.strategy_mode,
                "memory": len(self.core.memory_pool),
            }
        base = self.segment[(self.step_index - 1) % len(self.segment)]
        names = self.core.base_mapping.get(base, ["noop"])
        action = random.choice(names)
        return {
            "task": self.name,
            "action": action,
            "param": {k: v for k, v in self.param.get(action, {}).items() if k != "name"},
            "segment": self.segment,
            "step": self.step_index,
            "pressure": round(self.core.pressure, 3),
            "mode": self.core.strategy_mode,
            "memory": len(self.core.memory_pool),
        }

    def act(self, env):
        ""
        if self.policy is None:
            raise RuntimeError("act(env) 需要 mode=feature")
        weights = self.policy.weights(self.segment)
        return self.policy.choose(env, weights)

    def decode_params(self):
        out = {}
        for name, item in self.param_spec.items():
            idx = int(item.get("base", 0)) % max(1, len(self.segment))
            base = self.segment[idx]
            values = item.get("values", [0, 1])
            out[name] = values[BASES.index(base) % len(values)]
        return out

    
    def feedback(self, reward, done=False):
        self.episode_reward += float(reward)
        if done:
            return self.end_episode()
        return None

    def end_episode(self, success=None):
        raw = self.episode_reward if success is None else float(success)
        score = max(0.0, min(1.0, raw / max(1e-9, self.max_score)))
        self.core.record(score)                 
        self.core.reward_segment(self.segment, score)   
        self.episode_count += 1
        self.history.append({"segment": self.segment, "score": score,
                             "raw": raw, "steps": self.step_index})
        if self.best is None or score > self.best["score"]:
            self.best = {"segment": self.segment, "score": score, "raw": raw}
        if self.memory_path:
            self.core.save(self.memory_path)
        self.segment = ""
        return score

    
    def state(self):
        data = self.core.snapshot()
        data.update({"task": self.name, "episodes": self.episode_count,
                     "best": self.best, "gene_len": self.core.gene_len})
        return data


def load_spec(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def run_task(spec, env_factory, episodes=200, seed=None, verbose=False):
    engine = HunterEngine(spec, seed=seed)
    env = env_factory()
    scores = []
    for i in range(episodes):
        obs = env.reset()
        engine.begin_episode()
        done = False
        while not done:
            out = engine.tick(obs)
            if spec.get("mode") == "param":
                action = env.act(out["params"], obs)
            else:
                action = out["action"]
            obs, reward, done, _ = env.step(action)
            engine.feedback(reward, done)
        scores.append(engine.history[-1]["raw"])
        if verbose and (i + 1) % 20 == 0:
            st = engine.state()
            print("  %s %3d 分 %.3f  压力 %.2f  %s  记忆 %d  地形 %.2f"
                  % (spec.get("name", "task"), i + 1, scores[-1],
                     st["pressure"], st["mode"], st["memory"], st["terrain"]))
    return engine, scores
