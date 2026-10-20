# -*- coding: utf-8 -*-
""
from .base import ArcadeEnv, frags


# ══════════════════════════════════════════════════════════
class TicTacToe(ArcadeEnv):
    ""

    NAME = "tic_tac_toe"
    FULL = 1.0
    RENDERER = "plan"
    STEPS = 5
    BEAM = 16
    SLOTS = frags(*[{"op": "put", "cell": i} for i in range(9)])

    LINES = ((0, 1, 2), (3, 4, 5), (6, 7, 8),
             (0, 3, 6), (1, 4, 7), (2, 5, 8),
             (0, 4, 8), (2, 4, 6))

    def reset(self):
        self.board = [""] * 9
        self.score = 0.0
        self.done = False
        self.steps = 0
        return self

    def _win(self, who):
        return any(all(self.board[i] == who for i in line) for line in self.LINES)

    def _opponent(self):
        for i in range(9):
            if not self.board[i]:
                self.board[i] = "O"
                return

    def apply(self, step_json):
        if self.done:
            return True
        if step_json.get("op") != "put":
            return False
        cell = int(step_json.get("cell", 0))
        if not (0 <= cell < 9) or self.board[cell]:
            return False
        self.board[cell] = "X"
        self.steps += 1
        if self._win("X"):
            self.score = 1.0
            self.done = True
            return True
        if all(self.board):
            self.done = True
            return True
        self._opponent()
        if self._win("O"):
            self.done = True
        return self.done

    def situation(self):
        return None if self.done else 0


# ══════════════════════════════════════════════════════════
class Connect4(ArcadeEnv):
    ""

    NAME = "connect4"
    FULL = 1.0
    RENDERER = "plan"
    STEPS = 8
    BEAM = 20
    SLOTS = frags(*[{"op": "drop", "col": c} for c in range(7)])
    W, H = 7, 6

    def reset(self):
        self.grid = [[0] * self.W for _ in range(self.H)]   
        self.score = 0.0
        self.done = False
        self.steps = 0
        return self

    def _drop(self, col, who):
        if not (0 <= col < self.W):
            return False
        for y in range(self.H - 1, -1, -1):
            if self.grid[y][col] == 0:
                self.grid[y][col] = who
                return True
        return False

    def _best_line(self, who):
        best = 0
        for y in range(self.H):
            for x in range(self.W):
                for dx, dy in ((1, 0), (0, 1), (1, 1), (1, -1)):
                    n = 0
                    for k in range(4):
                        nx, ny = x + dx * k, y + dy * k
                        if not (0 <= nx < self.W and 0 <= ny < self.H):
                            n = -1
                            break
                        if self.grid[ny][nx] == who:
                            n += 1
                    best = max(best, n)
        return best

    def _four(self, who):
        for y in range(self.H):
            for x in range(self.W):
                for dx, dy in ((1, 0), (0, 1), (1, 1), (1, -1)):
                    cells = []
                    for k in range(4):
                        nx, ny = x + dx * k, y + dy * k
                        if not (0 <= nx < self.W and 0 <= ny < self.H):
                            break
                        cells.append(self.grid[ny][nx])
                    if len(cells) == 4 and all(c == who for c in cells):
                        return True
        return False

    def apply(self, step_json):
        if self.done:
            return True
        if step_json.get("op") != "drop":
            return False
        col = int(step_json.get("col", 0))
        if not self._drop(col, 1):
            return False
        self.steps += 1
        if self._four(1):
            self.score = 1.0
            self.done = True
            return True
        for c in range(self.W):
            if self._drop(c, 2):
                break
        if self._four(2):
            self.done = True
        elif not self.done:
            
            self.score = self._best_line(1) / 4.0
        return self.done

    def situation(self):
        return None if self.done else 0


# ══════════════════════════════════════════════════════════
class LightsOut(ArcadeEnv):
    ""

    NAME = "lights_out"
    FULL = 1.0
    RENDERER = "plan"
    STEPS = 6
    BEAM = 200

    def __init__(self):
        ArcadeEnv.__init__(self)
        self.N = 4
        self.SLOTS = frags(*[{"op": "press", "cell": r * self.N + c}
                             for r in range(self.N) for c in range(self.N)])

    def reset(self):
        
        self.lit = [[True] * 4 for _ in range(4)]
        self.score = 0.0
        self.done = False
        self.steps = 0
        for cell in (5, 6, 9, 10):
            self._press(cell, record=False)
        self._start = [row[:] for row in self.lit]
        return self

    def _press(self, cell, record=True):
        r, c = divmod(cell, 4)
        for dr, dc in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)):
            nr, nc = r + dr, c + dc
            if 0 <= nr < 4 and 0 <= nc < 4:
                self.lit[nr][nc] = not self.lit[nr][nc]
        if record:
            self.steps += 1

    def apply(self, step_json):
        if self.done:
            return True
        if step_json.get("op") != "press":
            return False
        cell = int(step_json.get("cell", 0))
        if not (0 <= cell < 16):
            return False
        self._press(cell)
        lit = sum(1 for row in self.lit for v in row if v)
        self.score = (16 - lit) / 16.0
        if lit == 0:
            self.score = 1.0
            self.done = True
        elif self.steps >= 12:
            self.done = True
        return self.done

    def situation(self):
        return None if self.done else 0


