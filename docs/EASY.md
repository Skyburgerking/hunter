# 傻瓜 JSON —— 一份短文件，直接跑到 hunter 的最好状态

> 2026-10-20。这一层只回答一个问题：**怎样让一个不懂 hunter 的人，三分钟拿到它最强的表现。**
>
> ★ 这一层服务的是**另一条路：权重优化器**（基因编权重）。
> 主方向是 JSON payload，教程在 [PAYLOAD.md](PAYLOAD.md)，两条路的取舍见 [../paths/README.md](../paths/README.md)。

---

## 一、三十秒

新建 `mytask.json`：

```json
{"task": "tetris"}
```

跑（两种等价）：

```bash
python -m hunter tetris
hunter tetris              # pip install -e . 之后多这一个命令
```

或者：

```python
import hunter
hunter.solve({"task": "tetris"})       # 内置任务自动读 specs/easy/tetris.json 的默认值
hunter.solve("mytask.json")            # 自己的文件
```

就这两行。其余全自动。

---

## 二、能写什么（全部可省）

| 键 | 缺省 | 什么时候要写 |
|---|---|---|
| `task` | `"task"` | **总得写**，或用 `env` |
| `env` | 按 task 查内置别名 | 自己的环境：`"模块:类"` |
| `features` | 从环境自动认 | feature 模式：特征名列表 |
| `params` | — | param 模式：`{名: [档位]}` |
| `target` | 0 | 满分线，也是「打到就停」的门槛 |
| `episodes` | 60 | 回合数 |
| `seeds` | 2 | 每回合拿几个种子取均值 |
| `test_seeds` | 3 | 复测用几个新种子 |
| `finalists` | 3 | 池顶前几名进复赛 |
| `grace` | 5 | 达标后再观察几局才停（连续两次达标则立刻停） |
| `stop_on_target` | `true` | 想要「跑满回合数」就写 `false` |
| `scale` | `auto` | 强制 `linear` / `log` |
| `sign_check` | `true` | 关掉就少花一点时间 |
| `env_args` | `{}` | 透传给环境构造（如 `max_pieces`） |
| `memory` | `false` | 跨运行复用记忆池 |

内置别名（`python -m hunter list` 可查）：

```
tetris → benches.official:OfficialTetris   （标准实现，47,663,220 分那套）
tetris_local / 2048 / flappy / pong / guess / snake / drone / grid / queue
```

---

## 三、特征别贪多（八到九个刚好）

feature 模式的最小写法：

```json
{
  "task": "tetris_local",
  "features": ["lines", "holes", "height", "bump"]
}
```

要调档位就这么写（不写 `base`，按顺序自动编号）：

```json
{
  "task": "tetris",
  "features": {
    "lines":  [0, 1, 2],
    "holes":  [0, -2, -4],
    "height": [0, -0.5, -1]
  }
}
```

**规则只有一条：好状态给正数。** 给反了也不用怕 —— 这一层会逐个特征 +1 / −1 各跑一遍，反了就自己翻回来，并在报告里写明翻了哪几个。

---

## 四、它替你做的事（每一条都对应一个踩过的坑）

| 自动动作 | 治的是哪个坑 |
|---|---|
| `base` 按顺序编号 | 手写 index 串位 |
| `segment_len` = 维度数 | 特征多于位数，两个特征抢同一位 |
| 档位默认 `[0, .5, 1, 2, 4]` | 忘了留 0，关不掉没用的特征 |
| 试跑标定 `max_score` | 满分设低，高分全被截成 1.0 |
| 满分随最好成绩上浮（+35%） | 出现远超预期的开局时再次截断 |
| 分数重尾自动换 `log` 尺度 | 47M 和 3,000 分在 0..1 里没区别，池子排不出序 |
| 逐特征符号核对 | 方向写反，所有基因活不过十几个块 |
| 每回合 N 个种子取均值 | 一次运气锁住池顶 |
| 池顶前 K 名复赛 | 训练种子上好看、别的种子上崩 |
| 新种子复测 | 自己给自己打分 |
| `getstate/setstate` 隔离 | 环境里的 `random.seed()` 污染抽基因 |

---

## 五、报告怎么读（下面是 `python -m hunter tetris` 的真实输出）

