# -*- coding: utf-8 -*-
""

import os
import sys

from hunter.features import feature

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
GH = os.path.join(ROOT, "_gh", "pvz")
_PKG = {}
FRAME_MS = 16.0          
LANES, COLS = 5, 9


SUNFLOWER, PEASHOOTER, SNOWPEA, WALLNUT = 0, 1, 2, 3


def _boot():
    ""
    if _PKG:
        return _PKG
    if not os.path.isdir(GH):
        raise ImportError("找不到 %s，先 git clone --depth 1 "
                          "https://github.com/marblexu/PythonPlantsVsZombies" % GH)
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    cwd = os.getcwd()
    os.chdir(GH)                      
    try:
        import pygame as pg
        import pygame.sysfont as sf
        sf.initsysfonts_win32 = lambda: {}      
        if GH not in sys.path:
            sys.path.insert(0, GH)
        from source import tool, constants as c
        from source.state import level
        from source.component import menubar, plant, zombie
    finally:
        os.chdir(cwd)
    _PKG.update(pg=pg, tool=tool, c=c, level=level, menubar=menubar,
                plant=plant, zombie=zombie, gh=GH)
    return _PKG


class PvZEnv(object):
    ""

    def __init__(self, level_num=1, cards=(0, 1, 3), frames_per_step=40,
                 cap=260, seed=None):
        self.level_num = int(level_num)
        self.cards = list(cards)
        self.frames_per_step = int(frames_per_step)
        self.cap = int(cap)
        self.score = 0.0
        self.lv = None

    
    def reset(self):
        p = _boot()
        c, level = p["c"], p["level"]
        cwd = os.getcwd()
        os.chdir(p["gh"])
        try:
            info = {c.CURRENT_TIME: 0.0, c.LEVEL_NUM: self.level_num}
            lv = level.Level()
            lv.startup(0.0, info)
            lv.initPlay(list(self.cards))
        finally:
            os.chdir(cwd)
        lv.draw = lambda *a, **k: None          
        lv.menubar.current_time = 0.0           
        self.lv = lv
        self.t = 0.0
        self.steps = 0
        self.kills = 0
        self.score = 0.0
        self.done = False
        self._last_zombies = 0
        return self._obs(None)

    
    def candidates(self):
        lv = self.lv
        if lv is None or lv.done:
            return []
        out = [("wait", 0, 0)]
        sun = lv.menubar.sun_value
        now = self.t
        grid = lv.map.map
        for idx in self.cards:
            card = self._card(idx)
            if card is None or not card.canClick(sun, now):
                continue                    
            for lane in range(LANES):
                for col in range(COLS):
                    if grid[lane][col] == 0:
                        out.append((idx, lane, col))
        return out

    def peek(self, action):
        ""
        idx, lane, col = action
        if idx == "wait":
            return self._obs(None)
        return self._obs(action)

    def step(self, action):
        lv = self.lv
        idx, lane, col = action
        before_score = self.score
        if idx != "wait":
            self._plant(idx, lane, col)
        for _ in range(self.frames_per_step):
            self.t += FRAME_MS
            lv.update(_boot()["tool"].SCREEN, self.t, None, [False, False])
            self._collect_sun()
            if lv.done:
                break
        self.steps += 1
        alive = sum(len(g) for g in lv.zombie_groups)
        self.kills += max(0, self._last_zombies - alive)
        self._last_zombies = alive
        self.score = self._raw_score()
        done = bool(lv.done or self.steps >= self.cap)
        self.done = done
        win = bool(lv.done and lv.next == _boot()["c"].GAME_VICTORY)
        return self._obs(None), self.score - before_score, done, {
            "win": win, "kills": self.kills}

    
    def apply(self, step_json):
        ""
        if self.done:
            return True
        op = step_json.get("op", "wait")
        if op == "wait":
            _, _, done, _ = self.step(("wait", 0, 0))
            return done
        if op != "plant":
            return False
        raw_lane = step_json.get("lane", 0)
        if raw_lane == "front":
            lane = self.situation()
            if lane is None:
                return False
        else:
            lane = int(raw_lane)
        try:
            card = int(step_json.get("card", 0))
            col = int(step_json.get("col", 0))
        except (TypeError, ValueError):
            return False
        if not (0 <= lane < LANES and 0 <= col < COLS and card in self.cards):
            return False
        _, _, done, _ = self.step((card, lane, col))
        return done

    def situation(self):
        ""
        if self.done:
            return None
        lv = self.lv
        best_lane, best_x = 0, -1
        for lane, group in enumerate(lv.zombie_groups):
            for z in group:
                if getattr(z, "x", -1) > best_x:
                    best_lane, best_x = lane, z.x
        rich = 1 if lv.menubar.sun_value >= 100 else 0
        return rich * LANES + best_lane

    
    def _cost(self, idx):
        return _boot()["menubar"].plant_sun_list[idx]

    def _card(self, idx):
        for card in self.lv.menubar.card_list:
            if card.name_index == idx:
                return card
        return None

    def _plant(self, idx, lane, col):
        p = _boot()
        lv, c, plant = self.lv, p["c"], p["plant"]
        cost = self._cost(idx)
        if lv.menubar.sun_value < cost or lv.map.map[lane][col] != 0:
            return False
        x, y = lv.map.getMapGridPos(col, lane)
        if idx == SUNFLOWER:
            new = plant.SunFlower(x, y, lv.sun_group)
        elif idx == PEASHOOTER:
            new = plant.PeaShooter(x, y, lv.bullet_groups[lane])
        elif idx == SNOWPEA:
            new = plant.SnowPeaShooter(x, y, lv.bullet_groups[lane])
        elif idx == WALLNUT:
            new = plant.WallNut(x, y)
        else:
            return False
        new.update(lv.game_info) if False else None
        lv.plant_groups[lane].add(new)
        lv.menubar.decreaseSunValue(cost)
        lv.menubar.setCardFrozenTime(p["menubar"].plant_name_list[idx])
        lv.map.setMapGridType(col, lane, c.MAP_EXIST)
        return True

    def _collect_sun(self):
        lv = self.lv
        for sun in list(lv.sun_group):
            lv.menubar.increaseSunValue(sun.sun_value)
            sun.kill()

    def _raw_score(self):
        ""
        lv = self.lv
        alive = sum(len(g) for g in lv.zombie_groups)
        won = bool(lv.done and lv.next == _boot()["c"].GAME_VICTORY)
        return float(self.kills * 10 + (200 if won else 0) + (5 if lv.done and not won else 0))

    def _obs(self, planting):
        ""
        lv = self.lv
        c = _boot()["c"]
        sun = float(lv.menubar.sun_value)
        grid = [[0] * COLS for _ in range(LANES)]
        for lane in range(LANES):
            for sp in lv.plant_groups[lane]:
                mx, my = lv.map.getMapIndex(sp.rect.centerx, sp.rect.bottom)
                if 0 <= my < LANES and 0 <= mx < COLS:
                    grid[my][mx] = 1 if sp.name == c.SUNFLOWER else (
                        2 if sp.name in (c.PEASHOOTER, c.REPEATERPEA) else
                        3 if sp.name in (c.SNOWPEASHOOTER,) else 4)
        if planting and planting[0] != "wait":
            idx, lane, col = planting
            grid[lane][col] = 1 if idx == SUNFLOWER else 2 if idx == PEASHOOTER else 3 if idx == SNOWPEA else 4
            sun -= self._cost(idx)

        dps = [0.0] * LANES
        sunflowers = 0
        walls = 0
        for lane in range(LANES):
            for col in range(COLS):
                v = grid[lane][col]
                if v == 1:
                    sunflowers += 1
                elif v == 2:
                    dps[lane] += 10.0        
                elif v == 3:
                    dps[lane] += 10.0
                elif v == 4:
                    walls += 1

        threat = [0.0] * LANES
        front = 0.0
        hp_sum = 0.0
        for lane in range(LANES):
            for z in lv.zombie_groups[lane]:
                threat[lane] += float(getattr(z, "health", 0))
                hp_sum += float(getattr(z, "health", 0))
                front = max(front, float(z.rect.centerx))
        covered = [dps[i] for i in range(LANES) if threat[i] > 0]
        return {
            "sun": sun,
            "sunflowers": float(sunflowers),
            "dps_total": float(sum(dps)),
            "dps_min_cover": float(min(covered)) if covered else 0.0,
            "walls": float(walls),
            "threat": hp_sum,
            "front": front,
            "zombies": float(sum(len(g) for g in lv.zombie_groups)),
            "win": 1.0 if (lv.done and lv.next == c.GAME_VICTORY) else 0.0,
            "lose": 1.0 if (lv.done and lv.next == c.GAME_LOSE) else 0.0,
        }


# ══════════════════════════════════════════════════════════
@feature("pvz_sun")
def _sun(s):
    return float(s.get("sun", 0)) / 400.0


@feature("pvz_econ")
def _econ(s):
    return float(s.get("sunflowers", 0)) / 6.0


@feature("pvz_dps")
def _dps(s):
    return float(s.get("dps_total", 0)) / 60.0


@feature("pvz_cover")
def _cover(s):
    return float(s.get("dps_min_cover", 0)) / 20.0


@feature("pvz_wall")
def _wall(s):
    return float(s.get("walls", 0)) / 3.0


@feature("pvz_threat")
def _threat(s):
    return -float(s.get("threat", 0)) / 2000.0


@feature("pvz_front")
def _front(s):
    return -float(s.get("front", 0)) / 800.0


@feature("pvz_win")
def _win(s):
    return float(s.get("win", 0.0))


@feature("pvz_lose")
def _lose(s):
    return -float(s.get("lose", 0.0))
