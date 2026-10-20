# -*- coding: utf-8 -*-
""
import io
import json
import os

from .base import ArcadeEnv, frags

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _seed(name):
    p = os.path.join(ROOT, "out", "payload", name + ".json")
    if not os.path.exists(p):
        return None
    with io.open(p, encoding="utf-8") as fh:
        return json.load(fh)["payload"]


# ══════════════════════════════════════════════════════════
class SokobanExt(ArcadeEnv):
    ""

    NAME = "sokoban_ext"
    FULL = 2.0
    RENDERER = "table"
    CONDITIONS = 3

    def __init__(self):
        ArcadeEnv.__init__(self)
        from benches.thirdparty.sokoban_env import SokobanEnv
        self.SEED_PAYLOAD = _seed("sokoban_table")
        self.inner_cls = SokobanEnv
        self.SLOTS = frags({"op": "push", "box": "near", "dir": "u"},
                           {"op": "push", "box": "near", "dir": "d"},
                           {"op": "push", "box": "near", "dir": "l"},
                           {"op": "push", "box": "near", "dir": "r"},
                           {"op": "wait"})

    def reset(self):
        self.inner = self.inner_cls(level="test2", cap=12)
        self.inner.reset()
        self.score = 0.0
        self.done = False
        return self

    def apply(self, step_json):
        done = self.inner.apply(step_json)
        self.score = float(self.inner.score)
        self.done = done
        return done

    def situation(self):
        return None if self.done else int(self.inner.situation() or 0) % self.CONDITIONS


# ══════════════════════════════════════════════════════════
class Sokoban5Ext(SokobanExt):
    ""

    NAME = "sokoban5_ext"
    FULL = 3.0
    RENDERER = "plan"
    STEPS = 10
    BEAM = 12

    def __init__(self):
        ArcadeEnv.__init__(self)
        from benches.thirdparty.sokoban_env import SokobanEnv
        self.SEED_PAYLOAD = _seed("sokoban5_plan")
        self.inner_cls = SokobanEnv
        self.SLOTS = frags(*[{"op": "push", "box": "near", "dir": d}
                             for d in ("u", "d", "l", "r")] + [{"op": "wait"}])

    def reset(self):
        self.inner = self.inner_cls(level="test5", cap=24)
        self.inner.reset()
        self.score = 0.0
        self.done = False
        return self

    def situation(self):
        return None if self.done else 0


# ══════════════════════════════════════════════════════════
class PacmanExt(ArcadeEnv):
    ""

    NAME = "pacman_ext"
    FULL = 97.0
    RENDERER = "table"
    CONDITIONS = 3

    def __init__(self):
        ArcadeEnv.__init__(self)
        from benches.thirdparty.pacman_env import PacmanEnv
        self.SEED_PAYLOAD = _seed("pacman_table")
        self.inner_cls = PacmanEnv
        self.SLOTS = frags({"op": "goto", "target": "food", "avoid": 2},
                           {"op": "goto", "target": "food", "avoid": 1},
                           {"op": "goto", "target": "food"},
                           {"op": "flee"})

    def reset(self):
        self.inner = self.inner_cls(cap=600)
        self.inner.reset()
        self.score = 0.0
        self.done = False
        return self

    def _left(self):
        try:
            return len(self.inner.state.getFood().asList())
        except Exception:                      # noqa: BLE001
            return 0

    def apply(self, step_json):
        done = self.inner.apply(step_json)
        self.score = float(97 - self._left())
        self.done = done
        if self.score >= 97:
            self.done = True
        return self.done

    def situation(self):
        return None if self.done else int(self.inner.situation() or 0) % self.CONDITIONS


# ══════════════════════════════════════════════════════════
class PvzExt(ArcadeEnv):
    ""

    NAME = "pvz_ext"
    FULL = 330.0
    RENDERER = "table"
    CONDITIONS = 10

    def __init__(self):
        ArcadeEnv.__init__(self)
        from benches.thirdparty.pvz_env import PvZEnv
        self.SEED_PAYLOAD = _seed("pvz_table")
        self.inner_cls = PvZEnv
        self.SLOTS = frags({"op": "plant", "card": 0, "lane": "front"},
                           {"op": "plant", "card": 1, "lane": "front"},
                           {"op": "plant", "card": 2, "lane": "front"},
                           {"op": "wait"})

    def reset(self):
        self.inner = self.inner_cls(level_num=1, cards=[0, 1, 3],
                                    frames_per_step=40, cap=260)
        self.inner.reset()
        self.score = 0.0
        self.done = False
        return self

    def apply(self, step_json):
        done = self.inner.apply(step_json)
        self.score = float(self.inner.score)
        self.done = done
        return done

    def situation(self):
        return None if self.done else int(self.inner.situation() or 0) % self.CONDITIONS


# ══════════════════════════════════════════════════════════
class RtsExt(ArcadeEnv):
    ""

    NAME = "rts_ext"
    FULL = 1.0
    RENDERER = "plan"
    STEPS = 80
    BEAM = 6

    def __init__(self):
        ArcadeEnv.__init__(self)
        from benches.thirdparty.rts_env import RTSEnv, STANCES
        self.SEED_PAYLOAD = _seed("rts_plan")
        self.inner_cls = RTSEnv
        self.SLOTS = frags(*[{"op": "stance", "value": s} for s in list(STANCES)])

    def reset(self):
        self.inner = self.inner_cls(cap=80)
        self.inner.reset()
        self.score = 0.0
        self.done = False
        return self

    def apply(self, step_json):
        done = self.inner.apply(step_json)
        
        enemy = self.inner._hp(self.inner.units, 1)
        if enemy <= 0:
            self.score = 1.0
        else:
            self.score = min(0.99, self.inner.damage_dealt / 400.0)
        self.done = bool(done or enemy <= 0)
        return self.done

    def situation(self):
        return None if self.done else 0
