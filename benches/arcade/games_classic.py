# -*- coding: utf-8 -*-
""
from .base import ArcadeEnv, frags
from .games_arcade import Cartpole


# ══════════════════════════════════════════════════════════
class TetrisArcade(ArcadeEnv):
    ""

    NAME = "tetris_arcade"
    FULL = 3.0
    RENDERER = "plan"
    STEPS = 6
    BEAM = 500
    PIECES = [((0, 0), (1, 0), (2, 0), (3, 0)),
              ((0, 0), (1, 0), (2, 0), (3, 0)),
              ((0, 0), (1, 0), (0, 1), (1, 1)),
              ((0, 0), (1, 0), (0, 1), (1, 1)),
              ((0, 0), (1, 0), (0, 1), (1, 1)),
              ((0, 0), (1, 0), (0, 1), (1, 1))]

    def __init__(self):
        ArcadeEnv.__init__(self)
        self.SLOTS = frags(*[{"op": "place", "x": c} for c in range(7)])

    def reset(self):
        self.grid = [[0] * 8 for _ in range(20)]
        self.k = 0
        self.lines = 0
        self.score = 0.0
        self.done = False
        self.steps = 0
        return self

    def apply(self, step_json):
        if self.done:
            return True
        if step_json.get("op") != "place" or self.k >= len(self.PIECES):
            return False
        x = int(step_json.get("x", 0))
        if not (0 <= x < 8):
            return False
        piece = self.PIECES[self.k]
        w = max(c for c, _ in piece)
        if x + w >= 8:
            return False
        
        y = 0
        while True:
            ny = y + 1
            ok = True
            for dx, dy in piece:
                py, px = ny + dy, x + dx
                if py >= 20 or (py >= 0 and self.grid[py][px]):
                    ok = False
                    break
            if not ok:
                break
            y = ny
        for dx, dy in piece:
            self.grid[y + dy][x + dx] = 1
        self.k += 1
        self.steps += 1
        full = [r for r in range(20) if all(self.grid[r])]
        for r in full:
            del self.grid[r]
            self.grid.insert(0, [0] * 8)
        self.lines += len(full)
        
        fill = max(sum(1 for v in row if v) for row in self.grid) / 8.0
        self.score = float(self.lines) + (0.0 if self.lines >= 3 else 0.09 * fill)
        if self.lines >= 3 or self.k >= len(self.PIECES):
            self.done = True
        return self.done

    def situation(self):
        return None if self.done else 0


# ══════════════════════════════════════════════════════════
class Game2048(ArcadeEnv):
    ""

    NAME = "game2048"
    FULL = 256.0
    RENDERER = "table"
    CONDITIONS = 16
    SLOTS = frags({"op": "m", "d": "u"}, {"op": "m", "d": "d"},
                  {"op": "m", "d": "l"}, {"op": "m", "d": "r"})
    SEED = 12345

    def reset(self):
        self.g = [0] * 16
        self.rng = self.SEED
        self.score = 0.0
        self.done = False
        self.steps = 0
        self._spawn()
        return self

    def _spawn(self):
        empty = [j for j in range(16) if self.g[j] == 0]
        if not empty:
            self.done = True
            return
        self.rng = (self.rng * 1103515245 + 12345) % (2 ** 31)
        cell = empty[self.rng % len(empty)]
        self.g[cell] = 2 if (self.rng >> 9) % 10 else 4

    def _line(self, cells, dry=False):
        vals = [self.g[c] for c in cells if self.g[c]]
        out = []
        for v in vals:
            if out and out[-1] == v:
                out[-1] = v * 2
            else:
                out.append(v)
        out += [0] * (4 - len(out))
        changed = any(self.g[c] != v for c, v in zip(cells, out))
        if not dry:
            for c, v in zip(cells, out):
                self.g[c] = v
        return changed

    def _move(self, d, dry=False):
        ""
        rows = [[r * 4 + c for c in range(4)] for r in range(4)]
        cols = [[r * 4 + c for r in range(4)] for c in range(4)]
        if d == "l":
            lines = rows
        elif d == "r":
            lines = [list(reversed(r)) for r in rows]
        elif d == "u":
            lines = cols
        elif d == "d":
            lines = [list(reversed(c)) for c in cols]
        else:
            return False
        changed = False
        for cells in lines:
            changed |= self._line(cells, dry=dry)
        return changed

    def _can(self, d):
        save = list(self.g)
        ok = self._move(d, dry=True)
        self.g = save
        return ok

    def apply(self, step_json):
        if self.done:
            return True
        if step_json.get("op") != "m":
            return False
        d = str(step_json.get("d", "l"))
        if not self._move(d):
            return False
        self.steps += 1
        self._spawn()
        self.score = float(max(self.g))
        if self.score >= 256 or self.steps >= 300:
            self.done = True
        return self.done

    def situation(self):
        if self.done:
            return None
        
        key = 0
        if self._can("l"):
            key |= 1
        if self._can("u"):
            key |= 2
        if self._can("r"):
            key |= 4
        if self._can("d"):
            key |= 8
        return key


