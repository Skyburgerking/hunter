# -*- coding: utf-8 -*-
""

import os
import sys
import types

from hunter.features import feature

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
GH = os.path.join(ROOT, "_gh", "pacman_dqn")

_CS = {}


def _cs188():
    ""
    if _CS:
        return _CS
    if not os.path.isdir(GH):
        raise ImportError("找不到 %s，先 git clone ---depth 1 "
                          "https://github.com/tychovdo/PacmanDQN" % GH)
    if GH not in sys.path:
        sys.path.insert(0, GH)
    if "pacmanDQN_Agents" not in sys.modules:
        stub = types.ModuleType("pacmanDQN_Agents")

        class _Stub(object):
            def __init__(self, *a, **k):
                pass

        stub.PacmanDQNAgent = _Stub
        sys.modules["pacmanDQN_Agents"] = stub
    import pacman as _p
    import layout as _l
    import ghostAgents as _g
    import util as _u
    _CS.update(pacman=_p, layout=_l, ghost=_g, util=_u)
    return _CS


def _load_layout(cs, name):
    ""
    for path in (os.path.join(GH, "layouts", name + ".lay"),
                 os.path.join(GH, name + ".lay"),
                 os.path.join(GH, "layouts", name)):
        if os.path.isfile(path):
            with open(path) as handle:
                return cs["layout"].Layout([line.strip() for line in handle])
    raise IOError("找不到地图 %s（%s/layouts）" % (name, GH))


