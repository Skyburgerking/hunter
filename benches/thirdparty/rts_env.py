# -*- coding: utf-8 -*-
""

import copy
import math

from hunter.features import feature

TICK = 1.0 / 25.0            
CELL = 1024.0                
RANGE = 4 * 1024 + 768       


VEHICLES = {
    "1TNK": dict(hp=23000, speed=113, cost=700, damage=4000, burst=1, reload=21),
    "2TNK": dict(hp=46000, speed=72, cost=850, damage=4000, burst=2, reload=70),
    "3TNK": dict(hp=60000, speed=64, cost=1150, damage=6000, burst=2, reload=90),
}
VS_HEAVY = 1.15               

STANCES = ("advance", "hold", "retreat", "focus_weak", "focus_near", "spread")


class Unit(object):
    __slots__ = ("x", "y", "hp", "max_hp", "team", "kind", "reload", "dmg", "burst",
                 "speed", "range2")

    def __init__(self, kind, team, x, y):
        v = VEHICLES[kind]
        self.kind = kind
        self.team = team
        self.x, self.y = float(x), float(y)
        self.max_hp = float(v["hp"])
        self.hp = float(v["hp"])
        self.reload = 0
        self.dmg = v["damage"] * VS_HEAVY
        self.burst = v["burst"]
        self.speed = v["speed"] / 100.0 / 25.0        
        self.range2 = (RANGE / CELL) ** 2

    def dist2(self, other):
        dx, dy = self.x - other.x, self.y - other.y
        return dx * dx + dy * dy

    def alive(self):
        return self.hp > 0


