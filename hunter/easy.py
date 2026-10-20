# -*- coding: utf-8 -*-
""

import importlib
import inspect
import json
import math
import os
import random
import statistics
import sys
import time

from .api import HunterEngine
from .core import BASES

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


ALIASES = {
    "tetris":          "benches.official:OfficialTetris",
    "tetris_official": "benches.official:OfficialTetris",
    "tetris_local":    "benches.tetris:TetrisEnv",
    "方块":            "benches.official:OfficialTetris",
    "2048":            "benches.games:Game2048",
    "game2048":        "benches.games:Game2048",
    "flappy":          "benches.games:Flappy",
    "pong":            "benches.games:Pong",
    "guess":           "benches.basics:GuessEnv",
    "snake":           "benches.basics:SnakeEnv",
    "drone":           "benches.basics:DroneEnv",
    "grid":            "benches.basics:GridHuntEnv",
    "queue":           "benches.basics:QueueEnv",
    
    "pacman":          "benches.thirdparty.pacman_env:PacmanEnv",
    "sokoban":         "benches.thirdparty.sokoban_env:SokobanEnv",
    "pvz":             "benches.thirdparty.pvz_env:PvZEnv",
    "rts":             "benches.thirdparty.rts_env:RTSEnv",
}

DEFAULT_TIERS = [0.0, 0.5, 1.0, 2.0, 4.0]     
SCORE_ATTRS = ("score", "lines", "passed", "hits", "steps", "total")


def _clamp(x, lo=0.0, hi=1.0):
    return max(lo, min(hi, x))


def _num(x):
    ""
    if isinstance(x, float) and not x.is_integer():
        return "{:,.2f}".format(x)
    return "{:,}".format(int(x))


# ══════════════════════════════════════════════════════════

# ══════════════════════════════════════════════════════════
def load_easy(source):
    ""
    if isinstance(source, dict):
        return dict(source)
    path = os.path.abspath(source)
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    data.setdefault("_path", path)
    return data


def _import_env(target):
    if ":" not in target:
        raise ValueError("环境要写成 '模块:类'，例如 benches.official:OfficialTetris")
    module_name, class_name = target.split(":", 1)
    module = importlib.import_module(module_name)
    return getattr(module, class_name)


# ══════════════════════════════════════════════════════════