class PacmanEnv(object):
    ""

    def __init__(self, layout_name="mediumClassic", ghosts=2, cap=800, seed=None):
        self.layout_name = layout_name
        self.num_ghosts = int(ghosts)
        self.cap = int(cap)
        self.score = 0.0
        self.state = None

    
    def reset(self):
        cs = _cs188()
        self.lay = _load_layout(cs, self.layout_name)
        self.state = cs["pacman"].GameState()
        self.state.initialize(self.lay, self.num_ghosts)
        self.ghosts = [cs["ghost"].RandomGhost(i + 1) for i in range(self.num_ghosts)]
        self.steps = 0
        self.score = float(self.state.getScore())
        self.done = False
        return self._obs(self.state)

    def candidates(self):
        st = self.state
        if st is None or st.isWin() or st.isLose():
            return []
        acts = list(st.getLegalPacmanActions())
        
        if len(acts) > 1:
            acts = [a for a in acts if a != "Stop"] or acts
        return acts

    def peek(self, action):
        ""
        st = self.state
        if st is None or st.isWin() or st.isLose():
            return None
        try:
            nxt = st.generatePacmanSuccessor(action)
        except Exception:
            return None
        return self._obs(nxt)

    def step(self, action):
        cs = _cs188()
        pac = cs["pacman"]
        st = self.state
        before = st.getScore()
        st = st.generatePacmanSuccessor(action)
        if not (st.isWin() or st.isLose()):
            for i, ghost in enumerate(self.ghosts):
                act = ghost.getAction(st)          
                if st.isWin() or st.isLose():
                    break                          
                st = st.generateSuccessor(i + 1, act)
        self.state = st
        self.steps += 1
        score = float(st.getScore())
        reward = score - before
        self.score = score
        done = bool(st.isWin() or st.isLose() or self.steps >= self.cap)
        self.done = done
        
        if self.steps % 64 == 0:
            pac.GameState.explored = set()
        return self._obs(st), reward, done, {"win": st.isWin(), "lose": st.isLose()}

    
    def apply(self, step_json):
        ""
        if self.done:
            return True
        op = step_json.get("op")
        if op in (None, "move"):
            name = {"N": "North", "S": "South", "W": "West", "E": "East"}.get(
                str(step_json.get("dir", "N")))
            legal = self.candidates()
            if name is None or name not in legal:
                return False
            _, _, done, _ = self.step(name)
            return done
        if op == "goto":
            step = self._dir_to(str(step_json.get("target", "food")), avoid=step_json.get("avoid"))
        elif op == "flee":
            step = self._dir_away()
        else:
            return False
        if step is None:
            legal = self.candidates()                      
            if not legal:
                return False
            step = legal[0]
        _, _, done, _ = self.step(step)
        return done

    
    def _walls(self):
        st = self.state
        return st.getWalls()

    def _bfs_first_dir(self, goal_test, avoid=None):
        ""
        st = self.state
        danger = set()
        if avoid:
            for i in range(len(self.ghosts)):
                if st.getGhostState(i + 1).scaredTimer > 0:
                    continue
                gx, gy = st.getGhostPosition(i + 1)
                gx, gy = int(gx), int(gy)
                for ddx in range(-avoid, avoid + 1):
                    for ddy in range(-avoid, avoid + 1):
                        if abs(ddx) + abs(ddy) <= avoid:
                            danger.add((gx + ddx, gy + ddy))
        walls = st.getWalls()
        W, H = walls.width, walls.height
        start = st.getPacmanPosition()
        prev = {start: None}
        q = [start]
        while q:
            cur = q.pop(0)
            if goal_test(cur) and cur != start:
                node = cur
                while prev[node] is not None and prev[node] != start:
                    node = prev[node]
                return self._step_name(start, node)
            for dx, dy, nm in ((0, 1, "North"), (0, -1, "South"), (-1, 0, "West"), (1, 0, "East")):
                nx, ny = cur[0] + dx, cur[1] + dy
                if 0 <= nx < W and 0 <= ny < H and not walls[nx][ny] and (nx, ny) not in prev:
                    if (nx, ny) in danger:
                        continue
                    prev[(nx, ny)] = cur
                    q.append((nx, ny))
        if avoid and not any(goal_test(c) for c in prev):
            return self._bfs_first_dir(goal_test)      
        return None

    @staticmethod
    def _step_name(a, b):
        dx, dy = b[0] - a[0], b[1] - a[1]
        if dy > 0:
            return "North"          
        if dy < 0:
            return "South"
        if dx < 0:
            return "West"
        return "East"

    def _dir_to(self, target, avoid=None):
        st = self.state
        if target == "food":
            cells = set(map(tuple, st.getFood().asList()))
        elif target == "capsule":
            cells = set(st.getCapsules())
        elif target == "ghost":
            cells = set()
            for i in range(len(self.ghosts)):
                if st.getGhostState(i + 1).scaredTimer > 0:
                    cells.add(tuple(int(v) for v in st.getGhostPosition(i + 1)))
        else:
            return None
        if not cells:
            return None
        return self._bfs_first_dir(lambda c: c in cells, avoid=avoid)

    def _dir_away(self):
        ""
        st = self.state
        ppos = st.getPacmanPosition()
        ghosts = []
        for i in range(len(self.ghosts)):
            if st.getGhostState(i + 1).scaredTimer > 0:
                continue
            gx, gy = st.getGhostPosition(i + 1)
            ghosts.append((gx, gy))
        if not ghosts:
            return None
        walls = st.getWalls()
        W, H = walls.width, walls.height
        prev = {ppos: None}
        q = [ppos]
        while q:
            cur = q.pop(0)
            for dx, dy in ((0, 1), (0, -1), (-1, 0), (1, 0)):
                nx, ny = cur[0] + dx, cur[1] + dy
                if 0 <= nx < W and 0 <= ny < H and not walls[nx][ny] and (nx, ny) not in prev:
                    prev[(nx, ny)] = cur
                    q.append((nx, ny))

        def ghost_dist(c):
            return min(abs(c[0] - g[0]) + abs(c[1] - g[1]) for g in ghosts)

        best = max(prev.keys(), key=ghost_dist)
        if best == ppos:
            return None
        node = best
        while prev[node] is not None and prev[node] != ppos:
            node = prev[node]
        return self._step_name(ppos, node)


    def situation(self):
        ""
        if self.done:
            return None
        st = self.state
        ppos = st.getPacmanPosition()
        near = 999
        scared = 0
        for i in range(len(self.ghosts)):
            gs = st.getGhostState(i + 1)
            if gs.scaredTimer > 0:
                scared = 1
                continue
            gx, gy = st.getGhostPosition(i + 1)
            near = min(near, abs(ppos[0] - gx) + abs(ppos[1] - gy))
        danger = 2 if near <= 2 else (1 if near <= 6 else 0)
        return danger

    
    def _obs(self, st):
        cs = _cs188()
        md = cs["util"].manhattanDistance
        ppos = st.getPacmanPosition()
        ghosts = list(st.getGhostPositions())
        scared = 0
        near = 999
        danger = 0.0
        for i, g in enumerate(ghosts):
            gs = st.getGhostState(i + 1)
            if gs.scaredTimer > 0:
                scared += 1
            else:
                d = md(ppos, g)
                near = min(near, d)
                
                if d <= 3:
                    danger += (4 - d) / 3.0
        food = st.getFood().asList()
        food_left = len(food)
        food_d = min([md(ppos, f) for f in food]) if food else 0
        walls = st.getWalls()
        open_dirs = 0
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            if not walls[ppos[0] + dx][ppos[1] + dy]:
                open_dirs += 1
        return {
            "score": float(st.getScore()),
            "food_left": food_left,
            "food_dist": food_d,
            "ghost_dist": near,
            "danger": danger,
            "scared": scared,
            "capsules": len(st.getCapsules()),
            "open_dirs": open_dirs,
            "legal": len(st.getLegalPacmanActions()),
            "dead": 1.0 if st.isLose() else 0.0,
            "win": 1.0 if st.isWin() else 0.0,
        }


# ══════════════════════════════════════════════════════════

# ══════════════════════════════════════════════════════════
@feature("pac_score")
def _pac_score(s):
    return float(s.get("score", 0.0)) / 100.0


@feature("pac_food")
def _pac_food(s):
    return -float(s.get("food_left", 0)) / 50.0


@feature("pac_food_near")
def _pac_food_near(s):
    return -float(s.get("food_dist", 0)) / 10.0


@feature("pac_ghost_far")
def _pac_ghost_far(s):
    d = float(s.get("ghost_dist", 99))
    return min(d, 10) / 10.0


@feature("pac_capsule")
def _pac_capsule(s):
    return float(s.get("capsules", 0)) / 4.0


@feature("pac_mobility")
def _pac_mobility(s):
    return float(s.get("open_dirs", 0)) / 4.0


@feature("pac_dead")
def _pac_dead(s):
    return -float(s.get("dead", 0.0))


@feature("pac_win")
def _pac_win(s):
    return float(s.get("win", 0.0))


@feature("pac_danger")
def _pac_danger(s):
    return -float(s.get("danger", 0.0))
