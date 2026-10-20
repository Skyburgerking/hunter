# -*- coding: utf-8 -*-
""
from .base import ArcadeEnv, frags


# ══════════════════════════════════════════════════════════
class Snake(ArcadeEnv):
    ""

    NAME = "snake"
    FULL = 5.0
    RENDERER = "table"
    CONDITIONS = 4
    SLOTS = frags({"op": "mv", "dir": "N"}, {"op": "mv", "dir": "S"},
                  {"op": "mv", "dir": "E"}, {"op": "mv", "dir": "W"})
    APPLES = [(1, 0), (2, 0), (3, 0), (3, 1), (3, 2)]

    def reset(self):
        self.body = [(0, 0)]
        self.dir = (1, 0)
        self.k = 0
        self.score = 0.0
        self.done = False
        self.steps = 0
        return self

    def _apple(self):
        return self.APPLES[min(self.k, len(self.APPLES) - 1)]

    def apply(self, step_json):
        if self.done:
            return True
        d = {"N": (0, -1), "S": (0, 1), "E": (1, 0), "W": (-1, 0)}.get(
            str(step_json.get("dir", "E")))
        if d is None or step_json.get("op") != "mv":
            return False
        head = (self.body[0][0] + d[0], self.body[0][1] + d[1])
        self.steps += 1
        if not (0 <= head[0] < 8 and 0 <= head[1] < 8) or head in self.body:
            self.done = True
            return True
        self.body.insert(0, head)
        if head == self._apple():
            self.k += 1
            self.score = float(self.k)
            if self.k >= len(self.APPLES):
                self.done = True
                return True
        else:
            self.body.pop()
        if self.steps >= 200:
            self.done = True
        return self.done

    def situation(self):
        if self.done:
            return None
        ax, ay = self._apple()
        dx, dy = ax - self.body[0][0], ay - self.body[0][1]
        if abs(dx) >= abs(dy):
            return 0 if dx > 0 else 1          
        return 2 if dy > 0 else 3              


# ══════════════════════════════════════════════════════════
class Flappy(ArcadeEnv):
    ""

    NAME = "flappy"
    FULL = 10.0
    RENDERER = "table"
    CONDITIONS = 5
    SLOTS = frags({"op": "flap"}, {"op": "glide"})

    def reset(self):
        self.y = 10.0
        self.vy = 0.0
        self.t = 0
        self.k = 0
        self.score = 0.0
        self.done = False
        self.steps = 0
        return self

    def _gap(self):
        
        return [10, 8, 11, 9, 10, 7, 11, 9, 10, 8][min(self.k, 9)]

    def apply(self, step_json):
        if self.done:
            return True
        op = step_json.get("op")
        if op == "flap":
            self.vy = -1.0
        elif op == "glide":
            pass
        else:
            return False
        self.vy += 0.45
        self.y += self.vy
        self.steps += 1
        self.t += 1
        gap = self._gap()
        if self.y < 1 or self.y > 19:
            self.done = True
            return True
        if self.t % 8 == 0:                 
            if abs(self.y - gap) <= 1.5:
                self.k += 1
                self.score = float(self.k)
                if self.k >= 10:
                    self.done = True
                    return True
            else:
                self.done = True
        return self.done

    def situation(self):
        if self.done:
            return None
        d = int(round(self.y - self._gap()))
        return max(0, min(4, d + 2))


# ══════════════════════════════════════════════════════════
class Pong(ArcadeEnv):
    ""

    NAME = "pong"
    FULL = 20.0
    RENDERER = "table"
    CONDITIONS = 6
    SLOTS = frags({"op": "up"}, {"op": "stay"}, {"op": "down"})

    def reset(self):
        self.paddle = 10
        self.ball = 10.0
        self.vy = 1.0
        self.t = 0
        self.score = 0.0
        self.done = False
        self.steps = 0
        return self

    def apply(self, step_json):
        if self.done:
            return True
        op = step_json.get("op")
        if op == "up":
            self.paddle = max(1, self.paddle - 1)
        elif op == "down":
            self.paddle = min(19, self.paddle + 1)
        elif op != "stay":
            return False
        self.ball += self.vy
        if self.ball <= 1 or self.ball >= 19:
            self.vy = -self.vy
            self.ball += 2 * self.vy
        self.steps += 1
        self.t += 1
        if self.t % 6 == 0:
            if abs(self.ball - self.paddle) <= 1.5:
                self.score += 1.0
                self.vy = 1.0 if self.ball < 10 else -1.0
                if self.score >= 20:
                    self.done = True
                    return True
            else:
                self.done = True
        return self.done

    def situation(self):
        if self.done:
            return None
        rel = int(round(self.ball - self.paddle))
        bucket = max(-2, min(2, rel)) + 2
        return bucket + (3 if self.vy > 0 else 0)