# ══════════════════════════════════════════════════════════
class Drone(ArcadeEnv):
    ""

    NAME = "drone"
    FULL = 1.0
    RENDERER = "table"
    CONDITIONS = 5
    SLOTS = frags({"op": "climb"}, {"op": "dive"}, {"op": "hold"})

    def reset(self):
        self.y, self.ty = 3, 12
        self.tv = -1
        self.score = 0.0
        self.done = False
        self.steps = 0
        return self

    def apply(self, step_json):
        if self.done:
            return True
        op = step_json.get("op")
        if op == "climb":
            self.y -= 1
        elif op == "dive":
            self.y += 1
        elif op != "hold":
            return False
        self.ty += self.tv
        if self.ty <= 1 or self.ty >= 19:
            self.tv = -self.tv
            self.ty += 2 * self.tv
        self.steps += 1
        self.score = 1.0 if self.y == self.ty else 0.0
        if self.y == self.ty:
            self.done = True
        if self.steps >= 40:
            self.done = True
        return self.done

    def situation(self):
        if self.done:
            return None
        d = self.ty - self.y
        if d <= -3:
            return 0
        if d < 0:
            return 1
        if d == 0:
            return 2
        if d <= 3:
            return 3
        return 4


# ══════════════════════════════════════════════════════════
class GridHunt(ArcadeEnv):
    ""

    NAME = "grid_hunt"
    FULL = 1.0
    RENDERER = "table"
    CONDITIONS = 4
    SLOTS = frags({"op": "go", "dir": "u"}, {"op": "go", "dir": "d"},
                  {"op": "go", "dir": "l"}, {"op": "go", "dir": "r"})
    TREASURE = (4, 4)

    def reset(self):
        self.p = (0, 0)
        self.score = 0.0
        self.done = False
        self.steps = 0
        return self

    def apply(self, step_json):
        if self.done:
            return True
        if step_json.get("op") != "go":
            return False
        d = {"u": (0, -1), "d": (0, 1), "l": (-1, 0), "r": (1, 0)}.get(
            str(step_json.get("dir", "r")))
        if d is None:
            return False
        nxt = (self.p[0] + d[0], self.p[1] + d[1])
        if not (0 <= nxt[0] < 5 and 0 <= nxt[1] < 5):
            return False
        self.p = nxt
        self.steps += 1
        dist = abs(self.p[0] - self.TREASURE[0]) + abs(self.p[1] - self.TREASURE[1])
        self.score = 1.0 if dist == 0 else 0.9 * (1.0 - dist / 8.0)
        if dist == 0:
            self.done = True
        if self.steps >= 40:
            self.done = True
        return self.done

    def situation(self):
        if self.done:
            return None
        dx = self.TREASURE[0] - self.p[0]
        dy = self.TREASURE[1] - self.p[1]
        if abs(dx) >= abs(dy):
            return 0 if dx > 0 else 1
        return 2 if dy > 0 else 3