# ══════════════════════════════════════════════════════════
class Queens8(ArcadeEnv):
    ""

    NAME = "queens8"
    FULL = 8.0
    RENDERER = "plan"
    STEPS = 8
    BEAM = 40
    SLOTS = frags(*[{"op": "place", "col": c} for c in range(8)])

    def reset(self):
        self.rows = []
        self.score = 0.0
        self.done = False
        self.steps = 0
        return self

    def _ok(self, col):
        r = len(self.rows)
        for i, c in enumerate(self.rows):
            if c == col or abs(c - col) == abs(i - r):
                return False
        return True

    def apply(self, step_json):
        if self.done:
            return True
        if step_json.get("op") != "place":
            return False
        col = int(step_json.get("col", 0))
        if not (0 <= col < 8) or not self._ok(col):
            return False
        self.rows.append(col)
        self.steps += 1
        self.score = float(len(self.rows))
        if len(self.rows) == 8:
            self.done = True
        return self.done

    def situation(self):
        return None if self.done else 0


# ══════════════════════════════════════════════════════════
class Sudoku4(ArcadeEnv):
    ""

    NAME = "sudoku4"
    FULL = 8.0
    RENDERER = "plan"
    STEPS = 8
    BEAM = 30

    SOLUTION = [[1, 2, 3, 4],
                [3, 4, 1, 2],
                [2, 1, 4, 3],
                [4, 3, 2, 1]]
    GIVEN = {0, 5, 10, 15}     

    def __init__(self):
        ArcadeEnv.__init__(self)
        self.blank = [i for i in range(16) if i not in self.GIVEN]
        self.SLOTS = frags(*[{"op": "fill", "cell": i, "v": v}
                             for i in self.blank for v in (1, 2, 3, 4)])

    def reset(self):
        self.grid = [self.SOLUTION[i // 4][i % 4] if i in self.GIVEN else 0
                     for i in range(16)]
        self.score = 0.0
        self.done = False
        self.steps = 0
        return self

    def apply(self, step_json):
        if self.done:
            return True
        if step_json.get("op") != "fill":
            return False
        cell = int(step_json.get("cell", 0))
        v = int(step_json.get("v", 0))
        if cell not in self.blank or self.grid[cell] or not (1 <= v <= 4):
            return False
        self.grid[cell] = v
        self.steps += 1
        if self.grid[cell] != self.SOLUTION[cell // 4][cell % 4]:
            self.grid[cell] = 0              
            return False
        self.score = float(sum(1 for i in self.blank if self.grid[i]))
        if self.score >= len(self.blank):
            self.done = True
        return self.done

    def situation(self):
        return None if self.done else 0


# ══════════════════════════════════════════════════════════
class Hanoi3(ArcadeEnv):
    ""

    NAME = "hanoi3"
    FULL = 3.0
    RENDERER = "plan"
    STEPS = 7
    BEAM = 400

    def __init__(self):
        ArcadeEnv.__init__(self)
        moves = []
        for a in range(3):
            for b in range(3):
                if a != b:
                    moves.append({"op": "move", "from": a, "to": b})
        self.SLOTS = frags(*moves)

    def reset(self):
        self.pegs = [[3, 2, 1], [], []]      
        self.score = 0.0
        self.done = False
        self.steps = 0
        return self

    def apply(self, step_json):
        if self.done:
            return True
        if step_json.get("op") != "move":
            return False
        a, b = int(step_json.get("from", 0)), int(step_json.get("to", 0))
        if not (0 <= a < 3 and 0 <= b < 3) or a == b or not self.pegs[a]:
            return False
        if self.pegs[b] and self.pegs[b][-1] < self.pegs[a][-1]:
            return False
        self.pegs[b].append(self.pegs[a].pop())
        self.steps += 1
        
        tower, want = 0, 3
        for disk in self.pegs[2]:
            if disk != want:
                break
            tower += 1
            want -= 1
        self.score = float(tower)
        if tower == 3:
            self.done = True
        return self.done

    def situation(self):
        return None if self.done else 0


# ══════════════════════════════════════════════════════════
class Fifteen(ArcadeEnv):
    ""

    NAME = "fifteen"
    FULL = 8.0
    RENDERER = "plan"
    STEPS = 6
    BEAM = 24
    SLOTS = frags(*[{"op": "slide", "dir": d} for d in ("u", "d", "l", "r")])

    SOLVED = list(range(1, 9)) + [0]

    def reset(self):
        self.grid = list(self.SOLVED)
        self.blank = 8
        
        for d in ("u", "l", "d", "l", "u", "r"):
            self._slide(d)
        self.score = 0.0
        self.done = False
        self.steps = 0
        return self

    def _slide(self, d):
        b = self.blank
        r, c = divmod(b, 3)
        dr, dc = {"u": (-1, 0), "d": (1, 0), "l": (0, -1), "r": (0, 1)}[d]
        nr, nc = r + dr, c + dc
        if not (0 <= nr < 3 and 0 <= nc < 3):
            return False
        nb = nr * 3 + nc
        self.grid[b], self.grid[nb] = self.grid[nb], self.grid[b]
        self.blank = nb
        return True

    def apply(self, step_json):
        if self.done:
            return True
        if step_json.get("op") != "slide":
            return False
        if not self._slide(str(step_json.get("dir", "u"))):
            return False
        self.steps += 1
        self.score = float(sum(1 for i, v in enumerate(self.grid)
                               if v and v == self.SOLVED[i]))
        if self.grid == self.SOLVED:
            self.done = True
        return self.done

    def situation(self):
        return None if self.done else 0