# ══════════════════════════════════════════════════════════
class Breakout(ArcadeEnv):
    ""

    NAME = "breakout"
    FULL = 14.0
    RENDERER = "table"
    CONDITIONS = 4
    SLOTS = frags({"op": "left"}, {"op": "right"}, {"op": "stay"})

    def reset(self):
        self.bricks = set((x, y) for y in (2, 3) for x in range(7))
        self.px = 3
        self.ball = (3, 8)
        self.dx, self.dy = 1, -1
        self.score = 0.0
        self.done = False
        self.steps = 0
        return self

    def apply(self, step_json):
        if self.done:
            return True
        op = step_json.get("op")
        if op == "left":
            self.px = max(0, self.px - 1)
        elif op == "right":
            self.px = min(6, self.px + 1)
        elif op != "stay":
            return False
        x, y = self.ball
        x += self.dx
        y += self.dy
        if x < 0 or x > 6:
            self.dx = -self.dx
            x += 2 * self.dx
        if y < 1:
            self.dy = 1
            y = 1
        self.ball = (x, y)
        self.steps += 1
        if self.ball in self.bricks:
            self.bricks.discard(self.ball)
            self.dy = -self.dy
            self.score = float(14 - len(self.bricks))
            if not self.bricks:
                self.done = True
                return True
        if y >= 8:                       
            if abs(x - self.px) <= 1:
                self.dy = -1
                self.ball = (x, 8)
            else:
                self.done = True
        if self.steps >= 400:
            self.done = True
        return self.done

    def situation(self):
        if self.done:
            return None
        rel = self.ball[0] - self.px
        return max(0, min(3, rel + 1))


# ══════════════════════════════════════════════════════════
class Thunder(ArcadeEnv):
    ""

    NAME = "thunder"
    FULL = 8.0
    RENDERER = "table"
    CONDITIONS = 8
    SLOTS = frags({"op": "left"}, {"op": "right"}, {"op": "shoot"})

    def reset(self):
        self.px = 4
        self.enemies = [(2, 30), (5, 32), (3, 34), (6, 36),
                        (1, 38), (4, 40), (7, 42), (2, 44)]
        self.cool = 0
        self.score = 0.0
        self.done = False
        self.steps = 0
        return self

    def apply(self, step_json):
        if self.done:
            return True
        op = step_json.get("op")
        if op == "left":
            self.px = max(0, self.px - 1)
        elif op == "right":
            self.px = min(8, self.px + 1)
        elif op == "shoot":
            if self.cool == 0:
                for i, (ex, _) in enumerate(self.enemies):
                    if ex == self.px:
                        self.enemies.pop(i)
                        self.score = float(8 - len(self.enemies))
                        if not self.enemies:
                            self.done = True
                            return True
                        break
                self.cool = 2
        else:
            return False
        self.cool = max(0, self.cool - 1)
        self.steps += 1
        for i in range(len(self.enemies)):
            ex, ey = self.enemies[i]
            self.enemies[i] = (ex, ey - 1)
        if any(ey <= 0 for _, ey in self.enemies):
            self.done = True
        if self.steps >= 300:
            self.done = True
        return self.done

    def situation(self):
        if self.done or not self.enemies:
            return None
        ex, ey = min(self.enemies, key=lambda e: e[1])
        rel = max(0, min(3, ex - self.px + 1))
        return rel + (4 if self.cool > 0 else 0)   


