# -*- coding: utf-8 -*-
""


class ArcadeEnv(object):
    NAME = "arcade"
    FULL = 1.0            
    RENDERER = "plan"     
    STEPS = 8             
    CONDITIONS = 1        
    BEAM = 12             
    SLOTS = {}            

    def __init__(self):
        self.score = 0.0
        self.done = False
        self.steps = 0

    
    def reset(self):
        raise NotImplementedError

    def apply(self, step_json):
        raise NotImplementedError

    def situation(self):
        return 0

    
    def observe(self):
        ""
        k = self.situation()
        return (0.0 if k is None else float(k),)

    def actions(self):
        ""
        out = []
        for base in ("A", "G", "C", "T"):
            for frag in (self.SLOTS or {}).get(base, []):
                out.append(frag)
        return out

    # ---------- spec ----------
    def spec(self):
        return {
            "name": self.NAME,
            "renderer": self.RENDERER,
            "steps": self.STEPS,
            "conditions": self.CONDITIONS,
            "gene_len": 48,
            "segment_len": 16,
            "max_score": float(self.FULL),
            "rounds": 24,
            "swarm": 16,
            "reps": 1,
            "beam": self.BEAM,
            "refine_seconds": 30,
            "slots": self.SLOTS,
        }


def frags(*items):
    ""
    keys = ("A", "G", "C", "T")
    out = {k: [] for k in ("A", "G", "C", "T", "X")}
    for i, item in enumerate(items):
        out[keys[i % 4]].append(item)
    out["X"] = [{"op": "wait"}]
    for k in keys:                 
        if not out[k]:
            out[k] = list(items) or [{"op": "wait"}]
    return out