# ══════════════════════════════════════════════════════════
class EasyTask:
    def __init__(self, source, episodes=None, seed=7, verbose=True,
                 sign_check=None, out_dir=None):
        cfg = load_easy(source)
        self.name = str(cfg.get("task") or cfg.get("name") or "task")
        
        if not any(cfg.get(k) for k in ("features", "params", "actions")):
            builtin = os.path.join(ROOT, "specs", "easy", "%s.json" % self.name)
            if os.path.exists(builtin) and os.path.abspath(builtin) != cfg.get("_path"):
                with open(builtin, encoding="utf-8") as handle:
                    merged = json.load(handle)
                merged.update(cfg)
                cfg = merged
        self.cfg = cfg
        self.seed = int(seed if seed is not None else cfg.get("seed", 7))
        self.verbose = verbose
        self.target = float(cfg.get("target") or 0.0)
        self.episodes = int(episodes or cfg.get("episodes") or 60)
        self.n_eval = int(cfg.get("seeds", 2))          
        self.n_test = int(cfg.get("test_seeds", 3))     
        self.max_steps = int(cfg.get("max_steps", 20000))
        self.sign_steps = int(cfg.get("sign_steps", 200))
        self.probe_runs = int(cfg.get("probe_runs", 6))
        self.n_final = int(cfg.get("finalists", 3))     
        self.grace = int(cfg.get("grace", 5))           
        self.scale_mode = str(cfg.get("scale", "auto"))
        self.do_sign = bool(cfg.get("sign_check", True) if sign_check is None else sign_check)
        self.do_memory = bool(cfg.get("memory", False))
        self.stop_on_target = bool(cfg.get("stop_on_target", True))
        self.env_args = dict(cfg.get("env_args") or {})
        self.score_key = cfg.get("score")
        self.log_every = int(cfg.get("log_every", 10))
        self.probe_notes = []

        
        target = cfg.get("env") or ALIASES.get(self.name)
        if not target:
            raise ValueError("不认识的 task：%r。用 env 写 '模块:类'，或换内置别名 %s"
                             % (self.name, sorted(ALIASES)))
        self.env_target = target
        self.env_cls = _import_env(target)
        self.env_seed_arg = "seed" if "seed" in inspect.signature(
            self.env_cls.__init__).parameters else None

        
        if cfg.get("features"):
            self.mode = "feature"
        elif cfg.get("params"):
            self.mode = "param"
        elif cfg.get("actions"):
            self.mode = "action"
        else:
            
            if hasattr(self.env_cls, "candidates") and hasattr(self.env_cls, "peek"):
                self.mode = "feature"
                self.names = []
            else:
                raise ValueError("%s 不是 feature 环境，JSON 里要写 params 或 actions"
                                 % self.name)

        if self.mode == "feature":
            self._parse_features(cfg.get("features") or self._auto_features())
        elif self.mode == "param":
            self._parse_params(cfg.get("params") or {})
        else:
            self.actions = cfg.get("actions") or {}

        
        self.scale = "linear"
        self.max_score = 1.0
        self.probe_best = 0.0
        self.probe_median = 0.0
        self.best_raw = 0.0
        self.raw_of = {}
        self.curve = []
        self.elapsed = 0.0

        
        base_dir = out_dir or cfg.get("out_dir") or os.path.join(ROOT, "out", "easy")
        self.out_dir = base_dir
        self.out_path = os.path.join(base_dir, "%s.best.json" % self._safe(self.name))

        self.engine = None

    
    def _auto_features(self):
        ""
        from . import features as registry
        mod = self.env_target.split(":")[0]
        names = [n for n in registry.names() if registry.get(n).__module__ == mod]
        if not names:
            raise ValueError(
                "环境 %s 没有注册任何特征，也不是 param/action 环境。\n"
                "JSON 里加一句 features（或 params）。已注册：%s"
                % (self.env_target, registry.names()))
        return names

    def _parse_features(self, raw):
        self.tiers = {}
        if isinstance(raw, dict):
            items = raw.items()
        else:
            items = ((n, None) for n in raw)
        self.names = []
        for name, spec in items:
            self.names.append(name)
            if spec is None:
                self.tiers[name] = list(DEFAULT_TIERS)
            elif isinstance(spec, (int, float)):
                self.tiers[name] = [v * float(spec) for v in DEFAULT_TIERS]
            else:
                tiers = list(spec)
                if 0.0 not in tiers:
                    tiers = [0.0] + tiers          
                self.tiers[name] = tiers
        if not self.names:
            raise ValueError("features 不能为空")
        from . import features as registry
        missing = [n for n in self.names if not registry.has(n)]
        if missing:
            raise ValueError(
                "特征没注册：%s\n已注册：%s\n"
                "特征由环境模块用 @feature 注册，确认 env 写对了（当前 %s）"
                % (missing, registry.names(), self.env_target))
        owners = sorted({registry.get(n).__module__ for n in self.names})
        if len(owners) > 1:
            self.probe_notes.append("注意：特征来自多个模块 %s，同名可能被覆盖" % owners)
        space = 1
        for name in self.names:
            space *= max(1, len(self.tiers[name]))
        if space > 2000000:
            self.probe_notes.append(
                "提示：%d 维 × 档位 = %.1e 种组合，超过 10^6 后每代只动一两位摸不到边，建议砍到 9 维以内"
                % (len(self.names), space))

    def _parse_params(self, raw):
        self.param_table = {}
        for i, (name, values) in enumerate(raw.items()):
            if isinstance(values, dict):
                values = values.get("values", [0, 1])
            values = list(values)
            if not values:
                raise ValueError("参数 %s 的档位为空" % name)
            self.param_table[name] = {"base": i, "values": values}
        if not self.param_table:
            raise ValueError("params 不能为空")

    @staticmethod
    def _safe(text):
        return "".join(c if c.isalnum() or c in "-_." else "_" for c in str(text))

    
    def build_spec(self):
        if self.mode == "feature":
            spec = {
                "name": self.name,
                "mode": "feature",
                "segment_len": max(1, len(self.names)),
                "max_score": 1.0,
                "features": {n: {"weight": list(self.tiers[n])} for n in self.names},
            }
        elif self.mode == "param":
            spec = {
                "name": self.name,
                "mode": "param",
                "segment_len": max(8, len(self.param_table)),
                "max_score": 1.0,
                "actions": {b: [{"name": "noop"}] for b in BASES},
                "params": self.param_table,
            }
        else:
            spec = {
                "name": self.name,
                "mode": "action",
                "segment_len": int(self.cfg.get("segment_len", 8)),
                "max_score": float(self.cfg.get("max_score", 100.0)),
                "actions": self.actions,
            }
        self.spec = spec
        return spec

    # ══════════════════════════════════════════════════════
    
    # ══════════════════════════════════════════════════════
    def _make_env(self, seed):
        kwargs = dict(self.env_args)
        if self.env_seed_arg:
            kwargs.setdefault(self.env_seed_arg, seed)
        env = self.env_cls(**kwargs)
        
        env._easy_obs = env.reset() if hasattr(env, "reset") else None
        return env

    @staticmethod
    def _unpack(out):
        ""
        if isinstance(out, bool):
            return out, 0.0, {}
        if isinstance(out, tuple) and len(out) >= 3:
            info = out[3] if len(out) > 3 and isinstance(out[3], dict) else {}
            return bool(out[2]), float(out[1]), info
        return bool(out), 0.0, {}

    def _score_of(self, env, info=None):
        if self.score_key:
            if hasattr(env, self.score_key):
                return float(getattr(env, self.score_key))
            if info and self.score_key in info:
                return float(info[self.score_key])
        for key in SCORE_ATTRS:
            if hasattr(env, key):
                return float(getattr(env, key))
        if info:
            for key in SCORE_ATTRS:
                if key in info:
                    return float(info[key])
        return None

    def _episode(self, seed, weights=None, params=None, cap=None):
        ""
        cap = cap or self.max_steps
        state = random.getstate()
        random.seed(seed)
        try:
            env = self._make_env(seed)
            total, info, steps = 0.0, {}, 0
            if self.mode == "feature":
                w = weights or {}
                while steps < cap:
                    action = self.engine.policy.choose(env, w)
                    if action is None:
                        break
                    done, reward, info = self._unpack(env.step(action))
                    total += reward
                    steps += 1
                    if done:
                        break
            elif self.mode == "param":
                obs = getattr(env, "_easy_obs", None)
                if obs is None:
                    obs = env.reset()
                while steps < cap:
                    action = env.act(params or {}, obs)
                    out = env.step(action)
                    if isinstance(out, tuple) and len(out) >= 3:
                        obs, reward, done, info = out[0], out[1], out[2], \
                            (out[3] if len(out) > 3 and isinstance(out[3], dict) else {})
                    else:
                        done, reward = bool(out), 0.0
                    total += reward
                    steps += 1
                    if done:
                        break
            else:
                while steps < cap:
                    out = self.engine.tick()
                    action = out["action"]
                    done, reward, info = self._unpack(env.step(action))
                    total += reward
                    steps += 1
                    if done:
                        break
            score = self._score_of(env, info)
            self.last_detail = {"lines": getattr(env, "lines", None),
                                "pieces": getattr(env, "pieces", None),
                                "steps": steps}
            return (score if score is not None else total), total
        finally:
            random.setstate(state)

    
    def _denom(self, m):
        m = max(float(m), 1e-9)
        return math.log1p(m) if self.scale == "log" else m

    def _utility(self, raw):
        raw = max(0.0, float(raw))
        return _clamp(self._denom(raw) / self._denom(self.max_score))

    def _raise_max(self, raw):
        ""
        want = max(raw * 1.35, self.probe_best * 1.35, self.target, 1e-6)
        if want <= self.max_score * 1.001:
            return False
        old = self.max_score
        self.max_score = want
        factor = self._denom(old) / self._denom(want)
        core = self.engine.core
        if core.memory_pool:
            core.memory_pool = [(s, _clamp(u * factor)) for s, u in core.memory_pool]
            core.hot_genes = core.memory_pool[:core.hot_capacity]
        core.best_utility = _clamp(core.best_utility * factor)
        return True

    # ══════════════════════════════════════════════════════
    
    # ══════════════════════════════════════════════════════
    def probe(self):
        raws = []
        probe_seed = self.seed * 7919 + 1
        draws = []
        if self.mode == "feature":
            
            rng = random.Random(self.seed)
            for _ in range(self.probe_runs):
                draws.append({n: rng.choice(self.tiers[n]) for n in self.names})
        elif self.mode == "param":
            rng = random.Random(self.seed)
            for _ in range(self.probe_runs):
                draws.append({n: rng.choice(item["values"])
                              for n, item in self.param_table.items()})
        else:
            draws = [{}] * self.probe_runs

        
        self.build_spec()
        self.engine = HunterEngine(self.spec, seed=self.seed)
        for i, w in enumerate(draws):
            score, _ = self._episode(probe_seed + i, weights=w,
                                     params=w if self.mode == "param" else None)
            raws.append(float(score))
        raws.sort()
        self.probe_best = raws[-1] if raws else 0.0
        self.probe_median = statistics.median(raws) if raws else 0.0

        if self.scale_mode in ("linear", "log"):
            self.scale = self.scale_mode
        else:
            
            denom = self.probe_median if self.probe_median > 0 else 1.0
            self.scale = "log" if (self.probe_best / denom) >= 30 else "linear"

        self.max_score = max(self.probe_best * 1.35, self.target, 1e-6)
        self.best_raw = 0.0
        self.probe_notes.append(
            "试跑 %d 次：最好 %s / 中位 %s → 尺度 %s，满分 %s"
            % (len(raws), _num(self.probe_best), _num(self.probe_median),
               self.scale, _num(round(self.max_score, 4))))
        if self.verbose:
            print("[标定] " + self.probe_notes[-1], flush=True)
        return raws

    # ══════════════════════════════════════════════════════
    
    # ══════════════════════════════════════════════════════
    def sign_check(self):
        if self.mode != "feature" or not self.do_sign:
            return
        
        
        seeds = [self.seed * 31 + 5, self.seed * 31 + 6]
        flips, notes = [], []
        for name in self.names:
            plus = self._eval_raw({n: 1.0 if n == name else 0.0 for n in self.names},
                                  seeds, cap=self.sign_steps)
            minus = self._eval_raw({n: -1.0 if n == name else 0.0 for n in self.names},
                                   seeds, cap=self.sign_steps)
            if minus > plus * 1.10 and abs(minus - plus) > 1e-9:
                self.tiers[name] = [-v for v in self.tiers[name]]
                flips.append(name)
            notes.append("%s %s" % (name, "←翻" if name in flips else "ok"))
        msg = "方向核对 %d 个特征：翻了 %d 个%s" % (
            len(self.names), len(flips), ("（%s）" % ", ".join(flips)) if flips else "")
        self.probe_notes.append(msg)
        if self.verbose:
            print("[符号] " + msg, flush=True)

    def _eval_raw(self, weights, seeds, cap=None):
        scores = []
        for s in seeds:
            score, _ = self._episode(s, weights=weights, cap=cap)
            scores.append(float(score))
        return sum(scores) / max(1, len(scores))

    # ══════════════════════════════════════════════════════
    
    # ══════════════════════════════════════════════════════
    def _eval_seeds(self):
        return [self.seed * 100000 + i for i in range(self.n_eval)]

    def _val_seeds(self):
        return [self.seed * 500000 + 50 + i for i in range(self.n_eval)]

    def _test_seeds(self):
        return [self.seed * 900000 + 100 + i for i in range(self.n_test)]

    def _decode(self, seg):
        ""
        if self.mode == "feature":
            return self.engine.policy.weights(seg), None
        if self.mode == "param":
            out = {}
            for name, item in self.param_table.items():
                idx = int(item.get("base", 0)) % max(1, len(seg))
                values = item["values"]
                out[name] = values[BASES.index(seg[idx]) % len(values)]
            return None, out
        return None, None

    def _run_with(self, seg, seeds, cap=None):
        weights, params = self._decode(seg)
        scores = []
        for s in seeds:
            score, _ = self._episode(s, weights=weights, params=params, cap=cap)
            scores.append(float(score))
        return scores, sum(scores) / max(1, len(scores))

    def train(self):
        self.build_spec()
        self.spec["max_score"] = self.max_score
        self.engine = HunterEngine(self.spec, seed=self.seed)
        self.engine.max_score = self.max_score
        if self.do_memory:
            self._load_memory()

        core = self.engine.core
        seeds = self._eval_seeds()
        best = {"raw": -1e18, "weights": None, "params": None, "segment": None}
        hits, first_hit = 0, None
        t0 = time.time()

        for ep in range(1, self.episodes + 1):
            seg = self.engine.begin_episode()
            if self.mode == "feature":
                weights = self.engine.policy.weights(seg)
                params = None
                scores = [self._episode(s, weights=weights)[0] for s in seeds]
            elif self.mode == "param":
                params = self.engine.decode_params()
                weights = None
                scores = [self._episode(s, params=params)[0] for s in seeds]
            else:
                weights = params = None
                scores = [self._episode(s)[0] for s in seeds]

            avg = sum(scores) / len(scores)
            self._raise_max(avg)
            u = self._utility(avg)
            self.raw_of[seg] = max(self.raw_of.get(seg, 0.0), avg)
            core.record(u)                    
            core.reward_segment(seg, u)       
            if self.do_memory:
                self._save_memory()

            improved = avg > best["raw"]
            if improved:
                best = {"raw": avg, "weights": weights, "params": params,
                        "segment": seg, "scores": scores}
            self.best_raw = max(self.best_raw, avg)
            self.curve.append(round(avg, 4))

            if self.verbose and (improved or ep % self.log_every == 0):
                st = core.snapshot()
                print("  第 %3d 局  本局 %s  最好 %s  池 %d  地形 %.2f  %s"
                      % (ep, _num(avg), _num(best["raw"]), st["memory"],
                         st["terrain"], st["mode"]), flush=True)
            
            if self.target and avg >= self.target:
                hits += 1
                if first_hit is None:
                    first_hit = ep
            if self.stop_on_target and first_hit is not None and \
                    (hits >= 2 or ep - first_hit >= self.grace):
                if self.verbose:
                    print("  过满分线 %d 次（首次第 %d 局），停。" % (hits, first_hit),
                          flush=True)
                break

        self.elapsed = time.time() - t0
        self.best = self._shortlist(best) if self.n_final > 0 else best
        return self.best

    def _shortlist(self, best):
        ""
        segs, seen = [], set()
        if best.get("segment"):
            segs.append(best["segment"])
        for seg, _u in self.engine.core.memory_pool[:self.n_final]:
            if seg not in seen:
                segs.append(seg)
        cands = []
        for seg in segs:
            if seg in seen:
                continue
            seen.add(seg)
            scores, avg = self._run_with(seg, self._val_seeds())
            cands.append({"segment": seg, "scores": scores, "raw": avg})
        cands.sort(key=lambda r: -r["raw"])
        top = cands[0]
        weights, params = self._decode(top["segment"])
        if self.verbose:
            print("[复赛] %d 个候选·验证种子重跑：%s → 入选 %s"
                  % (len(cands),
                     " / ".join(_num(round(c["raw"], 2)) for c in cands),
                     _num(top["raw"])), flush=True)
        return {"raw": top["raw"], "weights": weights, "params": params,
                "segment": top["segment"], "scores": top["scores"],
                "train_raw": best["raw"], "cands": cands}

    
    def _memory_path(self):
        return os.path.join(self.out_dir, "mem", "%s.json" % self._safe(self.name))

    def _load_memory(self):
        path = self._memory_path()
        if os.path.exists(path):
            if self.engine.core.load(path):
                
                core = self.engine.core
                core.memory_pool = [(s, self._utility(u * self.max_score))
                                    for s, u in core.memory_pool]
                core.hot_genes = core.memory_pool[:core.hot_capacity]
                core.best_utility = max([u for _, u in core.memory_pool] or [0.0])

    def _save_memory(self):
        path = self._memory_path()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        core = self.engine.core
        
        payload = {
            "scale": self.scale,
            "max_score": self.max_score,
            "pool": [{"segment": s, "raw": self.raw_of.get(s, 0.0)}
                     for s, _ in core.memory_pool],
            "pressure": core.pressure,
        }
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
        os.replace(tmp, path)

    # ══════════════════════════════════════════════════════
    
    # ══════════════════════════════════════════════════════
    def retest(self, seeds=None):
        seeds = seeds or self._test_seeds()
        rows, lines = [], []
        for s in seeds:
            if self.mode == "feature":
                score, _ = self._episode(s, weights=self.best["weights"])
            elif self.mode == "param":
                score, _ = self._episode(s, params=self.best["params"])
            else:
                score, _ = self._episode(s)
            rows.append(float(score))
            if getattr(self, "last_detail", {}).get("lines") is not None:
                lines.append(self.last_detail["lines"])
        avg = sum(rows) / len(rows)
        self.retest_lines = lines
        if self.verbose:
            extra = (" ｜ 行数 " + ", ".join(str(x) for x in lines)) if lines else ""
            print("[复测] %d 个新种子：%s ｜ 均值 %s%s"
                  % (len(rows), ", ".join(_num(r) for r in rows), _num(avg), extra),
                  flush=True)
        return rows, avg

    # ══════════════════════════════════════════════════════
    
    # ══════════════════════════════════════════════════════
    def run(self):
        t_all = time.time()
        if self.verbose:
            print("[识别] 任务 %s ｜ 模式 %s ｜ 环境 %s ｜ 维度 %d ｜ 回合 %d ｜ 每回合 %d 种子"
                  % (self.name, self.mode, self.env_target,
                     len(self.names) if self.mode == "feature" else
                     (len(self.param_table) if self.mode == "param" else len(self.actions)),
                     self.episodes, self.n_eval), flush=True)
        self.probe()
        self.sign_check()
        self.train()
        train_elapsed = self.elapsed
        rows, avg = self.retest()
        self.elapsed = time.time() - t_all          
        report = self._report(rows, avg)
        report["train_elapsed"] = round(train_elapsed, 1)
        self.save(report)
        if self.verbose:
            self._print_report(report)
        return report

    def _report(self, rows, avg):
        core = self.engine.core
        return {
            "task": self.name,
            "mode": self.mode,
            "env": self.env_target,
            "env_args": self.env_args,
            "seed": self.seed,
            "features": self.names if self.mode == "feature" else None,
            "weights": self.best.get("weights"),
            "params": self.best.get("params"),
            "segment": self.best.get("segment"),
            "best_raw": self.best.get("raw"),
            "train_raw": self.best.get("train_raw", self.best.get("raw")),
            "train_scores": self.best.get("scores"),
            "retest_scores": rows,
            "retest_lines": getattr(self, "retest_lines", None),
            "retest_avg": avg,
            "scale": self.scale,
            "max_score": round(self.max_score, 6),
            "episodes": len(self.curve),
            "curve": self.curve,
            "terrain": round(core.terrain_coef(), 3),
            "memory": len(core.memory_pool),
            "notes": self.probe_notes,
            "elapsed": round(self.elapsed, 1),
            "spec": self.spec,
        }

    def save(self, report):
        os.makedirs(self.out_dir, exist_ok=True)
        payload = dict(report)
        payload["spec"] = dict(report["spec"])
        payload["spec"]["max_score"] = report["max_score"]
        with open(self.out_path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)

    def _print_report(self, report):
        print("")
        print("─" * 56)
        print("任务 %s ｜ %d 局 ｜ 训练 %.1fs ｜ 全程 %.1fs ｜ 地形 %.2f ｜ 池 %d"
              % (report["task"], report["episodes"],
                 report.get("train_elapsed", report["elapsed"]),
                 report["elapsed"], report["terrain"], report["memory"]))
        if report["mode"] == "feature":
            weights = report["weights"] or {}
            print("权重 " + "  ".join("%s=%.2f" % (k, v) for k, v in weights.items()))
        elif report["mode"] == "param":
            print("参数 " + json.dumps(report["params"], ensure_ascii=False))
        print("训练最好 %s ｜ 复赛(验证种子) %s ｜ 复测(新种子) %s"
              % (_num(report.get("train_raw", report["best_raw"])),
                 _num(report["best_raw"]),
                 _num(round(report["retest_avg"], 4))))
        print("存档 " + self.out_path)


