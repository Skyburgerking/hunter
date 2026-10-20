# -*- coding: utf-8 -*-
""

import itertools
import os
import sys
from collections import deque

from hunter.features import feature

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
GH = os.path.join(ROOT, "_gh", "sokoban2")
_PKG = {}
DIRS = ((-1, 0, "u"), (1, 0, "d"), (0, -1, "l"), (0, 1, "r"))


def _sok():
    if _PKG:
        return _PKG
    if not os.path.isdir(GH):
        raise ImportError("找不到 %s，先 git clone --depth 1 "
                          "https://github.com/KnightofLuna/sokoban-solver" % GH)
    if GH not in sys.path:
        sys.path.insert(0, GH)
    import sokoban as _s
    _PKG["s"] = _s
    return _PKG


class SokobanEnv(object):
    ""

    def __init__(self, level="test1", cap=40, seed=None, situation_mode="mask"):
        self.level = level
        self.cap = int(cap)          
        self.situation_mode = situation_mode
        self.score = 0.0

    
    def _load_level(self):
        base = os.path.join(GH, "sokobanLevels")
        path = os.path.join(base, self.level + ".txt")
        if not os.path.isfile(path):
            raise IOError("没有这一关：%s（%s）" % (self.level, base))
        with open(path) as handle:
            return [line.rstrip("\r\n") for line in handle if line.strip("\r\n")]

    def reset(self):
        s = _sok()["s"]
        board = s.transferToGameState(self._load_level())
        self.goals = set(tuple(int(v) for v in g) for g in s.PosOfGoals(board))
        self.walls = set(tuple(int(v) for v in w) for w in s.PosOfWalls(board))
        self.player = tuple(int(v) for v in s.PosOfPlayer(board))
        self.boxes = set(tuple(int(v) for v in b) for b in s.PosOfBoxes(board))
        
        s.posGoals = tuple(sorted(self.goals))
        s.posWalls = tuple(sorted(self.walls))
        self.moves = 0               
        self.pushes = 0              
        self.failed = False
        self.solved = self.boxes == self.goals
        self._init_dist = max(1.0, self._total_dist())
        self.score = self._score_now()
        return self._obs(self.player, self.boxes)

    
    def _total_dist(self):
        return sum(min(abs(b[0] - g[0]) + abs(b[1] - g[1]) for g in self.goals)
                   for b in self.boxes)

    def _score_now(self):
        placed = len(self.boxes & self.goals)
        if placed >= len(self.boxes):
            return float(placed)                     
        prog = 1.0 - self._total_dist() / max(1.0, getattr(self, "_init_dist", 1.0))
        return placed + 0.9 * max(0.0, min(0.999, prog))

    
    def candidates(self):
        if self.solved or self.failed or self.pushes >= self.cap:
            return []
        out = []
        for box in sorted(self.boxes):
            for dx, dy, ch in DIRS:
                stand = (box[0] - dx, box[1] - dy)
                dest = (box[0] + dx, box[1] + dy)
                if stand in self.walls or stand in self.boxes:
                    continue
                if dest in self.walls or dest in self.boxes:
                    continue
                path = self._path(self.player, stand, self.boxes - {box})
                if path is None:
                    continue
                out.append((box[0], box[1], dx, dy))
        return out

    def peek(self, action):
        bx, by, dx, dy = action
        boxes = set(self.boxes)
        boxes.discard((bx, by))
        boxes.add((bx + dx, by + dy))
        return self._obs((bx, by), boxes)      

    def step(self, action):
        bx, by, dx, dy = action
        stand = (bx - dx, by - dy)
        path = self._path(self.player, stand, self.boxes - {(bx, by)}) or []
        self.moves += len(path) + 1
        self.boxes.discard((bx, by))
        self.boxes.add((bx + dx, by + dy))
        self.player = (bx, by)
        self.pushes += 1

        before = len(self.boxes & self.goals)
        self.solved = self.boxes == self.goals
        if not self.solved and _sok()["s"].isFailed(tuple(sorted(self.boxes))):
            self.failed = True
        self.score = self._score_now()

        obs = self._obs(self.player, self.boxes)
        reward = 10.0 * (self.score - before) - 0.05 - 0.02 * len(path)
        if self.solved:
            reward += 50.0
        if self.failed:
            reward -= 30.0
        done = self.solved or self.failed or self.pushes >= self.cap
        return obs, reward, done, {"solved": self.solved, "failed": self.failed}

    
    def apply(self, step_json):
        ""
        if self.solved or self.failed or self.pushes >= self.cap:
            return True
        if step_json.get("op") != "push":
            return False
        boxes = sorted(self.boxes)
        raw = step_json.get("box", 0)
        if raw == "near":
            idx = self.nearest_box()
            if idx is None:
                return False
        else:
            idx = int(raw)
        if idx < 0 or idx >= len(boxes):
            return False
        box = boxes[idx]
        dmap = {"u": (0, -1), "d": (0, 1), "l": (-1, 0), "r": (1, 0)}
        d = dmap.get(str(step_json.get("dir", "u")))
        if d is None:
            return False
        action = (box[0], box[1], d[0], d[1])
        if action not in self.candidates():
            return False
        _, _, done, _ = self.step(action)
        return done

    def nearest_box(self):
        ""
        if self.solved or self.failed or self.pushes >= self.cap:
            return None
        pend = [b for b in sorted(self.boxes) if b not in self.goals]
        if not pend:
            return None
        best_box, best_len = pend[0], 10 ** 9
        for box in pend:
            for dx, dy, _ in DIRS:
                path = self._path(self.player, (box[0] - dx, box[1] - dy),
                                  self.boxes - {box})
                if path is not None and len(path) < best_len:
                    best_box, best_len = box, len(path)
        return sorted(self.boxes).index(best_box)

    def situation_side(self):
        idx = self.nearest_box()
        if idx is None:
            return None
        box = sorted(self.boxes)[idx]
        dx, dy = self.player[0] - box[0], self.player[1] - box[1]
        if abs(dx) >= abs(dy):
            side = 3 if dx > 0 else 2
        else:
            side = 1 if dy > 0 else 0
        return min(idx, 2) * 4 + side

    def situation(self):
        if getattr(self, "situation_mode", "mask") == "side":
            return self.situation_side()
        ""
        if self.solved or self.failed or self.pushes >= self.cap:
            return None
        mask = 0
        for i, box in enumerate(sorted(self.boxes)):
            if box in self.goals:
                mask |= 1 << i
        return mask if mask != (1 << len(self.boxes)) - 1 else None

    
    def _path(self, start, goal, blocked):
        if start == goal:
            return []
        seen = {start}
        queue = deque([(start, [])])
        while queue:
            (x, y), path = queue.popleft()
            for dx, dy, ch in DIRS:
                nxt = (x + dx, y + dy)
                if nxt in seen or nxt in self.walls or nxt in blocked:
                    continue
                if nxt == goal:
                    return path + [ch]
                seen.add(nxt)
                queue.append((nxt, path + [ch]))
        return None

    
    def _obs(self, player, boxes):
        goals = self.goals

        def dist(a, b):
            return abs(a[0] - b[0]) + abs(a[1] - b[1])

        loose = sorted(boxes - goals)
        pool = sorted(goals - boxes)
        
        if not loose:
            box_dist = 0
        elif not pool:
            box_dist = 20 * len(loose)
        elif len(loose) <= 5 and len(pool) <= 5:
            box_dist = min(sum(dist(b, g) for b, g in zip(loose, perm))
                           for perm in itertools.permutations(pool, len(loose)))
        else:
            box_dist = sum(min(dist(b, g) for g in pool) for b in loose)

        
        stuck = 0
        for b in boxes - goals:
            x, y = b
            up = (x - 1, y) in self.walls
            down = (x + 1, y) in self.walls
            left = (x, y - 1) in self.walls
            right = (x, y + 1) in self.walls
            if (up or down) and (left or right):
                stuck += 1

        
        gap = None
        for b in loose:
            for dx, dy, ch in DIRS:
                stand = (b[0] - dx, b[1] - dy)
                dest = (b[0] + dx, b[1] + dy)
                if stand in self.walls or stand in boxes or dest in self.walls or dest in boxes:
                    continue
                d = dist(player, stand)
                gap = d if gap is None else min(gap, d)

        
        dead = False
        if boxes != goals:
            try:
                dead = _sok()["s"].isFailed(tuple(sorted(boxes)))
            except Exception:
                dead = False

        return {
            "on_goal": float(len(boxes & goals)),
            "boxes_left": float(len(loose)),
            "box_dist": float(box_dist),
            "stuck": float(stuck),
            "player_gap": float(gap if gap is not None else 12),
            "solved": 1.0 if boxes == goals else 0.0,
            "failed": 1.0 if (dead or self.failed) else 0.0,
        }


# ══════════════════════════════════════════════════════════
@feature("sok_on_goal")
def _on_goal(s):
    return float(s.get("on_goal", 0)) / 4.0


@feature("sok_box_dist")
def _box_dist(s):
    return -float(s.get("box_dist", 0)) / 20.0


@feature("sok_stuck")
def _stuck(s):
    return -float(s.get("stuck", 0))


@feature("sok_player_gap")
def _player_gap(s):
    return -float(s.get("player_gap", 0)) / 10.0


@feature("sok_solved")
def _solved(s):
    return float(s.get("solved", 0.0))


@feature("sok_failed")
def _failed(s):
    return -float(s.get("failed", 0.0))
