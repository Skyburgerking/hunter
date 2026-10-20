# -*- coding: utf-8 -*-
""

import math
import random


# ══════════════════════════════════════════════════════════
# 2048
# ══════════════════════════════════════════════════════════
class Game2048:
    name = "2048"

    def reset(self):
        self.board = [[0] * 4 for _ in range(4)]
        self.score = 0
        self.t = 0
        self._spawn()
        self._spawn()
        return self._obs()

    def _obs(self):
        return {"board": [row[:] for row in self.board], "score": self.score}

    def _spawn(self):
        empty = [(r, c) for r in range(4) for c in range(4) if not self.board[r][c]]
        if not empty:
            return
        r, c = random.choice(empty)
        self.board[r][c] = 2 if random.random() < 0.9 else 4

    @staticmethod
    def _compress(line):
        vals = [v for v in line if v]
        out, gained, i = [], 0, 0
        while i < len(vals):
            if i + 1 < len(vals) and vals[i] == vals[i + 1]:
                v = vals[i] * 2
                out.append(v)
                gained += v
                i += 2
            else:
                out.append(vals[i])
                i += 1
        out += [0] * (4 - len(out))
        return out, gained

    def _move(self, board, d):
        b = [row[:] for row in board]
        gained = 0
        if d in ("left", "right"):
            for r in range(4):
                line = b[r] if d == "left" else b[r][::-1]
                new, g = self._compress(line)
                if d == "right":
                    new = new[::-1]
                b[r] = new
                gained += g
        else:
            for c in range(4):
                col = [b[r][c] for r in range(4)]
                line = col if d == "up" else col[::-1]
                new, g = self._compress(line)
                if d == "down":
                    new = new[::-1]
                for r in range(4):
                    b[r][c] = new[r]
                gained += g
        return b, gained, b != board

    def step(self, action):
        b, gained, changed = self._move(self.board, action)
        self.t += 1
        if not changed:
            return self._obs(), -0.05, False, {"score": self.score}
        self.board = b
        self.score += gained
        self._spawn()
        dead = not any(self._move(self.board, d)[2] for d in ("up", "down", "left", "right"))
        reward = gained / 200.0
        done = dead or self.t >= 800
        if dead:
            reward -= 1.0
        return self._obs(), reward, done, {"score": self.score, "dead": dead}

    def act(self, params, obs):
        best, best_v = "left", -1e18
        for d in ("up", "down", "left", "right"):
            b, gained, changed = self._move(self.board, d)
            if not changed:
                continue
            v = self._value(b, gained, params)
            if v > best_v:
                best_v, best = v, d
        return best

    @staticmethod
    def _value(board, gained, params):
        empty = sum(1 for row in board for v in row if not v)
        mono = 0.0
        for row in board:
            for i in range(3):
                a, b = row[i], row[i + 1]
                if a and b:
                    mono += a - b if a >= b else -(b - a)
        for c in range(4):
            for r in range(3):
                a, b = board[r][c], board[r + 1][c]
                if a and b:
                    mono += a - b if a >= b else -(b - a)
        smooth = 0.0
        for r in range(4):
            for c in range(4):
                if not board[r][c]:
                    continue
                for dr, dc in ((1, 0), (0, 1)):
                    nr, nc = r + dr, c + dc
                    if nr < 4 and nc < 4 and board[nr][nc]:
                        smooth -= abs(board[r][c] - board[nr][nc])
        top = max(max(row) for row in board)
        corner = 1.0 if max(board[0][0], board[0][3], board[3][0], board[3][3]) == top else 0.0
        return (params.get("empty", 1.0) * empty
                + params.get("gain", 1.0) * gained * 0.05
                + params.get("mono", 0.1) * mono
                + params.get("smooth", 0.1) * smooth
                + params.get("corner", 0.5) * corner * 10.0)


