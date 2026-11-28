"""Offline timestamp planner prototype; signals are not semantic observations.

Inputs are measured candidate timestamps and optional cut/motion scores. Output
contains only selected timestamps and explicit unobserved temporal gaps. No
network, video decoding, model call, subject state or persistent storage.
"""
from dataclasses import dataclass
from math import isfinite


@dataclass(frozen=True)
class Candidate:
    seconds: float
    cut: float = 0.0
    motion: float = 0.0


def plan(duration, candidates, budget, *, max_gap):
    """Reserve coverage first; use remaining budget for measured change.

    max_gap is a target, never an assertion that unobserved video was seen.
    Finite budget and sparse candidates can leave gaps; they are returned.
    """
    if not isfinite(duration) or duration <= 0 or type(budget) is not int or not 1 <= budget <= 256 or duration > 86400 or not isfinite(max_gap) or max_gap <= 0:
        raise ValueError('invalid planning bounds')
    ordered = sorted(candidates, key=lambda c: c.seconds)
    if not 1 <= len(ordered) <= 10000 or any(not all(isfinite(x) for x in (c.seconds,c.cut,c.motion)) or
                          not 0 <= c.seconds <= duration or c.cut < 0 or c.motion < 0 for c in ordered):
        raise ValueError('invalid candidate')
    if len({c.seconds for c in ordered}) != len(ordered):
        raise ValueError('duplicate timestamp')
    selected = []
    # Split the entire duration into equal windows, with budget distributed
    # evenly. Empty windows stay gaps rather than being invented as frames.
    windows = min(budget, max(1, int(-(-duration // max_gap))))
    for i in range(windows):
        lo, hi = duration*i/windows, duration*(i+1)/windows
        local = [c for c in ordered if lo <= c.seconds < hi or (i == windows-1 and c.seconds == duration)]
        if local:
            midpoint = (lo+hi)/2
            selected.append(min(local, key=lambda c: (abs(c.seconds-midpoint),c.seconds)))
    remaining = [c for c in ordered if c not in selected]
    # Change is an engineering cue only, not a claim of meaningful action.
    remaining.sort(key=lambda c: (-max(c.cut,c.motion),c.seconds))
    selected.extend(remaining[:max(0,budget-len(selected))])
    times = tuple(sorted(c.seconds for c in selected))
    points = (0.0, *times, duration)
    gaps = tuple((a,b) for a,b in zip(points,points[1:]) if b-a > max_gap)
    return {'timestamps':times,'gaps':gaps,'max_gap_target':max_gap,
            'coverage_target_met':not gaps,'meaning':'sampling only; unseen intervals remain unobserved'}