# ══════════════════════════════════════════════════════════

# ══════════════════════════════════════════════════════════
def solve(source, episodes=None, seed=7, verbose=True, sign_check=None, out_dir=None):
    ""
    task = EasyTask(source, episodes=episodes, seed=seed, verbose=verbose,
                    sign_check=sign_check, out_dir=out_dir)
    return task.run()


def watch(source, seed=9001, verbose=True, cap=None):
    ""
    data = load_easy(source)
    if "weights" in data and "spec" in data:
        spec = data["spec"]
        env_cls = _import_env(data["env"])
        env_args = dict(data.get("env_args") or {})
        mode = data.get("mode", "feature")
        task = EasyTask.__new__(EasyTask)
        task.name, task.mode, task.spec = data.get("task", "task"), mode, spec
        task.env_cls, task.env_args = env_cls, env_args
        task.max_steps = int(cap or 20000)
        task.score_key = None
        task.env_seed_arg = "seed" if "seed" in inspect.signature(
            env_cls.__init__).parameters else None
        task.engine = HunterEngine(spec, seed=seed)
        weights = data.get("weights") or {}
        params = data.get("params") or {}
        return _watch_run(task, weights, params, seed, verbose)

    cfg = dict(data)
    cfg.setdefault("seed", seed)
    task = EasyTask(cfg, verbose=verbose)
    report_path = task.out_path
    if os.path.exists(report_path):
        return watch(report_path, seed=seed, verbose=verbose, cap=cap)
    raise FileNotFoundError("还没有最优权重：%s。先跑 solve()。" % report_path)


