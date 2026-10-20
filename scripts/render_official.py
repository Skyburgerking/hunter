# -*- coding: utf-8 -*-
""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from benches.official import INDEX, SCALE, SIGN, OfficialTetris

W9 = [1.0, 0.5, 0.5, 0.5, 0.0, 4.0, 1.0, 4.0, 2.0]
ORDER = ["lines", "bump", "holes", "landing",
         "row_trans", "col_trans", "wells", "eroded", "height"]
COEF = [W9[i] * SIGN[n] * SCALE[n] for i, n in enumerate(ORDER)]

CELL = 28
BW, BH = 10, 20
OX, OY = 16, 18
PANEL = 240
WIDTH = OX * 2 + BW * CELL + PANEL
HEIGHT = OY * 2 + BH * CELL

COLORS = {
    1: (0, 220, 230),    # I
    2: (235, 220, 40),   # O
    3: (240, 150, 30),   # L
    4: (40, 70, 230),    # J
    5: (165, 60, 230),   # T
    6: (60, 210, 70),    # S
    7: (235, 55, 55),    # Z
}

FONT_PATH = "C:/Windows/Fonts/consola.ttf"
if not os.path.exists(FONT_PATH):
    FONT_PATH = "C:/Windows/Fonts/arial.ttf"
F_BIG = ImageFont.truetype(FONT_PATH, 26)
F_MID = ImageFont.truetype(FONT_PATH, 18)
F_SMALL = ImageFont.truetype(FONT_PATH, 13)


def score_info(info):
    return sum(c * float(v) for c, v in zip(COEF, info))


def run(seed, max_pieces=20000, verbose=False):
    ""
    env = OfficialTetris(seed=seed)
    pieces = 0
    while pieces < max_pieces:
        cands = env.candidates()
        if not cands:
            break
        best = max(cands, key=lambda i: score_info(env.peek(i)))
        done = env.step(best)
        pieces += 1
        if done:
            break
        if verbose and pieces % 500 == 0:
            print("  %5d 块  %6d 行  %12d 分" %
                  (pieces, env.lines, env.score))
    return env.score, env.lines, pieces


def render(seed, out_path, max_pieces=20000, every=1):
    env = OfficialTetris(seed=seed)
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    vw = cv2.VideoWriter(out_path, fourcc, 60.0, (WIDTH, HEIGHT))
    pieces = 0
    frames = 0
    while pieces < max_pieces:
        cands = env.candidates()
        if not cands:
            break
        best = max(cands, key=lambda i: score_info(env.peek(i)))
        done = env.step(best)
        pieces += 1
        if pieces % every == 0 or done:
            img = draw(env, pieces)
            vw.write(cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR))
            frames += 1
        if done:
            break
    vw.release()
    return env.score, env.lines, pieces, frames


def draw(env, pieces):
    img = Image.new("RGB", (WIDTH, HEIGHT), (14, 16, 22))
    d = ImageDraw.Draw(img)
    table = env.game.board.pieces_table

    
    bx, by = OX, OY
    d.rectangle([bx - 2, by - 2, bx + BW * CELL + 2, by + BH * CELL + 2],
                outline=(60, 70, 90), width=2)
    for y in range(BH):
        for x in range(BW):
            px = bx + x * CELL
            py = by + y * CELL
            code = table[y][x] if y < len(table) else 0
            if code:
                color = COLORS.get(code, (200, 200, 200))
                d.rectangle([px, py, px + CELL - 2, py + CELL - 2],
                            fill=color, outline=(0, 0, 0))
            else:
                d.rectangle([px, py, px + CELL - 2, py + CELL - 2],
                            outline=(28, 32, 42))

    
    piece = env.game.board.piece
    if piece is not None:
        for (x, y), code in zip(piece.get_shape_coords(), [piece.shape.code] * 4):
            if 0 <= y < BH and 0 <= x < BW:
                px = bx + x * CELL
                py = by + y * CELL
                color = COLORS.get(code, (200, 200, 200))
                d.rectangle([px, py, px + CELL - 2, py + CELL - 2],
                            fill=color, outline=(255, 255, 255))

    
    px = bx + BW * CELL + 22
    py = by
    d.text((px, py), "HUNTER", font=F_BIG, fill=(120, 220, 255))
    d.text((px, py + 34), "GEDA feature mode", font=F_SMALL, fill=(140, 150, 170))

    rows = [
        ("SCORE", "{:,}".format(env.score), (255, 235, 140)),
        ("LINES", str(env.lines), (200, 240, 200)),
        ("LEVEL", str(env.level), (200, 240, 200)),
        ("PIECES", str(pieces), (200, 200, 220)),
    ]
    yy = py + 66
    for label, val, color in rows:
        d.text((px, yy), label, font=F_SMALL, fill=(130, 140, 160))
        d.text((px, yy + 16), val, font=F_MID, fill=color)
        yy += 46

    d.text((px, yy + 6), "weights", font=F_SMALL, fill=(130, 140, 160))
    yy += 24
    for name, w in zip(ORDER, W9):
        d.text((px, yy), "%-10s %.1f" % (name, w), font=F_SMALL,
               fill=(170, 180, 200))
        yy += 15
    return img


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "render"
    if mode == "find":
        n = int(sys.argv[2]) if len(sys.argv) > 2 else 20
        best = (0, 0, 0, 0)
        for seed in range(1, n + 1):
            s, l, p = run(seed)
            mark = ""
            if l > best[1]:
                best = (s, l, p, seed)
                mark = " *"
            print("seed %2d  %5d 行  %12d 分  %5d 块%s" % (seed, l, s, p, mark))
        print("\n最优 seed %d: %d 行 / %d 分 / %d 块" %
              (best[3], best[1], best[0], best[2]))
        return 0

    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    every = int(sys.argv[3]) if len(sys.argv) > 3 else 1
    out = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "out", "official_seed%d.mp4" % seed)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    print("渲染 seed %d ..." % seed)
    score, lines, pieces, frames = render(seed, out, every=every)
    print("完成：%d 行 / %d 分 / %d 块 / %d 帧 → %s"
          % (lines, score, pieces, frames, out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
