# JSON payload 傻瓜教程

> 不懂 GEDA、不懂演化、不懂方块，也能用。
> 你只要回答两件事：**这台机器能做哪些动作**、**什么算好**。
> 剩下的（编基因、打分、留优、重启）引擎自己干。

---

## 一、三十秒上手

```bash
cd hunter
python scripts/train_payload.py specs/payload/sokoban_table.json
```

跑完你会看到：

```
任务 sokoban_table ｜ 120 轮 × 蜂群 30 × 2 次 ｜ 最好 2.0（第 14 代）
存档 out/payload/sokoban_table.json
```

打开存档，里面就是引擎「进化出来」的那张表：

```json
{
  "payload": {"table": [{"op": "push", "box": "near", "dir": "l"}, ...]},
  "score": 2.0,
  "gen": 7
}
```

**这就是全部产出**：一个 JSON。拿它去用，不需要 Python。

---

## 二、一份 spec 只有六件事

```json
{
  "name": "sokoban_table",     ← 名字，决定用哪个环境（前缀匹配）
  "renderer": "table",         ← plan 还是 table，见下
  "conditions": 3,             ← 只 table 用：局面有几种
  "max_score": 2.0,            ← 满分线，必须略高于真实最好成绩
  "rounds": 120,               ← 迭代多少代
  "population": 30,            ← 每代试多少个基因
  "reps": 2,                   ← 同一个基因跑几次取平均（压运气）
  "slots": { ... }             ← 动作表：每个碱基能变成哪些 JSON 片段
}
```

**`renderer` 二选一：**

| | 吐出来的是什么 | 什么时候用 |
|---|---|---|
| `plan` | `{"steps": [动作, 动作, ...]}` 一整套固定顺序 | 短局、确定性、步骤少于 30 |
| `table` | `{"table": [局面0的动作, 局面1的动作, ...]}` 一张查表 | 长局、要看着局面改主意 |

长局（吃豆人 400 步、PvZ 260 步）**只能用 table**。

---

## 三、片段怎么写：你会写字就会写

`slots` 是「五个碱基各能变成哪些 JSON」。引擎从里面挑、拼、试。

```json
"slots": {
  "A": [{"op": "push", "box": "near", "dir": "u"},
        {"op": "push", "box": "near", "dir": "l"}],
  "G": [{"op": "push", "box": "near", "dir": "r"},
        {"op": "push", "box": "near", "dir": "d"}],
  "C": [{"op": "wait"}],
  "T": [{"op": "wait"}],
  "X": [{"op": "wait"}]
}
```

三条规矩：

1. **五个键都要有**（A G C T X），缺一个引擎就少一条路。
2. **片段必须是环境认识的 JSON**，不认识的会被 `apply` 拒绝（当空转，不崩）。
3. **别写死编号，写「相对」的**。推箱子里 `"box": "near"` 比 `"box": 0` 强得多——
   箱子顺序一变，写死的编号就全废了。

### 片段里能放三类东西

| 类型 | 例子 | 用途 |
|---|---|---|
| 原语 | `{"op":"push","box":"near","dir":"l"}` | 一步小动作 |
| 带参数的 | `{"op":"goto","target":"food","avoid":2}` | 走位 + 躲鬼 2 格 |
| 整段行为 | `{"op":"plant","card":1,"lane":"front","col":1}` | 由环境解释的复合动作 |

**"整段行为"是关键**：环境里实现好一个 `goto food`，基因就只需要选「去吃 / 去躲」，
不用自己拼每一步怎么走。人写一次，引擎用一万次。

---

## 四、接一个新游戏：三步

环境只要能回答这四件事（`benches/thirdparty/*_env.py` 都是这个形状）：

```python
env.reset()             # 开一局
env.apply(step_json)    # 执行一个 JSON 片段；不合法返回 False（空转，不算崩）
env.situation()         # table 用：现在是哪种局面，返回 0..conditions-1；结束返回 None
env.score               # 现在得了几分
```

