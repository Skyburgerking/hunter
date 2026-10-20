# -*- coding: utf-8 -*-
""

_REGISTRY = {}


def feature(name):
    def deco(fn):
        _REGISTRY[name] = fn
        return fn
    return deco


def get(name):
    return _REGISTRY.get(name)


def has(name):
    return name in _REGISTRY


def names():
    return sorted(_REGISTRY)


@feature("reward")
def _reward(state):
    return float(state.get("reward", 0.0))


@feature("dead")
def _dead(state):
    return 1.0 if state.get("done") else 0.0


@feature("one")
def _one(state):
    return 1.0
