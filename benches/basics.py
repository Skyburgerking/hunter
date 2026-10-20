# -*- coding: utf-8 -*-
""

import math
import random


class DroneEnv:
    ""
    name = "drone_intercept"

    def reset(self):
        self.pos = [0.0, 0.0]
        self.goal = [8.0, 6.0]
        self.goal_vel = [0.0, 0.0]
        self.t = 0
        self.prev = math.hypot(8.0, 6.0)
        return {"pos": list(self.pos), "goal": list(self.goal),
                "goal_vel": list(self.goal_vel)}

    def step(self, action):
        self.t += 1
        vx = random.uniform(-0.6, 0.6)
        vy = random.uniform(-0.6, 0.6)
        self.goal[0] = max(-5, min(12, self.goal[0] + vx))
        self.goal[1] = max(-5, min(12, self.goal[1] + vy))
        self.goal_vel = [vx, vy]
        moves = {"up": (0, 1), "down": (0, -1), "left": (-1, 0),
                 "right": (1, 0), "boost": (0, 0), "hover": (0, 0)}
        dx, dy = moves.get(action, (0, 0))
        speed = 2.0 if action == "boost" else 1.0
        if action == "boost":
            gx = self.goal[0] - self.pos[0]
            gy = self.goal[1] - self.pos[1]
            n = math.hypot(gx, gy) or 1.0
            dx, dy = gx / n, gy / n
        self.pos[0] += dx * speed
        self.pos[1] += dy * speed
        dist = math.hypot(self.goal[0] - self.pos[0], self.goal[1] - self.pos[1])
        reward = (self.prev - dist) * 0.15
        self.prev = dist
        done = dist < 1.2 or self.t >= 120
        if dist < 1.2:
            reward += 1.0
        return ({"pos": list(self.pos), "goal": list(self.goal),
                 "goal_vel": list(self.goal_vel)}, reward, done, {"dist": dist})

    def act(self, params, obs):
        gx = obs["goal"][0] - obs["pos"][0]
        gy = obs["goal"][1] - obs["pos"][1]
        if params.get("lead", 0):
            gx += obs["goal_vel"][0] * 2.0
            gy += obs["goal_vel"][1] * 2.0
        if math.hypot(gx, gy) > params.get("boost_dist", 4.0) and params.get("speed", 1.0) > 1.4:
            return "boost"
        axis = params.get("axis", 1.0)
        if abs(gx) * axis >= abs(gy):
            return "right" if gx > 0 else "left"
        return "up" if gy > 0 else "down"


class SnakeEnv:
    ""
    name = "snake"

    MOVES = {"up": (0, 1), "down": (0, -1), "left": (-1, 0), "right": (1, 0)}

    def reset(self):
        self.body = [(2, 5), (1, 5), (0, 5)]
        self.food = (7, 5)
        self.dir = (1, 0)
        self.t = 0
        self.eaten = 0
        return {"head": self.body[0], "food": self.food,
                "body": list(self.body), "dir": self.dir}

    def _obs(self, head):
        return {"head": head, "food": self.food,
                "body": list(self.body), "dir": self.dir}

    def step(self, action):
        self.t += 1
        nd = self.MOVES.get(action, self.dir)
        if (nd[0] == -self.dir[0] and nd[1] == -self.dir[1]):
            nd = self.dir
        self.dir = nd
        head = (self.body[0][0] + nd[0], self.body[0][1] + nd[1])
        if not (0 <= head[0] < 10 and 0 <= head[1] < 10):
            return self._obs(head), -1.0, True, {"cause": "wall"}
        if head in self.body[:-1]:
            return self._obs(head), -1.0, True, {"cause": "self"}
        self.body.insert(0, head)
        if head == self.food:
            self.eaten += 1
            reward = 1.0
            free = [(x, y) for x in range(10) for y in range(10)
                    if (x, y) not in self.body]
            self.food = random.choice(free) if free else self.food
        else:
            self.body.pop()
            reward = -0.01
        done = self.eaten >= 5 or self.t >= 150
        return self._obs(head), reward, done, {"eaten": self.eaten}

    def act(self, params, obs):
        head = obs["head"]
        food = obs["food"]
        body = set(obs["body"][:-1])
        margin = int(params.get("margin", 0))
        safe_only = bool(params.get("greedy", 1))
        lookahead = int(params.get("lookahead", 1))
        best = None
        best_score = -1e9
        for name, (dx, dy) in self.MOVES.items():
            nx, ny = head[0] + dx, head[1] + dy
            if not (0 <= nx < 10 and 0 <= ny < 10):
                continue
            if (nx, ny) in body:
                continue
            wall_pen = params.get("wall_w", 0.5) if (margin and (nx < margin or nx > 9 - margin or
                                           ny < margin or ny > 9 - margin)) else 0.0
            dist = abs(food[0] - nx) + abs(food[1] - ny)
            score = -dist - wall_pen
            if lookahead >= 2:
                free = 0
                for ddx, ddy in self.MOVES.values():
                    px, py = nx + ddx, ny + ddy
                    if (0 <= px < 10 and 0 <= py < 10
                            and (px, py) not in body and (px, py) != (nx, ny)):
                        free += 1
                if free == 0:
                    score -= 5.0
                elif free == 1:
                    score -= 1.0
            if not safe_only and dist == 0:
                score += 2.0
            if score > best_score:
                best_score = score
                best = name
        if best is None:
            for name, (dx, dy) in self.MOVES.items():
                nx, ny = head[0] + dx, head[1] + dy
                if 0 <= nx < 10 and 0 <= ny < 10 and (nx, ny) not in body:
                    return name
            return "right"
        return best


