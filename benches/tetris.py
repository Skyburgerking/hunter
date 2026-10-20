# -*- coding: utf-8 -*-
""

import random

W, H = 10, 20

SHAPES = {
    "I": [[0, 0, 0, 0], [1, 1, 1, 1], [0, 0, 0, 0], [0, 0, 0, 0]],
    "J": [[1, 0, 0], [1, 1, 1], [0, 0, 0]],
    "L": [[0, 0, 1], [1, 1, 1], [0, 0, 0]],
    "O": [[1, 1], [1, 1]],
    "S": [[0, 1, 1], [1, 1, 0], [0, 0, 0]],
    "T": [[0, 1, 0], [1, 1, 1], [0, 0, 0]],
    "Z": [[1, 1, 0], [0, 1, 1], [0, 0, 0]],
}

LINE_SCORE = {1: 100, 2: 300, 3: 500, 4: 800}


def _rotate(m):
    return [list(row) for row in zip(*m[::-1])]


def _shape_of(name):
    base = SHAPES[name]
    out = []
    cur = base
    for _ in range(4):
        key = tuple(tuple(r) for r in cur)
        if key not in out:
            out.append(key)
        cur = _rotate(cur)
    return [[list(r) for r in m] for m in out]


ROTATIONS = {name: _shape_of(name) for name in SHAPES}


class TetrisEnv:
    name = "tetris"

    def __init__(self, seed=None, max_pieces=500, max_steps=4000):
        self.rng = random.Random(seed)
        self.max_pieces = max_pieces
        self.max_steps = max_steps

    
    def reset(self):
        self.board = [[0] * W for _ in range(H)]
        self.bag = []
        self.piece = self._next_piece()
        self.next_piece = self._peek_piece()
        self.pieces = 0
        self.steps = 0
        self.lines = 0
        self.score = 0
        self.dead = False
        return self._obs()

    def _peek_piece(self):
        if not self.bag:
            self.bag = list(SHAPES.keys())
            self.rng.shuffle(self.bag)
        return self.bag[-1]

    def _next_piece(self):
        if not self.bag:
            self.bag = list(SHAPES.keys())
            self.rng.shuffle(self.bag)
        return self.bag.pop()

    def _obs(self):
        return {"board": [row[:] for row in self.board], "piece": self.piece,
                "lines": self.lines, "score": self.score}

    
    def _cells(self, name, rot, col, row):
        shape = ROTATIONS[name][rot % len(ROTATIONS[name])]
        out = []
        for dy, line in enumerate(shape):
            for dx, v in enumerate(line):
                if v:
                    out.append((col + dx, row + dy))
        return out

    def _collide(self, cells):
        for x, y in cells:
            if x < 0 or x >= W or y >= H:
                return True
            if y >= 0 and self.board[y][x]:
                return True
        return False

    def _drop_row(self, name, rot, col):
        row = -3
        while not self._collide(self._cells(name, rot, col, row + 1)):
            row += 1
        return row

    def _place(self, board, name, rot, col):
        ""
        row = -3
        trial = [r[:] for r in board]
        while True:
            cells = self._cells(name, rot, col, row + 1)
            bad = any(x < 0 or x >= W or y >= H or (y >= 0 and trial[y][x])
                      for x, y in cells)
            if bad:
                break
            row += 1
        cells = self._cells(name, rot, col, row)
        if any(x < 0 or x >= W or y >= H or (y >= 0 and trial[y][x]) for x, y in cells):
            return board, 0, False
        for x, y in cells:
            if y >= 0:
                trial[y][x] = name   
        cleared = 0
        keep = []
        for line in trial:
            if all(line):
                cleared += 1
            else:
                keep.append(line)
        while len(keep) < H:
            keep.insert(0, [0] * W)
        return keep, cleared, True

    
    @staticmethod
    def _features(board):
        heights = []
        for x in range(W):
            top = H
            for y in range(H):
                if board[y][x]:
                    top = y
                    break
            heights.append(H - top)
        holes = 0
        for x in range(W):
            seen = False
            for y in range(H):
                if board[y][x]:
                    seen = True
                elif seen:
                    holes += 1
        bump = sum(abs(heights[i] - heights[i + 1]) for i in range(W - 1))
        return sum(heights), holes, bump, max(heights) if heights else 0

    def _score_move(self, board, cleared, params):
        height, holes, bump, _top = self._features(board)
        w_lines = params.get("lines", 1.0)
        w_height = params.get("height", 0.5)
        w_holes = params.get("holes", 0.6)
        w_bump = params.get("bump", 0.2)
        return (w_lines * cleared * 8.0
                - w_height * height * 0.6
                - w_holes * holes * 2.0
                - w_bump * bump * 0.4)

    
    def step(self, action):
        self.steps += 1
        rot = col = 0
        try:
            body = action[1:]
            r_part, c_part = body.split("c")
            rot, col = int(r_part), int(c_part)
        except Exception:
            pass
        board, cleared, ok = self._place(self.board, self.piece, rot, col)
        if not ok:
            self.dead = True
            return self._obs(), -2.0, True, {"reason": "invalid", "lines": self.lines}
        self.board = board
        self.pieces += 1
        if cleared:
            self.lines += cleared
            self.score += LINE_SCORE.get(cleared, 800)
        reward = cleared * 1.0 - 0.02
        self.piece = self._next_piece()
        self.next_piece = self._peek_piece()
        done = (self._collide(self._cells(self.piece, 0, 3, 0))
                or self._no_landing()
                or self.pieces >= self.max_pieces or self.steps >= self.max_steps)
        if done:
            self.dead = True
            reward -= 1.0
        return self._obs(), reward, done, {"lines": self.lines, "score": self.score}

    def _no_landing(self):
        ""
        for rot in range(len(ROTATIONS[self.piece])):
            for col in range(-3, W):
                if self._place(self.board, self.piece, rot, col)[2]:
                    return False
        return True

    def _best_next(self, board, piece, params):
        best = -1e18
        for rot in range(len(ROTATIONS[piece])):
            for col in range(-3, W):
                b2, c2, ok = self._place(board, piece, rot, col)
                if not ok:
                    continue
                v = self._score_move(b2, c2, params)
                if v > best:
                    best = v
        return best

    
    @staticmethod
    def _parse(action):
        try:
            r_part, c_part = action[1:].split("c")
            return int(r_part), int(c_part)
        except Exception:
            return 0, 3

    def candidates(self):
        out = []
        for rot in range(len(ROTATIONS[self.piece])):
            for col in range(-3, W):
                if self._place(self.board, self.piece, rot, col)[2]:
                    out.append("r%dc%d" % (rot, col))
        return out

    def peek(self, action):
        rot, col = self._parse(action)
        board, cleared, ok = self._place(self.board, self.piece, rot, col)
        if not ok:
            return None
        return {"board": board, "cleared": cleared,
                "reward": cleared * 1.0 - 0.02, "done": False,
                "env": self, "next_piece": self.next_piece}

    def act(self, params, obs):
        depth = int(params.get("depth", 1))
        gamma = float(params.get("gamma", 0.9))
        best, best_score = None, -1e18
        for rot in range(len(ROTATIONS[self.piece])):
            for col in range(-3, W):
                board, cleared, ok = self._place(self.board, self.piece, rot, col)
                if not ok:
                    continue
                value = self._score_move(board, cleared, params)
                if depth >= 2:
                    value += gamma * self._best_next(board, self.next_piece, params)
                if value > best_score:
                    best_score = value
                    best = (rot, col)
        if best is None:
            return "r0c3"
        return "r%dc%d" % best


