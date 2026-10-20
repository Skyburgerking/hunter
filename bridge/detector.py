# -*- coding: utf-8 -*-
""

import math
import statistics


def _cv(values):
    if len(values) < 2:
        return 0.0
    mean = statistics.fmean(values)
    if mean <= 1e-9:
        return 0.0
    return statistics.pstdev(values) / mean


def _autocorr(values, lag=1):
    if len(values) <= lag + 1:
        return 0.0
    xs = values[:-lag]
    ys = values[lag:]
    mx = statistics.fmean(xs)
    my = statistics.fmean(ys)
    num = sum((a - mx) * (b - my) for a, b in zip(xs, ys))
    dx = math.sqrt(sum((a - mx) ** 2 for a in xs))
    dy = math.sqrt(sum((b - my) ** 2 for b in ys))
    if dx < 1e-9 or dy < 1e-9:
        return 0.0
    return num / (dx * dy)


def analyze(log):
    holds = [e["hold"] for e in log if e.get("hold")]
    times = [e["t"] for e in log]
    gaps = [b - a for a, b in zip(times, times[1:])]

    hold_cv = _cv(holds)
    gap_cv = _cv(gaps)
    gap_ac = abs(_autocorr(gaps))
    keys = [e.get("key") for e in log]
    unique_keys = len(set(keys))

    reasons = []
    score = 0.0

    
    if hold_cv >= 0.25:
        score += 0.30
        reasons.append("按住时长变异系数 %.2f（人）" % hold_cv)
    elif hold_cv >= 0.10:
        score += 0.15
        reasons.append("按住时长变异系数 %.2f（偏机械）" % hold_cv)
    else:
        reasons.append("按住时长变异系数 %.3f（机械）" % hold_cv)

    
    if gap_cv >= 0.30:
        score += 0.25
        reasons.append("操作间隔变异系数 %.2f（人）" % gap_cv)
    elif gap_cv >= 0.12:
        score += 0.12
        reasons.append("操作间隔变异系数 %.2f（偏机械）" % gap_cv)
    else:
        reasons.append("操作间隔变异系数 %.3f（机械）" % gap_cv)

    
    if gap_ac < 0.25:
        score += 0.20
        reasons.append("间隔自相关 %.2f（无明显周期）" % gap_ac)
    else:
        reasons.append("间隔自相关 %.2f（周期性明显）" % gap_ac)

    
    if unique_keys >= 2:
        score += 0.15
        reasons.append("用到 %d 种按键" % unique_keys)
    else:
        reasons.append("只用一个按键")

    
    if gaps:
        med = statistics.median(gaps)
        long_tails = sum(1 for g in gaps if g > med * 5)
        if long_tails >= 1:
            score += 0.10
            reasons.append("有 %d 次长停顿（走神）" % long_tails)
        else:
            reasons.append("没有长停顿（机器不会走神）")

    verdict = "human" if score >= 0.55 else "bot"
    return {
        "verdict": verdict,
        "score": round(score, 3),
        "sample": len(log),
        "hold_cv": round(hold_cv, 3),
        "gap_cv": round(gap_cv, 3),
        "gap_autocorr": round(gap_ac, 3),
        "reasons": reasons,
    }


def report(result):
    lines = ["判定: %s  像人度 %.2f  样本 %d" %
             (result["verdict"], result["score"], result["sample"])]
    for r in result["reasons"]:
        lines.append("  · " + r)
    return "\n".join(lines)



def make_bot_log(n=100, hold=0.045, gap=0.011, key="right"):
    t = 0.0
    log = []
    for _ in range(n):
        log.append({"t": t, "key": key, "hold": hold, "kind": "press"})
        t += hold + gap
    return log


if __name__ == "__main__":
    import human_input
    hk = human_input.HumanKeyboard(seed=1)
    import time
    for _ in range(40):
        hk.press("right")
    print(report(analyze(hk.log)))
    print()
    print(report(analyze(make_bot_log(40))))