class GridHuntEnv:
    ""
    name = "grid_hunt"

    def reset(self):
        self.pos = (0, 0)
        self.target = (random.randint(0, 9), random.randint(0, 9))
        self.t = 0
        self.prev = math.hypot(9, 9)
        self.last_axis = None
        return {"pos": self.pos, "target": self.target, "last_axis": None}

    def step(self, action):
        self.t += 1
        moves = {"n": (0, 1), "s": (0, -1), "e": (1, 0), "w": (-1, 0)}
        dx, dy = moves.get(action, (0, 0))
        self.pos = (max(0, min(9, self.pos[0] + dx)), max(0, min(9, self.pos[1] + dy)))
        dist = math.hypot(self.target[0] - self.pos[0], self.target[1] - self.pos[1])
        reward = (self.prev - dist) * 0.05 - 0.01
        self.prev = dist
        done = dist < 0.5 or self.t >= 80
        if dist < 0.5:
            reward += 1.0
        axis = None
        if dx:
            axis = "e" if dx > 0 else "w"
        elif dy:
            axis = "n" if dy > 0 else "s"
        self.last_axis = axis
        return ({"pos": self.pos, "target": self.target, "last_axis": axis},
                reward, done, {"dist": dist})

    def act(self, params, obs):
        dx = obs["target"][0] - obs["pos"][0]
        dy = obs["target"][1] - obs["pos"][1]
        axis_w = params.get("axis", 1.0)
        stick = params.get("stick", 0)
        hx = "e" if dx > 0 else "w"
        hy = "n" if dy > 0 else "s"
        if stick and obs.get("last_axis") == hx and abs(dx) > 0:
            return hx
        if abs(dx) * axis_w >= abs(dy):
            return hx
        return hy


class GuessEnv:
    ""
    name = "guess_number"

    def reset(self):
        self.target = random.randint(1, 500)
        self.value = 1
        self.t = 0
        self.prev = abs(self.target - self.value)
        return {"value": self.value,
                "hint": "low" if self.value < self.target else "high"}

    def step(self, action):
        self.t += 1
        if action == "inc":
            self.value += 1
        elif action == "dec":
            self.value -= 1
        elif action == "double":
            self.value *= 2
        elif action == "half":
            self.value = max(1, self.value // 2)
        self.value = max(1, min(2000, self.value))
        dist = abs(self.target - self.value)
        reward = (self.prev - dist) * 0.02 - 0.01
        self.prev = dist
        done = dist == 0 or self.t >= 60
        if dist == 0:
            reward += 1.0
        hint = "ok" if dist == 0 else ("low" if self.value < self.target else "high")
        return {"value": self.value, "hint": hint}, reward, done, {"dist": dist}

    def act(self, params, obs):
        if obs["hint"] == "low":
            if params.get("grow", 1) and obs["value"] * 2 <= params.get("cap", 1000):
                return "double"
            return "inc"
        if obs["hint"] == "high":
            if params.get("shrink", 1) and obs["value"] > 2:
                return "half"
            return "dec"
        return "inc"


class QueueEnv:
    ""
    name = "queue_schedule"

    def reset(self):
        self.jobs = [{"id": i, "left": 3, "due": 6 + i * 4} for i in range(5)]
        self.t = 0
        self.done_jobs = 0
        self.current = None
        return {"jobs": [dict(j) for j in self.jobs], "current": None}

    def step(self, action):
        self.t += 1
        reward = 0.0
        idx = None
        if action.startswith("pick_"):
            try:
                idx = int(action.split("_")[1])
            except (ValueError, IndexError):
                idx = None
        if idx is not None and 0 <= idx < len(self.jobs) and self.jobs[idx]["left"] > 0:
            job = self.jobs[idx]
            job["left"] -= 1
            self.current = idx
            if job["left"] == 0:
                self.done_jobs += 1
                if self.t <= job["due"]:
                    reward += 1.0
                else:
                    reward -= 0.5
        else:
            reward -= 0.05
        all_done = all(j["left"] == 0 for j in self.jobs)
        done = all_done or self.t >= 60
        return ({"jobs": [dict(j) for j in self.jobs], "current": self.current},
                reward, done, {"finished": self.done_jobs})

    def act(self, params, obs):
        pending = [(j, i) for i, j in enumerate(obs["jobs"]) if j["left"] > 0]
        if not pending:
            return "wait"
        rule = params.get("order", 0)
        preempt = params.get("preempt", 1)
        cur = obs.get("current")
        if (not preempt) and cur is not None and 0 <= cur < len(obs["jobs"]) \
                and obs["jobs"][cur]["left"] > 0:
            return "pick_%d" % cur
        tie = params.get("tie", 0)
        if rule == 1:
            job, idx = min(pending, key=lambda kv: (kv[0]["left"], kv[1] if tie else -kv[0]["due"]))
        elif rule == 2:
            if tie:
                job, idx = max(pending, key=lambda kv: kv[0]["due"])
            else:
                job, idx = pending[0]
        else:
            job, idx = min(pending, key=lambda kv: (kv[0]["due"], -kv[0]["left"] if tie else kv[1]))
        return "pick_%d" % idx


ENVS = {
    "drone": DroneEnv,
    "snake": SnakeEnv,
    "grid": GridHuntEnv,
    "guess": GuessEnv,
    "queue": QueueEnv,
}