# ══════════════════════════════════════════════════════════

# ══════════════════════════════════════════════════════════
import hunter.features


def _heights(board):
    out = []
    for x in range(W):
        top = H
        for y in range(H):
            if board[y][x]:
                top = y
                break
        out.append(H - top)
    return out


def _agg_height(board):
    return sum(_heights(board))


def _max_height(board):
    return max(_heights(board))


def _holes(board):
    count = 0
    for x in range(W):
        seen = False
        for y in range(H):
            if board[y][x]:
                seen = True
            elif seen:
                count += 1
    return count


def _bumpiness(board):
    hs = _heights(board)
    return sum(abs(hs[i] - hs[i + 1]) for i in range(W - 1))


def _wells(board):
    hs = _heights(board)
    total = 0
    for i in range(W):
        left = hs[i - 1] if i > 0 else H
        right = hs[i + 1] if i < W - 1 else H
        depth = min(left, right) - hs[i]
        if depth > 0:
            total += depth
    return total


def _row_transitions(board):
    total = 0
    for y in range(H):
        prev = 1
        for x in range(W):
            cur = 1 if board[y][x] else 0
            if cur != prev:
                total += 1
            prev = cur
        if prev == 0:
            total += 1
    return total


def _col_transitions(board):
    total = 0
    for x in range(W):
        prev = 1
        for y in range(H):
            cur = 1 if board[y][x] else 0
            if cur != prev:
                total += 1
            prev = cur
        if prev == 0:
            total += 1
    return total


@hunter.features.feature("lines")
def _f_lines(state):
    return float(state.get("cleared", 0))


@hunter.features.feature("height")
def _f_height(state):
    return -_agg_height(state["board"]) / 100.0


@hunter.features.feature("max_h")
def _f_max_h(state):
    return -_max_height(state["board"]) / 10.0


@hunter.features.feature("holes")
def _f_holes(state):
    return -_holes(state["board"]) / 10.0


@hunter.features.feature("bump")
def _f_bump(state):
    return -_bumpiness(state["board"]) / 10.0


@hunter.features.feature("wells")
def _f_wells(state):
    return -_wells(state["board"]) / 10.0


@hunter.features.feature("row_trans")
def _f_row_trans(state):
    return -_row_transitions(state["board"]) / 10.0


@hunter.features.feature("col_trans")
def _f_col_trans(state):
    return -_col_transitions(state["board"]) / 10.0



def _well_depth(board):
    hs = _heights(board)
    best = 0
    for i in range(W):
        left = hs[i - 1] if i > 0 else H
        right = hs[i + 1] if i < W - 1 else H
        depth = min(left, right) - hs[i]
        if depth > best:
            best = depth
    return best


def _flatness(board):
    hs = _heights(board)
    mean = sum(hs) / len(hs)
    var = sum((h - mean) ** 2 for h in hs) / len(hs)
    return -var / 10.0


@hunter.features.feature("well_depth")
def _f_well_depth(state):
    return _well_depth(state["board"]) / 10.0


@hunter.features.feature("flat")
def _f_flat(state):
    return _flatness(state["board"]) / 10.0
