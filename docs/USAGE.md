# 通用 hunter 使用说明

一份 setting 定义「能做什么」和「什么算好」，引擎负责找路。换任务只换 JSON。

> **只想快点跑起来？** 看 [EASY.md](EASY.md)：一份 5 行 JSON + `python -m hunter tetris`，
> 本篇后面所有手写字段它都自动补。本篇是完整手册，EASY 是傻瓜入口。
>
> **主方向是 JSON payload（基因吐 JSON）**，教程见 [PAYLOAD.md](PAYLOAD.md)。
> 本篇讲的 action / param / feature 三种 setting 属于「另一条路：权重优化器」，
> 两条路的分岔见 [../paths/README.md](../paths/README.md)。

---

## 一、目录

```
hunter/
  hunter/core.py        算法核：五碱基 / 双链 / 怀疑链 / 记忆池 / 热度基因 / 压力 / 步长 / 地形
  hunter/api.py         薄封装：setting → 动作与参数，管回合与分数
  hunter/policy.py      特征加权策略（feature 模式）
  hunter/features.py    特征注册表（feature 模式）

  benches/basics.py     五个示例任务（drone / snake / grid / guess / queue）
  benches/tetris.py     本地俄罗斯方块
  benches/games.py      2048 / Flappy / Pong
  benches/official.py   标准俄罗斯方块接入（GitHub gym_tetris）
  benches/quant/        量化实验环境（见第十一节）

  scripts/bench_algorithms.py   六算法对比
  scripts/bench_final.py        多种子重复，报均值
  scripts/run_five.py           五件事一起跑
  scripts/train_tetris.py       俄罗斯方块训练
  scripts/train_game.py         小游戏训练
  scripts/train_feature.py      feature 模式训练
  scripts/train_official.py     标准方块搜权重
  scripts/render_tetris.py      渲染演示视频
  scripts/long_run.py           不设上限跑到底

  specs/                12 份 setting：
                          drone / grid / guess / queue / snake   五个示范任务（param）
                          tetris                                 俄罗斯方块（param）
                          2048 / flappy / pong                   三个小游戏（param）
                          tetris_feature                         方块 feature，起步示例
                          tetris_feature2                        方块 feature，推荐
                          tetris_official                        标准方块，9 特征自搜
  docs/USAGE.md         本文件
  docs/HANDOVER.md      交接文档
  archive/              归档数据
  out/                  视频与截图
  _gh/                  从 GitHub 下的标准方块实现（benches/official.py 依赖）
```

依赖：Python 3.12、numpy、opencv-python、Pillow。核本身只用标准库。

---

## 二、三十秒跑起来

```bash
cd "<repo>"

# 五件事一起跑（每件 200 回合）
python scripts/scripts/run_five.py 200

# 六算法对比（预算 200，3 个种子）
python bench_final.py 3 200
```

输出会直接告诉你每个任务的分数、随机基线、记忆池大小、最优段。

---

## 三、接自己的任务（三步）

本节按 `param` 模式写。`feature` 模式的接法不同（多两个方法），见第十节。

### 第 1 步：写环境

新建 `myenv.py`，实现三个方法：

```python
class MyEnv:
    def reset(self):
        # 返回初始观测，dict 就行
        return {"x": 0.0, "y": 0.0}

    def step(self, action):
        # action 是 act() 返回的字符串
        # 返回 (obs, reward, done, info)
        reward = ...
        done = ...
        return {"x": ...}, reward, done, {}

    def act(self, params, obs):
        # 参数化策略：params 来自 setting，obs 是当前观测
        # 返回动作名，例如 "left" / "pick_3" / "r2c5"
        return "left"
```

约定：
- `obs` 至少包含 `act` 需要的东西，格式随意。
- `reward` 每步给，正负都行。
- `done` 为 True 时引擎会收尾（记录 + 入池）。

### 第 2 步：写 setting

新建 `specs/myenv.json`：

