# -*- coding: utf-8 -*-
""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import random
import sys

from hunter.api import HunterEngine, load_spec
from benches.tetris import TetrisEnv

EPISODES = int(sys.argv[1]) if len(sys.argv) > 1 else 60
PIECES = int(sys.argv[2]) if len(sys.argv) > 2 else 500

spec = load_spec('specs/tetris.json')
engine = HunterEngine(spec, seed=11)
history = []

for ep in range(EPISODES):
    env = TetrisEnv(seed=2000 + ep, max_pieces=PIECES)
    obs = env.reset()
    engine.begin_episode()
    params = engine.decode_params()
    done = False
    while not done:
        out = engine.tick(obs)
        obs, r, done, _ = env.step(env.act(out['params'], obs))
        engine.feedback(r, done)
    history.append((env.lines, env.score, params))
    if (ep + 1) % 10 == 0:
        st = engine.state()
        best_lines = max(h[0] for h in history)
        print('%3d 局  本局 %3d 行 %6d 分  历史最好 %3d 行  %s  池 %d  地形 %.2f'
              % (ep + 1, env.lines, env.score, best_lines,
                 params, st['memory'], st['terrain']))

print('--- 最优参数 ---')
print(engine.best)
print('--- 记忆池前 5 ---')
for seg, u in engine.core.memory_pool[:5]:
    print(seg, round(u, 3))


import os
import sys


