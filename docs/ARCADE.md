# 街机库（39 款，全部满分）

一把跑完：

```bash
python scripts/run_arcade.py --save
```

| 游戏 | 分数 | 满分 | 步数 | 用时 |
|---|---|---|---|---|
| blackjack | 3.00 | 3.00 | 3 | 0.0s |
| breakout | 14.00 | 14.00 | 164 | 0.0s |
| card_battle | 1.00 | 1.00 | 5 | 0.0s |
| cartpole | 200.00 | 200.00 | 200 | 0.0s |
| cartpole_auto | 200.00 | 200.00 | 200 | 0.2s |
| connect4 | 1.00 | 1.00 | 8 | 1.4s |
| corridor | 1.00 | 1.00 | 30 | 0.0s |
| drone | 1.00 | 1.00 | 6 | 0.0s |
| fifteen | 8.00 | 8.00 | 6 | 0.0s |
| finrl_trade | 71.17 | 71.17 | 19 | 0.0s |
| flappy | 10.00 | 10.00 | 80 | 0.0s |
| game2048 | 256.00 | 256.00 | 141 | 31.4s |
| grid_hunt | 1.00 | 1.00 | 8 | 0.1s |
| guess | 1.00 | 1.00 | 1 | 0.0s |
| hanoi3 | 3.00 | 3.00 | 7 | 0.2s |
| jobshop | 1.00 | 1.00 | 5 | 0.0s |
| lights_out | 1.00 | 1.00 | 6 | 0.4s |
| lunar | 1.00 | 1.00 | 36 | 0.0s |
| match3 | 6.00 | 6.00 | 1 | 0.2s |
| maze | 3.00 | 3.00 | 14 | 0.4s |
| maze_small | 3.00 | 3.00 | 6 | 0.0s |
| maze_small_prims | 3.00 | 3.00 | 2 | 0.1s |
| minesweeper | 13.00 | 13.00 | 13 | 0.0s |
| mining | 5.00 | 5.00 | 13 | 0.2s |
| pacman_ext | 97.00 | 97.00 | 134 | 0.1s |
| platformer | 1.00 | 1.00 | 10 | 0.1s |
| pong | 20.00 | 20.00 | 120 | 0.1s |
| pvz_ext | 330.00 | 330.00 | 212 | 1.3s |
| queens8 | 8.00 | 8.00 | 8 | 0.0s |
| racing | 1.00 | 1.00 | 24 | 0.1s |
| rts_ext | 1.00 | 1.00 | 80 | 0.0s |
| snake | 5.00 | 5.00 | 5 | 0.1s |
| sokoban5_ext | 3.00 | 3.00 | 10 | 0.0s |
| sokoban_ext | 2.00 | 2.00 | 4 | 0.0s |
| sudoku4 | 8.00 | 8.00 | 8 | 0.4s |
| tetris_arcade | 3.00 | 3.00 | 6 | 1.7s |
| thunder | 8.00 | 8.00 | 28 | 0.1s |
| tic_tac_toe | 1.00 | 1.00 | 5 | 0.0s |
| tower_defense | 3.00 | 3.00 | 12 | 0.0s |

合计 38.8 秒，39 款全部 `score == full`。

## 分数怎么算

两类来源：

- **现场搜**：棋牌/街机/模拟/2048 等 30 款，一次命令现演化现精修，总分 34 秒；
- **存档复跑**：推箱子 ×2、吃豆人、PvZ、红警 5 款，直接回放 `out/payload` 里的存档，
  命中满分就不再重训（表里带 `from_seed` 标记）。

每款环境自带 `FULL`（这一关的理论最高分），跑出来等于它才算过。
打满靠两件事：**片段表**（JSON 动作原语）+ **局面键**（`situation()` 分档）；
搜索在 `hunter/payload.py`：演化出草稿，再用 `beam`（计划）或逐格换片段（查表）收尾。

## 加一款新的要写什么

1. `benches/arcade/games_*.py` 写一个 `ArcadeEnv` 子类：`reset / apply / situation` + `FULL` + `SLOTS`；
2. `benches/arcade/registry.py` 加一行；
3. `python scripts/run_arcade.py 你的名字`。

## 对照组（故意打不满）

```bash
python scripts/run_arcade.py --controls
```

| 对照 | 分数 | 满分 | 说明 |
|---|---|---|---|
| maze_small_atoms | 1.08 | 3.00 | 3 个槽只给单步动作 → 够不着出口 |
| maze_atoms6 | — | 3.00 | 6 个槽只给单步动作 → 14 步路线走不完 |
| maze_prims6 | 3.00 | 3.00 | 同样 6 个槽，片段换成机器发现的「三连」→ 打满 |

最后两行是同一条题、同一套核，只差片段表——原语发现到底值多少，看这里。