```json
{
  "name": "my_task",
  "mode": "param",
  "segment_len": 8,
  "max_score": 1.0,
  "expected_steps": 60,
  "actions": {
    "A": [{"name": "noop"}],
    "G": [{"name": "noop"}],
    "C": [{"name": "noop"}],
    "T": [{"name": "noop"}],
    "X": [{"name": "noop"}]
  },
  "params": {
    "gain":  {"base": 0, "values": [0.5, 1.0, 1.5, 2.0]},
    "brake": {"base": 1, "values": [0.1, 0.3, 0.6]}
  }
}
```

字段说明：

| 字段 | 必填 | 作用 |
|---|---|---|
| `name` | 是 | 任务名，出现在报告里 |
| `mode` | 是 | `param`（推荐）或 `action` |
| `segment_len` | 是 | 每条基因取多少位，一般 8 |
| `max_score` | 是 | 归一化上限，**要比实际最好成绩高 10~40%** |
| `expected_steps` | 否 | 典型步数，用于内部节奏判断 |
| `actions` | 是 | 每个碱基对应哪些动作名 |
| `params` | param 模式必填 | 每一位碱基解码成什么参数值 |
| `gene_len` | 否 | 基因总长，默认 80，一般不用改 |
| `memory_path` | 否 | 记忆池文件，给了就跨运行复用 |

`params` 的规则：
- `base` 是段内第几位（0 起）。
- 碱基按 `A=0 G=1 C=2 T=3 X=4` 取模映射到 `values`。
- `values` 给 3~7 档就够，太多搜不动。

### 第 3 步：跑

```python
from hunter import HunterEngine, load_spec
from myenv import MyEnv

spec = load_spec("specs/myenv.json")
engine = HunterEngine(spec, seed=1)
env = MyEnv()

for episode in range(200):
    obs = env.reset()
    engine.begin_episode()
    done = False
    while not done:
        out = engine.tick(obs)                    # {"params": {...}, ...}
        action = env.act(out["params"], obs)
        obs, reward, done, _ = env.step(action)
        engine.feedback(reward, done)
    print(episode, engine.history[-1]["raw"], engine.best)
```

---

## 四、反馈怎么给（三条铁律）

引擎只有两条反馈通道：

```python
core.record(fitness)                  # 压力 / streak / 策略模式
core.reward_segment(segment, utility) # 记忆池 / 热度基因
```

`engine.feedback(reward, done)` 会自动调它们。你只需要把分数给对：

1. **两个值都是 0..1**，不是原始分。引擎内部用 `raw / max_score` 归一化。
2. **`max_score` 留余量**。猜数任务 oracle 4.13，上限设 6.0；设 4.5 会让所有高分被截成 1.0，池顶分不出优劣。
3. **评估要多回合取均值**。单回合评分噪声大，运气好的差基因会锁顶。参考 `scripts/bench_algorithms.py` 的 `evaluate3`：10 个固定种子。

---

## 五、训练和评估

### 单任务学习曲线

```bash
python scripts/scripts/run_five.py 200          # 五个任务
python scripts/scripts/train_benches/tetris.py 120 400  # 俄罗斯方块，120 局，每局 400 块
python scripts/train_game.py 2048 60    # 小游戏：2048 / flappy / pong
```

### 六算法对比

```bash
python scripts/bench_algorithms.py 40             # 单次，快
python bench_final.py 3 200    # 3 个种子重复，报均值（推荐）
```

对比对象：random / grid / hill / sa / ga / hunter。

注意：参数空间小的时候，所有算法都能到 oracle。别拿这个吹 hunter。

---

## 六、渲染视频

```bash
python scripts/scripts/render_benches/tetris.py 102 10000 60
```

参数：种子 / 最多方块数 / 帧率。输出 `out/tetris_<行数>lines_<种子>.mp4`。

帧率越高越快。每帧落一块，60fps 大约一秒 60 块。

---

## 七、记忆池

- 位置：`specs` 里 `memory_path` 指定的文件；没给就不落盘。
- 内容：`[{"segment": "AGCT...", "score": 0.87}, ...]`，按分数降序。
- 复用：同 setting 再跑会自动加载，收敛更快。
- 清空：删掉对应 JSON 文件即可。
- 池已同质化：看 `engine.state()["terrain"]`，低于 0.2 说明池里基因太像，该加参数档位或清池。

---

