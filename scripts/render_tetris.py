# -*- coding: utf-8 -*-
""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from benches.tetris import TetrisEnv

CELL = 28
BW, BH = 10, 20
OX, OY = 16, 18
PANEL = 214
W = OX * 2 + BW * CELL + PANEL
H = OY * 2 + BH * CELL

COLORS = {
    "I": (0, 220, 230),
    "J": (40, 70, 230),
    "L": (240, 150, 30),
    "O": (235, 220, 40),
    "S": (60, 210, 70),
    "T": (165, 60, 230),
    "Z": (235, 55, 55),
}

FONT_PATH = "C:/Windows/Fonts/consola.ttf"
if not os.path.exists(FONT_PATH):
    FONT_PATH = "C:/Windows/Fonts/arial.ttf"


def _fonts():
    return {
        "big": ImageFont.truetype(FONT_PATH, 30),
        "mid": ImageFont.truetype(FONT_PATH, 19),
        "small": ImageFont.truetype(FONT_PATH, 14),
    }


F = _fonts()


def draw_frame(env, params, piece_index):
    img = Image.new("RGB", (W, H), (16, 17, 24))
    d = ImageDraw.Draw(img)

    
    d.rectangle([OX - 2, OY - 2, OX + BW * CELL + 2, OY + BH * CELL + 2],
                fill=(8, 8, 12), outline=(58, 60, 84), width=2)
    
    for x in range(1, BW):
        d.line([OX + x * CELL, OY, OX + x * CELL, OY + BH * CELL],
               fill=(30, 31, 44))
    for y in range(1, BH):
        d.line([OX, OY + y * CELL, OX + BW * CELL, OY + y * CELL],
               fill=(30, 31, 44))
    
    for y in range(BH):
        for x in range(BW):
            v = env.board[y][x]
            if not v:
                continue
            color = COLORS.get(v, (200, 200, 200))
            x0, y0 = OX + x * CELL, OY + y * CELL
            d.rectangle([x0 + 1, y0 + 1, x0 + CELL - 2, y0 + CELL - 2],
                        fill=color)
            d.rectangle([x0 + 1, y0 + 1, x0 + CELL - 2, y0 + CELL - 2],
                        outline=(255, 255, 255, 60), width=1)
            d.rectangle([x0 + 3, y0 + 3, x0 + CELL - 6, y0 + 5],
                        fill=tuple(min(255, c + 55) for c in color))

    
    hx = OX + BW * CELL + 18
    d.text((hx, 20), "TETRIS", font=F["mid"], fill=(130, 132, 160))
    d.text((hx, 42), "hunter generic", font=F["small"], fill=(90, 92, 120))

    labels = [
        ("SCORE", "{:,}".format(env.score), (240, 240, 255)),
        ("LINES", str(env.lines), (150, 235, 180)),
        ("PIECES", str(env.pieces), (200, 200, 225)),
    ]
    y = 86
    for name, value, color in labels:
        d.text((hx, y), name, font=F["small"], fill=(120, 122, 150))
        d.text((hx, y + 16), value, font=F["big"], fill=color)
        y += 66

    
    d.text((hx, y), "WEIGHTS", font=F["small"], fill=(120, 122, 150))
    y += 18
    for key in ("lines", "height", "holes", "bump"):
        d.text((hx, y), "%-7s %.2f" % (key, params[key]),
               font=F["small"], fill=(170, 172, 200))
        y += 17

    
    d.text((hx, H - 74), "PROGRESS", font=F["small"], fill=(110, 112, 140))
    d.rectangle([hx, H - 56, hx + 176, H - 48], fill=(34, 35, 50))
    ratio = min(1.0, piece_index / 4000.0)
    d.rectangle([hx, H - 56, hx + int(176 * ratio), H - 48],
                fill=(80, 190, 240))
    d.text((hx, H - 42), "%d / 4000" % piece_index, font=F["small"],
           fill=(150, 152, 180))
    return img


def draw_end(env, params):
    img = draw_frame(env, params, 4000)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, H], fill=(8, 8, 12))
    d.text((34, H // 2 - 96), "GAME OVER", font=F["big"], fill=(240, 80, 80))
    d.text((34, H // 2 - 46), "LINES  %d" % env.lines, font=F["big"],
           fill=(150, 235, 180))
    d.text((34, H // 2 + 4), "SCORE  %s" % format(env.score, ","),
           font=F["big"], fill=(240, 240, 255))
    d.text((34, H // 2 + 54), "PIECES %d" % env.pieces, font=F["big"],
           fill=(200, 200, 225))
    d.text((34, H // 2 + 116), "lines %.2f  height %.2f" %
           (params["lines"], params["height"]), font=F["small"],
           fill=(150, 152, 180))
    d.text((34, H // 2 + 134), "holes %.2f  bump %.2f" %
           (params["holes"], params["bump"]), font=F["small"],
           fill=(150, 152, 180))
    return img


def main():
    seed = int(sys.argv[1]) if len(sys.argv) > 1 else 102
    max_pieces = int(sys.argv[2]) if len(sys.argv) > 2 else 10000
    fps = int(sys.argv[3]) if len(sys.argv) > 3 else 60

    params = {"lines": 1.5, "height": 0.7, "holes": 1.6, "bump": 1.5}
    env = TetrisEnv(seed=seed, max_pieces=max_pieces)
    obs = env.reset()

    os.makedirs("out", exist_ok=True)
    path = "out/tetris_%dlines_%d.mp4" % (0, seed)
    writer = cv2.VideoWriter(path, cv2.VideoWriter_fourcc(*"mp4v"), fps, (W, H))

    done = False
    frame_index = 0
    while not done:
        img = draw_frame(env, params, env.pieces)
        writer.write(cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR))
        obs, reward, done, _ = env.step(env.act(params, obs))
        frame_index += 1

    final = draw_end(env, params)
    for _ in range(fps * 4):
        writer.write(cv2.cvtColor(np.array(final), cv2.COLOR_RGB2BGR))
    writer.release()

    final_path = "out/tetris_%dlines_%d.mp4" % (env.lines, seed)
    if path != final_path:
        os.replace(path, final_path)
    print("视频:", final_path, "帧数", frame_index + fps * 4,
          "时长 %.1fs" % ((frame_index + fps * 4) / fps),
          "| %d 行 %d 分 %d 块" % (env.lines, env.score, env.pieces))


if __name__ == "__main__":
    main()