**第一步**：照着 `benches/thirdparty/sokoban_env.py` 抄一个 `apply` 和 `situation`。
`apply` 里那些「不合法就 return False」的分支一定要留，它是引擎的安全网。

**第二步**：在 `scripts/train_payload.py` 的 `FACTORIES` 里加一行：

```python
"mygame": lambda: MyGameEnv(cap=200),
```

**第三步**：写一份 spec（上面第二节），跑：

```bash
python scripts/train_payload.py specs/payload/mygame_table.json
```

### `situation()` 怎么写——这是唯一需要动脑的地方

它把局面压成一个整数，引擎按这个整数查表。**要压到「同一个整数下，该做的动作是一样的」**。

| 游戏 | 局面键 | 为什么够 |
|---|---|---|
| 推箱子 | 最近箱子 × 玩家在它哪一侧（12 档） | 同一侧、同一个箱子，该往哪推差不多 |
| 吃豆人 | 危险档 0/1/2（鬼在 6 格外 / 6 格内 / 2 格内） | 决定了「继续吃」还是「跑」 |
| PvZ | 阳光够不够 100 × 最靠前僵尸在哪条道（10 档） | 决定了「种葵花」还是「种射手」 |
| 红警 | 自己血量档 | 决定了「压上去」还是「撤」 |

**不通就调粗调细**——这是唯一的手艺，下面第六节有实例。

---

## 五、怎么读结果

```
任务 pvz_table ｜ 12 轮 × 蜂群 16 × 1 次 ｜ 最好 330.0（第 1 代）
```

| 看什么 | 什么意思 |
|---|---|
| **最好 330.0** | 训练里最高分 |
| **第 1 代** | 多早就摸到了。**第 1 代就满分 = 你的片段表写得对** |
| 池 N | 记忆池大小。池大 = 好基因多；池一直是 1 = 就一个能打的 |
| 压力 0.05~1.00 | 1.0 = 一直没进步，在乱撞；0.05 = 一直在进步 |

**第 1 代就满分时不要高兴太早**：可能是题目简单，也可能是片段表里直接塞了答案。
真的验证办法——拿存档重跑几次：

```bash
python -c "
import json, sys; sys.path.insert(0,'.')
from hunter.payload import PayloadSpace
from benches.thirdparty.pacman_env import PacmanEnv
spec = json.load(open('specs/payload/pacman_table.json', encoding='utf-8'))
d = json.load(open('out/payload/pacman_table.json', encoding='utf-8'))
sp = PayloadSpace(spec)
for k in range(3):
    e = PacmanEnv(cap=600); e.reset()
    print(sp.play(e, d['payload']))
"
```

---

## 六、要打满，必须凑齐三样（四题实测）

### ① 片段表里要有那件东西

推箱子满分（2.0）靠的片段：

```json
{"op": "push", "box": "near", "dir": "l"}
```

`"near"` = 推离玩家最近、能绕到背后去的那个箱子。换成写死编号 `"box": 0`，只到 1/2。

### ② 局面键要带够信息

| 版本 | 结果 |
|---|---|
| PvZ：键 = 僵尸在哪条道 | 60 分（5 只僵尸） |
| PvZ：键 = 阳光够不够 × 僵尸在哪条道 | **330 = 通关** |

差的就是「现在该攒钱还是该开枪」这一位。

### ③ 步长要和游戏对上

| 每步时长 | PvZ 结果 |
|---|---|
| 3.3 秒 | 30 分（来不及种） |
| 0.64 秒（和特征路一样） | **330 = 通关** |

### 四题最终成绩

| 题 | 规格 | 成绩 | 满分线 |
|---|---|---|---|
| 推箱子 | `sokoban_plan` | **2.00 / 2.00**，第 1 代 | 2 |
| 推箱子 | `sokoban_table` | **2.00 / 2.00**，第 14 代 | 2 |
| 推箱子（3 箱走廊） | `sokoban5_plan` | **3.00 / 3.00** | 3 |
| 红警 | `rts_plan` | **493.2 = 打赢** | 赢 |
| 植物大战僵尸 | `pvz_table` | **330 = 通关**，第 1 代 | 330 |
| 吃豆人 | `pacman_table` | 最优 **1939**，连跑 5 次全部清盘 | 吃光 97 颗豆 |