## 八、常见问题

**分数上不去**
1. 参数空间太小，最优解不在里面 → 加档位或换维度。
2. `max_score` 太低，高分被截断 → 抬高上限。
3. 评估噪声大 → 多回合取均值。
4. 池顶锁死 → 检查 `no_improve` 是否强制探索。

**200 回合只见到两三种参数组合**
评估里的 `random.seed()` 污染了引擎抽基因的随机数。用 `getstate/setstate` 隔离。

**某个参数永远取不到某个值**
互补链 `A↔T`、`G↔C` 是固定映射。`values` 给 5 档，或保证互补对覆盖候选。

**hunter 比 random 还差**
先看 `terrain` 和 `no_improve`。多数是反馈给错了，不是算法不行。

---

## 九、已有战绩

| 任务 | oracle | hunter |
|---|---|---|
| 空中拦截 | 2.411 | 2.408 |
| 贪吃蛇 | 4.748 | 4.747 |
| 网格寻宝 | 1.546 | 1.546 |
| 猜数 | 4.130 | 4.130 |
| 任务调度 | 5.000 | 5.000 |
| 俄罗斯方块（本地实现） | — | 1595 行 / 175,900 分（当时误判为堆死，实为截断） |
| 俄罗斯方块（GitHub 标准实现） | — | 4447 行 / 47,663,220 分 |
| 2048 | — | 平均 5228 分（最好 6720） |
| Flappy | — | 最好 22 根管道（平均 9.2） |
| Pong | — | 最好 45 次接球（平均 14.4） |

俄罗斯方块详见 `archive/2026-10-19_tetris.md`。

---

## 十、feature 模式：把策略也交给 hunter

### 10.0 三种模式怎么选

| 模式 | 谁决定动作 | 调用者写什么 | 什么时候用 |
|---|---|---|---|
| `action` | 引擎按碱基动作表选 | 动作表 | 动作少、状态简单 |
| `param` | 引擎给参数，`env.act` 用参数决策 | act 函数 | 已有靠谱的策略骨架，只调参数 |
| `feature` | 引擎枚举候选，按特征权重打分 | `candidates` + `peek` + 特征函数 | 判断好坏要看好几项，或不知道哪些信号重要 |

拿不准就从 `param` 起步；发现「分数卡在某个水平，怎么调参数都上不去」，说明缺的是特征，换 `feature`。

前两种模式（`action` / `param`）里，评分公式是调用者写死的，hunter 只调系数。

feature 模式把评分结构也交出去：**调用者只注册特征函数，hunter 自己决定用哪些、各给多大权重。**

### 10.1 什么时候用

- 一个动作的后果要算好几项才能判断好坏（消了几行、留了几个洞、平不平）
- 你不确定哪些特征重要
- 想让 hunter 自己发现"哪些信号有用"

### 10.2 三步接入

**第 1 步**：env 补两个方法。

```python
class MyEnv:
    def candidates(self):
        """当前所有合法动作，返回列表。"""
        return ["left", "right", "jump"]

    def peek(self, action):
        """预演这个动作，不改自身状态。
        返回一个 dict，特征函数从这里读数。
        返回 None 表示这个动作非法。"""
        return {"x": self.x + 1, "hp": self.hp - 3}
```

**第 2 步**：注册特征。

```python
from hunter.features import feature

@feature("hp")
def hp(state):
    return state["hp"] / 100.0

@feature("dist")
def dist(state):
    return -abs(state["x"] - 10) / 10.0
```

特征就是纯函数：`state -> float`。不用写在 class 里，模块级就行。

**第 3 步**：写 config。

```json
{
  "name": "my_task",
  "mode": "feature",
  "segment_len": 8,
  "max_score": 1.0,
  "features": {
    "hp":   {"weight": [0.0, 0.5, 1.0, 2.0, 3.0]},
    "dist": {"weight": [0.0, 0.5, 1.0, 2.0, 3.0]}
  }
}
```

训练：

```python
import myenv                       # 先 import，触发特征注册
from hunter import HunterEngine, load_spec

engine = HunterEngine(load_spec("specs/my_task.json"), seed=1)
while not done:
    action = engine.act(env)       # 引擎替你选
    obs, reward, done, _ = env.step(action)
    engine.feedback(reward, done)
```