def _watch_run(task, weights, params, seed, verbose):
    state = random.getstate()
    random.seed(seed)
    t0 = time.time()
    try:
        env = task._make_env(seed)
        obs = None
        if task.mode == "param":
            obs = getattr(env, "_easy_obs", None)
            if obs is None:
                obs = env.reset()
        steps, total, info = 0, 0.0, {}
        report_every = 500
        while steps < task.max_steps:
            if task.mode == "feature":
                action = task.engine.policy.choose(env, weights)
            elif task.mode == "param":
                action = env.act(params, obs)
            else:
                action = task.engine.tick()["action"]
            if action is None:
                break
            out = env.step(action)
            if isinstance(out, tuple) and len(out) >= 3:
                obs, reward, done = out[0], float(out[1]), bool(out[2])
                info = out[3] if len(out) > 3 and isinstance(out[3], dict) else {}
            else:
                done, reward = bool(out), 0.0
            total += reward
            steps += 1
            if verbose and steps % report_every == 0:
                score = task._score_of(env, info)
                print("  %5d 步  分数 %s  %.0fs"
                      % (steps, _num(score if score is not None else total),
                         time.time() - t0), flush=True)
            if done:
                break
        score = task._score_of(env, info)
        if verbose:
            print("结束：%d 步 ｜ 分数 %s ｜ %.1fs"
                  % (steps, _num(score if score is not None else total),
                     time.time() - t0), flush=True)
        return score if score is not None else total
    finally:
        random.setstate(state)
