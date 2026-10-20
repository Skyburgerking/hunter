# -*- coding: utf-8 -*-
""

import json
import os
import random

BASES = ["A", "G", "C", "T", "X"]
COMPLEMENT = {"A": "T", "T": "A", "G": "C", "C": "G", "X": "X"}


def _clamp(x, lo, hi):
    return max(lo, min(hi, x))


class GedaCore:
    def __init__(self, setting=None, gene_len=80, memory_capacity=40,
                 hot_capacity=8):
        self.gene_len = gene_len
        self.gene_primary = "".join(random.choice(BASES) for _ in range(gene_len))
        self.gene_complementary = "".join(COMPLEMENT[b] for b in self.gene_primary)
        self.doubt_chain = "".join(
            random.choice(BASES) for _ in range(max(1, gene_len // 3)))
        self.memory_pool = []          # [(segment, utility)]
        self.hot_genes = []            
        self.memory_capacity = memory_capacity
        self.hot_capacity = hot_capacity
        self.pressure = 0.5
        self.streak = 0
        self.no_improve = 0
        self.step_size = 1.0
        self.best_utility = 0.0
        self.strategy_mode = "balanced"
        self.configure(setting or {})

    
    def configure(self, setting):
        self.setting = dict(setting or {})
        self.mode = self.setting.get("mode", "action")
        self.segment_len = int(self.setting.get("segment_len", 8))
        self.max_score = float(self.setting.get("max_score", 1.0))
        self.param_spec = self.setting.get("params", {})
        mapping = {}
        for base in BASES:
            names = [a["name"] for a in self.setting.get("actions", {}).get(base, [])]
            mapping[base] = names or ["noop"]
        self.base_mapping = mapping
        return self

    
    def _get_active_strand(self):
        ""
        if self.strategy_mode == "exploitative" and self.hot_genes:
            return self.hot_genes[0][0], True
        if self.pressure < 0.3:
            return self.gene_complementary, False
        if self.pressure > 0.7:
            return self.gene_primary, False
        strand = self.gene_primary if random.random() < 0.5 else self.gene_complementary
        return strand, False

    def get_gene_segment(self, n=None):
        n = n or self.segment_len
        strand, aligned = self._get_active_strand()
        if aligned:
            start = 0
        else:
            start = random.randrange(max(1, len(strand) - n))
        seg = list(strand[start:start + n].ljust(n, random.choice(BASES)))
        if aligned:
            return "".join(seg)      
        
        if random.random() < 0.10 + self.pressure * 0.20:
            i = random.randrange(n)
            if random.random() < 0.5:
                seg[i] = self.doubt_chain[i % len(self.doubt_chain)]
            else:
                seg[i] = random.choice(BASES)
        
        if self.no_improve >= 5 and random.random() < 0.5:
            seg[random.randrange(n)] = random.choice(BASES)
        return "".join(seg)

    
    def record(self, fitness):
        ""
        fitness = _clamp(float(fitness), 0.0, 1.0)
        self.pressure = _clamp(self.pressure * 0.85 + (1 - fitness) * 0.25, 0.05, 1.0)
        if fitness > 0.6:
            self.streak += 1
        else:
            self.streak = 0
        self._update_mode()
        return self.pressure

    def _update_mode(self):
        if self.streak > 5 and self.no_improve < 5:
            self.strategy_mode = "exploitative"
        elif self.pressure > 0.6 or self.no_improve >= 5:
            self.strategy_mode = "exploratory"
        else:
            self.strategy_mode = "balanced"

    def reward_segment(self, segment, utility):
        ""
        seg = segment[:self.segment_len]
        utility = _clamp(float(utility), 0.0, 1.0)
        
        if utility > self.best_utility + 1e-9:
            self.best_utility = utility
            self.no_improve = 0
            self.step_size = min(2.0, self.step_size * 1.05)
        else:
            self.no_improve += 1
            if self.no_improve >= 5:
                self.step_size = max(0.2, self.step_size * 0.95)
        for i, (old, u) in enumerate(self.memory_pool):
            if old == seg:
                self.memory_pool[i] = (seg, max(u, utility))
                break
        else:
            self.memory_pool.append((seg, utility))
        self.memory_pool.sort(key=lambda x: -x[1])
        self.memory_pool = self.memory_pool[:self.memory_capacity]
        self.hot_genes = [row for row in self.memory_pool[:self.hot_capacity]]
        self._update_mode()
        return self.memory_pool

    
    def terrain_coef(self):
        ""
        if len(self.memory_pool) < 2:
            return 1.0
        segs = [s for s, _ in self.memory_pool[:10]]
        total, pairs = 0, 0
        for i in range(len(segs)):
            for j in range(i + 1, len(segs)):
                total += sum(1 for a, b in zip(segs[i], segs[j]) if a != b)
                pairs += 1
        return total / max(1, pairs * len(segs[0]))

    
    def refine(self, space, env_factory, best=None, **kw):
        ""
        from . import search
        return search.refine(space, env_factory, best, **kw)

    def snapshot(self):
        return {
            "pressure": round(self.pressure, 3),
            "mode": self.strategy_mode,
            "streak": self.streak,
            "no_improve": self.no_improve,
            "step_size": round(self.step_size, 3),
            "memory": len(self.memory_pool),
            "hot": len(self.hot_genes),
            "terrain": round(self.terrain_coef(), 3),
            "best": round(self.best_utility, 3),
        }

    
    def save(self, path):
        folder = os.path.dirname(path)
        if folder:
            os.makedirs(folder, exist_ok=True)
        data = {
            "pool": [{"segment": s, "score": u} for s, u in self.memory_pool],
            "pressure": self.pressure,
            "best": self.best_utility,
        }
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)

    def load(self, path):
        if not path or not os.path.exists(path):
            return False
        try:
            with open(path, encoding="utf-8") as handle:
                data = json.load(handle)
            self.memory_pool = [(r["segment"], float(r["score"]))
                                for r in data.get("pool", [])][:self.memory_capacity]
            self.hot_genes = self.memory_pool[:self.hot_capacity]
            self.pressure = float(data.get("pressure", self.pressure))
            self.best_utility = float(data.get("best", 0.0))
            return True
        except Exception:
            return False