class RTSEnv(object):
    ""

    def __init__(self, my_army=("2TNK",) * 4, enemy_army=("2TNK", "2TNK", "2TNK", "1TNK", "1TNK"),
                 decision_ticks=10, peek_ticks=50, cap=120, seed=None):
        self.my_army = list(my_army)
        self.enemy_army = list(enemy_army)
        self.decision_ticks = int(decision_ticks)
        self.peek_ticks = int(peek_ticks)
        self.cap = int(cap)
        self.score = 0.0

    
    def reset(self):
        self.units = []
        for i, kind in enumerate(self.my_army):
            self.units.append(Unit(kind, 0, 4.0, 4.0 + 3.0 * i))
        for i, kind in enumerate(self.enemy_army):
            self.units.append(Unit(kind, 1, 26.0, 4.0 + 3.0 * i))
        self.t = 0
        self.steps = 0
        self.done = False
        self.score = 0.0
        self.damage_dealt = 0.0
        return self._obs(self.units)

    
    def candidates(self):
        if self.done:
            return []
        return list(STANCES)

    def peek(self, action):
        sim = copy.deepcopy(self.units)
        self._advance(sim, action, self.peek_ticks)
        return self._obs(sim)

    def step(self, action):
        before_enemy = self._hp(self.units, 1)
        before_own = self._hp(self.units, 0)
        self._advance(self.units, action, self.decision_ticks)
        self.steps += 1
        self.t += self.decision_ticks
        own, enemy = self._hp(self.units, 0), self._hp(self.units, 1)
        reward = ((before_enemy - enemy) - (before_own - own)) / 1000.0
        self.done = bool(own <= 0 or enemy <= 0 or self.steps >= self.cap)
        won = enemy <= 0 < own
        
        self.damage_dealt += (before_enemy - enemy) / 1000.0
        self.score = self.damage_dealt
        if won:
            self.score += 300 + own / 1000.0
        return self._obs(self.units), reward, self.done, {"win": won, "own": own, "enemy": enemy}

    
    def apply(self, step_json):
        ""
        if self.done:
            return True
        if step_json.get("op") != "stance":
            return False
        value = str(step_json.get("value", ""))
        if value not in STANCES:
            return False
        _, _, done, _ = self.step(value)
        return done

    def situation(self):
        ""
        if self.done:
            return None
        own = self._hp(self.units, 0)
        own_max = sum(VEHICLES[k]["hp"] for k in self.my_army) or 1.0
        frac = own / own_max
        if frac > 0.66:
            return 0
        if frac > 0.33:
            return 1
        return 2

    
    def _advance(self, units, stance, ticks):
        for _ in range(ticks):
            self._move(units, 0, stance)
            self._move(units, 1, "advance")      
            self._fire(units, stance)

    def _move(self, units, team, stance):
        mine = [u for u in units if u.team == team and u.alive()]
        foes = [u for u in units if u.team != team and u.alive()]
        if not mine or not foes:
            return
        for u in mine:
            if stance in ("focus_near", "focus_weak"):
                key = (lambda f: f.dist2(u)) if stance == "focus_near" \
                    else (lambda f: f.hp)
                target = min(foes, key=key)
            else:
                target = min(foes, key=lambda f: f.dist2(u))

            d = math.sqrt(u.dist2(target))
            in_range = d * CELL <= RANGE
            if stance == "retreat":
                away = -1.0
            elif stance == "hold":
                away = -1.0 if in_range else 1.0
                if in_range:
                    away = 0.0
            elif stance == "spread":
                
                mate = min([m for m in mine if m is not u] or [u],
                           key=lambda m: m.dist2(u))
                md = math.sqrt(u.dist2(mate))
                if md < 3.0:
                    dx, dy = u.x - mate.x, u.y - mate.y
                    n = math.hypot(dx, dy) or 1.0
                    self._step(u, dx / n, dy / n)
                    continue
                away = -1.0 if in_range else 1.0
            else:
                away = -1.0 if in_range and d < 2.5 else (0.0 if in_range else 1.0)

            if away == 0.0:
                continue
            dx, dy = target.x - u.x, target.y - u.y
            n = math.hypot(dx, dy) or 1.0
            self._step(u, away * dx / n, away * dy / n)

    def _step(self, u, dx, dy):
        u.x = min(29.5, max(0.5, u.x + dx * u.speed))
        u.y = min(19.5, max(0.5, u.y + dy * u.speed))

    def _fire(self, units, stance="advance"):
        for u in units:
            if not u.alive():
                continue
            if u.reload > 0:
                u.reload -= 1
                continue
            foes = [f for f in units if f.team != u.team and f.alive()]
            if not foes:
                continue
            if u.team == 0 and stance == "focus_weak":
                target = min(foes, key=lambda f: f.hp)          
            elif u.team == 0 and stance == "focus_near":
                target = min(foes, key=lambda f: f.dist2(u))     
            elif u.team == 0 and stance == "retreat":
                
                target = min(foes, key=lambda f: f.dist2(u))
                if u.dist2(target) > u.range2 * 0.25:
                    continue
            else:
                target = min(foes, key=lambda f: f.dist2(u))
            if u.dist2(target) > u.range2:
                continue
            target.hp -= u.dmg * u.burst
            u.reload = int(VEHICLES[u.kind]["reload"])

    
    @staticmethod
    def _hp(units, team):
        return sum(max(0.0, u.hp) for u in units if u.team == team)

    def _obs(self, units):
        mine = [u for u in units if u.team == 0 and u.alive()]
        foes = [u for u in units if u.team == 1 and u.alive()]
        own_hp = self._hp(units, 0)
        enemy_hp = self._hp(units, 1)
        own_max = sum(VEHICLES[k]["hp"] for k in self.my_army)
        enemy_max = sum(VEHICLES[k]["hp"] for k in self.enemy_army)
        in_range = 0
        for u in mine:
            if foes and min(u.dist2(f) for f in foes) <= u.range2:
                in_range += 1
        focus = 0
        if foes:
            
            targets = {}
            for u in mine:
                if not foes:
                    continue
                t = min(foes, key=lambda f: u.dist2(f))
                targets[id(t)] = targets.get(id(t), 0) + 1
            focus = max(targets.values()) if targets else 0
        engaged = 0
        for f in foes:
            if mine and min(f.dist2(m) for m in mine) <= f.range2:
                engaged += 1
        dist = 0.0
        if mine and foes:
            dist = min(math.sqrt(u.dist2(f)) for u in mine for f in foes)
        return {
            "own_hp": own_hp / own_max if own_max else 0.0,
            "enemy_hp": enemy_hp / enemy_max if enemy_max else 0.0,
            "alive_mine": float(len(mine)),
            "alive_foes": float(len(foes)),
            "in_range": float(in_range),
            "focus": float(focus),
            "engaged": float(engaged),
            "dist": dist,
            "win": 1.0 if (enemy_hp <= 0 < own_hp) else 0.0,
            "lose": 1.0 if (own_hp <= 0) else 0.0,
        }


# ══════════════════════════════════════════════════════════
@feature("rts_own_hp")
def _own_hp(s):
    return float(s.get("own_hp", 0.0))


@feature("rts_enemy_hp")
def _enemy_hp(s):
    return -float(s.get("enemy_hp", 0.0))


@feature("rts_numbers")
def _numbers(s):
    return (float(s.get("alive_mine", 0)) - float(s.get("alive_foes", 0))) / 5.0


@feature("rts_in_range")
def _in_range(s):
    return float(s.get("in_range", 0)) / 5.0


@feature("rts_focus")
def _focus(s):
    return float(s.get("focus", 0)) / 5.0


@feature("rts_engaged")
def _engaged(s):
    return -float(s.get("engaged", 0)) / 5.0


@feature("rts_win")
def _win(s):
    return float(s.get("win", 0.0)) * 2.0


@feature("rts_lose")
def _lose(s):
    return -float(s.get("lose", 0.0)) * 2.0
