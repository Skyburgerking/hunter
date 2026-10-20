# -*- coding: utf-8 -*-
""

import math
import random
import time

from input import Keyboard, find_window, vk_of, user32  # noqa: E402


HOLD_MEAN = 0.110
HOLD_SD = 0.038
GAP_MEAN = 0.040
GAP_SD = 0.022
REACT_MEDIAN = 0.180
REACT_SIGMA = 0.35


class HumanKeyboard:
    def __init__(self, seed=None, hwnd=None):
        self.kb = Keyboard()
        self.rng = random.Random(seed)
        self.hwnd = hwnd
        self.log = []          

    
    def _reaction(self):
        
        return min(0.9, self.rng.lognormvariate(
            math.log(REACT_MEDIAN), REACT_SIGMA))

    def _hold(self):
        v = self.rng.gauss(HOLD_MEAN, HOLD_SD)
        return max(0.045, min(0.30, v))

    def _gap(self):
        v = self.rng.gauss(GAP_MEAN, GAP_SD)
        return max(0.008, min(0.12, v))

    
    def press(self, key, react=True):
        ""
        t0 = time.time()
        if react:
            time.sleep(self._reaction())
        hold = self._hold()
        vk = vk_of(key)
        user32.keybd_event(vk, 0, 0, 0)
        time.sleep(hold)
        user32.keybd_event(vk, 0, 0x0002, 0)
        self.log.append({
            "t": t0, "key": key, "hold": hold,
            "gap": None, "kind": "press",
        })
        
        if self.rng.random() < 0.02:
            time.sleep(self.rng.uniform(0.4, 1.4))
        time.sleep(self._gap())

    def hold_for(self, key, seconds, react=True):
        ""
        t0 = time.time()
        if react:
            time.sleep(self._reaction())
        actual = seconds * self.rng.uniform(0.88, 1.12)
        vk = vk_of(key)
        user32.keybd_event(vk, 0, 0, 0)
        time.sleep(actual)
        user32.keybd_event(vk, 0, 0x0002, 0)
        self.log.append({
            "t": t0, "key": key, "hold": actual,
            "gap": None, "kind": "hold",
        })
        time.sleep(self._gap())
        return actual

    
    def move(self, direction, duration=0.12, curve=True):
        ""
        if not curve:
            return self.hold_for(direction, duration)
        t0 = time.time()
        segments = [0.28, 0.44, 0.28]
        for i, frac in enumerate(segments):
            seg = duration * frac * self.rng.uniform(0.85, 1.15)
            seg = max(0.02, min(0.4, seg))
            vk = vk_of(direction)
            user32.keybd_event(vk, 0, 0, 0)
            time.sleep(seg)
            user32.keybd_event(vk, 0, 0x0002, 0)
            time.sleep(self._gap() * (0.6 if i < 2 else 1.0))
        total = time.time() - t0
        self.log.append({
            "t": t0, "key": direction, "hold": total,
            "gap": None, "kind": "move",
        })
        return total

    def idle(self, seconds=None):
        ""
        time.sleep(seconds if seconds is not None else self._reaction() * 2)

    def maybe_slip(self):
        ""
        r = self.rng.random()
        return "extra" if r < 0.02 else ("skip" if r < 0.05 else None)

    def release_all(self):
        self.kb.release_all()

    
    def dump_log(self, path):
        import json
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.log, f)
        return path