# ══════════════════════════════════════════════════════════
class Guess(ArcadeEnv):
    ""

    NAME = "guess"
    FULL = 1.0
    RENDERER = "plan"
    STEPS = 7
    BEAM = 20
    TARGET = 73
    SLOTS = frags(*[{"op": "guess", "v": v} for v in (25, 50, 62, 68, 71, 74, 73)])

    def reset(self):
        self.score = 0.0
        self.done = False
        self.steps = 0
        return self

    def apply(self, step_json):
        if self.done:
            return True
        if step_json.get("op") != "guess":
            return False
        v = int(step_json.get("v", 0))
        self.steps += 1
        if v == self.TARGET:
            self.score = 1.0
            self.done = True
            return True
        
        self.score = max(0.0, 0.9 * (1.0 - abs(v - self.TARGET) / 100.0))
        if self.steps >= 7:
            self.done = True
        return self.done

    def situation(self):
        return None if self.done else 0


# ══════════════════════════════════════════════════════════
class JobShop(ArcadeEnv):
    ""

    NAME = "jobshop"
    FULL = 1.0
    RENDERER = "plan"
    STEPS = 5
    BEAM = 20
    JOBS = [7, 6, 5, 4, 3]
    TARGET = 20

    def __init__(self):
        ArcadeEnv.__init__(self)
        self.SLOTS = frags(*[{"op": "assign", "m": m} for m in range(3)])

    def reset(self):
        self.load = [0, 0, 0]
        self.i = 0
        self.score = 0.0
        self.done = False
        self.steps = 0
        return self

    def apply(self, step_json):
        if self.done:
            return True
        if step_json.get("op") != "assign":
            return False
        m = int(step_json.get("m", 0))
        if not (0 <= m < 3) or self.i >= len(self.JOBS):
            return False
        self.load[m] += self.JOBS[self.i]
        self.i += 1
        self.steps += 1
        if self.i >= len(self.JOBS):
            mk = max(self.load)
            self.score = 1.0 if mk <= self.TARGET else max(0.0, 0.9 * self.TARGET / mk)
            self.done = True
        return self.done

    def situation(self):
        return None if self.done else 0


# ══════════════════════════════════════════════════════════
class Corridor(ArcadeEnv):
    ""

    NAME = "corridor"
    FULL = 1.0
    RENDERER = "stage"
    STAGES = 3
    CONDITIONS = 1

    def __init__(self):
        ArcadeEnv.__init__(self)
        self.SLOTS = frags({"op": "go", "dir": "u"}, {"op": "go", "dir": "d"},
                           {"op": "go", "dir": "l"}, {"op": "go", "dir": "r"})

    def spec(self):
        d = ArcadeEnv.spec(self)
        d["stages"] = self.STAGES
        d["refine_seconds"] = 20
        return d

    def reset(self):
        self.x, self.y = 0, 0
        self.score = 0.0
        self.done = False
        self.steps = 0
        return self

    def _want(self, stage):
        return {0: "r", 1: "d", 2: "r"}[stage]

    def stage(self):
        if self.steps < 10:
            return 0
        if self.steps < 20:
            return 1
        return 2

    def apply(self, step_json):
        if self.done:
            return True
        if step_json.get("op") != "go":
            return False
        d = str(step_json.get("dir", ""))
        if d != self._want(self.stage()):
            self.done = True                 
            return True
        if d == "r":
            self.x += 1
        elif d == "d":
            self.y += 1
        self.steps += 1
        self.score = min(1.0, self.steps / 30.0)
        if self.steps >= 30:
            self.score = 1.0
            self.done = True
        return self.done

    def situation(self):
        return None if self.done else 0


# ══════════════════════════════════════════════════════════
class CartpoleAuto(Cartpole):
    ""

    NAME = "cartpole_auto"
    CONDITIONS = 25

    def __init__(self):
        Cartpole.__init__(self)
        self._binner = None

    def observe(self):
        return (self.theta, self.omega)

    def _keyer(self):
        if self._binner is None:
            from hunter import sense
            
            self._binner = sense.Binner.fit([], bins=5,
                                            bounds=Cartpole().bounds())
        return self._binner

    def situation(self):
        if self.done:
            return None
        return self._keyer().key(self.observe())
