# specs/payload — 主方向的规格清单

跑法都一样：

```bash
python scripts/train_payload.py specs/payload/<名字>.json
```

存档写到 `out/payload/<名字>.json`。

## 主推的（都打满了）

| 规格 | 渲染器 | 局面/步数 | 成绩 |
|---|---|---|---|
| `sokoban_plan.json` | plan | 8 步 | **2.0 / 2.0**，第 1 代 |
| `sokoban_table.json` | table | 3 个局面 | **2.0 / 2.0**，第 14 代 |
| `sokoban5_plan.json` | plan | 10 步计划 | **3.0 / 3.0（3 箱全中）** |
| `rts_plan.json` | plan | 80 步姿态 | **493.2 = 打赢**（第 77 代） |
| `pvz_table.json` | table | 10 个局面 | **330 = 通关**，第 1 代 |
| `pacman_table.json` | table | 3 个危险档 | 最优 **1939**，连跑 5 次全部清盘 |

## 对照用的（都是同一道题的低配版，用来证明「片段/局面键/步长」三件事）

| 规格 | 差在哪 | 成绩 |
|---|---|---|
| `pacman_plan.json` | 300 步定长计划，不能看局面改主意 | 658 |
| `pacman_table12.json` | 12 档（危险 × 食物方向）+ 只会走绝对方向 | 144 |
| `rts_table.json` | 3 档 × 6 姿态查表，预算也小 | 147.2（打了伤害，没赢） |

这三个留着当反面对照：**同一套核，换掉的只是片段/局面键，分数差十倍。**

## 移出去的：test5 的查表版

`sokoban5_table.json` 移到了 `_tries/`：3 个箱子挤一条走廊、必须先推中间那个，
**查表表达不了顺序**（12 档侧位表最高 1/3，逐格精修也提不上去）。
同一道题用 **plan + 收尾精修** 是满分 3.0 —— 拿 `sokoban5_plan.json`。
