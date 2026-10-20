# -*- coding: utf-8 -*-
""
from .base import ArcadeEnv, frags


# ══════════════════════════════════════════════════════════
class Minesweeper(ArcadeEnv):
    ""

    NAME = "minesweeper"
    FULL = 13.0
    RENDERER = "plan"
    STEPS = 13
    BEAM = 20
    MINES = {5, 10, 15}
    SLOTS = frags(*[{"op": "reveal", "cell": i} for i in range(16)])

    def reset(self):
        self.open = set()
        self.score = 0.0
        self.done = False
        self.steps = 0
        return self

    def apply(self, step_json):
        if self.done:
            return True
        if step_json.get("op") != "reveal":
            return False
        cell = int(step_json.get("cell", 0))
        if not (0 <= cell < 16) or cell in self.open:
            return False
        if cell in self.MINES:
            self.done = True                    
            return True
        self.open.add(cell)
        self.steps += 1
        self.score = float(len(self.open))
        if len(self.open) >= 13:
            self.done = True
        return self.done

    def situation(self):
        return None if self.done else 0


# ══════════════════════════════════════════════════════════
class Maze(ArcadeEnv):
    ""

    NAME = "maze"
    FULL = 3.0
    RENDERER = "plan"
    STEPS = 18
    BEAM = 200
    SLOTS = frags(*[{"op": "go", "dir": d} for d in ("u", "d", "l", "r")])
    COINS = {(3, 0), (7, 3)}
    EXIT = (7, 7)
    WALLS = {(2, 2), (3, 2), (4, 2), (5, 2), (6, 2),
             (1, 5), (2, 5), (3, 5), (4, 5)}

    def reset(self):
        self.pos = (0, 0)
        self.got = set()
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
        nxt = (self.pos[0] + d[0], self.pos[1] + d[1])
        self.steps += 1
        if not (0 <= nxt[0] < 8 and 0 <= nxt[1] < 8) or nxt in self.WALLS:
            return False
        self.pos = nxt
        if nxt in self.COINS:
            self.got.add(nxt)
        
        if self.pos == self.EXIT:
            self.score = float(len(self.got)) + 1.0
            self.done = True
        else:
            left = sorted(self.COINS - self.got)
            tgt = left[0] if left else self.EXIT
            d = abs(self.pos[0] - tgt[0]) + abs(self.pos[1] - tgt[1])
            self.score = float(len(self.got)) + 0.09 * (1.0 - min(d, 16) / 16.0)
        if self.steps >= 60:
            self.done = True
        return self.done

    def situation(self):
        return None if self.done else 0


# ══════════════════════════════════════════════════════════
class TowerDefense(ArcadeEnv):
    ""

    NAME = "tower_defense"
    FULL = 3.0
    RENDERER = "table"
    CONDITIONS = 3
    SLOTS = frags({"op": "build", "lane": 0}, {"op": "build", "lane": 1},
                  {"op": "build", "lane": 2}, {"op": "wait"})

    def reset(self):
        self.towers = set()
        self.wave = 0
        self.t = 0
        self.score = 0.0
        self.done = False
        self.steps = 0
        return self

    def apply(self, step_json):
        if self.done:
            return True
        op = step_json.get("op")
        if op == "build":
            lane = int(step_json.get("lane", 0))
            if not (0 <= lane < 3):
                return False
            self.towers.add(lane)        
        elif op != "wait":
            return False
        self.steps += 1
        self.t += 1
        if self.t % 4 == 0:                 
            lane = self.wave % 3
            if lane not in self.towers:
                self.done = True
                return True
            self.wave += 1
            self.score = float(self.wave)
            if self.wave >= 3:
                self.done = True
                return True
        if self.steps >= 40:
            self.done = True
        return self.done

    def situation(self):
        return None if self.done else min(2, self.wave)


# ══════════════════════════════════════════════════════════
class Platformer(ArcadeEnv):
    ""

    NAME = "platformer"
    FULL = 1.0
    RENDERER = "table"
    CONDITIONS = 4
    SLOTS = frags({"op": "run"}, {"op": "jump"})
    GAPS = (6, 12, 18, 24)
    GOAL = 30

    def reset(self):
        self.x = 0
        self.air = 0
        self.score = 0.0
        self.done = False
        self.steps = 0
        return self

    def apply(self, step_json):
        if self.done:
            return True
        op = step_json.get("op")
        if op == "run":
            self.x += 1
        elif op == "jump":
            self.air = 2
            self.x += 2
        else:
            return False
        if self.air > 0:
            self.air -= 1
            self.x += 1
        self.steps += 1
        if self.x in self.GAPS and self.air == 0:
            self.done = True                      
            return True
        self.score = min(1.0, self.x / float(self.GOAL))
        if self.x >= self.GOAL:
            self.score = 1.0
            self.done = True
        if self.steps >= 100:
            self.done = True
        return self.done

    def situation(self):
        if self.done:
            return None
        nxt = min([g for g in self.GAPS if g >= self.x] or [self.GOAL])
        d = nxt - self.x
        return 0 if d > 4 else (1 if d > 2 else (2 if d > 0 else 3))


