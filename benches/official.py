# -*- coding: utf-8 -*-
""

import os
import random
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_PKG_DIR = os.path.join(ROOT, "_gh", "Tetris-DQN-master", "gym_tetris")
sys.path.insert(0, os.path.dirname(_PKG_DIR))


import types  # noqa: E402
_pkg = types.ModuleType("gym_tetris")
_pkg.__path__ = [_PKG_DIR]
sys.modules.setdefault("gym_tetris", _pkg)

from gym_tetris.board import Board  # noqa: E402
from gym_tetris.game import Game   # noqa: E402

import hunter.features  # noqa: E402


INDEX = {
    "lines": 0,
    "bump": 1,
    "holes": 2,
    "landing": 3,
    "row_trans": 4,
    "col_trans": 5,
    "wells": 6,
    "eroded": 7,
    "height": 8,
}


SIGN = {
    "lines": 1.0,
    "bump": -1.0,
    "holes": -1.0,
    "landing": -1.0,
    "row_trans": -1.0,
    "col_trans": -1.0,
    "wells": -1.0,
    "eroded": 1.0,
    "height": -1.0,
}

SCALE = {
    "lines": 1.0,
    "bump": 0.1,
    "holes": 0.1,
    "landing": 0.1,
    "row_trans": 0.1,
    "col_trans": 0.1,
    "wells": 0.1,
    "eroded": 1.0,
    "height": 0.01,
}


def _make(i, sign, scale):
    def fn(state):
        return sign * float(state[i]) * scale
    return fn


for _name, _idx in INDEX.items():
    hunter.features.feature(_name)(_make(_idx, SIGN[_name], SCALE[_name]))


class OfficialTetris:
    ""

    def __init__(self, seed=None):
        self.seed = seed
        self.reset()

    def reset(self):
        if self.seed is not None:
            random.seed(self.seed)
        self.game = Game(Board(10, 20))
        self.states = []
        self.pieces = 0
        return None

    @property
    def score(self):
        return self.game.score

    @property
    def lines(self):
        return self.game.lines

    @property
    def level(self):
        return self.game.level

    def candidates(self):
        self.states = self.game.board.get_possible_states()
        return list(range(len(self.states)))

    def peek(self, idx):
        return self.states[idx][1]

    def step(self, idx):
        board, game = self.game.board, self.game
        action, _info = self.states[idx]
        if not board.move_and_drop(*action):
            return True
        self.pieces += 1
        rows = board.get_cleared_rows()
        if rows:
            game._complete_rows(rows)
        board.create_piece()
        return board.is_game_over()