```
[识别] 任务 tetris ｜ 模式 feature ｜ 环境 benches.official:OfficialTetris ｜ 维度 9 ｜ 回合 50 ｜ 每回合 2 种子
[标定] 试跑 6 次：最好 4,450,440 / 中位 880 → 尺度 log，满分 20,000,000
[符号] 方向核对 9 个特征：翻了 0 个
  第   1 局  本局 3,220  最好 3,220  池 1  地形 1.00  balanced
  第   2 局  本局 143,360  最好 143,360  池 2  地形 0.89  balanced
  第   3 局  本局 71,651,890  最好 71,651,890  池 3  地形 0.81  balanced
  第  10 局  本局 1,390  最好 71,651,890  池 9  地形 0.86  exploratory
  ...
[复赛] 3 个候选·验证种子重跑：74,927,580 / 58,098,330 / 41,797,330 → 入选 74,927,580
[复测] 3 个新种子：33,843,320, 28,978,900, 88,414,840 ｜ 均值 50,412,353.33 ｜ 行数 3723, 3483, 6207

────────────────────────────────────────────────────────
任务 tetris ｜ 50 局 ｜ 训练 99.0s ｜ 全程 289.8s ｜ 地形 0.78 ｜ 池 40
权重 lines=1.00  bump=0.50  holes=0.50  landing=0.50  row_trans=0.00  col_trans=4.00  wells=1.00  eroded=4.00  height=2.00
训练最好 71,651,890 ｜ 复赛(验证种子) 74,927,580 ｜ 复测(新种子) 50,412,353.33
```

三个数，分别回答三个问题：

| 数字 | 回答什么 |
|---|---|
| **训练最好** | 这一轮摸到过最好的地方是多少（可能带运气） |
| **复赛（验证种子）** | 把候选放到没训练过的种子上，还站得住吗 |
| **复测（新种子）** | 最终这个权重，在完全没见过的种子上能打多少 |

**只有第三个数算成绩。** 前两个是过程。

这条命令从头到尾五分钟上下（训练 100 秒左右，其余是复赛和复测的长局）。同一条命令连跑四次，逐位相同。

顺带一件有意思的事：这轮自己搜出来的权重
（`lines 1.0 / bump 0.5 / holes 0.5 / landing 0.5 / row_trans 0 / col_trans 4 / wells 1 / eroded 4 / height 2`）
和归档里那次 4766 万分那一局的权重**一模一样**。搜 50 局，重新走到了同一个地方。

---

## 六、自己的任务

三步，一分钟：

**1. 写环境**（只要有特征就能用，不用写策略）

```python
class MyEnv:
    def reset(self): ...
    def candidates(self):  return [动作, ...]        # 现在能选什么
    def peek(self, action): return 预演后的状态       # 确定的状态，别猜未来
    def step(self, action):
        return obs, reward, done, info               # 或只返回 done
```

**2. 注册特征**（纯函数，好状态给正数，量纲压到 0~10）

```python
from hunter.features import feature

@feature("距离")
def dist(state):
    return -abs(state["x"] - 10) / 10.0
```

**3. 写 JSON**

```json
{"task": "mytask", "env": "mymod:MyEnv", "features": ["距离", "血量"]}
```

---

## 七、它救不了你的时候

这一层只补「调用姿势」，不补「题出得对不对」。下面五条仍然要人负责：

1. **特征池决定上限** —— 池里没有的信号，它永远发现不了。
2. **`peek` 必须是确定的** —— 棋盘可以，明天涨跌不行。它是评估器，不是预测器。
3. **维度别超 10^6** —— 5 档时 8~9 个特征刚好（39 万~195 万）；超了会打一行提示。
4. **测量错误比算法错误常见** —— 分数不涨先查「是不是被截断、是不是没死、是不是量纲错了」。
5. **重尾任务里它基本在做随机搜索** —— 分数能从 0 跑到一亿的任务（方块就是），
   归一化后普通局面的效用很低，压力常年拉满，引擎几乎一直处在 `exploratory`。
   这不是坏处（这类任务本来就靠抽得多），但要清楚：这类任务上别指望「记忆池的利用」替你省回合。

---

## 八、和旧写法的关系

傻瓜 JSON 是**入口**，不是替代。它最后展开成的就是原来的 setting，存在报告的 `spec` 字段里：

```python
report = hunter.solve("specs/easy/tetris.json")
report["spec"]      # 完整的 features / segment_len / max_score
report["weights"]   # 最优权重
```

想自己接管回合，把 `spec` 丢给 `HunterEngine` 就行，用法见 `docs/USAGE.md`。

---

## 九、换游戏验过（2026-10-20）

四款 GitHub 上的真游戏，一份 JSON 一款，核一行没改：

| 命令 | 接的是什么 | 复测 |
|---|---|---|
| `python -m hunter pacman` | UC Berkeley CS188 的吃豆人 | 1,122.67 |
| `python -m hunter sokoban` | KnightofLuna 的推箱子 | 3.00（3 个箱子全中） |
| `python -m hunter pvz` | marblexu 的植物大战僵尸（3.7k star） | 330.00（通关） |
| `python -m hunter rts` | OpenRA 的坦克数值 | 534.60（赢） |

怎么接的、哪里翻车了、随机基线报分布的结果 —— 全在 [EASY_GAMES.md](EASY_GAMES.md)。

一句话：**JSON 只写「有哪些特征」，其它交给它；成绩只看复测那一行。**