# ══════════════════════════════════════════════════════════
class Match3(ArcadeEnv):
    ""

    NAME = "match3"
    FULL = 6.0
    RENDERER = "plan"
    STEPS = 6
    BEAM = 40

    BOARD = [1, 1, 1, 2,
             3, 4, 1, 2,
             3, 2, 2, 2,
             3, 4, 4, 4]

    def __init__(self):
        ArcadeEnv.__init__(self)
        pairs = []
        for r in range(4):
            for c in range(4):
                if c < 3:
                    pairs.append({"op": "swap", "a": r * 4 + c, "b": r * 4 + c + 1})
                if r < 3:
                    pairs.append({"op": "swap", "a": r * 4 + c, "b": (r + 1) * 4 + c})
        self.SLOTS = frags(*pairs)

    def reset(self):
        self.g = list(self.BOARD)
        self.score = 0.0
        self.done = False
        self.steps = 0
        return self

    def _matches(self):
        hit = set()
        for r in range(4):
            run = 1
            for c in range(1, 4):
                if self.g[r * 4 + c] == self.g[r * 4 + c - 1]:
                    run += 1
                else:
                    run = 1
                if run >= 3:
                    hit.update({r * 4 + c, r * 4 + c - 1, r * 4 + c - 2})
        for c in range(4):
            run = 1
            for r in range(1, 4):
                if self.g[r * 4 + c] == self.g[(r - 1) * 4 + c]:
                    run += 1
                else:
                    run = 1
                if run >= 3:
                    hit.update({r * 4 + c, (r - 1) * 4 + c, (r - 2) * 4 + c})
        return hit

    def apply(self, step_json):
        if self.done:
            return True
        if step_json.get("op") != "swap":
            return False
        a, b = int(step_json.get("a", 0)), int(step_json.get("b", 1))
        if not (0 <= a < 16 and 0 <= b < 16):
            return False
        self.g[a], self.g[b] = self.g[b], self.g[a]
        hit = self._matches()
        if not hit:                              
            self.g[a], self.g[b] = self.g[b], self.g[a]
            return False
        for i in hit:
            self.g[i] = 0
        self.cleared = getattr(self, "cleared", set())
        self.cleared |= hit
        self.steps += 1
        self.score = float(min(6, len(self.cleared)))
        if self.score >= 6:
            self.done = True
        return self.done

    def situation(self):
        return None if self.done else 0


# ══════════════════════════════════════════════════════════
class Mining(ArcadeEnv):
    ""

    NAME = "mining"
    FULL = 5.0
    RENDERER = "plan"
    STEPS = 14
    BEAM = 120
    SLOTS = frags({"op": "dig"}, {"op": "down"}, {"op": "up"},
                  {"op": "right"}, {"op": "left"})
    ORES = {(1, 1), (3, 1), (1, 3), (3, 3)}

    def reset(self):
        self.x, self.y = 2, 0            
        self.ores = set(self.ORES)
        self.score = 0.0
        self.done = False
        self.steps = 0
        return self

    def apply(self, step_json):
        if self.done:
            return True
        op = step_json.get("op")
        if op == "down":
            self.y = min(4, self.y + 1)
        elif op == "up":
            self.y = max(0, self.y - 1)
        elif op == "right":
            self.x = min(4, self.x + 1)
        elif op == "left":
            self.x = max(0, self.x - 1)
        elif op == "dig":
            self.ores.discard((self.x, self.y))
        else:
            return False
        self.steps += 1
        base = float(4 - len(self.ores)) + (1.0 if (self.y == 0 and not self.ores) else 0.0)
        if self.ores:
            d = min(abs(self.x - ox) + abs(self.y - oy) for ox, oy in self.ores)
            base += 0.09 * (1.0 - min(d, 10) / 10.0)
        elif self.y:
            base += 0.09 * (1.0 - min(self.y, 10) / 10.0)
        self.score = base
        if not self.ores and self.y == 0:
            self.score = 5.0
            self.done = True
        if self.steps >= 40:
            self.done = True
        return self.done

    def situation(self):
        return None if self.done else 0