### 10.3 特征怎么写

**要**：

- 归一化到 0~10 量级。`-holes/10` 比 `-holes` 好，不然权重档位全被一个特征吃掉。
- 一个特征只表达一件事。`holes` 别把 `height` 也算进去。
- 方向统一：**好状态给正数**。消行 +，空洞 −。
- 名字短、语义清楚。config 里要手写这些名字。

**不要**：

- 别在特征里做决策（"如果 x>3 就返回 100"），那不是特征，是策略。
- 别放量纲差异大的特征（一个 0~1，一个 0~10000），权重档位会被大的那个支配。
- 别注册几十个特征。8~12 个够，50 个档位组合数爆炸，搜不动。

### 10.4 权重档位怎么给

- 每个特征 4~6 档，**必须包含 0**（让 hunter 能关掉这个特征）。
- 档位覆盖 0 到"明显过大"，让它能试出过犹不及。
- 8 个特征 × 5 档 = 39 万种组合，够它搜。

### 10.5 训练

```
python scripts/train_feature.py <env名> <回合数> <种子数> <每局上限>
```

例：

```
python scripts/train_feature.py tetris 100 2 200
```

打印每 10 回合的分数，结束时给出最优权重和复测结果。

### 10.6 实测（俄罗斯方块）

| 方式 | 行数 / 块 |
|---|---|
| 手写 act，人工调参 | 0.40 |
| feature 模式，hunter 自搜 | 0.39 |

hunter 搜出的权重：`lines 0.0 / height 0.4 / max_h 0.4 / holes 0.0 / well_depth 0.4 / flat 0.4 / row_trans 0.4 / col_trans 0.7`

有意思的是它把 `lines`（消行）权重归零，把 `flat`（平整度）和 `well_depth`（留井）看得很重。这个结论不是人教的。

### 10.7 边界

- feature 模式还是"单步评估"：看一个动作做完之后的样子。要前瞻得自己在 `peek` 里做，或者另写。
- 特征池决定了上限。池里没有的信号，hunter 永远发现不了。
- 特征写错（量纲、方向、共线）会让它搜得很慢，甚至搜出反直觉的权重。写之前先手算两个例子。

### 10.8 具身智能

同一套接口能直接用在机器人 / 无人机这类连续控制上：

- `candidates()` 返回离散化后的控制量组合（舵机角、油门档、转向档）
- `peek(action)` 跑一步物理模型，返回预测状态
- 特征：`距离`、`朝向误差`、`碰撞风险`、`能量`、`平稳度`

act 里一行决策都不用写，权重全归 hunter。

---

## 十一、怎么给题：让 hunter 自己决定权重的正确姿势

> 2026-10-19 金融实验的教训。这一节讲的是「怎么让它发挥最大能力」，
> 不谈具体行业。同一套引擎，方块里 4447 行，金融里跑输基准，差别全在这里。

### 11.1 它是评估器，不是预测器

hunter 的核心动作只有一个——**给候选打分，挑最高分**：

```python
value = score(state, weights)
best  = argmax(score(peek(a)) for a in candidates())
```

所以它要的是 `score(state)`：一个「这个状态好不好」的打分函数。

- 方块：`score(落完的棋盘)` → 挑最高分的落点
- 无人机：`score(预演后的姿态)` → 挑最高分的舵机量
- 量化（我写错的）：`score(历史指标)` → **预测明天涨跌**

区别在于：前者评估的是**已经确定的状态**，后者预测的是**还没发生的未来**。

状态确定 → 函数关系稳定 → 搜索有解
未来不确定 → 函数关系漂移 → 搜索只能背噪声

### 11.2 四条给题规矩

**① 空间控制在 10^6 以内**

实测成功案例：