---

## 七、什么时候别用 payload

| 症状 | 该换什么 |
|---|---|
| 每一步都要看局面打分，且动作是「往哪走」这种细活 | 权重优化器（`python -m hunter tetris`） |
| 需要按顺序做一串事，中途被打断要重排 | 现在的 table/plan 表达不了，得让片段带状态 |
| 局面根本压不成一个小整数 | 先想想是不是要换特征路 |
| 一个片段就对、不需要组合 | 恭喜，直接写死，不用引擎 |

**「顺序题」用 plan，不要用 table**：推箱子 test5（3 个箱子挤一条走廊，必须先推中间那个）
用 `sokoban_plan` 的写法拿到 **3.0 满分**；同一道题写成 table 只有 1/3——
查表是「看局面选动作」，表达不了「先做 A 再做 B」。

### plan 的收尾精修（beam）

定长计划只整条变异时，10 格 × 4 选的空间摸不到唯一解（实测随机 4000 条，最高 2.75）。
所以 `plan` 渲染器跑完演化会再做一次**逐位往后试**：每一步只留分最高的 `beam` 条，
默认 `beam=12`（0.8 秒），拿到 3.0。规格里可以改：

```json
{ "beam": 12, "refine_seconds": 30 }
```

`table` 渲染器对应的是**逐格精修**：一格一格换片段，整局分不掉就留着（`sweeps` / `restarts` 可调）。

---

## 七点五、核的五个能力（2026-10-20 升级）

搜索和感知都在 `hunter/` 里，不挂在渲染器后面：

| 模块 | 干什么 | 一句话用法 |
|---|---|---|
| `hunter/search.py` | 收尾搜索：beam 逐位（计划）/ 逐格换片段（查表）/ 分阶段 | `core.refine(space, factory)`，`evolve()` 自动调 |
| `hunter/sense.py` | 局面自动分档：人只给范围，机器切 | `sense.Binner.fit([], bins=5, bounds=env.bounds())` |
| `hunter/primitives.py` | 原语发现：把一串动作合成一个片段 | `primitives.discover(factory, atoms, depth=3)` |
| `hunter/parallel.py` | 蜂群分进程 | `evolve(..., workers=4, factory_ref="模块:make", factory_args=("游戏",))` |
| 渲染器 `stage` | 表 = 阶段 × 局面，撑长局 | spec 里 `"renderer": "stage", "stages": 3` |

复合原语长这样，核里会自动展开：

```json
{"op": "seq", "steps": [{"op": "go", "dir": "d"},
                        {"op": "go", "dir": "d"},
                        {"op": "go", "dir": "d"}]}
```

守卫测试（街机 39 款 + 存档 + 五个能力，42 秒）：

```bash
python scripts/check_all.py
```

---

## 八、跟另一条路什么关系

同一个核，基因编的东西不一样：

```
GedaCore（五碱基 / 双链 / 怀疑链 / 记忆池 / 压力 / 步长）
   │
   ├── payload（本篇）      基因 → 一个 JSON（做什么）
   └── 权重优化器           基因 → 一组权重（看重什么）
```

选路表见 [`paths/README.md`](../paths/README.md)，另一条路见
[`paths/weight_optimizer/README.md`](../paths/weight_optimizer/README.md)。

---

## 附：全部命令

```bash
# 跑内置的四题
python scripts/train_payload.py specs/payload/sokoban_plan.json
python scripts/train_payload.py specs/payload/sokoban_table.json
python scripts/train_payload.py specs/payload/rts_plan.json
python scripts/train_payload.py specs/payload/pvz_table.json
python scripts/train_payload.py specs/payload/pacman_table.json

# 改预算（不写进 spec 也行）
python scripts/train_payload.py specs/payload/pacman_table.json --rounds 60 --population 24 --reps 2

# 换种子
python scripts/train_payload.py specs/payload/rts_plan.json --seed 7
```

存档统一在 `out/payload/<spec 名>.json`。
