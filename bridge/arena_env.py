# -*- coding: utf-8 -*-
""

import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from input import Keyboard  # noqa: E402
from human_input import HumanKeyboard  # noqa: E402
from memory import Process  # noqa: E402

EXE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "arena.exe")

OFF = {
    "x": 0x2010,
    "y": 0x2014,
    "tx": 0x2018,
    "ty": 0x201C,
    "running": 0x2020,
    "score": 0x7000,
    "ticks": 0x7004,
}

DIRS = {
    "left": (-4, 0),
    "right": (4, 0),
    "up": (0, -4),
    "down": (0, 4),
}


class ArenaEnv:
    def __init__(self, exe=EXE, timeout=10.0, human=True, seed=None):
        self.exe = exe
        self.proc = None
        self.mem = None
        self.base = 0
        self.human = human
        self.kb = HumanKeyboard(seed=seed) if human else Keyboard()
        self.last_score = 0
        self.start_time = 0
        self.reset()

    def reset(self):
        if self.proc is not None:
            self.close()
        self.proc = subprocess.Popen(
            [self.exe], stdout=subprocess.PIPE, text=True)
        line = self.proc.stdout.readline().strip()
        pid = int(line.split("=")[1])
        self.proc.stdout.readline()          
        deadline = time.time() + 3.0
        while True:
            try:
                self.mem = Process(pid=pid)
                self.base = self.mem.module("arena.exe").base
                break
            except Exception:
                if time.time() > deadline:
                    raise
                time.sleep(0.05)
        time.sleep(0.2)
        self.last_score = 0
        self.start_time = time.time()
        return self.observe()

    def observe(self):
        m, b = self.mem, self.base
        return {
            "x": m.read_int(b + OFF["x"]),
            "y": m.read_int(b + OFF["y"]),
            "tx": m.read_int(b + OFF["tx"]),
            "ty": m.read_int(b + OFF["ty"]),
            "ticks": m.read_int(b + OFF["ticks"]),
            "score": m.read_int(b + OFF["score"]),
        }

    def candidates(self):
        return list(DIRS.keys())

    def peek(self, action):
        s = self.observe()
        dx, dy = DIRS[action]
        return {
            "x": max(0, min(800, s["x"] + dx * 3)),
            "y": max(0, min(600, s["y"] + dy * 3)),
            "tx": s["tx"],
            "ty": s["ty"],
        }

    def step(self, action, hold_ms=45):
        if self.human:
            self.kb.press(action)
        else:
            self.kb.hold(action, hold_ms)
        time.sleep(0.01)
        s = self.observe()
        reward = 0.01 * (s["score"] - self.last_score)
        self.last_score = s["score"]
        return s, reward

    def done(self, max_seconds=30.0):
        if self.proc.poll() is not None:
            return True
        return time.time() - self.start_time > max_seconds

    def close(self):
        try:
            if self.mem:
                self.mem.write_int(self.base + OFF["running"], 0)
        except Exception:
            pass
        try:
            self.kb.release_all()
        except Exception:
            pass
        try:
            if self.proc:
                self.proc.wait(timeout=3)
        except Exception:
            try:
                self.proc.kill()
            except Exception:
                pass
        if self.mem:
            self.mem.close()
        self.mem = None
        self.proc = None


if __name__ == "__main__":
    env = ArenaEnv()
    print("start:", env.observe())
    for _ in range(20):
        env.step("right")
    print("after 20 right:", env.observe())
    env.close()
    print("closed")
