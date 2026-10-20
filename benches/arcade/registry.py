# -*- coding: utf-8 -*-
""
from .games_board import (TicTacToe, Connect4, LightsOut, Queens8,
                          Sudoku4, Hanoi3, Fifteen)
from .games_arcade import (Snake, Flappy, Pong, Breakout, Thunder,
                           Lunar, Cartpole, Racing)
from .games_sim import (Minesweeper, Maze, MazeAtoms6, MazePrims6,
                        MazeSmall, MazeSmallAtoms, MazeSmallPrims,
                        TowerDefense, Platformer, Match3, Mining,
                        CardBattle, Blackjack)
from .games_classic import (TetrisArcade, Game2048, Drone, GridHunt,
                            Guess, JobShop, Corridor, CartpoleAuto)
from .games_finance import FinrlTrade
from .games_external import (SokobanExt, Sokoban5Ext, PacmanExt,
                             PvzExt, RtsExt)

GAMES = {
    "tic_tac_toe": TicTacToe,
    "connect4": Connect4,
    "lights_out": LightsOut,
    "queens8": Queens8,
    "sudoku4": Sudoku4,
    "hanoi3": Hanoi3,
    "fifteen": Fifteen,
    "snake": Snake,
    "flappy": Flappy,
    "pong": Pong,
    "breakout": Breakout,
    "thunder": Thunder,
    "lunar": Lunar,
    "cartpole": Cartpole,
    "racing": Racing,
    "minesweeper": Minesweeper,
    "maze": Maze,
    "maze_small": MazeSmall,
    "maze_small_prims": MazeSmallPrims,
    "tower_defense": TowerDefense,
    "platformer": Platformer,
    "match3": Match3,
    "mining": Mining,
    "card_battle": CardBattle,
    "blackjack": Blackjack,
    "tetris_arcade": TetrisArcade,
    "game2048": Game2048,
    "drone": Drone,
    "grid_hunt": GridHunt,
    "guess": Guess,
    "jobshop": JobShop,
    "corridor": Corridor,
    "cartpole_auto": CartpoleAuto,
    "finrl_trade": FinrlTrade,
    "sokoban_ext": SokobanExt,
    "sokoban5_ext": Sokoban5Ext,
    "pacman_ext": PacmanExt,
    "pvz_ext": PvzExt,
    "rts_ext": RtsExt,
}



CONTROLS = {
    "maze_small_atoms": MazeSmallAtoms,   
    "maze_atoms6": MazeAtoms6,            
    "maze_prims6": MazePrims6,            
}


def make(name):
    if name in GAMES:
        return GAMES[name]()
    return CONTROLS[name]()