# ══════════════════════════════════════════════════════════
class CardBattle(ArcadeEnv):
    ""

    NAME = "card_battle"
    FULL = 1.0
    RENDERER = "table"
    CONDITIONS = 4
    SLOTS = frags({"op": "attack"}, {"op": "block"}, {"op": "heal"})

    def reset(self):
        self.hp, self.ehp, self.t = 20, 20, 0
        self.guard = 0
        self.score = 0.0
        self.done = False
        self.steps = 0
        return self

    def apply(self, step_json):
        if self.done:
            return True
        op = step_json.get("op")
        if op == "attack":
            self.ehp -= 4
        elif op == "heal":
            self.hp = min(20, self.hp + 3)
        elif op == "block":
            self.guard = 1
        else:
            return False
        self.steps += 1
        self.t += 1
        if self.ehp <= 0:
            self.score = 1.0
            self.done = True
            return True
        dmg = 5 if self.t % 2 == 0 else 3        
        if self.guard:
            dmg = max(0, dmg - 3)
            self.guard = 0
        self.hp -= dmg
        self.score = min(0.99, (20 - self.ehp) / 20.0)
        if self.hp <= 0 or self.steps >= 60:
            self.done = True
        return self.done

    def situation(self):
        if self.done:
            return None
        if self.hp > 12:
            return 0
        if self.hp > 6:
            return 1
        return 2 if self.hp > 2 else 3


# ══════════════════════════════════════════════════════════
class Blackjack(ArcadeEnv):
    ""

    NAME = "blackjack"
    FULL = 3.0
    RENDERER = "table"
    CONDITIONS = 3
    SLOTS = frags({"op": "hit"}, {"op": "stand"})
    DECK = [4, 7, 11, 3, 11, 9, 7, 4, 10, 11, 3, 7, 3, 3, 5, 5, 7, 7]

    def reset(self):
        self.i = 0
        self.won = 0
        self.hand = 0
        self.dealer = 0
        self.phase = "player"
        self.score = 0.0
        self.done = False
        self.steps = 0
        self._deal()
        return self

    def _card(self):
        v = self.DECK[self.i % len(self.DECK)]
        self.i += 1
        return v

    def _deal(self):
        self.hand = self._card() + self._card()
        self.dealer = self._card()

    def apply(self, step_json):
        if self.done:
            return True
        op = step_json.get("op")
        if self.phase != "player" or op not in ("hit", "stand"):
            return False
        self.steps += 1
        if op == "hit":
            self.hand += self._card()
            if self.hand > 21:
                self._next()
                return self.done
            return False
        while self.dealer < 17:
            self.dealer += self._card()
        if self.dealer > 21 or self.hand > self.dealer:
            self.won += 1
        self.score = float(self.won)
        self._next()
        return self.done

    def _next(self):
        if self.won >= 3 or self.i >= len(self.DECK) - 3:
            self.score = float(self.won)
            self.done = True
            return
        self._deal()

    def situation(self):
        if self.done:
            return None
        if self.hand <= 11:
            return 0
        if self.hand <= 16:
            return 1
        return 2


# ══════════════════════════════════════════════════════════
class MazeAtoms6(Maze):
    ""

    NAME = "maze_atoms6"
    STEPS = 6


class MazePrims6(Maze):
    ""

    NAME = "maze_prims6"
    STEPS = 6
    BEAM = 400
    _CACHE = None

    def __init__(self):
        Maze.__init__(self)
        from hunter import primitives
        if MazePrims6._CACHE is None:
            atoms = [{"op": "go", "dir": d} for d in ("u", "d", "l", "r")]
            prims = primitives.discover(lambda: Maze(), atoms, depth=3,
                                        samples=16, top=6)
            MazePrims6._CACHE = frags(*(atoms + prims))
        self.SLOTS = MazePrims6._CACHE


# ══════════════════════════════════════════════════════════
class MazeSmall(Maze):
    ""

    NAME = "maze_small"
    COINS = {(1, 0), (3, 1)}
    EXIT = (3, 3)
    WALLS = {(0, 4), (1, 4)}
    STEPS = 6


class MazeSmallAtoms(MazeSmall):
    ""

    NAME = "maze_small_atoms"
    STEPS = 3


class MazeSmallPrims(MazeSmall):
    ""

    NAME = "maze_small_prims"
    STEPS = 3
    _CACHE = None

    def __init__(self):
        MazeSmall.__init__(self)
        from hunter import primitives
        if MazeSmallPrims._CACHE is None:
            atoms = [{"op": "go", "dir": d} for d in ("u", "d", "l", "r")]
            prims = primitives.discover(lambda: MazeSmall(), atoms, depth=3,
                                        samples=12, top=8, seed=3)
            MazeSmallPrims._CACHE = (frags(*(atoms + prims)), len(prims))
        self.SLOTS = MazeSmallPrims._CACHE[0]
