# Hunter

**A generic evolutionary solver for sequential decision problems.**

Hunter searches for a *program* (a plan, a lookup table, or a set of evaluation
weights) that maximises a score returned by an environment. It does not need
gradients, a differentiable model, or hand-written heuristics. You describe the
task in JSON; Hunter searches for a solution and validates it.

---

## What it does

- **Search over programs, not parameters.** A gene is decoded into an executable
  program (a fixed-length plan, a state-to-action table, or a feature-weight
  vector) and evaluated by running the environment.
- **Deterministic.** The same seed and the same specification produce the same
  result.
- **Contract-driven.** Any environment that implements `reset()` / `apply(action)`
  / `situation()` / `score()` can be plugged in.
- **Validated end-to-end.** Every run ends with a shortlist re-test on separate
  seeds, so a single lucky episode does not become the reported result.
- **Included benchmarks.** 35 built-in tasks (board games, arcade games,
  scheduling, control), all reachable with the same core.

## Install

```bash
python -m pip install -r requirements.txt
```

Python 3.10+. `numpy` is required; `taichi` is optional and used only for
parallel score evaluation.

## Quick start

```bash
# list built-in tasks
python -m hunter list

# solve a built-in task
python -m hunter tetris

# solve any task described by a JSON spec
python -m hunter run specs/easy/tetris.json
```

A specification is small:

```json
{
  "name": "tetris",
  "renderer": "plan",
  "steps": 40,
  "slots": {
    "A": [{"op": "left"}, {"op": "right"}],
    "G": [{"op": "rotate"}, {"op": "drop"}]
  }
}
```

## Two interfaces

| Interface | Gene means | Best for |
|---|---|---|
| **Payload** (`renderer`: `plan` / `table`) | an executable program | discrete actions, short horizons, exact sequences |
| **Features** | weights of a linear evaluation function | long horizons, continuous state, real-time control |

The payload interface is the primary one. The feature interface is kept as a
second, independent path for problems where a one-step greedy evaluator is the
natural formulation.

## Repository layout

```
hunter/        search core, program decoders, parallel evaluation
benches/       environments (board, arcade, simulation)
specs/         JSON task definitions
scripts/       training / evaluation entry points
examples/      minimal usage examples
docs/          reference documentation (Chinese)
```

## Verification

```bash
python scripts/check_all.py
```

The script reports pass/fail per task. A failing task is reported as a warning
and does not abort the run.

## License

MIT. See `LICENSE`.

---

# 中文说明

**Hunter：面向序列决策的通用演化求解器。**

Hunter 不训练参数，而是搜索一段**程序**——定长计划、状态动作表，或一组评估权重。
只要环境提供 `reset()` / `apply(action)` / `situation()` / `score()` 四个接口，
就可以接入 Hunter；你只需要用 JSON 描述任务，剩下交给搜索。

## 特点

- **搜索程序而不是参数**：基因解码成可执行程序，直接在环境里跑，用得分当判据。
- **确定性**：同一随机种子、同一份规格，结果可复现。
- **契约驱动**：环境只认四个方法，不依赖具体游戏类型。
- **结果经过复核**：训练结束后用独立种子复赛，避免单次幸运局被当成结论。
- **自带基准**：35 个内置任务（棋类、街机、调度、控制），同一套内核全部可达。

## 安装

```bash
python -m pip install -r requirements.txt
```

Python 3.10 及以上。必需 `numpy`；`taichi` 为可选项，仅用于并行评分。

## 快速开始

```bash
python -m hunter list                       # 列出内置任务
python -m hunter tetris                     # 求解内置任务
python -m hunter run specs/easy/tetris.json # 用 JSON 规格求解
```

## 两种接口

| 接口 | 基因含义 | 适用场景 |
|---|---|---|
| **Payload**（`plan` / `table`） | 一段可执行程序 | 离散动作、短程、精确序列 |
| **Features** | 线性评估函数的权重 | 长程、连续状态、实时控制 |

Payload 是主接口；Features 作为第二条独立路径保留，适合「一步贪心评估」就是自然形式的问题。

## 目录

```
hunter/        搜索内核、程序解码、并行评估
benches/       环境（棋类、街机、仿真）
specs/         JSON 任务定义
scripts/       训练与评估入口
examples/      最小示例
docs/          参考文档（中文）
```

## 验证

```bash
python scripts/check_all.py
```

逐项输出通过/未通过。未通过只作警告，不中断运行。

## 许可

MIT，见 `LICENSE`。