# ══════════════════════════════════════════════════════════
class Lunar(ArcadeEnv):
    ""

    NAME = "lunar"
    FULL = 1.0
    RENDERER = "table"
    CONDITIONS = 4
    SLOTS = frags({"op": "thrust"}, {"op": "coast"})

    def reset(self):
        self.h = 20.0
        self.v = 3.0
        self.fuel = 25
        self.score = 0.0
        self.done = False
        self.steps = 0
        return self

    def apply(self, step_json):
        if self.done:
            return True
        op = step_json.get("op")
        if op == "thrust":
            if self.fuel <= 0:
                return False
            self.v -= 1.6
            self.fuel -= 1
        elif op != "coast":
            return False
        self.v += 0.8
        self.h += self.v
        self.steps += 1
        if self.h <= 0:
            self.score = 1.0 if abs(self.v) <= 2.0 else 0.0
            self.done = True
        if self.steps >= 60:
            self.done = True
        return self.done

    def situation(self):
        if self.done:
            return None
        if self.h > 14:
            return 0
        if self.h > 7:
            return 1
        if self.h > 3:
            return 2
        return 3


# ══════════════════════════════════════════════════════════
class Cartpole(ArcadeEnv):
    ""

    NAME = "cartpole"
    FULL = 200.0
    RENDERER = "table"
    CONDITIONS = 5
    SLOTS = frags({"op": "push", "dir": -1}, {"op": "push", "dir": 1})

    def reset(self):
        self.theta = 0.05
        self.omega = 0.0
        self.score = 0.0
        self.done = False
        self.steps = 0
        return self

    def apply(self, step_json):
        if self.done:
            return True
        if step_json.get("op") != "push":
            return False
        d = int(step_json.get("dir", 1))
        self.omega += (0.25 * d) - 0.05 * self.theta
        self.theta += self.omega
        self.omega *= 0.98
        self.steps += 1
        self.score = float(self.steps)
        if abs(self.theta) > 0.6:
            self.done = True
        elif self.steps >= 200:
            self.done = True
        return self.done

    def bounds(self):
        ""
        return ((-0.7, 0.7), (-0.6, 0.6))

    def situation(self):
        if self.done:
            return None
        t = self.theta + 0.15 * self.omega      
        if t < -0.24:
            return 0
        if t < -0.06:
            return 1
        if t <= 0.06:
            return 2
        if t <= 0.24:
            return 3
        return 4


# ══════════════════════════════════════════════════════════
class Racing(ArcadeEnv):
    ""

    NAME = "racing"
    FULL = 1.0
    RENDERER = "table"
    CONDITIONS = 6
    SLOTS = frags({"op": "lane", "to": -1}, {"op": "lane", "to": 1},
                  {"op": "stay"})
    OBSTACLES = [(1, 0), (1, 2), (0, 4), (2, 6), (1, 8),
                 (0, 10), (2, 12), (1, 14), (0, 16), (2, 18), (1, 20), (0, 22)]

    def reset(self):
        self.lane = 1
        self.t = 0
        self.score = 0.0
        self.done = False
        self.steps = 0
        return self

    def apply(self, step_json):
        if self.done:
            return True
        op = step_json.get("op")
        if op == "lane":
            self.lane = max(0, min(2, self.lane + int(step_json.get("to", 0))))
        elif op != "stay":
            return False
        self.t += 1
        self.steps += 1
        if (self.lane, self.t) in self.OBSTACLES:
            self.done = True
            return True
        self.score = min(1.0, self.t / 24.0)
        if self.t >= 24:
            self.score = 1.0
            self.done = True
        return self.done

    def situation(self):
        if self.done:
            return None
        
        ahead = [(l, t) for l, t in self.OBSTACLES if t > self.t][:2]
        if not ahead:
            return self.lane
        danger_now = any(l == self.lane for l, _ in ahead)
        if not danger_now:
            return self.lane
        left_ok = self.lane > 0 and not any(l == self.lane - 1 for l, _ in ahead)
        right_ok = self.lane < 2 and not any(l == self.lane + 1 for l, _ in ahead)
        if left_ok:
            return 3
        if right_ok:
            return 4
        return 5
