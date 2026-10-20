# -*- coding: utf-8 -*-
""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time

from benches.tetris import TetrisEnv, _heights

WEIGHTS = {"lines": 1.5, "height": 0.7, "holes": 1.6, "bump": 1.5, "depth": 1}
CAP = 10 ** 9


def main():
    seed = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    env = TetrisEnv(seed=seed, max_pieces=CAP, max_steps=10 ** 9)
    obs = env.reset()
    done = False
    t0 = time.time()
    last = 0
    print("start seed=%d weights=%s" % (seed, WEIGHTS), flush=True)
    while not done:
        obs, reward, done, info = env.step(env.act(WEIGHTS, obs))
        if env.pieces - last >= 1000:
            last = env.pieces
            hs = _heights(env.board)
            holes = sum(
                1
                for x in range(10)
                for y in range(20)
                if not env.board[y][x] and any(env.board[yy][x] for yy in range(y))
            )
            print(
                "%7d 块  %7d 行  %9d 分  %5.0fs  高 %2d  洞 %3d"
                % (env.pieces, env.lines, env.score, time.time() - t0, max(hs), holes),
                flush=True,
            )
    print(
        "DIED at %d 块 / %d 行 / %d 分 / %.0fs"
        % (env.pieces, env.lines, env.score, time.time() - t0),
        flush=True,
    )


if __name__ == "__main__":
    main()