# ══════════════════════════════════════════════════════════
# Flappy
# ══════════════════════════════════════════════════════════
class Flappy:
    name = "flappy"

    H = 10.0
    GAP = 3.2
    GRAVITY = 0.15
    FLAP = -0.70
    SPEED = 1.0
    PIPE_W = 1.4

    def reset(self):
        self.y = 5.0
        self.vy = 0.0
        self.pipes = [[8.0, 5.0]]
        self.passed = 0
        self.t = 0
        self.dead = False
        return self._obs()

    def _obs(self):
        return {"y": self.y, "vy": self.vy,
                "pipes": [[p[0], p[1]] for p in self.pipes],
                "passed": self.passed}

    def step(self, action):
        self.t += 1
        if action == "flap":
            self.vy = self.FLAP
        self.vy += self.GRAVITY
        self.vy = min(self.vy, 3.0)
        self.y += self.vy
        for p in self.pipes:
            p[0] -= self.SPEED
        gained_pipe = False
        if self.pipes and self.pipes[0][0] < -self.PIPE_W:
            self.pipes.pop(0)
            self.passed += 1
            gained_pipe = True
        if not self.pipes or self.pipes[-1][0] < 8.0:
            gap = random.uniform(3.0, self.H - 3.0)
            last_x = self.pipes[-1][0] if self.pipes else 0.0
            self.pipes.append([max(last_x + 5.0, 8.0), gap])
        dead = self.y < 0 or self.y > self.H
        for p in self.pipes:
            px, gap = p
            if px < 0.9 and px > -self.PIPE_W - 0.9:
                if not (gap - self.GAP / 2 < self.y < gap + self.GAP / 2):
                    dead = True
        if dead and not self.dead:
            self.dead = True
            return self._obs(), -1.0, True, {"passed": self.passed}
        reward = 0.01 + (1.0 if gained_pipe else 0.0)
        done = self.t >= 4000
        return self._obs(), reward, done, {"passed": self.passed}

    def act(self, params, obs):
        look = params.get("lookahead", 1.0)
        offset = params.get("offset", 0.0)
        visible = [p for p in obs["pipes"] if p[0] > -self.PIPE_W]
        if not visible:
            return "noop"
        idx = min(int(params.get("n_pipes", 1)) - 1, len(visible) - 1)
        dist, target = visible[idx][0], visible[idx][1]
        want = target + offset
        deadband = params.get("deadband", 0.2)
        
        if obs["y"] > want + deadband and obs["vy"] > params.get("vy_gate", -0.8):
            return "flap"
        return "noop"


# ══════════════════════════════════════════════════════════
# Pong
# ══════════════════════════════════════════════════════════
class Pong:
    name = "pong"

    W, H = 20.0, 12.0
    PADDLE = 2.2
    BALL_R = 0.35

    def reset(self):
        self.bx, self.by = 10.0, 6.0
        ang = random.uniform(-0.6, 0.6)
        self.vx = 0.55 * math.cos(ang)
        self.vy = 0.55 * math.sin(ang)
        self.px = 1.0
        self.py = 6.0
        self.hits = 0
        self.misses = 0
        self.t = 0
        self._hit_bonus = 0.0
        return self._obs()

    def _obs(self):
        return {"bx": self.bx, "by": self.by, "vx": self.vx, "vy": self.vy,
                "px": self.px, "py": self.py}

    def step(self, action):
        self.t += 1
        if action == "up":
            self.py = min(self.H - self.PADDLE / 2, self.py + 0.9)
        elif action == "down":
            self.py = max(self.PADDLE / 2, self.py - 0.9)
        self.bx += self.vx
        self.by += self.vy
        if self.by < self.BALL_R or self.by > self.H - self.BALL_R:
            self.vy = -self.vy
            self.by = max(self.BALL_R, min(self.H - self.BALL_R, self.by))
        if self.vx < 0 and abs(self.bx - self.px) < self.BALL_R + 0.3:
            if abs(self.by - self.py) < self.PADDLE / 2 + self.BALL_R:
                self.vx = abs(self.vx) * 1.02
                self.vy += (self.by - self.py) * 0.25
                self.hits += 1
                self._hit_bonus = 0.2
            else:
                self.misses += 1
                return self._obs(), -1.0, True, {"hits": self.hits}
        if self.bx < -2:
            self.misses += 1
            return self._obs(), -1.0, True, {"hits": self.hits}
        if self.bx > self.W:
            self.vx = -abs(self.vx)
            self.bx = self.W
        done = self.t >= 3000 or self.hits >= 60
        reward = 0.01 + self._hit_bonus
        self._hit_bonus = 0.0
        return self._obs(), reward, done, {"hits": self.hits}

    def _mirror(self, v):
        while v < 0 or v > self.H:
            if v < 0:
                v = -v
            if v > self.H:
                v = 2 * self.H - v
        return v

    def act(self, params, obs):
        lead = params.get("lead", 1.0)
        margin = params.get("margin", 0.0)
        if obs["vx"] >= 0:
            return "stay"
        time_to = max(0.0, (obs["bx"] - obs["px"]) / max(-0.01, obs["vx"]))
        target = obs["by"] + obs["vy"] * time_to * lead
        target = self._mirror(target)
        target = max(0.5, min(self.H - 0.5, target))
        if obs["py"] < target - margin:
            return "up"
        if obs["py"] > target + margin:
            return "down"
        return "stay"


GAMES = {
    "2048": Game2048,
    "flappy": Flappy,
    "pong": Pong,
}
