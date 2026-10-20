# -*- coding: utf-8 -*-
""
import os
from concurrent.futures import ProcessPoolExecutor


def _resolve(ref):
    mod, attr = ref.split(":")
    obj = __import__(mod, fromlist=[attr])
    return getattr(obj, attr)


def _score_one(job):
    ref, args, spec, gene = job
    from .payload import PayloadSpace
    factory = _resolve(ref)
    space = PayloadSpace(spec)
    env = factory(*args)
    env.reset()
    score, _ = space.play(env, space.payload(gene))
    return float(score)


def map_scores(ref, args, spec, genes, workers=None):
    ""
    workers = int(workers or 0)
    if workers <= 1 or len(genes) <= 1:
        return [_score_one((ref, args, spec, g)) for g in genes]
    jobs = [(ref, args, spec, g) for g in genes]
    with ProcessPoolExecutor(max_workers=min(workers, len(jobs))) as pool:
        return list(pool.map(_score_one, jobs, chunksize=max(1, len(jobs) // (workers * 2))))


def cpu_count():
    return os.cpu_count() or 1