| 任务 | 模式 | 维度 | 空间 | 结果 |
|---|---|---|---|---|
| 猜数 / 贪吃蛇 / 寻宝 / 调度 / 队列 | param | 1–4 | 10^2 | 全达 oracle |
| 无人机 | drone | 8 段 | 3.9×10^5 | 击敌 15/20 |
| 俄罗斯方块（本地 `benches/tetris.py`） | feature | 8 | 3.9×10^5 | 78 行（打平手工调参） |
| 俄罗斯方块（GitHub 标准实现） | feature | 9 | 2.0×10^6 | **4447 行 / 47,663,220 分** |

失败案例：

| 任务 | 模式 | 维度 | 空间 | 结果 |
|---|---|---|---|---|
| 量化（人挑 18 特征） | param | 18 | 1.6×10^15 | 88% 跑赢（人挑的特征，不算） |
| 量化（全 51 特征） | param | 51 | 10^43 | 训练 +289.9%，测试 +10.96% |

**分界线大约在 10^6。** 超过这个量级，每代只变异一两位的搜索方式摸不到边。

**② 特征是测量值，不是估计值**

方块的特征：孔数、堆高、井深、行变换——**棋盘的精确计数**，同一个棋盘算一百次都一样。

量化的特征：RSI、MACD、布林带——**从历史价格估计出来的**，参数一改、窗口一挪，值就变。

它搜量化权重时方向全对（`mom*` 全负、`boll*` 全负、`close_pos*` 全负——反转 + 买低位），说明它理解了这个意思。但 44 个估计值乘 44 个系数，噪声盖过信号。

**③ 反馈要即时且低噪声**

方块：落完立刻知道消了几行、留了几个洞。一步一反馈。
量化：今天买，收益要等 N 天，中间还有波动。

延迟反馈 + 高噪声 = 学不到东西。这是评估函数的固有难度，不是接口问题。

**④ 符号先验证**

方块第一次接入时特征全带错符号，所有基因活不过 13–15 块；翻正后同一份代码跑到 291 行，最终 9752 行。

量化里：`mom5 +1`（追涨）全样本 -8.56%，`mom5 -1`（反转）+76.79%。

写特征之前，手工算一个「明显该好」的样本，确认符号。

### 11.3 怎么让它做你想让它做的事

**把「预测」改写成「评估」。**

假设想让 hunter 做交易。错误写法：

```python
# 错：让它预测未来
w = hunter.search(51 个权重)
score = dot(w, 历史指标)
if score > 0: 买
```

正确写法：

```python
# 对：让它评估状态
def candidates():
    return ["空仓", "半仓", "满仓"]

def peek(action):
    return 预演这个动作之后的持仓状态      # 确定的，能立刻算

@feature("drawdown")
def drawdown(state):
    return -state.回撤

@feature("health")
def health(state):
    return state.仓位健康度

# hunter 搜的是"什么样的状态算好"，不是"明天涨不涨"
```

维度从 51 降到 5–8，空间从 10^43 降到 10^5，反馈变成即时（预演状态立刻可算）。

同样的改写适用于任何任务：

| 你想让它做的 | 错误问法（预测） | 正确问法（评估） |
|---|---|---|
| 玩游戏 | 预测下一步会发生什么 | 评估每个可行动作做完后的局面 |
| 控制机器人 | 预测轨迹终点 | 评估每个控制量执行后的姿态 |
| 交易 | 预测明天涨跌 | 评估当前持仓状态好不好 |
| 调度 | 预测任务完成时间 | 评估每个调度方案当前的负载 |

**判断标准：`peek` 出来的状态，是不是确定的？**
- 确定（棋盘、物理模型）→ 评估题，hunter 强
- 不确定（市场、人群）→ 预测题，hunter 弱

### 11.4 发挥最大能力的清单

1. **空间 ≤ 10^6**：维度 × 档位控制在百万级
2. **特征精确**：能算准的才进池，估计值少放
3. **反馈即时**：一步一反馈，多回合平均降噪
4. **符号验证**：先手算一个样本确认方向
5. **单步评估**：`peek` 里做一步预演，别做多步前瞻
6. **不给答案**：不替它挑特征——要么全池配稀疏表示，要么低维全池
7. **样本外验证**：训练段和测试段严格分开
8. **读它的权重**：方向对、成绩差 = 表示问题；方向错 = 特征或奖励有问题

### 11.5 一句话

**给状态打分，别让它猜未来。**
